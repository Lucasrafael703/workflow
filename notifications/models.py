from django.conf import settings
from django.db import models


class Notification(models.Model):
    class EventType(models.TextChoices):
        STEP_RELEASED = "STEP_RELEASED", "Atividade liberada"
        STEP_OVERDUE = "STEP_OVERDUE", "Atividade atrasada"
        STEP_CLAIMED = "STEP_CLAIMED", "Atividade assumida"
        STEP_COMPLETED = "STEP_COMPLETED", "Atividade concluída"
        STEP_REOPENED = "STEP_REOPENED", "Atividade reaberta"
        STEP_BLOCKED = "STEP_BLOCKED", "Atividade bloqueada"
        STEP_CANCELLED = "STEP_CANCELLED", "Atividade cancelada"
        PROCESS_CREATED = "PROCESS_CREATED", "Processo criado"
        PROCESS_CANCELLED = "PROCESS_CANCELLED", "Processo cancelado"
        PROCESS_FINALIZED = "PROCESS_FINALIZED", "Processo finalizado"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="destinatário", on_delete=models.CASCADE, related_name="notifications"
    )
    event_type = models.CharField("tipo", max_length=20, choices=EventType.choices)
    process = models.ForeignKey(
        "workflows.Process", verbose_name="processo", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    step = models.ForeignKey(
        "workflows.ProcessStep",
        verbose_name="atividade",
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
