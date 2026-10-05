"""Kanban de Demandas no Workspace (flag `WORKSPACE_V2`): o MESMO modelo visual de Quadros, alimentado por Demandas.

Quatro grupos: (1) regras puras do construtor (`boards/demand_kanban.py`), sem banco; (2) a página real: raias, campos,
quem pode arrastar; (3) o fragmento `?fragmento=raias` que redesenha as raias depois de mover; (4) o CONTRATO entre o que
a tela deixa fazer e o que o servidor aceita — para cada par cartão × raia, "pode soltar" no cliente ⇔ 200 no servidor.
"""

import datetime
import json
import re
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlsplit

from django.db import connection, transaction
from django.test import SimpleTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from acessos.testing import grant_actions
from activities.models import Activity
from activities.test_demand_filters import DemandFilterBase
from core.models import ActivityStage

from .demand_kanban import BLANK_COLOR, build_demand_kanban
from .domain_defaults import ensure_domain_board
from .models import DomainBoard, DomainBoardCardField, DomainBoardView

SECTORS = {1: "Orçamento", 2: "Financeiro"}


def group(key, label, items=(), **extra):
    return {"key": key, "label": label, "color": "#3B82F6", "items": list(items), **extra}


def build(groups, group_by="stage", **extra):
    options = dict(sectors_by_id=SECTORS, show_field_names=False, can_create=True, create_url="/demandas/nova/", return_url="/demandas/kanban/")
    options.update(extra)
    return build_demand_kanban(groups=groups, group_by=group_by, **options)


def item(pk, sector_id=1, status="ABERTA", movable=True):
    return SimpleNamespace(
        pk=pk, title=f"Demanda {pk}", sector_id=sector_id, status=status, can_move_kanban=movable, work_cells=[],
        updated_at=datetime.datetime(2026, 10, 3, 10, 0, tzinfo=datetime.timezone.utc),
    )


class BuilderLaneRulesTests(SimpleTestCase):
    def test_the_blank_lane_is_grey_and_accepts_only_where_the_server_accepts_empty(self):
        for group_by, accepts in (("stage", True), ("condition", True), ("sector", False), ("owner", False), ("urgency", False)):
            with self.subTest(group_by=group_by):
                (lane,) = build([group("empty", "Sem valor")], group_by)["lanes"]
                self.assertTrue(lane["is_blank"])
                self.assertEqual(lane["color"], BLANK_COLOR)
                self.assertEqual(lane["accepts"], accepts)
                self.assertEqual("Arraste" in lane["empty_text"], accepts)  # nunca convidar a soltar onde não se pode

    def test_stage_and_status_lanes_belong_to_one_sector_the_others_to_none(self):
        stage_lane = build([group(10, "A fazer", sector_id=1)], "stage")["lanes"][0]
        self.assertEqual(stage_lane["scope"], "1")
        for group_by in ("sector", "owner", "urgency"):
            self.assertEqual(build([group(10, "X", sector_id=1)], group_by)["lanes"][0]["scope"], "", group_by)

    def test_the_sector_shows_under_the_title_only_when_lanes_of_different_sectors_mix(self):
        mixed = build([group(11, "A fazer", sector_id=1), group(12, "A fazer", sector_id=2)])["lanes"]
        self.assertEqual([lane["sector"] for lane in mixed], ["Financeiro", "Orçamento"])  # ordenadas por setor
        single = build([group(11, "A fazer", sector_id=1), group(13, "Levantamento", sector_id=1)])["lanes"]
        self.assertEqual([lane["sector"] for lane in single], ["", ""])  # um setor só: a sublinha só repetiria

    def test_in_a_mixed_board_the_blank_lane_stays_first_and_the_flow_order_is_kept_inside_each_sector(self):
        lanes = build([
            group(11, "A fazer", sector_id=1), group(13, "Levantamento", sector_id=1), group("empty", "Sem estágio"),
            group(12, "A fazer", sector_id=2),
        ])["lanes"]
        self.assertEqual([(lane["key"], lane["sector"]) for lane in lanes],
                         [("empty", ""), (12, "Financeiro"), (11, "Orçamento"), (13, "Orçamento")])

    def test_a_lane_of_a_deactivated_stage_still_shows_but_does_not_receive(self):
        lanes = build([group(11, "Antiga", sector_id=1, is_active=False), group(13, "Nova", sector_id=1)])["lanes"]
        self.assertFalse(lanes[0]["accepts"])
        self.assertTrue(lanes[1]["accepts"])

    def test_the_footer_only_exists_for_who_can_create(self):
        self.assertEqual(build([group(1, "X")])["lanes"][0]["add"]["href"], "/demandas/nova/")
        self.assertIsNone(build([group(1, "X")], can_create=False)["lanes"][0]["add"])

    def test_the_lane_count_is_the_number_of_cards(self):
        lane = build([group(1, "X", [item(1), item(2)]), group(2, "Y", sector_id=1)])["lanes"][0]
        self.assertEqual((lane["count"], len(lane["cards"])), (2, 2))


class BuilderMovableTests(SimpleTestCase):
    def movable(self, groups, group_by="stage"):
        return {card["id"]: card["can_move"] for lane in build(groups, group_by)["lanes"] for card in lane["cards"]}

    def test_the_card_needs_the_permission_a_finished_demand_never_moves(self):
        groups = [group(1, "A", [item(1), item(2, movable=False), item(3, status="CONCLUIDA"), item(4, status="CANCELADA")], sector_id=1), group("empty", "Sem")]
        self.assertEqual(self.movable(groups), {1: True, 2: False, 3: False, 4: False})

    def test_without_another_lane_that_receives_it_the_card_does_not_move(self):
        self.assertEqual(self.movable([group(1, "Única", [item(1)], sector_id=1)]), {1: False})  # só tem a própria raia
        # cartão do setor 2 numa raia do setor 1: a única que o recebe é a em branco
        self.assertEqual(self.movable([group(1, "A", [item(1, sector_id=2)], sector_id=1), group("empty", "Sem")]), {1: True})
        self.assertEqual(self.movable([group(1, "A", [item(1, sector_id=2)], sector_id=1), group(2, "B", sector_id=1)]), {1: False})

    def test_a_card_without_sector_only_goes_to_the_blank_lane(self):
        groups = [group("empty", "Sem estágio", [item(1, sector_id=None)]), group(1, "A", sector_id=1)]
        self.assertEqual(self.movable(groups), {1: False})  # já está na única raia que o recebe
        groups.append(group(2, "B", [item(2, sector_id=None)], sector_id=1))
        self.assertEqual(self.movable(groups), {1: False, 2: True})

    def test_a_draft_cannot_change_sector_or_owner_but_can_change_the_rest(self):
        for group_by, expected in (("sector", False), ("owner", False), ("urgency", True), ("stage", True)):
            with self.subTest(group_by=group_by):
                groups = [group(1, "A", [item(1, status="RASCUNHO")], sector_id=1), group(2, "B", sector_id=1)]
                self.assertEqual(self.movable(groups, group_by), {1: expected})

    def test_the_card_carries_the_scope_the_version_and_the_return_address(self):
        (card,) = build([group(1, "A", [item(7)], sector_id=1), group(2, "B", sector_id=1)])["lanes"][0]["cards"]
        self.assertEqual(card["scope"], "1")
        self.assertEqual(card["updated_at"], "2026-10-03T10:00:00+00:00")
        self.assertEqual(card["url"], "/demandas/7/?next=/demandas/kanban/")


class KanbanBase(DemandFilterBase):
    flag = "on"

    def setUp(self):
        super().setUp()
        self.board = ensure_domain_board(self.org, DomainBoard.Domain.DEMAND)
        self.view = self.board.views.get(type=DomainBoardView.Type.KANBAN)

    def page(self, name="activity-kanban", user=None, **params):
        if user is not None:
            self.client.force_login(user)
        params.setdefault("tab", "todas")
        with override_settings(WORKSPACE_V2=self.flag):
            response = self.client.get(reverse(name), params)
        self.assertEqual(response.status_code, 200, (name, params))
        return response

    def kanban(self, user=None, **params):
        return self.page(user=user, **params).context["kanban"]

    @staticmethod
    def cards(kanban):
        return {card["title"]: (lane, card) for lane in kanban["lanes"] for card in lane["cards"]}

    def show_card_fields(self, *keys):
        for position, key in enumerate(keys, start=100):
            DomainBoardCardField.objects.get_or_create(view=self.view, field=self.board.fields.get(key=key), defaults={"position": position})


class LanesOnThePageTests(KanbanBase):
    def test_stage_lanes_of_several_sectors_say_which_sector_each_one_is(self):
        lanes = self.kanban(agrupar="stage")["lanes"]
        self.assertEqual([(lane["label"], lane["sector"]) for lane in lanes if not lane["is_blank"]],
                         [("A fazer", "Financeiro"), ("A fazer", "Orçamento"), ("Levantamento", "Orçamento")])
        self.assertEqual(lanes[0]["key"], "empty")  # a raia em branco abre o quadro
        html = self.page(agrupar="stage").content.decode()
        self.assertIn('<p class="kanban-lane__meta">Financeiro</p>', html)
        self.assertIn('aria-label="A fazer — Orçamento"', html)

    def test_filtering_one_sector_removes_the_sublabel(self):
        lanes = self.kanban(agrupar="stage", setor=self.orcamento.pk)["lanes"]
        self.assertEqual([lane["label"] for lane in lanes if not lane["is_blank"]], ["A fazer", "Levantamento"])
        self.assertEqual({lane["sector"] for lane in lanes}, {""})

    def test_lane_colors_are_the_ones_of_the_stage_and_the_blank_one_is_grey(self):
        lanes = {lane["key"]: lane for lane in self.kanban(agrupar="stage")["lanes"]}
        self.assertEqual(lanes[self.afazer.pk]["color"], self.afazer.color)
        self.assertEqual(lanes["empty"]["color"], BLANK_COLOR)

    def test_every_grouping_renders_and_counts_the_cards(self):
        for group_by in ("stage", "condition", "sector", "owner", "urgency"):
            with self.subTest(group_by=group_by):
                kanban = self.kanban(agrupar=group_by)
                self.assertEqual(sum(lane["count"] for lane in kanban["lanes"]), 5)  # as 5 abertas de "Todas"
                self.assertEqual(sum(len(lane["cards"]) for lane in kanban["lanes"]), 5)

    def test_the_page_has_what_the_adapter_needs(self):
        html = self.page(agrupar="condition").content.decode()
        field = self.board.fields.get(key="condition")
        self.assertIn(f'data-move-url="/quadros/dominio/{self.board.pk}/campos/{field.pk}/itens/0/valor/"', html)
        self.assertIn('data-group-by="condition"', html)
        self.assertIn("data-kanban-lanes", html)
        self.assertIn("data-board-toasts", html)
        self.assertIn('aria-label="Demandas em raias, agrupadas por status"', html)

    def test_without_the_grouping_field_nobody_can_drag(self):
        self.board.fields.filter(key="stage").update(is_active=False)
        self.client.force_login(self.mover)
        response = self.page(agrupar="stage")
        self.assertNotIn("data-move-url", response.content.decode())
        self.assertFalse(any(card["can_move"] for lane in response.context["kanban"]["lanes"] for card in lane["cards"]))

    def test_the_card_links_to_the_demand_and_comes_back_to_the_same_screen(self):
        _lane, card = self.cards(self.kanban(agrupar="stage", q="Aurora"))["Orçamento Aurora"]
        path, _sep, query = card["url"].partition("?next=")
        self.assertEqual(path, f"/demandas/{self.a1.pk}/")
        back = urlsplit(unquote(query))
        self.assertEqual(back.path, "/demandas/kanban/")
        self.assertEqual(parse_qs(back.query), {"tab": ["todas"], "agrupar": ["stage"], "q": ["Aurora"]})

    def test_the_old_screen_is_untouched_with_the_flag_off(self):
        with override_settings(WORKSPACE_V2="off"):
            old = self.client.get(reverse("activity-kanban"), {"tab": "todas"})
        self.assertTemplateUsed(old, "boards/demand_work_board.html")
        self.assertContains(old, "data-work-kanban")
        self.assertNotContains(old, "data-kanban-lanes")
        self.assertNotIn("kanban", old.context)


class CardsOnThePageTests(KanbanBase):
    def test_default_card_fields_are_typed(self):
        _lane, card = self.cards(self.kanban())["Orçamento Aurora"]
        self.assertEqual([(field["kind"], field["label"]) for field in card["fields"]],
                         [("person", "Responsável"), ("sector", "Setor"), ("pill", "Prioridade"), ("date", "Prazo")])
        person = card["fields"][0]
        self.assertEqual((person["name"], person["initials"]), ("ana", "A"))

    def test_stage_and_status_are_told_apart_and_tasks_become_progress(self):
        self.show_card_fields("stage", "condition", "tasks")
        _lane, card = self.cards(self.kanban())["Orçamento Aurora"]
        by_label = {field["label"]: field for field in card["fields"]}
        self.assertEqual(by_label["Etapa"], {"kind": "pill", "label": "Etapa", "text": "A fazer", "color": self.afazer.color})
        self.assertEqual((by_label["Status"]["kind"], by_label["Status"]["text"]), ("pill", "Normal"))
        self.assertEqual(by_label["Tarefas"]["kind"], "progress")
        self.assertEqual((by_label["Tarefas"]["done"], by_label["Tarefas"]["total"]), (0, 0))

    def test_a_missing_value_is_an_empty_field_not_a_made_up_text(self):
        self.show_card_fields("stage")
        Activity.objects.filter(pk=self.a1.pk).update(stage=None)
        _lane, card = self.cards(self.kanban())["Orçamento Aurora"]
        stage = next(field for field in card["fields"] if field["label"] == "Etapa")
        self.assertEqual(stage["text"], "")  # o template mostra "—", nunca "Sem etapa" como se fosse um valor

    def test_overdue_is_a_badge_on_the_date_never_a_color_of_the_card(self):
        Activity.objects.filter(pk=self.a1.pk).update(requested_deadline=timezone.now() - datetime.timedelta(days=2))
        Activity.objects.filter(pk=self.a2.pk).update(requested_deadline=timezone.now() + datetime.timedelta(days=5))
        response = self.page()
        cards = self.cards(response.context["kanban"])
        date = lambda title: next(field for field in cards[title][1]["fields"] if field["kind"] == "date")  # noqa: E731
        self.assertTrue(date("Orçamento Aurora")["overdue"])
        self.assertFalse(date("Levantamento da garagem")["overdue"])
        html = response.content.decode()
        self.assertEqual(html.count("board-date__flag"), 1)
        self.assertNotIn("is-late", html)
        self.assertNotRegex(html, r'<article class="kanban-card[^"]*(overdue|late)')

    def test_the_field_names_are_hidden_by_default_and_shown_when_the_view_asks(self):
        self.assertIn('<dt class="sr-only">Responsável</dt>', self.page().content.decode())
        self.view.settings = {**(self.view.settings or {}), "show_field_names": True}
        self.view.save(update_fields=["settings"])
        html = self.page().content.decode()
        self.assertIn("<dt>Responsável</dt>", html)
        self.assertNotIn('<dt class="sr-only">Responsável</dt>', html)

    def test_user_text_in_a_title_is_escaped(self):
        Activity.objects.filter(pk=self.a1.pk).update(title="<img src=x onerror=alert(1)>")
        html = self.page().content.decode()
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html)


class WhoCanDragTests(KanbanBase):
    def movable(self, user, **params):
        kanban = self.kanban(user=user, **params)
        return {title: card["can_move"] for title, (_lane, card) in self.cards(kanban).items()}

    def test_someone_who_only_reads_has_no_drag_and_no_menu(self):
        response = self.page(user=self.leitor, agrupar="stage")
        self.assertFalse(any(self.movable(self.leitor, agrupar="stage").values()))
        html = response.content.decode()
        self.assertNotIn('draggable="true"', html)
        self.assertNotIn("data-card-menu", html)

    def test_each_grouping_asks_for_its_own_permission(self):
        self.assertTrue(all(self.movable(self.mover, agrupar="stage").values()))
        self.assertFalse(any(self.movable(self.mover, agrupar="condition").values()))  # sem DEFINIR_CONDICAO
        grant_actions(self.mover, [catalog.ATIVIDADE_DEFINIR_CONDICAO], organization=self.org)
        self.assertTrue(all(self.movable(self.mover, agrupar="condition").values()))

    def test_the_stage_also_moves_with_the_define_stage_permission_like_the_service_accepts(self):
        user = self.visitante
        self.assertFalse(any(self.movable(user, agrupar="stage").values()))
        grant_actions(user, [catalog.ATIVIDADE_DEFINIR_ETAPA], organization=self.org)
        self.assertTrue(all(self.movable(user, agrupar="stage").values()))
        self.assertFalse(any(self.movable(user, agrupar="condition").values()))  # a permissão nova só vale para a etapa

    def test_a_finished_demand_is_shown_but_not_movable(self):
        moved = self.movable(self.mover, tab="todas", concluidas="1", agrupar="stage")
        self.assertEqual(moved, {"Já concluída": False})

    def test_a_demand_in_a_deactivated_stage_still_appears(self):
        ActivityStage.objects.filter(pk=self.levantamento.pk).update(is_active=False)
        lanes = {lane["label"]: lane for lane in self.kanban(user=self.mover, agrupar="stage")["lanes"]}
        self.assertEqual([card["title"] for card in lanes["Levantamento"]["cards"]], ["Levantamento da garagem"])
        self.assertFalse(lanes["Levantamento"]["accepts"])


class FragmentTests(KanbanBase):
    def fragment(self, name="activity-kanban", **params):
        params = {"tab": "todas", "fragmento": "raias", **params}
        with override_settings(WORKSPACE_V2=self.flag):
            return self.client.get(reverse(name), params)

    def test_the_fragment_is_only_the_lanes(self):
        response = self.fragment(agrupar="stage")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "kanban/_lanes.html")
        self.assertTemplateNotUsed(response, "workspace/demandas.html")
        html = response.content.decode()
        self.assertIn("data-lane-key", html)
        for shell in ("data-ws", "<html", "<script", "Escopo"):
            self.assertNotIn(shell, html, shell)

    def test_the_fragment_has_the_same_cut_as_the_page(self):
        for params in ({"q": "Aurora"}, {"setor": self.financeiro.pk}, {"pessoa": "eu"}, {"estagio": self.levantamento.pk}):
            with self.subTest(params=params):
                on_the_page = sorted(self.cards(self.kanban(**params)))
                in_the_fragment = re.findall(r'data-card-title href="[^"]*" draggable="false">([^<]+)<', self.fragment(**params).content.decode())
                self.assertTrue(on_the_page)
                self.assertEqual(sorted(in_the_fragment), on_the_page)

    def test_the_cards_of_the_fragment_come_back_to_the_page_not_to_the_fragment(self):
        html = self.fragment(q="Aurora").content.decode()
        self.assertNotIn("fragmento", html)
        self.assertIn("next=/demandas/kanban/%3F", html)

    def test_the_fragment_needs_login_and_never_leaks_another_organization(self):
        self.assertNotIn("Alheia", self.fragment(q="Alheia").content.decode())
        self.client.logout()
        response = self.fragment()
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_only_the_kanban_answers_fragments_and_only_with_the_flag(self):
        for name in ("activity-list", "activity-calendar"):
            response = self.fragment(name)
            self.assertTemplateUsed(response, "workspace/demandas.html", name)  # a Lista e o Calendário ignoram o parâmetro
        with override_settings(WORKSPACE_V2="off"):
            old = self.client.get(reverse("activity-kanban"), {"tab": "todas", "fragmento": "raias"})
        self.assertTemplateUsed(old, "boards/demand_work_board.html")

    def test_a_cut_with_no_cards_keeps_the_flow_lanes_empty_and_inviting(self):
        html = self.fragment(q="nada-que-case-com-nenhuma-demanda", agrupar="stage").content.decode()
        self.assertIn("data-lane-empty>Nenhuma demanda. Arraste uma demanda para cá.<", html)
        self.assertNotIn("data-card ", html)

    def test_nothing_is_disabled_to_look_the_same(self):
        for user in (self.leitor, self.mover):
            self.client.force_login(user)
            self.assertNotIn("disabled", self.fragment(agrupar="stage").content.decode(), user.username)

    def test_the_cost_does_not_grow_with_the_number_of_cards(self):
        def queries():
            with CaptureQueriesContext(connection) as captured:
                self.fragment(agrupar="stage")
            return len(captured)

        self.fragment(agrupar="stage")  # esquenta caches de contexto
        base = queries()
        for index in range(12):
            self._activity(f"Extra {index}", self.ana, self.orcamento, self.afazer, self.normal)
        self.assertLessEqual(queries(), base + 1)


class _Rollback(Exception):
    pass


class ClientServerContractTests(KanbanBase):
    """O que a tela deixa soltar é exatamente o que o servidor aceita (e nada além): o servidor segue sendo a verdade."""

    def setUp(self):
        super().setUp()
        grant_actions(self.mover, [catalog.ATIVIDADE_DEFINIR_CONDICAO, catalog.ATIVIDADE_EDITAR, catalog.ATIVIDADE_ALTERAR_DONO], organization=self.org)
        self._activity("Aberta do mover", self.mover, self.orcamento, self.afazer, self.normal)
        self._activity("Rascunho do mover", self.mover, self.orcamento, None, None, status=Activity.Status.RASCUNHO)
        self._activity("Concluída do mover", self.mover, self.orcamento, self.afazer, self.normal, status=Activity.Status.CONCLUIDA)
        self._activity("Sem setor", self.mover, None, None, None)
        # uma demanda dentro de uma etapa desativada: a raia aparece, mas não recebe
        old = ActivityStage.objects.create(organization=self.org, sector=self.orcamento, name="Antiga", order=9, is_active=False)
        self._activity("Na etapa antiga", self.gestor, self.orcamento, old, self.normal)
        self.client.force_login(self.mover)

    def server_status(self, field, card, lane):
        value = "" if lane["key"] == "empty" else lane["key"]
        try:
            with transaction.atomic():  # cada tentativa é desfeita: todas partem do mesmo estado
                response = self.client.post(
                    reverse("workboard-value", args=[self.board.pk, field.pk, card["id"]]),
                    data=json.dumps({"value": value, "updated_at": card["updated_at"]}), content_type="application/json",
                )
                raise _Rollback
        except _Rollback:
            pass
        return response.status_code

    @staticmethod
    def client_allows(card, lane):
        return bool(card["can_move"] and lane["accepts"] and lane["scope"] in ("", card["scope"]))

    def test_every_card_against_every_lane_for_every_grouping(self):
        samples = ({"tab": "todas"}, {"tab": "minhas"}, {"tab": "minhas", "concluidas": "1"})
        outcomes = {}  # (agrupamento, status) -> quantos pares: a grade precisa exercitar os DOIS lados em cada agrupamento
        for group_by in ("stage", "condition", "sector", "owner", "urgency"):
            field = self.board.fields.get(key=group_by)
            for sample in samples:
                kanban = self.kanban(agrupar=group_by, **sample)
                for lane in kanban["lanes"]:
                    for card in lane["cards"]:
                        for target in kanban["lanes"]:
                            if target is lane:
                                continue
                            expected = 200 if self.client_allows(card, target) else 400
                            status = self.server_status(field, card, target)
                            outcomes[(group_by, status)] = outcomes.get((group_by, status), 0) + 1
                            self.assertEqual(
                                status, expected,
                                f"{group_by} {sample}: «{card['title']}» ({lane['label']}) → «{target['label']}» "
                                f"[{target['sector']}] — a tela diz {expected}, o servidor respondeu {status}",
                            )
        for group_by in ("stage", "condition", "sector", "owner", "urgency"):
            self.assertGreater(outcomes.get((group_by, 200), 0), 3, f"{group_by}: nenhum par aceito — a grade não prova nada")
            self.assertGreater(outcomes.get((group_by, 400), 0), 3, f"{group_by}: nenhum par recusado — a grade não prova nada")

    def test_an_old_version_is_a_conflict_and_the_value_is_not_applied(self):
        field = self.board.fields.get(key="stage")
        kanban = self.kanban(agrupar="stage")
        lane, card = self.cards(kanban)["Orçamento Aurora"]
        target = next(other for other in kanban["lanes"] if other["key"] == self.levantamento.pk)
        Activity.objects.filter(pk=card["id"]).update(updated_at=timezone.now() + datetime.timedelta(minutes=5))
        self.assertEqual(self.server_status(field, card, target), 409)
