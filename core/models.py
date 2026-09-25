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


class Tag(models.Model):
    """Marcador livre, configurável por organização — cópia do
    `project.tags` do Odoo: nome único à organização, sem vínculo fixo a
    Activity ou Task específica, puramente informativo/de busca."""

    class Color(models.IntegerChoices):
        CINZA = 0, "Cinza"
        AZUL = 1, "Azul"
        VERDE = 2, "Verde"
        AMARELO = 3, "Amarelo"
        LARANJA = 4, "Laranja"
        VERMELHO = 5, "Vermelho"
        ROXO = 6, "Roxo"

    organization = models.ForeignKey(
        Organization, verbose_name="organização", on_delete=models.CASCADE, related_name="tags"
    )
    name = models.CharField("nome", max_length=80)
    color = models.PositiveSmallIntegerField("cor", choices=Color.choices, default=Color.CINZA)
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


class Site(models.Model):
    """Obra (Regras 10 §11). Opcional na atividade."""

    organization = models.ForeignKey(
        Organization, verbose_name="organização", on_delete=models.CASCADE, related_name="sites"
    )
    company = models.ForeignKey(
        Company, verbose_name="empresa", null=True, blank=True, on_delete=models.SET_NULL, related_name="sites"
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
