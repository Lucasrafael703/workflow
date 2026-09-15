from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="usuário", on_delete=models.CASCADE, related_name="profile"
    )
    organization = models.ForeignKey(
        "core.Organization",
        verbose_name="organização",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="members",
        help_text="Um usuário da LPS pertence a uma única organização (Regras 05 §7).",
    )
    phone = models.CharField("telefone", max_length=20, blank=True)
    main_sector = models.ForeignKey(
        "core.Sector",
        verbose_name="setor principal",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Usado como padrão em filtros de telas do usuário (Regras 05 §29). Não limita os demais vínculos.",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfis"

    def __str__(self):
        return f"Perfil de {self.user}"


class UserSector(models.Model):
    """Participação operacional de um usuário em um setor (Regras 05 §24-26).

    Separado de Group/Permission: indica "faz parte deste setor", não "pode fazer X".
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="usuário", on_delete=models.CASCADE, related_name="sector_memberships"
    )
    sector = models.ForeignKey(
        "core.Sector", verbose_name="setor", on_delete=models.CASCADE, related_name="user_memberships"
    )
    joined_at = models.DateTimeField("desde", auto_now_add=True)
    removed_at = models.DateTimeField("removido em", null=True, blank=True)

    class Meta:
        verbose_name = "participação em setor"
        verbose_name_plural = "participações em setores"
        constraints = [
            models.UniqueConstraint(fields=["user", "sector"], name="unique_active_user_sector"),
        ]

    def __str__(self):
        return f"{self.user} em {self.sector}"
