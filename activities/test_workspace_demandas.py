"""Workspace de Demandas (flag `WORKSPACE_V2`): um shell, três visualizações, o mesmo recorte.

O que este arquivo prova: com a flag desligada nada muda; ligada, `/demandas/`, `/demandas/kanban/` e
`/demandas/calendario/` mostram o MESMO cabeçalho, as MESMAS abas e a MESMA barra, e trocar de visão preserva o
recorte (busca, filtros, escopo, agrupar, ordenar, mês). Só a área de conteúdo muda.
"""

import datetime
from urllib.parse import parse_qs, quote, urlsplit

from django.db import connection
from django.http import QueryDict
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from acessos.testing import grant_actions

from .models import Activity
from .test_demand_filters import DemandFilterBase

VIEWS = ("activity-list", "activity-kanban", "activity-calendar")
STATE = {"tab": "todas", "q": "o", "setor": None, "ordem": "titulo", "dir": "desc", "agrupar": "condition", "concluidas": "1"}


class WorkspaceBase(DemandFilterBase):
    flag = "on"

    def page(self, name="activity-list", user=None, **params):
        if user is not None:
            self.client.force_login(user)
        params.setdefault("tab", "todas")
        with override_settings(WORKSPACE_V2=self.flag):
            response = self.client.get(reverse(name), params)
        self.assertEqual(response.status_code, 200, (name, params))
        return response

    @staticmethod
    def query(url):
        return {key: sorted(values) for key, values in parse_qs(urlsplit(url).query).items()}


class FlagTests(WorkspaceBase):
    def test_off_nobody_sees_the_workspace(self):
        with override_settings(WORKSPACE_V2="off"):
            response = self.client.get(reverse("activity-list"), {"tab": "todas"})
        self.assertTemplateUsed(response, "boards/demand_work_board.html")
        self.assertTemplateNotUsed(response, "workspace/demandas.html")
        self.assertNotContains(response, "data-ws")

    def test_on_everybody_sees_the_workspace_on_the_three_addresses(self):
        for name in VIEWS:
            response = self.page(name)
            self.assertTemplateUsed(response, "workspace/demandas.html")
            self.assertContains(response, "data-ws-view=")

    @override_settings(WORKSPACE_V2="allowlist", WORKSPACE_V2_USERS=["ana"])
    def test_allowlist_only_for_the_listed_people(self):
        self.client.force_login(self.ana)
        listed = self.client.get(reverse("activity-list"), {"tab": "todas"})
        self.client.force_login(self.gestor)
        other = self.client.get(reverse("activity-list"), {"tab": "todas"})
        self.assertTemplateUsed(listed, "workspace/demandas.html")
        self.assertTemplateUsed(other, "boards/demand_work_board.html")

    def test_the_old_screen_keeps_its_group_by_setting_and_ignores_the_new_parameters(self):
        with override_settings(WORKSPACE_V2="off"):
            response = self.client.get(reverse("activity-kanban"), {"tab": "todas", "agrupar": "sector"})
        self.assertEqual(response.context["group_by"], "stage")


class SameShellTests(WorkspaceBase):
    """Cabeçalho, abas e barra são os mesmos nas três visões; só o conteúdo muda."""

    def setUp(self):
        super().setUp()
        grant_actions(self.ana, [catalog.ATIVIDADE_CRIAR], organization=self.org)

    def test_header_tabs_and_core_controls_are_on_every_view(self):
        for name in VIEWS:
            with self.subTest(view=name):
                response = self.page(name)
                html = response.content.decode()
                self.assertContains(response, "Demandas</h1>")
                self.assertContains(response, "Criar demanda")
                self.assertEqual([tab["label"] for tab in response.context["ws"]["tabs"]], ["Lista", "Kanban", "Calendário"])
                for control in ("Escopo", "Mostrar", "Buscar demanda", "Filtros"):
                    self.assertIn(control, html, control)
                self.assertEqual(html.count('data-ws-panel-toggle'), 1)

    def test_the_count_is_the_filtered_universe_and_is_equal_in_every_view(self):
        counts = {name: self.page(name).context["ws"]["count"] for name in VIEWS}
        self.assertEqual(len(set(counts.values())), 1, counts)
        self.assertEqual(counts["activity-list"], len(self.page().context["activities"]))

    def test_group_and_sort_are_contextual_and_never_disabled(self):
        lista, kanban, calendario = (self.page(name) for name in VIEWS)
        for response in (lista, kanban):
            self.assertIsNotNone(response.context["ws"]["group"])
            self.assertIsNotNone(response.context["ws"]["sort"])
        self.assertIsNone(calendario.context["ws"]["group"])
        self.assertIsNone(calendario.context["ws"]["sort"])
        for response in (lista, kanban, calendario):
            shell = response.content.decode().split('<section class="ws ', 1)[1].split("</section>", 1)[0]
            self.assertNotIn("disabled", shell)  # nada de controle desabilitado só para a barra "parecer igual"

    def test_personalize_exists_only_in_the_kanban_for_who_can_configure(self):
        grant_actions(self.ana, [catalog.QUADRO_GERIR_COLUNAS], organization=self.org)
        self.client.force_login(self.ana)
        self.assertContains(self.page("activity-kanban"), "data-work-card-settings")
        self.assertNotContains(self.page("activity-list"), "data-work-card-settings")
        self.assertNotContains(self.page("activity-calendar"), "data-work-card-settings")
        self.client.force_login(self.leitor)
        self.assertNotContains(self.page("activity-kanban"), "data-work-card-settings")

    def test_each_view_only_changes_the_content_area(self):
        lista, kanban, calendario = (self.page(name).content.decode() for name in VIEWS)
        self.assertIn("data-activity-list", lista)
        self.assertNotIn("data-kanban-lanes", lista)
        self.assertIn("data-kanban-lanes", kanban)
        self.assertNotIn("data-activity-list", kanban)
        self.assertIn("demand-board__calendar", calendario)

    def test_the_top_bar_says_the_same_in_every_view(self):
        for name in VIEWS:
            with self.subTest(view=name):
                html = self.page(name).content.decode()
                location = html.split('class="workspace-location">')[1].split("</span>")[0].strip()
                self.assertEqual(location, "Demandas")


class StatePreservedTests(WorkspaceBase):
    def test_every_tab_carries_the_whole_state_except_the_page(self):
        params = {**STATE, "setor": self.orcamento.pk, "pessoa": [self.gestor.pk, self.bia.pk], "page": "3", "view": "9", "visao": "9"}
        response = self.page("activity-kanban", **{key: value for key, value in params.items() if value is not None})
        for tab in response.context["ws"]["tabs"]:
            state = self.query(tab["url"])
            for gone in ("page", "view", "visao"):
                self.assertNotIn(gone, state, (tab["label"], gone))
            self.assertEqual(state["tab"], ["todas"])
            self.assertEqual(state["setor"], [str(self.orcamento.pk)])
            self.assertEqual(state["pessoa"], sorted([str(self.gestor.pk), str(self.bia.pk)]))
            self.assertEqual((state["q"], state["ordem"], state["dir"], state["agrupar"]), (["o"], ["titulo"], ["desc"], ["condition"]))

    def test_the_old_aliases_become_the_canonical_name_when_a_control_rewrites_them(self):
        response = self.page(grupo=self.financeiro.pk, responsavel=self.bia.pk)
        options = response.context["ws"]["scope"]["options"] + response.context["ws"]["show"]["options"]
        for option in options:
            state = self.query(option["url"])
            self.assertNotIn("grupo", state)  # os apelidos antigos não vão para o link novo
            self.assertNotIn("sector", state)

    def test_forms_forward_the_rest_of_the_state_without_duplicating_their_own_fields(self):
        response = self.page(q="Aurora", setor=self.orcamento.pk, ordem="titulo", agrupar="stage")
        ws = response.context["ws"]
        search_hidden = dict(ws["search"]["hidden"])
        panel_hidden = dict(ws["panel"]["hidden"])
        self.assertNotIn("q", search_hidden)
        self.assertEqual(search_hidden["setor"], str(self.orcamento.pk))
        self.assertEqual((search_hidden["ordem"], search_hidden["agrupar"], search_hidden["tab"]), ("titulo", "stage", "todas"))
        self.assertEqual(panel_hidden["q"], "Aurora")
        for own in ("setor", "pessoa", "estagio", "condicao", "cliente", "obra", "prazo"):
            self.assertNotIn(own, panel_hidden)
        self.assertEqual((panel_hidden["ordem"], panel_hidden["agrupar"], panel_hidden["tab"]), ("titulo", "stage", "todas"))

    def test_opening_a_demand_and_coming_back_returns_to_the_same_address(self):
        response = self.page(setor=self.orcamento.pk, q="o", ordem="titulo")
        full_path = response.wsgi_request.get_full_path()
        html = response.content.decode()
        self.assertIn("?next=" + quote(full_path, safe="/"), html)  # o link da ficha leva o endereço COMPLETO de volta

    def test_the_month_of_the_calendar_survives_a_tab_switch(self):
        response = self.page("activity-calendar", mes="2026-10")
        for tab in response.context["ws"]["tabs"]:
            self.assertEqual(self.query(tab["url"]).get("mes"), ["2026-10"], tab["label"])


class ScopeAndShowTests(WorkspaceBase):
    def active(self, response, group):
        return [option["key"] for option in response.context["ws"][group]["options"] if option["active"]]

    def test_scope_and_show_are_two_separate_controls(self):
        response = self.page(tab="minhas")
        self.assertEqual(self.active(response, "scope"), ["minhas"])
        self.assertEqual(self.active(response, "show"), ["abertas"])
        done = self.page(tab="minhas", concluidas="1")
        self.assertEqual((self.active(done, "scope"), self.active(done, "show")), (["minhas"], ["concluidas"]))

    def test_the_old_finished_tab_is_read_as_minhas_plus_concluidas(self):
        response = self.page(tab="concluidas")
        self.assertEqual((self.active(response, "scope"), self.active(response, "show")), (["minhas"], ["concluidas"]))
        keep = {option["key"]: self.query(option["url"]) for option in response.context["ws"]["scope"]["options"]}
        self.assertEqual(keep["grupo"]["tab"], ["grupo"])
        self.assertEqual(keep["grupo"]["concluidas"], ["1"])  # trocar o escopo não perde o "Concluídas"
        back = {option["key"]: self.query(option["url"]) for option in response.context["ws"]["show"]["options"]}
        self.assertNotIn("tab", back["abertas"])  # "Em aberto" sai do link antigo

    def test_everyone_sees_todas_only_with_the_permission(self):
        self.assertIn("todas", [o["key"] for o in self.page(user=self.ana).context["ws"]["scope"]["options"]])
        self.assertNotIn("todas", [o["key"] for o in self.page(user=self.restrito, tab="minhas").context["ws"]["scope"]["options"]])

    def test_choosing_someone_else_never_changes_the_scope_by_itself(self):
        response = self.page(tab="minhas", pessoa=self.gestor.pk)
        self.assertEqual(self.active(response, "scope"), ["minhas"])
        notices = response.context["ws"]["notices"]
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]["kind"], "warning")
        self.assertIn("Você está vendo só “Minhas”", notices[0]["text"])
        self.assertEqual(self.query(notices[0]["action"]["url"])["tab"], ["todas"])  # a escolha é do usuário: um botão

    def test_the_warning_has_no_action_for_who_cannot_see_everything(self):
        self.client.force_login(self.restrito)
        response = self.page(tab="minhas", pessoa=self.gestor.pk)
        self.assertIsNone(response.context["ws"]["notices"][0]["action"])

    def test_no_warning_when_the_person_is_me_or_the_scope_is_wider(self):
        self.assertEqual(self.page(tab="minhas", pessoa="eu").context["ws"]["notices"], [])
        self.assertEqual(self.page(tab="minhas", pessoa=self.ana.pk).context["ws"]["notices"], [])
        self.assertEqual(self.page(tab="todas", pessoa=self.gestor.pk).context["ws"]["notices"], [])

    def test_an_invalid_filter_is_ignored_with_a_visible_notice_never_an_error(self):
        response = self.page(cliente="abc", setor="x")
        self.assertEqual(sorted(item.title for item in response.context["activities"]), sorted(self.titles()))
        texts = [notice["text"] for notice in response.context["ws"]["notices"]]
        self.assertTrue(any("Ignoramos o filtro inválido" in text and "cliente" in text and "setor" in text for text in texts), texts)
        self.assertContains(response, "Ignoramos o filtro inválido")


class FilterPanelTests(WorkspaceBase):
    def test_active_filters_show_as_chips_each_removable_in_one_click(self):
        response = self.page(q="Aurora", setor=self.orcamento.pk, cliente=self.convivy.pk, obra=self.aurora.pk, prazo="atrasadas")
        chips = {chip["label"]: chip for chip in response.context["ws"]["chips"]}
        self.assertEqual(set(chips), {"Busca", "Setor", "Cliente", "Obra", "Prazo"})
        self.assertEqual(chips["Cliente"]["value"], "Convivy")
        self.assertEqual(chips["Obra"]["value"], "Residencial Aurora")
        removed = self.query(chips["Setor"]["url"])
        self.assertNotIn("setor", removed)
        self.assertEqual(removed["q"], ["Aurora"])  # tirar um chip não perde os outros
        self.assertEqual(removed["cliente"], [str(self.convivy.pk)])

    def test_the_panel_opens_by_itself_only_when_a_secondary_filter_is_active(self):
        self.assertFalse(self.page().context["ws"]["panel"]["open"])
        self.assertFalse(self.page(q="Aurora").context["ws"]["panel"]["open"])  # só a busca: o painel não abre
        self.assertTrue(self.page(setor=self.orcamento.pk).context["ws"]["panel"]["open"])

    def test_clear_filters_keeps_the_view_scope_and_ordering_but_drops_every_filter(self):
        response = self.page("activity-kanban", q="o", setor=self.orcamento.pk, cliente=self.convivy.pk, ordem="titulo", agrupar="stage", mes="2026-10")
        state = self.query(response.context["ws"]["clear_url"])
        self.assertEqual(state, {"tab": ["todas"], "ordem": ["titulo"], "agrupar": ["stage"], "mes": ["2026-10"]})
        self.assertTrue(urlsplit(response.context["ws"]["clear_url"]).path.endswith("/demandas/kanban/"))

    def test_the_client_and_site_pickers_are_prefilled_and_site_depends_on_client(self):
        response = self.page(cliente=self.convivy.pk, obra=self.aurora.pk)
        self.assertContains(response, 'data-filter-field="ws-filter-cliente"')
        self.assertContains(response, 'data-filter-param="client"')
        self.assertContains(response, 'value="%d"' % self.convivy.pk)
        self.assertContains(response, "Residencial Aurora")

    def test_stage_and_status_options_come_with_their_sector_so_the_panel_can_filter_them(self):
        panel = self.page().context["ws"]["panel"]
        self.assertEqual({group["sector_name"] for group in panel["stage_groups"]}, {"Orçamento", "Financeiro"})
        self.assertTrue(all(group["sector_id"] for group in panel["stage_groups"]))

    def test_filter_options_do_not_load_every_client_and_site_up_front(self):
        for index in range(25):
            from core.models import Client

            Client.objects.create(organization=self.org, name=f"Cliente {index}")
        html = self.page().content.decode()
        self.assertNotIn("Cliente 7", html)  # o seletor busca sob demanda: não despeja a base inteira na página


class ViewContentTests(WorkspaceBase):
    def test_the_list_is_flat_by_default_and_in_sections_with_agrupar(self):
        flat = self.page()
        self.assertIsNone(flat.context["ws"]["list_groups"])
        self.assertNotContains(flat, "ws-group__head")
        grouped = self.page(agrupar="stage")
        groups = grouped.context["ws"]["list_groups"]
        self.assertTrue(groups)
        self.assertEqual(sorted(item.pk for group in groups for item in group["items"]), sorted(item.pk for item in grouped.context["activities"]))
        self.assertTrue(all(group["items"] for group in groups))  # seção vazia não aparece na lista
        self.assertContains(grouped, "ws-group__head")

    def test_agrupar_sets_the_kanban_lanes_and_an_invalid_value_falls_back_to_the_saved_default(self):
        by_status = self.page("activity-kanban", agrupar="condition")
        self.assertEqual(by_status.context["group_by"], "condition")
        self.assertEqual(self.page("activity-kanban", agrupar="zzz").context["group_by"], "stage")
        self.assertEqual(self.page("activity-kanban").context["group_by"], "stage")

    def test_the_list_has_six_information_columns_plus_the_open_action(self):
        html = self.page().content.decode()
        head = html.split("<thead>")[1].split("</thead>")[0]
        for label in ("Demanda", "Setor", "Responsável", "Prazo", "Etapa", "Status"):
            self.assertIn(f"<th>{label}</th>", head)
        self.assertNotIn("<th>Cliente / Obra</th>", head)
        self.assertNotIn("<th>Tarefas</th>", head)

    def test_the_row_keeps_the_inline_edit_contract(self):
        grant_actions(
            self.ana,
            [catalog.ATIVIDADE_EDITAR, catalog.ATIVIDADE_ALTERAR_DONO, catalog.ATIVIDADE_DEFINIR_ETAPA, catalog.ATIVIDADE_DEFINIR_CONDICAO],
            organization=self.org,
        )
        html = self.page(user=self.ana, tab="minhas").content.decode()
        for marker in ('data-activity-id="', 'data-inline-field="title"', 'data-inline-field="owner"', 'data-inline-field="requested_deadline"',
                       'data-inline-field="stage"', 'data-inline-field="condition"', 'data-inline-field="sector"', "data-activity-list", "data-inline-url="):
            self.assertIn(marker, html, marker)
        self.assertIn("passo=2", html)  # Cliente · Obra continua abrindo a edição no passo 2

    def test_the_row_shows_the_client_site_and_task_progress(self):
        html = self.page(q="Aurora").content.decode()
        self.assertIn("Convivy", html)
        self.assertIn("Residencial Aurora", html)
        self.assertIn("0/0 tarefas", html)

    def test_empty_states_tell_nothing_registered_from_nothing_found(self):
        found = self.page(q="zzz-nada")
        self.assertContains(found, "Nenhuma demanda com esses filtros")
        self.assertContains(found, "Limpar filtros")
        Activity.objects.filter(organization=self.org).delete()
        self.assertContains(self.page(), "Nenhuma demanda ainda")

    def test_a_demand_without_permission_to_create_hides_the_create_button(self):
        self.client.force_login(self.restrito)
        self.assertNotContains(self.page(tab="minhas"), "Criar demanda")


class OrderingTests(WorkspaceBase):
    """Migrados do Kanban por setor antigo: ordenar por título e por prazo, com o vazio sempre no fim."""

    def ordered(self, **params):
        return [item.title for item in self.page(**params).context["activities"]]

    def test_ordering_by_title_in_both_directions(self):
        asc = self.ordered(ordem="titulo", dir="asc")
        desc = self.ordered(ordem="titulo", dir="desc")
        self.assertEqual(asc, sorted(asc))
        self.assertEqual(desc, list(reversed(asc)))

    def test_deadline_ordering_puts_the_empty_deadline_last_in_both_directions(self):
        now = timezone.now()
        Activity.objects.filter(pk=self.a4.pk).update(requested_deadline=now + datetime.timedelta(days=9))
        Activity.objects.filter(pk=self.a1.pk).update(requested_deadline=now + datetime.timedelta(days=1))
        asc = self.ordered(ordem="prazo", dir="asc")
        desc = self.ordered(ordem="prazo", dir="desc")
        self.assertEqual(asc[:2], ["Orçamento Aurora", "Item do visitante"])
        self.assertEqual(desc[:2], ["Item do visitante", "Orçamento Aurora"])
        self.assertEqual(set(asc[2:]), set(desc[2:]))  # os sem prazo, sempre depois dos que têm
        self.assertEqual(len(asc), len(desc))

    def test_recent_ordering_and_an_unknown_value_fall_back_safely(self):
        self.assertEqual(len(self.ordered(ordem="recentes")), len(self.ordered()))
        self.assertEqual(self.ordered(ordem="zzz", dir="up"), self.ordered())

    def test_the_sort_control_offers_both_directions_of_each_order(self):
        labels = [option["label"] for option in self.page().context["ws"]["sort"]["options"]]
        self.assertEqual(labels, ["Prazo: mais próximo primeiro", "Prazo: mais distante primeiro", "Mais recentes", "Mais antigas", "Demanda (A–Z)", "Demanda (Z–A)"])
        active = [option["label"] for option in self.page(ordem="titulo", dir="desc").context["ws"]["sort"]["options"] if option["active"]]
        self.assertEqual(active, ["Demanda (Z–A)"])


class QueryCountTests(WorkspaceBase):
    def count(self, name):
        self.page(name)  # a primeira visita cria o quadro padrão e semeia coisas
        with CaptureQueriesContext(connection) as context:
            self.page(name)
        return len(context)

    def test_the_number_of_queries_does_not_grow_with_the_number_of_demands(self):
        before = {name: self.count(name) for name in VIEWS}
        for index in range(12):
            self._activity(f"Extra {index}", self.ana, self.orcamento, self.afazer, self.normal)
        after = {name: self.count(name) for name in VIEWS}
        for name in VIEWS:
            self.assertLessEqual(after[name], before[name] + 1, (name, before[name], after[name]))
