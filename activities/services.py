import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, DurationField, ExpressionWrapper, F, Max, Sum
from django.utils import timezone

from acessos import catalog
from acessos.services import AuthorizationError, AuthorizationService, ResourceContext
from audit.models import AuditLog
from audit.services import AuditService
from core.models import Tag
from notifications.models import Notification
from notifications.recipients import resolve_sector_and_admins, resolve_sector_managers
from notifications.services import EmailService, NotificationService

from . import policies, process_state
from .errors import ActivityError  # noqa: F401  (reexportado: `from .services import ActivityError`)
from .models import (
    Activity,
    ActivityAttachment,
    ActivityMessage,
    ActivityPendency,
    DeadlineConflict,
    DeadlineProposal,
    MessageKind,
    OwnerChangeLog,
    QueueEntry,
    QueuePositionChange,
    SectorTransfer,
    Task,
    TaskAssignment,
    TaskBlock,
    TaskChecklistItem,
    TaskExecutor,
    TaskMessage,
    TaskResponsavelChangeLog,
    TaskReturn,
    WorkSession,
)
from .policies import ActivityTransitionPolicy, TaskTransitionPolicy, open_pendency


User = get_user_model()


#: "Já realizei este trabalho": mesmo dia é livre; dias anteriores são permitidos
#: e destacados; se o trabalho começou há mais de N dias, o comentário (a
#: justificativa) passa a ser obrigatório. Sem aprovação: burocracia demais.
RETROACTIVE_JUSTIFICATION_DAYS = 7


def require_action(user, action_key, resource=None):
    """Exige uma ação do catálogo dentro do escopo do recurso.

    A negação vira ActivityError para as telas continuarem tratando erro de
    autorização e erro de regra de negócio da mesma forma.
    """
    try:
        AuthorizationService.require(user, action_key, resource)
    except AuthorizationError as exc:
        raise ActivityError(str(exc)) from exc


def _same_organization(*objects):
    orgs = {obj.organization_id for obj in objects if obj is not None}
    return len(orgs) <= 1


def _pick_sector_manager(sector):
    """Um gestor do setor para virar dono temporário da atividade pendente.

    Vira dono só para aparecer na fila certa ("Minhas atividades"); quem de
    fato pode aprovar continua decidido pelo motor de autorização
    (`ATIVIDADE_APROVAR_PENDENCIA`), não por este vínculo organizacional —
    por isso os demais gestores do setor também são avisados, mesmo sem
    virar dono (ver `resolve_sector_managers`).
    """
    managers = sorted(resolve_sector_managers(sector), key=lambda u: u.get_username())
    return managers[0] if managers else None


MENTION_PATTERN = re.compile(r"@([\w.]+)")


def _truncate_mention_text(text, limit=200):
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def find_mentioned_users(text, author, resource):
    """Extrai @usuário de qualquer texto livre do sistema (Regras 06 §28-32).

    Só individual no D0 — nunca @setor. Mencionar não concede acesso: a
    pessoa só é notificada se já for autorizada a participar daquele
    contexto (§29). Uma menção inválida ou sem acesso é ignorada em
    silêncio, sem quebrar a ação que está sendo executada.

    `resource` deve ser sempre a Activity ou a Task do contexto — nunca um
    objeto satélite como ActivityPendency/TaskReturn/TaskBlock/
    TaskAssignment/DeadlineConflict/DeadlineProposal, que o motor de
    autorização não sabe resolver e cairia num contexto sem organização
    (nega tudo).
    """
    raw_tokens = set(MENTION_PATTERN.findall(text or ""))
    if not raw_tokens:
        return set()

    # O username aceita ponto (é o e-mail completo em algumas organizações,
    # ex. "@paulo@biasiengenharia.com.br"), então o regex captura de forma
    # gulosa e inclui pontuação de frase colada ao final ("@fulano." vira
    # "fulano."). Tenta o token inteiro primeiro; se não existir ninguém com
    # esse username exato, tenta de novo sem um caractere de pontuação final.
    usernames = set()
    for token in raw_tokens:
        usernames.add(token)
        stripped = token.rstrip(".,;:!?")
        if stripped and stripped != token:
            usernames.add(stripped)

    candidates = User.objects.filter(username__in=usernames, is_active=True).exclude(id=author.id)
    return {
        user
        for user in candidates
        if AuthorizationService.can(user, catalog.COMUNICACAO_PARTICIPAR, resource)
    }


def notify_mentions(text, author, resource, activity=None, task=None):
    """Extrai @menções de `text` e notifica quem for autorizado.

    `resource` é o objeto usado para checar a permissão (ver
    `find_mentioned_users`); `activity`/`task` são os campos de contexto
    passados para `NotificationService.notify` (normalmente o mesmo objeto
    de `resource`, mas mantidos separados porque `Notification` só aceita
    uma Activity e/ou uma Task, nunca outro tipo).

    Retorna o conjunto de usuários notificados, para quem chama poder
    excluí-los de uma notificação "normal" paralela (evita notificar a
    mesma pessoa duas vezes pelo mesmo evento).
    """
    mentioned = find_mentioned_users(text, author, resource)
    if mentioned:
        NotificationService.notify(
            users=mentioned,
            event_type=Notification.EventType.MENTIONED,
            title="Você foi mencionado",
            message=_truncate_mention_text(text),
            activity=activity,
            task=task,
            actor=author,
        )
    return mentioned


class ActivityService:
    # ------------------------------------------------------------------
    # Criação e responsabilidade
    # ------------------------------------------------------------------

    @staticmethod
    def _finalize_creation(activity, created_by):
        """Efeitos colaterais do momento em que uma atividade passa a existir
        de verdade para o resto do sistema — reaproveitado tanto por
        `create_activity` (criação direta, sem rascunho) quanto por
        `publish_draft` (criação via wizard de 3 etapas)."""
        AuditService.log(user=created_by, action=AuditLog.Action.CREATE, activity=activity, new_value=activity.title)
        NotificationService.notify(
            users={activity.owner, created_by},
            event_type=Notification.EventType.ACTIVITY_CREATED,
            title="Atividade criada",
            message=f"A atividade '{activity.title}' foi criada.",
            activity=activity,
            actor=created_by,
        )
        notify_mentions(activity.description, created_by, activity, activity=activity)

    @staticmethod
    @transaction.atomic
    def create_activity(
        organization,
        title,
        owner,
        created_by,
        description="",
        company=None,
        site=None,
        cost_center=None,
        requested_deadline=None,
        client=None,
        urgency=None,
        sector=None,
        address="",
        tags=None,
    ):
        require_action(
            created_by,
            catalog.ATIVIDADE_CRIAR,
            ResourceContext.for_new(
                organization, company=company, sector=sector, site=site, cost_center=cost_center, owner=owner
            ),
        )
        if not title:
            raise ActivityError("Informe o resultado esperado da atividade.")
        if owner is None:
            raise ActivityError("Toda atividade precisa de um único dono.")

        activity = Activity.objects.create(
            organization=organization,
            client=client,
            company=company,
            site=site,
            cost_center=cost_center,
            sector=sector,
            title=title,
            description=description,
            urgency=urgency or Activity.Urgency.MEDIA,
            address=address,
            owner=owner,
            created_by=created_by,
            requested_deadline=requested_deadline,
        )
        if tags:
            activity.tags.set(tags)

        ActivityService._finalize_creation(activity, created_by)
        return activity

    @staticmethod
    @transaction.atomic
    def save_draft(organization, created_by, activity=None, **fields):
        """Cria (se `activity` for None) ou atualiza um rascunho — nunca
        valida `title`/`owner`, nunca dispara auditoria/notificação: um
        rascunho ainda não existe para o resto do sistema, só para quem o
        está preenchendo (wizard de 3 etapas). Campos vazios de M2M (`tags`)
        são tratados à parte, o resto é salvo direto no model."""
        tags = fields.pop("tags", None)
        title = (fields.pop("title", None) or "").strip() or Activity.DRAFT_TITLE_PLACEHOLDER

        if activity is None:
            require_action(
                created_by,
                catalog.ATIVIDADE_CRIAR,
                ResourceContext.for_new(
                    organization,
                    company=fields.get("company"),
                    sector=fields.get("sector"),
                    site=fields.get("site"),
                    cost_center=fields.get("cost_center"),
                    owner=fields.get("owner"),
                ),
            )
            activity = Activity(
                organization=organization,
                created_by=created_by,
                status=Activity.Status.RASCUNHO,
                title=title,
            )
        else:
            if activity.status != Activity.Status.RASCUNHO:
                raise ActivityError("Esta atividade já foi criada e não é mais um rascunho.")
            if activity.created_by_id != created_by.id:
                raise ActivityError("Você não pode editar o rascunho de outra pessoa.")
            activity.title = title

        for field_name, value in fields.items():
            setattr(activity, field_name, value)
        activity.save()
        if tags is not None:
            activity.tags.set(tags)
        return activity

    @staticmethod
    @transaction.atomic
    def publish_draft(activity, user):
        """Transforma um rascunho em atividade de verdade: revalida
        autorização com o contexto final (pode ter mudado desde a criação do
        rascunho), exige título e dono de verdade, e só então dispara os
        mesmos efeitos colaterais de `create_activity`."""
        if activity.status != Activity.Status.RASCUNHO:
            raise ActivityError("Esta atividade já foi publicada.")
        require_action(user, catalog.ATIVIDADE_CRIAR, ResourceContext.of(activity))
        if not activity.title or activity.title == Activity.DRAFT_TITLE_PLACEHOLDER:
            raise ActivityError("Informe o resultado esperado antes de concluir.")
        if activity.owner_id is None:
            raise ActivityError("Toda atividade precisa de um único dono antes de concluir.")

        activity.status = Activity.Status.ABERTA
        activity.save(update_fields=["status"])
        ActivityService._finalize_creation(activity, user)
        return activity

    @staticmethod
    @transaction.atomic
    def discard_draft(activity, user):
        """Descarta um rascunho nunca publicado — exclusão de verdade (sem
        rastro de auditoria a preservar, já que nada foi anunciado ao resto
        do sistema); os anexos do rascunho somem em cascata."""
        if activity.status != Activity.Status.RASCUNHO:
            raise ActivityError("Só é possível descartar um rascunho ainda não publicado.")
        if activity.created_by_id != user.id:
            raise ActivityError("Você não pode descartar o rascunho de outra pessoa.")
        for attachment in activity.attachments.all():
            attachment.file.delete(save=False)
        activity.delete()

    @staticmethod
    @transaction.atomic
    def change_owner(activity, new_owner, changed_by):
        require_action(changed_by, catalog.ATIVIDADE_ALTERAR_DONO, activity)
        ActivityTransitionPolicy.assert_allowed(activity, "change_owner", changed_by)
        if new_owner.id == activity.owner_id:
            raise ActivityError("Este usuário já é o dono da atividade.")

        previous_owner = activity.owner
        activity.owner = new_owner
        activity.save(update_fields=["owner"])

        OwnerChangeLog.objects.create(
            activity=activity, previous_owner=previous_owner, new_owner=new_owner, changed_by=changed_by
        )
        AuditService.log(
            user=changed_by,
            action=AuditLog.Action.OWNER_CHANGED,
            activity=activity,
            old_value=previous_owner.get_username(),
            new_value=new_owner.get_username(),
        )
        NotificationService.notify(
            users={previous_owner, new_owner},
            event_type=Notification.EventType.OWNER_CHANGED,
            title="Dono da atividade alterado",
            message=f"O dono de '{activity.title}' passou de {previous_owner} para {new_owner}.",
            activity=activity,
            actor=changed_by,
        )
        return activity

    @staticmethod
    @transaction.atomic
    def claim(activity, user):
        """Assumir uma atividade da fila do próprio grupo (fila por setor):
        a pessoa vira dona sem precisar de quem tinha autorização para
        transferir para qualquer um — só para o que já está endereçado ao
        setor dela (Regra 6, tela de fila)."""
        require_action(user, catalog.ATIVIDADE_ASSUMIR, activity)
        ActivityTransitionPolicy.assert_allowed(activity, "claim", user)
        if activity.sector_id is None:
            raise ActivityError("Esta atividade não possui um grupo designado para ser assumida pela fila.")
        if user.id == activity.owner_id:
            raise ActivityError("Você já é o dono desta atividade.")

        previous_owner = activity.owner
        activity.owner = user
        activity.save(update_fields=["owner"])

        OwnerChangeLog.objects.create(
            activity=activity, previous_owner=previous_owner, new_owner=user, changed_by=user
        )
        AuditService.log(
            user=user,
            action=AuditLog.Action.OWNER_CHANGED,
            activity=activity,
            old_value=previous_owner.get_username(),
            new_value=user.get_username(),
            reason="Assumida da fila do grupo",
        )
        NotificationService.notify(
            users={previous_owner, user},
            event_type=Notification.EventType.OWNER_CHANGED,
            title="Atividade assumida",
            message=f"{user.get_username()} assumiu a atividade '{activity.title}'.",
            activity=activity,
            actor=user,
        )
        return activity

    @staticmethod
    @transaction.atomic
    def update_activity(activity, user, **fields):
        """Edita campos não sensíveis da atividade, auditando cada alteração.

        Dono, conclusão e cancelamento possuem serviços próprios e não passam por aqui.
        """
        require_action(user, catalog.ATIVIDADE_EDITAR, activity)
        ActivityTransitionPolicy.assert_allowed(activity, "edit", user)

        editable = {
            "title",
            "description",
            "internal_notes",
            "requested_by",
            "requested_deadline",
            "company",
            "site",
            "cost_center",
            "client",
            "urgency",
            "sector",
            "address",
            "external_requester",
            "files_location",
        }
        changed = []
        for field, value in fields.items():
            if field not in editable:
                continue
            old_value = getattr(activity, field)
            if old_value == value:
                continue
            if field == "title" and not value:
                raise ActivityError("Informe o resultado esperado da atividade.")
            setattr(activity, field, value)
            changed.append(field)
            AuditService.log(
                user=user,
                action=AuditLog.Action.UPDATE,
                activity=activity,
                field_name=field,
                old_value=old_value,
                new_value=value,
            )

        if changed:
            activity.save(update_fields=changed)

        # M2M não passa por setattr/save — camada puramente informativa,
        # sem auditoria de valor anterior (mesmo espírito de TaskStage: não
        # é regra de negócio).
        if "tags" in fields:
            activity.tags.set(fields["tags"])

        if "description" in changed:
            notify_mentions(activity.description, user, activity, activity=activity)

        return activity

    @staticmethod
    def _register_first_action(activity_or_task):
        """Marca a primeira ação relevante, se ainda não registrada (Regras 02 §45)."""
        if activity_or_task.first_action_at is None:
            activity_or_task.first_action_at = timezone.now()
            activity_or_task.save(update_fields=["first_action_at"])

    @staticmethod
    def _mark_in_progress(activity, user):
        """Quando o trabalho numa tarefa começa, a atividade deixa de estar só
        "Aberta" e passa a "Em andamento" (auditado). Só age sobre `ABERTA`; o
        `UPDATE ... WHERE status = ABERTA` evita mexer numa atividade que outra
        pessoa acabou de marcar pendente ou finalizar."""
        changed = Activity.objects.filter(pk=activity.pk, status=Activity.Status.ABERTA).update(
            status=Activity.Status.EM_ANDAMENTO
        )
        if not changed:
            return False
        activity.status = Activity.Status.EM_ANDAMENTO
        AuditService.log(
            user=user,
            action=AuditLog.Action.UPDATE,
            activity=activity,
            field_name="status",
            old_value=Activity.Status.ABERTA,
            new_value=Activity.Status.EM_ANDAMENTO,
            reason="O trabalho na primeira tarefa começou.",
        )
        return True

    @staticmethod
    @transaction.atomic
    def change_sector(activity, sector, user):
        """Troca o setor responsável (o "grupo designado"). Recusa enquanto houver
        pendência aguardando aprovação: o setor define quem aprova e o dono já foi
        trocado para o gestor."""
        require_action(user, catalog.ATIVIDADE_EDITAR, activity)
        ActivityTransitionPolicy.assert_allowed(activity, "change_sector", user)
        if sector is None:
            raise ActivityError("Escolha o setor responsável.")
        if not _same_organization(activity, sector):
            raise ActivityError("O setor informado pertence a outra organização.")
        if sector.pk == activity.sector_id:
            raise ActivityError("Esta atividade já está neste setor.")
        return ActivityService.update_activity(activity, user, sector=sector)

    @staticmethod
    def _unmet_criteria_message(names):
        return (
            "Não é possível concluir com sucesso ainda. Falta atender: "
            + "; ".join(names)
            + ". Se a atividade precisa ser encerrada mesmo assim, finalize como “Concluído com pendências”."
        )

    @staticmethod
    @transaction.atomic
    def complete_activity(activity, user):
        require_action(user, catalog.ATIVIDADE_CONCLUIR, activity)
        ActivityTransitionPolicy.assert_allowed(activity, "complete", user)
        # Caminho antigo de conclusão = "sucesso": mesma regra do finalize,
        # senão seria uma porta lateral para fechar sem os critérios.
        unmet_criteria = process_state.unmet_required_criterion_names(activity)
        if unmet_criteria:
            raise ActivityError(ActivityService._unmet_criteria_message(unmet_criteria))

        old_status = activity.status
        activity.status = Activity.Status.CONCLUIDA
        activity.completed_at = timezone.now()
        activity.completed_by = user
        activity.save(update_fields=["status", "completed_at", "completed_by"])

        AuditService.log(
            user=user, action=AuditLog.Action.COMPLETE, activity=activity, old_value=old_status, new_value=activity.status
        )
        NotificationService.notify(
            users={activity.owner},
            event_type=Notification.EventType.ACTIVITY_COMPLETED,
            title="Atividade concluída",
            message=f"A atividade '{activity.title}' foi concluída.",
            activity=activity,
            actor=user,
        )
        return activity

    @staticmethod
    @transaction.atomic
    def cancel_activity(activity, user, reason):
        require_action(user, catalog.ATIVIDADE_CANCELAR, activity)
        ActivityTransitionPolicy.assert_allowed(activity, "cancel", user)
        if not reason:
            raise ActivityError("Informe o motivo do cancelamento.")

        old_status = activity.status
        activity.status = Activity.Status.CANCELADA
        activity.cancelled_at = timezone.now()
        activity.cancelled_reason = reason
        activity.save(update_fields=["status", "cancelled_at", "cancelled_reason"])

        AuditService.log(
            user=user,
            action=AuditLog.Action.CANCEL,
            activity=activity,
            old_value=old_status,
            new_value=activity.status,
            reason=reason,
        )
        NotificationService.notify(
            users={activity.owner},
            event_type=Notification.EventType.ACTIVITY_CANCELLED,
            title="Atividade cancelada",
            message=f"A atividade '{activity.title}' foi cancelada. Motivo: {reason}",
            activity=activity,
            actor=user,
        )
        notify_mentions(reason, user, activity, activity=activity)
        return activity

    @staticmethod
    @transaction.atomic
    def reopen_activity(activity, user, reason):
        require_action(user, catalog.ATIVIDADE_REABRIR, activity)
        ActivityTransitionPolicy.assert_allowed(activity, "reopen", user)
        if not reason:
            raise ActivityError("Informe o motivo da reabertura.")

        old_status = activity.status
        activity.status = Activity.Status.EM_ANDAMENTO
        activity.completed_at = None
        activity.completed_by = None
        activity.reopened_at = timezone.now()
        activity.save(update_fields=["status", "completed_at", "completed_by", "reopened_at"])

        AuditService.log(
            user=user,
            action=AuditLog.Action.REOPEN,
            activity=activity,
            old_value=old_status,
            new_value=activity.status,
            reason=reason,
        )
        NotificationService.notify(
            users={activity.owner},
            event_type=Notification.EventType.ACTIVITY_REOPENED,
            title="Atividade reaberta",
            message=f"A atividade '{activity.title}' foi reaberta. Motivo: {reason}"[:255],
            activity=activity,
            actor=user,
        )
        return activity

    # ------------------------------------------------------------------
    # Finalização (popup único) e pendências (fila do gestor)
    # ------------------------------------------------------------------

    #: Resultados que encerram a atividade como concluída — os demais
    #: (declinado/cancelado) encerram como cancelada (Regras avulsas).
    OUTCOMES_AS_CONCLUDED = (
        Activity.CompletionOutcome.SUCESSO,
        Activity.CompletionOutcome.CONCLUIDO_COM_PENDENCIAS,
    )

    @staticmethod
    @transaction.atomic
    def finalize(activity, user, outcome, comment):
        """Popup único de finalização: um resultado explícito — Sucesso,
        Concluído com pendências, Declinado ou Cancelado — sempre com
        comentário obrigatório, no lugar dos antigos "Concluir"/"Cancelar"
        em ações separadas e sem exigir explicação."""
        if outcome not in Activity.CompletionOutcome.values:
            raise ActivityError("Selecione um resultado válido para a finalização.")
        comment = (comment or "").strip()
        if not comment:
            raise ActivityError("O comentário de finalização é obrigatório.")
        if activity.status in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA):
            raise ActivityError("Esta atividade já foi finalizada.")

        as_concluded = outcome in ActivityService.OUTCOMES_AS_CONCLUDED
        action_key = catalog.ATIVIDADE_CONCLUIR if as_concluded else catalog.ATIVIDADE_CANCELAR
        require_action(user, action_key, activity)

        unmet_criteria = []
        if as_concluded:
            ActivityTransitionPolicy.assert_allowed(activity, "complete", user)
            unmet_criteria = process_state.unmet_required_criterion_names(activity)
            if unmet_criteria and outcome == Activity.CompletionOutcome.SUCESSO:
                raise ActivityError(ActivityService._unmet_criteria_message(unmet_criteria))

        now = timezone.now()
        old_status = activity.status
        activity.completion_outcome = outcome
        update_fields = ["completion_outcome"]
        if as_concluded:
            activity.status = Activity.Status.CONCLUIDA
            activity.completed_at = now
            activity.completed_by = user
            update_fields += ["status", "completed_at", "completed_by"]
        else:
            activity.status = Activity.Status.CANCELADA
            activity.cancelled_at = now
            activity.cancelled_reason = comment
            update_fields += ["status", "cancelled_at", "cancelled_reason"]
        activity.save(update_fields=update_fields)

        # Uma finalização enquanto ainda pendente encerra a pendência aberta
        # — não faz sentido seguir esperando aprovação de algo já finalizado.
        activity.pendencies.filter(status=ActivityPendency.Status.ABERTA).update(
            status=ActivityPendency.Status.ENCERRADA, resolved_by=user, resolved_at=now
        )

        outcome_label = Activity.CompletionOutcome(outcome).label
        # "Concluído com pendências" pode fechar com critério obrigatório em
        # aberto (Regras 02:1223 proíbe a conclusão *silenciosa*): o que ficou
        # de fora vai para a auditoria e para a conversa da atividade.
        pending_note = (
            f" Critérios de aceite obrigatórios não atendidos: {'; '.join(unmet_criteria)}." if unmet_criteria else ""
        )
        AuditService.log(
            user=user,
            action=AuditLog.Action.COMPLETE if as_concluded else AuditLog.Action.CANCEL,
            activity=activity,
            old_value=old_status,
            new_value=activity.status,
            reason=f"{outcome_label}: {comment}{pending_note}",
        )
        # O comentário é obrigatório e entra no histórico único da tela —
        # a mesma conversa que já mostra comentários e anexos (Regra pedida).
        ActivityMessage.objects.create(
            activity=activity, author=user, body=f"Finalização ({outcome_label}): {comment}{pending_note}"
        )

        event_type = (
            Notification.EventType.ACTIVITY_COMPLETED
            if as_concluded
            else Notification.EventType.ACTIVITY_CANCELLED
        )
        NotificationService.notify(
            users={activity.owner},
            event_type=event_type,
            title="Atividade finalizada" if as_concluded else "Atividade cancelada",
            message=f"A atividade '{activity.title}' foi finalizada como \"{outcome_label}\". {comment}",
            activity=activity,
            actor=user,
        )
        notify_mentions(comment, user, activity, activity=activity)
        return activity

    @staticmethod
    @transaction.atomic
    def mark_pending(activity, user, reason, comment, decision_deadline=None, notify_client=False):
        """Marca a atividade como pendente (Regras avulsas — fila do gestor).

        Dois motivos pedem decisão do gestor do setor, com prazo obrigatório
        para essa decisão: a atividade vai temporariamente para a fila dele
        ("Minhas atividades"). Os demais motivos só avisam — a atividade
        fica visível como pendente, sem trocar de dono.
        """
        require_action(user, catalog.ATIVIDADE_MARCAR_PENDENTE, activity)
        ActivityTransitionPolicy.assert_allowed(activity, "mark_pending", user)
        if reason not in ActivityPendency.Reason.values:
            raise ActivityError("Selecione um motivo de pendência válido.")
        comment = (comment or "").strip()
        if not comment:
            raise ActivityError("O comentário da pendência é obrigatório.")

        requires_approval = reason in ActivityPendency.APPROVAL_REASONS
        approver = None
        previous_owner = None
        if requires_approval:
            if not decision_deadline:
                raise ActivityError("Informe o prazo para o gestor decidir.")
            if activity.sector_id is None:
                raise ActivityError(
                    "Esta atividade não possui um grupo designado — defina um grupo antes de "
                    "marcar uma pendência que precisa de aprovação do gestor."
                )
            approver = _pick_sector_manager(activity.sector)
            if approver is None:
                raise ActivityError(
                    f"O grupo \"{activity.sector.name}\" não possui um gestor cadastrado para aprovar esta pendência."
                )
            previous_owner = activity.owner

        pendency = ActivityPendency.objects.create(
            activity=activity,
            reason=reason,
            comment=comment,
            decision_deadline=decision_deadline,
            notify_client=bool(notify_client) and reason == ActivityPendency.Reason.INFORMACOES_CLIENTE,
            previous_owner=previous_owner,
            approver=approver,
            opened_by=user,
        )

        old_status = activity.status
        activity.status = Activity.Status.PENDENTE
        activity.save(update_fields=["status"])

        AuditService.log(
            user=user,
            action=AuditLog.Action.PENDENCY_OPENED,
            activity=activity,
            old_value=old_status,
            new_value=activity.status,
            reason=pendency.get_reason_display(),
        )
        ActivityMessage.objects.create(
            activity=activity, author=user, body=f"Pendência ({pendency.get_reason_display()}): {comment}"
        )

        if requires_approval and approver.id != activity.owner_id:
            activity.owner = approver
            activity.save(update_fields=["owner"])
            OwnerChangeLog.objects.create(
                activity=activity, previous_owner=previous_owner, new_owner=approver, changed_by=user
            )
            AuditService.log(
                user=user,
                action=AuditLog.Action.OWNER_CHANGED,
                activity=activity,
                old_value=previous_owner.get_username(),
                new_value=approver.get_username(),
                reason="Pendência aguardando aprovação do gestor",
            )

        if requires_approval:
            recipients = resolve_sector_managers(activity.sector)
            NotificationService.notify(
                users=recipients,
                event_type=Notification.EventType.ACTIVITY_APPROVAL_NEEDED,
                title="Atividade aguardando sua aprovação",
                message=f"A atividade '{activity.title}' está pendente: {pendency.get_reason_display()}. Prazo: {decision_deadline:%d/%m/%Y %H:%M}.",
                activity=activity,
                actor=user,
            )
            EmailService.send_activity_approval_needed(activity, pendency, recipients)
            if previous_owner is not None:
                NotificationService.notify(
                    users={previous_owner},
                    event_type=Notification.EventType.ACTIVITY_PENDING,
                    title="Atividade pendente",
                    message=f"A atividade '{activity.title}' está pendente e aguarda aprovação do gestor.",
                    activity=activity,
                    actor=user,
                )
        else:
            NotificationService.notify(
                users={activity.owner},
                event_type=Notification.EventType.ACTIVITY_PENDING,
                title="Atividade pendente",
                message=f"A atividade '{activity.title}' está pendente: {pendency.get_reason_display()}.",
                activity=activity,
                actor=user,
            )
            if pendency.notify_client:
                EmailService.send_client_information_request(activity, pendency)

        notify_mentions(comment, user, activity, activity=activity)
        return pendency

    @staticmethod
    @transaction.atomic
    def approve_pendency(activity, user, comment=""):
        """Gestor aprova a pendência: a atividade volta para quem a
        designou (ou segue com o gestor, se não houver a quem devolver),
        com status "Em andamento" (Regra pedida — item 4)."""
        require_action(user, catalog.ATIVIDADE_APROVAR_PENDENCIA, activity)
        ActivityTransitionPolicy.assert_allowed(activity, "approve_pendency", user)
        pendency = open_pendency(activity, requires_approval=True)

        comment = (comment or "").strip()
        now = timezone.now()
        pendency.status = ActivityPendency.Status.APROVADA
        pendency.resolved_by = user
        pendency.resolved_at = now
        pendency.resolution_comment = comment
        pendency.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_comment"])

        old_status = activity.status
        activity.status = Activity.Status.EM_ANDAMENTO
        activity.save(update_fields=["status"])

        new_owner = pendency.previous_owner
        if new_owner is not None and new_owner.id != activity.owner_id:
            previous_owner = activity.owner
            activity.owner = new_owner
            activity.save(update_fields=["owner"])
            OwnerChangeLog.objects.create(
                activity=activity, previous_owner=previous_owner, new_owner=new_owner, changed_by=user
            )

        AuditService.log(
            user=user,
            action=AuditLog.Action.PENDENCY_APPROVED,
            activity=activity,
            old_value=old_status,
            new_value=activity.status,
            reason=comment,
        )
        ActivityMessage.objects.create(
            activity=activity,
            author=user,
            body=f"Pendência aprovada.{' ' + comment if comment else ''}",
        )

        NotificationService.notify(
            users={activity.owner},
            event_type=Notification.EventType.ACTIVITY_APPROVED,
            title="Pendência aprovada",
            message=f"A pendência de '{activity.title}' foi aprovada. A atividade voltou para a sua fila.",
            activity=activity,
            actor=user,
        )
        notify_mentions(comment, user, activity, activity=activity)
        return pendency

    @staticmethod
    @transaction.atomic
    def resolve_pendency(activity, user, comment=""):
        """Encerra uma pendência que só **avisava** (material ou informações do
        cliente): não há gestor para aprovar, então quem pode marcar pendência
        também a resolve. A atividade volta a "Em andamento" (se o trabalho já
        começou) ou "Aberta"; a pendência fica `ENCERRADA`."""
        require_action(user, catalog.ATIVIDADE_MARCAR_PENDENTE, activity)
        ActivityTransitionPolicy.assert_allowed(activity, "resolve_pendency", user)
        pendency = open_pendency(activity, requires_approval=False)

        comment = (comment or "").strip()
        now = timezone.now()
        pendency.status = ActivityPendency.Status.ENCERRADA
        pendency.resolved_by = user
        pendency.resolved_at = now
        pendency.resolution_comment = comment
        pendency.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_comment"])

        old_status = activity.status
        activity.status = Activity.Status.EM_ANDAMENTO if activity.first_action_at else Activity.Status.ABERTA
        activity.save(update_fields=["status"])

        AuditService.log(
            user=user,
            action=AuditLog.Action.PENDENCY_RESOLVED,
            activity=activity,
            old_value=old_status,
            new_value=activity.status,
            reason=f"{pendency.get_reason_display()}{': ' + comment if comment else ''}",
        )
        ActivityMessage.objects.create(
            activity=activity,
            author=user,
            body=f"Pendência resolvida ({pendency.get_reason_display()}).{' ' + comment if comment else ''}",
        )
        if user.id != activity.owner_id:
            NotificationService.notify(
                users={activity.owner},
                event_type=Notification.EventType.ACTIVITY_APPROVED,
                title="Pendência resolvida",
                message=f"A pendência de '{activity.title}' foi resolvida.",
                activity=activity,
                actor=user,
            )
        notify_mentions(comment, user, activity, activity=activity)
        return pendency


class ActivityAttachmentService:
    """Anexos de uma atividade (Regra 13): cada arquivo vai para a pasta da
    atividade dentro de `MEDIA_ROOT`, nomeada pelo código gerado ao criar a
    atividade — mesmo princípio da regra original, adaptado para um caminho
    portátil em vez do disco local de uma máquina específica."""

    @staticmethod
    @transaction.atomic
    def add(activity, uploaded_file, uploaded_by):
        is_own_draft = activity.status == Activity.Status.RASCUNHO and activity.created_by_id == uploaded_by.id
        if not is_own_draft:
            # Rascunho sem dono ainda não tem contexto para o escopo relacional
            # "minhas atividades" resolver — mas quem criou o rascunho sempre
            # pode mexer nele, igual a qualquer outro campo do wizard.
            require_action(uploaded_by, catalog.ATIVIDADE_EDITAR, activity)
        if not uploaded_file:
            raise ActivityError("Selecione um arquivo para anexar.")

        attachment = ActivityAttachment.objects.create(
            activity=activity,
            file=uploaded_file,
            original_name=getattr(uploaded_file, "name", "") or "",
            uploaded_by=uploaded_by,
        )
        AuditService.log(
            user=uploaded_by,
            action=AuditLog.Action.UPDATE,
            activity=activity,
            field_name="anexo",
            new_value=attachment.original_name,
        )
        return attachment

    @staticmethod
    @transaction.atomic
    def remove(attachment, removed_by):
        activity = attachment.activity
        if activity.status == Activity.Status.RASCUNHO:
            if activity.created_by_id != removed_by.pk:
                raise ActivityError("Você não pode editar o rascunho de outra pessoa.")
        else:
            require_action(removed_by, catalog.ATIVIDADE_EDITAR, activity)
        name = attachment.original_name
        attachment.file.delete(save=False)
        attachment.delete()
        AuditService.log(
            user=removed_by,
            action=AuditLog.Action.UPDATE,
            activity=activity,
            field_name="anexo",
            old_value=name,
        )


# Atalhos de título no "+ Nova tarefa" (mesma ideia do Odoo: #tag e
# @pessoa digitados no título já preenchem os campos correspondentes, sem
# abrir mais campos). O grupo \s antes evita casar um # ou @ no meio de uma
# palavra (ex.: "cotação#123" não devia virar tag "123"). A menção aceita
# @ no meio do token (não só no início) porque o username aqui é o
# e-mail completo (ex. "@paulo@biasiengenharia.com.br") — só a tag exclui
# @ do meio, para "#tag@algo" não grudar os dois num token só.
TAG_TOKEN_PATTERN = re.compile(r"(?:^|\s)#([^\s#@]+)")
MENTION_TOKEN_PATTERN = re.compile(r"(?:^|\s)@([^\s#]+)")


class TaskService:
    # ------------------------------------------------------------------
    # Criação e execução
    # ------------------------------------------------------------------

    @staticmethod
    def parse_quick_title(title, organization):
        """Extrai #tag e @pessoa do título digitado no popup "+ Nova
        tarefa" (mesmo espírito do parser de atalhos do Odoo). Só resolve
        e retorna os dados — quem chama decide o que fazer com eles
        (`task.tags.set(...)`, `TaskService.add_executor(...)`) depois da
        tarefa já criada; este método nunca grava nada sozinho.

        Uma @menção ambígua (mais de um usuário) ou que não corresponde a
        ninguém permanece como texto no título, sem tentar adivinhar —
        mesma regra usada em `MessageService._mentioned_users`.
        """
        tag_names = TAG_TOKEN_PATTERN.findall(title)
        mentioned_usernames = MENTION_TOKEN_PATTERN.findall(title)

        clean_title = TAG_TOKEN_PATTERN.sub(" ", title)
        clean_title = MENTION_TOKEN_PATTERN.sub(" ", clean_title)

        tags = []
        seen_tag_names = set()
        for name in tag_names:
            key = name.lower()
            if key in seen_tag_names:
                continue
            seen_tag_names.add(key)
            tag = Tag.objects.filter(organization=organization, name__iexact=name).first()
            if tag is None:
                tag = Tag.objects.create(organization=organization, name=name)
            tags.append(tag)

        assignee = None
        unresolved_usernames = []
        for username in mentioned_usernames:
            candidates = User.objects.filter(
                username__iexact=username, profile__organization=organization, is_active=True
            )
            if candidates.count() == 1:
                assignee = candidates.first()
            else:
                unresolved_usernames.append(username)

        if unresolved_usernames:
            clean_title = clean_title.rstrip() + " " + " ".join(f"@{u}" for u in unresolved_usernames)

        clean_title = " ".join(clean_title.split())
        return {"title": clean_title, "tags": tags, "assignee": assignee}

    @staticmethod
    @transaction.atomic
    def create_task(
        activity, sector, title, created_by, responsavel, description="", order=1, depends_on=None,
        requested_deadline=None, tags=None, participantes=None,
    ):
        # A tarefa nasce no setor informado: é esse o escopo que autoriza.
        require_action(
            created_by,
            catalog.TAREFA_CRIAR,
            ResourceContext.for_new(
                activity.organization,
                company=activity.company,
                sector=sector,
                site=activity.site,
                cost_center=activity.cost_center,
                owner=activity.owner,
            ),
        )
        return TaskService._create_task_core(
            activity, sector, title, created_by, responsavel, description=description, order=order,
            depends_on=depends_on, requested_deadline=requested_deadline, tags=tags, participantes=participantes,
        )

    @staticmethod
    def _create_task_core(
        activity, sector, title, created_by, responsavel, description="", order=1, depends_on=None,
        requested_deadline=None, tags=None, participantes=None, process_step=None, enqueue=True, notify=True,
    ):
        """Validação e gravação de uma tarefa nova — **sem autorizar**.

        Método interno: quem chama é responsável por já ter exigido a ação
        certa do catálogo. Hoje são dois chamadores, cada um com a sua:
        `create_task` (`tarefa.criar` no setor da tarefa) e
        `ProcessApplicationService.apply` (`processo.aplicar` na atividade,
        para materializar as etapas de uma versão publicada). Nenhuma view
        chama este método.

        `enqueue=False` deixa a tarefa `DISPONIVEL` e fora da fila — é como a
        etapa que aguarda a anterior nasce. `notify=False` fica por conta de
        quem cria várias tarefas de uma vez e agrega os avisos.
        """
        if not _same_organization(activity, sector):
            raise ActivityError("O setor informado pertence a outra organização.")
        if not title:
            raise ActivityError("Informe o título da tarefa.")
        if responsavel is None:
            raise ActivityError("Informe o responsável pela tarefa.")
        if getattr(getattr(responsavel, "profile", None), "organization_id", None) != activity.organization_id:
            raise ActivityError("O responsável informado pertence a outra organização.")

        task = Task.objects.create(
            activity=activity,
            sector=sector,
            order=order,
            title=title,
            description=description,
            depends_on=depends_on,
            process_step=process_step,
            requested_deadline=requested_deadline,
            status=Task.Status.DISPONIVEL,
            created_by=created_by,
            responsavel=responsavel,
        )
        if tags:
            task.tags.set(tags)
        for participante in participantes or []:
            if participante.id == responsavel.id:
                continue
            TaskService.add_executor(task, participante, added_by=created_by)
        AuditService.log(user=created_by, action=AuditLog.Action.TASK_CREATED, activity=activity, task=task, new_value=title)

        if enqueue:
            QueueService.enqueue(task, sector, user=created_by)

        if notify:
            TaskService._notify_task_available(task, created_by)
        notify_mentions(description, created_by, task, activity=activity, task=task)
        return task

    @staticmethod
    def _notify_task_available(
        task, actor, title="Nova tarefa disponível", message=None, include_responsavel=False, extra_recipients=()
    ):
        """Avisa o setor (membros e gestores) de que a tarefa está na fila.

        `include_responsavel` acrescenta o responsável mesmo que ele não
        participe do setor (a busca de responsável não se restringe ao
        setor). A criação manual mantém só o setor, como sempre foi; o fluxo
        de processo liga a opção porque o responsável vem de um padrão que
        ele não escolheu. `extra_recipients` acrescenta outras pessoas (ex.:
        o dono da atividade, ao reabrir uma tarefa).
        """
        recipients = resolve_sector_and_admins(task.sector)
        if include_responsavel:
            recipients = recipients | {task.responsavel}
        recipients = recipients | {person for person in extra_recipients if person is not None}
        NotificationService.notify(
            users=recipients,
            event_type=Notification.EventType.TASK_ASSIGNED,
            title=title,
            message=(message or f"A tarefa '{task.title}' está disponível no setor {task.sector.name}.")[:255],
            activity=task.activity,
            task=task,
            actor=actor,
        )

    # ------------------------------------------------------------------
    # Dependência entre tarefas (Regras 02 §29)
    # ------------------------------------------------------------------

    @staticmethod
    def pending_dependency(task):
        """A predecessora que ainda impede a tarefa de andar, ou `None`.

        Só `CONCLUIDA` satisfaz a dependência: predecessora cancelada,
        bloqueada ou devolvida continua segurando a sucessora.
        """
        return policies.pending_dependency(task)

    @staticmethod
    def _assert_dependency_satisfied(task):
        message = policies.dependency_message(task)
        if message:
            raise ActivityError(message)

    @staticmethod
    def _assert_process_inputs_ready(task):
        """Tarefa gerada por processo só anda com os inputs obrigatórios recebidos.

        Regras 12 §10 / 08:1284: input obrigatório faltante não impede criar a
        atividade nem aplicar o processo, mas impede o início do fluxo — a
        primeira tarefa não deve começar como se a informação existisse.
        Tarefa manual (sem `process_step`) não é afetada.
        """
        message = policies.process_inputs_message(task)
        if message:
            raise ActivityError(message)

    @staticmethod
    def _has_active_queue_entry(task):
        return policies.has_active_queue_entry(task)

    @staticmethod
    def _release_task(task, user, reason):
        """Coloca na fila uma tarefa que estava fora dela só esperando a
        dependência, auditando e avisando o setor e o responsável.

        Idempotente: só age se a tarefa ainda está `DISPONIVEL` e fora da
        fila, e nunca em atividade já encerrada. Retorna `True` se liberou.
        """
        if task.status != Task.Status.DISPONIVEL or TaskService._has_active_queue_entry(task):
            return False
        if task.activity.status in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA):
            return False

        QueueService.enqueue(task, task.sector, user=user)
        AuditService.log(
            user=user,
            action=AuditLog.Action.TASK_RELEASED,
            activity=task.activity,
            task=task,
            old_value=Task.Status.DISPONIVEL,
            new_value=task.sector.name,
            reason=reason,
        )
        TaskService._notify_task_available(
            task,
            user,
            title="Tarefa liberada para a fila",
            message=f"A tarefa '{task.title}' entrou na fila de {task.sector.name}. {reason}",
            include_responsavel=True,
        )
        return True

    @staticmethod
    def _release_dependents(task, user):
        """Ao concluir `task`, libera as tarefas que só esperavam por ela."""
        dependents = (
            Task.objects.select_for_update(of=("self",))
            .select_related("sector", "activity", "responsavel")
            .filter(depends_on=task, status=Task.Status.DISPONIVEL)
            .order_by("order", "pk")
        )
        for dependent in dependents:
            TaskService._release_task(dependent, user, reason=f"A etapa anterior «{task.title}» foi concluída.")

    @staticmethod
    @transaction.atomic
    def update_task(task, user, **fields):
        """Edita campos não sensíveis da tarefa, auditando cada alteração.

        Setor, prazo comprometido, executores e transições de estado possuem
        serviços próprios e não passam por aqui.
        """
        require_action(user, catalog.TAREFA_EDITAR, task)
        TaskTransitionPolicy.assert_allowed(task, "edit", user)

        editable = {"title", "description", "requested_deadline", "order"}
        changed = []
        for field, value in fields.items():
            if field not in editable:
                continue
            old_value = getattr(task, field)
            if old_value == value:
                continue
            if field == "title" and not value:
                raise ActivityError("Informe o título da tarefa.")
            setattr(task, field, value)
            changed.append(field)
            AuditService.log(
                user=user,
                action=AuditLog.Action.UPDATE,
                activity=task.activity,
                task=task,
                field_name=field,
                old_value=old_value,
                new_value=value,
            )

        if changed:
            task.save(update_fields=changed)

        if "depends_on" in fields:
            TaskService._apply_dependency(task, user, fields["depends_on"])

        if "tags" in fields:
            TaskService._set_tags(task, user, fields["tags"])

        if "description" in changed:
            notify_mentions(task.description, user, task, activity=task.activity, task=task)

        return task

    @staticmethod
    def _set_tags(task, user, tags):
        """Troca os marcadores da tarefa e audita o que mudou (antes e depois)."""
        old = set(task.tags.values_list("pk", flat=True))
        new_tags = list(tags or [])
        if old == {tag.pk for tag in new_tags}:
            return False
        old_names = ", ".join(task.tags.order_by("name").values_list("name", flat=True))
        task.tags.set(new_tags)
        AuditService.log(
            user=user,
            action=AuditLog.Action.UPDATE,
            activity=task.activity,
            task=task,
            field_name="tags",
            old_value=old_names or "Nenhum",
            new_value=", ".join(sorted(tag.name for tag in new_tags)) or "Nenhum",
        )
        return True

    # ------------------------------------------------------------------
    # Dependência: troca, ciclo e candidatas (Regras 02 §29)
    # ------------------------------------------------------------------

    @staticmethod
    def _descendant_ids(task):
        """Tarefas da atividade que dependem de `task`, direta ou indiretamente."""
        children = {}
        rows = Task.objects.filter(activity_id=task.activity_id, depends_on__isnull=False).values_list(
            "pk", "depends_on_id"
        )
        for pk, parent_id in rows:
            children.setdefault(parent_id, []).append(pk)
        found, pending = set(), [task.pk]
        while pending:
            for child in children.get(pending.pop(), ()):
                if child not in found:
                    found.add(child)
                    pending.append(child)
        return found

    @staticmethod
    def dependency_candidates(task):
        """Tarefas que `task` pode ter como predecessora: da mesma atividade,
        não canceladas e que não dependam (nem indiretamente) dela — senão as
        duas ficariam esperando uma pela outra para sempre."""
        blocked = TaskService._descendant_ids(task) | {task.pk}
        return (
            Task.objects.filter(activity_id=task.activity_id)
            .exclude(status=Task.Status.CANCELADA)
            .exclude(pk__in=blocked)
            .order_by("order", "pk")
        )

    @staticmethod
    def _apply_dependency(task, user, depends_on):
        """Troca a predecessora de `task` — **sem autorizar**: quem chama já
        exigiu `tarefa.editar`. Devolve `True` se algo mudou.

        Recusa ciclo, predecessora de outra atividade ou cancelada e uma nova
        espera numa tarefa que já começou. Uma tarefa que estava na fila e passa
        a esperar sai da fila (como na reabertura); a que deixa de esperar
        entra na fila, para não ficar esquecida fora dela.
        """
        if task.depends_on_id == (depends_on.pk if depends_on is not None else None):
            return False
        if depends_on is not None:
            if depends_on.pk == task.pk:
                raise ActivityError("Uma tarefa não pode depender dela mesma.")
            if depends_on.activity_id != task.activity_id:
                raise ActivityError("A tarefa anterior precisa ser da mesma atividade.")
            if depends_on.status == Task.Status.CANCELADA:
                raise ActivityError("Não dá para depender de uma tarefa cancelada.")
            if depends_on.pk in TaskService._descendant_ids(task):
                raise ActivityError(
                    f"«{depends_on.title}» já depende desta tarefa: a dependência formaria um ciclo "
                    "e nenhuma das duas poderia começar."
                )
        will_wait = depends_on is not None and depends_on.status != Task.Status.CONCLUIDA
        if will_wait and (
            task.status not in (Task.Status.DISPONIVEL, Task.Status.EM_FILA)
            or (task.status == Task.Status.EM_FILA and task.work_sessions.exists())
        ):
            raise ActivityError(
                "Esta tarefa já começou; não dá para fazê-la esperar por outra tarefa que ainda não terminou."
            )

        old = task.depends_on
        task.depends_on = depends_on
        task.save(update_fields=["depends_on"])
        AuditService.log(
            user=user,
            action=AuditLog.Action.UPDATE,
            activity=task.activity,
            task=task,
            field_name="depends_on",
            old_value=old.title if old is not None else "Nenhuma",
            new_value=depends_on.title if depends_on is not None else "Nenhuma",
        )

        if will_wait and task.status == Task.Status.EM_FILA:
            entry = task.queue_entries.filter(left_at__isnull=True).select_related("sector").first()
            if entry is not None:
                entry.left_at = timezone.now()
                entry.save(update_fields=["left_at"])
                QueueService.renumber(entry.sector)
            task.status = Task.Status.DISPONIVEL
            task.save(update_fields=["status"])
            AuditService.log(
                user=user,
                action=AuditLog.Action.UPDATE,
                activity=task.activity,
                task=task,
                field_name="status",
                old_value=Task.Status.EM_FILA,
                new_value=Task.Status.DISPONIVEL,
                reason=f"A tarefa passou a depender de «{depends_on.title}».",
            )
        elif not will_wait:
            # Tarefa que só esperava a antiga predecessora e agora não espera
            # mais ninguém não pode ficar esquecida fora da fila.
            TaskService._release_task(
                task, user, reason="A dependência da tarefa foi removida ou já está concluída."
            )
        return True

    @staticmethod
    @transaction.atomic
    def change_dependency(task, user, depends_on):
        """“Gerenciar dependência”: define (ou retira, com `None`) a tarefa que
        precisa terminar antes desta. Muda o fluxo operacional — por isso tem
        janela própria e não faz parte do editor comum. Exige `tarefa.editar`."""
        task = Task.objects.select_for_update(of=("self",)).select_related("activity", "sector", "depends_on").get(pk=task.pk)
        require_action(user, catalog.TAREFA_EDITAR, task)
        if task.status in (Task.Status.CONCLUIDA, Task.Status.CANCELADA):
            raise ActivityError("Não é possível mudar a dependência de uma tarefa concluída ou cancelada.")
        TaskService._apply_dependency(task, user, depends_on)
        return task

    # ------------------------------------------------------------------
    # Editor da tarefa: tudo numa transação só
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def edit_task(
        task, user, *, title, description, requested_deadline, tags, responsavel=None, participants=None
    ):
        """Salva o editor da tarefa de uma vez: dados, marcadores, responsável
        e participantes. Se qualquer parte for recusada, **nada** é gravado.

        Cada parte continua exigindo a sua própria ação: dados e marcadores,
        `tarefa.editar`; responsável, `tarefa.alterar_responsavel`; participantes,
        `tarefa.atribuir` (ou `tarefa.assumir`, para a própria pessoa).
        `responsavel=None` e `participants=None` deixam essas partes como estão
        (é o que a tela envia para quem não pode mexer nelas).

        Adicionar *outra* pessoa como participante não a inclui já: cria um
        convite que ela precisa aceitar (`TaskAssignment` pendente). Por isso o
        retorno diz quem foi convidado.
        """
        task = Task.objects.select_for_update(of=("self",)).select_related("activity", "sector", "responsavel").get(pk=task.pk)
        TaskService.update_task(
            task, user, title=title, description=description, requested_deadline=requested_deadline, tags=tags
        )
        if responsavel is not None and responsavel.pk != task.responsavel_id:
            TaskService.change_responsavel(task, responsavel, user)

        invited, added, removed = [], [], []
        if participants is not None:
            wanted = {person.pk: person for person in participants if person.pk != task.responsavel_id}
            current = {
                link.user_id: link.user
                for link in task.executors.filter(removed_at__isnull=True).select_related("user")
            }
            pending = set(
                task.assignments.filter(status=TaskAssignment.Status.PENDENTE).values_list("user_id", flat=True)
            )
            for pk, person in current.items():
                if pk not in wanted:
                    TaskService.remove_executor(task, person, removed_by=user)
                    removed.append(person)
            for pk, person in wanted.items():
                if pk in current or pk in pending:
                    continue
                result = TaskService.add_executor(task, person, added_by=user)
                (invited if isinstance(result, TaskAssignment) else added).append(person)
        return {"task": task, "invited": invited, "added": added, "removed": removed}

    @staticmethod
    def _clean_informed_reason(reason, note, started_at, now):
        """Motivo e comentário de um período informado pela pessoa — a mesma
        regra para “Já realizei este trabalho” e “Adicionar tempo trabalhado”:
        motivo válido, comentário para *Outro* e para trabalho de mais de
        `RETROACTIVE_JUSTIFICATION_DAYS` dias atrás, até 255 caracteres."""
        if reason not in WorkSession.ManualReason.values:
            raise ActivityError("Escolha o motivo.")
        note = (note or "").strip()
        if reason == WorkSession.ManualReason.OUTRO and not note:
            raise ActivityError("Explique o motivo no comentário.")
        days_ago = (timezone.localdate(now) - timezone.localdate(started_at)).days
        if days_ago > RETROACTIVE_JUSTIFICATION_DAYS and not note:
            raise ActivityError(
                f"O trabalho foi há mais de {RETROACTIVE_JUSTIFICATION_DAYS} dias: escreva uma justificativa no comentário."
            )
        max_note = WorkSession._meta.get_field("note").max_length
        if len(note) > max_note:
            raise ActivityError(f"O comentário deve ter no máximo {max_note} caracteres.")
        return note

    @staticmethod
    @transaction.atomic
    def log_manual_time(task, user, started_at, ended_at, logged_by, reason="", note=""):
        """Apropriação posterior de tempo trabalhado (Regras 04 §110-113, §214).

        Fica marcada como lançamento manual para diferenciar do tempo capturado
        pelo timer, preservando a confiabilidade das métricas. Só acrescenta
        tempo: não conclui a tarefa (para isso, `register_completed_work`).

        O motivo (`WorkSession.ManualReason`) e o comentário seguem as mesmas
        regras de “Já realizei este trabalho”. A tela sempre pede o motivo; em
        código ele continua opcional para não invalidar chamadores antigos — sem
        motivo, a sessão fica sem `manual_reason`, como as anteriores a ele.
        """
        require_action(logged_by, catalog.TEMPO_LANCAR_MANUAL, task)
        if started_at is None or ended_at is None:
            raise ActivityError("Informe o início e o fim do período trabalhado.")
        if ended_at <= started_at:
            raise ActivityError("O fim do período precisa ser posterior ao início.")
        now = timezone.now()
        if started_at > now:
            raise ActivityError("Não é possível lançar tempo no futuro.")
        # Tempo só pode ser apropriado a quem de fato executa a tarefa — do
        # contrário as horas-homem deixam de refletir o trabalho real.
        if not TaskService._is_responsavel_or_participant(task, user):
            raise ActivityError("Só é possível lançar tempo para o responsável ou um participante da tarefa.")
        if reason:
            note = TaskService._clean_informed_reason(reason, note, started_at, now)
        else:
            reason, note = "", ""

        session = WorkSession.objects.create(
            task=task, user=user, started_at=started_at, ended_at=ended_at, is_manual=True,
            logged_at=now, manual_reason=reason, note=note,
        )
        ActivityService._register_first_action(task)
        ActivityService._register_first_action(task.activity)
        ActivityService._mark_in_progress(task.activity, user)

        audit_reason = "Lançamento manual de tempo"
        if reason:
            audit_reason += f" · {WorkSession.ManualReason(reason).label}"
            if note:
                audit_reason += f" · {note}"
        AuditService.log(
            user=logged_by,
            action=AuditLog.Action.SESSION_STARTED,
            activity=task.activity,
            task=task,
            new_value=f"{started_at:%d/%m/%Y %H:%M} - {ended_at:%d/%m/%Y %H:%M}",
            reason=audit_reason,
        )
        return session

    @staticmethod
    @transaction.atomic
    def register_completed_work(task, user, started_at, ended_at, reason, note=""):
        """"Já realizei este trabalho": a pessoa esqueceu de iniciar, já fez, e
        informa quando fez. Registra o período trabalhado **e conclui a tarefa
        agora**.

        Duas verdades separadas (Regras 04 §214):

        - *quando o trabalho aconteceu* fica na `WorkSession` (início/fim
          informados);
        - *quando o sistema soube* — conclusão, saída da fila, liberação da
          sucessora, primeira ação, `logged_at` — é sempre **agora**. Nunca se
          reescreve o passado operacional da fila: uma tarefa não aparece
          "concluída às 10h" se ficou na fila até as 14h.

        Quem pode: quem executa a tarefa (responsável ou participante) com
        `tarefa.concluir` — não exige `tempo.lancar_manual`, que continua
        valendo para "Adicionar tempo trabalhado". A governança é leve e sem
        aprovação: o tempo fica marcado como informado (não cronometrado), com
        motivo; dia anterior é permitido (e destacado nas telas); início há mais
        de `RETROACTIVE_JUSTIFICATION_DAYS` dias exige justificativa.
        """
        task = Task.objects.select_for_update(of=("self",)).select_related("activity", "sector").get(pk=task.pk)
        require_action(user, catalog.TAREFA_CONCLUIR, task)
        TaskTransitionPolicy.assert_allowed(task, "retroactive", user)

        now = timezone.now()
        if started_at is None or ended_at is None:
            raise ActivityError("Informe a hora em que você começou e a hora em que terminou.")
        if ended_at <= started_at:
            raise ActivityError("A hora em que você terminou precisa ser depois da hora em que começou.")
        if ended_at > now:
            raise ActivityError("O trabalho não pode terminar no futuro.")
        if ended_at < task.created_at:
            created = timezone.localtime(task.created_at)
            raise ActivityError(
                f"Esta tarefa só foi criada em {created:%d/%m/%Y às %H:%M}; o trabalho não pode ter terminado antes disso."
            )
        note = TaskService._clean_informed_reason(reason, note, started_at, now)

        WorkSession.objects.create(
            task=task, user=user, started_at=started_at, ended_at=ended_at, is_manual=True,
            logged_at=now, manual_reason=reason, note=note,
        )
        ActivityService._register_first_action(task)
        ActivityService._register_first_action(task.activity)
        ActivityService._mark_in_progress(task.activity, user)

        local_start, local_end = timezone.localtime(started_at), timezone.localtime(ended_at)
        period = (
            f"{local_start:%d/%m/%Y %H:%M}–{local_end:%H:%M}"
            if local_start.date() == local_end.date()
            else f"{local_start:%d/%m/%Y %H:%M} – {local_end:%d/%m/%Y %H:%M}"
        )
        audit_reason = f"Informado em {timezone.localtime(now):%d/%m/%Y %H:%M} · {WorkSession.ManualReason(reason).label}"
        if note:
            audit_reason += f" · {note}"
        AuditService.log(
            user=user,
            action=AuditLog.Action.RETROACTIVE_LOGGED,
            activity=task.activity,
            task=task,
            new_value=period,
            reason=audit_reason,
        )
        return TaskService.complete(task, user)

    @staticmethod
    @transaction.atomic
    def add_executor(task, user, added_by):
        if task.responsavel_id == user.id:
            raise ActivityError("Esta pessoa já é responsável pela tarefa — não pode também ser participante.")
        # Assumir a si mesmo é imediato — a própria pessoa decidiu. Atribuir
        # outra pessoa passa por um pedido de aceite: ela pode recusar (ex.:
        # "isso não é comigo"), então ainda não vira executora aqui.
        if user.id == added_by.id:
            require_action(added_by, catalog.TAREFA_ASSUMIR, task)
            if TaskExecutor.objects.filter(task=task, user=user, removed_at__isnull=True).exists():
                raise ActivityError("Este usuário já é executor desta tarefa.")

            TaskExecutor.objects.create(task=task, user=user, added_by=added_by)
            AuditService.log(
                user=added_by, action=AuditLog.Action.EXECUTOR_ADDED, activity=task.activity, task=task, new_value=user.get_username()
            )
            return task

        require_action(added_by, catalog.TAREFA_ATRIBUIR, task)
        if TaskExecutor.objects.filter(task=task, user=user, removed_at__isnull=True).exists():
            raise ActivityError("Este usuário já é executor desta tarefa.")
        if TaskAssignment.objects.filter(task=task, user=user, status=TaskAssignment.Status.PENDENTE).exists():
            raise ActivityError("Este usuário já possui uma atribuição pendente de aceite nesta tarefa.")

        assignment = TaskAssignment.objects.create(task=task, user=user, assigned_by=added_by)
        AuditService.log(
            user=added_by, action=AuditLog.Action.ASSIGNMENT_CREATED, activity=task.activity, task=task, new_value=user.get_username()
        )
        NotificationService.notify(
            users={user},
            event_type=Notification.EventType.TASK_ASSIGNMENT_PENDING,
            title="Uma tarefa foi atribuída a você",
            message=f"'{task.title}' foi atribuída a você. Aceite ou recuse a atribuição.",
            activity=task.activity,
            task=task,
            actor=added_by,
        )
        return assignment

    @staticmethod
    @transaction.atomic
    def accept_assignment(assignment, user):
        require_action(user, catalog.TAREFA_ACEITAR, assignment.task)
        if assignment.status != TaskAssignment.Status.PENDENTE:
            raise ActivityError("Esta atribuição já foi decidida.")
        if user.id != assignment.user_id:
            raise ActivityError("Somente a pessoa designada pode aceitar esta atribuição.")

        task = assignment.task
        if TaskExecutor.objects.filter(task=task, user=user, removed_at__isnull=True).exists():
            raise ActivityError("Este usuário já é executor desta tarefa.")
        if task.responsavel_id == user.id:
            raise ActivityError("Esta pessoa já é responsável pela tarefa — não pode também ser participante.")

        assignment.status = TaskAssignment.Status.ACEITA
        assignment.decided_at = timezone.now()
        assignment.save(update_fields=["status", "decided_at"])

        TaskExecutor.objects.create(task=task, user=user, added_by=assignment.assigned_by)
        AuditService.log(
            user=user, action=AuditLog.Action.ASSIGNMENT_ACCEPTED, activity=task.activity, task=task, new_value=user.get_username()
        )
        AuditService.log(
            user=user, action=AuditLog.Action.EXECUTOR_ADDED, activity=task.activity, task=task, new_value=user.get_username()
        )
        NotificationService.notify(
            users={user},
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Você foi incluído em uma tarefa",
            message=f"Você foi incluído como executor de '{task.title}'.",
            activity=task.activity,
            task=task,
            actor=user,
        )
        return task

    @staticmethod
    @transaction.atomic
    def reject_assignment(assignment, user, reason, observation=""):
        require_action(user, catalog.TAREFA_RECUSAR, assignment.task)
        if assignment.status != TaskAssignment.Status.PENDENTE:
            raise ActivityError("Esta atribuição já foi decidida.")
        if user.id != assignment.user_id:
            raise ActivityError("Somente a pessoa designada pode recusar esta atribuição.")
        if reason is None:
            raise ActivityError("Informe o motivo da recusa.")

        assignment.status = TaskAssignment.Status.RECUSADA
        assignment.decided_at = timezone.now()
        assignment.reason = reason
        assignment.observation = observation
        assignment.save(update_fields=["status", "decided_at", "reason", "observation"])

        task = assignment.task
        AuditService.log(
            user=user, action=AuditLog.Action.ASSIGNMENT_REJECTED, activity=task.activity, task=task, reason=str(reason)
        )
        NotificationService.notify(
            users={assignment.assigned_by},
            event_type=Notification.EventType.TASK_ASSIGNMENT_REJECTED,
            title="Atribuição recusada",
            message=f"{user.get_username()} recusou a atribuição de '{task.title}'. Motivo: {reason}.",
            activity=task.activity,
            task=task,
            actor=user,
        )
        notify_mentions(observation, user, task, activity=task.activity, task=task)
        return assignment

    @staticmethod
    def _deactivate_executor_link(task, user):
        """Soft-delete da linha de TaskExecutor, sem checagem de autorização —
        uso interno de remove_executor (que autoriza publicamente) e de
        change_responsavel (que já autorizou via TAREFA_ALTERAR_RESPONSAVEL e
        não deveria precisar também de TAREFA_ATRIBUIR/TAREFA_ASSUMIR só para
        tirar o novo responsável de Participantes)."""
        link = TaskExecutor.objects.filter(task=task, user=user, removed_at__isnull=True).first()
        if link is None:
            return None
        link.removed_at = timezone.now()
        link.save(update_fields=["removed_at"])
        return link

    @staticmethod
    @transaction.atomic
    def remove_executor(task, user, removed_by):
        # Sair de uma tarefa que assumi é o oposto de assumir; tirar outra
        # pessoa é atribuição.
        if user.id == removed_by.id:
            require_action(removed_by, catalog.TAREFA_ASSUMIR, task)
        else:
            require_action(removed_by, catalog.TAREFA_ATRIBUIR, task)
        link = TaskService._deactivate_executor_link(task, user)
        if link is None:
            raise ActivityError("Este usuário não é executor ativo desta tarefa.")

        AuditService.log(
            user=removed_by, action=AuditLog.Action.EXECUTOR_REMOVED, activity=task.activity, task=task, new_value=user.get_username()
        )
        return task

    @staticmethod
    @transaction.atomic
    def change_responsavel(task, new_responsavel, changed_by):
        require_action(changed_by, catalog.TAREFA_ALTERAR_RESPONSAVEL, task)
        TaskTransitionPolicy.assert_allowed(task, "change_responsavel", changed_by)
        if new_responsavel.id == task.responsavel_id:
            raise ActivityError("Este usuário já é o responsável desta tarefa.")
        if TaskService._is_active_participant(task, new_responsavel):
            # Novo responsável sai de Participantes automaticamente —
            # conjuntos continuam disjuntos, sem exigir que quem troca
            # remova a pessoa manualmente antes.
            TaskService._deactivate_executor_link(task, new_responsavel)

        previous = task.responsavel
        task.responsavel = new_responsavel
        task.save(update_fields=["responsavel"])

        TaskResponsavelChangeLog.objects.create(
            task=task, previous_responsavel=previous, new_responsavel=new_responsavel, changed_by=changed_by
        )
        AuditService.log(
            user=changed_by,
            action=AuditLog.Action.RESPONSAVEL_CHANGED,
            activity=task.activity,
            task=task,
            old_value=previous.get_username(),
            new_value=new_responsavel.get_username(),
        )
        NotificationService.notify(
            users={previous, new_responsavel},
            event_type=Notification.EventType.TASK_RESPONSAVEL_CHANGED,
            title="Responsável da tarefa alterado",
            message=f"O responsável de '{task.title}' passou de {previous} para {new_responsavel}.",
            activity=task.activity,
            task=task,
            actor=changed_by,
        )
        return task

    @staticmethod
    def _is_active_participant(task, user):
        return policies.is_active_participant(task, user)

    @staticmethod
    def _is_responsavel_or_participant(task, user):
        return policies.is_responsavel_or_participant(task, user)

    @staticmethod
    @transaction.atomic
    def start(task, user):
        require_action(user, catalog.TAREFA_INICIAR, task)
        TaskTransitionPolicy.assert_allowed(task, "start", user)

        # Regra 04 §115 (revista): a pessoa pode ter sessões de trabalho
        # simultâneas em tarefas diferentes — cada uma é independente e
        # gerenciada separadamente, sem pausar as demais automaticamente.
        now = timezone.now()
        if not WorkSession.objects.filter(task=task, user=user, ended_at__isnull=True).exists():
            WorkSession.objects.create(task=task, user=user, started_at=now)

        old_status = task.status
        task.status = Task.Status.EM_EXECUCAO
        task.save(update_fields=["status"])
        ActivityService._register_first_action(task)
        ActivityService._register_first_action(task.activity)
        ActivityService._mark_in_progress(task.activity, user)

        AuditService.log(
            user=user, action=AuditLog.Action.SESSION_STARTED, activity=task.activity, task=task, old_value=old_status, new_value=task.status
        )
        return task

    @staticmethod
    @transaction.atomic
    def pause(task, user):
        require_action(user, catalog.TAREFA_PAUSAR, task)
        TaskTransitionPolicy.assert_allowed(task, "pause", user)
        session = WorkSession.objects.filter(task=task, user=user, ended_at__isnull=True).first()

        session.ended_at = timezone.now()
        session.save(update_fields=["ended_at"])

        if not WorkSession.objects.filter(task=task, ended_at__isnull=True).exists():
            task.status = Task.Status.EM_FILA
            task.save(update_fields=["status"])

        AuditService.log(user=user, action=AuditLog.Action.SESSION_PAUSED, activity=task.activity, task=task)
        return task

    @staticmethod
    @transaction.atomic
    def resume(task, user):
        require_action(user, catalog.TAREFA_RETOMAR, task)
        if not TaskService._is_responsavel_or_participant(task, user):
            raise ActivityError("Somente o responsável ou participantes atribuídos podem retomar a tarefa.")
        return TaskService.start(task, user)

    @staticmethod
    @transaction.atomic
    def complete(task, user):
        require_action(user, catalog.TAREFA_CONCLUIR, task)
        TaskTransitionPolicy.assert_allowed(task, "complete", user)

        now = timezone.now()
        open_sessions = WorkSession.objects.filter(task=task, ended_at__isnull=True)
        for session in open_sessions:
            session.ended_at = now
            session.save(update_fields=["ended_at"])

        old_status = task.status
        task.status = Task.Status.CONCLUIDA
        task.completed_at = now
        task.completed_by = user
        task.save(update_fields=["status", "completed_at", "completed_by"])

        active_entry = task.queue_entries.filter(left_at__isnull=True).first()
        if active_entry:
            active_entry.left_at = now
            active_entry.save(update_fields=["left_at"])
            QueueService.renumber(active_entry.sector)

        AuditService.log(
            user=user, action=AuditLog.Action.COMPLETE, activity=task.activity, task=task, old_value=old_status, new_value=task.status
        )
        recipients = {task.activity.owner}
        if task.responsavel_id:
            recipients.add(task.responsavel)
        NotificationService.notify(
            users=recipients,
            event_type=Notification.EventType.TASK_COMPLETED,
            title="Tarefa concluída",
            message=f"A tarefa '{task.title}' foi concluída.",
            activity=task.activity,
            task=task,
            actor=user,
        )
        # Só a conclusão satisfaz a dependência (cancelar, bloquear ou devolver
        # a predecessora nunca chega aqui e mantém as sucessoras esperando).
        TaskService._release_dependents(task, user)
        return task

    @staticmethod
    @transaction.atomic
    def cancel(task, user, reason):
        require_action(user, catalog.TAREFA_CANCELAR, task)
        TaskTransitionPolicy.assert_allowed(task, "cancel", user)
        if not reason:
            raise ActivityError("Informe o motivo do cancelamento.")

        old_status = task.status
        task.status = Task.Status.CANCELADA
        task.cancelled_at = timezone.now()
        task.save(update_fields=["status", "cancelled_at"])

        active_entry = task.queue_entries.filter(left_at__isnull=True).first()
        if active_entry:
            active_entry.left_at = timezone.now()
            active_entry.save(update_fields=["left_at"])
            QueueService.renumber(active_entry.sector)

        AuditService.log(
            user=user, action=AuditLog.Action.CANCEL, activity=task.activity, task=task, old_value=old_status, new_value=task.status, reason=reason
        )
        return task

    @staticmethod
    @transaction.atomic
    def reopen(task, user, reason):
        """Reabre uma tarefa **concluída**, com motivo obrigatório.

        A tarefa volta ao fim da fila do setor (nova passagem pela fila,
        Regras 04 §37); sessões de trabalho, checklist, participantes e prazos
        ficam como estavam — o histórico é fato. Regras desta operação (as
        Regras 02/05 eram omissas; ver `docs/06` §2.11):

        - se a atividade está `CONCLUIDA`, ela é reaberta junto, na mesma
          transação, e por isso a pessoa também precisa de `atividade.reabrir`;
          atividade `CANCELADA` não permite;
        - tarefas que dependiam desta e **já foram trabalhadas** (em execução,
          concluídas, bloqueadas, devolvidas ou com sessão registrada) impedem
          a reabertura; as que só esperam na fila voltam a "aguardando a etapa
          anterior" (saem da fila, com auditoria) e são liberadas de novo
          quando esta for concluída.
        """
        caller_copy = task
        task = (
            Task.objects.select_for_update(of=("self",))
            .select_related("activity", "sector", "responsavel")
            .get(pk=task.pk)
        )
        require_action(user, catalog.TAREFA_REABRIR, task)
        TaskTransitionPolicy.assert_allowed(task, "reopen", user)
        reason = (reason or "").strip()
        if not reason:
            raise ActivityError("Informe o motivo da reabertura.")

        activity = task.activity
        if activity.status == Activity.Status.CANCELADA:
            raise ActivityError("A atividade desta tarefa foi cancelada; não é possível reabrir a tarefa.")
        reopens_activity = activity.status == Activity.Status.CONCLUIDA
        if reopens_activity and not AuthorizationService.can(user, catalog.ATIVIDADE_REABRIR, activity):
            raise ActivityError(
                "A atividade desta tarefa está concluída e reabrir a tarefa exige reabrir a atividade, "
                "o que você não tem permissão para fazer. Peça a quem pode reabrir a atividade."
            )

        # Tudo o que pode recusar vem antes de qualquer gravação.
        dependents = list(
            Task.objects.select_for_update(of=("self",))
            .filter(depends_on=task)
            .exclude(status=Task.Status.CANCELADA)
            .order_by("order", "pk")
        )
        worked = [
            dependent
            for dependent in dependents
            if dependent.status not in (Task.Status.DISPONIVEL, Task.Status.EM_FILA)
            or (dependent.status == Task.Status.EM_FILA and dependent.work_sessions.exists())
        ]
        if worked:
            names = "; ".join(f"«{dependent.title}» ({dependent.get_status_display()})" for dependent in worked)
            raise ActivityError(
                f"Não é possível reabrir «{task.title}»: a(s) tarefa(s) seguinte(s) já foi(ram) trabalhada(s) — "
                f"{names}. Resolva-a(s) antes (cancelando ou devolvendo) ou reabra a mais recente."
            )

        if reopens_activity:
            ActivityService.reopen_activity(activity, user, f"Tarefa «{task.title}» reaberta: {reason}")

        now = timezone.now()
        for dependent in dependents:
            if dependent.status != Task.Status.EM_FILA:
                continue
            entry = dependent.queue_entries.filter(left_at__isnull=True).select_related("sector").first()
            if entry is not None:
                entry.left_at = now
                entry.save(update_fields=["left_at"])
                QueueService.renumber(entry.sector)
            dependent.status = Task.Status.DISPONIVEL
            dependent.save(update_fields=["status"])
            AuditService.log(
                user=user,
                action=AuditLog.Action.UPDATE,
                activity=activity,
                task=dependent,
                field_name="status",
                old_value=Task.Status.EM_FILA,
                new_value=Task.Status.DISPONIVEL,
                reason=f"A etapa anterior «{task.title}» foi reaberta.",
            )

        task.status = Task.Status.DISPONIVEL
        task.completed_at = None
        task.completed_by = None
        task.save(update_fields=["status", "completed_at", "completed_by"])
        waiting_for = TaskService.pending_dependency(task)
        if waiting_for is None:
            QueueService.enqueue(task, task.sector, user=user)

        AuditService.log(
            user=user,
            action=AuditLog.Action.REOPEN,
            activity=activity,
            task=task,
            old_value=Task.Status.CONCLUIDA,
            new_value=task.status,
            reason=reason,
        )
        where = (
            f"voltou para a fila de {task.sector.name}"
            if waiting_for is None
            else f"aguarda a conclusão de «{waiting_for.title}»"
        )
        TaskService._notify_task_available(
            task,
            user,
            title="Tarefa reaberta",
            message=f"A tarefa '{task.title}' foi reaberta e {where}. Motivo: {reason}",
            include_responsavel=True,
            extra_recipients={activity.owner},
        )
        notify_mentions(reason, user, task, activity=activity, task=task)

        caller_copy.status = task.status
        caller_copy.completed_at = None
        caller_copy.completed_by = None
        return task

    @staticmethod
    @transaction.atomic
    def block(task, user, reason, observation=""):
        require_action(user, catalog.TAREFA_BLOQUEAR, task)
        if not reason:
            raise ActivityError("Informe o motivo do bloqueio.")
        TaskTransitionPolicy.assert_allowed(task, "block", user)

        old_status = task.status
        TaskBlock.objects.create(task=task, reason=reason, observation=observation, started_by=user)
        task.status = Task.Status.BLOQUEADA
        task.save(update_fields=["status"])

        AuditService.log(
            user=user, action=AuditLog.Action.BLOCK, activity=task.activity, task=task, old_value=old_status, new_value=task.status, reason=reason
        )
        NotificationService.notify(
            users={task.activity.owner},
            event_type=Notification.EventType.TASK_BLOCKED,
            title="Tarefa bloqueada",
            message=f"A tarefa '{task.title}' foi bloqueada: {reason}",
            activity=task.activity,
            task=task,
            actor=user,
        )
        notify_mentions(observation, user, task, activity=task.activity, task=task)
        return task

    @staticmethod
    @transaction.atomic
    def unblock(task, user, resume_status=None):
        require_action(user, catalog.TAREFA_BLOQUEAR, task)
        TaskTransitionPolicy.assert_allowed(task, "unblock", user)

        open_block = task.blocks.filter(ended_at__isnull=True).order_by("-started_at").first()
        if open_block:
            open_block.ended_at = timezone.now()
            open_block.ended_by = user
            open_block.save(update_fields=["ended_at", "ended_by"])

        if resume_status is None:
            # Etapa que ainda espera a anterior e nunca entrou na fila volta a
            # esperar; do contrário o desbloqueio a colocaria na fila cedo demais.
            still_waiting = (
                TaskService.pending_dependency(task) is not None and not TaskService._has_active_queue_entry(task)
            )
            resume_status = Task.Status.DISPONIVEL if still_waiting else Task.Status.EM_FILA
        task.status = resume_status
        task.save(update_fields=["status"])

        AuditService.log(user=user, action=AuditLog.Action.UNBLOCK, activity=task.activity, task=task, new_value=task.status)
        NotificationService.notify(
            users={task.activity.owner},
            event_type=Notification.EventType.TASK_UNBLOCKED,
            title="Tarefa desbloqueada",
            message=f"A tarefa '{task.title}' foi desbloqueada.",
            activity=task.activity,
            task=task,
            actor=user,
        )
        return task

    # ------------------------------------------------------------------
    # Fluxo entre setores / devolução
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def move_to_sector(task, new_sector, user, note="", keep_status=False):
        """Envia a tarefa para a fila de outro setor.

        `keep_status=True` (devolução) mantém `DEVOLVIDA` na fila do setor que
        recebeu em vez de `EM_FILA`: o status diz a verdade até alguém agir e a
        notificação de "ação necessária" continua valendo.
        """
        require_action(user, catalog.TAREFA_MOVER_SETOR, task)
        TaskTransitionPolicy.assert_allowed(task, "move_sector", user)
        if not _same_organization(task.activity, new_sector):
            raise ActivityError("O setor informado pertence a outra organização.")

        old_sector = task.sector
        now = timezone.now()

        # Quem estava trabalhando deixa de estar: o cronômetro não segue
        # rodando numa tarefa que agora pertence a outro setor.
        for session in WorkSession.objects.filter(task=task, ended_at__isnull=True):
            session.ended_at = now
            session.save(update_fields=["ended_at"])

        active_entry = task.queue_entries.filter(left_at__isnull=True).first()
        if active_entry:
            active_entry.left_at = now
            active_entry.save(update_fields=["left_at"])
            QueueService.renumber(old_sector)

        task.sector = new_sector
        # Etapa que ainda espera a anterior muda de setor sem entrar na fila do
        # novo setor: ela só entra quando a predecessora for concluída.
        waiting = TaskService.pending_dependency(task) is not None and active_entry is None
        queued_status = Task.Status.DEVOLVIDA if keep_status else Task.Status.EM_FILA
        task.status = Task.Status.DISPONIVEL if waiting else queued_status
        task.save(update_fields=["sector", "status"])

        SectorTransfer.objects.create(task=task, from_sector=old_sector, to_sector=new_sector, moved_by=user, note=note)
        if not waiting:
            QueueService.enqueue(task, new_sector, user=user, status=queued_status)

        AuditService.log(
            user=user,
            action=AuditLog.Action.SECTOR_MOVED,
            activity=task.activity,
            task=task,
            old_value=old_sector.name if old_sector else "",
            new_value=new_sector.name,
        )
        recipients = resolve_sector_and_admins(new_sector)
        NotificationService.notify(
            users=recipients,
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Tarefa recebida",
            message=f"A tarefa '{task.title}' foi movida para o setor {new_sector.name}.",
            activity=task.activity,
            task=task,
            actor=user,
        )
        return task

    @staticmethod
    @transaction.atomic
    def return_task(task, to_sector, reason, user, observation=""):
        """Devolve a tarefa para um setor anterior. Motivo sempre obrigatório (Regras 02 §36-39)."""
        require_action(user, catalog.TAREFA_DEVOLVER, task)
        if reason is None:
            raise ActivityError("Toda devolução precisa de um motivo.")
        if not _same_organization(task.activity, to_sector, reason):
            raise ActivityError("Dados informados pertencem a outra organização.")
        TaskTransitionPolicy.assert_allowed(task, "return", user)

        old_sector = task.sector
        TaskReturn.objects.create(
            task=task, from_sector=old_sector, to_sector=to_sector, reason=reason, observation=observation, returned_by=user
        )

        old_status = task.status
        task.status = Task.Status.DEVOLVIDA
        task.save(update_fields=["status"])

        AuditService.log(
            user=user,
            action=AuditLog.Action.RETURNED,
            activity=task.activity,
            task=task,
            old_value=old_status,
            new_value=task.status,
            reason=reason.name,
        )

        TaskService.move_to_sector(task, to_sector, user, note=f"Devolução: {reason.name}", keep_status=True)

        recipients = resolve_sector_and_admins(to_sector) | resolve_sector_and_admins(old_sector)
        NotificationService.notify(
            users=recipients | {task.activity.owner},
            event_type=Notification.EventType.TASK_RETURNED,
            title="Tarefa devolvida",
            message=f"A tarefa '{task.title}' foi devolvida de {old_sector.name} para {to_sector.name}. Motivo: {reason.name}",
            activity=task.activity,
            task=task,
            actor=user,
        )
        notify_mentions(observation, user, task, activity=task.activity, task=task)
        return task


    # ------------------------------------------------------------------
    # Checklist / subtarefas
    # ------------------------------------------------------------------

    @staticmethod
    def can_toggle_checklist(task, user):
        if AuthorizationService.can(user, catalog.TAREFA_EDITAR, task):
            return True
        return (
            user.is_active
            and getattr(getattr(user, "profile", None), "organization_id", None) == task.activity.organization_id
            and TaskService._is_responsavel_or_participant(task, user)
        )

    @staticmethod
    @transaction.atomic
    def add_checklist_item(task, user, text):
        require_action(user, catalog.TAREFA_EDITAR, task)
        text = (text or "").strip()
        if not text:
            raise ActivityError("Escreva o texto do item.")
        if len(text) > TaskChecklistItem._meta.get_field("text").max_length:
            raise ActivityError("O item deve ter no máximo 255 caracteres.")
        Task.objects.select_for_update().get(pk=task.pk)
        next_order = (task.checklist_items.aggregate(last=Max("order"))["last"] or 0) + 1
        return TaskChecklistItem.objects.create(task=task, text=text, order=next_order, created_by=user)

    @staticmethod
    @transaction.atomic
    def toggle_checklist_item(item, user, is_done):
        if not TaskService.can_toggle_checklist(item.task, user):
            raise ActivityError("Somente executores ativos ou quem pode editar a tarefa podem marcar os itens.")
        if not isinstance(is_done, bool):
            raise ActivityError("Informe se o item está concluído.")
        if item.is_done == is_done:
            return item
        item.is_done = is_done
        item.done_by = user if is_done else None
        item.done_at = timezone.now() if is_done else None
        item.save(update_fields=["is_done", "done_by", "done_at"])
        return item

    @staticmethod
    @transaction.atomic
    def remove_checklist_item(item, user):
        require_action(user, catalog.TAREFA_EDITAR, item.task)
        item.delete()

    @staticmethod
    def mark_overdue_tasks():
        """Verifica tarefas com prazo comprometido vencido e ainda não notificadas
        (Regras 03 §140-142, 04). Deve ser agendada periodicamente."""
        now = timezone.now()
        overdue_tasks = Task.objects.filter(
            committed_deadline__lt=now,
            overdue_notified_at__isnull=True,
            status__in=[
                Task.Status.DISPONIVEL, Task.Status.EM_FILA, Task.Status.DEVOLVIDA,
                Task.Status.EM_EXECUCAO, Task.Status.BLOQUEADA,
            ],
        )

        count = 0
        for task in overdue_tasks:
            recipients = resolve_sector_and_admins(task.sector) | {task.activity.owner}
            if task.responsavel_id:
                recipients.add(task.responsavel)
            NotificationService.notify(
                users=recipients,
                event_type=Notification.EventType.TASK_OVERDUE,
                title="Tarefa atrasada",
                message=f"A tarefa '{task.title}' da atividade '{task.activity.title}' está atrasada.",
                activity=task.activity,
                task=task,
            )
            from notifications.services import EmailService

            EmailService.send_task_overdue(task, recipients)
            task.overdue_notified_at = now
            task.save(update_fields=["overdue_notified_at"])
            count += 1
        return count


class WorkTimeService:
    """Origem do tempo registrado (Regras 04 §113 e §119): quanto foi
    cronometrado, quanto foi informado pela pessoa e por que motivo. Não muda
    nenhum dado — só responde “de onde vêm as horas” para a gestão."""

    @staticmethod
    def origin_breakdown(activities):
        """`activities`: queryset de `Activity` já recortado pelos filtros da
        tela. Só conta sessões encerradas. `informed_pct` é `None` sem tempo."""
        duration = ExpressionWrapper(F("ended_at") - F("started_at"), output_field=DurationField())
        rows = (
            WorkSession.objects.filter(task__activity__in=activities, ended_at__isnull=False)
            .values("is_manual", "manual_reason")
            .annotate(total=Sum(duration), sessions=Count("id"))
        )
        zero = timedelta(0)
        timer, informed, by_reason = zero, zero, {}
        for row in rows:
            total = row["total"] or zero
            if row["is_manual"]:
                informed += total
                bucket = by_reason.setdefault(row["manual_reason"], {"total": zero, "sessions": 0})
                bucket["total"] += total
                bucket["sessions"] += row["sessions"]
            else:
                timer += total
        everything = timer + informed
        labels = dict(WorkSession.ManualReason.choices)
        reasons = [
            {
                "reason": reason,
                "label": labels.get(reason) or "Sem motivo (registrado antes de o motivo existir)",
                "total": bucket["total"],
                "sessions": bucket["sessions"],
                "pct_of_informed": round(bucket["total"] / informed * 100, 1) if informed else None,
                "pct_of_all": round(bucket["total"] / everything * 100, 1) if everything else None,
            }
            for reason, bucket in by_reason.items()
        ]
        reasons.sort(key=lambda item: item["total"], reverse=True)
        return {
            "timer": timer,
            "informed": informed,
            "total": everything,
            "timer_pct": round(timer / everything * 100, 1) if everything else None,
            "informed_pct": round(informed / everything * 100, 1) if everything else None,
            "reasons": reasons,
        }


class QueueService:
    @staticmethod
    @transaction.atomic
    def enqueue(task, sector, user=None, status=Task.Status.EM_FILA):
        """Insere a tarefa no final da fila ativa do setor (Regras 03 §6-8).

        `status` é o que a tarefa passa a ter na fila: `EM_FILA`, ou `DEVOLVIDA`
        quando chega por devolução."""
        active_entries = QueueEntry.objects.filter(sector=sector, left_at__isnull=True).order_by("position")
        new_total = active_entries.count() + 1
        position = new_total

        entry = QueueEntry.objects.create(
            task=task, sector=sector, position=position, queue_size_at_entry=new_total
        )
        task.status = status
        task.save(update_fields=["status"])
        return entry

    @staticmethod
    @transaction.atomic
    def renumber(sector, previous_total=None):
        """Fecha buracos de posição depois que uma tarefa deixa a fila (Regras 03 §83, §118).

        A posição precisa ser confiável porque é o que o solicitante enxerga
        ("4 de 17"); registra a mudança como automática, sem usuário.

        `previous_total` é o tamanho da fila antes da saída — quando omitido,
        assume-se que uma única entrada saiu.
        """
        active_entries = list(
            QueueEntry.objects.filter(sector=sector, left_at__isnull=True).order_by("position")
        )
        new_total = len(active_entries)
        old_total = previous_total if previous_total is not None else new_total + 1

        for index, entry in enumerate(active_entries, start=1):
            if entry.position == index:
                continue
            old_position = entry.position
            entry.position = index
            entry.save(update_fields=["position"])
            QueuePositionChange.objects.create(
                queue_entry=entry,
                old_position=old_position,
                new_position=index,
                old_total=old_total,
                new_total=new_total,
                reason=QueuePositionChange.Reason.AUTOMATICA_CONCLUSAO,
                changed_by=None,
            )

    @staticmethod
    @transaction.atomic
    def reorder(queue_entry, new_position, user, reason=None):
        """Reordena a fila ativa de um setor, preservando histórico de todas as posições afetadas."""
        # O escopo importa: quem reordena o Comercial não reordena Compras.
        require_action(user, catalog.FILA_REORDENAR, queue_entry)
        if not queue_entry.is_active:
            raise ActivityError("Esta entrada não está mais ativa na fila.")

        active_entries = list(
            QueueEntry.objects.filter(sector=queue_entry.sector, left_at__isnull=True).order_by("position")
        )
        total = len(active_entries)
        new_position = max(1, min(new_position, total))

        active_entries.remove(queue_entry)
        active_entries.insert(new_position - 1, queue_entry)

        for index, entry in enumerate(active_entries, start=1):
            if entry.position == index:
                continue
            old_position = entry.position
            entry.position = index
            entry.save(update_fields=["position"])
            QueuePositionChange.objects.create(
                queue_entry=entry,
                old_position=old_position,
                new_position=index,
                old_total=total,
                new_total=total,
                reason=QueuePositionChange.Reason.MANUAL if entry.pk == queue_entry.pk else QueuePositionChange.Reason.AUTOMATICA_ENTRADA,
                note=reason or "",
                changed_by=user if entry.pk == queue_entry.pk else None,
            )
            AuditService.log(
                user=user if entry.pk == queue_entry.pk else None,
                action=AuditLog.Action.QUEUE_POSITION_CHANGED,
                activity=entry.task.activity,
                task=entry.task,
                old_value=old_position,
                new_value=index,
                reason=reason or "",
            )

        NotificationService.notify(
            users={queue_entry.task.activity.owner},
            event_type=Notification.EventType.QUEUE_POSITION_CHANGED,
            title="Posição na fila alterada",
            message=f"A posição de '{queue_entry.task.title}' mudou para {queue_entry.position} de {total}.",
            activity=queue_entry.task.activity,
            task=queue_entry.task,
            actor=user,
        )
        return queue_entry


class DeadlineService:
    @staticmethod
    @transaction.atomic
    def propose(task, deadline, user):
        require_action(user, catalog.PRAZO_PROPOR, task)
        proposal = DeadlineProposal.objects.create(task=task, proposed_deadline=deadline, proposed_by=user)
        AuditService.log(
            user=user, action=AuditLog.Action.DEADLINE_PROPOSED, activity=task.activity, task=task, new_value=deadline
        )
        NotificationService.notify(
            users={task.activity.owner},
            event_type=Notification.EventType.DEADLINE_PROPOSED,
            title="Novo prazo proposto",
            message=f"Foi proposto o prazo {deadline:%d/%m/%Y %H:%M} para '{task.title}'.",
            activity=task.activity,
            task=task,
            actor=user,
        )
        return proposal

    @staticmethod
    @transaction.atomic
    def accept(proposal, user):
        require_action(user, catalog.PRAZO_ACEITAR, proposal.task)
        if proposal.status != DeadlineProposal.Status.PENDENTE:
            raise ActivityError("Esta proposta já foi decidida.")
        if user.id != proposal.task.activity.owner_id:
            raise ActivityError("Somente o dono da atividade pode aceitar o prazo proposto.")

        proposal.status = DeadlineProposal.Status.ACEITO
        proposal.decided_by = user
        proposal.decided_at = timezone.now()
        proposal.save(update_fields=["status", "decided_by", "decided_at"])

        task = proposal.task
        task.committed_deadline = proposal.proposed_deadline
        task.save(update_fields=["committed_deadline"])

        AuditService.log(
            user=user, action=AuditLog.Action.DEADLINE_ACCEPTED, activity=task.activity, task=task, new_value=proposal.proposed_deadline
        )
        NotificationService.notify(
            users={proposal.proposed_by},
            event_type=Notification.EventType.DEADLINE_ACCEPTED,
            title="Prazo aceito",
            message=f"O prazo proposto para '{task.title}' foi aceito.",
            activity=task.activity,
            task=task,
            actor=user,
        )
        return proposal

    @staticmethod
    @transaction.atomic
    def reject(proposal, user, note=""):
        require_action(user, catalog.PRAZO_RECUSAR, proposal.task)
        if proposal.status != DeadlineProposal.Status.PENDENTE:
            raise ActivityError("Esta proposta já foi decidida.")
        if user.id != proposal.task.activity.owner_id:
            raise ActivityError("Somente o dono da atividade pode recusar o prazo proposto.")

        proposal.status = DeadlineProposal.Status.RECUSADO
        proposal.decided_by = user
        proposal.decided_at = timezone.now()
        proposal.decision_note = note
        proposal.save(update_fields=["status", "decided_by", "decided_at", "decision_note"])

        task = proposal.task
        AuditService.log(
            user=user, action=AuditLog.Action.DEADLINE_REJECTED, activity=task.activity, task=task, reason=note
        )

        # Regras 03 §34 / Roadmap §31: recusa gera conflito registrado + notificação.
        # Motor completo de escalonamento por níveis é D1.
        conflict = DeadlineConflict.objects.create(task=task, proposal=proposal)
        AuditService.log(user=user, action=AuditLog.Action.CONFLICT_OPENED, activity=task.activity, task=task, reason=note)

        recipients = resolve_sector_and_admins(task.sector) | {task.activity.owner}
        NotificationService.notify(
            users=recipients,
            event_type=Notification.EventType.DEADLINE_CONFLICT,
            title="Conflito de prazo",
            message=f"O prazo proposto para '{task.title}' foi recusado. Motivo: {note}",
            activity=task.activity,
            task=task,
            actor=user,
        )
        notify_mentions(note, user, task, activity=task.activity, task=task)
        return conflict

    @staticmethod
    @transaction.atomic
    def resolve_conflict(conflict, user, resolution_note):
        require_action(user, catalog.ESCALONAMENTO_RESOLVER, conflict.task)
        if conflict.status == DeadlineConflict.Status.RESOLVIDO:
            raise ActivityError("Este conflito já foi resolvido.")

        conflict.status = DeadlineConflict.Status.RESOLVIDO
        conflict.resolution_note = resolution_note
        conflict.resolved_by = user
        conflict.resolved_at = timezone.now()
        conflict.save(update_fields=["status", "resolution_note", "resolved_by", "resolved_at"])

        AuditService.log(
            user=user, action=AuditLog.Action.CONFLICT_RESOLVED, activity=conflict.task.activity, task=conflict.task, reason=resolution_note
        )
        notify_mentions(resolution_note, user, conflict.task, activity=conflict.task.activity, task=conflict.task)
        return conflict


class MessageService:
    """Comunicação contextual (Regras 06).

    Mensagem nunca altera dado oficial: para mudar prazo, devolver ou concluir
    é preciso a ação estruturada correspondente (Regras 01 §6.14, 06 §137).
    """

    @staticmethod
    def _truncate(text, limit=200):
        return _truncate_mention_text(text, limit)

    @staticmethod
    def _executors_of(task_queryset_filter):
        return User.objects.filter(
            tasks_executed__removed_at__isnull=True, **task_queryset_filter
        ).distinct()

    @staticmethod
    def _mentioned_users(body, author, resource):
        return find_mentioned_users(body, author, resource)

    @staticmethod
    @transaction.atomic
    def post_activity_message(activity, author, body, kind=MessageKind.NORMAL):
        require_action(author, catalog.COMUNICACAO_PARTICIPAR, activity)
        body = (body or "").strip()
        if not body:
            raise ActivityError("Escreva uma mensagem antes de enviar.")

        message = ActivityMessage.objects.create(activity=activity, author=author, body=body, kind=kind)

        mentioned = find_mentioned_users(body, author, activity)

        recipients = {activity.owner, activity.created_by}
        recipients.update(MessageService._executors_of({"tasks_executed__task__activity": activity}))
        recipients.update(User.objects.filter(tasks_responsavel__activity=activity).distinct())
        recipients = {u for u in recipients if u is not None and u.id != author.id} - mentioned

        if recipients:
            NotificationService.notify(
                users=recipients,
                event_type=Notification.EventType.MESSAGE_POSTED,
                title="Nova mensagem na atividade",
                message=MessageService._truncate(f"{author.get_username()}: {body}"),
                activity=activity,
                actor=author,
            )
        notify_mentions(body, author, activity, activity=activity)
        return message

    @staticmethod
    @transaction.atomic
    def post_task_message(task, author, body, kind=MessageKind.NORMAL):
        require_action(author, catalog.COMUNICACAO_PARTICIPAR, task)
        body = (body or "").strip()
        if not body:
            raise ActivityError("Escreva uma mensagem antes de enviar.")

        message = TaskMessage.objects.create(task=task, author=author, body=body, kind=kind)

        mentioned = find_mentioned_users(body, author, task)

        recipients = {task.activity.owner}
        if task.responsavel_id:
            recipients.add(task.responsavel)
        recipients.update(MessageService._executors_of({"tasks_executed__task": task}))
        recipients = {u for u in recipients if u is not None and u.id != author.id} - mentioned

        notify_mentions(body, author, task, activity=task.activity, task=task)
        if recipients:
            NotificationService.notify(
                users=recipients,
                event_type=Notification.EventType.MESSAGE_POSTED,
                title="Nova mensagem na tarefa",
                message=MessageService._truncate(f"{author.get_username()}: {body}"),
                activity=task.activity,
                task=task,
                actor=author,
            )
        return message
