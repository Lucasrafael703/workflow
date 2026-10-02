"""Visualização Kanban: configuração, raias, serviço de visualizações, telas e API."""

import json
from decimal import Decimal

from django.apps import apps as django_apps
from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from audit.models import AuditLog

from .kanban import (
    BLANK_ALWAYS,
    BLANK_NEVER,
    build_lanes,
    clean_kanban_settings,
    resolve_card_columns,
    resolve_group_column,
    resolve_sum_column,
    sort_choice,
    sort_options,
)
from .models import Board, BoardColumn, BoardItem, BoardView
from .queries import BoardQueryService
from .services import (
    BoardError,
    BoardPermissionError,
    BoardService,
    CellService,
    ColumnService,
    ItemService,
    ViewService,
)
from .starter_templates import create_board_from_template
from .test_views import ViewTestCase
from .testing import BoardTestCase

T = BoardColumn.Type


class KanbanBase(BoardTestCase):
    def columns(self):
        return list(BoardQueryService.columns(self.board, visible=None))

    def lanes(self, settings=None, sum_key=None, **filters):
        columns = self.columns()
        merged = clean_kanban_settings(columns, settings or {}, current=self.kanban.settings)
        group = resolve_group_column(merged, columns)
        sum_column = resolve_sum_column(merged, columns)
        by_id = {column.pk: column for column in columns}
        items = BoardQueryService.with_cells(BoardQueryService.kanban_items(self.board, **filters))
        items = BoardQueryService.attach_cells(list(items), by_id)
        return build_lanes(group, items, merged, sum_column)

    def lane(self, lanes, label):
        return next(lane for lane in lanes if lane["label"] == label)


class DefaultViewTests(KanbanBase):
    def test_every_board_is_born_with_a_kanban(self):
        view = self.board.views.get()
        self.assertEqual((view.name, view.type, view.is_active), ("Kanban", "KANBAN", True))
        self.assertEqual(view.created_by, self.admin)
        log = AuditLog.objects.get(action=AuditLog.Action.BOARD_VIEW_CREATED, target_id=view.pk)
        self.assertEqual((log.target_type, log.metadata["board_id"]), ("board_view", self.board.pk))

    def test_orcamentos_template_brings_a_configured_kanban(self):
        board = create_board_from_template(user=self.admin, organization=self.org, key="orcamentos")
        view = board.views.get()
        columns = {column.name: column for column in board.columns.all()}
        self.assertEqual(view.name, "Kanban por Status")
        self.assertEqual(view.settings["group_by"], columns["Status"].pk)
        self.assertEqual(view.settings["sum_column"], columns["Valor"].pk)
        self.assertEqual(view.settings["card_fields"], [columns[n].pk for n in ("Cliente", "Responsável", "Prazo", "Valor")])

    def test_data_migration_gives_a_kanban_to_boards_that_have_none(self):
        migration = __import__("boards.migrations.0003_kanban_padrao_nos_quadros", fromlist=["create_default_views"])
        self.board.views.all().delete()
        migration.create_default_views(django_apps, None)
        self.assertEqual(list(self.board.views.values_list("name", flat=True)), ["Kanban"])
        migration.create_default_views(django_apps, None)  # de novo: não duplica
        self.assertEqual(self.board.views.count(), 1)


class SettingsTests(KanbanBase):
    def test_defaults_when_nothing_was_chosen(self):
        clean = clean_kanban_settings(self.columns(), {})
        self.assertEqual(clean["group_by"], None)
        self.assertTrue(clean["show_empty"])
        self.assertEqual(clean["blank_lane"], "auto")
        self.assertEqual(clean["sort"], {"by": "manual", "dir": "asc"})
        self.assertIsNone(clean["card_fields"])

    def test_group_column_falls_back_to_the_first_status_then_list(self):
        columns = self.columns()
        self.assertEqual(resolve_group_column({}, columns), self.col["status"])
        self.assertEqual(resolve_group_column({"group_by": self.col["lista"].pk}, columns), self.col["lista"])
        self.assertEqual(resolve_group_column({"group_by": 999999}, columns), self.col["status"])  # coluna que sumiu
        no_status = [c for c in columns if c.type != T.STATUS]
        self.assertEqual(resolve_group_column({}, no_status), self.col["lista"])
        self.assertIsNone(resolve_group_column({}, [c for c in columns if c.type not in (T.STATUS, T.DROPDOWN)]))

    def test_group_by_only_accepts_status_or_list_of_this_board(self):
        columns = self.columns()
        for bad in (self.col["texto"].pk, self.col["data"].pk, 999999, "abc"):
            with self.assertRaises(ValidationError, msg=bad):
                clean_kanban_settings(columns, {"group_by": bad})
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro")
        foreign = ColumnService.create(user=self.admin, board=other, column_type=T.STATUS)
        with self.assertRaises(ValidationError):
            clean_kanban_settings(columns, {"group_by": foreign.pk})
        self.assertEqual(clean_kanban_settings(columns, {"group_by": str(self.col["lista"].pk)})["group_by"], self.col["lista"].pk)
        self.assertIsNone(clean_kanban_settings(columns, {"group_by": ""})["group_by"])

    def test_sum_column_only_number_or_currency(self):
        columns = self.columns()
        self.assertEqual(clean_kanban_settings(columns, {"sum_column": self.col["moeda"].pk})["sum_column"], self.col["moeda"].pk)
        self.assertEqual(clean_kanban_settings(columns, {"sum_column": self.col["numero"].pk})["sum_column"], self.col["numero"].pk)
        with self.assertRaises(ValidationError):
            clean_kanban_settings(columns, {"sum_column": self.col["texto"].pk})
        self.assertIsNone(clean_kanban_settings(columns, {"sum_column": None})["sum_column"])

    def test_card_fields_keep_order_drop_repeats_and_refuse_strangers(self):
        columns = self.columns()
        ids = [self.col["moeda"].pk, self.col["texto"].pk, self.col["moeda"].pk]
        self.assertEqual(clean_kanban_settings(columns, {"card_fields": ids})["card_fields"], [self.col["moeda"].pk, self.col["texto"].pk])
        self.assertEqual(clean_kanban_settings(columns, {"card_fields": []})["card_fields"], [])
        self.assertIsNone(clean_kanban_settings(columns, {"card_fields": None})["card_fields"])
        for bad in ([999999], "texto", [self.col["texto"].pk, "x"]):
            with self.assertRaises(ValidationError):
                clean_kanban_settings(columns, {"card_fields": bad})
        with self.assertRaises(ValidationError):
            clean_kanban_settings(columns, {"card_fields": list(range(1, 14))})

    def test_sort_booleans_and_blank_lane_validation(self):
        columns = self.columns()
        clean = clean_kanban_settings(columns, {"sort": {"by": self.col["numero"].pk, "dir": "desc"}, "show_empty": False,
                                                "show_field_names": True, "blank_lane": "always"})
        self.assertEqual(clean["sort"], {"by": self.col["numero"].pk, "dir": "desc"})
        self.assertFalse(clean["show_empty"])
        self.assertTrue(clean["show_field_names"])
        for bad in ({"sort": {"by": "preco"}}, {"sort": {"by": "name", "dir": "up"}}, {"sort": "name"}, {"blank_lane": "talvez"},
                    {"show_empty": "talvez"}):
            with self.assertRaises(ValidationError, msg=bad):
                clean_kanban_settings(columns, bad)
        self.assertEqual(clean_kanban_settings(columns, {"sort": {"dir": "desc"}})["sort"], {"by": "manual", "dir": "desc"})

    def test_unknown_keys_are_dropped_and_current_is_kept(self):
        columns = self.columns()
        current = clean_kanban_settings(columns, {"show_field_names": True})
        clean = clean_kanban_settings(columns, {"script": "<b>", "show_empty": False}, current=current)
        self.assertNotIn("script", clean)
        self.assertTrue(clean["show_field_names"])
        self.assertFalse(clean["show_empty"])

    def test_default_card_fields_are_the_first_visible_columns_without_the_group_column(self):
        columns = self.columns()
        group = self.col["status"]
        chosen = resolve_card_columns({}, columns, group)
        self.assertEqual([c.name for c in chosen], ["Texto", "Números", "Valor", "Data"])
        ColumnService.set_visible(user=self.admin, column=self.col["numero"], visible=False)
        columns = self.columns()
        self.assertNotIn(self.col["numero"].pk, [c.pk for c in resolve_card_columns({}, columns, group)])
        # escolha explícita vale, até de coluna oculta, e ignora o que sumiu
        explicit = resolve_card_columns({"card_fields": [self.col["numero"].pk, 999999, self.col["texto"].pk]}, columns, group)
        self.assertEqual([c.pk for c in explicit], [self.col["numero"].pk, self.col["texto"].pk])

    def test_sort_choice_and_options(self):
        columns = self.columns()
        self.assertEqual(sort_choice({}, columns), ("manual", "asc"))
        self.assertEqual(sort_choice({"sort": {"by": "name", "dir": "desc"}}, columns), ("name", "desc"))
        by, direction = sort_choice({"sort": {"by": self.col["numero"].pk, "dir": "desc"}}, columns)
        self.assertEqual((by, direction), (self.col["numero"], "desc"))
        self.assertEqual(sort_choice({"sort": {"by": 999999}}, columns), ("manual", "asc"))
        options = sort_options(columns, {"sort": {"by": "created", "dir": "desc"}})
        self.assertEqual([o["value"] for o in options if o["selected"]], ["created|desc"])
        self.assertIn(f"{self.col['moeda'].pk}|asc", [o["value"] for o in options])

    def test_sum_column_helper(self):
        columns = self.columns()
        self.assertEqual(resolve_sum_column({"sum_column": self.col["moeda"].pk}, columns), self.col["moeda"])
        self.assertIsNone(resolve_sum_column({"sum_column": self.col["texto"].pk}, columns))
        self.assertIsNone(resolve_sum_column({}, columns))


class LaneTests(KanbanBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for item, status, valor, lista in ((cls.item1, cls.andamento, "1000", cls.opt_a), (cls.item2, cls.andamento, "250,5", cls.opt_b),
                                           (cls.item3, cls.concluido, "2000", None)):
            CellService.set_value(user=cls.admin, item=item, column=cls.col["status"], raw_value=status.pk)
            CellService.set_value(user=cls.admin, item=item, column=cls.col["moeda"], raw_value=valor)
            if lista:
                CellService.set_value(user=cls.admin, item=item, column=cls.col["lista"], raw_value=lista.pk)

    def test_one_lane_per_active_label_in_the_label_order(self):
        lanes = self.lanes()
        self.assertEqual([lane["label"] for lane in lanes], ["Não iniciado", "Em andamento", "Concluído"])
        self.assertEqual([lane["count"] for lane in lanes], [0, 2, 1])
        self.assertEqual([i.name for i in self.lane(lanes, "Em andamento")["items"]], ["Arena Norte", "Condomínio Cotia"])
        self.assertEqual(self.lane(lanes, "Concluído")["color"], self.concluido.color)

    def test_no_item_is_duplicated_or_lost(self):
        lanes = self.lanes()
        ids = [item.pk for lane in lanes for item in lane["items"]]
        self.assertEqual(sorted(ids), sorted(BoardItem.objects.filter(board=self.board, is_active=True).values_list("pk", flat=True)))

    def test_renaming_or_recoloring_a_label_changes_the_lane(self):
        from .services import OptionService

        OptionService.update(user=self.admin, option=self.andamento, label="Em execução", color="#E2445C")
        lane = self.lane(self.lanes(), "Em execução")
        self.assertEqual((lane["color"], lane["count"]), ("#E2445C", 2))

    def test_group_by_the_dropdown_column(self):
        lanes = self.lanes({"group_by": self.col["lista"].pk})
        self.assertEqual([lane["label"] for lane in lanes], ["Comercial", "Engenharia", "Em branco"])
        self.assertEqual([lane["count"] for lane in lanes], [1, 1, 1])
        self.assertTrue(lanes[-1]["is_blank"])

    def test_blank_lane_modes(self):
        self.assertEqual(self.lanes()[-1]["label"], "Concluído")  # status: todo item tem etiqueta, não há "Em branco"
        CellService.set_value(user=self.admin, item=self.item1, column=self.col["status"], raw_value="")
        self.assertEqual(self.lanes()[-1]["label"], "Em branco")
        self.assertEqual(self.lane(self.lanes(), "Em branco")["count"], 1)
        self.assertNotIn("Em branco", [lane["label"] for lane in self.lanes({"blank_lane": BLANK_NEVER})])
        CellService.set_value(user=self.admin, item=self.item1, column=self.col["status"], raw_value=self.andamento.pk)
        self.assertNotIn("Em branco", [lane["label"] for lane in self.lanes()])
        self.assertEqual(self.lanes({"blank_lane": BLANK_ALWAYS})[-1]["label"], "Em branco")

    def test_a_deleted_label_sends_its_items_to_the_blank_lane(self):
        from .services import OptionService

        OptionService.soft_delete(user=self.admin, option=self.concluido)
        lanes = self.lanes()
        self.assertNotIn("Concluído", [lane["label"] for lane in lanes])
        self.assertEqual([i.name for i in self.lane(lanes, "Em branco")["items"]], ["Hospital Vida"])

    def test_empty_lanes_can_be_hidden(self):
        labels = [lane["label"] for lane in self.lanes({"show_empty": False})]
        self.assertEqual(labels, ["Em andamento", "Concluído"])

    def test_sum_per_lane_is_formatted_like_the_column(self):
        lanes = self.lanes({"sum_column": self.col["moeda"].pk})
        self.assertEqual(self.lane(lanes, "Em andamento")["total"], Decimal("1250.50"))
        self.assertEqual(self.lane(lanes, "Em andamento")["total_display"], "R$ 1.250,50")
        self.assertEqual(self.lane(lanes, "Concluído")["total_display"], "R$ 2.000,00")
        self.assertEqual(self.lane(lanes, "Não iniciado")["total_display"], "")  # raia vazia não mostra "R$ 0,00"
        self.assertIsNone(self.lane(self.lanes(), "Em andamento")["total"])

    def test_filters_apply_before_distributing(self):
        lanes = self.lanes(search="hospital")
        self.assertEqual([lane["count"] for lane in lanes], [0, 0, 1])
        CellService.set_value(user=self.admin, item=self.item2, column=self.col["pessoa"], raw_value=self.ana.pk)
        lanes = self.lanes(person_id=self.ana.pk)
        self.assertEqual([i.name for i in self.lane(lanes, "Em andamento")["items"]], ["Condomínio Cotia"])

    def test_sorting_inside_each_lane(self):
        names = lambda lanes: [i.name for i in self.lane(lanes, "Em andamento")["items"]]  # noqa: E731
        self.assertEqual(names(self.lanes(sort="name", direction="desc")), ["Condomínio Cotia", "Arena Norte"])
        self.assertEqual(names(self.lanes(sort=self.col["moeda"], direction="asc")), ["Condomínio Cotia", "Arena Norte"])
        self.assertEqual(names(self.lanes(sort=self.col["moeda"], direction="desc")), ["Arena Norte", "Condomínio Cotia"])
        self.assertEqual(names(self.lanes(sort="created", direction="desc")), ["Condomínio Cotia", "Arena Norte"])
        self.assertEqual(names(self.lanes(sort="manual")), ["Arena Norte", "Condomínio Cotia"])


class ViewServiceTests(KanbanBase):
    def test_create_names_and_audit(self):
        view = ViewService.create(user=self.admin, board=self.board, name="  Kanban   Comercial ")
        self.assertEqual(view.name, "Kanban Comercial")
        self.assertEqual(ViewService.create(user=self.admin, board=self.board).name, "Kanban 2")
        self.assertEqual(ViewService.create(user=self.admin, board=self.board).name, "Kanban 3")
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.BOARD_VIEW_CREATED, target_id=view.pk).exists())

    def test_new_views_come_after_the_others(self):
        view = ViewService.create(user=self.admin, board=self.board, name="Segundo")
        self.assertEqual(list(self.board.views.filter(is_active=True).values_list("pk", flat=True)), [self.kanban.pk, view.pk])

    def test_create_with_settings_and_only_kanban_type(self):
        view = ViewService.create(user=self.admin, board=self.board, name="Por lista",
                                  settings={"group_by": self.col["lista"].pk, "card_fields": [self.col["texto"].pk]})
        self.assertEqual(view.settings["group_by"], self.col["lista"].pk)
        with self.assertRaises(BoardError):
            ViewService.create(user=self.admin, board=self.board, name="X", view_type="CALENDAR")
        with self.assertRaises(BoardError):
            ViewService.create(user=self.admin, board=self.board, name="X", settings={"group_by": self.col["texto"].pk})

    def test_only_who_edits_the_board_manages_views(self):
        for user in (self.editor, self.viewer, self.sem_acesso, self.estranho):
            with self.assertRaises(BoardPermissionError):
                ViewService.create(user=user, board=self.board, name="X")
            with self.assertRaises(BoardPermissionError):
                ViewService.update(user=user, view=self.kanban, name="X")
            with self.assertRaises(BoardPermissionError):
                ViewService.soft_delete(user=user, view=self.kanban)

    def test_update_name_and_settings_with_one_audit_per_change(self):
        ViewService.update(user=self.admin, view=self.kanban, name="Pipeline",
                           settings={"group_by": self.col["lista"].pk, "show_field_names": True})
        self.kanban.refresh_from_db()
        self.assertEqual(self.kanban.name, "Pipeline")
        self.assertEqual(self.kanban.settings["group_by"], self.col["lista"].pk)
        logs = AuditLog.objects.filter(action=AuditLog.Action.BOARD_VIEW_UPDATED, target_id=self.kanban.pk)
        self.assertEqual({log.field_name for log in logs}, {"name", "group_by", "show_field_names"})
        ViewService.update(user=self.admin, view=self.kanban, settings={"show_field_names": True})  # igual: não audita de novo
        self.assertEqual(AuditLog.objects.filter(action=AuditLog.Action.BOARD_VIEW_UPDATED, target_id=self.kanban.pk).count(), 3)

    def test_update_refuses_bad_values_and_keeps_the_old_ones(self):
        before = dict(self.kanban.settings)
        for bad in ({"group_by": self.col["texto"].pk}, {"sum_column": self.col["data"].pk}, {"card_fields": [999999]}):
            with self.assertRaises(BoardError):
                ViewService.update(user=self.admin, view=self.kanban, settings=bad)
        with self.assertRaises(BoardError):
            ViewService.update(user=self.admin, view=self.kanban, name="   ")
        self.kanban.refresh_from_db()
        self.assertEqual(self.kanban.settings, before)

    def test_soft_delete(self):
        view = ViewService.create(user=self.admin, board=self.board, name="Descartável")
        ViewService.soft_delete(user=self.admin, view=view)
        view.refresh_from_db()
        self.assertFalse(view.is_active)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.BOARD_VIEW_DELETED, target_id=view.pk).exists())

    def test_deleting_the_kanban_does_not_touch_the_items(self):
        ViewService.soft_delete(user=self.admin, view=self.kanban)
        self.assertEqual(BoardItem.objects.filter(board=self.board, is_active=True).count(), 3)


class KanbanPageTests(KanbanBase, ViewTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for item, status, valor in ((cls.item1, cls.andamento, "1000"), (cls.item2, cls.andamento, "250,5"), (cls.item3, cls.concluido, "2000")):
            CellService.set_value(user=cls.admin, item=item, column=cls.col["status"], raw_value=status.pk)
            CellService.set_value(user=cls.admin, item=item, column=cls.col["moeda"], raw_value=valor)
        CellService.set_value(user=cls.admin, item=cls.item1, column=cls.col["texto"], raw_value="Shopping Norte")

    def page(self, user=None, view=None, **params):
        if user is not None:
            self.login(user)
        return self.client.get(reverse("board-view-detail", args=[(view or self.kanban).pk]), params)

    def cards(self, response):
        return [item.name for lane in response.context["lanes"] for item in lane["items"]]

    def test_access(self):
        self.assertEqual(self.page(self.viewer).status_code, 200)
        self.assertEqual(self.page(self.sem_acesso).status_code, 403)
        self.assertEqual(self.page(self.estranho).status_code, 404)
        self.client.logout()
        self.assertEqual(self.page().status_code, 302)

    def test_deleted_view_and_deleted_board_are_404(self):
        view = ViewService.create(user=self.admin, board=self.board, name="Velha")
        ViewService.soft_delete(user=self.admin, view=view)
        self.assertEqual(self.page(self.admin, view=view).status_code, 404)
        BoardService.soft_delete(user=self.admin, board=self.board)
        self.assertEqual(self.page(self.admin).status_code, 404)

    def test_renders_lanes_cards_and_counts(self):
        response = self.page(self.viewer)
        for text in ("Não iniciado", "Em andamento", "Concluído", "Arena Norte", "Condomínio Cotia", "Hospital Vida", "Shopping Norte"):
            self.assertContains(response, text)
        self.assertEqual(self.cards(response), ["Arena Norte", "Condomínio Cotia", "Hospital Vida"])
        self.assertContains(response, 'data-lane-key="%d"' % self.andamento.pk)
        self.assertContains(response, 'style="--lane-color:#579BFC;--lane-text:#FFFFFF"')  # etiqueta azul: texto branco
        self.assertContains(response, 'id="board-meta"')
        self.assertContains(response, "js/boards.js")

    def test_tabs_on_both_pages(self):
        view = ViewService.create(user=self.admin, board=self.board, name="Kanban por Lista")
        for response in (self.page(self.viewer), self.client.get(reverse("board-detail", args=[self.board.pk]))):
            self.assertContains(response, "Quadro principal")
            self.assertContains(response, ">Kanban<")
            self.assertContains(response, "Kanban por Lista")
            self.assertContains(response, reverse("board-view-detail", args=[view.pk]))
            self.assertNotContains(response, "data-view-add")
            self.assertNotContains(response, "data-view-menu")
        response = self.page(self.admin, view=view)
        self.assertEqual(response.context["active_view"], view)
        self.assertContains(response, "data-view-add")
        self.assertContains(response, 'aria-current="page"', count=1)
        table = self.client.get(reverse("board-detail", args=[self.board.pk]))
        self.assertIsNone(table.context["active_view"])
        self.assertEqual([v.name for v in table.context["views"]], ["Kanban", "Kanban por Lista"])

    def test_controls_depend_on_the_permission(self):
        viewer = self.page(self.viewer)
        for marker in ("data-kanban-config", "data-kanban-group-by", "data-kanban-sort", "data-kanban-add", "data-card-menu", "data-lane-menu", 'draggable="true"'):
            self.assertNotContains(viewer, marker, msg_prefix=marker)
        self.assertContains(viewer, "Agrupado por")
        editor = self.page(self.editor)
        self.assertContains(editor, 'draggable="true"')
        self.assertContains(editor, "data-kanban-add")
        self.assertContains(editor, "data-card-menu")
        for marker in ("data-kanban-config", "data-kanban-group-by", "data-lane-menu"):
            self.assertNotContains(editor, marker, msg_prefix=marker)  # configurar e mexer em etiquetas é de quem edita o quadro
        admin = self.page(self.admin)
        for marker in ("data-kanban-config", "data-kanban-group-by", "data-kanban-sort", "data-lane-menu", "data-view-menu"):
            self.assertContains(admin, marker, msg_prefix=marker)

    def test_card_shows_the_chosen_fields_in_the_chosen_order(self):
        ViewService.update(user=self.admin, view=self.kanban, settings={
            "card_fields": [self.col["moeda"].pk, self.col["texto"].pk], "show_field_names": True})
        response = self.page(self.viewer)
        self.assertEqual([c.name for c in response.context["card_columns"]], ["Valor", "Texto"])
        html = response.content.decode()
        self.assertLess(html.index("R$ 1.000,00"), html.index("Shopping Norte"))
        self.assertContains(response, "<dt>Valor</dt>")
        self.assertNotContains(response, "<dt>Pessoa</dt>")

    def test_empty_field_values_are_still_clickable_placeholders(self):
        ViewService.update(user=self.admin, view=self.kanban, settings={"card_fields": [self.col["data"].pk]})
        response = self.page(self.editor)
        self.assertContains(response, 'data-type="DATE" data-value=""')
        self.assertContains(response, 'tabindex="0"')

    def test_sum_in_the_lane_header(self):
        ViewService.update(user=self.admin, view=self.kanban, settings={"sum_column": self.col["moeda"].pk})
        response = self.page(self.viewer)
        self.assertContains(response, "R$ 1.250,50")
        self.assertContains(response, "R$ 2.000,00")
        self.assertEqual(response.context["sum_column"], self.col["moeda"])

    def test_group_by_in_the_saved_view_changes_the_lanes(self):
        ViewService.update(user=self.admin, view=self.kanban, settings={"group_by": self.col["lista"].pk})
        response = self.page(self.viewer)
        self.assertEqual([lane["label"] for lane in response.context["lanes"]], ["Comercial", "Engenharia", "Em branco"])
        self.assertEqual(response.context["group_column"], self.col["lista"])

    def test_board_without_status_or_list_shows_the_hint(self):
        board = BoardService.create(user=self.admin, organization=self.org, name="Sem raias")
        view = board.views.get()
        response = self.page(self.admin, view=view)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Escolha por qual coluna agrupar")
        self.assertIsNone(response.context["group_column"])
        self.assertEqual(response.context["lanes"], [])

    def test_search_and_person_filter_use_the_url(self):
        CellService.set_value(user=self.admin, item=self.item2, column=self.col["pessoa"], raw_value=self.ana.pk)
        self.assertEqual(self.cards(self.page(self.viewer, q="hospital")), ["Hospital Vida"])
        self.assertEqual(self.cards(self.page(self.viewer, pessoa=self.ana.pk)), ["Condomínio Cotia"])
        response = self.page(self.viewer, q="nada")
        self.assertEqual(self.cards(response), [])
        self.assertTrue(response.context["filtering"])
        self.assertContains(response, "Limpar busca")
        self.assertEqual([p.username for p in self.page(self.viewer).context["people"]], ["ana"])

    def test_text_is_escaped(self):
        ItemService.rename(user=self.admin, item=self.item3, name="<script>alert(1)</script>")
        ViewService.update(user=self.admin, view=self.kanban, name="</script><b>Visão")
        html = self.page(self.viewer).content.decode()
        self.assertNotIn("<script>alert(1)", html)
        self.assertNotIn("</script><b>Visão", html)
        self.assertIn("&lt;script&gt;alert(1)", html)

    def test_meta_for_the_javascript(self):
        meta = self.page(self.admin).context["meta"]
        kanban = meta["kanban"]
        self.assertEqual(kanban["view"], {"id": self.kanban.pk, "name": "Kanban"})
        self.assertEqual(kanban["group_column_id"], self.col["status"].pk)
        self.assertEqual(kanban["default_group_id"], self.group_a.pk)
        self.assertEqual(set(kanban["groupable_ids"]), {self.col["status"].pk, self.col["lista"].pk})
        self.assertEqual(set(kanban["summable_ids"]), {self.col["numero"].pk, self.col["moeda"].pk})
        self.assertEqual(len(meta["columns"]), 8)  # todas as colunas ativas, as ocultas também
        for key in ("view_create", "view_update", "view_delete", "view_lanes", "view_detail"):
            self.assertIn(key, meta["urls"])

    def test_the_kanban_does_not_grow_with_the_number_of_cards(self):
        def count():
            self.login(self.admin)
            self.client.get(reverse("board-view-detail", args=[self.kanban.pk]))
            with CaptureQueriesContext(connection) as queries:
                self.assertEqual(self.client.get(reverse("board-view-detail", args=[self.kanban.pk])).status_code, 200)
            return len(queries)

        small = count()
        for index in range(12):
            item = ItemService.create(user=self.admin, board=self.board, group=self.group_a, name=f"Extra {index}")
            for key, value in (("texto", "x"), ("pessoa", self.ana.pk), ("moeda", "10"), ("data", "2025-10-01"), ("lista", self.opt_a.pk)):
                CellService.set_value(user=self.admin, item=item, column=self.col[key], raw_value=value)
        self.assertEqual(count(), small)


class KanbanApiTests(ViewTestCase):
    def test_create_view(self):
        data = self.api("board-view-create", [self.board.pk], {"name": "Kanban Comercial", "type": "KANBAN"}, user=self.admin).json()
        view = BoardView.objects.get(pk=data["view"]["id"])
        self.assertEqual(view.name, "Kanban Comercial")
        self.assertEqual(data["redirect_url"], reverse("board-view-detail", args=[view.pk]))
        self.assertEqual(self.api("board-view-create", [self.board.pk], {}).json()["view"]["name"], "Kanban 2")

    def test_create_view_errors(self):
        self.login(self.admin)
        self.assertEqual(self.api("board-view-create", [self.board.pk], {"type": "CALENDAR"}).status_code, 400)
        self.assertEqual(self.api("board-view-create", [self.board.pk], {"settings": "x"}).status_code, 400)
        self.assertEqual(self.api("board-view-create", [self.board.pk], {"settings": {"group_by": self.col["texto"].pk}}).status_code, 400)

    def test_update_view_returns_the_full_settings(self):
        data = self.api("board-view-update", [self.kanban.pk], {"name": "Pipeline", "settings": {"show_empty": False}}, user=self.admin).json()
        self.assertEqual(data["view"], {"id": self.kanban.pk, "name": "Pipeline"})
        self.assertFalse(data["settings"]["show_empty"])
        self.assertEqual(data["settings"]["blank_lane"], "auto")  # o que não foi tocado vem com o padrão
        bad = self.api("board-view-update", [self.kanban.pk], {"settings": {"sort": {"by": "preco"}}})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.api("board-view-update", [self.kanban.pk], {"name": "  "}).status_code, 400)

    def test_delete_view(self):
        view = ViewService.create(user=self.admin, board=self.board, name="Temporária")
        data = self.api("board-view-delete", [view.pk], user=self.admin).json()
        self.assertEqual(data, {"ok": True, "redirect_url": reverse("board-detail", args=[self.board.pk])})
        self.assertFalse(BoardView.objects.get(pk=view.pk).is_active)

    def test_who_cannot_edit_the_board_cannot_manage_views(self):
        for user in (self.editor, self.viewer, self.sem_acesso):
            self.login(user)
            self.assertEqual(self.api("board-view-create", [self.board.pk], {"name": "X"}).status_code, 403)
            self.assertEqual(self.api("board-view-update", [self.kanban.pk], {"name": "X"}).status_code, 403)
            self.assertEqual(self.api("board-view-update", [self.kanban.pk], {}).status_code, 403)  # nem sem nada a gravar
            self.assertEqual(self.api("board-view-delete", [self.kanban.pk]).status_code, 403)
        self.kanban.refresh_from_db()
        self.assertEqual((self.kanban.name, self.kanban.is_active), ("Kanban", True))

    def test_other_organization_gets_404_on_every_view_endpoint(self):
        self.login(self.estranho)
        cases = [("board-view-create", [self.board.pk]), ("board-view-update", [self.kanban.pk]),
                 ("board-view-delete", [self.kanban.pk]), ("board-view-lanes", [self.kanban.pk])]
        for name, args in cases:
            self.assertEqual(self.api(name, args, {"name": "Hackeada"}).status_code, 404, name)
        self.kanban.refresh_from_db()
        self.assertEqual((self.kanban.name, self.kanban.is_active), ("Kanban", True))

    def test_lanes_fragment(self):
        CellService.set_value(user=self.admin, item=self.item1, column=self.col["status"], raw_value=self.andamento.pk)
        data = self.api("board-view-lanes", [self.kanban.pk], {}, user=self.viewer).json()
        self.assertTrue(data["ok"])
        self.assertIn("data-lane", data["lanes_html"])
        self.assertIn("Arena Norte", data["lanes_html"])
        self.assertEqual(data["total_items"], 3)
        self.assertEqual(data["group_column_id"], self.col["status"].pk)
        self.assertEqual(len(data["columns"]), 8)
        self.assertEqual(data["settings"]["blank_lane"], "auto")
        self.assertIn("card_column_ids", data)

    def test_lanes_fragment_honors_the_filters_and_the_permission(self):
        data = self.api("board-view-lanes", [self.kanban.pk], {"q": "hospital"}, user=self.viewer).json()
        self.assertEqual(data["total_items"], 1)
        self.assertNotIn("Arena Norte", data["lanes_html"])
        self.assertEqual(self.api("board-view-lanes", [self.kanban.pk], {}, user=self.sem_acesso).status_code, 403)

    def test_lanes_fragment_follows_a_setting_change(self):
        self.api("board-view-update", [self.kanban.pk], {"settings": {"group_by": self.col["lista"].pk}}, user=self.admin)
        data = self.api("board-view-lanes", [self.kanban.pk], {}).json()
        self.assertEqual(data["group_column_id"], self.col["lista"].pk)
        self.assertIn("Engenharia", data["lanes_html"])

    # -- cartão: mover = gravar a etiqueta (o mesmo endpoint da célula) -----------------------------------

    def test_dragging_a_card_is_a_cell_update_of_the_group_column(self):
        data = self.api("board-cell-update", [self.item1.pk, self.col["status"].pk], {"value": self.concluido.pk}, user=self.editor).json()
        self.assertTrue(data["ok"])
        lanes = self.api("board-view-lanes", [self.kanban.pk], {}).json()["lanes_html"]
        concluded = lanes.split('data-lane-key="%d"' % self.concluido.pk)[1].split("</section>")[0]
        self.assertIn("Arena Norte", concluded)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.BOARD_CELL_UPDATED, new_value="Concluído",
                                                metadata__item_id=self.item1.pk).exists())

    def test_dropping_on_the_blank_lane_clears_the_label(self):
        data = self.api("board-cell-update", [self.item1.pk, self.col["status"].pk], {"value": ""}, user=self.editor).json()
        self.assertEqual(data["display"], "")
        self.assertIn('data-lane-key="blank"', self.api("board-view-lanes", [self.kanban.pk], {}).json()["lanes_html"])

    def test_a_required_group_column_refuses_the_blank_lane_and_keeps_the_card(self):
        ColumnService.update_common(user=self.admin, column=self.col["status"], is_required=True)
        response = self.api("board-cell-update", [self.item1.pk, self.col["status"].pk], {"value": ""}, user=self.editor)
        self.assertEqual(response.status_code, 400)
        self.assertIn("obrigatória", response.json()["error"])

    def test_a_viewer_cannot_drag(self):
        response = self.api("board-cell-update", [self.item1.pk, self.col["status"].pk], {"value": self.concluido.pk}, user=self.viewer)
        self.assertEqual(response.status_code, 403)

    # -- criar o cartão já dentro da raia --------------------------------------------------------------

    def test_create_item_inside_a_lane_fills_the_group_column(self):
        data = self.api("board-item-create", [self.board.pk], {
            "group_id": self.group_a.pk, "name": "Novo", "initial": {"column_id": self.col["status"].pk, "value": self.concluido.pk}},
            user=self.editor).json()
        item = BoardItem.objects.get(pk=data["item"]["id"])
        cell = item.cells.get(column=self.col["status"])
        self.assertEqual(cell.option_values.get().option, self.concluido)
        self.assertEqual(item.cells.filter(column=self.col["status"]).count(), 1)

    def test_create_item_inside_the_blank_lane(self):
        data = self.api("board-item-create", [self.board.pk], {
            "group_id": self.group_a.pk, "initial": {"column_id": self.col["status"].pk, "value": ""}}, user=self.editor).json()
        cell = BoardItem.objects.get(pk=data["item"]["id"]).cells.get(column=self.col["status"])
        self.assertFalse(cell.option_values.exists())

    def test_create_item_with_a_bad_initial_value_creates_nothing(self):
        before = BoardItem.objects.count()
        self.login(self.editor)
        bad = self.api("board-item-create", [self.board.pk], {
            "group_id": self.group_a.pk, "initial": {"column_id": self.col["status"].pk, "value": self.opt_a.pk}})  # etiqueta de outra coluna
        self.assertEqual(bad.status_code, 400)
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro")
        foreign = ColumnService.create(user=self.admin, board=other, column_type=T.TEXT)
        self.assertEqual(self.api("board-item-create", [self.board.pk], {
            "group_id": self.group_a.pk, "initial": {"column_id": foreign.pk, "value": "x"}}).status_code, 404)
        self.assertEqual(self.api("board-item-create", [self.board.pk], {"group_id": self.group_a.pk, "initial": "x"}).status_code, 400)
        self.assertEqual(BoardItem.objects.count(), before)  # tudo ou nada

    def test_create_item_in_a_lane_needs_both_permissions(self):
        from acessos import catalog
        from activities.testing import make_user

        only_create = make_user("soCria", self.org, [catalog.QUADRO_VISUALIZAR, catalog.QUADRO_CRIAR_ITEM])
        before = BoardItem.objects.count()
        response = self.api("board-item-create", [self.board.pk], {
            "group_id": self.group_a.pk, "initial": {"column_id": self.col["status"].pk, "value": self.concluido.pk}}, user=only_create)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(BoardItem.objects.count(), before)


class JsonSafetyTests(ViewTestCase):
    def test_view_endpoints_accept_only_post_and_json_objects(self):
        self.login(self.admin)
        for name, args in (("board-view-create", [self.board.pk]), ("board-view-update", [self.kanban.pk]),
                           ("board-view-delete", [self.kanban.pk]), ("board-view-lanes", [self.kanban.pk])):
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 405, name)
        self.assertEqual(self.api("board-view-update", [self.kanban.pk], raw="{nope").status_code, 400)
        self.assertEqual(self.api("board-view-lanes", [self.kanban.pk], raw="[1]").status_code, 400)
        self.assertEqual(json.loads(self.api("board-view-update", [self.kanban.pk], raw="").content)["ok"], True)
