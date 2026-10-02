"""Quadro Kanban de Demandas e de Tarefas: sempre de um setor, com as Etapas e Condições desse setor.

Cobre: setor obrigatório e visibilidade, colunas (inclusive "Sem etapa" e o limite), filtros e ordenação, o que o
arraste e os seletores gravam (só etapa / só condição, nunca o status operacional), criação na coluna, limite,
criação de opções, gaveta da demanda e da tarefa, isolamento entre organizações e consultas por cartão.
"""

import datetime

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse
from django.utils import timezone

from accounts.models import UserSector
from acessos import catalog
from acessos.testing import grant_actions
from audit.models import AuditLog
from core.models import ActivityStage, Client, Organization, Sector, Site, TaskStage, WorkflowStatus

from .models import Activity, Task
from .testing import make_user

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

WORK_ACTIONS = [
    catalog.ATIVIDADE_DEFINIR_ETAPA,
    catalog.ATIVIDADE_DEFINIR_CONDICAO,
    catalog.TAREFA_DEFINIR_ETAPA,
    catalog.TAREFA_DEFINIR_CONDICAO,
    catalog.ATIVIDADE_CRIAR,
    catalog.ATIVIDADE_EDITAR,
    catalog.ATIVIDADE_CANCELAR,
    catalog.COMUNICACAO_PARTICIPAR,
]
MANAGER_ACTIONS = WORK_ACTIONS + [catalog.ETAPA_GERIR, catalog.CONDICAO_GERIR]


class KanbanTestCase(TestCase):
    """Dados montados uma vez por classe (`setUpTestData`); cada teste roda numa transação que é desfeita."""

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Biasi")
        cls.other_org = Organization.objects.create(name="Outra")
        cls.orcamento = Sector.objects.create(organization=cls.org, name="Orçamento")
        cls.financeiro = Sector.objects.create(organization=cls.org, name="Financeiro")
        cls.foreign_sector = Sector.objects.create(organization=cls.other_org, name="Alheio")

        cls.ana = make_user("ana", cls.org, WORK_ACTIONS)  # membro de Orçamento, pode mexer em etapa e condição
        cls.gestor = make_user("gestor", cls.org, MANAGER_ACTIONS)  # gestor de Orçamento
        cls.bia = make_user("bia", cls.org, WORK_ACTIONS)  # membro de Financeiro
        cls.duo = make_user("duo", cls.org, WORK_ACTIONS)  # membro dos dois setores
        cls.visitante = make_user("visitante", cls.org, WORK_ACTIONS)  # de nenhum setor; atua em um item de Orçamento
        cls.semsetor = make_user("semsetor", cls.org)  # de nenhum setor e sem itens
        cls.leitor = make_user("leitor", cls.org)  # membro de Orçamento, sem permissão de mexer
        cls.alheio = make_user("alheio", cls.other_org, MANAGER_ACTIONS)
        for user, sector in (
            (cls.ana, cls.orcamento), (cls.gestor, cls.orcamento), (cls.bia, cls.financeiro),
            (cls.duo, cls.orcamento), (cls.duo, cls.financeiro), (cls.leitor, cls.orcamento),
        ):
            UserSector.objects.create(user=user, sector=sector)

        # Etapas e condições, por setor e por tipo
        cls.d_afazer = cls._stage(ActivityStage, cls.orcamento, "A fazer", 1, default=True)
        cls.d_levant = cls._stage(ActivityStage, cls.orcamento, "Levantamento", 2)
        cls.d_cotacao = cls._stage(ActivityStage, cls.orcamento, "Cotação", 3)
        cls.f_afazer = cls._stage(ActivityStage, cls.financeiro, "A fazer", 1, default=True)
        cls.f_conf = cls._stage(ActivityStage, cls.financeiro, "Conferência", 2)
        cls.t_afazer = cls._stage(TaskStage, cls.orcamento, "A fazer", 1, default=True)
        cls.t_exec = cls._stage(TaskStage, cls.orcamento, "Em execução", 2)
        cls.t_pronto = cls._stage(TaskStage, cls.orcamento, "Pronto", 3)
        cls.tf_fila = cls._stage(TaskStage, cls.financeiro, "Fila", 1, default=True)
        cls.d_normal = cls._condition(cls.orcamento, WorkflowStatus.Domain.ACTIVITY, "Normal", 1, default=True)
        cls.d_cliente = cls._condition(cls.orcamento, WorkflowStatus.Domain.ACTIVITY, "Aguardando cliente", 2)
        cls.f_normal = cls._condition(cls.financeiro, WorkflowStatus.Domain.ACTIVITY, "Normal", 1, default=True)
        cls.t_normal = cls._condition(cls.orcamento, WorkflowStatus.Domain.TASK, "Normal", 1, default=True)
        cls.t_info = cls._condition(cls.orcamento, WorkflowStatus.Domain.TASK, "Aguardando informação", 2)

        cls.convivy = Client.objects.create(organization=cls.org, name="Convivy")
        cls.aurora = Site.objects.create(organization=cls.org, name="Residencial Aurora", client=cls.convivy)

        # Demandas
        cls.a1 = cls._activity("Orçamento Aurora", cls.ana, cls.orcamento, cls.d_afazer, cls.d_normal, client=cls.convivy, site=cls.aurora)
        cls.a2 = cls._activity("Levantamento da garagem", cls.gestor, cls.orcamento, cls.d_levant, cls.d_cliente)
        cls.a3 = cls._activity("Pagamento fornecedor", cls.bia, cls.financeiro, cls.f_afazer, cls.f_normal)
        cls.a_visitante = cls._activity("Item do visitante", cls.visitante, cls.orcamento, cls.d_afazer, cls.d_normal)
        cls.a_done = cls._activity("Já concluída", cls.ana, cls.orcamento, cls.d_afazer, cls.d_normal, status=Activity.Status.CONCLUIDA)
        cls.a_draft = cls._activity("Rascunho", cls.ana, cls.orcamento, None, None, status=Activity.Status.RASCUNHO)
        cls.a_foreign = Activity.objects.create(organization=cls.other_org, title="Alheia", owner=cls.alheio, created_by=cls.alheio)

        # Tarefas
        cls.t1 = cls._task(cls.a1, "Levantar quantitativos", cls.ana, cls.orcamento, cls.t_afazer, cls.t_normal)
        cls.t2 = cls._task(cls.a2, "Cotar cabos", cls.gestor, cls.orcamento, cls.t_exec, cls.t_info)
        cls.t3 = cls._task(cls.a3, "Conferir nota", cls.bia, cls.financeiro, cls.tf_fila, None)
        cls.t_visitante = cls._task(cls.a_visitante, "Tarefa do visitante", cls.visitante, cls.orcamento, cls.t_afazer, cls.t_normal)

    # -- fábricas --------------------------------------------------------------

    @classmethod
    def _stage(cls, model, sector, name, order, default=False):
        return model.objects.create(organization=cls.org, sector=sector, name=name, order=order, is_default=default)

    @classmethod
    def _condition(cls, sector, domain, name, order, default=False):
        return WorkflowStatus.objects.create(
            organization=cls.org, sector=sector, domain=domain, name=name, order=order, is_default=default, color="#3B82F6"
        )

    @classmethod
    def _activity(cls, title, owner, sector, stage, condition, status=Activity.Status.ABERTA, **extra):
        return Activity.objects.create(
            organization=cls.org, title=title, owner=owner, created_by=owner, sector=sector,
            stage=stage, condition=condition, status=status, **extra,
        )

    @classmethod
    def _task(cls, activity, title, responsavel, sector, stage, condition, status=Task.Status.EM_FILA, **extra):
        return Task.objects.create(
            activity=activity, title=title, responsavel=responsavel, created_by=responsavel, sector=sector,
            stage=stage, condition=condition, status=status, **extra,
        )

    def stage(self, *args, **kwargs):
        return self._stage(*args, **kwargs)

    def condition(self, *args, **kwargs):
        return self._condition(*args, **kwargs)

    def activity(self, *args, **kwargs):
        return self._activity(*args, **kwargs)

    def task(self, *args, **kwargs):
        return self._task(*args, **kwargs)

    # -- leitura ----------------------------------------------------------------

    def board(self, name, user, **params):
        self.client.force_login(user)
        return self.client.get(reverse(name), params)

    def titles(self, response, stage=None):
        columns = response.context["columns"]
        rows = []
        for column in columns:
            if stage is None or column["stage"] == stage:
                rows.extend(item.title for item in column["items"])
        return rows

    def all_titles(self, response):
        titles = self.titles(response)
        if response.context["unassigned"]:
            titles += [item.title for item in response.context["unassigned"]["items"]]
        return titles


class BoardSectorTests(KanbanTestCase):
    def test_the_board_is_always_of_one_sector_with_its_own_stages(self):
        response = self.board("activity-kanban", self.ana)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sector"], self.orcamento)
        self.assertEqual([c["stage"].name for c in response.context["columns"]], ["A fazer", "Levantamento", "Cotação"])
        self.assertNotContains(response, "Conferência")

    def test_tasks_board_uses_the_task_stages_of_the_sector(self):
        response = self.board("task-kanban", self.ana)
        self.assertEqual([c["stage"].name for c in response.context["columns"]], ["A fazer", "Em execução", "Pronto"])

    def test_a_member_of_two_sectors_switches_and_the_choice_is_remembered(self):
        self.duo.profile.main_sector = None
        self.duo.profile.save(update_fields=["main_sector"])
        first = self.board("activity-kanban", self.duo)
        # Sem setor principal abre no setor em que a pessoa passou a atuar primeiro, não no primeiro por nome.
        self.assertEqual(first.context["sector"], self.orcamento)
        switched = self.client.get(reverse("activity-kanban"), {"setor": self.financeiro.pk})
        self.assertEqual(switched.context["sector"], self.financeiro)
        remembered = self.client.get(reverse("activity-kanban"))
        self.assertEqual(remembered.context["sector"], self.financeiro)

    def test_the_main_sector_of_the_person_is_the_default(self):
        self.duo.profile.main_sector = self.orcamento
        self.duo.profile.save(update_fields=["main_sector"])
        self.assertEqual(self.board("activity-kanban", self.duo).context["sector"], self.orcamento)

    def test_a_sector_the_person_cannot_open_is_ignored_not_leaked(self):
        for other in (self.financeiro, self.foreign_sector):
            with self.subTest(sector=other.name):
                response = self.board("activity-kanban", self.ana, setor=other.pk)
                self.assertEqual(response.context["sector"], self.orcamento)
                self.assertNotIn("Pagamento fornecedor", self.all_titles(response))

    def test_old_group_parameter_still_selects_the_sector(self):
        response = self.board("activity-kanban", self.duo, grupo=self.financeiro.pk)
        self.assertEqual(response.context["sector"], self.financeiro)

    def test_a_person_without_sector_or_items_sees_an_explanation(self):
        response = self.board("activity-kanban", self.semsetor)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["sector"])
        self.assertContains(response, "Você ainda não tem um setor neste quadro")

    def test_a_sector_without_stages_explains_and_offers_setup_only_to_managers(self):
        ActivityStage.objects.filter(sector=self.orcamento).delete()
        manager = self.board("activity-kanban", self.gestor)
        self.assertContains(manager, "ainda não tem etapas para demandas")
        self.assertContains(manager, "Configurar etapas")
        member = self.board("activity-kanban", self.ana)
        self.assertContains(member, "Fale com o gestor do setor")
        self.assertNotContains(member, "Configurar etapas")

    def test_login_is_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("activity-kanban")).status_code, 302)
        self.assertEqual(self.client.get(reverse("task-kanban")).status_code, 302)


class BoardVisibilityTests(KanbanTestCase):
    def test_a_member_of_the_sector_sees_every_item_of_it(self):
        response = self.board("activity-kanban", self.ana)
        self.assertEqual(
            sorted(self.all_titles(response)), sorted(["Orçamento Aurora", "Levantamento da garagem", "Item do visitante"])
        )

    def test_someone_outside_the_sector_sees_only_what_they_work_on(self):
        response = self.board("activity-kanban", self.visitante)
        self.assertEqual(response.context["sector"], self.orcamento)
        self.assertEqual(self.all_titles(response), ["Item do visitante"])

    def test_participating_in_a_task_makes_the_demand_visible_to_an_outsider(self):
        self.t1.executors.create(user=self.visitante, added_by=self.ana)
        response = self.board("activity-kanban", self.visitante)
        self.assertIn("Item do visitante", self.all_titles(response))

    def test_tasks_of_an_outsider_are_limited_to_their_own(self):
        response = self.board("task-kanban", self.visitante)
        self.assertEqual(self.all_titles(response), ["Tarefa do visitante"])

    def test_drafts_and_finished_items_are_hidden_until_asked(self):
        hidden = self.board("activity-kanban", self.ana)
        self.assertNotIn("Já concluída", self.all_titles(hidden))
        self.assertNotIn("Rascunho", self.all_titles(hidden))
        shown = self.client.get(reverse("activity-kanban"), {"concluidas": "1"})
        self.assertIn("Já concluída", self.all_titles(shown))
        self.assertNotIn("Rascunho", self.all_titles(shown))

    def test_finished_tasks_are_hidden_until_asked(self):
        done = self.task(self.a1, "Tarefa pronta", self.ana, self.orcamento, self.t_pronto, None, status=Task.Status.CONCLUIDA)
        self.assertNotIn(done.title, self.all_titles(self.board("task-kanban", self.ana)))
        self.assertIn(done.title, self.all_titles(self.client.get(reverse("task-kanban"), {"concluidas": "1"})))

    def test_nothing_from_another_organization_ever_shows(self):
        self.client.force_login(self.alheio)
        response = self.client.get(reverse("activity-kanban"))
        self.assertNotIn("Orçamento Aurora", self.all_titles(response))


class ColumnTests(KanbanTestCase):
    def test_items_are_grouped_by_stage_and_counted(self):
        response = self.board("activity-kanban", self.ana)
        counts = {c["stage"].name: c["count"] for c in response.context["columns"]}
        self.assertEqual(counts, {"A fazer": 2, "Levantamento": 1, "Cotação": 0})

    def test_sem_etapa_only_appears_when_something_needs_classifying(self):
        self.assertIsNone(self.board("activity-kanban", self.ana).context["unassigned"])
        Activity.objects.filter(pk=self.a1.pk).update(stage=None)
        response = self.client.get(reverse("activity-kanban"))
        self.assertEqual([i.title for i in response.context["unassigned"]["items"]], ["Orçamento Aurora"])
        self.assertContains(response, "Sem etapa")

    def test_an_inactive_stage_sends_its_items_to_sem_etapa(self):
        ActivityStage.objects.filter(pk=self.d_levant.pk).update(is_active=False)
        response = self.board("activity-kanban", self.ana)
        self.assertEqual([c["stage"].name for c in response.context["columns"]], ["A fazer", "Cotação"])
        self.assertEqual([i.title for i in response.context["unassigned"]["items"]], ["Levantamento da garagem"])

    def test_the_column_limit_only_warns(self):
        ActivityStage.objects.filter(pk=self.d_afazer.pk).update(column_limit=1)
        response = self.board("activity-kanban", self.ana)
        column = response.context["columns"][0]
        self.assertTrue(column["over_limit"])
        self.assertContains(response, "2 de 1")
        self.assertEqual(response.status_code, 200)

    def test_a_column_within_the_limit_is_not_flagged(self):
        ActivityStage.objects.filter(pk=self.d_afazer.pk).update(column_limit=5)
        self.assertFalse(self.board("activity-kanban", self.ana).context["columns"][0]["over_limit"])

    def test_cards_show_the_condition_and_titles_are_escaped(self):
        Activity.objects.filter(pk=self.a1.pk).update(title="<script>alert(1)</script>")
        response = self.board("activity-kanban", self.ana)
        self.assertContains(response, "Aguardando cliente")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_cards_the_person_cannot_move_are_not_draggable(self):
        response = self.board("activity-kanban", self.leitor)
        self.assertContains(response, 'draggable="false"')
        self.assertNotContains(response, 'draggable="true"')
        mover = self.board("activity-kanban", self.ana)
        self.assertContains(mover, 'draggable="true"')

    def test_the_column_menu_offers_limit_and_edit_only_to_managers(self):
        self.assertContains(self.board("activity-kanban", self.gestor), "Definir limite da coluna")
        self.assertNotContains(self.board("activity-kanban", self.ana), "Definir limite da coluna")

    def test_task_columns_open_the_new_task_window_already_in_the_sector_and_stage(self):
        response = self.board("task-kanban", self.ana)
        self.assertContains(response, f"sector={self.orcamento.pk}&amp;stage={self.t_afazer.pk}")


class FilterTests(KanbanTestCase):
    def test_search_matches_title_client_site_and_the_old_code(self):
        for term in ("Aurora", "Convivy", "Residencial", self.a1.code.replace("DEM-", "ATV-")):
            with self.subTest(term=term):
                response = self.board("activity-kanban", self.ana, q=term)
                self.assertEqual(self.all_titles(response), ["Orçamento Aurora"])

    def test_task_search_matches_the_demand_of_the_task(self):
        response = self.board("task-kanban", self.ana, q="garagem")
        self.assertEqual(self.all_titles(response), ["Cotar cabos"])

    def test_person_filter(self):
        mine = self.board("activity-kanban", self.ana, pessoa="eu")
        self.assertEqual(self.all_titles(mine), ["Orçamento Aurora"])
        other = self.client.get(reverse("activity-kanban"), {"pessoa": self.gestor.pk})
        self.assertEqual(self.all_titles(other), ["Levantamento da garagem"])

    def test_condition_filter(self):
        response = self.board("activity-kanban", self.ana, condicao=self.d_cliente.pk)
        self.assertEqual(self.all_titles(response), ["Levantamento da garagem"])

    def test_client_and_site_filters(self):
        self.assertEqual(self.all_titles(self.board("activity-kanban", self.ana, cliente=self.convivy.pk)), ["Orçamento Aurora"])
        self.assertEqual(self.all_titles(self.client.get(reverse("activity-kanban"), {"obra": self.aurora.pk})), ["Orçamento Aurora"])

    def test_deadline_filters(self):
        now = timezone.now()
        Activity.objects.filter(pk=self.a1.pk).update(requested_deadline=now - datetime.timedelta(days=2))
        Activity.objects.filter(pk=self.a2.pk).update(requested_deadline=now + datetime.timedelta(days=3))
        self.assertEqual(self.all_titles(self.board("activity-kanban", self.ana, prazo="atrasadas")), ["Orçamento Aurora"])
        self.assertEqual(self.all_titles(self.client.get(reverse("activity-kanban"), {"prazo": "7_dias"})), ["Levantamento da garagem"])
        self.assertEqual(self.all_titles(self.client.get(reverse("activity-kanban"), {"prazo": "sem_prazo"})), ["Item do visitante"])

    def test_blocked_filter_uses_the_operational_status(self):
        Activity.objects.filter(pk=self.a2.pk).update(status=Activity.Status.BLOQUEADA)
        self.assertEqual(self.all_titles(self.board("activity-kanban", self.ana, bloqueio="1")), ["Levantamento da garagem"])

    def test_task_participant_filter(self):
        self.t1.executors.create(user=self.duo, added_by=self.ana)
        response = self.board("task-kanban", self.ana, participante=self.duo.pk)
        self.assertEqual(self.all_titles(response), ["Levantar quantitativos"])

    def test_invalid_values_are_ignored(self):
        response = self.board("activity-kanban", self.ana, pessoa="abc", condicao="x", cliente="; drop", prazo="nunca", ordem="zzz", dir="up")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.all_titles(response)), 3)

    def test_ordering_by_title_in_both_directions(self):
        asc = self.board("activity-kanban", self.ana, ordem="titulo")
        self.assertEqual(self.titles(asc, self.d_afazer), ["Item do visitante", "Orçamento Aurora"])
        desc = self.client.get(reverse("activity-kanban"), {"ordem": "titulo", "dir": "desc"})
        self.assertEqual(self.titles(desc, self.d_afazer), ["Orçamento Aurora", "Item do visitante"])

    def test_deadline_ordering_puts_the_empty_deadline_last(self):
        now = timezone.now()
        Activity.objects.filter(pk=self.a_visitante.pk).update(requested_deadline=now + datetime.timedelta(days=9))
        Activity.objects.filter(pk=self.a1.pk).update(requested_deadline=now + datetime.timedelta(days=1))
        asc = self.board("activity-kanban", self.ana, ordem="prazo", dir="asc")
        self.assertEqual(self.titles(asc, self.d_afazer), ["Orçamento Aurora", "Item do visitante"])
        desc = self.client.get(reverse("activity-kanban"), {"ordem": "prazo", "dir": "desc"})
        self.assertEqual(self.titles(desc, self.d_afazer), ["Item do visitante", "Orçamento Aurora"])
        # sem prazo, o vazio fica sempre por último, qualquer que seja o sentido
        Activity.objects.filter(pk=self.a_visitante.pk).update(requested_deadline=None)
        for direction in ("asc", "desc"):
            response = self.client.get(reverse("activity-kanban"), {"ordem": "prazo", "dir": direction})
            self.assertEqual(self.titles(response, self.d_afazer)[-1], "Item do visitante")

    def test_clear_link_keeps_only_the_sector(self):
        response = self.board("activity-kanban", self.ana, q="x")
        self.assertTrue(response.context["has_filters"])
        self.assertContains(response, f'href="{reverse("activity-kanban")}?setor={self.orcamento.pk}"')


class QueryCountTests(KanbanTestCase):
    def count_queries(self, name):
        # A primeira visita grava o setor escolhido na sessão (UPDATE + savepoint); só a partir da segunda
        # o número de consultas depende dos cartões.
        self.client.get(reverse(name))
        with CaptureQueriesContext(connection) as context:
            self.client.get(reverse(name))
        return len(context)

    def test_demand_cards_do_not_cost_a_query_each(self):
        self.client.force_login(self.ana)
        few = self.count_queries("activity-kanban")
        for index in range(12):
            self.activity(f"Extra {index}", self.ana, self.orcamento, self.d_afazer, self.d_normal, client=self.convivy)
        self.assertEqual(self.count_queries("activity-kanban"), few)

    def test_task_cards_do_not_cost_a_query_each(self):
        self.client.force_login(self.ana)
        few = self.count_queries("task-kanban")
        for index in range(12):
            activity = self.activity(f"Demanda {index}", self.ana, self.orcamento, self.d_afazer, self.d_normal)
            self.task(activity, f"Tarefa {index}", self.ana, self.orcamento, self.t_afazer, self.t_normal)
        self.assertEqual(self.count_queries("task-kanban"), few)


class SetStageTests(KanbanTestCase):
    def post(self, domain, item, stage_id, user=None):
        self.client.force_login(user or self.ana)
        return self.client.post(reverse("kanban-set-stage", args=[domain, item.pk]), {"stage_id": stage_id}, **AJAX)

    def test_moving_a_demand_changes_only_the_stage(self):
        before = (self.a1.status, self.a1.condition_id, self.a1.owner_id, self.a1.sector_id)
        response = self.post("demandas", self.a1, self.d_cotacao.pk)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["stage_id"], self.d_cotacao.pk)
        self.assertIn(f'data-stage-id="{self.d_cotacao.pk}"', data["card_html"])
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.stage, self.d_cotacao)
        self.assertIsNotNone(self.a1.stage_changed_at)
        self.assertEqual((self.a1.status, self.a1.condition_id, self.a1.owner_id, self.a1.sector_id), before)

    def test_moving_a_task_never_touches_status_or_condition(self):
        response = self.post("tarefas", self.t1, self.t_pronto.pk)
        self.assertEqual(response.status_code, 200)
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.stage, self.t_pronto)
        self.assertEqual(self.t1.status, Task.Status.EM_FILA)
        self.assertEqual(self.t1.condition, self.t_normal)
        self.assertFalse(self.t1.work_sessions.exists())

    def test_the_move_is_audited(self):
        self.post("demandas", self.a1, self.d_levant.pk)
        entry = AuditLog.objects.get(activity=self.a1, field_name="etapa")
        self.assertEqual((entry.old_value, entry.new_value), ("A fazer", "Levantamento"))

    def test_a_stage_of_another_sector_is_refused(self):
        response = self.post("demandas", self.a1, self.f_conf.pk)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["success"])
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.stage, self.d_afazer)

    def test_an_unknown_stage_is_404(self):
        self.assertEqual(self.post("demandas", self.a1, 999999).status_code, 404)

    def test_a_task_stage_is_not_resolved_as_a_demand_stage(self):
        # Ids de etapa de tarefa e de demanda se sobrepõem: o que vale é o catálogo do tipo certo.
        ActivityStage.objects.filter(pk=self.t_pronto.pk).delete()
        self.assertEqual(self.post("demandas", self.a1, self.t_pronto.pk).status_code, 404)

    def test_an_inactive_stage_is_refused(self):
        ActivityStage.objects.filter(pk=self.d_cotacao.pk).update(is_active=False)
        self.assertEqual(self.post("demandas", self.a1, self.d_cotacao.pk).status_code, 403)

    def test_a_person_without_the_action_is_refused(self):
        response = self.post("demandas", self.a1, self.d_cotacao.pk, user=self.leitor)
        self.assertEqual(response.status_code, 403)
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.stage, self.d_afazer)

    def test_another_organization_gets_404(self):
        response = self.post("demandas", self.a1, self.d_cotacao.pk, user=self.alheio)
        self.assertEqual(response.status_code, 404)

    def test_a_blank_stage_is_not_accepted(self):
        self.assertEqual(self.post("demandas", self.a1, "").status_code, 400)

    def test_only_post_is_accepted(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse("kanban-set-stage", args=["demandas", self.a1.pk])).status_code, 405)

    def test_unknown_board_is_404(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.post(reverse("kanban-set-stage", args=["outros", self.a1.pk]), {"stage_id": 1}).status_code, 404)


class SetConditionTests(KanbanTestCase):
    def post(self, domain, item, condition_id, user=None):
        self.client.force_login(user or self.ana)
        return self.client.post(reverse("kanban-set-condition", args=[domain, item.pk]), {"condition_id": condition_id}, **AJAX)

    def test_choosing_a_condition_changes_only_the_condition(self):
        before_stage, before_status = self.a1.stage_id, self.a1.status
        response = self.post("demandas", self.a1, self.d_cliente.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["condition_name"], "Aguardando cliente")
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.condition, self.d_cliente)
        self.assertEqual((self.a1.stage_id, self.a1.status), (before_stage, before_status))

    def test_a_condition_never_runs_an_operational_action(self):
        waiting = Task.Status.EM_EXECUCAO
        Task.objects.filter(pk=self.t1.pk).update(status=waiting)
        self.post("tarefas", self.t1, self.t_info.pk)
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.status, waiting)
        self.assertEqual(self.t1.condition, self.t_info)
        self.assertFalse(self.t1.blocks.exists())

    def test_the_condition_can_be_cleared(self):
        response = self.post("demandas", self.a1, "")
        self.assertEqual(response.status_code, 200)
        self.a1.refresh_from_db()
        self.assertIsNone(self.a1.condition)

    def test_a_condition_of_another_sector_is_refused(self):
        self.assertEqual(self.post("demandas", self.a1, self.f_normal.pk).status_code, 403)

    def test_a_task_condition_cannot_be_used_on_a_demand(self):
        self.assertEqual(self.post("demandas", self.a1, self.t_info.pk).status_code, 404)

    def test_a_person_without_the_action_is_refused(self):
        self.assertEqual(self.post("demandas", self.a1, self.d_cliente.pk, user=self.leitor).status_code, 403)

    def test_the_card_offers_the_condition_picker_only_to_who_can_change_it(self):
        self.assertContains(self.board("activity-kanban", self.ana), "data-workflow-picker")
        self.assertNotContains(self.board("activity-kanban", self.leitor), 'data-kind="condition"')


class CreateCardTests(KanbanTestCase):
    def create(self, user=None, **data):
        self.client.force_login(user or self.ana)
        payload = {"sector_id": self.orcamento.pk, "stage_id": self.d_levant.pk, **data}
        return self.client.post(reverse("kanban-create-card", args=["demandas"]), payload, **AJAX)

    def test_a_demand_is_created_in_the_column_with_the_sector_and_defaults(self):
        response = self.create(title="  Nova   demanda do quadro ")
        self.assertEqual(response.status_code, 201)
        activity = Activity.objects.get(title="Nova demanda do quadro")
        self.assertEqual(activity.sector, self.orcamento)
        self.assertEqual(activity.owner, self.ana)
        self.assertEqual(activity.created_by, self.ana)
        self.assertEqual(activity.stage, self.d_levant)
        self.assertEqual(activity.condition, self.d_normal)
        self.assertEqual(activity.status, Activity.Status.ABERTA)
        self.assertIn(activity.title, response.json()["card_html"])
        self.assertTrue(activity.code.startswith("DEM-"))

    def test_without_the_stage_action_the_demand_stays_in_the_default_stage(self):
        creator = make_user("criador", self.org, [catalog.ATIVIDADE_CRIAR])
        UserSector.objects.create(user=creator, sector=self.orcamento)
        response = self.create(user=creator, title="Só criar")
        self.assertEqual(response.status_code, 201)
        self.assertIn("etapa padrão", response.json()["message"])
        self.assertEqual(Activity.objects.get(title="Só criar").stage, self.d_afazer)

    def test_validations(self):
        self.assertEqual(self.create(title="   ").status_code, 400)
        self.assertEqual(self.create(title="x" * 201).status_code, 400)
        self.assertEqual(self.create(title="Ok", sector_id=self.financeiro.pk).status_code, 403)
        self.assertEqual(self.create(title="Ok", sector_id=self.foreign_sector.pk).status_code, 403)
        self.assertEqual(self.create(title="Ok", stage_id=self.f_conf.pk).status_code, 404)
        self.assertFalse(Activity.objects.filter(title="Ok").exists())

    def test_someone_who_cannot_create_demands_is_refused_and_nothing_is_written(self):
        before = Activity.objects.count()
        response = self.create(user=self.leitor, title="Não pode")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Activity.objects.count(), before)

    def test_tasks_are_not_created_inline(self):
        self.client.force_login(self.ana)
        response = self.client.post(reverse("kanban-create-card", args=["tarefas"]), {"title": "x", "sector_id": self.orcamento.pk}, **AJAX)
        self.assertEqual(response.status_code, 400)


class ColumnLimitTests(KanbanTestCase):
    def post(self, user, stage, limit):
        self.client.force_login(user)
        return self.client.post(reverse("kanban-column-limit", args=["demandas"]), {"stage_id": stage.pk, "limit": limit}, **AJAX)

    def test_a_manager_sets_and_removes_the_limit(self):
        self.assertEqual(self.post(self.gestor, self.d_afazer, "4").status_code, 200)
        self.d_afazer.refresh_from_db()
        self.assertEqual(self.d_afazer.column_limit, 4)
        self.assertEqual(self.post(self.gestor, self.d_afazer, "").status_code, 200)
        self.d_afazer.refresh_from_db()
        self.assertIsNone(self.d_afazer.column_limit)

    def test_a_member_cannot_set_it(self):
        self.assertEqual(self.post(self.ana, self.d_afazer, "4").status_code, 403)
        self.d_afazer.refresh_from_db()
        self.assertIsNone(self.d_afazer.column_limit)

    def test_a_manager_of_another_sector_cannot_set_it(self):
        grant = make_user("gestor_fin", self.org)
        from acessos.testing import grant_action

        grant_action(grant, catalog.ETAPA_GERIR, organization=self.org, sector=self.financeiro)
        self.assertEqual(self.post(grant, self.d_afazer, "4").status_code, 403)
        self.assertEqual(self.post(grant, self.f_afazer, "4").status_code, 200)

    def test_invalid_limits_are_refused(self):
        for bad in ("0", "1000", "-3", "abc", "2.5"):
            with self.subTest(value=bad):
                self.assertEqual(self.post(self.gestor, self.d_afazer, bad).status_code, 400)

    def test_another_organization_gets_404(self):
        self.assertEqual(self.post(self.alheio, self.d_afazer, "3").status_code, 404)


class CreateOptionTests(KanbanTestCase):
    def post(self, user, kind, name, color="#22C55E", sector=None, domain="demandas"):
        self.client.force_login(user)
        return self.client.post(
            reverse("kanban-create-option", args=[domain]),
            {"kind": kind, "name": name, "color": color, "sector_id": (sector or self.orcamento).pk},
            **AJAX,
        )

    def test_a_manager_creates_a_stage_and_a_condition_in_the_sector(self):
        stage = self.post(self.gestor, "stage", "Revisão")
        self.assertEqual(stage.status_code, 201)
        self.assertTrue(ActivityStage.objects.filter(sector=self.orcamento, name="Revisão", color="#22C55E").exists())
        condition = self.post(self.gestor, "condition", "Suspensa")
        self.assertEqual(condition.status_code, 201)
        self.assertTrue(
            WorkflowStatus.objects.filter(sector=self.orcamento, domain=WorkflowStatus.Domain.ACTIVITY, name="Suspensa").exists()
        )

    def test_task_options_go_to_the_task_catalog(self):
        self.assertEqual(self.post(self.gestor, "stage", "Revisar", domain="tarefas").status_code, 201)
        self.assertTrue(TaskStage.objects.filter(sector=self.orcamento, name="Revisar").exists())
        self.assertFalse(ActivityStage.objects.filter(name="Revisar").exists())

    def test_a_member_is_refused(self):
        self.assertEqual(self.post(self.ana, "stage", "Nova").status_code, 403)
        self.assertEqual(self.post(self.ana, "condition", "Nova").status_code, 403)
        self.assertFalse(ActivityStage.objects.filter(name="Nova").exists())

    def test_duplicates_blank_names_unknown_kinds_and_bad_colors_are_refused(self):
        self.assertEqual(self.post(self.gestor, "stage", "levantamento").status_code, 400)
        self.assertEqual(self.post(self.gestor, "stage", "   ").status_code, 400)
        self.assertEqual(self.post(self.gestor, "other", "X").status_code, 400)
        self.assertEqual(self.post(self.gestor, "stage", "Cor ruim", color="#123456").status_code, 400)

    def test_a_sector_of_another_organization_is_404(self):
        self.assertEqual(self.post(self.gestor, "stage", "X", sector=self.foreign_sector).status_code, 404)


class CardEndpointTests(KanbanTestCase):
    def get(self, domain, item, user=None, **params):
        self.client.force_login(user or self.ana)
        return self.client.get(reverse("kanban-card", args=[domain, item.pk]), params, **AJAX)

    def test_returns_the_card_as_it_is_now(self):
        data = self.get("demandas", self.a1, setor=self.orcamento.pk).json()
        self.assertTrue(data["visible"])
        self.assertEqual(data["stage_id"], self.d_afazer.pk)
        self.assertIn("Orçamento Aurora", data["card_html"])

    def test_says_when_the_card_left_the_board(self):
        Activity.objects.filter(pk=self.a1.pk).update(status=Activity.Status.CONCLUIDA)
        self.assertFalse(self.get("demandas", self.a1, setor=self.orcamento.pk).json()["visible"])
        self.assertTrue(self.get("demandas", self.a1, setor=self.orcamento.pk, concluidas="1").json()["visible"])

    def test_an_outsider_does_not_get_a_card_they_cannot_see(self):
        self.assertFalse(self.get("demandas", self.a1, user=self.visitante, setor=self.orcamento.pk).json()["visible"])


class DrawerTests(KanbanTestCase):
    def test_the_demand_drawer_has_the_essentials_and_the_workflow_controls(self):
        self.client.force_login(self.ana)
        response = self.client.get(reverse("activity-kanban-drawer", args=[self.a1.pk]), **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Orçamento Aurora")
        self.assertContains(response, self.a1.code)
        self.assertContains(response, "Levantar quantitativos")  # as tarefas da demanda
        self.assertContains(response, "Abrir ficha completa")
        self.assertContains(response, 'data-kind="stage"')
        self.assertContains(response, 'data-kind="condition"')
        self.assertContains(response, "js-drawer-backdrop")

    def test_the_drawer_controls_are_read_only_without_permission(self):
        self.client.force_login(self.leitor)
        response = self.client.get(reverse("activity-kanban-drawer", args=[self.a1.pk]), **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-workflow-picker")
        self.assertNotContains(response, ">Editar<")

    def test_drafts_have_no_drawer_and_other_organizations_get_404(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse("activity-kanban-drawer", args=[self.a_draft.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("activity-kanban-drawer", args=[self.a_foreign.pk])).status_code, 404)

    def test_the_task_drawer_gets_stage_and_condition_controls(self):
        self.client.force_login(self.ana)
        response = self.client.get(reverse("task-drawer", args=[self.t1.pk]), **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-kind="stage"')
        self.assertContains(response, 'data-kind="condition"')
        self.assertContains(response, f'data-set-url="{reverse("kanban-set-stage", args=["tarefas", self.t1.pk])}"')
        self.assertContains(response, f'data-options-url="{reverse("sector-stage-options", args=[self.orcamento.pk])}?dominio=tarefa"')

    def test_the_task_drawer_controls_are_read_only_without_permission(self):
        self.client.force_login(self.leitor)
        response = self.client.get(reverse("task-drawer", args=[self.t1.pk]), **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-workflow-picker")


class WiringTests(KanbanTestCase):
    def test_the_kanban_addresses_use_the_new_views(self):
        self.assertEqual(reverse("activity-kanban"), "/demandas/kanban/")
        self.assertEqual(reverse("task-kanban"), "/tarefas/kanban/")
        self.assertEqual(resolve("/demandas/kanban/").func.view_class.__module__, "activities.kanban")
        self.assertEqual(resolve("/tarefas/kanban/").func.view_class.__module__, "activities.kanban")

    def test_both_boards_light_up_their_menu_item(self):
        self.assertEqual(self.board("activity-kanban", self.ana).context["nav_active"], "activities")
        self.assertEqual(self.board("task-kanban", self.ana).context["nav_active"], "tasks")

    def test_the_old_address_still_redirects_to_the_board(self):
        response = self.client.get("/atividades/kanban/?setor=1")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/demandas/kanban/?setor=1")

    def test_the_new_task_window_opens_already_in_the_sector_and_stage(self):
        self.client.force_login(self.ana)
        response = self.client.get(
            reverse("task-quick-create-standalone"), {"sector": self.orcamento.pk, "stage": self.t_exec.pk}
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial["sector"], self.orcamento.pk)
        self.assertEqual(form.initial["stage"], self.t_exec.pk)

    def test_garbage_in_the_initial_values_is_ignored(self):
        self.client.force_login(self.ana)
        response = self.client.get(reverse("task-quick-create-standalone"), {"sector": "x", "stage": "1; drop"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("stage", response.context["form"].initial)

    def test_the_picker_script_and_style_load_on_every_page(self):
        self.client.force_login(self.ana)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "js/workflow-picker.js")
        self.assertContains(response, "css/kanban.css")
