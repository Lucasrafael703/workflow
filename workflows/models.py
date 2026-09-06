from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models


class Priority(models.TextChoices):
    BAIXA = "BAIXA", "Baixa"
    NORMAL = "NORMAL", "Normal"
    ALTA = "ALTA", "Alta"
    URGENTE = "URGENTE", "Urgente"


class ProcessTemplate(models.Model):
    name = models.CharField("nome", max_length=150)
    description = models.TextField("descrição", blank=True)
    is_active = models.BooleanField("ativo", default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="criado por",
        on_delete=models.PROTECT,
        related_name="+",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "template de processo"
        verbose_name_plural = "templates de processo"
        permissions = [
            ("can_manage_templates", "Pode gerenciar templates de processo"),
        ]

    def __str__(self):
        return self.name


class ProcessTemplateStep(models.Model):
    template = models.ForeignKey(
        ProcessTemplate, verbose_name="template", on_delete=models.CASCADE, related_name="steps"
    )
    order = models.PositiveIntegerField("ordem")
    name = models.CharField("nome", max_length=150)
    description = models.TextField("descrição", blank=True)
    responsible_group = models.ForeignKey(
        Group, verbose_name="grupo responsável", on_delete=models.PROTECT, related_name="+"
    )
    default_deadline_days = models.PositiveIntegerField(
        "prazo padrão (dias corridos)",
        help_text="Dias corridos a partir da liberação da etapa.",
    )
    default_priority = models.CharField(
        "prioridade padrão", max_length=10, choices=Priority.choices, default=Priority.NORMAL
    )

    # Reservado para evolução futura (workflow condicional/paralelo). Não avaliado no MVP:
    # o motor sempre segue estritamente por `order`.
    next_step = models.ForeignKey(
        "self",
        verbose_name="próxima etapa (reservado)",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="previous_steps",
    )
    condition = models.CharField(
        "condição (reservado)", max_length=255, blank=True
    )

    class Meta:
        verbose_name = "etapa do template"
        verbose_name_plural = "etapas do template"
        ordering = ["order"]
        unique_together = ("template", "order")

    def __str__(self):
        return f"{self.order}. {self.name}"


class Process(models.Model):
    class Status(models.TextChoices):
        ABERTO = "ABERTO", "Aberto"
        CANCELADO = "CANCELADO", "Cancelado"
        FINALIZADO = "FINALIZADO", "Finalizado"

    template = models.ForeignKey(
        ProcessTemplate, verbose_name="template", on_delete=models.PROTECT, related_name="processes"
    )
    demand = models.ForeignKey(
        "demands.Demand",
        verbose_name="demanda de origem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="processes",
    )
    title = models.CharField("título", max_length=200)
    status = models.CharField("status", max_length=12, choices=Status.choices, default=Status.ABERTO)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="criado por",
        on_delete=models.PROTECT,
        related_name="processes_created",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    cancelled_at = models.DateTimeField("cancelado em", null=True, blank=True)
    cancelled_reason = models.TextField("motivo do cancelamento", blank=True)
    finalized_at = models.DateTimeField("finalizado em", null=True, blank=True)

    class Meta:
        verbose_name = "processo"
        verbose_name_plural = "processos"
        permissions = [
            ("can_create_process", "Pode criar processo"),
            ("can_cancel_process", "Pode cancelar processo"),
            ("can_view_all_processes", "Pode visualizar todos os processos"),
            ("can_view_dashboard", "Pode visualizar o dashboard"),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def current_step(self):
        return (
            self.steps.exclude(status__in=[ProcessStep.Status.CONCLUIDA, ProcessStep.Status.CANCELADA])
            .order_by("order")
            .first()
        )


class ProcessStep(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        EM_REVISAO = "EM_REVISAO", "Em revisão"
        CONCLUIDA = "CONCLUIDA", "Concluída"
        BLOQUEADA = "BLOQUEADA", "Bloqueada"
        CANCELADA = "CANCELADA", "Cancelada"

    process = models.ForeignKey(Process, verbose_name="processo", on_delete=models.CASCADE, related_name="steps")
    template_step = models.ForeignKey(
        ProcessTemplateStep,
        verbose_name="etapa do template de origem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    order = models.PositiveIntegerField("ordem")
    name = models.CharField("nome", max_length=150)
    description = models.TextField("descrição", blank=True)
    responsible_group = models.ForeignKey(
        Group, verbose_name="grupo responsável", on_delete=models.PROTECT, related_name="+"
    )
    priority = models.CharField("prioridade", max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField("status", max_length=12, choices=Status.choices, default=Status.PENDENTE)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="assumida por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="steps_assumed",
    )
    assigned_at = models.DateTimeField("assumida em", null=True, blank=True)

    released_at = models.DateTimeField("liberada em", null=True, blank=True)
    deadline_at = models.DateTimeField("prazo", null=True, blank=True)
    started_at = models.DateTimeField("iniciada em", null=True, blank=True)
    completed_at = models.DateTimeField("concluída em", null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="concluída por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    observations = models.TextField("observações", blank=True)

    # Reservado para evolução futura (workflow condicional/paralelo).
    next_step = models.ForeignKey(
        "self", verbose_name="próxima etapa (reservado)", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    condition = models.CharField("condição (reservado)", max_length=255, blank=True)

    overdue_notified_at = models.DateTimeField(
        "notificação de atraso enviada em",
        null=True,
        blank=True,
        help_text="Evita reenviar a notificação/e-mail de atraso a cada verificação.",
    )

    class Meta:
        verbose_name = "atividade"
        verbose_name_plural = "atividades"
        ordering = ["order"]
        unique_together = ("process", "order")
        permissions = [
            ("can_claim_any_activity", "Pode assumir qualquer atividade, fora do próprio grupo"),
            ("can_override_assignment", "Pode concluir atividade que não assumiu"),
            ("can_reopen_activity", "Pode reabrir atividade concluída"),
            ("can_edit_workflow", "Pode editar a estrutura do workflow de um processo"),
            ("can_block_activity", "Pode bloquear/desbloquear atividade"),
        ]

    def __str__(self):
        return f"{self.process} - {self.order}. {self.name}"

    @property
    def is_releasable_pending(self):
        return self.status == self.Status.PENDENTE and self.released_at is not None

    @property
    def is_overdue(self):
        from django.utils import timezone

        return (
            self.deadline_at is not None
            and self.deadline_at < timezone.now()
            and self.status in (self.Status.PENDENTE, self.Status.EM_ANDAMENTO, self.Status.EM_REVISAO)
        )


class Attachment(models.Model):
    class Category(models.TextChoices):
        DOCUMENTO = "DOCUMENTO", "Documento"
        PROPOSTA = "PROPOSTA", "Proposta"
        PLANILHA = "PLANILHA", "Planilha"
        FOTO = "FOTO", "Foto"
        OUTRO = "OUTRO", "Outro"

    process = models.ForeignKey(Process, verbose_name="processo", on_delete=models.CASCADE, related_name="attachments")
    step = models.ForeignKey(
        ProcessStep,
        verbose_name="atividade",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attachments",
    )
    file = models.FileField("arquivo", upload_to="attachments/%Y/%m/")
    category = models.CharField("categoria", max_length=12, choices=Category.choices, default=Category.OUTRO)
    description = models.CharField("descrição", max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="enviado por", on_delete=models.PROTECT, related_name="+"
    )
    uploaded_at = models.DateTimeField("enviado em", auto_now_add=True)

    class Meta:
        verbose_name = "anexo"
        verbose_name_plural = "anexos"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.description or self.file.name
