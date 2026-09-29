from django.db import models, transaction

from .colors import DEFAULTS, is_valid_palette_color, valid_codes_for
from .models import ActivityStage, Client, Company, CostCenter, EnumColor, Sector, Site, Tag, TaskStage, WorkflowStatus


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


class ClientService(SimpleCadastroService):
    model = Client


class TagService(SimpleCadastroService):
    model = Tag


class TaskStageService(SimpleCadastroService):
    """Estágios de Kanban de tarefa (cadastro configurável por organização).

    `order` nunca é digitado — nasce no fim da lista e só muda via `reorder`,
    chamado pelo drag-and-drop da tela de cadastro.
    """

    model = TaskStage

    @classmethod
    @transaction.atomic
    def create(cls, organization, name, created_by=None, **extra):
        last_order = cls.model.objects.filter(organization=organization).aggregate(models.Max("order"))[
            "order__max"
        ] or 0
        extra.setdefault("order", last_order + 1)
        extra.setdefault("created_by", created_by)
        return super().create(organization, name, **extra)

    @classmethod
    @transaction.atomic
    def reorder(cls, organization, ordered_ids):
        """Recebe a lista completa de IDs de TaskStage na nova ordem e
        renumera 1..N. Ignora IDs que não pertencem à organização (defesa
        contra manipulação do payload)."""
        stages = {s.pk: s for s in cls.model.objects.filter(organization=organization, pk__in=ordered_ids)}
        for position, stage_id in enumerate(ordered_ids, start=1):
            stage = stages.get(stage_id)
            if stage and stage.order != position:
                stage.order = position
                stage.save(update_fields=["order"])


class ActivityStageService(SimpleCadastroService):
    model = ActivityStage

    @classmethod
    @transaction.atomic
    def create(cls, organization, name, created_by=None, **extra):
        last_order = cls.model.objects.filter(organization=organization).aggregate(models.Max("order"))[
            "order__max"
        ] or 0
        extra.setdefault("order", last_order + 1)
        extra.setdefault("created_by", created_by)
        return super().create(organization, name, **extra)

    @classmethod
    @transaction.atomic
    def reorder(cls, organization, ordered_ids):
        stages = {s.pk: s for s in cls.model.objects.filter(organization=organization, pk__in=ordered_ids)}
        for position, stage_id in enumerate(ordered_ids, start=1):
            stage = stages.get(stage_id)
            if stage and stage.order != position:
                stage.order = position
                stage.save(update_fields=["order"])


class WorkflowStatusService(SimpleCadastroService):
    model = WorkflowStatus

    @classmethod
    @transaction.atomic
    def create(cls, organization, name, domain, behavior, created_by=None, description="", color="#94A3B8"):
        name = (name or "").strip()
        if not name:
            raise CadastroError("Informe o nome.")
        color_domain = "activity_status" if domain == WorkflowStatus.Domain.ACTIVITY else "task_status"
        if behavior not in valid_codes_for(color_domain):
            raise CadastroError("Escolha um comportamento base valido.")
        if not is_valid_palette_color(color):
            raise CadastroError("Escolha uma cor da paleta oficial.")
        if cls.model.objects.filter(organization=organization, domain=domain, name__iexact=name).exists():
            raise CadastroError(f"Ja existe um status com o nome \"{name}\" nesta organizacao.")
        return cls.model.objects.create(
            organization=organization,
            domain=domain,
            name=name,
            description=description,
            behavior=behavior,
            color=color,
            created_by=created_by,
        )

    @classmethod
    @transaction.atomic
    def update(cls, instance, name=None, description=None, behavior=None, color=None, **extra):
        fields = []
        if name is not None:
            name = name.strip()
            if not name:
                raise CadastroError("Informe o nome.")
            queryset = cls.model.objects.filter(
                organization=instance.organization, domain=instance.domain, name__iexact=name
            ).exclude(pk=instance.pk)
            if queryset.exists():
                raise CadastroError(f"Ja existe um status com o nome \"{name}\" nesta organizacao.")
            instance.name = name
            fields.append("name")
        if description is not None:
            instance.description = description
            fields.append("description")
        if behavior is not None:
            color_domain = "activity_status" if instance.domain == WorkflowStatus.Domain.ACTIVITY else "task_status"
            if behavior not in valid_codes_for(color_domain):
                raise CadastroError("Escolha um comportamento base valido.")
            instance.behavior = behavior
            fields.append("behavior")
        if color is not None:
            if not is_valid_palette_color(color):
                raise CadastroError("Escolha uma cor da paleta oficial.")
            instance.color = color
            fields.append("color")
        if fields:
            instance.save(update_fields=fields)
        return instance


class EnumColorService:
    """Cor visual configurável por organização para os enums fixos
    (Activity.status, Task.status, Activity.urgency). A tabela EnumColor só
    guarda o hex — o código nunca muda de significado, e o nome exibido
    continua vindo de get_FOO_display() no Python."""

    @staticmethod
    def get_color(organization, domain, code):
        override = (
            EnumColor.objects.filter(organization=organization, domain=domain, code=code)
            .values_list("color", flat=True)
            .first()
        )
        return override or DEFAULTS.get(domain, {}).get(code, "#94A3B8")

    @staticmethod
    @transaction.atomic
    def set_color(organization, domain, code, color, updated_by=None):
        if code not in valid_codes_for(domain):
            raise CadastroError(f"Código “{code}” não existe no domínio “{domain}”.")
        if not is_valid_palette_color(color):
            raise CadastroError("Escolha uma cor da paleta oficial.")
        obj, _created = EnumColor.objects.update_or_create(
            organization=organization,
            domain=domain,
            code=code,
            defaults={"color": color, "updated_by": updated_by},
        )
        return obj

    @staticmethod
    @transaction.atomic
    def reset_to_defaults(organization, domain=None):
        """Ação "Restaurar cores padrão LPS": apaga as customizações — a
        resolução volta a cair no default automaticamente, sem precisar
        recriar linhas com os hex padrão."""
        queryset = EnumColor.objects.filter(organization=organization)
        if domain is not None:
            queryset = queryset.filter(domain=domain)
        return queryset.delete()

    @staticmethod
    def list_for_domain(organization, domain):
        """Todos os codes do domínio com a cor atualmente efetiva
        (customizada ou default) — usado para popular a tela de
        configuração."""
        overrides = dict(
            EnumColor.objects.filter(organization=organization, domain=domain).values_list("code", "color")
        )
        return {code: overrides.get(code, default_hex) for code, default_hex in DEFAULTS.get(domain, {}).items()}

    @staticmethod
    def get_overrides(organization, domain, code):
        """(label, description, is_hidden) customizados pela organização
        para este code — vazios/False quando não há override."""
        row = EnumColor.objects.filter(organization=organization, domain=domain, code=code).first()
        if row is None:
            return "", "", False
        return row.label, row.description, row.is_hidden

    @staticmethod
    @transaction.atomic
    def set_overrides(organization, domain, code, *, label="", description="", is_hidden=False, updated_by=None):
        """Grava nome/descrição exibidos e o estado oculto de um status
        nativo, preservando a cor já customizada (ou o default) na mesma
        linha. Nunca move nem remove o `code`, que continua sendo o valor
        real gravado em Activity.status/Task.status."""
        if code not in valid_codes_for(domain):
            raise CadastroError(f"Código \"{code}\" não existe no domínio \"{domain}\".")
        label = (label or "").strip()
        description = (description or "").strip()
        existing_color = (
            EnumColor.objects.filter(organization=organization, domain=domain, code=code)
            .values_list("color", flat=True)
            .first()
        )
        obj, _created = EnumColor.objects.update_or_create(
            organization=organization,
            domain=domain,
            code=code,
            defaults={
                "color": existing_color or DEFAULTS.get(domain, {}).get(code, "#94A3B8"),
                "label": label,
                "description": description,
                "is_hidden": is_hidden,
                "updated_by": updated_by,
            },
        )
        return obj

    @staticmethod
    def list_overrides_for_domain(organization, domain):
        """{code: {"label":..., "description":..., "is_hidden":...}} —
        usado para popular a tela de configuração junto com list_for_domain."""
        rows = EnumColor.objects.filter(organization=organization, domain=domain).values_list(
            "code", "label", "description", "is_hidden"
        )
        return {code: {"label": label, "description": description, "is_hidden": is_hidden} for code, label, description, is_hidden in rows}


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
    """Participação operacional de um usuário em um setor (Regras 05 §8, §10).

    Participar de um setor não concede autorização: quem decide o que a pessoa
    pode fazer é o motor de acessos (Regras 08 §14).
    """

    @staticmethod
    @transaction.atomic
    def add(user, sector, role=None):
        from accounts.models import UserSector

        role = role or UserSector.Role.MEMBRO
        membership = UserSector.objects.filter(
            user=user, sector=sector, removed_at__isnull=True
        ).first()
        if membership is not None:
            if membership.role != role:
                membership.role = role
                membership.save(update_fields=["role"])
            return membership

        # Entrar de novo abre um novo período; o anterior continua no histórico.
        return UserSector.objects.create(user=user, sector=sector, role=role)

    @staticmethod
    @transaction.atomic
    def set_role(user, sector, role):
        from accounts.models import UserSector

        membership = UserSector.objects.filter(
            user=user, sector=sector, removed_at__isnull=True
        ).first()
        if membership is None:
            raise CadastroError("Este usuário não participa deste setor.")
        membership.role = role
        membership.save(update_fields=["role"])
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
