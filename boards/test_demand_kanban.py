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
from acessos.testing import grant_action, grant_actions
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


def item(pk, sector_id=1, status="ABERTA", movable=True, inline=None, code=""):
    return SimpleNamespace(
        pk=pk, title=f"Demanda {pk}", sector_id=sector_id, status=status, can_move_kanban=movable, work_cells=[],
        inline=inline, code=code, updated_at=datetime.datetime(2026, 10, 3, 10, 0, tzinfo=datetime.timezone.utc),
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
        self.assertEqual(build([group(1, "X", sector_id=1)])["lanes"][0]["add"]["href"], "/demandas/nova/?etapa=1&setor=1")
        self.assertIsNone(build([group(1, "X", sector_id=1)], can_create=False)["lanes"][0]["add"])

    def test_the_lane_count_is_the_number_of_cards(self):
        lane = build([group(1, "X", [item(1), item(2)]), group(2, "Y", sector_id=1)])["lanes"][0]
        self.assertEqual((lane["count"], len(lane["cards"])), (2, 2))


class BuilderAddAndMenuTests(SimpleTestCase):
    """"+ Adicionar" e ⋮ da raia: o que cada agrupamento deixa fazer e o que cada raia leva para a janela "Nova demanda"."""

    def lane(self, key, group_by, **extra):
        groups = [group(key, "X", sector_id=1 if group_by in ("stage", "condition") else None)]
        return build(groups, group_by, **extra)["lanes"][0]

    def test_each_grouping_presets_what_the_lane_says(self):
        self.assertEqual(self.lane(11, "stage")["add"]["href"], "/demandas/nova/?etapa=11&setor=1")
        self.assertEqual(self.lane(12, "condition")["add"]["href"], "/demandas/nova/?condicao=12&setor=1")
        self.assertEqual(self.lane(2, "sector")["add"]["href"], "/demandas/nova/?setor=2")
        self.assertEqual(self.lane(7, "owner")["add"]["href"], "/demandas/nova/?pessoa=7")
        self.assertEqual(self.lane("ALTA", "urgency")["add"]["href"], "/demandas/nova/?urgencia=ALTA")

    def test_owner_and_priority_lanes_take_the_sector_of_the_filter_when_there_is_one(self):
        self.assertEqual(self.lane(7, "owner", default_sector_id=1)["add"]["href"], "/demandas/nova/?pessoa=7&setor=1")
        self.assertEqual(self.lane("BAIXA", "urgency", default_sector_id=2)["add"]["href"], "/demandas/nova/?urgencia=BAIXA&setor=2")
        self.assertEqual(self.lane(2, "sector", default_sector_id=1)["add"]["href"], "/demandas/nova/?setor=2")  # a raia já é o setor

    def test_the_return_address_that_is_already_in_the_url_is_kept(self):
        href = self.lane(11, "stage", create_url="/demandas/nova/?next=%2Fdemandas%2Fkanban%2F")["add"]["href"]
        self.assertEqual(href, "/demandas/nova/?next=%2Fdemandas%2Fkanban%2F&etapa=11&setor=1")

    def test_a_lane_that_cannot_receive_a_new_demand_has_no_add(self):
        for group_by in ("stage", "condition", "sector", "owner", "urgency"):
            with self.subTest(group_by=group_by):
                self.assertIsNone(build([group("empty", "Sem valor")], group_by)["lanes"][0]["add"])  # "sem valor" nunca é destino
        self.assertIsNone(build([group(11, "Antiga", sector_id=1, is_active=False)])["lanes"][0]["add"])
        self.assertIsNone(build([group(11, "Solta")])["lanes"][0]["add"])  # etapa sem setor: não há o que preencher

    def test_the_sector_and_the_owner_of_the_lane_decide_if_the_person_can_create(self):
        asked = []

        def can_create_in(sector_id, owner_id):
            asked.append((sector_id, owner_id))
            return sector_id == 1

        lanes = build([group(11, "A fazer", sector_id=1), group(12, "A fazer", sector_id=2)], can_create_in=can_create_in)["lanes"]
        by_sector = {lane["scope"]: lane["add"] is not None for lane in lanes}
        self.assertEqual(by_sector, {"1": True, "2": False})
        self.assertEqual(sorted(asked), [(1, None), (2, None)])
        asked.clear()
        build([group(7, "Bia")], "owner", default_sector_id=1, can_create_in=can_create_in)
        self.assertEqual(asked, [(1, 7)])  # criar para OUTRA pessoa é outra pergunta ao servidor

    def test_without_permission_to_create_no_lane_has_an_add(self):
        lanes = build([group(11, "A", sector_id=1), group(12, "B", sector_id=1)], can_create=False)["lanes"]
        self.assertEqual([lane["add"] for lane in lanes], [None, None])

    MENU = dict(can_manage=lambda kind, sector_id: True, config_url="/config/etapas/")

    def test_who_manages_the_sector_gets_the_menu_of_its_stage_and_status_lanes(self):
        stage = build([group(11, "A fazer", sector_id=1)], "stage", **self.MENU)["lanes"][0]
        self.assertTrue(stage["menu"])
        links = json.loads(dict(stage["menu_attrs"])["data-lane-menu-items"])
        self.assertEqual(links, [{"label": "Editar as etapas do setor", "icon": "sliders", "href": "/config/etapas/?domain=demandas&sector=1"}])
        condition = build([group(12, "Normal", sector_id=2)], "condition", **self.MENU)["lanes"][0]
        links = json.loads(dict(condition["menu_attrs"])["data-lane-menu-items"])
        self.assertEqual((links[0]["label"], links[0]["href"]), ("Editar os status do setor", "/config/etapas/?domain=demandas&sector=2"))

    def test_there_is_no_menu_where_there_is_nothing_to_offer(self):
        for group_by in ("sector", "owner", "urgency"):
            self.assertFalse(build([group(5, "X")], group_by, **self.MENU)["lanes"][0]["menu"], group_by)
        self.assertFalse(build([group("empty", "Sem estágio")], "stage", **self.MENU)["lanes"][0]["menu"])
        self.assertFalse(build([group(11, "A fazer", sector_id=1)], "stage", can_manage=lambda *_: False, config_url="/c/")["lanes"][0]["menu"])
        self.assertFalse(build([group(11, "A fazer", sector_id=1)], "stage")["lanes"][0]["menu"])  # sem quem diga: nada de botão vazio
        self.assertNotIn("menu_attrs", build([group(5, "X")], "owner", **self.MENU)["lanes"][0])


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


class BuilderCardTests(SimpleTestCase):
    """O cartão de Demandas no contrato do kit: título que renomeia no lugar, ficha pelo código e pelo ⋯."""

    def card(self, **extra):
        groups = [group(1, "A", [item(7, **extra.pop("item", {}))], sector_id=1), group(2, "B", sector_id=1)]
        return build(groups, **extra)["lanes"][0]["cards"][0]

    def test_the_title_renames_in_place_only_for_who_may_edit_and_when_the_title_field_exists(self):
        self.assertTrue(self.card(item={"inline": {"title": True}}, can_rename=True)["title_editable"])
        self.assertFalse(self.card(item={"inline": {"title": False}}, can_rename=True)["title_editable"])
        self.assertFalse(self.card(item={"inline": None}, can_rename=True)["title_editable"])
        self.assertFalse(self.card(item={"inline": {"title": True}}, can_rename=False)["title_editable"])  # sem o campo Título não há onde gravar

    def test_every_card_has_the_menu_and_the_demand_opens_from_the_code_and_from_the_title_when_it_does_not_rename(self):
        card = self.card(item={"code": "DEM-2026-00007"})
        self.assertTrue(card["menu"])
        self.assertEqual(card["link"], {"text": "DEM-2026-00007", "url": "/demandas/7/?next=/demandas/kanban/", "label": "Abrir a demanda Demanda 7"})
        self.assertEqual(card["url"], card["link"]["url"])  # quem não renomeia clica no título e abre a ficha, como antes

    def test_a_demand_without_code_still_has_a_way_in(self):
        self.assertEqual(self.card()["link"]["text"], "Abrir")

    def test_the_card_carries_what_the_host_scripts_need(self):
        card = self.card()
        self.assertEqual(card["attrs"], [("data-activity-id", 7), ("data-detail-url", "/demandas/7/?next=/demandas/kanban/")])
        self.assertEqual(card["title_label"], "Título da demanda")


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

    def test_the_kanban_is_the_same_component_with_or_without_the_workspace(self):
        """Decisão do usuário: o Kanban de Quadros é o Kanban de Demandas, sem flag. A tela de sempre (flag desligada) mantém o
        resto (cabeçalho, abas, filtros), mas o Kanban dela é o componente único."""
        with override_settings(WORKSPACE_V2="off"):
            old = self.client.get(reverse("activity-kanban"), {"tab": "todas"})
        self.assertTemplateUsed(old, "boards/demand_work_board.html")
        self.assertTemplateNotUsed(old, "workspace/demandas.html")
        for template in ("boards/_demand_kanban.html", "kanban/_lanes.html", "kanban/_lane.html", "kanban/_card.html"):
            self.assertTemplateUsed(old, template)
        self.assertContains(old, "data-kanban-lanes")
        self.assertNotContains(old, "data-work-kanban")  # o Kanban antigo (boards/_work_kanban.html) não é mais o de Demandas
        self.assertContains(old, "js/kanban-core.js")
        self.assertContains(old, "js/demand-kanban.js")
        self.assertContains(old, "data-board-toasts")
        on = self.page()
        self.assertEqual([lane["label"] for lane in old.context["kanban"]["lanes"]], [lane["label"] for lane in on.context["kanban"]["lanes"]])

    def test_the_old_screen_keeps_its_own_filters_and_the_other_two_views(self):
        with override_settings(WORKSPACE_V2="off"):
            lista = self.client.get(reverse("activity-list"), {"tab": "todas"})
            calendario = self.client.get(reverse("activity-calendar"), {"tab": "todas"})
        for response in (lista, calendario):
            self.assertTemplateUsed(response, "boards/demand_work_board.html")
            self.assertTemplateNotUsed(response, "kanban/_lanes.html")


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


class RenameInPlaceTests(KanbanBase):
    def titles(self, user, **params):
        kanban = self.kanban(user=user, **params)
        return {title: card["title_editable"] for title, (_lane, card) in self.cards(kanban).items()}

    def test_who_may_edit_renames_in_place_and_the_page_says_where_to_save(self):
        grant_actions(self.mover, [catalog.ATIVIDADE_EDITAR], organization=self.org)
        response = self.page(user=self.mover, agrupar="stage")
        field = self.board.fields.get(key="title")
        html = response.content.decode()
        self.assertIn(f'data-rename-url="/quadros/dominio/{self.board.pk}/campos/{field.pk}/itens/0/valor/"', html)
        self.assertTrue(all(self.titles(self.mover, agrupar="stage").values()))
        self.assertIn('data-card-title tabindex="0" role="textbox" aria-label="Título da demanda"', html)

    def test_who_only_reads_keeps_the_title_as_a_link(self):
        self.assertFalse(any(self.titles(self.leitor, agrupar="stage").values()))

    def test_a_finished_demand_never_renames(self):
        grant_actions(self.mover, [catalog.ATIVIDADE_EDITAR], organization=self.org)
        self.assertEqual(self.titles(self.mover, tab="todas", concluidas="1", agrupar="stage"), {"Já concluída": False})

    def test_the_cards_carry_the_ids_the_scripts_use(self):
        html = self.page(agrupar="stage").content.decode()
        self.assertIn(f'data-activity-id="{self.a1.pk}"', html)
        self.assertIn(f'data-detail-url="/demandas/{self.a1.pk}/?next=', html)
        self.assertIn(f'<a class="kanban-card__code" href="/demandas/{self.a1.pk}/', html)

    def test_without_the_title_field_nobody_renames(self):
        grant_actions(self.mover, [catalog.ATIVIDADE_EDITAR], organization=self.org)
        self.board.fields.filter(key="title").update(is_active=False)
        response = self.page(user=self.mover, agrupar="stage")
        self.assertNotIn("data-rename-url", response.content.decode())
        self.assertFalse(any(card["title_editable"] for lane in response.context["kanban"]["lanes"] for card in lane["cards"]))

    def test_the_cost_does_not_grow_with_the_number_of_cards_even_with_the_edit_permissions(self):
        def queries():
            with CaptureQueriesContext(connection) as captured:
                self.page(user=self.mover, agrupar="stage")
            return len(captured)

        grant_actions(self.mover, [catalog.ATIVIDADE_EDITAR], organization=self.org)
        queries()
        base = queries()
        for index in range(12):
            self._activity(f"Extra {index}", self.ana, self.orcamento, self.afazer, self.normal)
        self.assertLessEqual(queries(), base + 1)


class ConfigureCardsTests(KanbanBase):
    """"Configurar cartões": o diálogo de Quadros (`LPSKanbanCore.openConfig`) com os dados desta visualização."""

    def setUp(self):
        super().setUp()
        grant_actions(self.mover, [catalog.QUADRO_GERIR_COLUNAS], organization=self.org)

    def config(self, response):
        html = response.content.decode()
        match = re.search(r'<script id="kanban-config" type="application/json">(.*?)</script>', html, re.S)
        return json.loads(match.group(1)) if match else None

    def test_who_configures_the_board_gets_the_button_and_the_data(self):
        response = self.page(user=self.mover, agrupar="stage")
        self.assertContains(response, "data-kanban-config")
        config = self.config(response)
        view = self.view
        self.assertEqual(config["fields_url"], reverse("workboard-card-fields", args=[view.pk]))
        self.assertEqual(config["settings_url"], reverse("workboard-view-settings", args=[view.pk]))
        title = self.board.fields.get(key="title")
        self.assertEqual(config["always"], [title.pk])
        self.assertNotIn(title.pk, [field["id"] for field in config["fields"]], "o Título é o título do cartão: não é um campo a escolher")
        self.assertEqual(config["settings"], {"show_empty": config["settings"]["show_empty"], "show_field_names": False})

    def test_the_card_fields_are_listed_with_the_names_the_card_shows_and_the_ones_on_the_card_come_first(self):
        self.show_card_fields("stage", "condition", "tasks")
        config = self.config(self.page(user=self.mover, agrupar="stage"))
        names = [field["name"] for field in config["fields"]]
        on_the_card = [self.board.fields.get(key=key).pk for key in ("owner", "sector", "urgency", "requested_deadline", "stage", "condition", "tasks")]
        self.assertEqual([field["id"] for field in config["fields"]][:len(config["selected"])], config["selected"])  # os do cartão primeiro, na ordem
        self.assertTrue(set(on_the_card) <= set(config["selected"]))
        for name in ("Etapa", "Status", "Prioridade", "Responsável", "Setor", "Prazo", "Tarefas"):
            self.assertIn(name, names)  # os mesmos rótulos do cartão (Etapa ≠ Status; no cadastro os dois se chamam "Status")

    def test_who_cannot_configure_gets_neither_the_button_nor_the_data(self):
        response = self.page(user=self.leitor, agrupar="stage")
        self.assertNotContains(response, "data-kanban-config")
        self.assertNotContains(response, 'id="kanban-config"')

    def test_the_old_side_panel_for_the_cards_is_gone_but_adding_a_field_stays(self):
        html = self.page(user=self.mover, agrupar="stage").content.decode()
        self.assertNotIn("data-work-card-settings-panel", html)
        self.assertNotIn("data-work-card-settings-form", html)
        self.assertIn("data-work-add-field-panel", html)  # "Adicionar campo" continua sendo daquele painel

    def test_both_screens_give_the_same_configuration(self):
        with override_settings(WORKSPACE_V2="off"):
            self.client.force_login(self.mover)
            old = self.client.get(reverse("activity-kanban"), {"tab": "todas"})
        self.assertEqual(self.config(old), self.config(self.page(user=self.mover)))
        self.assertContains(old, "data-kanban-config")

    def test_saving_the_order_through_the_real_endpoint_changes_the_cards_and_keeps_the_title(self):
        self.client.force_login(self.mover)
        config = self.config(self.page(user=self.mover))
        owner, urgency = (self.board.fields.get(key=key).pk for key in ("owner", "urgency"))
        response = self.client.post(
            config["fields_url"], data=json.dumps({"field_ids": config["always"] + [urgency, owner]}), content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        kanban = self.kanban(user=self.mover)
        _lane, card = self.cards(kanban)["Orçamento Aurora"]
        self.assertEqual([field["label"] for field in card["fields"]], ["Prioridade", "Responsável"])  # a ordem escolhida
        self.assertEqual(card["title"], "Orçamento Aurora")  # o título segue sendo o título do cartão
        self.assertEqual(self.config(self.page(user=self.mover))["selected"], [urgency, owner])

    def test_the_display_options_go_through_the_view_settings_endpoint_and_reach_the_cards(self):
        self.client.force_login(self.mover)
        config = self.config(self.page(user=self.mover))
        response = self.client.post(config["settings_url"], data=json.dumps({"show_field_names": True}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("<dt>Responsável</dt>", self.page(user=self.mover).content.decode())
        self.assertTrue(self.config(self.page(user=self.mover))["settings"]["show_field_names"])

    def test_who_cannot_configure_cannot_save_either(self):
        config = self.config(self.page(user=self.mover))  # (a página troca o login: pegar os endereços ANTES de entrar como leitor)
        self.client.force_login(self.leitor)
        for url, body in ((config["fields_url"], {"field_ids": []}), (config["settings_url"], {"show_empty": False})):
            self.assertEqual(self.client.post(url, data=json.dumps(body), content_type="application/json").status_code, 403)


class EditFieldsOnTheCardTests(KanbanBase):
    """Os campos do cartão editam com o mesmo editor da Lista: a tela só oferece o que o servidor aceita."""

    FIELDS = ("owner", "sector", "urgency", "requested_deadline", "stage", "condition")

    def setUp(self):
        super().setUp()
        self.show_card_fields("stage", "condition")
        grant_actions(
            self.mover, [catalog.ATIVIDADE_EDITAR, catalog.ATIVIDADE_ALTERAR_DONO, catalog.ATIVIDADE_DEFINIR_ETAPA, catalog.ATIVIDADE_DEFINIR_CONDICAO],
            organization=self.org,
        )

    def fields_of(self, user, title="Orçamento Aurora", **params):
        kanban = self.kanban(user=user, **params)
        _lane, card = self.cards(kanban)[title]
        return {field["label"]: field for field in card["fields"]}, card

    @staticmethod
    def hook(field):
        return dict(field.get("attrs", []))

    def test_who_may_edit_gets_every_field_as_editable_with_the_hook_and_the_model(self):
        fields, _card = self.fields_of(self.mover)
        for label, key in (("Responsável", "owner"), ("Setor", "sector"), ("Prioridade", "urgency"), ("Prazo", "requested_deadline"), ("Etapa", "stage"), ("Status", "condition")):
            field = fields[label]
            self.assertTrue(field["editable"], label)
            self.assertEqual(self.hook(field)["data-inline-field"], key, label)
            json.loads(self.hook(field)["data-inline-model"])  # JSON válido

    def test_the_models_say_the_current_value(self):
        Activity.objects.filter(pk=self.a1.pk).update(requested_deadline=timezone.make_aware(datetime.datetime(2026, 10, 14, 17, 47)))
        fields, _card = self.fields_of(self.mover)
        owner = json.loads(self.hook(fields["Responsável"])["data-inline-model"])
        self.assertEqual((owner["value"], owner["text"]), (str(self.ana.pk), "ana"))
        sector = json.loads(self.hook(fields["Setor"])["data-inline-model"])
        self.assertEqual((sector["id"], sector["name"]), (self.orcamento.pk, "Orçamento"))
        self.assertEqual(self.hook(fields["Setor"])["data-option-id"], self.orcamento.pk)
        stage = json.loads(self.hook(fields["Etapa"])["data-inline-model"])
        self.assertEqual((stage["id"], stage["name"]), (self.afazer.pk, "A fazer"))
        self.assertEqual(self.hook(fields["Etapa"])["data-option-id"], self.afazer.pk)
        urgency = json.loads(self.hook(fields["Prioridade"])["data-inline-model"])
        self.assertEqual((urgency["id"], urgency["name"]), ("MEDIA", "Média"))
        self.assertRegex(urgency["color"], r"^#[0-9A-Fa-f]{6}$")
        deadline = json.loads(self.hook(fields["Prazo"])["data-inline-model"])
        self.assertEqual((deadline["date"], deadline["time"], deadline["text"]), ("2026-10-14", "17:47", "14/10/2026 17:47"))

    def test_an_empty_value_still_has_its_hook_and_an_empty_model(self):
        Activity.objects.filter(pk=self.a1.pk).update(stage=None, condition=None, requested_deadline=None)
        fields, _card = self.fields_of(self.mover)
        self.assertEqual(json.loads(self.hook(fields["Etapa"])["data-inline-model"]), None)
        self.assertEqual(self.hook(fields["Etapa"])["data-option-id"], "")
        self.assertEqual(json.loads(self.hook(fields["Prazo"])["data-inline-model"])["text"], "Sem prazo")

    def test_who_only_reads_gets_nothing_editable_and_no_hooks_in_the_page(self):
        fields, _card = self.fields_of(self.leitor)
        self.assertFalse(any(field.get("editable") for field in fields.values()))
        html = self.page(user=self.leitor, agrupar="stage").content.decode()
        self.assertNotIn("data-inline-field", html)
        self.assertNotIn("is-editable", html)

    def test_each_permission_unlocks_only_its_own_field(self):
        user = self.visitante
        grant_actions(user, [catalog.ATIVIDADE_EDITAR], organization=self.org)
        fields, _card = self.fields_of(user, title="Item do visitante")
        self.assertFalse(fields["Responsável"].get("editable"), "trocar o responsável é outra ação (ALTERAR_DONO)")
        self.assertTrue(fields["Setor"]["editable"])
        self.assertTrue(fields["Prioridade"]["editable"])
        self.assertTrue(fields["Prazo"]["editable"])
        self.assertFalse(fields["Etapa"].get("editable"), "mover a etapa é a ação própria")
        self.assertFalse(fields["Status"].get("editable"), "definir o status é a ação própria")

    def test_a_finished_demand_has_nothing_editable(self):
        fields, _card = self.fields_of(self.mover, title="Já concluída", tab="todas", concluidas="1")
        self.assertFalse(any(field.get("editable") for field in fields.values()))

    def test_a_demand_without_sector_cannot_choose_stage_or_status(self):
        sem = self._activity("Sem setor", self.ana, None, None, None)
        fields, _card = self.fields_of(self.mover, title="Sem setor")
        self.assertFalse(fields["Etapa"].get("editable"))
        self.assertFalse(fields["Status"].get("editable"))
        self.assertTrue(fields["Responsável"]["editable"])
        del sem

    def test_the_progress_is_never_editable_and_neither_is_the_title_field(self):
        self.show_card_fields("tasks")
        fields, card = self.fields_of(self.mover)
        self.assertFalse(fields["Tarefas"].get("editable"))
        self.assertNotIn("Título", fields)

    def test_the_region_carries_the_inline_endpoints_and_the_overlay_on_both_screens(self):
        for flag in ("on", "off"):
            with self.subTest(flag=flag), override_settings(WORKSPACE_V2=flag):
                self.client.force_login(self.mover)
                html = self.client.get(reverse("activity-kanban"), {"tab": "todas"}).content.decode()
                self.assertIn('data-inline-url="/demandas/999999999/inline/"', html)
                self.assertIn('data-inline-sentinel="999999999"', html)
                self.assertIn(f'data-people-url="{reverse("person-search")}"', html)
                self.assertIn('data-options-url="/demandas/999999999/inline/opcoes/"', html)
                self.assertIn('id="activity-inline-overlay-root"', html)
                for script in ("js/activity-inline-edit.js", "js/activity-inline-options.js", "js/kanban-core.js", "js/demand-kanban.js"):
                    self.assertIn(script, html, script)
                self.assertLess(html.index("js/activity-inline-edit.js"), html.index("js/demand-kanban.js"))  # o adaptador se pendura nele

    def test_the_demand_list_still_loads_the_same_inline_scripts(self):
        self.client.force_login(self.mover)
        html = self.client.get(reverse("activity-list"), {"tab": "todas"}).content.decode()
        self.assertIn("js/activity-inline-edit.js", html)
        self.assertNotIn("js/kanban-core.js", html)

    def test_the_page_costs_no_more_queries_per_card_with_the_edit_flags(self):
        def queries():
            with CaptureQueriesContext(connection) as captured:
                self.page(user=self.mover, agrupar="stage")
            return len(captured)

        queries()
        base = queries()
        for index in range(12):
            self._activity(f"Extra {index}", self.ana, self.orcamento, self.afazer, self.normal)
        self.assertLessEqual(queries(), base + 1)

    def post(self, activity_id, **data):
        return self.client.post(reverse("activity-inline-update", args=[activity_id]), data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def server_accepts(self, activity_id, **data):
        try:
            with transaction.atomic():
                response = self.post(activity_id, **data)
                raise _Rollback
        except _Rollback:
            pass
        return response.status_code == 200

    def test_the_card_offers_a_field_exactly_when_the_server_accepts_editing_it(self):
        """Cada campo × cada cartão × quem edita e quem só lê: "a tela oferece" ⇔ "o servidor aceita um valor válido"."""
        def valid(card):
            """Um valor VÁLIDO e DIFERENTE do atual (pedir o que a demanda já tem é um "nada a gravar" que responde 200 sem
            consultar permissão: não prova nada)."""
            current = Activity.objects.get(pk=card["id"])
            return {
                "owner": {"field": "owner", "value": str(self.bia.pk if current.owner_id != self.bia.pk else self.gestor.pk)},
                "urgency": {"field": "urgency", "value": "ALTA" if current.urgency != "ALTA" else "BAIXA"},
                "requested_deadline": {"field": "requested_deadline", "date": "2026-12-01", "time": ""},
                "sector": {"field": "sector", "value": str(self.financeiro.pk)},
                "stage": {"field": "stage", "value": str(self.levantamento.pk if current.stage_id != self.levantamento.pk else self.afazer.pk)},
                "condition": {"field": "condition", "value": str(self.aguardando.pk if current.condition_id != self.aguardando.pk else self.normal.pk)},
            }
        outcomes = {True: 0, False: 0}
        for user in (self.mover, self.leitor, self.visitante):
            for sample in ({"tab": "todas"}, {"tab": "todas", "concluidas": "1"}):
                kanban = self.kanban(user=user, agrupar="stage", **sample)
                for lane in kanban["lanes"]:
                    for card in lane["cards"]:
                        if card["scope"] != str(self.orcamento.pk):
                            continue  # etapa e status "válidos" acima são do Orçamento
                        for field in card["fields"]:
                            key = dict(field.get("attrs", [])).get("data-inline-field")
                            label_key = {"Responsável": "owner", "Setor": "sector", "Prioridade": "urgency", "Prazo": "requested_deadline", "Etapa": "stage", "Status": "condition"}.get(field["label"])
                            if label_key is None:
                                continue
                            offered = bool(field.get("editable"))
                            if offered:
                                self.assertEqual(key, label_key)
                            accepts = self.server_accepts(card["id"], **valid(card)[label_key])
                            who = f"{user.username} «{card['title']}» {field['label']}"
                            if offered:
                                self.assertTrue(accepts, f"{who}: a tela oferece editar e o servidor recusou")
                            else:
                                self.assertFalse(accepts, f"{who}: a tela NÃO oferece editar mas o servidor aceitou")
                            outcomes[offered] += 1
        self.assertGreater(outcomes[True], 10, "a grade não exercitou o lado 'oferece'")
        self.assertGreater(outcomes[False], 10, "a grade não exercitou o lado 'não oferece'")


class AddAndMenuOnThePageTests(KanbanBase):
    """O "+ Adicionar" e o ⋮ das raias na página real, para quem pode e para quem não pode."""

    def setUp(self):
        super().setUp()
        grant_actions(self.gestor, [catalog.ATIVIDADE_CRIAR], organization=self.org)  # cria em qualquer setor
        grant_action(self.bia, catalog.ATIVIDADE_CRIAR, organization=self.org, sector=self.financeiro)  # só no Financeiro

    @staticmethod
    def adds(kanban):
        return {lane["label"] + ("/" + lane["sector"] if lane["sector"] else ""): (dict(parse_qs(urlsplit(lane["add"]["href"]).query)) if lane["add"] else None)
                for lane in kanban["lanes"]}

    def test_a_stage_lane_opens_the_new_demand_window_in_its_stage_and_sector(self):
        adds = self.adds(self.kanban(user=self.gestor, agrupar="stage"))
        self.assertEqual(adds["A fazer/Orçamento"]["etapa"], [str(self.afazer.pk)])
        self.assertEqual(adds["A fazer/Orçamento"]["setor"], [str(self.orcamento.pk)])
        self.assertEqual(adds["A fazer/Financeiro"]["etapa"], [str(self.f_afazer.pk)])
        self.assertEqual(adds["A fazer/Financeiro"]["setor"], [str(self.financeiro.pk)])
        self.assertIn("next", adds["A fazer/Orçamento"])  # e a ficha volta para este Kanban

    def test_who_creates_only_in_one_sector_gets_the_add_only_on_its_lanes(self):
        adds = self.adds(self.kanban(user=self.bia, agrupar="stage"))
        self.assertIsNone(adds["A fazer/Orçamento"])
        self.assertIsNone(adds["Levantamento/Orçamento"])
        self.assertIsNotNone(adds["A fazer/Financeiro"])

    def test_who_cannot_create_sees_no_add_in_any_grouping(self):
        for group_by in ("stage", "condition", "sector", "owner", "urgency"):
            with self.subTest(group_by=group_by):
                self.assertEqual({lane["add"] for lane in self.kanban(user=self.leitor, agrupar=group_by)["lanes"]}, {None})

    def test_the_other_groupings_preset_status_sector_owner_and_priority(self):
        condition = self.adds(self.kanban(user=self.gestor, agrupar="condition"))
        self.assertEqual(condition["Aguardando cliente/Orçamento"]["condicao"], [str(self.aguardando.pk)])
        sector = self.adds(self.kanban(user=self.gestor, agrupar="sector"))
        self.assertEqual(sector["Orçamento"]["setor"], [str(self.orcamento.pk)])
        owner = self.adds(self.kanban(user=self.gestor, agrupar="owner", setor=self.orcamento.pk))
        self.assertEqual(owner["ana"]["pessoa"], [str(self.ana.pk)])
        self.assertEqual(owner["ana"]["setor"], [str(self.orcamento.pk)])  # o filtro de setor vira o setor da demanda nova
        urgency = self.adds(self.kanban(user=self.gestor, agrupar="urgency"))
        self.assertEqual(urgency["Média"]["urgencia"], ["MEDIA"])
        self.assertNotIn("setor", urgency["Média"])  # sem filtro de setor, a janela pergunta

    def test_the_blank_lane_never_has_an_add(self):
        Activity.objects.filter(pk=self.a1.pk).update(stage=None)
        lanes = {lane["key"]: lane for lane in self.kanban(user=self.gestor, agrupar="stage")["lanes"]}
        self.assertIsNone(lanes["empty"]["add"])

    def test_the_menu_of_a_stage_lane_only_exists_for_who_manages_that_sector(self):
        grant_action(self.gestor, catalog.ETAPA_GERIR, organization=self.org, sector=self.orcamento)
        lanes = {(lane["label"], lane["sector"]): lane for lane in self.kanban(user=self.gestor, agrupar="stage")["lanes"]}
        mine, other = lanes[("A fazer", "Orçamento")], lanes[("A fazer", "Financeiro")]
        self.assertTrue(mine["menu"])
        links = json.loads(dict(mine["menu_attrs"])["data-lane-menu-items"])
        self.assertEqual(links[0]["href"], f"{reverse('config-etapas-status')}?domain=demandas&sector={self.orcamento.pk}")
        self.assertFalse(other["menu"])  # gere o Orçamento, não o Financeiro
        self.assertFalse(any(lane["menu"] for lane in self.kanban(user=self.leitor, agrupar="stage")["lanes"]))

    def test_the_status_menu_asks_for_the_status_permission_not_the_stage_one(self):
        grant_action(self.gestor, catalog.CONDICAO_GERIR, organization=self.org, sector=self.orcamento)
        stage = self.kanban(user=self.gestor, agrupar="stage")["lanes"]
        self.assertFalse(any(lane["menu"] for lane in stage))
        condition = [lane for lane in self.kanban(user=self.gestor, agrupar="condition")["lanes"] if lane["menu"]]
        self.assertTrue(condition)
        for lane in condition:
            self.assertEqual(json.loads(dict(lane["menu_attrs"])["data-lane-menu-items"])[0]["label"], "Editar os status do setor")

    def test_the_page_shows_the_add_link_and_the_lane_menu_button(self):
        grant_action(self.gestor, catalog.ETAPA_GERIR, organization=self.org, sector=self.orcamento)
        html = self.page(user=self.gestor, agrupar="stage").content.decode()
        self.assertRegex(html, r'<a class="kanban-add" data-kanban-add href="[^"]*etapa=%d[^"]*" data-activity-action="" data-activity-navigate="">' % self.afazer.pk)
        self.assertIn("data-lane-menu data-lane-menu-items=", html)
        self.assertIn("Editar as etapas do setor", html)

    def test_the_cost_of_the_page_does_not_grow_with_the_cards(self):
        grant_action(self.gestor, catalog.ETAPA_GERIR, organization=self.org, sector=self.orcamento)

        def queries():
            with CaptureQueriesContext(connection) as captured:
                self.page(user=self.gestor, agrupar="stage")
            return len(captured)

        queries()
        base = queries()
        for index in range(15):
            self._activity(f"Extra {index}", self.ana, self.orcamento, self.afazer, self.normal)
        self.assertLessEqual(queries(), base + 1)

    # -- o contrato: a raia oferece o "+ Adicionar" ⇔ o servidor deixa criar ali --------------------------------------------

    def create(self, sector_id, owner_id, **extra):
        data = {"title": "Criada na raia", "owner": owner_id, "sector": sector_id, "urgency": "MEDIA", "acao": "publicar", **extra}
        return self.client.post(reverse("activity-create"), data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def server_accepts_create(self, sector_id, owner_id):
        try:
            with transaction.atomic():
                response = self.create(sector_id, owner_id)
                raise _Rollback
        except _Rollback:
            pass
        return response.status_code == 200 and "redirect_url" in response.json()

    def test_the_lane_offers_the_add_exactly_when_the_server_lets_the_person_create_there(self):
        outcomes = {True: 0, False: 0}
        for user in (self.gestor, self.bia, self.leitor):
            self.client.force_login(user)
            for group_by in ("stage", "condition", "sector", "owner", "urgency"):
                for params in ({}, {"setor": self.orcamento.pk}, {"setor": self.financeiro.pk}):
                    kanban = self.kanban(user=user, agrupar=group_by, **params)
                    for lane in kanban["lanes"]:
                        if lane["is_blank"] or not lane["accepts"]:
                            continue
                        if group_by in ("stage", "condition"):
                            sector_id = int(lane["scope"])
                        elif group_by == "sector":
                            sector_id = int(lane["key"])
                        elif params:
                            sector_id = params["setor"]
                        else:
                            continue  # sem setor no filtro a janela pergunta: nada a comparar
                        owner_id = int(lane["key"]) if group_by == "owner" else user.pk
                        offered = lane["add"] is not None
                        accepted = self.server_accepts_create(sector_id, owner_id)
                        who = f"{user.username} {group_by} «{lane['label']}» {params}"
                        self.assertEqual(offered, accepted, f"{who}: oferece={offered}, servidor aceita={accepted}")
                        outcomes[offered] += 1
        self.assertGreater(outcomes[True], 10, "a grade não exercitou o lado 'oferece'")
        self.assertGreater(outcomes[False], 10, "a grade não exercitou o lado 'não oferece'")

    def test_the_link_the_lane_offers_opens_the_window_filled_and_creates_in_the_lane(self):
        Activity.objects.filter(pk=self.a2.pk).update(urgency="ALTA")  # existe uma raia "Alta"
        self.client.force_login(self.gestor)
        samples = (
            ("stage", "A fazer", "Levantamento", "stage_id", self.levantamento.pk, {}),
            ("condition", "Aguardando cliente", "Aguardando cliente", "condition_id", self.aguardando.pk, {}),
            ("sector", "Financeiro", "Financeiro", "sector_id", self.financeiro.pk, {}),
            ("owner", "ana", "ana", "owner_id", self.ana.pk, {"setor": self.orcamento.pk}),
            ("urgency", "Alta", "Alta", "urgency", "ALTA", {"setor": self.orcamento.pk}),
        )
        for group_by, _first, label, attribute, expected, params in samples:
            with self.subTest(group_by=group_by):
                lane = next(lane for lane in self.kanban(user=self.gestor, agrupar=group_by, **params)["lanes"] if lane["label"] == label and lane["add"])
                window = self.client.get(lane["add"]["href"])
                self.assertEqual(window.status_code, 200)
                initial = window.context["form"].initial
                data = {"title": f"Nova {group_by}", "acao": "publicar", "urgency": initial.get("urgency", "MEDIA"),
                        "sector": initial.get("sector", ""), "owner": getattr(initial.get("owner"), "pk", self.gestor.pk)}
                for name in ("stage", "condition"):
                    if initial.get(name):
                        data[name] = initial[name]
                created = self.client.post(lane["add"]["href"], data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
                self.assertEqual(created.status_code, 200, created.content)
                activity = Activity.objects.get(title=f"Nova {group_by}")
                self.assertEqual(getattr(activity, attribute), expected)


class WhoCanDragTests(KanbanBase):
    def movable(self, user, **params):
        kanban = self.kanban(user=user, **params)
        return {title: card["can_move"] for title, (_lane, card) in self.cards(kanban).items()}

    def test_someone_who_only_reads_cannot_drag_or_rename_but_still_opens_the_demand(self):
        response = self.page(user=self.leitor, agrupar="stage")
        self.assertFalse(any(self.movable(self.leitor, agrupar="stage").values()))
        html = response.content.decode()
        self.assertNotIn('draggable="true"', html)
        self.assertNotIn('role="textbox"', html)  # o título não renomeia
        self.assertIn('<a class="kanban-card__title" data-card-title href="/demandas/', html)  # e continua sendo o caminho para a ficha
        self.assertIn("data-card-menu", html)  # o ⋯ existe em todo cartão: pelo menos "Abrir demanda"
        self.assertIn("kanban-card__code", html)

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

    def test_only_the_kanban_answers_fragments_with_or_without_the_workspace(self):
        for name in ("activity-list", "activity-calendar"):
            response = self.fragment(name)
            self.assertTemplateUsed(response, "workspace/demandas.html", name)  # a Lista e o Calendário ignoram o parâmetro
        with override_settings(WORKSPACE_V2="off"):
            for name in ("activity-list", "activity-calendar"):
                ignored = self.client.get(reverse(name), {"tab": "todas", "fragmento": "raias"})
                self.assertTemplateUsed(ignored, "boards/demand_work_board.html", name)
                self.assertTemplateNotUsed(ignored, "kanban/_lanes.html", name)
            kanban = self.client.get(reverse("activity-kanban"), {"tab": "todas", "fragmento": "raias"})
        self.assertTemplateUsed(kanban, "kanban/_lanes.html")  # o Kanban redesenha as raias também na tela de sempre
        self.assertTemplateNotUsed(kanban, "boards/demand_work_board.html")
        self.assertIn("data-lane-key", kanban.content.decode())

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

    def rename_status(self, card, title="Novo título"):
        field = self.board.fields.get(key="title")
        try:
            with transaction.atomic():
                response = self.client.post(
                    reverse("workboard-value", args=[self.board.pk, field.pk, card["id"]]),
                    data=json.dumps({"value": title, "updated_at": card["updated_at"]}), content_type="application/json",
                )
                raise _Rollback
        except _Rollback:
            pass
        return response.status_code, response.json()

    def test_the_title_edits_in_place_exactly_when_the_server_accepts_the_rename(self):
        checked = {True: 0, False: 0}
        for sample in ({"tab": "todas"}, {"tab": "minhas"}, {"tab": "minhas", "concluidas": "1"}):
            kanban = self.kanban(agrupar="stage", **sample)
            for lane in kanban["lanes"]:
                for card in lane["cards"]:
                    if card["title"] == "Rascunho do mover":
                        continue  # rascunho: a edição inline o recusa por política, o serviço não; a tela é só mais estrita
                    status, _body = self.rename_status(card)
                    label = f"{sample} «{card['title']}»"
                    if card["title_editable"]:
                        self.assertEqual(status, 200, f"{label}: a tela deixa renomear e o servidor recusou ({status})")
                    else:
                        self.assertNotEqual(status, 200, f"{label}: a tela NÃO deixa renomear mas o servidor aceitou")
                    checked[card["title_editable"]] += 1
        self.assertGreater(checked[True], 2, "a grade não exercitou o lado 'aceita'")
        self.assertGreater(checked[False], 0, "a grade não exercitou o lado 'recusa'")

    def test_the_server_answers_the_rename_with_the_new_version_and_refuses_an_empty_title(self):
        kanban = self.kanban(agrupar="stage")
        _lane, card = self.cards(kanban)["Orçamento Aurora"]
        status, body = self.rename_status(card)
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])
        self.assertIn("updated_at", body)  # o cartão guarda a versão nova: o próximo movimento não toma um 409 à toa
        status, body = self.rename_status(card, title="   ")
        self.assertEqual(status, 400)
        self.assertFalse(body["success"])

    def test_an_old_version_is_a_conflict_and_the_value_is_not_applied(self):
        field = self.board.fields.get(key="stage")
        kanban = self.kanban(agrupar="stage")
        lane, card = self.cards(kanban)["Orçamento Aurora"]
        target = next(other for other in kanban["lanes"] if other["key"] == self.levantamento.pk)
        Activity.objects.filter(pk=card["id"]).update(updated_at=timezone.now() + datetime.timedelta(minutes=5))
        self.assertEqual(self.server_status(field, card, target), 409)
