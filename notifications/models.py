from django.conf import settings
from django.db import models


class Notification(models.Model):
    class EventType(models.TextChoices):
        TASK_ASSIGNED = "TASK_ASSIGNED", "Tarefa atribuída"
        TASK_ASSIGNMENT_PENDING = "TASK_ASSIGNMENT_PENDING", "Atribuição aguardando seu aceite"
        TASK_ASSIGNMENT_REJECTED = "TASK_ASSIGNMENT_REJECTED", "Atribuição recusada"
        TASK_RETURNED = "TASK_RETURNED", "Tarefa devolvida"
        TASK_BLOCKED = "TASK_BLOCKED", "Tarefa bloqueada"
        TASK_UNBLOCKED = "TASK_UNBLOCKED", "Tarefa desbloqueada"
        TASK_COMPLETED = "TASK_COMPLETED", "Tarefa concluída"
        QUEUE_POSITION_CHANGED = "QUEUE_POSITION_CHANGED", "Posição na fila alterada"
        DEADLINE_PROPOSED = "DEADLINE_PROPOSED", "Novo prazo proposto"
        DEADLINE_ACCEPTED = "DEADLINE_ACCEPTED", "Prazo aceito"
        DEADLINE_REJECTED = "DEADLINE_REJECTED", "Prazo recusado"
        DEADLINE_CONFLICT = "DEADLINE_CONFLICT", "Conflito de prazo"
        TASK_OVERDUE = "TASK_OVERDUE", "Tarefa atrasada"
        ACTIVITY_CREATED = "ACTIVITY_CREATED", "Atividade criada"
        ACTIVITY_COMPLETED = "ACTIVITY_COMPLETED", "Atividade concluída"
        ACTIVITY_CANCELLED = "ACTIVITY_CANCELLED", "Atividade cancelada"
        ACTIVITY_REOPENED = "ACTIVITY_REOPENED", "Atividade reaberta"
        ACTIVITY_PENDING = "ACTIVITY_PENDING", "Atividade pendente"
        ACTIVITY_APPROVAL_NEEDED = "ACTIVITY_APPROVAL_NEEDED", "Pendência aguardando aprovação"
        ACTIVITY_APPROVED = "ACTIVITY_APPROVED", "Pendência aprovada"
        OWNER_CHANGED = "OWNER_CHANGED", "Dono alterado"
        MESSAGE_POSTED = "MESSAGE_POSTED", "Nova mensagem"
        MENTIONED = "MENTIONED", "Você foi mencionado"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="destinatário", on_delete=models.CASCADE, related_name="notifications"
    )
    event_type = models.CharField("tipo", max_length=24, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="quem gerou o evento",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Quem delegou, propôs, mencionou ou concluiu — o sujeito da frase da notificação.",
    )
    activity = models.ForeignKey(
        "activities.Activity",
        verbose_name="atividade",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    task = models.ForeignKey(
        "activities.Task",
        verbose_name="tarefa",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    title = models.CharField("título", max_length=150)
    message = models.CharField("mensagem", max_length=255)
    url = models.CharField("link", max_length=255, blank=True)
    is_read = models.BooleanField("lida", default=False)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    read_at = models.DateTimeField("lida em", null=True, blank=True)

    class Meta:
        verbose_name = "notificação"
        verbose_name_plural = "notificações"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"
