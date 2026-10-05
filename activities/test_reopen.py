"""Reabrir tarefa e atividade concluídas.

Quem reabre: `self.owner` (dono da atividade) recebe `tarefa.reabrir` **e**
`atividade.reabrir`; `self.manager` só `tarefa.reabrir`; `self.ryan` só executa.
"""

import json
from unittest import mock

from django.urls import reverse

from acessos import catalog
from acessos.testing import grant_action, grant_actions
from audit.models import AuditLog
from notifications.models import Notification
from processes.models import ActivityInputValue

from .models import Activity, QueueEntry, Task, TaskChecklistItem, WorkSession
from .process_application import ActivityProcessService
from .services import ActivityError, ActivityService, QueueService, TaskService
from .testing import WORKER_ACTIONS, ProcessTestCase, make_user

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class ReopenTestCase(ProcessTestCase):
    def setUp(self):
        super().setUp()
        grant_actions(self.owner, [catalog.TAREFA_REABRIR, catalog.ATIVIDADE_REABRIR], organization=self.org)
        self.manager = make_user("gestor", self.org, [catalog.TAREFA_REABRIR, *WORKER_ACTIONS])

    # -- fábricas -------------------------------------------------------------

    def queued_task(self, title="Tarefa manual", activity=None, sector=None, responsavel=None, **extra):
        task = Task.objects.create(
            activity=activity or self.activity,
            sector=sector or self.comercial,
            title=title,
            created_by=self.owner,
            responsavel=responsavel or self.ryan,
            status=Task.Status.DISPONIVEL,
            **extra,
        )
        QueueService.enqueue(task, task.sector, user=self.owner)
        task.refresh_from_db()
        return task

    def concluded_task(self, title="Tarefa manual", by=None, **kwargs):
        task = self.queued_task(title, **kwargs)
        TaskService.complete(task, by or self.ryan)
        task.refresh_from_db()
        return task

    def reopen(self, task, user=None, reason="Faltou conferir o material"):
        return TaskService.reopen(task, user or self.manager, reason)

    def active_entries(self, task):
        return task.queue_entries.filter(left_at__isnull=True)


# ---------------------------------------------------------------------------
# A tarefa
# ---------------------------------------------------------------------------


class ReopenTaskTests(ReopenTestCase):
    def test_reopened_task_returns_to_the_end_of_its_sector_queue(self):
        task = self.concluded_task("Primeira")
        other = self.queued_task("Já esperando")
        completed_at = task.completed_at
        self.assertIsNotNone(completed_at)

        self.reopen(task)

        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.EM_FILA)
        self.assertIsNone(task.completed_at)
        self.assertIsNone(task.completed_by)
        entry = self.active_entries(task).get()
        self.assertEqual((entry.position, entry.queue_size_at_entry), (2, 2))
        self.assertEqual(self.active_entries(other).get().position, 1)
        # nova passagem pela fila: a antiga continua como histórico
        self.assertEqual(task.queue_entries.count(), 2)
        self.assertEqual(task.queue_entries.filter(left_at__isnull=False).count(), 1)

    def test_reopen_is_audited_with_reason_and_states(self):
        task = self.concluded_task()
        self.reopen(task, reason="O cliente pediu ajuste")
        log = AuditLog.objects.get(task=task, action=AuditLog.Action.REOPEN)
        self.assertEqual(log.user, self.manager)
        self.assertEqual((log.old_value, log.new_value), ("CONCLUIDA", "EM_FILA"))
        self.assertEqual(log.reason, "O cliente pediu ajuste")
        self.assertEqual(log.activity, self.activity)

    def test_responsavel_sector_and_owner_are_notified(self):
        task = self.concluded_task(responsavel=self.ryan)
        Notification.objects.all().delete()
        self.reopen(task, reason="Ajustar quantitativos")
        rows = Notification.objects.filter(task=task, event_type=Notification.EventType.TASK_ASSIGNED)
        self.assertEqual(set(rows.values_list("recipient__username", flat=True)), {"ryan", "paulo", "dono"})
        message = rows.first().message
        self.assertIn("foi reaberta", message)
        self.assertIn("Ajustar quantitativos", message)
        self.assertEqual(rows.first().title, "Tarefa reaberta")

    def test_worked_time_checklist_and_first_action_are_preserved(self):
        task = self.queued_task()
        item = TaskChecklistItem.objects.create(task=task, text="Conferir", is_done=True, created_by=self.ryan)
        TaskService.start(task, self.ryan)
        TaskService.complete(task, self.ryan)
        task.refresh_from_db()
        first_action = task.first_action_at
        sessions = list(WorkSession.objects.filter(task=task).values_list("pk", "ended_at"))
        self.assertEqual(len(sessions), 1)

        self.reopen(task)

        task.refresh_from_db()
        self.assertEqual(list(WorkSession.objects.filter(task=task).values_list("pk", "ended_at")), sessions)
        self.assertFalse(WorkSession.objects.filter(task=task, ended_at__isnull=True).exists())
        self.assertEqual(task.first_action_at, first_action)
        item.refresh_from_db()
        self.assertTrue(item.is_done)

    def test_can_be_started_and_concluded_again(self):
        task = self.concluded_task()
        self.reopen(task)
        TaskService.start(task, self.ryan)
        TaskService.complete(task, self.ryan)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.CONCLUIDA)
        self.assertIsNotNone(task.completed_at)
        self.assertFalse(self.active_entries(task).exists())
        self.assertEqual(task.queue_entries.count(), 2)

    def test_caller_copy_is_updated(self):
        task = self.concluded_task()
        stale = Task.objects.get(pk=task.pk)
        self.reopen(stale)
        self.assertEqual(stale.status, Task.Status.EM_FILA)
        self.assertIsNone(stale.completed_at)

    def test_requires_the_permission(self):
        task = self.concluded_task()
        with self.assertRaises(ActivityError):
            TaskService.reopen(task, self.ryan, "Quero de volta")
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.CONCLUIDA)
        self.assertFalse(AuditLog.objects.filter(action=AuditLog.Action.REOPEN).exists())

    def test_permission_is_scoped_to_the_task_sector(self):
        scoped = make_user("so_compras", self.org)
        grant_action(scoped, catalog.TAREFA_REABRIR, organization=self.org, sector=self.compras)
        commercial = self.concluded_task("Do comercial", sector=self.comercial)
        purchasing = self.concluded_task("De compras", sector=self.compras, by=self.vitor)
        with self.assertRaises(ActivityError):
            TaskService.reopen(commercial, scoped, "Fora do meu setor")
        TaskService.reopen(purchasing, scoped, "No meu setor")
        purchasing.refresh_from_db()
        self.assertEqual(purchasing.status, Task.Status.EM_FILA)

    def test_reason_is_required(self):
        task = self.concluded_task()
        for reason in ("", "   ", None):
            with self.assertRaisesMessage(ActivityError, "motivo"):
                TaskService.reopen(task, self.manager, reason)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.CONCLUIDA)

    def test_only_concluded_tasks_can_be_reopened(self):
        queued = self.queued_task("Na fila")
        with self.assertRaisesMessage(ActivityError, "Somente tarefas concluídas"):
            self.reopen(queued)
        cancelled = self.queued_task("Cancelada")
        TaskService.cancel(cancelled, self.manager, "Não é mais necessária")
        with self.assertRaisesMessage(ActivityError, "Somente tarefas concluídas"):
            self.reopen(cancelled)

    def test_other_tenant_cannot_reopen(self):
        task = self.concluded_task()
        foreign = make_user("gestor_alheio", self.other_org, [catalog.TAREFA_REABRIR])
        with self.assertRaises(ActivityError):
            TaskService.reopen(task, foreign, "Intruso")
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.CONCLUIDA)

    def test_task_whose_own_predecessor_is_still_open_goes_back_to_waiting(self):
        predecessor = self.queued_task("Predecessora")
        dependent = Task.objects.create(
            activity=self.activity, sector=self.compras, title="Dependente", created_by=self.owner,
            responsavel=self.vitor, depends_on=predecessor, status=Task.Status.CONCLUIDA,
        )
        self.reopen(dependent)
        dependent.refresh_from_db()
        self.assertEqual(dependent.status, Task.Status.DISPONIVEL)
        self.assertFalse(dependent.queue_entries.exists())
        self.assertEqual(dependent.status_label, "Aguardando etapa anterior")
        # e entra na fila quando a predecessora for concluída
        TaskService.complete(predecessor, self.ryan)
        dependent.refresh_from_db()
        self.assertEqual(dependent.status, Task.Status.EM_FILA)


# ---------------------------------------------------------------------------
# Tarefas seguintes (dependentes)
# ---------------------------------------------------------------------------


class ReopenWithDependentsTests(ReopenTestCase):
    def setUp(self):
        super().setUp()
        self.apply()
        self.receive_all_required_inputs()
        self.t1, self.t2, self.t3 = self.tasks()
        TaskService.complete(self.t1, self.ryan)  # libera a t2 na fila de Compras
        self.t2.refresh_from_db()

    def test_dependent_that_only_waits_in_the_queue_goes_back_to_waiting(self):
        self.assertEqual(self.t2.status, Task.Status.EM_FILA)
        self.reopen(self.t1)

        self.t1.refresh_from_db()
        self.t2.refresh_from_db()
        self.assertEqual(self.t1.status, Task.Status.EM_FILA)
        self.assertEqual(self.t2.status, Task.Status.DISPONIVEL)
        self.assertFalse(self.active_entries(self.t2).exists())
        self.assertFalse(self.active_queue(self.compras).exists())
        log = AuditLog.objects.get(task=self.t2, action=AuditLog.Action.UPDATE, field_name="status")
        self.assertEqual((log.old_value, log.new_value), ("EM_FILA", "DISPONIVEL"))
        self.assertIn("foi reaberta", log.reason)
        # a tela explica a espera e o serviço volta a barrar o início
        with self.assertRaisesMessage(ActivityError, "depende da conclusão"):
            TaskService.start(self.t2, self.vitor)

    def test_the_queue_of_the_dependent_sector_is_renumbered(self):
        # fila de Compras: t2 (1), "Outra de compras" (2), "Atrás" (3)
        self.queued_task("Outra de compras", sector=self.compras, responsavel=self.vitor)
        behind = self.queued_task("Atrás", sector=self.compras, responsavel=self.vitor)
        self.assertEqual(
            list(self.active_queue(self.compras).order_by("position").values_list("task__title", "position")),
            [("Cotação de materiais", 1), ("Outra de compras", 2), ("Atrás", 3)],
        )
        self.reopen(self.t1)
        self.assertEqual(
            list(self.active_queue(self.compras).order_by("position").values_list("task__title", "position")),
            [("Outra de compras", 1), ("Atrás", 2)],
        )
        self.assertEqual(behind.queue_entries.get(left_at__isnull=True).position, 2)

    def test_concluding_the_reopened_task_releases_the_dependent_again(self):
        self.reopen(self.t1)
        TaskService.complete(self.t1, self.ryan)
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, Task.Status.EM_FILA)
        self.assertEqual(self.active_queue(self.compras).get().task, self.t2)
        self.assertEqual(AuditLog.objects.filter(task=self.t2, action=AuditLog.Action.TASK_RELEASED).count(), 2)

    def test_refused_when_the_dependent_is_in_execution(self):
        TaskService.start(self.t2, self.vitor)
        with self.assertRaises(ActivityError) as ctx:
            self.reopen(self.t1)
        self.assertIn("Cotação de materiais", str(ctx.exception))
        self.assertIn("Em execução", str(ctx.exception))
        self.t1.refresh_from_db()
        self.t2.refresh_from_db()
        self.assertEqual(self.t1.status, Task.Status.CONCLUIDA)
        self.assertEqual(self.t2.status, Task.Status.EM_EXECUCAO)

    def test_refused_when_the_dependent_was_worked_and_paused(self):
        TaskService.start(self.t2, self.vitor)
        TaskService.pause(self.t2, self.vitor)  # volta à fila, mas já tem sessão registrada
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, Task.Status.EM_FILA)
        with self.assertRaisesMessage(ActivityError, "Cotação de materiais"):
            self.reopen(self.t1)
        self.assertTrue(self.active_entries(self.t2).exists())

    def test_refused_when_the_dependent_is_concluded(self):
        TaskService.complete(self.t2, self.vitor)
        with self.assertRaisesMessage(ActivityError, "Concluída"):
            self.reopen(self.t1)
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.status, Task.Status.CONCLUIDA)

    def test_refused_when_the_dependent_is_blocked(self):
        TaskService.block(self.t2, self.vitor, "Falta fornecedor")
        with self.assertRaisesMessage(ActivityError, "Bloqueada"):
            self.reopen(self.t1)

    def test_cancelled_dependent_does_not_prevent_reopening(self):
        TaskService.cancel(self.t2, self.owner, "Não será cotada")
        self.reopen(self.t1)
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.status, Task.Status.EM_FILA)

    def test_a_refusal_changes_nothing_at_all(self):
        # t2 em execução impede; nenhuma auditoria/notificação/fila nova.
        TaskService.start(self.t2, self.vitor)
        before = (
            AuditLog.objects.count(),
            Notification.objects.count(),
            QueueEntry.objects.count(),
        )
        with self.assertRaises(ActivityError):
            self.reopen(self.t1)
        self.assertEqual(
            (AuditLog.objects.count(), Notification.objects.count(), QueueEntry.objects.count()), before
        )

    def test_process_input_gate_still_applies_after_reopening(self):
        row = ActivityInputValue.objects.get(activity=self.activity, process_input__name="Projetos")
        ActivityProcessService.update_input(self.owner, row, value="")  # reabre o input obrigatório
        self.reopen(self.t1)  # reabrir não exige inputs...
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.status, Task.Status.EM_FILA)
        with self.assertRaisesMessage(ActivityError, "Projetos"):  # ...mas iniciar continua exigindo
            TaskService.start(self.t1, self.ryan)


# ---------------------------------------------------------------------------
# Atividade concluída / cancelada
# ---------------------------------------------------------------------------


class ReopenWithActivityTests(ReopenTestCase):
    def setUp(self):
        super().setUp()
        self.task = self.concluded_task()
        ActivityService.finalize(self.activity, self.owner, Activity.CompletionOutcome.SUCESSO, "Entregue")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.CONCLUIDA)

    def test_reopens_the_activity_together_when_allowed(self):
        self.reopen(self.task, user=self.owner, reason="Cliente pediu revisão")
        self.activity.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.EM_ANDAMENTO)
        self.assertIsNotNone(self.activity.reopened_at)
        self.assertIsNone(self.activity.completed_at)
        self.assertEqual(self.task.status, Task.Status.EM_FILA)
        activity_log = AuditLog.objects.get(activity=self.activity, task__isnull=True, action=AuditLog.Action.REOPEN)
        self.assertEqual(activity_log.old_value, "CONCLUIDA")
        self.assertIn("Cliente pediu revisão", activity_log.reason)
        self.assertIn("Tarefa manual", activity_log.reason)
        self.assertEqual(AuditLog.objects.filter(task=self.task, action=AuditLog.Action.REOPEN).count(), 1)

    def test_refused_without_permission_to_reopen_the_activity(self):
        with self.assertRaisesMessage(ActivityError, "reabrir a demanda"):
            self.reopen(self.task, user=self.manager)
        self.activity.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.CONCLUIDA)
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)

    def test_cancelled_activity_cannot_have_its_tasks_reopened(self):
        Activity.objects.filter(pk=self.activity.pk).update(status=Activity.Status.CANCELADA)
        with self.assertRaisesMessage(ActivityError, "cancelada"):
            self.reopen(self.task, user=self.owner)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)

    def test_it_is_all_or_nothing(self):
        with mock.patch.object(QueueService, "enqueue", side_effect=RuntimeError("falha na fila")):
            with self.assertRaises(RuntimeError):
                self.reopen(self.task, user=self.owner)
        self.activity.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.CONCLUIDA)
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)
        self.assertIsNotNone(self.task.completed_at)
        self.assertFalse(AuditLog.objects.filter(action=AuditLog.Action.REOPEN).exists())

    def test_then_the_activity_can_be_finalized_again(self):
        self.reopen(self.task, user=self.owner)
        self.activity.refresh_from_db()  # o serviço reabriu outra cópia do objeto
        with self.assertRaisesMessage(ActivityError, "tarefas ainda não concluídas"):
            ActivityService.finalize(self.activity, self.owner, Activity.CompletionOutcome.SUCESSO, "Cedo demais")
        TaskService.complete(self.task, self.ryan)
        ActivityService.finalize(self.activity, self.owner, Activity.CompletionOutcome.SUCESSO, "Agora sim")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.CONCLUIDA)

    def test_reopening_the_activity_records_the_previous_status(self):
        ActivityService.reopen_activity(self.activity, self.owner, "Voltou")
        log = AuditLog.objects.get(activity=self.activity, task__isnull=True, action=AuditLog.Action.REOPEN)
        self.assertEqual((log.old_value, log.new_value), ("CONCLUIDA", "EM_ANDAMENTO"))


# ---------------------------------------------------------------------------
# Telas
# ---------------------------------------------------------------------------


class ReopenViewTests(ReopenTestCase):
    def setUp(self):
        super().setUp()
        self.task = self.concluded_task(responsavel=self.manager, by=self.manager)
        self.url = reverse("task-reopen", args=[self.task.pk])
        self.detail = reverse("task-detail", args=[self.task.pk])

    def login(self, user):
        self.client.force_login(user)

    # -- botão ----------------------------------------------------------------

    def test_task_page_shows_the_button_to_someone_who_can_reopen(self):
        self.login(self.manager)
        response = self.client.get(self.detail)
        self.assertContains(response, self.url)
        self.assertContains(response, "Reabrir tarefa")
        self.assertTrue(response.context["can_reopen_task"])

    def test_task_page_hides_it_from_others_and_for_open_tasks(self):
        self.login(self.ryan)
        response = self.client.get(self.detail)
        self.assertNotContains(response, self.url)
        self.assertFalse(response.context["can_reopen_task"])
        open_task = self.queued_task("Aberta", responsavel=self.manager)
        self.login(self.manager)
        response = self.client.get(reverse("task-detail", args=[open_task.pk]))
        self.assertNotContains(response, reverse("task-reopen", args=[open_task.pk]))

    def test_side_panel_offers_it_too(self):
        self.login(self.manager)
        response = self.client.get(reverse("task-drawer", args=[self.task.pk]))
        self.assertContains(response, self.url)
        self.login(self.ryan)
        self.assertNotContains(self.client.get(reverse("task-drawer", args=[self.task.pk])), self.url)

    def test_concluded_tab_of_the_task_list_has_the_menu_item(self):
        self.login(self.manager)
        response = self.client.get(reverse("task-list"), {"status": "concluidas"})
        self.assertContains(response, self.url)
        self.login(self.ryan)
        self.assertNotContains(self.client.get(reverse("task-list"), {"status": "concluidas"}), self.url)

    # -- popup ----------------------------------------------------------------

    def test_popup_needs_the_permission(self):
        self.login(self.ryan)
        self.assertEqual(self.client.get(self.url, **AJAX).status_code, 403)
        self.assertEqual(self.client.post(self.url, {"reason": "x"}, **AJAX).status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CONCLUIDA)

    def test_popup_explains_and_asks_for_the_reason(self):
        self.login(self.manager)
        response = self.client.get(self.url, **AJAX)
        self.assertContains(response, "Reabrir tarefa")
        self.assertContains(response, "volta ao fim da fila")
        self.assertContains(response, 'name="reason"')

    def test_ajax_post_reopens_and_answers_json(self):
        self.login(self.manager)
        response = self.client.post(self.url, {"reason": "Falta o anexo"}, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["redirect_url"], self.detail)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_FILA)

    def test_post_without_javascript_redirects_to_the_task(self):
        self.login(self.manager)
        response = self.client.post(self.url, {"reason": "Falta o anexo"})
        self.assertRedirects(response, self.detail)

    def test_missing_reason_is_reported_on_the_field(self):
        self.login(self.manager)
        response = self.client.post(self.url, {"reason": ""}, **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("reason", json.loads(response.content)["errors"])

    def test_business_refusal_comes_back_as_a_form_error(self):
        open_task = self.queued_task("Ainda aberta", responsavel=self.manager)
        self.login(self.manager)
        response = self.client.post(reverse("task-reopen", args=[open_task.pk]), {"reason": "x"}, **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Somente tarefas concluídas", json.dumps(json.loads(response.content)["errors"], ensure_ascii=False))

    def test_other_tenant_gets_404(self):
        foreign = make_user("gestor_alheio", self.other_org, [catalog.TAREFA_REABRIR])
        self.login(foreign)
        self.assertEqual(self.client.get(self.url, **AJAX).status_code, 404)

    # -- atividade ------------------------------------------------------------

    def concluded_activity(self):
        ActivityService.finalize(
            self.activity, self.owner, Activity.CompletionOutcome.CONCLUIDO_COM_PENDENCIAS, "Encerrada"
        )
        return reverse("activity-detail", args=[self.activity.pk])

    def test_concluded_activity_shows_the_button_in_summary_actions(self):
        detail = self.concluded_activity()
        reopen_url = reverse("activity-reopen", args=[self.activity.pk])
        self.login(self.owner)
        response = self.client.get(detail)
        self.assertTrue(response.context["can_reopen"])
        html = response.content.decode()
        actions = html[html.index("Ações da demanda") : html.index("Ações da demanda") + 1200]
        self.assertIn(reopen_url, actions)
        self.assertIn("Reabrir demanda", actions)
        notice = html[html.index("Concluída em") : html.index("Concluída em") + 240]
        self.assertNotIn(reopen_url, notice)

    def test_button_is_hidden_from_those_without_atividade_reabrir(self):
        detail = self.concluded_activity()
        self.login(self.manager)  # só tarefa.reabrir
        response = self.client.get(detail)
        self.assertFalse(response.context["can_reopen"])
        self.assertNotContains(response, reverse("activity-reopen", args=[self.activity.pk]))

    def test_cancelled_activity_shows_no_reopen_at_all(self):
        Activity.objects.filter(pk=self.activity.pk).update(
            status=Activity.Status.CANCELADA, cancelled_reason="Desistiu"
        )
        self.login(self.owner)
        response = self.client.get(reverse("activity-detail", args=[self.activity.pk]))
        self.assertFalse(response.context["can_reopen"])
        self.assertFalse(response.context["is_menu_active"])
        self.assertNotContains(response, reverse("activity-reopen", args=[self.activity.pk]))

    def test_activity_list_offers_it_for_concluded_activities_only(self):
        self.concluded_activity()
        reopen_url = reverse("activity-reopen", args=[self.activity.pk])
        self.login(self.owner)
        self.assertContains(self.client.get(reverse("activity-list"), {"tab": "concluidas"}), reopen_url)
        self.login(self.manager)
        # o gestor nem vê a atividade como dono; e sem a permissão o item não existe
        self.assertNotContains(self.client.get(reverse("activity-list"), {"tab": "concluidas"}), reopen_url)

    def test_activity_reopen_popup_still_works_from_the_button(self):
        detail = self.concluded_activity()
        self.login(self.owner)
        response = self.client.post(reverse("activity-reopen", args=[self.activity.pk]), {"reason": "Voltou"}, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.EM_ANDAMENTO)
        self.assertNotContains(self.client.get(detail), "Concluída em")
