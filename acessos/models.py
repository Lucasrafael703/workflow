from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ActionGroup(models.Model):
    """Organiza ações para a administração (Regras 08 §18).

    Grupo nunca concede acesso por si só — existe para a interface.
    """

    key = models.SlugField("chave", max_length=50, unique=True)
    name = models.CharField("nome", max_length=100)
    description = models.CharField("descrição", max_length=255, blank=True)
    order = models.PositiveIntegerField("ordem", default=0)
    is_active = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "grupo de ações"
        verbose_name_plural = "grupos de ações"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Action(models.Model):
    """Catálogo atômico das capacidades reais da LPS (Regras 08 §19).

    A ação existe porque a aplicação possui comportamento correspondente: a
    organização combina ações em perfis, mas não inventa ações novas (§14 do
    doc 05). Por isso o catálogo é semeado pelo produto, não pelo cliente.
    """

    group = models.ForeignKey(
        ActionGroup, verbose_name="grupo", on_delete=models.PROTECT, related_name="actions"
    )
    key = models.CharField("chave", max_length=80, unique=True, help_text="Ex.: fila.reordenar")
    name = models.CharField("nome", max_length=120)
    description = models.CharField("descrição", max_length=255)
    is_sensitive = models.BooleanField(
        "sensível",
        default=False,
        help_text="Orienta confirmação na interface e auditoria reforçada; não concede nem remove acesso.",
    )
    is_active = models.BooleanField("ativo", default=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)

    class Meta:
        verbose_name = "ação"
        verbose_name_plural = "ações"
        ordering = ["group__order", "key"]
        indexes = [models.Index(fields=["group", "is_active"])]

    def __str__(self):
        return self.name


class Profile(models.Model):
    """Conjunto reutilizável de ações, configurável pela organização (Regras 08 §20)."""

    organization = models.ForeignKey(
        "core.Organization", verbose_name="organização", on_delete=models.CASCADE, related_name="profiles"
    )
    name = models.CharField("nome", max_length=120)
    description = models.CharField("descrição", max_length=255, blank=True)
    is_active = models.BooleanField("ativo", default=True)
    actions = models.ManyToManyField(
        Action, through="ProfileAction", verbose_name="ações", related_name="profiles"
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="criado por", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "perfil de acesso"
        verbose_name_plural = "perfis de acesso"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_profile_name_per_org"),
        ]
        indexes = [models.Index(fields=["organization", "is_active"])]

    def __str__(self):
        return self.name


class ProfileAction(models.Model):
    """Ação marcada em um perfil (Regras 08 §21). Marcar insere, desmarcar remove."""

    profile = models.ForeignKey(Profile, verbose_name="perfil", on_delete=models.CASCADE, related_name="profile_actions")
    action = models.ForeignKey(Action, verbose_name="ação", on_delete=models.CASCADE, related_name="profile_actions")
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="criada por", null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "ação do perfil"
        verbose_name_plural = "ações do perfil"
        constraints = [
            models.UniqueConstraint(fields=["profile", "action"], name="unique_action_per_profile"),
        ]

    def __str__(self):
        return f"{self.profile} — {self.action}"


class Scope(models.Model):
    """Onde uma concessão é válida (Regras 08 §22, doc 05 §16-22).

    Empresa, setor, obra e centro de custo não são motores separados: são
    tipos deste mesmo escopo (doc 05 §46, doc 08 §17).
    """

    class Type(models.TextChoices):
        ORGANIZACAO = "ORGANIZACAO", "Organização inteira"
        EMPRESA = "EMPRESA", "Empresa"
        SETOR = "SETOR", "Setor"
        OBRA = "OBRA", "Obra"
        CENTRO_CUSTO = "CENTRO_CUSTO", "Centro de custo"
        RELACIONAL = "RELACIONAL", "Relação com o objeto"

    class Relation(models.TextChoices):
        MINHAS_ATIVIDADES = "MINHAS_ATIVIDADES", "Atividades das quais sou dono"
        MINHAS_TAREFAS = "MINHAS_TAREFAS", "Tarefas atribuídas a mim"
        MEUS_SETORES = "MEUS_SETORES", "Setores dos quais participo"
        SETORES_GERENCIADOS = "SETORES_GERENCIADOS", "Setores que gerencio"

    organization = models.ForeignKey(
        "core.Organization", verbose_name="organização", on_delete=models.CASCADE, related_name="scopes"
    )
    type = models.CharField("tipo", max_length=14, choices=Type.choices)

    company = models.ForeignKey(
        "core.Company", verbose_name="empresa", null=True, blank=True, on_delete=models.CASCADE, related_name="scopes"
    )
    sector = models.ForeignKey(
        "core.Sector", verbose_name="setor", null=True, blank=True, on_delete=models.CASCADE, related_name="scopes"
    )
    site = models.ForeignKey(
        "core.Site", verbose_name="obra", null=True, blank=True, on_delete=models.CASCADE, related_name="scopes"
    )
    cost_center = models.ForeignKey(
        "core.CostCenter",
        verbose_name="centro de custo",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="scopes",
    )
    relation = models.CharField(
        "relação", max_length=24, choices=Relation.choices, blank=True
    )

    is_active = models.BooleanField("ativo", default=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "escopo"
        verbose_name_plural = "escopos"
        ordering = ["type"]
        indexes = [models.Index(fields=["organization", "type"])]

    def __str__(self):
        return self.label

    @property
    def label(self):
        """Leitura humana, usada para explicar a origem de uma permissão."""
        if self.type == self.Type.ORGANIZACAO:
            return "Organização inteira"
        if self.type == self.Type.EMPRESA and self.company:
            return f"Empresa {self.company.name}"
        if self.type == self.Type.SETOR and self.sector:
            return f"Setor {self.sector.name}"
        if self.type == self.Type.OBRA and self.site:
            return f"Obra {self.site.name}"
        if self.type == self.Type.CENTRO_CUSTO and self.cost_center:
            return f"Centro de custo {self.cost_center.name}"
        if self.type == self.Type.RELACIONAL:
            return self.get_relation_display()
        return self.get_type_display()

    # O banco precisa validar coerência entre tipo e campos preenchidos
    # (Regras 08 §22): um escopo de setor sem setor não significa nada.
    REQUIRED_FIELD_BY_TYPE = {
        Type.EMPRESA: "company",
        Type.SETOR: "sector",
        Type.OBRA: "site",
        Type.CENTRO_CUSTO: "cost_center",
        Type.RELACIONAL: "relation",
    }

    def clean(self):
        required = self.REQUIRED_FIELD_BY_TYPE.get(self.type)
        if required and not getattr(self, required, None):
            raise ValidationError({required: "Obrigatório para este tipo de escopo."})

        for scope_type, field in self.REQUIRED_FIELD_BY_TYPE.items():
            if scope_type != self.type and getattr(self, field, None):
                raise ValidationError({field: "Não se aplica a este tipo de escopo."})

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)


class UserProfile(models.Model):
    """Atribui um perfil a um usuário dentro de um escopo (Regras 08 §24).

    O escopo é obrigatório: uma capacidade sem "onde" é ambígua (doc 05 §54).
    """

    organization = models.ForeignKey(
        "core.Organization", verbose_name="organização", on_delete=models.CASCADE, related_name="user_profiles"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="usuário", on_delete=models.CASCADE, related_name="access_profiles"
    )
    profile = models.ForeignKey(Profile, verbose_name="perfil", on_delete=models.CASCADE, related_name="assignments")
    scope = models.ForeignKey(Scope, verbose_name="escopo", on_delete=models.PROTECT, related_name="user_profiles")
    is_active = models.BooleanField("ativo", default=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="criada por", null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "perfil do usuário"
        verbose_name_plural = "perfis do usuário"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "profile", "scope"],
                condition=models.Q(is_active=True),
                name="unique_active_user_profile_scope",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["profile", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.profile} em {self.scope.label}"


class UserAction(models.Model):
    """Concessão direta para exceção individual (Regras 08 §26, doc 05 §27).

    No D0 representa apenas concessão positiva: sem concessão válida, nega-se
    (doc 05 §28-29). Não existe DENY explícito.
    """

    organization = models.ForeignKey(
        "core.Organization", verbose_name="organização", on_delete=models.CASCADE, related_name="user_actions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="usuário", on_delete=models.CASCADE, related_name="direct_actions"
    )
    action = models.ForeignKey(Action, verbose_name="ação", on_delete=models.CASCADE, related_name="direct_grants")
    scope = models.ForeignKey(Scope, verbose_name="escopo", on_delete=models.PROTECT, related_name="user_actions")
    is_active = models.BooleanField("ativa", default=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="criada por", null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "concessão direta"
        verbose_name_plural = "concessões diretas"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "action", "scope"],
                condition=models.Q(is_active=True),
                name="unique_active_user_action_scope",
            ),
        ]
        indexes = [models.Index(fields=["user", "is_active"])]

    def __str__(self):
        return f"{self.user} — {self.action} em {self.scope.label}"
