"""Edição inline da lista de Demandas: título, responsável e prazo (Entrega 1); cliente/obra, setor, estágio e status
(Entrega 2).

O inline é um adapter: estes testes conferem (a) o contrato JSON e os códigos HTTP, (b) que a regra de negócio vive no
`ActivityService` (valem também fora do inline), (c) que a lista só oferece edição a quem pode e (d) o isolamento entre
organizações.
"""

import datetime
import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from acessos.testing import grant_action
from audit.models import AuditLog
from core import models as core_models
from core.models import Organization, Sector
from notifications.models import Notification

from .errors import ActivityError, ActivityPermissionError
from .inline_edit import (
    ActivityInlineService,
    deadline_display,
    deadline_parts,
    deadline_state,
    inline_flags,
    parse_deadline,
)
from .models import Activity, ActivityPendency, OwnerChangeLog
from .services import ActivityService
from .testing import make_user

User = get_user_model()
AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

FILL = [catalog.ATIVIDADE_VISUALIZAR, catalog.ATIVIDADE_VISUALIZAR_TODAS, catalog.ATIVIDADE_EDITAR]
FULL = FILL + [catalog.ATIVIDADE_ALTERAR_DONO]


class InlineBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Biasi")
        cls.other_org = Organization.objects.create(name="Outra")
        cls.sector = Sector.objects.create(organization=cls.org, name="Comercial")

        cls.editor = make_user("editor", cls.org, FULL)  # edita e troca o responsável
        cls.filler = make_user("filler", cls.org, FILL)  # edita, mas NÃO troca o responsável
        cls.reader = make_user("reader", cls.org, [catalog.ATIVIDADE_VISUALIZAR, catalog.ATIVIDADE_VISUALIZAR_TODAS])
        cls.novo = make_user("novo", cls.org)  # candidato a responsável
        cls.novo.first_name, cls.novo.last_name = "Nova", "Pessoa"
        cls.novo.save(update_fields=["first_name", "last_name"])
        cls.inativo = make_user("inativo", cls.org)
        cls.inativo.is_active = False
        cls.inativo.save(update_fields=["is_active"])
        cls.alheio = make_user("alheio", cls.other_org, FULL)

        cls.a1 = cls.activity("Orçamento Aurora", cls.editor)
        cls.a_done = cls.activity("Já concluída", cls.editor, status=Activity.Status.CONCLUIDA)
        cls.a_cancel = cls.activity("Cancelada", cls.editor, status=Activity.Status.CANCELADA)
        cls.a_draft = cls.activity("Rascunho", cls.editor, status=Activity.Status.RASCUNHO)
        cls.a_foreign = Activity.objects.create(
            organization=cls.other_org, title="Alheia", owner=cls.alheio, created_by=cls.alheio
        )

    @classmethod
    def activity(cls, title, owner, status=Activity.Status.ABERTA, **extra):
        return Activity.objects.create(
            organization=cls.org, title=title, owner=owner, created_by=owner, sector=cls.sector, status=status, **extra
        )

    def post(self, activity, user=None, **data):
        self.client.force_login(user or self.editor)
        return self.client.post(reverse("activity-inline-update", args=[activity.pk]), data, **AJAX)

    def audit(self, activity, **filters):
        return AuditLog.objects.filter(activity=activity, **filters)


# ---------------------------------------------------------------------------
# Funções puras do adapter
# ---------------------------------------------------------------------------


class DeadlineHelpersTests(InlineBase):
    def local(self, *args):
        return timezone.make_aware(datetime.datetime(*args))

    def test_deadline_without_a_time_is_stored_at_2359_and_shown_as_a_date(self):
        value = parse_deadline("2026-10-14", "")
        self.assertEqual(timezone.localtime(value).time(), datetime.time(23, 59))
        self.assertEqual(deadline_display(value), "14/10/2026")
        self.assertEqual(deadline_parts(value), ("2026-10-14", ""))  # o editor trata 23:59 como "sem hora"

    def test_deadline_with_a_time_shows_the_time(self):
        value = parse_deadline("2026-10-14", "17:47")
        self.assertEqual(deadline_display(value), "14/10/2026 17:47")
        self.assertEqual(deadline_parts(value), ("2026-10-14", "17:47"))

    def test_display_uses_the_local_timezone(self):
        self.assertEqual(deadline_display(self.local(2026, 10, 14, 0, 5)), "14/10/2026 00:05")

    def test_no_deadline(self):
        self.assertIsNone(parse_deadline("", ""))
        self.assertEqual(deadline_display(None), "")
        self.assertEqual(deadline_parts(None), ("", ""))

    def test_invalid_deadlines_are_refused_with_a_message(self):
        for date_text, time_text in (("2026-02-30", ""), ("14/10/2026", ""), ("abc", ""), ("2026-10-14", "25:00"),
                                     ("2026-10-14", "xx"), ("0800-01-01", ""), ("9999-01-01", ""), ("", "10:00")):
            with self.assertRaises(ActivityError, msg=(date_text, time_text)):
                parse_deadline(date_text, time_text)

    def test_overdue_state_follows_the_status_of_the_activity(self):
        past = self.local(2020, 1, 10, 12, 0)
        open_activity = Activity(status=Activity.Status.ABERTA, requested_deadline=past)
        done = Activity(status=Activity.Status.CONCLUIDA, requested_deadline=past)
        future = Activity(status=Activity.Status.ABERTA, requested_deadline=timezone.now() + datetime.timedelta(days=3))
        self.assertTrue(deadline_state(open_activity)[0])
        self.assertGreater(deadline_state(open_activity)[1], 1000)
        self.assertEqual(deadline_state(done), (False, 0))
        self.assertEqual(deadline_state(future), (False, 0))
        self.assertEqual(deadline_state(Activity(status=Activity.Status.ABERTA)), (False, 0))


# ---------------------------------------------------------------------------
# Invariantes que ficam no Service (valem fora do inline)
# ---------------------------------------------------------------------------


class ServiceInvariantTests(InlineBase):
    def test_title_is_trimmed_and_audited_only_when_it_changes(self):
        ActivityService.update_activity(self.a1, self.editor, title="  Novo título  ")
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.title, "Novo título")
        entry = self.audit(self.a1, field_name="title").get()
        self.assertEqual((entry.old_value, entry.new_value), ("Orçamento Aurora", "Novo título"))
        ActivityService.update_activity(self.a1, self.editor, title="Novo título   ")  # igual depois do strip
        self.assertEqual(self.audit(self.a1, field_name="title").count(), 1)

    def test_empty_and_too_long_titles_are_refused_by_the_service(self):
        for bad in ("", "   ", None):
            with self.assertRaises(ActivityError, msg=repr(bad)):
                ActivityService.update_activity(self.a1, self.editor, title=bad)
        limit = Activity._meta.get_field("title").max_length
        ActivityService.update_activity(self.a1, self.editor, title="x" * limit)  # no limite pode
        with self.assertRaisesMessage(ActivityError, f"até {limit} caracteres"):
            ActivityService.update_activity(self.a1, self.editor, title="x" * (limit + 1))
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.title, "x" * limit)  # a recusa não mexe no título anterior

    def test_owner_must_be_an_active_person_of_the_same_organization(self):
        for candidate in (self.alheio, self.inativo):
            with self.assertRaises(ActivityError, msg=candidate.username):
                ActivityService.change_owner(self.a1, candidate, self.editor)
        with self.assertRaises(ActivityError):
            ActivityService.change_owner(self.a1, None, self.editor)
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.owner, self.editor)
        self.assertFalse(OwnerChangeLog.objects.filter(activity=self.a1).exists())

    def test_permission_denial_is_a_permission_error_that_is_still_an_activity_error(self):
        with self.assertRaises(ActivityPermissionError):
            ActivityService.update_activity(self.a1, self.reader, title="Não pode")
        with self.assertRaises(ActivityError):  # quem já capturava ActivityError continua capturando
            ActivityService.update_activity(self.a1, self.reader, title="Não pode")
        with self.assertRaises(ActivityPermissionError):
            ActivityService.change_owner(self.a1, self.novo, self.filler)
        # regra de negócio NÃO é erro de permissão
        with self.assertRaises(ActivityError) as caught:
            ActivityService.update_activity(self.a1, self.editor, title="")
        self.assertNotIsInstance(caught.exception, ActivityPermissionError)


# ---------------------------------------------------------------------------
# Endpoint: título
# ---------------------------------------------------------------------------


class TitleTests(InlineBase):
    def test_saves_the_title_and_audits_old_and_new(self):
        response = self.post(self.a1, field="title", value="  Orçamento Aurora — fase 2 ")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual((data["ok"], data["field"], data["display"]["text"]), (True, "title", "Orçamento Aurora — fase 2"))
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.title, "Orçamento Aurora — fase 2")
        entry = self.audit(self.a1, field_name="title").get()
        self.assertEqual((entry.old_value, entry.new_value, entry.user), ("Orçamento Aurora", "Orçamento Aurora — fase 2", self.editor))

    def test_same_title_is_not_audited(self):
        self.assertEqual(self.post(self.a1, field="title", value="Orçamento Aurora").status_code, 200)
        self.assertFalse(self.audit(self.a1, field_name="title").exists())

    def test_empty_or_too_long_title_is_refused_and_nothing_changes(self):
        for value in ("", "   ", "x" * 201):
            response = self.post(self.a1, field="title", value=value)
            self.assertEqual(response.status_code, 400, value[:10])
            self.assertFalse(response.json()["ok"])
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.title, "Orçamento Aurora")

    def test_a_reader_is_refused_with_403_and_nothing_changes(self):
        response = self.post(self.a1, user=self.reader, field="title", value="Invasão")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["ok"])
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.title, "Orçamento Aurora")
        self.assertFalse(self.audit(self.a1).filter(field_name="title").exists())

    def test_the_title_is_returned_as_data_and_never_as_html(self):
        payload = "<img src=x onerror=alert(1)>"
        data = self.post(self.a1, field="title", value=payload).json()
        self.assertEqual(data["display"]["text"], payload)  # o navegador usa textContent
        self.assertNotIn("html", data)


# ---------------------------------------------------------------------------
# Endpoint: responsável
# ---------------------------------------------------------------------------


class OwnerTests(InlineBase):
    def test_changes_the_owner_through_the_service_with_log_audit_and_notification(self):
        response = self.post(self.a1, field="owner", value=self.novo.pk)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["value"], self.novo.pk)
        self.assertEqual(data["display"]["text"], "Nova Pessoa")
        self.assertEqual(data["display"]["initials"], "NO")
        self.assertEqual(data["display"]["avatar_class"], f"avatar--{self.novo.pk % 6}")
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.owner, self.novo)
        log = OwnerChangeLog.objects.get(activity=self.a1)
        self.assertEqual((log.previous_owner, log.new_owner, log.changed_by), (self.editor, self.novo, self.editor))
        entry = self.audit(self.a1, action=AuditLog.Action.OWNER_CHANGED).get()
        self.assertEqual((entry.old_value, entry.new_value), ("editor", "novo"))
        notified = set(Notification.objects.filter(activity=self.a1, event_type=Notification.EventType.OWNER_CHANGED)
                       .values_list("recipient__username", flat=True))
        self.assertTrue({"novo"} <= notified)

    def test_choosing_the_current_owner_is_a_quiet_no_op(self):
        response = self.post(self.a1, field="owner", value=self.editor.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["value"], self.editor.pk)
        self.assertFalse(OwnerChangeLog.objects.filter(activity=self.a1).exists())
        self.assertFalse(self.audit(self.a1, action=AuditLog.Action.OWNER_CHANGED).exists())

    def test_changing_the_owner_needs_its_own_permission(self):
        response = self.post(self.a1, user=self.filler, field="owner", value=self.novo.pk)  # pode editar, não trocar
        self.assertEqual(response.status_code, 403)
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.owner, self.editor)
        self.assertFalse(OwnerChangeLog.objects.filter(activity=self.a1).exists())

    def test_invalid_owners_are_refused_and_nothing_changes(self):
        for value in (self.alheio.pk, self.inativo.pk, 999999, "abc", ""):
            response = self.post(self.a1, field="owner", value=value)
            self.assertEqual(response.status_code, 400, value)
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.owner, self.editor)
        self.assertFalse(OwnerChangeLog.objects.filter(activity=self.a1).exists())


# ---------------------------------------------------------------------------
# Endpoint: prazo
# ---------------------------------------------------------------------------


class DeadlineTests(InlineBase):
    def test_a_date_alone_is_saved_at_2359_and_shown_without_a_time(self):
        data = self.post(self.a1, field="requested_deadline", date="2026-10-14", time="").json()
        self.assertEqual(data["display"]["text"], "14/10/2026")
        self.assertEqual(data["value"], {"date": "2026-10-14", "time": ""})
        self.a1.refresh_from_db()
        self.assertEqual(timezone.localtime(self.a1.requested_deadline).strftime("%Y-%m-%d %H:%M"), "2026-10-14 23:59")

    def test_date_and_time(self):
        data = self.post(self.a1, field="requested_deadline", date="2026-10-14", time="17:47").json()
        self.assertEqual(data["display"]["text"], "14/10/2026 17:47")
        self.assertEqual(data["value"], {"date": "2026-10-14", "time": "17:47"})
        entry = self.audit(self.a1, field_name="requested_deadline").get()
        self.assertEqual(entry.user, self.editor)
        self.assertIn("2026-10-14", entry.new_value)

    def test_clearing_the_deadline(self):
        self.post(self.a1, field="requested_deadline", date="2026-10-14", time="09:00")
        data = self.post(self.a1, field="requested_deadline", date="", time="").json()
        self.assertEqual(data["display"]["text"], "Sem prazo")
        self.assertEqual(data["value"], {"date": "", "time": ""})
        self.a1.refresh_from_db()
        self.assertIsNone(self.a1.requested_deadline)

    def test_a_past_deadline_is_flagged_as_late_with_the_number_of_days(self):
        data = self.post(self.a1, field="requested_deadline", date="2020-01-10", time="08:00").json()
        self.assertTrue(data["display"]["is_late"])
        self.assertGreater(data["derived"]["overdue_days"], 1000)
        data = self.post(self.a1, field="requested_deadline", date="2099-01-10", time="08:00").json()
        self.assertFalse(data["display"]["is_late"])
        self.assertEqual(data["derived"]["overdue_days"], 0)

    def test_invalid_values_are_refused_and_the_old_deadline_stays(self):
        self.post(self.a1, field="requested_deadline", date="2026-10-14", time="10:00")
        for date_text, time_text in (("2026-02-30", ""), ("lixo", ""), ("2026-10-14", "99:99"), ("", "10:00")):
            response = self.post(self.a1, field="requested_deadline", date=date_text, time=time_text)
            self.assertEqual(response.status_code, 400, (date_text, time_text))
        self.a1.refresh_from_db()
        self.assertEqual(timezone.localtime(self.a1.requested_deadline).strftime("%Y-%m-%d %H:%M"), "2026-10-14 10:00")

    def test_a_reader_cannot_change_the_deadline(self):
        response = self.post(self.a1, user=self.reader, field="requested_deadline", date="2026-10-14", time="")
        self.assertEqual(response.status_code, 403)
        self.a1.refresh_from_db()
        self.assertIsNone(self.a1.requested_deadline)


# ---------------------------------------------------------------------------
# Regras comuns do endpoint
# ---------------------------------------------------------------------------


class EndpointRulesTests(InlineBase):
    def test_finished_demands_are_locked_for_every_field(self):
        for activity in (self.a_done, self.a_cancel):
            for data in ({"field": "title", "value": "Novo"}, {"field": "owner", "value": self.novo.pk},
                         {"field": "requested_deadline", "date": "2026-10-14", "time": ""}):
                response = self.post(activity, **data)
                self.assertEqual(response.status_code, 400, (activity.status, data["field"]))
                self.assertIn("concluída ou cancelada", response.json()["error"])
            activity.refresh_from_db()
            self.assertNotEqual(activity.title, "Novo")
            self.assertEqual(activity.owner, self.editor)
            self.assertIsNone(activity.requested_deadline)

    def test_business_status_and_other_fields_cannot_be_edited_here(self):
        for field in ("status", "description", "client_site", "", "owner_id", "organization"):
            response = self.post(self.a1, field=field, value="CONCLUIDA")
            self.assertEqual(response.status_code, 400, field)
            self.assertEqual(response.json()["error"], "Este campo não pode ser editado por aqui.")
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.status, Activity.Status.ABERTA)

    def test_another_organization_gets_404_and_nothing_changes(self):
        self.assertEqual(self.post(self.a1, user=self.alheio, field="title", value="Invasão").status_code, 404)
        self.assertEqual(self.post(self.a_foreign, user=self.editor, field="title", value="Invasão").status_code, 404)
        self.a1.refresh_from_db()
        self.a_foreign.refresh_from_db()
        self.assertEqual((self.a1.title, self.a_foreign.title), ("Orçamento Aurora", "Alheia"))

    def test_drafts_are_not_reachable(self):
        self.assertEqual(self.post(self.a_draft, field="title", value="Invasão").status_code, 404)

    def test_login_post_only_and_csrf(self):
        url = reverse("activity-inline-update", args=[self.a1.pk])
        self.client.logout()
        response = self.client.post(url, {"field": "title", "value": "X"}, **AJAX)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.editor)
        self.assertEqual(strict.post(url, {"field": "title", "value": "X"}, **AJAX).status_code, 403)

    def test_the_endpoint_does_not_leave_django_messages_behind(self):
        self.post(self.a1, field="title", value="Sem mensagem")
        self.post(self.a1, user=self.reader, field="title", value="Negado")
        self.assertEqual(list(self.client.get(reverse("activity-list"), {"tab": "todas"}).context["messages"]), [])


# ---------------------------------------------------------------------------
# A lista só oferece edição a quem pode
# ---------------------------------------------------------------------------


class ListTests(InlineBase):
    def page(self, user, **params):
        self.client.force_login(user)
        params.setdefault("tab", "todas")
        return self.client.get(reverse("activity-list"), params)

    def row_html(self, response, activity):
        html = response.content.decode()
        start = html.index(f'<tr data-activity-id="{activity.pk}">')
        return html[start: html.index("</tr>", start)]

    def test_flags_per_person(self):
        response = self.page(self.editor)
        flags = {activity.pk: activity.inline for activity in response.context["activities"]}
        self.assertEqual((flags[self.a1.pk]["title"], flags[self.a1.pk]["owner"], flags[self.a1.pk]["requested_deadline"]), (True, True, True))
        finished = {a.pk: a.inline for a in self.page(self.editor, tab="concluidas").context["activities"]}
        for activity in (self.a_done, self.a_cancel):
            self.assertTrue(finished[activity.pk]["locked"], activity.status)
            self.assertFalse(finished[activity.pk]["title"] or finished[activity.pk]["owner"] or finished[activity.pk]["requested_deadline"])
        filler = {a.pk: a.inline for a in self.page(self.filler).context["activities"]}[self.a1.pk]
        self.assertEqual((filler["title"], filler["owner"], filler["requested_deadline"]), (True, False, True))
        self.assertTrue(flags[self.a1.pk]["client"] and filler["client"])
        self.assertTrue(flags[self.a1.pk]["sector"] and filler["sector"])
        self.assertFalse(finished[self.a_done.pk]["sector"] or finished[self.a_done.pk]["client"])
        self.assertFalse({a.pk: a.inline for a in self.page(self.reader).context["activities"]}[self.a1.pk]["client"])
        reader = {a.pk: a.inline for a in self.page(self.reader).context["activities"]}[self.a1.pk]
        self.assertEqual((reader["title"], reader["owner"], reader["requested_deadline"]), (False, False, False))

    def test_editable_cells_carry_the_markers_and_a_reader_sees_the_page_as_before(self):
        editor_row = self.row_html(self.page(self.editor), self.a1)
        for marker in ('data-inline-field="title"', 'data-inline-field="owner"', 'data-inline-field="requested_deadline"', 'role="button"'):
            self.assertIn(marker, editor_row)
        reader_row = self.row_html(self.page(self.reader), self.a1)
        self.assertNotIn("data-inline-field", reader_row)
        self.assertNotIn("activity-inline-field", reader_row)
        self.assertIn(f'<a href="{reverse("activity-detail", args=[self.a1.pk])}', reader_row)  # o título continua sendo o link
        filler_row = self.row_html(self.page(self.filler), self.a1)
        self.assertNotIn('data-inline-field="owner"', filler_row)
        self.assertIn('data-inline-field="title"', filler_row)

    def test_locked_rows_have_no_markers_for_anyone(self):
        response = self.page(self.editor, tab="concluidas")
        self.assertNotIn("data-inline-field", self.row_html(response, self.a_done))
        self.assertNotIn("data-inline-field", self.row_html(response, self.a_cancel))

    def test_client_cell_opens_the_editor_at_step_two_only_for_who_can_edit(self):
        edit_url = reverse("activity-edit", args=[self.a1.pk])
        editor_row = self.row_html(self.page(self.editor), self.a1)
        self.assertIn(f'<a class="demand-board__context-link" href="{edit_url}?passo=2&amp;next=', editor_row)
        self.assertIn("data-activity-action", editor_row)
        self.assertNotIn("data-activity-navigate", editor_row)  # ao salvar, a lista recarrega (filtros e aba ficam na URL)
        self.assertIn("<strong>Sem cliente</strong>", editor_row)  # o texto da célula é o de sempre
        reader_row = self.row_html(self.page(self.reader), self.a1)
        self.assertNotIn("demand-board__context-link", reader_row)
        self.assertNotIn("passo=2", reader_row)
        locked = self.page(self.editor, tab="concluidas")
        self.assertNotIn("passo=2", self.row_html(locked, self.a_done))
        self.assertNotIn("passo=2", self.row_html(locked, self.a_cancel))

    def test_drafts_listed_for_their_author_offer_no_inline_edit_at_all(self):
        # A rota inline devolve 404 para rascunho: a lista não pode oferecer o que o servidor recusa.
        response = self.page(self.editor, tab="minhas")
        flags = {activity.pk: activity.inline for activity in response.context["activities"]}
        self.assertIn(self.a_draft.pk, flags)
        self.assertFalse(any(flags[self.a_draft.pk][key] for key in ("title", "client", "requested_deadline", "owner")))
        row = self.row_html(response, self.a_draft)
        self.assertNotIn("data-inline-field", row)
        self.assertNotIn("passo=2", row)

    def test_the_page_wires_the_script_the_table_and_the_overlay(self):
        html = self.page(self.editor).content.decode()
        self.assertIn("data-activity-list", html)
        self.assertIn(reverse("activity-inline-update", args=[999999999]), html)
        self.assertIn('id="activity-inline-overlay-root"', html)
        self.assertIn("js/activity-inline-edit.js", html)
        self.assertNotIn("chevron", html.lower().split("demand-board__table")[1])  # nenhuma seta nas células

    def test_deadline_text_in_the_list_follows_the_display_rule(self):
        ActivityService.update_activity(self.a1, self.editor, requested_deadline=parse_deadline("2026-10-14", ""))
        html = self.row_html(self.page(self.editor), self.a1)
        self.assertIn("<span>14/10/2026</span>", html)
        self.assertNotIn("23:59", html)
        ActivityService.update_activity(Activity.objects.get(pk=self.a1.pk), self.editor,
                                        requested_deadline=parse_deadline("2026-10-14", "17:47"))
        self.assertIn("<span>14/10/2026 17:47</span>", self.row_html(self.page(self.editor), self.a1))

    def test_number_of_queries_does_not_grow_with_the_rows(self):
        def queries():
            self.client.force_login(self.editor)
            with CaptureQueriesContext(connection) as context:
                self.client.get(reverse("activity-list"), {"tab": "todas"})
            return len(context)

        queries()  # aquece os caches (a primeira chamada paga consultas que as seguintes não pagam)
        few = queries()
        for index in range(12):
            self.activity(f"Extra {index}", self.editor)
        self.assertEqual(queries(), few)

    def test_inline_flags_ask_the_authorization_engine_once_for_the_whole_list(self):
        activities = list(Activity.objects.filter(organization=self.org).exclude(status=Activity.Status.RASCUNHO))
        with CaptureQueriesContext(connection) as small:
            inline_flags(self.editor, activities[:1])
        for index in range(10):
            self.activity(f"Mais {index}", self.editor)
        activities = list(Activity.objects.filter(organization=self.org).exclude(status=Activity.Status.RASCUNHO))
        with CaptureQueriesContext(connection) as big:
            inline_flags(self.editor, activities)
        self.assertEqual(len(small), len(big))


class AdapterTests(InlineBase):
    def test_update_returns_structured_data_for_each_field(self):
        result = ActivityInlineService.update(
            user=self.editor, activity=self.a1, field="owner", data={"value": str(self.novo.pk)}
        )
        self.assertEqual(result["value"], self.novo.pk)
        self.assertEqual(json.loads(json.dumps(result))["display"]["text"], "Nova Pessoa")

    def test_unknown_field_is_refused(self):
        with self.assertRaisesMessage(ActivityError, "não pode ser editado"):
            ActivityInlineService.update(user=self.editor, activity=self.a1, field="status", data={"value": "CONCLUIDA"})


# ---------------------------------------------------------------------------
# Entrega 2: setor
# ---------------------------------------------------------------------------


class SectorBase(InlineBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.destino = Sector.objects.create(organization=cls.org, name="Engenharia", color="#2563EB")
        cls.setor_inativo = Sector.objects.create(organization=cls.org, name="Antigo", is_active=False)
        cls.setor_alheio = Sector.objects.create(organization=cls.other_org, name="Alheio")
        make = core_models.ActivityStage.objects.create
        cond = core_models.WorkflowStatus.objects.create
        cls.stage_a = make(organization=cls.org, sector=cls.sector, name="Triagem", color="#EF4444", is_default=True)
        cls.cond_a = cond(organization=cls.org, sector=cls.sector, domain="activity", name="Normal", color="#94A3B8", is_default=True)
        cls.stage_b = make(organization=cls.org, sector=cls.destino, name="Projeto", color="#22C55E", is_default=True)
        cls.cond_b = cond(organization=cls.org, sector=cls.destino, domain="activity", name="Em análise", color="#F59E0B", is_default=True)
        Activity.objects.filter(pk=cls.a1.pk).update(stage=cls.stage_a, condition=cls.cond_a)
        cls.a1.refresh_from_db()
        cls.admin = make_user("admin", cls.org, FULL + [catalog.SETOR_EDITAR])
        # Edita só no Comercial (concessão por setor): não tem acesso ao destino.
        cls.so_comercial = make_user("socomercial", cls.org)
        grant_action(cls.so_comercial, catalog.ATIVIDADE_EDITAR, organization=cls.org, sector=cls.sector)
        # Cria setor, mas só edita demandas do Comercial: o destino de um setor novo ficaria fora do seu alcance.
        cls.criador_limitado = make_user("limitado", cls.org, [catalog.SETOR_EDITAR])
        grant_action(cls.criador_limitado, catalog.ATIVIDADE_EDITAR, organization=cls.org, sector=cls.sector)

    def fresh(self, activity=None):
        return Activity.objects.get(pk=(activity or self.a1).pk)

    def state(self, activity=None):
        activity = self.fresh(activity)
        return (activity.sector_id, activity.stage_id, activity.condition_id)

    def untouched(self):
        self.assertEqual(self.state(), (self.sector.pk, self.stage_a.pk, self.cond_a.pk))
        self.assertFalse(AuditLog.objects.filter(activity=self.a1, field_name="setor").exists())


class SectorServiceTests(SectorBase):
    """O que vale para QUALQUER tela está no Service, não no adapter."""

    def move(self, user=None, sector=None, activity=None):
        return ActivityService.update_activity(self.fresh(activity), user or self.editor, sector=sector or self.destino)

    def test_moving_resets_stage_and_condition_to_the_new_sectors_defaults_and_audits_the_three_changes(self):
        activity = self.move()
        self.assertEqual((activity.sector_id, activity.stage_id, activity.condition_id), (self.destino.pk, self.stage_b.pk, self.cond_b.pk))
        entries = {entry.field_name: (entry.old_value, entry.new_value) for entry in self.audit(activity, reason__startswith="Setor alterado")}
        self.assertEqual(entries, {
            "setor": ("Comercial", "Engenharia"), "etapa": ("Triagem", "Projeto"), "condição": ("Normal", "Em análise"),
        })

    def test_destination_authorization_is_checked_before_any_write(self):
        with self.assertRaises(ActivityPermissionError):
            self.move(user=self.so_comercial)
        self.untouched()

    def test_a_grant_in_the_destination_allows_the_move(self):
        grant_action(self.so_comercial, catalog.ATIVIDADE_EDITAR, organization=self.org, sector=self.destino)
        self.move(user=self.so_comercial)
        self.assertEqual(self.state()[0], self.destino.pk)

    def test_the_same_person_can_still_edit_other_fields_without_touching_the_sector(self):
        ActivityService.update_activity(self.fresh(), self.so_comercial, title="Só o título", sector=self.sector)
        self.assertEqual(self.fresh().title, "Só o título")

    def test_inactive_and_foreign_destinations_are_refused(self):
        with self.assertRaisesMessage(ActivityError, "inativo"):
            self.move(sector=self.setor_inativo)
        with self.assertRaisesMessage(ActivityError, "outra organização"):
            self.move(sector=self.setor_alheio)
        self.untouched()

    def test_a_pending_approval_blocks_the_move(self):
        ActivityPendency.objects.create(
            activity=self.a1, reason=ActivityPendency.Reason.APROVACAO_GESTOR, comment="Aguardando", opened_by=self.editor,
        )
        with self.assertRaisesMessage(ActivityError, "Resolva a pendência"):
            self.move()
        self.untouched()

    def test_a_failure_in_the_middle_rolls_everything_back(self):
        # a 2ª auditoria falha: setor, etapa, condição e as auditorias já gravadas voltam juntos
        with mock.patch("activities.services.AuditService.log", side_effect=[None, RuntimeError("falha no meio")]):
            with self.assertRaisesMessage(RuntimeError, "falha no meio"):
                self.move()
        self.untouched()
        self.assertFalse(AuditLog.objects.filter(activity=self.a1, field_name__in=("etapa", "condição")).exists())

    def test_the_other_organizations_demand_cannot_be_moved_by_name(self):
        with self.assertRaises(ActivityError):
            ActivityService.update_activity(self.a_foreign, self.alheio, sector=self.destino)


class ClientSiteInvariantTests(SectorBase):
    """A obra pertence ao cliente da demanda: vale também fora do formulário (cliente sem obra e obra sem cliente valem)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.c1 = core_models.Client.objects.create(organization=cls.org, name="Alfa")
        cls.c2 = core_models.Client.objects.create(organization=cls.org, name="Beta")
        cls.c_alheio = core_models.Client.objects.create(organization=cls.other_org, name="Gama")
        cls.s1 = core_models.Site.objects.create(organization=cls.org, name="Obra Alfa", client=cls.c1)
        cls.s2 = core_models.Site.objects.create(organization=cls.org, name="Obra Beta", client=cls.c2)
        cls.s_livre = core_models.Site.objects.create(organization=cls.org, name="Obra livre")

    def edit(self, **fields):
        return ActivityService.update_activity(self.fresh(), self.editor, **fields)

    def test_a_site_of_another_client_is_refused_and_nothing_changes(self):
        with self.assertRaisesMessage(ActivityError, "pertence a outro cliente"):
            self.edit(client=self.c1, site=self.s2)
        activity = self.fresh()
        self.assertEqual((activity.client_id, activity.site_id), (None, None))

    def test_matching_free_and_missing_values_are_accepted(self):
        self.edit(client=self.c1, site=self.s1)
        self.edit(client=self.c1, site=self.s_livre)  # obra sem cliente vale para qualquer cliente
        self.edit(client=self.c2)  # trocar só o cliente com obra livre continua coerente
        self.edit(client=None, site=None)
        self.assertEqual((self.fresh().client_id, self.fresh().site_id), (None, None))

    def test_changing_only_the_site_is_checked_against_the_current_client(self):
        self.edit(client=self.c1)
        with self.assertRaisesMessage(ActivityError, "pertence a outro cliente"):
            self.edit(site=self.s2)

    def test_old_inconsistent_data_can_still_be_saved_when_client_and_site_do_not_change(self):
        Activity.objects.filter(pk=self.a1.pk).update(client=self.c1, site=self.s2)
        self.edit(client=self.c1, site=self.s2, title="Ainda salva")
        self.assertEqual(self.fresh().title, "Ainda salva")

    def test_other_organizations_client_or_site_is_refused(self):
        with self.assertRaisesMessage(ActivityError, "outra organização"):
            self.edit(client=self.c_alheio)


class SectorEndpointTests(SectorBase):
    def move(self, activity=None, user=None, **data):
        return self.post(activity or self.a1, user=user, field="sector", **data)

    def test_changing_the_sector_answers_with_structured_data_and_the_new_defaults(self):
        response = self.move(value=self.destino.pk)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["ok"], True)
        self.assertEqual(body["value"], self.destino.pk)
        self.assertEqual(body["display"], {"id": self.destino.pk, "name": "Engenharia", "color": "#2563EB", "text_color": self.destino.text_color})
        self.assertEqual(body["derived"]["stage"]["name"], "Projeto")
        self.assertEqual(body["derived"]["stage"]["color"], "#22C55E")
        self.assertEqual(body["derived"]["condition"]["name"], "Em análise")
        self.assertNotIn("created_sector", body)
        self.assertEqual(self.state(), (self.destino.pk, self.stage_b.pk, self.cond_b.pk))
        self.assertEqual(self.audit(self.a1, reason__startswith="Setor alterado").count(), 3)

    def test_the_same_sector_is_a_no_op_without_audit(self):
        response = self.move(value=self.sector.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["derived"]["stage"]["name"], "Triagem")
        self.assertFalse(self.audit(self.a1, field_name="setor").exists())

    def test_a_sector_without_defaults_answers_null_for_stage_and_condition(self):
        vazio = Sector.objects.create(organization=self.org, name="Vazio")
        body = self.move(value=vazio.pk).json()
        self.assertEqual(body["derived"], {"stage": None, "condition": None})
        self.assertEqual(self.state(), (vazio.pk, None, None))

    def test_creating_a_sector_applies_it_in_one_step(self):
        response = self.move(user=self.admin, new_name="  Qualidade  ", new_color="#16a34a")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        novo = Sector.objects.get(organization=self.org, name="Qualidade")
        self.assertEqual((novo.color, novo.created_by_id, novo.is_active), ("#16A34A", self.admin.pk, True))
        self.assertEqual(body["created_sector"], {"id": novo.pk, "name": "Qualidade", "color": "#16A34A", "text_color": novo.text_color})
        self.assertEqual(body["display"]["id"], novo.pk)
        self.assertEqual(body["derived"], {"stage": None, "condition": None})  # setor novo nasce sem etapas nem condições
        self.assertEqual(self.state(), (novo.pk, None, None))
        self.assertEqual(self.audit(self.a1, reason__startswith="Setor alterado").count(), 3)

    def test_creating_requires_the_sector_permission_and_creates_nothing_without_it(self):
        response = self.move(user=self.editor, new_name="Qualidade", new_color="#16A34A")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Sector.objects.filter(name="Qualidade").exists())
        self.untouched()

    def test_when_the_move_is_refused_the_new_sector_is_not_left_behind(self):
        # tem permissão para criar setor, mas não para editar demandas no setor que acabou de criar
        response = self.move(user=self.criador_limitado, new_name="Qualidade", new_color="#16A34A")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Sector.objects.filter(name="Qualidade").exists())
        self.untouched()
        for activity in (self.a_done, self.a_cancel):
            response = self.move(activity=activity, user=self.admin, new_name="Qualidade", new_color="#16A34A")
            self.assertEqual(response.status_code, 400, activity.status)
            self.assertFalse(Sector.objects.filter(name="Qualidade").exists())

    def test_invalid_new_sectors_are_refused_with_a_message_and_create_nothing(self):
        count = Sector.objects.count()
        cases = (
            ({"new_name": "engenharia", "new_color": "#16A34A"}, "Já existe"),
            ({"new_name": "Qualidade", "new_color": "#123456"}, "paleta"),
            ({"new_name": "   ", "new_color": "#16A34A"}, "nome do setor"),
            ({"new_name": "x" * 151, "new_color": "#16A34A"}, "150 caracteres"),
        )
        for data, text in cases:
            response = self.move(user=self.admin, **data)
            self.assertEqual(response.status_code, 400, data)
            self.assertIn(text, response.json()["error"], data)
        self.assertEqual(Sector.objects.count(), count)
        self.untouched()

    def test_refusals_are_400_403_404_and_change_nothing(self):
        self.assertEqual(self.move(user=self.reader, value=self.destino.pk).status_code, 403)
        self.assertEqual(self.move(user=self.so_comercial, value=self.destino.pk).status_code, 403)
        self.assertEqual(self.move(value=self.setor_inativo.pk).status_code, 400)
        foreign = self.move(value=self.setor_alheio.pk)
        self.assertEqual((foreign.status_code, foreign.json()["error"]), (400, "O setor escolhido não existe nesta organização."))
        for value in ("", "abc", "0", "999999"):
            self.assertEqual(self.move(value=value).status_code, 400, value)
        self.assertEqual(self.move(activity=self.a_done, value=self.destino.pk).status_code, 400)
        self.assertEqual(self.move(activity=self.a_draft, value=self.destino.pk).status_code, 404)
        self.assertEqual(self.move(user=self.alheio, value=self.destino.pk).status_code, 404)
        self.untouched()

    def test_a_pending_approval_is_reported_and_nothing_changes(self):
        ActivityPendency.objects.create(
            activity=self.a1, reason=ActivityPendency.Reason.APROVACAO_GESTOR, comment="Aguardando", opened_by=self.editor,
        )
        response = self.move(value=self.destino.pk)
        self.assertEqual((response.status_code, "Resolva a pendência" in response.json()["error"]), (400, True))
        self.untouched()

    def test_the_endpoint_leaves_no_django_messages_behind(self):
        self.move(value=self.destino.pk)
        self.move(user=self.reader, value=self.sector.pk)
        self.assertEqual(list(self.client.get(reverse("activity-list"), {"tab": "todas"}).context["messages"]), [])


class OptionsEndpointTests(SectorBase):
    def get(self, activity=None, user=None, **params):
        self.client.force_login(user or self.editor)
        return self.client.get(reverse("activity-inline-options", args=[(activity or self.a1).pk]), params)

    def test_sector_options_list_the_active_sectors_of_the_organization_with_colors(self):
        response = self.get(campo="sector")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        names = [item["name"] for item in body["items"]]
        self.assertEqual(names, ["Comercial", "Engenharia"])  # sem o inativo e sem o de outra organização
        self.assertEqual(body["current_id"], self.sector.pk)
        self.assertEqual(body["allow_clear"], False)
        item = {item["name"]: item for item in body["items"]}["Engenharia"]
        self.assertEqual(item, {"id": self.destino.pk, "name": "Engenharia", "color": "#2563EB", "text_color": self.destino.text_color})

    def test_can_create_follows_the_sector_permission(self):
        self.assertFalse(self.get(campo="sector").json()["can_create"])
        self.assertTrue(self.get(user=self.admin, campo="sector").json()["can_create"])

    def test_who_cannot_edit_the_demand_does_not_get_the_list(self):
        self.assertEqual(self.get(user=self.reader, campo="sector").status_code, 403)
        self.assertEqual(self.get(user=self.alheio, campo="sector").status_code, 404)
        self.assertEqual(self.get(activity=self.a_draft, campo="sector").status_code, 404)
        self.assertEqual(self.get(activity=self.a_done, campo="sector").status_code, 400)

    def test_unknown_fields_have_no_list(self):
        for campo in ("", "status", "owner", "title"):
            response = self.get(campo=campo)
            self.assertEqual((response.status_code, response.json()["error"]), (400, "Este campo não tem lista de opções."), campo)

    def test_login_and_get_only(self):
        url = reverse("activity-inline-options", args=[self.a1.pk])
        self.client.logout()
        response = self.client.get(url, {"campo": "sector"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])
        self.client.force_login(self.editor)
        self.assertEqual(self.client.put(url).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
        # POST existe (criar e editar etapas/condições), mas não para o setor: o setor é criado pelo próprio campo
        refused = self.client.post(url, {"campo": "sector", "acao": "criar", "name": "X"}, **AJAX)
        self.assertEqual((refused.status_code, refused.json()["error"]), (400, "Este campo não tem opções para gerir."))


# ---------------------------------------------------------------------------
# Entrega 2C: estágio e status (condição) + opções criadas/editadas ali mesmo
# ---------------------------------------------------------------------------


class OptionBase(SectorBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        make = core_models.ActivityStage.objects.create
        cond = core_models.WorkflowStatus.objects.create
        cls.stage_a2 = make(organization=cls.org, sector=cls.sector, name="Execução", color="#2563EB", order=2)
        cls.stage_off = make(organization=cls.org, sector=cls.sector, name="Antiga", color="#64748B", order=3, is_active=False)
        cls.cond_a2 = cond(organization=cls.org, sector=cls.sector, domain="activity", name="Aguardando cliente", color="#F59E0B", order=2)
        cls.cond_off = cond(organization=cls.org, sector=cls.sector, domain="activity", name="Antiga", color="#64748B", order=3, is_active=False)
        cls.cond_task = cond(organization=cls.org, sector=cls.sector, domain="task", name="Da tarefa", color="#EF4444")
        see = [catalog.ATIVIDADE_VISUALIZAR, catalog.ATIVIDADE_VISUALIZAR_TODAS]
        cls.definidor = make_user("definidor", cls.org, see + [catalog.ATIVIDADE_DEFINIR_ETAPA, catalog.ATIVIDADE_DEFINIR_CONDICAO])
        cls.legado = make_user("legado", cls.org, see + [catalog.ATIVIDADE_MOVER_ESTAGIO])  # ação antiga: só estágio
        cls.gestor = make_user(
            "gestor", cls.org,
            see + [catalog.ATIVIDADE_DEFINIR_ETAPA, catalog.ATIVIDADE_DEFINIR_CONDICAO, catalog.ETAPA_GERIR, catalog.CONDICAO_GERIR],
        )
        # Gere etapas e condições SÓ do setor Engenharia: não vale para uma demanda do Comercial.
        cls.gestor_destino = make_user("gdestino", cls.org, see)
        for action in (catalog.ETAPA_GERIR, catalog.CONDICAO_GERIR, catalog.ATIVIDADE_DEFINIR_ETAPA, catalog.ATIVIDADE_DEFINIR_CONDICAO):
            grant_action(cls.gestor_destino, action, organization=cls.org, sector=cls.destino)
        cls.a_nosetor = Activity.objects.create(
            organization=cls.org, title="Sem setor", owner=cls.editor, created_by=cls.editor, status=Activity.Status.ABERTA,
        )

    def opt_get(self, activity=None, user=None, **params):
        self.client.force_login(user or self.definidor)
        return self.client.get(reverse("activity-inline-options", args=[(activity or self.a1).pk]), params)

    def opt_post(self, activity=None, user=None, **data):
        self.client.force_login(user or self.gestor)
        return self.client.post(reverse("activity-inline-options", args=[(activity or self.a1).pk]), data, **AJAX)

    def set(self, field, value, activity=None, user=None):
        return self.post(activity or self.a1, user=user or self.definidor, field=field, value=value)


class TerminalPolicyTests(OptionBase):
    """Demanda encerrada não troca de estágio nem de status em NENHUMA tela: a regra está no Service."""

    def test_the_service_refuses_both_changes_on_finished_demands(self):
        for activity in (self.a_done, self.a_cancel):
            with self.assertRaisesMessage(ActivityError, "concluída ou cancelada") as caught:
                ActivityService.set_stage(self.fresh(activity), self.stage_a2, self.definidor)
            self.assertNotIsInstance(caught.exception, ActivityPermissionError)
            with self.assertRaisesMessage(ActivityError, "concluída ou cancelada"):
                ActivityService.set_condition(self.fresh(activity), self.cond_a2, self.definidor)
            self.assertEqual((self.fresh(activity).stage_id, self.fresh(activity).condition_id), (None, None))

    def test_the_permission_is_checked_before_the_state(self):
        with self.assertRaises(ActivityPermissionError):
            ActivityService.set_stage(self.fresh(self.a_done), self.stage_a2, self.reader)

    def test_open_demands_still_change(self):
        ActivityService.set_stage(self.fresh(), self.stage_a2, self.definidor)
        ActivityService.set_condition(self.fresh(), self.cond_a2, self.definidor)
        self.assertEqual((self.fresh().stage_id, self.fresh().condition_id), (self.stage_a2.pk, self.cond_a2.pk))

    def test_the_kanban_endpoints_obey_the_same_rule(self):
        self.client.force_login(self.definidor)
        for activity in (self.a_done, self.a_cancel):
            response = self.client.post(reverse("kanban-set-stage", args=["demandas", activity.pk]), {"stage_id": self.stage_a2.pk}, **AJAX)
            self.assertEqual(response.status_code, 403, activity.status)
            self.assertIn("concluída ou cancelada", response.json()["message"])
            response = self.client.post(reverse("kanban-set-condition", args=["demandas", activity.pk]), {"condition_id": self.cond_a2.pk}, **AJAX)
            self.assertEqual(response.status_code, 403, activity.status)
            self.assertEqual(self.fresh(activity).stage_id, None)
        ok = self.client.post(reverse("kanban-set-stage", args=["demandas", self.a1.pk]), {"stage_id": self.stage_a2.pk}, **AJAX)
        self.assertEqual(ok.status_code, 200)

    def test_the_form_path_cannot_move_a_finished_demand_either(self):
        with self.assertRaises(ActivityError):
            ActivityService.update_activity(self.fresh(self.a_done), self.admin, stage=self.stage_a2)


class StageConditionEndpointTests(OptionBase):
    def test_choosing_a_stage_answers_with_structured_data_audits_and_records_the_time(self):
        response = self.set("stage", self.stage_a2.pk)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["value"], self.stage_a2.pk)
        self.assertEqual(body["display"], {"id": self.stage_a2.pk, "name": "Execução", "color": "#2563EB", "text_color": self.stage_a2.text_color})
        activity = self.fresh()
        self.assertEqual(activity.stage_id, self.stage_a2.pk)
        self.assertIsNotNone(activity.stage_changed_at)
        entry = self.audit(self.a1, field_name="etapa").get()
        self.assertEqual((entry.old_value, entry.new_value), ("Triagem", "Execução"))

    def test_the_same_stage_or_condition_is_a_no_op_without_audit(self):
        self.assertEqual(self.set("stage", self.stage_a.pk).status_code, 200)
        self.assertEqual(self.set("condition", self.cond_a.pk).status_code, 200)
        self.assertFalse(self.audit(self.a1, field_name__in=("etapa", "condição")).exists())

    def test_choosing_a_condition_and_clearing_it(self):
        body = self.set("condition", self.cond_a2.pk).json()
        self.assertEqual((body["value"], body["display"]["name"]), (self.cond_a2.pk, "Aguardando cliente"))
        self.assertEqual(self.audit(self.a1, field_name="condição").get().new_value, "Aguardando cliente")
        cleared = self.set("condition", "").json()
        self.assertEqual((cleared["value"], cleared["display"]), ("", None))
        self.assertIsNone(self.fresh().condition_id)
        self.assertEqual(self.audit(self.a1, field_name="condição").order_by("-id").first().new_value, "Sem condição")

    def test_the_stage_cannot_be_cleared(self):
        for value in ("", "  "):
            response = self.set("stage", value)
            self.assertEqual((response.status_code, response.json()["error"]), (400, "Escolha o estágio."))
        self.assertEqual(self.fresh().stage_id, self.stage_a.pk)

    def test_options_of_another_sector_inactive_other_domain_or_organization_are_refused(self):
        foreign = core_models.ActivityStage.objects.create(organization=self.other_org, sector=self.setor_alheio, name="Alheia")
        cases = (
            ("stage", self.stage_b.pk, "não pertence ao setor atual"),
            ("stage", self.stage_off.pk, "inativa"),
            ("stage", foreign.pk, "não existe nesta organização"),
            ("stage", "abc", "Escolha o estágio."),
            ("stage", 999999, "não existe nesta organização"),
            ("condition", self.cond_b.pk, "não pertence ao setor atual"),
            ("condition", self.cond_off.pk, "inativa"),
            ("condition", self.cond_task.pk, "não existe nesta organização"),  # condição de TAREFA não serve para demanda
            ("condition", "abc", "Escolha o status."),
        )
        for field, value, text in cases:
            response = self.set(field, value)
            self.assertEqual(response.status_code, 400, (field, value))
            self.assertIn(text, response.json()["error"], (field, value))
        self.assertEqual((self.fresh().stage_id, self.fresh().condition_id), (self.stage_a.pk, self.cond_a.pk))

    def test_permissions_per_action_and_state(self):
        # sem as ações de definir: 403 (quem só edita título/prazo não mexe em estágio nem status)
        self.assertEqual(self.set("stage", self.stage_a2.pk, user=self.editor).status_code, 403)
        self.assertEqual(self.set("condition", self.cond_a2.pk, user=self.editor).status_code, 403)
        self.assertEqual(self.set("stage", self.stage_a2.pk, user=self.reader).status_code, 403)
        # a ação antiga "mover estágio" ainda vale para o estágio e só para ele
        self.assertEqual(self.set("stage", self.stage_a2.pk, user=self.legado).status_code, 200)
        self.assertEqual(self.set("condition", self.cond_a2.pk, user=self.legado).status_code, 403)
        # concluída/cancelada: regra de estado (400), rascunho e outra organização: 404
        self.assertEqual(self.set("stage", self.stage_a2.pk, activity=self.a_done).status_code, 400)
        self.assertEqual(self.set("condition", self.cond_a2.pk, activity=self.a_cancel).status_code, 400)
        self.assertEqual(self.set("stage", self.stage_a2.pk, activity=self.a_draft).status_code, 404)
        self.assertEqual(self.set("stage", self.stage_a2.pk, user=self.alheio).status_code, 404)
        self.assertEqual(self.fresh().condition_id, self.cond_a.pk)

    def test_a_demand_without_a_sector_has_no_valid_option(self):
        response = self.set("stage", self.stage_a.pk, activity=self.a_nosetor)
        self.assertEqual(response.status_code, 400)
        self.assertIn("não pertence ao setor atual", response.json()["error"])

    def test_no_django_messages_are_left_behind(self):
        self.set("stage", self.stage_a2.pk)
        self.set("stage", self.stage_b.pk)
        self.assertEqual(list(self.client.get(reverse("activity-list"), {"tab": "todas"}).context["messages"]), [])


class OptionListTests(OptionBase):
    def test_stage_options_are_the_active_ones_of_the_demands_own_sector_in_order(self):
        body = self.opt_get(campo="stage").json()
        self.assertEqual([item["name"] for item in body["items"]], ["Triagem", "Execução"])  # sem a inativa e sem as de outro setor
        self.assertEqual((body["current_id"], body["allow_clear"], body["sector_name"]), (self.stage_a.pk, False, "Comercial"))
        self.assertEqual(body["items"][1], {"id": self.stage_a2.pk, "name": "Execução", "color": "#2563EB", "text_color": self.stage_a2.text_color})

    def test_condition_options_only_list_the_demand_domain_and_can_be_cleared(self):
        body = self.opt_get(campo="condition").json()
        self.assertEqual([item["name"] for item in body["items"]], ["Normal", "Aguardando cliente"])
        self.assertEqual((body["current_id"], body["allow_clear"]), (self.cond_a.pk, True))

    def test_the_options_follow_the_sector_after_it_changes(self):
        ActivityService.update_activity(self.fresh(), self.editor, sector=self.destino)
        self.assertEqual([item["name"] for item in self.opt_get(campo="stage").json()["items"]], ["Projeto"])

    def test_create_and_manage_follow_the_manage_permission_in_the_demands_sector(self):
        plain = self.opt_get(campo="stage").json()
        self.assertEqual((plain["can_create"], plain["can_manage"], plain["manage_url"]), (False, False, ""))
        manager = self.opt_get(user=self.gestor, campo="stage").json()
        self.assertEqual((manager["can_create"], manager["can_manage"]), (True, True))
        self.assertEqual(manager["manage_url"], f"{reverse('config-etapas-status')}?domain=demandas&sector={self.sector.pk}")
        # gere só o setor Engenharia: não gere as opções de uma demanda do Comercial (e nem sequer pode defini-las lá)
        self.assertEqual(self.opt_get(user=self.gestor_destino, campo="stage").status_code, 403)

    def test_refusals(self):
        self.assertEqual(self.opt_get(user=self.editor, campo="stage").status_code, 403)  # sem a ação de definir
        self.assertEqual(self.opt_get(user=self.reader, campo="condition").status_code, 403)
        self.assertEqual(self.opt_get(user=self.legado, campo="condition").status_code, 403)
        self.assertEqual(self.opt_get(user=self.legado, campo="stage").status_code, 200)
        self.assertEqual(self.opt_get(activity=self.a_done, campo="stage").status_code, 400)
        no_sector = self.opt_get(activity=self.a_nosetor, campo="stage")
        self.assertEqual((no_sector.status_code, no_sector.json()["error"]), (400, "Defina o setor da demanda antes de escolher."))
        self.assertEqual(self.opt_get(activity=self.a_draft, campo="stage").status_code, 404)
        self.assertEqual(self.opt_get(user=self.alheio, campo="stage").status_code, 404)


class OptionManageTests(OptionBase):
    def test_creating_a_stage_answers_201_and_the_option_shows_up_in_the_list(self):
        response = self.opt_post(campo="stage", acao="criar", name="  Revisão  ", color="#16a34a")
        self.assertEqual(response.status_code, 201)
        item = response.json()["item"]
        created = core_models.ActivityStage.objects.get(pk=item["id"])
        self.assertEqual((created.name, created.color, created.sector_id, created.created_by_id, created.is_default), ("Revisão", "#16A34A", self.sector.pk, self.gestor.pk, False))
        self.assertEqual(item, {"id": created.pk, "name": "Revisão", "color": "#16A34A", "text_color": created.text_color})
        self.assertEqual(created.order, 4)  # depois das já existentes
        self.assertIn("Revisão", [i["name"] for i in self.opt_get(user=self.gestor, campo="stage").json()["items"]])
        self.assertEqual(self.fresh().stage_id, self.stage_a.pk, "criar a opção não muda a demanda")

    def test_creating_a_condition_uses_the_demand_domain_and_a_neutral_default_color(self):
        item = self.opt_post(campo="condition", acao="criar", name="Bloqueada").json()["item"]
        created = core_models.WorkflowStatus.objects.get(pk=item["id"])
        self.assertEqual((created.domain, created.sector_id, created.color, created.is_default), ("activity", self.sector.pk, "#94A3B8", False))

    def test_editing_name_and_color(self):
        response = self.opt_post(campo="stage", acao="editar", option_id=self.stage_a2.pk, name="Execução 2", color="#EF4444")
        self.assertEqual(response.status_code, 200)
        self.stage_a2.refresh_from_db()
        self.assertEqual((self.stage_a2.name, self.stage_a2.color), ("Execução 2", "#EF4444"))
        self.assertEqual(response.json()["item"]["text_color"], self.stage_a2.text_color)
        self.opt_post(campo="condition", acao="editar", option_id=self.cond_a2.pk, color="#16A34A")  # só a cor
        self.cond_a2.refresh_from_db()
        self.assertEqual((self.cond_a2.name, self.cond_a2.color), ("Aguardando cliente", "#16A34A"))
        self.assertTrue(self.stage_a2.is_active and not self.stage_a2.is_default, "inativar e padrão ficam na tela de configuração")

    def test_the_manage_permission_is_checked_in_the_demands_sector(self):
        for user in (self.definidor, self.editor, self.reader, self.gestor_destino):
            response = self.opt_post(user=user, campo="stage", acao="criar", name="Nova")
            self.assertEqual(response.status_code, 403, user.username)
        self.assertFalse(core_models.ActivityStage.objects.filter(name="Nova").exists())
        allowed = self.opt_post(user=self.gestor_destino, activity=self.fresh(self.a1), campo="stage", acao="criar", name="Nova")
        self.assertEqual(allowed.status_code, 403)
        ActivityService.update_activity(self.fresh(), self.admin, sector=self.destino)
        self.assertEqual(self.opt_post(user=self.gestor_destino, campo="stage", acao="criar", name="Nova").status_code, 201)

    def test_invalid_requests_are_400_and_change_nothing(self):
        count = core_models.ActivityStage.objects.count()
        cases = (
            ({"campo": "stage", "acao": "criar", "name": "triagem"}, "Já existe"),
            ({"campo": "stage", "acao": "criar", "name": "   "}, "Informe o nome"),
            ({"campo": "stage", "acao": "criar", "name": "Nova", "color": "#123456"}, "paleta"),
            ({"campo": "stage", "acao": "editar", "option_id": self.stage_a2.pk, "name": "Triagem"}, "Já existe"),
            ({"campo": "stage", "acao": "editar", "option_id": self.stage_a2.pk, "name": ""}, "Informe o nome"),
            ({"campo": "stage", "acao": "editar", "option_id": self.stage_a2.pk, "color": "#123456"}, "paleta"),
            ({"campo": "stage", "acao": "editar", "option_id": self.stage_b.pk, "name": "X"}, "não existe neste setor"),
            ({"campo": "stage", "acao": "editar", "option_id": "abc", "name": "X"}, "não existe neste setor"),
            ({"campo": "condition", "acao": "editar", "option_id": self.cond_task.pk, "name": "X"}, "não existe neste setor"),
            ({"campo": "condition", "acao": "criar", "name": "normal"}, "Já existe"),
            ({"campo": "owner", "acao": "criar", "name": "X"}, "não tem opções"),
            ({"campo": "stage", "acao": "apagar", "name": "X"}, "Ação desconhecida"),
        )
        for data, text in cases:
            response = self.opt_post(**data)
            self.assertEqual(response.status_code, 400, data)
            self.assertIn(text, response.json()["error"], data)
        self.assertEqual(core_models.ActivityStage.objects.count(), count)
        self.stage_a2.refresh_from_db()
        self.assertEqual((self.stage_a2.name, self.stage_a2.color), ("Execução", "#2563EB"))

    def test_a_demand_without_a_sector_has_no_options_to_manage(self):
        response = self.opt_post(activity=self.a_nosetor, campo="stage", acao="criar", name="Nova")
        self.assertEqual((response.status_code, response.json()["error"]), (400, "Defina o setor da demanda antes de gerir as opções."))

    def test_other_organizations_and_drafts_are_404_and_get_is_not_post(self):
        self.assertEqual(self.opt_post(user=self.alheio, campo="stage", acao="criar", name="N").status_code, 404)
        self.assertEqual(self.opt_post(activity=self.a_draft, campo="stage", acao="criar", name="N").status_code, 404)
        self.client.logout()
        url = reverse("activity-inline-options", args=[self.a1.pk])
        self.assertEqual(self.client.post(url, {"campo": "stage"}, **AJAX).status_code, 302)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.gestor)
        self.assertEqual(strict.post(url, {"campo": "stage", "acao": "criar", "name": "Nova"}, **AJAX).status_code, 403)


class StageConditionListTests(OptionBase):
    def page(self, user, **params):
        self.client.force_login(user)
        params.setdefault("tab", "todas")
        return self.client.get(reverse("activity-list"), params)

    def row_html(self, response, activity):
        html = response.content.decode()
        start = html.index(f'<tr data-activity-id="{activity.pk}">')
        return html[start: html.index("</tr>", start)]

    def flags(self, user, activity):
        return {a.pk: a.inline for a in self.page(user).context["activities"]}[activity.pk]

    def test_flags_per_action(self):
        self.assertEqual({k: self.flags(self.definidor, self.a1)[k] for k in ("stage", "condition")}, {"stage": True, "condition": True})
        self.assertEqual({k: self.flags(self.legado, self.a1)[k] for k in ("stage", "condition")}, {"stage": True, "condition": False})
        self.assertEqual({k: self.flags(self.editor, self.a1)[k] for k in ("stage", "condition")}, {"stage": False, "condition": False})
        self.assertEqual({k: self.flags(self.reader, self.a1)[k] for k in ("stage", "condition")}, {"stage": False, "condition": False})

    def test_finished_and_sectorless_demands_get_no_marker(self):
        for activity in (self.a_done, self.a_cancel, self.a_nosetor):
            flags = inline_flags(self.definidor, [self.fresh(activity)])[0].inline
            self.assertFalse(flags["stage"] or flags["condition"], activity.title)
        self.assertTrue(inline_flags(self.definidor, [self.fresh(self.a1)])[0].inline["stage"], "e uma aberta com setor pode")

    def test_markers_are_in_the_cells_only_for_who_can_and_carry_the_current_option(self):
        row = self.row_html(self.page(self.definidor), self.a1)
        self.assertIn(f'data-column="stage" data-option-id="{self.stage_a.pk}"', row)
        self.assertIn('data-inline-field="stage"', row)
        self.assertIn('data-inline-field="condition"', row)
        self.assertIn(f'data-column="condition" data-option-id="{self.cond_a.pk}"', row)
        legacy = self.row_html(self.page(self.legado), self.a1)
        self.assertIn('data-inline-field="stage"', legacy)
        self.assertNotIn('data-inline-field="condition"', legacy)
        reader = self.row_html(self.page(self.reader), self.a1)
        self.assertNotIn("data-inline-field", reader)
        self.assertIn(f'data-column="stage" data-option-id="{self.stage_a.pk}"', reader)  # só dados, nada editável

    def test_the_page_loads_both_scripts_and_the_options_url(self):
        html = self.page(self.definidor).content.decode()
        self.assertIn("js/activity-inline-options.js", html)
        self.assertIn(reverse("activity-inline-options", args=[999999999]), html)


class OverdueLineTests(OptionBase):
    """STATUS ganha uma segunda linha pequena "Vencida há N dias", derivada do prazo (nunca marcada à mão)."""

    def page(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("activity-list"), {"tab": "todas"})

    def row(self, response, activity):
        html = response.content.decode()
        start = html.index(f'<tr data-activity-id="{activity.pk}">')
        return html[start: html.index("</tr>", start)]

    def condition_cell(self, row):
        start = row.index('data-column="condition"')
        return row[start: row.index("</td>", start)]

    def test_overdue_open_demands_show_the_second_line_to_everyone(self):
        late = timezone.now() - datetime.timedelta(days=5)
        Activity.objects.filter(pk=self.a1.pk).update(requested_deadline=late)
        for user in (self.editor, self.reader, self.definidor):
            cell = self.condition_cell(self.row(self.page(user), self.a1))
            self.assertIn("Vencida há 5 dias", cell, user.username)
            self.assertIn("demand-board__status-late", cell)
            self.assertIn("has-late", cell)
            self.assertIn('class="demand-board__status-name">Normal</span>', cell)  # o nome da condição segue como estava

    def test_singular_and_plural(self):
        Activity.objects.filter(pk=self.a1.pk).update(requested_deadline=timezone.now() - datetime.timedelta(days=1, hours=1))
        self.assertIn("Vencida há 1 dia<", self.condition_cell(self.row(self.page(self.editor), self.a1)))

    def test_no_line_without_a_deadline_before_it_or_when_finished(self):
        Activity.objects.filter(pk=self.a1.pk).update(requested_deadline=timezone.now() + datetime.timedelta(days=3))
        Activity.objects.filter(pk=self.a_done.pk).update(requested_deadline=timezone.now() - datetime.timedelta(days=9))
        response = self.page(self.editor)
        self.assertNotIn("Vencida há", self.condition_cell(self.row(response, self.a1)))
        self.assertNotIn("has-late", self.condition_cell(self.row(response, self.a1)))
        self.client.force_login(self.editor)
        finished = self.client.get(reverse("activity-list"), {"tab": "concluidas"})
        self.assertNotIn("Vencida há", self.condition_cell(self.row(finished, self.a_done)))

    def test_the_manual_overdue_condition_is_just_a_condition_not_the_derived_line(self):
        manual = core_models.WorkflowStatus.objects.create(organization=self.org, sector=self.sector, domain="activity", name="Vencida", color="#EF4444", order=9)
        Activity.objects.filter(pk=self.a1.pk).update(condition=manual)
        cell = self.condition_cell(self.row(self.page(self.editor), self.a1))
        self.assertIn(">Vencida</span>", cell)
        self.assertNotIn("Vencida há", cell)  # sem prazo vencido, a marcação manual não vira atraso


class StageConditionQueryTests(OptionBase):
    def test_extra_flags_do_not_add_queries_per_row(self):
        def queries():
            self.client.force_login(self.definidor)
            with CaptureQueriesContext(connection) as context:
                self.client.get(reverse("activity-list"), {"tab": "todas"})
            return len(context)

        queries()
        few = queries()
        for index in range(12):
            self.activity(f"Mais {index}", self.editor)
        self.assertEqual(queries(), few)
