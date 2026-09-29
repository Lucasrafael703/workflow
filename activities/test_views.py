from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserSector
from acessos import catalog
from acessos.models import Scope
from acessos.testing import grant_action, grant_actions
from core.models import Organization, Sector

from .models import QueueEntry, ReturnReason, Task
from .services import ActivityService, TaskService

User = get_user_model()

# O mínimo para uma pessoa operar: criar o que é seu e enxergar o próprio
# trabalho. Nada além disso — o resto é concedido explicitamente em cada teste.
BASE_ACTIONS = [
    catalog.ATIVIDADE_CRIAR,
    catalog.ATIVIDADE_VISUALIZAR,
    catalog.TAREFA_CRIAR,
    catalog.TAREFA_VISUALIZAR,
    catalog.FILA_VISUALIZAR_POSICAO_PROPRIA,
]


class ViewTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Instaladora X")
        self.sector = Sector.objects.create(organization=self.org, name="Compras")

        self.member = self._user("membro", self.org)
        UserSector.objects.create(user=self.member, sector=self.sector)

        self.requester = self._user("solicitante", self.org)
        self.outsider = self._user("externo", self.other_org)

        self.activity = ActivityService.create_activity(
            organization=self.org,
            title="Material na obra",
            owner=self.requester,
            created_by=self.requester,
        )
        self.task = TaskService.create_task(
            self.activity, self.sector, "Realizar cotação", created_by=self.requester
        )

    def _user(self, username, organization, actions=BASE_ACTIONS):
        user = User.objects.create_user(username, password="x")
        user.profile.organization = organization
        user.profile.save()
        if actions:
            grant_actions(user, actions, organization=organization)
        return user


class OrganizationIsolationViewTests(ViewTestCase):
    def test_user_from_another_organization_cannot_open_activity(self):
        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(reverse("activity-detail", args=[self.activity.pk])).status_code, 404
        )

    def test_user_from_another_organization_cannot_open_task(self):
        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(reverse("task-detail", args=[self.task.pk])).status_code, 404
        )

    def test_activity_list_only_shows_own_organization(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("activity-list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Material na obra")

    def test_user_without_organization_is_redirected_to_profile(self):
        orphan = User.objects.create_user("sem-org", password="x")
        self.client.force_login(orphan)
        self.assertRedirects(self.client.get(reverse("home")), reverse("profile"))


class QueuePrivacyViewTests(ViewTestCase):
    """O solicitante vê a própria posição, nunca o conteúdo alheio (doc 05 §24)."""

    def setUp(self):
        super().setUp()
        secret_activity = ActivityService.create_activity(
            organization=self.org,
            title="Atividade do membro",
            owner=self.member,
            created_by=self.member,
        )
        self.secret_task = TaskService.create_task(
            secret_activity, self.sector, "TAREFA SIGILOSA", created_by=self.member
        )

    def test_full_queue_requires_the_action(self):
        """Participar do setor não basta: ver a fila inteira é ação autorizada.

        Testado contra a tarefa de outra pessoa — a própria demanda o usuário
        sempre enxerga, com posição e prazo.
        """
        self.client.force_login(self.member)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertNotContains(response, "Realizar cotação")

        grant_action(self.member, catalog.FILA_VISUALIZAR_COMPLETA, sector=self.sector)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertContains(response, "Realizar cotação")
        self.assertContains(response, "TAREFA SIGILOSA")

    def test_requester_never_sees_other_task_titles(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "TAREFA SIGILOSA")

    def test_requester_sees_own_position_and_live_total(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertContains(response, "Posição: 1 de 2")

    def test_position_total_is_recalculated_after_completion(self):
        grant_action(self.member, catalog.TAREFA_CONCLUIR, sector=self.sector)
        TaskService.complete(self.secret_task, self.member)

        self.client.force_login(self.requester)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertContains(response, "Posição: 1 de 1")

    def test_queue_permission_does_not_leak_across_sectors(self):
        """Autorização em um setor não vale no outro (doc 05 §19)."""
        other_sector = Sector.objects.create(organization=self.org, name="Engenharia")
        TaskService.create_task(
            self.activity, other_sector, "Tarefa de Engenharia", created_by=self.requester
        )
        grant_action(self.member, catalog.FILA_VISUALIZAR_COMPLETA, sector=self.sector)

        self.client.force_login(self.member)
        response = self.client.get(reverse("queue"), {"sector": other_sector.pk})
        self.assertNotContains(response, "Tarefa de Engenharia")


class QueueReorderViewTests(ViewTestCase):
    def test_reorder_requires_the_action(self):
        entry = QueueEntry.objects.get(task=self.task)
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("queue-reorder", args=[entry.pk]), {"new_position": 1}, follow=True
        )
        self.assertContains(response, "autorização")

    def test_reorder_with_the_action_succeeds(self):
        other = TaskService.create_task(
            self.activity, self.sector, "Segunda tarefa", created_by=self.requester
        )
        entry = QueueEntry.objects.get(task=other)
        grant_action(self.member, catalog.FILA_REORDENAR, sector=self.sector)
        self.client.force_login(self.member)

        self.client.post(reverse("queue-reorder", args=[entry.pk]), {"new_position": 1})

        entry.refresh_from_db()
        self.assertEqual(entry.position, 1)

    def test_reorder_granted_in_one_sector_does_not_apply_to_another(self):
        other_sector = Sector.objects.create(organization=self.org, name="Engenharia")
        other_task = TaskService.create_task(
            self.activity, other_sector, "Tarefa de Engenharia", created_by=self.requester
        )
        entry = QueueEntry.objects.get(task=other_task)
        grant_action(self.member, catalog.FILA_REORDENAR, sector=self.sector)

        self.client.force_login(self.member)
        response = self.client.post(
            reverse("queue-reorder", args=[entry.pk]), {"new_position": 1}, follow=True
        )
        self.assertContains(response, "autorização")


class ManagementViewTests(ViewTestCase):
    def test_management_requires_action(self):
        self.client.force_login(self.requester)
        self.assertEqual(self.client.get(reverse("management")).status_code, 403)

    def test_management_allowed_with_action(self):
        grant_action(self.member, catalog.METRICAS_VISUALIZAR, organization=self.org)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("management")).status_code, 200)


class TaskActionViewTests(ViewTestCase):
    def test_assume_requires_the_action(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("task-assume", args=[self.task.pk]), follow=True)
        self.assertContains(response, "autorização")

    def test_assume_then_start_flow(self):
        grant_actions(
            self.member,
            [catalog.TAREFA_ASSUMIR, catalog.TAREFA_INICIAR],
            sector=self.sector,
        )
        self.client.force_login(self.member)

        self.client.post(reverse("task-assume", args=[self.task.pk]))
        self.client.post(reverse("task-start", args=[self.task.pk]))

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_EXECUCAO)
        self.assertTrue(
            self.task.work_sessions.filter(user=self.member, ended_at__isnull=True).exists()
        )

    def test_non_executor_cannot_start_even_with_the_action(self):
        """Autorização não substitui regra de negócio (doc 05 §30, §212)."""
        grant_action(self.member, catalog.TAREFA_INICIAR, sector=self.sector)
        self.client.force_login(self.member)
        response = self.client.post(reverse("task-start", args=[self.task.pk]), follow=True)
        self.assertContains(response, "executores atribuídos")


class TaskAssignmentViewTests(ViewTestCase):
    """Atribuir a outra pessoa gera pendência de aceite; ela decide (doc 02 — novo)."""

    def _assign_member(self):
        grant_actions(self.requester, [catalog.TAREFA_ATRIBUIR], sector=self.sector)
        self.client.force_login(self.requester)
        self.client.post(
            reverse("task-executor-add", args=[self.task.pk]), {"user": self.member.pk}
        )
        return self.task.assignments.get(user=self.member)

    def test_assigning_another_person_does_not_create_executor_immediately(self):
        assignment = self._assign_member()
        self.assertEqual(assignment.status, "PENDENTE")
        self.assertFalse(self.task.executors.filter(user=self.member).exists())

    def test_member_accepts_assignment_and_becomes_executor(self):
        assignment = self._assign_member()
        grant_actions(self.member, [catalog.TAREFA_ACEITAR], sector=self.sector)
        self.client.force_login(self.member)

        self.client.post(
            reverse("task-assignment-accept", args=[self.task.pk, assignment.pk])
        )

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, "ACEITA")
        self.assertTrue(
            self.task.executors.filter(user=self.member, removed_at__isnull=True).exists()
        )

    def test_member_rejects_assignment_with_reason(self):
        assignment = self._assign_member()
        grant_actions(self.member, [catalog.TAREFA_RECUSAR], sector=self.sector)
        self.client.force_login(self.member)
        reason = ReturnReason.objects.create(organization=self.org, name="Fora da minha área")

        self.client.post(
            reverse("task-assignment-reject", args=[self.task.pk, assignment.pk]),
            {"reason": reason.pk, "observation": "Isso é do orçamentista, não meu."},
        )

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, "RECUSADA")
        self.assertEqual(assignment.reason, reason)
        self.assertFalse(self.task.executors.filter(user=self.member).exists())

    def test_someone_else_cannot_accept_another_persons_assignment(self):
        assignment = self._assign_member()
        third_party = self._user("terceiro", self.org)
        grant_actions(third_party, [catalog.TAREFA_ACEITAR], sector=self.sector)
        self.client.force_login(third_party)

        self.client.post(
            reverse("task-assignment-accept", args=[self.task.pk, assignment.pk]), follow=True
        )

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, "PENDENTE")


class TaskAuthorizationTests(ViewTestCase):
    """Nenhuma ação de tarefa fica aberta a qualquer usuário da organização."""

    def test_stranger_cannot_open_block_form(self):
        self.client.force_login(self.requester)
        self.assertEqual(
            self.client.get(reverse("task-block", args=[self.task.pk])).status_code, 403
        )

    def test_stranger_cannot_block_task(self):
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("task-block", args=[self.task.pk]), {"reason": "Invadido"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.task.blocks.count(), 0)

    def test_stranger_cannot_reach_other_task_actions(self):
        self.client.force_login(self.requester)
        for name in ("task-return", "task-move", "task-cancel", "task-manual-time"):
            self.assertEqual(
                self.client.get(reverse(name, args=[self.task.pk])).status_code, 403, msg=name
            )

    def test_stranger_cannot_post_task_message(self):
        self.client.force_login(self.requester)
        self.client.post(reverse("task-message", args=[self.task.pk]), {"body": "oi"})
        self.assertEqual(self.task.messages.count(), 0)

    def test_authorized_user_may_block(self):
        grant_action(self.member, catalog.TAREFA_BLOQUEAR, sector=self.sector)
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.get(reverse("task-block", args=[self.task.pk])).status_code, 200
        )

    def test_relational_scope_lets_the_owner_act_on_own_activity(self):
        """Escopo relacional "minhas atividades" (doc 05 §22)."""
        grant_action(
            self.requester,
            catalog.TAREFA_BLOQUEAR,
            organization=self.org,
            relation=Scope.Relation.MINHAS_ATIVIDADES,
        )
        self.client.force_login(self.requester)
        self.assertEqual(
            self.client.get(reverse("task-block", args=[self.task.pk])).status_code, 200
        )

    def test_relational_scope_does_not_reach_other_peoples_activities(self):
        other_activity = ActivityService.create_activity(
            organization=self.org, title="De outra pessoa", owner=self.member, created_by=self.member
        )
        other_task = TaskService.create_task(
            other_activity, self.sector, "Tarefa alheia", created_by=self.member
        )
        grant_action(
            self.requester,
            catalog.TAREFA_BLOQUEAR,
            organization=self.org,
            relation=Scope.Relation.MINHAS_ATIVIDADES,
        )
        self.client.force_login(self.requester)
        self.assertEqual(
            self.client.get(reverse("task-block", args=[other_task.pk])).status_code, 403
        )

    def test_manual_time_only_for_executors(self):
        grant_action(self.member, catalog.TEMPO_LANCAR_MANUAL, sector=self.sector)
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("task-manual-time", args=[self.task.pk]),
            {"started_at": "2026-09-01T08:00", "ended_at": "2026-09-01T09:00"},
        )
        self.assertContains(response, "executor da tarefa")
        self.assertEqual(self.task.work_sessions.count(), 0)


class ActivityAuthorizationTests(ViewTestCase):
    def test_stranger_cannot_complete_activity(self):
        stranger = self._user("estranho", self.org)
        self.client.force_login(stranger)
        self.client.post(reverse("activity-complete", args=[self.activity.pk]))
        self.activity.refresh_from_db()
        self.assertNotEqual(self.activity.status, "CONCLUIDA")

    def test_stranger_cannot_post_activity_message(self):
        stranger = self._user("estranho", self.org)
        self.client.force_login(stranger)
        self.client.post(reverse("activity-message", args=[self.activity.pk]), {"body": "oi"})
        self.assertEqual(self.activity.messages.count(), 0)

    def test_owner_with_the_action_can_complete(self):
        grant_action(self.requester, catalog.ATIVIDADE_CONCLUIR, organization=self.org)
        grant_action(self.requester, catalog.TAREFA_CANCELAR, sector=self.sector)
        TaskService.cancel(self.task, self.requester, reason="Não é mais necessária")

        self.client.force_login(self.requester)
        self.client.post(reverse("activity-complete", args=[self.activity.pk]))
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, "CONCLUIDA")


class CadastroAuthorizationTests(ViewTestCase):
    """Cadastro é ação administrativa: exige autorização explícita."""

    def test_plain_user_cannot_deactivate_sector(self):
        self.client.force_login(self.requester)
        response = self.client.post(reverse("cadastro-toggle", args=["setores", self.sector.pk]))
        self.assertEqual(response.status_code, 403)
        self.sector.refresh_from_db()
        self.assertTrue(self.sector.is_active)

    def test_plain_user_cannot_open_sector_form(self):
        self.client.force_login(self.requester)
        self.assertEqual(self.client.get(reverse("sector-create")).status_code, 403)

    def test_authorized_user_can_deactivate_sector(self):
        grant_action(self.member, catalog.SETOR_INATIVAR, organization=self.org)
        self.client.force_login(self.member)
        response = self.client.post(reverse("cadastro-toggle", args=["setores", self.sector.pk]))
        self.assertEqual(response.status_code, 302)
        self.sector.refresh_from_db()
        self.assertFalse(self.sector.is_active)


class ActivityCreateViewTests(ViewTestCase):
    def test_create_activity_through_the_screen(self):
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("activity-create"),
            {"title": "Orçamento entregue ao cliente", "owner": self.requester.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.org.activities.filter(title="Orçamento entregue ao cliente").exists()
        )

    def test_owner_choices_are_limited_to_the_organization(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("activity-create"))
        owners = response.context["form"].fields["owner"].queryset
        self.assertIn(self.member, owners)

    def test_deadline_with_date_only_defaults_to_end_of_day(self):
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("activity-create"),
            {
                "title": "Prazo sem hora",
                "owner": self.requester.pk,
                "requested_deadline_0": "2026-12-25",
                "requested_deadline_1": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        activity = self.org.activities.get(title="Prazo sem hora")
        from django.utils import timezone

        local = timezone.localtime(activity.requested_deadline)
        self.assertEqual((local.hour, local.minute), (23, 59))

    def test_deadline_with_date_and_time_keeps_exact_time(self):
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("activity-create"),
            {
                "title": "Prazo com hora",
                "owner": self.requester.pk,
                "requested_deadline_0": "2026-12-25",
                "requested_deadline_1": "14:30",
            },
        )
        self.assertEqual(response.status_code, 302)
        activity = self.org.activities.get(title="Prazo com hora")
        from django.utils import timezone

        local = timezone.localtime(activity.requested_deadline)
        self.assertEqual((local.hour, local.minute), (14, 30))

    def test_deadline_left_blank_stays_none(self):
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("activity-create"),
            {
                "title": "Sem prazo",
                "owner": self.requester.pk,
                "requested_deadline_0": "",
                "requested_deadline_1": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        activity = self.org.activities.get(title="Sem prazo")
        self.assertIsNone(activity.requested_deadline)

    def test_sector_label_is_setor_responsavel(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("activity-create"))
        self.assertEqual(response.context["form"].fields["sector"].label, "Setor Responsável")


class SearchViewTests(ViewTestCase):
    """Endpoints de busca por nome usados pelos pickers de Setor/Empresa/
    Obra/Centro de custo no formulário de atividade — mesmo contrato JSON
    de `ClientSearchView`, escopado por organização."""

    def test_sector_search_filters_by_name_and_organization(self):
        from core.models import Sector

        Sector.objects.create(organization=self.other_org, name="Compras")
        self.client.force_login(self.requester)
        response = self.client.get(reverse("sector-search"), {"q": "Comp"})
        self.assertEqual(response.status_code, 200)
        names = [r["name"] for r in response.json()["results"]]
        self.assertIn(self.sector.name, names)
        self.assertEqual(len(names), 1)

    def test_company_search_returns_results(self):
        from core.models import Company

        Company.objects.create(organization=self.org, name="Biasi Engenharia")
        self.client.force_login(self.requester)
        response = self.client.get(reverse("company-search"), {"q": "Biasi"})
        self.assertEqual(response.status_code, 200)
        names = [r["name"] for r in response.json()["results"]]
        self.assertIn("Biasi Engenharia", names)

    def test_site_search_returns_results(self):
        from core.models import Site

        Site.objects.create(organization=self.org, name="Capão Redondo")
        self.client.force_login(self.requester)
        response = self.client.get(reverse("site-search"), {"q": "Capão"})
        self.assertEqual(response.status_code, 200)
        names = [r["name"] for r in response.json()["results"]]
        self.assertIn("Capão Redondo", names)

    def test_cost_center_search_returns_results(self):
        from core.models import CostCenter

        CostCenter.objects.create(organization=self.org, name="Obra 123")
        self.client.force_login(self.requester)
        response = self.client.get(reverse("costcenter-search"), {"q": "Obra"})
        self.assertEqual(response.status_code, 200)
        names = [r["name"] for r in response.json()["results"]]
        self.assertIn("Obra 123", names)


class ActivityKanbanAndCalendarViewTests(ViewTestCase):
    """Kanban e Calendário de atividades espelham a Lista: mesmo filtro,
    mesma organização, e o drag-and-drop do Kanban nunca toca
    Activity.status (só Activity.stage), igual ao já garantido para Task."""

    def setUp(self):
        super().setUp()
        from core.models import ActivityStage

        self.stage = ActivityStage.objects.create(
            organization=self.org, name="Em análise", order=1, color="#3B82F6", created_by=self.requester
        )

    def test_kanban_shows_stage_columns_and_unassigned_activities(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("activity-kanban"))
        self.assertEqual(response.status_code, 200)
        stages = [column["stage"] for column in response.context["columns"]]
        self.assertIn(self.stage, stages)
        unassigned_ids = [a.pk for a in response.context["unassigned_column"]["activities"]]
        self.assertIn(self.activity.pk, unassigned_ids)

    def test_calendar_returns_ok_with_week_grid(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("activity-calendar"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("weeks", response.context)
        self.assertTrue(len(response.context["weeks"]) > 0)

    def test_move_stage_updates_stage_only_never_status(self):
        self.client.force_login(self.requester)
        original_status = self.activity.status
        response = self.client.post(
            reverse("activity-move-stage", args=[self.activity.pk]),
            {"stage_id": self.stage.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.stage_id, self.stage.pk)
        self.assertIsNotNone(self.activity.stage_changed_at)
        self.assertEqual(self.activity.status, original_status)

    def test_move_stage_to_unassigned_clears_stage(self):
        self.activity.stage = self.stage
        self.activity.save(update_fields=["stage"])
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("activity-move-stage", args=[self.activity.pk]),
            {"stage_id": ""},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.activity.refresh_from_db()
        self.assertIsNone(self.activity.stage_id)

    def test_move_stage_rejects_stage_from_another_organization(self):
        from core.models import ActivityStage

        other_stage = ActivityStage.objects.create(
            organization=self.other_org, name="Externo", order=1, created_by=self.outsider
        )
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("activity-move-stage", args=[self.activity.pk]),
            {"stage_id": other_stage.pk},
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_move_activity_from_another_organization(self):
        from activities.services import ActivityService

        foreign_activity = ActivityService.create_activity(
            organization=self.other_org, title="Fora", owner=self.outsider, created_by=self.outsider
        )
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("activity-move-stage", args=[foreign_activity.pk]),
            {"stage_id": self.stage.pk},
        )
        self.assertEqual(response.status_code, 404)


class ActivityWizardViewTests(ViewTestCase):
    """Wizard de 3 etapas: cada etapa só aceita o próprio rascunho
    (status=RASCUNHO, created_by=quem está logado), e um rascunho nunca
    aparece nas telas normais (Lista/Kanban/Calendário/Home/Detalhe)."""

    def _create_draft(self, user=None):
        from activities.services import ActivityService

        return ActivityService.save_draft(
            organization=self.org, created_by=user or self.requester, activity=None
        )

    def test_step1_post_creates_a_real_draft_row(self):
        self.client.force_login(self.requester)
        response = self.client.post(reverse("activity-create"), {"acao": "continuar", "urgency": "MEDIA"})
        self.assertEqual(response.status_code, 302)
        from activities.models import Activity

        draft = Activity.objects.filter(organization=self.org, status=Activity.Status.RASCUNHO).first()
        self.assertIsNotNone(draft)
        self.assertEqual(draft.title, Activity.DRAFT_TITLE_PLACEHOLDER)

    def test_step2_rejects_draft_from_another_user(self):
        draft = self._create_draft(user=self.member)
        self.client.force_login(self.requester)
        response = self.client.get(reverse("activity-wizard-contexto", args=[draft.pk]))
        self.assertEqual(response.status_code, 404)

    def test_step3_rejects_a_non_draft_activity(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("activity-wizard-detalhes", args=[self.activity.pk]))
        self.assertEqual(response.status_code, 404)

    def test_step3_publish_requires_title_and_owner(self):
        draft = self._create_draft()
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("activity-wizard-detalhes", args=[draft.pk]),
            {"acao": "publicar", "description": "", "internal_notes": ""},
        )
        self.assertEqual(response.status_code, 200)
        draft.refresh_from_db()
        self.assertEqual(draft.status, "RASCUNHO")

    def test_step3_publish_succeeds_with_title_and_owner(self):
        from activities.services import ActivityService

        draft = self._create_draft()
        draft = ActivityService.save_draft(
            organization=self.org, created_by=self.requester, activity=draft,
            title="Visita técnica", owner=self.requester,
        )
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("activity-wizard-detalhes", args=[draft.pk]),
            {"acao": "publicar", "description": "", "internal_notes": ""},
        )
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.status, "ABERTA")

    def test_draft_never_appears_in_activity_list(self):
        draft = self._create_draft()
        draft.title = "Rascunho invisivel"
        draft.save(update_fields=["title"])
        self.client.force_login(self.requester)
        response = self.client.get(reverse("activity-list"))
        self.assertNotContains(response, "Rascunho invisivel")

    def test_draft_detail_redirects_to_wizard(self):
        draft = self._create_draft()
        self.client.force_login(self.requester)
        response = self.client.get(reverse("activity-detail", args=[draft.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("activity-create"), response.url)

    def test_discard_view_removes_draft(self):
        draft = self._create_draft()
        self.client.force_login(self.requester)
        response = self.client.post(reverse("activity-wizard-discard", args=[draft.pk]))
        self.assertEqual(response.status_code, 302)
        from activities.models import Activity

        self.assertFalse(Activity.objects.filter(pk=draft.pk).exists())
