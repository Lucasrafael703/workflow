from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="usuário", on_delete=models.CASCADE, related_name="profile"
    )
    phone = models.CharField("telefone", max_length=20, blank=True)
    area_group = models.ForeignKey(
        Group,
        verbose_name="grupo/área principal",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Usado como padrão em filtros de telas do usuário.",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfis"

    def __str__(self):
        return f"Perfil de {self.user}"
