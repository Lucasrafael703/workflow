from django.conf import settings
from django.db import models


class ActivityType(models.Model):
    """Classificação usada para organizar processos (Regras 11 §4). Um tipo pode ter vários processos."""

    organization = models.ForeignKey(
        "core.Organization", verbose_name="organização", on_delete=models.CASCADE, related_name="activity_types"
    )
    name = models.CharField("nome", max_length=150)
    is_active = models.BooleanField("ativo", default=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "tipo de atividade"
        verbose_name_plural = "tipos de atividade"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_activity_type_name_per_org"),
        ]

    def __str__(self):
        return self.name


class Process(models.Model):
    """Modelo reutilizável de execução (Regras 11 §3). Pertence a uma única empresa (§7)."""

    organization = models.ForeignKey(
        "core.Organization", verbose_name="organização", on_delete=models.CASCADE, related_name="processes"
    )
    company = models.ForeignKey(
        "core.Company", verbose_name="empresa", on_delete=models.PROTECT, related_name="processes"
    )
    activity_type = models.ForeignKey(
        ActivityType,
        verbose_name="tipo de atividade",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="processes",
    )
    name = models.CharField("nome", max_length=200)
    description = models.TextField("descrição", blank=True)
    is_active = models.BooleanField(
        "ativo", default=True, help_text="Inativar impede novas aplicações, mas preserva o histórico (Regras 05 §22)."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="criado por", on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "processo"
        verbose_name_plural = "processos"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["company", "name"], name="unique_process_name_per_company"),
        ]

    def __str__(self):
        return self.name

    @property
    def published_version(self):
        return self.versions.filter(status=ProcessVersion.Status.PUBLICADO).order_by("-number").first()

    @property
    def draft_version(self):
        return self.versions.filter(status=ProcessVersion.Status.RASCUNHO).order_by("-number").first()


class ProcessVersion(models.Model):
    """Definição versionada do processo (Regras 11 §17-19). Publicada não é alterada retroativamente."""

    class Status(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"
        PUBLICADO = "PUBLICADO", "Publicado"
        SUBSTITUIDO = "SUBSTITUIDO", "Substituído"

    class EvidenceType(models.TextChoices):
        ARQUIVO = "ARQUIVO", "Arquivo"
        LINK = "LINK", "Link"
        CHECKLIST = "CHECKLIST", "Checklist"
        CONFIRMACAO = "CONFIRMACAO", "Confirmação simples"

    process = models.ForeignKey(Process, verbose_name="processo", on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField("versão")
    status = models.CharField("status", max_length=11, choices=Status.choices, default=Status.RASCUNHO)

    output_description = models.TextField(
        "entrega esperada",
        blank=True,
        help_text="Resultado verificável, não a ação (Regras 11 §11) — ex.: 'Proposta comercial pronta para envio'.",
    )
    output_evidence_type = models.CharField(
        "evidência do output", max_length=11, choices=EvidenceType.choices, blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="criada por", on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="publicada por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    published_at = models.DateTimeField("publicada em", null=True, blank=True)

    class Meta:
        verbose_name = "versão do processo"
        verbose_name_plural = "versões do processo"
        ordering = ["process", "-number"]
        constraints = [
            models.UniqueConstraint(fields=["process", "number"], name="unique_version_number_per_process"),
        ]

    def __str__(self):
        return f"{self.process} — v{self.number} ({self.get_status_display()})"

    @property
    def is_editable(self):
        return self.status == self.Status.RASCUNHO


class ProcessInput(models.Model):
    """O que precisa estar disponível para a execução acontecer (Regras 11 §8-9)."""

    class InputType(models.TextChoices):
        TEXTO = "TEXTO", "Texto"
        ARQUIVO = "ARQUIVO", "Arquivo"
        DATA = "DATA", "Data"
        NUMERO = "NUMERO", "Número"
        LINK = "LINK", "Link"
        SELECAO = "SELECAO", "Seleção"

    class Source(models.TextChoices):
        SOLICITANTE = "SOLICITANTE", "Solicitante"
        EXECUTOR = "EXECUTOR", "Executor"
        TERCEIRO = "TERCEIRO", "Terceiro"

    version = models.ForeignKey(
        ProcessVersion, verbose_name="versão do processo", on_delete=models.CASCADE, related_name="inputs"
    )
    name = models.CharField("nome", max_length=150)
    input_type = models.CharField("tipo", max_length=8, choices=InputType.choices, default=InputType.TEXTO)
    is_required = models.BooleanField("obrigatório", default=True)
    source = models.CharField("origem", max_length=11, choices=Source.choices, blank=True)
    help_text = models.CharField("ajuda de preenchimento", max_length=255, blank=True)
    order = models.PositiveIntegerField("ordem", default=1)

    class Meta:
        verbose_name = "input do processo"
        verbose_name_plural = "inputs do processo"
        ordering = ["version", "order"]

    def __str__(self):
        return self.name


class ProcessCriterion(models.Model):
    """Como a organização comprova que a entrega está pronta (Regras 11 §13-14)."""

    version = models.ForeignKey(
        ProcessVersion, verbose_name="versão do processo", on_delete=models.CASCADE, related_name="criteria"
    )
    name = models.CharField("critério", max_length=255)
    is_required = models.BooleanField("obrigatório", default=True)
    order = models.PositiveIntegerField("ordem", default=1)

    class Meta:
        verbose_name = "critério de aceite"
        verbose_name_plural = "critérios de aceite"
        ordering = ["version", "order"]

    def __str__(self):
        return self.name


class ProcessStep(models.Model):
    """Tarefa modelo do fluxo padrão (Regras 11 §15-16). Vira tarefa real ao aplicar o processo."""

    version = models.ForeignKey(
        ProcessVersion, verbose_name="versão do processo", on_delete=models.CASCADE, related_name="steps"
    )
    sector = models.ForeignKey(
        "core.Sector", verbose_name="setor responsável", on_delete=models.PROTECT, related_name="+"
    )
    name = models.CharField("nome da tarefa", max_length=200)
    order = models.PositiveIntegerField("ordem", default=1)
    depends_on_previous = models.BooleanField(
        "depende da etapa anterior",
        default=True,
        help_text="Dependência simples e linear (Regras 11 §37) — sem regras condicionais.",
    )

    class Meta:
        verbose_name = "etapa do fluxo padrão"
        verbose_name_plural = "etapas do fluxo padrão"
        ordering = ["version", "order"]

    def __str__(self):
        return f"{self.order}. {self.name} — {self.sector}"


# ---------------------------------------------------------------------------
# Execução: o que a atividade concreta faz com o processo aplicado
# ---------------------------------------------------------------------------


class ActivityInputValue(models.Model):
    """Situação de um input do processo dentro de uma atividade real (Regras 11 §10, §29)."""

    activity = models.ForeignKey(
        "activities.Activity", verbose_name="atividade", on_delete=models.CASCADE, related_name="input_values"
    )
    process_input = models.ForeignKey(
        ProcessInput, verbose_name="input do processo", on_delete=models.PROTECT, related_name="+"
    )
    value = models.TextField("valor", blank=True)
    is_received = models.BooleanField("recebido", default=False)
    received_at = models.DateTimeField("recebido em", null=True, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrado por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "input recebido na atividade"
        verbose_name_plural = "inputs recebidos na atividade"
        ordering = ["activity", "process_input__order"]
        constraints = [
            models.UniqueConstraint(fields=["activity", "process_input"], name="unique_input_value_per_activity"),
        ]

    def __str__(self):
        return f"{self.process_input}: {'recebido' if self.is_received else 'faltando'}"


class ActivityCriterionCheck(models.Model):
    """Situação de um critério de aceite dentro de uma atividade real (Regras 11 §14, §31)."""

    activity = models.ForeignKey(
        "activities.Activity", verbose_name="atividade", on_delete=models.CASCADE, related_name="criterion_checks"
    )
    process_criterion = models.ForeignKey(
        ProcessCriterion, verbose_name="critério de aceite", on_delete=models.PROTECT, related_name="+"
    )
    is_met = models.BooleanField("atendido", default=False)
    met_at = models.DateTimeField("atendido em", null=True, blank=True)
    met_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrado por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "critério verificado na atividade"
        verbose_name_plural = "critérios verificados na atividade"
        ordering = ["activity", "process_criterion__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "process_criterion"], name="unique_criterion_check_per_activity"
            ),
        ]

    def __str__(self):
        return f"{self.process_criterion}: {'atendido' if self.is_met else 'pendente'}"
