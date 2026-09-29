from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from acessos import catalog
from acessos.testing import grant_action, grant_actions
from audit.models import AuditLog
from core.models import Organization, Sector
from notifications.models import Notification

from .models import (
    Activity,
    DeadlineConflict,
    DeadlineProposal,
    QueueEntry,
    QueuePositionChange,
    ReturnReason,
    Task,
    TaskAssignment,
    TaskExecutor,
    WorkSession,
)
from .services import (
    ActivityError,
    ActivityService,
    DeadlineService,
    MessageService,
    QueueService,
    TaskService,
    find_mentioned_users,
)

User = get_user_model()


# Tudo é negado por padrão: cada teste concede explicitamente o que precisa,
# deixando visível qual ação e qual escopo estão sendo exercidos.
OPERATOR_ACTIONS = [
    catalog.ATIVIDADE_CRIAR,
    catalog.ATIVIDADE_EDITAR,
    catalog.ATIVIDADE_CONCLUIR,
    catalog.TAREFA_CRIAR,
    catalog.TAREFA_EDITAR,
    catalog.TAREFA_ASSUMIR,
    catalog.TAREFA_ATRIBUIR,
    catalog.TAREFA_ACEITAR,
    catalog.TAREFA_RECUSAR,
    catalog.TAREFA_INICIAR,
    catalog.TAREFA_PAUSAR,
    catalog.TAREFA_RETOMAR,
    catalog.TAREFA_CONCLUIR,
    catalog.TAREFA_CANCELAR,
    catalog.TAREFA_DEVOLVER,
    catalog.TAREFA_BLOQUEAR,
    catalog.TAREFA_MOVER_SETOR,
    catalog.TEMPO_LANCAR_MANUAL,
    catalog.PRAZO_PROPOR,
    catalog.PRAZO_ACEITAR,
    catalog.PRAZO_RECUSAR,
    catalog.COMUNICACAO_PARTICIPAR,
]


class ActivitiesTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Outra Empresa")
        self.sector = Sector.objects.create(organization=self.org, name="Compras")
        self.other_sector = Sector.objects.create(organization=self.other_org, name="Financeiro")
        self.owner = User.objects.create_user("paulo", password="x")
        self.creator = User.objects.create_user("jennifer", password="x")
        self.executor = User.objects.create_user("ryan", password="x")
        self.executor2 = User.objects.create_user("luan", password="x")
        self.gestor = User.objects.create_user("gestor", password="x")
        self.reason = ReturnReason.objects.create(organization=self.org, name="Especificação incompleta")

        for user in (self.owner, self.creator, self.executor, self.executor2, self.gestor):
            user.profile.organization = self.org
            user.profile.save(update_fields=["organization"])
            grant_actions(user, OPERATOR_ACTIONS, organization=self.org)


class ActivityOwnershipTests(ActivitiesTestCase):
    def test_activity_always_has_single_owner(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Material disponível na obra", owner=self.owner, created_by=self.creator
        )
        self.assertEqual(activity.owner, self.owner)

    def test_change_owner_requires_permission(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade X", owner=self.owner, created_by=self.creator
        )
        with self.assertRaises(ActivityError):
            ActivityService.change_owner(activity, self.executor, changed_by=self.creator)

    def test_change_owner_is_audited_and_never_leaves_two_owners(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade X", owner=self.owner, created_by=self.creator
        )
        grant_action(self.gestor, catalog.ATIVIDADE_ALTERAR_DONO, organization=self.org)
        ActivityService.change_owner(activity, self.executor, changed_by=self.gestor)
        activity.refresh_from_db()

        self.assertEqual(activity.owner, self.executor)
        self.assertEqual(activity.owner_changes.count(), 1)
        change = activity.owner_changes.first()
        self.assertEqual(change.previous_owner, self.owner)
        self.assertEqual(change.new_owner, self.executor)


class TaskExecutionTests(ActivitiesTestCase):
    def _make_task(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Orçamento", owner=self.owner, created_by=self.creator
        )
        return TaskService.create_task(activity, self.sector, "Levantar quantitativos", created_by=self.creator, responsavel=self.creator)

    def _assign_and_accept(self, task, user, assigned_by):
        assignment = TaskService.add_executor(task, user, added_by=assigned_by)
        TaskService.accept_assignment(assignment, user)

    def test_multiple_executors_track_individual_time(self):
        task = self._make_task()
        self._assign_and_accept(task, self.executor, assigned_by=self.creator)
        self._assign_and_accept(task, self.executor2, assigned_by=self.creator)

        TaskService.start(task, self.executor)
        TaskService.start(task, self.executor2)

        session1 = WorkSession.objects.get(task=task, user=self.executor)
        session2 = WorkSession.objects.get(task=task, user=self.executor2)
        self.assertIsNone(session1.ended_at)
        self.assertIsNone(session2.ended_at)

        # Overlapping sessions must sum as man-hours, not collapse into one.
        now = timezone.now()
        session1.started_at = now - timezone.timedelta(hours=2)
        session1.ended_at = now
        session1.save()
        session2.started_at = now - timezone.timedelta(hours=1)
        session2.ended_at = now
        session2.save()

        total_man_hours = sum((s.duration for s in task.work_sessions.all()), timezone.timedelta())
        self.assertEqual(total_man_hours, timezone.timedelta(hours=3))

    def test_starting_new_task_keeps_previous_session_open(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        task1 = TaskService.create_task(activity, self.sector, "Tarefa 1", created_by=self.creator, responsavel=self.creator)
        task2 = TaskService.create_task(activity, self.sector, "Tarefa 2", created_by=self.creator, responsavel=self.creator)
        self._assign_and_accept(task1, self.executor, assigned_by=self.creator)
        self._assign_and_accept(task2, self.executor, assigned_by=self.creator)

        TaskService.start(task1, self.executor)
        self.assertTrue(WorkSession.objects.filter(task=task1, user=self.executor, ended_at__isnull=True).exists())

        TaskService.start(task2, self.executor)
        self.assertTrue(WorkSession.objects.filter(task=task1, user=self.executor, ended_at__isnull=True).exists())
        self.assertTrue(WorkSession.objects.filter(task=task2, user=self.executor, ended_at__isnull=True).exists())

    def test_only_assigned_executor_can_start_task(self):
        task = self._make_task()
        with self.assertRaises(ActivityError):
            TaskService.start(task, self.executor)

    def test_first_action_recorded_once(self):
        task = self._make_task()
        self._assign_and_accept(task, self.executor, assigned_by=self.creator)
        TaskService.start(task, self.executor)
        task.refresh_from_db()
        first_action = task.first_action_at
        self.assertIsNotNone(first_action)

        TaskService.pause(task, self.executor)
        TaskService.start(task, self.executor)
        task.refresh_from_db()
        self.assertEqual(task.first_action_at, first_action)


class TaskAssignmentTests(ActivitiesTestCase):
    """Atribuir uma tarefa a outra pessoa exige aceite; assumir é imediato (doc 02 — novo)."""

    def _make_task(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Orçamento", owner=self.owner, created_by=self.creator
        )
        return TaskService.create_task(activity, self.sector, "Buscar bomba", created_by=self.creator, responsavel=self.creator)

    def test_assigning_another_person_creates_pending_assignment_not_executor(self):
        task = self._make_task()
        result = TaskService.add_executor(task, self.executor, added_by=self.creator)

        self.assertIsInstance(result, TaskAssignment)
        self.assertEqual(result.status, TaskAssignment.Status.PENDENTE)
        self.assertFalse(TaskExecutor.objects.filter(task=task, user=self.executor).exists())

    def test_self_assignment_is_immediate_and_creates_no_pending_assignment(self):
        task = self._make_task()
        result = TaskService.add_executor(task, self.executor, added_by=self.executor)

        self.assertIsInstance(result, Task)
        self.assertTrue(
            TaskExecutor.objects.filter(task=task, user=self.executor, removed_at__isnull=True).exists()
        )
        self.assertFalse(TaskAssignment.objects.filter(task=task, user=self.executor).exists())

    def test_accepting_turns_assignment_into_executor(self):
        task = self._make_task()
        assignment = TaskService.add_executor(task, self.executor, added_by=self.creator)

        TaskService.accept_assignment(assignment, self.executor)
        assignment.refresh_from_db()

        self.assertEqual(assignment.status, TaskAssignment.Status.ACEITA)
        self.assertTrue(
            TaskExecutor.objects.filter(task=task, user=self.executor, removed_at__isnull=True).exists()
        )

    def test_rejecting_requires_reason_and_creates_no_executor(self):
        task = self._make_task()
        assignment = TaskService.add_executor(task, self.executor, added_by=self.creator)

        with self.assertRaises(ActivityError):
            TaskService.reject_assignment(assignment, self.executor, reason=None)

        TaskService.reject_assignment(assignment, self.executor, reason=self.reason, observation="Não é da minha área")
        assignment.refresh_from_db()

        self.assertEqual(assignment.status, TaskAssignment.Status.RECUSADA)
        self.assertEqual(assignment.reason, self.reason)
        self.assertFalse(TaskExecutor.objects.filter(task=task, user=self.executor).exists())

    def test_only_the_designated_person_can_accept_or_reject(self):
        task = self._make_task()
        assignment = TaskService.add_executor(task, self.executor, added_by=self.creator)

        with self.assertRaises(ActivityError):
            TaskService.accept_assignment(assignment, self.executor2)

        with self.assertRaises(ActivityError):
            TaskService.reject_assignment(assignment, self.executor2, reason=self.reason)

    def test_cannot_decide_an_assignment_twice(self):
        task = self._make_task()
        assignment = TaskService.add_executor(task, self.executor, added_by=self.creator)
        TaskService.accept_assignment(assignment, self.executor)

        with self.assertRaises(ActivityError):
            TaskService.accept_assignment(assignment, self.executor)


class TaskResponsavelTests(ActivitiesTestCase):
    """Responsável é único e obrigatório; Participantes continuam via TaskExecutor (doc — novo)."""

    def _make_task(self, **kwargs):
        activity = ActivityService.create_activity(
            organization=self.org, title="Orçamento", owner=self.owner, created_by=self.creator
        )
        params = {"responsavel": self.creator}
        params.update(kwargs)
        return TaskService.create_task(activity, self.sector, "Levantar quantitativos", created_by=self.creator, **params)

    def test_create_task_requires_responsavel(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Orçamento", owner=self.owner, created_by=self.creator
        )
        with self.assertRaises(ActivityError):
            TaskService.create_task(activity, self.sector, "Sem responsável", created_by=self.creator, responsavel=None)

    def test_create_task_populates_participantes_excluding_responsavel(self):
        # Participantes que não são quem cria a tarefa passam por pedido de
        # aceite (mesma regra de add_executor) — viram pendência, não
        # executor imediato. O responsável nunca aparece nessa lista.
        task = self._make_task(participantes=[self.executor, self.executor2, self.creator])

        self.assertEqual(task.responsavel, self.creator)
        pending_ids = set(
            TaskAssignment.objects.filter(
                task=task, status=TaskAssignment.Status.PENDENTE
            ).values_list("user_id", flat=True)
        )
        self.assertEqual(pending_ids, {self.executor.id, self.executor2.id})
        self.assertFalse(TaskAssignment.objects.filter(task=task, user=self.creator).exists())
        self.assertFalse(TaskExecutor.objects.filter(task=task, user=self.creator).exists())

    def test_add_executor_rejects_the_responsavel_as_participant(self):
        task = self._make_task()
        with self.assertRaises(ActivityError):
            TaskService.add_executor(task, self.creator, added_by=self.creator)

    def test_accept_assignment_rejects_the_responsavel_as_participant(self):
        task = self._make_task()
        assignment = TaskService.add_executor(task, self.executor, added_by=self.creator)
        grant_action(self.creator, catalog.TAREFA_ALTERAR_RESPONSAVEL, organization=self.org)
        TaskService.change_responsavel(task, self.executor, changed_by=self.creator)
        with self.assertRaises(ActivityError):
            TaskService.accept_assignment(assignment, self.executor)

    def test_responsavel_alone_can_start_pause_and_log_time(self):
        task = self._make_task()
        TaskService.start(task, self.creator)
        self.assertTrue(WorkSession.objects.filter(task=task, user=self.creator, ended_at__isnull=True).exists())
        TaskService.pause(task, self.creator)
        self.assertFalse(WorkSession.objects.filter(task=task, user=self.creator, ended_at__isnull=True).exists())

    def test_participant_without_being_responsavel_can_start_task(self):
        task = self._make_task()
        assignment = TaskService.add_executor(task, self.executor, added_by=self.creator)
        TaskService.accept_assignment(assignment, self.executor)
        TaskService.start(task, self.executor)
        self.assertTrue(WorkSession.objects.filter(task=task, user=self.executor, ended_at__isnull=True).exists())

    def test_change_responsavel_requires_permission(self):
        task = self._make_task()
        with self.assertRaises(ActivityError):
            TaskService.change_responsavel(task, self.executor, changed_by=self.executor)

    def test_change_responsavel_creates_log_audits_and_notifies(self):
        task = self._make_task()
        grant_action(self.gestor, catalog.TAREFA_ALTERAR_RESPONSAVEL, organization=self.org)

        TaskService.change_responsavel(task, self.executor, changed_by=self.gestor)
        task.refresh_from_db()

        self.assertEqual(task.responsavel, self.executor)
        self.assertEqual(task.responsavel_changes.count(), 1)
        change = task.responsavel_changes.first()
        self.assertEqual(change.previous_responsavel, self.creator)
        self.assertEqual(change.new_responsavel, self.executor)
        self.assertEqual(change.changed_by, self.gestor)

        self.assertTrue(
            AuditLog.objects.filter(task=task, action=AuditLog.Action.RESPONSAVEL_CHANGED).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                task=task, event_type=Notification.EventType.TASK_RESPONSAVEL_CHANGED, recipient=self.creator
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                task=task, event_type=Notification.EventType.TASK_RESPONSAVEL_CHANGED, recipient=self.executor
            ).exists()
        )

    def test_change_responsavel_removes_new_responsavel_from_participantes(self):
        task = self._make_task()
        assignment = TaskService.add_executor(task, self.executor, added_by=self.creator)
        TaskService.accept_assignment(assignment, self.executor)
        grant_action(self.gestor, catalog.TAREFA_ALTERAR_RESPONSAVEL, organization=self.org)

        TaskService.change_responsavel(task, self.executor, changed_by=self.gestor)

        self.assertFalse(
            TaskExecutor.objects.filter(task=task, user=self.executor, removed_at__isnull=True).exists()
        )

    def test_change_responsavel_rejects_same_person(self):
        task = self._make_task()
        grant_action(self.gestor, catalog.TAREFA_ALTERAR_RESPONSAVEL, organization=self.org)
        with self.assertRaises(ActivityError):
            TaskService.change_responsavel(task, self.creator, changed_by=self.gestor)

    def test_change_responsavel_rejects_completed_or_cancelled_task(self):
        task = self._make_task()
        grant_action(self.gestor, catalog.TAREFA_ALTERAR_RESPONSAVEL, organization=self.org)
        TaskService.start(task, self.creator)
        TaskService.complete(task, self.creator)
        with self.assertRaises(ActivityError):
            TaskService.change_responsavel(task, self.executor, changed_by=self.gestor)


class TaskReturnTests(ActivitiesTestCase):
    def test_return_requires_reason(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        task = TaskService.create_task(activity, self.sector, "Cotação", created_by=self.creator, responsavel=self.creator)
        target_sector = Sector.objects.create(organization=self.org, name="Engenharia")

        with self.assertRaises(ActivityError):
            TaskService.return_task(task, target_sector, reason=None, user=self.creator)

    def test_return_preserves_history_and_moves_sector(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        task = TaskService.create_task(activity, self.sector, "Cotação", created_by=self.creator, responsavel=self.creator)
        engenharia = Sector.objects.create(organization=self.org, name="Engenharia")

        TaskService.return_task(task, engenharia, reason=self.reason, user=self.creator, observation="Faltou item X")
        task.refresh_from_db()

        self.assertEqual(task.sector, engenharia)
        self.assertEqual(task.returns.count(), 1)
        record = task.returns.first()
        self.assertEqual(record.from_sector, self.sector)
        self.assertEqual(record.to_sector, engenharia)
        self.assertEqual(record.reason, self.reason)
        # Sector transfer history must also exist (Regras 02 §90, 04 §101-105).
        self.assertTrue(task.sector_transfers.filter(from_sector=self.sector, to_sector=engenharia).exists())


class QueueTests(ActivitiesTestCase):
    def test_position_and_total_are_tracked(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        task1 = TaskService.create_task(activity, self.sector, "Tarefa 1", created_by=self.creator, responsavel=self.creator)
        task2 = TaskService.create_task(activity, self.sector, "Tarefa 2", created_by=self.creator, responsavel=self.creator)
        task3 = TaskService.create_task(activity, self.sector, "Tarefa 3", created_by=self.creator, responsavel=self.creator)

        entry1 = QueueEntry.objects.get(task=task1)
        entry2 = QueueEntry.objects.get(task=task2)
        entry3 = QueueEntry.objects.get(task=task3)

        self.assertEqual((entry1.position, entry1.queue_size_at_entry), (1, 1))
        self.assertEqual((entry2.position, entry2.queue_size_at_entry), (2, 2))
        self.assertEqual((entry3.position, entry3.queue_size_at_entry), (3, 3))

    def test_reorder_requires_permission_and_is_audited(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        task1 = TaskService.create_task(activity, self.sector, "Tarefa 1", created_by=self.creator, responsavel=self.creator)
        TaskService.create_task(activity, self.sector, "Tarefa 2", created_by=self.creator, responsavel=self.creator)
        entry1 = QueueEntry.objects.get(task=task1)

        with self.assertRaises(ActivityError):
            QueueService.reorder(entry1, 2, user=self.creator)

        grant_action(self.gestor, catalog.FILA_REORDENAR, sector=self.sector)
        QueueService.reorder(entry1, 2, user=self.gestor, reason="Entrada de demanda bloqueadora")
        entry1.refresh_from_db()

        self.assertEqual(entry1.position, 2)
        self.assertTrue(entry1.position_changes.filter(old_position=1, new_position=2).exists())


class DeadlineNegotiationTests(ActivitiesTestCase):
    def _make_task(self):
        activity = ActivityService.create_activity(
            organization=self.org,
            title="Atividade",
            owner=self.owner,
            created_by=self.creator,
            requested_deadline=timezone.now(),
        )
        return TaskService.create_task(
            activity, self.sector, "Tarefa", created_by=self.creator, responsavel=self.creator,
            requested_deadline=timezone.now()
        )

    def test_requested_and_committed_deadline_are_distinct(self):
        task = self._make_task()
        proposal = DeadlineService.propose(task, timezone.now() + timezone.timedelta(days=2), user=self.creator)
        DeadlineService.accept(proposal, user=self.owner)
        task.refresh_from_db()

        self.assertIsNotNone(task.requested_deadline)
        self.assertIsNotNone(task.committed_deadline)
        self.assertNotEqual(task.requested_deadline, task.committed_deadline)

    def test_only_owner_can_accept_or_reject(self):
        task = self._make_task()
        proposal = DeadlineService.propose(task, timezone.now() + timezone.timedelta(days=2), user=self.creator)
        with self.assertRaises(ActivityError):
            DeadlineService.accept(proposal, user=self.creator)

    def test_rejection_opens_deadline_conflict(self):
        task = self._make_task()
        proposal = DeadlineService.propose(task, timezone.now() + timezone.timedelta(days=2), user=self.creator)
        DeadlineService.reject(proposal, user=self.owner, note="Equipe da obra ficará parada.")
        proposal.refresh_from_db()

        self.assertEqual(proposal.status, DeadlineProposal.Status.RECUSADO)
        self.assertTrue(DeadlineConflict.objects.filter(task=task, proposal=proposal).exists())

    def test_resolving_conflict_requires_permission(self):
        task = self._make_task()
        proposal = DeadlineService.propose(task, timezone.now() + timezone.timedelta(days=2), user=self.creator)
        DeadlineService.reject(proposal, user=self.owner, note="Sem capacidade.")
        conflict = DeadlineConflict.objects.get(task=task)

        with self.assertRaises(ActivityError):
            DeadlineService.resolve_conflict(conflict, user=self.creator, resolution_note="Mantido")

        grant_action(self.gestor, catalog.ESCALONAMENTO_RESOLVER, organization=self.org)
        DeadlineService.resolve_conflict(conflict, user=self.gestor, resolution_note="Mantido prazo original")
        conflict.refresh_from_db()
        self.assertEqual(conflict.status, DeadlineConflict.Status.RESOLVIDO)


class OrganizationIsolationTests(ActivitiesTestCase):
    def test_task_cannot_use_sector_from_another_organization(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        with self.assertRaises(ActivityError):
            TaskService.create_task(activity, self.other_sector, "Tarefa cruzada", created_by=self.creator, responsavel=self.creator)

    def test_task_cannot_move_to_sector_from_another_organization(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        task = TaskService.create_task(activity, self.sector, "Tarefa", created_by=self.creator, responsavel=self.creator)
        with self.assertRaises(ActivityError):
            TaskService.move_to_sector(task, self.other_sector, user=self.creator)


class ActivityCompletionTests(ActivitiesTestCase):
    def test_activity_cannot_complete_with_open_tasks(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        TaskService.create_task(activity, self.sector, "Tarefa", created_by=self.creator, responsavel=self.creator)
        with self.assertRaises(ActivityError):
            ActivityService.complete_activity(activity, user=self.owner)

    def test_activity_completion_notifies_owner(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        ActivityService.complete_activity(activity, user=self.owner)
        activity.refresh_from_db()
        self.assertEqual(activity.status, Activity.Status.CONCLUIDA)
        self.assertTrue(self.owner.notifications.filter(activity=activity, event_type="ACTIVITY_COMPLETED").exists())


class UpdateAuditTests(ActivitiesTestCase):
    def test_editing_activity_audits_each_field(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Título antigo", owner=self.owner, created_by=self.creator
        )
        ActivityService.update_activity(
            activity, self.owner, title="Título novo", description="Contexto"
        )
        activity.refresh_from_db()

        self.assertEqual(activity.title, "Título novo")
        entries = activity.audit_entries.filter(action=AuditLog.Action.UPDATE)
        self.assertEqual(entries.count(), 2)
        title_entry = entries.get(field_name="title")
        self.assertEqual(title_entry.old_value, "Título antigo")
        self.assertEqual(title_entry.new_value, "Título novo")

    def test_completed_activity_cannot_be_edited(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        ActivityService.complete_activity(activity, user=self.owner)
        with self.assertRaises(ActivityError):
            ActivityService.update_activity(activity, self.owner, title="Outro")

    def test_task_cannot_depend_on_itself(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        task = TaskService.create_task(activity, self.sector, "Tarefa", created_by=self.creator, responsavel=self.creator)
        with self.assertRaises(ActivityError):
            TaskService.update_task(task, self.creator, depends_on=task)


class ManualTimeTests(ActivitiesTestCase):
    def _task(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        task = TaskService.create_task(activity, self.sector, "Tarefa", created_by=self.creator, responsavel=self.creator)
        assignment = TaskService.add_executor(task, self.executor, added_by=self.creator)
        TaskService.accept_assignment(assignment, self.executor)
        return task

    def test_time_can_only_be_logged_for_an_executor(self):
        task = self._task()
        now = timezone.now()
        with self.assertRaises(ActivityError):
            TaskService.log_manual_time(
                task,
                user=self.executor2,  # não é executor da tarefa
                started_at=now - timezone.timedelta(hours=1),
                ended_at=now,
                logged_by=self.creator,
            )

    def test_manual_time_is_flagged(self):
        task = self._task()
        now = timezone.now()
        session = TaskService.log_manual_time(
            task,
            user=self.executor,
            started_at=now - timezone.timedelta(hours=2),
            ended_at=now - timezone.timedelta(hours=1),
            logged_by=self.creator,
        )
        self.assertTrue(session.is_manual)
        self.assertEqual(session.duration, timezone.timedelta(hours=1))

    def test_manual_time_rejects_inverted_period(self):
        task = self._task()
        now = timezone.now()
        with self.assertRaises(ActivityError):
            TaskService.log_manual_time(
                task,
                user=self.executor,
                started_at=now,
                ended_at=now - timezone.timedelta(hours=1),
                logged_by=self.creator,
            )

    def test_manual_time_rejects_future(self):
        task = self._task()
        future = timezone.now() + timezone.timedelta(days=1)
        with self.assertRaises(ActivityError):
            TaskService.log_manual_time(
                task,
                user=self.executor,
                started_at=future,
                ended_at=future + timezone.timedelta(hours=1),
                logged_by=self.creator,
            )


class QueueRenumberTests(ActivitiesTestCase):
    def test_completing_task_closes_position_gap(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        first = TaskService.create_task(activity, self.sector, "Tarefa 1", created_by=self.creator, responsavel=self.creator)
        second = TaskService.create_task(activity, self.sector, "Tarefa 2", created_by=self.creator, responsavel=self.creator)
        third = TaskService.create_task(activity, self.sector, "Tarefa 3", created_by=self.creator, responsavel=self.creator)

        TaskService.complete(first, self.creator)

        remaining = QueueEntry.objects.filter(sector=self.sector, left_at__isnull=True).order_by("position")
        self.assertEqual([e.position for e in remaining], [1, 2])
        self.assertEqual([e.task_id for e in remaining], [second.pk, third.pk])

    def test_renumbering_is_recorded_as_automatic(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        first = TaskService.create_task(activity, self.sector, "Tarefa 1", created_by=self.creator, responsavel=self.creator)
        second = TaskService.create_task(activity, self.sector, "Tarefa 2", created_by=self.creator, responsavel=self.creator)

        TaskService.complete(first, self.creator)

        entry = QueueEntry.objects.get(task=second)
        change = entry.position_changes.first()
        self.assertEqual(change.reason, QueuePositionChange.Reason.AUTOMATICA_CONCLUSAO)
        self.assertIsNone(change.changed_by)

    def test_history_never_records_a_position_larger_than_the_total(self):
        """"2 de 1" seria impossível e apareceria para o solicitante."""
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        first = TaskService.create_task(activity, self.sector, "Tarefa 1", created_by=self.creator, responsavel=self.creator)
        TaskService.create_task(activity, self.sector, "Tarefa 2", created_by=self.creator, responsavel=self.creator)
        TaskService.create_task(activity, self.sector, "Tarefa 3", created_by=self.creator, responsavel=self.creator)

        TaskService.complete(first, self.creator)

        for change in QueuePositionChange.objects.all():
            self.assertLessEqual(change.old_position, change.old_total)
            self.assertLessEqual(change.new_position, change.new_total)


class MessageTests(ActivitiesTestCase):
    def test_activity_message_notifies_owner_not_author(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        MessageService.post_activity_message(activity, self.creator, "Alguma novidade?")

        self.assertEqual(activity.messages.count(), 1)
        self.assertTrue(self.owner.notifications.filter(activity=activity).exists())
        self.assertFalse(
            self.creator.notifications.filter(
                activity=activity, title="Nova mensagem na atividade"
            ).exists()
        )

    def test_empty_message_is_rejected(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        with self.assertRaises(ActivityError):
            MessageService.post_activity_message(activity, self.creator, "   ")

    def test_task_message_reaches_executors(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        task = TaskService.create_task(activity, self.sector, "Tarefa", created_by=self.creator, responsavel=self.creator)
        assignment = TaskService.add_executor(task, self.executor, added_by=self.creator)
        TaskService.accept_assignment(assignment, self.executor)

        MessageService.post_task_message(task, self.owner, "Fornecedor informou 7 dias")

        self.assertTrue(
            self.executor.notifications.filter(task=task, title="Nova mensagem na tarefa").exists()
        )


class MentionTests(ActivitiesTestCase):
    """@menção com autocomplete (a inserção do texto é responsabilidade do
    front-end; aqui testamos só a extração/notificação server-side, que é
    a mesma para qualquer campo — texto puro ou HTML sanitizado)."""

    def test_mentioned_user_is_notified(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        mentioned = find_mentioned_users(f"Olá @{self.executor.username}", self.creator, activity)
        self.assertEqual(mentioned, {self.executor})

    def test_author_never_mentions_self(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        mentioned = find_mentioned_users(f"Olá @{self.creator.username}", self.creator, activity)
        self.assertEqual(mentioned, set())

    def test_mention_without_permission_is_silently_ignored(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        outsider = User.objects.create_user("externo", password="x")
        outsider.profile.organization = self.other_org
        outsider.profile.save(update_fields=["organization"])

        mentioned = find_mentioned_users(f"Olá @{outsider.username}", self.creator, activity)

        self.assertEqual(mentioned, set())
        self.assertFalse(outsider.notifications.exists())

    def test_mention_in_activity_description_on_create(self):
        activity = ActivityService.create_activity(
            organization=self.org,
            title="Atividade",
            owner=self.owner,
            created_by=self.creator,
            description=f"Confirmar com @{self.executor.username} antes de prosseguir.",
        )
        self.assertTrue(
            self.executor.notifications.filter(
                activity=activity, event_type=Notification.EventType.MENTIONED
            ).exists()
        )

    def test_mention_in_activity_description_on_update(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        self.assertFalse(self.executor.notifications.filter(event_type=Notification.EventType.MENTIONED).exists())

        ActivityService.update_activity(
            activity, self.owner, description=f"Ver com @{self.executor.username}."
        )

        self.assertTrue(
            self.executor.notifications.filter(
                activity=activity, event_type=Notification.EventType.MENTIONED
            ).exists()
        )

    def test_mention_in_task_description_on_update(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        task = TaskService.create_task(activity, self.sector, "Tarefa", created_by=self.creator, responsavel=self.creator)

        TaskService.update_task(task, self.creator, description=f"Falar com @{self.executor.username}.")

        self.assertTrue(
            self.executor.notifications.filter(task=task, event_type=Notification.EventType.MENTIONED).exists()
        )

    def test_mention_in_cancellation_reason(self):
        activity = ActivityService.create_activity(
            organization=self.org, title="Atividade", owner=self.owner, created_by=self.creator
        )
        grant_action(self.owner, catalog.ATIVIDADE_CANCELAR, organization=self.org)
        ActivityService.cancel_activity(
            activity, self.owner, reason=f"Cliente desistiu, @{self.executor.username} já sabe."
        )

        self.assertTrue(
            self.executor.notifications.filter(
                activity=activity, event_type=Notification.EventType.MENTIONED
            ).exists()
        )

    def test_mention_in_deadline_conflict_resolution(self):
        activity = ActivityService.create_activity(
            organization=self.org,
            title="Atividade",
            owner=self.owner,
            created_by=self.creator,
            requested_deadline=timezone.now(),
        )
        task = TaskService.create_task(
            activity, self.sector, "Tarefa", created_by=self.creator, responsavel=self.creator,
            requested_deadline=timezone.now()
        )
        proposal = DeadlineService.propose(task, timezone.now() + timezone.timedelta(days=2), user=self.creator)
        DeadlineService.reject(proposal, user=self.owner, note="Sem capacidade.")
        conflict = DeadlineConflict.objects.get(task=task)
        grant_action(self.gestor, catalog.ESCALONAMENTO_RESOLVER, organization=self.org)

        DeadlineService.resolve_conflict(
            conflict, user=self.gestor, resolution_note=f"Decidido com @{self.executor.username}."
        )

        self.assertTrue(
            self.executor.notifications.filter(task=task, event_type=Notification.EventType.MENTIONED).exists()
        )


class StatusLabelOverrideTests(ActivitiesTestCase):
    """status_label/status_description resolvem o override da organização
    sem nunca tocar o code real gravado em `status` nem a regra de negócio
    que compara contra ele (Regras: cor/label é só aparência)."""

    def _make_activity(self):
        return ActivityService.create_activity(
            organization=self.org, title="Orçamento", owner=self.owner, created_by=self.creator
        )

    def test_activity_status_label_falls_back_to_native_display(self):
        activity = self._make_activity()
        self.assertEqual(activity.status_label, activity.get_status_display())

    def test_activity_status_label_uses_organization_override(self):
        from core.services import EnumColorService

        activity = self._make_activity()
        EnumColorService.set_overrides(self.org, "activity_status", activity.status, label="Recem-criada")
        self.assertEqual(activity.status_label, "Recem-criada")
        self.assertEqual(activity.status, Activity.Status.ABERTA)
        self.assertEqual(activity.get_status_display(), "Aberta")

    def test_activity_status_description_falls_back_to_empty(self):
        activity = self._make_activity()
        self.assertEqual(activity.status_description, "")

    def test_task_status_label_uses_organization_override(self):
        from core.services import EnumColorService

        activity = self._make_activity()
        task = TaskService.create_task(activity, self.sector, "Levantar quantitativos", created_by=self.creator, responsavel=self.creator)
        original_status = task.status
        EnumColorService.set_overrides(self.org, "task_status", task.status, label="Aguardando fila")
        self.assertEqual(task.status_label, "Aguardando fila")
        self.assertEqual(task.status, original_status)

    def test_override_in_another_organization_does_not_leak(self):
        from core.models import Organization
        from core.services import EnumColorService

        activity = self._make_activity()
        other_org = Organization.objects.create(name="Outra Instaladora")
        EnumColorService.set_overrides(other_org, "activity_status", activity.status, label="Nao deveria aparecer")
        self.assertEqual(activity.status_label, activity.get_status_display())


class ActivityDraftServiceTests(ActivitiesTestCase):
    """Rascunho real (wizard de 3 etapas): pode salvar incompleto (sem
    título/dono) e só é cobrado de verdade ao publicar. `owner=None` nunca
    deve dar acesso indevido em nenhum escopo relacional."""

    def test_save_draft_creates_row_without_title_or_owner(self):
        activity = ActivityService.save_draft(
            organization=self.org, created_by=self.creator, activity=None
        )
        self.assertEqual(activity.status, Activity.Status.RASCUNHO)
        self.assertEqual(activity.title, Activity.DRAFT_TITLE_PLACEHOLDER)
        self.assertIsNone(activity.owner_id)
        self.assertEqual(activity.created_by, self.creator)

    def test_save_draft_updates_existing_row_in_place(self):
        activity = ActivityService.save_draft(organization=self.org, created_by=self.creator, activity=None)
        pk = activity.pk
        updated = ActivityService.save_draft(
            organization=self.org, created_by=self.creator, activity=activity, title="Visita técnica"
        )
        self.assertEqual(updated.pk, pk)
        self.assertEqual(updated.title, "Visita técnica")
        self.assertEqual(Activity.objects.filter(status=Activity.Status.RASCUNHO).count(), 1)

    def test_save_draft_rejects_editing_someone_elses_draft(self):
        activity = ActivityService.save_draft(organization=self.org, created_by=self.creator, activity=None)
        with self.assertRaises(ActivityError):
            ActivityService.save_draft(
                organization=self.org, created_by=self.owner, activity=activity, title="Sequestrado"
            )

    def test_publish_draft_requires_title_and_owner(self):
        activity = ActivityService.save_draft(organization=self.org, created_by=self.creator, activity=None)
        with self.assertRaises(ActivityError):
            ActivityService.publish_draft(activity, self.creator)

        activity = ActivityService.save_draft(
            organization=self.org, created_by=self.creator, activity=activity, title="Visita técnica"
        )
        with self.assertRaises(ActivityError):
            ActivityService.publish_draft(activity, self.creator)

    def test_publish_draft_succeeds_and_becomes_a_real_activity(self):
        activity = ActivityService.save_draft(
            organization=self.org,
            created_by=self.creator,
            activity=None,
            title="Visita técnica",
            owner=self.owner,
        )
        published = ActivityService.publish_draft(activity, self.creator)
        self.assertEqual(published.status, Activity.Status.ABERTA)

    def test_publish_draft_twice_fails(self):
        activity = ActivityService.save_draft(
            organization=self.org, created_by=self.creator, activity=None, title="Visita técnica", owner=self.owner
        )
        ActivityService.publish_draft(activity, self.creator)
        with self.assertRaises(ActivityError):
            ActivityService.publish_draft(activity, self.creator)

    def test_discard_draft_deletes_row_and_attachments(self):
        activity = ActivityService.save_draft(organization=self.org, created_by=self.creator, activity=None)
        pk = activity.pk
        ActivityService.discard_draft(activity, self.creator)
        self.assertFalse(Activity.objects.filter(pk=pk).exists())

    def test_discard_draft_rejects_publishing_or_other_users(self):
        activity = ActivityService.save_draft(
            organization=self.org, created_by=self.creator, activity=None, title="X", owner=self.owner
        )
        ActivityService.publish_draft(activity, self.creator)
        with self.assertRaises(ActivityError):
            ActivityService.discard_draft(activity, self.creator)

    def test_owner_none_never_matches_relational_scope(self):
        """Uma linha com owner=None nunca deve satisfazer o escopo "minhas
        atividades" para nenhum usuário — a checagem de autorização falha
        fechado, nunca abre uma brecha."""
        from acessos.services import ResourceContext

        activity = ActivityService.save_draft(organization=self.org, created_by=self.creator, activity=None)
        context = ResourceContext.of(activity)
        self.assertIsNone(context.owner_id)
        self.assertNotEqual(context.owner_id, self.creator.id)
        self.assertFalse(context.owner_id == self.creator.id)
