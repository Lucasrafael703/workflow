"""Kit do Kanban (templates/kanban/*): a ÚNICA marcação do Kanban do sistema (o modelo visual é o de Quadros).

Dois grupos de testes: o contrato do kit (dados simples -> marcação) e a prova de que Quadros desenha por ele.
"""

from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import reverse

from core.models import Sector

from .services import ViewService
from .testing import BoardTestCase


def card(**extra):
    base = {"id": 7, "title": "Orçamento Aurora", "url": "/demandas/7/?next=%2F", "updated_at": "2026-10-03T10:00:00+00:00",
            "scope": "5", "can_move": True, "menu": True, "fields": []}
    base.update(extra)
    return base


def lane(**extra):
    base = {"key": "1", "label": "A fazer", "color": "#579BFC", "is_blank": False, "accepts": True, "scope": "5", "sector": "",
            "count": 1, "empty_text": "Nenhuma demanda. Arraste uma demanda para cá.", "add": None, "cards": [card()]}
    base.update(extra)
    return base


def render(*lanes, **extra):
    kanban = {"item_label": "demanda", "show_field_names": False, "lanes": list(lanes) or [lane()]}
    kanban.update(extra)
    return render_to_string("kanban/_lanes.html", {"kanban": kanban})


class LaneContractTests(SimpleTestCase):
    def test_the_lane_has_the_models_classes_and_attributes(self):
        html = render()
        for marker in ('class="kanban-lane"', "data-lane ", 'data-lane-key="1"', 'data-lane-label="A fazer"', 'data-lane-scope="5"',
                       'class="kanban-lane__head"', 'class="kanban-lane__title" data-lane-title', 'class="kanban-lane__count" data-lane-count',
                       'class="kanban-lane__body" data-lane-body', 'class="kanban-lane__empty" data-lane-empty'):
            self.assertIn(marker, html, marker)

    def test_the_header_is_solid_with_text_chosen_by_contrast(self):
        self.assertIn('style="--lane-color:#579BFC;--lane-text:#FFFFFF"', render(lane(color="#579BFC")))  # azul: texto branco
        self.assertIn('style="--lane-color:#FACC15;--lane-text:#1F2937"', render(lane(color="#FACC15")))  # amarelo: texto escuro

    def test_the_count_and_the_empty_text_follow_the_cards(self):
        with_cards = render(lane())
        self.assertIn('data-lane-count title="Itens nesta raia">1<', with_cards)
        self.assertIn("data-lane-empty hidden>", with_cards)  # há cartões: o vazio fica escondido
        empty = render(lane(cards=[], count=0, empty_text="Nenhuma demanda."))
        self.assertIn("data-lane-empty>Nenhuma demanda.<", empty)
        self.assertNotIn("data-lane-empty hidden", empty)

    def test_blank_and_closed_lanes_are_marked(self):
        html = render(lane(key="empty", label="Sem estágio", color="#C4C4C4", is_blank=True, scope=""), lane(key="9", label="Fechada", accepts=False))
        self.assertIn('class="kanban-lane is-blank"', html)
        self.assertEqual(html.count("data-lane-closed"), 1)

    def test_a_sector_under_the_title_only_when_asked_and_named_in_the_aria_label(self):
        plain = render(lane(sector=""))
        self.assertNotIn("kanban-lane__meta", plain)
        mixed = render(lane(sector="Comercial"))
        self.assertIn('<p class="kanban-lane__meta">Comercial</p>', mixed)
        self.assertIn('aria-label="A fazer — Comercial"', mixed)

    def test_no_lanes_shows_the_state_not_an_empty_page(self):
        html = render_to_string("kanban/_lanes.html", {"kanban": {"lanes": [], "empty_title": "Nenhuma raia", "empty_text": "Crie etapas."}})
        self.assertIn('class="kanban-state"', html)
        self.assertIn("Nenhuma raia", html)
        self.assertIn("Crie etapas.", html)

    def test_the_footer_is_a_link_with_an_href_and_a_button_without_one(self):
        link = render(lane(add={"label": "Adicionar demanda", "href": "/demandas/nova/", "attrs": [("data-activity-action", ""), ("data-activity-navigate", "")]}))
        self.assertIn('<a class="kanban-add" data-kanban-add href="/demandas/nova/" data-activity-action="" data-activity-navigate="">', link)
        self.assertIn("Adicionar demanda", link)
        button = render(lane(add={"label": "Adicionar", "attrs": [("data-task-add", ""), ("data-state", "todo")]}))
        self.assertIn('<button type="button" class="kanban-add" data-kanban-add data-task-add="" data-state="todo">', button)
        self.assertNotIn("kanban-lane__foot", render(lane(add=None)))

    def test_nothing_is_disabled_to_look_the_same(self):
        self.assertNotIn("disabled", render(lane(), lane(key="2", cards=[card(can_move=False)], accepts=False)))


class CardContractTests(SimpleTestCase):
    def test_a_movable_card_is_draggable_and_has_the_move_menu(self):
        html = render()
        self.assertIn('<article class="kanban-card" data-card data-item-id="7" data-card-scope="5" data-updated-at="2026-10-03T10:00:00+00:00" draggable="true">', html)
        self.assertIn("data-card-menu", html)
        self.assertIn('aria-label="Opções da demanda Orçamento Aurora"', html)

    def test_a_card_that_cannot_be_moved_has_neither_drag_nor_menu(self):
        html = render(lane(cards=[card(can_move=False, menu=False)]))
        self.assertNotIn("draggable", html.replace('draggable="false"', ""))
        self.assertNotIn("data-card-menu", html)

    def test_the_title_is_a_link_that_does_not_hijack_the_drag(self):
        html = render()
        self.assertIn('<a class="kanban-card__title" data-card-title href="/demandas/7/?next=%2F" draggable="false">Orçamento Aurora</a>', html)
        self.assertIn('<span class="kanban-card__title" data-card-title>Sem título</span>', render(lane(cards=[card(url="", title="")])).replace("kanban-card__title is-empty", "kanban-card__title"))

    def test_user_text_is_escaped(self):
        html = render(lane(cards=[card(title="<script>alert(1)</script>")], label="<b>x</b>"))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn("<b>x</b>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_another_fields_template_replaces_only_the_body(self):
        html = render(lane(cards=[card(fields_template="kanban/_fields.html", fields=[{"kind": "text", "label": "Obra", "text": "Arena"}])]))
        self.assertIn('<dl class="kanban-card__fields">', html)


class FieldTypeTests(SimpleTestCase):
    @staticmethod
    def fields_html(*fields, **extra):
        return render(lane(cards=[card(fields=list(fields))]), **extra)

    def fields(self, *fields, **extra):
        return self.fields_html(*fields, **extra)

    def test_each_type_uses_the_models_cell_classes(self):
        sector = Sector(pk=3, name="Comercial", color="#FACC15")
        html = self.fields(
            {"kind": "person", "label": "Responsável", "name": "Ana Souza", "initials": "AS"},
            {"kind": "sector", "label": "Setor", "sector": sector},
            {"kind": "pill", "label": "Etapa", "text": "Proposta", "color": "#579BFC"},
            {"kind": "date", "label": "Prazo", "text": "02/10/2026", "overdue": True},
            {"kind": "progress", "label": "Tarefas", "done": 2, "total": 5, "percent": 40},
            {"kind": "text", "label": "Obra", "text": "Arena Norte"},
        )
        self.assertIn('<span class="board-avatar" aria-hidden="true">AS</span><span class="board-person__name">Ana Souza</span>', html)
        self.assertIn('class="sector-badge sector-badge--compact"', html)
        self.assertIn('<span class="board-pill" style="background:#579BFC;color:#FFFFFF">Proposta</span>', html)
        self.assertIn('<span class="board-date is-overdue">02/10/2026 <span class="board-date__flag">vencido</span></span>', html)
        self.assertIn('class="kanban-progress__bar"', html)
        self.assertIn("2/5", html)
        self.assertIn('<span class="board-text">Arena Norte</span>', html)

    def test_overdue_is_a_badge_never_a_background_or_a_card_class(self):
        html = self.fields({"kind": "date", "label": "Prazo", "text": "02/10/2026", "overdue": True})
        self.assertIn("board-date__flag", html)
        self.assertNotIn("is-late", html)
        self.assertIn('<article class="kanban-card" data-card', html)  # o cartão não ganha classe de atraso
        self.assertNotIn("is-overdue\"", html.split("<dl")[0])

    def test_a_date_that_is_not_overdue_has_no_flag(self):
        html = self.fields({"kind": "date", "label": "Prazo", "text": "10/10/2026", "overdue": False})
        self.assertNotIn("vencido", html)

    def test_empty_values_show_a_dash_and_tasks_zero_says_so(self):
        html = self.fields(
            {"kind": "person", "label": "Responsável", "name": ""},
            {"kind": "pill", "label": "Etapa", "text": ""},
            {"kind": "date", "label": "Prazo", "text": ""},
            {"kind": "text", "label": "Obra", "text": ""},
            {"kind": "progress", "label": "Tarefas", "done": 0, "total": 0, "percent": 0},
        )
        self.assertEqual(html.count('<span class="board-empty">—</span>'), 3)
        self.assertIn("Sem responsável", html)
        self.assertIn("Sem tarefas", html)

    def test_field_names_are_visible_only_when_asked_otherwise_screen_reader_only(self):
        field = {"kind": "text", "label": "Obra", "text": "Arena"}
        self.assertIn("<dt>Obra</dt>", self.fields(field, show_field_names=True))
        hidden = self.fields(field, show_field_names=False)
        self.assertIn('<dt class="sr-only">Obra</dt>', hidden)
        self.assertNotIn("<dt>Obra</dt>", hidden)


class ContractV2Tests(SimpleTestCase):
    """O kit passou a cobrir TUDO o que o Kanban de Quadros faz: é a única marcação, Quadros e Demandas só entregam dados."""

    def test_a_lane_may_name_its_label_have_a_menu_and_a_total(self):
        html = render(lane(option_id=42, menu=True, total="R$ 2.500,00", scope=""))
        self.assertIn('data-lane-key="1" data-option-id="42" data-lane-label="A fazer"', html)
        self.assertIn('<button type="button" class="kanban-lane__menu" data-lane-menu aria-haspopup="menu" aria-label="Opções da raia A fazer">', html)
        self.assertIn('<p class="kanban-lane__total" data-lane-total>R$ 2.500,00</p>', html)
        self.assertNotIn("data-lane-scope", html)  # sem escopo o atributo nem aparece

    def test_without_those_options_nothing_extra_is_emitted(self):
        html = render(lane())
        for marker in ("data-option-id", "data-lane-menu", "data-lane-total"):
            self.assertNotIn(marker, html, marker)

    def test_an_empty_total_keeps_the_line_so_the_lanes_align_and_none_removes_it(self):
        self.assertIn("data-lane-total>&nbsp;</p>", render(lane(total="")))
        self.assertNotIn("data-lane-total", render(lane(total=None)))

    def test_the_blank_state_may_come_from_another_partial(self):
        html = render_to_string("kanban/_lanes.html", {"kanban": {"lanes": [], "empty_template": "kanban/_fields.html"}})
        self.assertNotIn("kanban-state", html)

    def test_the_card_menu_does_not_depend_on_dragging(self):
        only_menu = render(lane(cards=[card(can_move=False, menu=True)]))
        self.assertIn("data-card-menu", only_menu)
        self.assertNotIn('draggable="true"', only_menu)
        only_drag = render(lane(cards=[card(can_move=True, menu=False)]))
        self.assertNotIn("data-card-menu", only_drag)
        self.assertIn('draggable="true"', only_drag)

    def test_the_title_edits_in_place_when_asked_and_a_link_can_still_exist_elsewhere(self):
        html = render(lane(cards=[card(title_editable=True, title_label="Obra")]))
        self.assertIn('<span class="kanban-card__title" data-card-title tabindex="0" role="textbox" aria-label="Obra">Orçamento Aurora</span>', html)
        self.assertNotIn('<a class="kanban-card__title"', html)  # o clique no título renomeia: ele não pode ser também um link
        empty = render(lane(cards=[card(title_editable=True, title="")]))
        self.assertIn('class="kanban-card__title is-empty" data-card-title tabindex="0" role="textbox"', empty)
        self.assertIn(">Sem título<", empty)

    def test_the_card_menu_label_can_be_set_by_the_host(self):
        self.assertIn('aria-label="Opções da tarefa Orçamento Aurora"', render(lane(), menu_label="Opções da tarefa"))
        self.assertIn('aria-label="Opções da demanda Orçamento Aurora"', render(lane()))  # sem o aviso do anfitrião: "Opções da <item_label>"

    def test_the_editable_title_label_defaults_to_the_item_label(self):
        self.assertIn('role="textbox" aria-label="demanda"', render(lane(cards=[card(title_editable=True)])))

    def test_extra_attributes_go_on_the_card(self):
        html = render(lane(cards=[card(attrs=[("data-activity-id", 7)])]))
        self.assertIn('data-updated-at="2026-10-03T10:00:00+00:00" data-activity-id="7" draggable="true">', html)

    def test_empty_scope_and_version_are_not_emitted(self):
        html = render(lane(cards=[card(scope="", updated_at="")]))
        self.assertNotIn("data-card-scope", html)
        self.assertNotIn("data-updated-at", html)

    def test_a_field_carries_the_hosts_editing_hooks(self):
        html = FieldTypeTests.fields_html(
            {"kind": "text", "label": "Obra", "text": "Arena", "editable": True, "css": "date",
             "attrs": [("data-cell", ""), ("data-item-id", 101), ("data-column-id", 14), ("data-type", "DATE"), ("data-value", "")]},
        )
        self.assertIn('<div class="kanban-field kanban-field--date">', html)
        self.assertIn('<dd class="kanban-field__value is-editable" data-cell="" data-item-id="101" data-column-id="14" data-type="DATE" data-value="" tabindex="0">', html)

    def test_a_field_that_is_not_editable_has_no_tabindex(self):
        html = FieldTypeTests.fields_html({"kind": "text", "label": "Obra", "text": "Arena"})
        self.assertIn('<dd class="kanban-field__value">', html)
        self.assertNotIn("tabindex", html)

    def test_a_field_can_reuse_another_partial_for_its_value(self):
        html = FieldTypeTests.fields_html({"kind": "template", "label": "Valor", "template": "boards/_cell.html", "cell": None, "column": SimpleNamespace(type="TEXT")})
        self.assertIn('<dd class="kanban-field__value">', html)


class QuadrosUsesTheKitTests(BoardTestCase):
    """Quadros e Demandas desenham o Kanban pela MESMA marcação (`templates/kanban/*`); Quadros só traduz os dados
    (`board_kanban`, em `boards/templatetags/lps_board.py`). Não existe mais uma cópia a comparar."""

    def kanban_page(self, user=None):
        self.login(user or self.admin)
        return self.client.get(reverse("board-view-detail", args=[self.kanban.pk]))

    def test_the_page_and_the_lanes_fragment_render_through_the_kit(self):
        response = self.kanban_page()
        for template in ("kanban/_lanes.html", "kanban/_lane.html", "kanban/_card.html", "kanban/_fields.html"):
            self.assertTemplateUsed(response, template)
        fragment = self.client.post(reverse("board-view-lanes", args=[self.kanban.pk]), data="{}", content_type="application/json")
        self.assertTemplateUsed(fragment, "kanban/_lane.html")
        self.assertTemplateUsed(fragment, "kanban/_card.html")

    def test_the_old_quadros_card_partial_is_gone(self):
        self.assertTemplateNotUsed(self.kanban_page(), "boards/_kanban_card.html")

    def test_quadros_features_come_through_the_same_markup(self):
        html = self.kanban_page().content.decode()
        self.assertIn(f'data-option-id="{self.novo.pk}"', html)                        # a etiqueta que a raia representa
        self.assertIn("data-lane-menu", html)                                         # ⋮ da raia para quem gere colunas
        self.assertIn('data-card-title tabindex="0" role="textbox"', html)             # o título edita no lugar
        self.assertIn("data-card-menu", html)
        self.assertIn('aria-label="Opções da tarefa ', html)                           # o texto de sempre de Quadros
        self.assertRegex(html, r'<dd class="kanban-field__value is-editable" data-cell="" data-item-id="\d+" data-column-id="\d+" data-type="[A-Z]+" data-value="[^"]*" tabindex="0">')

    def test_a_viewer_gets_the_same_cards_without_anything_editable(self):
        html = self.kanban_page(self.viewer).content.decode()
        for marker in ("data-lane-menu", "data-card-menu", 'draggable="true"', 'role="textbox"', "is-editable"):
            self.assertNotIn(marker, html, marker)
        self.assertIn("Arena Norte", html)

    def test_the_total_line_only_exists_when_the_view_sums_a_column(self):
        self.assertNotIn("data-lane-total", self.kanban_page().content.decode())
        ViewService.update(user=self.admin, view=self.kanban, settings={"sum_column": self.col["moeda"].pk})
        self.assertIn("data-lane-total", self.kanban_page().content.decode())
