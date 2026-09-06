from datetime import timedelta

from django.contrib.auth.models import Group
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditLog
from audit.services import AuditService
from notifications.models import Notification
from notifications.recipients import resolve_admins, resolve_group_and_admins
from notifications.services import EmailService, NotificationService

from .models import Process, ProcessStep


class WorkflowError(Exception):
    """Levantado para qualquer transição/ação inválida do workflow.
    Views capturam esta exceção e exibem a mensagem via django.contrib.messages."""


class WorkflowService:
    # ------------------------------------------------------------------
    # Criação / liberação
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def instanciar_processo(template, title, criado_por, demand=None):
        template_steps = list(template.steps.order_by("order"))
        if not template_steps:
            raise WorkflowError("O template selecionado não possui etapas configuradas.")

        process = Process.objects.create(
            template=template,
            demand=demand,
            title=title,
            created_by=criado_por,
        )

        steps = []
        for template_step in template_steps:
            steps.append(
                ProcessStep(
                    process=process,
                    template_step=template_step,
                    order=template_step.order,
                    name=template_step.name,
                    description=template_step.description,
                    responsible_group=template_step.responsible_group,
                    priority=template_step.default_priority,
                )
            )
        ProcessStep.objects.bulk_create(steps)

        AuditService.log(
            user=criado_por,
            action=AuditLog.Action.CREATE,
            process=process,
            new_value=template.name,
        )

        admins = resolve_admins()
        NotificationService.notify(
            users={criado_por, *admins},
            event_type=Notification.EventType.PROCESS_CREATED,
            title="Processo criado",
            message=f"O processo '{process.title}' foi criado.",
            process=process,
            url=reverse("process-detail", args=[process.pk]),
        )

        first_step = process.steps.order_by("order").first()
        WorkflowService.liberar_atividade(first_step)

        return process

    @staticmethod
    def liberar_atividade(step):
        """Interno: marca a etapa como liberada (released_at) e calcula o prazo.
        Único ponto (junto de marcar_atividades_atrasadas) que dispara e-mail."""
        now = timezone.now()
        step.released_at = now
        deadline_days = step.template_step.default_deadline_days if step.template_step else 0
        step.deadline_at = now + timedelta(days=deadline_days)
        step.overdue_notified_at = None
        step.save(update_fields=["released_at", "deadline_at", "overdue_notified_at"])

        recipients = resolve_group_and_admins(step.responsible_group)
        NotificationService.notify(
            users=recipients,
            event_type=Notification.EventType.STEP_RELEASED,
            title="Atividade liberada",
            message=f"A atividade '{step.name}' foi liberada para o grupo {step.responsible_group.name}.",
            process=step.process,
            step=step,
            url=reverse("activity-detail", args=[step.pk]),
        )
        EmailService.send_step_released(step, recipients)

    # ------------------------------------------------------------------
    # Máquina de estados
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def assumir_atividade(step, usuario):
        if not (step.status == ProcessStep.Status.PENDENTE and step.released_at is not None):
            raise WorkflowError("Esta atividade não está disponível para ser assumida.")
        pode_assumir = usuario.groups.filter(pk=step.responsible_group_id).exists() or usuario.has_perm(
            "workflows.can_claim_any_activity"
        )
        if not pode_assumir:
            raise WorkflowError("Você não pertence ao grupo responsável por esta atividade.")

        now = timezone.now()
        step.status = ProcessStep.Status.EM_ANDAMENTO
        step.assigned_to = usuario
        step.assigned_at = now
        step.started_at = now
        step.save(update_fields=["status", "assigned_to", "assigned_at", "started_at"])

        AuditService.log(
            user=usuario, action=AuditLog.Action.CLAIM, process=step.process, step=step, new_value=usuario.get_username()
        )
        NotificationService.notify(
            users=resolve_admins(),
            event_type=Notification.EventType.STEP_CLAIMED,
            title="Atividade assumida",
            message=f"{usuario.get_username()} assumiu a atividade '{step.name}'.",
            process=step.process,
            step=step,
            url=reverse("activity-detail", args=[step.pk]),
        )
        return step

    @staticmethod
    @transaction.atomic
    def concluir_atividade(step, usuario, observations=""):
        if step.status not in (ProcessStep.Status.EM_ANDAMENTO, ProcessStep.Status.EM_REVISAO):
            raise WorkflowError("Esta atividade não pode ser concluída no status atual.")
        pode_concluir = step.assigned_to_id == usuario.id or usuario.has_perm("workflows.can_override_assignment")
        if not pode_concluir:
            raise WorkflowError("Somente quem assumiu esta atividade pode concluí-la.")

        now = timezone.now()
        old_status = step.status
        step.status = ProcessStep.Status.CONCLUIDA
        step.completed_at = now
        step.completed_by = usuario
        if observations:
            step.observations = observations
        step.save(update_fields=["status", "completed_at", "completed_by", "observations"])

        AuditService.log(
            user=usuario,
            action=AuditLog.Action.COMPLETE,
            process=step.process,
            step=step,
            old_value=old_status,
            new_value=step.status,
        )
        NotificationService.notify(
            users=resolve_admins(),
            event_type=Notification.EventType.STEP_COMPLETED,
            title="Atividade concluída",
            message=f"A atividade '{step.name}' foi concluída por {usuario.get_username()}.",
            process=step.process,
            step=step,
            url=reverse("activity-detail", args=[step.pk]),
        )

        next_step = step.process.steps.filter(order__gt=step.order).order_by("order").first()
        if next_step:
            WorkflowService.liberar_atividade(next_step)
        else:
            WorkflowService._finalizar_processo(step.process, usuario)

        return step

    @staticmethod
    def _finalizar_processo(process, usuario):
        process.status = Process.Status.FINALIZADO
        process.finalized_at = timezone.now()
        process.save(update_fields=["status", "finalized_at"])

        AuditService.log(user=usuario, action=AuditLog.Action.FINALIZE, process=process)
        NotificationService.notify(
            users={process.created_by, *resolve_admins()},
            event_type=Notification.EventType.PROCESS_FINALIZED,
            title="Processo finalizado",
            message=f"O processo '{process.title}' foi finalizado.",
            process=process,
            url=reverse("process-detail", args=[process.pk]),
        )

    @staticmethod
    @transaction.atomic
    def reabrir_atividade(step, usuario, motivo):
        if not usuario.has_perm("workflows.can_reopen_activity"):
            raise WorkflowError("Você não tem permissão para reabrir atividades.")
        if step.status != ProcessStep.Status.CONCLUIDA:
            raise WorkflowError("Somente atividades concluídas podem ser reabertas.")
        if not motivo:
            raise WorkflowError("Informe o motivo da reabertura.")

        blocking_states = (
            ProcessStep.Status.EM_ANDAMENTO,
            ProcessStep.Status.EM_REVISAO,
            ProcessStep.Status.CONCLUIDA,
        )
        has_advanced_downstream = step.process.steps.filter(
            order__gt=step.order, status__in=blocking_states
        ).exists()
        if has_advanced_downstream:
            raise WorkflowError(
                "Não é possível reabrir: uma atividade posterior já foi iniciada. Resolva manualmente pelo Admin."
            )

        # A próxima etapa só pode ter sido liberada por esta conclusão; se ainda
        # não foi tocada (PENDENTE e liberada), volta a ficar travada.
        next_step = step.process.steps.filter(order__gt=step.order).order_by("order").first()
        if next_step and next_step.status == ProcessStep.Status.PENDENTE and next_step.released_at is not None:
            next_step.released_at = None
            next_step.deadline_at = None
            next_step.save(update_fields=["released_at", "deadline_at"])

        old_status = step.status
        step.status = ProcessStep.Status.EM_ANDAMENTO
        step.completed_at = None
        step.completed_by = None
        step.save(update_fields=["status", "completed_at", "completed_by"])

        if step.process.status == Process.Status.FINALIZADO:
            step.process.status = Process.Status.ABERTO
            step.process.finalized_at = None
            step.process.save(update_fields=["status", "finalized_at"])

        AuditService.log(
            user=usuario,
            action=AuditLog.Action.REOPEN,
            process=step.process,
            step=step,
            old_value=old_status,
            new_value=step.status,
            reason=motivo,
        )
        NotificationService.notify(
            users=resolve_group_and_admins(step.responsible_group),
            event_type=Notification.EventType.STEP_REOPENED,
            title="Atividade reaberta",
            message=f"A atividade '{step.name}' foi reaberta. Motivo: {motivo}",
            process=step.process,
            step=step,
            url=reverse("activity-detail", args=[step.pk]),
        )
        return step

    @staticmethod
    @transaction.atomic
    def bloquear_atividade(step, usuario, observations):
        if step.status not in (ProcessStep.Status.PENDENTE, ProcessStep.Status.EM_ANDAMENTO):
            raise WorkflowError("Esta atividade não pode ser bloqueada no status atual.")
        pode_bloquear = usuario.groups.filter(pk=step.responsible_group_id).exists() or usuario.has_perm(
            "workflows.can_block_activity"
        )
        if not pode_bloquear:
            raise WorkflowError("Você não tem permissão para bloquear esta atividade.")
        if not observations:
            raise WorkflowError("Informe uma observação descrevendo o bloqueio.")

        old_status = step.status
        step.status = ProcessStep.Status.BLOQUEADA
        step.observations = observations
        step.save(update_fields=["status", "observations"])

        AuditService.log(
            user=usuario,
            action=AuditLog.Action.BLOCK,
            process=step.process,
            step=step,
            old_value=old_status,
            new_value=step.status,
            reason=observations,
        )
        NotificationService.notify(
            users=resolve_group_and_admins(step.responsible_group),
            event_type=Notification.EventType.STEP_BLOCKED,
            title="Atividade bloqueada",
            message=f"A atividade '{step.name}' foi bloqueada: {observations}",
            process=step.process,
            step=step,
            url=reverse("activity-detail", args=[step.pk]),
        )
        return step

    @staticmethod
    @transaction.atomic
    def desbloquear_atividade(step, usuario):
        if step.status != ProcessStep.Status.BLOQUEADA:
            raise WorkflowError("Esta atividade não está bloqueada.")
        pode_desbloquear = usuario.groups.filter(pk=step.responsible_group_id).exists() or usuario.has_perm(
            "workflows.can_block_activity"
        )
        if not pode_desbloquear:
            raise WorkflowError("Você não tem permissão para desbloquear esta atividade.")

        old_status = step.status
        step.status = ProcessStep.Status.EM_ANDAMENTO if step.assigned_to_id else ProcessStep.Status.PENDENTE
        step.save(update_fields=["status"])

        AuditService.log(
            user=usuario,
            action=AuditLog.Action.UNBLOCK,
            process=step.process,
            step=step,
            old_value=old_status,
            new_value=step.status,
        )
        return step

    @staticmethod
    @transaction.atomic
    def cancelar_atividade(step, usuario, motivo):
        if step.status not in (ProcessStep.Status.PENDENTE, ProcessStep.Status.EM_ANDAMENTO):
            raise WorkflowError("Esta atividade não pode ser cancelada no status atual.")
        if not usuario.has_perm("workflows.can_cancel_process"):
            raise WorkflowError("Você não tem permissão para cancelar atividades.")
        if not motivo:
            raise WorkflowError("Informe o motivo do cancelamento.")

        old_status = step.status
        step.status = ProcessStep.Status.CANCELADA
        step.observations = motivo
        step.save(update_fields=["status", "observations"])

        AuditService.log(
            user=usuario,
            action=AuditLog.Action.CANCEL,
            process=step.process,
            step=step,
            old_value=old_status,
            new_value=step.status,
            reason=motivo,
        )
        NotificationService.notify(
            users=resolve_group_and_admins(step.responsible_group),
            event_type=Notification.EventType.STEP_CANCELLED,
            title="Atividade cancelada",
            message=f"A atividade '{step.name}' foi cancelada. Motivo: {motivo}",
            process=step.process,
            step=step,
            url=reverse("activity-detail", args=[step.pk]),
        )
        return step

    @staticmethod
    @transaction.atomic
    def cancelar_processo(process, usuario, motivo):
        if not usuario.has_perm("workflows.can_cancel_process"):
            raise WorkflowError("Você não tem permissão para cancelar processos.")
        if process.status != Process.Status.ABERTO:
            raise WorkflowError("Somente processos abertos podem ser cancelados.")
        if not motivo:
            raise WorkflowError("Informe o motivo do cancelamento.")

        process.status = Process.Status.CANCELADO
        process.cancelled_at = timezone.now()
        process.cancelled_reason = motivo
        process.save(update_fields=["status", "cancelled_at", "cancelled_reason"])

        AuditService.log(
            user=usuario, action=AuditLog.Action.CANCEL, process=process, reason=motivo
        )

        affected_groups = Group.objects.filter(
            pk__in=process.steps.exclude(
                status__in=[ProcessStep.Status.CONCLUIDA, ProcessStep.Status.CANCELADA]
            ).values_list("responsible_group_id", flat=True)
        )
        recipients = {process.created_by, *resolve_admins()}
        for group in affected_groups:
            recipients.update(resolve_group_and_admins(group))
        NotificationService.notify(
            users=recipients,
            event_type=Notification.EventType.PROCESS_CANCELLED,
            title="Processo cancelado",
            message=f"O processo '{process.title}' foi cancelado. Motivo: {motivo}",
            process=process,
            url=reverse("process-detail", args=[process.pk]),
        )
        return process

    # ------------------------------------------------------------------
    # Customização da estrutura (somente etapas ainda não liberadas)
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def editar_estrutura_processo(step, usuario, **campos):
        if not usuario.has_perm("workflows.can_edit_workflow"):
            raise WorkflowError("Você não tem permissão para editar o workflow deste processo.")
        if not (step.status == ProcessStep.Status.PENDENTE and step.released_at is None):
            raise WorkflowError("Só é possível editar etapas que ainda não foram liberadas.")

        editable_fields = {"name", "description", "responsible_group", "priority", "order"}
        for field, value in campos.items():
            if field not in editable_fields:
                continue
            old_value = getattr(step, field)
            if old_value == value:
                continue
            setattr(step, field, value)
            AuditService.log(
                user=usuario,
                action=AuditLog.Action.UPDATE,
                process=step.process,
                step=step,
                field_name=field,
                old_value=old_value,
                new_value=value,
            )
        step.save()
        return step

    # ------------------------------------------------------------------
    # Verificação de atraso (chamada por management command)
    # ------------------------------------------------------------------

    @staticmethod
    def marcar_atividades_atrasadas():
        now = timezone.now()
        overdue_steps = ProcessStep.objects.filter(
            deadline_at__lt=now,
            overdue_notified_at__isnull=True,
            status__in=[
                ProcessStep.Status.PENDENTE,
                ProcessStep.Status.EM_ANDAMENTO,
                ProcessStep.Status.EM_REVISAO,
            ],
        ).exclude(released_at__isnull=True)

        count = 0
        for step in overdue_steps:
            recipients = resolve_group_and_admins(step.responsible_group)
            NotificationService.notify(
                users=recipients,
                event_type=Notification.EventType.STEP_OVERDUE,
                title="Atividade atrasada",
                message=f"A atividade '{step.name}' do processo '{step.process.title}' está atrasada.",
                process=step.process,
                step=step,
                url=reverse("activity-detail", args=[step.pk]),
            )
            EmailService.send_step_overdue(step, recipients)
            step.overdue_notified_at = now
            step.save(update_fields=["overdue_notified_at"])
            count += 1
        return count
