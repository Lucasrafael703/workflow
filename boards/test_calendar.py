"""Visualização Calendário: configuração, grade do mês, serviço de visualizações, telas e API.

Referência fixa: outubro de 2026 começa numa quinta-feira, então a grade vai de segunda 28/09 a domingo 01/11 (5 semanas).
"""

import datetime

from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from audit.models import AuditLog

from .calendar_view import (
    MAX_VISIBLE_PER_DAY,
    build_month,
    clean_calendar_settings,
    complete_new_settings,
    grid_range,
    parse_month,
    resolve_card_columns,
    resolve_color_source,
    resolve_date_column,
    resolve_status_column,
    shift_month,
)
from .models import BoardColumn, BoardItem, BoardView
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
from .test_views import ViewTestCase
from .testing import BoardTestCase

T = BoardColumn.Type
D = datetime.date


class CalendarBase(ViewTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.cal = ViewService.create(user=cls.admin, board=cls.board, view_type="CALENDAR")

    def columns(self):
        return list(BoardQueryService.columns(self.board, visible=None))

    def page(self, user=None, view=None, **params):
        if user is not None:
            self.login(user)
        params.setdefault("mes", "2026-10")
        return self.client.get(reverse("board-view-detail", args=[(view or self.cal).pk]), params)

    def day(self, response, iso):
        for week in response.context["calendar"]["weeks"]:
            for day in week:
                if day["iso"] == iso:
                    return day
        raise AssertionError(f"dia {iso} não está na grade")

    def titles(self, response, iso):
        return [entry["item"].name for entry in self.day(response, iso)["entries"]]

    def put(self, item, key, value):
        return CellService.set_value(user=self.admin, item=item, column=self.col[key], raw_value=value)

    def show_time(self, on=True):
        ColumnService.update_settings(user=self.admin, column=self.col["data"], settings={"show_time": on})

    def deadline(self, on=True):
        ColumnService.update_settings(user=self.admin, column=self.col["data"], settings={"is_deadline": on})

    def configure(self, **settings):
        ViewService.update(user=self.admin, view=self.cal, settings=settings)
        self.cal.refresh_from_db()


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------


class SettingsTests(CalendarBase):
    def test_defaults(self):
        clean = clean_calendar_settings(self.columns(), {})
        self.assertEqual(
            clean,
            {"date_field": None, "period": "month", "color_by": None, "card_fields": None,
             "show_weekends": True, "show_completed": True},
        )

    def test_date_field_only_accepts_a_date_column_of_this_board(self):
        columns = self.columns()
        self.assertEqual(clean_calendar_settings(columns, {"date_field": str(self.col["data"].pk)})["date_field"], self.col["data"].pk)
        self.assertIsNone(clean_calendar_settings(columns, {"date_field": ""})["date_field"])
        for bad in (self.col["texto"].pk, self.col["status"].pk, 999999, "abc"):
            with self.assertRaises(ValidationError, msg=bad):
                clean_calendar_settings(columns, {"date_field": bad})
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro")
        foreign = ColumnService.create(user=self.admin, board=other, column_type=T.DATE)
        with self.assertRaises(ValidationError):
            clean_calendar_settings(columns, {"date_field": foreign.pk})

    def test_period_only_month_for_now(self):
        columns = self.columns()
        self.assertEqual(clean_calendar_settings(columns, {"period": "month"})["period"], "month")
        for bad in ("week", "day", "agenda", "", None):
            with self.assertRaises(ValidationError, msg=bad):
                clean_calendar_settings(columns, {"period": bad})

    def test_color_by_accepts_status_list_group_or_none(self):
        columns = self.columns()
        for good in (self.col["status"].pk, str(self.col["lista"].pk), "group", "none"):
            self.assertIsNotNone(clean_calendar_settings(columns, {"color_by": good})["color_by"])
        self.assertIsNone(clean_calendar_settings(columns, {"color_by": ""})["color_by"])
        for bad in (self.col["texto"].pk, self.col["pessoa"].pk, self.col["data"].pk, 999999, "cor"):
            with self.assertRaises(ValidationError, msg=bad):
                clean_calendar_settings(columns, {"color_by": bad})

    def test_card_fields_are_validated_like_the_kanban(self):
        columns = self.columns()
        ids = [self.col["moeda"].pk, self.col["texto"].pk, self.col["moeda"].pk]
        self.assertEqual(clean_calendar_settings(columns, {"card_fields": ids})["card_fields"], [self.col["moeda"].pk, self.col["texto"].pk])
        self.assertEqual(clean_calendar_settings(columns, {"card_fields": []})["card_fields"], [])
        self.assertIsNone(clean_calendar_settings(columns, {"card_fields": None})["card_fields"])
        for bad in ("x", 5, {"a": 1}, [999999]):
            with self.assertRaises(ValidationError, msg=bad):
                clean_calendar_settings(columns, {"card_fields": bad})
        with self.assertRaises(ValidationError):
            clean_calendar_settings(columns, {"card_fields": [column.pk for column in columns][:7]})

    def test_booleans_and_unknown_keys(self):
        columns = self.columns()
        clean = clean_calendar_settings(columns, {"show_weekends": False, "show_completed": "false", "script": "<b>", "group_by": 1})
        self.assertFalse(clean["show_weekends"])
        self.assertFalse(clean["show_completed"])
        self.assertNotIn("script", clean)
        self.assertNotIn("group_by", clean)  # chave do Kanban não vale aqui
        with self.assertRaises(ValidationError):
            clean_calendar_settings(columns, {"show_weekends": "talvez"})

    def test_current_is_kept_and_only_sent_keys_change(self):
        columns = self.columns()
        current = clean_calendar_settings(columns, {"show_weekends": False, "color_by": "group"})
        clean = clean_calendar_settings(columns, {"show_completed": False}, current=current)
        self.assertEqual((clean["show_weekends"], clean["color_by"], clean["show_completed"]), (False, "group", False))


class ResolverTests(CalendarBase):
    def test_date_column_prefers_the_choice_then_the_deadline_then_the_first(self):
        columns = self.columns()
        self.assertEqual(resolve_date_column({}, columns), self.col["data"])
        second = ColumnService.create(user=self.admin, board=self.board, column_type=T.DATE)
        ColumnService.update_settings(user=self.admin, column=second, settings={"is_deadline": True})
        columns = self.columns()
        self.assertEqual(resolve_date_column({}, columns), second)  # a marcada como prazo ganha da primeira
        self.assertEqual(resolve_date_column({"date_field": self.col["data"].pk}, columns), self.col["data"])
        self.assertEqual(resolve_date_column({"date_field": 999999}, columns), second)  # coluna que sumiu
        self.assertIsNone(resolve_date_column({}, [c for c in columns if c.type != T.DATE]))

    def test_status_column_is_the_first_status_only(self):
        columns = self.columns()
        self.assertEqual(resolve_status_column(columns), self.col["status"])
        self.assertIsNone(resolve_status_column([c for c in columns if c.type != T.STATUS]))

    def test_color_source(self):
        columns = self.columns()
        self.assertEqual(resolve_color_source({}, columns), ("column", self.col["status"]))
        self.assertEqual(resolve_color_source({"color_by": self.col["lista"].pk}, columns), ("column", self.col["lista"]))
        self.assertEqual(resolve_color_source({"color_by": "group"}, columns), ("group", None))
        self.assertEqual(resolve_color_source({"color_by": "none"}, columns), ("none", None))
        self.assertEqual(resolve_color_source({"color_by": 999999}, columns), ("column", self.col["status"]))
        no_labels = [c for c in columns if c.type not in (T.STATUS, T.DROPDOWN)]
        self.assertEqual(resolve_color_source({}, no_labels), ("group", None))  # sem etiquetas, a cor do grupo

    def test_default_card_fields_put_the_color_column_and_a_person_first(self):
        columns = self.columns()
        chosen = resolve_card_columns({}, columns, self.col["data"], self.col["status"])
        self.assertEqual(chosen, [self.col["status"], self.col["pessoa"], self.col["texto"]])
        self.assertNotIn(self.col["data"], chosen)
        self.assertLessEqual(len(chosen), 3)

    def test_default_card_fields_skip_hidden_columns_and_follow_explicit_choice(self):
        ColumnService.set_visible(user=self.admin, column=self.col["texto"], visible=False)
        columns = self.columns()
        chosen = resolve_card_columns({}, columns, self.col["data"], self.col["status"])
        self.assertNotIn(self.col["texto"], chosen)
        explicit = resolve_card_columns({"card_fields": [self.col["moeda"].pk, self.col["texto"].pk]}, columns, self.col["data"], None)
        self.assertEqual(explicit, [self.col["moeda"], self.col["texto"]])  # a escolha vale mesmo para coluna oculta

    def test_complete_new_settings_freezes_the_resolved_columns(self):
        clean = complete_new_settings(self.columns(), {})
        self.assertEqual((clean["date_field"], clean["color_by"]), (self.col["data"].pk, self.col["status"].pk))

    def test_complete_new_settings_needs_a_date_column(self):
        with self.assertRaisesMessage(ValidationError, "coluna de Data"):
            complete_new_settings([c for c in self.columns() if c.type != T.DATE], {})


class PeriodTests(BoardTestCase):
    def test_parse_month(self):
        self.assertEqual(parse_month("2026-10"), (2026, 10))
        self.assertEqual(parse_month("2026-1"), (2026, 1))
        today = D(2026, 3, 9)
        for bad in (None, "", "abc", "2026-13", "2026-00", "1800-05", "2026-10-01", "../etc"):
            self.assertEqual(parse_month(bad, today), (2026, 3), bad)

    def test_shift_month_crosses_years(self):
        self.assertEqual(shift_month(2026, 12, 1), (2027, 1))
        self.assertEqual(shift_month(2026, 1, -1), (2025, 12))
        self.assertEqual(shift_month(2026, 10, 0), (2026, 10))

    def test_grid_range_covers_whole_weeks(self):
        self.assertEqual(grid_range(2026, 10), (D(2026, 9, 28), D(2026, 11, 1)))
        self.assertEqual(grid_range(2026, 6), (D(2026, 6, 1), D(2026, 7, 5)))  # junho/2026 começa numa segunda
        self.assertEqual(grid_range(2024, 2), (D(2024, 1, 29), D(2024, 3, 3)))  # ano bissexto


# ---------------------------------------------------------------------------
# Grade
# ---------------------------------------------------------------------------


class GridTests(CalendarBase):
    def setUp(self):
        super().setUp()
        self.put(self.item1, "data", "2026-10-15")
        self.put(self.item2, "data", "2026-10-15")
        # item3 fica sem data

    def test_each_item_is_on_its_own_day_once(self):
        response = self.page(self.viewer)
        self.assertEqual(self.titles(response, "2026-10-15"), ["Arena Norte", "Condomínio Cotia"])
        total = sum(len(day["entries"]) for week in response.context["calendar"]["weeks"] for day in week)
        self.assertEqual(total, 2)
        self.assertEqual(response.context["calendar"]["total"], 2)

    def test_grid_has_five_weeks_of_seven_and_marks_outside_days(self):
        calendar = self.page(self.viewer).context["calendar"]
        self.assertEqual([len(week) for week in calendar["weeks"]], [7] * 5)
        self.assertEqual(calendar["weekdays"], ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"])
        first, last = calendar["weeks"][0][0], calendar["weeks"][-1][-1]
        self.assertEqual((first["iso"], first["in_month"]), ("2026-09-28", False))
        self.assertEqual((last["iso"], last["in_month"]), ("2026-11-01", False))
        self.assertTrue(calendar["weeks"][0][3]["in_month"])  # quinta, dia 1
        self.assertTrue(calendar["weeks"][0][3]["show_month"])

    def test_item_on_a_day_of_the_adjacent_month_shows_up_in_the_margin(self):
        self.put(self.item3, "data", "2026-11-01")
        self.assertEqual(self.titles(self.page(self.viewer), "2026-11-01"), ["Hospital Vida"])

    def test_only_the_grid_range_is_loaded(self):
        self.put(self.item3, "data", "2026-12-20")
        response = self.page(self.viewer)
        self.assertEqual(response.context["calendar"]["total"], 2)
        february = self.page(self.viewer, mes="2026-12")
        self.assertEqual(self.titles(february, "2026-12-20"), ["Hospital Vida"])
        self.assertEqual(february.context["calendar"]["total"], 1)

    def test_items_without_a_date_are_counted_and_listed(self):
        response = self.page(self.viewer)
        self.assertEqual(response.context["nodate_count"], 1)
        self.assertEqual([item.name for item in response.context["nodate_items"]], ["Hospital Vida"])
        self.assertContains(response, 'data-cal-panel-open="nodate"')
        self.put(self.item3, "data", "2026-10-18")
        response = self.page(self.viewer)
        self.assertEqual(response.context["nodate_count"], 0)
        self.assertEqual(self.titles(response, "2026-10-18"), ["Hospital Vida"])

    def test_clearing_the_date_takes_the_item_out_of_the_grid_but_not_out_of_the_board(self):
        self.put(self.item1, "data", "")
        response = self.page(self.viewer)
        self.assertEqual(self.titles(response, "2026-10-15"), ["Condomínio Cotia"])
        self.assertEqual(response.context["nodate_count"], 2)
        self.assertTrue(BoardItem.objects.get(pk=self.item1.pk).is_active)

    def test_all_day_items_come_before_timed_ones_and_time_is_never_invented(self):
        self.show_time()
        self.put(self.item1, "data", "2026-10-15T14:00")
        self.put(self.item3, "data", "2026-10-15T09:30")
        day = self.day(self.page(self.viewer), "2026-10-15")
        self.assertEqual([(e["item"].name, e["time"]) for e in day["entries"]],
                         [("Condomínio Cotia", ""), ("Hospital Vida", "09:30"), ("Arena Norte", "14:00")])
        self.assertContains(self.page(self.viewer), 'data-time="14:00"')

    def test_time_is_shown_in_the_local_timezone(self):
        self.show_time()
        self.put(self.item1, "data", "2026-10-15T23:30")  # horário de Brasília, que é o fuso do projeto
        entry = self.day(self.page(self.viewer), "2026-10-15")["entries"][-1]
        self.assertEqual((entry["item"].name, entry["time"]), ("Arena Norte", "23:30"))

    def test_a_column_that_does_not_show_time_never_shows_one(self):
        self.put(self.item1, "data", "2026-10-15T14:00")  # a coluna não tem horário: grava só o dia
        self.assertEqual([e["time"] for e in self.day(self.page(self.viewer), "2026-10-15")["entries"]], ["", ""])

    def test_many_items_on_one_day_overflow_into_more(self):
        for index in range(4):
            item = ItemService.create(user=self.admin, board=self.board, group=self.group_a, name=f"Extra {index}")
            self.put(item, "data", "2026-10-15")
        response = self.page(self.viewer)
        day = self.day(response, "2026-10-15")
        self.assertEqual(len(day["entries"]), 6)
        self.assertEqual(day["more"], 6 - MAX_VISIBLE_PER_DAY)
        self.assertEqual([entry["overflow"] for entry in day["entries"]], [False] * 3 + [True] * 3)
        self.assertContains(response, "+ 3 mais")
        self.assertContains(response, "is-overflow", count=3)

    def test_empty_month_shows_the_hint_and_is_not_an_error(self):
        response = self.page(self.viewer, mes="2027-02")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum item neste período.")
        self.assertContains(response, "Passe o mouse sobre um dia para adicionar.")
        self.assertNotContains(self.page(self.viewer), "Nenhum item neste período.")

    def test_today_is_highlighted(self):
        month = build_month(
            2026, 10, [], date_column=self.col["data"], status_column=self.col["status"], color_kind="column",
            color_column=self.col["status"], card_columns=[], today=D(2026, 10, 15),
        )
        flags = [(day["iso"], day["is_today"]) for week in month["weeks"] for day in week if day["is_today"]]
        self.assertEqual(flags, [("2026-10-15", True)])
        self.assertTrue(month["is_current"])

    def test_item_on_a_date_far_in_the_past_still_loads_in_its_month(self):
        self.put(self.item3, "data", "2020-01-15")
        response = self.page(self.viewer, mes="2020-01")
        self.assertEqual(self.titles(response, "2020-01-15"), ["Hospital Vida"])


class WeekendTests(CalendarBase):
    def setUp(self):
        super().setUp()
        self.put(self.item1, "data", "2026-10-17")  # sábado
        self.put(self.item2, "data", "2026-10-16")  # sexta

    def test_hiding_weekends_removes_the_columns_but_not_the_data(self):
        self.configure(show_weekends=False)
        response = self.page(self.viewer)
        calendar = response.context["calendar"]
        self.assertEqual(calendar["weekdays"], ["Seg", "Ter", "Qua", "Qui", "Sex"])
        self.assertEqual([len(week) for week in calendar["weeks"]], [5] * 5)
        self.assertEqual(self.titles(response, "2026-10-16"), ["Condomínio Cotia"])
        self.assertEqual(calendar["hidden_weekend"], 1)
        self.assertContains(response, "1 item em fim de semana oculto")
        self.assertEqual(CellService.display_value(
            BoardQueryService.with_cells(BoardItem.objects.filter(pk=self.item1.pk)).get().cells.get(column=self.col["data"])), "17/10/2026")

    def test_the_notice_offers_the_toggle_only_to_whoever_can_edit_the_view(self):
        self.configure(show_weekends=False)
        self.assertContains(self.page(self.admin), "data-cal-show-weekends")
        self.assertNotContains(self.page(self.viewer), "data-cal-show-weekends")
        self.assertContains(self.page(self.viewer), "1 item em fim de semana oculto")

    def test_weekends_shown_by_default(self):
        response = self.page(self.viewer)
        self.assertEqual(self.titles(response, "2026-10-17"), ["Arena Norte"])
        self.assertEqual(response.context["calendar"]["hidden_weekend"], 0)

    def test_blocked_days_when_the_column_refuses_weekends(self):
        ColumnService.update_settings(user=self.admin, column=self.col["data"], settings={"allow_weekends": False})
        response = self.page(self.editor)
        self.assertTrue(self.day(response, "2026-10-17")["blocked"])
        self.assertTrue(self.day(response, "2026-10-18")["blocked"])
        self.assertFalse(self.day(response, "2026-10-16")["blocked"])
        self.assertContains(response, "is-blocked")


class CompletedAndOverdueTests(CalendarBase):
    def setUp(self):
        super().setUp()
        self.put(self.item1, "data", "2020-01-10")
        self.put(self.item2, "data", "2020-01-10")
        self.put(self.item3, "data", "2020-01-12")
        self.put(self.item2, "status", self.concluido.pk)

    def test_overdue_needs_a_deadline_column_and_an_open_item(self):
        self.assertEqual(self.page(self.viewer, mes="2020-01").context["overdue_count"], 0)  # a coluna não é prazo
        self.deadline()
        response = self.page(self.viewer, mes="2020-01")
        entries = {e["item"].name: e for e in self.day(response, "2020-01-10")["entries"]}
        self.assertTrue(entries["Arena Norte"]["overdue"])
        self.assertFalse(entries["Condomínio Cotia"]["overdue"])  # concluído não está atrasado
        self.assertEqual(response.context["overdue_count"], 2)
        self.assertEqual([i.name for i in response.context["overdue_items"]], ["Arena Norte", "Hospital Vida"])
        self.assertContains(response, "Atrasada")
        self.assertContains(response, 'data-cal-panel-open="overdue"')

    def test_overdue_list_does_not_depend_on_the_month_being_looked_at(self):
        self.deadline()
        self.assertEqual(self.page(self.viewer, mes="2027-05").context["overdue_count"], 2)

    def test_future_dates_are_not_overdue(self):
        self.deadline()
        self.put(self.item1, "data", "2099-01-10")
        self.assertEqual(self.page(self.viewer, mes="2099-01").context["overdue_count"], 1)  # só o Hospital Vida

    def test_hiding_completed_is_a_view_filter_only(self):
        self.configure(show_completed=False)
        response = self.page(self.viewer, mes="2020-01")
        self.assertEqual(self.titles(response, "2020-01-10"), ["Arena Norte"])
        self.assertEqual(BoardItem.objects.filter(board=self.board, is_active=True).count(), 3)
        self.configure(show_completed=True)
        self.assertEqual(self.titles(self.page(self.viewer, mes="2020-01"), "2020-01-10"), ["Arena Norte", "Condomínio Cotia"])

    def test_completed_is_decided_by_the_status_column_only(self):
        # "Concluído" de uma Lista suspensa não esconde o item: só o Status conta
        self.configure(show_completed=False)
        done_option = self.col["lista"].options.first()
        done_option.is_done = True
        done_option.save()
        self.put(self.item1, "lista", done_option.pk)
        self.assertIn("Arena Norte", self.titles(self.page(self.viewer, mes="2020-01"), "2020-01-10"))


class ColorTests(CalendarBase):
    def setUp(self):
        super().setUp()
        self.put(self.item1, "data", "2026-10-15")
        self.put(self.item1, "status", self.andamento.pk)
        self.put(self.item1, "lista", self.opt_b.pk)

    def entry(self, **params):
        return self.day(self.page(self.viewer, **params), "2026-10-15")["entries"][0]

    def test_default_color_is_the_status_option_and_the_text_says_it(self):
        entry = self.entry()
        self.assertEqual((entry["color"], entry["color_label"]), (self.andamento.color, "Status: Em andamento"))
        self.assertContains(self.page(self.viewer), "Status: Em andamento")  # nunca só a cor

    def test_color_by_another_column_group_or_none(self):
        self.configure(color_by=self.col["lista"].pk)
        self.assertEqual(self.entry()["color"], self.opt_b.color)
        self.configure(color_by="group")
        entry = self.entry()
        self.assertEqual((entry["color"], entry["color_label"]), (self.group_a.color, "Grupo: Oportunidades"))
        self.configure(color_by="none")
        self.assertEqual(self.entry()["color_label"], "")

    def test_changing_the_color_or_the_name_of_the_option_reflects_at_once(self):
        from .services import OptionService
        OptionService.update(user=self.admin, option=self.andamento, label="Em execução", color="#112233")
        entry = self.entry()
        self.assertEqual((entry["color"], entry["color_label"]), ("#112233", "Status: Em execução"))
        self.assertContains(self.page(self.viewer), "Em execução")

    def test_changing_how_to_color_changes_no_item(self):
        before = list(BoardItem.objects.order_by("pk").values_list("pk", "name", "updated_at"))
        self.configure(color_by="group")
        self.assertEqual(before, list(BoardItem.objects.order_by("pk").values_list("pk", "name", "updated_at")))

    def test_item_without_a_label_gets_the_neutral_color(self):
        self.put(self.item1, "status", "")
        entry = self.entry()
        self.assertEqual(entry["color"], "#C4C4C4")
        self.assertEqual(entry["color_label"], "Status: sem etiqueta")


class CardTests(CalendarBase):
    def setUp(self):
        super().setUp()
        self.put(self.item1, "data", "2026-10-15")
        self.put(self.item1, "pessoa", self.ana.pk)
        self.put(self.item1, "texto", "Shopping Norte")

    def test_card_shows_only_filled_chosen_fields_in_order(self):
        self.configure(card_fields=[self.col["texto"].pk, self.col["pessoa"].pk, self.col["moeda"].pk])
        entry = self.day(self.page(self.viewer), "2026-10-15")["entries"][0]
        self.assertEqual([f["column"].name for f in entry["fields"]], ["Texto", "Pessoa"])  # Valor está vazio: não aparece
        html = self.page(self.viewer).content.decode()
        card = html[html.index("cal-card__fields"):]  # a lista de pessoas do filtro também traz "Ana Souza"
        self.assertLess(card.index("Shopping Norte"), card.index("Ana Souza"))

    def test_card_fields_are_editable_only_with_permission(self):
        self.assertContains(self.page(self.editor), 'data-cell data-item-id="%d"' % self.item1.pk)
        self.assertContains(self.page(self.editor), 'draggable="true"')
        viewer = self.page(self.viewer)
        self.assertNotContains(viewer, 'draggable="true"')
        self.assertNotContains(viewer, "is-editable")

    def test_empty_card_field_list_shows_the_title_alone(self):
        self.configure(card_fields=[])
        self.assertEqual(self.day(self.page(self.viewer), "2026-10-15")["entries"][0]["fields"], [])

    def test_item_without_a_title(self):
        ItemService.rename(user=self.admin, item=self.item1, name="")
        self.assertContains(self.page(self.viewer), "Sem título")

    def test_text_is_escaped(self):
        ItemService.rename(user=self.admin, item=self.item1, name="<script>alert(1)</script>")
        ViewService.update(user=self.admin, view=self.cal, name="</script><b>Visão")
        html = self.page(self.viewer).content.decode()
        self.assertNotIn("<script>alert(1)", html)
        self.assertNotIn("</script><b>Visão", html)
        self.assertIn("&lt;script&gt;alert(1)", html)


class FilterTests(CalendarBase):
    def setUp(self):
        super().setUp()
        for item in (self.item1, self.item2, self.item3):
            self.put(item, "data", "2026-10-15")
        self.put(self.item2, "pessoa", self.ana.pk)

    def test_search_filters_the_visible_items(self):
        self.assertEqual(self.titles(self.page(self.viewer, q="hospital"), "2026-10-15"), ["Hospital Vida"])
        response = self.page(self.viewer, q="nada")
        self.assertEqual(self.titles(response, "2026-10-15"), [])
        self.assertTrue(response.context["filtering"])

    def test_person_filter_and_combination(self):
        self.assertEqual(self.titles(self.page(self.viewer, pessoa=self.ana.pk), "2026-10-15"), ["Condomínio Cotia"])
        self.assertEqual(self.titles(self.page(self.viewer, pessoa=self.ana.pk, q="hospital"), "2026-10-15"), [])

    def test_filters_do_not_change_the_data(self):
        self.page(self.viewer, q="hospital")
        self.assertEqual(self.titles(self.page(self.viewer), "2026-10-15"), ["Arena Norte", "Condomínio Cotia", "Hospital Vida"])

    def test_month_links_keep_the_filters(self):
        html = self.page(self.viewer, q="Arena", pessoa=self.ana.pk).content.decode()
        self.assertIn("?mes=2026-11&amp;q=Arena&amp;pessoa=%d" % self.ana.pk, html)
        self.assertIn("?mes=2026-09&amp;q=Arena", html)

    def test_filters_also_apply_to_the_no_date_list(self):
        self.put(self.item3, "data", "")
        self.assertEqual(self.page(self.viewer).context["nodate_count"], 1)
        self.assertEqual(self.page(self.viewer, q="arena").context["nodate_count"], 0)


class NavigationTests(CalendarBase):
    def test_title_prev_next_and_today(self):
        response = self.page(self.viewer)
        self.assertEqual(response.context["month_title"], "outubro 2026")
        self.assertEqual((response.context["prev_month"], response.context["next_month"]), ("2026-09", "2026-11"))
        december = self.page(self.viewer, mes="2026-12")
        self.assertEqual(december.context["next_month"], "2027-01")
        self.assertContains(december, "dezembro 2026")

    def test_invalid_month_falls_back_to_the_current_month(self):
        response = self.page(self.viewer, mes="lixo")
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.context["month_key"], r"^\d{4}-\d{2}$")

    def test_scale_select_only_offers_month_for_now(self):
        html = self.page(self.viewer).content.decode()
        self.assertIn('<option value="month" selected>Mês</option>', html)
        for scale in ("week", "day", "agenda"):
            self.assertIn('<option value="%s" disabled>' % scale, html)


# ---------------------------------------------------------------------------
# Serviço de visualizações
# ---------------------------------------------------------------------------


class ServiceTests(CalendarBase):
    def test_create_freezes_the_date_and_color_columns(self):
        view = ViewService.create(user=self.admin, board=self.board, view_type="CALENDAR", name="Prazos")
        self.assertEqual((view.type, view.name), ("CALENDAR", "Prazos"))
        self.assertEqual(view.settings["date_field"], self.col["data"].pk)
        self.assertEqual(view.settings["color_by"], self.col["status"].pk)
        log = AuditLog.objects.get(action=AuditLog.Action.BOARD_VIEW_CREATED, target_id=view.pk)
        self.assertEqual((log.metadata["type"], log.metadata["board_id"]), ("CALENDAR", self.board.pk))

    def test_default_name_and_unique_names(self):
        self.assertEqual(self.cal.name, "Calendário")
        again = ViewService.create(user=self.admin, board=self.board, view_type="CALENDAR")
        self.assertEqual(again.name, "Calendário 2")

    def test_a_board_without_a_date_column_cannot_get_a_calendar(self):
        board = BoardService.create(user=self.admin, organization=self.org, name="Sem datas")
        with self.assertRaisesMessage(BoardError, "coluna de Data"):
            ViewService.create(user=self.admin, board=board, view_type="CALENDAR")
        self.assertEqual(board.views.count(), 1)  # só o Kanban

    def test_two_calendars_can_read_two_different_date_columns(self):
        visit = ColumnService.create(user=self.admin, board=self.board, column_type=T.DATE)
        ColumnService.rename(user=self.admin, column=visit, name="Visita técnica")
        other = ViewService.create(user=self.admin, board=self.board, view_type="CALENDAR", name="Visitas",
                                   settings={"date_field": visit.pk})
        self.put(self.item1, "data", "2026-10-15")
        CellService.set_value(user=self.admin, item=self.item2, column=visit, raw_value="2026-10-20")
        self.assertEqual(self.titles(self.page(self.viewer), "2026-10-15"), ["Arena Norte"])
        self.assertEqual(self.titles(self.page(self.viewer, view=other), "2026-10-20"), ["Condomínio Cotia"])
        self.assertEqual(self.titles(self.page(self.viewer, view=other), "2026-10-15"), [])
        self.assertEqual(self.board.items.filter(is_active=True).count(), 3)  # os mesmos itens, nenhuma cópia

    def test_update_is_audited_key_by_key_and_validated(self):
        ViewService.update(user=self.admin, view=self.cal, settings={"show_weekends": False, "color_by": "group"})
        self.cal.refresh_from_db()
        self.assertFalse(self.cal.settings["show_weekends"])
        fields = set(AuditLog.objects.filter(action=AuditLog.Action.BOARD_VIEW_UPDATED, target_id=self.cal.pk).values_list("field_name", flat=True))
        self.assertEqual(fields, {"show_weekends", "color_by"})
        with self.assertRaises(BoardError):
            ViewService.update(user=self.admin, view=self.cal, settings={"date_field": self.col["texto"].pk})
        self.cal.refresh_from_db()
        self.assertEqual(self.cal.settings["date_field"], self.col["data"].pk)  # a recusa não mexe na configuração

    def test_only_who_edits_the_board_changes_views(self):
        for call in (
            lambda: ViewService.create(user=self.editor, board=self.board, view_type="CALENDAR"),
            lambda: ViewService.update(user=self.editor, view=self.cal, settings={"show_weekends": False}),
            lambda: ViewService.soft_delete(user=self.editor, view=self.cal),
        ):
            with self.assertRaises(BoardPermissionError):
                call()

    def test_deleting_the_view_keeps_every_item_and_date(self):
        self.put(self.item1, "data", "2026-10-15")
        ViewService.soft_delete(user=self.admin, view=self.cal)
        self.assertEqual(self.board.items.filter(is_active=True).count(), 3)
        self.assertEqual(BoardItem.objects.get(pk=self.item1.pk).cells.get(column=self.col["data"]).value_date, D(2026, 10, 15))

    def test_the_kanban_keeps_ignoring_calendar_keys(self):
        with self.assertRaises(BoardError):
            ViewService.create(user=self.admin, board=self.board, view_type="TIMELINE")
        ViewService.update(user=self.admin, view=self.kanban, settings={"show_weekends": False, "show_empty": False})
        self.kanban.refresh_from_db()
        self.assertNotIn("show_weekends", self.kanban.settings)
        self.assertFalse(self.kanban.settings["show_empty"])

    def test_deleting_the_date_column_leaves_the_calendar_without_a_date(self):
        ColumnService.soft_delete(user=self.admin, column=self.col["data"])
        response = self.page(self.admin)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["date_column"])
        self.assertContains(response, "Escolha uma coluna de Data")
        self.assertContains(response, "data-cal-create-date")  # quem gere colunas cria a coluna sem sair da tela
        self.assertNotContains(self.page(self.viewer), "data-cal-create-date")
        self.assertNotContains(self.page(self.admin), 'data-cal-add')


# ---------------------------------------------------------------------------
# Tela
# ---------------------------------------------------------------------------


class PageTests(CalendarBase):
    def test_access_rules(self):
        self.assertEqual(self.page(self.sem_acesso).status_code, 403)
        self.assertEqual(self.page(self.estranho).status_code, 404)  # outra organização
        self.client.logout()
        self.assertEqual(self.client.get(reverse("board-view-detail", args=[self.cal.pk])).status_code, 302)

    def test_deleted_view_is_404(self):
        ViewService.soft_delete(user=self.admin, view=self.cal)
        self.assertEqual(self.page(self.viewer).status_code, 404)

    def test_tabs_show_the_calendar_with_its_own_icon_on_every_page(self):
        self.login(self.admin)
        table = self.client.get(reverse("board-detail", args=[self.board.pk]))
        self.assertEqual([v.name for v in table.context["views"]], ["Kanban", "Calendário"])
        self.assertContains(table, reverse("board-view-detail", args=[self.cal.pk]))
        self.assertContains(table, "#i-calendar")
        page = self.page(self.admin)
        self.assertEqual(page.context["active_view"], self.cal)
        self.assertContains(page, 'aria-current="page"', count=1)
        self.assertTemplateUsed(page, "boards/board_calendar.html")
        kanban = self.client.get(reverse("board-view-detail", args=[self.kanban.pk]))
        self.assertTemplateUsed(kanban, "boards/board_kanban.html")
        self.assertContains(kanban, "data-kanban-lanes")

    def test_controls_depend_on_the_permission(self):
        viewer = self.page(self.viewer)
        for marker in ("data-cal-config", "data-cal-add", "data-drawer-delete", 'draggable="true"', "data-view-add"):
            self.assertNotContains(viewer, marker, msg_prefix=marker)
        editor = self.page(self.editor)
        self.assertContains(editor, "data-cal-add")  # criar item é de quem preenche
        self.assertNotContains(editor, "data-cal-config")  # configurar é de quem edita o quadro
        admin = self.page(self.admin)
        for marker in ("data-cal-config", "data-cal-add", "data-view-menu"):
            self.assertContains(admin, marker, msg_prefix=marker)

    def test_add_button_names_the_day(self):
        self.assertContains(self.page(self.admin), 'aria-label="Adicionar item em 15 de outubro"')

    def test_meta_for_the_javascript(self):
        self.put(self.item1, "data", "2026-10-15")
        meta = self.page(self.admin).context["meta"]
        calendar = meta["calendar"]
        self.assertEqual(calendar["view"], {"id": self.cal.pk, "name": "Calendário"})
        self.assertEqual(calendar["date_column_id"], self.col["data"].pk)
        self.assertEqual(calendar["color_column_id"], self.col["status"].pk)
        self.assertEqual(calendar["status_column_id"], self.col["status"].pk)
        self.assertEqual(calendar["month"], "2026-10")
        self.assertEqual(calendar["max_visible"], MAX_VISIBLE_PER_DAY)
        self.assertEqual(calendar["default_group_id"], self.group_a.pk)
        self.assertEqual(calendar["dateable_ids"], [self.col["data"].pk])
        self.assertEqual(set(calendar["colorable_ids"]), {self.col["status"].pk, self.col["lista"].pk})
        self.assertEqual(len(meta["columns"]), 8)
        for key in ("view_calendar", "item_detail", "cell_update", "item_create", "view_update", "column_create"):
            self.assertIn(key, meta["urls"])

    def test_number_of_queries_does_not_grow_with_the_cards(self):
        def queries():
            self.login(self.admin)
            with CaptureQueriesContext(connection) as context:
                self.client.get(reverse("board-view-detail", args=[self.cal.pk]), {"mes": "2026-10"})
            return len(context)

        self.put(self.item1, "data", "2026-10-15")
        few = queries()
        for index in range(12):
            item = ItemService.create(user=self.admin, board=self.board, group=self.group_b, name=f"Extra {index}")
            self.put(item, "data", f"2026-10-{10 + index:02d}")
            self.put(item, "pessoa", self.ana.pk)
            self.put(item, "status", self.andamento.pk)
        self.assertEqual(queries(), few)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


class ApiTests(CalendarBase):
    def calendar(self, data=None, view=None, user=None):
        return self.api("board-view-calendar", [(view or self.cal).pk], data or {}, user=user)

    def test_fragment_contract(self):
        self.put(self.item1, "data", "2026-11-03")
        response = self.calendar({"mes": "2026-11"}, user=self.viewer)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual((data["title"], data["month"], data["prev"], data["next"]), ("novembro 2026", "2026-11", "2026-10", "2026-12"))
        self.assertIn('data-date="2026-11-03"', data["body_html"])
        self.assertIn("Arena Norte", data["body_html"])
        self.assertEqual(data["date_column_id"], self.col["data"].pk)
        self.assertEqual(data["dateable_ids"], [self.col["data"].pk])
        self.assertEqual(set(data["colorable_ids"]), {self.col["status"].pk, self.col["lista"].pk})
        self.assertEqual(data["settings"]["show_weekends"], True)
        self.assertEqual(len(data["columns"]), 8)

    def test_fragment_keeps_the_filters(self):
        self.put(self.item1, "data", "2026-10-15")
        self.put(self.item2, "data", "2026-10-15")
        body = self.calendar({"mes": "2026-10", "q": "cotia"}, user=self.viewer).json()["body_html"]
        self.assertIn("Condomínio Cotia", body)
        self.assertNotIn("Arena Norte", body)

    def test_fragment_needs_view_permission_and_the_right_view(self):
        self.assertEqual(self.calendar(user=self.sem_acesso).status_code, 403)
        self.assertEqual(self.calendar(user=self.estranho).status_code, 404)
        self.assertEqual(self.calendar(view=self.kanban, user=self.admin).status_code, 404)  # é a rota do calendário
        self.assertEqual(self.api("board-view-lanes", [self.cal.pk], {}, user=self.admin).status_code, 404)  # raias são do Kanban
        self.assertEqual(self.api("board-view-lanes", [self.kanban.pk], {}, user=self.admin).status_code, 200)

    def test_fragment_rejects_garbage(self):
        self.assertEqual(self.api("board-view-calendar", [self.cal.pk], raw="{nao", user=self.admin).status_code, 400)
        self.assertEqual(self.calendar({"mes": "../x", "pessoa": "abc"}, user=self.admin).status_code, 200)

    def test_update_returns_the_calendar_settings(self):
        response = self.api("board-view-update", [self.cal.pk], {"settings": {"show_weekends": False}}, user=self.admin)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["settings"]["show_weekends"])
        self.assertIn("card_fields", response.json()["settings"])
        self.assertNotIn("group_by", response.json()["settings"])
        bad = self.api("board-view-update", [self.cal.pk], {"settings": {"color_by": self.col["texto"].pk}}, user=self.admin)
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.api("board-view-update", [self.cal.pk], {"settings": {"show_weekends": True}}, user=self.editor).status_code, 403)

    def test_create_a_calendar_through_the_api(self):
        response = self.api("board-view-create", [self.board.pk], {"name": "Prazos", "type": "CALENDAR"}, user=self.admin)
        self.assertEqual(response.status_code, 200)
        view = BoardView.objects.get(pk=response.json()["view"]["id"])
        self.assertEqual(view.type, "CALENDAR")
        self.assertEqual(response.json()["redirect_url"], reverse("board-view-detail", args=[view.pk]))
        board = BoardService.create(user=self.admin, organization=self.org, name="Sem datas")
        bad = self.api("board-view-create", [board.pk], {"type": "CALENDAR"}, user=self.admin)
        self.assertEqual(bad.status_code, 400)
        self.assertIn("coluna de Data", bad.json()["error"])
        self.assertEqual(self.api("board-view-create", [self.board.pk], {"type": "TIMELINE"}, user=self.admin).status_code, 400)

    def test_create_the_date_column_without_leaving_the_screen(self):
        board = BoardService.create(user=self.admin, organization=self.org, name="Sem datas")
        response = self.api("board-column-create", [board.pk], {"type": "DATE"}, user=self.admin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.api("board-view-create", [board.pk], {"type": "CALENDAR"}, user=self.admin).status_code, 200)

    # -- criar no dia ----------------------------------------------------------------------------

    def create(self, initial, user=None, name="Novo"):
        return self.api("board-item-create", [self.board.pk], {"group_id": self.group_a.pk, "name": name, "initial": initial}, user=user)

    def test_create_on_a_day_fills_the_date_and_other_fields_together(self):
        response = self.create([
            {"column_id": self.col["data"].pk, "value": "2026-10-15"},
            {"column_id": self.col["status"].pk, "value": self.andamento.pk},
            {"column_id": self.col["pessoa"].pk, "value": self.ana.pk},
        ], user=self.editor)
        self.assertEqual(response.status_code, 200)
        item = BoardItem.objects.get(pk=response.json()["item"]["id"])
        self.assertEqual(item.cells.get(column=self.col["data"]).value_date, D(2026, 10, 15))
        self.assertEqual(self.titles(self.page(self.viewer), "2026-10-15"), ["Novo"])  # e a tabela também o mostra
        table = self.detail(self.viewer)
        self.assertIn("Novo", self.row_names(table))

    def test_create_is_all_or_nothing(self):
        before = BoardItem.objects.count()
        response = self.create([
            {"column_id": self.col["data"].pk, "value": "2026-10-15"},
            {"column_id": self.col["status"].pk, "value": 999999},
        ], user=self.admin)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(BoardItem.objects.count(), before)
        self.assertEqual(self.create([{"column_id": self.col["data"].pk, "value": "2026-13-45"}]).status_code, 400)
        self.assertEqual(BoardItem.objects.count(), before)

    def test_create_with_a_single_initial_still_works(self):
        response = self.create({"column_id": self.col["data"].pk, "value": "2026-10-15"}, user=self.admin)
        self.assertEqual(response.status_code, 200)

    def test_create_rejects_malformed_or_foreign_initials(self):
        for bad in ("2026-10-15", 5, [1, 2], [{"column_id": 1}] * 31):
            self.assertEqual(self.create(bad, user=self.admin).status_code, 400, bad)
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro")
        foreign = ColumnService.create(user=self.admin, board=other, column_type=T.DATE)
        self.assertEqual(self.create([{"column_id": foreign.pk, "value": "2026-10-15"}]).status_code, 404)
        self.assertEqual(self.create([{"column_id": 999999, "value": "2026-10-15"}]).status_code, 404)

    def test_create_needs_permission_to_create_and_to_edit(self):
        self.assertEqual(self.create([{"column_id": self.col["data"].pk, "value": "2026-10-15"}], user=self.viewer).status_code, 403)
        self.assertEqual(self.create([{"column_id": self.col["data"].pk, "value": "2026-10-15"}], user=self.estranho).status_code, 404)

    # -- mover o dia -----------------------------------------------------------------------------

    def move(self, item, value, user=None, column=None):
        column = column or self.col["data"]
        return self.api("board-cell-update", [item.pk, column.pk], {"value": value}, user=user)

    def test_moving_a_card_changes_only_the_date(self):
        self.put(self.item1, "data", "2026-10-15")
        self.put(self.item1, "status", self.andamento.pk)
        self.put(self.item1, "pessoa", self.ana.pk)
        response = self.move(self.item1, "2026-10-17", user=self.editor)
        self.assertEqual(response.status_code, 200)
        page = self.page(self.viewer)
        self.assertEqual(self.titles(page, "2026-10-17"), ["Arena Norte"])
        self.assertEqual(self.titles(page, "2026-10-15"), [])
        item = BoardQueryService.with_cells(BoardItem.objects.filter(pk=self.item1.pk)).get()
        cells = {cell.column_id: cell for cell in item.cells.all()}
        self.assertEqual(cells[self.col["status"].pk].option_values.get().option, self.andamento)
        self.assertEqual(cells[self.col["pessoa"].pk].user_values.get().user, self.ana)

    def test_rescheduling_is_audited_with_old_and_new_date(self):
        self.put(self.item1, "data", "2026-10-15")
        self.move(self.item1, "2026-10-18", user=self.editor)
        log = AuditLog.objects.filter(action=AuditLog.Action.BOARD_CELL_UPDATED, metadata__item_id=self.item1.pk).latest("id")
        self.assertEqual((log.old_value, log.new_value, log.user), ("15/10/2026", "18/10/2026", self.editor))
        self.assertEqual(log.metadata["board_id"], self.board.pk)

    def test_rescheduling_is_not_completing(self):
        self.put(self.item1, "data", "2026-10-15")
        self.move(self.item1, "2026-10-18", user=self.editor)
        status = BoardItem.objects.get(pk=self.item1.pk).cells.get(column=self.col["status"]).option_values.get().option
        self.assertEqual(status, self.novo)

    def test_moving_keeps_the_time_when_the_card_has_one(self):
        self.show_time()
        self.put(self.item1, "data", "2026-10-15T14:00")
        self.move(self.item1, "2026-10-16T14:00", user=self.editor)
        self.assertEqual([(e["item"].name, e["time"]) for e in self.day(self.page(self.viewer), "2026-10-16")["entries"]],
                         [("Arena Norte", "14:00")])

    def test_removing_only_the_time_keeps_the_date(self):
        self.show_time()
        self.put(self.item1, "data", "2026-10-15T14:00")
        self.move(self.item1, "2026-10-15", user=self.editor)
        entry = self.day(self.page(self.viewer), "2026-10-15")["entries"][0]
        self.assertEqual(entry["time"], "")

    def test_removing_the_date_takes_the_item_off_the_grid(self):
        self.put(self.item1, "data", "2026-10-15")
        self.assertEqual(self.move(self.item1, "", user=self.editor).status_code, 200)
        page = self.page(self.viewer)
        self.assertEqual(self.titles(page, "2026-10-15"), [])
        self.assertIn(self.item1.pk, [item.pk for item in page.context["nodate_items"]])

    def test_a_viewer_cannot_reschedule_and_nothing_changes(self):
        self.put(self.item1, "data", "2026-10-15")
        response = self.move(self.item1, "2026-10-17", user=self.viewer)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.titles(self.page(self.viewer), "2026-10-15"), ["Arena Norte"])
        self.assertFalse(AuditLog.objects.filter(action=AuditLog.Action.BOARD_CELL_UPDATED, new_value="17/10/2026").exists())

    def test_another_organization_cannot_touch_the_item(self):
        self.put(self.item1, "data", "2026-10-15")
        self.assertEqual(self.move(self.item1, "2026-10-17", user=self.estranho).status_code, 404)
        self.assertEqual(self.titles(self.page(self.viewer), "2026-10-15"), ["Arena Norte"])

    def test_a_date_the_column_refuses_is_refused_and_the_old_one_stays(self):
        ColumnService.update_settings(user=self.admin, column=self.col["data"], settings={"allow_weekends": False})
        self.put(self.item1, "data", "2026-10-15")
        response = self.move(self.item1, "2026-10-17", user=self.editor)  # sábado
        self.assertEqual(response.status_code, 400)
        self.assertIn("sábado", response.json()["error"])
        self.assertEqual(self.titles(self.page(self.viewer), "2026-10-15"), ["Arena Norte"])

    def test_impossible_dates_are_refused(self):
        self.put(self.item1, "data", "2026-10-15")
        for bad in ("2026-02-30", "2026-13-01", "amanhã", "2026-10-15T25:00"):
            self.assertEqual(self.move(self.item1, bad, user=self.editor).status_code, 400, bad)
        self.assertEqual(self.titles(self.page(self.viewer), "2026-10-15"), ["Arena Norte"])

    # -- gaveta ----------------------------------------------------------------------------------

    def detail_of(self, item, user=None):
        return self.api("board-item-detail", [item.pk], {}, user=user)

    def test_drawer_shows_every_column_and_the_item_history(self):
        self.put(self.item1, "data", "2026-10-15")
        self.put(self.item1, "data", "2026-10-18")
        ColumnService.set_visible(user=self.admin, column=self.col["texto"], visible=False)
        response = self.detail_of(self.item1, user=self.editor)
        self.assertEqual(response.status_code, 200)
        html = response.json()["drawer_html"]
        for column in self.columns():
            self.assertIn(f'data-column-id="{column.pk}"', html)  # as ocultas também
        self.assertIn("Arena Norte", html)
        self.assertIn("15/10/2026", html)  # data anterior
        self.assertIn("18/10/2026", html)  # nova data
        self.assertNotIn("Hospital Vida", html)  # só o histórico DESTE item
        self.assertIn("data-drawer-title", html)
        self.assertNotIn("data-drawer-delete", html)  # editor não exclui

    def test_drawer_is_read_only_without_edit_permission(self):
        html = self.detail_of(self.item1, user=self.viewer).json()["drawer_html"]
        self.assertNotIn("is-editable", html)
        self.assertNotIn('role="textbox"', html)

    def test_drawer_permissions_and_isolation(self):
        self.assertEqual(self.detail_of(self.item1, user=self.sem_acesso).status_code, 403)
        self.assertEqual(self.detail_of(self.item1, user=self.estranho).status_code, 404)
        ItemService.soft_delete(user=self.admin, item=self.item3)
        self.assertEqual(self.detail_of(self.item3, user=self.admin).status_code, 404)

    def test_drawer_delete_button_for_whoever_can_delete(self):
        self.assertIn("data-drawer-delete", self.detail_of(self.item1, user=self.admin).json()["drawer_html"])

    def test_drawer_escapes_text(self):
        ItemService.rename(user=self.admin, item=self.item1, name="<img src=x onerror=alert(1)>")
        html = self.detail_of(self.item1, user=self.admin).json()["drawer_html"]
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x", html)

    def test_item_history_query_is_limited_and_scoped(self):
        for day in range(1, 6):
            self.put(self.item1, "data", f"2026-10-{day:02d}")
        self.put(self.item2, "data", "2026-10-09")
        history = list(BoardQueryService.item_history(self.item1, 3))
        self.assertEqual(len(history), 3)
        self.assertTrue(all(entry.metadata.get("item_id") == self.item1.pk or entry.target_id == self.item1.pk for entry in history))
