import datetime
from unittest import mock

from django.utils import timezone

from acessos import catalog
from acessos.services import AuthorizationService, ResourceContext
from acessos.testing import grant_actions
from activities.errors import ActivityError
from activities.models import Activity
from activities.services import ActivityService, find_mentioned_users
from activities.testing import make_user
from notifications.models import Notification

from .models import IntakeEvent, IntakeItem
from .policies import IntakePolicy
from .services import IntakeError, IntakeService, build_activity_description
from .testing import EMAIL_TEXT, IntakeTestCase


def convert_args(test, **overrides):
    """Argumentos mínimos e válidos para `IntakeService.convert`."""
    args = dict(title="Orçamento do gerador", owner=test.triador, sector=test.comercial)
    args.update(overrides)
    return args


class CatalogTests(IntakeTestCase):
    def test_entrada_actions_are_in_the_catalog(self):
        keys = {key for _, _, actions in catalog.GROUPS for key, _, _, _ in actions}
        for key in ("entrada.visualizar", "entrada.registrar", "entrada.triar"):
            self.assertIn(key, keys)

    def test_suggested_profiles(self):
        self.assertIn(catalog.ENTRADA_REGISTRAR, catalog.SUGGESTED_PROFILES["Colaborador"])
        self.assertNotIn(catalog.ENTRADA_TRIAR, catalog.SUGGESTED_PROFILES["Colaborador"])
        for key in (catalog.ENTRADA_VISUALIZAR, catalog.ENTRADA_REGISTRAR, catalog.ENTRADA_TRIAR):
            self.assertIn(key, catalog.SUGGESTED_PROFILES["Gestor de Setor"])
            self.assertIn(key, catalog.SUGGESTED_PROFILES["Administrador"])


class ResourceContextTests(IntakeTestCase):
    def test_item_address_is_the_suggested_sector_and_site(self):
        item = self.new_item(suggested_sector=self.compras, suggested_site=self.aurora)
        context = ResourceContext.of(item)
        self.assertEqual(context.organization_id, self.org.pk)
        self.assertEqual(context.sector_id, self.compras.pk)
        self.assertEqual(context.site_id, self.aurora.pk)
        self.assertFalse(context.unresolved)

    def test_item_without_sector_has_organization_address_only(self):
        context = ResourceContext.of(self.new_item())
        self.assertIsNone(context.sector_id)
        self.assertFalse(context.unresolved)

    def test_sector_scope_covers_only_items_of_that_sector(self):
        can = AuthorizationService.can
        compras = self.new_item(suggested_sector=self.compras)
        comercial = self.new_item(suggested_sector=self.comercial, subject="Outro")
        sem_setor = self.new_item(subject="Sem setor")
        self.assertTrue(can(self.gestor_compras, catalog.ENTRADA_TRIAR, compras))
        self.assertFalse(can(self.gestor_compras, catalog.ENTRADA_TRIAR, comercial))
        self.assertFalse(can(self.gestor_compras, catalog.ENTRADA_TRIAR, sem_setor))

    def test_organization_scope_covers_every_item(self):
        can = AuthorizationService.can
        for item in (self.new_item(), self.new_item(suggested_sector=self.compras, subject="Outro")):
            self.assertTrue(can(self.triador, catalog.ENTRADA_TRIAR, item))

    def test_other_organization_is_denied(self):
        self.assertFalse(AuthorizationService.can(self.estranho, catalog.ENTRADA_TRIAR, self.new_item()))


class PolicyTests(IntakeTestCase):
    def test_actions_by_status(self):
        self.assertEqual(IntakePolicy.available_actions(IntakeItem(status="NOVO")), {"edit", "convert", "ignore"})
        self.assertEqual(IntakePolicy.available_actions(IntakeItem(status="IGNORADO")), {"restore"})
        self.assertEqual(IntakePolicy.available_actions(IntakeItem(status="CONVERTIDO")), set())

    def test_transitions(self):
        novo, ignorado, convertido = (IntakeItem(status=s) for s in ("NOVO", "IGNORADO", "CONVERTIDO"))
        self.assertTrue(IntakePolicy.can_transition(novo, "CONVERTIDO"))
        self.assertTrue(IntakePolicy.can_transition(novo, "IGNORADO"))
        self.assertTrue(IntakePolicy.can_transition(ignorado, "NOVO"))
        self.assertFalse(IntakePolicy.can_transition(ignorado, "CONVERTIDO"))
        self.assertFalse(IntakePolicy.can_transition(convertido, "NOVO"))
        self.assertFalse(IntakePolicy.can_transition(convertido, "IGNORADO"))


class RegisterTests(IntakeTestCase):
    def register(self, user=None, **overrides):
        args = dict(
            organization=self.org,
            user=user or self.triador,
            raw_content=EMAIL_TEXT,
            subject="Orçamento do gerador",
            sender_name="Maria da Convivy",
            sender_email="maria@convivy.com.br",
        )
        args.update(overrides)
        return IntakeService.register(**args)

    def test_register_stores_the_item_the_suggestions_and_the_event(self):
        item = self.register()
        self.assertEqual(item.status, IntakeItem.Status.NOVO)
        self.assertEqual(item.organization, self.org)
        self.assertEqual(item.created_by, self.triador)
        self.assertEqual(item.suggested_client, self.convivy)
        self.assertEqual(item.suggested_site, self.aurora)
        self.assertEqual(item.suggested_title, "Orçamento do gerador")
        self.assertEqual(timezone.localtime(item.suggested_deadline).weekday(), 4)  # sexta
        self.assertGreaterEqual(item.confidence, 70)
        self.assertTrue(item.suggestion_reasons)
        self.assertEqual(len(item.content_hash), 64)
        self.assertEqual([e.kind for e in item.events.all()], ["REGISTRADA"])
        self.assertEqual(item.events.get().user, self.triador)

    def test_register_trims_and_lowercases(self):
        item = self.register(sender_email="  Maria@Convivy.com.br ", subject="  Gerador  ", raw_content="  texto  ")
        self.assertEqual(item.sender_email, "maria@convivy.com.br")
        self.assertEqual(item.subject, "Gerador")
        self.assertEqual(item.raw_content, "texto")

    def test_register_accepts_a_past_received_date(self):
        yesterday = timezone.now() - datetime.timedelta(days=1)
        self.assertEqual(self.register(received_at=yesterday).received_at, yesterday)

    def test_register_without_content_is_refused(self):
        for content in ("", "   \n ", None):
            with self.assertRaisesMessage(IntakeError, "Cole o texto"):
                self.register(raw_content=content)
        self.assertEqual(IntakeItem.objects.count(), 0)

    def test_register_with_huge_content_is_refused(self):
        with self.assertRaisesMessage(IntakeError, "grande demais"):
            self.register(raw_content="x" * 20_001)
        self.register(raw_content="x" * 20_000)

    def test_register_validates_the_fields(self):
        with self.assertRaisesMessage(IntakeError, "assunto"):
            self.register(subject="a" * 201)
        with self.assertRaisesMessage(IntakeError, "nome do remetente"):
            self.register(sender_name="a" * 151)
        with self.assertRaisesMessage(IntakeError, "e-mail válido"):
            self.register(sender_email="isso nao e email")
        with self.assertRaisesMessage(IntakeError, "Origem desconhecida"):
            self.register(source="FAX")
        with self.assertRaisesMessage(IntakeError, "futuro"):
            self.register(received_at=timezone.now() + datetime.timedelta(hours=1))

    def test_register_requires_the_action(self):
        with self.assertRaises(IntakeError):
            self.register(user=self.sem_acesso)
        self.assertEqual(IntakeItem.objects.count(), 0)

    def test_registrador_without_view_permission_can_register(self):
        self.assertEqual(self.register(user=self.registrador).created_by, self.registrador)

    def test_sector_scoped_user_can_register_because_there_is_no_sector_yet(self):
        self.assertEqual(self.register(user=self.gestor_compras).created_by, self.gestor_compras)

    def test_register_in_another_organization_is_refused(self):
        with self.assertRaisesMessage(IntakeError, "não pertence"):
            self.register(user=self.estranho)

    def test_duplicate_of_a_new_item_is_blocked(self):
        self.register()
        with self.assertRaisesMessage(IntakeError, "já está na Caixa de Entrada"):
            self.register()
        self.assertEqual(IntakeItem.objects.count(), 1)

    def test_duplicate_is_recognised_despite_spacing_and_case(self):
        self.register(raw_content="Preciso do gerador")
        with self.assertRaises(IntakeError):
            self.register(raw_content="  PRECISO   do\ngerador ")

    def test_duplicate_of_a_converted_item_is_blocked(self):
        item = self.register()
        IntakeService.convert(item, self.triador, **convert_args(self))
        with self.assertRaises(IntakeError):
            self.register()

    def test_ignored_item_does_not_block_a_new_registration(self):
        item = self.register()
        IntakeService.ignore(item, self.triador)
        self.assertNotEqual(self.register().pk, item.pk)

    def test_old_duplicate_does_not_block(self):
        item = self.register()
        IntakeItem.objects.filter(pk=item.pk).update(created_at=timezone.now() - datetime.timedelta(days=8))
        self.assertNotEqual(self.register().pk, item.pk)

    def test_same_content_in_another_organization_is_not_a_duplicate(self):
        self.register()
        other = IntakeService.register(self.other_org, self.estranho, EMAIL_TEXT, subject="Orçamento do gerador",
                                       sender_name="Maria da Convivy", sender_email="maria@convivy.com.br")
        self.assertEqual(other.organization, self.other_org)

    def test_external_id_must_be_unique_per_source(self):
        self.register(external_id="<abc@mail>", raw_content="primeiro")
        with self.assertRaisesMessage(IntakeError, "já foi recebida"):
            self.register(external_id="<abc@mail>", raw_content="outro texto")
        other_source = self.register(external_id="<abc@mail>", raw_content="terceiro", source="TEAMS")
        self.assertEqual(other_source.source, "TEAMS")

    def test_empty_external_id_never_collides(self):
        self.register(raw_content="um")
        self.register(raw_content="dois")


class UpdateSuggestionsTests(IntakeTestCase):
    def setUp(self):
        super().setUp()
        self.item = self.new_item(suggested_client=self.convivy, suggested_sector=self.compras)

    def test_edit_updates_fields_and_logs_the_changes(self):
        deadline = timezone.now() + datetime.timedelta(days=3)
        item = IntakeService.update_suggestions(
            self.item, self.triador,
            suggested_title="Novo título", suggested_client=self.outra, suggested_site=None,
            suggested_sector=self.comercial, suggested_deadline=deadline,
        )
        item.refresh_from_db()
        self.assertEqual(item.suggested_title, "Novo título")
        self.assertEqual(item.suggested_client, self.outra)
        self.assertEqual(item.suggested_sector, self.comercial)
        self.assertEqual(item.suggested_deadline, deadline)
        event = item.events.get(kind=IntakeEvent.Kind.EDITADA)
        self.assertEqual(event.user, self.triador)
        self.assertIn("Cliente: Convivy → Outra Construtora", event.note)
        self.assertIn("Setor: Compras → Comercial", event.note)
        self.assertNotIn("Obra", event.note)

    def test_edit_without_changes_logs_nothing(self):
        IntakeService.update_suggestions(self.item, self.triador, suggested_client=self.convivy)
        self.assertFalse(self.item.events.exists())

    def test_edit_leaves_the_other_fields_alone(self):
        IntakeService.update_suggestions(self.item, self.triador, suggested_title="Só o título")
        self.item.refresh_from_db()
        self.assertEqual(self.item.suggested_client, self.convivy)

    def test_unknown_field_is_refused(self):
        with self.assertRaisesMessage(IntakeError, "não editável"):
            IntakeService.update_suggestions(self.item, self.triador, status="CONVERTIDO")

    def test_only_new_items_can_be_edited(self):
        IntakeService.ignore(self.item, self.triador)
        with self.assertRaisesMessage(IntakeError, "nova"):
            IntakeService.update_suggestions(self.item, self.triador, suggested_title="x")

    def test_other_organization_records_are_refused(self):
        for field, value in (("suggested_client", self.foreign_client), ("suggested_sector", self.foreign_sector),
                             ("suggested_site", self.foreign_site)):
            with self.assertRaisesMessage(IntakeError, "própria organização"):
                IntakeService.update_suggestions(self.item, self.triador, **{field: value})

    def test_site_of_another_client_is_refused(self):
        with self.assertRaisesMessage(IntakeError, "outro cliente"):
            IntakeService.update_suggestions(self.item, self.triador, suggested_client=self.outra, suggested_site=self.aurora)

    def test_title_too_long_is_refused(self):
        with self.assertRaisesMessage(IntakeError, "200"):
            IntakeService.update_suggestions(self.item, self.triador, suggested_title="a" * 201)

    def test_requires_triage_permission(self):
        with self.assertRaises(IntakeError):
            IntakeService.update_suggestions(self.item, self.registrador, suggested_title="x")

    def test_sector_manager_edits_within_the_sector(self):
        IntakeService.update_suggestions(self.item, self.gestor_compras, suggested_title="Compras mexeu")
        self.item.refresh_from_db()
        self.assertEqual(self.item.suggested_title, "Compras mexeu")

    def test_sector_manager_cannot_send_the_item_out_of_sight(self):
        with self.assertRaisesMessage(IntakeError, "não teria mais acesso"):
            IntakeService.update_suggestions(self.item, self.gestor_compras, suggested_sector=self.comercial)
        with self.assertRaisesMessage(IntakeError, "não teria mais acesso"):
            IntakeService.update_suggestions(self.item, self.gestor_compras, suggested_sector=None)
        self.item.refresh_from_db()
        self.assertEqual(self.item.suggested_sector, self.compras)

    def test_sector_manager_cannot_edit_another_sectors_item(self):
        other = self.new_item(suggested_sector=self.comercial, subject="Outro")
        with self.assertRaises(IntakeError):
            IntakeService.update_suggestions(other, self.gestor_compras, suggested_title="x")


class IgnoreRestoreTests(IntakeTestCase):
    def setUp(self):
        super().setUp()
        self.item = self.new_item()

    def test_ignore_records_who_when_and_why(self):
        item = IntakeService.ignore(self.item, self.triador, "  Não é conosco  ")
        item.refresh_from_db()
        self.assertEqual(item.status, IntakeItem.Status.IGNORADO)
        self.assertEqual(item.resolved_by, self.triador)
        self.assertIsNotNone(item.resolved_at)
        self.assertEqual(item.resolution_note, "Não é conosco")
        event = item.events.get(kind=IntakeEvent.Kind.IGNORADA)
        self.assertEqual((event.user, event.note), (self.triador, "Não é conosco"))

    def test_ignore_without_reason(self):
        self.assertEqual(IntakeService.ignore(self.item, self.triador).resolution_note, "")

    def test_ignore_reason_too_long(self):
        with self.assertRaisesMessage(IntakeError, "255"):
            IntakeService.ignore(self.item, self.triador, "a" * 256)

    def test_restore_brings_it_back_clean(self):
        IntakeService.ignore(self.item, self.triador, "motivo")
        item = IntakeService.restore(self.item, self.triador)
        item.refresh_from_db()
        self.assertEqual(item.status, IntakeItem.Status.NOVO)
        self.assertIsNone(item.resolved_by)
        self.assertIsNone(item.resolved_at)
        self.assertEqual(item.resolution_note, "")
        self.assertEqual(
            [e.kind for e in item.events.all()],
            [IntakeEvent.Kind.IGNORADA, IntakeEvent.Kind.RESTAURADA],
        )

    def test_invalid_transitions(self):
        with self.assertRaisesMessage(IntakeError, "ignorada pode ser restaurada"):
            IntakeService.restore(self.item, self.triador)
        IntakeService.ignore(self.item, self.triador)
        with self.assertRaisesMessage(IntakeError, "nova pode ser ignorada"):
            IntakeService.ignore(self.item, self.triador)

    def test_converted_item_cannot_be_ignored_or_restored(self):
        IntakeService.convert(self.item, self.triador, **convert_args(self))
        with self.assertRaises(IntakeError):
            IntakeService.ignore(self.item, self.triador)
        with self.assertRaises(IntakeError):
            IntakeService.restore(self.item, self.triador)

    def test_requires_triage_permission(self):
        with self.assertRaises(IntakeError):
            IntakeService.ignore(self.item, self.registrador)
        IntakeService.ignore(self.item, self.triador)
        with self.assertRaises(IntakeError):
            IntakeService.restore(self.item, self.registrador)


class ConvertTests(IntakeTestCase):
    def setUp(self):
        super().setUp()
        self.item = self.new_item(suggested_client=self.convivy, suggested_site=self.aurora)

    def convert(self, user=None, item=None, **overrides):
        return IntakeService.convert(
            item or self.item, user or self.triador,
            **convert_args(self, client=self.convivy, site=self.aurora, **overrides),
        )

    def test_convert_creates_a_published_activity_from_the_item(self):
        deadline = timezone.now() + datetime.timedelta(days=2)
        activity = self.convert(requested_deadline=deadline, urgency=Activity.Urgency.ALTA)
        self.assertEqual(activity.status, Activity.Status.ABERTA)
        self.assertTrue(activity.code.startswith("ATV-"))
        self.assertEqual(activity.title, "Orçamento do gerador")
        self.assertEqual(activity.owner, self.triador)
        self.assertEqual(activity.created_by, self.triador)
        self.assertEqual(activity.sector, self.comercial)
        self.assertEqual(activity.client, self.convivy)
        self.assertEqual(activity.site, self.aurora)
        self.assertEqual(activity.requested_deadline, deadline)
        self.assertEqual(activity.urgency, Activity.Urgency.ALTA)
        self.assertEqual(activity.external_requester, "Maria da Convivy")
        self.assertIsNone(activity.requested_by)

    def test_convert_links_the_item_and_logs_the_event(self):
        activity = self.convert()
        item = IntakeItem.objects.get(pk=self.item.pk)
        self.assertEqual(item.status, IntakeItem.Status.CONVERTIDO)
        self.assertEqual(item.activity, activity)
        self.assertEqual(activity.intake_item, item)
        self.assertEqual(item.resolved_by, self.triador)
        self.assertIsNotNone(item.resolved_at)
        event = item.events.get(kind=IntakeEvent.Kind.CONVERTIDA)
        self.assertEqual((event.user, event.note), (self.triador, activity.code))

    def test_convert_keeps_the_usual_side_effects_of_creating_an_activity(self):
        activity = self.convert()
        self.assertTrue(activity.audit_entries.filter(action="CREATE").exists())
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.triador, activity=activity, event_type=Notification.EventType.ACTIVITY_CREATED
            ).exists()
        )

    def test_internal_sender_becomes_the_requester(self):
        item = self.new_item(sender_email="Maria@Biasi.com.br", sender_name="Maria Interna", subject="Interno")
        activity = self.convert(item=item)
        self.assertEqual(activity.requested_by, self.maria)
        self.assertEqual(activity.external_requester, "")

    def test_external_requester_can_be_overridden_or_cleared(self):
        self.assertEqual(self.convert(external_requester="Outra pessoa").external_requester, "Outra pessoa")
        other = self.new_item(subject="Segundo", raw_content="outro texto")
        self.assertEqual(self.convert(item=other, external_requester="").external_requester, "")

    def test_sender_without_name_uses_the_email(self):
        item = self.new_item(sender_name="", sender_email="fulano@empresa.com", subject="Sem nome")
        self.assertEqual(self.convert(item=item).external_requester, "fulano@empresa.com")

    def test_description_has_origin_original_text_and_a_link_back(self):
        activity = self.convert()
        description = activity.description
        self.assertIn("Origem: E-mail · Maria da Convivy", description)
        self.assertIn("Residencial Aurora", description)
        self.assertIn(f'href="/entrada/{self.item.pk}/"', description)
        self.assertIn("Ver solicitação original", description)

    def test_description_neutralises_html_from_the_message(self):
        item = self.new_item(raw_content='<script>alert(1)</script> olá <a href="javascript:x()">clique</a>', subject="XSS")
        description = self.convert(item=item).description
        # Tudo que veio na mensagem vira texto inerte; o único elemento vivo é o link para a solicitação.
        self.assertNotIn("<script", description)
        self.assertIn("&lt;script&gt;", description)
        self.assertEqual(description.count("<a "), 1)
        self.assertIn(f'href="/entrada/{item.pk}/"', description)

    def test_description_of_a_long_message_is_cut_with_a_notice(self):
        item = self.new_item(raw_content="palavra " * 400, subject="Longo")
        description = self.convert(item=item).description
        self.assertIn("Texto cortado", description)
        self.assertLess(len(description), 2200)

    def test_description_does_not_mention_people_of_the_team(self):
        grant_actions(self.maria, [catalog.COMUNICACAO_PARTICIPAR], organization=self.org)
        item = self.new_item(
            raw_content="Oi @maria, veja com @naoexiste e escreva para contato@convivy.com.br", subject="Menção"
        )
        activity = self.convert(item=item)
        # O mecanismo existe: um texto com a mesma menção, sem neutralizar, notificaria a Maria.
        self.assertEqual(find_mentioned_users("oi @maria", self.triador, activity), {self.maria})
        self.assertFalse(find_mentioned_users(activity.description, self.triador, activity))
        self.assertFalse(Notification.objects.filter(recipient=self.maria, event_type="MENTIONED").exists())
        self.assertIn("contato@convivy.com.br", activity.description)
        self.assertIn("@​maria", activity.description)
        self.assertIn("@naoexiste", activity.description)

    def test_build_description_defuses_a_mention_in_the_sender_name(self):
        grant_actions(self.maria, [catalog.COMUNICACAO_PARTICIPAR], organization=self.org)
        item = self.new_item(sender_name="@maria", subject="Remetente")
        self.assertNotIn("@maria", build_activity_description(item))

    def test_everything_rolls_back_when_the_activity_cannot_be_published(self):
        before = self.activity_count()
        with mock.patch.object(ActivityService, "publish_draft", side_effect=ActivityError("Falhou ao publicar.")):
            with self.assertRaisesMessage(IntakeError, "Falhou ao publicar."):
                self.convert()
        self.assertEqual(self.activity_count(), before)
        self.assertFalse(Activity.objects.filter(status=Activity.Status.RASCUNHO).exists())
        item = IntakeItem.objects.get(pk=self.item.pk)
        self.assertEqual(item.status, IntakeItem.Status.NOVO)
        self.assertIsNone(item.activity)
        self.assertFalse(item.events.filter(kind=IntakeEvent.Kind.CONVERTIDA).exists())

    def test_second_conversion_of_the_same_item_fails_and_creates_nothing(self):
        stale = IntakeItem.objects.get(pk=self.item.pk)  # cópia "velha", ainda NOVO na memória
        self.convert()
        with self.assertRaisesMessage(IntakeError, "já foi tratada"):
            self.convert(item=stale)
        self.assertEqual(self.activity_count(), 1)
        self.assertEqual(self.item.events.filter(kind=IntakeEvent.Kind.CONVERTIDA).count(), 1)

    def test_ignored_item_cannot_be_converted(self):
        IntakeService.ignore(self.item, self.triador)
        with self.assertRaisesMessage(IntakeError, "já foi tratada"):
            self.convert()

    def test_triage_permission_is_required(self):
        with self.assertRaises(IntakeError):
            self.convert(user=self.registrador)
        self.assertEqual(self.activity_count(), 0)

    def test_creating_the_activity_still_requires_its_own_permission(self):
        so_triagem = make_user("sotriagem", self.org, [catalog.ENTRADA_VISUALIZAR, catalog.ENTRADA_TRIAR])
        with self.assertRaises(IntakeError):
            self.convert(user=so_triagem)
        self.assertEqual(self.activity_count(), 0)
        self.assertEqual(IntakeItem.objects.get(pk=self.item.pk).status, IntakeItem.Status.NOVO)

    def test_sector_manager_converts_only_into_their_own_sector(self):
        item = self.new_item(suggested_sector=self.compras, subject="Compras")
        with self.assertRaises(IntakeError):
            IntakeService.convert(item, self.gestor_compras, **convert_args(self, owner=self.gestor_compras, sector=self.comercial))
        self.assertEqual(self.activity_count(), 0)
        activity = IntakeService.convert(item, self.gestor_compras, **convert_args(self, owner=self.gestor_compras, sector=self.compras))
        self.assertEqual(activity.sector, self.compras)

    def test_required_fields(self):
        with self.assertRaisesMessage(IntakeError, "nome da atividade"):
            self.convert(title="   ")
        with self.assertRaisesMessage(IntakeError, "quem fica com a atividade"):
            self.convert(owner=None)
        with self.assertRaisesMessage(IntakeError, "setor responsável"):
            self.convert(sector=None)
        self.assertEqual(self.activity_count(), 0)

    def test_other_organization_records_are_refused(self):
        with self.assertRaisesMessage(IntakeError, "própria organização"):
            self.convert(sector=self.foreign_sector)
        with self.assertRaisesMessage(IntakeError, "própria organização"):
            IntakeService.convert(self.item, self.triador, **convert_args(self, client=self.foreign_client))
        with self.assertRaisesMessage(IntakeError, "entre as pessoas da organização"):
            self.convert(owner=self.estranho)
        self.assertEqual(self.activity_count(), 0)

    def test_inactive_owner_is_refused(self):
        self.maria.is_active = False
        self.maria.save()
        with self.assertRaisesMessage(IntakeError, "entre as pessoas da organização"):
            self.convert(owner=self.maria)

    def test_site_of_another_client_is_refused(self):
        with self.assertRaisesMessage(IntakeError, "outro cliente"):
            IntakeService.convert(self.item, self.triador, **convert_args(self, client=self.outra, site=self.aurora))

    def test_unknown_urgency_is_refused(self):
        with self.assertRaisesMessage(IntakeError, "Urgência"):
            self.convert(urgency="ALTISSIMA")


class VisibilityTests(IntakeTestCase):
    def setUp(self):
        super().setUp()
        self.compras_item = self.new_item(suggested_sector=self.compras, subject="Compras")
        self.comercial_item = self.new_item(suggested_sector=self.comercial, subject="Comercial")
        self.sem_setor = self.new_item(subject="Sem setor")
        self.ignorado = self.new_item(subject="Ignorado", status=IntakeItem.Status.IGNORADO)

    def ids(self, user, organization=None):
        return set(IntakeService.visible_queryset(user, organization or self.org).values_list("pk", flat=True))

    def test_organization_scope_sees_everything_even_without_sector(self):
        self.assertEqual(
            self.ids(self.triador),
            {self.compras_item.pk, self.comercial_item.pk, self.sem_setor.pk, self.ignorado.pk},
        )

    def test_sector_scope_sees_only_its_sector(self):
        self.assertEqual(self.ids(self.gestor_compras), {self.compras_item.pk})

    def test_user_without_the_action_sees_nothing(self):
        self.assertEqual(self.ids(self.sem_acesso), set())
        self.assertEqual(self.ids(self.registrador), set())

    def test_other_organization_sees_nothing_of_ours(self):
        self.assertEqual(self.ids(self.estranho, self.org), set())

    def test_new_count_counts_only_new_items_in_view(self):
        self.assertEqual(IntakeService.new_count(self.triador, self.org), 3)
        self.assertEqual(IntakeService.new_count(self.gestor_compras, self.org), 1)
        self.assertEqual(IntakeService.new_count(self.sem_acesso, self.org), 0)


class RequesterDefaultsTests(IntakeTestCase):
    def test_no_sender_information(self):
        item = self.new_item(sender_name="", sender_email="", subject="Anônimo")
        self.assertEqual(IntakeService.requester_defaults(item), (None, ""))

    def test_internal_user_of_another_organization_is_not_matched(self):
        item = self.new_item(sender_email=self.estranho.email)
        self.assertEqual(IntakeService.requester_defaults(item), (None, "Maria da Convivy"))
