from django.conf import settings
from django.db import models


class Organization(models.Model):
    """Ambiente principal de um cliente da LPS (tenant). Isola dados entre clientes."""

    name = models.CharField("nome", max_length=150, unique=True)
    is_active = models.BooleanField("ativa", default=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)

    class Meta:
        verbose_name = "organização"
        verbose_name_plural = "organizações"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Company(models.Model):
    """Empresa operacional dentro de uma organização (Regras 05 §9)."""

    organization = models.ForeignKey(
        Organization, verbose_name="organização", on_delete=models.CASCADE, related_name="companies"
    )
    name = models.CharField("nome", max_length=150)
    document = models.CharField("CNPJ/CPF", max_length=20, blank=True)
    is_active = models.BooleanField("ativa", default=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_company_name_per_org"),
        ]

    def __str__(self):
        return self.name


class Sector(models.Model):
    """Setor configurável por organização (Regras 05 §18-23). Nunca fixo no código."""

    organization = models.ForeignKey(
        Organization, verbose_name="organização", on_delete=models.CASCADE, related_name="sectors"
    )
    name = models.CharField("nome", max_length=150)
    description = models.CharField("descrição", max_length=255, blank=True)
    is_active = models.BooleanField("ativo", default=True)
    created_by = models.ForeignKey(
        "auth.User", verbose_name="criado por", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "setor"
        verbose_name_plural = "setores"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_sector_name_per_org"),
        ]

    def __str__(self):
        return self.name


class TaskStage(models.Model):
    """Estágio de Kanban configurável por organização — cópia do Kanban do
    Odoo (project.task.type): coluna livre, sem regra de negócio por trás.
    Não confundir com Task.status, que continua orientando fila, bloqueio e
    timer exatamente como hoje; stage é só uma camada visual."""

    organization = models.ForeignKey(
        Organization, verbose_name="organização", on_delete=models.CASCADE, related_name="task_stages"
    )
    name = models.CharField("nome", max_length=150)
    order = models.PositiveIntegerField("ordem", default=1)
    color = models.CharField(
        "cor",
        max_length=7,
        default="#94A3B8",
        help_text="Só decoração da coluna do Kanban — nunca afeta o status operacional da tarefa.",
    )
    is_active = models.BooleanField("ativo", default=True)
    created_by = models.ForeignKey(
        "auth.User", verbose_name="criado por", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "estágio de tarefa"
        verbose_name_plural = "estágios de tarefa"
        ordering = ["organization", "order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_taskstage_name_per_org"),
        ]

    def __str__(self):
        return self.name

    @property
    def text_color(self):
        from .colors import get_contrast_text

        return get_contrast_text(self.color)


class ActivityStage(models.Model):
    """Estagio visual configuravel para atividades.

    Assim como TaskStage, organiza a visualizacao e nunca substitui
    Activity.status, que continua sendo a verdade operacional.
    """

    organization = models.ForeignKey(
        Organization, verbose_name="organizacao", on_delete=models.CASCADE, related_name="activity_stages"
    )
    name = models.CharField("nome", max_length=150)
    order = models.PositiveIntegerField("ordem", default=1)
    color = models.CharField(
        "cor",
        max_length=7,
        default="#94A3B8",
        help_text="So decoracao do fluxo visual; nunca afeta o status operacional da atividade.",
    )
    is_active = models.BooleanField("ativo", default=True)
    created_by = models.ForeignKey(
        "auth.User", verbose_name="criado por", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "estagio de atividade"
        verbose_name_plural = "estagios de atividade"
        ordering = ["organization", "order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_activitystage_name_per_org"),
        ]

    def __str__(self):
        return self.name

    @property
    def text_color(self):
        from .colors import get_contrast_text

        return get_contrast_text(self.color)


class WorkflowStatus(models.Model):
    """Status configuravel exibido no editor de fluxo.

    Os status nativos continuam no codigo porque carregam regras internas.
    Status criados pela organizacao informam qual comportamento nativo devem
    seguir quando forem usados por telas futuras.
    """

    class Domain(models.TextChoices):
        ACTIVITY = "activity", "Atividade"
        TASK = "task", "Tarefa"

    organization = models.ForeignKey(
        Organization, verbose_name="organizacao", on_delete=models.CASCADE, related_name="workflow_statuses"
    )
    domain = models.CharField("tipo", max_length=12, choices=Domain.choices)
    name = models.CharField("nome", max_length=150)
    description = models.CharField("descricao", max_length=255, blank=True)
    behavior = models.CharField(
        "comportamento base",
        max_length=32,
        help_text="Codigo operacional que este status visual segue.",
    )
    color = models.CharField("cor", max_length=7, default="#94A3B8")
    is_active = models.BooleanField("ativo", default=True)
    created_by = models.ForeignKey(
        "auth.User", verbose_name="criado por", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "status configuravel"
        verbose_name_plural = "status configuraveis"
        ordering = ["organization", "domain", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "domain", "name"], name="unique_workflowstatus_name_per_org_domain"),
        ]

    def __str__(self):
        return self.name

    @property
    def text_color(self):
        from .colors import get_contrast_text

        return get_contrast_text(self.color)


class Tag(models.Model):
    """Marcador livre, configurável por organização — cópia do
    `project.tags` do Odoo: nome único à organização, sem vínculo fixo a
    Activity ou Task específica, puramente informativo/de busca.

    A cor é hex livre (paleta oficial de 36 cores, ver core/colors.py) desde
    que migrou da paleta fixa de 7 cores numeradas."""

    organization = models.ForeignKey(
        Organization, verbose_name="organização", on_delete=models.CASCADE, related_name="tags"
    )
    name = models.CharField("nome", max_length=80)
    color = models.CharField("cor", max_length=7, default="#94A3B8")
    is_active = models.BooleanField("ativo", default=True)
    created_by = models.ForeignKey(
        "auth.User", verbose_name="criado por", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "marcador"
        verbose_name_plural = "marcadores"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_tag_name_per_org"),
        ]

    def __str__(self):
        return self.name

    @property
    def text_color(self):
        from .colors import get_contrast_text

        return get_contrast_text(self.color)


class Site(models.Model):
    """Obra (Regras 10 §11). Opcional na atividade."""

    organization = models.ForeignKey(
        Organization, verbose_name="organização", on_delete=models.CASCADE, related_name="sites"
    )
    client = models.ForeignKey(
        "Client", verbose_name="cliente", null=True, blank=True, on_delete=models.SET_NULL, related_name="sites"
    )
    name = models.CharField("nome", max_length=150)
    is_active = models.BooleanField("ativa", default=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)

    class Meta:
        verbose_name = "obra"
        verbose_name_plural = "obras"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Client(models.Model):
    """Cliente da organização — pessoa física ou jurídica que solicita a atividade.

    Distinto de `Company` (empresa operacional da própria organização, usada
    para separar contratos/unidades internas): o cliente é quem pede o
    serviço, e uma atividade pode ou não ter um associado.
    """

    organization = models.ForeignKey(
        Organization, verbose_name="organização", on_delete=models.CASCADE, related_name="clients"
    )
    name = models.CharField("nome", max_length=150)
    document = models.CharField("CNPJ/CPF", max_length=20, blank=True)
    phone = models.CharField("telefone", max_length=30, blank=True)
    email = models.EmailField("e-mail", blank=True)
    address = models.CharField("endereço", max_length=255, blank=True)
    is_active = models.BooleanField("ativo", default=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_client_name_per_org"),
        ]

    def __str__(self):
        return self.name


class CostCenter(models.Model):
    """Centro de custo (Regras 10 §11). Opcional; pode estar ligado a uma obra."""

    organization = models.ForeignKey(
        Organization, verbose_name="organização", on_delete=models.CASCADE, related_name="cost_centers"
    )
    site = models.ForeignKey(
        Site, verbose_name="obra", null=True, blank=True, on_delete=models.SET_NULL, related_name="cost_centers"
    )
    name = models.CharField("nome", max_length=150)
    is_active = models.BooleanField("ativo", default=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "centro de custo"
        verbose_name_plural = "centros de custo"
        ordering = ["name"]

    def __str__(self):
        return self.name


class EnumColor(models.Model):
    """Aparência e rótulos configuráveis por organização para um código de
    enum fixo (Activity.Status, Task.Status, Activity.Urgency).

    O código nunca muda de significado nem de comportamento — `code` não tem
    FK: é validado no service contra o vocabulário real do TextChoices,
    nunca contra um cadastro editável. `label`/`description` vazios e
    `is_hidden=False` significam "sem override": a tela cai no
    get_FOO_display() nativo (ou no dict de meta hardcoded). `is_hidden`
    apenas remove o código das opções oferecidas dali para frente — itens
    que já têm esse status continuam exibindo o rótulo normalmente.
    """

    class Domain(models.TextChoices):
        ACTIVITY_STATUS = "activity_status", "Status da atividade"
        TASK_STATUS = "task_status", "Status da tarefa"
        ACTIVITY_URGENCY = "activity_urgency", "Prioridade da atividade"

    organization = models.ForeignKey(
        Organization, verbose_name="organização", on_delete=models.CASCADE, related_name="enum_colors"
    )
    domain = models.CharField("domínio", max_length=32, choices=Domain.choices)
    code = models.CharField("código", max_length=32)
    color = models.CharField("cor", max_length=7)
    label = models.CharField("nome exibido", max_length=100, blank=True)
    description = models.CharField("descrição", max_length=255, blank=True)
    is_hidden = models.BooleanField("oculto", default=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="alterado por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_at = models.DateTimeField("alterado em", auto_now=True)

    class Meta:
        verbose_name = "cor de status/prioridade"
        verbose_name_plural = "cores de status/prioridade"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "domain", "code"], name="unique_enumcolor_per_org_domain_code"
            ),
        ]

    def __str__(self):
        return f"{self.organization} · {self.domain} · {self.code} = {self.color}"
