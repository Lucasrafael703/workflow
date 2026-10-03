"""Filtros e busca da tela de Demandas: o MESMO recorte, qualquer que seja a tela que o desenha.

Estes testes substituem os do Kanban por setor antigo (`activities/test_kanban.py::FilterTests`), que descreviam uma
tela que não existe mais. A regra de negócio é a mesma e agora é testada na tela atual (`DemandWorkBoardView`, rota
`activity-list`). A classe-base roda com a flag `WORKSPACE_V2` desligada; a mesma bateria roda de novo com a flag
ligada (ver `WorkspaceOnFilterTests`, na fase do Workspace) para provar que o recorte não muda de tela para tela.
"""

import datetime

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserSector
from acessos import catalog
from core.models import ActivityStage, Client, Organization, Sector, Site, WorkflowStatus

from .filtering import normalize_workspace_filters
from .models import Activity, Task
from .testing import make_user

VIEW_ALL = [catalog.ATIVIDADE_VISUALIZAR, catalog.ATIVIDADE_VISUALIZAR_TODAS]


class DemandFilterBase(TestCase):
    """Dados montados uma vez; cada teste roda numa transação desfeita. `flag` escolhe a tela (off = a de sempre)."""

    flag = "off"

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Biasi")
        cls.other_org = Organization.objects.create(name="Outra")
        cls.orcamento = Sector.objects.create(organization=cls.org, name="Orçamento")
        cls.financeiro = Sector.objects.create(organization=cls.org, name="Financeiro")

        cls.ana = make_user("ana", cls.org, VIEW_ALL)  # quem navega; responsável por "Orçamento Aurora"
        cls.gestor = make_user("gestor", cls.org, VIEW_ALL)
        cls.bia = make_user("bia", cls.org, VIEW_ALL)
        cls.visitante = make_user("visitante", cls.org, VIEW_ALL)
        cls.alheio = make_user("alheio", cls.other_org, VIEW_ALL)
        cls.restrito = make_user("restrito", cls.org, [catalog.ATIVIDADE_VISUALIZAR])  # vê só o que é dele
        cls.mover = make_user("mover", cls.org, VIEW_ALL + [catalog.ATIVIDADE_MOVER_ESTAGIO])
        cls.leitor = make_user("leitor", cls.org, VIEW_ALL)  # vê tudo, não move nada
        for user, sector in (
            (cls.ana, cls.orcamento), (cls.gestor, cls.orcamento), (cls.bia, cls.financeiro),
            (cls.mover, cls.orcamento), (cls.leitor, cls.orcamento),
        ):
            UserSector.objects.create(user=user, sector=sector)

        cls.afazer = ActivityStage.objects.create(organization=cls.org, sector=cls.orcamento, name="A fazer", order=1, is_default=True)
        cls.levantamento = ActivityStage.objects.create(organization=cls.org, sector=cls.orcamento, name="Levantamento", order=2)
        cls.f_afazer = ActivityStage.objects.create(organization=cls.org, sector=cls.financeiro, name="A fazer", order=1, is_default=True)
        cls.normal = cls._condition(cls.orcamento, "Normal", 1, default=True)
        cls.aguardando = cls._condition(cls.orcamento, "Aguardando cliente", 2)
        cls.f_normal = cls._condition(cls.financeiro, "Normal", 1, default=True)

        cls.convivy = Client.objects.create(organization=cls.org, name="Convivy")
        cls.aurora = Site.objects.create(organization=cls.org, name="Residencial Aurora", client=cls.convivy)

        cls.a1 = cls._activity("Orçamento Aurora", cls.ana, cls.orcamento, cls.afazer, cls.normal, client=cls.convivy, site=cls.aurora)
        cls.a2 = cls._activity("Levantamento da garagem", cls.gestor, cls.orcamento, cls.levantamento, cls.aguardando)
        cls.a3 = cls._activity("Pagamento fornecedor", cls.bia, cls.financeiro, cls.f_afazer, cls.f_normal)
        cls.a4 = cls._activity("Item do visitante", cls.visitante, cls.orcamento, cls.afazer, cls.normal)
        cls.a_done = cls._activity("Já concluída", cls.ana, cls.orcamento, cls.afazer, cls.normal, status=Activity.Status.CONCLUIDA)
        cls.a_draft = cls._activity("Rascunho", cls.ana, cls.orcamento, None, None, status=Activity.Status.RASCUNHO)
        cls.a_foreign = Activity.objects.create(organization=cls.other_org, title="Alheia", owner=cls.alheio, created_by=cls.alheio)
        cls.a_restrito = cls._activity("Do restrito", cls.restrito, cls.orcamento, cls.afazer, cls.normal)

    @classmethod
    def _condition(cls, sector, name, order, default=False):
        return WorkflowStatus.objects.create(
            organization=cls.org, sector=sector, domain=WorkflowStatus.Domain.ACTIVITY, name=name, order=order,
            is_default=default, color="#3B82F6",
        )

    @classmethod
    def _activity(cls, title, owner, sector, stage, condition, status=Activity.Status.ABERTA, **extra):
        return Activity.objects.create(
            organization=cls.org, title=title, owner=owner, created_by=owner, sector=sector, stage=stage,
            condition=condition, status=status, **extra,
        )

    def setUp(self):
        self.client.force_login(self.ana)

    def get(self, **params):
        params.setdefault("tab", "todas")
        with override_settings(WORKSPACE_V2=self.flag):
            response = self.client.get(reverse("activity-list"), params)
        self.assertEqual(response.status_code, 200, params)
        return response

    def titles(self, **params):
        """Títulos do UNIVERSO filtrado (a mesma lista que Lista, Kanban e Calendário projetam), em ordem."""
        return [item.title for item in self.get(**params).context["activities"]]


class DemandFilterTests(DemandFilterBase):
    def test_scopes_and_defaults(self):
        # "Minhas": o que é meu e está aberto, mais o MEU rascunho (para poder retomá-lo); a concluída fica fora.
        self.assertEqual(sorted(self.titles(tab="minhas")), ["Orçamento Aurora", "Rascunho"])
        self.assertEqual(
            sorted(self.titles()),
            ["Do restrito", "Item do visitante", "Levantamento da garagem", "Orçamento Aurora", "Pagamento fornecedor"],
        )  # "Todas": abertas de toda a organização, nunca rascunho nem de outra organização

    def test_finished_ones_only_show_when_asked(self):
        self.assertNotIn("Já concluída", self.titles(tab="minhas"))
        self.assertEqual(self.titles(tab="minhas", concluidas="1"), ["Já concluída"])
        self.assertNotIn("Já concluída", self.titles())

    def test_search_matches_title_client_site_and_the_old_code(self):
        for term in ("Aurora", "Convivy", "Residencial", self.a1.code.replace("DEM-", "ATV-")):
            with self.subTest(term=term):
                self.assertEqual(self.titles(q=term), ["Orçamento Aurora"])

    def test_person_filter(self):
        self.assertEqual(self.titles(pessoa="eu"), ["Orçamento Aurora"])
        self.assertEqual(self.titles(pessoa=self.gestor.pk), ["Levantamento da garagem"])
        self.assertEqual(sorted(self.titles(pessoa=[self.gestor.pk, self.bia.pk])), ["Levantamento da garagem", "Pagamento fornecedor"])

    def test_old_responsavel_parameter_still_works(self):
        self.assertEqual(self.titles(responsavel=self.gestor.pk), ["Levantamento da garagem"])

    def test_sector_stage_and_condition_filters(self):
        self.assertEqual(self.titles(setor=self.financeiro.pk), ["Pagamento fornecedor"])
        self.assertEqual(self.titles(estagio=self.levantamento.pk), ["Levantamento da garagem"])
        self.assertEqual(self.titles(condicao=self.aguardando.pk), ["Levantamento da garagem"])

    def test_client_and_site_filters(self):
        self.assertEqual(self.titles(cliente=self.convivy.pk), ["Orçamento Aurora"])
        self.assertEqual(self.titles(obra=self.aurora.pk), ["Orçamento Aurora"])

    def test_deadline_filters(self):
        now = timezone.now()
        Activity.objects.filter(pk=self.a1.pk).update(requested_deadline=now - datetime.timedelta(days=2))
        Activity.objects.filter(pk=self.a2.pk).update(requested_deadline=now + datetime.timedelta(days=3))
        self.assertEqual(self.titles(prazo="atrasadas"), ["Orçamento Aurora"])
        self.assertEqual(self.titles(prazo="7_dias"), ["Levantamento da garagem"])
        self.assertEqual(sorted(self.titles(prazo="sem_prazo")), ["Do restrito", "Item do visitante", "Pagamento fornecedor"])

    def test_blocked_filter_uses_the_operational_status(self):
        Activity.objects.filter(pk=self.a2.pk).update(status=Activity.Status.BLOQUEADA)
        self.assertEqual(self.titles(bloqueio="1"), ["Levantamento da garagem"])

    def test_invalid_values_are_ignored_not_a_server_error(self):
        everything = sorted(self.titles())
        response = self.get(
            pessoa="abc", condicao="x", cliente="; drop", obra="1 OR 1=1", estagio="--", setor="zz", prazo="nunca", ordem="zzz", dir="up",
        )
        self.assertEqual(sorted(item.title for item in response.context["activities"]), everything)

    def test_another_organization_is_never_listed(self):
        for params in ({}, {"q": "Alheia"}, {"tab": "minhas"}):
            self.assertNotIn("Alheia", self.titles(**params), params)

    def test_the_same_query_answers_the_three_views(self):
        """Lista, Kanban e Calendário mostram o mesmo UNIVERSO filtrado (cada uma o projeta de seu jeito)."""
        params = {"tab": "todas", "setor": self.orcamento.pk, "q": "o"}
        universes = []
        for name in ("activity-list", "activity-kanban", "activity-calendar"):
            with override_settings(WORKSPACE_V2=self.flag):
                response = self.client.get(reverse(name), params)
            self.assertEqual(response.status_code, 200, name)
            universes.append(sorted(item.pk for item in response.context["activities"]))
        self.assertEqual(universes[0], universes[1])
        self.assertEqual(universes[0], universes[2])
        self.assertTrue(universes[0])


class DemandScopeTests(DemandFilterBase):
    """Quem enxerga o quê (regras que o Kanban por setor antigo já garantia): escopo, vazamento entre setores, rascunhos."""

    def as_user(self, user, **params):
        self.client.force_login(user)
        return self.titles(**params)

    def test_my_sector_scope_lists_the_demands_of_the_sectors_I_belong_to(self):
        self.assertEqual(sorted(self.as_user(self.ana, tab="grupo")), ["Do restrito", "Item do visitante", "Levantamento da garagem", "Orçamento Aurora"])
        self.assertEqual(self.as_user(self.bia, tab="grupo"), ["Pagamento fornecedor"])

    def test_someone_outside_every_sector_sees_nothing_in_the_sector_scope(self):
        self.assertEqual(self.as_user(self.visitante, tab="grupo"), [])

    def test_participating_in_a_task_makes_the_demand_visible_in_the_participating_scope(self):
        self.assertNotIn("Orçamento Aurora", self.as_user(self.visitante, tab="participando"))
        Task.objects.create(
            activity=self.a1, title="Levantar quantitativos", responsavel=self.visitante, created_by=self.ana,
            sector=self.orcamento, status=Task.Status.EM_FILA,
        )
        self.assertEqual(self.as_user(self.visitante, tab="participando"), ["Orçamento Aurora"])
        self.assertNotIn("Item do visitante", self.as_user(self.visitante, tab="participando"))  # a minha própria não é "participando"

    def test_the_all_scope_without_the_permission_shows_only_my_own_and_never_leaks_a_sector(self):
        self.assertEqual(self.as_user(self.restrito, tab="todas"), ["Do restrito"])
        for other in (self.financeiro, self.orcamento):
            self.assertEqual(self.as_user(self.restrito, tab="todas", setor=other.pk).count("Pagamento fornecedor"), 0)
        self.assertEqual(self.as_user(self.restrito, tab="todas", setor=self.financeiro.pk), [])

    def test_the_old_sector_names_still_select_the_sector(self):
        self.client.force_login(self.ana)
        for name in ("grupo", "sector", "setor"):
            with self.subTest(parameter=name):
                self.assertEqual(self.titles(**{name: self.financeiro.pk}), ["Pagamento fornecedor"])

    def test_drafts_never_show_up_in_the_all_scope_even_with_finished_ones(self):
        self.assertNotIn("Rascunho", self.titles(concluidas="1"))
        self.assertNotIn("Rascunho", self.titles())

    def test_the_kanban_never_loses_a_demand_when_its_stage_stops_being_active(self):
        before = sorted(self.titles())
        ActivityStage.objects.filter(pk=self.levantamento.pk).update(is_active=False)
        with override_settings(WORKSPACE_V2=self.flag):
            response = self.client.get(reverse("activity-kanban"), {"tab": "todas"})
        listed = sorted(item.title for group in response.context["groups"] for item in group["items"])
        self.assertEqual(listed, before)  # a etapa antiga ganha a sua raia ao fim; nada some

    def test_a_card_is_draggable_only_for_who_can_move_it(self):
        for user, draggable in ((self.mover, True), (self.leitor, False)):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                with override_settings(WORKSPACE_V2=self.flag):
                    response = self.client.get(reverse("activity-kanban"), {"tab": "todas"})
                self.assertEqual('draggable="true"' in response.content.decode(), draggable)

    def test_a_custom_status_shows_its_label_and_color_in_the_list(self):
        status = WorkflowStatus.objects.create(
            organization=self.org, sector=self.orcamento, domain=WorkflowStatus.Domain.ACTIVITY, name="Em análise",
            order=9, color="#8B5CF6",
        )
        Activity.objects.filter(pk=self.a1.pk).update(condition=status)
        html = self.get().content.decode()
        self.assertIn("Em análise", html)
        self.assertIn("#8B5CF6", html.upper())


class FilterNormalizationTests(SimpleTestCase):
    """O normalizador compartilhado nunca deixa um valor inválido chegar ao banco (era erro 500)."""

    def normalize(self, query):
        return normalize_workspace_filters(RequestFactory().get("/demandas/", query))

    def test_only_digits_are_accepted_as_ids(self):
        state = self.normalize({"cliente": "abc", "obra": "1 OR 1=1", "estagio": "--", "condicao": "x", "setor": "zz", "tag": "'"})
        for key in ("cliente", "obra", "estagio", "condicao", "setor", "tag"):
            self.assertEqual(state[key], "", key)
        self.assertEqual(state["invalid"], ["setor", "status", "etapa", "cliente", "obra", "marcador"])

    def test_valid_ids_pass_through_untouched(self):
        state = self.normalize({"cliente": "12", "obra": "3", "estagio": "4", "condicao": "5", "setor": "6", "tag": "7"})
        self.assertEqual([state[key] for key in ("cliente", "obra", "estagio", "condicao", "setor", "tag")], ["12", "3", "4", "5", "6", "7"])
        self.assertEqual(state["invalid"], [])

    def test_the_old_sector_names_are_checked_too(self):
        self.assertEqual(self.normalize({"sector": "x"})["invalid"], ["setor"])
        self.assertEqual(self.normalize({"grupo": "9"})["setor"], "9")

    def test_an_unknown_deadline_is_ignored_and_reported(self):
        state = self.normalize({"prazo": "nunca"})
        self.assertEqual((state["prazo"], state["invalid"]), ("", ["prazo"]))
        self.assertEqual(self.normalize({"prazo": "hoje"})["prazo"], "hoje")

    def test_unicode_digits_are_not_ids(self):
        self.assertEqual(self.normalize({"cliente": "١٢"})["cliente"], "")  # dígitos árabe-índicos
