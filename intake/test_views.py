import json

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from acessos.context_processors import _NAV_BY_URL_NAME
from acessos.testing import grant_actions
from activities.models import Activity
from activities.testing import make_user

from . import urls as intake_urls
from .models import IntakeEvent, IntakeItem
from .services import IntakeService
from .testing import AJAX, EMAIL_TEXT, IntakeTestCase

User = get_user_model()


class ViewTestCase(IntakeTestCase):
    def login(self, user):
        self.client.force_login(user)

    def post_json(self, url, data=None, user=None):
        if user:
            self.login(user)
        response = self.client.post(url, data or {}, **AJAX)
        return response, json.loads(response.content)

    def novo(self, **overrides):
        return self.new_item(suggested_client=self.convivy, suggested_site=self.aurora, **overrides)


class AccessTests(ViewTestCase):
    def test_anonymous_users_are_sent_to_login(self):
        item = self.novo()
        for name, args in (("intake-list", []), ("intake-capture", []), ("intake-detail", [item.pk]),
                           ("intake-edit", [item.pk]), ("intake-convert", [item.pk]), ("intake-ignore", [item.pk])):
            response = self.client.get(reverse(name, args=args))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn("/accounts/login/", response["Location"], name)

    def test_user_without_organization_is_sent_to_the_profile(self):
        orphan = User.objects.create_user("orfao", password="x")
        self.login(orphan)
        response = self.client.get(reverse("intake-list"))
        self.assertRedirects(response, reverse("profile"), fetch_redirect_response=False)

    def test_user_without_permission_gets_403_everywhere(self):
        item = self.novo()
        self.login(self.sem_acesso)
        for name, args in (("intake-list", []), ("intake-capture", []), ("intake-detail", [item.pk]),
                           ("intake-edit", [item.pk]), ("intake-convert", [item.pk]), ("intake-ignore", [item.pk])):
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403, name)
        self.assertEqual(self.client.post(reverse("intake-restore", args=[item.pk])).status_code, 403)

    def test_registrador_can_register_but_not_see_the_inbox(self):
        item = self.novo()
        self.login(self.registrador)
        self.assertEqual(self.client.get(reverse("intake-capture")).status_code, 200)
        self.assertEqual(self.client.get(reverse("intake-list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("intake-detail", args=[item.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("intake-convert", args=[item.pk])).status_code, 403)

    def test_other_organization_gets_404_on_every_route(self):
        item = self.novo()
        self.login(self.estranho)
        for name in ("intake-detail", "intake-edit", "intake-convert", "intake-ignore"):
            self.assertEqual(self.client.get(reverse(name, args=[item.pk])).status_code, 404, name)
        self.assertEqual(self.client.post(reverse("intake-restore", args=[item.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("intake-ignore", args=[item.pk])).status_code, 404)

    def test_sector_manager_only_reaches_items_of_the_sector(self):
        compras = self.novo(suggested_sector=self.compras, subject="Compras")
        comercial = self.novo(suggested_sector=self.comercial, subject="Comercial")
        sem_setor = self.novo(subject="Sem setor")
        self.login(self.gestor_compras)
        self.assertEqual(self.client.get(reverse("intake-detail", args=[compras.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("intake-detail", args=[comercial.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("intake-detail", args=[sem_setor.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("intake-convert", args=[comercial.pk])).status_code, 403)


class ListTests(ViewTestCase):
    def test_lists_new_items_with_what_was_understood(self):
        item = self.novo(suggested_title="Orçamento do gerador")
        self.login(self.triador)
        response = self.client.get(reverse("intake-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chegou uma solicitação de Convivy")
        self.assertContains(response, "Cliente identificado")
        self.assertContains(response, "Residencial Aurora")
        self.assertContains(response, f'id="intake-item-{item.pk}"')
        self.assertContains(response, "Criar demanda")
        self.assertContains(response, "Confiança")

    def test_tabs_show_counts_and_each_status(self):
        self.novo(subject="Nova")
        converted = self.novo(subject="Convertida", status=IntakeItem.Status.CONVERTIDO)
        self.novo(subject="Ignorada", status=IntakeItem.Status.IGNORADO, resolution_note="não é conosco")
        self.login(self.triador)
        response = self.client.get(reverse("intake-list"))
        self.assertEqual([(t["key"], t["count"]) for t in response.context["tabs"]],
                         [("novos", 1), ("convertidos", 1), ("ignorados", 1)])
        self.assertContains(self.client.get(reverse("intake-list"), {"status": "convertidos"}), "Convertida")
        ignoradas = self.client.get(reverse("intake-list"), {"status": "ignorados"})
        self.assertContains(ignoradas, "não é conosco")
        self.assertContains(ignoradas, "Restaurar")
        self.assertNotContains(ignoradas, "Criar demanda")
        self.assertNotEqual(converted.pk, None)

    def test_unknown_tab_falls_back_to_new(self):
        self.novo()
        self.login(self.triador)
        self.assertEqual(self.client.get(reverse("intake-list"), {"status": "x"}).context["tab"], "novos")

    def test_search(self):
        self.novo(subject="Gerador", raw_content="gerador da obra")
        self.novo(subject="Elevador", raw_content="elevador do bloco B", sender_email="outro@x.com")
        self.login(self.triador)
        response = self.client.get(reverse("intake-list"), {"q": "elevador"})
        self.assertContains(response, "Elevador")
        self.assertNotContains(response, "gerador da obra")
        empty = self.client.get(reverse("intake-list"), {"q": "inexistente"})
        self.assertContains(empty, "Nenhuma solicitação encontrada")

    def test_empty_states(self):
        self.login(self.triador)
        self.assertContains(self.client.get(reverse("intake-list")), "Caixa de Entrada em dia")
        self.assertContains(self.client.get(reverse("intake-list"), {"status": "convertidos"}), "virou demanda ainda")
        self.assertContains(self.client.get(reverse("intake-list"), {"status": "ignorados"}), "Nenhuma solicitação ignorada")

    def test_pagination(self):
        for index in range(27):
            self.new_item(subject=f"Item {index}", raw_content=f"texto {index}")
        self.login(self.triador)
        first = self.client.get(reverse("intake-list"))
        self.assertTrue(first.context["is_paginated"])
        self.assertEqual(len(first.context["page_obj"].object_list), 25)
        self.assertEqual(len(self.client.get(reverse("intake-list"), {"page": 2}).context["page_obj"].object_list), 2)

    def test_sector_manager_sees_only_the_sector(self):
        self.novo(suggested_sector=self.compras, subject="Pedido de compras")
        self.novo(suggested_sector=self.comercial, subject="Pedido do comercial")
        self.novo(subject="Pedido sem setor")
        self.login(self.gestor_compras)
        response = self.client.get(reverse("intake-list"))
        self.assertContains(response, "Pedido de compras")
        self.assertNotContains(response, "Pedido do comercial")
        self.assertNotContains(response, "Pedido sem setor")

    def test_organization_triager_sees_unassigned_items(self):
        self.novo(subject="Pedido sem setor")
        self.login(self.triador)
        self.assertContains(self.client.get(reverse("intake-list")), "Pedido sem setor")

    def test_message_text_is_escaped(self):
        self.new_item(subject="<b>negrito</b>", sender_name="<img src=x onerror=alert(1)>",
                      raw_content="<script>alert('xss')</script> pedido")
        self.login(self.triador)
        response = self.client.get(reverse("intake-list"))
        self.assertNotContains(response, "<script>alert")
        self.assertNotContains(response, "<img src=x")
        self.assertNotContains(response, "<b>negrito</b>")
        self.assertContains(response, "&lt;script&gt;alert")

    def test_number_of_queries_does_not_grow_with_the_number_of_items(self):
        def queries():
            self.client.force_login(self.triador)
            with CaptureQueriesContext(connection) as context:
                self.client.get(reverse("intake-list"))
            return len(context)

        for index in range(2):
            self.novo(subject=f"A{index}", raw_content=f"a{index}")
        few = queries()
        for index in range(12):
            self.novo(subject=f"B{index}", raw_content=f"b{index}")
        self.assertEqual(queries(), few)


class CaptureViewTests(ViewTestCase):
    payload = dict(source="EMAIL", sender_name="Maria da Convivy", sender_email="maria@convivy.com.br",
                   subject="Gerador", raw_content=EMAIL_TEXT)

    def test_form_page_and_modal(self):
        self.login(self.triador)
        page = self.client.get(reverse("intake-capture"))
        self.assertContains(page, "Registrar solicitação")
        self.assertContains(page, "Texto da solicitação")
        modal = self.client.get(reverse("intake-capture"), **AJAX)
        self.assertContains(modal, "modal-backdrop")

    def test_manual_form_does_not_offer_the_future_form_channel(self):
        self.login(self.triador)
        self.assertNotContains(self.client.get(reverse("intake-capture")), 'value="FORMULARIO"')

    def test_post_without_javascript_redirects_to_the_inbox(self):
        self.login(self.triador)
        response = self.client.post(reverse("intake-capture"), self.payload)
        self.assertRedirects(response, reverse("intake-list"))
        item = IntakeItem.objects.get()
        self.assertEqual(item.suggested_client, self.convivy)
        self.assertEqual(item.created_by, self.triador)

    def test_ajax_post_returns_the_destination(self):
        response, body = self.post_json(reverse("intake-capture"), self.payload, user=self.triador)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["redirect_url"], reverse("intake-list"))
        self.assertIn("registrada", body["message"])
        self.assertEqual(IntakeItem.objects.count(), 1)

    def test_ajax_post_leaves_the_notice_for_the_page_it_navigates_to(self):
        self.post_json(reverse("intake-capture"), self.payload, user=self.triador)
        self.assertContains(self.client.get(reverse("intake-list")), "Solicitação registrada na Caixa de Entrada.")

    def test_registrador_goes_home_because_cannot_see_the_inbox(self):
        response, body = self.post_json(reverse("intake-capture"), self.payload, user=self.registrador)
        self.assertEqual(body["redirect_url"], reverse("home"))
        self.assertEqual(IntakeItem.objects.get().created_by, self.registrador)

    def test_ajax_errors_are_json(self):
        response, body = self.post_json(reverse("intake-capture"), {**self.payload, "raw_content": ""}, user=self.triador)
        self.assertEqual(response.status_code, 400)
        self.assertIn("raw_content", body["errors"])
        self.assertEqual(IntakeItem.objects.count(), 0)

    def test_rule_errors_come_as_general_errors(self):
        self.post_json(reverse("intake-capture"), self.payload, user=self.triador)
        response, body = self.post_json(reverse("intake-capture"), self.payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("já está na Caixa de Entrada", body["errors"]["__all__"][0])

    def test_future_channel_is_not_accepted_here(self):
        response, body = self.post_json(reverse("intake-capture"), {**self.payload, "source": "FORMULARIO"}, user=self.triador)
        self.assertEqual(response.status_code, 400)
        self.assertIn("source", body["errors"])

    def test_invalid_page_is_rendered_with_the_errors(self):
        self.login(self.triador)
        response = self.client.post(reverse("intake-capture"), {**self.payload, "raw_content": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cole o texto da solicitação.")


class DetailViewTests(ViewTestCase):
    def test_shows_the_original_text_the_understanding_and_the_history(self):
        item = IntakeService.register(self.org, self.triador, EMAIL_TEXT, subject="Gerador",
                                      sender_name="Maria da Convivy", sender_email="maria@convivy.com.br")
        self.login(self.triador)
        response = self.client.get(reverse("intake-detail", args=[item.pk]))
        self.assertContains(response, "Precisamos do orçamento do gerador")
        self.assertContains(response, "Por que a LPS sugeriu isso")
        self.assertContains(response, "Registrada")
        self.assertContains(response, "Criar demanda")

    def test_raw_text_is_escaped(self):
        item = self.new_item(raw_content="<script>alert('xss')</script>")
        self.login(self.triador)
        response = self.client.get(reverse("intake-detail", args=[item.pk]))
        self.assertNotContains(response, "<script>alert")
        self.assertContains(response, "&lt;script&gt;")

    def test_converted_item_links_to_the_activity_and_has_no_actions(self):
        item = self.novo()
        activity = IntakeService.convert(item, self.triador, title="Gerador", owner=self.triador, sector=self.comercial)
        self.login(self.triador)
        response = self.client.get(reverse("intake-detail", args=[item.pk]))
        self.assertContains(response, activity.code)
        self.assertContains(response, reverse("activity-detail", args=[activity.pk]))
        self.assertNotContains(response, "Criar demanda")
        self.assertNotContains(response, reverse("intake-ignore", args=[item.pk]))

    def test_viewer_without_triage_permission_does_not_get_the_actions(self):
        viewer = User.objects.create_user("leitor", password="x")
        viewer.profile.organization = self.org
        viewer.profile.save()
        grant_actions(viewer, [catalog.ENTRADA_VISUALIZAR], organization=self.org)
        item = self.novo()
        self.login(viewer)
        response = self.client.get(reverse("intake-detail", args=[item.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Criar demanda")
        self.assertNotContains(response, "Ignorar")


class EditViewTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.item = self.novo(suggested_sector=self.compras, suggested_title="Título velho")

    def url(self):
        return reverse("intake-edit", args=[self.item.pk])

    def test_modal_starts_with_what_was_suggested(self):
        self.login(self.triador)
        response = self.client.get(self.url(), **AJAX)
        self.assertContains(response, "modal-backdrop")
        self.assertContains(response, "Título velho")
        self.assertContains(response, "Convivy")

    def test_ajax_post_updates_and_returns_the_new_card(self):
        data = {"title": "Título novo", "client": self.outra.pk, "site": "", "sector": self.comercial.pk,
                "deadline_0": "2026-12-10", "deadline_1": "09:30"}
        response, body = self.post_json(self.url(), data, user=self.triador)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["target"], f"#intake-item-{self.item.pk}")
        self.assertIn("Outra Construtora", body["html"])
        self.assertTrue(body["html"].lstrip().startswith("<li"))
        self.item.refresh_from_db()
        self.assertEqual(self.item.suggested_title, "Título novo")
        self.assertEqual(self.item.suggested_client, self.outra)
        self.assertEqual(self.item.suggested_sector, self.comercial)
        self.assertIsNone(self.item.suggested_site)
        self.assertEqual(self.item.suggested_deadline_label, "quinta, 10/12 às 09:30")
        self.assertTrue(self.item.events.filter(kind=IntakeEvent.Kind.EDITADA).exists())

    def test_site_of_another_client_is_rejected(self):
        data = {"title": "x", "client": self.outra.pk, "site": self.aurora.pk}
        response, body = self.post_json(self.url(), data, user=self.triador)
        self.assertEqual(response.status_code, 400)
        self.assertIn("site", body["errors"])

    def test_records_of_other_organizations_are_not_accepted(self):
        data = {"title": "x", "client": self.foreign_client.pk}
        response, body = self.post_json(self.url(), data, user=self.triador)
        self.assertEqual(response.status_code, 400)
        self.assertIn("client", body["errors"])

    def test_sector_manager_cannot_move_it_out_of_sight(self):
        data = {"title": "x", "client": self.convivy.pk, "sector": self.comercial.pk}
        response, body = self.post_json(self.url(), data, user=self.gestor_compras)
        self.assertEqual(response.status_code, 400)
        self.assertIn("não teria mais acesso", body["errors"]["__all__"][0])

    def test_already_handled_item_cannot_be_edited(self):
        IntakeService.ignore(self.item, self.triador)
        self.login(self.triador)
        self.assertRedirects(self.client.get(self.url()), reverse("intake-detail", args=[self.item.pk]))

    def test_requires_triage_permission(self):
        self.login(self.registrador)
        self.assertEqual(self.client.get(self.url()).status_code, 403)


class ConvertViewTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.item = self.novo(suggested_sector=self.comercial, suggested_title="Orçamento do gerador")

    def url(self):
        return reverse("intake-convert", args=[self.item.pk])

    def data(self, **overrides):
        data = {"title": "Orçamento do gerador", "owner": self.triador.pk, "sector": self.comercial.pk,
                "client": self.convivy.pk, "site": self.aurora.pk, "requested_deadline_0": "2026-12-10",
                "requested_deadline_1": "", "urgency": "ALTA", "company": "", "external_requester": "Maria da Convivy"}
        data.update(overrides)
        return data

    def test_form_starts_filled_with_what_was_understood(self):
        self.login(self.triador)
        response = self.client.get(self.url())
        initial = response.context["form"].initial
        self.assertEqual(initial["title"], "Orçamento do gerador")
        self.assertEqual(initial["client"], self.convivy)
        self.assertEqual(initial["site"], self.aurora)
        self.assertEqual(initial["sector"], self.comercial)
        self.assertEqual(initial["owner"], self.triador)
        self.assertEqual(initial["external_requester"], "Maria da Convivy")
        self.assertContains(response, "Mais detalhes")

    def test_sector_falls_back_to_the_users_main_sector(self):
        self.item.suggested_sector = None
        self.item.save()
        self.triador.profile.main_sector = self.compras
        self.triador.profile.save()
        self.login(self.triador)
        self.assertEqual(self.client.get(self.url()).context["form"].initial["sector"], self.compras)

    def test_ajax_post_creates_the_activity_and_points_to_it(self):
        response, body = self.post_json(self.url(), self.data(), user=self.triador)
        self.assertEqual(response.status_code, 200)
        activity = Activity.objects.get()
        self.assertEqual(body["redirect_url"], reverse("activity-detail", args=[activity.pk]))
        self.assertIn(activity.code, body["message"])
        self.assertEqual((activity.title, activity.owner, activity.sector), ("Orçamento do gerador", self.triador, self.comercial))
        self.assertEqual((activity.client, activity.site, activity.urgency), (self.convivy, self.aurora, "ALTA"))
        deadline = timezone.localtime(activity.requested_deadline)
        self.assertEqual((deadline.date().isoformat(), deadline.strftime("%H:%M")), ("2026-12-10", "23:59"))
        self.assertEqual(activity.external_requester, "Maria da Convivy")
        self.item.refresh_from_db()
        self.assertEqual((self.item.status, self.item.activity), (IntakeItem.Status.CONVERTIDO, activity))

    def test_ajax_post_leaves_the_notice_on_the_activity_page(self):
        self.post_json(self.url(), self.data(), user=self.triador)
        activity = Activity.objects.get()
        page = self.client.get(reverse("activity-detail", args=[activity.pk]))
        self.assertContains(page, f"Demanda {activity.code} criada.")

    def test_post_without_javascript_goes_to_the_activity(self):
        self.login(self.triador)
        response = self.client.post(self.url(), self.data())
        activity = Activity.objects.get()
        self.assertRedirects(response, reverse("activity-detail", args=[activity.pk]), fetch_redirect_response=False)

    def test_missing_required_fields(self):
        response, body = self.post_json(self.url(), self.data(title=" ", sector="", owner=""), user=self.triador)
        self.assertEqual(response.status_code, 400)
        self.assertEqual({"title", "sector", "owner"} & set(body["errors"]), {"title", "sector", "owner"})
        self.assertEqual(Activity.objects.count(), 0)

    def test_site_of_another_client_is_rejected(self):
        response, body = self.post_json(self.url(), self.data(client=self.outra.pk), user=self.triador)
        self.assertEqual(response.status_code, 400)
        self.assertIn("site", body["errors"])

    def test_owner_from_another_organization_is_rejected(self):
        response, body = self.post_json(self.url(), self.data(owner=self.estranho.pk), user=self.triador)
        self.assertEqual(response.status_code, 400)
        self.assertIn("owner", body["errors"])
        self.assertEqual(Activity.objects.count(), 0)

    def test_permission_to_create_activities_is_still_required(self):
        so_triagem = make_user("sotriagem", self.org, [catalog.ENTRADA_VISUALIZAR, catalog.ENTRADA_TRIAR])
        response, body = self.post_json(self.url(), self.data(owner=so_triagem.pk), user=so_triagem)
        self.assertEqual(response.status_code, 400)
        self.assertIn("__all__", body["errors"])
        self.assertEqual(Activity.objects.count(), 0)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, IntakeItem.Status.NOVO)

    def test_sector_manager_cannot_create_into_another_sector(self):
        item = self.novo(suggested_sector=self.compras, subject="Compras")
        url = reverse("intake-convert", args=[item.pk])
        response, body = self.post_json(url, self.data(owner=self.gestor_compras.pk, sector=self.comercial.pk), user=self.gestor_compras)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Activity.objects.count(), 0)
        ok, _ = self.post_json(url, self.data(owner=self.gestor_compras.pk, sector=self.compras.pk))
        self.assertEqual(ok.status_code, 200)

    def test_second_attempt_does_not_create_a_second_activity(self):
        self.post_json(self.url(), self.data(), user=self.triador)
        again = self.client.post(self.url(), self.data(), **AJAX)
        self.assertEqual(again.status_code, 302)
        self.assertEqual(Activity.objects.count(), 1)

    def test_get_of_a_handled_item_goes_back_to_the_detail(self):
        IntakeService.ignore(self.item, self.triador)
        self.login(self.triador)
        self.assertRedirects(self.client.get(self.url()), reverse("intake-detail", args=[self.item.pk]))


class IgnoreAndRestoreViewTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.item = self.novo()

    def test_ignore_modal_and_post(self):
        self.login(self.triador)
        self.assertContains(self.client.get(reverse("intake-ignore", args=[self.item.pk]), **AJAX), "Ignorar solicitação")
        response, body = self.post_json(reverse("intake-ignore", args=[self.item.pk]), {"reason": "Duplicada"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["remove"], f"#intake-item-{self.item.pk}")
        self.item.refresh_from_db()
        self.assertEqual((self.item.status, self.item.resolution_note), (IntakeItem.Status.IGNORADO, "Duplicada"))

    def test_ignore_updates_in_place_so_it_leaves_no_notice_behind(self):
        self.post_json(reverse("intake-ignore", args=[self.item.pk]), {"reason": ""}, user=self.triador)
        self.assertNotContains(self.client.get(reverse("intake-list")), "Solicitação ignorada.")

    def test_ignore_without_javascript(self):
        self.login(self.triador)
        response = self.client.post(reverse("intake-ignore", args=[self.item.pk]), {"reason": ""})
        self.assertRedirects(response, reverse("intake-detail", args=[self.item.pk]))

    def test_restore_only_accepts_post(self):
        IntakeService.ignore(self.item, self.triador)
        self.login(self.triador)
        self.assertEqual(self.client.get(reverse("intake-restore", args=[self.item.pk])).status_code, 405)

    def test_restore_ajax(self):
        IntakeService.ignore(self.item, self.triador)
        response, body = self.post_json(reverse("intake-restore", args=[self.item.pk]), user=self.triador)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["remove"], f"#intake-item-{self.item.pk}")
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, IntakeItem.Status.NOVO)

    def test_restore_without_javascript(self):
        IntakeService.ignore(self.item, self.triador)
        self.login(self.triador)
        response = self.client.post(reverse("intake-restore", args=[self.item.pk]))
        self.assertRedirects(response, reverse("intake-detail", args=[self.item.pk]))

    def test_restore_of_a_new_item_is_a_json_error(self):
        response, body = self.post_json(reverse("intake-restore", args=[self.item.pk]), user=self.triador)
        self.assertEqual(response.status_code, 400)
        self.assertIn("ignorada", body["error"])

    def test_ignored_item_cannot_be_ignored_again(self):
        IntakeService.ignore(self.item, self.triador)
        self.login(self.triador)
        self.assertEqual(self.client.post(reverse("intake-ignore", args=[self.item.pk]), {"reason": ""}).status_code, 302)


class MenuTests(ViewTestCase):
    def test_every_intake_route_is_mapped_to_the_menu_item(self):
        names = {pattern.name for pattern in intake_urls.urlpatterns}
        self.assertEqual(len(names), 7)
        for name in names:
            self.assertEqual(_NAV_BY_URL_NAME.get(name), "intake", name)

    def test_item_and_counter_for_who_can_see(self):
        self.novo(subject="Um")
        self.novo(subject="Dois", raw_content="outro")
        self.novo(subject="Ignorada", raw_content="x", status=IntakeItem.Status.IGNORADO)
        self.login(self.triador)
        response = self.client.get(reverse("intake-list"))
        self.assertTrue(response.context["lps_nav"]["intake"])
        self.assertEqual(response.context["lps_intake_new"], 2)
        self.assertEqual(response.context["nav_active"], "intake")
        self.assertContains(response, 'data-tooltip="Entrada"')
        self.assertContains(response, '<span class="nav-count">2</span>')

    def test_counter_follows_the_sector_scope(self):
        self.novo(suggested_sector=self.compras, subject="Compras")
        self.novo(suggested_sector=self.comercial, subject="Comercial", raw_content="y")
        self.login(self.gestor_compras)
        self.assertEqual(self.client.get(reverse("notification-list")).context["lps_intake_new"], 1)

    def test_registrador_gets_the_item_pointing_to_the_capture_form(self):
        self.login(self.registrador)
        response = self.client.get(reverse("notification-list"))
        self.assertTrue(response.context["lps_nav"]["intake"])
        self.assertFalse(response.context["lps_nav"]["intake_can_view"])
        self.assertEqual(response.context["lps_intake_new"], 0)
        self.assertContains(response, f'href="{reverse("intake-capture")}"')

    def test_no_item_without_permission(self):
        self.login(self.sem_acesso)
        response = self.client.get(reverse("notification-list"))
        self.assertFalse(response.context["lps_nav"]["intake"])
        self.assertNotContains(response, 'data-tooltip="Entrada"')
