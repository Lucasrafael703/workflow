"""Aplicação de um processo publicado a uma atividade, e a execução do que ele gera.

Um `ProcessVersion` publicado é um molde imutável (Regras 12 §17-19). Aplicá-lo
a uma atividade materializa, numa única transação:

    versão publicada ──► Activity.process_version   (vínculo permanente)
                     ├─► ActivityInputValue         (um por input do molde)
                     ├─► ActivityCriterionCheck     (um por critério do molde)
                     └─► Task                       (uma por etapa, ligadas por depends_on)

Depois disso o molde continua intacto: publicar a versão 2 não toca em
atividades que receberam a versão 1, e o que muda durante a execução são só
as linhas de `ActivityInputValue`/`ActivityCriterionCheck`/`Task`.

Fica em `activities` (e não em `processes`) porque quem materializa é o
domínio operacional; `processes` continua sem conhecer atividades e tarefas
além das FKs do próprio molde.

Autorização: `processo.aplicar` na atividade. Ela autoriza materializar as
tarefas de um fluxo *já publicado* em qualquer setor, sem exigir
`tarefa.criar` em cada um (Regras 05 §2057: usar o fluxo padrão não pede
permissão de editar fluxo). Não é um bypass genérico: a criação passa por
`TaskService._create_task_core`, que valida organização, setor e responsável
como qualquer outra criação, e nenhuma view a chama diretamente.
"""

import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import timezone

from acessos import catalog
from acessos.services import AuthorizationService
from audit.models import AuditLog
from audit.services import AuditService
from notifications.models import Notification
from notifications.services import NotificationService
from processes.models import (
    ActivityCriterionCheck,
    ActivityInputValue,
    ProcessInput,
    ProcessVersion,
)
from processes.services import people_with_sector_members

from .models import Activity, TaskExecutor
from .services import ActivityError, TaskService, require_action

User = get_user_model()

#: Estados em que a atividade ainda aceita receber um processo.
_CLOSED_STATUSES = (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA)

_NOTE_MAX = 500
_TEXT_MAX = 5000
_AUDIT_VALUE_MAX = 120


def _version_label(version):
    return f"{version.process.name} v{version.number}"


def _user_organization_id(user):
    return getattr(getattr(user, "profile", None), "organization_id", None)


def _person_name(user):
    return user.get_full_name() or user.get_username()


# ---------------------------------------------------------------------------
# Valores de input
# ---------------------------------------------------------------------------


def normalize_input_value(process_input, raw_value, is_received=False):
    """Valida o valor informado para um input e devolve `(valor, recebido)`.

    Tipos com conteúdo que o modelo guarda com segurança como texto —
    `TEXTO`, `DATA` (ISO), `NUMERO` (decimal) e `LINK` (http/https) — são
    validados e o input só fica "recebido" se houver valor.

    `ARQUIVO` e `SELECAO` **não** têm hoje onde guardar o conteúdo com
    segurança (não há vínculo com o mecanismo de anexos nem lista de opções no
    molde). Para eles o sistema registra apenas a confirmação de recebimento,
    com uma observação em texto livre — nunca um id de arquivo disfarçado de
    texto. A lacuna está documentada em `docs/13_PENDENCIAS_CONHECIDAS.md`.
    """
    value = (raw_value or "").strip()
    kind = process_input.input_type
    name = process_input.name

    if kind in (ProcessInput.InputType.ARQUIVO, ProcessInput.InputType.SELECAO):
        return value[:_NOTE_MAX], bool(is_received)

    if not value:
        return "", False

    if kind == ProcessInput.InputType.DATA:
        try:
            value = datetime.date.fromisoformat(value).isoformat()
        except ValueError:
            raise ActivityError(f"«{name}»: informe uma data válida.") from None
    elif kind == ProcessInput.InputType.NUMERO:
        try:
            number = Decimal(value.replace(",", "."))
        except InvalidOperation:
            raise ActivityError(f"«{name}»: informe um número válido.") from None
        if not number.is_finite():
            raise ActivityError(f"«{name}»: informe um número válido.")
        value = format(number, "f")
    elif kind == ProcessInput.InputType.LINK:
        try:
            URLValidator(schemes=["http", "https"])(value)
        except ValidationError:
            raise ActivityError(f"«{name}»: informe um link válido, começando com http:// ou https://.") from None
    else:  # TEXTO
        value = value[:_TEXT_MAX]

    return value, True


def _input_summary(process_input, value, is_received):
    """Texto curto do estado de um input, para a trilha de auditoria."""
    if not is_received:
        return "não recebido"
    if not value:
        return "recebido"
    shown = value if len(value) <= _AUDIT_VALUE_MAX else f"{value[: _AUDIT_VALUE_MAX - 1]}…"
    return f"recebido: {shown}"


# ---------------------------------------------------------------------------
# Aplicação
# ---------------------------------------------------------------------------


class ProcessApplicationService:
    @staticmethod
    def eligible_versions(activity):
        """Versões que esta atividade pode receber, prontas para a tela.

        Publicadas, de processo ativo, da mesma organização e da mesma
        empresa da atividade (Regras 08:2380 — processo e atividade são da
        mesma empresa). Atividade sem empresa não tem processo elegível.
        """
        if activity.company_id is None:
            return ProcessVersion.objects.none()
        return (
            ProcessVersion.objects.filter(
                status=ProcessVersion.Status.PUBLICADO,
                process__is_active=True,
                process__organization_id=activity.organization_id,
                process__company_id=activity.company_id,
            )
            .select_related("process", "process__company", "process__activity_type", "published_by")
            .annotate(
                step_count=Count("steps", distinct=True),
                input_count=Count("inputs", distinct=True),
                criterion_count=Count("criteria", distinct=True),
            )
            .order_by("process__name", "-number")
        )

    @staticmethod
    def can_offer(user, activity):
        """A atividade pode receber um processo *e* a pessoa pode aplicá-lo?

        Só decide o que mostrar (botão "Aplicar processo"); a verificação que
        vale é a de `apply`.
        """
        if activity.process_version_id is not None:
            return False
        if activity.status == Activity.Status.RASCUNHO or activity.status in _CLOSED_STATUSES:
            return False
        return AuthorizationService.can(user, catalog.PROCESSO_APLICAR, activity)

    @staticmethod
    def people_for_steps(organization, steps):
        """Pessoas ativas da organização e, por setor, quem participa dele.

        Alimenta os seletores de responsável: quem é do setor da etapa vem
        primeiro, as demais pessoas continuam disponíveis (a busca de
        responsável não se restringe ao setor).
        """
        return people_with_sector_members(organization, {step.sector_id for step in steps})

    # -- validação (sem gravar nada) ---------------------------------------

    @staticmethod
    def _validate(user, activity, process_version):
        if not getattr(user, "is_authenticated", False):
            raise ActivityError("Entre no sistema para aplicar um processo.")
        if _user_organization_id(user) != activity.organization_id:
            raise ActivityError("Você não pertence à organização desta demanda.")

        process = process_version.process
        if process.organization_id != activity.organization_id:
            raise ActivityError("Este processo pertence a outra organização.")
        if not process.is_active:
            raise ActivityError("Este processo está inativo e não pode ser aplicado.")
        if process_version.status != ProcessVersion.Status.PUBLICADO:
            raise ActivityError("Só é possível aplicar uma versão publicada do processo.")
        if activity.process_version_id is not None:
            raise ActivityError("Esta demanda já tem um processo aplicado.")
        if activity.status == Activity.Status.RASCUNHO:
            raise ActivityError("Conclua a criação da demanda antes de aplicar um processo.")
        if activity.status in _CLOSED_STATUSES:
            raise ActivityError("Não é possível aplicar um processo a uma demanda concluída ou cancelada.")
        if activity.company_id is None:
            raise ActivityError(
                "Defina a empresa da demanda antes de aplicar um processo: cada processo pertence a uma empresa."
            )
        if activity.company_id != process.company_id:
            raise ActivityError(
                f"O processo «{process.name}» pertence a {process.company.name}, "
                "que não é a empresa desta demanda."
            )

    @staticmethod
    def _resolve_responsibles(activity, steps, responsible_by_step):
        """Responsável de cada etapa: o informado agora ou o padrão da etapa.

        Devolve `{step.pk: User}` ou levanta `ActivityError` listando todas as
        etapas sem responsável válido — antes de qualquer gravação.
        """
        requested_ids = set()
        for value in responsible_by_step.values():
            if value is None or value == "":
                continue
            requested_ids.add(getattr(value, "pk", value))
        try:
            candidates = {
                candidate.pk: candidate
                for candidate in User.objects.filter(
                    pk__in=requested_ids,
                    is_active=True,
                    profile__organization_id=activity.organization_id,
                ).select_related("profile")
            }
        except (TypeError, ValueError):
            raise ActivityError("Responsável inválido.") from None

        resolved = {}
        missing = []
        invalid = []
        for step in steps:
            chosen = responsible_by_step.get(step.pk)
            if chosen is not None and chosen != "":
                person = candidates.get(getattr(chosen, "pk", chosen))
                if person is None:
                    invalid.append(f"{step.order}. {step.name}")
                    continue
                resolved[step.pk] = person
                continue
            default = step.default_responsavel
            if (
                default is not None
                and default.is_active
                and _user_organization_id(default) == activity.organization_id
            ):
                resolved[step.pk] = default
            else:
                missing.append(f"{step.order}. {step.name}")

        if invalid:
            raise ActivityError(
                "O responsável escolhido não pertence a esta organização ou está inativo — etapa(s): "
                + "; ".join(invalid)
                + "."
            )
        if missing:
            raise ActivityError("Defina o responsável de cada etapa. Faltam: " + "; ".join(missing) + ".")
        return resolved

    @staticmethod
    def _resolve_inputs(process_inputs, input_values):
        """Valida os valores iniciais informados. `{input.pk: (valor, recebido)}`."""
        by_id = {item.pk: item for item in process_inputs}
        unknown = [key for key in input_values if key not in by_id]
        if unknown:
            raise ActivityError("Há um input que não pertence a esta versão do processo.")
        normalized = {}
        for pk, raw in input_values.items():
            if isinstance(raw, dict):
                raw_value, raw_received = raw.get("value", ""), raw.get("is_received", False)
            else:
                raw_value, raw_received = raw, False
            normalized[pk] = normalize_input_value(by_id[pk], raw_value, raw_received)
        return normalized

    # -- aplicação -----------------------------------------------------------

    @staticmethod
    def apply(user, activity, process_version, responsible_by_step=None, input_values=None):
        """Aplica `process_version` a `activity`. Tudo ou nada.

        `responsible_by_step`: `{ProcessStep.pk: User ou pk}` — sobrepõe o
        responsável padrão da etapa; etapa sem padrão e sem valor aqui
        impede a aplicação.
        `input_values`: `{ProcessInput.pk: valor}` ou
        `{ProcessInput.pk: {"value": ..., "is_received": bool}}` — inputs
        conhecidos já na aplicação. Os demais nascem "não recebidos".

        Idempotente do ponto de vista dos dados: a atividade é travada e relida
        dentro da transação, a segunda chamada vê `process_version` preenchido
        e é recusada, e a constraint (atividade, etapa) é a rede de segurança.
        """
        require_action(user, catalog.PROCESSO_APLICAR, activity)
        try:
            with transaction.atomic():
                applied = ProcessApplicationService._apply_locked(
                    user, activity, process_version, responsible_by_step or {}, input_values or {}
                )
        except IntegrityError:
            raise ActivityError("Este processo já foi aplicado a esta demanda.") from None
        # Quem chamou segurou uma cópia anterior da atividade; deixa-a coerente.
        activity.process_version = applied.process_version
        return applied

    @staticmethod
    def _apply_locked(user, activity, process_version, responsible_by_step, input_values):
        # Trava a atividade e relê: duas abas / clique duplo não geram tarefas
        # duplicadas, e o estado validado é o estado que vai ser gravado.
        # `of=("self",)`: no PostgreSQL, travar também o lado opcional de um
        # JOIN (company/owner são nuláveis) é erro; aqui só a atividade importa.
        activity = (
            Activity.objects.select_for_update(of=("self",))
            .select_related("organization", "company", "owner")
            .get(pk=activity.pk)
        )
        process_version = ProcessVersion.objects.select_related("process", "process__company").get(
            pk=process_version.pk
        )
        ProcessApplicationService._validate(user, activity, process_version)

        steps = list(
            process_version.steps.select_related("sector", "default_responsavel", "default_responsavel__profile").order_by(
                "order", "pk"
            )
        )
        if not steps:
            raise ActivityError("Esta versão do processo não tem etapas para aplicar.")
        for step in steps:
            if step.sector.organization_id != activity.organization_id or not step.sector.is_active:
                raise ActivityError(
                    f"O setor «{step.sector.name}» da etapa «{step.name}» está inativo ou não pertence a esta organização."
                )
        process_inputs = list(process_version.inputs.order_by("order", "pk"))
        process_criteria = list(process_version.criteria.order_by("order", "pk"))

        responsibles = ProcessApplicationService._resolve_responsibles(activity, steps, responsible_by_step)
        initial_inputs = ProcessApplicationService._resolve_inputs(process_inputs, input_values)

        # ---- daqui em diante só grava; qualquer falha desfaz tudo ----------
        now = timezone.now()

        activity.process_version = process_version
        activity.save(update_fields=["process_version"])

        ActivityInputValue.objects.bulk_create(
            [
                ActivityInputValue(
                    activity=activity,
                    process_input=item,
                    value=initial_inputs.get(item.pk, ("", False))[0],
                    is_received=initial_inputs.get(item.pk, ("", False))[1],
                    received_at=now if initial_inputs.get(item.pk, ("", False))[1] else None,
                    received_by=user if initial_inputs.get(item.pk, ("", False))[1] else None,
                )
                for item in process_inputs
            ]
        )
        ActivityCriterionCheck.objects.bulk_create(
            [ActivityCriterionCheck(activity=activity, process_criterion=item) for item in process_criteria]
        )

        tasks = []
        previous = None
        for step in steps:
            depends_on = previous if (step.depends_on_previous and previous is not None) else None
            task = TaskService._create_task_core(
                activity,
                step.sector,
                step.name,
                user,
                responsibles[step.pk],
                order=step.order,
                depends_on=depends_on,
                process_step=step,
                # Etapa que espera a anterior nasce criada, ligada e FORA da fila.
                enqueue=depends_on is None,
                notify=False,
            )
            tasks.append(task)
            previous = task

        label = _version_label(process_version)
        AuditService.log(
            user=user,
            action=AuditLog.Action.PROCESS_APPLIED,
            activity=activity,
            field_name="process_version",
            new_value=label,
            reason=f"{len(tasks)} etapa(s), {len(process_inputs)} input(s), {len(process_criteria)} critério(s).",
        )
        for item in process_inputs:
            value, received = initial_inputs.get(item.pk, ("", False))
            if received:
                AuditService.log(
                    user=user,
                    action=AuditLog.Action.INPUT_UPDATED,
                    activity=activity,
                    field_name=item.name[:50],
                    old_value=_input_summary(item, "", False),
                    new_value=_input_summary(item, value, True),
                )

        ProcessApplicationService._notify(user, activity, process_version, tasks)
        return activity

    @staticmethod
    def _notify(user, activity, process_version, tasks):
        """Um aviso por tarefa que já nasceu na fila; nada para as que esperam.

        Etapas que aguardam a anterior não geram "faça agora": quem é
        responsável por elas é avisado quando a etapa é liberada. O dono da
        atividade, se não foi quem aplicou, recebe um único resumo.
        """
        label = _version_label(process_version)
        queued = [task for task in tasks if task.depends_on_id is None]
        for task in queued:
            TaskService._notify_task_available(
                task,
                user,
                message=f"A tarefa '{task.title}' ({label}) está disponível no setor {task.sector.name}.",
                include_responsavel=True,
            )
        owner = activity.owner
        if owner is not None and owner.pk != user.pk:
            NotificationService.notify(
                users={owner},
                event_type=Notification.EventType.PROCESS_APPLIED,
                title="Processo aplicado à demanda",
                message=(
                    f"O processo {label} foi aplicado a '{activity.title}': {len(tasks)} tarefa(s) criada(s), "
                    f"{len(queued)} já na fila."
                )[:255],
                activity=activity,
                actor=user,
            )


# ---------------------------------------------------------------------------
# Execução: inputs e critérios de uma atividade que já recebeu o processo
# ---------------------------------------------------------------------------


class ActivityProcessService:
    """Atualiza o *resultado* de inputs e critérios numa atividade concreta.

    O molde (`ProcessInput`/`ProcessCriterion`) não muda; aqui só mudam as
    linhas da atividade. Toda alteração é auditada com quem, o quê, de qual
    estado para qual (Regras 12 §34, 08:1337).
    """

    @staticmethod
    def can_update(user, activity):
        """Quem pode registrar inputs e marcar critérios.

        Quem pode editar a atividade, o dono e quem trabalha nela (responsável
        ou participante de alguma tarefa) — o mesmo critério do checklist da
        tarefa. Nunca fora da organização, nunca em atividade encerrada.
        """
        if not getattr(user, "is_authenticated", False) or not user.is_active:
            return False
        if _user_organization_id(user) != activity.organization_id:
            return False
        if activity.status in _CLOSED_STATUSES or activity.status == Activity.Status.RASCUNHO:
            return False
        if AuthorizationService.can(user, catalog.ATIVIDADE_EDITAR, activity):
            return True
        if activity.owner_id == user.pk:
            return True
        return (
            activity.tasks.filter(responsavel=user).exists()
            or TaskExecutor.objects.filter(task__activity=activity, user=user, removed_at__isnull=True).exists()
        )

    @staticmethod
    def _assert_can_update(user, activity):
        if activity.status in _CLOSED_STATUSES:
            raise ActivityError("Esta demanda já foi finalizada e não aceita mais alterações no processo.")
        if not ActivityProcessService.can_update(user, activity):
            raise ActivityError("Você não tem permissão para atualizar o processo desta demanda.")

    @staticmethod
    @transaction.atomic
    def update_input(user, input_value, value="", is_received=False):
        """Registra (ou corrige, ou reabre) um input da atividade."""
        input_value = (
            ActivityInputValue.objects.select_for_update(of=("self",))
            .select_related("activity", "process_input")
            .get(pk=input_value.pk)
        )
        activity = input_value.activity
        ActivityProcessService._assert_can_update(user, activity)

        process_input = input_value.process_input
        new_value, new_received = normalize_input_value(process_input, value, is_received)
        if new_value == input_value.value and new_received == input_value.is_received:
            return input_value

        old_summary = _input_summary(process_input, input_value.value, input_value.is_received)
        was_received = input_value.is_received
        input_value.value = new_value
        input_value.is_received = new_received
        if new_received:
            # "Recebido em" marca a chegada; corrigir o valor depois não a muda.
            if not was_received or input_value.received_at is None:
                input_value.received_at = timezone.now()
            input_value.received_by = user
        else:
            input_value.received_at = None
            input_value.received_by = None
        input_value.save(update_fields=["value", "is_received", "received_at", "received_by"])

        AuditService.log(
            user=user,
            action=AuditLog.Action.INPUT_UPDATED,
            activity=activity,
            field_name=process_input.name[:50],
            old_value=old_summary,
            new_value=_input_summary(process_input, new_value, new_received),
        )
        return input_value

    @staticmethod
    @transaction.atomic
    def set_criterion(user, criterion_check, is_met):
        """Marca ou desmarca um critério de aceite da atividade."""
        criterion_check = (
            ActivityCriterionCheck.objects.select_for_update(of=("self",))
            .select_related("activity", "process_criterion")
            .get(pk=criterion_check.pk)
        )
        activity = criterion_check.activity
        ActivityProcessService._assert_can_update(user, activity)

        is_met = bool(is_met)
        if criterion_check.is_met == is_met:
            return criterion_check

        criterion_check.is_met = is_met
        criterion_check.met_at = timezone.now() if is_met else None
        criterion_check.met_by = user if is_met else None
        criterion_check.save(update_fields=["is_met", "met_at", "met_by"])

        met, pending = "atendido", "pendente"
        AuditService.log(
            user=user,
            action=AuditLog.Action.CRITERION_UPDATED,
            activity=activity,
            field_name=criterion_check.process_criterion.name[:50],
            old_value=pending if is_met else met,
            new_value=met if is_met else pending,
        )
        return criterion_check


__all__ = [
    "ActivityProcessService",
    "ProcessApplicationService",
    "normalize_input_value",
]
