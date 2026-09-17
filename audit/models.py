from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Criação"
        UPDATE = "UPDATE", "Atualização"
        OWNER_CHANGED = "OWNER_CHANGED", "Dono alterado"
        TASK_CREATED = "TASK_CREATED", "Tarefa criada"
        EXECUTOR_ADDED = "EXECUTOR_ADDED", "Executor incluído"
        EXECUTOR_REMOVED = "EXECUTOR_REMOVED", "Executor removido"
        ASSIGNMENT_CREATED = "ASSIGNMENT_CREATED", "Atribuição criada, aguardando aceite"
        ASSIGNMENT_ACCEPTED = "ASSIGNMENT_ACCEPTED", "Atribuição aceita"
        ASSIGNMENT_REJECTED = "ASSIGNMENT_REJECTED", "Atribuição recusada"
        SESSION_STARTED = "SESSION_STARTED", "Sessão iniciada"
        SESSION_PAUSED = "SESSION_PAUSED", "Sessão pausada"
        SESSION_RESUMED = "SESSION_RESUMED", "Sessão retomada"
        SECTOR_MOVED = "SECTOR_MOVED", "Movida de setor"
        RETURNED = "RETURNED", "Devolvida"
        QUEUE_POSITION_CHANGED = "QUEUE_POSITION_CHANGED", "Posição na fila alterada"
        DEADLINE_PROPOSED = "DEADLINE_PROPOSED", "Prazo proposto"
        DEADLINE_ACCEPTED = "DEADLINE_ACCEPTED", "Prazo aceito"
        DEADLINE_REJECTED = "DEADLINE_REJECTED", "Prazo recusado"
        CONFLICT_OPENED = "CONFLICT_OPENED", "Conflito de prazo aberto"
        CONFLICT_RESOLVED = "CONFLICT_RESOLVED", "Conflito de prazo resolvido"
        BLOCK = "BLOCK", "Bloqueada"
        UNBLOCK = "UNBLOCK", "Desbloqueada"
        COMPLETE = "COMPLETE", "Concluída"
        REOPEN = "REOPEN", "Reaberta"
        CANCEL = "CANCEL", "Cancelada"
        # Segurança: toda mudança no que alguém pode fazer deixa rastro
        # (Regras 05 §41, doc 08 §30).
        PROFILE_CREATED = "PROFILE_CREATED", "Perfil criado"
        PROFILE_UPDATED = "PROFILE_UPDATED", "Perfil alterado"
        PROFILE_ACTIONS_CHANGED = "PROFILE_ACTIONS_CHANGED", "Ações do perfil alteradas"
        PROFILE_ASSIGNED = "PROFILE_ASSIGNED", "Perfil atribuído"
        PROFILE_REVOKED = "PROFILE_REVOKED", "Perfil removido"
        ACTION_GRANTED = "ACTION_GRANTED", "Concessão direta registrada"
        ACTION_REVOKED = "ACTION_REVOKED", "Concessão direta removida"
        SECTORS_CHANGED = "SECTORS_CHANGED", "Setores do usuário alterados"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuário",
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    activity = models.ForeignKey(
        "activities.Activity",
        verbose_name="atividade",
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    task = models.ForeignKey(
        "activities.Task",
        verbose_name="tarefa",
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuário afetado",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="security_audit_entries",
        help_text="Preenchido em eventos de segurança, que não se referem a uma atividade.",
    )
    action = models.CharField("ação", max_length=24, choices=Action.choices)
    field_name = models.CharField("campo alterado", max_length=50, blank=True)
    old_value = models.TextField("valor anterior", blank=True)
    new_value = models.TextField("novo valor", blank=True)
    reason = models.TextField("motivo", blank=True)
    timestamp = models.DateTimeField("data/hora", auto_now_add=True)

    class Meta:
        verbose_name = "registro de auditoria"
        verbose_name_plural = "registros de auditoria"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["activity", "timestamp"]),
            models.Index(fields=["task", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.timestamp:%d/%m/%Y %H:%M}"
