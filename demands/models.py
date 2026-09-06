from django.conf import settings
from django.db import models
from django.utils import timezone


class Demand(models.Model):
    class Origin(models.TextChoices):
        TELEFONE = "TELEFONE", "Telefone"
        EMAIL = "EMAIL", "E-mail"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        PRESENCIAL = "PRESENCIAL", "Presencial"
        SITE = "SITE", "Site/Formulário"
        OUTRO = "OUTRO", "Outro"

    class InformationCompleteness(models.TextChoices):
        BAIXA = "BAIXA", "Baixa"
        MEDIA = "MEDIA", "Média"
        ALTA = "ALTA", "Alta"

    # --- Identificação ---
    protocol = models.CharField("protocolo", max_length=30, unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="responsável interno",
        on_delete=models.PROTECT,
        related_name="demands_created",
    )
    created_at = models.DateTimeField("data de entrada", auto_now_add=True)
    communication_channel = models.CharField(
        "canal de origem", max_length=12, choices=Origin.choices, default=Origin.OUTRO
    )

    # --- Relacionamento / partes ---
    client_name = models.CharField("empresa/cliente solicitante", max_length=200)
    client_document = models.CharField("CPF/CNPJ", max_length=20, blank=True)
    client_contact_name = models.CharField("contato solicitante", max_length=150, blank=True)
    client_contact_phone = models.CharField("telefone do contato", max_length=20, blank=True)
    client_contact_email = models.EmailField("e-mail do contato", blank=True)
    intermediary_name = models.CharField("representante/intermediário", max_length=200, blank=True)
    final_client_name = models.CharField("cliente final", max_length=200, blank=True)
    is_existing_client = models.BooleanField("já é cliente", default=False)

    # --- Obra ---
    site_name = models.CharField("empreendimento", max_length=200, blank=True)
    site_address = models.CharField("endereço da obra", max_length=255, blank=True)
    site_city = models.CharField("cidade", max_length=100, blank=True)
    site_state = models.CharField("UF", max_length=2, blank=True)
    site_type = models.CharField("tipo de obra", max_length=150, blank=True)
    site_phase = models.CharField("fase da obra", max_length=150, blank=True)

    # --- Solicitação ---
    request_summary = models.TextField("objeto solicitado")
    disciplines_requested = models.TextField("disciplinas solicitadas", blank=True)
    supply_materials = models.BooleanField("fornecimento de materiais", default=False)
    supply_labor = models.BooleanField("fornecimento de mão de obra", default=False)
    supply_equipment = models.BooleanField("fornecimento de equipamentos", default=False)
    supply_project_development = models.BooleanField("desenvolvimento de projetos", default=False)
    request_details = models.TextField("detalhes adicionais da solicitação", blank=True)

    # --- Documentação recebida ---
    documentation_received = models.TextField(
        "documentação recebida", blank=True, help_text="Projetos, memoriais, planilhas, anexos, links externos."
    )
    documentation_missing = models.TextField("documentos faltantes", blank=True)
    documentation_invalid = models.TextField("arquivos inválidos/corrompidos", blank=True)

    # --- Qualidade da informação ---
    project_level = models.CharField("nível dos projetos recebidos", max_length=150, blank=True)
    disciplines_with_project = models.TextField("disciplinas com projeto", blank=True)
    disciplines_without_project = models.TextField("disciplinas sem projeto", blank=True)
    information_completeness = models.CharField(
        "documentação completa/parcial",
        max_length=10,
        choices=InformationCompleteness.choices,
        blank=True,
    )
    conflicts_identified = models.TextField("conflitos identificados", blank=True)
    confidence_notes = models.TextField("nível de confiança da entrada", blank=True)

    # --- Prazos ---
    confirmation_deadline = models.DateTimeField("prazo para confirmar participação", null=True, blank=True)
    questions_deadline = models.DateTimeField("prazo para envio de dúvidas", null=True, blank=True)
    proposal_deadline = models.DateTimeField("prazo para a proposta", null=True, blank=True)
    expected_construction_start = models.DateField("início previsto da obra", null=True, blank=True)
    expected_execution_duration = models.CharField("prazo previsto de execução", max_length=100, blank=True)

    # --- Condições comerciais ---
    contracting_modality = models.CharField("modalidade de contratação", max_length=150, blank=True)
    payment_terms = models.CharField("forma de pagamento", max_length=200, blank=True)
    direct_billing = models.BooleanField("faturamento direto", default=False)
    retentions_notes = models.CharField("retenções", max_length=255, blank=True)
    guarantees_notes = models.CharField("garantias/seguros", max_length=255, blank=True)
    specific_taxes_notes = models.CharField("impostos específicos", max_length=255, blank=True)
    proposal_validity_days = models.PositiveIntegerField("validade da proposta (dias)", null=True, blank=True)
    price_adjustment_notes = models.CharField("reajuste", max_length=255, blank=True)

    # --- Entregáveis esperados ---
    deliverable_technical_proposal = models.BooleanField("proposta técnica", default=False)
    deliverable_commercial_proposal = models.BooleanField("proposta comercial", default=False)
    deliverable_client_spreadsheet = models.BooleanField("planilha do cliente", default=False)
    deliverable_wbs = models.BooleanField("EAP/plano de contas", default=False)
    deliverable_schedule = models.BooleanField("cronograma", default=False)
    deliverable_histogram = models.BooleanField("histograma", default=False)
    deliverable_other_notes = models.CharField("outros documentos", max_length=255, blank=True)

    # --- Comunicação ---
    reference_email = models.CharField("e-mail de referência", max_length=255, blank=True)
    verbal_information_notes = models.TextField("informações recebidas verbalmente", blank=True)
    whatsapp_information_notes = models.TextField("informações recebidas por WhatsApp", blank=True)
    technical_contact_notes = models.CharField("contato para dúvidas técnicas", max_length=255, blank=True)
    proposal_recipient = models.CharField("destinatário da proposta", max_length=255, blank=True)
    requires_intermediary_approval = models.BooleanField("necessidade de aprovação do representante", default=False)

    class Meta:
        verbose_name = "demanda"
        verbose_name_plural = "demandas"
        ordering = ["-created_at"]
        permissions = [
            ("can_qualify_demand", "Pode qualificar/decidir sobre a demanda"),
            ("can_view_all_demands", "Pode visualizar todas as demandas"),
        ]

    def __str__(self):
        return f"{self.protocol} - {self.client_name}"

    def save(self, *args, **kwargs):
        if not self.protocol:
            year = timezone.now().year
            last = (
                Demand.objects.filter(protocol__startswith=f"DEM-{year}-")
                .order_by("-protocol")
                .first()
            )
            next_seq = 1
            if last:
                next_seq = int(last.protocol.rsplit("-", 1)[-1]) + 1
            self.protocol = f"DEM-{year}-{next_seq:06d}"
        super().save(*args, **kwargs)


class DemandDecision(models.Model):
    class Decision(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        CONVERTIDA = "CONVERTIDA", "Convertida em processo"
        RECUSADA = "RECUSADA", "Recusada"
        AGUARDANDO_INFO = "AGUARDANDO_INFO", "Aguardando informações"

    demand = models.OneToOneField(Demand, verbose_name="demanda", on_delete=models.CASCADE, related_name="decision")
    status = models.CharField("decisão", max_length=16, choices=Decision.choices, default=Decision.PENDENTE)

    # --- Pendências (seção 5.11 do formulário de demanda) ---
    pending_items = models.TextField("pendências", blank=True)
    pending_impact_notes = models.TextField("impacto no orçamento", blank=True)
    pending_disciplines_affected = models.CharField("disciplina afetada", max_length=255, blank=True)

    # --- Decisão de entrada (seção 5.12) ---
    can_budget = models.BooleanField("podemos orçar?", null=True, blank=True)
    can_budget_partially = models.BooleanField("podemos orçar parcialmente?", null=True, blank=True)
    risks_notes = models.TextField("principais riscos", blank=True)
    deadline_is_viable = models.BooleanField("prazo é viável?", null=True, blank=True)
    decision_notes = models.TextField("observações da decisão", blank=True)

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="decidido por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    decided_at = models.DateTimeField("data da decisão", null=True, blank=True)

    resulting_process = models.OneToOneField(
        "workflows.Process",
        verbose_name="processo gerado",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_decision",
    )

    class Meta:
        verbose_name = "decisão de demanda"
        verbose_name_plural = "decisões de demanda"

    def __str__(self):
        return f"Decisão de {self.demand.protocol}: {self.get_status_display()}"
