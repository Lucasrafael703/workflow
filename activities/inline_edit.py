"""Edição inline da lista de Demandas (/demandas/).

Este módulo é um ADAPTER, não um segundo Service de domínio: traduz o pedido da tela (campo + valor), chama o
`ActivityService` (onde moram autorização, validação, auditoria e notificação) e monta a resposta JSON que a tela usa
para redesenhar a célula. Regra de negócio nova vai no `ActivityService`, para valer em qualquer tela.

Também calcula, em UMA chamada `AuthorizationService.can_many` para a lista toda, o que mostrar como editável em cada
linha (`inline_flags`). Isso só decide se o afeto de clique aparece: quem manda é o Service, que confere de novo a cada
gravação.

Prazo sem hora: o formulário da demanda grava 23:59 quando a pessoa informa só a data (`SplitDateOptionalTimeField`).
Sem migração não dá para distinguir esse 23:59 automático de um 23:59 escolhido de propósito; por isso a lista mostra só
a data quando a hora é 23:59 e o editor trata 23:59 como "sem hora" (dívida técnica registrada em docs/13).
"""

import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.forms.utils import from_current_timezone
from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from acessos.services import AuthorizationService
from core.models import ActivityStage, Sector, WorkflowStatus
from core.services import (
    ActivityStageService,
    CadastroError,
    SectorService,
    WorkflowStatusService,
)

from .errors import ActivityError, ActivityPermissionError
from .models import Activity
from .policies import ACTIVITY_TERMINAL, ActivityTransitionPolicy
from .services import ActivityService, require_action
from .templatetags.lps import avatar_color

User = get_user_model()

NO_TIME = datetime.time(23, 59)
MIN_YEAR, MAX_YEAR = 1900, 2200
OPTION_LIMIT = 200  # teto de opções devolvidas numa lista (setores de uma organização são poucos)


# ---------------------------------------------------------------------------
# Texto exibido (um só lugar: a tabela e a resposta do servidor usam as mesmas funções)
# ---------------------------------------------------------------------------


def person_name(user):
    return user.get_full_name() or user.get_username()


def person_initials(user):
    return person_name(user)[:2].upper()


def option_data(obj):
    """Setor, etapa ou status para a tela: dados estruturados com a cor e a cor do texto calculadas no servidor
    (mesma fórmula WCAG do resto do sistema). `None` quando não há valor."""
    if obj is None:
        return None
    return {"id": obj.pk, "name": obj.name, "color": obj.color, "text_color": obj.text_color}


def deadline_display(value):
    """"10/10/2026" quando a hora é 23:59 (prazo só com data); "10/10/2026 17:47" nos demais; "" sem prazo."""
    if value is None:
        return ""
    local = timezone.localtime(value)
    if (local.hour, local.minute) == (NO_TIME.hour, NO_TIME.minute):
        return local.strftime("%d/%m/%Y")
    return local.strftime("%d/%m/%Y %H:%M")


def deadline_parts(value):
    """`(data ISO, "HH:MM" ou "")` para o editor; 23:59 conta como "sem hora"."""
    if value is None:
        return "", ""
    local = timezone.localtime(value)
    clock = "" if (local.hour, local.minute) == (NO_TIME.hour, NO_TIME.minute) else local.strftime("%H:%M")
    return local.date().isoformat(), clock


def deadline_state(activity, now=None):
    """`(vencido?, dias de atraso)`: a mesma regra de `decorate_activity_cards` (só demanda aberta com prazo vencido)."""
    now = now or timezone.now()
    overdue = bool(
        activity.requested_deadline
        and activity.requested_deadline < now
        and activity.status not in ACTIVITY_TERMINAL
    )
    days = max(1, (now.date() - activity.requested_deadline.date()).days) if overdue else 0
    return overdue, days


def parse_deadline(date_text, time_text):
    """Data (`YYYY-MM-DD`) + hora opcional (`HH:MM`) -> datetime no fuso corrente; sem data -> `None` (retira o prazo).
    Sem hora vale 23:59, como no formulário."""
    date_text = (date_text or "").strip()
    time_text = (time_text or "").strip()
    if not date_text:
        if time_text:
            raise ActivityError("Escolha a data do prazo.")
        return None
    try:
        day = datetime.date.fromisoformat(date_text)
    except ValueError:
        raise ActivityError("Informe uma data válida.") from None
    if not MIN_YEAR <= day.year <= MAX_YEAR:
        raise ActivityError("Informe uma data válida.")
    if time_text:
        try:
            clock = datetime.time.fromisoformat(time_text).replace(second=0, microsecond=0)
        except ValueError:
            raise ActivityError("Informe uma hora válida (HH:MM).") from None
    else:
        clock = NO_TIME
    return from_current_timezone(datetime.datetime.combine(day, clock))


# ---------------------------------------------------------------------------
# O que mostrar como editável em cada linha
# ---------------------------------------------------------------------------


def inline_flags(user, activities):
    """Anexa a cada demanda `inline` (o que a pessoa pode editar ali) e `inline_deadline_text`.

    Uma única consulta de autorização para a lista inteira (`can_many`). Demanda concluída/cancelada vem travada e
    rascunho nunca é editável por aqui (a rota inline devolve 404 para rascunho).
    """
    activities = list(activities)
    checks = []
    for activity in activities:
        checks.append((catalog.ATIVIDADE_EDITAR, activity))
        checks.append((catalog.ATIVIDADE_ALTERAR_DONO, activity))
        checks.append((catalog.ATIVIDADE_DEFINIR_ETAPA, activity))
        checks.append((catalog.ATIVIDADE_MOVER_ESTAGIO, activity))  # ação legada: o Service ainda a aceita
        checks.append((catalog.ATIVIDADE_DEFINIR_CONDICAO, activity))
    allowed = AuthorizationService.can_many(user, checks) if checks else {}
    for activity in activities:
        locked = activity.status in ACTIVITY_TERMINAL
        open_row = not locked and activity.status != Activity.Status.RASCUNHO
        can_edit = bool(allowed.get((catalog.ATIVIDADE_EDITAR, activity.pk))) and open_row
        # Estágio e Status são do setor da demanda: sem setor não há opções para escolher.
        can_stage = (
            open_row
            and activity.sector_id is not None
            and bool(allowed.get((catalog.ATIVIDADE_DEFINIR_ETAPA, activity.pk)) or allowed.get((catalog.ATIVIDADE_MOVER_ESTAGIO, activity.pk)))
        )
        can_condition = (
            open_row and activity.sector_id is not None and bool(allowed.get((catalog.ATIVIDADE_DEFINIR_CONDICAO, activity.pk)))
        )
        can_owner = (
            bool(allowed.get((catalog.ATIVIDADE_ALTERAR_DONO, activity.pk)))
            and not locked
            and activity.status != Activity.Status.RASCUNHO
        )
        date_text, time_text = deadline_parts(activity.requested_deadline)
        activity.inline = {
            "locked": locked,
            "title": can_edit,
            "client": can_edit,
            "sector": can_edit,
            "stage": can_stage,
            "condition": can_condition,
            "owner": can_owner,
            "requested_deadline": can_edit,
            "deadline_date": date_text,
            "deadline_time": time_text,
        }
        activity.inline_deadline_text = deadline_display(activity.requested_deadline)
    return activities


# ---------------------------------------------------------------------------
# Listas de opções dos pop-overs (setor)
# ---------------------------------------------------------------------------


OPTION_FIELDS = {
    # campo -> (ação de gerir as opções do setor, nome do domínio na tela de configuração)
    "stage": (catalog.ETAPA_GERIR, "demandas"),
    "condition": (catalog.CONDICAO_GERIR, "demandas"),
}


def _may_set(user, activity, field):
    """Espelha a regra de gravação do `ActivityService.set_stage/set_condition` só para decidir se a lista é mostrada;
    quem decide de verdade é o Service, a cada gravação."""
    if field == "stage":
        return AuthorizationService.can(user, catalog.ATIVIDADE_DEFINIR_ETAPA, activity) or AuthorizationService.can(
            user, catalog.ATIVIDADE_MOVER_ESTAGIO, activity
        )
    return AuthorizationService.can(user, catalog.ATIVIDADE_DEFINIR_CONDICAO, activity)


def inline_options(user, activity, field):
    """Opções para o pop-over de um campo, no contexto de UMA demanda (o cliente nunca informa o setor: ele vem da
    demanda). Só devolve a lista a quem poderia gravar: o `ActivityService` continua sendo quem decide na gravação."""
    if field in OPTION_FIELDS:
        sector = activity.sector
        if sector is None:
            raise ActivityError("Defina o setor da demanda antes de escolher.")
        if not _may_set(user, activity, field):
            raise ActivityPermissionError("Você não possui autorização para alterar este campo.")
        ActivityTransitionPolicy.assert_allowed(activity, "set_stage" if field == "stage" else "set_condition", user)
        manage_action = OPTION_FIELDS[field][0]
        can_manage = AuthorizationService.can(user, manage_action, sector)
        if field == "stage":
            options = ActivityStageService.available_for(activity.organization, sector)
            current_id = activity.stage_id
        else:
            options = WorkflowStatusService.available_for(activity.organization, sector, WorkflowStatus.Domain.ACTIVITY)
            current_id = activity.condition_id
        return {
            "current_id": current_id,
            "allow_clear": field == "condition",
            "can_create": can_manage,
            "can_manage": can_manage,
            "manage_url": f"{reverse('config-etapas-status')}?domain={OPTION_FIELDS[field][1]}&sector={sector.pk}" if can_manage else "",
            "sector_name": sector.name,
            "items": [option_data(option) for option in options[:OPTION_LIMIT]],
        }
    if field == "sector":
        require_action(user, catalog.ATIVIDADE_EDITAR, activity)
        ActivityTransitionPolicy.assert_allowed(activity, "change_sector", user)
        # Todos os setores ativos da organização, como o formulário e a busca de setor: a autorização do DESTINO é
        # conferida no Service ao gravar (esconder aqui bloquearia, em silêncio, quem tem concessão relacional).
        sectors = Sector.objects.filter(organization_id=activity.organization_id, is_active=True).order_by("name")
        return {
            "current_id": activity.sector_id,
            "allow_clear": False,
            "can_create": AuthorizationService.can(user, catalog.SETOR_EDITAR),
            "items": [option_data(sector) for sector in sectors[:OPTION_LIMIT]],
        }
    raise ActivityError("Este campo não tem lista de opções.")


def manage_option(user, activity, data):
    """Criar ou editar (nome e cor) uma etapa ou status do setor da demanda, sem sair da lista.

    Autoridade única: `ETAPA_GERIR` / `CONDICAO_GERIR` no setor da demanda, conferida aqui; nome, cor da paleta e nome
    repetido são validados pelos Services de cadastro (`CadastroError` vira 400). Inativar, ordenar e definir o padrão
    continuam na tela de configuração. Devolve `(dados, criada?)`."""
    field = (data.get("campo") or "").strip()
    action = (data.get("acao") or "").strip()
    if field not in OPTION_FIELDS:
        raise ActivityError("Este campo não tem opções para gerir.")
    sector = activity.sector
    if sector is None:
        raise ActivityError("Defina o setor da demanda antes de gerir as opções.")
    require_action(user, OPTION_FIELDS[field][0], sector)
    name = data.get("name")
    color = (data.get("color") or "").strip().upper()
    try:
        with transaction.atomic():
            if action == "criar":
                if field == "stage":
                    option = ActivityStageService.create(
                        activity.organization, sector, name, created_by=user, color=color or "#94A3B8"
                    )
                else:
                    option = WorkflowStatusService.create(
                        activity.organization, name, WorkflowStatus.Domain.ACTIVITY, sector=sector, created_by=user,
                        color=color or "#94A3B8",
                    )
                return {"item": option_data(option)}, True
            if action == "editar":
                model = ActivityStage if field == "stage" else WorkflowStatus
                filters = {"organization_id": activity.organization_id, "sector_id": sector.pk}
                if field == "condition":
                    filters["domain"] = WorkflowStatus.Domain.ACTIVITY
                try:
                    option = model.objects.filter(pk=int(data.get("option_id")), **filters).first()
                except (TypeError, ValueError):
                    option = None
                if option is None:
                    raise ActivityError("A opção escolhida não existe neste setor.")
                service = ActivityStageService if field == "stage" else WorkflowStatusService
                option = service.update(option, name=name, color=color or None)
                return {"item": option_data(option)}, False
    except CadastroError as exc:
        raise ActivityError(str(exc)) from exc
    raise ActivityError("Ação desconhecida.")


def _find_option(model, activity, raw, message, **filters):
    """Etapa ou status escolhida pela tela, sempre dentro da organização da demanda; o Service confere o setor."""
    try:
        pk = int(raw)
    except (TypeError, ValueError):
        raise ActivityError(message) from None
    option = model.objects.filter(pk=pk, organization_id=activity.organization_id, **filters).first()
    if option is None:
        raise ActivityError("A opção escolhida não existe nesta organização.")
    return option


# ---------------------------------------------------------------------------
# Gravação
# ---------------------------------------------------------------------------


class ActivityInlineService:
    """Traduz o pedido da tela para o `ActivityService`. Erros de regra e de permissão sobem como `ActivityError` e
    `ActivityPermissionError` para a view mapear em 400 e 403."""

    @classmethod
    def handlers(cls):
        return {
            "title": cls._title,
            "owner": cls._owner,
            "requested_deadline": cls._deadline,
            "sector": cls._sector,
            "stage": cls._stage,
            "condition": cls._condition,
        }

    @classmethod
    def update(cls, *, user, activity, field, data):
        handler = cls.handlers().get(field)
        if handler is None:
            raise ActivityError("Este campo não pode ser editado por aqui.")
        extra = handler(user, activity, data) or {}  # o que só esta gravação sabe (ex.: o setor recém-criado)
        activity.refresh_from_db()
        return {**cls.serialize(activity, field), **extra}

    # -- campos -------------------------------------------------------------------------------

    @staticmethod
    def _title(user, activity, data):
        # O Service normaliza (strip), recusa vazio e título longo, audita só o que mudou.
        ActivityService.update_activity(activity, user, title=data.get("value") or "")

    @staticmethod
    def _owner(user, activity, data):
        try:
            owner_id = int(data.get("value"))
        except (TypeError, ValueError):
            raise ActivityError("Escolha o responsável.") from None
        if owner_id == activity.owner_id:
            return  # nada a gravar: sem auditoria nem notificação à toa
        new_owner = User.objects.filter(pk=owner_id).first()
        if new_owner is None:
            raise ActivityError("O responsável escolhido não pertence à organização ou está inativo.")
        # Dono ativo da mesma organização, `OwnerChangeLog`, auditoria e notificações: tudo no Service.
        ActivityService.change_owner(activity, new_owner, user)

    @staticmethod
    def _deadline(user, activity, data):
        deadline = parse_deadline(data.get("date"), data.get("time"))
        ActivityService.update_activity(activity, user, requested_deadline=deadline)

    @staticmethod
    def _stage(user, activity, data):
        # Como no Kanban, o estágio não é limpável: sempre há uma etapa escolhida. Setor, ativa e estado da demanda
        # (concluída/cancelada não troca) são conferidos pelo `ActivityService.set_stage`.
        stage = _find_option(ActivityStage, activity, data.get("value"), "Escolha o estágio.")
        if stage.pk == activity.stage_id:
            return None  # nada a gravar: sem auditoria à toa
        ActivityService.set_stage(activity, stage, user)
        return None

    @staticmethod
    def _condition(user, activity, data):
        raw = (data.get("value") or "").strip()
        condition = None
        if raw:  # vazio = "Sem status"
            condition = _find_option(
                WorkflowStatus, activity, raw, "Escolha o status.", domain=WorkflowStatus.Domain.ACTIVITY
            )
        if (condition.pk if condition else None) == activity.condition_id:
            return None
        ActivityService.set_condition(activity, condition, user)
        return None

    @staticmethod
    def _sector(user, activity, data):
        """Trocar de setor (`value` = id) ou criar um setor novo e já aplicá-lo (`new_name` + `new_color`).

        Criar e aplicar é UMA transação: se a troca for recusada (destino sem permissão, pendência aberta, demanda
        concluída...), o setor também não fica criado. A etapa e o status passam para os padrões do novo setor dentro
        do `ActivityService` (que audita as três mudanças)."""
        new_name = (data.get("new_name") or "").strip()
        if new_name or (data.get("new_color") or "").strip():
            with transaction.atomic():
                # `SectorService` é de cadastro e não confere permissão (as telas conferem): criar setor exige a mesma
                # ação do cadastro de setores.
                require_action(user, catalog.SETOR_EDITAR)
                try:
                    sector = SectorService.create(
                        activity.organization, new_name, user, color=(data.get("new_color") or "").strip()
                    )
                except CadastroError as exc:
                    raise ActivityError(str(exc)) from exc
                ActivityService.update_activity(activity, user, sector=sector)
            return {"created_sector": option_data(sector)}
        try:
            sector_id = int(data.get("value"))
        except (TypeError, ValueError):
            raise ActivityError("Escolha o setor.") from None
        if sector_id == activity.sector_id:
            return None  # nada a gravar: sem auditoria à toa
        sector = Sector.objects.filter(pk=sector_id, organization_id=activity.organization_id).first()
        if sector is None:
            raise ActivityError("O setor escolhido não existe nesta organização.")
        ActivityService.update_activity(activity, user, sector=sector)
        return None

    # -- resposta -----------------------------------------------------------------------------

    @classmethod
    def serialize(cls, activity, field):
        """Dados estruturados (nunca HTML): a tela redesenha a célula com `textContent`."""
        if field == "title":
            return {"value": activity.title, "display": {"text": activity.title}}
        if field == "owner":
            owner = activity.owner
            return {
                "value": owner.pk if owner else "",
                "display": {
                    "text": person_name(owner) if owner else "Sem responsável",
                    "initials": person_initials(owner) if owner else "",
                    "avatar_class": f"avatar--{avatar_color(owner)}" if owner else "",
                },
            }
        if field == "stage":
            return {"value": activity.stage_id or "", "display": option_data(activity.stage)}
        if field == "condition":
            return {"value": activity.condition_id or "", "display": option_data(activity.condition)}
        if field == "sector":
            return {
                "value": activity.sector_id or "",
                "display": option_data(activity.sector),
                # Trocar o setor redefine etapa e status: a tela redesenha as duas células com estes dados.
                "derived": {"stage": option_data(activity.stage), "condition": option_data(activity.condition)},
            }
        if field == "requested_deadline":
            date_text, time_text = deadline_parts(activity.requested_deadline)
            overdue, days = deadline_state(activity)
            return {
                "value": {"date": date_text, "time": time_text},
                "display": {"text": deadline_display(activity.requested_deadline) or "Sem prazo", "is_late": overdue},
                "derived": {"overdue_days": days},
            }
        raise ActivityError("Este campo não pode ser editado por aqui.")
