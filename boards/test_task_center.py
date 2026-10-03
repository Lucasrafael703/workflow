"""Tela Tarefas (painel pessoal sobre os Quadros de Demanda) e a prévia do Quadro na ficha da Demanda.

A "tarefa" é o item do Quadro da Demanda: responsável = célula Pessoa, Status = célula de etiqueta, prazo = coluna Data.
"""

import datetime
import json

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from activities.models import Activity
from activities.services import ActivityService
from activities.testing import make_user
from core.models import Organization, Sector
from notifications.models import Notification

from .demand_preview import DemandBoardPreviewQuery
from .models import Board, BoardColumn
from .services import CellService, ItemService
from .task_center import DOING, DONE, TODO, TaskCenterQuery, open_task_count, parse_week

TODAY = datetime.date(2026, 10, 7)  # quarta-feira
EDITOR = [catalog.ATIVIDADE_CRIAR, catalog.QUADRO_CRIAR_ITEM, catalog.QUADRO_EDITAR_ITEM]


class TaskCenterBase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Outra")
        self.sector = Sector.objects.create(organization=self.org, name="Comercial")
        self.ana = make_user("ana", self.org, EDITOR)
        self.bruno = make_user("bruno", self.org, EDITOR)
        self.leitor = make_user("leitor", self.org, [])
        self.gestor = make_user("gestor", self.org, [catalog.QUADRO_VISUALIZAR, catalog.ATIVIDADE_VISUALIZAR])
        self.alheio = make_user("alheio", self.other_org, EDITOR)
        self.demand_a = self.activity("Orçamento A", self.ana)
        self.demand_b = self.activity("Orçamento B", self.bruno)

    def activity(self, title, owner, org=None, sector=None):
        org = org or self.org
        sector = sector or (self.sector if org == self.org else Sector.objects.create(organization=org, name="Setor"))
        return ActivityService.create_activity(organization=org, title=title, owner=owner, created_by=owner, sector=sector)

    def columns(self, activity):
        board = activity.task_board
        cols = {column.type: column for column in board.columns.filter(is_active=True)}
        options = {option.label: option for option in cols[BoardColumn.Type.STATUS].options.all()}
        return board, cols, options

    def task(self, activity, name, person=None, due=None, status=None, user=None):
        board, cols, options = self.columns(activity)
        user = user or activity.owner
        item = ItemService.create(user=user, board=board, group=board.groups.filter(is_active=True).first(), name=name)
        if person is not None:
            CellService.set_value(user=user, item=item, column=cols[BoardColumn.Type.PERSON], raw_value=person.pk)
        if due is not None:
            CellService.set_value(user=user, item=item, column=cols[BoardColumn.Type.DATE], raw_value=due.isoformat())
        if status:
            CellService.set_value(user=user, item=item, column=cols[BoardColumn.Type.STATUS], raw_value=options[status].pk)
        return item

    def query(self, user, today=TODAY, **params):
        return TaskCenterQuery(user, self.org, params, today=today)

    def names(self, rows):
        return [row.name for row in rows]


class ScopeTests(TaskCenterBase):
    def setUp(self):
        super().setUp()
        d = datetime.timedelta
        self.t_late = self.task(self.demand_a, "Revisar", self.ana, TODAY - d(days=2))
        self.t_today = self.task(self.demand_a, "Cotar", self.ana, TODAY, "Em andamento")
        self.t_open = self.task(self.demand_a, "Enviar", self.ana)
        self.t_done = self.task(self.demand_a, "Fechada", self.ana, TODAY - d(days=5), "Concluído")
        self.t_bruno = self.task(self.demand_a, "Do Bruno", self.bruno, TODAY)
        self.t_nobody = self.task(self.demand_a, "Sem pessoa")
        self.t_other_demand = self.task(self.demand_b, "Na outra demanda", self.ana, TODAY + d(days=3))

    def test_only_items_where_the_person_is_responsible_in_any_demand(self):
        rows = self.query(self.ana).rows()
        self.assertEqual(
            sorted(self.names(rows)), sorted(["Revisar", "Cotar", "Enviar", "Fechada", "Na outra demanda"])
        )
        self.assertEqual({row.board_url for row in rows}, {
            reverse("board-detail", args=[self.demand_a.task_board.pk]), reverse("board-detail", args=[self.demand_b.task_board.pk]),
        })

    def test_an_inactive_person_column_does_not_count(self):
        board, cols, _ = self.columns(self.demand_a)
        BoardColumn.objects.filter(pk=cols[BoardColumn.Type.PERSON].pk).update(is_active=False)
        self.assertEqual(self.names(self.query(self.ana).rows()), ["Na outra demanda"])

    def test_cancelled_and_draft_demands_are_left_out_and_blocked_is_kept(self):
        Activity.objects.filter(pk=self.demand_b.pk).update(status="CANCELADA")
        self.assertNotIn("Na outra demanda", self.names(self.query(self.ana).rows()))
        Activity.objects.filter(pk=self.demand_b.pk).update(status="BLOQUEADA")
        self.assertIn("Na outra demanda", self.names(self.query(self.ana).rows()))
        Activity.objects.filter(pk=self.demand_b.pk).update(status="RASCUNHO")
        self.assertNotIn("Na outra demanda", self.names(self.query(self.ana).rows()))

    def test_other_organizations_never_show_up(self):
        outra = self.activity("Alheia", self.alheio, org=self.other_org)
        self.task(outra, "Segredo", self.alheio)
        self.assertEqual(self.query(self.alheio).rows(), [])  # a consulta de quem é da organização A não enxerga
        self.assertNotIn("Segredo", self.names(self.query(self.ana).rows()))
        self.assertNotIn("Segredo", self.names(self.query(self.ana, pessoa="todas").rows()))

    def test_state_is_derived_from_the_status_label(self):
        states = {row.name: row.state for row in self.query(self.ana).rows()}
        self.assertEqual(states["Revisar"], TODO)  # etiqueta padrão ("Não iniciado")
        self.assertEqual(states["Cotar"], DOING)
        self.assertEqual(states["Fechada"], DONE)

    def test_overdue_and_due_today_use_the_local_date_and_ignore_finished_work(self):
        by_name = {row.name: row for row in self.query(self.ana).rows()}
        self.assertTrue(by_name["Revisar"].overdue and not by_name["Revisar"].due_today)
        self.assertTrue(by_name["Cotar"].due_today and not by_name["Cotar"].overdue)
        self.assertFalse(by_name["Fechada"].overdue)  # concluída com prazo vencido não é atraso
        self.assertFalse(by_name["Enviar"].overdue or by_name["Enviar"].due_today)  # sem prazo: nada inventado
        self.assertIsNone(by_name["Enviar"].due)

    def test_summary_counts_the_base_scope(self):
        summary = self.query(self.ana).summary()
        self.assertEqual((summary["overdue"], summary["due_today"], summary["doing"], summary["total"]), (1, 1, 1, 4))
        # a busca não muda os cards
        self.assertEqual(self.query(self.ana, q="zzz").summary()["overdue"], 1)

    def test_mentions_card_counts_only_unread_mentions_of_the_person(self):
        make = lambda **kw: Notification.objects.create(recipient=self.ana, activity=self.demand_a, title="x", message="x", **kw)
        make(event_type=Notification.EventType.MENTIONED)
        make(event_type=Notification.EventType.MENTIONED, is_read=True)
        make(event_type=Notification.EventType.OWNER_CHANGED)
        Notification.objects.create(recipient=self.bruno, activity=self.demand_a, title="x", message="x", event_type=Notification.EventType.MENTIONED)
        self.assertEqual(self.query(self.ana).summary()["mentions"], 1)


class FilterTests(ScopeTests):
    def test_list_sorts_by_deadline_with_undated_last_and_hides_finished_by_default(self):
        names = self.names(self.query(self.ana).list_rows())
        self.assertEqual(names, ["Revisar", "Cotar", "Na outra demanda", "Enviar"])
        self.assertEqual(self.names(self.query(self.ana, status="done").list_rows()), ["Fechada"])

    def test_search_covers_task_demand_client_and_site(self):
        self.assertEqual(self.names(self.query(self.ana, q="revisar").list_rows()), ["Revisar"])
        self.assertEqual(sorted(self.names(self.query(self.ana, q="orçamento b").list_rows())), ["Na outra demanda"])
        self.assertEqual(self.query(self.ana, q="inexistente").list_rows(), [])

    def test_deadline_and_state_filters(self):
        self.assertEqual(self.names(self.query(self.ana, prazo="overdue").list_rows()), ["Revisar"])
        self.assertEqual(self.names(self.query(self.ana, prazo="today").list_rows()), ["Cotar"])
        self.assertEqual(self.names(self.query(self.ana, prazo="week").list_rows()), ["Cotar", "Na outra demanda"])
        self.assertEqual(self.names(self.query(self.ana, prazo="none").list_rows()), ["Enviar"])
        self.assertEqual(self.names(self.query(self.ana, status="doing").list_rows()), ["Cotar"])
        self.assertEqual(self.query(self.ana, status="lixo", prazo="lixo").filters()["status"], "")

    def test_the_person_filter_needs_authorization_in_the_backend(self):
        # sem permissão de ver quadros além dos próprios: o parâmetro é ignorado e vale o próprio escopo
        self.assertFalse(self.query(self.leitor).can_filter_people)
        self.assertEqual(self.query(self.leitor, pessoa=str(self.ana.pk)).rows(), [])
        self.assertEqual(self.query(self.leitor, pessoa="todas").rows(), [])
        # quem pode ver os quadros enxerga as de outra pessoa e de todas
        manager = self.query(self.gestor, pessoa=str(self.ana.pk))
        self.assertTrue(manager.can_filter_people)
        self.assertIn("Revisar", self.names(manager.rows()))
        self.assertNotIn("Do Bruno", self.names(manager.rows()))
        self.assertIn("Do Bruno", self.names(self.query(self.gestor, pessoa="todas").rows()))
        self.assertEqual(self.query(self.gestor).rows(), [])  # sem pessoa: o próprio escopo (ele não tem tarefas)

    def test_someone_who_cannot_see_the_other_board_never_gets_its_items(self):
        # `ana` participa só das demandas A e B; um usuário comum com "pessoa=todas" não passa do próprio escopo
        outsider = make_user("fora", self.org, [catalog.ATIVIDADE_VISUALIZAR_TODAS])
        rows = self.query(outsider, pessoa="todas").rows()
        self.assertEqual(rows, [])

    def test_kanban_groups_by_derived_state(self):
        columns = {column["key"]: column for column in self.query(self.ana).kanban_columns()}
        self.assertEqual(self.names(columns[TODO]["items"]), ["Revisar", "Na outra demanda", "Enviar"])
        self.assertEqual(self.names(columns[DOING]["items"]), ["Cotar"])
        self.assertEqual(self.names(columns[DONE]["items"]), ["Fechada"])
        self.assertEqual(columns[TODO]["count"], 3)

    def test_week_places_items_on_their_day_and_counts_undated(self):
        week = self.query(self.ana, semana="2026-10-07").week()
        self.assertEqual(week["week_start"], datetime.date(2026, 10, 5))
        self.assertEqual(week["week_end"], datetime.date(2026, 10, 11))
        days = {day["date"]: self.names(day["items"]) for day in week["week_days"]}
        self.assertEqual(days[datetime.date(2026, 10, 5)], ["Revisar"])  # TODAY-2
        self.assertEqual(days[datetime.date(2026, 10, 7)], ["Cotar"])
        self.assertEqual(days[datetime.date(2026, 10, 10)], ["Na outra demanda"])
        self.assertEqual(week["week_undated"], 1)  # "Enviar" não entra no grid; nenhuma data é inventada
        self.assertEqual((week["week_previous"], week["week_next"]), ("2026-09-28", "2026-10-12"))

    def test_parse_week_falls_back_to_this_week(self):
        self.assertEqual(parse_week("2026-10-07"), datetime.date(2026, 10, 5))
        self.assertEqual(parse_week("lixo", today=TODAY), datetime.date(2026, 10, 5))
        self.assertEqual(parse_week("", today=TODAY), datetime.date(2026, 10, 5))


class ViewTests(TaskCenterBase):
    def setUp(self):
        super().setUp()
        today = timezone.localdate()
        self.task(self.demand_a, "Revisar documentação", self.ana, today - datetime.timedelta(days=2))
        self.task(self.demand_a, "Cotar materiais", self.ana, today, "Em andamento")
        self.task(self.demand_a, "Do Bruno", self.bruno)

    def get(self, name, user=None, **params):
        self.client.force_login(user or self.ana)
        return self.client.get(reverse(name), params)

    def test_the_three_views_render_without_choosing_a_demand(self):
        for name in ("task-list", "task-kanban", "task-calendar"):
            response = self.get(name)
            self.assertEqual(response.status_code, 200, name)
            self.assertNotContains(response, "Selecionar Demanda", msg_prefix=name)
            self.assertNotContains(response, "Selecione uma Demanda", msg_prefix=name)
            self.assertContains(response, "Revisar documentação" if name != "task-calendar" else "Cotar materiais")
            self.assertNotContains(response, "Do Bruno")
            self.assertEqual(response.context["nav_active"], "tasks")

    def test_each_item_opens_the_real_board_of_its_demand(self):
        response = self.get("task-list")
        url = reverse("board-detail", args=[self.demand_a.task_board.pk])
        self.assertContains(response, f'href="{url}"')
        self.assertContains(response, "Abrir quadro")
        self.assertEqual(self.demand_a.task_board.kind, Board.Kind.DEMAND)  # nunca um modelo

    def test_the_old_demand_address_redirects_to_the_demand_board(self):
        self.client.force_login(self.ana)
        response = self.client.get(reverse("task-list"), {"demanda": self.demand_a.pk})
        self.assertRedirects(response, reverse("board-detail", args=[self.demand_a.task_board.pk]), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("task-list"), {"demanda": 999999}).status_code, 404)
        self.assertEqual(self.client.get(reverse("task-list"), {"demanda": "abc"}).status_code, 404)
        self.client.force_login(self.alheio)
        self.assertEqual(self.client.get(reverse("task-list"), {"demanda": self.demand_a.pk}).status_code, 404)

    def test_there_is_no_demand_selector_and_the_summary_is_shown(self):
        html = self.get("task-list").content.decode()
        for text in ("Atrasadas", "Vencem hoje", "Em andamento", "Menções", "Lista", "Kanban", "Calendário"):
            self.assertIn(text, html)
        self.assertNotIn("Meu dia", html)
        self.assertNotIn("Concluídas hoje", html)

    def test_the_person_filter_is_only_offered_to_who_can_use_it(self):
        self.assertNotContains(self.get("task-list", user=self.ana), 'name="pessoa"')
        self.assertContains(self.get("task-list", user=self.gestor), 'name="pessoa"')

    def test_calendar_week_navigation_keeps_filters(self):
        response = self.get("task-calendar", semana="2026-09-28", q="cotar")
        self.assertContains(response, "28/09/2026")
        self.assertContains(response, "semana=2026-10-05")
        self.assertContains(response, "q=cotar")

    def test_empty_state_is_short(self):
        response = self.get("task-list", user=self.leitor)
        self.assertContains(response, "Nenhuma tarefa encontrada.")

    def test_number_of_queries_does_not_grow_with_the_items(self):
        def queries():
            self.client.force_login(self.ana)
            with CaptureQueriesContext(connection) as context:
                self.client.get(reverse("task-list"))
            return len(context)

        queries()  # aquece caches
        few = queries()
        for index in range(12):
            self.task(self.demand_a, f"Extra {index}", self.ana, timezone.localdate())
        self.assertEqual(queries(), few)

    def test_the_menu_badge_counts_open_items_of_the_person(self):
        self.assertEqual(open_task_count(self.ana), 2)
        self.assertEqual(open_task_count(self.leitor), 0)
        self.task(self.demand_a, "Concluída", self.ana, status="Concluído")
        self.assertEqual(open_task_count(self.ana), 2)


class AddTaskTests(TaskCenterBase):
    def post(self, user, board, body):
        self.client.force_login(user)
        return self.client.post(reverse("board-item-create", args=[board.pk]), json.dumps(body), content_type="application/json")

    def test_only_demands_where_the_person_can_create_items_are_offered(self):
        self.task(self.demand_b, "Dela", self.ana, user=self.bruno)  # ana passa a participar da demanda B
        offered = {entry["board_id"] for entry in self.query(self.ana).addable_boards()}
        self.assertEqual(offered, {self.demand_a.task_board.pk, self.demand_b.task_board.pk})
        self.assertEqual(self.query(self.leitor).addable_boards(), [])
        Activity.objects.filter(pk=self.demand_b.pk).update(status="CONCLUIDA")
        offered = {entry["board_id"] for entry in self.query(self.ana).addable_boards()}
        self.assertEqual(offered, {self.demand_a.task_board.pk})

    def test_payload_has_the_columns_and_status_options_to_fill(self):
        entry = next(e for e in self.query(self.ana).addable_boards() if e["board_id"] == self.demand_a.task_board.pk)
        board, cols, options = self.columns(self.demand_a)
        self.assertEqual(entry["person_column_id"], cols[BoardColumn.Type.PERSON].pk)
        self.assertEqual(entry["status_column_id"], cols[BoardColumn.Type.STATUS].pk)
        self.assertEqual(entry["status_options"], {
            TODO: options["Não iniciado"].pk, DOING: options["Em andamento"].pk, DONE: options["Concluído"].pk,
        })
        self.assertEqual(entry["group_id"], board.groups.filter(is_active=True).first().pk)

    def test_creating_through_the_board_endpoint_with_the_screens_body(self):
        board, cols, options = self.columns(self.demand_a)
        group = board.groups.filter(is_active=True).first()
        body = {"group_id": group.pk, "name": "Nova pelo painel", "initial": [
            {"column_id": cols[BoardColumn.Type.PERSON].pk, "value": self.ana.pk},
            {"column_id": cols[BoardColumn.Type.STATUS].pk, "value": options["Em andamento"].pk},
        ]}
        response = self.post(self.ana, board, body)
        self.assertEqual(response.status_code, 200, response.content)
        rows = {row.name: row for row in self.query(self.ana).rows()}
        self.assertEqual(rows["Nova pelo painel"].state, DOING)
        self.assertEqual(rows["Nova pelo painel"].person, self.ana)

    def test_who_cannot_create_items_is_refused_by_the_service(self):
        board = self.demand_a.task_board
        response = self.post(self.leitor, board, {"group_id": board.groups.first().pk, "name": "Invasão"})
        self.assertIn(response.status_code, (403, 404))
        self.assertFalse(board.items.filter(name="Invasão").exists())

    def test_the_page_offers_the_add_buttons_only_when_there_is_a_demand_to_add_to(self):
        self.client.force_login(self.ana)
        html = self.client.get(reverse("task-list")).content.decode()
        self.assertIn("data-task-add", html)
        self.assertIn('id="task-center-add"', html)
        self.client.force_login(self.leitor)
        self.assertNotIn("data-task-add", self.client.get(reverse("task-kanban")).content.decode())


class PreviewTests(TaskCenterBase):
    def test_preview_comes_from_the_real_board_and_is_limited(self):
        d = datetime.timedelta
        today = timezone.localdate()
        for index in range(7):
            self.task(self.demand_a, f"Tarefa {index}", self.ana, today + d(days=index))
        self.task(self.demand_a, "Feita", self.ana, status="Concluído")
        self.task(self.demand_a, "Andando", self.ana, status="Em andamento")
        preview = DemandBoardPreviewQuery.build(user=self.ana, activity=self.demand_a)
        self.assertEqual((preview["total"], preview["done"], preview["in_progress"], preview["todo"]), (9, 1, 1, 7))
        self.assertEqual(len(preview["rows"]), 5)
        self.assertEqual(preview["more"], 4)
        self.assertEqual(preview["rows"][0]["name"], "Tarefa 0")  # abertas primeiro, por prazo
        self.assertNotIn("Feita", [row["name"] for row in preview["rows"]])
        self.assertEqual(preview["board_url"], reverse("board-detail", args=[self.demand_a.task_board.pk]))

    def test_preview_never_mixes_boards(self):
        self.task(self.demand_a, "Só da A", self.ana)
        self.task(self.demand_b, "Só da B", self.bruno)
        names = [row["name"] for row in DemandBoardPreviewQuery.build(user=self.ana, activity=self.demand_a)["rows"]]
        self.assertEqual(names, ["Só da A"])

    def test_preview_counts_new_mentions_of_this_demand_only(self):
        Notification.objects.create(recipient=self.ana, activity=self.demand_a, title="x", message="x", event_type=Notification.EventType.MENTIONED)
        Notification.objects.create(recipient=self.ana, activity=self.demand_b, title="x", message="x", event_type=Notification.EventType.MENTIONED)
        self.assertEqual(DemandBoardPreviewQuery.build(user=self.ana, activity=self.demand_a)["unread_mentions"], 1)

    def test_a_demand_without_a_board_does_not_break(self):
        Board.objects.filter(activity=self.demand_a).delete()
        activity = Activity.objects.get(pk=self.demand_a.pk)
        self.assertIsNone(DemandBoardPreviewQuery.build(user=self.ana, activity=activity))
        self.client.force_login(self.ana)
        response = self.client.get(reverse("activity-detail", args=[activity.pk]))
        self.assertContains(response, "Nenhum quadro configurado para esta demanda.")

    def test_detail_page_shows_the_preview_and_progress_from_the_board(self):
        self.task(self.demand_a, "Feita 1", self.ana, status="Concluído")
        self.task(self.demand_a, "Feita 2", self.ana, status="Concluído")
        self.client.force_login(self.ana)
        response = self.client.get(reverse("activity-detail", args=[self.demand_a.pk]))
        self.assertContains(response, "task-preview")
        self.assertContains(response, "Feita 1")
        self.assertContains(response, "2 de 2 concluídas")
        self.assertTrue(response.context["is_ready_to_complete"])
        self.assertContains(response, reverse("board-detail", args=[self.demand_a.task_board.pk]))
        self.task(self.demand_a, "Aberta", self.ana)
        response = self.client.get(reverse("activity-detail", args=[self.demand_a.pk]))
        self.assertFalse(response.context["is_ready_to_complete"])
        self.assertContains(response, "2 de 3 concluídas")
