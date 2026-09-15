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
