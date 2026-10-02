"""Adapters de leitura e mutação dos quadros de Demandas e Tarefas.

Esta é deliberadamente uma fina camada de tradução: os services de
``activities`` continuam sendo responsáveis por toda alteração operacional.
"""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from acessos import catalog
from acessos.services import AuthorizationService
from audit.models import AuditLog
from audit.services import AuditService
from core.colors import EnumColorResolver, get_contrast_text
from core.models import ActivityStage, Sector, TaskStage, WorkflowStatus

from activities.models import Activity, Task
from activities.services import ActivityError, ActivityService, TaskService

from .models import DomainBoard, DomainBoardField, DomainCustomValue


class DomainBoardError(Exception):
    pass


class DomainBoardConflict(DomainBoardError):
    pass


def _datetime_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    parsed = parse_datetime(str(value))
    if parsed is None:
        raise DomainBoardError("Informe uma data e hora válidas.")
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def _user_for_org(value, organization):
    try:
        user_id = int(value)
    except (TypeError, ValueError):
        raise DomainBoardError("Pessoa inválida.")
    User = get_user_model()
    try:
        return User.objects.select_related("profile").get(pk=user_id, profile__organization=organization, is_active=True)
    except User.DoesNotExist as exc:
        raise DomainBoardError("A pessoa escolhida não pertence à organização.") from exc


def _stage_for(item, value):
    if not value:
        return None
    klass = ActivityStage if isinstance(item, Activity) else TaskStage
    try:
        return klass.objects.get(pk=int(value), organization=item.organization if isinstance(item, Activity) else item.activity.organization)
    except (klass.DoesNotExist, TypeError, ValueError) as exc:
        raise DomainBoardError("Etapa inválida para esta demanda ou tarefa.") from exc


def _condition_for(item, value):
    if not value:
        return None
    domain = WorkflowStatus.Domain.ACTIVITY if isinstance(item, Activity) else WorkflowStatus.Domain.TASK
    organization = item.organization if isinstance(item, Activity) else item.activity.organization
    try:
        return WorkflowStatus.objects.get(pk=int(value), organization=organization, domain=domain)
    except (WorkflowStatus.DoesNotExist, TypeError, ValueError) as exc:
        raise DomainBoardError("Condição inválida para esta demanda ou tarefa.") from exc


def _sector_for(item, value):
    if not value:
        if isinstance(item, Activity):
            return None
        raise DomainBoardError("A tarefa precisa de um setor responsável.")
    organization = item.organization if isinstance(item, Activity) else item.activity.organization
    try:
        return Sector.objects.get(pk=int(value), organization=organization, is_active=True)
    except (Sector.DoesNotExist, TypeError, ValueError) as exc:
        raise DomainBoardError("Setor inválido para esta organização.") from exc


class DomainBoardMutationService:
    @staticmethod
    def _assert_version(item, expected_updated_at):
        if not expected_updated_at:
            return
        try:
            expected = parse_datetime(expected_updated_at.replace("Z", "+00:00"))
        except AttributeError:
            expected = None
        if expected is None:
            raise DomainBoardError("Versão de edição inválida.")
        if timezone.is_naive(expected):
            expected = timezone.make_aware(expected)
        # microssegundos podem se perder no atributo HTML; comparar no segundo
        # ainda evita que uma edição atrasada sobrescreva uma alteração real.
        if item.updated_at.replace(microsecond=0) != expected.replace(microsecond=0):
            raise DomainBoardConflict("Esta informação foi alterada por outra pessoa. O valor atualizado foi recarregado.")

    @staticmethod
    @transaction.atomic
    def set_value(board, field, item, raw_value, user, expected_updated_at=None):
        if field.board_id != board.id:
            raise DomainBoardError("Campo não pertence a este quadro.")
        organization = item.organization if isinstance(item, Activity) else item.activity.organization
        if organization.id != board.organization_id:
            raise DomainBoardError("Registro não pertence a esta organização.")
        DomainBoardMutationService._assert_version(item, expected_updated_at)

        key = field.key
        if key == "title":
            if isinstance(item, Activity):
                return ActivityService.update_activity(item, user, title=str(raw_value or "").strip())
            return TaskService.update_task(item, user, title=str(raw_value or "").strip())
        if key in {"requested_deadline"}:
            # Prazo solicitado nunca altera o comprometido: a negociação
            # existente continua intacta e o service preserva a auditoria.
            deadline = _datetime_value(raw_value)
            if not AuthorizationService.can(user, catalog.PRAZO_ALTERAR_SOLICITADO, item):
                raise DomainBoardError("Você não possui permissão para alterar o prazo solicitado.")
            if isinstance(item, Activity):
                return ActivityService.update_activity(item, user, requested_deadline=deadline)
            return TaskService.update_task(item, user, requested_deadline=deadline)
        if key == "owner" and isinstance(item, Activity):
            return ActivityService.change_owner(item, _user_for_org(raw_value, organization), user)
        if key == "responsavel" and isinstance(item, Task):
            return TaskService.change_responsavel(item, _user_for_org(raw_value, organization), user)
        if key == "sector":
            sector = _sector_for(item, raw_value)
            if isinstance(item, Activity):
                return ActivityService.update_activity(item, user, sector=sector)
            return TaskService.move_to_sector(item, sector, user)
        if key == "stage":
            stage = _stage_for(item, raw_value)
            return ActivityService.set_stage(item, stage, user) if isinstance(item, Activity) else TaskService.set_stage(item, stage, user)
        if key == "condition":
            condition = _condition_for(item, raw_value)
            return ActivityService.set_condition(item, condition, user) if isinstance(item, Activity) else TaskService.set_condition(item, condition, user)
        if key == "urgency" and isinstance(item, Activity):
            if raw_value not in Activity.Urgency.values:
                raise DomainBoardError("Prioridade inválida.")
            return ActivityService.update_activity(item, user, urgency=raw_value)
        if key == "priority" and isinstance(item, Task):
            return TaskService.set_priority(item, raw_value, user)
        if field.is_system:
            raise DomainBoardError("Este campo não pode ser editado diretamente.")

        action = catalog.ATIVIDADE_EDITAR if isinstance(item, Activity) else catalog.TAREFA_EDITAR
        if not AuthorizationService.can(user, action, item):
            raise DomainBoardError("Você não possui permissão para editar este item.")
        target = {"activity": item} if isinstance(item, Activity) else {"task": item}
        current, _ = DomainCustomValue.objects.get_or_create(field=field, **target, defaults={"updated_by": user})
        old_value = current.value
        current.value = {"value": raw_value}
        current.updated_by = user
        current.save(update_fields=["value", "updated_by", "updated_at"])
        AuditService.log(
            user=user, action=AuditLog.Action.UPDATE, activity=target.get("activity"), task=target.get("task"),
            field_name=f"quadro:{field.key}", old_value=old_value, new_value=current.value,
            reason="Campo configurável alterado no quadro.",
        )
        return item


def build_cells(items, fields, organization):
    """Converte objetos de domínio em células puramente visuais sem N+1."""
    items = list(items)
    custom_fields = [field for field in fields if not field.is_system]
    activity_ids = [item.pk for item in items if isinstance(item, Activity)]
    task_ids = [item.pk for item in items if isinstance(item, Task)]
    custom_values = {}
    if custom_fields:
        values = DomainCustomValue.objects.filter(field__in=custom_fields).filter(
            models.Q(activity_id__in=activity_ids) | models.Q(task_id__in=task_ids)
        )
        for row in values:
            custom_values[(row.field_id, row.activity_id or row.task_id)] = row.value.get("value", "")
    demand_priority = EnumColorResolver(organization, "activity_urgency")
    task_priority = EnumColorResolver(organization, "task_priority")
    sector_options = list(Sector.objects.filter(organization=organization, is_active=True).order_by("name"))
    User = get_user_model()
    people_options = list(User.objects.filter(profile__organization=organization, is_active=True).order_by("first_name", "last_name", "username"))
    demand_stages, task_stages, demand_conditions, task_conditions = {}, {}, {}, {}
    sector_ids = {item.sector_id for item in items if getattr(item, "sector_id", None)}
    for stage in ActivityStage.objects.filter(organization=organization, sector_id__in=sector_ids, is_active=True).order_by("order", "name"):
        demand_stages.setdefault(stage.sector_id, []).append(stage)
    for stage in TaskStage.objects.filter(organization=organization, sector_id__in=sector_ids, is_active=True).order_by("order", "name"):
        task_stages.setdefault(stage.sector_id, []).append(stage)
    for condition in WorkflowStatus.objects.filter(organization=organization, sector_id__in=sector_ids, is_active=True).order_by("order", "name"):
        (demand_conditions if condition.domain == WorkflowStatus.Domain.ACTIVITY else task_conditions).setdefault(condition.sector_id, []).append(condition)
    for item in items:
        cells = []
        for field in fields:
            key = field.key
            cell = {"field": field, "key": key, "raw": "", "text": "—", "kind": field.type, "editable": True, "options": []}
            if key == "title":
                cell.update(raw=item.title, text=item.title)
            elif key in {"owner", "responsavel"}:
                person = getattr(item, key, None)
                cell.update(raw=getattr(person, "pk", ""), text=person.get_full_name() or person.get_username() if person else "Sem responsável", person=person, options=people_options)
            elif key == "sector":
                sector = item.sector
                cell.update(raw=getattr(sector, "pk", ""), text=sector.name if sector else "Sem setor", sector=sector, options=sector_options)
            elif key == "activity" and isinstance(item, Task):
                cell.update(raw=item.activity_id, text=item.activity.title, relation=item.activity, editable=False)
            elif key == "requested_deadline":
                deadline = item.requested_deadline
                cell.update(raw=deadline.isoformat() if deadline else "", text=timezone.localtime(deadline).strftime("%d/%m/%Y %H:%M") if deadline else "Sem prazo", deadline=deadline)
            elif key in {"stage", "condition"}:
                choice = getattr(item, key, None)
                if key == "stage":
                    options = (demand_stages if isinstance(item, Activity) else task_stages).get(item.sector_id, [])
                else:
                    options = (demand_conditions if isinstance(item, Activity) else task_conditions).get(item.sector_id, [])
                cell.update(raw=getattr(choice, "pk", ""), text=choice.name if choice else ("Sem etapa" if key == "stage" else "Sem condição"), choice=choice, options=options)
            elif key in {"urgency", "priority"}:
                code = getattr(item, key)
                resolver = demand_priority if key == "urgency" else task_priority
                label = item.get_urgency_display() if key == "urgency" else item.get_priority_display()
                color = resolver.color_for(code)
                cell.update(raw=code, text=resolver.label_for(code, label), color=color, text_color=get_contrast_text(color))
            elif key in {"tasks", "checklist"}:
                if isinstance(item, Activity):
                    total, done = getattr(item, "total_tasks", 0), getattr(item, "done_tasks", 0)
                else:
                    total = getattr(item, "checklist_total", 0)
                    done = getattr(item, "checklist_done", 0)
                cell.update(raw=f"{done}/{total}", text=f"{done}/{total}", progress=(int(done * 100 / total) if total else 0), editable=False)
            else:
                value = custom_values.get((field.pk, item.pk), "")
                cell.update(raw=value, text=str(value) if value not in (None, "") else "—")
            cells.append(cell)
        item.work_cells = cells
    return items
