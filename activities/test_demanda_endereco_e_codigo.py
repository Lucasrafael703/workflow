"""Endereço `/demandas/…` e código `DEM-AAAA-NNNNN` (a "Atividade" virou "Demanda" também aí, 01/10/2026).

Cobre: as páginas no endereço novo, os endereços antigos que redirecionam (inclusive formulário aberto
antes da troca), a busca que ainda aceita o prefixo antigo do código e a migração `0020_codigo_da_demanda`
(códigos, pastas e nomes dos anexos).
"""

import importlib
import pathlib
import re
import tempfile
from unittest import mock

from django.apps import apps
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone
from django.views.static import serve

from . import urls as activities_urls
from .models import Activity, ActivityAttachment, code_search_term
from .testing import ProcessTestCase

migration = importlib.import_module("activities.migrations.0020_codigo_da_demanda")

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class EnderecoDasDemandasTests(TestCase):
    def test_pages_live_under_demandas(self):
        self.assertEqual(reverse("activity-list"), "/demandas/")
        self.assertEqual(reverse("activity-detail", args=[7]), "/demandas/7/")
        self.assertEqual(reverse("activity-search"), "/demandas/busca/")
        self.assertEqual(reverse("task-quick-create", args=[7]), "/demandas/7/tarefas/rapida/")
        self.assertEqual(reverse("activitystage-create"), "/configuracoes/estagios-de-demanda/novo/")
        self.assertEqual(settings.ACTIVITY_FILES_URL, "/demanda-arquivos/")

    def test_every_route_has_an_old_address_that_redirects_to_it(self):
        routes = [str(p.pattern) for p in activities_urls.urlpatterns if str(p.pattern).startswith("demandas/")]
        self.assertGreater(len(routes), 25)
        for route in routes:
            with self.subTest(route=route):
                concrete = "/" + re.sub(r"<int:\w+>", "7", route)
                self.assertNotEqual(resolve(concrete).url_name, "legacy-activities")
                response = self.client.get("/atividades/" + concrete[len("/demandas/"):])
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response["Location"], concrete)

    def test_the_old_list_address_redirects_to_the_new_one(self):
        response = self.client.get("/atividades/")
        self.assertRedirects(response, "/demandas/", status_code=301, fetch_redirect_response=False)

    def test_the_query_string_is_kept(self):
        response = self.client.get("/atividades/?tab=todas&q=ATV-2026-00007")
        self.assertEqual(response["Location"], "/demandas/?tab=todas&q=ATV-2026-00007")

    def test_a_form_posted_to_the_old_address_keeps_its_method(self):
        response = self.client.post("/atividades/7/concluir/", {"motivo": "x"})
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response["Location"], "/demandas/7/concluir/")

    def test_the_old_address_never_leads_outside_the_site(self):
        for path in ("/atividades//evil.example.com/", "/atividades/https://evil.example.com/"):
            with self.subTest(path=path):
                location = self.client.get(path)["Location"]
                self.assertTrue(location.startswith("/demandas/"))

    def test_the_old_address_needs_no_login(self):
        self.assertEqual(self.client.get("/atividades/7/").status_code, 301)

    def test_old_stage_addresses_redirect(self):
        for old, new in (
            ("/configuracoes/estagios-de-atividade/novo/", "/configuracoes/estagios-de-demanda/novo/"),
            ("/configuracoes/estagios-de-atividade/5/?x=1", "/configuracoes/estagios-de-demanda/5/?x=1"),
        ):
            with self.subTest(old=old):
                self.assertEqual(self.client.get(old)["Location"], new)


class ArquivosAntigosTests(TestCase):
    """`/atividade-arquivos/<empresa>/ATV-…/<arquivo>` → `/demanda-arquivos/…`."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = pathlib.Path(folder.name)
        self.enterContext(override_settings(ACTIVITY_FILES_ROOT=folder.name))

    def put(self, relative):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("conteúdo", encoding="utf-8")

    def test_uses_the_new_folder_once_it_was_renamed(self):
        self.put("sem-empresa/DEM-2026-00003/teste.txt")
        response = self.client.get("/atividade-arquivos/sem-empresa/ATV-2026-00003/teste.txt")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/demanda-arquivos/sem-empresa/DEM-2026-00003/teste.txt")

    def test_keeps_the_old_folder_when_the_file_was_not_moved(self):
        self.put("sem-empresa/ATV-2026-00003/teste.txt")
        response = self.client.get("/atividade-arquivos/sem-empresa/ATV-2026-00003/teste.txt")
        self.assertEqual(response["Location"], "/demanda-arquivos/sem-empresa/ATV-2026-00003/teste.txt")

    def test_a_path_that_climbs_out_of_the_folder_is_not_followed(self):
        response = self.client.get("/atividade-arquivos/ATV-2026-00003/../../../etc/passwd")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response["Location"].startswith("/demanda-arquivos/ATV-2026-00003/"))

    def test_the_new_address_is_served_from_the_files_folder(self):
        self.assertIs(resolve("/demanda-arquivos/sem-empresa/DEM-2026-00003/teste.txt").func, serve)


class CodigoDaDemandaTests(ProcessTestCase):
    def test_new_codes_start_with_dem_and_the_sequence_goes_on(self):
        year = timezone.now().year
        self.assertEqual(self.activity.code, f"DEM-{year}-00001")
        self.assertEqual(self.new_activity(title="Outra").code, f"DEM-{year}-00002")

    def test_code_generation_retries_a_unique_collision(self):
        year = timezone.now().year
        next_code = f"DEM-{year}-99999"
        activity = Activity(
            organization=self.org,
            title="Demanda criada ao mesmo tempo",
            owner=self.owner,
            created_by=self.owner,
        )

        with mock.patch.object(
            Activity, "_generate_code", side_effect=[self.activity.code, next_code]
        ) as generate_code:
            activity.save()

        self.assertEqual(activity.code, next_code)
        self.assertEqual(generate_code.call_count, 2)

    def test_code_search_term_swaps_only_the_old_prefix_of_a_code(self):
        for typed, expected in (
            ("ATV-2026-00007", "DEM-2026-00007"),
            ("atv-2026-7", "DEM-2026-7"),
            ("ver ATV-2026-00007 e ATV-2026-00008", "ver DEM-2026-00007 e DEM-2026-00008"),
            ("ATV extra", "ATV extra"),
            ("XATV-2026-00007", "XATV-2026-00007"),
            ("DEM-2026-00007", "DEM-2026-00007"),
            ("", ""),
            (None, ""),
        ):
            with self.subTest(typed=typed):
                self.assertEqual(code_search_term(typed), expected)

    def test_the_list_finds_a_demand_by_its_old_code(self):
        self.client.force_login(self.owner)
        old_code = self.activity.code.replace("DEM-", "ATV-")
        response = self.client.get(reverse("activity-list"), {"q": old_code})
        self.assertIn(self.activity, list(response.context["activities"]))

    def test_the_task_picker_finds_a_demand_by_its_old_code(self):
        self.client.force_login(self.owner)
        old_code = self.activity.code.replace("DEM-", "ATV-")
        response = self.client.get(reverse("activity-search"), {"q": old_code}, **AJAX)
        self.assertEqual([item["id"] for item in response.json()["results"]], [self.activity.pk])


class MigracaoDoCodigoTests(ProcessTestCase):
    """`0020_codigo_da_demanda`: `ATV-AAAA-NNNNN` → `DEM-AAAA-NNNNN` e os anexos acompanham."""

    def setUp(self):
        super().setUp()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = pathlib.Path(folder.name)
        self.enterContext(override_settings(ACTIVITY_FILES_ROOT=folder.name))

    def legacy(self, activity, code="ATV-2026-00003"):
        Activity.objects.filter(pk=activity.pk).update(code=code)
        activity.refresh_from_db()
        return activity

    def attach(self, activity, name, on_disk=True):
        if on_disk:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("conteúdo", encoding="utf-8")
        return ActivityAttachment.objects.create(
            activity=activity, file=name, original_name="teste.txt", uploaded_by=self.owner
        )

    def code_of(self, activity):
        return Activity.objects.get(pk=activity.pk).code

    def name_of(self, attachment):
        return ActivityAttachment.objects.get(pk=attachment.pk).file.name

    def test_codes_are_rewritten_keeping_year_and_number(self):
        self.legacy(self.activity, "ATV-2026-00003")
        other = self.legacy(self.new_activity(title="Outra"), "ATV-2027-00120")
        migration.to_demanda(apps, None)
        self.assertEqual(self.code_of(self.activity), "DEM-2026-00003")
        self.assertEqual(self.code_of(other), "DEM-2027-00120")

    def test_text_written_by_people_is_not_touched(self):
        activity = self.new_activity(title="Ver ATV-2026-00003")
        Activity.objects.filter(pk=activity.pk).update(description="<p>Igual à ATV-2026-00003</p>")
        migration.to_demanda(apps, None)
        activity.refresh_from_db()
        self.assertEqual(activity.title, "Ver ATV-2026-00003")
        self.assertEqual(activity.description, "<p>Igual à ATV-2026-00003</p>")

    def test_running_twice_changes_nothing_more(self):
        self.legacy(self.activity)
        migration.to_demanda(apps, None)
        migration.to_demanda(apps, None)
        self.assertEqual(self.code_of(self.activity), "DEM-2026-00003")

    def test_reverse_goes_back(self):
        self.legacy(self.activity)
        migration.to_demanda(apps, None)
        migration.to_atividade(apps, None)
        self.assertEqual(self.code_of(self.activity), "ATV-2026-00003")

    def test_a_code_that_is_already_taken_is_left_as_it_was(self):
        self.legacy(self.activity, "ATV-2026-00003")
        taken = self.legacy(self.new_activity(title="Já migrada"), "DEM-2026-00003")
        migration.to_demanda(apps, None)
        self.assertEqual(self.code_of(self.activity), "ATV-2026-00003")
        self.assertEqual(self.code_of(taken), "DEM-2026-00003")

    def test_the_attachment_folder_is_renamed_and_the_stored_name_follows(self):
        self.legacy(self.activity)
        attachment = self.attach(self.activity, "sem-empresa/ATV-2026-00003/teste.txt")
        migration.to_demanda(apps, None)
        self.assertEqual(self.name_of(attachment), "sem-empresa/DEM-2026-00003/teste.txt")
        self.assertTrue((self.root / "sem-empresa/DEM-2026-00003/teste.txt").is_file())
        self.assertFalse((self.root / "sem-empresa/ATV-2026-00003").exists())

    def test_every_file_of_the_demand_moves(self):
        self.legacy(self.activity)
        first = self.attach(self.activity, "Biasi Engenharia/ATV-2026-00003/a.txt")
        second = self.attach(self.activity, "Biasi Engenharia/ATV-2026-00003/b.txt")
        migration.to_demanda(apps, None)
        self.assertEqual(self.name_of(first), "Biasi Engenharia/DEM-2026-00003/a.txt")
        self.assertEqual(self.name_of(second), "Biasi Engenharia/DEM-2026-00003/b.txt")
        self.assertTrue((self.root / "Biasi Engenharia/DEM-2026-00003/b.txt").is_file())

    def test_a_file_missing_from_the_disk_only_gets_its_name_adjusted(self):
        self.legacy(self.activity)
        attachment = self.attach(self.activity, "sem-empresa/ATV-2026-00003/sumiu.txt", on_disk=False)
        migration.to_demanda(apps, None)
        self.assertEqual(self.name_of(attachment), "sem-empresa/DEM-2026-00003/sumiu.txt")
        self.assertFalse((self.root / "sem-empresa/DEM-2026-00003").exists())

    def test_a_file_that_cannot_be_moved_keeps_its_old_name(self):
        self.legacy(self.activity)
        attachment = self.attach(self.activity, "sem-empresa/ATV-2026-00003/teste.txt")
        (self.root / "sem-empresa/DEM-2026-00003").mkdir(parents=True)
        (self.root / "sem-empresa/DEM-2026-00003/teste.txt").write_text("outro", encoding="utf-8")
        migration.to_demanda(apps, None)
        self.assertEqual(self.name_of(attachment), "sem-empresa/ATV-2026-00003/teste.txt")
        self.assertTrue((self.root / "sem-empresa/ATV-2026-00003/teste.txt").is_file())

    def test_files_of_other_demands_are_not_touched(self):
        self.legacy(self.activity)
        other = self.new_activity(title="Outra")
        mine = self.attach(other, f"sem-empresa/{other.code}/x.txt")
        migration.to_demanda(apps, None)
        self.assertEqual(self.name_of(mine), f"sem-empresa/{other.code}/x.txt")
        self.assertTrue((self.root / f"sem-empresa/{other.code}/x.txt").is_file())

    def test_reverse_moves_the_files_back(self):
        self.legacy(self.activity)
        attachment = self.attach(self.activity, "sem-empresa/ATV-2026-00003/teste.txt")
        migration.to_demanda(apps, None)
        migration.to_atividade(apps, None)
        self.assertEqual(self.name_of(attachment), "sem-empresa/ATV-2026-00003/teste.txt")
        self.assertTrue((self.root / "sem-empresa/ATV-2026-00003/teste.txt").is_file())
        self.assertFalse((self.root / "sem-empresa/DEM-2026-00003").exists())
