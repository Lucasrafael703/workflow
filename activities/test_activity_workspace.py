from tempfile import TemporaryDirectory
from unittest.mock import patch
from pathlib import Path
from datetime import datetime
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from urllib.parse import urlencode

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from acessos import catalog
from acessos.testing import grant_action
from audit.models import AuditLog
from core.models import Client
from .models import Activity, OwnerChangeLog
from .test_views import ViewTestCase


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ActivityWorkspaceTests(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.requester)

    def payload(self, **changes):
        data = {
            "title": "Entrega organizada", "owner": self.requester.pk, "sector": self.sector.pk,
            "urgency": "MEDIA", "acao": "publicar",
        }
        data.update(changes)
        return data

    def test_create_and_edit_use_one_editor(self):
        create = self.client.get(reverse("activity-create"))
        self.assertTemplateUsed(create, "activities/activity_form.html")
        self.assertContains(create, "Informações principais")
        self.assertNotContains(create, "wizard-stepper")
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        edit = self.client.get(reverse("activity-edit", args=[self.activity.pk]))
        self.assertTemplateUsed(edit, "activities/activity_form.html")

    def test_create_publishes_all_three_steps_in_one_submission(self):
        response = self.client.post(reverse("activity-create"), self.payload(
            description="<p>Entrega</p>", external_requester="Maria do Cliente", address="Rua A, 10",
            files_location=r"\\Servidor\Comercial\Orçamentos\Projeto X", urgency="ALTA",
        ))
        self.assertEqual(response.status_code, 302)
        activity = Activity.objects.get(title="Entrega organizada")
        self.assertEqual(activity.status, Activity.Status.ABERTA)
        self.assertEqual(activity.sector_id, self.sector.pk)
        self.assertEqual(activity.external_requester, "Maria do Cliente")
        self.assertEqual(activity.address, "Rua A, 10")
        self.assertEqual(activity.files_location, r"\\Servidor\Comercial\Orçamentos\Projeto X")
        self.assertEqual(activity.urgency, "ALTA")
        self.assertEqual(activity.description, "<p>Entrega</p>")
        self.assertEqual(activity.audit_entries.filter(action=AuditLog.Action.CREATE).count(), 1)

    def test_publish_missing_owner_preserves_form_and_does_not_create_row(self):
        count = Activity.objects.count()
        response = self.client.post(reverse("activity-create"), self.payload(owner=""))
        self.assertEqual(response.status_code, 200)
        self.assertIn("owner", response.context["form"].errors)
        self.assertEqual(Activity.objects.count(), count)

    def test_empty_draft_can_be_saved_and_resumed(self):
        response = self.client.post(reverse("activity-create"), self.payload(title="", owner="", sector="", acao="rascunho", address="Continuar depois"))
        draft = Activity.objects.get(status=Activity.Status.RASCUNHO)
        self.assertIn("pk=" + str(draft.pk), response.url)
        response = self.client.get(response.url)
        self.assertContains(response, "Continuar depois")
        self.assertEqual(response.context["form"]["title"].value(), "")

    def test_resuming_draft_publishes_same_row(self):
        draft = Activity.objects.create(organization=self.org, created_by=self.requester, title="Rascunho", status=Activity.Status.RASCUNHO)
        count = Activity.objects.count()
        self.client.post(reverse("activity-create") + f"?pk={draft.pk}", self.payload())
        draft.refresh_from_db()
        self.assertEqual(draft.status, Activity.Status.ABERTA)
        self.assertEqual(Activity.objects.count(), count)

    def test_other_users_draft_is_not_editable(self):
        draft = Activity.objects.create(organization=self.org, created_by=self.member, title="Privado", status=Activity.Status.RASCUNHO)
        response = self.client.post(reverse("activity-create") + f"?pk={draft.pk}", self.payload())
        self.assertEqual(response.status_code, 404)

    def test_foreign_client_is_rejected(self):
        client = Client.objects.create(organization=self.other_org, name="Outra organização")
        response = self.client.post(reverse("activity-create"), self.payload(client=client.pk))
        self.assertIn("client", response.context["form"].errors)

    def test_edit_saves_the_new_fields_and_audits_changes(self):
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        response = self.client.post(reverse("activity-edit", args=[self.activity.pk]), self.payload(
            external_requester="Fornecedor X", files_location="https://drive.example.com/pasta",
        ))
        self.assertEqual(response.status_code, 302)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.external_requester, "Fornecedor X")
        self.assertEqual(self.activity.files_location, "https://drive.example.com/pasta")
        self.assertTrue(self.activity.audit_entries.filter(field_name="title", old_value="Material na obra").exists())
        self.assertTrue(self.activity.audit_entries.filter(field_name="files_location", new_value="https://drive.example.com/pasta").exists())
        self.assertTrue(self.activity.audit_entries.filter(field_name="external_requester").exists())

    def test_editing_never_erases_what_the_editor_no_longer_shows(self):
        """Marcadores, solicitante interno e anotações internas saíram da tela: salvar não pode apagá-los."""
        from core.models import Tag

        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        tag = Tag.objects.create(organization=self.org, name="Importante")
        self.activity.tags.set([tag])
        Activity.objects.filter(pk=self.activity.pk).update(internal_notes="Nota antiga", requested_by=self.member)
        response = self.client.post(reverse("activity-edit", args=[self.activity.pk]), self.payload(title="Novo nome"))
        self.assertEqual(response.status_code, 302)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.title, "Novo nome")
        self.assertEqual(self.activity.internal_notes, "Nota antiga")
        self.assertEqual(self.activity.requested_by_id, self.member.pk)
        self.assertEqual(list(self.activity.tags.all()), [tag])

    def test_posted_values_for_removed_fields_are_ignored(self):
        response = self.client.post(reverse("activity-create"), self.payload(internal_notes="Nota", requested_by=self.member.pk, tags=[1]))
        self.assertEqual(response.status_code, 302)
        activity = Activity.objects.get(title="Entrega organizada")
        self.assertEqual(activity.internal_notes, "")
        self.assertIsNone(activity.requested_by_id)
        self.assertFalse(activity.tags.exists())

    def test_edit_without_transfer_permission_keeps_owner(self):
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        self.client.post(reverse("activity-edit", args=[self.activity.pk]), self.payload(owner=self.member.pk))
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.owner_id, self.requester.pk)

    def test_edit_with_transfer_permission_logs_owner_change(self):
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        grant_action(self.requester, catalog.ATIVIDADE_ALTERAR_DONO, organization=self.org)
        self.client.post(reverse("activity-edit", args=[self.activity.pk]), self.payload(owner=self.member.pk))
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.owner_id, self.member.pk)
        self.assertTrue(OwnerChangeLog.objects.filter(activity=self.activity, previous_owner=self.requester, new_owner=self.member).exists())

    def test_edit_requires_permission_even_on_get(self):
        self.assertEqual(self.client.get(reverse("activity-edit", args=[self.activity.pk])).status_code, 403)

    def test_list_rows_and_links_have_one_destination(self):
        response = self.client.get(reverse("activity-list"), {"q": "Material"})
        self.assertNotContains(response, "data-drawer-url")
        self.assertContains(response, reverse("activity-detail", args=[self.activity.pk]) + "?next=")

    def test_legacy_drawer_redirects_to_full_activity(self):
        self.assertRedirects(self.client.get(reverse("activity-drawer", args=[self.activity.pk])), reverse("activity-detail", args=[self.activity.pk]))

    def test_old_wizard_bookmark_opens_unified_editor(self):
        draft = Activity.objects.create(organization=self.org, created_by=self.requester, title="Rascunho", status=Activity.Status.RASCUNHO)
        for route in ("activity-wizard-contexto", "activity-wizard-detalhes"):
            response = self.client.get(reverse(route, args=[draft.pk]))
            self.assertRedirects(response, reverse("activity-create") + f"?pk={draft.pk}")

    def test_collection_context_is_preserved(self):
        origin = reverse("activity-kanban") + "?tab=grupo&q=Material"
        response = self.client.get(reverse("activity-detail", args=[self.activity.pk]), {"next": origin})
        self.assertEqual(response.context["return_url"], origin)
        response = self.client.post(reverse("activity-create"), self.payload(next=origin))
        self.assertIn(urlencode({"next": origin}), response.url)

    def test_external_return_is_ignored(self):
        response = self.client.get(reverse("activity-detail", args=[self.activity.pk]), {"next": "https://example.org/"})
        self.assertEqual(response.context["return_url"], reverse("activity-list"))

    def test_scope_switch_preserves_search(self):
        response = self.client.get(reverse("activity-list"), {"q": "Material", "status": "ABERTA"})
        self.assertContains(response, "q=Material&amp;status=ABERTA&amp;tab=grupo")

    def test_picker_uses_full_editor_and_same_validation(self):
        response = self.client.get(reverse("activity-mini-create"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTemplateUsed(response, "activities/activity_form.html")
        self.assertContains(response, "Informações do cliente")
        response = self.client.post(reverse("activity-mini-create"), self.payload(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Activity.objects.filter(pk=response.json()["id"], status=Activity.Status.ABERTA).exists())

    def test_short_action_supports_json_errors_and_success(self):
        grant_action(self.requester, catalog.ATIVIDADE_ALTERAR_DONO, organization=self.org)
        url = reverse("activity-change-owner", args=[self.activity.pk])
        response = self.client.post(url, {"new_owner": ""}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertIn("new_owner", response.json()["errors"])
        response = self.client.post(url, {"new_owner": self.member.pk}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.owner_id, self.member.pk)

    def test_list_cancellation_uses_same_finalization_as_detail(self):
        grant_action(self.requester, catalog.ATIVIDADE_CANCELAR, organization=self.org)
        response = self.client.get(reverse("activity-list"))
        self.assertContains(response, reverse("activity-finalize", args=[self.activity.pk]) + "?outcome=CANCELADO")
        self.assertNotContains(response, reverse("activity-cancel", args=[self.activity.pk]))

    def test_edit_displays_deadline_in_local_time(self):
        self.activity.requested_deadline = timezone.make_aware(datetime(2026, 10, 5, 16, 0))
        self.activity.save(update_fields=["requested_deadline"])
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        response = self.client.get(reverse("activity-edit", args=[self.activity.pk]))
        self.assertContains(response, 'value="16:00"')

    def test_there_is_no_file_upload_anymore(self):
        html = self.client.get(reverse("activity-create")).content.decode()
        self.assertNotIn('type="file"', html)
        self.assertNotIn("multipart/form-data", html)
        self.assertNotIn("Adicionar arquivos", html)
        self.assertIn("Link / caminho dos arquivos", html)

    def test_files_posted_anyway_are_not_stored(self):
        from .models import ActivityAttachment

        response = self.client.post(reverse("activity-create"), self.payload(files=[SimpleUploadedFile("a.txt", b"a")]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ActivityAttachment.objects.count(), 0)

    def test_publish_failure_rolls_back_the_database(self):
        from .services import ActivityError
        count = Activity.objects.count()
        with patch("activities.activity_editor.ActivityService.publish_draft", side_effect=ActivityError("Permissão alterada")):
            response = self.client.post(reverse("activity-create"), self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Activity.objects.count(), count)

    def test_other_users_draft_cannot_be_posted_to_edit_route(self):
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        draft = Activity.objects.create(organization=self.org, created_by=self.member, title="Privado", status=Activity.Status.RASCUNHO)
        response = self.client.post(reverse("activity-edit", args=[draft.pk]), self.payload())
        self.assertEqual(response.status_code, 404)

    def test_attachment_removal_from_editor_returns_json(self):
        from .models import ActivityAttachment
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        with TemporaryDirectory() as root:
            with patch.object(ActivityAttachment._meta.get_field("file"), "storage", FileSystemStorage(location=root)):
                attachment = ActivityAttachment.objects.create(activity=self.activity, uploaded_by=self.requester, file=SimpleUploadedFile("remove.txt", b"temporary"))
                response = self.client.post(reverse("activity-attachment-delete", args=[self.activity.pk, attachment.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
                self.assertEqual(response.status_code, 200)
                self.assertFalse(ActivityAttachment.objects.filter(pk=attachment.pk).exists())
                self.assertFalse(list(Path(root).rglob("*.txt")))

    def test_legacy_cancel_link_opens_common_finalization(self):
        response = self.client.get(reverse("activity-cancel", args=[self.activity.pk]))
        self.assertRedirects(response, reverse("activity-finalize", args=[self.activity.pk]) + "?outcome=CANCELADO")

    def test_own_draft_attachment_can_be_removed_without_edit_permission(self):
        from .models import ActivityAttachment
        draft = Activity.objects.create(organization=self.org, created_by=self.requester, title="Rascunho", status=Activity.Status.RASCUNHO)
        with TemporaryDirectory() as root:
            with patch.object(ActivityAttachment._meta.get_field("file"), "storage", FileSystemStorage(location=root)):
                attachment = ActivityAttachment.objects.create(activity=draft, uploaded_by=self.requester, file=SimpleUploadedFile("draft.txt", b"draft"))
                response = self.client.post(reverse("activity-attachment-delete", args=[draft.pk, attachment.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
                self.assertEqual(response.status_code, 200)
                self.assertFalse(ActivityAttachment.objects.filter(pk=attachment.pk).exists())

    def test_legacy_title_only_picker_submission_remains_valid(self):
        response = self.client.post(reverse("activity-mini-create"), {"title": "Seletor legado"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Activity.objects.get(pk=response.json()["id"]).owner_id, self.requester.pk)
