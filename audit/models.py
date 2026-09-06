from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Criação"
        UPDATE = "UPDATE", "Atualização"
        CLAIM = "CLAIM", "Assumida"
        COMPLETE = "COMPLETE", "Concluída"
        REOPEN = "REOPEN", "Reaberta"
        BLOCK = "BLOCK", "Bloqueada"
        UNBLOCK = "UNBLOCK", "Desbloqueada"
        CANCEL = "CANCEL", "Cancelada"
        FINALIZE = "FINALIZE", "Finalizada"
        DECIDE = "DECIDE", "Decisão registrada"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuário",
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    demand = models.ForeignKey(
        "demands.Demand", verbose_name="demanda", null=True, on_delete=models.SET_NULL, related_name="audit_entries"
    )
    process = models.ForeignKey(
        "workflows.Process",
        verbose_name="processo",
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    step = models.ForeignKey(
        "workflows.ProcessStep",
        verbose_name="atividade",
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    action = models.CharField("ação", max_length=12, choices=Action.choices)
    field_name = models.CharField("campo alterado", max_length=50, blank=True)
    old_value = models.TextField("valor anterior", blank=True)
    new_value = models.TextField("novo valor", blank=True)
    reason = models.TextField("motivo", blank=True)
    timestamp = models.DateTimeField("data/hora", auto_now_add=True)

    class Meta:
        verbose_name = "registro de auditoria"
        verbose_name_plural = "registros de auditoria"
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["process", "timestamp"])]

    def __str__(self):
        return f"{self.get_action_display()} - {self.timestamp:%d/%m/%Y %H:%M}"
