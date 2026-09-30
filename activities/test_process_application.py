"""Aplicação de processo a uma atividade: materialização, dependências,
inputs, critérios, integridade e finalização.

O cenário base (Orçamento v3, três etapas em sequência, três inputs e quatro
critérios) está em `activities/testing.py`.
"""

from unittest import mock

from django.db import IntegrityError, transaction

from acessos import catalog
from acessos.testing import grant_action
from audit.models import AuditLog
from notifications.models import Notification
from processes.models import (
    ActivityCriterionCheck,
    ActivityInputValue,
    ProcessInput,
    ProcessVersion,
)
from processes.services import ProcessService
from processes.testing import build_process

from .models import Activity, QueueEntry, Task
from .process_application import ActivityProcessService, ProcessApplicationService, normalize_input_value
from .services import ActivityError, ActivityService, TaskService
from .testing import ProcessTestCase, make_user


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ProcessModelTests(ProcessTestCase):
    def test_task_accepts_process_step_and_manual_tasks_have_none(self):
        step = self.version.steps.first()
        task = Task.objects.create(
            activity=self.activity, sector=self.comercial, title="Da etapa", created_by=self.owner,
            responsavel=self.ryan, process_step=step,
        )
        self.assertEqual(task.process_step, step)
        self.assertIn(task, step.tasks.all())
        plain = Task.objects.create(
            activity=self.activity, sector=self.comercial, title="Manual", created_by=self.owner, responsavel=self.ryan
        )
        self.assertIsNone(plain.process_step)

    def test_constraint_blocks_second_task_for_same_activity_and_step(self):
        step = self.version.steps.first()
        Task.objects.create(
            activity=self.activity, sector=self.comercial, title="A", created_by=self.owner,
            responsavel=self.ryan, process_step=step,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Task.objects.create(
                activity=self.activity, sector=self.comercial, title="B", created_by=self.owner,
                responsavel=self.ryan, process_step=step,
            )

    def test_constraint_allows_same_step_in_another_activity_and_many_manual_tasks(self):
        step = self.version.steps.first()
        other_activity = self.new_activity(title="Outra")
        for activity in (self.activity, other_activity):
            Task.objects.create(
                activity=activity, sector=self.comercial, title="Da etapa", created_by=self.owner,
                responsavel=self.ryan, process_step=step,
            )
        for _ in range(2):
            Task.objects.create(
                activity=self.activity, sector=self.comercial, title="Manual", created_by=self.owner,
                responsavel=self.ryan,
            )
        self.assertEqual(Task.objects.filter(process_step__isnull=True).count(), 2)


# ---------------------------------------------------------------------------
# Aplicação: o que é materializado
# ---------------------------------------------------------------------------


class ApplyMaterializationTests(ProcessTestCase):
    def test_published_process_can_be_applied_and_locks_the_version(self):
        applied = self.apply()
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.process_version, self.version)
        self.assertEqual(applied.pk, self.activity.pk)

    def test_every_process_input_becomes_an_activity_input_value_not_received(self):
        self.apply()
        rows = ActivityInputValue.objects.filter(activity=self.activity)
        self.assertEqual(rows.count(), 3)
        self.assertEqual(
            set(rows.values_list("process_input__name", flat=True)), {"Projetos", "Memorial", "Prazo solicitado"}
        )
        self.assertFalse(rows.filter(is_received=True).exists())

    def test_every_process_criterion_becomes_an_unmet_check(self):
        self.apply()
        rows = ActivityCriterionCheck.objects.filter(activity=self.activity)
        self.assertEqual(rows.count(), 4)
        self.assertFalse(rows.filter(is_met=True).exists())

    def test_every_step_becomes_a_task_with_sector_order_step_and_responsavel(self):
        self.apply()
        tasks = self.tasks()
        self.assertEqual(len(tasks), 3)
        steps = list(self.version.steps.order_by("order"))
        for task, step, person in zip(tasks, steps, (self.ryan, self.vitor, self.paulo)):
            self.assertEqual(task.title, step.name)
            self.assertEqual(task.sector, step.sector)
            self.assertEqual(task.order, step.order)
            self.assertEqual(task.process_step, step)
            self.assertEqual(task.responsavel, person)
            self.assertEqual(task.created_by, self.applier)

    def test_default_responsavel_is_used_when_nothing_is_informed(self):
        self.apply()
        self.assertEqual(self.tasks()[1].responsavel, self.vitor)

    def test_override_informed_at_apply_time_wins_over_the_default(self):
        step2 = self.version.steps.get(order=2)
        self.apply(responsible_by_step={step2.pk: self.paulo})
        self.assertEqual(self.tasks()[1].responsavel, self.paulo)
        self.assertEqual(self.tasks()[0].responsavel, self.ryan)

    def test_override_accepts_a_plain_user_id(self):
        step2 = self.version.steps.get(order=2)
        self.apply(responsible_by_step={step2.pk: self.paulo.pk})
        self.assertEqual(self.tasks()[1].responsavel, self.paulo)

    def test_responsavel_outside_the_sector_is_accepted(self):
        step2 = self.version.steps.get(order=2)  # setor Compras
        self.apply(responsible_by_step={step2.pk: self.ryan})  # Ryan é do Comercial
        self.assertEqual(self.tasks()[1].responsavel, self.ryan)

    def test_initial_input_values_are_stored_and_audited(self):
        projetos = self.version.inputs.get(name="Projetos")
        prazo = self.version.inputs.get(name="Prazo solicitado")
        self.apply(input_values={projetos.pk: "Projeto executivo rev. B", prazo.pk: "2026-10-15"})
        row = ActivityInputValue.objects.get(activity=self.activity, process_input=projetos)
        self.assertTrue(row.is_received)
        self.assertEqual(row.value, "Projeto executivo rev. B")
        self.assertEqual(row.received_by, self.applier)
        self.assertIsNotNone(row.received_at)
        self.assertEqual(ActivityInputValue.objects.get(activity=self.activity, process_input=prazo).value, "2026-10-15")
        self.assertFalse(ActivityInputValue.objects.get(activity=self.activity, process_input__name="Memorial").is_received)
        self.assertEqual(AuditLog.objects.filter(activity=self.activity, action=AuditLog.Action.INPUT_UPDATED).count(), 2)

    def test_applier_needs_only_processo_aplicar_not_tarefa_criar(self):
        from acessos.services import AuthorizationService

        self.assertFalse(AuthorizationService.can(self.applier, catalog.TAREFA_CRIAR, self.activity))
        # Criar tarefa avulsa continua exigindo tarefa.criar...
        with self.assertRaises(ActivityError):
            TaskService.create_task(self.activity, self.compras, "Solta", created_by=self.applier, responsavel=self.vitor)
        # ...mas aplicar o processo materializa as tarefas de todos os setores.
        self.apply()
        self.assertEqual({t.sector for t in self.tasks()}, {self.comercial, self.compras})
        self.assertEqual(len(self.tasks()), 3)

    def test_apply_is_audited_with_process_name_and_version(self):
        self.apply()
        entry = AuditLog.objects.get(activity=self.activity, action=AuditLog.Action.PROCESS_APPLIED)
        self.assertEqual(entry.user, self.applier)
        self.assertEqual(entry.new_value, "Orçamento v3")
        self.assertEqual(AuditLog.objects.filter(activity=self.activity, action=AuditLog.Action.TASK_CREATED).count(), 3)
        self.assertTrue(
            AuditLog.objects.filter(activity=self.activity, action=AuditLog.Action.TASK_CREATED, user=self.applier).count() == 3
        )

    def test_rewritten_caller_activity_is_coherent_after_apply(self):
        stale = Activity.objects.get(pk=self.activity.pk)
        self.apply(activity=stale)
        self.assertEqual(stale.process_version_id, self.version.pk)


# ---------------------------------------------------------------------------
# Aplicação: o que é recusado (e nada é gravado)
# ---------------------------------------------------------------------------


class ApplyValidationTests(ProcessTestCase):
    def assertNothingPersisted(self, activity=None):
        activity = activity or self.activity
        activity.refresh_from_db()
        self.assertIsNone(activity.process_version_id)
        self.assertFalse(activity.tasks.exists())
        self.assertFalse(ActivityInputValue.objects.filter(activity=activity).exists())
        self.assertFalse(ActivityCriterionCheck.objects.filter(activity=activity).exists())
        self.assertFalse(AuditLog.objects.filter(activity=activity, action=AuditLog.Action.PROCESS_APPLIED).exists())

    def test_draft_version_cannot_be_applied(self):
        draft = self.new_process(name="Rascunho", publish=False)
        with self.assertRaisesMessage(ActivityError, "versão publicada"):
            self.apply(version=draft)
        self.assertNothingPersisted()

    def test_superseded_version_cannot_be_applied(self):
        newer = self.new_process(process=self.version.process, number=4)
        self.version.refresh_from_db()
        self.assertEqual(self.version.status, ProcessVersion.Status.SUBSTITUIDO)
        with self.assertRaisesMessage(ActivityError, "versão publicada"):
            self.apply(version=self.version)
        self.apply(version=newer)

    def test_inactive_process_cannot_be_applied(self):
        self.version.process.is_active = False
        self.version.process.save(update_fields=["is_active"])
        with self.assertRaisesMessage(ActivityError, "inativo"):
            self.apply()
        self.assertNothingPersisted()

    def test_process_from_another_tenant_cannot_be_applied(self):
        foreign_owner = make_user("dono_alheio", self.other_org, [catalog.ATIVIDADE_CRIAR])
        foreign_version = build_process(
            self.other_org, self.foreign_company, foreign_owner, name="Alheio",
            steps=[{"name": "X", "sector": self.foreign_sector, "default_responsavel": foreign_owner}],
        )
        with self.assertRaisesMessage(ActivityError, "outra organização"):
            self.apply(version=foreign_version)
        self.assertNothingPersisted()

    def test_activity_from_another_tenant_cannot_receive_a_process(self):
        with self.assertRaises(ActivityError):
            self.apply(user=self.foreign)
        self.assertNothingPersisted()

    def test_process_from_another_company_is_rejected(self):
        activity = self.new_activity(company=self.other_company, title="Outra empresa")
        with self.assertRaisesMessage(ActivityError, "não é a empresa desta atividade"):
            self.apply(activity=activity)
        self.assertNothingPersisted(activity)

    def test_activity_without_company_is_rejected_with_a_clear_message(self):
        activity = self.new_activity(company=None, title="Sem empresa")
        with self.assertRaisesMessage(ActivityError, "Defina a empresa da atividade"):
            self.apply(activity=activity)
        self.assertNothingPersisted(activity)

    def test_completed_activity_is_rejected(self):
        Activity.objects.filter(pk=self.activity.pk).update(status=Activity.Status.CONCLUIDA)
        self.activity.refresh_from_db()
        with self.assertRaisesMessage(ActivityError, "concluída ou cancelada"):
            self.apply()
        self.activity.refresh_from_db()
        self.assertIsNone(self.activity.process_version_id)

    def test_cancelled_activity_is_rejected(self):
        Activity.objects.filter(pk=self.activity.pk).update(status=Activity.Status.CANCELADA)
        self.activity.refresh_from_db()
        with self.assertRaisesMessage(ActivityError, "concluída ou cancelada"):
            self.apply()
        self.assertFalse(self.activity.tasks.exists())

    def test_draft_activity_is_rejected(self):
        Activity.objects.filter(pk=self.activity.pk).update(status=Activity.Status.RASCUNHO)
        self.activity.refresh_from_db()
        with self.assertRaisesMessage(ActivityError, "Conclua a criação"):
            self.apply()

    def test_activity_that_already_has_a_process_is_rejected(self):
        self.apply()
        other = self.new_process(name="Outro", number=1)
        with self.assertRaisesMessage(ActivityError, "já tem um processo aplicado"):
            self.apply(version=other)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.process_version, self.version)

    def test_user_without_processo_aplicar_is_rejected(self):
        with self.assertRaises(ActivityError):
            self.apply(user=self.stranger)
        self.assertNothingPersisted()

    def test_processo_aplicar_is_checked_against_the_activity_scope(self):
        from acessos.models import Scope
        from acessos.services import ScopeService

        other_scope = ScopeService.get_or_create(self.org, Scope.Type.EMPRESA, company=self.other_company)
        own_scope = ScopeService.get_or_create(self.org, Scope.Type.EMPRESA, company=self.company)

        wrong = make_user("escopo_errado", self.org)
        grant_action(wrong, catalog.PROCESSO_APLICAR, organization=self.org, scope=other_scope)
        with self.assertRaises(ActivityError):
            self.apply(user=wrong)
        self.assertNothingPersisted()

        right = make_user("escopo_certo", self.org)
        grant_action(right, catalog.PROCESSO_APLICAR, organization=self.org, scope=own_scope)
        self.apply(user=right)
        self.assertEqual(self.activity.tasks.count(), 3)

    def test_step_without_any_responsavel_fails_before_any_write(self):
        version = self.new_process(
            name="Sem padrão",
            steps=[
                {"name": "A", "sector": self.comercial, "default_responsavel": self.ryan},
                {"name": "B", "sector": self.compras},
                {"name": "C", "sector": self.comercial},
            ],
        )
        with self.assertRaisesMessage(ActivityError, "2. B; 3. C"):
            self.apply(version=version)
        self.assertNothingPersisted()

    def test_responsavel_of_another_tenant_is_rejected(self):
        step2 = self.version.steps.get(order=2)
        with self.assertRaisesMessage(ActivityError, "não pertence a esta organização"):
            self.apply(responsible_by_step={step2.pk: self.foreign})
        self.assertNothingPersisted()

    def test_inactive_responsavel_is_rejected(self):
        self.paulo.is_active = False
        self.paulo.save(update_fields=["is_active"])
        step2 = self.version.steps.get(order=2)
        with self.assertRaises(ActivityError):
            self.apply(responsible_by_step={step2.pk: self.paulo})
        self.assertNothingPersisted()

    def test_inactive_default_responsavel_requires_an_override(self):
        self.vitor.is_active = False
        self.vitor.save(update_fields=["is_active"])
        with self.assertRaisesMessage(ActivityError, "2. Cotação de materiais"):
            self.apply()
        self.assertNothingPersisted()
        step2 = self.version.steps.get(order=2)
        self.apply(responsible_by_step={step2.pk: self.paulo})
        self.assertEqual(self.tasks()[1].responsavel, self.paulo)

    def test_inactive_sector_is_rejected(self):
        self.compras.is_active = False
        self.compras.save(update_fields=["is_active"])
        with self.assertRaisesMessage(ActivityError, "Compras"):
            self.apply()
        self.assertNothingPersisted()

    def test_invalid_initial_input_value_is_rejected_before_writing(self):
        prazo = self.version.inputs.get(name="Prazo solicitado")
        with self.assertRaisesMessage(ActivityError, "data válida"):
            self.apply(input_values={prazo.pk: "amanhã"})
        self.assertNothingPersisted()

    def test_input_of_another_version_is_rejected(self):
        other = self.new_process(name="Outro", number=1)
        foreign_input = other.inputs.first()
        with self.assertRaisesMessage(ActivityError, "não pertence a esta versão"):
            self.apply(input_values={foreign_input.pk: "x"})
        self.assertNothingPersisted()

    def test_anonymous_user_is_rejected(self):
        from django.contrib.auth.models import AnonymousUser

        with self.assertRaises(ActivityError):
            self.apply(user=AnonymousUser())
        self.assertNothingPersisted()

    def test_eligible_versions_only_lists_published_active_same_company(self):
        self.new_process(name="Rascunho", publish=False)
        self.new_process(name="Inativo", is_active=False)
        self.new_process(name="Outra empresa", company=self.other_company)
        eligible = list(ProcessApplicationService.eligible_versions(self.activity))
        self.assertEqual([v.pk for v in eligible], [self.version.pk])
        self.assertEqual((eligible[0].step_count, eligible[0].input_count, eligible[0].criterion_count), (3, 3, 4))
        no_company = self.new_activity(company=None, title="Sem empresa")
        self.assertEqual(list(ProcessApplicationService.eligible_versions(no_company)), [])


# ---------------------------------------------------------------------------
# Dependências e liberação
# ---------------------------------------------------------------------------


class DependencyTests(ProcessTestCase):
    def setUp(self):
        super().setUp()
        self.apply()
        self.receive_all_required_inputs()
        self.t1, self.t2, self.t3 = self.tasks()

    def test_first_step_enters_its_sector_queue(self):
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.status, Task.Status.EM_FILA)
        self.assertTrue(self.active_queue(self.comercial).filter(task=self.t1).exists())

    def test_independent_step_also_enters_the_queue(self):
        version = self.new_process(
            name="Paralelo",
            steps=[
                {"name": "A", "sector": self.comercial, "default_responsavel": self.ryan, "depends_on_previous": False},
                {"name": "B", "sector": self.compras, "default_responsavel": self.vitor, "depends_on_previous": False},
            ],
        )
        activity = self.new_activity(title="Paralela")
        self.apply(activity=activity, version=version)
        a, b = self.tasks(activity)
        self.assertEqual((a.status, b.status), (Task.Status.EM_FILA, Task.Status.EM_FILA))
        self.assertIsNone(b.depends_on)

    def test_dependent_step_is_created_but_not_queued(self):
        for task in (self.t2, self.t3):
            task.refresh_from_db()
            self.assertEqual(task.status, Task.Status.DISPONIVEL)
            self.assertFalse(task.queue_entries.exists())
        self.assertFalse(self.active_queue(self.compras).exists())
        self.assertEqual(self.active_queue(self.comercial).count(), 1)

    def test_depends_on_points_to_the_previous_task(self):
        self.assertIsNone(self.t1.depends_on)
        self.assertEqual(self.t2.depends_on_id, self.t1.pk)
        self.assertEqual(self.t3.depends_on_id, self.t2.pk)

    def test_cannot_start_a_task_whose_predecessor_is_not_done(self):
        with self.assertRaisesMessage(ActivityError, "depende da conclusão de «Levantamento de quantitativos»"):
            TaskService.start(self.t2, self.vitor)
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, Task.Status.DISPONIVEL)

    def test_cannot_complete_a_task_whose_predecessor_is_not_done(self):
        with self.assertRaisesMessage(ActivityError, "depende da conclusão"):
            TaskService.complete(self.t2, self.vitor)

    def test_dependency_check_reads_the_current_predecessor_status_not_a_cached_one(self):
        cached = Task.objects.select_related("depends_on").get(pk=self.t2.pk)
        self.assertEqual(cached.depends_on.status, Task.Status.EM_FILA)  # cache antigo
        TaskService.complete(self.t1, self.ryan)
        TaskService.start(cached, self.vitor)  # não pode falhar por causa do cache
        cached.refresh_from_db()
        self.assertEqual(cached.status, Task.Status.EM_EXECUCAO)

    def test_completing_the_predecessor_releases_the_next_step_into_the_right_queue(self):
        TaskService.complete(self.t1, self.ryan)
        self.t2.refresh_from_db()
        self.t3.refresh_from_db()
        self.assertEqual(self.t2.status, Task.Status.EM_FILA)
        entry = self.active_queue(self.compras).get()
        self.assertEqual(entry.task, self.t2)
        self.assertEqual((entry.position, entry.queue_size_at_entry), (1, 1))
        # a etapa 3 continua esperando a 2
        self.assertEqual(self.t3.status, Task.Status.DISPONIVEL)
        self.assertFalse(self.t3.queue_entries.exists())

    def test_release_is_audited_and_notifies_sector_and_responsavel(self):
        Notification.objects.all().delete()
        TaskService.complete(self.t1, self.ryan)
        log = AuditLog.objects.get(task=self.t2, action=AuditLog.Action.TASK_RELEASED)
        self.assertEqual(log.user, self.ryan)
        self.assertEqual(log.new_value, "Compras")
        self.assertIn("Levantamento de quantitativos", log.reason)
        recipients = set(
            Notification.objects.filter(task=self.t2, event_type=Notification.EventType.TASK_ASSIGNED).values_list(
                "recipient__username", flat=True
            )
        )
        self.assertEqual(recipients, {"vitor"})

    def test_release_notifies_a_responsavel_who_is_not_in_the_sector(self):
        step2 = self.version.steps.get(order=2)
        activity = self.new_activity(title="Outra")
        self.apply(activity=activity, responsible_by_step={step2.pk: self.paulo})
        t1, t2, _ = self.tasks(activity)
        for row in ActivityInputValue.objects.filter(activity=activity, process_input__is_required=True):
            ActivityProcessService.update_input(self.owner, row, value="ok")
        Notification.objects.all().delete()
        TaskService.complete(t1, self.ryan)
        recipients = set(Notification.objects.filter(task=t2).values_list("recipient__username", flat=True))
        self.assertIn("paulo", recipients)  # responsável fora do setor Compras
        self.assertIn("vitor", recipients)  # membro do setor Compras

    def test_apply_does_not_notify_about_waiting_steps(self):
        self.assertFalse(Notification.objects.filter(task=self.t2).exists())
        self.assertFalse(Notification.objects.filter(task=self.t3).exists())
        self.assertTrue(Notification.objects.filter(task=self.t1, recipient=self.ryan).exists())

    def test_owner_gets_a_single_summary_when_someone_else_applies(self):
        summary = Notification.objects.filter(
            recipient=self.owner, event_type=Notification.EventType.PROCESS_APPLIED, activity=self.activity
        )
        self.assertEqual(summary.count(), 1)
        self.assertIn("3 tarefa(s)", summary.get().message)

    def test_released_task_can_now_be_started_and_finished_in_order(self):
        TaskService.complete(self.t1, self.ryan)
        TaskService.start(self.t2, self.vitor)
        TaskService.complete(self.t2, self.vitor)
        self.t3.refresh_from_db()
        self.assertEqual(self.t3.status, Task.Status.EM_FILA)
        self.assertEqual(self.active_queue(self.comercial).filter(task=self.t3).count(), 1)

    def test_cancelled_predecessor_does_not_release_the_dependent(self):
        TaskService.cancel(self.t1, self.owner, "Cliente desistiu")
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, Task.Status.DISPONIVEL)
        self.assertFalse(self.t2.queue_entries.exists())
        with self.assertRaisesMessage(ActivityError, "depende da conclusão"):
            TaskService.start(self.t2, self.vitor)

    def test_blocked_predecessor_does_not_release_the_dependent(self):
        TaskService.block(self.t1, self.ryan, "Falta o projeto")
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, Task.Status.DISPONIVEL)
        self.assertFalse(self.t2.queue_entries.exists())

    def test_returned_predecessor_does_not_release_the_dependent(self):
        from .models import ReturnReason

        reason = ReturnReason.objects.create(organization=self.org, name="Incompleta")
        grant_action(self.ryan, catalog.TAREFA_DEVOLVER, organization=self.org)
        TaskService.return_task(self.t1, self.compras, reason, self.ryan)
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, Task.Status.DISPONIVEL)
        self.assertFalse(self.t2.queue_entries.exists())

    def test_unblocking_then_completing_the_predecessor_still_releases(self):
        TaskService.block(self.t1, self.ryan, "Falta o projeto")
        TaskService.unblock(self.t1, self.ryan)
        TaskService.complete(self.t1, self.ryan)
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, Task.Status.EM_FILA)

    def test_release_is_idempotent(self):
        TaskService.complete(self.t1, self.ryan)
        TaskService._release_dependents(self.t1, self.ryan)
        self.assertEqual(self.t2.queue_entries.count(), 1)
        self.assertEqual(AuditLog.objects.filter(task=self.t2, action=AuditLog.Action.TASK_RELEASED).count(), 1)

    def test_nothing_is_released_into_a_cancelled_activity(self):
        Activity.objects.filter(pk=self.activity.pk).update(status=Activity.Status.CANCELADA)
        TaskService.complete(self.t1, self.ryan)
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, Task.Status.DISPONIVEL)
        self.assertFalse(self.t2.queue_entries.exists())

    def test_removing_the_dependency_of_a_waiting_task_releases_it(self):
        TaskService.update_task(self.t2, self.owner, depends_on=None)
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, Task.Status.EM_FILA)
        self.assertEqual(self.active_queue(self.compras).filter(task=self.t2).count(), 1)

    def test_a_waiting_task_moved_to_another_sector_stays_out_of_the_queue(self):
        TaskService.move_to_sector(self.t2, self.comercial, self.owner)
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.sector, self.comercial)
        self.assertEqual(self.t2.status, Task.Status.DISPONIVEL)
        self.assertFalse(self.t2.queue_entries.exists())

    def test_a_waiting_task_cannot_be_returned(self):
        from .models import ReturnReason

        reason = ReturnReason.objects.create(organization=self.org, name="Incompleta")
        grant_action(self.vitor, catalog.TAREFA_DEVOLVER, organization=self.org)
        with self.assertRaisesMessage(ActivityError, "aguarda a etapa anterior"):
            TaskService.return_task(self.t2, self.comercial, reason, self.vitor)

    def test_unblocking_a_waiting_task_sends_it_back_to_waiting_not_to_the_queue(self):
        TaskService.block(self.t2, self.vitor, "Aguardando fornecedor")
        TaskService.unblock(self.t2, self.vitor)
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, Task.Status.DISPONIVEL)
        self.assertFalse(self.t2.queue_entries.exists())

    def test_waiting_property_and_status_label(self):
        self.t2 = Task.objects.select_related("depends_on", "activity__organization").get(pk=self.t2.pk)
        self.assertEqual(self.t2.waiting_for.pk, self.t1.pk)
        self.assertEqual(self.t2.status_label, "Aguardando etapa anterior")
        self.assertEqual(self.t2.status_color, "#607188")  # cinza legível, não o de "Disponível"
        self.t1.refresh_from_db()
        self.assertIsNone(self.t1.waiting_for)
        self.assertNotEqual(self.t1.status_label, "Aguardando etapa anterior")
        # depois de liberada, volta ao rótulo e à cor normais
        TaskService.complete(self.t1, self.ryan)
        self.t2.refresh_from_db()
        self.assertIsNone(self.t2.waiting_for)
        self.assertNotEqual(self.t2.status_label, "Aguardando etapa anterior")

    def test_manual_task_with_manual_dependency_is_also_guarded(self):
        manual = Task.objects.create(
            activity=self.activity, sector=self.comercial, title="Manual", created_by=self.owner,
            responsavel=self.ryan, depends_on=self.t1, status=Task.Status.EM_FILA,
        )
        with self.assertRaisesMessage(ActivityError, "depende da conclusão"):
            TaskService.start(manual, self.ryan)


# ---------------------------------------------------------------------------
# Inputs e critérios durante a execução
# ---------------------------------------------------------------------------


class InputAndCriterionTests(ProcessTestCase):
    def setUp(self):
        super().setUp()
        types = ProcessInput.InputType
        self.version = self.new_process(
            name="Tipos",
            inputs=[
                {"name": "Descrição", "type": types.TEXTO, "required": True},
                {"name": "Data limite", "type": types.DATA, "required": False},
                {"name": "Valor", "type": types.NUMERO, "required": False},
                {"name": "Site", "type": types.LINK, "required": False},
                {"name": "Planta", "type": types.ARQUIVO, "required": False},
                {"name": "Modelo", "type": types.SELECAO, "required": False},
            ],
        )
        self.apply()
        self.row = {r.process_input.name: r for r in ActivityInputValue.objects.filter(activity=self.activity)}

    def update(self, name, value="", received=False, user=None):
        return ActivityProcessService.update_input(user or self.owner, self.row[name], value=value, is_received=received)

    def test_text_input_is_received_when_it_has_a_value(self):
        updated = self.update("Descrição", "  Memorial descritivo  ")
        self.assertTrue(updated.is_received)
        self.assertEqual(updated.value, "Memorial descritivo")
        self.assertEqual(updated.received_by, self.owner)
        self.assertIsNotNone(updated.received_at)

    def test_empty_value_reopens_the_input(self):
        self.update("Descrição", "algo")
        reopened = self.update("Descrição", "")
        self.assertFalse(reopened.is_received)
        self.assertIsNone(reopened.received_at)
        self.assertIsNone(reopened.received_by)

    def test_typed_values_are_validated_and_normalized(self):
        self.assertEqual(self.update("Data limite", "2026-10-15").value, "2026-10-15")
        self.assertEqual(self.update("Valor", "1500,5").value, "1500.5")
        self.assertEqual(self.update("Site", "https://biasi.com.br/obra").value, "https://biasi.com.br/obra")
        for name, bad in (("Data limite", "31/12/2026"), ("Valor", "mil"), ("Site", "javascript:alert(1)"), ("Site", "biasi")):
            with self.assertRaises(ActivityError, msg=f"{name}={bad}"):
                self.update(name, bad)

    def test_file_and_selection_inputs_only_confirm_receipt_with_a_free_note(self):
        planta = self.update("Planta", "Está na pasta da obra", received=True)
        self.assertTrue(planta.is_received)
        self.assertEqual(planta.value, "Está na pasta da obra")
        self.assertFalse(self.update("Modelo", "", received=False).is_received)
        # não interpreta o texto como id de arquivo nem valida opções inexistentes
        self.assertTrue(self.update("Modelo", "Opção B", received=True).is_received)

    def test_normalize_helper_matches_service_behaviour(self):
        item = ProcessInput(name="Valor", input_type=ProcessInput.InputType.NUMERO)
        self.assertEqual(normalize_input_value(item, "10,25"), ("10.25", True))
        self.assertEqual(normalize_input_value(item, "  "), ("", False))
        with self.assertRaises(ActivityError):
            normalize_input_value(item, "NaN")

    def test_every_change_is_audited_with_before_and_after(self):
        self.update("Descrição", "v1")
        self.update("Descrição", "v2")
        self.update("Descrição", "")
        logs = list(
            AuditLog.objects.filter(activity=self.activity, action=AuditLog.Action.INPUT_UPDATED, field_name="Descrição")
            .order_by("pk")
        )
        self.assertEqual([(l.old_value, l.new_value) for l in logs], [
            ("não recebido", "recebido: v1"),
            ("recebido: v1", "recebido: v2"),
            ("recebido: v2", "não recebido"),
        ])
        self.assertTrue(all(l.user == self.owner for l in logs))

    def test_unchanged_input_writes_no_audit(self):
        self.update("Descrição", "v1")
        before = AuditLog.objects.filter(action=AuditLog.Action.INPUT_UPDATED).count()
        self.update("Descrição", "v1")
        self.assertEqual(AuditLog.objects.filter(action=AuditLog.Action.INPUT_UPDATED).count(), before)

    def test_who_can_update_inputs_and_criteria(self):
        self.assertFalse(ActivityProcessService.can_update(self.stranger, self.activity))
        self.assertFalse(ActivityProcessService.can_update(self.foreign, self.activity))
        self.assertTrue(ActivityProcessService.can_update(self.owner, self.activity))
        # responsável por uma tarefa da atividade também pode
        self.assertTrue(ActivityProcessService.can_update(self.ryan, self.activity))
        grant_action(self.stranger, catalog.ATIVIDADE_EDITAR, organization=self.org)
        self.assertTrue(ActivityProcessService.can_update(self.stranger, self.activity))

    def test_stranger_cannot_update_input_or_criterion(self):
        with self.assertRaisesMessage(ActivityError, "permissão"):
            self.update("Descrição", "x", user=self.stranger)
        check = ActivityCriterionCheck.objects.filter(activity=self.activity).first()
        if check is not None:
            with self.assertRaises(ActivityError):
                ActivityProcessService.set_criterion(self.stranger, check, True)

    def test_closed_activity_rejects_changes(self):
        self.receive_all_required_inputs()
        for task in self.tasks():
            Task.objects.filter(pk=task.pk).update(status=Task.Status.CONCLUIDA)
        Activity.objects.filter(pk=self.activity.pk).update(status=Activity.Status.CONCLUIDA)
        with self.assertRaisesMessage(ActivityError, "finalizada"):
            self.update("Descrição", "tarde demais")


class CriteriaTests(ProcessTestCase):
    def setUp(self):
        super().setUp()
        self.apply()
        self.checks = {c.process_criterion.name: c for c in ActivityCriterionCheck.objects.filter(activity=self.activity)}

    def test_set_and_unset_a_criterion_records_who_and_when(self):
        check = ActivityProcessService.set_criterion(self.owner, self.checks["Escopo revisado"], True)
        self.assertTrue(check.is_met)
        self.assertEqual(check.met_by, self.owner)
        self.assertIsNotNone(check.met_at)
        check = ActivityProcessService.set_criterion(self.owner, check, False)
        self.assertFalse(check.is_met)
        self.assertIsNone(check.met_by)
        self.assertIsNone(check.met_at)

    def test_criterion_changes_are_audited_including_reopening(self):
        check = self.checks["Escopo revisado"]
        ActivityProcessService.set_criterion(self.owner, check, True)
        ActivityProcessService.set_criterion(self.owner, check, True)  # sem mudança: sem log
        ActivityProcessService.set_criterion(self.owner, check, False)
        logs = list(
            AuditLog.objects.filter(activity=self.activity, action=AuditLog.Action.CRITERION_UPDATED).order_by("pk")
        )
        self.assertEqual([(l.field_name, l.old_value, l.new_value) for l in logs], [
            ("Escopo revisado", "pendente", "atendido"),
            ("Escopo revisado", "atendido", "pendente"),
        ])

    def test_the_process_template_is_not_touched_by_execution(self):
        criterion = self.checks["Escopo revisado"].process_criterion
        ActivityProcessService.set_criterion(self.owner, self.checks["Escopo revisado"], True)
        criterion.refresh_from_db()
        self.assertTrue(criterion.is_required)
        self.assertEqual(criterion.name, "Escopo revisado")

    def test_criteria_of_one_activity_are_independent_of_another_using_the_same_version(self):
        other = self.new_activity(title="Segunda")
        self.apply(activity=other)
        ActivityProcessService.set_criterion(self.owner, self.checks["Escopo revisado"], True)
        other_check = ActivityCriterionCheck.objects.get(activity=other, process_criterion__name="Escopo revisado")
        self.assertFalse(other_check.is_met)


# ---------------------------------------------------------------------------
# Inputs obrigatórios seguram o início das tarefas do processo
# ---------------------------------------------------------------------------


class RequiredInputGateTests(ProcessTestCase):
    def setUp(self):
        super().setUp()
        self.apply()
        self.t1, self.t2, self.t3 = self.tasks()

    def test_apply_is_allowed_with_required_inputs_missing_but_tasks_cannot_start(self):
        self.assertEqual(self.t1.status, Task.Status.EM_FILA)
        with self.assertRaisesMessage(ActivityError, "Projetos; Memorial"):
            TaskService.start(self.t1, self.ryan)
        with self.assertRaisesMessage(ActivityError, "Projetos; Memorial"):
            TaskService.complete(self.t1, self.ryan)

    def test_partial_receipt_still_blocks_and_names_only_what_is_missing(self):
        row = ActivityInputValue.objects.get(activity=self.activity, process_input__name="Projetos")
        ActivityProcessService.update_input(self.owner, row, value="Projeto rev. A")
        with self.assertRaisesMessage(ActivityError, "Memorial"):
            TaskService.start(self.t1, self.ryan)

    def test_optional_input_missing_never_blocks(self):
        self.receive_all_required_inputs()
        TaskService.start(self.t1, self.ryan)
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.status, Task.Status.EM_EXECUCAO)

    def test_reopening_a_required_input_blocks_again(self):
        self.receive_all_required_inputs()
        row = ActivityInputValue.objects.get(activity=self.activity, process_input__name="Projetos")
        ActivityProcessService.update_input(self.owner, row, value="")
        with self.assertRaises(ActivityError):
            TaskService.start(self.t1, self.ryan)

    def test_manual_task_of_a_process_activity_is_not_gated(self):
        manual = Task.objects.create(
            activity=self.activity, sector=self.comercial, title="Extra", created_by=self.owner,
            responsavel=self.ryan, status=Task.Status.EM_FILA,
        )
        TaskService.start(manual, self.ryan)


# ---------------------------------------------------------------------------
# Integridade: atomicidade, reaplicação, versões, isolamento
# ---------------------------------------------------------------------------


class IntegrityTests(ProcessTestCase):
    def test_apply_is_atomic_when_a_late_step_fails(self):
        real = TaskService._create_task_core
        calls = {"n": 0}

        def flaky(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 3:
                raise RuntimeError("falha na etapa 3")
            return real(*args, **kwargs)

        with mock.patch.object(TaskService, "_create_task_core", staticmethod(flaky)):
            with self.assertRaises(RuntimeError):
                self.apply()

        self.assertEqual(calls["n"], 3)
        self.activity.refresh_from_db()
        self.assertIsNone(self.activity.process_version_id)
        self.assertFalse(self.activity.tasks.exists())
        self.assertFalse(QueueEntry.objects.exists())
        self.assertFalse(ActivityInputValue.objects.filter(activity=self.activity).exists())
        self.assertFalse(ActivityCriterionCheck.objects.filter(activity=self.activity).exists())
        self.assertFalse(AuditLog.objects.filter(action=AuditLog.Action.PROCESS_APPLIED).exists())
        self.assertFalse(AuditLog.objects.filter(action=AuditLog.Action.TASK_CREATED).exists())
        self.assertFalse(Notification.objects.filter(event_type=Notification.EventType.PROCESS_APPLIED).exists())

        # e a segunda tentativa, sem falha, funciona do zero
        self.apply()
        self.assertEqual(self.activity.tasks.count(), 3)

    def test_reapplying_never_duplicates_tasks(self):
        self.apply()
        for _ in range(2):
            with self.assertRaises(ActivityError):
                self.apply()
        self.assertEqual(self.activity.tasks.count(), 3)
        self.assertEqual(ActivityInputValue.objects.filter(activity=self.activity).count(), 3)
        self.assertEqual(ActivityCriterionCheck.objects.filter(activity=self.activity).count(), 4)

    def test_a_stale_copy_of_the_activity_cannot_apply_a_second_time(self):
        # "Duas abas": as duas carregaram a atividade ANTES de a primeira aplicar.
        tab_a = Activity.objects.get(pk=self.activity.pk)
        tab_b = Activity.objects.get(pk=self.activity.pk)
        self.apply(activity=tab_a)
        with self.assertRaisesMessage(ActivityError, "já tem um processo aplicado"):
            self.apply(activity=tab_b)
        self.assertEqual(self.activity.tasks.count(), 3)

    def test_database_constraint_is_the_last_line_of_defence(self):
        # Mesmo que a checagem em Python fosse contornada, o banco recusa a
        # segunda etapa duplicada e o serviço traduz o erro.
        self.apply()
        step = self.version.steps.first()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Task.objects.create(
                activity=self.activity, sector=step.sector, title="dup", created_by=self.owner,
                responsavel=self.ryan, process_step=step,
            )

    def test_integrity_error_inside_apply_becomes_a_friendly_error(self):
        def duplicate(*args, **kwargs):
            raise IntegrityError("unique_task_per_activity_process_step")

        with mock.patch.object(TaskService, "_create_task_core", staticmethod(duplicate)):
            with self.assertRaisesMessage(ActivityError, "já foi aplicado"):
                self.apply()
        self.activity.refresh_from_db()
        self.assertIsNone(self.activity.process_version_id)

    def test_new_version_of_the_process_never_changes_existing_activities(self):
        self.apply()
        self.receive_all_required_inputs()
        maker = make_user("editor", self.org, [catalog.PROCESSO_CRIAR_VERSAO, catalog.PROCESSO_EDITAR_RASCUNHO, catalog.PROCESSO_PUBLICAR])
        draft = ProcessService.create_new_version(self.version.process, maker)
        self.assertEqual(draft.number, 4)
        draft.steps.filter(order=3).delete()
        draft.criteria.all().delete()
        ProcessService.publish(draft, maker)

        self.activity.refresh_from_db()
        self.version.refresh_from_db()
        self.assertEqual(self.activity.process_version_id, self.version.pk)
        self.assertEqual(self.version.status, ProcessVersion.Status.SUBSTITUIDO)
        self.assertEqual(self.activity.tasks.count(), 3)
        self.assertEqual(ActivityCriterionCheck.objects.filter(activity=self.activity).count(), 4)
        self.assertEqual(ActivityInputValue.objects.filter(activity=self.activity).count(), 3)

        # atividades novas usam a versão nova; a antiga não é mais elegível
        fresh = self.new_activity(title="Nova")
        self.assertEqual([v.number for v in ProcessApplicationService.eligible_versions(fresh)], [4])
        self.apply(activity=fresh, version=draft, responsible_by_step={})
        self.assertEqual(fresh.tasks.count(), 2)

    def test_second_activity_with_the_same_version_gets_its_own_tasks(self):
        self.apply()
        other = self.new_activity(title="Segunda")
        self.apply(activity=other)
        self.assertEqual(Task.objects.filter(process_step__version=self.version).count(), 6)
        self.assertEqual(self.tasks(other)[0].process_step, self.tasks()[0].process_step)

    def test_tenant_isolation_holds_for_apply_inputs_and_criteria(self):
        self.apply()
        row = ActivityInputValue.objects.filter(activity=self.activity).first()
        check = ActivityCriterionCheck.objects.filter(activity=self.activity).first()
        with self.assertRaises(ActivityError):
            ActivityProcessService.update_input(self.foreign, row, value="x")
        with self.assertRaises(ActivityError):
            ActivityProcessService.set_criterion(self.foreign, check, True)
        row.refresh_from_db()
        check.refresh_from_db()
        self.assertFalse(row.is_received)
        self.assertFalse(check.is_met)


# ---------------------------------------------------------------------------
# Finalização e o cenário completo de aceite
# ---------------------------------------------------------------------------


class FinalizationTests(ProcessTestCase):
    def setUp(self):
        super().setUp()
        self.apply()
        self.receive_all_required_inputs()
        for task in self.tasks():
            Task.objects.filter(pk=task.pk).update(status=Task.Status.CONCLUIDA)
        self.checks = {c.process_criterion.name: c for c in ActivityCriterionCheck.objects.filter(activity=self.activity)}

    def finalize(self, outcome, comment="Encerrada"):
        return ActivityService.finalize(self.activity, self.owner, outcome, comment)

    def meet_required(self):
        for name in ("Escopo revisado", "Quantitativos conferidos", "Cotação revisada"):
            ActivityProcessService.set_criterion(self.owner, self.checks[name], True)

    def test_success_is_blocked_while_required_criteria_are_open_and_lists_them(self):
        with self.assertRaises(ActivityError) as ctx:
            self.finalize(Activity.CompletionOutcome.SUCESSO)
        message = str(ctx.exception)
        for name in ("Escopo revisado", "Quantitativos conferidos", "Cotação revisada"):
            self.assertIn(name, message)
        self.assertNotIn("Aprovação comercial", message)  # opcional não bloqueia
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.ABERTA)

    def test_partial_progress_lists_only_what_is_missing(self):
        ActivityProcessService.set_criterion(self.owner, self.checks["Escopo revisado"], True)
        with self.assertRaises(ActivityError) as ctx:
            self.finalize(Activity.CompletionOutcome.SUCESSO)
        self.assertNotIn("Escopo revisado", str(ctx.exception))
        self.assertIn("Cotação revisada", str(ctx.exception))

    def test_success_with_all_required_criteria_met_completes(self):
        self.meet_required()  # o critério opcional continua aberto
        self.finalize(Activity.CompletionOutcome.SUCESSO)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.CONCLUIDA)
        self.assertEqual(self.activity.completion_outcome, Activity.CompletionOutcome.SUCESSO)

    def test_completed_with_pendencies_is_allowed_and_records_what_was_left_open(self):
        self.finalize(Activity.CompletionOutcome.CONCLUIDO_COM_PENDENCIAS, "Cliente aceitou sem a revisão")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.CONCLUIDA)
        log = AuditLog.objects.filter(activity=self.activity, action=AuditLog.Action.COMPLETE).latest("pk")
        self.assertIn("Cliente aceitou sem a revisão", log.reason)
        self.assertIn("Escopo revisado", log.reason)
        self.assertIn("Cotação revisada", log.reason)
        self.assertTrue(
            self.activity.messages.filter(body__contains="Critérios de aceite obrigatórios não atendidos").exists()
        )

    def test_completed_with_pendencies_still_requires_a_comment(self):
        with self.assertRaisesMessage(ActivityError, "comentário"):
            self.finalize(Activity.CompletionOutcome.CONCLUIDO_COM_PENDENCIAS, "  ")

    def test_cancelling_and_declining_ignore_the_criteria(self):
        self.finalize(Activity.CompletionOutcome.CANCELADO, "Cliente desistiu")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.CANCELADA)

    def test_declining_ignores_the_criteria_too(self):
        self.finalize(Activity.CompletionOutcome.DECLINADO, "Fora do escopo")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.CANCELADA)

    def test_legacy_complete_endpoint_is_not_a_side_door(self):
        with self.assertRaisesMessage(ActivityError, "Falta atender"):
            ActivityService.complete_activity(self.activity, self.owner)
        self.meet_required()
        ActivityService.complete_activity(self.activity, self.owner)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.CONCLUIDA)

    def test_activity_without_process_is_unaffected(self):
        plain = self.new_activity(title="Simples")
        ActivityService.finalize(plain, self.owner, Activity.CompletionOutcome.SUCESSO, "Feito")
        plain.refresh_from_db()
        self.assertEqual(plain.status, Activity.Status.CONCLUIDA)


class AcceptanceScenarioTests(ProcessTestCase):
    """O exemplo do produto, do começo ao fim."""

    def test_orcamento_v3_from_apply_to_success(self):
        activity = self.new_activity(title="ATV-2026-00123")
        self.apply(activity=activity)

        activity.refresh_from_db()
        self.assertEqual(activity.process_version.process.name, "Orçamento")
        self.assertEqual(activity.process_version.number, 3)
        self.assertEqual(ActivityInputValue.objects.filter(activity=activity).count(), 3)
        self.assertEqual(ActivityCriterionCheck.objects.filter(activity=activity).count(), 4)
        t1, t2, t3 = self.tasks(activity)
        self.assertEqual(t1.status, Task.Status.EM_FILA)
        self.assertEqual((t2.status, t3.status), (Task.Status.DISPONIVEL, Task.Status.DISPONIVEL))
        self.assertFalse(self.active_queue(self.compras).exists())

        self.receive_all_required_inputs(activity)

        TaskService.complete(t1, self.ryan)  # Ryan conclui a 1
        t2.refresh_from_db()
        self.assertEqual(t2.status, Task.Status.EM_FILA)
        self.assertEqual(self.active_queue(self.compras).get().task, t2)  # entrou na fila de Compras

        TaskService.complete(t2, self.vitor)  # Vitor conclui a 2
        t3.refresh_from_db()
        self.assertEqual(t3.status, Task.Status.EM_FILA)
        self.assertEqual(self.active_queue(self.comercial).get().task, t3)  # entrou na do Comercial

        TaskService.complete(t3, self.paulo)  # Paulo conclui a 3

        for check in ActivityCriterionCheck.objects.filter(activity=activity, process_criterion__is_required=True):
            ActivityProcessService.set_criterion(self.owner, check, True)

        ActivityService.finalize(activity, self.owner, Activity.CompletionOutcome.SUCESSO, "Orçamento entregue")
        activity.refresh_from_db()
        self.assertEqual(activity.status, Activity.Status.CONCLUIDA)
        self.assertEqual(activity.process_version.number, 3)
