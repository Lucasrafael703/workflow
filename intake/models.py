from django.conf import settings
from django.db import models
from django.utils import timezone

from . import textparse


class IntakeItem(models.Model):
    """Uma solicitação que chegou e ainda não virou (nem deixou de virar) trabalho.

    A Caixa de Entrada fica antes da Atividade: nada vira atividade sozinho,
    alguém decide. As colunas `suggested_*` guardam o que a LPS entendeu do
    texto, só como ponto de partida para quem faz a triagem.
    """

    class Source(models.TextChoices):
        EMAIL = "EMAIL", "E-mail"
        TEAMS = "TEAMS", "Teams"
        # Pedido verbal, ligação, reunião: alguém digitou o que ouviu.
        USUARIO = "USUARIO", "Pedido verbal ou conversa"
        # Reservado ao canal futuro; fora das opções do registro manual.
        FORMULARIO = "FORMULARIO", "Formulário"

    class Status(models.TextChoices):
        NOVO = "NOVO", "Nova"
        CONVERTIDO = "CONVERTIDO", "Virou demanda"
        IGNORADO = "IGNORADO", "Ignorada"

    class Confidence(models.TextChoices):
        ALTA = "ALTA", "Alta"
        MEDIA = "MEDIA", "Média"
        BAIXA = "BAIXA", "Baixa"

    organization = models.ForeignKey(
        "core.Organization",
        verbose_name="organização",
        on_delete=models.PROTECT,
        related_name="intake_items",
    )
    source = models.CharField("origem", max_length=12, choices=Source.choices, default=Source.EMAIL)
    external_id = models.CharField(
        "identificador externo",
        max_length=255,
        blank=True,
        help_text="Identificador do e-mail ou da mensagem na origem. Vazio no registro manual.",
    )
    subject = models.CharField("assunto", max_length=200, blank=True)
    sender_name = models.CharField("nome do remetente", max_length=150, blank=True)
    sender_email = models.EmailField("e-mail do remetente", blank=True)
    raw_content = models.TextField(
        "texto recebido",
        help_text="Texto puro, exatamente como chegou. Nunca é exibido como HTML.",
    )
    content_hash = models.CharField("assinatura do conteúdo", max_length=64, db_index=True, editable=False)
    received_at = models.DateTimeField("recebida em", default=timezone.now)
    status = models.CharField("situação", max_length=10, choices=Status.choices, default=Status.NOVO)

    suggested_title = models.CharField("título sugerido", max_length=200, blank=True)
    suggested_client = models.ForeignKey(
        "core.Client",
        verbose_name="cliente sugerido",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    suggested_site = models.ForeignKey(
        "core.Site",
        verbose_name="obra sugerida",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    suggested_sector = models.ForeignKey(
        "core.Sector",
        verbose_name="setor sugerido",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    suggested_deadline = models.DateTimeField("prazo sugerido", null=True, blank=True)
    confidence = models.PositiveSmallIntegerField("confiança (0 a 100)", default=0)
    suggestion_reasons = models.JSONField(
        "por que a LPS sugeriu isso",
        default=list,
        blank=True,
    )

    activity = models.OneToOneField(
        "activities.Activity",
        verbose_name="demanda criada",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="intake_item",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrada por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="intake_items_created",
    )
    created_at = models.DateTimeField("registrada no sistema em", auto_now_add=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="tratada por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    resolved_at = models.DateTimeField("tratada em", null=True, blank=True)
    resolution_note = models.CharField("motivo", max_length=255, blank=True)

    class Meta:
        verbose_name = "solicitação"
        verbose_name_plural = "solicitações"
        ordering = ["-received_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status", "-received_at"], name="intake_org_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "source", "external_id"],
                condition=~models.Q(external_id=""),
                name="unique_intake_external_id_per_source",
            ),
            models.CheckConstraint(
                condition=models.Q(confidence__gte=0, confidence__lte=100),
                name="intake_confidence_0_100",
            ),
        ]

    def __str__(self):
        return self.subject or self.excerpt(60) or f"Solicitação {self.pk}"

    @property
    def confidence_level(self):
        if self.confidence >= 70:
            return self.Confidence.ALTA
        if self.confidence >= 40:
            return self.Confidence.MEDIA
        return self.Confidence.BAIXA

    @property
    def confidence_label(self):
        return self.confidence_level.label

    @property
    def sender_display(self):
        return self.sender_name or self.sender_email or "Remetente não informado"

    @property
    def suggested_deadline_label(self):
        """"sexta, 02/10" (com o ano se não for o corrente e a hora se não for fim do dia)."""
        if not self.suggested_deadline:
            return ""
        local = timezone.localtime(self.suggested_deadline)
        label = f"{textparse.weekday_label(local)}, {local:%d/%m}"
        if local.year != timezone.localtime().year:
            label += f"/{local:%Y}"
        if (local.hour, local.minute) != (23, 59):
            label += f" às {local:%H:%M}"
        return label

    def excerpt(self, limit=240):
        """Começo do texto, em uma linha, para o cartão da lista."""
        text = " ".join((self.raw_content or "").split())
        return text if len(text) <= limit else f"{text[: limit - 1]}…"


class IntakeEvent(models.Model):
    """Trilha da própria solicitação.

    `AuditLog` só liga a Atividade e Tarefa, então o que acontece antes de a
    atividade existir (e o que acontece com a solicitação depois) fica aqui.
    """

    class Kind(models.TextChoices):
        REGISTRADA = "REGISTRADA", "Registrada"
        EDITADA = "EDITADA", "Sugestões corrigidas"
        CONVERTIDA = "CONVERTIDA", "Virou demanda"
        IGNORADA = "IGNORADA", "Ignorada"
        RESTAURADA = "RESTAURADA", "Restaurada"

    item = models.ForeignKey(
        IntakeItem,
        verbose_name="solicitação",
        on_delete=models.CASCADE,
        related_name="events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuário",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    kind = models.CharField("tipo", max_length=12, choices=Kind.choices)
    note = models.TextField("detalhe", blank=True)
    created_at = models.DateTimeField("quando", auto_now_add=True)

    class Meta:
        verbose_name = "evento da solicitação"
        verbose_name_plural = "eventos da solicitação"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.item_id}"
