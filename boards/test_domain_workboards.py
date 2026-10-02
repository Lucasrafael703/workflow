from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from acessos import catalog
from acessos.testing import grant_actions
from activities.models import Activity, Task
from activities.services import ActivityService, TaskService
from audit.models import AuditLog
from core.models import Organization, Sector

from .domain_defaults import ensure_domain_board
from .domain_services import DomainBoardMutationService
from .models import DomainBoard


User = get_user_model()


class DomainWorkBoardTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Outra")
        self.sector = Sector.objects.create(organization=self.org, name="Comercial")
        self.user = User.objects.create_user("paulo", password="x")
        self.user.profile.organization = self.org
        self.user.profile.save(update_fields=["organization"])
        grant_actions(
            self.user,
            [
                catalog.ATIVIDADE_CRIAR, catalog.ATIVIDADE_VISUALIZAR, catalog.ATIVIDADE_EDITAR,
                catalog.TAREFA_CRIAR, catalog.TAREFA_VISUALIZAR, catalog.TAREFA_EDITAR,
                catalog.PRAZO_ALTERAR_SOLICITADO,
            ],
            organization=self.org,
        )
        self.activity = ActivityService.create_activity(
            self.org, "Conferir proposta", self.user, self.user, sector=self.sector
        )
        self.task = TaskService.create_task(
            self.activity, self.sector, "Revisar escopo", self.user, self.user
        )

    def test_default_boards_are_idempotent_and_keep_domain_entities(self):
        demand = ensure_domain_board(self.org, DomainBoard.Domain.DEMAND)
        same = ensure_domain_board(self.org, DomainBoard.Domain.DEMAND)
        task = ensure_domain_board(self.org, DomainBoard.Domain.TASK)
        self.assertEqual(demand.pk, same.pk)
        self.assertEqual(demand.fields.count(), 8)
        self.assertEqual(task.views.count(), 3)
        self.assertEqual(Activity.objects.count(), 1)
        self.assertEqual(Task.objects.count(), 1)

    def test_inline_title_uses_domain_service_and_audits(self):
        board = ensure_domain_board(self.org, DomainBoard.Domain.DEMAND)
        field = board.fields.get(key="title")
        DomainBoardMutationService.set_value(board, field, self.activity, "Proposta revisada", self.user)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.title, "Proposta revisada")
        self.assertTrue(AuditLog.objects.filter(activity=self.activity, field_name="title").exists())

    def test_task_priority_is_saved_without_bypassing_audit(self):
        board = ensure_domain_board(self.org, DomainBoard.Domain.TASK)
        field = board.fields.get(key="priority")
        DomainBoardMutationService.set_value(board, field, self.task, "ALTA", self.user)
        self.task.refresh_from_db()
        self.assertEqual(self.task.priority, Task.Priority.ALTA)
        self.assertTrue(AuditLog.objects.filter(task=self.task, field_name="prioridade").exists())

    def test_primary_routes_render_the_new_views(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("activity-list"))
        self.assertContains(response, "Sob minha responsabilidade")
        self.assertContains(response, "Criar demanda")
        self.assertContains(response, "Conferir proposta")
        response = self.client.get(reverse("activity-kanban"))
        self.assertContains(response, "Quadro por etapas")
        self.assertContains(response, "Sem estágio")
        # Tarefas agora é a entrada única que escolhe uma Demanda e abre o quadro próprio dela.
        response = self.client.get(reverse("task-kanban"))
        self.assertContains(response, "Selecione uma Demanda")
        self.assertContains(response, "Conferir proposta")

    def test_value_endpoint_rejects_item_from_another_organization(self):
        other_sector = Sector.objects.create(organization=self.other_org, name="Financeiro")
        other_user = User.objects.create_user("outro", password="x")
        other_user.profile.organization = self.other_org
        other_user.profile.save(update_fields=["organization"])
        grant_actions(other_user, [catalog.ATIVIDADE_CRIAR], organization=self.other_org)
        other = ActivityService.create_activity(self.other_org, "Segredo", other_user, other_user, sector=other_sector)
        board = ensure_domain_board(self.org, DomainBoard.Domain.DEMAND)
        field = board.fields.get(key="title")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("workboard-value", args=[board.pk, field.pk, other.pk]),
            data='{"value":"vazamento"}', content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
