from django.db import transaction

from .models import Company, CostCenter, Sector, Site


class CadastroError(Exception):
    """Levantado para qualquer operação inválida de cadastro.
    Views capturam esta exceção e exibem a mensagem via django.contrib.messages."""


def _assert_unique_name(model, organization, name, instance=None):
    """Impede duplicidade óbvia ignorando maiúsculas/minúsculas (Regras 05 §22).

    Nomes apenas parecidos ("Financeiro" x "Financeiro e Administrativo") são
    considerados legítimos e não são bloqueados (Regras 05 §23).
    """
    queryset = model.objects.filter(organization=organization, name__iexact=name.strip())
    if instance is not None:
        queryset = queryset.exclude(pk=instance.pk)
    if queryset.exists():
        raise CadastroError(f"Já existe um registro com o nome “{name.strip()}” nesta organização.")


class SectorService:
    @staticmethod
    @transaction.atomic
    def create(organization, name, created_by, description=""):
        name = (name or "").strip()
        if not name:
            raise CadastroError("Informe o nome do setor.")
        _assert_unique_name(Sector, organization, name)
        return Sector.objects.create(
            organization=organization, name=name, description=description, created_by=created_by
        )

    @staticmethod
    @transaction.atomic
    def update(sector, name=None, description=None):
        if name is not None:
            name = name.strip()
            if not name:
                raise CadastroError("Informe o nome do setor.")
            _assert_unique_name(Sector, sector.organization, name, instance=sector)
            sector.name = name
        if description is not None:
            sector.description = description
        sector.save(update_fields=["name", "description"])
        return sector

    @staticmethod
    def open_task_count(sector):
        """Impacto da inativação, exibido antes de confirmar (doc 09 §183)."""
        from activities.models import Task

        return Task.objects.filter(
            sector=sector,
            status__in=[
                Task.Status.DISPONIVEL,
                Task.Status.EM_FILA,
                Task.Status.EM_EXECUCAO,
                Task.Status.BLOQUEADA,
            ],
        ).count()

    @staticmethod
    @transaction.atomic
    def deactivate(sector):
        """Inativa em vez de excluir, preservando o histórico (Regras 05 §89-90)."""
        sector.is_active = False
        sector.save(update_fields=["is_active"])
        return sector

    @staticmethod
    @transaction.atomic
    def activate(sector):
        sector.is_active = True
        sector.save(update_fields=["is_active"])
        return sector


class SimpleCadastroService:
    """CRUD comum aos cadastros auxiliares de uma organização."""

    model = None

    @classmethod
    @transaction.atomic
    def create(cls, organization, name, **extra):
        name = (name or "").strip()
        if not name:
            raise CadastroError("Informe o nome.")
        _assert_unique_name(cls.model, organization, name)
        return cls.model.objects.create(organization=organization, name=name, **extra)

    @classmethod
    @transaction.atomic
    def update(cls, instance, name=None, **extra):
        fields = []
        if name is not None:
            name = name.strip()
            if not name:
                raise CadastroError("Informe o nome.")
            _assert_unique_name(cls.model, instance.organization, name, instance=instance)
            instance.name = name
            fields.append("name")
        for field, value in extra.items():
            setattr(instance, field, value)
            fields.append(field)
        instance.save(update_fields=fields)
        return instance

    @classmethod
    @transaction.atomic
    def set_active(cls, instance, is_active):
        instance.is_active = is_active
        instance.save(update_fields=["is_active"])
        return instance


class CompanyService(SimpleCadastroService):
    model = Company


class SiteService(SimpleCadastroService):
    model = Site


class CostCenterService(SimpleCadastroService):
    model = CostCenter


class ReturnReasonService(SimpleCadastroService):
    """O model é resolvido tardiamente porque vive no app `activities`,
    que por sua vez importa `core` — evita import circular."""

    @classmethod
    def _resolve_model(cls):
        from activities.models import ReturnReason

        return ReturnReason

    @classmethod
    def create(cls, organization, name, **extra):
        name = (name or "").strip()
        if not name:
            raise CadastroError("Informe o nome.")
        model = cls._resolve_model()
        _assert_unique_name(model, organization, name)
        return model.objects.create(organization=organization, name=name, **extra)

    @classmethod
    def update(cls, instance, name=None, **extra):
        if name is not None:
            name = name.strip()
            if not name:
                raise CadastroError("Informe o nome.")
            _assert_unique_name(cls._resolve_model(), instance.organization, name, instance=instance)
            instance.name = name
        for field, value in extra.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class UserSectorService:
    """Participação operacional de um usuário em um setor (Regras 05 §24-26)."""

    @staticmethod
    @transaction.atomic
    def add(user, sector):
        from accounts.models import UserSector

        membership, created = UserSector.objects.get_or_create(user=user, sector=sector)
        if not created and membership.removed_at is not None:
            # O UniqueConstraint é incondicional: reativa a linha existente
            # em vez de tentar criar uma segunda.
            membership.removed_at = None
            membership.save(update_fields=["removed_at"])
        return membership

    @staticmethod
    @transaction.atomic
    def remove(user, sector):
        from django.utils import timezone

        from accounts.models import UserSector

        membership = UserSector.objects.filter(
            user=user, sector=sector, removed_at__isnull=True
        ).first()
        if membership is None:
            raise CadastroError("Este usuário não participa deste setor.")
        membership.removed_at = timezone.now()
        membership.save(update_fields=["removed_at"])
        return membership
