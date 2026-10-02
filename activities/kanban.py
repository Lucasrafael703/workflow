"""Quadro Kanban de Demandas e de Tarefas, sempre de um setor por vez.

As colunas são as **Etapas do setor** (`ActivityStage` / `TaskStage`); a **Condição** (`WorkflowStatus`) é a
leitura manual de "o que está acontecendo". O `status` operacional (fila, cronômetro, bloqueio, conclusão…)
continua exclusivo dos services de Demanda e de Tarefa: arrastar um cartão muda **somente** a etapa
(`set_stage`), e escolher uma condição nunca executa nada (`set_condition`).

Este módulo não decide regra de negócio. Ele resolve o setor, filtra o que a pessoa pode ver, monta colunas e
cartões e devolve fragmentos; quem autoriza e grava são os services que já existem (`ActivityService`,
`TaskService`, `StageService`, `ConditionService`).

Visibilidade (decisão deste quadro, ver docs/06): dentro do setor escolhido, quem **participa do setor** ou tem
a ação de visualizar naquele setor vê todos os itens dele; as demais pessoas veem só os itens em que atuam
(dono da demanda; responsável ou participante da tarefa).
"""

from datetime import timedelta
from functools import cached_property

from django.contrib.auth import get_user_model
from django.db.models import Exists, F, OuterRef, Prefetch, Q
from django.db.models.functions import Coalesce
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from acessos import catalog
from acessos.services import AuthorizationService
from audit.models import AuditLog
from core.mixins import OrganizationRequiredMixin, user_sectors
from core.models import ActivityStage, Client, Sector, Site, Tag, TaskStage, WorkflowStatus
from core.services import ActivityStageService, CadastroError, TaskStageService, WorkflowStatusService

from .errors import ActivityError
from .filtering import canonical_filter_querystring, filter_state_for_template, normalize_workspace_filters
from .models import Activity, ActivityMessage, MessageKind, Task, TaskExecutor, code_search_term
from .policies import ACTIVITY_TERMINAL, TASK_TERMINAL
from .services import ActivityService, TaskService

User = get_user_model()

TITLE_MAX_LENGTH = 200
MAX_PEOPLE_OPTIONS = 60
MAX_DRAWER_MESSAGES = 15
MAX_DRAWER_HISTORY = 6
#: Estimativa de "parado": a partir daqui o cartão ganha um destaque discreto.
STALE_AFTER_DAYS = 5
DEFAULT_OPTION_COLOR = "#94A3B8"
SECTOR_PARAMS = ("setor", "grupo", "sector")
DEADLINE_CHOICES = (
    ("", "Qualquer prazo"),
    ("atrasadas", "Atrasadas"),
    ("hoje", "Vencem hoje"),
    ("7_dias", "Próximos 7 dias"),
    ("sem_prazo", "Sem prazo"),
)


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _expression(spec, descending):
    """Campo de ordenação; prazo vazio sempre por último, qualquer que seja o sentido."""
    if isinstance(spec, tuple):
        expression = F(spec[1]) if isinstance(spec[1], str) else spec[1]
        return expression.desc(nulls_last=True) if descending else expression.asc(nulls_last=True)
    return f"-{spec}" if descending else spec


# ---------------------------------------------------------------------------
# Quadros
# ---------------------------------------------------------------------------


class Board:
    """O que é igual nos dois quadros. As subclasses dizem o que é de Demanda e o que é de Tarefa."""

    slug = ""  # aparece na URL: "demandas" | "tarefas"
    stage_domain = ""  # chave dos services de etapa: "demanda" | "tarefa"
    condition_domain = None  # `WorkflowStatus.Domain`
    stage_model = None
    stage_service = None
    view_action = None
    card_template = ""
    noun = ("demanda", "demandas")
    search_placeholder = ""
    #: chave → (rótulo, campos de ordenação, sentido padrão). Um campo `("prazo", expr)` põe o vazio por último.
    orderings = {}
    default_ordering = ""
    #: ações do catálogo avaliadas por cartão, em lote (`can_many`): nome → ações (basta uma).
    card_permissions = {}

    def __init__(self, request, organization):
        self.request = request
        self.user = request.user
        self.organization = organization
        self.params = request.GET

    # -- setores -----------------------------------------------------------

    @cached_property
    def member_sector_ids(self):
        return set(user_sectors(self.user).values_list("id", flat=True))

    @cached_property
    def full_view_sector_ids(self):
        """Setores em que a pessoa vê tudo: onde participa ou onde tem a ação de visualizar."""
        return self.member_sector_ids | set(AuthorizationService.accessible_sector_ids(self.user, self.view_action))

    @cached_property
    def involved_sector_ids(self):
        return set(
            self.involvement(self.item_queryset()).exclude(sector__isnull=True).values_list("sector_id", flat=True).distinct()
        )

    @cached_property
    def sectors(self):
        ids = self.full_view_sector_ids | self.involved_sector_ids
        return list(Sector.objects.filter(organization=self.organization, is_active=True, pk__in=ids).order_by("name"))

    @cached_property
    def sector(self):
        """O setor do quadro: o pedido, senão o último usado, senão o principal da pessoa, senão o primeiro."""
        by_id = {sector.pk: sector for sector in self.sectors}
        session_key = f"kanban_sector_{self.slug}"
        requested = next((_int_or_none(self.params.get(key)) for key in SECTOR_PARAMS if self.params.get(key)), None)
        chosen = by_id.get(requested)
        if chosen is None and requested is None:
            chosen = by_id.get(self.request.session.get(session_key))
        if chosen is None:
            profile = getattr(self.user, "profile", None)
            chosen = by_id.get(getattr(profile, "main_sector_id", None))
        if chosen is None:
            # Sem setor principal configurado, prioriza o primeiro setor em
            # que a pessoa passou a atuar. A lista continua ordenada para a
            # interface, mas a abertura do quadro não muda arbitrariamente
            # só porque outro setor tem um nome alfabético anterior.
            membership_ids = self.user.sector_memberships.filter(
                removed_at__isnull=True,
                sector__organization=self.organization,
                sector__is_active=True,
            ).order_by("pk").values_list("sector_id", flat=True)
            chosen = next((by_id.get(sector_id) for sector_id in membership_ids if sector_id in by_id), None)
        if chosen is None and self.sectors:
            chosen = self.sectors[0]
        if chosen is not None and self.request.session.get(session_key) != chosen.pk:
            self.request.session[session_key] = chosen.pk
        return chosen

    @property
    def sees_everything(self):
        return self.sector is not None and self.sector.pk in self.full_view_sector_ids

    # -- consultas ---------------------------------------------------------

    def item_queryset(self):
        raise NotImplementedError

    def involvement(self, queryset):
        """Só o que a pessoa atua; usado quando ela não participa do setor."""
        raise NotImplementedError

    def visible_items(self):
        """Os itens do setor que a pessoa pode ver, já com os filtros da barra e a ordenação."""
        if self.sector is None:
            return self.item_queryset().none()
        queryset = self.item_queryset().filter(sector=self.sector)
        if not self.sees_everything:
            queryset = self.involvement(queryset)
        return self.order(self.apply_filters(queryset))

    def scoped_items(self):
        """O mesmo recorte de visibilidade, antes dos filtros (alimenta as opções do filtro)."""
        queryset = self.item_queryset().filter(sector=self.sector)
        return queryset if self.sees_everything else self.involvement(queryset)

    @cached_property
    def filters(self):
        normalized = normalize_workspace_filters(self.request, default_order=self.default_ordering)
        pessoa = normalized["pessoa"]
        if pessoa == "eu":
            pessoa = str(self.user.pk)
        return {
            "q": normalized["q"],
            "pessoa": pessoa,
            "setor": normalized["setor"],
            "condicao": normalized["condicao"],
            "estagio": normalized["estagio"],
            "filtro": normalized["filtro"],
            "status": normalized["status"],
            "cliente": normalized["cliente"],
            "obra": normalized["obra"],
            "prazo": normalized["prazo"],
            "bloqueio": "1" if normalized["bloqueio"] else "",
            "tag": normalized["tag"],
            "participante": normalized["participante"],
            "concluidas": "1" if normalized["concluidas"] else "",
            "ordem": normalized["ordem"] if normalized["ordem"] in self.orderings else self.default_ordering,
            "dir": normalized["dir"] if normalized["dir"] in ("asc", "desc") else "",
        }

    ADVANCED_FILTERS = ("cliente", "obra", "prazo", "bloqueio", "tag", "participante", "concluidas", "filtro", "estagio")

    @property
    def advanced_count(self):
        return sum(1 for key in self.ADVANCED_FILTERS if self.filters[key])

    @property
    def has_filters(self):
        simple = ("q", "pessoa", "condicao", "estagio")
        return (
            any(self.filters[key] for key in simple)
            or bool(self.advanced_count)
            or self.filters["ordem"] != self.default_ordering
            or bool(self.filters["dir"])
        )

    def apply_filters(self, queryset):
        raise NotImplementedError

    def order(self, queryset):
        key = self.filters["ordem"]
        _label, specs, default_direction = self.orderings[key]
        descending = (self.filters["dir"] or default_direction) == "desc"
        return queryset.order_by(*[_expression(spec, descending) for spec in specs], "pk")

    def tag_filter(self, queryset, through, fk_name):
        tag_id = _int_or_none(self.filters["tag"])
        if tag_id is None:
            return queryset
        return queryset.filter(Exists(through.objects.filter(**{fk_name: OuterRef("pk"), "tag_id": tag_id})))

    # -- colunas e cartões -------------------------------------------------

    def stages(self):
        return list(self.stage_service.available_for(self.organization, self.sector))

    def conditions(self):
        return list(
            WorkflowStatusService.available_for(self.organization, self.sector, self.condition_domain)
        )

    def decorate(self, items):
        """Dados só de exibição + as permissões de todos os cartões numa consulta de autorização."""
        now = timezone.now()
        checks = [(action, item) for item in items for actions in self.card_permissions.values() for action in actions]
        access = AuthorizationService.can_many(self.user, checks) if checks else {}
        for item in items:
            reference = item.stage_changed_at or item.created_at
            item.days_in_stage = max(0, (now - reference).days)
            item.is_stale = item.days_in_stage >= STALE_AFTER_DAYS
            item.perm = {
                name: any(access.get((action, item.pk), False) for action in actions)
                for name, actions in self.card_permissions.items()
            }
            item.condition_name = item.condition.name if item.condition_id else ""
            item.condition_color = item.condition.color if item.condition_id else DEFAULT_OPTION_COLOR
            item.condition_text_color = item.condition.text_color if item.condition_id else ""
            self.decorate_item(item, now)
        return items

    def decorate_item(self, item, now):
        raise NotImplementedError

    def columns(self, items):
        stages = self.stages()
        buckets = {stage.pk: [] for stage in stages}
        loose = []
        for item in items:
            bucket = buckets.get(item.stage_id)
            (bucket if bucket is not None else loose).append(item)
        can_manage = self.can_manage_stages
        columns = []
        for stage in stages:
            count = len(buckets[stage.pk])
            columns.append(
                {
                    "stage": stage,
                    "items": buckets[stage.pk],
                    "count": count,
                    "limit": stage.column_limit,
                    "over_limit": bool(stage.column_limit) and count > stage.column_limit,
                    "can_manage": can_manage,
                }
            )
        # "Sem etapa" não é uma etapa: só aparece quando sobra item legado/inativo para classificar.
        unassigned = {"stage": None, "items": loose, "count": len(loose)} if loose else None
        return columns, unassigned

    @cached_property
    def can_manage_stages(self):
        return bool(self.sector) and AuthorizationService.can(self.user, catalog.ETAPA_GERIR, self.sector)

    @cached_property
    def can_manage_conditions(self):
        return bool(self.sector) and AuthorizationService.can(self.user, catalog.CONDICAO_GERIR, self.sector)

    def person_options(self):
        return list(
            User.objects.filter(
                is_active=True,
                sector_memberships__sector=self.sector,
                sector_memberships__removed_at__isnull=True,
            )
            .distinct()
            .order_by("first_name", "username")[:MAX_PEOPLE_OPTIONS]
        )

    def context(self):
        sector = self.sector
        params = self.request.GET.copy()
        params.pop("page", None)
        context = {
            "board": self,
            "kanban_domain": self.slug,
            "noun_singular": self.noun[0],
            "noun_plural": self.noun[1],
            "search_placeholder": self.search_placeholder,
            "view_mode": "kanban",
            "sectors": self.sectors,
            "sector": sector,
            "filters": self.filters,
            "advanced_count": self.advanced_count,
            "has_filters": self.has_filters,
            "filter_querystring": params.urlencode(),
            "orderings": [(key, label) for key, (label, _specs, _dir) in self.orderings.items()],
            "deadline_choices": DEADLINE_CHOICES,
            "columns": [],
            "unassigned": None,
            "total_items": 0,
            "has_stages": False,
            "can_manage_stages": False,
            "can_manage_conditions": False,
        }
        if sector is None:
            context["filter_state"] = filter_state_for_template(
                self.request,
                domain=self.stage_domain,
                view_mode="kanban",
                sectors=self.sectors,
                people=[],
                board=True,
                orderings=[(key, label) for key, (label, _specs, _dir) in self.orderings.items()],
                default_order=self.default_ordering,
            )
            context["filter_querystring"] = context["filter_state"]["filter_querystring"]
            return context
        items = self.decorate(list(self.visible_items()))
        columns, unassigned = self.columns(items)
        scoped = self.scoped_items()
        context.update(
            {
                "columns": columns,
                "unassigned": unassigned,
                "total_items": len(items),
                "has_stages": bool(columns),
                "can_manage_stages": self.can_manage_stages,
                "can_manage_conditions": self.can_manage_conditions,
                "condition_choices": self.conditions(),
                "people": self.person_options(),
                "clients": list(Client.objects.filter(pk__in=scoped.values("client_id" if self.slug == "demandas" else "activity__client_id")).order_by("name")),
                "sites": list(Site.objects.filter(pk__in=scoped.values("site_id" if self.slug == "demandas" else "activity__site_id")).order_by("name")),
                "tags": list(Tag.objects.filter(organization=self.organization, is_active=True).order_by("name")),
                "clear_url": f"{reverse(self.list_url_name)}?setor={sector.pk}",
                "config_url": f"{reverse('config-etapas-status')}?domain={self.slug}&sector={sector.pk}",
            }
        )
        filter_state = filter_state_for_template(
            self.request,
            domain=self.stage_domain,
            view_mode="kanban",
            sectors=self.sectors,
            people=context["people"],
            clients=context["clients"],
            sites=context["sites"],
            tags=context["tags"],
            stage_groups=[(sector.name, self.stages())],
            condition_groups=[(sector.name, context["condition_choices"])],
            board=True,
            orderings=[(key, label) for key, (label, _specs, _dir) in self.orderings.items()],
            default_order=self.default_ordering,
        )
        filter_state["sector_obj"] = sector
        filter_state["setor"] = str(sector.pk)
        filter_state["filter_querystring"] = canonical_filter_querystring(
            self.request,
            keep_calendar=bool(normalize_workspace_filters(self.request)["ano"] or normalize_workspace_filters(self.request)["mes"]),
        )
        if f"setor={sector.pk}" not in filter_state["filter_querystring"]:
            filter_state["filter_querystring"] = (
                f"{filter_state['filter_querystring']}&setor={sector.pk}"
                if filter_state["filter_querystring"]
                else f"setor={sector.pk}"
            )
        filter_state["clear_url"] = f"{reverse(self.list_url_name)}?setor={sector.pk}"
        context["filter_state"] = filter_state
        context["filter_querystring"] = filter_state["filter_querystring"]
        return context

    list_url_name = ""

    # -- um cartão só (depois de uma ação) ---------------------------------

    def item_or_404(self, pk):
        item = self.decorate([get_object_or_404(self.item_queryset(), pk=pk)])[0]
        return item

    def render_card(self, item):
        return render_to_string(
            self.card_template,
            {
                "item": item,
                "kanban_domain": self.slug,
                "sector": item.sector,
                "can_manage_stages": AuthorizationService.can(self.user, catalog.ETAPA_GERIR, item.sector)
                if item.sector_id else False,
                "can_manage_conditions": AuthorizationService.can(self.user, catalog.CONDICAO_GERIR, item.sector)
                if item.sector_id else False,
            },
            request=self.request,
        )

    def set_stage(self, item, stage):
        raise NotImplementedError

    def set_condition(self, item, condition):
        raise NotImplementedError


class DemandBoard(Board):
    slug = "demandas"
    stage_domain = "demanda"
    condition_domain = WorkflowStatus.Domain.ACTIVITY
    stage_model = ActivityStage
    stage_service = ActivityStageService
    view_action = catalog.ATIVIDADE_VISUALIZAR_TODAS
    card_template = "activities/_kanban_activity_card.html"
    noun = ("demanda", "demandas")
    search_placeholder = "Buscar demanda, cliente, obra…"
    list_url_name = "activity-kanban"
    orderings = {
        "prazo": ("Prazo", [("deadline", "requested_deadline"), "created_at"], "asc"),
        "criacao": ("Data de criação", ["created_at"], "desc"),
        "titulo": ("Título", ["title"], "asc"),
        "dono": ("Responsável", [("owner", "owner__first_name"), "owner__username"], "asc"),
    }
    default_ordering = "prazo"
    card_permissions = {
        "set_stage": (catalog.ATIVIDADE_DEFINIR_ETAPA, catalog.ATIVIDADE_MOVER_ESTAGIO),
        "set_condition": (catalog.ATIVIDADE_DEFINIR_CONDICAO,),
        "cancel": (catalog.ATIVIDADE_CANCELAR,),
    }

    def item_queryset(self):
        return (
            Activity.objects.filter(organization=self.organization)
            .exclude(status=Activity.Status.RASCUNHO)
            .select_related("owner", "client", "site", "sector", "stage", "condition")
        )

    def involvement(self, queryset):
        mine = Task.objects.filter(activity=OuterRef("pk")).filter(
            Q(responsavel=self.user)
            | Exists(TaskExecutor.objects.filter(task=OuterRef("pk"), user=self.user, removed_at__isnull=True))
        )
        return queryset.filter(Q(owner=self.user) | Exists(mine))

    def apply_filters(self, queryset):
        filters = self.filters
        if filters["concluidas"]:
            queryset = queryset.filter(status__in=ACTIVITY_TERMINAL)
        elif filters["status"]:
            queryset = queryset.filter(status=filters["status"])
        else:
            queryset = queryset.exclude(status__in=ACTIVITY_TERMINAL)
        if filters["q"]:
            queryset = queryset.filter(
                Q(title__icontains=filters["q"])
                | Q(code__icontains=code_search_term(filters["q"]))
                | Q(client__name__icontains=filters["q"])
                | Q(site__name__icontains=filters["q"])
            )
        if filters["pessoa"] == "sem":
            queryset = queryset.filter(owner__isnull=True)
        elif _int_or_none(filters["pessoa"]) is not None:
            queryset = queryset.filter(owner_id=int(filters["pessoa"]))
        if _int_or_none(filters["condicao"]) is not None:
            queryset = queryset.filter(condition_id=int(filters["condicao"]))
        if _int_or_none(filters["estagio"]) is not None:
            queryset = queryset.filter(stage_id=int(filters["estagio"]))
        if _int_or_none(filters["cliente"]) is not None:
            queryset = queryset.filter(client_id=int(filters["cliente"]))
        if _int_or_none(filters["obra"]) is not None:
            queryset = queryset.filter(site_id=int(filters["obra"]))
        if filters["bloqueio"] or filters["filtro"] == "bloqueadas":
            queryset = queryset.filter(status=Activity.Status.BLOQUEADA)
        queryset = self._deadline_filter(queryset, filters["prazo"])
        return self.tag_filter(queryset, Activity.tags.through, "activity_id")

    @staticmethod
    def _deadline_filter(queryset, choice):
        now = timezone.now()
        if choice == "atrasadas":
            return queryset.filter(requested_deadline__lt=now).exclude(status__in=ACTIVITY_TERMINAL)
        if choice == "hoje":
            return queryset.filter(requested_deadline__date=timezone.localdate())
        if choice == "7_dias":
            return queryset.filter(requested_deadline__gte=now, requested_deadline__lte=now + timedelta(days=7))
        if choice == "30_dias":
            return queryset.filter(requested_deadline__gte=now, requested_deadline__lte=now + timedelta(days=30))
        if choice == "sem_prazo":
            return queryset.filter(requested_deadline__isnull=True)
        return queryset

    def decorate_item(self, item, now):
        item.deadline = item.requested_deadline
        item.is_overdue = bool(item.deadline and item.deadline < now and item.status not in ACTIVITY_TERMINAL)
        item.person = item.owner
        item.place = item.site.name if item.site_id else (item.client.name if item.client_id else "")
        item.can_cancel = item.status not in ACTIVITY_TERMINAL and item.perm["cancel"]

    def set_stage(self, item, stage):
        return ActivityService.set_stage(item, stage, self.user)

    def set_condition(self, item, condition):
        return ActivityService.set_condition(item, condition, self.user)


class TaskBoard(Board):
    slug = "tarefas"
    stage_domain = "tarefa"
    condition_domain = WorkflowStatus.Domain.TASK
    stage_model = TaskStage
    stage_service = TaskStageService
    view_action = catalog.TAREFA_VISUALIZAR
    card_template = "activities/_kanban_task_card.html"
    noun = ("tarefa", "tarefas")
    search_placeholder = "Buscar tarefa, demanda, cliente ou obra…"
    list_url_name = "task-kanban"
    orderings = {
        "prazo": ("Prazo comprometido", [("deadline", "effective_deadline"), "created_at"], "asc"),
        "solicitado": ("Prazo solicitado", [("deadline", "requested_deadline"), "created_at"], "asc"),
        "criacao": ("Data de criação", ["created_at"], "desc"),
        "titulo": ("Título", ["title"], "asc"),
        "responsavel": ("Responsável", [("person", "responsavel__first_name"), "responsavel__username"], "asc"),
    }
    default_ordering = "prazo"
    card_permissions = {
        "set_stage": (catalog.TAREFA_DEFINIR_ETAPA, catalog.TAREFA_MOVER_ESTAGIO),
        "set_condition": (catalog.TAREFA_DEFINIR_CONDICAO,),
        "block": (catalog.TAREFA_BLOQUEAR,),
        "complete": (catalog.TAREFA_CONCLUIR,),
        "cancel": (catalog.TAREFA_CANCELAR,),
        "move_sector": (catalog.TAREFA_MOVER_SETOR,),
    }

    def item_queryset(self):
        return (
            Task.objects.filter(activity__organization=self.organization)
            .select_related(
                "activity", "activity__client", "activity__site", "sector", "stage", "condition", "responsavel"
            )
            .annotate(effective_deadline=Coalesce("committed_deadline", "requested_deadline"))
            # O motor de autorização usa os executores ativos de cada tarefa; trazê-los junto evita uma
            # consulta por tarefa e por ação avaliada.
            .prefetch_related(
                Prefetch(
                    "executors",
                    queryset=TaskExecutor.objects.filter(removed_at__isnull=True),
                    to_attr="active_executors",
                )
            )
        )

    def involvement(self, queryset):
        return queryset.filter(
            Q(responsavel=self.user)
            | Exists(TaskExecutor.objects.filter(task=OuterRef("pk"), user=self.user, removed_at__isnull=True))
        )

    def apply_filters(self, queryset):
        filters = self.filters
        if filters["concluidas"]:
            queryset = queryset.filter(status__in=TASK_TERMINAL)
        elif filters["status"]:
            queryset = queryset.filter(status=filters["status"])
        else:
            queryset = queryset.exclude(status__in=TASK_TERMINAL)
        if filters["q"]:
            queryset = queryset.filter(
                Q(title__icontains=filters["q"])
                | Q(activity__title__icontains=filters["q"])
                | Q(activity__code__icontains=code_search_term(filters["q"]))
                | Q(activity__client__name__icontains=filters["q"])
                | Q(activity__site__name__icontains=filters["q"])
            )
        if filters["pessoa"] == "sem":
            queryset = queryset.filter(responsavel__isnull=True)
        elif _int_or_none(filters["pessoa"]) is not None:
            queryset = queryset.filter(responsavel_id=int(filters["pessoa"]))
        participant = _int_or_none(filters["participante"])
        if participant is not None:
            queryset = queryset.filter(
                Exists(TaskExecutor.objects.filter(task=OuterRef("pk"), user_id=participant, removed_at__isnull=True))
            )
        if filters["filtro"] == "em-fila":
            queryset = queryset.filter(status=Task.Status.EM_FILA)
        elif filters["filtro"] == "em-execucao":
            queryset = queryset.filter(status=Task.Status.EM_EXECUCAO)
        elif filters["filtro"] == "devolvidas":
            queryset = queryset.filter(status=Task.Status.DEVOLVIDA)
        elif filters["filtro"] == "bloqueadas":
            queryset = queryset.filter(status=Task.Status.BLOQUEADA)
        if _int_or_none(filters["estagio"]) is not None:
            queryset = queryset.filter(stage_id=int(filters["estagio"]))
        if _int_or_none(filters["condicao"]) is not None:
            queryset = queryset.filter(condition_id=int(filters["condicao"]))
        if _int_or_none(filters["cliente"]) is not None:
            queryset = queryset.filter(activity__client_id=int(filters["cliente"]))
        if _int_or_none(filters["obra"]) is not None:
            queryset = queryset.filter(activity__site_id=int(filters["obra"]))
        if filters["bloqueio"] or filters["filtro"] == "bloqueadas":
            queryset = queryset.filter(status=Task.Status.BLOQUEADA)
        queryset = self._deadline_filter(queryset, filters["prazo"])
        return self.tag_filter(queryset, Task.tags.through, "task_id")

    @staticmethod
    def _deadline_filter(queryset, choice):
        now = timezone.now()
        if choice == "atrasadas":
            return queryset.filter(
                Q(committed_deadline__lt=now) | Q(requested_deadline__lt=now)
            ).exclude(status__in=TASK_TERMINAL)
        if choice == "hoje":
            today = timezone.localdate()
            return queryset.filter(Q(committed_deadline__date=today) | Q(requested_deadline__date=today))
        if choice == "7_dias":
            return queryset.filter(
                Q(committed_deadline__gte=now, committed_deadline__lte=now + timedelta(days=7))
                | Q(requested_deadline__gte=now, requested_deadline__lte=now + timedelta(days=7))
            )
        if choice == "30_dias":
            return queryset.filter(
                Q(committed_deadline__gte=now, committed_deadline__lte=now + timedelta(days=30))
                | Q(requested_deadline__gte=now, requested_deadline__lte=now + timedelta(days=30))
            )
        if choice == "sem_prazo":
            return queryset.filter(committed_deadline__isnull=True, requested_deadline__isnull=True)
        return queryset

    def decorate_item(self, item, now):
        item.deadline = item.committed_deadline or item.requested_deadline
        item.is_overdue = bool(item.deadline and item.deadline < now and item.status not in TASK_TERMINAL)
        item.person = item.responsavel
        open_task = item.status not in TASK_TERMINAL
        item.is_blocked = item.status == Task.Status.BLOQUEADA
        item.can_block = open_task and not item.is_blocked and item.perm["block"]
        item.can_unblock = item.is_blocked and item.perm["block"]
        item.can_complete = item.status in (
            Task.Status.EM_EXECUCAO, Task.Status.EM_FILA, Task.Status.DISPONIVEL, Task.Status.DEVOLVIDA
        ) and item.perm["complete"]
        item.can_cancel = open_task and item.perm["cancel"]
        item.can_move_sector = open_task and item.perm["move_sector"]

    def set_stage(self, item, stage):
        return TaskService.set_stage(item, stage, self.user)

    def set_condition(self, item, condition):
        return TaskService.set_condition(item, condition, self.user)


BOARDS = {DemandBoard.slug: DemandBoard, TaskBoard.slug: TaskBoard}


def workflow_context(item, user, slug):
    """Etapa, Condição e o que a pessoa pode mexer, para os seletores da gaveta de uma Demanda/Tarefa."""
    permissions = DemandBoard.card_permissions if slug == "demandas" else TaskBoard.card_permissions
    checks = [(action, item) for name in ("set_stage", "set_condition") for action in permissions[name]]
    access = AuthorizationService.can_many(user, checks)
    sector = item.sector if item.sector_id else None
    return {
        "domain": slug,
        "sector": sector,
        "stage": item.stage,
        "condition": item.condition,
        "can_set_stage": bool(sector) and any(access[(a, item.pk)] for a in permissions["set_stage"]),
        "can_set_condition": bool(sector) and any(access[(a, item.pk)] for a in permissions["set_condition"]),
        "can_manage_stages": bool(sector) and AuthorizationService.can(user, catalog.ETAPA_GERIR, sector),
        "can_manage_conditions": bool(sector) and AuthorizationService.can(user, catalog.CONDICAO_GERIR, sector),
    }


# ---------------------------------------------------------------------------
# Telas
# ---------------------------------------------------------------------------


class KanbanBoardView(OrganizationRequiredMixin, TemplateView):
    board_class = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.board_class(self.request, self.organization).context())
        return context


class ActivityKanbanView(KanbanBoardView):
    template_name = "activities/activity_kanban.html"
    board_class = DemandBoard


class TaskKanbanView(KanbanBoardView):
    template_name = "activities/task_kanban.html"
    board_class = TaskBoard


# ---------------------------------------------------------------------------
# Ações (JSON). Sempre via service: aqui só se resolve o objeto e se devolve o cartão novo.
# ---------------------------------------------------------------------------


def _failure(message, status=400):
    return JsonResponse({"success": False, "message": message}, status=status)


class KanbanActionView(OrganizationRequiredMixin, View):
    def board(self, domain):
        board_class = BOARDS.get(domain)
        if board_class is None:
            raise Http404("Quadro desconhecido.")
        return board_class(self.request, self.organization)


class KanbanCardView(KanbanActionView):
    """O cartão como está agora, ou `visible: false` se saiu do quadro (concluída, filtro, outra etapa de outro setor)."""

    def get(self, request, domain, pk):
        board = self.board(domain)
        item = board.visible_items().filter(pk=pk).first()
        if item is None:
            return JsonResponse({"success": True, "visible": False})
        item = board.decorate([item])[0]
        return JsonResponse(
            {"success": True, "visible": True, "stage_id": item.stage_id, "card_html": board.render_card(item)}
        )


class KanbanSetStageView(KanbanActionView):
    """Arrastar entre colunas (ou escolher a etapa num seletor): grava só a etapa."""

    http_method_names = ["post"]

    def post(self, request, domain, pk):
        board = self.board(domain)
        item = get_object_or_404(board.item_queryset(), pk=pk)
        stage_id = _int_or_none(request.POST.get("stage_id"))
        if stage_id is None:
            return _failure("Escolha uma etapa.")
        stage = get_object_or_404(board.stage_model, pk=stage_id, organization=self.organization)
        try:
            board.set_stage(item, stage)
        except ActivityError as exc:
            return _failure(str(exc), status=403)
        item = board.item_or_404(pk)
        return JsonResponse(
            {
                "success": True,
                "message": f"Etapa alterada para {stage.name}.",
                "stage_id": stage.pk,
                "stage_name": stage.name,
                "card_html": board.render_card(item),
            }
        )


class KanbanSetConditionView(KanbanActionView):
    http_method_names = ["post"]

    def post(self, request, domain, pk):
        board = self.board(domain)
        item = get_object_or_404(board.item_queryset(), pk=pk)
        condition_id = _int_or_none(request.POST.get("condition_id"))
        condition = None
        if condition_id is not None:
            condition = get_object_or_404(
                WorkflowStatus, pk=condition_id, organization=self.organization, domain=board.condition_domain
            )
        try:
            board.set_condition(item, condition)
        except ActivityError as exc:
            return _failure(str(exc), status=403)
        item = board.item_or_404(pk)
        return JsonResponse(
            {
                "success": True,
                "message": f"Condição alterada para {condition.name}." if condition else "Condição removida.",
                "condition_name": condition.name if condition else "",
                "card_html": board.render_card(item),
            }
        )


class KanbanCreateCardView(KanbanActionView):
    """Criar uma Demanda direto na coluna: só o nome. Setor e etapa vêm do quadro; dono é quem criou."""

    http_method_names = ["post"]

    def post(self, request, domain):
        if domain != DemandBoard.slug:
            return _failure("Uma tarefa precisa de uma demanda: use o botão de nova tarefa.")
        board = self.board(domain)
        title = " ".join(request.POST.get("title", "").split())
        if not title:
            return _failure("Informe o nome da demanda.")
        if len(title) > TITLE_MAX_LENGTH:
            return _failure(f"O nome da demanda pode ter até {TITLE_MAX_LENGTH} caracteres.")
        sector = next((s for s in board.sectors if s.pk == _int_or_none(request.POST.get("sector_id"))), None)
        if sector is None:
            return _failure("Escolha um setor do quadro.", status=403)
        stage = None
        stage_id = _int_or_none(request.POST.get("stage_id"))
        if stage_id is not None:
            stage = get_object_or_404(board.stage_model, pk=stage_id, organization=self.organization, sector=sector)
        try:
            activity = ActivityService.create_activity(
                organization=self.organization, title=title, owner=request.user, created_by=request.user, sector=sector
            )
        except ActivityError as exc:
            return _failure(str(exc), status=403)
        note = ""
        if stage is not None and activity.stage_id != stage.pk:
            try:
                ActivityService.set_stage(activity, stage, request.user)
            except ActivityError:
                note = " Ela ficou na etapa padrão do setor: você não pode escolher a etapa."
        item = board.item_or_404(activity.pk)
        return JsonResponse(
            {
                "success": True,
                "message": f"Demanda criada.{note}",
                "id": item.pk,
                "stage_id": item.stage_id,
                "card_html": board.render_card(item),
            },
            status=201,
        )


class KanbanColumnLimitView(KanbanActionView):
    """Limite informativo da coluna: o contador avisa quando passa, nada é bloqueado."""

    http_method_names = ["post"]

    def post(self, request, domain):
        board = self.board(domain)
        stage = get_object_or_404(board.stage_model, pk=_int_or_none(request.POST.get("stage_id")), organization=self.organization)
        if not AuthorizationService.can(request.user, catalog.ETAPA_GERIR, stage):
            return _failure("Você não pode gerir as etapas deste setor.", status=403)
        raw = request.POST.get("limit", "").strip()
        limit = None
        if raw:
            limit = _int_or_none(raw)
            if limit is None or not 1 <= limit <= 999:
                return _failure("Informe um limite entre 1 e 999, ou deixe vazio para remover.")
        stage.column_limit = limit
        stage.save(update_fields=["column_limit"])
        return JsonResponse(
            {
                "success": True,
                "limit": limit,
                "message": f"Limite da coluna definido em {limit}." if limit else "Limite da coluna removido.",
            }
        )


class KanbanCreateOptionView(KanbanActionView):
    """Nova Etapa ou nova Condição do setor, criada sem sair do quadro (quem gere o catálogo)."""

    http_method_names = ["post"]

    def post(self, request, domain):
        board = self.board(domain)
        sector = get_object_or_404(
            Sector, pk=_int_or_none(request.POST.get("sector_id")), organization=self.organization, is_active=True
        )
        kind = request.POST.get("kind")
        name = request.POST.get("name", "")
        color = request.POST.get("color") or DEFAULT_OPTION_COLOR
        if kind == "stage":
            action = catalog.ETAPA_GERIR
        elif kind == "condition":
            action = catalog.CONDICAO_GERIR
        else:
            return _failure("Informe se é uma etapa ou uma condição.")
        if not AuthorizationService.can(request.user, action, sector):
            return _failure("Você não pode gerir as opções deste setor.", status=403)
        try:
            if kind == "stage":
                option = board.stage_service.create(self.organization, sector, name, created_by=request.user, color=color)
            else:
                option = WorkflowStatusService.create(
                    self.organization, name=name, domain=board.condition_domain, sector=sector,
                    created_by=request.user, color=color,
                )
        except CadastroError as exc:
            return _failure(str(exc))
        return JsonResponse(
            {
                "success": True,
                "message": "Etapa criada." if kind == "stage" else "Condição criada.",
                "item": {"id": option.pk, "name": option.name, "color": option.color, "is_default": option.is_default},
            },
            status=201,
        )


class ActivityKanbanDrawerView(OrganizationRequiredMixin, View):
    """Gaveta da Demanda aberta a partir do quadro: o essencial sem sair dele. A ficha completa continua a um clique."""

    def get(self, request, pk):
        activity = get_object_or_404(
            Activity.objects.select_related("owner", "client", "site", "sector", "stage", "condition"),
            pk=pk,
            organization=self.organization,
        )
        if activity.status == Activity.Status.RASCUNHO:
            raise Http404("Rascunho não tem gaveta.")
        user = request.user
        tasks = list(
            activity.tasks.select_related("responsavel", "sector", "stage").order_by("order", "created_at")
        )
        access = AuthorizationService.can_many(
            user, [(catalog.ATIVIDADE_EDITAR, activity), (catalog.COMUNICACAO_PARTICIPAR, activity)]
        )
        context = {
            "activity": activity,
            "tasks": tasks,
            "workflow": workflow_context(activity, user, "demandas"),
            "activity_messages": list(
                ActivityMessage.objects.filter(activity=activity).select_related("author").order_by("-created_at")[:MAX_DRAWER_MESSAGES]
            ),
            "attachments": list(activity.attachments.all()[:10]),
            "history": list(
                AuditLog.objects.filter(activity=activity).select_related("user").order_by("-timestamp")[:MAX_DRAWER_HISTORY]
            ),
            "message_kind_choices": MessageKind.choices,
            "can_edit": access[(catalog.ATIVIDADE_EDITAR, activity.pk)],
            "can_message": access[(catalog.COMUNICACAO_PARTICIPAR, activity.pk)],
            "is_open": activity.status not in ACTIVITY_TERMINAL,
        }
        return render(request, "activities/_activity_drawer.html", context)
