import json
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from acessos.testing import grant_actions
from activities.models import Activity, Task
from activities.services import ActivityService, TaskService
from audit.models import AuditLog
from core.models import ActivityStage, Organization, Sector, WorkflowStatus

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
        # Tarefas tem sua própria visão operacional de Kanban.
        response = self.client.get(reverse("task-kanban"))
        self.assertContains(response, "Tarefas por estado")
        self.assertContains(response, "Conferir proposta")

    def test_demand_kanban_uses_the_interactive_board_and_keeps_empty_stages(self):
        first = ActivityStage.objects.create(
            organization=self.org, sector=self.sector, name="Triagem", order=1, color="#0EA5E9"
        )
        ActivityStage.objects.create(
            organization=self.org, sector=self.sector, name="Revisão", order=2, color="#22C55E"
        )
        self.activity.stage = first
        self.activity.save(update_fields=["stage"])
        grant_actions(self.user, [catalog.ATIVIDADE_MOVER_ESTAGIO], organization=self.org)

        self.client.force_login(self.user)
        response = self.client.get(reverse("activity-kanban"))

        self.assertContains(response, 'data-work-board')
        self.assertContains(response, 'data-work-card')
        self.assertContains(response, 'draggable="true"')
        self.assertContains(response, "Adicionar demanda")
        self.assertContains(response, 'data-work-group-field')
        self.assertContains(response, "Triagem")
        self.assertContains(response, "Revisão")

    def test_kanban_settings_persist_empty_lanes_and_card_field_labels(self):
        board = ensure_domain_board(self.org, DomainBoard.Domain.DEMAND)
        view = board.views.get(type="KANBAN")
        grant_actions(self.user, [catalog.QUADRO_GERIR_COLUNAS], organization=self.org)
        self.client.force_login(self.user)
        page = self.client.get(reverse("activity-kanban"))
        self.assertContains(page, "Configurar cartões")
        self.assertContains(page, 'data-work-card-settings-form')

        response = self.client.post(
            reverse("workboard-view-settings", args=[view.pk]),
            data=json.dumps({"show_empty": False, "show_field_names": False}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        view.refresh_from_db()
        self.assertFalse(view.settings["show_empty"])
        self.assertFalse(view.settings["show_field_names"])

    def test_dragging_a_demand_card_uses_the_stage_service(self):
        initial = ActivityStage.objects.create(
            organization=self.org, sector=self.sector, name="Triagem", order=1
        )
        destination = ActivityStage.objects.create(
            organization=self.org, sector=self.sector, name="Em revisão", order=2
        )
        self.activity.stage = initial
        self.activity.save(update_fields=["stage"])
        grant_actions(self.user, [catalog.ATIVIDADE_MOVER_ESTAGIO], organization=self.org)
        board = ensure_domain_board(self.org, DomainBoard.Domain.DEMAND)
        field = board.fields.get(key="stage")
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("workboard-value", args=[board.pk, field.pk, self.activity.pk]),
            data=json.dumps({"value": destination.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.stage, destination)

    def test_status_grouping_persists_and_uses_the_condition_field(self):
        first = WorkflowStatus.objects.create(
            organization=self.org,
            sector=self.sector,
            domain=WorkflowStatus.Domain.ACTIVITY,
            name="Aguardando cliente",
            order=1,
        )
        WorkflowStatus.objects.create(
            organization=self.org,
            sector=self.sector,
            domain=WorkflowStatus.Domain.ACTIVITY,
            name="Em revisão",
            order=2,
        )
        self.activity.condition = first
        self.activity.save(update_fields=["condition"])
        board = ensure_domain_board(self.org, DomainBoard.Domain.DEMAND)
        view = board.views.get(type="KANBAN")
        condition_field = board.fields.get(key="condition")
        grant_actions(self.user, [catalog.QUADRO_GERIR_COLUNAS], organization=self.org)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("workboard-view-settings", args=[view.pk]),
            data=json.dumps({"group_by": "condition"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        view.refresh_from_db()
        self.assertEqual(view.settings["group_by"], "condition")
        page = self.client.get(reverse("activity-kanban"))
        self.assertContains(page, f'data-work-group-field="{condition_field.pk}"')
        self.assertContains(page, "Aguardando cliente")
        self.assertContains(page, "Em revisão")

    def test_dragging_a_status_grouped_card_uses_the_condition_service(self):
        initial = WorkflowStatus.objects.create(
            organization=self.org,
            sector=self.sector,
            domain=WorkflowStatus.Domain.ACTIVITY,
            name="Aguardando cliente",
            order=1,
        )
        destination = WorkflowStatus.objects.create(
            organization=self.org,
            sector=self.sector,
            domain=WorkflowStatus.Domain.ACTIVITY,
            name="Aprovada",
            order=2,
        )
        self.activity.condition = initial
        self.activity.save(update_fields=["condition"])
        board = ensure_domain_board(self.org, DomainBoard.Domain.DEMAND)
        view = board.views.get(type="KANBAN")
        field = board.fields.get(key="condition")
        grant_actions(
            self.user,
            [catalog.QUADRO_GERIR_COLUNAS, catalog.ATIVIDADE_DEFINIR_CONDICAO],
            organization=self.org,
        )
        self.client.force_login(self.user)
        self.client.post(
            reverse("workboard-view-settings", args=[view.pk]),
            data=json.dumps({"group_by": "condition"}),
            content_type="application/json",
        )

        page = self.client.get(reverse("activity-kanban"))
        self.assertContains(page, 'draggable="true"')
        response = self.client.post(
            reverse("workboard-value", args=[board.pk, field.pk, self.activity.pk]),
            data=json.dumps({"value": destination.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.condition, destination)

    def test_invalid_kanban_grouping_is_rejected(self):
        board = ensure_domain_board(self.org, DomainBoard.Domain.DEMAND)
        view = board.views.get(type="KANBAN")
        grant_actions(self.user, [catalog.QUADRO_GERIR_COLUNAS], organization=self.org)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("workboard-view-settings", args=[view.pk]),
            data=json.dumps({"group_by": "inexistente"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

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


class DemandFilterToolbarTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.commercial = Sector.objects.create(organization=self.org, name="Comercial")
        self.finance = Sector.objects.create(organization=self.org, name="Financeiro")
        self.user = User.objects.create_user("paulo", password="x", first_name="Paulo")
        self.other = User.objects.create_user("ana", password="x", first_name="Ana")
        for person in (self.user, self.other):
            person.profile.organization = self.org
            person.profile.save(update_fields=["organization"])
        grant_actions(
            self.user,
            [catalog.ATIVIDADE_CRIAR, catalog.ATIVIDADE_VISUALIZAR, catalog.ATIVIDADE_VISUALIZAR_TODAS],
            organization=self.org,
        )
        self.commercial_stage = ActivityStage.objects.create(
            organization=self.org, sector=self.commercial, name="Triagem comercial", order=1
        )
        self.finance_stage = ActivityStage.objects.create(
            organization=self.org, sector=self.finance, name="Triagem financeira", order=1
        )
        self.commercial_status = WorkflowStatus.objects.create(
            organization=self.org, sector=self.commercial, domain=WorkflowStatus.Domain.ACTIVITY,
            name="Aguardando cliente", order=1,
        )
        self.finance_status = WorkflowStatus.objects.create(
            organization=self.org, sector=self.finance, domain=WorkflowStatus.Domain.ACTIVITY,
            name="Em conferência", order=1,
        )
        self.mine = self._activity("Demanda comercial", self.user, self.commercial)
        self.mine.stage = self.commercial_stage
        self.mine.condition = self.commercial_status
        self.mine.requested_deadline = timezone.now() - timedelta(days=1)
        self.mine.save(update_fields=["stage", "condition", "requested_deadline"])
        self.other_demand = self._activity("Demanda financeira", self.other, self.finance)
        self.other_demand.stage = self.finance_stage
        self.other_demand.condition = self.finance_status
        self.other_demand.requested_deadline = timezone.now() + timedelta(days=1)
        self.other_demand.save(update_fields=["stage", "condition", "requested_deadline"])
        self.unassigned = Activity.objects.create(
            organization=self.org, title="Demanda sem responsável", created_by=self.user, sector=self.finance,
        )
        self.unassigned.stage = self.finance_stage
        self.unassigned.condition = self.finance_status
        self.unassigned.save(update_fields=["stage", "condition"])
        self.client.force_login(self.user)

    def _activity(self, title, owner, sector):
        return ActivityService.create_activity(self.org, title, owner, self.user, sector=sector)

    def _response(self, route, **params):
        return self.client.get(reverse(route), {"tab": "todas", **params})

    def test_toolbar_has_the_same_order_without_retired_controls(self):
        labels = [
            "Buscar demanda", "Atrasadas", "Vencem hoje", "Setor", "Etapa", "Status", "Pessoas (Responsáveis)",
        ]
        for route in ("activity-list", "activity-kanban", "activity-calendar"):
            html = self._response(route).content.decode()
            toolbar = re.search(r'<form class="demand-board__filters".*?</form>', html, re.S).group(0)
            positions = [toolbar.index(label) for label in labels]
            self.assertEqual(positions, sorted(positions), route)
            self.assertIn('type="checkbox" name="pessoa"', toolbar)
            self.assertIn('data-auto-submit', toolbar)
            self.assertNotIn('name="pessoa" multiple', toolbar)
            self.assertNotIn("Aplicar pessoas", toolbar)
            self.assertNotIn(">Bloqueadas<", toolbar)
            self.assertNotIn("Mostrar primeiro", toolbar)
            self.assertNotIn("Agrupar por", toolbar)

    def test_deadline_shortcuts_are_exclusive_and_toggle_off_without_losing_filters(self):
        response = self._response("activity-list", prazo="atrasadas", q="financeira", pessoa=[self.other.pk, "sem"])
        html = response.content.decode()
        late_link = re.search(r'<a href="([^"]*)" class="is-late is-active">', html)
        self.assertIsNotNone(late_link)
        self.assertNotIn("prazo=", late_link.group(1))
        self.assertIn("q=financeira", late_link.group(1))
        self.assertEqual(late_link.group(1).count("pessoa="), 2)

        today_link = re.search(r'<a href="([^"]*)" class="is-today">', html)
        self.assertIsNotNone(today_link)
        self.assertIn("prazo=hoje", today_link.group(1))
        self.assertNotIn("prazo=atrasadas", today_link.group(1))

    def test_sector_scopes_stage_and_status_options_on_every_view(self):
        for route in ("activity-list", "activity-kanban", "activity-calendar"):
            response = self._response(route, setor=self.finance.pk)
            stage_groups = response.context["stage_choice_groups"]
            condition_groups = response.context["condition_choice_groups"]
            self.assertEqual([name for name, _items in stage_groups], ["Financeiro"], route)
            self.assertEqual([name for name, _items in condition_groups], ["Financeiro"], route)
            self.assertEqual([item.pk for _name, items in stage_groups for item in items], [self.finance_stage.pk])
            self.assertEqual([item.pk for _name, items in condition_groups for item in items], [self.finance_status.pk])

    def test_kanban_sector_filter_scopes_stage_and_status_lanes(self):
        board = ensure_domain_board(self.org, DomainBoard.Domain.DEMAND)
        view = board.views.get(type="KANBAN")
        grant_actions(self.user, [catalog.QUADRO_GERIR_COLUNAS], organization=self.org)

        self.client.post(
            reverse("workboard-view-settings", args=[view.pk]),
            data=json.dumps({"group_by": "stage"}),
            content_type="application/json",
        )
        stage_response = self._response("activity-kanban", setor=self.finance.pk)
        stage_labels = [group["label"] for group in stage_response.context["groups"]]
        self.assertIn(self.finance_stage.name, stage_labels)
        self.assertNotIn(self.commercial_stage.name, stage_labels)

        self.client.post(
            reverse("workboard-view-settings", args=[view.pk]),
            data=json.dumps({"group_by": "condition"}),
            content_type="application/json",
        )
        status_response = self._response("activity-kanban", setor=self.finance.pk)
        status_labels = [group["label"] for group in status_response.context["groups"]]
        self.assertIn(self.finance_status.name, status_labels)
        self.assertNotIn(self.commercial_status.name, status_labels)

    def test_multiple_people_and_unassigned_are_an_or_filter_in_all_views(self):
        for route in ("activity-list", "activity-kanban", "activity-calendar"):
            response = self._response(route, pessoa=[self.other.pk, "sem"])
            html = response.content.decode()
            self.assertContains(response, self.other_demand.title)
            self.assertContains(response, self.unassigned.title)
            self.assertNotIn(self.mine.title, html)
            self.assertEqual(response.context["filter_querystring"].count("pessoa="), 2)

    def test_people_dropdown_marks_every_selected_value(self):
        html = self._response("activity-list", pessoa=[self.other.pk, "sem"]).content.decode()
        toolbar = re.search(r'<form class="demand-board__filters".*?</form>', html, re.S).group(0)
        self.assertIn('value="sem" data-auto-submit checked', toolbar)
        self.assertIn(f'value="{self.other.pk}" data-auto-submit checked', toolbar)
        self.assertIn("2 pessoas selecionadas", toolbar)

    def test_single_person_and_legacy_responsavel_urls_stay_compatible(self):
        current = self._response("activity-list", pessoa=self.other.pk)
        legacy = self._response("activity-list", responsavel=self.other.pk)
        for response in (current, legacy):
            self.assertContains(response, self.other_demand.title)
            self.assertNotContains(response, self.unassigned.title)
            self.assertIn(f"pessoa={self.other.pk}", response.context["filter_querystring"])
            self.assertNotIn("responsavel=", response.context["filter_querystring"])

    def test_calendar_clear_keeps_its_month_but_removes_every_person_value(self):
        response = self._response(
            "activity-calendar", ano=2026, mes=10, pessoa=[self.other.pk, "sem"], setor=self.finance.pk,
        )
        html = response.content.decode()
        clear_link = re.search(r'<a class="demand-board__clear" href="([^"]*)">Limpar filtros</a>', html)
        self.assertIsNotNone(clear_link)
        self.assertIn("tab=todas", clear_link.group(1))
        self.assertIn("ano=2026", clear_link.group(1))
        self.assertIn("mes=10", clear_link.group(1))
        self.assertNotIn("pessoa=", clear_link.group(1))
        self.assertNotIn("setor=", clear_link.group(1))
