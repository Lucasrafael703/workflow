"""Modelos e serviços dos quadros: posição, colunas, etiquetas, itens, células, conversão de tipo, auditoria,
permissões e isolamento entre organizações."""

import datetime
from decimal import Decimal

from django.test import SimpleTestCase

from audit.models import AuditLog

from .models import BoardCell, BoardCellOption, BoardColumn, BoardColumnOption, BoardGroup, BoardItem
from .queries import BoardQueryService
from .services import (
    BoardError,
    BoardPermissionError,
    BoardService,
    CellService,
    ColumnService,
    GroupService,
    ItemService,
    OptionService,
    PositionService,
)
from .starter_templates import create_board_from_template
from .testing import BoardTestCase
from .validators import clean_color, format_date, format_number

T = BoardColumn.Type


class PositionMathTests(SimpleTestCase):
    def test_between_handles_each_edge(self):
        self.assertEqual(PositionService.between(None, None), Decimal("1000"))
        self.assertEqual(PositionService.between(None, Decimal("5000")), Decimal("4000"))
        self.assertEqual(PositionService.between(Decimal("1000"), None), Decimal("2000"))
        self.assertEqual(PositionService.between(Decimal("1000"), Decimal("2000")), Decimal("1500"))

    def test_between_asks_for_rebalance_when_the_gap_is_gone(self):
        self.assertIsNone(PositionService.between(Decimal("1000"), Decimal("1000.0005")))


class PositionTests(BoardTestCase):
    def siblings(self):
        return BoardColumn.objects.filter(board=self.board, is_active=True)

    def test_new_column_goes_to_the_end(self):
        last = self.siblings().order_by("-position").first()
        column = ColumnService.create(user=self.admin, board=self.board, column_type=T.TEXT)
        self.assertGreater(column.position, last.position)

    def test_new_column_can_go_right_after_another(self):
        first, second = list(self.siblings().order_by("position")[:2])
        column = ColumnService.create(user=self.admin, board=self.board, column_type=T.TEXT, after_column=first)
        self.assertGreater(column.position, first.position)
        self.assertLess(column.position, second.position)

    def test_reorder_places_between_the_neighbours(self):
        columns = list(self.siblings().order_by("position"))
        moved = columns[-1]
        ColumnService.reorder(user=self.admin, column=moved, before_id=columns[0].pk, after_id=columns[1].pk)
        order = [c.pk for c in self.siblings().order_by("position", "id")]
        self.assertEqual(order[:3], [columns[0].pk, moved.pk, columns[1].pk])

    def test_reorder_with_only_the_left_neighbour_sticks_to_it(self):
        columns = list(self.siblings().order_by("position"))
        moved = columns[-1]
        ColumnService.reorder(user=self.admin, column=moved, before_id=columns[0].pk)
        order = [c.pk for c in self.siblings().order_by("position", "id")]
        self.assertEqual(order[:2], [columns[0].pk, moved.pk])

    def test_reorder_with_a_neighbour_that_no_longer_exists_is_refused(self):
        moved = self.siblings().order_by("position").first()
        with self.assertRaises(BoardError):
            ColumnService.reorder(user=self.admin, column=moved, before_id=999999)

    def test_stale_neighbours_fall_back_to_the_left_one(self):
        columns = list(self.siblings().order_by("position"))
        moved = columns[-1]
        # a tela achava que 0 e 5 eram vizinhas; hoje há colunas entre elas: vale a da esquerda
        ColumnService.reorder(user=self.admin, column=moved, before_id=columns[0].pk, after_id=columns[5].pk)
        order = [c.pk for c in self.siblings().order_by("position", "id")]
        self.assertEqual(order[:2], [columns[0].pk, moved.pk])

    def test_rebalances_when_there_is_no_room_left(self):
        columns = list(self.siblings().order_by("position"))
        BoardColumn.objects.filter(pk=columns[1].pk).update(position=columns[0].position + Decimal("0.0005"))
        moved = columns[-1]
        ColumnService.reorder(user=self.admin, column=moved, before_id=columns[0].pk, after_id=columns[1].pk)
        moved.refresh_from_db()
        order = [c.pk for c in self.siblings().order_by("position", "id")]
        self.assertEqual(order[:3], [columns[0].pk, moved.pk, columns[1].pk])
        positions = list(self.siblings().order_by("position", "id").values_list("position", flat=True))
        self.assertTrue(all(b - a > Decimal("0.001") for a, b in zip(positions, positions[1:])))


class BoardAndGroupTests(BoardTestCase):
    def test_create_makes_a_default_group_and_audits(self):
        board = BoardService.create(user=self.admin, organization=self.org, name="  Obras   2026 ")
        self.assertEqual(board.name, "Obras 2026")
        self.assertEqual(list(board.groups.values_list("name", flat=True)), ["Grupo"])
        log = AuditLog.objects.get(action=AuditLog.Action.BOARD_CREATED, target_id=board.pk)
        self.assertEqual(log.target_type, "board")
        self.assertEqual(log.metadata["board_id"], board.pk)
        self.assertEqual(log.user, self.admin)

    def test_blank_name_gets_a_default(self):
        self.assertEqual(BoardService.create(user=self.admin, organization=self.org, name="  ").name, "Novo quadro")

    def test_create_needs_the_action(self):
        for user in (self.editor, self.viewer, self.sem_acesso):
            with self.assertRaises(BoardPermissionError):
                BoardService.create(user=user, organization=self.org, name="X")

    def test_nobody_creates_in_another_organization(self):
        with self.assertRaises(BoardPermissionError):
            BoardService.create(user=self.estranho, organization=self.org, name="Invasão")

    def test_update_and_delete_are_audited_and_permissioned(self):
        BoardService.update(user=self.admin, board=self.board, name="Orçamentos 2026")
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.BOARD_UPDATED, field_name="name",
                                                old_value="Orçamentos", new_value="Orçamentos 2026").exists())
        with self.assertRaises(BoardPermissionError):
            BoardService.update(user=self.editor, board=self.board, name="Outro")
        with self.assertRaises(BoardPermissionError):
            BoardService.soft_delete(user=self.editor, board=self.board)
        board = BoardService.create(user=self.admin, organization=self.org, name="Temporário")
        BoardService.soft_delete(user=self.admin, board=board)
        board.refresh_from_db()
        self.assertFalse(board.is_active)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.BOARD_DELETED, target_id=board.pk).exists())

    def test_group_color_is_validated(self):
        with self.assertRaises(BoardError):
            GroupService.create(user=self.admin, board=self.board, name="Ruim", color="vermelho")
        with self.assertRaises(BoardError):
            GroupService.update(user=self.admin, group=self.group_a, color="#12345")

    def test_group_with_items_cannot_be_deleted(self):
        with self.assertRaises(BoardError):
            GroupService.soft_delete(user=self.admin, group=self.group_a)
        empty = GroupService.create(user=self.admin, board=self.board, name="Vazio")
        GroupService.soft_delete(user=self.admin, group=empty)
        empty.refresh_from_db()
        self.assertFalse(empty.is_active)

    def test_group_reorder(self):
        third = GroupService.create(user=self.admin, board=self.board, name="Terceiro")
        GroupService.reorder(user=self.admin, group=third, before_id=None, after_id=self.group_a.pk)
        order = list(BoardGroup.objects.filter(board=self.board, is_active=True).order_by("position").values_list("pk", flat=True))
        self.assertEqual(order[0], third.pk)

    def test_group_actions_need_edit(self):
        with self.assertRaises(BoardPermissionError):
            GroupService.create(user=self.editor, board=self.board, name="X")


class ColumnTests(BoardTestCase):
    def test_every_active_type_can_be_created_with_its_defaults(self):
        for column_type in BoardColumn.ACTIVE_TYPES:
            column = ColumnService.create(user=self.admin, board=self.board, column_type=column_type)
            self.assertEqual(column.type, column_type)
            self.assertEqual(column.width, 160)
        status = ColumnService.create(user=self.admin, board=self.board, column_type=T.STATUS)
        self.assertEqual(
            list(status.options.order_by("position").values_list("label", "is_default", "is_done")),
            [("Não iniciado", True, False), ("Em andamento", False, False), ("Concluído", False, True)],
        )

    def test_reserved_and_unknown_types_are_refused(self):
        for bad in (T.FILE, T.FORMULA, "XYZ", ""):
            with self.assertRaises(BoardError):
                ColumnService.create(user=self.admin, board=self.board, column_type=bad)

    def test_default_names_do_not_repeat(self):
        first = ColumnService.create(user=self.admin, board=self.board, column_type=T.TEXT)
        second = ColumnService.create(user=self.admin, board=self.board, column_type=T.TEXT)
        self.assertEqual(first.name, "Texto 2")  # a coluna "Texto" já existe no cenário
        self.assertEqual(second.name, "Texto 3")

    def test_rename_trims_and_refuses_empty(self):
        column = ColumnService.rename(user=self.admin, column=self.col["texto"], name="  Cliente   final ")
        self.assertEqual(column.name, "Cliente final")
        with self.assertRaises(BoardError):
            ColumnService.rename(user=self.admin, column=self.col["texto"], name="   ")

    def test_resize_clamps_to_the_limits(self):
        column = self.col["texto"]
        self.assertEqual(ColumnService.resize(user=self.admin, column=column, width=40).width, 96)
        self.assertEqual(ColumnService.resize(user=self.admin, column=column, width=900).width, 640)
        self.assertEqual(ColumnService.resize(user=self.admin, column=column, width="250").width, 250)
        with self.assertRaises(BoardError):
            ColumnService.resize(user=self.admin, column=column, width="larga")

    def test_resize_is_audited_only_when_it_changes(self):
        column = self.col["texto"]
        ColumnService.resize(user=self.admin, column=column, width=200)
        ColumnService.resize(user=self.admin, column=column, width=200)
        self.assertEqual(
            AuditLog.objects.filter(action=AuditLog.Action.BOARD_COLUMN_RESIZED, target_id=column.pk).count(), 1
        )

    def test_column_actions_need_manage_columns(self):
        for user in (self.editor, self.viewer, self.sem_acesso):
            with self.assertRaises(BoardPermissionError):
                ColumnService.create(user=user, board=self.board, column_type=T.TEXT)
            with self.assertRaises(BoardPermissionError):
                ColumnService.resize(user=user, column=self.col["texto"], width=200)

    def test_other_organization_cannot_touch_the_column(self):
        with self.assertRaises(BoardPermissionError):
            ColumnService.rename(user=self.estranho, column=self.col["texto"], name="Hackeada")

    def test_settings_are_validated_per_type(self):
        column = self.col["numero"]
        ColumnService.update_settings(user=self.admin, column=column,
                                      settings={"decimal_places": 0, "unit": "%", "minimum": "0", "maximum": "100"})
        column.refresh_from_db()
        self.assertEqual(column.settings["unit"], "%")
        self.assertEqual(column.settings["maximum"], 100.0)
        with self.assertRaises(BoardError):
            ColumnService.update_settings(user=self.admin, column=column, settings={"decimal_places": 9})
        with self.assertRaises(BoardError):
            ColumnService.update_settings(user=self.admin, column=column, settings={"minimum": "50", "maximum": "10"})
        with self.assertRaises(BoardError):
            ColumnService.update_settings(user=self.admin, column=column, settings={"minimum": "abc"})

    def test_unknown_settings_keys_are_dropped(self):
        column = self.col["texto"]
        ColumnService.update_settings(user=self.admin, column=column, settings={"script": "<b>"})
        column.refresh_from_db()
        self.assertEqual(column.settings, {})

    def test_person_column_refuses_multiple(self):
        with self.assertRaises(BoardError):
            ColumnService.update_settings(user=self.admin, column=self.col["pessoa"], settings={"multiple": True})

    def test_common_settings(self):
        column = ColumnService.update_common(user=self.admin, column=self.col["texto"], description="Quem pediu", is_required=True)
        self.assertEqual(column.description, "Quem pediu")
        self.assertTrue(column.is_required)

    def test_hide_and_show(self):
        column = self.col["check"]
        ColumnService.set_visible(user=self.admin, column=column, visible=False)
        self.assertNotIn(column.pk, [c.pk for c in BoardQueryService.columns(self.board)])
        self.assertIn(column.pk, [c.pk for c in BoardQueryService.columns(self.board, visible=None)])
        ColumnService.set_visible(user=self.admin, column=column, visible=True)
        self.assertIn(column.pk, [c.pk for c in BoardQueryService.columns(self.board)])

    def test_soft_delete_keeps_the_data(self):
        self.set_cell(self.item1, "texto", "Convivy")
        column = self.col["texto"]
        ColumnService.soft_delete(user=self.admin, column=column)
        column.refresh_from_db()
        self.assertFalse(column.is_active)
        self.assertTrue(BoardCell.objects.filter(column=column, value_text="Convivy").exists())
        self.assertNotIn(column.pk, [c.pk for c in BoardQueryService.columns(self.board, visible=None)])

    def test_duplicate_copies_options_and_values(self):
        self.set_cell(self.item1, "status", self.andamento.pk)
        self.set_cell(self.item2, "status", self.concluido.pk)
        copy = ColumnService.duplicate(user=self.admin, column=self.col["status"])
        self.assertEqual(copy.name, "Status (cópia)")
        self.assertEqual(copy.options.count(), 3)
        self.assertNotEqual(set(copy.options.values_list("pk", flat=True)), set(self.col["status"].options.values_list("pk", flat=True)))
        labels = {
            cell.item_id: cell.option_values.get().option.label
            for cell in BoardCell.objects.filter(column=copy, item__in=[self.item1, self.item2])
        }
        self.assertEqual(labels, {self.item1.pk: "Em andamento", self.item2.pk: "Concluído"})
        # a cópia fica logo depois da original
        original = BoardColumn.objects.get(pk=self.col["status"].pk)
        self.assertGreater(copy.position, original.position)


class ConversionTests(BoardTestCase):
    def new_column(self, column_type):
        return ColumnService.create(user=self.admin, board=self.board, column_type=column_type)

    def test_number_to_currency_keeps_values_without_asking(self):
        column = self.new_column(T.NUMBER)
        CellService.set_value(user=self.admin, item=self.item1, column=column, raw_value="1500,5")
        self.assertEqual(ColumnService.conversion_plan(column, T.CURRENCY), {"mode": "safe", "filled": 1, "lost": 0})
        ColumnService.change_type(user=self.admin, column=column, new_type=T.CURRENCY)
        column.refresh_from_db()
        self.assertEqual(column.type, T.CURRENCY)
        self.assertEqual(column.settings["currency"], "BRL")
        self.assertEqual(BoardCell.objects.get(column=column).value_number, Decimal("1500.5"))

    def test_status_and_dropdown_keep_their_labels(self):
        self.set_cell(self.item1, "status", self.andamento.pk)
        status = self.col["status"]
        ColumnService.change_type(user=self.admin, column=status, new_type=T.DROPDOWN)
        status.refresh_from_db()
        self.assertEqual(status.type, T.DROPDOWN)
        cell = BoardCell.objects.get(item=self.item1, column=status)
        self.assertEqual(cell.option_values.get().option.label, "Em andamento")

    def test_anything_to_text_writes_what_the_screen_showed(self):
        self.set_cell(self.item1, "moeda", "1234,5")
        self.set_cell(self.item1, "pessoa", self.ana.pk)
        self.set_cell(self.item1, "data", "2025-10-01")
        ColumnService.change_type(user=self.admin, column=self.col["moeda"], new_type=T.TEXT)
        ColumnService.change_type(user=self.admin, column=self.col["pessoa"], new_type=T.TEXT)
        ColumnService.change_type(user=self.admin, column=self.col["data"], new_type=T.TEXT)
        values = {c.column_id: c.value_text for c in BoardCell.objects.filter(item=self.item1)}
        self.assertEqual(values[self.col["moeda"].pk], "R$ 1.234,50")
        self.assertEqual(values[self.col["pessoa"].pk], "Ana Souza")
        self.assertEqual(values[self.col["data"].pk], "01/10/2025")
        self.assertFalse(BoardCell.objects.get(item=self.item1, column=self.col["pessoa"]).user_values.exists())

    def test_text_to_number_parses_and_asks_before_losing_values(self):
        column = self.new_column(T.TEXT)
        for item, text in ((self.item1, "10,5"), (self.item2, "dez"), (self.item3, "")):
            CellService.set_value(user=self.admin, item=item, column=column, raw_value=text)
        plan = ColumnService.conversion_plan(column, T.NUMBER)
        self.assertEqual((plan["mode"], plan["lost"]), ("parsed", 1))
        with self.assertRaises(BoardError) as ctx:
            ColumnService.change_type(user=self.admin, column=column, new_type=T.NUMBER)
        self.assertTrue(ctx.exception.needs_confirmation)
        column.refresh_from_db()
        self.assertEqual(column.type, T.TEXT)  # nada mudou sem a confirmação

        ColumnService.change_type(user=self.admin, column=column, new_type=T.NUMBER, confirm=True)
        column.refresh_from_db()
        self.assertEqual(column.type, T.NUMBER)
        numbers = {c.item_id: c.value_number for c in BoardCell.objects.filter(column=column)}
        self.assertEqual(numbers[self.item1.pk], Decimal("10.5"))
        self.assertIsNone(numbers[self.item2.pk])

    def test_text_to_date_parses_brazilian_dates(self):
        column = self.new_column(T.TEXT)
        CellService.set_value(user=self.admin, item=self.item1, column=column, raw_value="15/10/2025")
        ColumnService.change_type(user=self.admin, column=column, new_type=T.DATE)
        self.assertEqual(BoardCell.objects.get(column=column).value_date, datetime.date(2025, 10, 15))

    def test_incompatible_types_clear_values_only_with_confirmation(self):
        self.set_cell(self.item1, "data", "2025-10-01")
        column = self.col["data"]
        plan = ColumnService.conversion_plan(column, T.NUMBER)
        self.assertEqual((plan["mode"], plan["lost"]), ("destructive", 1))
        with self.assertRaises(BoardError) as ctx:
            ColumnService.change_type(user=self.admin, column=column, new_type=T.NUMBER)
        self.assertTrue(ctx.exception.needs_confirmation)
        ColumnService.change_type(user=self.admin, column=column, new_type=T.NUMBER, confirm=True)
        cell = BoardCell.objects.get(column=column, item=self.item1)
        self.assertIsNone(cell.value_date)
        self.assertIsNone(cell.value_number)

    def test_converting_to_status_seeds_labels(self):
        column = self.new_column(T.TEXT)
        ColumnService.change_type(user=self.admin, column=column, new_type=T.STATUS, confirm=True)
        self.assertEqual(column.options.filter(is_active=True).count(), 3)

    def test_same_type_and_unknown_type_are_refused(self):
        with self.assertRaises(BoardError):
            ColumnService.change_type(user=self.admin, column=self.col["texto"], new_type=T.TEXT)
        with self.assertRaises(BoardError):
            ColumnService.change_type(user=self.admin, column=self.col["texto"], new_type=T.FILE)

    def test_conversion_is_audited(self):
        ColumnService.change_type(user=self.admin, column=self.col["numero"], new_type=T.CURRENCY)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.BOARD_COLUMN_UPDATED, field_name="type",
                                                old_value=T.NUMBER, new_value=T.CURRENCY).exists())


class OptionTests(BoardTestCase):
    def test_create_refuses_a_duplicate_label_ignoring_case(self):
        with self.assertRaises(BoardError):
            OptionService.create(user=self.admin, column=self.col["status"], label="concluído")

    def test_only_status_and_dropdown_have_options(self):
        with self.assertRaises(BoardError):
            OptionService.create(user=self.admin, column=self.col["texto"], label="X")

    def test_default_option_is_unique_and_fills_new_items(self):
        OptionService.update(user=self.admin, option=self.andamento, is_default=True)
        self.assertEqual(list(self.col["status"].options.filter(is_default=True)), [BoardColumnOption.objects.get(pk=self.andamento.pk)])
        item = ItemService.create(user=self.admin, board=self.board, group=self.group_a, name="Novo")
        cell = BoardCell.objects.get(item=item, column=self.col["status"])
        self.assertEqual(cell.option_values.get().option_id, self.andamento.pk)

    def test_rename_and_recolor_do_not_touch_cells(self):
        self.set_cell(self.item1, "status", self.andamento.pk)
        OptionService.update(user=self.admin, option=self.andamento, label="Fazendo", color="#e2445c")
        cell = BoardCell.objects.get(item=self.item1, column=self.col["status"])
        self.assertEqual(cell.option_values.get().option.label, "Fazendo")
        self.assertEqual(cell.option_values.get().option.color, "#E2445C")

    def test_rename_to_an_existing_label_is_refused(self):
        with self.assertRaises(BoardError):
            OptionService.update(user=self.admin, option=self.andamento, label="Concluído")

    def test_invalid_color_is_refused(self):
        with self.assertRaises(BoardError):
            OptionService.update(user=self.admin, option=self.andamento, color="azul")
        with self.assertRaises(BoardError):
            OptionService.create(user=self.admin, column=self.col["lista"], label="Nova", color="#GGGGGG")

    def test_delete_clears_the_cells_that_used_it(self):
        self.set_cell(self.item1, "lista", self.opt_a.pk)
        self.set_cell(self.item2, "lista", self.opt_b.pk)
        cleared = OptionService.soft_delete(user=self.admin, option=self.opt_a)
        self.assertEqual(cleared, 1)
        self.assertFalse(BoardCellOption.objects.filter(option=self.opt_a).exists())
        self.assertTrue(BoardCellOption.objects.filter(option=self.opt_b).exists())
        self.opt_a.refresh_from_db()
        self.assertFalse(self.opt_a.is_active)
        with self.assertRaises(BoardError):  # etiqueta apagada não vale mais
            self.set_cell(self.item1, "lista", self.opt_a.pk)

    def test_reorder(self):
        OptionService.reorder(user=self.admin, option=self.concluido, before_id=None, after_id=self.novo.pk)
        order = list(self.col["status"].options.filter(is_active=True).order_by("position").values_list("pk", flat=True))
        self.assertEqual(order[0], self.concluido.pk)

    def test_actions_need_manage_columns(self):
        with self.assertRaises(BoardPermissionError):
            OptionService.create(user=self.editor, column=self.col["lista"], label="X")


class ItemTests(BoardTestCase):
    def test_create_fills_default_labels_and_audits(self):
        cell = BoardCell.objects.get(item=self.item1, column=self.col["status"])
        self.assertEqual(cell.option_values.get().option.label, "Não iniciado")
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.BOARD_ITEM_CREATED, target_id=self.item1.pk).exists())

    def test_create_places_at_the_end_of_the_group(self):
        item = ItemService.create(user=self.admin, board=self.board, group=self.group_a, name="Último")
        positions = list(BoardItem.objects.filter(group=self.group_a, is_active=True).order_by("position").values_list("pk", flat=True))
        self.assertEqual(positions[-1], item.pk)

    def test_create_refuses_a_group_from_another_board(self):
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro quadro")
        with self.assertRaises(BoardError):
            ItemService.create(user=self.admin, board=self.board, group=other.groups.get(), name="X")

    def test_blank_name_is_allowed(self):
        item = ItemService.create(user=self.admin, board=self.board, group=self.group_a)
        self.assertEqual(item.name, "")

    def test_rename(self):
        ItemService.rename(user=self.admin, item=self.item1, name="  Arena   Sul ")
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.name, "Arena Sul")

    def test_move_between_groups_and_positions(self):
        ItemService.move(user=self.admin, item=self.item1, group=self.group_b, before_id=None, after_id=self.item3.pk)
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.group_id, self.group_b.pk)
        order = list(BoardItem.objects.filter(group=self.group_b, is_active=True).order_by("position").values_list("pk", flat=True))
        self.assertEqual(order, [self.item1.pk, self.item3.pk])
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.BOARD_ITEM_MOVED, target_id=self.item1.pk,
                                                old_value="Oportunidades", new_value="Em andamento").exists())

    def test_move_within_the_same_group(self):
        ItemService.move(user=self.admin, item=self.item2, before_id=None, after_id=self.item1.pk)
        order = list(BoardItem.objects.filter(group=self.group_a, is_active=True).order_by("position").values_list("pk", flat=True))
        self.assertEqual(order, [self.item2.pk, self.item1.pk])

    def test_move_to_a_group_of_another_board_is_refused(self):
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro quadro")
        with self.assertRaises(BoardError):
            ItemService.move(user=self.admin, item=self.item1, group=other.groups.get())

    def test_delete_is_logical_and_needs_its_own_action(self):
        with self.assertRaises(BoardPermissionError):
            ItemService.soft_delete(user=self.editor, item=self.item1)
        ItemService.soft_delete(user=self.admin, item=self.item1)
        self.item1.refresh_from_db()
        self.assertFalse(self.item1.is_active)
        self.assertTrue(BoardCell.objects.filter(item=self.item1).exists())

    def test_editor_can_create_and_rename_but_viewer_cannot(self):
        item = ItemService.create(user=self.editor, board=self.board, group=self.group_a, name="Do editor")
        ItemService.rename(user=self.editor, item=item, name="Do editor 2")
        with self.assertRaises(BoardPermissionError):
            ItemService.create(user=self.viewer, board=self.board, group=self.group_a, name="Não")
        with self.assertRaises(BoardPermissionError):
            ItemService.rename(user=self.viewer, item=item, name="Não")


class CellTests(BoardTestCase):
    def cell(self, item, key):
        return BoardCell.objects.get(item=item, column=self.col[key])

    def test_text(self):
        self.set_cell(self.item1, "texto", "  Convivy  ")
        self.assertEqual(self.cell(self.item1, "texto").value_text, "Convivy")

    def test_text_limit(self):
        with self.assertRaises(BoardError):
            self.set_cell(self.item1, "texto", "x" * 5001)

    def test_number_accepts_brazilian_and_plain_formats(self):
        self.set_cell(self.item1, "numero", "1.234,56")
        self.assertEqual(self.cell(self.item1, "numero").value_number, Decimal("1234.56"))
        self.set_cell(self.item1, "numero", 7.5)
        self.assertEqual(self.cell(self.item1, "numero").value_number, Decimal("7.50"))

    def test_number_is_rounded_to_the_configured_places(self):
        ColumnService.update_settings(user=self.admin, column=self.col["numero"], settings={"decimal_places": 0})
        self.set_cell(self.item1, "numero", "2,5")
        self.assertEqual(self.cell(self.item1, "numero").value_number, Decimal("3"))

    def test_number_rejects_garbage_and_out_of_range(self):
        for bad in ("abc", "1,2,3x", "NaN", "Infinity", "1e99"):
            with self.assertRaises(BoardError, msg=bad):
                self.set_cell(self.item1, "numero", bad)
        ColumnService.update_settings(user=self.admin, column=self.col["numero"], settings={"minimum": 0, "maximum": 100})
        with self.assertRaises(BoardError):
            self.set_cell(self.item1, "numero", "101")
        with self.assertRaises(BoardError):
            self.set_cell(self.item1, "numero", "-1")
        self.set_cell(self.item1, "numero", "100")

    def test_currency_display(self):
        cell = self.set_cell(self.item1, "moeda", "2500000")
        self.assertEqual(CellService.display_value(cell, self.col["moeda"]), "R$ 2.500.000,00")

    def test_date_formats(self):
        self.set_cell(self.item1, "data", "2025-10-01")
        self.assertEqual(self.cell(self.item1, "data").value_date, datetime.date(2025, 10, 1))
        self.set_cell(self.item1, "data", "02/10/2025")
        self.assertEqual(self.cell(self.item1, "data").value_date, datetime.date(2025, 10, 2))
        for bad in ("31/02/2025", "ontem", "2025-13-01"):
            with self.assertRaises(BoardError, msg=bad):
                self.set_cell(self.item1, "data", bad)

    def test_date_without_weekends(self):
        ColumnService.update_settings(user=self.admin, column=self.col["data"], settings={"allow_weekends": False})
        with self.assertRaises(BoardError):
            self.set_cell(self.item1, "data", "2025-10-04")  # sábado
        self.set_cell(self.item1, "data", "2025-10-03")  # sexta

    def test_date_with_time(self):
        ColumnService.update_settings(user=self.admin, column=self.col["data"], settings={"show_time": True})
        self.set_cell(self.item1, "data", "2025-10-01T14:30")
        cell = self.cell(self.item1, "data")
        self.assertIsNotNone(cell.value_datetime)
        self.assertTrue(CellService.display_value(cell, self.col["data"]).endswith("14:30"))

    def test_person_is_a_user_of_the_same_organization(self):
        self.set_cell(self.item1, "pessoa", self.ana.pk)
        cell = self.cell(self.item1, "pessoa")
        self.assertEqual(cell.user_values.get().user, self.ana)
        self.assertEqual(CellService.display_value(cell, self.col["pessoa"]), "Ana Souza")
        with self.assertRaises(BoardError):
            self.set_cell(self.item1, "pessoa", self.foreign_person.pk)
        with self.assertRaises(BoardError):
            self.set_cell(self.item1, "pessoa", "ana")
        # a recusa não apaga o valor que já estava lá
        self.assertEqual(self.cell(self.item1, "pessoa").user_values.get().user, self.ana)

    def test_inactive_person_is_refused(self):
        self.bruno.is_active = False
        self.bruno.save(update_fields=["is_active"])
        with self.assertRaises(BoardError):
            self.set_cell(self.item1, "pessoa", self.bruno.pk)

    def test_person_replaces_the_previous_one(self):
        self.set_cell(self.item1, "pessoa", self.ana.pk)
        self.set_cell(self.item1, "pessoa", self.bruno.pk)
        self.assertEqual([link.user for link in self.cell(self.item1, "pessoa").user_values.all()], [self.bruno])

    def test_status_must_be_an_active_option_of_the_same_column(self):
        self.set_cell(self.item1, "status", self.andamento.pk)
        self.assertEqual(self.cell(self.item1, "status").option_values.get().option, self.andamento)
        with self.assertRaises(BoardError):
            self.set_cell(self.item1, "status", self.opt_a.pk)  # etiqueta de outra coluna
        with self.assertRaises(BoardError):
            self.set_cell(self.item1, "status", 999999)
        with self.assertRaises(BoardError):
            self.set_cell(self.item1, "status", "x")
        self.assertEqual(self.cell(self.item1, "status").option_values.get().option, self.andamento)

    def test_checkbox(self):
        self.set_cell(self.item1, "check", "1")
        self.assertIs(self.cell(self.item1, "check").value_boolean, True)
        self.set_cell(self.item1, "check", False)
        self.assertIs(self.cell(self.item1, "check").value_boolean, False)
        with self.assertRaises(BoardError):
            self.set_cell(self.item1, "check", "talvez")

    def test_clearing(self):
        self.set_cell(self.item1, "texto", "algo")
        self.set_cell(self.item1, "texto", "")
        self.assertEqual(self.cell(self.item1, "texto").value_text, "")
        self.set_cell(self.item1, "status", "")
        self.assertFalse(self.cell(self.item1, "status").option_values.exists())

    def test_required_column_cannot_be_cleared(self):
        ColumnService.update_common(user=self.admin, column=self.col["texto"], is_required=True)
        self.col["texto"].refresh_from_db()
        with self.assertRaises(BoardError) as ctx:
            self.set_cell(self.item1, "texto", "")
        self.assertIn("obrigatória", str(ctx.exception))

    def test_column_of_another_board_is_refused(self):
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro")
        column = ColumnService.create(user=self.admin, board=other, column_type=T.TEXT)
        with self.assertRaises(BoardError):
            CellService.set_value(user=self.admin, item=self.item1, column=column, raw_value="x")

    def test_deleted_column_is_refused(self):
        column = self.col["check"]
        ColumnService.soft_delete(user=self.admin, column=column)
        column.refresh_from_db()
        with self.assertRaises(BoardError):
            CellService.set_value(user=self.admin, item=self.item1, column=column, raw_value="1")

    def test_audit_only_when_the_value_changes(self):
        self.set_cell(self.item1, "texto", "A")
        self.set_cell(self.item1, "texto", "A")
        self.set_cell(self.item1, "texto", "B")
        logs = AuditLog.objects.filter(action=AuditLog.Action.BOARD_CELL_UPDATED, metadata__item_id=self.item1.pk,
                                       metadata__column_id=self.col["texto"].pk).order_by("id")
        self.assertEqual([(log.old_value, log.new_value) for log in logs], [("", "A"), ("A", "B")])
        self.assertEqual(logs[0].target_type, "board_cell")
        self.assertEqual(logs[0].metadata["board_id"], self.board.pk)
        self.assertEqual(logs[0].field_name, self.col["texto"].name)

    def test_viewer_and_stranger_cannot_write(self):
        with self.assertRaises(BoardPermissionError):
            self.set_cell(self.item1, "texto", "x", user=self.viewer)
        with self.assertRaises(BoardPermissionError):
            self.set_cell(self.item1, "texto", "x", user=self.sem_acesso)
        with self.assertRaises(BoardPermissionError):
            self.set_cell(self.item1, "texto", "x", user=self.estranho)
        self.set_cell(self.item1, "texto", "ok", user=self.editor)

    def test_editing_touches_the_item(self):
        self.set_cell(self.item1, "texto", "x", user=self.editor)
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.updated_by, self.editor)


class FormattingTests(SimpleTestCase):
    def test_number_format_is_brazilian(self):
        self.assertEqual(format_number(Decimal("1234567.891"), 2), "1.234.567,89")
        self.assertEqual(format_number(Decimal("5"), 0), "5")
        self.assertEqual(format_number(None, 2), "")

    def test_date_formats(self):
        day = datetime.date(2025, 3, 7)
        self.assertEqual(format_date(day), "07/03/2025")
        self.assertEqual(format_date(day, "DD/MM/YY"), "07/03/25")
        self.assertEqual(format_date(day, "YYYY-MM-DD"), "2025-03-07")

    def test_colors(self):
        self.assertEqual(clean_color("#a1b2c3", "#000000"), "#A1B2C3")
        self.assertEqual(clean_color("", "#579BFC"), "#579BFC")


class QueryTests(BoardTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for item, texto, numero, data, pessoa, status in (
            (cls.item1, "banana", "30", "2025-12-01", cls.bruno.pk, cls.concluido.pk),
            (cls.item2, "Abacate", "5,5", "2025-01-15", cls.ana.pk, cls.andamento.pk),
            (cls.item3, "", "", "", "", ""),
        ):
            for key, value in (("texto", texto), ("numero", numero), ("data", data), ("pessoa", pessoa), ("status", status)):
                CellService.set_value(user=cls.admin, item=item, column=cls.col[key], raw_value=value)

    def names(self, **kwargs):
        return [item.name for item in BoardQueryService.items(self.board, **kwargs)]

    def test_default_order_is_group_then_position(self):
        self.assertEqual(self.names(), ["Arena Norte", "Condomínio Cotia", "Hospital Vida"])

    def test_sort_text_ignores_case_and_puts_empty_last(self):
        self.assertEqual(self.names(sort_column=self.col["texto"]), ["Condomínio Cotia", "Arena Norte", "Hospital Vida"])
        self.assertEqual(self.names(sort_column=self.col["texto"], direction="desc"), ["Arena Norte", "Condomínio Cotia", "Hospital Vida"])

    def test_sort_number_is_numeric_not_alphabetical(self):
        self.assertEqual(self.names(sort_column=self.col["numero"]), ["Condomínio Cotia", "Arena Norte", "Hospital Vida"])

    def test_sort_date(self):
        self.assertEqual(self.names(sort_column=self.col["data"]), ["Condomínio Cotia", "Arena Norte", "Hospital Vida"])

    def test_sort_status_follows_the_option_order(self):
        self.assertEqual(self.names(sort_column=self.col["status"]), ["Condomínio Cotia", "Arena Norte", "Hospital Vida"])

    def test_sort_person_by_name(self):
        self.assertEqual(self.names(sort_column=self.col["pessoa"]), ["Condomínio Cotia", "Arena Norte", "Hospital Vida"])

    def test_sort_keeps_the_groups_apart(self):
        ItemService.move(user=self.admin, item=self.item3, group=self.group_a)
        names = self.names(sort_column=self.col["numero"], direction="desc")
        self.assertEqual(names, ["Arena Norte", "Condomínio Cotia", "Hospital Vida"])

    def test_search_in_name_text_label_and_person(self):
        self.assertEqual(self.names(search="arena"), ["Arena Norte"])
        self.assertEqual(self.names(search="abacate"), ["Condomínio Cotia"])
        self.assertEqual(self.names(search="andamento"), ["Condomínio Cotia"])
        self.assertEqual(self.names(search="Bruno"), ["Arena Norte"])
        self.assertEqual(self.names(search="nada disso"), [])

    def test_filter_by_person(self):
        self.assertEqual(self.names(person_id=self.ana.pk), ["Condomínio Cotia"])

    def test_deleted_items_and_columns_disappear(self):
        ItemService.soft_delete(user=self.admin, item=self.item2)
        self.assertNotIn("Condomínio Cotia", self.names())

    def test_attach_cells_needs_no_extra_queries_per_cell(self):
        columns = list(BoardQueryService.columns(self.board))
        with self.assertNumQueries(4):
            items = list(BoardQueryService.with_cells(BoardQueryService.items(self.board)))
            BoardQueryService.attach_cells(items, {c.pk: c for c in columns})
            for item in items:
                for cell in item.cell_map.values():
                    cell.display, cell.option, cell.person  # tudo já resolvido

    def test_history_only_has_this_board(self):
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro")
        ids = {log.metadata["board_id"] for log in BoardQueryService.history(self.board)}
        self.assertEqual(ids, {self.board.pk})
        self.assertTrue(BoardQueryService.history(other).exists())


class StarterTemplateTests(BoardTestCase):
    def test_orcamentos_template(self):
        board = create_board_from_template(user=self.admin, organization=self.org, key="orcamentos")
        self.assertEqual(board.name, "Orçamentos")
        self.assertEqual(board.item_label, "Nome da Tarefa")
        self.assertEqual([g.name for g in board.groups.order_by("position")],
                         ["Oportunidades", "Em andamento", "Propostas enviadas", "Concluídos"])
        names = [c.name for c in board.columns.order_by("position")]
        self.assertEqual(names, ["Cliente", "Responsável", "Setor", "Prazo", "Status", "Valor", "Probabilidade",
                                 "Pendência", "Visita técnica"])
        status = board.columns.get(name="Status")
        self.assertEqual(status.options.count(), 9)
        self.assertEqual(status.options.get(is_default=True).label, "Novo")
        self.assertEqual(board.columns.get(name="Probabilidade").settings["unit"], "%")
        self.assertTrue(board.columns.get(name="Prazo").settings["is_deadline"])
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.BOARD_CREATED, target_id=board.pk,
                                                metadata__template="orcamentos").exists())

    def test_examples_are_optional(self):
        board = create_board_from_template(user=self.admin, organization=self.org, key="orcamentos", with_examples=True)
        self.assertEqual(board.items.count(), 4)
        item = board.items.get(name="Galpão Logístico ABC")
        status = BoardCell.objects.get(item=item, column__name="Status").option_values.get().option.label
        self.assertEqual(status, "Novo")
        deadline = BoardCell.objects.get(item=item, column__name="Prazo").value_date
        self.assertGreater(deadline, datetime.date.today())

    def test_template_needs_the_create_action_and_a_known_key(self):
        with self.assertRaises(BoardPermissionError):
            create_board_from_template(user=self.editor, organization=self.org, key="orcamentos")
        with self.assertRaises(BoardError):
            create_board_from_template(user=self.admin, organization=self.org, key="nao-existe")
