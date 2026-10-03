"""Integração de Demanda com o motor genérico de Quadros."""

import json
from unittest import mock

from django.test import TestCase
from django.template.loader import render_to_string
from django.urls import reverse

from acessos import catalog
from activities.forms import ActivityEditorForm
from activities.models import Activity, Task
from activities.services import ActivityService
from activities.testing import make_user
from audit.models import AuditLog
from core.models import Organization, Sector

from .demand_services import BoardInstantiationService
from .models import Board, BoardCellOption, BoardColumn, BoardItem
from .services import BoardError, BoardPermissionError, BoardService, CellService, ItemService


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


class ReplaceDemandBoardTests(TestCase):
    """Editar a Demanda: trocar o quadro de tarefas (exclui as tarefas do quadro atual, no MESMO `Board`)."""

    def setUp(self):
        self.org = Organization.objects.create(name="Organização de teste")
        self.other_org = Organization.objects.create(name="Outra organização")
        self.sector = Sector.objects.create(organization=self.org, name="Comercial")
        self.owner = make_user(
            "dono-troca-quadro",
            self.org,
            [catalog.ATIVIDADE_CRIAR, catalog.QUADRO_CRIAR, catalog.QUADRO_CRIAR_ITEM, catalog.QUADRO_EDITAR_ITEM],
        )
        self.stranger = make_user("alheio-troca-quadro", self.org, [catalog.ATIVIDADE_EDITAR])
        self.manager = make_user("gerente-troca-quadro", self.org, [catalog.QUADRO_GERIR_COLUNAS])
        self.activity = ActivityService.create_activity(
            organization=self.org, title="Demanda com quadro", owner=self.owner, created_by=self.owner, sector=self.sector
        )
        self.board = self.activity.task_board

    def make_template(self, name="Modelo", items=("Visitar a obra", "Orçar materiais")):
        template = BoardService.create(user=self.owner, organization=self.org, name=name, sector=self.sector)
        for item_name in items:
            ItemService.create(user=self.owner, board=template, group=template.groups.get(), name=item_name)
        return template

    def fill(self, board, names=("Primeira", "Segunda", "Terceira")):
        """Itens com Status padrão (célula + etiqueta) e Responsável (célula + pessoa), como no uso real."""
        person = board.columns.get(type=BoardColumn.Type.PERSON, is_active=True)
        created = []
        for name in names:
            item = ItemService.create(user=self.owner, board=board, group=board.groups.filter(is_active=True).first(), name=name)
            CellService.set_value(user=self.owner, item=item, column=person, raw_value=self.owner.pk)
            created.append(item)
        return created

    def replace(self, template=None, confirmed=True, user=None):
        return BoardInstantiationService.replace_for_activity(
            user=user or self.owner, activity=self.activity, template=template, confirmed=confirmed
        )

    def test_a_different_choice_without_confirmation_is_refused_and_nothing_changes(self):
        self.fill(self.board)
        template = self.make_template()
        columns_before = set(self.board.columns.values_list("pk", flat=True))
        with self.assertRaises(BoardError) as caught:
            self.replace(template, confirmed=False)
        self.assertTrue(caught.exception.needs_confirmation)
        self.board.refresh_from_db()
        self.assertEqual(BoardItem.objects.filter(board=self.board, is_active=True).count(), 3)
        self.assertEqual(set(self.board.columns.values_list("pk", flat=True)), columns_before)
        self.assertIsNone(self.board.source_template_id)

    def test_blank_to_template_replaces_everything_inside_the_same_board(self):
        old_items = self.fill(self.board)
        old_columns = set(self.board.columns.values_list("pk", flat=True))
        old_groups = set(self.board.groups.values_list("pk", flat=True))
        old_views = set(self.board.views.values_list("pk", flat=True))
        template = self.make_template()

        board, deleted = self.replace(template)

        self.assertEqual((board.pk, deleted), (self.board.pk, 3))  # mesmo quadro (mesmo endereço) e 3 tarefas excluídas
        self.assertEqual(self.activity.task_board.pk, self.board.pk)
        self.assertEqual(Board.objects.filter(activity=self.activity).count(), 1)
        self.assertFalse(BoardItem.objects.filter(pk__in=[item.pk for item in old_items]).exists())
        self.assertFalse(BoardColumn.objects.filter(pk__in=old_columns).exists())
        self.assertFalse(self.board.groups.filter(pk__in=old_groups).exists())
        self.assertFalse(self.board.views.filter(pk__in=old_views).exists())
        board.refresh_from_db()
        self.assertEqual(board.source_template_id, template.pk)
        self.assertEqual(sorted(board.items.filter(is_active=True).values_list("name", flat=True)), ["Orçar materiais", "Visitar a obra"])
        self.assertTrue(board.columns.filter(type=BoardColumn.Type.PERSON, is_active=True).exists())
        self.assertTrue(board.views.exists())
        self.activity.refresh_from_db()
        self.assertEqual((self.activity.board_setup_mode, self.activity.board_template_id), ("TEMPLATE", template.pk))

    def test_the_new_board_is_an_independent_copy_of_the_template(self):
        template = self.make_template(items=("Visitar a obra",))
        board, _ = self.replace(template)
        copied = board.items.get()
        template_item = template.items.get()
        self.assertNotEqual(copied.pk, template_item.pk)
        ItemService.rename(user=self.owner, item=copied, name="Só na demanda")
        template_item.refresh_from_db()
        self.assertEqual(template_item.name, "Visitar a obra")
        ItemService.rename(user=self.owner, item=template_item, name="Só no modelo")
        copied.refresh_from_db()
        self.assertEqual(copied.name, "Só na demanda")
        self.assertEqual(template.items.filter(is_active=True).count(), 1)  # o modelo continua inteiro

    def test_template_to_blank_leaves_a_default_blank_board(self):
        template = self.make_template()
        self.replace(template)
        self.fill(self.activity.task_board, names=("Extra",))

        board, deleted = self.replace(None)

        self.assertEqual(deleted, 3)  # as 2 do modelo + a nova
        board.refresh_from_db()
        self.assertIsNone(board.source_template_id)
        self.assertFalse(board.items.exists())
        self.assertTrue(board.columns.filter(type=BoardColumn.Type.PERSON, is_active=True).exists())
        self.assertTrue(board.columns.filter(type=BoardColumn.Type.STATUS, is_active=True).exists())
        self.assertEqual(sorted(board.views.values_list("type", flat=True)), ["CALENDAR", "KANBAN"])
        self.activity.refresh_from_db()
        self.assertEqual((self.activity.board_setup_mode, self.activity.board_template_id), ("BLANK", None))

    def test_the_same_choice_changes_nothing_and_needs_no_confirmation(self):
        items = self.fill(self.board)
        board, deleted = self.replace(None, confirmed=False)  # em branco -> em branco
        self.assertEqual((board.pk, deleted), (self.board.pk, 0))
        self.assertEqual(BoardItem.objects.filter(pk__in=[item.pk for item in items], is_active=True).count(), 3)

        template = self.make_template()
        self.replace(template)
        kept = list(self.activity.task_board.items.values_list("pk", flat=True))
        Board.objects.filter(pk=template.pk).update(is_active=False)  # o modelo some depois: continua valendo como "mesma escolha"
        board, deleted = self.replace(template, confirmed=False)
        self.assertEqual(deleted, 0)
        self.assertEqual(list(board.items.values_list("pk", flat=True)), kept)

    def test_no_audit_entry_and_no_change_when_nothing_is_replaced(self):
        self.replace(None, confirmed=False)
        self.assertFalse(AuditLog.objects.filter(action=AuditLog.Action.BOARD_UPDATED, target_type="board", target_id=self.board.pk).exists())

    def test_the_replacement_is_audited_with_the_number_of_deleted_tasks(self):
        self.fill(self.board)
        template = self.make_template("Modelo auditado")
        self.replace(template)
        entry = AuditLog.objects.filter(action=AuditLog.Action.BOARD_UPDATED, target_type="board", target_id=self.board.pk).latest("pk")
        self.assertEqual((entry.old_value, entry.new_value), ("Em branco", "Modelo auditado"))
        self.assertEqual(entry.user_id, self.owner.pk)
        self.assertEqual(entry.metadata["items_deleted"], 3)
        self.assertTrue(entry.metadata["replaced"])
        self.assertEqual(entry.metadata["activity_id"], self.activity.pk)

    def test_a_demand_without_a_board_gets_one_without_confirmation(self):
        Board.objects.filter(activity=self.activity).delete()
        self.activity.refresh_from_db()
        board, deleted = self.replace(None, confirmed=False)
        self.assertEqual(deleted, 0)
        self.assertEqual(Board.objects.filter(activity=self.activity).count(), 1)
        self.assertEqual(board.kind, Board.Kind.DEMAND)

        Board.objects.filter(activity=self.activity).delete()
        template = self.make_template()
        board, _ = self.replace(template, confirmed=False)
        self.assertEqual(board.source_template_id, template.pk)
        self.assertEqual(board.items.filter(is_active=True).count(), 2)

    def test_only_who_manages_the_structure_can_replace(self):
        self.fill(self.board)
        template = self.make_template()
        with self.assertRaises(BoardPermissionError):
            self.replace(template, user=self.stranger)  # nem responsável, nem criador, nem gerencia quadros
        self.assertEqual(BoardItem.objects.filter(board=self.board, is_active=True).count(), 3)
        self.assertIsNone(Board.objects.get(pk=self.board.pk).source_template_id)
        board, deleted = self.replace(template, user=self.manager)  # quem gerencia quadros pode
        self.assertEqual((board.pk, deleted), (self.board.pk, 3))

    def test_inactive_and_foreign_templates_are_refused_and_nothing_is_deleted(self):
        self.fill(self.board)
        inactive = self.make_template("Inativo")
        Board.objects.filter(pk=inactive.pk).update(is_active=False)
        inactive.refresh_from_db()
        foreign = Board.objects.create(
            organization=self.other_org, name="De fora", kind=Board.Kind.TEMPLATE, created_by=self.owner
        )
        for template in (inactive, foreign):
            with self.assertRaises(BoardError):
                self.replace(template)
        self.assertEqual(BoardItem.objects.filter(board=self.board, is_active=True).count(), 3)

    def test_a_failure_while_rebuilding_keeps_the_old_board_intact(self):
        self.fill(self.board)
        columns_before = set(self.board.columns.values_list("pk", flat=True))
        template = self.make_template()
        with mock.patch.object(BoardInstantiationService, "_copy_structure", side_effect=RuntimeError("falhou no meio")):
            with self.assertRaises(RuntimeError):
                self.replace(template)
        self.board.refresh_from_db()
        self.assertEqual(BoardItem.objects.filter(board=self.board, is_active=True).count(), 3)
        self.assertEqual(set(self.board.columns.values_list("pk", flat=True)), columns_before)
        self.assertIsNone(self.board.source_template_id)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.board_setup_mode, "BLANK")

    def test_other_boards_are_untouched(self):
        other = ActivityService.create_activity(
            organization=self.org, title="Outra demanda", owner=self.owner, created_by=self.owner, sector=self.sector
        )
        self.fill(other.task_board, names=("Da outra",))
        self.fill(self.board)
        template = self.make_template()
        self.replace(template)
        self.assertEqual(list(other.task_board.items.filter(is_active=True).values_list("name", flat=True)), ["Da outra"])
        self.assertEqual(template.items.filter(is_active=True).count(), 2)

    def test_item_count_counts_only_active_tasks(self):
        items = self.fill(self.board)
        BoardItem.objects.filter(pk=items[0].pk).update(is_active=False)  # excluída (soft delete)
        self.assertEqual(BoardInstantiationService.item_count(self.board), 2)
        self.assertEqual(BoardInstantiationService.item_count(None), 0)

    def test_the_current_choice_comes_from_the_real_board(self):
        self.assertEqual(BoardInstantiationService.current_choice(self.board), ("BLANK", None))
        self.assertEqual(BoardInstantiationService.current_choice(None), ("BLANK", None))
        template = self.make_template()
        board, _ = self.replace(template)
        board.refresh_from_db()
        self.assertEqual(BoardInstantiationService.current_choice(board), ("TEMPLATE", template))
        Activity.objects.filter(pk=self.activity.pk).update(board_setup_mode="", board_template=None)  # campo velho/vazio
        self.assertEqual(BoardInstantiationService.current_choice(board), ("TEMPLATE", template))
