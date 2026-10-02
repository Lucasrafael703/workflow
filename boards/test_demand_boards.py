"""Integração de Demanda com o motor genérico de Quadros."""

import json

from django.test import TestCase
from django.template.loader import render_to_string
from django.urls import reverse

from acessos import catalog
from activities.forms import ActivityEditorForm
from activities.models import Task
from activities.services import ActivityService
from activities.testing import make_user
from core.models import Organization, Sector

from .models import Board, BoardCellOption, BoardColumn
from .services import BoardService, CellService, ItemService


class DemandBoardTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Organização de teste")
        self.comercial = Sector.objects.create(organization=self.org, name="Comercial")
        self.compras = Sector.objects.create(organization=self.org, name="Compras")
        self.owner = make_user(
            "dono-demand-board",
            self.org,
            [
                catalog.ATIVIDADE_CRIAR,
                catalog.QUADRO_CRIAR,
                catalog.QUADRO_CRIAR_ITEM,
                catalog.QUADRO_EDITAR_ITEM,
                catalog.QUADRO_EXCLUIR_ITEM,
            ],
        )
        self.collaborator = make_user("colaborador-demand-board", self.org, [])
        self.owner.profile.main_sector = self.comercial
        self.owner.profile.save(update_fields=["main_sector"])
        self.collaborator.profile.main_sector = self.compras
        self.collaborator.profile.save(update_fields=["main_sector"])

    def activity(self, title="Demanda"):
        return ActivityService.create_activity(
            organization=self.org,
            title=title,
            owner=self.owner,
            created_by=self.owner,
            sector=self.comercial,
        )

    def test_published_demand_has_a_generic_person_column_and_default_status(self):
        activity = self.activity()
        board = activity.task_board

        self.assertEqual(board.kind, Board.Kind.DEMAND)
        self.assertEqual(board.item_label, "Nome da Tarefa")
        responsible = board.columns.get(type=BoardColumn.Type.PERSON, is_active=True)
        status = board.columns.get(type=BoardColumn.Type.STATUS, is_active=True)
        self.assertFalse(hasattr(BoardColumn, "binding"))

        item = ItemService.create(user=self.owner, board=board, group=board.groups.get())
        self.assertEqual(item.name, "")
        self.assertFalse(hasattr(item, "task"))
        self.assertEqual(Task.objects.filter(activity=activity).count(), 0)
        self.assertTrue(
            BoardCellOption.objects.filter(
                cell__item=item,
                cell__column=status,
                option__is_default=True,
            ).exists()
        )
        self.assertFalse(item.cells.filter(column=responsible).exists())

    def test_collaborator_named_in_a_person_cell_can_create_and_edit_generic_items(self):
        activity = self.activity()
        board = activity.task_board
        responsible = board.columns.get(type=BoardColumn.Type.PERSON, is_active=True)
        seed = ItemService.create(user=self.owner, board=board, group=board.groups.get(), name="Preparar")
        CellService.set_value(user=self.owner, item=seed, column=responsible, raw_value=self.collaborator.pk)

        item = ItemService.create(user=self.collaborator, board=board, group=board.groups.get())
        ItemService.rename(user=self.collaborator, item=item, name="Comprar material")

        item.refresh_from_db()
        self.assertEqual(item.name, "Comprar material")
        self.assertEqual(Task.objects.filter(activity=activity).count(), 0)

    def test_item_create_endpoint_uses_the_same_blank_row_contract(self):
        activity = self.activity()
        board = activity.task_board
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("board-item-create", args=[board.pk]),
            data=json.dumps({"group_id": board.groups.get().pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        item = board.items.get()
        self.assertEqual(item.name, "")
        self.assertIn("row_html", response.json())
        self.assertEqual(Task.objects.filter(activity=activity).count(), 0)

    def test_demand_board_renders_only_the_standard_add_item_control(self):
        activity = self.activity()
        board = activity.task_board
        html = render_to_string(
            "boards/_group.html",
            {
                "board": board,
                "group": board.groups.get(),
                "columns": list(board.columns.filter(is_active=True)),
                "permissions": {"edit": True, "manage_columns": True, "create_item": True},
                "colspan": board.columns.filter(is_active=True).count() + 2,
            },
        )

        self.assertIn('class="board-add-item" data-item-add', html)
        self.assertIn("Adicionar tarefa", html)
        self.assertNotIn("Adicionar nome da tarefa", html)
        self.assertNotIn("data-demand-task", html)

    def test_template_items_are_copied_without_materializing_operational_tasks(self):
        template = BoardService.create(
            user=self.owner, organization=self.org, name="Modelo de orçamento", sector=self.compras
        )
        template_item = ItemService.create(
            user=self.owner, board=template, group=template.groups.get(), name="Solicitar cotação"
        )

        draft = ActivityService.save_draft(
            self.org,
            self.owner,
            title="Nova demanda",
            owner=self.owner,
            sector=self.comercial,
            board_setup_mode="TEMPLATE",
            board_template=template,
        )
        ActivityService.publish_draft(draft, self.owner)
        board = draft.task_board
        copied = board.items.get()

        self.assertEqual(board.source_template, template)
        self.assertEqual(copied.name, template_item.name)
        self.assertNotEqual(copied.pk, template_item.pk)
        self.assertEqual(Task.objects.filter(activity=draft).count(), 0)

    def test_legacy_task_and_process_urls_return_gone(self):
        self.assertEqual(self.client.get("/tarefas/999/").status_code, 410)
        self.assertEqual(self.client.get("/tarefas/nova-rapida/").status_code, 410)
        self.assertEqual(self.client.get("/demandas/999/tarefas/rapida/").status_code, 410)
        self.assertEqual(self.client.get("/demandas/999/processo/aplicar/").status_code, 410)
        self.assertEqual(self.client.get("/processos/").status_code, 410)

    def test_new_demand_form_accepts_a_template_from_its_organization(self):
        template = BoardService.create(
            user=self.owner, organization=self.org, name="Modelo para o wizard", sector=self.comercial
        )
        form = ActivityEditorForm(
            data={
                "title": "Demanda via wizard",
                "owner": self.owner.pk,
                "sector": self.comercial.pk,
                "board_setup_mode": "TEMPLATE",
                "board_template": template.pk,
            },
            organization=self.org,
            user=self.owner,
            drafting=True,
            can_change_owner=True,
        )
        self.assertTrue(form.is_valid(), form.errors)
