from django.db import transaction
from django.utils import timezone

from acessos import catalog
from acessos.services import AuthorizationError, AuthorizationService, ResourceContext

from .models import (
    Process,
    ProcessCriterion,
    ProcessInput,
    ProcessStep,
    ProcessVersion,
)


class ProcessError(Exception):
    """Levantado para qualquer operação inválida do módulo de processos.
    Views capturam esta exceção e exibem a mensagem via django.contrib.messages."""


def _require(user, action_key, resource=None):
    try:
        AuthorizationService.require(user, action_key, resource)
    except AuthorizationError as exc:
        raise ProcessError(str(exc)) from exc


def people_with_sector_members(organization, sector_ids):
    """Pessoas ativas da organização e, por setor, quem participa dele agora.

    Serve aos seletores de responsável (editor de processo e tela de aplicar):
    quem é do setor da etapa é sugerido primeiro, mas qualquer pessoa da
    organização continua elegível. Retorna `(pessoas, {setor_id: {user_id}})`.
    """
    from django.contrib.auth import get_user_model

    from accounts.models import UserSector

    people = list(
        get_user_model()
        .objects.filter(profile__organization=organization, is_active=True)
        .order_by("first_name", "username")
    )
    members = {sector_id: set() for sector_id in sector_ids}
    rows = UserSector.objects.filter(sector_id__in=list(members), removed_at__isnull=True).values_list(
        "sector_id", "user_id"
    )
    for sector_id, user_id in rows:
        members[sector_id].add(user_id)
    return people, members


def validate_default_responsavel(process, responsavel):
    """O responsável padrão de uma etapa precisa ser uma pessoa ativa da
    mesma organização do processo.

    Não exige participar do setor da etapa: a criação manual de tarefas já
    aceita como responsável qualquer pessoa da organização (a busca de
    responsável não se restringe ao setor, Regras 02), e o processo segue a
    mesma regra. O setor serve para *sugerir* pessoas no editor.
    """
    if responsavel is None:
        return
    organization_id = getattr(getattr(responsavel, "profile", None), "organization_id", None)
    if organization_id != process.organization_id:
        raise ProcessError("O responsável padrão precisa pertencer à mesma organização do processo.")
    if not responsavel.is_active:
        raise ProcessError("O responsável padrão precisa ser uma pessoa ativa.")


def _assert_unique_name(company, name, instance=None):
    queryset = Process.objects.filter(company=company, name__iexact=name.strip())
    if instance is not None:
        queryset = queryset.exclude(pk=instance.pk)
    if queryset.exists():
        raise ProcessError(f"Já existe um processo com o nome “{name.strip()}” nesta empresa.")


class ProcessService:
    """Ciclo de vida do processo e de sua versão em rascunho (Regras 11 §17-19)."""

    @staticmethod
    @transaction.atomic
    def create(organization, company, name, created_by, description="", activity_type=None):
        _require(
            created_by,
            catalog.PROCESSO_CRIAR,
            ResourceContext.for_new(organization, company=company),
        )
        name = (name or "").strip()
        if not name:
            raise ProcessError("Informe o nome do processo.")
        _assert_unique_name(company, name)

        process = Process.objects.create(
            organization=organization,
            company=company,
            activity_type=activity_type,
            name=name,
            description=description,
            created_by=created_by,
        )
        version = ProcessVersion.objects.create(process=process, number=1, created_by=created_by)
        return process, version

    @staticmethod
    @transaction.atomic
    def create_new_version(process, user):
        """Abre um rascunho a partir da versão publicada, sem alterar atividades em andamento (§18)."""
        _require(user, catalog.PROCESSO_CRIAR_VERSAO, ResourceContext(organization_id=process.organization_id, company_id=process.company_id))
        if process.draft_version is not None:
            raise ProcessError("Já existe um rascunho em aberto para este processo.")
        base = process.published_version
        next_number = (base.number if base else 0) + 1
        new_version = ProcessVersion.objects.create(
            process=process,
            number=next_number,
            created_by=user,
            output_description=base.output_description if base else "",
            output_evidence_type=base.output_evidence_type if base else "",
        )
        if base is not None:
            for item in base.inputs.all():
                ProcessInput.objects.create(
                    version=new_version,
                    name=item.name,
                    input_type=item.input_type,
                    is_required=item.is_required,
                    source=item.source,
                    help_text=item.help_text,
                    order=item.order,
                )
            for item in base.criteria.all():
                ProcessCriterion.objects.create(
                    version=new_version, name=item.name, is_required=item.is_required, order=item.order
                )
            for item in base.steps.all():
                ProcessStep.objects.create(
                    version=new_version,
                    sector=item.sector,
                    name=item.name,
                    order=item.order,
                    depends_on_previous=item.depends_on_previous,
                    default_responsavel=item.default_responsavel,
                )
        return new_version

    @staticmethod
    @transaction.atomic
    def update_basic_info(version, user, name=None, description=None, activity_type=None):
        process = version.process
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada. Crie uma nova versão.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=process.organization_id, company_id=process.company_id))
        if name is not None:
            name = name.strip()
            if not name:
                raise ProcessError("Informe o nome do processo.")
            _assert_unique_name(process.company, name, instance=process)
            process.name = name
        if description is not None:
            process.description = description
        if activity_type is not None or activity_type is False:
            process.activity_type = activity_type or None
        process.save()
        return process

    @staticmethod
    @transaction.atomic
    def update_output(version, user, output_description, output_evidence_type):
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada. Crie uma nova versão.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=version.process.organization_id, company_id=version.process.company_id))
        version.output_description = (output_description or "").strip()
        version.output_evidence_type = output_evidence_type or ""
        version.save(update_fields=["output_description", "output_evidence_type"])
        return version

    @staticmethod
    @transaction.atomic
    def publish(version, user):
        process = version.process
        _require(user, catalog.PROCESSO_PUBLICAR, ResourceContext(organization_id=process.organization_id, company_id=process.company_id))
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada.")
        if not version.output_description:
            raise ProcessError("Defina a entrega esperada (output) antes de publicar.")
        if not version.steps.exists():
            raise ProcessError("Defina ao menos uma etapa no fluxo padrão antes de publicar.")

        previous = process.published_version
        if previous is not None:
            previous.status = ProcessVersion.Status.SUBSTITUIDO
            previous.save(update_fields=["status"])

        version.status = ProcessVersion.Status.PUBLICADO
        version.published_by = user
        version.published_at = timezone.now()
        version.save(update_fields=["status", "published_by", "published_at"])
        return version

    @staticmethod
    @transaction.atomic
    def set_active(process, user, is_active):
        action = catalog.PROCESSO_INATIVAR
        _require(user, action, ResourceContext(organization_id=process.organization_id, company_id=process.company_id))
        process.is_active = is_active
        process.save(update_fields=["is_active"])
        return process


class ProcessInputService:
    @staticmethod
    @transaction.atomic
    def add(version, user, name, input_type, is_required=True, source="", help_text=""):
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=version.process.organization_id, company_id=version.process.company_id))
        name = (name or "").strip()
        if not name:
            raise ProcessError("Informe o nome do input.")
        next_order = (version.inputs.count() or 0) + 1
        return ProcessInput.objects.create(
            version=version, name=name, input_type=input_type, is_required=is_required, source=source,
            help_text=help_text, order=next_order,
        )

    @staticmethod
    @transaction.atomic
    def remove(process_input, user):
        version = process_input.version
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=version.process.organization_id, company_id=version.process.company_id))
        process_input.delete()

    @staticmethod
    @transaction.atomic
    def reorder(version, user, ordered_ids):
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=version.process.organization_id, company_id=version.process.company_id))
        items = {item.pk: item for item in version.inputs.all()}
        for position, item_id in enumerate(ordered_ids, start=1):
            item = items.get(item_id)
            if item is not None and item.order != position:
                item.order = position
                item.save(update_fields=["order"])


class ProcessCriterionService:
    @staticmethod
    @transaction.atomic
    def add(version, user, name, is_required=True):
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=version.process.organization_id, company_id=version.process.company_id))
        name = (name or "").strip()
        if not name:
            raise ProcessError("Informe o critério de aceite.")
        next_order = (version.criteria.count() or 0) + 1
        return ProcessCriterion.objects.create(version=version, name=name, is_required=is_required, order=next_order)

    @staticmethod
    @transaction.atomic
    def remove(criterion, user):
        version = criterion.version
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=version.process.organization_id, company_id=version.process.company_id))
        criterion.delete()

    @staticmethod
    @transaction.atomic
    def reorder(version, user, ordered_ids):
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=version.process.organization_id, company_id=version.process.company_id))
        items = {item.pk: item for item in version.criteria.all()}
        for position, item_id in enumerate(ordered_ids, start=1):
            item = items.get(item_id)
            if item is not None and item.order != position:
                item.order = position
                item.save(update_fields=["order"])


class ProcessStepService:
    @staticmethod
    @transaction.atomic
    def add(version, user, sector, name, depends_on_previous=True, default_responsavel=None):
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=version.process.organization_id, company_id=version.process.company_id))
        name = (name or "").strip()
        if not name:
            raise ProcessError("Informe o nome da etapa.")
        if sector is None:
            raise ProcessError("Selecione o setor responsável pela etapa.")
        if sector.organization_id != version.process.organization_id:
            raise ProcessError("O setor informado pertence a outra organização.")
        validate_default_responsavel(version.process, default_responsavel)
        next_order = (version.steps.count() or 0) + 1
        return ProcessStep.objects.create(
            version=version,
            sector=sector,
            name=name,
            order=next_order,
            depends_on_previous=depends_on_previous,
            default_responsavel=default_responsavel,
        )

    @staticmethod
    @transaction.atomic
    def set_default_responsavel(step, user, responsavel):
        """Define (ou limpa, com `None`) o responsável padrão de uma etapa.

        Só em rascunho: numa versão publicada o molde é imutável, e mudar quem
        responde por uma etapa mudaria o que a versão aplicada promete.
        """
        version = step.version
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada. Crie uma nova versão.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=version.process.organization_id, company_id=version.process.company_id))
        validate_default_responsavel(version.process, responsavel)
        step.default_responsavel = responsavel
        step.save(update_fields=["default_responsavel"])
        return step

    @staticmethod
    @transaction.atomic
    def remove(step, user):
        version = step.version
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=version.process.organization_id, company_id=version.process.company_id))
        step.delete()

    @staticmethod
    @transaction.atomic
    def reorder(version, user, ordered_ids):
        if not version.is_editable:
            raise ProcessError("Esta versão já foi publicada e não pode ser alterada.")
        _require(user, catalog.PROCESSO_EDITAR_RASCUNHO, ResourceContext(organization_id=version.process.organization_id, company_id=version.process.company_id))
        items = {item.pk: item for item in version.steps.all()}
        for position, item_id in enumerate(ordered_ids, start=1):
            item = items.get(item_id)
            if item is not None and item.order != position:
                item.order = position
                item.save(update_fields=["order"])
