"""Caixa de Entrada inativa (`settings.INTAKE_ENABLED` desligado, o padrão): some do menu e as rotas dão 404.

O código, as tabelas e as permissões `entrada.*` continuam; ligar a chave devolve tudo (o resto dos testes
do app roda com a chave ligada, ver `IntakeTestCase`).
"""

from unittest import mock

from django.test import override_settings
from django.urls import reverse

from .models import IntakeItem
from .testing import AJAX, EMAIL_TEXT, IntakeTestCase


@override_settings(INTAKE_ENABLED=False)
class CaixaDeEntradaInativaTests(IntakeTestCase):
    def setUp(self):
        super().setUp()
        self.item = self.new_item()
        self.client.force_login(self.triador)

    def test_every_route_answers_404_even_for_who_has_every_permission(self):
        pk = self.item.pk
        for name, args in (
            ("intake-list", []),
            ("intake-capture", []),
            ("intake-detail", [pk]),
            ("intake-edit", [pk]),
            ("intake-convert", [pk]),
            ("intake-ignore", [pk]),
            ("intake-restore", [pk]),
        ):
            for headers in ({}, AJAX):
                with self.subTest(route=name, ajax=bool(headers)):
                    self.assertEqual(self.client.get(reverse(name, args=args), **headers).status_code, 404)
                    self.assertEqual(self.client.post(reverse(name, args=args), {}, **headers).status_code, 404)

    def test_nothing_is_written_through_the_closed_routes(self):
        before = IntakeItem.objects.count()
        self.client.post(reverse("intake-capture"), {"source": "EMAIL", "raw_content": EMAIL_TEXT}, **AJAX)
        self.client.post(reverse("intake-ignore", args=[self.item.pk]), {"reason": "x"}, **AJAX)
        self.item.refresh_from_db()
        self.assertEqual(IntakeItem.objects.count(), before)
        self.assertEqual(self.item.status, IntakeItem.Status.NOVO)

    def test_the_menu_has_no_entrada_item_and_no_counter(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-tooltip="Entrada"')
        self.assertFalse(response.context["lps_nav"]["intake"])
        self.assertEqual(response.context["lps_intake_new"], 0)

    def test_the_menu_does_not_even_count_the_items(self):
        with mock.patch("intake.services.IntakeService.new_count") as new_count:
            self.client.get(reverse("home"))
        new_count.assert_not_called()

    def test_the_registrador_has_no_entrada_item_either(self):
        self.client.force_login(self.registrador)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, 'data-tooltip="Entrada"')
        self.assertNotContains(response, reverse("intake-capture"))

    def test_turning_the_switch_on_brings_it_back(self):
        with override_settings(INTAKE_ENABLED=True):
            self.assertEqual(self.client.get(reverse("intake-list")).status_code, 200)
            self.assertContains(self.client.get(reverse("home")), 'data-tooltip="Entrada"')
