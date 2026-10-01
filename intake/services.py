"""Regras da Caixa de Entrada: registrar, corrigir sugestões, ignorar, restaurar e converter.

Segue o fluxo dos demais serviços do projeto: autoriza → valida → grava → deixa
rastro. O rastro aqui é o `IntakeEvent`; a atividade criada tem o seu próprio
(`ActivityService`). Nada vira atividade sozinho: `convert` é sempre uma pessoa
decidindo.
"""

import datetime
import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from acessos import catalog
from acessos.services import AuthorizationError, AuthorizationService, ResourceContext
from activities.errors import ActivityError
from activities.models import Activity
from activities.services import MENTION_PATTERN, ActivityService
from core.sanitize import sanitize_description

from . import textparse
from .models import IntakeEvent, IntakeItem
from .policies import IntakePolicy
from .suggestions import suggest

User = get_user_model()

MAX_CONTENT_LENGTH = 20_000
MAX_SUBJECT_LENGTH = 200
MAX_SENDER_NAME_LENGTH = 150
MAX_EXTERNAL_ID_LENGTH = 255
MAX_NOTE_LENGTH = 255
DUPLICATE_WINDOW = datetime.timedelta(days=7)
FUTURE_TOLERANCE = datetime.timedelta(minutes=5)
DESCRIPTION_EXCERPT_LENGTH = 1500

# Campos que a triagem pode corrigir, com o rótulo usado no registro do evento.
EDITABLE_FIELDS = {
    "suggested_title": "Título",
    "suggested_client": "Cliente",
    "suggested_site": "Obra",
    "suggested_sector": "Setor",
    "suggested_deadline": "Prazo",
}


class IntakeError(Exception):
    """Regra de negócio ou autorização negada, com mensagem pronta para a tela."""


def _require(user, action_key, resource=None):
    try:
        AuthorizationService.require(user, action_key, resource)
    except AuthorizationError as exc:
        raise IntakeError(str(exc)) from exc


def _require_anywhere(user, action_key):
    """A pessoa pode a ação em algum lugar? Registrar não tem setor ainda."""
    if not AuthorizationService.can_anywhere(user, action_key):
        raise IntakeError("Você não tem autorização para esta ação.")


def _lock(item):
    """Relê a solicitação travando a linha: dois cliques ou duas pessoas não passam juntos."""
    return IntakeItem.objects.select_for_update().get(pk=item.pk)


def _event(item, user, kind, note=""):
    return IntakeEvent.objects.create(item=item, user=user, kind=kind, note=note)


def _check_same_organization(organization_id, *objects):
    for obj in objects:
        if obj is not None and obj.organization_id != organization_id:
            raise IntakeError("Escolha apenas registros da própria organização.")


def _check_site_belongs_to_client(client, site):
    if client is not None and site is not None and site.client_id not in (None, client.pk):
        raise IntakeError("Esta obra pertence a outro cliente. Escolha uma obra de quem foi selecionado.")


def _show(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime("%d/%m/%Y %H:%M")
    return str(value)


def _defuse_mentions(text):
    """Impede que texto de terceiros mencione alguém da equipe.

    `ActivityService` varre a descrição atrás de "@usuario" e notifica a pessoa;
    um e-mail recebido de fora não pode disparar isso. Só o "@" que de fato bate
    com um usuário recebe um caractere invisível — e-mails comuns ficam intactos.
    """
    tokens = set(MENTION_PATTERN.findall(text))
    if not tokens:
        return text
    candidates = tokens | {token.rstrip(".,;:!?") for token in tokens}
    existing = set(User.objects.filter(username__in=candidates).values_list("username", flat=True))
    if not existing:
        return text

    def defuse(match):
        token = match.group(1)
        if token in existing or token.rstrip(".,;:!?") in existing:
            return "@​" + token
        return match.group(0)

    return MENTION_PATTERN.sub(defuse, text)


def build_activity_description(item):
    """Descrição (HTML já sanitizado) da atividade criada a partir da solicitação."""
    when = timezone.localtime(item.received_at).strftime("%d/%m/%Y %H:%M")
    header = _defuse_mentions(f"Origem: {item.get_source_display()} · {item.sender_display} · {when}")
    original = (item.raw_content or "").strip()
    excerpt = _defuse_mentions(original[:DESCRIPTION_EXCERPT_LENGTH])

    parts = [f"<p>{escape(header)}</p>"]
    for chunk in re.split(r"\n\s*\n", excerpt):
        if chunk.strip():
            parts.append("<p>{}</p>".format(escape(chunk.strip()).replace("\n", "<br>")))
    if len(original) > DESCRIPTION_EXCERPT_LENGTH:
        parts.append("<p><em>Texto cortado: veja a solicitação original.</em></p>")
    link = reverse("intake-detail", args=[item.pk])
    parts.append(f'<p><a href="{link}">Ver solicitação original</a></p>')
    return sanitize_description("".join(parts))


class IntakeService:
    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------

    @staticmethod
    def visible_queryset(user, organization):
        """Solicitações da organização que a pessoa pode ver.

        Escopo de organização vê tudo, inclusive o que ainda não tem setor
        sugerido; escopo de setor vê só as do seu setor.
        """
        queryset = IntakeItem.objects.filter(organization=organization)
        if AuthorizationService.can(user, catalog.ENTRADA_VISUALIZAR, ResourceContext.for_new(organization)):
            return queryset
        sector_ids = AuthorizationService.accessible_sector_ids(user, catalog.ENTRADA_VISUALIZAR)
        return queryset.filter(suggested_sector_id__in=sector_ids)

    @staticmethod
    def new_count(user, organization):
        return IntakeService.visible_queryset(user, organization).filter(status=IntakeItem.Status.NOVO).count()

    @staticmethod
    def requester_defaults(item):
        """(solicitante interno, solicitante externo) a partir do remetente.

        Se o e-mail é de alguém da equipe, ele é o solicitante interno e não há
        solicitante externo; senão, o remetente é o solicitante externo.
        """
        email = (item.sender_email or "").strip()
        internal = None
        if email:
            internal = (
                User.objects.filter(
                    email__iexact=email, is_active=True, profile__organization_id=item.organization_id
                )
                .order_by("id")
                .first()
            )
        if internal is not None:
            return internal, ""
        return None, item.sender_display if (item.sender_name or item.sender_email) else ""

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def register(
        organization,
        user,
        raw_content,
        subject="",
        sender_name="",
        sender_email="",
        source=IntakeItem.Source.EMAIL,
        received_at=None,
        external_id="",
    ):
        _require_anywhere(user, catalog.ENTRADA_REGISTRAR)
        if user.profile.organization_id != organization.pk:
            raise IntakeError("Você não pertence a esta organização.")

        raw_content = (raw_content or "").strip()
        subject = (subject or "").strip()
        sender_name = (sender_name or "").strip()
        sender_email = (sender_email or "").strip().lower()
        external_id = (external_id or "").strip()

        if not raw_content:
            raise IntakeError("Cole o texto da solicitação.")
        if len(raw_content) > MAX_CONTENT_LENGTH:
            limit = f"{MAX_CONTENT_LENGTH:,}".replace(",", ".")
            raise IntakeError(f"O texto é grande demais (máximo de {limit} caracteres).")
        if len(subject) > MAX_SUBJECT_LENGTH:
            raise IntakeError(f"O assunto passa de {MAX_SUBJECT_LENGTH} caracteres.")
        if len(sender_name) > MAX_SENDER_NAME_LENGTH:
            raise IntakeError(f"O nome do remetente passa de {MAX_SENDER_NAME_LENGTH} caracteres.")
        if len(external_id) > MAX_EXTERNAL_ID_LENGTH:
            raise IntakeError("O identificador externo é longo demais.")
        if source not in IntakeItem.Source.values:
            raise IntakeError("Origem desconhecida.")
        if sender_email:
            try:
                validate_email(sender_email)
            except ValidationError:
                raise IntakeError("Informe um e-mail válido para o remetente.") from None

        now = timezone.now()
        received_at = received_at or now
        if received_at > now + FUTURE_TOLERANCE:
            raise IntakeError("A data de recebimento não pode estar no futuro.")

        signature = textparse.content_signature(sender_email, subject, raw_content)
        duplicated = IntakeItem.objects.filter(
            organization=organization,
            content_hash=signature,
            status__in=[IntakeItem.Status.NOVO, IntakeItem.Status.CONVERTIDO],
            created_at__gte=now - DUPLICATE_WINDOW,
        ).exists()
        if duplicated:
            raise IntakeError("Esta solicitação já está na Caixa de Entrada.")
        if external_id and IntakeItem.objects.filter(
            organization=organization, source=source, external_id=external_id
        ).exists():
            raise IntakeError("Esta mensagem já foi recebida por este canal.")

        suggestion = suggest(
            organization,
            subject=subject,
            raw_content=raw_content,
            sender_name=sender_name,
            sender_email=sender_email,
            received_at=received_at,
        )
        try:
            with transaction.atomic():
                item = IntakeItem.objects.create(
                    organization=organization,
                    source=source,
                    external_id=external_id,
                    subject=subject,
                    sender_name=sender_name,
                    sender_email=sender_email,
                    raw_content=raw_content,
                    content_hash=signature,
                    received_at=received_at,
                    suggested_title=suggestion.title,
                    suggested_client=suggestion.client,
                    suggested_site=suggestion.site,
                    suggested_sector=suggestion.sector,
                    suggested_deadline=suggestion.deadline,
                    confidence=suggestion.confidence,
                    suggestion_reasons=suggestion.reasons,
                    created_by=user,
                )
        except IntegrityError:
            # Outra requisição registrou o mesmo identificador externo entre a checagem e a gravação.
            raise IntakeError("Esta mensagem já foi recebida por este canal.") from None

        _event(item, user, IntakeEvent.Kind.REGISTRADA, f"Origem: {item.get_source_display()}")
        return item

    # ------------------------------------------------------------------
    # Triagem
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def update_suggestions(item, user, **fields):
        unknown = set(fields) - set(EDITABLE_FIELDS)
        if unknown:
            raise IntakeError(f"Campo não editável: {', '.join(sorted(unknown))}.")

        item = _lock(item)
        _require(user, catalog.ENTRADA_TRIAR, item)
        if item.status != IntakeItem.Status.NOVO:
            raise IntakeError("Só uma solicitação nova pode ser corrigida.")

        if "suggested_title" in fields:
            fields["suggested_title"] = (fields["suggested_title"] or "").strip()
            if len(fields["suggested_title"]) > 200:
                raise IntakeError("O título passa de 200 caracteres.")

        client = fields.get("suggested_client", item.suggested_client)
        site = fields.get("suggested_site", item.suggested_site)
        sector = fields.get("suggested_sector", item.suggested_sector)
        _check_same_organization(item.organization_id, client, site, sector)
        _check_site_belongs_to_client(client, site)

        # Quem faz a triagem de um setor só não pode, sem querer, mandar a solicitação para um setor que não vê.
        try:
            AuthorizationService.require(
                user, catalog.ENTRADA_TRIAR, ResourceContext.for_new(item.organization, sector=sector, site=site)
            )
        except AuthorizationError:
            raise IntakeError(
                "Depois desta mudança você não teria mais acesso a esta solicitação. Escolha um setor que você gerencia."
            ) from None

        changes = []
        for name, new_value in fields.items():
            old_value = getattr(item, name)
            if old_value != new_value:
                changes.append(f"{EDITABLE_FIELDS[name]}: {_show(old_value)} → {_show(new_value)}")
                setattr(item, name, new_value)
        if not changes:
            return item

        item.save(update_fields=list(fields))
        _event(item, user, IntakeEvent.Kind.EDITADA, "\n".join(changes))
        return item

    @staticmethod
    @transaction.atomic
    def ignore(item, user, reason=""):
        item = _lock(item)
        _require(user, catalog.ENTRADA_TRIAR, item)
        if not IntakePolicy.can_transition(item, IntakeItem.Status.IGNORADO):
            raise IntakeError("Só uma solicitação nova pode ser ignorada.")
        reason = (reason or "").strip()
        if len(reason) > MAX_NOTE_LENGTH:
            raise IntakeError(f"O motivo passa de {MAX_NOTE_LENGTH} caracteres.")

        item.status = IntakeItem.Status.IGNORADO
        item.resolved_by = user
        item.resolved_at = timezone.now()
        item.resolution_note = reason
        item.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_note"])
        _event(item, user, IntakeEvent.Kind.IGNORADA, reason)
        return item

    @staticmethod
    @transaction.atomic
    def restore(item, user):
        item = _lock(item)
        _require(user, catalog.ENTRADA_TRIAR, item)
        if not IntakePolicy.can_transition(item, IntakeItem.Status.NOVO):
            raise IntakeError("Só uma solicitação ignorada pode ser restaurada.")

        item.status = IntakeItem.Status.NOVO
        item.resolved_by = None
        item.resolved_at = None
        item.resolution_note = ""
        item.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_note"])
        _event(item, user, IntakeEvent.Kind.RESTAURADA)
        return item

    @staticmethod
    @transaction.atomic
    def convert(
        item,
        user,
        *,
        title,
        owner,
        sector,
        requested_deadline=None,
        client=None,
        site=None,
        company=None,
        urgency=None,
        external_requester=None,
    ):
        """Cria a atividade a partir da solicitação — o mesmo caminho do editor.

        Tudo na mesma transação: se a atividade não puder ser criada, a
        solicitação continua nova e nada fica pela metade.
        """
        item = _lock(item)
        _require(user, catalog.ENTRADA_TRIAR, item)
        if not IntakePolicy.can_transition(item, IntakeItem.Status.CONVERTIDO):
            raise IntakeError("Esta solicitação já foi tratada.")

        title = (title or "").strip()
        if not title:
            raise IntakeError("Informe o nome da demanda.")
        if owner is None:
            raise IntakeError("Escolha quem fica com a demanda.")
        if sector is None:
            raise IntakeError("Escolha o setor responsável.")
        if urgency and urgency not in Activity.Urgency.values:
            raise IntakeError("Urgência desconhecida.")

        _check_same_organization(item.organization_id, client, site, sector, company)
        if owner.profile.organization_id != item.organization_id or not owner.is_active:
            raise IntakeError("Escolha quem fica com a demanda entre as pessoas da organização.")
        _check_site_belongs_to_client(client, site)

        requested_by, default_external = IntakeService.requester_defaults(item)
        if external_requester is None:
            external_requester = default_external
        external_requester = (external_requester or "").strip()

        try:
            activity = ActivityService.save_draft(
                item.organization,
                user,
                title=title,
                owner=owner,
                sector=sector,
                client=client,
                site=site,
                company=company,
                urgency=urgency or Activity.Urgency.MEDIA,
                requested_deadline=requested_deadline,
                external_requester=external_requester,
                requested_by=requested_by,
                description=build_activity_description(item),
            )
            ActivityService.publish_draft(activity, user)
        except ActivityError as exc:
            raise IntakeError(str(exc)) from exc

        item.status = IntakeItem.Status.CONVERTIDO
        item.activity = activity
        item.resolved_by = user
        item.resolved_at = timezone.now()
        item.save(update_fields=["status", "activity", "resolved_by", "resolved_at"])
        _event(item, user, IntakeEvent.Kind.CONVERTIDA, activity.code)
        return activity
