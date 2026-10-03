import random
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


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
    must_change_password = models.BooleanField(
        "trocar a senha no próximo acesso",
        default=False,
        help_text="Ligado quando um administrador define uma senha provisória: a pessoa só segue depois de escolher a dela.",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfis"

    def __str__(self):
        return f"Perfil de {self.user}"


class UserSector(models.Model):
    """Participação operacional de um usuário em um setor (Regras 05 §8, §10).

    Vínculo organizacional descreve **onde a pessoa atua**; autorização define
    o que ela pode fazer. Participar de um setor — inclusive como gestor — não
    concede capacidade alguma por si só (Regras 08 §14, doc 05 §45).
    """

    class Role(models.TextChoices):
        MEMBRO = "MEMBRO", "Membro"
        GESTOR = "GESTOR", "Gestor"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="usuário", on_delete=models.CASCADE, related_name="sector_memberships"
    )
    sector = models.ForeignKey(
        "core.Sector", verbose_name="setor", on_delete=models.CASCADE, related_name="user_memberships"
    )
    role = models.CharField("papel", max_length=6, choices=Role.choices, default=Role.MEMBRO)
    joined_at = models.DateTimeField("desde", auto_now_add=True)
    removed_at = models.DateTimeField("removido em", null=True, blank=True)

    class Meta:
        verbose_name = "participação em setor"
        verbose_name_plural = "participações em setores"
        ordering = ["-joined_at"]
        constraints = [
            # Só a participação ativa é única: sair e voltar a um setor gera um
            # novo período, preservando o histórico anterior (Regras 08 §14).
            models.UniqueConstraint(
                fields=["user", "sector"],
                condition=models.Q(removed_at__isnull=True),
                name="unique_active_user_sector",
            ),
        ]

    def __str__(self):
        return f"{self.user} em {self.sector}"


class EmailVerification(models.Model):
    """Código de 6 dígitos para confirmar o e-mail no cadastro (Telas/09_03).

    Um novo código sempre substitui o anterior (mesma linha, campos
    atualizados) — assim "o código anterior é invalidado" fica automático,
    sem precisar de uma tabela de histórico.
    """

    CODE_TTL = timedelta(minutes=15)
    RESEND_COOLDOWN = timedelta(seconds=60)
    MAX_ATTEMPTS = 5

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="usuário", on_delete=models.CASCADE, related_name="email_verification"
    )
    code = models.CharField("código", max_length=6)
    created_at = models.DateTimeField("gerado em", auto_now_add=True)
    expires_at = models.DateTimeField("expira em")
    attempts = models.PositiveSmallIntegerField("tentativas", default=0)
    confirmed_at = models.DateTimeField("confirmado em", null=True, blank=True)

    class Meta:
        verbose_name = "confirmação de e-mail"
        verbose_name_plural = "confirmações de e-mail"

    def __str__(self):
        return f"Confirmação de {self.user}"

    @classmethod
    def issue(cls, user):
        """Gera (ou substitui) o código ativo do usuário e zera tentativas."""
        now = timezone.now()
        code = f"{random.randint(0, 999999):06d}"
        verification, _ = cls.objects.update_or_create(
            user=user,
            defaults={
                "code": code,
                "created_at": now,
                "expires_at": now + cls.CODE_TTL,
                "attempts": 0,
                "confirmed_at": None,
            },
        )
        return verification

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def can_resend(self):
        return timezone.now() >= self.created_at + self.RESEND_COOLDOWN

    def verify(self, code):
        """Valida o código informado; registra a tentativa mesmo quando erra."""
        if self.confirmed_at is not None:
            return True
        if self.is_expired:
            return False
        if self.attempts >= self.MAX_ATTEMPTS:
            return False
        self.attempts += 1
        if code != self.code:
            self.save(update_fields=["attempts"])
            return False
        self.confirmed_at = timezone.now()
        self.save(update_fields=["attempts", "confirmed_at"])
        return True
