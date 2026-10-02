"""Telas e endpoints dos quadros: acesso, isolamento entre organizações, contratos JSON e leitura sem N+1."""

import json

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from acessos.context_processors import _NAV_BY_URL_NAME
from audit.models import AuditLog

from . import urls as board_urls
from .models import Board, BoardCell, BoardColumn, BoardGroup, BoardItem
from .services import BoardService, CellService, ColumnService, ItemService
from .testing import JSON, BoardTestCase

User = get_user_model()
T = BoardColumn.Type


class ViewTestCase(BoardTestCase):
    def api(self, name, args=(), data=None, user=None, raw=None):
        if user is not None:
            self.login(user)
        body = raw if raw is not None else json.dumps(data if data is not None else {})
        return self.client.post(reverse(name, args=list(args)), body, content_type=JSON)

    def detail(self, user=None, **params):
        if user is not None:
            self.login(user)
        return self.client.get(reverse("board-detail", args=[self.board.pk]), params)

    def row_names(self, response):
        return [item.name for group in response.context["groups"] for item in group.board_items]


class AccessTests(ViewTestCase):
    def test_login_is_required_everywhere(self):
        for name, args in (("board-list", []), ("board-detail", [self.board.pk]), ("board-history", [self.board.pk])):
            response = self.client.get(reverse(name, args=args))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn("login", response["Location"])
        response = self.client.post(reverse("board-rename", args=[self.board.pk]), "{}", content_type=JSON)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_user_without_organization_is_sent_to_the_profile(self):
        loner = User.objects.create_user("sozinho", password="x")
        self.login(loner)
        response = self.client.get(reverse("board-list"))
        self.assertRedirects(response, reverse("profile"), fetch_redirect_response=False)

    def test_list_needs_view_permission(self):
        self.login(self.sem_acesso)
        self.assertEqual(self.client.get(reverse("board-list")).status_code, 403)

    def test_list_only_shows_boards_of_the_own_organization(self):
        BoardService.create(user=self.estranho, organization=self.other_org, name="Quadro Alheio")
        self.login(self.viewer)
        response = self.client.get(reverse("board-list"))
        self.assertContains(response, "Orçamentos")
        self.assertNotContains(response, "Quadro Alheio")
        self.assertFalse(response.context["can_create"])
        self.assertNotContains(response, 'action="%s"' % reverse("board-create"))

    def test_deleted_boards_leave_the_list(self):
        board = BoardService.create(user=self.admin, organization=self.org, name="Velho")
        BoardService.soft_delete(user=self.admin, board=board)
        self.login(self.viewer)
        self.assertNotContains(self.client.get(reverse("board-list")), "Velho")
        self.assertEqual(self.client.get(reverse("board-detail", args=[board.pk])).status_code, 404)

    def test_detail_needs_view_permission(self):
        self.assertEqual(self.detail(self.sem_acesso).status_code, 403)

    def test_detail_of_another_organization_is_404(self):
        self.assertEqual(self.detail(self.estranho).status_code, 404)
        self.assertEqual(self.client.get(reverse("board-history", args=[self.board.pk])).status_code, 404)

    def test_viewer_sees_the_board_but_not_the_editing_controls(self):
        response = self.detail(self.viewer)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Arena Norte")
        self.assertNotContains(response, "data-column-add")
        self.assertNotContains(response, "data-item-add")
        self.assertNotContains(response, "data-group-add")
        self.assertNotContains(response, "data-board-delete")
        self.assertNotContains(response, "data-column-resize")
        self.assertNotContains(response, 'tabindex="0"')  # nenhuma célula editável
        self.assertContains(response, "readonly")  # título só leitura
        self.assertEqual(
            response.context["meta"]["permissions"],
            {"view": True, "edit": False, "delete": False, "manage_columns": False,
             "create_item": False, "edit_item": False, "delete_item": False},
        )

    def test_editor_fills_items_but_does_not_shape_the_board(self):
        response = self.detail(self.editor)
        self.assertContains(response, "data-item-add")
        self.assertContains(response, 'tabindex="0"')
        self.assertNotContains(response, "data-column-add")
        self.assertNotContains(response, "data-column-resize")
        self.assertNotContains(response, "data-item-menu")  # excluir item é outra permissão

    def test_admin_sees_every_control(self):
        response = self.detail(self.admin)
        for marker in ("data-column-add", "data-item-add", "data-group-add", "data-board-delete", "data-column-resize",
                       "data-item-menu", "data-group-menu", "data-item-grip"):
            self.assertContains(response, marker)

    def test_history_page(self):
        self.login(self.viewer)
        response = self.client.get(reverse("board-history", args=[self.board.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Orçamentos")
        self.assertGreater(len(response.context["page"].object_list), 0)
        self.assertEqual(self.client.get(reverse("board-history", args=[self.board.pk])).status_code, 200)
        self.login(self.sem_acesso)
        self.assertEqual(self.client.get(reverse("board-history", args=[self.board.pk])).status_code, 403)

    def test_history_is_paginated_and_ordered_newest_first(self):
        for index in range(60):
            CellService.set_value(user=self.admin, item=self.item1, column=self.col["texto"], raw_value=f"v{index}")
        self.login(self.viewer)
        response = self.client.get(reverse("board-history", args=[self.board.pk]))
        page = response.context["page"]
        self.assertEqual(page.paginator.per_page, 50)
        self.assertGreater(page.paginator.num_pages, 1)
        self.assertEqual(page.object_list[0].new_value, "v59")
        self.assertEqual(self.client.get(reverse("board-history", args=[self.board.pk]), {"page": 2}).status_code, 200)


class CreateBoardTests(ViewTestCase):
    def setor(self):
        """Todo quadro nasce dentro de um setor da organização."""
        from core.models import Sector

        return Sector.objects.get_or_create(organization=self.org, name="Comercial")[0]

    def test_create_blank_board(self):
        self.login(self.admin)
        response = self.client.post(reverse("board-create"), {"name": "Contratos", "sector_id": self.setor().pk})
        board = Board.objects.get(name="Contratos")
        self.assertRedirects(response, reverse("board-detail", args=[board.pk]), fetch_redirect_response=False)
        self.assertEqual(board.organization, self.org)
        self.assertEqual(board.groups.count(), 1)

    def test_create_from_the_template(self):
        self.login(self.admin)
        self.client.post(reverse("board-create"), {"name": "", "template": "orcamentos", "sector_id": self.setor().pk})
        board = Board.objects.exclude(pk=self.board.pk).get(name="Orçamentos")
        self.assertEqual(board.columns.count(), 9)

    def test_unknown_template_shows_a_message(self):
        self.login(self.admin)
        response = self.client.post(reverse("board-create"), {"name": "X", "template": "xyz", "sector_id": self.setor().pk}, follow=True)
        self.assertContains(response, "Modelo de quadro desconhecido")
        self.assertFalse(Board.objects.filter(name="X").exists())

    def test_needs_the_create_action(self):
        before = Board.objects.count()
        for user in (self.editor, self.viewer, self.sem_acesso):
            self.login(user)
            self.assertEqual(self.client.post(reverse("board-create"), {"name": "Nope", "sector_id": self.setor().pk}).status_code, 403)
        self.assertEqual(Board.objects.count(), before)

    def test_only_post(self):
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse("board-create")).status_code, 405)


class DetailContentTests(ViewTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for item, texto, numero, data, status in (
            (cls.item1, "banana", "30", "2025-12-01", cls.concluido.pk),
            (cls.item2, "Abacate", "5,5", "2025-01-15", cls.andamento.pk),
        ):
            for key, value in (("texto", texto), ("numero", numero), ("data", data), ("status", status)):
                CellService.set_value(user=cls.admin, item=item, column=cls.col[key], raw_value=value)
        CellService.set_value(user=cls.admin, item=cls.item1, column=cls.col["pessoa"], raw_value=cls.ana.pk)
        ColumnService.update_settings(user=cls.admin, column=cls.col["data"], settings={"is_deadline": True})

    def test_rows_columns_and_cells_are_rendered(self):
        response = self.detail(self.viewer)
        self.assertEqual([c.name for c in response.context["columns"]],
                         ["Texto", "Números", "Valor", "Data", "Pessoa", "Status", "Lista suspensa", "Confirmação"])
        self.assertContains(response, "banana")
        self.assertContains(response, "30,00")
        self.assertContains(response, "Em andamento")
        self.assertContains(response, "Ana Souza")
        self.assertContains(response, "2 tarefas")
        self.assertContains(response, "1 tarefa")
        self.assertContains(response, 'id="board-meta"')

    def test_overdue_deadline_is_flagged_with_text(self):
        response = self.detail(self.viewer)
        self.assertContains(response, "vencido")
        self.assertContains(response, "15/01/2025")

    def test_status_pill_has_readable_text_color(self):
        response = self.detail(self.viewer)
        self.assertContains(response, "background:#00C875;color:#FFFFFF")  # verde forte: texto branco
        self.assertContains(response, "background:#C4C4C4;color:#1F2937")  # cinza claro: texto escuro

    def test_hidden_columns_are_listed_but_not_drawn(self):
        ColumnService.set_visible(user=self.admin, column=self.col["check"], visible=False)
        response = self.detail(self.admin)
        self.assertEqual(len(response.context["columns"]), 7)
        self.assertContains(response, "Colunas ocultas (1)")
        self.assertContains(response, "data-column-show")
        self.assertNotContains(response, 'data-column-id="%d" data-type="CHECKBOX"' % self.col["check"].pk)

    def test_deleted_items_are_not_drawn(self):
        ItemService.soft_delete(user=self.admin, item=self.item2)
        self.assertNotIn("Condomínio Cotia", self.row_names(self.detail(self.viewer)))

    def test_sorting_through_the_url(self):
        numero = self.col["numero"].pk
        self.assertEqual(self.row_names(self.detail(self.viewer, sort=numero, dir="asc")),
                         ["Condomínio Cotia", "Arena Norte", "Hospital Vida"])
        response = self.detail(self.viewer, sort=numero, dir="desc")
        self.assertEqual(self.row_names(response), ["Arena Norte", "Condomínio Cotia", "Hospital Vida"])
        self.assertEqual(response.context["sort_column_id"], numero)
        self.assertContains(response, 'aria-sort="descending"')

    def test_invalid_sort_is_ignored(self):
        for value in ("abc", "999999", str(self.col["texto"].pk) + "x", ""):
            response = self.detail(self.viewer, sort=value)
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.context["sort_column_id"])

    def test_sort_by_a_column_of_another_board_is_ignored(self):
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro")
        column = ColumnService.create(user=self.admin, board=other, column_type=T.TEXT)
        self.assertIsNone(self.detail(self.viewer, sort=column.pk).context["sort_column_id"])

    def test_search_and_person_filter(self):
        self.assertEqual(self.row_names(self.detail(self.viewer, q="abacate")), ["Condomínio Cotia"])
        self.assertEqual(self.row_names(self.detail(self.viewer, q="Ana")), ["Arena Norte"])
        self.assertEqual(self.row_names(self.detail(self.viewer, pessoa=self.ana.pk)), ["Arena Norte"])
        self.assertEqual(self.row_names(self.detail(self.viewer, pessoa="x")), ["Arena Norte", "Condomínio Cotia", "Hospital Vida"])
        response = self.detail(self.viewer, q="nada")
        self.assertEqual(self.row_names(response), [])
        self.assertTrue(response.context["filtering"])

    def test_person_filter_only_lists_people_in_the_board(self):
        response = self.detail(self.viewer)
        self.assertEqual([p.username for p in response.context["people"]], ["ana"])

    def test_text_is_escaped(self):
        ItemService.rename(user=self.admin, item=self.item3, name="<script>alert(1)</script>")
        CellService.set_value(user=self.admin, item=self.item3, column=self.col["texto"], raw_value='"><img src=x onerror=alert(2)>')
        BoardService.update(user=self.admin, board=self.board, name="</script><b>Quadro")
        html = self.detail(self.viewer).content.decode()
        self.assertNotIn("<script>alert(1)", html)
        self.assertNotIn("<img src=x", html)
        self.assertNotIn("</script><b>Quadro", html)
        self.assertIn("&lt;script&gt;alert(1)", html)

    def test_meta_has_what_the_javascript_needs(self):
        meta = self.detail(self.admin).context["meta"]
        self.assertEqual(meta["board"]["id"], self.board.pk)
        self.assertEqual(meta["limits"], {"min_width": 96, "max_width": 640})
        self.assertEqual([t["value"] for t in meta["types"]],
                         ["STATUS", "DROPDOWN", "TEXT", "DATE", "PERSON", "NUMBER", "CURRENCY", "CHECKBOX"])
        status = next(c for c in meta["columns"] if c["type"] == "STATUS")
        self.assertEqual([o["label"] for o in status["options"]], ["Não iniciado", "Em andamento", "Concluído"])
        self.assertTrue(meta["urls"]["person_search"].startswith("/api/pessoas"))
        for key in ("column_rename", "item_move", "option_update", "group_reorder"):
            self.assertIn(str(meta["sentinels"]["id"]), meta["urls"][key])
        self.assertIn(str(meta["sentinels"]["column"]), meta["urls"]["cell_update"])

    def test_table_width_matches_the_columns(self):
        response = self.detail(self.viewer)
        self.assertEqual(response.context["table_width"], 280 + 64 + 160 * 8)
        self.assertContains(response, 'style="width:1624px"')


class QueryCountTests(ViewTestCase):
    def count(self):
        self.login(self.admin)
        self.client.get(reverse("board-detail", args=[self.board.pk]))  # aquece caches de sessão e de permissão
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("board-detail", args=[self.board.pk]))
        self.assertEqual(response.status_code, 200)
        return len(queries)

    def test_detail_does_not_grow_with_the_number_of_items(self):
        small = self.count()
        for index in range(12):
            item = ItemService.create(user=self.admin, board=self.board, group=self.group_a, name=f"Extra {index}")
            for key, value in (("texto", "x"), ("numero", "1"), ("pessoa", self.ana.pk), ("status", self.andamento.pk),
                               ("lista", self.opt_a.pk), ("data", "2025-10-01")):
                CellService.set_value(user=self.admin, item=item, column=self.col[key], raw_value=value)
        self.assertEqual(self.count(), small)


class JsonContractTests(ViewTestCase):
    def test_only_post_is_accepted(self):
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse("board-rename", args=[self.board.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("board-cell-update", args=[self.item1.pk, self.col["texto"].pk])).status_code, 405)

    def test_invalid_json_is_a_400(self):
        self.login(self.admin)
        for raw in ("{nope", "[1, 2]", '"texto"', "\xff"):
            response = self.api("board-rename", [self.board.pk], raw=raw)
            self.assertEqual(response.status_code, 400, raw)
            self.assertEqual(response.json(), {"ok": False, "error": "JSON inválido."})

    def test_empty_body_is_an_empty_object(self):
        self.login(self.admin)
        self.assertEqual(self.api("board-rename", [self.board.pk], raw="").status_code, 200)

    def test_csrf_is_enforced(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.admin)
        response = strict.post(reverse("board-rename", args=[self.board.pk]), json.dumps({"name": "X"}), content_type=JSON)
        self.assertEqual(response.status_code, 403)
        self.board.refresh_from_db()
        self.assertEqual(self.board.name, "Orçamentos")

    def test_permission_error_is_a_403_with_a_message(self):
        response = self.api("board-rename", [self.board.pk], {"name": "X"}, user=self.editor)
        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertTrue(body["error"])

    def test_business_error_is_a_400(self):
        response = self.api("board-column-rename", [self.col["texto"].pk], {"name": "  "}, user=self.admin)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Informe um nome.")
        self.assertFalse(response.json()["needs_confirmation"])

    # -- quadro -----------------------------------------------------------------------------------

    def test_rename_and_delete_board(self):
        response = self.api("board-rename", [self.board.pk], {"name": "  Novo   nome "}, user=self.admin)
        self.assertEqual(response.json(), {"ok": True, "name": "Novo nome", "description": ""})
        board = BoardService.create(user=self.admin, organization=self.org, name="Descartável")
        response = self.api("board-delete", [board.pk])
        self.assertEqual(response.json(), {"ok": True, "redirect_url": reverse("board-list")})
        board.refresh_from_db()
        self.assertFalse(board.is_active)

    # -- grupos -----------------------------------------------------------------------------------

    def test_group_endpoints(self):
        self.login(self.admin)
        created = self.api("board-group-create", [self.board.pk], {"name": "Concluídos", "color": "#A25DDC"}).json()
        self.assertTrue(created["ok"])
        group = BoardGroup.objects.get(pk=created["group"]["id"])
        self.assertEqual((group.name, group.color), ("Concluídos", "#A25DDC"))
        self.assertIn('data-group-id="%d"' % group.pk, created["group_html"])
        self.assertIn("0 tarefas", created["group_html"])

        updated = self.api("board-group-update", [group.pk], {"name": "Feitos", "color": "#00C875"}).json()
        self.assertEqual(updated["group"], {"id": group.pk, "name": "Feitos", "color": "#00C875"})

        moved = self.api("board-group-reorder", [group.pk], {"before_id": None, "after_id": self.group_a.pk}).json()
        self.assertTrue(moved["ok"])
        self.assertEqual(BoardGroup.objects.filter(board=self.board, is_active=True).order_by("position").first(), group)

        self.assertTrue(self.api("board-group-delete", [group.pk]).json()["ok"])
        response = self.api("board-group-delete", [self.group_a.pk])
        self.assertEqual(response.status_code, 400)
        self.assertIn("itens", response.json()["error"])

    def test_group_bad_color_is_a_400(self):
        response = self.api("board-group-update", [self.group_a.pk], {"color": "red"}, user=self.admin)
        self.assertEqual(response.status_code, 400)

    # -- colunas ----------------------------------------------------------------------------------

    def test_column_create_returns_header_and_one_cell_per_item(self):
        response = self.api("board-column-create", [self.board.pk], {"type": "NUMBER"}, user=self.admin)
        data = response.json()
        self.assertTrue(data["ok"])
        column = BoardColumn.objects.get(pk=data["column"]["id"])
        self.assertEqual(column.type, "NUMBER")
        self.assertIn("data-column-th", data["header_html"])
        self.assertIn(column.name, data["header_html"])
        self.assertEqual(set(data["cells"]), {str(self.item1.pk), str(self.item2.pk), str(self.item3.pk)})
        for html in data["cells"].values():
            self.assertTrue(html.lstrip().startswith("<td"))
            self.assertIn('data-column-id="%d"' % column.pk, html)
        self.assertIsNone(data["after_column_id"])

    def test_column_create_after_another(self):
        first = self.col["texto"]
        data = self.api("board-column-create", [self.board.pk], {"type": "TEXT", "after_column_id": first.pk}, user=self.admin).json()
        self.assertEqual(data["after_column_id"], first.pk)
        new = BoardColumn.objects.get(pk=data["column"]["id"])
        second = BoardColumn.objects.filter(board=self.board, position__gt=first.position).exclude(pk=new.pk).order_by("position").first()
        self.assertLess(first.position, new.position)
        self.assertLess(new.position, second.position)

    def test_column_create_refuses_bad_types_and_foreign_anchors(self):
        self.login(self.admin)
        self.assertEqual(self.api("board-column-create", [self.board.pk], {"type": "FILE"}).status_code, 400)
        self.assertEqual(self.api("board-column-create", [self.board.pk], {}).status_code, 400)
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro")
        foreign = ColumnService.create(user=self.admin, board=other, column_type=T.TEXT)
        self.assertEqual(self.api("board-column-create", [self.board.pk], {"type": "TEXT", "after_column_id": foreign.pk}).status_code, 404)

    def test_column_rename_resize_reorder(self):
        column = self.col["texto"]
        self.login(self.admin)
        data = self.api("board-column-rename", [column.pk], {"name": "Cliente"}).json()
        self.assertEqual(data["column"]["name"], "Cliente")
        self.assertIn("Cliente", data["header_html"])
        self.assertNotIn("cells", data)

        self.assertEqual(self.api("board-column-resize", [column.pk], {"width": 40}).json()["width"], 96)
        self.assertEqual(self.api("board-column-resize", [column.pk], {"width": 900}).json()["width"], 640)
        self.assertEqual(self.api("board-column-resize", [column.pk], {"width": "x"}).status_code, 400)

        last = self.col["check"]
        data = self.api("board-column-reorder", [last.pk], {"before_id": None, "after_id": column.pk}).json()
        self.assertTrue(data["ok"])
        self.assertEqual(BoardColumn.objects.filter(board=self.board, is_active=True).order_by("position").first(), last)

    def test_column_settings_returns_the_new_meta_and_cells(self):
        column = self.col["numero"]
        data = self.api("board-column-settings", [column.pk],
                        {"description": "Quantidade", "is_required": False, "settings": {"decimal_places": 0, "unit": "un"}},
                        user=self.admin).json()
        self.assertEqual(data["column"]["settings"]["unit"], "un")
        self.assertEqual(data["column"]["description"], "Quantidade")
        self.assertIn("cells", data)
        bad = self.api("board-column-settings", [column.pk], {"settings": {"decimal_places": 9}})
        self.assertEqual(bad.status_code, 400)

    def test_hide_duplicate_delete(self):
        self.login(self.admin)
        column = self.col["check"]
        self.assertEqual(self.api("board-column-hide", [column.pk], {"visible": False}).json()["visible"], False)
        self.assertEqual(self.api("board-column-hide", [column.pk], {"visible": True}).json()["visible"], True)
        copy = self.api("board-column-duplicate", [column.pk]).json()
        self.assertEqual(copy["after_column_id"], column.pk)
        self.assertEqual(copy["column"]["name"], "Confirmação (cópia)")
        self.assertTrue(self.api("board-column-delete", [copy["column"]["id"]]).json()["ok"])
        self.assertFalse(BoardColumn.objects.get(pk=copy["column"]["id"]).is_active)

    def test_type_change_preview_then_confirmation(self):
        self.login(self.admin)
        column = self.col["texto"]
        CellService.set_value(user=self.admin, item=self.item1, column=column, raw_value="dez")
        preview = self.api("board-column-type", [column.pk], {"type": "NUMBER", "preview": True}).json()
        self.assertEqual(preview["plan"], {"mode": "parsed", "filled": 1, "lost": 1})
        column.refresh_from_db()
        self.assertEqual(column.type, "TEXT")

        refused = self.api("board-column-type", [column.pk], {"type": "NUMBER"})
        self.assertEqual(refused.status_code, 409)
        self.assertTrue(refused.json()["needs_confirmation"])
        column.refresh_from_db()
        self.assertEqual(column.type, "TEXT")

        done = self.api("board-column-type", [column.pk], {"type": "NUMBER", "confirm": True}).json()
        self.assertEqual(done["column"]["type"], "NUMBER")
        self.assertIn("cells", done)

    def test_type_change_safe_needs_no_confirmation(self):
        data = self.api("board-column-type", [self.col["numero"].pk], {"type": "CURRENCY"}, user=self.admin).json()
        self.assertEqual(data["column"]["type"], "CURRENCY")

    def test_fragment_redraws_a_column(self):
        data = self.api("board-column-fragment", [self.col["status"].pk], {}, user=self.viewer).json()
        self.assertEqual(len(data["cells"]), 3)
        self.assertEqual([o["label"] for o in data["column"]["options"]], ["Não iniciado", "Em andamento", "Concluído"])
        self.assertEqual(self.api("board-column-fragment", [self.col["status"].pk], {}, user=self.sem_acesso).status_code, 403)

    def test_manage_columns_is_required(self):
        self.login(self.editor)
        for name, data in (("board-column-rename", {"name": "X"}), ("board-column-resize", {"width": 200}),
                           ("board-column-reorder", {}), ("board-column-settings", {}), ("board-column-hide", {"visible": False}),
                           ("board-column-duplicate", {}), ("board-column-type", {"type": "NUMBER"}), ("board-column-delete", {})):
            self.assertEqual(self.api(name, [self.col["texto"].pk], data).status_code, 403, name)
        self.assertEqual(self.api("board-column-create", [self.board.pk], {"type": "TEXT"}).status_code, 403)
        # sem nada para gravar também é recusado: a resposta traz o desenho da coluna e a prévia traz contagens
        self.assertEqual(self.api("board-column-settings", [self.col["texto"].pk], {}).status_code, 403)
        self.assertEqual(self.api("board-column-type", [self.col["texto"].pk], {"type": "NUMBER", "preview": True}).status_code, 403)
        self.login(self.sem_acesso)
        self.assertEqual(self.api("board-column-settings", [self.col["texto"].pk], {}).status_code, 403)
        self.assertEqual(self.api("board-column-type", [self.col["texto"].pk], {"type": "NUMBER", "preview": True}).status_code, 403)

    # -- etiquetas --------------------------------------------------------------------------------

    def test_option_endpoints(self):
        self.login(self.admin)
        created = self.api("board-option-create", [self.col["status"].pk], {"label": "Em revisão", "color": "#FDAB3D"}).json()
        option = created["option"]
        self.assertEqual((option["label"], option["color"]), ("Em revisão", "#FDAB3D"))

        updated = self.api("board-option-update", [option["id"]], {"label": "Revisando", "is_done": True}).json()["option"]
        self.assertEqual((updated["label"], updated["is_done"]), ("Revisando", True))
        self.assertEqual(self.api("board-option-update", [option["id"]], {"label": "Concluído"}).status_code, 400)

        self.assertTrue(self.api("board-option-reorder", [option["id"]], {"before_id": None, "after_id": self.novo.pk}).json()["ok"])
        self.set_cell(self.item1, "status", option["id"])
        self.assertEqual(self.api("board-option-delete", [option["id"]]).json(), {"ok": True, "cleared_cells": 1})
        self.assertEqual(self.api("board-option-create", [self.col["texto"].pk], {"label": "Nada"}).status_code, 400)

    # -- itens ------------------------------------------------------------------------------------

    def test_item_create_returns_the_row(self):
        data = self.api("board-item-create", [self.board.pk], {"group_id": self.group_b.pk, "name": "Novo"}, user=self.editor).json()
        self.assertEqual(data["item"]["name"], "Novo")
        self.assertEqual(data["item"]["group_id"], self.group_b.pk)
        self.assertIn('data-item-row', data["row_html"])
        self.assertIn('data-item-id="%d"' % data["item"]["id"], data["row_html"])
        self.assertEqual(data["row_html"].count("data-cell"), 8)
        self.assertIn("Não iniciado", data["row_html"])  # etiqueta padrão já preenchida

    def test_item_create_with_a_group_of_another_board_is_404(self):
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro")
        response = self.api("board-item-create", [self.board.pk], {"group_id": other.groups.get().pk}, user=self.admin)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.api("board-item-create", [self.board.pk], {}).status_code, 404)

    def test_item_rename_move_delete(self):
        self.login(self.admin)
        self.assertEqual(self.api("board-item-rename", [self.item1.pk], {"name": "  Arena   Sul "}).json()["name"], "Arena Sul")
        moved = self.api("board-item-move", [self.item1.pk], {"group_id": self.group_b.pk, "before_id": None, "after_id": self.item3.pk}).json()
        self.assertEqual(moved["group_id"], self.group_b.pk)
        order = list(BoardItem.objects.filter(group=self.group_b, is_active=True).order_by("position").values_list("pk", flat=True))
        self.assertEqual(order, [self.item1.pk, self.item3.pk])
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro")
        self.assertEqual(self.api("board-item-move", [self.item1.pk], {"group_id": other.groups.get().pk}).status_code, 404)
        self.assertTrue(self.api("board-item-delete", [self.item2.pk]).json()["ok"])
        self.assertFalse(BoardItem.objects.get(pk=self.item2.pk).is_active)

    def test_item_delete_needs_its_own_permission(self):
        self.assertEqual(self.api("board-item-delete", [self.item1.pk], user=self.editor).status_code, 403)
        self.assertEqual(self.api("board-item-move", [self.item1.pk], {"group_id": self.group_b.pk}, user=self.viewer).status_code, 403)

    # -- células ----------------------------------------------------------------------------------

    def test_cell_update_returns_the_td_and_the_text(self):
        data = self.api("board-cell-update", [self.item1.pk, self.col["moeda"].pk], {"value": "2500000"}, user=self.editor).json()
        self.assertEqual(data["display"], "R$ 2.500.000,00")
        self.assertTrue(data["cell_html"].lstrip().startswith("<td"))
        self.assertIn("R$ 2.500.000,00", data["cell_html"])
        self.assertIn('data-value="2500000"', data["cell_html"])

    def test_cell_update_status_and_person(self):
        self.login(self.editor)
        data = self.api("board-cell-update", [self.item1.pk, self.col["status"].pk], {"value": self.andamento.pk}).json()
        self.assertIn("Em andamento", data["cell_html"])
        self.assertIn('data-value="%d"' % self.andamento.pk, data["cell_html"])
        data = self.api("board-cell-update", [self.item1.pk, self.col["pessoa"].pk], {"value": self.ana.pk}).json()
        self.assertIn("Ana Souza", data["cell_html"])
        self.assertEqual(data["display"], "Ana Souza")

    def test_cell_update_clears(self):
        self.set_cell(self.item1, "texto", "algo")
        data = self.api("board-cell-update", [self.item1.pk, self.col["texto"].pk], {"value": ""}, user=self.editor).json()
        self.assertEqual(data["display"], "")

    def test_cell_update_errors(self):
        self.login(self.editor)
        response = self.api("board-cell-update", [self.item1.pk, self.col["numero"].pk], {"value": "abc"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Informe um número válido.")
        self.assertEqual(self.api("board-cell-update", [self.item1.pk, self.col["pessoa"].pk], {"value": self.foreign_person.pk}).status_code, 400)
        self.assertEqual(self.api("board-cell-update", [self.item1.pk, self.col["status"].pk], {"value": self.opt_a.pk}).status_code, 400)
        self.assertEqual(self.api("board-cell-update", [self.item1.pk, self.col["data"].pk], {"value": "2025-13-01"}).status_code, 400)
        self.assertEqual(self.api("board-cell-update", [self.item1.pk, self.col["numero"].pk], {}).status_code, 200)  # sem valor = limpa

    def test_cell_update_with_a_column_of_another_board_is_404(self):
        other = BoardService.create(user=self.admin, organization=self.org, name="Outro")
        column = ColumnService.create(user=self.admin, board=other, column_type=T.TEXT)
        self.assertEqual(self.api("board-cell-update", [self.item1.pk, column.pk], {"value": "x"}, user=self.admin).status_code, 404)

    def test_viewer_cannot_edit_cells(self):
        response = self.api("board-cell-update", [self.item1.pk, self.col["texto"].pk], {"value": "x"}, user=self.viewer)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(BoardCell.objects.filter(item=self.item1, column=self.col["texto"]).exists())

    def test_every_write_leaves_a_trace_in_the_board_history(self):
        self.api("board-cell-update", [self.item1.pk, self.col["texto"].pk], {"value": "Convivy"}, user=self.editor)
        self.api("board-column-rename", [self.col["texto"].pk], {"name": "Cliente"}, user=self.admin)
        logs = AuditLog.objects.filter(metadata__board_id=self.board.pk, action__in=[
            AuditLog.Action.BOARD_CELL_UPDATED, AuditLog.Action.BOARD_COLUMN_UPDATED])
        self.assertEqual({log.user_id for log in logs[:]} & {self.editor.pk, self.admin.pk}, {self.editor.pk, self.admin.pk})


class TenantIsolationTests(ViewTestCase):
    """Quem é de outra organização recebe 404 em tudo, sem nada mudar (o endereço não revela que o quadro existe)."""

    def cases(self):
        c, o = self.col, self.novo
        return [
            ("board-rename", [self.board.pk], {"name": "Hackeado"}),
            ("board-delete", [self.board.pk], {}),
            ("board-group-create", [self.board.pk], {"name": "X"}),
            ("board-group-update", [self.group_a.pk], {"name": "X"}),
            ("board-group-reorder", [self.group_a.pk], {}),
            ("board-group-delete", [self.group_b.pk], {}),
            ("board-column-create", [self.board.pk], {"type": "TEXT"}),
            ("board-column-rename", [c["texto"].pk], {"name": "X"}),
            ("board-column-resize", [c["texto"].pk], {"width": 300}),
            ("board-column-reorder", [c["texto"].pk], {}),
            ("board-column-settings", [c["texto"].pk], {"description": "X"}),
            ("board-column-hide", [c["texto"].pk], {"visible": False}),
            ("board-column-duplicate", [c["texto"].pk], {}),
            ("board-column-type", [c["texto"].pk], {"type": "NUMBER", "confirm": True}),
            ("board-column-delete", [c["texto"].pk], {}),
            ("board-column-fragment", [c["texto"].pk], {}),
            ("board-option-create", [c["status"].pk], {"label": "X"}),
            ("board-option-update", [o.pk], {"label": "X"}),
            ("board-option-reorder", [o.pk], {}),
            ("board-option-delete", [o.pk], {}),
            ("board-item-create", [self.board.pk], {"group_id": self.group_a.pk}),
            ("board-item-rename", [self.item1.pk], {"name": "X"}),
            ("board-item-move", [self.item1.pk], {"group_id": self.group_b.pk}),
            ("board-item-delete", [self.item1.pk], {}),
            ("board-cell-update", [self.item1.pk, c["texto"].pk], {"value": "X"}),
        ]

    def test_every_write_endpoint_is_404_for_another_organization(self):
        self.login(self.estranho)
        for name, args, data in self.cases():
            response = self.api(name, args, data)
            self.assertEqual(response.status_code, 404, name)

    def test_nothing_changed_after_the_attempts(self):
        self.login(self.estranho)
        for name, args, data in self.cases():
            self.api(name, args, data)
        self.board.refresh_from_db()
        self.assertEqual(self.board.name, "Orçamentos")
        self.assertTrue(self.board.is_active)
        self.assertEqual(BoardGroup.objects.filter(board=self.board, is_active=True).count(), 2)
        self.assertEqual(BoardColumn.objects.filter(board=self.board, is_active=True).count(), 8)
        self.assertEqual(BoardItem.objects.filter(board=self.board, is_active=True).count(), 3)
        self.assertFalse(BoardCell.objects.filter(value_text="X").exists())

    def test_the_foreign_organization_cannot_even_see_the_pages(self):
        self.login(self.estranho)
        self.assertEqual(self.client.get(reverse("board-detail", args=[self.board.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("board-history", args=[self.board.pk])).status_code, 404)

    def test_each_organization_only_lists_its_own_boards(self):
        BoardService.create(user=self.estranho, organization=self.other_org, name="Dos outros")
        self.login(self.estranho)
        response = self.client.get(reverse("board-list"))
        self.assertContains(response, "Dos outros")
        self.assertNotContains(response, reverse("board-detail", args=[self.board.pk]))


class MenuTests(ViewTestCase):
    def test_every_board_route_is_mapped_to_the_menu_item(self):
        # só as rotas do motor de quadros (`board-*`): as `workboard-*` são das lentes sobre Demandas e Tarefas
        names = {pattern.name for pattern in board_urls.urlpatterns if pattern.name.startswith("board-")}
        self.assertEqual(len(names), 36)
        for name in names:
            self.assertEqual(_NAV_BY_URL_NAME.get(name), "boards", name)

    def test_menu_item_only_for_who_can_see(self):
        response = self.detail(self.viewer)
        self.assertTrue(response.context["lps_nav"]["boards"])
        self.assertEqual(response.context["nav_active"], "boards")
        self.assertContains(response, 'data-tooltip="Quadros"')
        self.login(self.sem_acesso)
        home = self.client.get(reverse("home"))
        self.assertFalse(home.context["lps_nav"]["boards"])
        self.assertNotContains(home, 'data-tooltip="Quadros"')

    def test_menu_item_does_not_show_for_sector_scoped_grants(self):
        from acessos import catalog
        from acessos.testing import grant_actions
        from activities.testing import make_user
        from core.models import Sector

        sector = Sector.objects.create(organization=self.org, name="Comercial")
        gestor = make_user("gestor", self.org)
        grant_actions(gestor, [catalog.QUADRO_VISUALIZAR], organization=self.org, sector=sector)
        self.login(gestor)
        self.assertFalse(self.client.get(reverse("home")).context["lps_nav"]["boards"])
        self.assertEqual(self.client.get(reverse("board-list")).status_code, 403)

    def test_board_pages_load_their_own_assets(self):
        response = self.detail(self.viewer)
        self.assertContains(response, "js/boards.js")
        self.assertContains(response, "css/boards.css")


class ExampleDataTests(ViewTestCase):
    def test_orcamentos_template_renders_for_a_viewer(self):
        from .starter_templates import create_board_from_template

        board = create_board_from_template(user=self.admin, organization=self.org, key="orcamentos", with_examples=True)
        self.login(self.viewer)
        response = self.client.get(reverse("board-detail", args=[board.pk]))
        self.assertEqual(response.status_code, 200)
        for text in ("Arena Center Norte", "Hospital Vida Plena", "Proposta enviada", "R$ 2.500.000,00", "Probabilidade",
                     "Propostas enviadas", "Nome da Tarefa"):
            self.assertContains(response, text)
        self.assertContains(response, "40 %")
        self.assertContains(response, 'placeholder="Buscar neste quadro…"')
