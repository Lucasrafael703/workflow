from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from audit.models import AuditLog
from audit.services import AuditService
from notifications.models import Notification
from notifications.recipients import resolve_admins, resolve_sector_and_admins
from notifications.services import NotificationService

from .models import (
    Activity,
    ActivityMessage,
    DeadlineConflict,
    DeadlineProposal,
    OwnerChangeLog,
    QueueEntry,
    QueuePositionChange,
    SectorTransfer,
    Task,
    TaskBlock,
    TaskExecutor,
    TaskMessage,
    TaskReturn,
    WorkSession,
)


User = get_user_model()


class ActivityError(Exception):
    """Levantado para qualquer transição/ação inválida do núcleo de atividades.
    Views capturam esta exceção e exibem a mensagem via django.contrib.messages."""


def _same_organization(*objects):
    orgs = {obj.organization_id for obj in objects if obj is not None}
    return len(orgs) <= 1


class ActivityService:
    # ------------------------------------------------------------------
    # Criação e responsabilidade
    # ------------------------------------------------------------------

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
    ):
        if not title:
            raise ActivityError("Informe o resultado esperado da atividade.")
        if owner is None:
            raise ActivityError("Toda atividade precisa de um único dono.")

        activity = Activity.objects.create(
            organization=organization,
            company=company,
            site=site,
            cost_center=cost_center,
            title=title,
            description=description,
            owner=owner,
            created_by=created_by,
            requested_deadline=requested_deadline,
        )

        AuditService.log(user=created_by, action=AuditLog.Action.CREATE, activity=activity, new_value=title)
        NotificationService.notify(
            users={owner, created_by, *resolve_admins()},
            event_type=Notification.EventType.ACTIVITY_CREATED,
            title="Atividade criada",
            message=f"A atividade '{activity.title}' foi criada.",
            activity=activity,
        )
        return activity

    @staticmethod
    @transaction.atomic
    def change_owner(activity, new_owner, changed_by):
        if not changed_by.has_perm("activities.can_change_owner"):
            raise ActivityError("Você não tem permissão para alterar o dono desta atividade.")
        if activity.status in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA):
            raise ActivityError("Não é possível alterar o dono de uma atividade concluída ou cancelada.")
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
            users={previous_owner, new_owner, *resolve_admins()},
            event_type=Notification.EventType.OWNER_CHANGED,
            title="Dono da atividade alterado",
            message=f"O dono de '{activity.title}' passou de {previous_owner} para {new_owner}.",
            activity=activity,
        )
        return activity

    @staticmethod
    @transaction.atomic
    def update_activity(activity, user, **fields):
        """Edita campos não sensíveis da atividade, auditando cada alteração.

        Dono, conclusão e cancelamento possuem serviços próprios e não passam por aqui.
        """
        if activity.status in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA):
            raise ActivityError("Não é possível editar uma atividade concluída ou cancelada.")

        editable = {"title", "description", "requested_deadline", "company", "site", "cost_center"}
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
        return activity

    @staticmethod
    def _register_first_action(activity_or_task):
        """Marca a primeira ação relevante, se ainda não registrada (Regras 02 §45)."""
        if activity_or_task.first_action_at is None:
            activity_or_task.first_action_at = timezone.now()
            activity_or_task.save(update_fields=["first_action_at"])

    @staticmethod
    @transaction.atomic
    def complete_activity(activity, user):
        if activity.status in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA):
            raise ActivityError("Esta atividade já está concluída ou cancelada.")
        open_tasks = activity.tasks.exclude(
            status__in=[Task.Status.CONCLUIDA, Task.Status.CANCELADA]
        )
        if open_tasks.exists():
            raise ActivityError("Existem tarefas ainda não concluídas ou canceladas nesta atividade.")

        old_status = activity.status
        activity.status = Activity.Status.CONCLUIDA
        activity.completed_at = timezone.now()
        activity.completed_by = user
        activity.save(update_fields=["status", "completed_at", "completed_by"])

        AuditService.log(
            user=user, action=AuditLog.Action.COMPLETE, activity=activity, old_value=old_status, new_value=activity.status
        )
        NotificationService.notify(
            users={activity.owner, *resolve_admins()},
            event_type=Notification.EventType.ACTIVITY_COMPLETED,
            title="Atividade concluída",
            message=f"A atividade '{activity.title}' foi concluída.",
            activity=activity,
        )
        return activity

    @staticmethod
    @transaction.atomic
    def cancel_activity(activity, user, reason):
        if not user.has_perm("activities.can_cancel_activity"):
            raise ActivityError("Você não tem permissão para cancelar atividades.")
        if activity.status in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA):
            raise ActivityError("Esta atividade já está concluída ou cancelada.")
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
            users={activity.owner, *resolve_admins()},
            event_type=Notification.EventType.ACTIVITY_CANCELLED,
            title="Atividade cancelada",
            message=f"A atividade '{activity.title}' foi cancelada. Motivo: {reason}",
            activity=activity,
        )
        return activity

    @staticmethod
    @transaction.atomic
    def reopen_activity(activity, user, reason):
        if not user.has_perm("activities.can_reopen_activity"):
            raise ActivityError("Você não tem permissão para reabrir atividades.")
        if activity.status != Activity.Status.CONCLUIDA:
            raise ActivityError("Somente atividades concluídas podem ser reabertas.")
        if not reason:
            raise ActivityError("Informe o motivo da reabertura.")

        activity.status = Activity.Status.EM_ANDAMENTO
        activity.completed_at = None
        activity.completed_by = None
        activity.reopened_at = timezone.now()
        activity.save(update_fields=["status", "completed_at", "completed_by", "reopened_at"])

        AuditService.log(
            user=user, action=AuditLog.Action.REOPEN, activity=activity, new_value=activity.status, reason=reason
        )
        NotificationService.notify(
            users={activity.owner, *resolve_admins()},
            event_type=Notification.EventType.ACTIVITY_REOPENED,
            title="Atividade reaberta",
            message=f"A atividade '{activity.title}' foi reaberta. Motivo: {reason}",
            activity=activity,
        )
        return activity


class TaskService:
    # ------------------------------------------------------------------
    # Criação e execução
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_task(activity, sector, title, created_by, description="", order=1, depends_on=None, requested_deadline=None):
        if not _same_organization(activity, sector):
            raise ActivityError("O setor informado pertence a outra organização.")
        if not title:
            raise ActivityError("Informe o título da tarefa.")

        task = Task.objects.create(
            activity=activity,
            sector=sector,
            order=order,
            title=title,
            description=description,
            depends_on=depends_on,
            requested_deadline=requested_deadline,
            status=Task.Status.DISPONIVEL,
            created_by=created_by,
        )
        AuditService.log(user=created_by, action=AuditLog.Action.TASK_CREATED, activity=activity, task=task, new_value=title)

        QueueService.enqueue(task, sector, user=created_by)

        recipients = resolve_sector_and_admins(sector)
        NotificationService.notify(
            users=recipients,
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Nova tarefa disponível",
            message=f"A tarefa '{task.title}' está disponível no setor {sector.name}.",
            activity=activity,
            task=task,
        )
        return task

    @staticmethod
    @transaction.atomic
    def update_task(task, user, **fields):
        """Edita campos não sensíveis da tarefa, auditando cada alteração.

        Setor, prazo comprometido, executores e transições de estado possuem
        serviços próprios e não passam por aqui.
        """
        if task.status in (Task.Status.CONCLUIDA, Task.Status.CANCELADA):
            raise ActivityError("Não é possível editar uma tarefa concluída ou cancelada.")

        editable = {"title", "description", "requested_deadline", "order", "depends_on"}
        changed = []
        for field, value in fields.items():
            if field not in editable:
                continue
            old_value = getattr(task, field)
            if old_value == value:
                continue
            if field == "title" and not value:
                raise ActivityError("Informe o título da tarefa.")
            if field == "depends_on" and value is not None and value.pk == task.pk:
                raise ActivityError("Uma tarefa não pode depender dela mesma.")
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
        return task

    @staticmethod
    @transaction.atomic
    def log_manual_time(task, user, started_at, ended_at, logged_by):
        """Apropriação posterior de tempo trabalhado (Regras 04 §110-113, §214).

        Fica marcada como lançamento manual para diferenciar do tempo capturado
        pelo timer, preservando a confiabilidade das métricas.
        """
        if started_at is None or ended_at is None:
            raise ActivityError("Informe o início e o fim do período trabalhado.")
        if ended_at <= started_at:
            raise ActivityError("O fim do período precisa ser posterior ao início.")
        if started_at > timezone.now():
            raise ActivityError("Não é possível lançar tempo no futuro.")
        # Tempo só pode ser apropriado a quem de fato executa a tarefa — do
        # contrário as horas-homem deixam de refletir o trabalho real.
        if not TaskService._is_active_executor(task, user):
            raise ActivityError("Só é possível lançar tempo para um executor da tarefa.")

        session = WorkSession.objects.create(
            task=task, user=user, started_at=started_at, ended_at=ended_at, is_manual=True
        )
        ActivityService._register_first_action(task)
        ActivityService._register_first_action(task.activity)

        AuditService.log(
            user=logged_by,
            action=AuditLog.Action.SESSION_STARTED,
            activity=task.activity,
            task=task,
            new_value=f"{started_at:%d/%m/%Y %H:%M} - {ended_at:%d/%m/%Y %H:%M}",
            reason="Lançamento manual de tempo",
        )
        return session

    @staticmethod
    @transaction.atomic
    def add_executor(task, user, added_by):
        if TaskExecutor.objects.filter(task=task, user=user, removed_at__isnull=True).exists():
            raise ActivityError("Este usuário já é executor desta tarefa.")

        TaskExecutor.objects.create(task=task, user=user, added_by=added_by)
        AuditService.log(
            user=added_by, action=AuditLog.Action.EXECUTOR_ADDED, activity=task.activity, task=task, new_value=user.get_username()
        )
        NotificationService.notify(
            users={user},
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Você foi incluído em uma tarefa",
            message=f"Você foi incluído como executor de '{task.title}'.",
            activity=task.activity,
            task=task,
        )
        return task

    @staticmethod
    @transaction.atomic
    def remove_executor(task, user, removed_by):
        link = TaskExecutor.objects.filter(task=task, user=user, removed_at__isnull=True).first()
        if link is None:
            raise ActivityError("Este usuário não é executor ativo desta tarefa.")

        link.removed_at = timezone.now()
        link.save(update_fields=["removed_at"])
        AuditService.log(
            user=removed_by, action=AuditLog.Action.EXECUTOR_REMOVED, activity=task.activity, task=task, new_value=user.get_username()
        )
        return task

    @staticmethod
    def _is_active_executor(task, user):
        return TaskExecutor.objects.filter(task=task, user=user, removed_at__isnull=True).exists()

    @staticmethod
    @transaction.atomic
    def start(task, user):
        if not TaskService._is_active_executor(task, user):
            raise ActivityError("Somente executores atribuídos podem iniciar a tarefa.")
        if task.status not in (
            Task.Status.DISPONIVEL,
            Task.Status.EM_FILA,
            Task.Status.DEVOLVIDA,
            Task.Status.EM_EXECUCAO,
        ):
            raise ActivityError("Esta tarefa não pode ser iniciada no status atual.")

        # Regra 04 §115: iniciar uma nova sessão pausa qualquer sessão ativa
        # da mesma pessoa em outra tarefa (evita dupla contagem de tempo).
        now = timezone.now()
        other_open_sessions = WorkSession.objects.filter(user=user, ended_at__isnull=True).exclude(task=task)
        for session in other_open_sessions:
            session.ended_at = now
            session.save(update_fields=["ended_at"])
            AuditService.log(user=user, action=AuditLog.Action.SESSION_PAUSED, activity=session.task.activity, task=session.task)

        if not WorkSession.objects.filter(task=task, user=user, ended_at__isnull=True).exists():
            WorkSession.objects.create(task=task, user=user, started_at=now)

        old_status = task.status
        task.status = Task.Status.EM_EXECUCAO
        task.save(update_fields=["status"])
        ActivityService._register_first_action(task)
        ActivityService._register_first_action(task.activity)

        AuditService.log(
            user=user, action=AuditLog.Action.SESSION_STARTED, activity=task.activity, task=task, old_value=old_status, new_value=task.status
        )
        return task

    @staticmethod
    @transaction.atomic
    def pause(task, user):
        session = WorkSession.objects.filter(task=task, user=user, ended_at__isnull=True).first()
        if session is None:
            raise ActivityError("Você não possui uma sessão de trabalho ativa nesta tarefa.")

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
        if not TaskService._is_active_executor(task, user):
            raise ActivityError("Somente executores atribuídos podem retomar a tarefa.")
        return TaskService.start(task, user)

    @staticmethod
    @transaction.atomic
    def complete(task, user):
        if task.status not in (Task.Status.EM_EXECUCAO, Task.Status.EM_FILA, Task.Status.DISPONIVEL):
            raise ActivityError("Esta tarefa não pode ser concluída no status atual.")

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
        NotificationService.notify(
            users={task.activity.owner},
            event_type=Notification.EventType.TASK_COMPLETED,
            title="Tarefa concluída",
            message=f"A tarefa '{task.title}' foi concluída.",
            activity=task.activity,
            task=task,
        )
        return task

    @staticmethod
    @transaction.atomic
    def cancel(task, user, reason):
        if task.status in (Task.Status.CONCLUIDA, Task.Status.CANCELADA):
            raise ActivityError("Esta tarefa já está concluída ou cancelada.")
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
    def block(task, user, reason, observation=""):
        if not reason:
            raise ActivityError("Informe o motivo do bloqueio.")
        if task.status == Task.Status.BLOQUEADA:
            raise ActivityError("Esta tarefa já está bloqueada.")

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
        )
        return task

    @staticmethod
    @transaction.atomic
    def unblock(task, user, resume_status=None):
        if task.status != Task.Status.BLOQUEADA:
            raise ActivityError("Esta tarefa não está bloqueada.")

        open_block = task.blocks.filter(ended_at__isnull=True).order_by("-started_at").first()
        if open_block:
            open_block.ended_at = timezone.now()
            open_block.ended_by = user
            open_block.save(update_fields=["ended_at", "ended_by"])

        task.status = resume_status or Task.Status.EM_FILA
        task.save(update_fields=["status"])

        AuditService.log(user=user, action=AuditLog.Action.UNBLOCK, activity=task.activity, task=task, new_value=task.status)
        NotificationService.notify(
            users={task.activity.owner},
            event_type=Notification.EventType.TASK_UNBLOCKED,
            title="Tarefa desbloqueada",
            message=f"A tarefa '{task.title}' foi desbloqueada.",
            activity=task.activity,
            task=task,
        )
        return task

    # ------------------------------------------------------------------
    # Fluxo entre setores / devolução
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def move_to_sector(task, new_sector, user, note=""):
        if not _same_organization(task.activity, new_sector):
            raise ActivityError("O setor informado pertence a outra organização.")

        old_sector = task.sector
        now = timezone.now()

        active_entry = task.queue_entries.filter(left_at__isnull=True).first()
        if active_entry:
            active_entry.left_at = now
            active_entry.save(update_fields=["left_at"])
            QueueService.renumber(old_sector)

        task.sector = new_sector
        task.status = Task.Status.EM_FILA
        task.save(update_fields=["sector", "status"])

        SectorTransfer.objects.create(task=task, from_sector=old_sector, to_sector=new_sector, moved_by=user, note=note)
        QueueService.enqueue(task, new_sector, user=user)

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
        )
        return task

    @staticmethod
    @transaction.atomic
    def return_task(task, to_sector, reason, user, observation=""):
        """Devolve a tarefa para um setor anterior. Motivo sempre obrigatório (Regras 02 §36-39)."""
        if reason is None:
            raise ActivityError("Toda devolução precisa de um motivo.")
        if not _same_organization(task.activity, to_sector, reason):
            raise ActivityError("Dados informados pertencem a outra organização.")

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

        TaskService.move_to_sector(task, to_sector, user, note=f"Devolução: {reason.name}")

        recipients = resolve_sector_and_admins(to_sector) | resolve_sector_and_admins(old_sector)
        NotificationService.notify(
            users=recipients | {task.activity.owner},
            event_type=Notification.EventType.TASK_RETURNED,
            title="Tarefa devolvida",
            message=f"A tarefa '{task.title}' foi devolvida de {old_sector.name} para {to_sector.name}. Motivo: {reason.name}",
            activity=task.activity,
            task=task,
        )
        return task


    @staticmethod
    def mark_overdue_tasks():
        """Verifica tarefas com prazo comprometido vencido e ainda não notificadas
        (Regras 03 §140-142, 04). Deve ser agendada periodicamente."""
        now = timezone.now()
        overdue_tasks = Task.objects.filter(
            committed_deadline__lt=now,
            overdue_notified_at__isnull=True,
            status__in=[Task.Status.DISPONIVEL, Task.Status.EM_FILA, Task.Status.EM_EXECUCAO, Task.Status.BLOQUEADA],
        )

        count = 0
        for task in overdue_tasks:
            recipients = resolve_sector_and_admins(task.sector) | {task.activity.owner}
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


class QueueService:
    @staticmethod
    @transaction.atomic
    def enqueue(task, sector, user=None):
        """Insere a tarefa no final da fila ativa do setor (Regras 03 §6-8)."""
        active_entries = QueueEntry.objects.filter(sector=sector, left_at__isnull=True).order_by("position")
        new_total = active_entries.count() + 1
        position = new_total

        entry = QueueEntry.objects.create(
            task=task, sector=sector, position=position, queue_size_at_entry=new_total
        )
        task.status = Task.Status.EM_FILA
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
        if not user.has_perm("activities.can_reorder_queue"):
            raise ActivityError("Você não tem permissão para reordenar esta fila.")
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
        )
        return queue_entry


class DeadlineService:
    @staticmethod
    @transaction.atomic
    def propose(task, deadline, user):
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
        )
        return proposal

    @staticmethod
    @transaction.atomic
    def accept(proposal, user):
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
        )
        return proposal

    @staticmethod
    @transaction.atomic
    def reject(proposal, user, note=""):
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
        )
        return conflict

    @staticmethod
    @transaction.atomic
    def resolve_conflict(conflict, user, resolution_note):
        if not user.has_perm("activities.can_resolve_deadline_conflict"):
            raise ActivityError("Você não tem permissão para resolver conflitos de prazo.")
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
        return conflict


class MessageService:
    """Comunicação contextual (Regras 06).

    Mensagem nunca altera dado oficial: para mudar prazo, devolver ou concluir
    é preciso a ação estruturada correspondente (Regras 01 §6.14, 06 §137).
    """

    @staticmethod
    def _truncate(text, limit=200):
        text = " ".join(text.split())
        return text if len(text) <= limit else f"{text[: limit - 1]}…"

    @staticmethod
    def _executors_of(task_queryset_filter):
        return User.objects.filter(
            tasks_executed__removed_at__isnull=True, **task_queryset_filter
        ).distinct()

    @staticmethod
    @transaction.atomic
    def post_activity_message(activity, author, body):
        body = (body or "").strip()
        if not body:
            raise ActivityError("Escreva uma mensagem antes de enviar.")

        message = ActivityMessage.objects.create(activity=activity, author=author, body=body)

        recipients = {activity.owner, activity.created_by}
        recipients.update(MessageService._executors_of({"tasks_executed__task__activity": activity}))
        recipients = {u for u in recipients if u is not None and u.id != author.id}

        if recipients:
            NotificationService.notify(
                users=recipients,
                event_type=Notification.EventType.ACTIVITY_CREATED,
                title="Nova mensagem na atividade",
                message=MessageService._truncate(f"{author.get_username()}: {body}"),
                activity=activity,
            )
        return message

    @staticmethod
    @transaction.atomic
    def post_task_message(task, author, body):
        body = (body or "").strip()
        if not body:
            raise ActivityError("Escreva uma mensagem antes de enviar.")

        message = TaskMessage.objects.create(task=task, author=author, body=body)

        recipients = {task.activity.owner}
        recipients.update(MessageService._executors_of({"tasks_executed__task": task}))
        recipients = {u for u in recipients if u is not None and u.id != author.id}

        if recipients:
            NotificationService.notify(
                users=recipients,
                event_type=Notification.EventType.TASK_ASSIGNED,
                title="Nova mensagem na tarefa",
                message=MessageService._truncate(f"{author.get_username()}: {body}"),
                activity=task.activity,
                task=task,
            )
        return message
