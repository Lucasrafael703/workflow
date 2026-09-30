"""Molde do processo: responsável padrão por etapa, imutabilidade da versão
publicada, cópia na nova versão e o editor de etapas."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserSector
from acessos import catalog
from acessos.testing import grant_actions
from core.models import Company, Organization, Sector

from .models import Process, ProcessCriterion, ProcessInput, ProcessStep, ProcessVersion
from .services import (
    ProcessCriterionService,
    ProcessError,
    ProcessInputService,
    ProcessService,
    ProcessStepService,
)
from .testing import build_process

User = get_user_model()

EDITOR_ACTIONS = [
    catalog.PROCESSO_VISUALIZAR,
    catalog.PROCESSO_CRIAR,
    catalog.PROCESSO_EDITAR_RASCUNHO,
    catalog.PROCESSO_PUBLICAR,
    catalog.PROCESSO_CRIAR_VERSAO,
]


def make_user(username, organization, actions=()):
    user = User.objects.create_user(username, email=f"{username}@example.com", password="x")
    user.profile.organization = organization
    user.profile.save(update_fields=["organization"])
    if actions:
        grant_actions(user, list(actions), organization=organization)
    return user


class ProcessBase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Outra")
        self.company = Company.objects.create(organization=self.org, name="Biasi Engenharia")
        self.compras = Sector.objects.create(organization=self.org, name="Compras")
        self.comercial = Sector.objects.create(organization=self.org, name="Comercial")
        self.editor = make_user("editor", self.org, EDITOR_ACTIONS)
        self.vitor = make_user("vitor", self.org)
        self.ryan = make_user("ryan", self.org)
        self.foreign = make_user("alheio", self.other_org)
        UserSector.objects.create(user=self.vitor, sector=self.compras)
        self.process, self.draft = ProcessService.create(
            self.org, self.company, "Orçamento", created_by=self.editor, description="d"
        )


class DefaultResponsavelTests(ProcessBase):
    def test_same_tenant_user_is_accepted_by_model_and_service(self):
        step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação", default_responsavel=self.vitor)
        step.refresh_from_db()
        self.assertEqual(step.default_responsavel, self.vitor)

    def test_default_responsavel_is_optional(self):
        step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação")
        self.assertIsNone(step.default_responsavel)

    def test_responsavel_does_not_need_to_belong_to_the_step_sector(self):
        step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação", default_responsavel=self.ryan)
        self.assertEqual(step.default_responsavel, self.ryan)

    def test_user_from_another_tenant_is_rejected_by_the_service(self):
        with self.assertRaisesMessage(ProcessError, "mesma organização"):
            ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação", default_responsavel=self.foreign)
        self.assertFalse(self.draft.steps.exists())

    def test_user_from_another_tenant_is_rejected_by_the_model_too(self):
        with self.assertRaises(ValidationError):
            ProcessStep.objects.create(version=self.draft, sector=self.compras, name="X", default_responsavel=self.foreign)
        step = ProcessStep(version=self.draft, sector=self.compras, name="X", default_responsavel=self.foreign)
        with self.assertRaises(ValidationError):
            step.full_clean()

    def test_inactive_user_is_rejected(self):
        self.vitor.is_active = False
        self.vitor.save(update_fields=["is_active"])
        with self.assertRaisesMessage(ProcessError, "ativa"):
            ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação", default_responsavel=self.vitor)

    def test_set_and_clear_on_a_draft_step(self):
        step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação")
        ProcessStepService.set_default_responsavel(step, self.editor, self.vitor)
        step.refresh_from_db()
        self.assertEqual(step.default_responsavel, self.vitor)
        ProcessStepService.set_default_responsavel(step, self.editor, None)
        step.refresh_from_db()
        self.assertIsNone(step.default_responsavel)

    def test_set_requires_the_edit_permission(self):
        step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação")
        with self.assertRaises(ProcessError):
            ProcessStepService.set_default_responsavel(step, self.ryan, self.vitor)

    def test_set_rejects_another_tenant(self):
        step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação")
        with self.assertRaises(ProcessError):
            ProcessStepService.set_default_responsavel(step, self.editor, self.foreign)

    def test_step_sector_from_another_tenant_is_rejected(self):
        foreign_sector = Sector.objects.create(organization=self.other_org, name="Financeiro")
        with self.assertRaisesMessage(ProcessError, "outra organização"):
            ProcessStepService.add(self.draft, self.editor, foreign_sector, "X")

    def test_user_deleted_later_only_clears_the_default(self):
        step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação", default_responsavel=self.vitor)
        self.vitor.delete()
        step.refresh_from_db()
        self.assertIsNone(step.default_responsavel)


class PublishedVersionIsImmutableTests(ProcessBase):
    def setUp(self):
        super().setUp()
        self.step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação", default_responsavel=self.vitor)
        self.input = ProcessInputService.add(self.draft, self.editor, "Projeto", ProcessInput.InputType.ARQUIVO)
        self.criterion = ProcessCriterionService.add(self.draft, self.editor, "Aprovado")
        ProcessService.update_output(self.draft, self.editor, "Proposta pronta", "LINK")
        ProcessService.publish(self.draft, self.editor)
        self.draft.refresh_from_db()

    def test_published_version_status(self):
        self.assertEqual(self.draft.status, ProcessVersion.Status.PUBLICADO)
        self.assertFalse(self.draft.is_editable)

    def test_no_structural_change_is_possible(self):
        for call in (
            lambda: ProcessStepService.add(self.draft, self.editor, self.compras, "Outra"),
            lambda: ProcessStepService.remove(self.step, self.editor),
            lambda: ProcessStepService.set_default_responsavel(self.step, self.editor, self.ryan),
            lambda: ProcessStepService.set_default_responsavel(self.step, self.editor, None),
            lambda: ProcessStepService.reorder(self.draft, self.editor, [self.step.pk]),
            lambda: ProcessInputService.add(self.draft, self.editor, "Novo", ProcessInput.InputType.TEXTO),
            lambda: ProcessInputService.remove(self.input, self.editor),
            lambda: ProcessCriterionService.add(self.draft, self.editor, "Novo"),
            lambda: ProcessCriterionService.remove(self.criterion, self.editor),
            lambda: ProcessService.update_output(self.draft, self.editor, "Outro", "ARQUIVO"),
            lambda: ProcessService.update_basic_info(self.draft, self.editor, name="Novo nome"),
        ):
            with self.assertRaisesMessage(ProcessError, "publicada"):
                call()
        self.step.refresh_from_db()
        self.assertEqual(self.step.default_responsavel, self.vitor)
        self.assertEqual(self.draft.steps.count(), 1)
        self.assertEqual(self.draft.inputs.count(), 1)
        self.assertEqual(self.draft.criteria.count(), 1)

    def test_new_version_copies_everything_including_default_responsavel(self):
        new = ProcessService.create_new_version(self.process, self.editor)
        self.assertEqual(new.number, 2)
        self.assertEqual(new.status, ProcessVersion.Status.RASCUNHO)
        self.assertEqual(new.output_description, "Proposta pronta")
        copied = new.steps.get()
        self.assertEqual((copied.name, copied.sector, copied.default_responsavel), ("Cotação", self.compras, self.vitor))
        self.assertNotEqual(copied.pk, self.step.pk)
        self.assertEqual(new.inputs.get().name, "Projeto")
        self.assertEqual(new.criteria.get().name, "Aprovado")

    def test_the_copy_is_editable_and_the_original_stays_untouched(self):
        new = ProcessService.create_new_version(self.process, self.editor)
        copied = new.steps.get()
        ProcessStepService.set_default_responsavel(copied, self.editor, self.ryan)
        copied.refresh_from_db()
        self.step.refresh_from_db()
        self.assertEqual(copied.default_responsavel, self.ryan)
        self.assertEqual(self.step.default_responsavel, self.vitor)


class ProcessEditorViewTests(ProcessBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.editor)
        self.url = reverse("process-edit", args=[self.process.pk])

    def test_editor_lists_sector_people_first_and_marks_the_default(self):
        step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação", default_responsavel=self.vitor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Responsável padrão")
        self.assertContains(response, f'action="{reverse("process-step-responsavel", args=[self.process.pk, step.pk])}"')
        self.assertContains(response, "Do setor Compras")
        row = [r for r in response.context["step_rows"] if r["step"].pk == step.pk][0]
        self.assertEqual([p.username for p in row["sector_people"]], ["vitor"])
        self.assertIn("ryan", [p.username for p in row["other_people"]])
        self.assertNotIn("alheio", [p.username for p in row["other_people"] + row["sector_people"]])

    def test_add_step_with_default_responsavel_via_the_form(self):
        response = self.client.post(
            reverse("process-step-add", args=[self.process.pk]),
            {"name": "Cotação", "sector": self.compras.pk, "depends_on_previous": "on", "default_responsavel": self.vitor.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.draft.steps.get().default_responsavel, self.vitor)

    def test_add_step_with_a_user_from_another_tenant_shows_an_error(self):
        response = self.client.post(
            reverse("process-step-add", args=[self.process.pk]),
            {"name": "Cotação", "sector": self.compras.pk, "default_responsavel": self.foreign.pk},
            follow=True,
        )
        self.assertContains(response, "mesma organização")
        self.assertFalse(self.draft.steps.exists())

    def test_change_and_clear_default_responsavel_via_the_row_form(self):
        step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação")
        url = reverse("process-step-responsavel", args=[self.process.pk, step.pk])
        self.client.post(url, {"default_responsavel": self.vitor.pk})
        step.refresh_from_db()
        self.assertEqual(step.default_responsavel, self.vitor)
        self.client.post(url, {"default_responsavel": ""})
        step.refresh_from_db()
        self.assertIsNone(step.default_responsavel)

    def test_changing_the_default_of_a_published_version_is_refused(self):
        step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação", default_responsavel=self.vitor)
        ProcessService.update_output(self.draft, self.editor, "Pronto", "LINK")
        ProcessService.publish(self.draft, self.editor)
        response = self.client.post(
            reverse("process-step-responsavel", args=[self.process.pk, step.pk]),
            {"default_responsavel": self.ryan.pk},
            follow=True,
        )
        self.assertContains(response, "não pode ser alterada")
        step.refresh_from_db()
        self.assertEqual(step.default_responsavel, self.vitor)

    def test_published_version_shows_the_default_but_no_selector(self):
        ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação", default_responsavel=self.vitor)
        ProcessService.update_output(self.draft, self.editor, "Pronto", "LINK")
        ProcessService.publish(self.draft, self.editor)
        response = self.client.get(self.url)
        self.assertContains(response, "Responsável padrão:")
        self.assertNotContains(response, 'name="default_responsavel"')

    def test_other_tenant_cannot_touch_the_step(self):
        step = ProcessStepService.add(self.draft, self.editor, self.compras, "Cotação")
        stranger = make_user("intruso", self.other_org, EDITOR_ACTIONS)
        self.client.force_login(stranger)
        response = self.client.post(
            reverse("process-step-responsavel", args=[self.process.pk, step.pk]), {"default_responsavel": ""}
        )
        self.assertEqual(response.status_code, 404)
