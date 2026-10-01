"""Editor da tarefa, “Gerenciar dependência”, motivo no tempo manual, origem
do tempo na gestão e as ações da tarefa em janela.

O editor salva dados, prazo pedido, marcadores, responsável e participantes
numa transação só; adicionar *outra* pessoa como participante cria um convite
(“aguardando aceite”), nunca um participante efetivo.
"""

import datetime
import json

from django.urls import get_resolver, reverse
from django.utils import timezone

from acessos import catalog
from acessos.context_processors import _NAV_BY_URL_NAME
from acessos.testing import grant_action, grant_actions
from audit.models import AuditLog
from core.models import Tag
from notifications.models import Notification

from .models import Task, TaskAssignment, TaskExecutor, WorkSession
from .services import ActivityError, QueueService, TaskService, WorkTimeService
from .testing import WORKER_ACTIONS, ProcessTestCase, make_user

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
Reason = WorkSession.ManualReason

MANAGER_ACTIONS = [
    catalog.TAREFA_EDITAR,
    catalog.TAREFA_ALTERAR_RESPONSAVEL,
    catalog.TAREFA_ATRIBUIR,
    catalog.TAREFA_ASSUMIR,
    catalog.TAREFA_DEVOLVER,
    catalog.TAREFA_MOVER_SETOR,
    catalog.TAREFA_BLOQUEAR,
    catalog.TAREFA_CANCELAR,
    catalog.PRAZO_PROPOR,
    catalog.TEMPO_LANCAR_MANUAL,
    catalog.TAREFA_CONCLUIR,
    catalog.TAREFA_INICIAR,
]


class EditorTestCase(ProcessTestCase):
    def setUp(self):
        super().setUp()
        self.manager = make_user("gestor", self.org, MANAGER_ACTIONS)
        self.editor_only = make_user("so_editor", self.org, [catalog.TAREFA_EDITAR])
        self.urgente = Tag.objects.create(organization=self.org, name="Urgente")
        self.obra = Tag.objects.create(organization=self.org, name="Obra")
        self.task = self.queued_task("Entrevista com Jovem Aprendizes")

    def queued_task(self, title, responsavel=None, sector=None, depends_on=None, status=None, activity=None):
        task = Task.objects.create(
            activity=activity or self.activity,
            sector=sector or self.comercial,
            title=title,
            created_by=self.owner,
            responsavel=responsavel or self.ryan,
            status=Task.Status.DISPONIVEL,
            depends_on=depends_on,
        )
        if depends_on is None:
            QueueService.enqueue(task, task.sector, user=self.owner)
        if status:
            Task.objects.filter(pk=task.pk).update(status=status)
        task.refresh_from_db()
        return task

    def edit(self, user=None, task=None, **overrides):
        data = dict(
            title="Entrevista com Jovem Aprendizes",
            description="",
            requested_deadline=None,
            tags=[],
        )
        data.update(overrides)
        return TaskService.edit_task(task or self.task, user or self.manager, **data)

    def audits(self, field, task=None):
        return AuditLog.objects.filter(
            task=task or self.task, action=AuditLog.Action.UPDATE, field_name=field
        ).order_by("pk")


# ---------------------------------------------------------------------------
# Editor: serviço
# ---------------------------------------------------------------------------


class EditTaskServiceTests(EditorTestCase):
    def test_saves_data_deadline_and_tags_and_audits_each_change(self):
        deadline = timezone.now() + datetime.timedelta(days=5)
        self.edit(
            title="Entrevistar jovens aprendizes",
            description="<p>Conduzir as entrevistas.</p>",
            requested_deadline=deadline,
            tags=[self.urgente, self.obra],
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Entrevistar jovens aprendizes")
        self.assertEqual(self.task.description, "<p>Conduzir as entrevistas.</p>")
        self.assertEqual(self.task.requested_deadline, deadline)
        self.assertEqual({tag.name for tag in self.task.tags.all()}, {"Urgente", "Obra"})
        for field in ("title", "description", "requested_deadline", "tags"):
            self.assertEqual(self.audits(field).count(), 1, msg=field)

    def test_nothing_changed_writes_nothing(self):
        self.edit()
        self.assertFalse(AuditLog.objects.filter(task=self.task, action=AuditLog.Action.UPDATE).exists())

    def test_tag_changes_are_audited_with_before_and_after(self):
        self.edit(tags=[self.urgente])
        self.edit(tags=[self.obra, self.urgente])
        self.edit(tags=[self.obra, self.urgente])  # sem mudança: não audita
        self.edit(tags=[])
        entries = list(self.audits("tags"))
        self.assertEqual([(e.old_value, e.new_value) for e in entries], [
            ("Nenhum", "Urgente"),
            ("Urgente", "Obra, Urgente"),
            ("Obra, Urgente", "Nenhum"),
        ])

    def test_tags_are_audited_on_the_plain_update_path_too(self):
        TaskService.update_task(self.task, self.manager, tags=[self.obra])
        self.assertEqual(self.audits("tags").get().new_value, "Obra")

    def test_empty_title_is_refused_and_nothing_is_saved(self):
        with self.assertRaisesMessage(ActivityError, "título"):
            self.edit(title="", description="<p>x</p>", tags=[self.urgente])
        self.task.refresh_from_db()
        self.assertEqual(self.task.description, "")
        self.assertFalse(self.task.tags.exists())

    def test_responsavel_is_changed_with_permission_and_leaves_the_participants(self):
        TaskExecutor.objects.create(task=self.task, user=self.paulo, added_by=self.owner)
        self.edit(responsavel=self.paulo, participants=[self.paulo, self.vitor])
        self.task.refresh_from_db()
        self.assertEqual(self.task.responsavel, self.paulo)
        active = set(self.task.executors.filter(removed_at__isnull=True).values_list("user__username", flat=True))
        self.assertNotIn("paulo", active)  # o novo responsável sai de Participantes
        self.assertTrue(AuditLog.objects.filter(task=self.task, action=AuditLog.Action.RESPONSAVEL_CHANGED).exists())
        self.assertTrue(Notification.objects.filter(task=self.task, event_type=Notification.EventType.TASK_RESPONSAVEL_CHANGED).exists())

    def test_responsavel_needs_its_own_permission_and_everything_rolls_back(self):
        with self.assertRaises(ActivityError):
            self.edit(user=self.editor_only, title="Novo título", tags=[self.urgente], responsavel=self.paulo)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Entrevista com Jovem Aprendizes")
        self.assertEqual(self.task.responsavel, self.ryan)
        self.assertFalse(self.task.tags.exists())
        self.assertFalse(AuditLog.objects.filter(task=self.task, action=AuditLog.Action.UPDATE).exists())

    def test_inviting_someone_else_creates_a_pending_invite_not_a_participant(self):
        result = self.edit(participants=[self.vitor])
        self.assertEqual(result["invited"], [self.vitor])
        self.assertEqual(result["added"], [])
        self.assertFalse(TaskExecutor.objects.filter(task=self.task, user=self.vitor).exists())
        invite = TaskAssignment.objects.get(task=self.task, user=self.vitor)
        self.assertEqual(invite.status, TaskAssignment.Status.PENDENTE)
        self.assertEqual(invite.assigned_by, self.manager)
        self.assertTrue(AuditLog.objects.filter(task=self.task, action=AuditLog.Action.ASSIGNMENT_CREATED).exists())
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.vitor, event_type=Notification.EventType.TASK_ASSIGNMENT_PENDING
            ).exists()
        )

    def test_adding_yourself_is_immediate(self):
        result = self.edit(participants=[self.manager])
        self.assertEqual(result["added"], [self.manager])
        self.assertEqual(result["invited"], [])
        self.assertTrue(TaskExecutor.objects.filter(task=self.task, user=self.manager, removed_at__isnull=True).exists())

    def test_choosing_someone_who_already_has_an_invite_does_not_duplicate_it(self):
        self.edit(participants=[self.vitor])
        result = self.edit(participants=[self.vitor])
        self.assertEqual(result["invited"], [])
        self.assertEqual(TaskAssignment.objects.filter(task=self.task, user=self.vitor).count(), 1)

    def test_unselecting_a_participant_removes_them(self):
        TaskExecutor.objects.create(task=self.task, user=self.vitor, added_by=self.owner)
        result = self.edit(participants=[])
        self.assertEqual(result["removed"], [self.vitor])
        self.assertFalse(TaskExecutor.objects.filter(task=self.task, user=self.vitor, removed_at__isnull=True).exists())
        self.assertTrue(AuditLog.objects.filter(task=self.task, action=AuditLog.Action.EXECUTOR_REMOVED).exists())

    def test_none_leaves_responsavel_and_participants_alone(self):
        TaskExecutor.objects.create(task=self.task, user=self.vitor, added_by=self.owner)
        self.edit(title="Só o título mudou", responsavel=None, participants=None)
        self.task.refresh_from_db()
        self.assertEqual(self.task.responsavel, self.ryan)
        self.assertTrue(TaskExecutor.objects.filter(task=self.task, user=self.vitor, removed_at__isnull=True).exists())

    def test_participants_need_their_own_permission_and_everything_rolls_back(self):
        with self.assertRaises(ActivityError):
            self.edit(user=self.editor_only, title="Novo título", participants=[self.vitor])
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Entrevista com Jovem Aprendizes")
        self.assertFalse(TaskAssignment.objects.filter(task=self.task).exists())

    def test_someone_without_edit_permission_is_refused(self):
        with self.assertRaises(ActivityError):
            self.edit(user=self.stranger, title="Invasão")
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Entrevista com Jovem Aprendizes")

    def test_other_organization_is_refused(self):
        foreign = make_user("gestor_alheio", self.other_org, MANAGER_ACTIONS)
        with self.assertRaises(ActivityError):
            self.edit(user=foreign, title="Invasão")

    def test_concluded_or_cancelled_tasks_cannot_be_edited(self):
        for status in (Task.Status.CONCLUIDA, Task.Status.CANCELADA):
            task = self.queued_task(f"Em {status}", status=status)
            with self.assertRaises(ActivityError, msg=status):
                self.edit(task=task, title="Mudou")


# ---------------------------------------------------------------------------
# Dependência
# ---------------------------------------------------------------------------


class DependencyServiceTests(EditorTestCase):
    def chain(self):
        """t1 ← t2 ← t3 (cada uma depende da anterior)."""
        t1 = self.queued_task("Primeira")
        t2 = self.queued_task("Segunda", depends_on=t1)
        t3 = self.queued_task("Terceira", depends_on=t2)
        return t1, t2, t3

    def test_sets_and_audits_the_dependency_with_titles(self):
        other = self.queued_task("Outra")
        TaskService.change_dependency(self.task, self.manager, other)
        self.task.refresh_from_db()
        self.assertEqual(self.task.depends_on, other)
        entry = self.audits("depends_on").get()
        self.assertEqual((entry.old_value, entry.new_value), ("Nenhuma", "Outra"))

    def test_requires_the_edit_permission(self):
        other = self.queued_task("Outra")
        with self.assertRaises(ActivityError):
            TaskService.change_dependency(self.task, self.stranger, other)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.depends_on)

    def test_direct_cycle_is_refused(self):
        t1, t2, _ = self.chain()
        with self.assertRaisesMessage(ActivityError, "ciclo"):
            TaskService.change_dependency(t1, self.manager, t2)
        t1.refresh_from_db()
        self.assertIsNone(t1.depends_on)

    def test_indirect_cycle_is_refused(self):
        t1, _, t3 = self.chain()
        with self.assertRaisesMessage(ActivityError, "ciclo"):
            TaskService.change_dependency(t1, self.manager, t3)

    def test_cycle_is_also_refused_on_the_plain_update_path(self):
        t1, t2, _ = self.chain()
        with self.assertRaisesMessage(ActivityError, "ciclo"):
            TaskService.update_task(t1, self.manager, depends_on=t2)
        t1.refresh_from_db()
        self.assertIsNone(t1.depends_on)

    def test_self_other_activity_and_cancelled_are_refused(self):
        with self.assertRaisesMessage(ActivityError, "dela mesma"):
            TaskService.change_dependency(self.task, self.manager, self.task)
        other_activity = self.new_activity(title="Outra demanda")
        foreign = self.queued_task("De outra demanda", activity=other_activity)
        with self.assertRaisesMessage(ActivityError, "mesma demanda"):
            TaskService.change_dependency(self.task, self.manager, foreign)
        cancelled = self.queued_task("Cancelada", status=Task.Status.CANCELADA)
        with self.assertRaisesMessage(ActivityError, "cancelada"):
            TaskService.change_dependency(self.task, self.manager, cancelled)

    def test_candidates_exclude_itself_its_dependents_and_cancelled_tasks(self):
        t1, t2, t3 = self.chain()
        cancelled = self.queued_task("Cancelada", status=Task.Status.CANCELADA)
        other_activity = self.new_activity(title="Outra demanda")
        foreign = self.queued_task("De outra demanda", activity=other_activity)
        names = set(TaskService.dependency_candidates(t1).values_list("title", flat=True))
        self.assertNotIn("Primeira", names)
        self.assertNotIn("Segunda", names)  # depende de t1
        self.assertNotIn("Terceira", names)  # depende de t1 por t2
        self.assertNotIn(cancelled.title, names)
        self.assertNotIn(foreign.title, names)
        self.assertIn("Entrevista com Jovem Aprendizes", names)
        self.assertEqual(set(TaskService.dependency_candidates(t3).values_list("title", flat=True)) & {"Terceira"}, set())

    def test_a_queued_task_that_starts_to_wait_leaves_the_queue(self):
        predecessor = self.queued_task("Predecessora")
        follower = self.queued_task("Seguidora")
        third = self.queued_task("Terceira da fila")
        # a fila do setor tem ainda a tarefa do setUp na frente
        self.assertEqual(follower.queue_entries.get().position, 3)
        TaskService.change_dependency(follower, self.manager, predecessor)
        follower.refresh_from_db()
        self.assertEqual(follower.status, Task.Status.DISPONIVEL)
        self.assertFalse(follower.queue_entries.filter(left_at__isnull=True).exists())
        self.assertEqual(third.queue_entries.get(left_at__isnull=True).position, 3)  # renumerou
        self.assertTrue(self.audits("status", task=follower).exists())

    def test_a_task_that_already_started_cannot_start_to_wait(self):
        predecessor = self.queued_task("Predecessora")
        TaskService.start(self.task, self.ryan)
        with self.assertRaisesMessage(ActivityError, "já começou"):
            TaskService.change_dependency(self.task, self.manager, predecessor)
        paused = self.queued_task("Pausada")
        TaskService.start(paused, self.ryan)
        TaskService.pause(paused, self.ryan)
        with self.assertRaisesMessage(ActivityError, "já começou"):
            TaskService.change_dependency(paused, self.manager, predecessor)

    def test_a_started_task_can_depend_on_one_already_concluded(self):
        done = self.queued_task("Já concluída")
        TaskService.complete(done, self.ryan)
        TaskService.start(self.task, self.ryan)
        TaskService.change_dependency(self.task, self.manager, done)
        self.task.refresh_from_db()
        self.assertEqual(self.task.depends_on, done)
        self.assertEqual(self.task.status, Task.Status.EM_EXECUCAO)

    def test_removing_the_dependency_releases_the_task_to_the_queue(self):
        predecessor = self.queued_task("Predecessora")
        waiting = self.queued_task("Esperando", depends_on=predecessor)
        self.assertFalse(waiting.queue_entries.exists())
        TaskService.change_dependency(waiting, self.manager, None)
        waiting.refresh_from_db()
        self.assertIsNone(waiting.depends_on)
        self.assertTrue(waiting.queue_entries.filter(left_at__isnull=True).exists())
        self.assertTrue(AuditLog.objects.filter(task=waiting, action=AuditLog.Action.TASK_RELEASED).exists())

    def test_nothing_changes_when_the_dependency_is_the_same(self):
        predecessor = self.queued_task("Predecessora")
        waiting = self.queued_task("Esperando", depends_on=predecessor)
        TaskService.change_dependency(waiting, self.manager, predecessor)
        self.assertFalse(self.audits("depends_on", task=waiting).exists())

    def test_concluded_task_cannot_change_dependency(self):
        done = self.queued_task("Concluída", status=Task.Status.CONCLUIDA)
        with self.assertRaises(ActivityError):
            TaskService.change_dependency(done, self.manager, self.task)


# ---------------------------------------------------------------------------
# Tempo informado: motivo também em “Adicionar tempo trabalhado”
# ---------------------------------------------------------------------------


class ManualTimeReasonTests(EditorTestCase):
    def setUp(self):
        super().setUp()
        grant_actions(self.ryan, [catalog.TEMPO_LANCAR_MANUAL], organization=self.org)
        now = timezone.now()
        self.started = now - datetime.timedelta(hours=3)
        self.ended = now - datetime.timedelta(hours=2)

    def log(self, reason="", note="", started=None, ended=None):
        return TaskService.log_manual_time(
            self.task, self.ryan, started or self.started, ended or self.ended, logged_by=self.ryan,
            reason=reason, note=note,
        )

    def test_reason_and_comment_are_stored_with_when_it_was_informed(self):
        session = self.log(reason=Reason.FORA_DA_LPS, note="No cliente")
        self.assertEqual((session.manual_reason, session.note), (Reason.FORA_DA_LPS, "No cliente"))
        self.assertIsNotNone(session.logged_at)
        entry = AuditLog.objects.filter(task=self.task, action=AuditLog.Action.SESSION_STARTED).latest("pk")
        self.assertIn("Trabalhei fora da LPS", entry.reason)
        self.assertIn("No cliente", entry.reason)

    def test_it_does_not_conclude_the_task(self):
        self.log(reason=Reason.ESQUECI_INICIAR)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_FILA)

    def test_other_needs_a_comment(self):
        with self.assertRaisesMessage(ActivityError, "comentário"):
            self.log(reason=Reason.OUTRO)
        self.assertFalse(WorkSession.objects.filter(task=self.task).exists())
        self.log(reason=Reason.OUTRO, note="Reunião externa")

    def test_old_work_needs_a_justification(self):
        started = timezone.now() - datetime.timedelta(days=10)
        with self.assertRaisesMessage(ActivityError, "justificativa"):
            self.log(reason=Reason.AJUSTE_PERIODO, started=started, ended=started + datetime.timedelta(hours=1))
        self.log(
            reason=Reason.AJUSTE_PERIODO, note="Esquecido na virada do mês",
            started=started, ended=started + datetime.timedelta(hours=1),
        )

    def test_invalid_reason_is_refused(self):
        with self.assertRaisesMessage(ActivityError, "motivo"):
            self.log(reason="INVENTADO")

    def test_without_a_reason_the_old_behavior_is_kept(self):
        session = self.log()
        self.assertEqual((session.manual_reason, session.note), ("", ""))
        self.assertTrue(session.is_manual)

    def test_the_form_asks_for_the_reason(self):
        self.client.force_login(self.ryan)
        url = reverse("task-manual-time", args=[self.task.pk])
        response = self.client.get(url, **AJAX)
        self.assertContains(response, 'name="reason"')
        self.assertContains(response, "Esqueci de iniciar")
        self.assertContains(response, 'name="note"')
        payload = {
            "started_at": self.started.astimezone().strftime("%Y-%m-%dT%H:%M"),
            "ended_at": self.ended.astimezone().strftime("%Y-%m-%dT%H:%M"),
        }
        missing = self.client.post(url, payload, **AJAX)
        self.assertEqual(missing.status_code, 400)
        self.assertIn("reason", json.loads(missing.content)["errors"])
        ok = self.client.post(url, {**payload, "reason": Reason.FORA_DA_LPS, "note": "No cliente"}, **AJAX)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(WorkSession.objects.get(task=self.task).manual_reason, Reason.FORA_DA_LPS)


# ---------------------------------------------------------------------------
# Origem do tempo na gestão
# ---------------------------------------------------------------------------


class WorkTimeOriginTests(EditorTestCase):
    def sessions(self):
        base = timezone.now() - datetime.timedelta(days=1)

        def make(task, hours, **extra):
            return WorkSession.objects.create(
                task=task, user=self.ryan, started_at=base, ended_at=base + datetime.timedelta(hours=hours), **extra
            )

        make(self.task, 6)  # cronômetro
        make(self.task, 2, is_manual=True, logged_at=timezone.now(), manual_reason=Reason.ESQUECI_INICIAR)
        make(self.task, 1, is_manual=True, logged_at=timezone.now(), manual_reason=Reason.FORA_DA_LPS)
        make(self.task, 1, is_manual=True)  # anterior ao motivo existir
        WorkSession.objects.create(task=self.task, user=self.ryan, started_at=base)  # aberta: não conta

    def test_breakdown_splits_timer_informed_and_reasons(self):
        self.sessions()
        result = WorkTimeService.origin_breakdown(type(self.activity).objects.filter(pk=self.activity.pk))
        self.assertEqual(result["timer"], datetime.timedelta(hours=6))
        self.assertEqual(result["informed"], datetime.timedelta(hours=4))
        self.assertEqual(result["total"], datetime.timedelta(hours=10))
        self.assertEqual((result["timer_pct"], result["informed_pct"]), (60.0, 40.0))
        labels = [(row["label"], row["total"], row["pct_of_informed"]) for row in result["reasons"]]
        self.assertEqual(labels[0], ("Esqueci de iniciar", datetime.timedelta(hours=2), 50.0))
        self.assertEqual({label for label, _, _ in labels}, {
            "Esqueci de iniciar", "Trabalhei fora da LPS", "Sem motivo (registrado antes de o motivo existir)",
        })

    def test_no_time_means_no_percentages(self):
        result = WorkTimeService.origin_breakdown(type(self.activity).objects.filter(pk=self.activity.pk))
        self.assertEqual(result["total"], datetime.timedelta(0))
        self.assertIsNone(result["informed_pct"])
        self.assertEqual(result["reasons"], [])

    def test_only_the_filtered_activities_count(self):
        self.sessions()
        other = self.new_activity(title="Outra demanda")
        result = WorkTimeService.origin_breakdown(type(self.activity).objects.filter(pk=other.pk))
        self.assertEqual(result["total"], datetime.timedelta(0))

    def test_management_shows_the_card_to_who_sees_metrics(self):
        self.sessions()
        viewer = make_user("diretor", self.org, [catalog.METRICAS_VISUALIZAR])
        self.client.force_login(viewer)
        response = self.client.get(reverse("management"))
        self.assertContains(response, "Origem do tempo registrado")
        self.assertContains(response, "Esqueci de iniciar")
        self.assertEqual(response.context["dash_time_origin"]["informed_pct"], 40.0)

    def test_management_says_so_when_there_is_no_time(self):
        viewer = make_user("diretor", self.org, [catalog.METRICAS_VISUALIZAR])
        self.client.force_login(viewer)
        self.assertContains(self.client.get(reverse("management")), "Ainda não há tempo registrado")


# ---------------------------------------------------------------------------
# Telas
# ---------------------------------------------------------------------------


class EditorViewTestCase(EditorTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("task-edit", args=[self.task.pk])
        self.detail = reverse("task-detail", args=[self.task.pk])

    def login(self, user):
        self.client.force_login(user)

    def payload(self, **overrides):
        data = {
            "title": "Entrevistar jovens aprendizes",
            "description": "<p>Conduzir as entrevistas.</p>",
            "requested_deadline_0": "2026-12-15",
            "requested_deadline_1": "10:00",
            "tags": [self.urgente.pk],
            "responsavel": self.ryan.pk,
            "participantes": [],
        }
        data.update(overrides)
        return data


class EditorPopupTests(EditorViewTestCase):
    def test_opening_needs_the_edit_permission_already_on_get(self):
        self.login(self.stranger)
        self.assertEqual(self.client.get(self.url, **AJAX).status_code, 403)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.payload(), **AJAX).status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Entrevista com Jovem Aprendizes")

    def test_other_organization_gets_404(self):
        self.login(make_user("gestor_alheio", self.other_org, MANAGER_ACTIONS))
        self.assertEqual(self.client.get(self.url, **AJAX).status_code, 404)

    def test_popup_has_the_editable_fields(self):
        self.login(self.manager)
        response = self.client.get(self.url, **AJAX)
        for name in ("title", "description", "requested_deadline_0", "requested_deadline_1", "tags", "responsavel", "participantes"):
            self.assertContains(response, f'name="{name}"')
        self.assertContains(response, "Data do prazo")
        self.assertContains(response, "Hora do prazo")
        self.assertContains(response, "Salvar alterações")

    def test_sector_and_dependency_are_not_editable_here(self):
        self.login(self.manager)
        response = self.client.get(self.url, **AJAX)
        self.assertNotContains(response, 'name="sector"')
        self.assertNotContains(response, 'name="depends_on"')
        self.assertContains(response, "Enviar para outro setor")  # só o texto apontando o caminho
        self.assertContains(response, self.task.sector.name)

    def test_committed_deadline_is_shown_but_not_editable(self):
        Task.objects.filter(pk=self.task.pk).update(committed_deadline=timezone.now() + datetime.timedelta(days=3))
        self.login(self.manager)
        response = self.client.get(self.url, **AJAX)
        self.assertContains(response, "Prazo que a equipe se comprometeu a cumprir")
        self.assertContains(response, "Propor novo prazo")
        self.assertNotContains(response, 'name="committed_deadline"')
        self.assertNotIn("committed_deadline", response.context["form"].fields)

    def test_fields_the_person_cannot_change_become_plain_information(self):
        self.login(self.editor_only)
        response = self.client.get(self.url, **AJAX)
        self.assertNotContains(response, 'name="responsavel"')
        self.assertNotContains(response, 'name="participantes"')
        self.assertContains(response, "Você não tem permissão para trocar o responsável.")
        self.assertContains(response, "Você não tem permissão para incluir ou remover participantes.")
        self.assertContains(response, 'name="title"')

    def test_current_values_come_filled(self):
        TaskExecutor.objects.create(task=self.task, user=self.vitor, added_by=self.owner)
        self.task.tags.set([self.obra])
        self.login(self.manager)
        form = self.client.get(self.url, **AJAX).context["form"]
        self.assertEqual(form["title"].value(), "Entrevista com Jovem Aprendizes")
        self.assertEqual(form["responsavel"].value(), self.ryan.pk)
        self.assertEqual(list(form["participantes"].value()), [self.vitor.pk])
        self.assertEqual(list(form["tags"].value()), [self.obra.pk])

    def test_pending_invites_are_shown_as_waiting_for_acceptance(self):
        TaskService.add_executor(self.task, self.vitor, added_by=self.manager)
        self.login(self.manager)
        response = self.client.get(self.url, **AJAX)
        self.assertContains(response, "aguardando aceite")
        self.assertContains(response, "vitor")
        self.assertNotIn(self.vitor, response.context["current_participants"])
        form = response.context["form"]
        self.assertNotIn(self.vitor.pk, list(form["participantes"].value()))  # o convite não é participante

    def test_ajax_post_saves_everything_and_answers_json(self):
        self.login(self.manager)
        response = self.client.post(self.url, self.payload(), **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["redirect_url"], self.detail)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Entrevistar jovens aprendizes")
        self.assertEqual(self.task.requested_deadline.date(), datetime.date(2026, 12, 15))
        self.assertEqual(list(self.task.tags.all()), [self.urgente])

    def test_post_without_javascript_redirects_and_says_who_was_invited(self):
        self.login(self.manager)
        response = self.client.post(self.url, self.payload(participantes=[self.vitor.pk]), follow=True)
        self.assertRedirects(response, self.detail)
        self.assertContains(response, "Convite enviado a vitor")
        self.assertTrue(TaskAssignment.objects.filter(task=self.task, user=self.vitor).exists())

    def test_empty_title_is_reported_on_the_field(self):
        self.login(self.manager)
        response = self.client.post(self.url, self.payload(title=""), **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", json.loads(response.content)["errors"])

    def test_service_refusal_is_reported_without_saving_anything(self):
        self.login(self.manager)
        Task.objects.filter(pk=self.task.pk).update(status=Task.Status.CONCLUIDA)
        response = self.client.post(self.url, self.payload(), **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("concluída", json.dumps(json.loads(response.content)["errors"], ensure_ascii=False))
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Entrevista com Jovem Aprendizes")

    def test_a_person_from_another_organization_cannot_be_chosen(self):
        self.login(self.manager)
        response = self.client.post(self.url, self.payload(responsavel=self.foreign.pk), **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("responsavel", json.loads(response.content)["errors"])

    def test_the_responsavel_cannot_also_be_a_participant(self):
        self.login(self.manager)
        response = self.client.post(self.url, self.payload(participantes=[self.ryan.pk]), **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TaskExecutor.objects.filter(task=self.task, user=self.ryan).exists())
        self.assertFalse(TaskAssignment.objects.filter(task=self.task, user=self.ryan).exists())

    def test_the_posted_responsavel_is_ignored_without_permission(self):
        self.login(self.editor_only)
        response = self.client.post(self.url, self.payload(responsavel=self.paulo.pk, title="Só o título"), **AJAX)
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.responsavel, self.ryan)
        self.assertEqual(self.task.title, "Só o título")

    def test_page_without_javascript_is_a_complete_page(self):
        self.login(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")
        self.assertEqual(response.context["nav_active"], "tasks")


class DetailPageTests(EditorViewTestCase):
    def test_pending_invites_show_in_the_participants_card(self):
        TaskService.add_executor(self.task, self.vitor, added_by=self.manager)
        TaskExecutor.objects.create(task=self.task, user=self.paulo, added_by=self.owner)
        self.login(self.manager)
        response = self.client.get(self.detail)
        self.assertContains(response, "aguardando aceite")
        self.assertEqual([invite.user for invite in response.context["pending_assignments"]], [self.vitor])
        self.assertEqual([link.user for link in response.context["executors"]], [self.paulo])

    def test_empty_participants_message_only_without_invites_either(self):
        self.login(self.manager)
        self.assertContains(self.client.get(self.detail), "Ainda não há participantes adicionais.")
        TaskService.add_executor(self.task, self.vitor, added_by=self.manager)
        self.assertNotContains(self.client.get(self.detail), "Ainda não há participantes adicionais.")

    def test_manage_dependency_is_offered_to_editors_of_open_tasks_only(self):
        url = reverse("task-dependency", args=[self.task.pk])
        self.login(self.manager)
        self.assertContains(self.client.get(self.detail), f'href="{url}" data-activity-action')
        self.login(self.stranger)
        self.assertNotContains(self.client.get(self.detail), url)
        TaskService.complete(self.task, self.ryan)
        self.login(self.manager)
        response = self.client.get(self.detail)
        self.assertNotContains(response, url)
        self.assertFalse(response.context["can_manage_dependency"])

    def test_deadlines_are_named_clearly(self):
        self.login(self.manager)
        response = self.client.get(self.detail)
        self.assertContains(response, "Prazo pedido pelo solicitante")
        self.assertContains(response, "Prazo que a equipe se comprometeu a cumprir")


class DependencyPopupTests(EditorViewTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("task-dependency", args=[self.task.pk])
        self.predecessor = self.queued_task("Predecessora")

    def test_needs_the_edit_permission(self):
        self.login(self.stranger)
        self.assertEqual(self.client.get(self.url, **AJAX).status_code, 403)
        self.assertEqual(self.client.post(self.url, {"depends_on": self.predecessor.pk}, **AJAX).status_code, 403)

    def test_popup_only_offers_valid_predecessors(self):
        dependent = self.queued_task("Dependente", depends_on=self.task)
        self.login(self.manager)
        response = self.client.get(self.url, **AJAX)
        offered = set(response.context["form"].fields["depends_on"].queryset.values_list("title", flat=True))
        self.assertIn("Predecessora", offered)
        self.assertNotIn(self.task.title, offered)
        self.assertNotIn(dependent.title, offered)
        self.assertContains(response, "Nenhuma")
        self.assertContains(response, "aguardando a etapa anterior")

    def test_ajax_post_sets_the_dependency(self):
        self.login(self.manager)
        response = self.client.post(self.url, {"depends_on": self.predecessor.pk}, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.depends_on, self.predecessor)
        self.assertEqual(self.task.status, Task.Status.DISPONIVEL)  # passou a aguardar

    def test_empty_choice_removes_it(self):
        TaskService.change_dependency(self.task, self.manager, self.predecessor)
        self.login(self.manager)
        form = self.client.get(self.url, **AJAX).context["form"]
        self.assertEqual(form["depends_on"].value(), self.predecessor.pk)
        self.assertEqual(self.client.post(self.url, {"depends_on": ""}, **AJAX).status_code, 200)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.depends_on)

    def test_a_cycle_cannot_be_chosen(self):
        dependent = self.queued_task("Dependente", depends_on=self.task)
        self.login(self.manager)
        response = self.client.post(self.url, {"depends_on": dependent.pk}, **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("depends_on", json.loads(response.content)["errors"])  # fora das opções válidas
        self.task.refresh_from_db()
        self.assertIsNone(self.task.depends_on)

    def test_service_refusal_comes_back_as_a_form_error(self):
        TaskService.start(self.task, self.ryan)
        self.login(self.manager)
        response = self.client.post(self.url, {"depends_on": self.predecessor.pk}, **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("já começou", json.dumps(json.loads(response.content)["errors"], ensure_ascii=False))


class ActionWindowsTests(EditorViewTestCase):
    """Todas as ações da tarefa respondem JSON quando abertas em janela."""

    def setUp(self):
        super().setUp()
        self.login(self.manager)

    def test_block_answers_json(self):
        response = self.client.post(reverse("task-block", args=[self.task.pk]), {"reason": "Falta o contato"}, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["redirect_url"], self.detail)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.BLOQUEADA)

    def test_block_without_reason_is_a_field_error(self):
        response = self.client.post(reverse("task-block", args=[self.task.pk]), {"reason": ""}, **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("reason", json.loads(response.content)["errors"])

    def test_cancel_answers_json(self):
        response = self.client.post(reverse("task-cancel", args=[self.task.pk]), {"reason": "Não é mais preciso"}, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.CANCELADA)

    def test_move_and_return_answer_json(self):
        move = self.client.post(reverse("task-move", args=[self.task.pk]), {"to_sector": self.compras.pk, "note": "Segue"}, **AJAX)
        self.assertEqual(move.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.sector, self.compras)
        bad = self.client.post(reverse("task-return", args=[self.task.pk]), {}, **AJAX)
        self.assertEqual(bad.status_code, 400)
        self.assertIn("to_sector", json.loads(bad.content)["errors"])

    def test_propose_deadline_answers_json(self):
        when = (timezone.now() + datetime.timedelta(days=4)).astimezone().strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(reverse("deadline-propose", args=[self.task.pk]), {"proposed_deadline": when}, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["redirect_url"], self.detail)

    def test_service_errors_come_back_as_400_not_as_a_page(self):
        Task.objects.filter(pk=self.task.pk).update(status=Task.Status.CANCELADA)
        response = self.client.post(reverse("task-block", args=[self.task.pk]), {"reason": "x"}, **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertIn("__all__", json.loads(response.content)["errors"])

    def test_a_closed_task_cannot_be_blocked(self):
        for status in (Task.Status.CONCLUIDA, Task.Status.CANCELADA):
            task = self.queued_task(f"Em {status}", status=status)
            with self.assertRaisesMessage(ActivityError, "concluída ou cancelada"):
                TaskService.block(task, self.manager, "Tentativa")
            task.refresh_from_db()
            self.assertEqual(task.status, status)
            self.assertFalse(task.blocks.exists())

    def test_without_javascript_they_still_redirect(self):
        response = self.client.post(reverse("task-block", args=[self.task.pk]), {"reason": "Falta o contato"})
        self.assertRedirects(response, self.detail)

    def test_the_old_link_of_the_comment_footer_respects_the_permission(self):
        self.login(self.stranger)
        self.assertNotContains(self.client.get(self.detail), reverse("deadline-propose", args=[self.task.pk]))


class SideMenuTests(EditorTestCase):
    # Endpoints que só respondem POST/JSON/fragmento: não têm página para destacar.
    NOT_PAGES = {
        "task-move-stage", "task-assume", "task-start", "task-pause", "task-resume", "task-complete",
        "task-unblock", "task-executor-add", "task-executor-remove", "task-assignment-accept", "task-message",
        "task-drawer", "task-start-ajax", "task-pause-ajax", "task-complete-ajax", "task-checklist-add",
        "task-checklist-toggle", "task-checklist-remove",
    }

    def test_every_task_page_keeps_its_menu_item_highlighted(self):
        names = set()

        def walk(patterns):
            for pattern in patterns:
                if hasattr(pattern, "url_patterns"):
                    walk(pattern.url_patterns)
                elif pattern.name:
                    names.add(pattern.name)

        walk(get_resolver().url_patterns)
        task_pages = {
            name for name in names
            if (name.startswith("task-") or name.startswith("deadline-propose")) and name not in self.NOT_PAGES
        }
        missing = sorted(task_pages - set(_NAV_BY_URL_NAME))
        self.assertEqual(missing, [], "rota de tarefa sem destaque no menu lateral")

    def test_action_page_highlights_tasks(self):
        self.client.force_login(self.owner)
        grant_action(self.owner, catalog.TAREFA_EDITAR, organization=self.org)
        task = self.queued_task("Qualquer", responsavel=self.owner)
        for name in ("task-dependency", "task-return", "task-block", "task-cancel"):
            grant_actions(
                self.owner,
                [catalog.TAREFA_EDITAR, catalog.TAREFA_DEVOLVER, catalog.TAREFA_BLOQUEAR, catalog.TAREFA_CANCELAR],
                organization=self.org,
            )
            response = self.client.get(reverse(name, args=[task.pk]))
            self.assertEqual(response.context["nav_active"], "tasks", msg=name)
