"""“Já realizei este trabalho” e a área “Ações da tarefa”.

A tarefa foi feita, mas ninguém a iniciou. A pessoa informa quando trabalhou; o
sistema registra esse período **e conclui a tarefa agora** — o passado
operacional da fila nunca é reescrito. O relógio é congelado em
`FIXED_NOW` (quarta-feira, 15:00, hora local) para que “hoje”, “ontem” e “há
mais de 7 dias” não dependam da hora em que a suíte roda.
"""

import datetime
import json
from unittest import mock

from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from acessos.services import AuthorizationService
from acessos.testing import grant_action, grant_actions
from audit.models import AuditLog
from notifications.models import Notification

from .models import Task, TaskExecutor, WorkSession
from .services import RETROACTIVE_JUSTIFICATION_DAYS, ActivityError, QueueService, TaskService
from .testing import WORKER_ACTIONS, ProcessTestCase, make_user

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
Reason = WorkSession.ManualReason


def local(year, month, day, hour=0, minute=0):
    return timezone.make_aware(datetime.datetime(year, month, day, hour, minute))


FIXED_NOW = local(2026, 9, 30, 15, 0)


class RetroactiveTestCase(ProcessTestCase):
    def setUp(self):
        patcher = mock.patch("django.utils.timezone.now", return_value=FIXED_NOW)
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()
        self.now = FIXED_NOW
        self.task = self.queued_task("Entrevista com Jovem Aprendizes")

    # -- fábricas -------------------------------------------------------------

    def queued_task(self, title, responsavel=None, sector=None, created_days_ago=30, **extra):
        task = Task.objects.create(
            activity=self.activity,
            sector=sector or self.comercial,
            title=title,
            created_by=self.owner,
            responsavel=responsavel or self.ryan,
            status=Task.Status.DISPONIVEL,
            **extra,
        )
        QueueService.enqueue(task, task.sector, user=self.owner)
        # A tarefa existe há tempo: senão qualquer trabalho “de ontem” terminaria
        # antes de ela ser criada.
        Task.objects.filter(pk=task.pk).update(created_at=self.now - datetime.timedelta(days=created_days_ago))
        task.refresh_from_db()
        return task

    def process_tasks(self):
        return [task for task in self.tasks() if task.process_step_id]

    def period(self, days_ago=0, start=(9, 0), end=(10, 30)):
        day = (self.now - datetime.timedelta(days=days_ago)).date()
        return (
            local(day.year, day.month, day.day, *start),
            local(day.year, day.month, day.day, *end),
        )

    def register(self, task=None, user=None, days_ago=0, start=(9, 0), end=(10, 30), reason=Reason.ESQUECI_INICIAR, note=""):
        started_at, ended_at = self.period(days_ago, start, end)
        return TaskService.register_completed_work(task or self.task, user or self.ryan, started_at, ended_at, reason, note)

    def assertRefused(self, *args, message=None, **kwargs):
        """Recusou **e não deixou nada para trás**."""
        with self.assertRaises(ActivityError) as caught:
            self.register(*args, **kwargs)
        if message:
            self.assertIn(message, str(caught.exception))
        task = kwargs.get("task") or (args[0] if args else self.task)
        task.refresh_from_db()
        self.assertNotEqual(task.status, Task.Status.CONCLUIDA)
        self.assertFalse(WorkSession.objects.filter(task=task).exists())
        self.assertFalse(AuditLog.objects.filter(task=task, action=AuditLog.Action.RETROACTIVE_LOGGED).exists())
        return caught.exception


# ---------------------------------------------------------------------------
# Serviço
# ---------------------------------------------------------------------------


class RegisterCompletedWorkTests(RetroactiveTestCase):
    def test_records_the_worked_period_as_an_informed_session(self):
        self.register()
        session = WorkSession.objects.get(task=self.task)
        started_at, ended_at = self.period()
        self.assertEqual((session.started_at, session.ended_at), (started_at, ended_at))
        self.assertTrue(session.is_manual)
        self.assertEqual(session.user, self.ryan)
        self.assertEqual(session.logged_at, self.now)
        self.assertEqual(session.manual_reason, Reason.ESQUECI_INICIAR)
        self.assertEqual(session.note, "")

    def test_concludes_the_task_now_not_at_the_informed_end(self):
        self.register()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)
        self.assertEqual(self.task.completed_by, self.ryan)
        # 10:30 é quando a pessoa diz que terminou; 15:00 é quando o sistema soube.
        self.assertEqual(self.task.completed_at, self.now)
        self.assertNotEqual(self.task.completed_at, self.period()[1])

    def test_first_action_of_task_and_activity_is_now(self):
        self.assertIsNone(self.task.first_action_at)
        self.register()
        self.task.refresh_from_db()
        self.activity.refresh_from_db()
        self.assertEqual(self.task.first_action_at, self.now)
        self.assertEqual(self.activity.first_action_at, self.now)

    def test_leaves_the_queue_now_and_the_queue_is_renumbered(self):
        other = self.queued_task("Segunda da fila")
        self.assertEqual(self.task.queue_entries.get().position, 1)
        self.register()
        entry = self.task.queue_entries.get()
        self.assertEqual(entry.left_at, self.now)
        self.assertFalse(self.active_queue(self.comercial).filter(task=self.task).exists())
        self.assertEqual(other.queue_entries.get(left_at__isnull=True).position, 1)

    def test_releases_the_next_step_now(self):
        dependent = Task.objects.create(
            activity=self.activity, sector=self.compras, title="Depois", created_by=self.owner,
            responsavel=self.vitor, status=Task.Status.DISPONIVEL, depends_on=self.task,
        )
        self.assertFalse(dependent.queue_entries.exists())
        self.register()
        entry = dependent.queue_entries.get(left_at__isnull=True)
        self.assertEqual(entry.entered_at, self.now)
        self.assertTrue(AuditLog.objects.filter(task=dependent, action=AuditLog.Action.TASK_RELEASED).exists())

    def test_audits_the_informed_period_and_the_completion(self):
        self.register(note="")
        informed = AuditLog.objects.get(task=self.task, action=AuditLog.Action.RETROACTIVE_LOGGED)
        self.assertEqual(informed.user, self.ryan)
        self.assertEqual(informed.activity, self.activity)
        self.assertEqual(informed.new_value, "30/09/2026 09:00–10:30")
        self.assertIn("Informado em 30/09/2026 15:00", informed.reason)
        self.assertIn("Esqueci de iniciar", informed.reason)
        completed = AuditLog.objects.get(task=self.task, action=AuditLog.Action.COMPLETE)
        self.assertEqual(completed.new_value, Task.Status.CONCLUIDA)

    def test_audit_carries_the_comment(self):
        self.register(reason=Reason.OUTRO, note="Fiz a entrevista na sede do cliente")
        informed = AuditLog.objects.get(task=self.task, action=AuditLog.Action.RETROACTIVE_LOGGED)
        self.assertIn("Outro", informed.reason)
        self.assertIn("Fiz a entrevista na sede do cliente", informed.reason)

    def test_audit_shows_both_days_when_the_work_crossed_midnight(self):
        started_at = local(2026, 9, 29, 23, 0)
        ended_at = local(2026, 9, 30, 1, 0)
        TaskService.register_completed_work(self.task, self.ryan, started_at, ended_at, Reason.ESQUECI_INICIAR)
        informed = AuditLog.objects.get(task=self.task, action=AuditLog.Action.RETROACTIVE_LOGGED)
        self.assertEqual(informed.new_value, "29/09/2026 23:00 – 30/09/2026 01:00")

    def test_owner_is_notified_of_the_completion(self):
        Notification.objects.all().delete()
        self.register()
        rows = Notification.objects.filter(task=self.task, event_type=Notification.EventType.TASK_COMPLETED)
        self.assertIn(self.owner, {row.recipient for row in rows})

    def test_returns_the_concluded_task(self):
        result = self.register()
        self.assertEqual(result.pk, self.task.pk)
        self.assertEqual(result.status, Task.Status.CONCLUIDA)

    def test_task_marked_as_available_also_works(self):
        self.task.status = Task.Status.DISPONIVEL
        self.task.save(update_fields=["status"])
        self.register()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)

    def test_previous_day_is_allowed_without_comment(self):
        self.register(days_ago=1)
        session = WorkSession.objects.get(task=self.task)
        self.assertEqual(timezone.localtime(session.started_at).date(), (self.now - datetime.timedelta(days=1)).date())
        self.assertEqual(session.logged_at, self.now)

    def test_seven_days_ago_still_needs_no_justification(self):
        self.assertEqual(RETROACTIVE_JUSTIFICATION_DAYS, 7)
        self.register(days_ago=RETROACTIVE_JUSTIFICATION_DAYS)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)

    def test_more_than_seven_days_ago_asks_for_a_justification(self):
        error = self.assertRefused(days_ago=RETROACTIVE_JUSTIFICATION_DAYS + 1, message="justificativa")
        self.assertIn("7 dias", str(error))

    def test_more_than_seven_days_ago_with_a_justification_works(self):
        self.register(days_ago=10, note="Estava de férias e só lancei agora")
        session = WorkSession.objects.get(task=self.task)
        self.assertEqual(session.note, "Estava de férias e só lancei agora")
        self.assertEqual(session.manual_reason, Reason.ESQUECI_INICIAR)

    def test_every_reason_is_accepted_and_stored(self):
        for reason in (Reason.ESQUECI_INICIAR, Reason.FORA_DA_LPS, Reason.AJUSTE_PERIODO):
            task = self.queued_task(f"Tarefa {reason}")
            self.register(task=task, reason=reason)
            self.assertEqual(WorkSession.objects.get(task=task).manual_reason, reason)

    def test_other_requires_a_comment(self):
        self.assertRefused(reason=Reason.OUTRO, message="comentário")
        self.assertRefused(reason=Reason.OUTRO, note="   ", message="comentário")
        self.register(reason=Reason.OUTRO, note="Reunião com o cliente")
        self.assertEqual(WorkSession.objects.get(task=self.task).note, "Reunião com o cliente")

    def test_comment_is_trimmed(self):
        self.register(reason=Reason.FORA_DA_LPS, note="  Trabalhei no sistema do cliente  ")
        self.assertEqual(WorkSession.objects.get(task=self.task).note, "Trabalhei no sistema do cliente")

    def test_unknown_or_missing_reason_is_refused(self):
        self.assertRefused(reason="INVENTADO", message="motivo")
        self.assertRefused(reason="", message="motivo")

    def test_comment_length_is_limited(self):
        self.assertRefused(reason=Reason.OUTRO, note="x" * 256, message="255")

    def test_overlap_with_other_sessions_is_allowed(self):
        # Regras 04 §115: sobreposição não é proibida (a mesma pessoa pode ter
        # cronometrado outra tarefa no mesmo horário).
        other = self.queued_task("Outra tarefa")
        WorkSession.objects.create(task=other, user=self.ryan, started_at=self.period()[0], ended_at=self.period()[1])
        self.register()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)


class RegisterCompletedWorkPeriodTests(RetroactiveTestCase):
    def test_end_must_be_after_start(self):
        self.assertRefused(start=(10, 0), end=(9, 0), message="depois")
        self.assertRefused(start=(10, 0), end=(10, 0), message="depois")

    def test_missing_times_are_refused(self):
        with self.assertRaises(ActivityError):
            TaskService.register_completed_work(self.task, self.ryan, None, self.period()[1], Reason.ESQUECI_INICIAR)
        with self.assertRaises(ActivityError):
            TaskService.register_completed_work(self.task, self.ryan, self.period()[0], None, Reason.ESQUECI_INICIAR)

    def test_work_cannot_end_in_the_future(self):
        self.assertRefused(start=(14, 0), end=(16, 0), message="futuro")

    def test_work_until_right_now_is_fine(self):
        self.register(start=(14, 0), end=(15, 0))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)

    def test_work_cannot_end_before_the_task_existed(self):
        task = self.queued_task("Criada hoje", created_days_ago=0)
        Task.objects.filter(pk=task.pk).update(created_at=local(2026, 9, 30, 12, 0))
        task.refresh_from_db()
        error = self.assertRefused(task=task, start=(9, 0), end=(10, 0), message="só foi criada")
        self.assertIn("30/09/2026 às 12:00", str(error))

    def test_work_that_ends_after_the_task_was_created_is_fine(self):
        task = self.queued_task("Criada hoje", created_days_ago=0)
        Task.objects.filter(pk=task.pk).update(created_at=local(2026, 9, 30, 9, 30))
        task.refresh_from_db()
        self.register(task=task, start=(9, 0), end=(10, 0))
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.CONCLUIDA)


class RegisterCompletedWorkPermissionTests(RetroactiveTestCase):
    def test_responsavel_with_the_permission_can(self):
        self.register(user=self.ryan)
        self.task.refresh_from_db()
        self.assertEqual(self.task.completed_by, self.ryan)

    def test_participant_with_the_permission_can(self):
        TaskExecutor.objects.create(task=self.task, user=self.paulo, added_by=self.owner)
        self.register(user=self.paulo)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)
        self.assertEqual(self.task.completed_by, self.paulo)
        self.assertEqual(WorkSession.objects.get(task=self.task).user, self.paulo)

    def test_does_not_need_the_manual_time_permission(self):
        self.assertFalse(AuthorizationService.can(self.ryan, catalog.TEMPO_LANCAR_MANUAL, self.task))
        self.register(user=self.ryan)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)

    def test_add_time_still_needs_the_manual_time_permission(self):
        with self.assertRaises(ActivityError):
            TaskService.log_manual_time(self.task, self.ryan, *self.period(), logged_by=self.ryan)

    def test_someone_who_is_not_on_the_task_cannot_even_with_the_permission(self):
        self.assertTrue(AuthorizationService.can(self.vitor, catalog.TAREFA_CONCLUIR, self.task))
        self.assertRefused(user=self.vitor, message="responsável ou um participante")

    def test_responsavel_without_the_permission_cannot(self):
        unauthorized = make_user("sem_permissao", self.org)
        task = self.queued_task("Sem permissão", responsavel=unauthorized)
        self.assertRefused(task=task, user=unauthorized)

    def test_stranger_cannot(self):
        self.assertRefused(user=self.stranger)

    def test_other_organization_cannot(self):
        foreign = make_user("gestor_alheio", self.other_org, WORKER_ACTIONS)
        self.assertRefused(user=foreign)

    def test_permission_scoped_to_another_sector_is_not_enough(self):
        scoped = make_user("so_compras", self.org)
        grant_action(scoped, catalog.TAREFA_CONCLUIR, organization=self.org, sector=self.compras)
        task = self.queued_task("Do comercial", responsavel=scoped)
        self.assertRefused(task=task, user=scoped)


class RegisterCompletedWorkStatusTests(RetroactiveTestCase):
    def test_task_in_execution_is_sent_to_the_normal_conclusion(self):
        TaskService.start(self.task, self.ryan)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_EXECUCAO)
        with self.assertRaisesMessage(ActivityError, "Concluir tarefa"):
            self.register()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_EXECUCAO)
        self.assertFalse(WorkSession.objects.filter(task=self.task, is_manual=True).exists())

    def test_finished_blocked_or_cancelled_tasks_are_refused(self):
        for status in (Task.Status.CONCLUIDA, Task.Status.CANCELADA, Task.Status.BLOQUEADA, Task.Status.DEVOLVIDA):
            task = self.queued_task(f"Em {status}")
            Task.objects.filter(pk=task.pk).update(status=status)
            task.refresh_from_db()
            with self.assertRaises(ActivityError, msg=status):
                self.register(task=task)
            self.assertFalse(WorkSession.objects.filter(task=task).exists(), msg=status)

    def test_cannot_be_used_twice(self):
        self.register()
        with self.assertRaises(ActivityError):
            self.register()
        self.assertEqual(WorkSession.objects.filter(task=self.task).count(), 1)

    def test_waiting_for_the_previous_step_is_refused(self):
        predecessor = self.queued_task("Etapa anterior")
        dependent = Task.objects.create(
            activity=self.activity, sector=self.comercial, title="Espera", created_by=self.owner,
            responsavel=self.ryan, status=Task.Status.DISPONIVEL, depends_on=predecessor,
        )
        Task.objects.filter(pk=dependent.pk).update(created_at=self.now - datetime.timedelta(days=30))
        dependent.refresh_from_db()
        error = self.assertRefused(task=dependent, message="Etapa anterior")
        self.assertIn("depende", str(error))

    def test_after_the_previous_step_is_concluded_it_works(self):
        predecessor = self.queued_task("Etapa anterior")
        dependent = Task.objects.create(
            activity=self.activity, sector=self.comercial, title="Espera", created_by=self.owner,
            responsavel=self.ryan, status=Task.Status.DISPONIVEL, depends_on=predecessor,
        )
        Task.objects.filter(pk=dependent.pk).update(created_at=self.now - datetime.timedelta(days=30))
        TaskService.complete(predecessor, self.ryan)
        dependent.refresh_from_db()
        self.register(task=dependent)
        dependent.refresh_from_db()
        self.assertEqual(dependent.status, Task.Status.CONCLUIDA)


class RegisterCompletedWorkProcessTests(RetroactiveTestCase):
    def setUp(self):
        super().setUp()
        self.apply()
        self.first, self.second, self.third = self.process_tasks()
        Task.objects.filter(activity=self.activity).exclude(pk=self.task.pk).update(
            created_at=self.now - datetime.timedelta(days=30)
        )
        self.first.refresh_from_db()

    def test_missing_required_inputs_block_it(self):
        error = self.assertRefused(task=self.first, user=self.ryan, message="inputs obrigatórios")
        self.assertIn("Projetos", str(error))

    def test_with_the_inputs_received_it_concludes_and_releases_the_next_step(self):
        self.receive_all_required_inputs()
        self.assertFalse(self.active_queue(self.compras).filter(task=self.second).exists())
        self.register(task=self.first, user=self.ryan)
        self.first.refresh_from_db()
        self.assertEqual(self.first.status, Task.Status.CONCLUIDA)
        self.assertTrue(self.active_queue(self.compras).filter(task=self.second).exists())
        self.assertEqual(self.second.queue_entries.get().entered_at, self.now)
        self.assertEqual(self.active_queue(self.comercial).filter(task=self.third).count(), 0)

    def test_the_second_step_cannot_be_skipped_to(self):
        self.receive_all_required_inputs()
        self.assertRefused(task=self.second, user=self.vitor, message="depende")


class RegisterCompletedWorkAtomicityTests(RetroactiveTestCase):
    def test_a_failure_in_the_conclusion_leaves_nothing_behind(self):
        with mock.patch.object(TaskService, "complete", side_effect=ActivityError("falhou no meio")):
            with self.assertRaisesMessage(ActivityError, "falhou no meio"):
                self.register()
        self.task.refresh_from_db()
        self.activity.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_FILA)
        self.assertIsNone(self.task.first_action_at)
        self.assertIsNone(self.activity.first_action_at)
        self.assertFalse(WorkSession.objects.filter(task=self.task).exists())
        self.assertFalse(AuditLog.objects.filter(task=self.task, action=AuditLog.Action.RETROACTIVE_LOGGED).exists())
        self.assertTrue(self.task.queue_entries.filter(left_at__isnull=True).exists())


class AddTimeStillWorksTests(RetroactiveTestCase):
    def test_add_time_records_when_it_was_informed_without_a_reason(self):
        grant_actions(self.ryan, [catalog.TEMPO_LANCAR_MANUAL], organization=self.org)
        started_at, ended_at = self.period(days_ago=1)
        session = TaskService.log_manual_time(self.task, self.ryan, started_at, ended_at, logged_by=self.ryan)
        session.refresh_from_db()
        self.assertTrue(session.is_manual)
        self.assertEqual(session.logged_at, self.now)
        self.assertEqual(session.manual_reason, "")
        # só acrescenta tempo: não conclui nada
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_FILA)


# ---------------------------------------------------------------------------
# Telas
# ---------------------------------------------------------------------------


class RetroactiveViewTestCase(RetroactiveTestCase):
    def setUp(self):
        super().setUp()
        self.detail = reverse("task-detail", args=[self.task.pk])
        self.url = reverse("task-retroactive", args=[self.task.pk])

    def login(self, user):
        self.client.force_login(user)

    def payload(self, **overrides):
        data = {
            "date": "2026-09-30",
            "start_time": "09:00",
            "end_time": "10:30",
            "reason": Reason.ESQUECI_INICIAR,
            "note": "",
        }
        data.update(overrides)
        return data


class ActionButtonTests(RetroactiveViewTestCase):
    def test_executor_of_an_unstarted_task_sees_the_button_next_to_start(self):
        self.login(self.ryan)
        response = self.client.get(self.detail)
        self.assertContains(response, self.url)
        self.assertContains(response, "Já realizei este trabalho")
        self.assertContains(response, "Iniciar tarefa")
        self.assertTrue(response.context["can_retroactive"])

    def test_participant_sees_it_too(self):
        TaskExecutor.objects.create(task=self.task, user=self.paulo, added_by=self.owner)
        self.login(self.paulo)
        self.assertContains(self.client.get(self.detail), self.url)

    def test_someone_who_is_not_on_the_task_does_not(self):
        self.login(self.vitor)
        response = self.client.get(self.detail)
        self.assertNotContains(response, self.url)
        self.assertFalse(response.context["can_retroactive"])

    def test_nobody_without_the_permission_does(self):
        self.login(self.stranger)
        self.assertNotContains(self.client.get(self.detail), self.url)

    def test_not_while_the_task_is_running(self):
        TaskService.start(self.task, self.ryan)
        self.login(self.ryan)
        response = self.client.get(self.detail)
        self.assertNotContains(response, self.url)
        self.assertFalse(response.context["can_retroactive"])

    def test_not_after_the_task_is_concluded(self):
        TaskService.complete(self.task, self.ryan)
        self.login(self.ryan)
        self.assertNotContains(self.client.get(self.detail), self.url)

    def test_not_while_waiting_for_the_previous_step(self):
        predecessor = self.queued_task("Etapa anterior")
        waiting = Task.objects.create(
            activity=self.activity, sector=self.comercial, title="Espera", created_by=self.owner,
            responsavel=self.ryan, status=Task.Status.DISPONIVEL, depends_on=predecessor,
        )
        self.login(self.ryan)
        response = self.client.get(reverse("task-detail", args=[waiting.pk]))
        self.assertNotContains(response, reverse("task-retroactive", args=[waiting.pk]))
        self.assertFalse(response.context["can_retroactive"])

    def test_not_while_required_process_inputs_are_missing(self):
        self.apply()
        first = self.process_tasks()[0]
        self.login(self.ryan)
        response = self.client.get(reverse("task-detail", args=[first.pk]))
        self.assertNotContains(response, reverse("task-retroactive", args=[first.pk]))
        self.receive_all_required_inputs()
        self.assertContains(self.client.get(reverse("task-detail", args=[first.pk])), reverse("task-retroactive", args=[first.pk]))

    def test_the_button_opens_the_popup(self):
        self.login(self.ryan)
        self.assertContains(self.client.get(self.detail), f'href="{self.url}" data-activity-action')

    def test_side_panel_offers_it_too(self):
        self.login(self.ryan)
        self.assertContains(self.client.get(reverse("task-drawer", args=[self.task.pk])), self.url)
        self.login(self.vitor)
        self.assertNotContains(self.client.get(reverse("task-drawer", args=[self.task.pk])), self.url)


class TaskActionsBarTests(RetroactiveViewTestCase):
    def test_the_old_details_block_is_gone(self):
        self.login(self.owner)
        response = self.client.get(self.detail)
        self.assertNotContains(response, "Editar, mudar prazo ou encaminhar tarefa")
        self.assertNotContains(response, "Registrar tempo já trabalhado")
        self.assertContains(response, "Ações da tarefa")
        self.assertContains(response, "Mais ações")

    def test_edit_is_in_sight_and_the_rest_is_in_more_actions(self):
        self.login(self.ryan)
        response = self.client.get(self.detail)
        self.assertContains(response, reverse("task-edit", args=[self.task.pk]))
        self.assertContains(response, 'class="menu-more"')
        self.assertContains(response, reverse("task-move", args=[self.task.pk]))
        self.assertContains(response, reverse("task-block", args=[self.task.pk]))
        self.assertContains(response, reverse("task-cancel", args=[self.task.pk]))

    def test_each_item_only_appears_for_who_can_use_it(self):
        self.login(self.ryan)
        response = self.client.get(self.detail)
        # o colaborador não tem devolver, propor prazo nem lançar tempo
        self.assertNotContains(response, reverse("task-return", args=[self.task.pk]))
        self.assertNotContains(response, reverse("deadline-propose", args=[self.task.pk]))
        self.assertNotContains(response, reverse("task-manual-time", args=[self.task.pk]))
        self.assertFalse(response.context["can_return"])

    def test_granting_an_action_adds_its_item(self):
        grant_actions(self.ryan, [catalog.TAREFA_DEVOLVER, catalog.PRAZO_PROPOR, catalog.TEMPO_LANCAR_MANUAL], organization=self.org)
        self.login(self.ryan)
        response = self.client.get(self.detail)
        self.assertContains(response, reverse("task-return", args=[self.task.pk]))
        self.assertContains(response, reverse("deadline-propose", args=[self.task.pk]))
        self.assertContains(response, reverse("task-manual-time", args=[self.task.pk]))
        self.assertContains(response, "Adicionar tempo trabalhado")

    def test_cancel_is_the_last_item_and_marked_as_dangerous(self):
        self.login(self.ryan)
        body = self.client.get(self.detail).content.decode()
        self.assertIn("menu-more__danger", body)
        self.assertLess(body.index("menu-more__divider"), body.index("menu-more__danger"))

    def test_the_bar_disappears_when_nothing_is_allowed(self):
        self.login(self.stranger)
        response = self.client.get(self.detail)
        self.assertNotContains(response, "task-actions-bar")
        self.assertNotContains(response, 'class="menu-more"')

    def test_block_is_not_offered_while_already_blocked(self):
        TaskService.block(self.task, self.ryan, "Falta o contato do cliente")
        self.login(self.ryan)
        response = self.client.get(self.detail)
        self.assertNotContains(response, reverse("task-block", args=[self.task.pk]))
        self.assertContains(response, reverse("task-move", args=[self.task.pk]))

    def test_no_actions_on_a_concluded_task(self):
        TaskService.complete(self.task, self.ryan)
        self.login(self.owner)
        response = self.client.get(self.detail)
        self.assertNotContains(response, "task-actions-bar")

    def test_every_action_opens_as_a_window_and_keeps_a_real_link(self):
        # sem JavaScript o link continua levando à página da ação
        grant_actions(self.ryan, [catalog.TAREFA_DEVOLVER, catalog.PRAZO_PROPOR, catalog.TEMPO_LANCAR_MANUAL], organization=self.org)
        self.login(self.ryan)
        body = self.client.get(self.detail).content.decode()
        for name in ("task-edit", "task-return", "task-move", "task-dependency", "task-block",
                     "deadline-propose", "task-manual-time", "task-cancel"):
            url = reverse(name, args=[self.task.pk])
            self.assertIn(f'href="{url}" data-activity-action', body, msg=name)


class RetroactivePopupTests(RetroactiveViewTestCase):
    def test_popup_needs_to_be_someone_who_can_conclude(self):
        self.login(self.stranger)
        self.assertEqual(self.client.get(self.url, **AJAX).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.payload(), **AJAX).status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_FILA)

    def test_other_organization_gets_404(self):
        foreign = make_user("gestor_alheio", self.other_org, WORKER_ACTIONS)
        self.login(foreign)
        self.assertEqual(self.client.get(self.url, **AJAX).status_code, 404)
        self.assertEqual(self.client.post(self.url, self.payload(), **AJAX).status_code, 404)

    def test_popup_is_simple_and_does_not_use_jargon(self):
        self.login(self.ryan)
        response = self.client.get(self.url, **AJAX)
        for text in ("Já realizei este trabalho", "Data", "Comecei às", "Terminei às", "Motivo", "Registrar e concluir"):
            self.assertContains(response, text)
        self.assertContains(response, "A tarefa será concluída agora.")
        body = response.content.decode()
        popup = body[body.index("data-retroactive-form"):body.index("</form>")].lower()
        for jargon in ("retroativ", "lançamento manual", "sessão", "sessao"):
            self.assertNotIn(jargon, popup)

    def test_popup_fields_and_defaults(self):
        self.login(self.ryan)
        response = self.client.get(self.url, **AJAX)
        for name in ("date", "start_time", "end_time", "reason", "note"):
            self.assertContains(response, f'name="{name}"')
        self.assertContains(response, 'value="2026-09-30"')  # data padrão: hoje
        self.assertContains(response, 'value="15:00"')  # término padrão: agora
        self.assertContains(response, 'data-retroactive-form')
        self.assertContains(response, 'data-justify-days="7"')
        self.assertContains(response, 'data-today="2026-09-30"')
        self.assertContains(response, "Esqueci de iniciar")
        self.assertContains(response, "Trabalhei fora da LPS")
        self.assertContains(response, "Ajuste do período")
        self.assertContains(response, "Outro")

    def test_default_reason_is_forgot_to_start(self):
        self.login(self.ryan)
        form = self.client.get(self.url, **AJAX).context["form"]
        self.assertEqual(form["reason"].value(), Reason.ESQUECI_INICIAR)

    def test_ajax_post_registers_and_answers_json(self):
        self.login(self.ryan)
        response = self.client.post(self.url, self.payload(), **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["redirect_url"], self.detail)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)
        self.assertEqual(self.task.completed_at, self.now)
        session = WorkSession.objects.get(task=self.task)
        self.assertEqual((session.started_at, session.ended_at), self.period())
        self.assertEqual(session.manual_reason, Reason.ESQUECI_INICIAR)

    def test_post_without_javascript_redirects_to_the_task(self):
        self.login(self.ryan)
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, self.detail)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)

    def test_success_message_is_shown(self):
        self.login(self.ryan)
        response = self.client.post(self.url, self.payload(), follow=True)
        self.assertContains(response, "Trabalho registrado e tarefa concluída.")

    def test_comment_is_only_mandatory_for_other(self):
        self.login(self.ryan)
        response = self.client.post(self.url, self.payload(reason=Reason.OUTRO, note=""), **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("note", json.loads(response.content)["errors"])
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_FILA)
        response = self.client.post(self.url, self.payload(reason=Reason.OUTRO, note="Reunião externa"), **AJAX)
        self.assertEqual(response.status_code, 200)

    def test_the_form_hides_the_comment_until_needed_but_keeps_it_in_the_page(self):
        self.login(self.ryan)
        response = self.client.get(self.url, **AJAX)
        self.assertContains(response, "data-note-row")
        self.assertContains(response, "data-note-required hidden")

    def test_end_before_start_is_reported_on_the_field(self):
        self.login(self.ryan)
        response = self.client.post(self.url, self.payload(start_time="11:00", end_time="10:00"), **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("end_time", json.loads(response.content)["errors"])

    def test_future_date_is_reported_on_the_field(self):
        self.login(self.ryan)
        response = self.client.post(self.url, self.payload(date="2026-10-01"), **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", json.loads(response.content)["errors"])

    def test_end_later_today_is_refused_by_the_service(self):
        self.login(self.ryan)
        response = self.client.post(self.url, self.payload(start_time="14:00", end_time="17:00"), **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("futuro", json.dumps(json.loads(response.content)["errors"]))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_FILA)

    def test_old_work_without_comment_is_refused_with_a_clear_message(self):
        self.login(self.ryan)
        response = self.client.post(self.url, self.payload(date="2026-09-01"), **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("justificativa", json.dumps(json.loads(response.content)["errors"], ensure_ascii=False))
        response = self.client.post(self.url, self.payload(date="2026-09-01", note="Lançando agora"), **AJAX)
        self.assertEqual(response.status_code, 200)

    def test_a_task_already_running_is_refused_with_the_reason(self):
        TaskService.start(self.task, self.ryan)
        self.login(self.ryan)
        response = self.client.post(self.url, self.payload(), **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Concluir tarefa", json.dumps(json.loads(response.content)["errors"], ensure_ascii=False))

    def test_page_without_javascript_is_a_complete_page(self):
        self.login(self.ryan)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")
        self.assertEqual(response.context["nav_active"], "tasks")


class InformedTimeCardTests(RetroactiveViewTestCase):
    def informed(self, task, started_at, ended_at, reason=Reason.ESQUECI_INICIAR, note="", user=None):
        return WorkSession.objects.create(
            task=task, user=user or self.ryan, started_at=started_at, ended_at=ended_at, is_manual=True,
            logged_at=self.now, manual_reason=reason, note=note,
        )

    def timed(self, task, started_at, ended_at, user=None):
        return WorkSession.objects.create(task=task, user=user or self.ryan, started_at=started_at, ended_at=ended_at)

    def test_card_separates_timer_from_informed_time(self):
        self.timed(self.task, local(2026, 9, 29, 9, 0), local(2026, 9, 29, 10, 0))
        self.informed(self.task, *self.period(start=(13, 0), end=(14, 30)))
        self.login(self.owner)
        response = self.client.get(self.detail)
        self.assertEqual(response.context["timer_hours"], datetime.timedelta(hours=1))
        self.assertEqual(response.context["informed_hours"], datetime.timedelta(hours=1, minutes=30))
        self.assertContains(response, "Cronometrado")
        self.assertContains(response, "Informado pela pessoa")
        # o total da equipe continua sendo a soma
        self.assertEqual(response.context["man_hours"], datetime.timedelta(hours=2, minutes=30))

    def test_informed_session_shows_who_when_and_why(self):
        self.informed(self.task, *self.period(start=(13, 0), end=(14, 30)), reason=Reason.FORA_DA_LPS, note="No cliente")
        self.login(self.owner)
        response = self.client.get(self.detail)
        self.assertContains(response, "Informado em 30/09 15:00")
        self.assertContains(response, "Trabalhei fora da LPS")
        self.assertContains(response, "No cliente")

    def test_work_from_a_previous_day_is_highlighted(self):
        self.informed(self.task, *self.period(days_ago=2))
        self.login(self.owner)
        response = self.client.get(self.detail)
        self.assertContains(response, "Dia anterior")
        self.assertTrue(response.context["sessions"][0].is_past_day)

    def test_work_from_the_same_day_is_not_highlighted(self):
        self.informed(self.task, *self.period())
        self.login(self.owner)
        response = self.client.get(self.detail)
        self.assertNotContains(response, "Dia anterior")
        self.assertFalse(response.context["sessions"][0].is_past_day)

    def test_timer_sessions_are_never_highlighted(self):
        self.timed(self.task, local(2026, 9, 28, 9, 0), local(2026, 9, 28, 10, 0))
        self.login(self.owner)
        response = self.client.get(self.detail)
        self.assertNotContains(response, "Dia anterior")
        self.assertEqual(response.context["informed_hours"], datetime.timedelta())

    def test_old_manual_sessions_without_a_reason_still_render(self):
        WorkSession.objects.create(
            task=self.task, user=self.ryan, started_at=self.period()[0], ended_at=self.period()[1], is_manual=True
        )
        self.login(self.owner)
        response = self.client.get(self.detail)
        self.assertContains(response, "Lançado manualmente")
        self.assertFalse(response.context["sessions"][0].is_past_day)

    def test_a_retroactive_registration_shows_up_in_the_card(self):
        self.login(self.ryan)
        self.client.post(self.url, self.payload(date="2026-09-29"), **AJAX)
        response = self.client.get(self.detail)
        self.assertContains(response, "Esqueci de iniciar")
        self.assertContains(response, "Dia anterior")
        self.assertEqual(response.context["informed_hours"], datetime.timedelta(hours=1, minutes=30))
        self.assertEqual(response.context["timer_hours"], datetime.timedelta())
