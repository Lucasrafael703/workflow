from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Avg, Count, Exists, F, OuterRef, Prefetch, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DetailView, FormView, ListView, TemplateView, View

from audit.models import AuditLog
from acessos import catalog
from acessos.services import AuthorizationService
from core.mixins import ActionRequiredMixin, OrganizationRequiredMixin, user_sectors
from core.models import ActivityStage, Client, CostCenter, Sector, Site, Tag, TaskStage, WorkflowStatus
from notifications.models import Notification
from notifications.services import NotificationService
from processes.models import ActivityCriterionCheck, ActivityInputValue

from .forms import (
    ActivityApprovePendencyForm,
    ActivityAttachmentForm,
    ActivityDeadlineChangeForm,
    ActivityFinalizeForm,
    ActivityPendingForm,
    ActivityWizardStep2Form,
    ActivityWizardStep3Form,
    AssignmentRejectForm,
    CancelForm,
    ChangeOwnerForm,
    ConflictResolutionForm,
    DeadlineProposalForm,
    ExecutorForm,
    ManualTimeForm,
    MessageForm,
    MoveSectorForm,
    ProcessApplyForm,
    ReorderForm,
    RetroactiveWorkForm,
    TaskBlockForm,
    TaskChangeResponsavelForm,
    TaskDependencyForm,
    TaskEditorForm,
    TaskQuickCreateForm,
    TaskQuickCreateStandaloneForm,
    TaskReturnForm,
    activity_summary,
)
from .models import (
    Activity,
    ActivityAttachment,
    ActivityPendency,
    DeadlineConflict,
    DeadlineProposal,
    MessageKind,
    QueueEntry,
    Task,
    TaskAssignment,
    TaskChecklistItem,
    TaskExecutor,
    TaskReturn,
    code_search_term,
)
from .activity_editor import ActivityCreateView, ActivityEditView, ActivityMiniCreateView
from .filtering import canonical_filter_querystring, filter_state_for_template, normalize_workspace_filters
from .navigation import activity_return_url
from . import process_state
from .process_application import ActivityProcessService, ProcessApplicationService
from .services import (
    RETROACTIVE_JUSTIFICATION_DAYS,
    ActivityAttachmentService,
    ActivityError,
    ActivityService,
    DeadlineService,
    MessageService,
    QueueService,
    TaskService,
    WorkTimeService,
)


User = get_user_model()


def _is_ajax(request):
    """Requisição feita pelo modal via JS (LPSModal.open), não navegação de página."""
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"

OPEN_TASK_STATUSES = [
    Task.Status.DISPONIVEL,
    Task.Status.EM_FILA,
    Task.Status.EM_EXECUCAO,
    Task.Status.BLOQUEADA,
]

#: Etapa criada por um processo que ainda espera a anterior: `DISPONIVEL`, fora
#: da fila, com predecessora não concluída. Não é "próxima tarefa" de ninguém.
WAITING_ON_DEPENDENCY = Q(status=Task.Status.DISPONIVEL, depends_on__isnull=False) & ~Q(
    depends_on__status=Task.Status.CONCLUIDA
)


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def filtered_tasks_queryset(request, organization):
    """Filtro de tarefas compartilhado entre Lista, Kanban, Calendário e
    visão por Atividade — mesmos parâmetros GET (tab/status/filtro/q/sector),
    para as 4 visualizações sempre mostrarem exatamente o mesmo subconjunto,
    só reagrupado/re-renderizado de formas diferentes."""
    user = request.user
    filters = normalize_workspace_filters(request)
    tab = filters["tab"]
    queryset = Task.objects.filter(activity__organization=organization)

    if tab == "setor":
        queryset = queryset.filter(sector__in=user_sectors(user))
    elif tab == "participando":
        queryset = queryset.filter(
            executors__user=user, executors__removed_at__isnull=True
        ).exclude(responsavel=user)
    elif tab == "concluidas":
        queryset = queryset.filter(
            Q(responsavel=user) | Q(executors__user=user, executors__removed_at__isnull=True)
        )
    else:
        queryset = queryset.filter(responsavel=user)

    if filters["concluidas"] or tab == "concluidas":
        queryset = queryset.filter(status__in=[Task.Status.CONCLUIDA, Task.Status.CANCELADA])
    elif filters["status"]:
        queryset = queryset.filter(status=filters["status"])
    else:
        queryset = queryset.filter(status__in=OPEN_TASK_STATUSES)

    # Visões salvas por condição operacional, no lugar de segmentações
    # comerciais (Benchmark §3: atrasadas, bloqueadas, devolvidas).
    view = filters["filtro"]
    if view == "atrasadas":
        queryset = queryset.filter(
            Q(committed_deadline__lt=timezone.now()) | Q(requested_deadline__lt=timezone.now())
        ).exclude(status__in=[Task.Status.CONCLUIDA, Task.Status.CANCELADA])
    elif view == "bloqueadas":
        queryset = queryset.filter(status=Task.Status.BLOQUEADA)
    elif view == "devolvidas":
        queryset = queryset.filter(status=Task.Status.DEVOLVIDA)
    elif view == "em-execucao":
        queryset = queryset.filter(status=Task.Status.EM_EXECUCAO)
    elif view == "em-fila":
        queryset = queryset.filter(status=Task.Status.EM_FILA)
    elif view == "hoje":
        today = timezone.localdate()
        queryset = queryset.filter(
            Q(committed_deadline__date=today) | Q(requested_deadline__date=today)
        )
    elif filters["prazo"] == "atrasadas":
        queryset = queryset.filter(
            Q(committed_deadline__lt=timezone.now()) | Q(requested_deadline__lt=timezone.now())
        ).exclude(status__in=[Task.Status.CONCLUIDA, Task.Status.CANCELADA])
    elif filters["prazo"] == "hoje":
        today = timezone.localdate()
        queryset = queryset.filter(
            Q(committed_deadline__date=today) | Q(requested_deadline__date=today)
        )
    elif filters["prazo"] == "7_dias":
        queryset = queryset.filter(
            Q(committed_deadline__gte=timezone.now(), committed_deadline__lte=timezone.now() + timedelta(days=7))
            | Q(requested_deadline__gte=timezone.now(), requested_deadline__lte=timezone.now() + timedelta(days=7))
        )
    elif filters["prazo"] == "30_dias":
        queryset = queryset.filter(
            Q(committed_deadline__gte=timezone.now(), committed_deadline__lte=timezone.now() + timedelta(days=30))
            | Q(requested_deadline__gte=timezone.now(), requested_deadline__lte=timezone.now() + timedelta(days=30))
        )
    elif filters["prazo"] == "sem_prazo":
        queryset = queryset.filter(committed_deadline__isnull=True, requested_deadline__isnull=True)

    search = filters["q"]
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(activity__title__icontains=search)
            | Q(activity__client__name__icontains=search)
            | Q(activity__site__name__icontains=search)
        )

    sector = filters["setor"]
    if sector:
        queryset = queryset.filter(sector_id=sector)
    condition = filters["condicao"]
    if condition:
        queryset = queryset.filter(condition_id=condition)
    stage = filters["estagio"]
    if stage:
        queryset = queryset.filter(stage_id=stage)
    if filters["cliente"]:
        queryset = queryset.filter(activity__client_id=filters["cliente"])
    if filters["obra"]:
        queryset = queryset.filter(activity__site_id=filters["obra"])
    if filters["tag"]:
        queryset = queryset.filter(tags__pk=filters["tag"])
    if filters["pessoa"] == "sem":
        queryset = queryset.filter(responsavel__isnull=True)
    elif filters["pessoa"] == "eu":
        queryset = queryset.filter(responsavel=user)
    elif _int_or_none(filters["pessoa"]) is not None:
        queryset = queryset.filter(responsavel_id=_int_or_none(filters["pessoa"]))
    if filters["participante"]:
        queryset = queryset.filter(
            executors__user_id=filters["participante"], executors__removed_at__isnull=True
        )

    return (
        queryset.select_related(
            "activity",
            "activity__client",
            "activity__site",
            "activity__cost_center",
            "sector",
            "stage",
            "condition",
            "responsavel",
            "depends_on",
        )
        .prefetch_related(
            Prefetch(
                "executors",
                queryset=TaskExecutor.objects.filter(removed_at__isnull=True).select_related("user"),
                to_attr="active_executors",
            )
        )
        .distinct()
    )


def _task_stats(request, organization):
    """Contadores da barra de estatísticas: só reagem à troca de aba
    (`tab`), nunca aos filtros pontuais (`filtro`/`status`/`q`/`sector`) —
    senão os cards mudariam de número ao aplicar um filtro secundário, o
    que contradiria a própria ideia de "visão geral fixa"."""
    user = request.user
    tab = request.GET.get("tab", "minhas")
    queryset = Task.objects.filter(activity__organization=organization)
    if tab == "setor":
        queryset = queryset.filter(sector__in=user_sectors(user))
    elif tab == "participando":
        queryset = queryset.filter(
            executors__user=user, executors__removed_at__isnull=True
        ).exclude(responsavel=user)
    elif tab == "concluidas":
        queryset = queryset.filter(
            Q(responsavel=user) | Q(executors__user=user, executors__removed_at__isnull=True)
        )
    else:
        queryset = queryset.filter(responsavel=user)
    queryset = queryset.filter(status__in=OPEN_TASK_STATUSES).distinct()

    return {
        "total": queryset.count(),
        "in_progress": queryset.filter(status=Task.Status.EM_EXECUCAO).count(),
        "queued": queryset.filter(status=Task.Status.EM_FILA).count(),
        "overdue": queryset.filter(committed_deadline__lt=timezone.now()).count(),
        "blocked": queryset.filter(status=Task.Status.BLOQUEADA).count(),
    }


def task_filter_context(request, organization):
    """Contexto dos filtros/abas comuns às 4 visualizações de tarefa, mais a
    querystring atual sem `visao`/`page`/`sort`/`dir` — usada por cada aba do
    seletor de visão e por cada cabeçalho de coluna ordenável para montar seu
    link preservando os demais filtros ativos, sem duplicar `sort`/`dir`."""
    filters = normalize_workspace_filters(request)
    return {
        "tab": filters["tab"],
        "status": "concluidas" if filters["concluidas"] else filters["status"] or "abertas",
        "view_filter": filters["filtro"],
        "search": filters["q"],
        "has_filters": any(filters[key] for key in ("q", "pessoa", "setor", "condicao", "estagio", "filtro", "cliente", "obra", "tag", "participante", "prazo", "bloqueio", "concluidas", "status", "dir")) or filters["ordem"] != "prazo",
        "sectors": Sector.objects.filter(organization=organization, is_active=True),
        "selected_sector": filters["setor"],
        "selected_stage": filters["estagio"],
        "filter_querystring": canonical_filter_querystring(
            request, keep_calendar=bool(filters["ano"] or filters["mes"])
        ),
        "workspace_filters": filters,
    }


def visual_filter_choice_groups(organization, domain, selected_sector_id=None):
    """Agrupa opções visuais por setor para não confundir nomes iguais."""
    stage_model = ActivityStage if domain == "demanda" else TaskStage
    condition_domain = WorkflowStatus.Domain.ACTIVITY if domain == "demanda" else WorkflowStatus.Domain.TASK
    sectors = Sector.objects.filter(organization=organization, is_active=True).order_by("name")
    if selected_sector_id:
        sectors = sectors.filter(pk=selected_sector_id)
    sectors = list(sectors)
    sector_ids = [sector.pk for sector in sectors]
    stage_map, condition_map = {}, {}
    for stage in stage_model.objects.filter(
        organization=organization, sector_id__in=sector_ids, is_active=True
    ).order_by("sector__name", "order", "name"):
        stage_map.setdefault(stage.sector_id, []).append(stage)
    for condition in WorkflowStatus.objects.filter(
        organization=organization, sector_id__in=sector_ids, domain=condition_domain, is_active=True
    ).order_by("sector__name", "order", "name"):
        condition_map.setdefault(condition.sector_id, []).append(condition)
    return (
        [(sector.name, stage_map[sector.pk]) for sector in sectors if stage_map.get(sector.pk)],
        [(sector.name, condition_map[sector.pk]) for sector in sectors if condition_map.get(sector.pk)],
    )


def build_filter_toolbar_state(request, organization, *, domain, view_mode, sectors, stage_groups=None, condition_groups=None, board=False, sector=None, orderings=None, default_order="prazo", year="", month=""):
    state = filter_state_for_template(
        request,
        domain=domain,
        view_mode=view_mode,
        sectors=sectors,
        people=User.objects.filter(profile__organization=organization, is_active=True).order_by("first_name", "username"),
        clients=Client.objects.filter(organization=organization, is_active=True).order_by("name"),
        sites=Site.objects.filter(organization=organization, is_active=True).order_by("name"),
        tags=Tag.objects.filter(organization=organization, is_active=True).order_by("name"),
        stage_groups=stage_groups,
        condition_groups=condition_groups,
        board=board,
        orderings=orderings,
        default_order=default_order,
        year=year,
        month=month,
    )
    if sector is not None:
        state["sector_obj"] = sector
        state["setor"] = str(sector.pk)
    else:
        state["sector_obj"] = None
    return state


# ---------------------------------------------------------------------------
# Helpers compartilhados
# ---------------------------------------------------------------------------


def queue_position(task):
    """Posição viva na fila, sempre no formato "4 de 17" (doc 09 §97-98).

    O total é contado agora, nunca lido de `queue_size_at_entry`, que envelhece.
    """
    entry = task.queue_entries.filter(left_at__isnull=True).select_related("sector").first()
    if entry is None:
        return None
    total = QueueEntry.objects.filter(sector_id=entry.sector_id, left_at__isnull=True).count()
    return {"entry": entry, "position": entry.position, "total": total, "sector": entry.sector}


def _next_attention(tasks):
    """A tarefa que mais precisa de atenção agora, entre as ainda abertas —
    "Onde está o problema?" em vez de uma lista neutra. Ordem de prioridade:
    bloqueada > mais atrasada > com decisão de prazo parada > próxima a
    vencer. Retorna None se não houver nenhuma tarefa aberta com sinal de
    atenção ou prazo definido. `attention_reason` vai junto para o template
    não precisar comparar datas de novo."""
    blocked = [t for t in tasks if t.status == Task.Status.BLOQUEADA]
    if blocked:
        blocked[0].attention_reason = "blocked"
        return blocked[0]

    now = timezone.now()
    overdue = [
        t
        for t in tasks
        if t.status not in (Task.Status.CONCLUIDA, Task.Status.CANCELADA)
        and t.committed_deadline
        and t.committed_deadline < now
    ]
    if overdue:
        task = min(overdue, key=lambda t: t.committed_deadline)
        task.attention_reason = "overdue"
        return task

    pending_decision = [
        t
        for t in tasks
        if t.status not in (Task.Status.CONCLUIDA, Task.Status.CANCELADA)
        and (t.has_pending_proposal or t.has_open_conflict)
    ]
    if pending_decision:
        pending_decision[0].attention_reason = "negotiating"
        return pending_decision[0]

    open_with_deadline = [
        t
        for t in tasks
        if t.status in (Task.Status.EM_EXECUCAO, Task.Status.EM_FILA, Task.Status.DISPONIVEL)
        and (t.committed_deadline or t.requested_deadline)
    ]
    if open_with_deadline:
        task = min(open_with_deadline, key=lambda t: t.committed_deadline or t.requested_deadline)
        task.attention_reason = "upcoming"
        return task

    return None


def can(user, action_key, resource=None):
    """Atalho de leitura para os templates decidirem o que exibir.

    Esconder botão é experiência do usuário, não segurança: a decisão real é
    refeita na camada de serviço (Regras 05 §42).
    """
    return AuthorizationService.can(user, action_key, resource)


def pending_items(user, organization):
    """O que está esperando uma decisão desta pessoa (doc 09 §26)."""
    owned = Activity.objects.filter(organization=organization, owner=user)
    proposals = (
        DeadlineProposal.objects.filter(
            task__activity__in=owned, status=DeadlineProposal.Status.PENDENTE
        )
        .select_related("task", "task__activity", "proposed_by")
        .order_by("-proposed_at")
    )
    conflicts = (
        DeadlineConflict.objects.filter(
            task__activity__organization=organization, status=DeadlineConflict.Status.ABERTO
        )
        .select_related("task", "task__activity")
        .order_by("-opened_at")
    )
    resolvable = AuthorizationService.accessible_sector_ids(user, catalog.ESCALONAMENTO_RESOLVER)
    conflicts = conflicts.filter(
        Q(task__sector_id__in=resolvable) | Q(task__activity__owner=user)
    )
    assignments = (
        TaskAssignment.objects.filter(
            task__activity__organization=organization, user=user, status=TaskAssignment.Status.PENDENTE
        )
        .select_related("task", "task__activity", "assigned_by")
        .order_by("-assigned_at")
    )
    return {"proposals": proposals, "conflicts": conflicts, "assignments": assignments}


class ServiceActionView(OrganizationRequiredMixin, View):
    """Base para ações POST: chama o serviço, traduz erro em mensagem e volta."""

    def perform(self, request, *args, **kwargs):
        raise NotImplementedError

    def redirect_to(self):
        referer = self.request.META.get("HTTP_REFERER")
        if referer and url_has_allowed_host_and_scheme(
            referer, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure()
        ):
            return referer
        return reverse("home")

    def post(self, request, *args, **kwargs):
        try:
            self.perform(request, *args, **kwargs)
        except ActivityError as exc:
            messages.error(request, str(exc))
        return redirect(self.redirect_to())


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------


class HomeView(OrganizationRequiredMixin, TemplateView):
    """Responde "O que precisa da minha atenção agora?" (doc 09 §20-27)."""

    template_name = "activities/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        org = self.organization

        my_sectors = user_sectors(user)

        next_tasks = list(
            Task.objects.filter(
                activity__organization=org,
                status__in=[Task.Status.DISPONIVEL, Task.Status.EM_FILA],
            )
            .exclude(WAITING_ON_DEPENDENCY)
            .filter(
                Q(responsavel=user)
                | Q(executors__user=user, executors__removed_at__isnull=True)
                | Q(sector__in=my_sectors)
            )
            .select_related("activity", "sector")
            .distinct()
            .order_by("requested_deadline", "created_at")[:8]
        )

        followed = list(
            Activity.objects.filter(organization=org, owner=user)
            .exclude(status__in=[Activity.Status.CONCLUIDA, Activity.Status.CANCELADA, Activity.Status.RASCUNHO])
            .select_related("stage")
            .annotate(
                total_tasks=Count("tasks", distinct=True),
                done_tasks=Count("tasks", filter=Q(tasks__status=Task.Status.CONCLUIDA), distinct=True),
            )
            .order_by("requested_deadline", "-created_at")[:6]
        )
        decorate_task_statuses(next_tasks, org)
        decorate_activity_cards(followed, org)

        pending = pending_items(user, org)

        # Cartões do topo: só número que leva a uma ação (Benchmark §8.3).
        my_open = Task.objects.filter(
            Q(responsavel=user) | Q(executors__user=user, executors__removed_at__isnull=True),
            activity__organization=org,
        ).exclude(status__in=[Task.Status.CONCLUIDA, Task.Status.CANCELADA]).distinct()

        summary = {
            "open_tasks": my_open.count(),
            "overdue": my_open.filter(
                committed_deadline__lt=timezone.now(),
            ).exclude(status=Task.Status.CONCLUIDA).count(),
            "blocked": my_open.filter(status=Task.Status.BLOQUEADA).count(),
            "waiting_decision": pending["proposals"].count() + pending["conflicts"].count() + pending["assignments"].count(),
        }

        context.update(
            {
                "next_tasks": next_tasks,
                "pending": pending,
                "summary": summary,
                "followed_activities": followed,
                "unread_notifications": user.notifications.filter(is_read=False)[:5],
                "my_sectors": my_sectors,
            }
        )
        return context


# ---------------------------------------------------------------------------
# Atividades
# ---------------------------------------------------------------------------


ACTIVITY_FILTER_KEYS = (
    "status",
    "estagio",
    "condicao",
    "prazo",
    "urgencia",
    "cliente",
    "grupo",
    "centro_custo",
    "criado_de",
    "criado_ate",
    "prazo_de",
    "prazo_ate",
)

ACTIVITY_ORDERINGS = {
    "prazo": ("requested_deadline", "-created_at"),
    "recentes": ("-created_at",),
    "titulo": ("title",),
}


def filtered_activities_queryset(request, organization, *, order=True):
    """Filtro de atividades compartilhado entre Lista, Kanban e Calendário —
    mesmos parâmetros GET (tab/status/prazo/urgencia/cliente/grupo/
    centro_custo/datas/q), para as 3 visualizações sempre mostrarem
    exatamente o mesmo subconjunto, só reagrupado/re-renderizado de formas
    diferentes."""
    user = request.user
    filters = normalize_workspace_filters(request)
    tab = filters["tab"]
    queryset = Activity.objects.filter(organization=organization)

    if tab == "grupo":
        queryset = queryset.exclude(status=Activity.Status.RASCUNHO).filter(sector__in=user_sectors(user))
    elif tab == "participando":
        queryset = queryset.exclude(status=Activity.Status.RASCUNHO).filter(
            Q(tasks__responsavel=user)
            | Q(tasks__executors__user=user, tasks__executors__removed_at__isnull=True)
        ).exclude(owner=user)
    elif tab == "concluidas":
        queryset = queryset.exclude(status=Activity.Status.RASCUNHO).filter(
            Q(owner=user)
            | Q(tasks__responsavel=user)
            | Q(tasks__executors__user=user, tasks__executors__removed_at__isnull=True),
            status__in=[Activity.Status.CONCLUIDA, Activity.Status.CANCELADA],
        )
    elif tab == "todas":
        queryset = queryset.exclude(status=Activity.Status.RASCUNHO)
        if not can(user, catalog.ATIVIDADE_VISUALIZAR_TODAS):
            queryset = queryset.filter(owner=user)
    else:
        # Rascunho ainda pode não ter dono definido (só `created_by` é
        # garantido desde a etapa 1 do wizard) — sem isso, um rascunho salvo
        # e retomado depois fica sem nenhuma tela que o encontre de volta.
        queryset = queryset.filter(Q(owner=user) | Q(created_by=user, status=Activity.Status.RASCUNHO))

    search = filters["q"]
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(code__icontains=code_search_term(search))
            | Q(client__name__icontains=search)
            | Q(site__name__icontains=search)
        )

    status = filters["status"]
    if filters["concluidas"]:
        queryset = queryset.filter(status__in=[Activity.Status.CONCLUIDA, Activity.Status.CANCELADA])
    elif status:
        queryset = queryset.filter(status=status)
    elif tab != "concluidas":
        # Sem filtro explícito de status, cada visão esconde o que já
        # terminou — quem quiser ver concluída/cancelada escolhe o status.
        queryset = queryset.exclude(status__in=[Activity.Status.CONCLUIDA, Activity.Status.CANCELADA])

    if filters["filtro"] == "bloqueadas" or filters["bloqueio"]:
        queryset = queryset.filter(status=Activity.Status.BLOQUEADA)

    deadline = filters["prazo"]
    now = timezone.now()
    if deadline == "atrasadas":
        queryset = queryset.filter(requested_deadline__lt=now).exclude(
            status__in=[Activity.Status.CONCLUIDA, Activity.Status.CANCELADA]
        )
    elif deadline == "hoje":
        queryset = queryset.filter(requested_deadline__date=timezone.localdate())
    elif deadline == "7_dias":
        queryset = queryset.filter(
            requested_deadline__gte=now,
            requested_deadline__lte=now + timedelta(days=7),
        )
    elif deadline == "30_dias":
        queryset = queryset.filter(
            requested_deadline__gte=now,
            requested_deadline__lte=now + timedelta(days=30),
        )
    elif deadline == "sem_prazo":
        queryset = queryset.filter(requested_deadline__isnull=True)

    stage_id = filters["estagio"]
    if stage_id:
        queryset = queryset.filter(stage_id=stage_id)

    condition_id = filters["condicao"]
    if condition_id:
        queryset = queryset.filter(condition_id=condition_id)

    urgency = request.GET.get("urgencia", "")
    if urgency:
        queryset = queryset.filter(urgency=urgency)

    client_id = filters["cliente"]
    if client_id:
        queryset = queryset.filter(client_id=client_id)

    sector_id = filters["setor"]
    if sector_id:
        queryset = queryset.filter(sector_id=sector_id)

    if filters["pessoa"] == "sem":
        queryset = queryset.filter(owner__isnull=True)
    elif filters["pessoa"] == "eu":
        queryset = queryset.filter(owner=user)
    elif _int_or_none(filters["pessoa"]) is not None:
        queryset = queryset.filter(owner_id=_int_or_none(filters["pessoa"]))

    if filters["obra"]:
        queryset = queryset.filter(site_id=filters["obra"])
    if filters["tag"]:
        queryset = queryset.filter(tags__pk=filters["tag"])

    cost_center_id = request.GET.get("centro_custo", "")
    if cost_center_id:
        queryset = queryset.filter(cost_center_id=cost_center_id)

    created_from = request.GET.get("criado_de", "")
    if created_from:
        queryset = queryset.filter(created_at__date__gte=created_from)
    created_to = request.GET.get("criado_ate", "")
    if created_to:
        queryset = queryset.filter(created_at__date__lte=created_to)

    deadline_from = request.GET.get("prazo_de", "")
    if deadline_from:
        queryset = queryset.filter(requested_deadline__date__gte=deadline_from)
    deadline_to = request.GET.get("prazo_ate", "")
    if deadline_to:
        queryset = queryset.filter(requested_deadline__date__lte=deadline_to)

    queryset = (
        queryset.select_related("owner", "company", "site", "client", "sector", "cost_center", "stage", "condition")
        .annotate(
            total_tasks=Count("tasks", distinct=True),
            done_tasks=Count("tasks", filter=Q(tasks__status=Task.Status.CONCLUIDA), distinct=True),
            blocked_tasks=Count("tasks", filter=Q(tasks__status=Task.Status.BLOQUEADA), distinct=True),
            open_deadline_conflicts=Count(
                "tasks__deadline_conflicts",
                filter=Q(tasks__deadline_conflicts__status=DeadlineConflict.Status.ABERTO),
                distinct=True,
            ),
        )
        .distinct()
    )
    if order:
        orderings = ACTIVITY_ORDERINGS.get(filters["ordem"], ACTIVITY_ORDERINGS["prazo"])
        queryset = queryset.order_by(*orderings)
    return queryset


def activity_filter_context(request, organization):
    """Contexto mínimo compartilhado pela nav de troca de visão (Lista/
    Kanban/Calendário) das 3 telas de atividade — `filter_querystring` some
    com `page`/`ano`/`mes` para não duplicar paginação/navegação de mês ao
    trocar de visão."""
    filters = normalize_workspace_filters(request)
    return {
        "tab": filters["tab"],
        "filter_querystring": canonical_filter_querystring(
            request, keep_calendar=bool(filters["ano"] or filters["mes"])
        ),
        "search": filters["q"],
        "f_status": filters["status"],
        "f_stage": filters["estagio"],
        "f_condition": filters["condicao"],
        "f_group": filters["setor"],
        "ordem": filters["ordem"],
        "has_filters": any(filters[key] for key in ("q", "pessoa", "setor", "condicao", "estagio", "filtro", "cliente", "obra", "tag", "participante", "prazo", "bloqueio", "concluidas", "status", "dir")) or filters["ordem"] != "prazo",
        "can_view_all": can(request.user, catalog.ATIVIDADE_VISUALIZAR_TODAS),
        "workspace_filters": filters,
    }


def decorate_activity_cards(activities, organization):
    """Prepare display-only attributes shared by list, Kanban and calendar."""
    from core.colors import EnumColorResolver

    now = timezone.now()
    status_colors = EnumColorResolver(organization, "activity_status")
    for activity in activities:
        activity._status_color = status_colors.color_for(activity.status)
        activity._status_label = status_colors.label_for(activity.status, activity.get_status_display())
        activity.is_overdue = bool(
            activity.requested_deadline
            and activity.requested_deadline < now
            and activity.status not in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA)
        )
        activity.overdue_days = (
            max(1, (now.date() - activity.requested_deadline.date()).days)
            if activity.is_overdue
            else 0
        )
        activity.progress_percent = int((activity.done_tasks / activity.total_tasks) * 100) if activity.total_tasks else 0
        activity.stage_name = activity.stage.name if activity.stage else "Sem estagio"
        activity.stage_color = activity.stage.color if activity.stage else "#94A3B8"
        activity.condition_name = activity.condition.name if activity.condition else "Sem condição"
        activity.condition_color = activity.condition.color if activity.condition else "#94A3B8"
    return activities


def decorate_task_statuses(tasks, organization):
    """Resolve os rótulos e cores de tarefa uma vez por lista, sem N+1."""
    from core.colors import EnumColorResolver

    status_colors = EnumColorResolver(organization, "task_status")
    for task in tasks:
        task._status_color = status_colors.color_for(task.status)
        task._status_label = status_colors.label_for(task.status, task.get_status_display())
    return tasks


def activity_row_for_request(activity_id, user, organization):
    """Re-render one activity row after a confirmed contextual action."""
    activity = (
        Activity.objects.filter(pk=activity_id, organization=organization)
        .select_related("client", "site", "cost_center", "sector", "stage", "condition", "owner")
        .annotate(
            total_tasks=Count("tasks", distinct=True),
            done_tasks=Count("tasks", filter=Q(tasks__status=Task.Status.CONCLUIDA), distinct=True),
        )
        .get()
    )
    decorate_activity_cards([activity], organization)
    actions = [
        catalog.ATIVIDADE_ASSUMIR,
        catalog.ATIVIDADE_ALTERAR_DONO,
        catalog.ATIVIDADE_EDITAR,
        catalog.ATIVIDADE_CONCLUIR,
        catalog.ATIVIDADE_CANCELAR,
        catalog.ATIVIDADE_REABRIR,
        catalog.ATIVIDADE_DEFINIR_ETAPA,
        catalog.ATIVIDADE_DEFINIR_CONDICAO,
        catalog.ATIVIDADE_MOVER_ESTAGIO,
    ]
    access = AuthorizationService.can_many(user, [(action, activity) for action in actions])
    activity.can_assumir = (
        activity.status not in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA)
        and access[(catalog.ATIVIDADE_ASSUMIR, activity.pk)]
    )
    activity.can_repassar = activity.status not in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA) and access[
        (catalog.ATIVIDADE_ALTERAR_DONO, activity.pk)
    ]
    activity.can_edit = access[(catalog.ATIVIDADE_EDITAR, activity.pk)]
    activity.can_complete = activity.status not in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA) and access[
        (catalog.ATIVIDADE_CONCLUIR, activity.pk)
    ]
    activity.can_cancel = activity.status not in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA) and access[
        (catalog.ATIVIDADE_CANCELAR, activity.pk)
    ]
    activity.can_reopen = activity.status == Activity.Status.CONCLUIDA and access[
        (catalog.ATIVIDADE_REABRIR, activity.pk)
    ]
    activity.can_set_stage = (
        access[(catalog.ATIVIDADE_DEFINIR_ETAPA, activity.pk)]
        or access[(catalog.ATIVIDADE_MOVER_ESTAGIO, activity.pk)]
    )
    activity.can_set_condition = access[(catalog.ATIVIDADE_DEFINIR_CONDICAO, activity.pk)]
    activity.stage_options = list(
        ActivityStage.objects.filter(
            organization=organization, sector_id=activity.sector_id, is_active=True
        ).order_by("order", "name")
    ) if activity.sector_id else []
    activity.condition_options = list(
        WorkflowStatus.objects.filter(
            organization=organization, sector_id=activity.sector_id,
            domain=WorkflowStatus.Domain.ACTIVITY, is_active=True,
        ).order_by("order", "name")
    ) if activity.sector_id else []
    return activity


class ActivityListView(OrganizationRequiredMixin, ListView):
    """Fila de atividades (doc 09, ampliado pelo pedido de filtros §1): busca
    por cliente/título/ID, filtros por status, urgência, cliente, grupo,
    centro de custo e datas — os mesmos campos criados na Regra 1-13."""

    template_name = "activities/activity_list.html"
    context_object_name = "activities"
    paginate_by = 20

    FILTER_KEYS = ACTIVITY_FILTER_KEYS

    def get_queryset(self):
        return filtered_activities_queryset(self.request, self.organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        tab = self.request.GET.get("tab", "minhas")
        my_sector_ids = set(user_sectors(user).values_list("id", flat=True))

        context["view_mode"] = "lista"
        context["search"] = self.request.GET.get("q", "")
        context["ordem"] = normalize_workspace_filters(self.request)["ordem"]
        context["can_view_all"] = can(user, catalog.ATIVIDADE_VISUALIZAR_TODAS)

        # Opções dos filtros: mesmos campos criados na Regra 1-13.
        context.update(activity_filter_context(self.request, self.organization))
        context["querystring"] = context["filter_querystring"]

        from core.colors import EnumColorResolver

        status_colors = EnumColorResolver(self.organization, "activity_status")
        urgency_colors = EnumColorResolver(self.organization, "activity_urgency")

        context["status_choices"] = [
            (code, status_colors.label_for(code, label))
            for code, label in Activity.Status.choices
            if not status_colors.is_hidden(code)
        ]
        context["urgency_choices"] = Activity.Urgency.choices
        context["clients"] = Client.objects.filter(organization=self.organization, is_active=True)
        context["sectors"] = Sector.objects.filter(organization=self.organization, is_active=True)
        selected_sector = normalize_workspace_filters(self.request)["setor"]
        stage_groups, condition_groups = visual_filter_choice_groups(
            self.organization, "demanda", selected_sector
        )
        context["stage_choice_groups"] = stage_groups
        context["condition_choice_groups"] = condition_groups
        context["stage_choices"] = [item for _sector, items in stage_groups for item in items]
        context["condition_choices"] = [item for _sector, items in condition_groups for item in items]
        context["filter_state"] = build_filter_toolbar_state(
            self.request,
            self.organization,
            domain="demanda",
            view_mode="lista",
            sectors=context["sectors"],
            stage_groups=stage_groups,
            condition_groups=condition_groups,
            orderings=[("prazo", "Prazo"), ("recentes", "Mais recentes"), ("titulo", "Demanda (A-Z)")],
        )
        context["cost_centers"] = CostCenter.objects.filter(organization=self.organization, is_active=True)
        for key in self.FILTER_KEYS:
            context[f"f_{key}"] = self.request.GET.get(key, "")
        context["has_filters"] = bool(self.request.GET.get("q")) or any(
            self.request.GET.get(key) for key in self.FILTER_KEYS
        )

        decorate_activity_cards(context["activities"], self.organization)
        activities = list(context["activities"])
        action_keys = [
            catalog.ATIVIDADE_ASSUMIR,
            catalog.ATIVIDADE_ALTERAR_DONO,
            catalog.ATIVIDADE_EDITAR,
            catalog.ATIVIDADE_CONCLUIR,
            catalog.ATIVIDADE_CANCELAR,
            catalog.ATIVIDADE_REABRIR,
            catalog.ATIVIDADE_DEFINIR_ETAPA,
            catalog.ATIVIDADE_DEFINIR_CONDICAO,
            catalog.ATIVIDADE_MOVER_ESTAGIO,
        ]
        access = AuthorizationService.can_many(
            user, [(action, activity) for activity in activities for action in action_keys]
        )
        for activity in activities:
            activity._urgency_color = urgency_colors.color_for(activity.urgency)
            activity.can_assumir = (
                activity.sector_id in my_sector_ids
                and activity.owner_id != user.id
                and activity.status not in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA)
                and access[(catalog.ATIVIDADE_ASSUMIR, activity.pk)]
            )
            activity.can_repassar = activity.status not in (
                Activity.Status.CONCLUIDA,
                Activity.Status.CANCELADA,
            ) and access[(catalog.ATIVIDADE_ALTERAR_DONO, activity.pk)]
            activity.can_edit = access[(catalog.ATIVIDADE_EDITAR, activity.pk)]
            activity.can_complete = activity.status not in (
                Activity.Status.CONCLUIDA,
                Activity.Status.CANCELADA,
            ) and access[(catalog.ATIVIDADE_CONCLUIR, activity.pk)]
            activity.can_cancel = activity.status not in (
                Activity.Status.CONCLUIDA,
                Activity.Status.CANCELADA,
            ) and access[(catalog.ATIVIDADE_CANCELAR, activity.pk)]
            # Só concluída reabre (cancelada não): o serviço recusaria o resto.
            activity.can_reopen = activity.status == Activity.Status.CONCLUIDA and access[
                (catalog.ATIVIDADE_REABRIR, activity.pk)
            ]
            activity.can_set_stage = (
                access[(catalog.ATIVIDADE_DEFINIR_ETAPA, activity.pk)]
                or access[(catalog.ATIVIDADE_MOVER_ESTAGIO, activity.pk)]
            )
            activity.can_set_condition = access[(catalog.ATIVIDADE_DEFINIR_CONDICAO, activity.pk)]
        sector_ids = {activity.sector_id for activity in activities if activity.sector_id}
        stages_by_sector, conditions_by_sector = {}, {}
        for stage in ActivityStage.objects.filter(
            organization=self.organization, sector_id__in=sector_ids, is_active=True
        ).order_by("order", "name"):
            stages_by_sector.setdefault(stage.sector_id, []).append(stage)
        for condition in WorkflowStatus.objects.filter(
            organization=self.organization, sector_id__in=sector_ids,
            domain=WorkflowStatus.Domain.ACTIVITY, is_active=True,
        ).order_by("order", "name"):
            conditions_by_sector.setdefault(condition.sector_id, []).append(condition)
        for activity in activities:
            activity.stage_options = stages_by_sector.get(activity.sector_id, [])
            activity.condition_options = conditions_by_sector.get(activity.sector_id, [])
        context["activities"] = activities
        return context


class ActivityMoveStageView(OrganizationRequiredMixin, View):
    """Move uma atividade entre colunas do Kanban. Toca somente
    `Activity.stage` — nunca `Activity.status`, nunca passa pelo
    `ActivityService`. É uma camada visual, não uma ação de negócio."""

    def post(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        stage_id = request.POST.get("stage_id") or None
        stage = None
        if stage_id:
            stage = get_object_or_404(ActivityStage, pk=stage_id, organization=self.organization)
        try:
            ActivityService.set_stage(activity, stage, request.user)
        except ActivityError as exc:
            if _is_ajax(request):
                return JsonResponse({"success": False, "message": str(exc), "errors": {"stage_id": [str(exc)]}}, status=403)
            messages.error(request, str(exc))
            return redirect("activity-list")
        if _is_ajax(request):
            activity = activity_row_for_request(activity.pk, request.user, self.organization)
            return JsonResponse({
                "success": True,
                "message": "Estágio da demanda atualizado.",
                "activity_id": activity.pk,
                "stage_id": stage.pk if stage else None,
                "target": f"activity-{activity.pk}",
                "html": render_to_string("activities/_activity_row.html", {"activity": activity}, request=request),
            })
        return redirect("activity-kanban")


class ActivitySetConditionView(OrganizationRequiredMixin, View):
    """Altera somente a condição manual da demanda, após validação do serviço."""

    def post(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        condition_id = request.POST.get("condition_id") or None
        condition = None
        if condition_id:
            condition = get_object_or_404(
                WorkflowStatus, pk=condition_id, organization=self.organization,
                domain=WorkflowStatus.Domain.ACTIVITY,
            )
        try:
            ActivityService.set_condition(activity, condition, request.user)
        except ActivityError as exc:
            if _is_ajax(request):
                return JsonResponse({"success": False, "message": str(exc), "errors": {"condition_id": [str(exc)]}}, status=403)
            messages.error(request, str(exc))
            return redirect("activity-list")
        if _is_ajax(request):
            activity = activity_row_for_request(activity.pk, request.user, self.organization)
            return JsonResponse({
                "success": True, "message": "Condição da demanda atualizada.",
                "target": f"activity-{activity.pk}", "html": render_to_string(
                    "activities/_activity_row.html", {"activity": activity}, request=request
                ), "errors": {},
            })
        return redirect("activity-list")


class ActivityCalendarView(OrganizationRequiredMixin, TemplateView):
    """Calendário mensal de atividades, por `requested_deadline` — sem prazo
    fica só na lista lateral "Sem prazo definido" (Activity não tem
    `committed_deadline`, diferente de Task)."""

    template_name = "activities/activity_calendar.html"

    def get_context_data(self, **kwargs):
        import calendar as calendar_module
        from datetime import date as date_cls

        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        try:
            year = int(self.request.GET.get("ano", today.year))
            month = int(self.request.GET.get("mes", today.month))
        except (TypeError, ValueError):
            year, month = today.year, today.month
        if month < 1 or month > 12:
            month = today.month

        from core.colors import EnumColorResolver

        status_colors = EnumColorResolver(self.organization, "activity_status")

        activities = filtered_activities_queryset(self.request, self.organization, order=False)
        decorate_activity_cards(activities, self.organization)
        by_day = {}
        undated = []
        for activity in activities:
            deadline = activity.requested_deadline
            if deadline is None:
                undated.append(activity)
                continue
            by_day.setdefault(timezone.localtime(deadline).date(), []).append(activity)

        cal = calendar_module.Calendar(firstweekday=6)  # domingo primeiro
        weeks = [
            [
                {
                    "date": day,
                    "in_month": day.month == month,
                    "is_today": day == today,
                    "activities": by_day.get(day, []),
                }
                for day in week
            ]
            for week in cal.monthdatescalendar(year, month)
        ]

        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        if month == 12:
            next_year, next_month = year + 1, 1
        else:
            next_year, next_month = year, month + 1

        context.update(activity_filter_context(self.request, self.organization))
        selected_sector = normalize_workspace_filters(self.request)["setor"]
        stage_groups, condition_groups = visual_filter_choice_groups(
            self.organization, "demanda", selected_sector
        )
        context.update(
            {
                "weeks": weeks,
                "year": year,
                "month": month,
                "month_date": date_cls(year, month, 1),
                "today_year": today.year,
                "today_month": today.month,
                "undated_activities": undated,
                "prev_year": prev_year,
                "prev_month": prev_month,
                "next_year": next_year,
                "next_month": next_month,
                "view_mode": "calendario",
                "status_choices": [
                    (code, status_colors.label_for(code, label))
                    for code, label in Activity.Status.choices
                    if not status_colors.is_hidden(code)
                ],
                "sectors": Sector.objects.filter(organization=self.organization, is_active=True),
                "stage_choices": [item for _sector, items in stage_groups for item in items],
                "condition_choices": [item for _sector, items in condition_groups for item in items],
                "stage_choice_groups": stage_groups,
                "condition_choice_groups": condition_groups,
                "filter_state": build_filter_toolbar_state(
                    self.request,
                    self.organization,
                    domain="demanda",
                    view_mode="calendario",
                    sectors=Sector.objects.filter(organization=self.organization, is_active=True),
                    stage_groups=stage_groups,
                    condition_groups=condition_groups,
                    year=year,
                    month=month,
                    orderings=[("prazo", "Prazo"), ("recentes", "Mais recentes"), ("titulo", "Demanda (A-Z)")],
                ),
            }
        )
        return context


class ActivityWizardStep2View(OrganizationRequiredMixin, FormView):
    """Etapa 2 (Contexto) do wizard — Organização/Empresa, Centro de custo,
    Solicitante, Endereço complementar, Marcadores. Tudo opcional."""

    template_name = "activities/activity_wizard_step2.html"
    form_class = ActivityWizardStep2Form

    def get(self, request, *args, **kwargs):
        # Old bookmarks resolve to the unified editor; legacy POSTs remain valid.
        draft = self.get_draft()
        return redirect(f"{reverse('activity-create')}?pk={draft.pk}")

    def get_draft(self):
        return get_object_or_404(
            Activity,
            pk=self.kwargs["pk"],
            organization=self.organization,
            status=Activity.Status.RASCUNHO,
            created_by=self.request.user,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["instance"] = self.get_draft()
        kwargs["can_create_company"] = can(self.request.user, catalog.EMPRESA_GERIR)
        kwargs["can_create_cost_center"] = can(self.request.user, catalog.CENTRO_CUSTO_GERIR)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["draft"] = self.get_draft()
        return context

    def form_valid(self, form):
        activity = form.save()
        if self.request.POST.get("acao") == "sair":
            messages.success(self.request, "Rascunho salvo. Você pode retomar quando quiser.")
            return redirect("activity-list")
        if self.request.POST.get("acao") == "voltar":
            return redirect(f"{reverse('activity-create')}?pk={activity.pk}")
        return redirect("activity-wizard-detalhes", pk=activity.pk)


class ActivityWizardStep3View(OrganizationRequiredMixin, FormView):
    """Etapa 3 (Detalhes) do wizard — descrição, observações internas,
    anexos (via `ActivityAttachmentUploadView`, já apontando pro rascunho) e
    o resumo final. O botão "Criar atividade" publica de verdade."""

    template_name = "activities/activity_wizard_step3.html"
    form_class = ActivityWizardStep3Form

    def get(self, request, *args, **kwargs):
        # Old bookmarks resolve to the unified editor; legacy POSTs remain valid.
        draft = self.get_draft()
        return redirect(f"{reverse('activity-create')}?pk={draft.pk}")

    def get_draft(self):
        return get_object_or_404(
            Activity,
            pk=self.kwargs["pk"],
            organization=self.organization,
            status=Activity.Status.RASCUNHO,
            created_by=self.request.user,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_draft()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["draft"] = self.get_draft()
        return context

    def form_valid(self, form):
        activity = form.save()
        acao = self.request.POST.get("acao")

        if acao == "sair":
            messages.success(self.request, "Rascunho salvo. Você pode retomar quando quiser.")
            return redirect("activity-list")
        if acao == "voltar":
            return redirect("activity-wizard-contexto", pk=activity.pk)

        try:
            activity = ActivityService.publish_draft(activity, self.request.user)
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        if acao == "publicar_e_tarefas":
            messages.success(self.request, "Demanda criada. Agora defina a primeira tarefa.")
            return redirect("task-quick-create", activity_pk=activity.pk)

        messages.success(self.request, "Demanda criada. Próximo passo: adicionar a primeira tarefa.")
        return redirect("activity-detail", pk=activity.pk)


class ActivityWizardDiscardView(OrganizationRequiredMixin, View):
    """Descarta um rascunho nunca publicado — ação explícita, sem volta."""

    def post(self, request, pk):
        activity = get_object_or_404(
            Activity, pk=pk, organization=self.organization, status=Activity.Status.RASCUNHO
        )
        try:
            ActivityService.discard_draft(activity, request.user)
        except ActivityError as exc:
            messages.error(request, str(exc))
            return redirect("activity-list")
        messages.success(request, "Rascunho descartado.")
        return redirect("activity-list")


class ActivitySearchView(OrganizationRequiredMixin, View):
    """Busca de atividades para o `ActivityPickerWidget` (fluxo "+ Nova
    tarefa" fora do contexto de uma atividade já aberta), mesmo padrão de
    `core.views.ClientSearchView`. Só oferece atividades ainda não encerradas
    como destino de uma tarefa nova."""

    MAX_RESULTS = 20

    def get(self, request):
        term = request.GET.get("q", "").strip()
        queryset = (
            Activity.objects.filter(
                organization=self.organization,
                status__in=TaskQuickCreateStandaloneForm.OPEN_ACTIVITY_STATUSES,
            )
            .select_related("client", "sector")
            .annotate(task_total=Count("tasks"))
            .order_by("-created_at")
        )
        if term:
            queryset = queryset.filter(Q(title__icontains=term) | Q(code__icontains=code_search_term(term)))
        results = [
            {
                "id": activity.pk,
                "name": f"{activity.code} — {activity.title}" if activity.code else activity.title,
                # Alimenta o cartão "atividade escolhida" da janela de tarefa.
                "summary": activity_summary(activity),
            }
            for activity in queryset[: self.MAX_RESULTS]
        ]
        return JsonResponse({"results": results})


class ActivityDetailView(OrganizationRequiredMixin, DetailView):
    """Centro de comando da atividade: situação atual, tarefas e conversa
    na frente; dados cadastrais e histórico do sistema atrás — não uma tela
    de cadastro com o trabalho em segundo plano."""

    template_name = "activities/activity_detail.html"
    context_object_name = "activity"

    def get(self, request, *args, **kwargs):
        activity = get_object_or_404(Activity, pk=kwargs["pk"], organization=self.organization)
        if activity.status == Activity.Status.RASCUNHO:
            return redirect(f"{reverse('activity-create')}?pk={activity.pk}")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Activity.objects.filter(organization=self.organization).select_related(
            "owner",
            "created_by",
            "client",
            "sector",
            "company",
            "site",
            "cost_center",
            "completed_by",
            "process_version__process__company",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["return_url"] = activity_return_url(self.request)
        activity = self.object
        user = self.request.user

        pending_proposals = DeadlineProposal.objects.filter(
            task=OuterRef("pk"), status=DeadlineProposal.Status.PENDENTE
        )
        open_conflicts = DeadlineConflict.objects.filter(task=OuterRef("pk"), status=DeadlineConflict.Status.ABERTO)

        tasks = list(
            activity.tasks.select_related("sector", "depends_on", "responsavel", "process_step")
            .prefetch_related(
                Prefetch(
                    "executors",
                    queryset=TaskExecutor.objects.filter(removed_at__isnull=True).select_related("user"),
                    to_attr="active_executors",
                )
            )
            .annotate(
                has_pending_proposal=Exists(pending_proposals),
                has_open_conflict=Exists(open_conflicts),
            )
            .order_by("order", "created_at")
        )

        status_counts = {"done": 0, "in_progress": 0, "waiting": 0, "blocked": 0, "dependency_waiting": 0}
        for task in tasks:
            task.queue_info = queue_position(task)
            if task.status == Task.Status.CONCLUIDA:
                status_counts["done"] += 1
            elif task.status == Task.Status.EM_EXECUCAO:
                status_counts["in_progress"] += 1
            elif task.status == Task.Status.BLOQUEADA:
                status_counts["blocked"] += 1
            elif task.status == Task.Status.DISPONIVEL and task.waiting_for is not None:
                # Etapa que espera a anterior: existe, mas não está na fila.
                status_counts["dependency_waiting"] += 1
            elif task.status in (Task.Status.DISPONIVEL, Task.Status.EM_FILA):
                status_counts["waiting"] += 1

        done = status_counts["done"]
        open_tasks = [t for t in tasks if t.status in OPEN_TASK_STATUSES]
        my_sector_ids = set(user_sectors(user).values_list("id", flat=True))

        now = timezone.now()
        is_overdue = bool(
            activity.requested_deadline
            and activity.requested_deadline < now
            and activity.status not in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA)
        )
        overdue_days = (
            max(1, (now.date() - activity.requested_deadline.date()).days) if is_overdue else 0
        )

        is_open = activity.status not in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA)
        can_edit = can(user, catalog.ATIVIDADE_EDITAR, activity)
        can_change_owner = can(user, catalog.ATIVIDADE_ALTERAR_DONO, activity)
        # Só atividade concluída reabre; cancelada não (o serviço recusa), então
        # nem o botão nem o item de menu aparecem para ela.
        can_reopen = activity.status == Activity.Status.CONCLUIDA and can(user, catalog.ATIVIDADE_REABRIR, activity)
        can_mark_pending = activity.status in (
            Activity.Status.ABERTA,
            Activity.Status.EM_ANDAMENTO,
        ) and can(user, catalog.ATIVIDADE_MARCAR_PENDENTE, activity)
        can_finalize = can(user, catalog.ATIVIDADE_CONCLUIR, activity) or can(
            user, catalog.ATIVIDADE_CANCELAR, activity
        )

        # Painel do processo aplicado (Regras 12 §28): reaproveita as tarefas já
        # carregadas acima em vez de consultá-las de novo.
        process_panel = process_state.process_panel(activity, tasks=tasks)
        unmet_required_criteria = process_panel["unmet_required_criteria"] if process_panel else []

        context.update(
            {
                "process_panel": process_panel,
                "can_apply_process": ProcessApplicationService.can_offer(user, activity),
                "can_update_process": bool(process_panel) and ActivityProcessService.can_update(user, activity),
                "tasks": tasks,
                "tasks_done": done,
                "tasks_total": len(tasks),
                "open_tasks": open_tasks,
                "sectors_involved": sorted({t.sector.name for t in tasks}),
                "status_counts": status_counts,
                "next_attention": _next_attention(tasks),
                "is_overdue": is_overdue,
                "overdue_days": overdue_days,
                "has_blocked_task": status_counts["blocked"] > 0,
                "is_negotiating_deadline": any(t.has_pending_proposal or t.has_open_conflict for t in tasks),
                "is_ready_to_complete": len(tasks) > 0 and not open_tasks and not unmet_required_criteria,
                # Tarefas terminadas, mas ainda faltam critérios obrigatórios: a
                # atividade não está pronta para "Sucesso" (Regras 12 §14, §31).
                "is_blocked_by_criteria": len(tasks) > 0 and not open_tasks and bool(unmet_required_criteria),
                "conversation": activity.messages.select_related("author").order_by("-created_at")[:100],
                "attachments": activity.attachments.select_related("uploaded_by").order_by("-uploaded_at"),
                "history_entries": activity.audit_entries.select_related("user", "task").order_by("-timestamp")[
                    :100
                ],
                "owner_changes": activity.owner_changes.select_related(
                    "previous_owner", "new_owner", "changed_by"
                ),
                "can_change_owner": can_change_owner,
                "can_assumir": (
                    activity.sector_id in my_sector_ids
                    and activity.owner_id != user.id
                    and activity.status not in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA)
                    and can(user, catalog.ATIVIDADE_ASSUMIR, activity)
                ),
                "can_cancel": can(user, catalog.ATIVIDADE_CANCELAR, activity),
                "can_reopen": can_reopen,
                "can_complete": can(user, catalog.ATIVIDADE_CONCLUIR, activity),
                # Finalizar (popup único) aparece para quem pode concluir OU
                # cancelar — o popup decide o resultado real, não o botão.
                "can_finalize": can_finalize,
                "can_mark_pending": can_mark_pending,
                "can_approve_pendency": (
                    activity.status == Activity.Status.PENDENTE
                    and can(user, catalog.ATIVIDADE_APROVAR_PENDENCIA, activity)
                ),
                "open_pendency": (
                    activity.pendencies.select_related("opened_by", "previous_owner")
                    .filter(status=ActivityPendency.Status.ABERTA)
                    .order_by("-opened_at")
                    .first()
                    if activity.status == Activity.Status.PENDENTE
                    else None
                ),
                "can_edit": can_edit,
                "can_add_task": can(user, catalog.TAREFA_CRIAR, activity),
                "can_message": can(user, catalog.COMUNICACAO_PARTICIPAR, activity),
                "is_owner": activity.owner_id == user.id,
                "can_manage_attachments": can_edit,
                "message_kind_choices": MessageKind.choices,
                "is_menu_active": (
                    (is_open and (can_edit or can_change_owner or can_mark_pending or can_finalize))
                    or (not is_open and can_reopen)
                ),
            }
        )
        return context


class ActivityDrawerView(OrganizationRequiredMixin, View):
    """Compatibility route: activities always open their complete workspace."""

    def get(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        return redirect("activity-detail", pk=activity.pk)


class ActivityCompleteView(ServiceActionView):
    def perform(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        ActivityService.complete_activity(activity, request.user)
        messages.success(request, "Demanda concluída.")

    def redirect_to(self):
        return reverse("activity-detail", args=[self.kwargs["pk"]])


class ActivityCancelView(OrganizationRequiredMixin, FormView):
    template_name = "activities/activity_cancel.html"
    form_class = CancelForm

    def get(self, request, pk):
        get_object_or_404(Activity, pk=pk, organization=self.organization)
        return redirect(reverse("activity-finalize", args=[pk]) + "?outcome=CANCELADO")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = get_object_or_404(
            Activity, pk=self.kwargs["pk"], organization=self.organization
        )
        return context

    def form_valid(self, form):
        activity = get_object_or_404(Activity, pk=self.kwargs["pk"], organization=self.organization)
        try:
            ActivityService.cancel_activity(activity, self.request.user, form.cleaned_data["reason"])
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Demanda cancelada.")
        return redirect("activity-detail", pk=activity.pk)


class ActivityActionResponseMixin:
    """Same action form works as a page or as a dialog over its caller."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if _is_ajax(request) and response.status_code == 302:
            activity = activity_row_for_request(kwargs["pk"], request.user, self.organization)
            return JsonResponse({
                "success": True,
                "message": "Demanda atualizada.",
                "target": f"activity-{activity.pk}",
                "html": render_to_string("activities/_activity_row.html", {"activity": activity}, request=request),
                "redirect_url": response.url,
            })
        return response

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
        return super().form_invalid(form)


class ActivityReopenView(ActivityActionResponseMixin, OrganizationRequiredMixin, FormView):
    template_name = "activities/activity_reopen.html"
    form_class = CancelForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = get_object_or_404(
            Activity, pk=self.kwargs["pk"], organization=self.organization
        )
        return context

    def form_valid(self, form):
        activity = get_object_or_404(Activity, pk=self.kwargs["pk"], organization=self.organization)
        try:
            ActivityService.reopen_activity(activity, self.request.user, form.cleaned_data["reason"])
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Demanda reaberta.")
        return redirect("activity-detail", pk=activity.pk)


class ActivityChangeOwnerView(ActivityActionResponseMixin, OrganizationRequiredMixin, FormView):
    template_name = "activities/activity_change_owner.html"
    form_class = ChangeOwnerForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["can_create_person"] = can(self.request.user, catalog.USUARIO_CRIAR)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = get_object_or_404(
            Activity, pk=self.kwargs["pk"], organization=self.organization
        )
        return context

    def form_valid(self, form):
        activity = get_object_or_404(Activity, pk=self.kwargs["pk"], organization=self.organization)
        try:
            ActivityService.change_owner(activity, form.cleaned_data["new_owner"], self.request.user)
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Dono da demanda alterado.")
        return redirect("activity-detail", pk=activity.pk)


class ActivityChangeDeadlineView(ActivityActionResponseMixin, OrganizationRequiredMixin, FormView):
    template_name = "activities/activity_change_deadline.html"
    form_class = ActivityDeadlineChangeForm

    def get_activity(self):
        return get_object_or_404(Activity, pk=self.kwargs["pk"], organization=self.organization)

    def get_initial(self):
        initial = super().get_initial()
        initial["requested_deadline"] = self.get_activity().requested_deadline
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.get_activity()
        return context

    def form_valid(self, form):
        activity = self.get_activity()
        try:
            ActivityService.update_activity(
                activity, self.request.user, requested_deadline=form.cleaned_data["requested_deadline"]
            )
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Prazo da demanda alterado.")
        return redirect("activity-detail", pk=activity.pk)


class ActivityFinalizeView(OrganizationRequiredMixin, FormView):
    """Popup único de finalização: Sucesso, Concluído com pendências,
    Declinado ou Cancelado, sempre com comentário obrigatório — no lugar de
    "Concluir" e "Cancelar" como ações separadas e sem explicação."""

    template_name = "activities/activity_finalize_form.html"
    form_class = ActivityFinalizeForm

    def get_activity(self):
        return get_object_or_404(Activity, pk=self.kwargs["pk"], organization=self.organization)

    def get_initial(self):
        initial = super().get_initial()
        outcome = self.request.GET.get("outcome")
        if outcome in Activity.CompletionOutcome.values:
            initial["outcome"] = outcome
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activity = self.get_activity()
        context["activity"] = activity
        # Critérios obrigatórios em aberto: o popup avisa antes de a pessoa
        # tentar "Sucesso" (Regras 12 §32 — sem mensagem genérica).
        context["unmet_required_criteria"] = process_state.unmet_required_criterion_names(activity)
        return context

    def form_valid(self, form):
        activity = self.get_activity()
        try:
            ActivityService.finalize(
                activity, self.request.user, form.cleaned_data["outcome"], form.cleaned_data["comment"]
            )
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        if _is_ajax(self.request):
            activity = activity_row_for_request(activity.pk, self.request.user, self.organization)
            return JsonResponse({
                "success": True,
                "message": "Demanda finalizada.",
                "status": activity.status,
                "target": f"activity-{activity.pk}",
                "html": render_to_string("activities/_activity_row.html", {"activity": activity}, request=self.request),
            })
        messages.success(self.request, "Demanda finalizada.")
        return redirect("activity-detail", pk=activity.pk)

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class ActivityProcessApplyView(OrganizationRequiredMixin, FormView):
    """Popup "Aplicar processo" da ficha da atividade (Regras 12 §20).

    View fina: mostra os processos elegíveis, valida o formato do formulário
    e entrega tudo a `ProcessApplicationService.apply`, que autoriza, valida
    as regras e grava numa única transação.
    """

    template_name = "activities/activity_process_apply.html"
    form_class = ProcessApplyForm

    def get_activity(self):
        return get_object_or_404(
            Activity.objects.select_related("organization", "company", "owner"),
            pk=self.kwargs["pk"],
            organization=self.organization,
        )

    def get(self, request, *args, **kwargs):
        activity = self.get_activity()
        if activity.process_version_id is not None:
            messages.info(request, "Esta demanda já tem um processo aplicado.")
            return redirect("activity-detail", pk=activity.pk)
        if not AuthorizationService.can(request.user, catalog.PROCESSO_APLICAR, activity):
            raise PermissionDenied
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        activity = self.get_activity()
        kwargs["activity"] = activity
        kwargs["versions"] = ProcessApplicationService.eligible_versions(activity)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activity = self.get_activity()
        form = context["form"]
        context.update(
            {
                "activity": activity,
                "panels": form.panels(),
                "no_company": activity.company_id is None,
            }
        )
        return context

    def form_valid(self, form):
        activity = self.get_activity()
        data = form.cleaned_data
        try:
            ProcessApplicationService.apply(
                self.request.user,
                activity,
                data["process_version"],
                responsible_by_step=data["responsible_by_step"],
                input_values=data["input_values"],
            )
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        redirect_url = reverse("activity-detail", args=[activity.pk]) + "#processo"
        if _is_ajax(self.request):
            return JsonResponse({"redirect_url": redirect_url})
        messages.success(self.request, "Processo aplicado. As tarefas da demanda foram criadas.")
        return redirect(redirect_url)

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class ActivityInputUpdateView(ServiceActionView):
    """Registra, corrige ou reabre um input do processo aplicado."""

    def perform(self, request, pk, input_pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        input_value = get_object_or_404(ActivityInputValue, pk=input_pk, activity=activity)
        if request.POST.get("clear"):
            ActivityProcessService.update_input(request.user, input_value, value="", is_received=False)
            messages.success(request, "Input marcado como não recebido.")
            return
        ActivityProcessService.update_input(
            request.user,
            input_value,
            value=request.POST.get("value", ""),
            is_received=bool(request.POST.get("is_received")),
        )
        messages.success(request, "Input atualizado.")

    def redirect_to(self):
        return reverse("activity-detail", args=[self.kwargs["pk"]]) + "#processo"


class ActivityCriterionUpdateView(ServiceActionView):
    """Marca ou desmarca um critério de aceite da atividade."""

    def perform(self, request, pk, check_pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        check = get_object_or_404(ActivityCriterionCheck, pk=check_pk, activity=activity)
        ActivityProcessService.set_criterion(request.user, check, is_met=bool(request.POST.get("is_met")))

    def redirect_to(self):
        return reverse("activity-detail", args=[self.kwargs["pk"]]) + "#processo"


class ActivityMarkPendingView(OrganizationRequiredMixin, FormView):
    """Popup de "Definir como pendente": motivo + comentário obrigatório;
    os motivos que pedem aprovação do gestor também exigem prazo — a
    atividade vai então para a fila dele (pedidos 2 e 3)."""

    template_name = "activities/activity_pending_form.html"
    form_class = ActivityPendingForm

    def get_activity(self):
        return get_object_or_404(Activity, pk=self.kwargs["pk"], organization=self.organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.get_activity()
        context["approval_reasons"] = [reason.value for reason in ActivityPendency.APPROVAL_REASONS]
        return context

    def form_valid(self, form):
        activity = self.get_activity()
        data = form.cleaned_data
        try:
            ActivityService.mark_pending(
                activity,
                self.request.user,
                reason=data["reason"],
                comment=data["comment"],
                decision_deadline=data.get("decision_deadline"),
                notify_client=data.get("notify_client", False),
            )
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        if _is_ajax(self.request):
            return JsonResponse({"status": activity.status})
        messages.success(self.request, "Demanda marcada como pendente.")
        return redirect("activity-detail", pk=activity.pk)

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class ActivityApprovePendencyView(OrganizationRequiredMixin, FormView):
    """Popup de aprovação da pendência: devolve a atividade para quem a
    designou, com status "Em andamento" (pedido 4)."""

    template_name = "activities/activity_approve_pendency_form.html"
    form_class = ActivityApprovePendencyForm

    def get_activity(self):
        return get_object_or_404(Activity, pk=self.kwargs["pk"], organization=self.organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activity = self.get_activity()
        context["activity"] = activity
        context["pendency"] = (
            activity.pendencies.filter(status=ActivityPendency.Status.ABERTA).order_by("-opened_at").first()
        )
        return context

    def form_valid(self, form):
        activity = self.get_activity()
        try:
            ActivityService.approve_pendency(activity, self.request.user, form.cleaned_data.get("comment", ""))
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        if _is_ajax(self.request):
            return JsonResponse({"status": activity.status})
        messages.success(self.request, "Pendência aprovada.")
        return redirect("activity-detail", pk=activity.pk)

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class ActivityClaimView(ServiceActionView):
    """"Assumir" na fila do grupo (pedido 1 do esquema de fila): vira dono
    sem precisar de quem tem autorização para transferir para qualquer um."""

    def perform(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        ActivityService.claim(activity, request.user)
        messages.success(request, "Demanda assumida — agora está em Minhas demandas.")

    def redirect_to(self):
        referer = self.request.META.get("HTTP_REFERER")
        if referer and url_has_allowed_host_and_scheme(
            referer, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure()
        ):
            return referer
        return reverse("activity-detail", args=[self.kwargs["pk"]])


class ActivityMessageCreateView(ServiceActionView):
    def perform(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        form = MessageForm(request.POST)
        if not form.is_valid():
            raise ActivityError("Escreva uma mensagem antes de enviar.")
        MessageService.post_activity_message(activity, request.user, form.cleaned_data["body"])

    def redirect_to(self):
        return reverse("activity-detail", args=[self.kwargs["pk"]])


class ActivityContinueView(ServiceActionView):
    """Continuação da atividade em um único envio (pedido 2): comentário e/ou
    anexo, sem precisar trocar de aba — ambos opcionais, mas ao menos um dos
    dois é obrigatório para o envio fazer sentido."""

    def perform(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        body = (request.POST.get("body") or "").strip()
        uploaded = request.FILES.get("file")
        if not body and not uploaded:
            raise ActivityError("Escreva um comentário ou selecione um arquivo para continuar.")
        if body:
            kind = request.POST.get("kind") or MessageKind.NORMAL
            if kind not in MessageKind.values:
                kind = MessageKind.NORMAL
            MessageService.post_activity_message(activity, request.user, body, kind=kind)
        if uploaded:
            ActivityAttachmentService.add(activity, uploaded, uploaded_by=request.user)
        messages.success(request, "Atualização adicionada ao histórico.")

    def redirect_to(self):
        return reverse("activity-detail", args=[self.kwargs["pk"]])


# ---------------------------------------------------------------------------
# Tarefas
# ---------------------------------------------------------------------------


class TaskListView(OrganizationRequiredMixin, ListView):
    template_name = "activities/task_list.html"
    context_object_name = "tasks"
    paginate_by = 25

    # Coluna do cabeçalho clicável -> campo real de ordenação. "prazo" cai no
    # mesmo par (comprometido, solicitado) já usado como ordenação padrão.
    SORT_FIELDS = {
        "tarefa": ["title"],
        "demanda": ["activity__title"],
        "prazo": ["requested_deadline", "created_at"],
        "condicao": ["condition__name", "title"],
        # URL antiga: mantida como alias para não invalidar links salvos.
        "situacao": ["condition__name", "title"],
    }

    # Endereços de antes da troca de "atividade" por "demanda" (01/10/2026) continuam valendo.
    LEGACY_VALUES = {"atividade": "demanda"}

    def current_sort(self):
        sort = self.request.GET.get("ordem") or self.request.GET.get("sort", "prazo")
        return self.LEGACY_VALUES.get(sort, sort)

    def current_view_mode(self):
        mode = self.request.GET.get("visao", "lista")
        return self.LEGACY_VALUES.get(mode, mode)

    def get_queryset(self):
        sort = self.current_sort()
        direction = self.request.GET.get("dir", "asc")
        fields = self.SORT_FIELDS.get(sort, self.SORT_FIELDS["prazo"])
        if direction == "desc":
            fields = [f"-{field}" for field in fields]
        return filtered_tasks_queryset(self.request, self.organization).order_by(*fields)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(task_filter_context(self.request, self.organization))
        context["view_mode"] = self.current_view_mode()
        context["stats"] = _task_stats(self.request, self.organization)
        context["current_sort"] = self.current_sort()
        context["current_dir"] = self.request.GET.get("dir", "asc")

        from core.colors import EnumColorResolver

        status_colors = EnumColorResolver(self.organization, "task_status")

        now = timezone.now()
        tasks = list(context["object_list"])
        list_actions = [
            catalog.TAREFA_REABRIR,
            catalog.TAREFA_ALTERAR_RESPONSAVEL,
            catalog.TAREFA_MOVER_SETOR,
            catalog.PRAZO_PROPOR,
            catalog.TAREFA_DEFINIR_ETAPA,
            catalog.TAREFA_DEFINIR_CONDICAO,
            catalog.TAREFA_MOVER_ESTAGIO,
        ]
        list_access = AuthorizationService.can_many(
            self.request.user,
            [(action, task) for task in tasks for action in list_actions],
        )
        for task in tasks:
            task._status_color = status_colors.color_for(task.status)
            task._status_label = status_colors.label_for(task.status, task.get_status_display())
            task.effective_deadline = task.committed_deadline or task.requested_deadline
            task.is_overdue = bool(
                task.effective_deadline
                and task.effective_deadline < now
                and task.status not in (Task.Status.CONCLUIDA, Task.Status.CANCELADA)
            )
            # Só as concluídas oferecem "Reabrir" (a permissão é por tarefa/setor).
            task.can_reopen = task.status == Task.Status.CONCLUIDA and list_access[
                (catalog.TAREFA_REABRIR, task.pk)
            ]
            task.can_change_responsavel = list_access[(catalog.TAREFA_ALTERAR_RESPONSAVEL, task.pk)]
            task.can_move_sector = list_access[(catalog.TAREFA_MOVER_SETOR, task.pk)]
            task.can_propose_deadline = list_access[(catalog.PRAZO_PROPOR, task.pk)]
            task.can_set_stage = (
                list_access[(catalog.TAREFA_DEFINIR_ETAPA, task.pk)]
                or list_access[(catalog.TAREFA_MOVER_ESTAGIO, task.pk)]
            )
            task.can_set_condition = list_access[(catalog.TAREFA_DEFINIR_CONDICAO, task.pk)]
            task.stage_name = task.stage.name if task.stage else "Sem etapa"
            task.stage_color = task.stage.color if task.stage else "#94A3B8"
            task.condition_name = task.condition.name if task.condition else "Sem condição"
            task.condition_color = task.condition.color if task.condition else "#94A3B8"
        sector_ids = {task.sector_id for task in tasks if task.sector_id}
        stages_by_sector, conditions_by_sector = {}, {}
        for stage in TaskStage.objects.filter(
            organization=self.organization, sector_id__in=sector_ids, is_active=True
        ).order_by("order", "name"):
            stages_by_sector.setdefault(stage.sector_id, []).append(stage)
        for condition in WorkflowStatus.objects.filter(
            organization=self.organization, sector_id__in=sector_ids,
            domain=WorkflowStatus.Domain.TASK, is_active=True,
        ).order_by("order", "name"):
            conditions_by_sector.setdefault(condition.sector_id, []).append(condition)
        for task in tasks:
            task.stage_options = stages_by_sector.get(task.sector_id, [])
            task.condition_options = conditions_by_sector.get(task.sector_id, [])
        stage_groups, condition_groups = visual_filter_choice_groups(
            self.organization, "tarefa", normalize_workspace_filters(self.request)["setor"]
        )
        context["stage_choice_groups"] = stage_groups
        context["condition_choice_groups"] = condition_groups
        context["stage_choices"] = [item for _sector, items in stage_groups for item in items]
        context["condition_choices"] = [item for _sector, items in condition_groups for item in items]
        context["filter_state"] = build_filter_toolbar_state(
            self.request,
            self.organization,
            domain="tarefa",
            view_mode=context["view_mode"],
            sectors=context["sectors"],
            stage_groups=stage_groups,
            condition_groups=condition_groups,
            orderings=[
                ("prazo", "Prazo"),
                ("tarefa", "Tarefa (A-Z)"),
                ("demanda", "Demanda (A-Z)"),
                ("condicao", "Condição"),
            ],
        )
        context["object_list"] = tasks

        if context["view_mode"] == "demanda":
            grouped = {}
            order = []
            for task in context["object_list"]:
                if task.activity_id not in grouped:
                    grouped[task.activity_id] = {"activity": task.activity, "tasks": []}
                    order.append(task.activity_id)
                grouped[task.activity_id]["tasks"].append(task)
            context["activity_groups"] = [grouped[activity_id] for activity_id in order]
        return context


def task_row_for_request(task_id, user, organization):
    """Re-renderiza uma única linha sem recarregar filtros, scroll ou drawer."""
    task = Task.objects.select_related(
        "activity", "activity__client", "activity__site", "sector", "stage", "condition", "responsavel"
    ).prefetch_related(
        Prefetch(
            "executors",
            queryset=TaskExecutor.objects.filter(removed_at__isnull=True).select_related("user"),
            to_attr="active_executors",
        )
    ).get(pk=task_id, activity__organization=organization)
    from core.colors import EnumColorResolver

    resolver = EnumColorResolver(organization, "task_status")
    task._status_color = resolver.color_for(task.status)
    task._status_label = resolver.label_for(task.status, task.get_status_display())
    task.effective_deadline = task.committed_deadline or task.requested_deadline
    task.is_overdue = bool(task.effective_deadline and task.effective_deadline < timezone.now())
    permissions = AuthorizationService.can_many(user, [
        (catalog.TAREFA_ALTERAR_RESPONSAVEL, task), (catalog.TAREFA_MOVER_SETOR, task),
        (catalog.PRAZO_PROPOR, task), (catalog.TAREFA_DEFINIR_ETAPA, task),
        (catalog.TAREFA_DEFINIR_CONDICAO, task), (catalog.TAREFA_MOVER_ESTAGIO, task),
    ])
    task.can_change_responsavel = permissions[(catalog.TAREFA_ALTERAR_RESPONSAVEL, task.pk)]
    task.can_move_sector = permissions[(catalog.TAREFA_MOVER_SETOR, task.pk)]
    task.can_propose_deadline = permissions[(catalog.PRAZO_PROPOR, task.pk)]
    task.can_set_stage = (
        permissions[(catalog.TAREFA_DEFINIR_ETAPA, task.pk)]
        or permissions[(catalog.TAREFA_MOVER_ESTAGIO, task.pk)]
    )
    task.can_set_condition = permissions[(catalog.TAREFA_DEFINIR_CONDICAO, task.pk)]
    task.stage_name = task.stage.name if task.stage else "Sem etapa"
    task.stage_color = task.stage.color if task.stage else "#94A3B8"
    task.condition_name = task.condition.name if task.condition else "Sem condição"
    task.condition_color = task.condition.color if task.condition else "#94A3B8"
    task.stage_options = list(TaskStage.objects.filter(
        organization=organization, sector=task.sector, is_active=True
    ).order_by("order", "name"))
    task.condition_options = list(WorkflowStatus.objects.filter(
        organization=organization, sector=task.sector, domain=WorkflowStatus.Domain.TASK, is_active=True
    ).order_by("order", "name"))
    return task


class TaskMoveStageView(OrganizationRequiredMixin, View):
    """Move uma tarefa entre colunas do Kanban. Toca somente `Task.stage` —
    nunca `Task.status`, nunca passa pelo `TaskService`. Qualquer pessoa que
    já enxerga a tarefa (mesmo escopo de `filtered_tasks_queryset`) pode
    reorganizar o board; é uma camada visual, não uma ação de negócio."""

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, activity__organization=self.organization)
        stage_id = request.POST.get("stage_id") or None
        stage = None
        if stage_id:
            stage = get_object_or_404(TaskStage, pk=stage_id, organization=self.organization)
        try:
            TaskService.set_stage(task, stage, request.user)
        except ActivityError as exc:
            if _is_ajax(request):
                return JsonResponse({"success": False, "message": str(exc), "errors": {"stage_id": [str(exc)]}}, status=403)
            messages.error(request, str(exc))
            return redirect("task-list")
        if _is_ajax(request):
            task = task_row_for_request(task.pk, request.user, self.organization)
            return JsonResponse({
                "success": True, "message": "Etapa da tarefa atualizada.", "task_id": task.pk,
                "stage_id": stage.pk if stage else None, "target": f"task-{task.pk}",
                "html": render_to_string("activities/_task_row.html", {"task": task}, request=request), "errors": {},
            })
        return redirect("task-kanban")


class TaskSetConditionView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, activity__organization=self.organization)
        condition_id = request.POST.get("condition_id") or None
        condition = None
        if condition_id:
            condition = get_object_or_404(
                WorkflowStatus, pk=condition_id, organization=self.organization,
                domain=WorkflowStatus.Domain.TASK,
            )
        try:
            TaskService.set_condition(task, condition, request.user)
        except ActivityError as exc:
            if _is_ajax(request):
                return JsonResponse({"success": False, "message": str(exc), "errors": {"condition_id": [str(exc)]}}, status=403)
            messages.error(request, str(exc))
            return redirect("task-list")
        if _is_ajax(request):
            task = task_row_for_request(task.pk, request.user, self.organization)
            return JsonResponse({
                "success": True, "message": "Condição da tarefa atualizada.", "target": f"task-{task.pk}",
                "html": render_to_string("activities/_task_row.html", {"task": task}, request=request), "errors": {},
            })
        return redirect("task-list")


class TaskCalendarView(OrganizationRequiredMixin, TemplateView):
    """Calendário mensal de tarefas: `committed_deadline` > `requested_deadline`
    > sem prazo (fica só na lista lateral "Sem prazo definido")."""

    template_name = "activities/task_calendar.html"

    def get_context_data(self, **kwargs):
        import calendar as calendar_module
        from datetime import date as date_cls

        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        try:
            year = int(self.request.GET.get("ano", today.year))
            month = int(self.request.GET.get("mes", today.month))
        except (TypeError, ValueError):
            year, month = today.year, today.month
        if month < 1 or month > 12:
            month = today.month

        from core.colors import EnumColorResolver

        status_colors = EnumColorResolver(self.organization, "task_status")

        tasks = filtered_tasks_queryset(self.request, self.organization)
        by_day = {}
        undated = []
        for task in tasks:
            task._status_color = status_colors.color_for(task.status)
            task._status_label = status_colors.label_for(task.status, task.get_status_display())
            task.condition_name = task.condition.name if task.condition else "Sem condição"
            task.condition_color = task.condition.color if task.condition else "#94A3B8"
            deadline = task.committed_deadline or task.requested_deadline
            if deadline is None:
                undated.append(task)
                continue
            by_day.setdefault(timezone.localtime(deadline).date(), []).append(task)

        cal = calendar_module.Calendar(firstweekday=6)  # domingo primeiro
        weeks = [
            [
                {
                    "date": day,
                    "in_month": day.month == month,
                    "is_today": day == today,
                    "tasks": by_day.get(day, []),
                }
                for day in week
            ]
            for week in cal.monthdatescalendar(year, month)
        ]

        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        if month == 12:
            next_year, next_month = year + 1, 1
        else:
            next_year, next_month = year, month + 1

        context.update(task_filter_context(self.request, self.organization))
        stage_groups, condition_groups = visual_filter_choice_groups(
            self.organization, "tarefa", normalize_workspace_filters(self.request)["setor"]
        )
        context.update(
            {
                "weeks": weeks,
                "year": year,
                "month": month,
                "month_date": date_cls(year, month, 1),
                "undated_tasks": undated,
                "prev_year": prev_year,
                "prev_month": prev_month,
                "next_year": next_year,
                "next_month": next_month,
                "view_mode": "calendario",
                "stage_choice_groups": stage_groups,
                "condition_choice_groups": condition_groups,
                "stage_choices": [item for _sector, items in stage_groups for item in items],
                "condition_choices": [item for _sector, items in condition_groups for item in items],
                "filter_state": build_filter_toolbar_state(
                    self.request,
                    self.organization,
                    domain="tarefa",
                    view_mode="calendario",
                    sectors=Sector.objects.filter(organization=self.organization, is_active=True),
                    stage_groups=stage_groups,
                    condition_groups=condition_groups,
                    year=year,
                    month=month,
                    orderings=[
                        ("prazo", "Prazo"),
                        ("tarefa", "Tarefa (A-Z)"),
                        ("demanda", "Demanda (A-Z)"),
                        ("condicao", "Condição"),
                    ],
                ),
            }
        )
        return context


class TaskDetailView(OrganizationRequiredMixin, DetailView):
    template_name = "activities/task_detail.html"
    context_object_name = "task"

    def get_queryset(self):
        return Task.objects.filter(activity__organization=self.organization).select_related(
            "activity", "sector", "depends_on", "created_by", "completed_by", "responsavel"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.object
        user = self.request.user

        executors = task.executors.filter(removed_at__isnull=True).select_related("user")
        sessions = task.work_sessions.select_related("user").order_by("-started_at")
        closed = [s for s in sessions if s.ended_at]
        man_hours = sum((s.duration for s in closed), timedelta())
        # Tempo cronometrado × tempo informado pela pessoa (Regras 04 §113): o
        # gestor enxerga a diferença no próprio cartão "Tempo registrado".
        timer_hours = sum((s.duration for s in closed if not s.is_manual), timedelta())
        informed_hours = sum((s.duration for s in closed if s.is_manual), timedelta())
        for session in closed:
            # Trabalho de um dia anterior ao do registro: destacado na tela.
            session.is_past_day = bool(
                session.is_manual
                and session.logged_at
                and timezone.localdate(session.started_at) < timezone.localdate(session.logged_at)
            )

        my_open_session = task.work_sessions.filter(user=user, ended_at__isnull=True).first()
        is_participant = executors.filter(user=user).exists()
        is_responsavel = task.responsavel_id == user.id
        dependency_blocking = task.depends_on is not None and task.depends_on.status != Task.Status.CONCLUIDA
        missing_process_inputs = process_state.missing_required_input_names(task.activity) if task.process_step_id else []
        # "Já realizei este trabalho": tarefa ainda não iniciada, que a pessoa
        # executa e pode concluir agora, sem nada a esperar (dependência/inputs).
        can_retroactive = bool(
            task.status in (Task.Status.EM_FILA, Task.Status.DISPONIVEL)
            and (is_participant or is_responsavel)
            and not dependency_blocking
            and not missing_process_inputs
            and can(user, catalog.TAREFA_CONCLUIR, task)
        )
        open_block = task.blocks.filter(ended_at__isnull=True).order_by("-started_at").first()
        pending_proposal = task.deadline_proposals.filter(
            status=DeadlineProposal.Status.PENDENTE
        ).select_related("proposed_by").first()
        pending_assignments = list(
            task.assignments.filter(status=TaskAssignment.Status.PENDENTE).select_related("user", "assigned_by")
        )
        my_pending_assignment = next((item for item in pending_assignments if item.user_id == user.id), None)
        task_is_open = task.status not in (Task.Status.CONCLUIDA, Task.Status.CANCELADA)

        context.update(
            {
                "activity": task.activity,
                "responsavel": task.responsavel,
                "executors": executors,
                "is_participant": is_participant,
                "is_responsavel": is_responsavel,
                "can_change_responsavel": can(user, catalog.TAREFA_ALTERAR_RESPONSAVEL, task),
                "my_open_session": my_open_session,
                "sessions": sessions,
                "man_hours": man_hours,
                "timer_hours": timer_hours,
                "informed_hours": informed_hours,
                "can_retroactive": can_retroactive,
                "queue_info": queue_position(task),
                "open_block": open_block,
                "checklist_items": task.checklist_items.select_related("created_by", "done_by"),
                "checklist_done": task.checklist_items.filter(is_done=True).count(),
                "can_toggle_checklist": TaskService.can_toggle_checklist(task, user),
                "pending_proposal": pending_proposal,
                "my_pending_assignment": my_pending_assignment,
                "pending_assignments": pending_assignments,
                "can_accept_assignment": can(user, catalog.TAREFA_ACEITAR, task),
                "can_reject_assignment": can(user, catalog.TAREFA_RECUSAR, task),
                "assignment_reject_form": AssignmentRejectForm(organization=self.organization),
                "conflicts": task.deadline_conflicts.select_related("resolved_by").order_by("-opened_at"),
                "proposals": task.deadline_proposals.select_related("proposed_by", "decided_by"),
                "returns": task.returns.select_related("from_sector", "to_sector", "reason", "returned_by"),
                "transfers": task.sector_transfers.select_related("from_sector", "to_sector", "moved_by"),
                "history": task.audit_entries.select_related("user").order_by("-timestamp")[:60],
                "task_messages": task.messages.select_related("author"),
                "message_form": MessageForm(),
                "message_kind_choices": MessageKind.choices,
                "is_owner": task.activity.owner_id == user.id,
                "can_assume": can(user, catalog.TAREFA_ASSUMIR, task),
                "can_assign": can(user, catalog.TAREFA_ATRIBUIR, task),
                "can_start": can(user, catalog.TAREFA_INICIAR, task),
                "can_complete": can(user, catalog.TAREFA_CONCLUIR, task),
                "can_return": can(user, catalog.TAREFA_DEVOLVER, task),
                "can_block": can(user, catalog.TAREFA_BLOQUEAR, task),
                "can_move": can(user, catalog.TAREFA_MOVER_SETOR, task),
                "can_cancel_task": can(user, catalog.TAREFA_CANCELAR, task),
                "can_reopen_task": task.status == Task.Status.CONCLUIDA and can(user, catalog.TAREFA_REABRIR, task),
                "can_edit_task": can(user, catalog.TAREFA_EDITAR, task),
                "can_manage_dependency": task_is_open and can(user, catalog.TAREFA_EDITAR, task),
                "can_log_time": can(user, catalog.TEMPO_LANCAR_MANUAL, task),
                "can_propose": can(user, catalog.PRAZO_PROPOR, task),
                "can_resolve_conflict": can(user, catalog.ESCALONAMENTO_RESOLVER, task),
                "can_message": can(user, catalog.COMUNICACAO_PARTICIPAR, task),
                "executor_form": ExecutorForm(
                    organization=self.organization,
                    can_create_person=can(user, catalog.USUARIO_CRIAR),
                ),
                "manual_time_form": ManualTimeForm(),
                "deadline_form": DeadlineProposalForm(),
                "return_form": TaskReturnForm(organization=self.organization, task=task),
                "block_form": TaskBlockForm(),
                "move_form": MoveSectorForm(organization=self.organization, task=task),
                "dependency_blocking": dependency_blocking,
                # Tarefa de processo com input obrigatório ainda não recebido:
                # a tela explica o que falta em vez de oferecer um "Iniciar"
                # que o serviço recusaria (Regras 12 §10).
                "missing_process_inputs": missing_process_inputs,
            }
        )
        return context


class TaskDrawerView(TaskDetailView):
    """Mesmo contexto de `TaskDetailView`, num fragmento estreito o
    suficiente para o painel lateral — sem navegar para fora da ficha da
    atividade. Reaproveita o contexto por herança em vez de duplicar as
    queries de executores/sessões/prazo já montadas ali."""

    template_name = "activities/_task_drawer.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["checklist_items"] = self.object.checklist_items.select_related("created_by", "done_by")
        context["message_kind_choices"] = MessageKind.choices
        from .kanban import workflow_context

        context["workflow"] = workflow_context(self.object, self.request.user, "tarefas")
        return context


class TaskAjaxActionView(OrganizationRequiredMixin, View):
    """Mesmas ações de estado de `TaskActionView` (start/pause/complete),
    respondendo JSON em vez de redirect — para o timer do painel lateral
    funcionar sem recarregar a página. `TaskService` não muda: só a camada
    de transporte é diferente."""

    action = None

    def get_task(self, pk):
        return get_object_or_404(Task, pk=pk, activity__organization=self.organization)

    def post(self, request, pk):
        task = self.get_task(pk)
        labels = {
            "start": "Tarefa iniciada.",
            "pause": "Tarefa pausada.",
            "complete": "Tarefa concluída.",
        }
        try:
            if self.action == "start":
                TaskService.start(task, request.user)
            elif self.action == "pause":
                TaskService.pause(task, request.user)
            elif self.action == "complete":
                TaskService.complete(task, request.user)
            else:
                raise ActivityError("Ação desconhecida.")
        except ActivityError as exc:
            return JsonResponse({"success": False, "error": str(exc), "errors": {"__all__": [str(exc)]}}, status=400)
        task.refresh_from_db()
        task = Task.objects.select_related(
            "activity", "activity__client", "activity__site", "sector", "responsavel", "depends_on"
        ).prefetch_related(Prefetch("executors", queryset=TaskExecutor.objects.filter(removed_at__isnull=True).select_related("user"), to_attr="active_executors")).get(pk=task.pk)
        from core.colors import EnumColorResolver
        colors = EnumColorResolver(self.organization, "task_status")
        task._status_color = colors.color_for(task.status)
        task._status_label = colors.label_for(task.status, task.get_status_display())
        task.effective_deadline = task.committed_deadline or task.requested_deadline
        task.is_overdue = bool(task.effective_deadline and task.effective_deadline < timezone.now() and task.status not in (Task.Status.CONCLUIDA, Task.Status.CANCELADA))
        access = AuthorizationService.can_many(request.user, [
            (catalog.TAREFA_ALTERAR_RESPONSAVEL, task),
            (catalog.TAREFA_MOVER_SETOR, task),
            (catalog.PRAZO_PROPOR, task),
            (catalog.TAREFA_REABRIR, task),
        ])
        task.can_change_responsavel = access[(catalog.TAREFA_ALTERAR_RESPONSAVEL, task.pk)]
        task.can_move_sector = access[(catalog.TAREFA_MOVER_SETOR, task.pk)]
        task.can_propose_deadline = access[(catalog.PRAZO_PROPOR, task.pk)]
        task.can_reopen = task.status == Task.Status.CONCLUIDA and access[(catalog.TAREFA_REABRIR, task.pk)]
        html = render_to_string("activities/_task_row.html", {"task": task}, request=request)
        return JsonResponse({
            "success": True,
            "message": labels.get(self.action, "Ação concluída."),
            "status": task.status,
            "target": f"task-{task.pk}",
            "html": html,
        })


class TaskChecklistAddView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, activity__organization=self.organization)
        try:
            item = TaskService.add_checklist_item(task, request.user, request.POST.get("text"))
        except ActivityError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse({
            "id": item.pk, "text": item.text, "is_done": item.is_done,
            "toggle_url": reverse("task-checklist-toggle", args=[item.pk]),
            "remove_url": reverse("task-checklist-remove", args=[item.pk]),
        })


class TaskChecklistToggleView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(
            TaskChecklistItem, pk=pk, task__activity__organization=self.organization
        )
        raw_is_done = request.POST.get("is_done")
        if raw_is_done not in ("0", "1"):
            return JsonResponse({"error": "Informe se o item está concluído."}, status=400)
        is_done = raw_is_done == "1"
        try:
            TaskService.toggle_checklist_item(item, request.user, is_done)
        except ActivityError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse({"id": item.pk, "is_done": item.is_done})


class TaskChecklistRemoveView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(
            TaskChecklistItem, pk=pk, task__activity__organization=self.organization
        )
        try:
            TaskService.remove_checklist_item(item, request.user)
        except ActivityError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse({"ok": True})


class TaskQuickCreateView(OrganizationRequiredMixin, FormView):
    """Popup ajax de "+ Adicionar tarefa" na tela da atividade (Regra 12),
    único ponto de criação de tarefa dentro de uma atividade já aberta —
    mesmo padrão ajax de `UserFormView`."""

    template_name = "activities/task_quick_form.html"
    form_class = TaskQuickCreateForm

    def get_activity(self):
        return get_object_or_404(
            Activity, pk=self.kwargs["activity_pk"], organization=self.organization
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["activity"] = self.get_activity()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activity = self.get_activity()
        context["activity"] = activity
        context["activity_summary"] = activity_summary(activity)
        return context

    def form_valid(self, form):
        activity = self.get_activity()
        data = form.cleaned_data
        next_order = (activity.tasks.count() or 0) + 1
        parsed = TaskService.parse_quick_title(data["title"], self.organization)
        merged_tags = list({t.pk: t for t in [*(data.get("tags") or []), *parsed["tags"]]}.values())
        responsavel = data.get("responsavel") or parsed["assignee"]
        try:
            task = TaskService.create_task(
                activity=activity,
                sector=data["sector"],
                title=parsed["title"] or data["title"],
                created_by=self.request.user,
                responsavel=responsavel,
                description=data.get("description") or "",
                order=next_order,
                requested_deadline=data.get("requested_deadline"),
                tags=merged_tags,
                participantes=data.get("participantes"),
                stage=data.get("stage"),
                condition=data.get("condition"),
            )
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        if _is_ajax(self.request):
            return JsonResponse({"id": task.pk, "title": task.title})
        messages.success(self.request, "Tarefa adicionada.")
        return redirect("activity-detail", pk=activity.pk)

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class TaskQuickCreateStandaloneView(OrganizationRequiredMixin, FormView):
    """Botão "+ Nova tarefa" em Minhas tarefas (lista/kanban/calendário):
    mesma criação de `TaskQuickCreateView`, mas a atividade é escolhida (ou
    criada) no próprio popup via `ActivityPickerWidget`, em vez de vir fixa
    da URL. Chama o mesmo `TaskService.create_task` — zero mudança de regra."""

    template_name = "activities/task_quick_form_standalone.html"
    form_class = TaskQuickCreateStandaloneForm

    def get_initial(self):
        initial = super().get_initial()
        # O quadro Kanban abre esta janela já no setor e na etapa da coluna (o formulário valida de novo).
        for key in ("sector", "stage"):
            value = self.request.GET.get(key, "")
            if value.isdigit():
                initial[key] = int(value)
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["can_create_activity"] = can(self.request.user, catalog.ATIVIDADE_CRIAR)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity_summary"] = activity_summary(context["form"].selected_activity)
        return context

    def form_valid(self, form):
        activity = form.cleaned_data["activity"]
        data = form.cleaned_data
        next_order = (activity.tasks.count() or 0) + 1
        parsed = TaskService.parse_quick_title(data["title"], self.organization)
        merged_tags = list({t.pk: t for t in [*(data.get("tags") or []), *parsed["tags"]]}.values())
        responsavel = data.get("responsavel") or parsed["assignee"]
        try:
            task = TaskService.create_task(
                activity=activity,
                sector=data["sector"],
                title=parsed["title"] or data["title"],
                created_by=self.request.user,
                responsavel=responsavel,
                description=data.get("description") or "",
                order=next_order,
                requested_deadline=data.get("requested_deadline"),
                tags=merged_tags,
                participantes=data.get("participantes"),
                stage=data.get("stage"),
                condition=data.get("condition"),
            )
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        if _is_ajax(self.request):
            return JsonResponse({"id": task.pk, "title": task.title})
        messages.success(self.request, "Tarefa adicionada.")
        return redirect("task-list")

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class ActivityAttachmentUploadView(ServiceActionView):
    """Upload de anexo (Regra 13): guardado em uma pasta própria da atividade
    dentro de `MEDIA_ROOT`, nomeada pelo código gerado automaticamente.
    Também usado pela Etapa 3 do wizard, apontando pro rascunho."""

    def perform(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        form = ActivityAttachmentForm(request.POST, request.FILES)
        if not form.is_valid():
            raise ActivityError("Selecione um arquivo válido.")
        ActivityAttachmentService.add(activity, form.cleaned_data["file"], uploaded_by=request.user)
        messages.success(request, "Anexo enviado.")

    def redirect_to(self):
        activity = get_object_or_404(Activity, pk=self.kwargs["pk"], organization=self.organization)
        if activity.status == Activity.Status.RASCUNHO:
            return reverse("activity-wizard-detalhes", args=[activity.pk])
        return f"{reverse('activity-detail', args=[self.kwargs['pk']])}#feed-panel"


class ActivityAttachmentDeleteView(ServiceActionView):
    def post(self, request, pk, attachment_pk):
        if not _is_ajax(request):
            return super().post(request, pk=pk, attachment_pk=attachment_pk)
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        attachment = get_object_or_404(ActivityAttachment, pk=attachment_pk, activity=activity)
        try:
            ActivityAttachmentService.remove(attachment, removed_by=request.user)
        except ActivityError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse({"removed": attachment_pk})

    def perform(self, request, pk, attachment_pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        attachment = get_object_or_404(ActivityAttachment, pk=attachment_pk, activity=activity)
        ActivityAttachmentService.remove(attachment, removed_by=request.user)
        messages.success(request, "Anexo removido.")

    def redirect_to(self):
        activity = get_object_or_404(Activity, pk=self.kwargs["pk"], organization=self.organization)
        if activity.status == Activity.Status.RASCUNHO:
            return reverse("activity-wizard-detalhes", args=[activity.pk])
        return f"{reverse('activity-detail', args=[self.kwargs['pk']])}#feed-panel"


class TaskActionView(ServiceActionView):
    """Ações de estado da tarefa, cada uma delegando ao serviço correspondente."""

    action = None

    def get_task(self, pk):
        return get_object_or_404(Task, pk=pk, activity__organization=self.organization)

    def redirect_to(self):
        return reverse("task-detail", args=[self.kwargs["pk"]])

    def perform(self, request, pk):
        task = self.get_task(pk)
        user = request.user

        if self.action == "assume":
            TaskService.add_executor(task, user, added_by=user)
            messages.success(request, "Tarefa assumida.")
            return

        if self.action == "start":
            TaskService.start(task, user)
            messages.success(request, "Tarefa iniciada.")
        elif self.action == "pause":
            TaskService.pause(task, user)
            messages.success(request, "Tarefa pausada.")
        elif self.action == "resume":
            TaskService.resume(task, user)
            messages.success(request, "Tarefa retomada.")
        elif self.action == "complete":
            TaskService.complete(task, user)
            messages.success(request, "Tarefa concluída.")
        elif self.action == "unblock":
            TaskService.unblock(task, user)
            messages.success(request, "Bloqueio resolvido.")
        else:
            raise ActivityError("Ação desconhecida.")


class TaskFormActionView(ActivityActionResponseMixin, OrganizationRequiredMixin, FormView):
    """Ações que exigem dados extras (devolver, bloquear, mover, prazo...).

    Todas servem de página (sem JavaScript) ou de janela sobre a tela de onde a
    pessoa veio: com `X-Requested-With`, sucesso vira `{redirect_url}` e erro
    vira 400 com `{errors}` (`ActivityActionResponseMixin`).
    """

    template_name = "activities/task_action_form.html"
    title = ""
    submit_label = "Confirmar"

    def get_task(self):
        return get_object_or_404(
            Task, pk=self.kwargs["pk"], activity__organization=self.organization
        )

    required_action = None

    def dispatch(self, request, *args, **kwargs):
        organization_id = getattr(
            getattr(request.user, "profile", None), "organization_id", None
        )
        if self.required_action and request.user.is_authenticated and organization_id:
            task = get_object_or_404(
                Task, pk=kwargs["pk"], activity__organization_id=organization_id
            )
            if not can(request.user, self.required_action, task):
                raise PermissionDenied("Você não possui acesso a este conteúdo.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # O `pk` da URL aqui é de uma TAREFA. O `post` de `ActivityActionResponseMixin` devolve a linha de uma
        # ATIVIDADE usando esse mesmo `pk` (erro 500, ou a linha de outra atividade quando os ids coincidem).
        # Ação de tarefa responde só com o destino, como descrito acima.
        response = FormView.post(self, request, *args, **kwargs)
        if _is_ajax(request) and response.status_code == 302:
            return JsonResponse({"redirect_url": response.url})
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task"] = self.get_task()
        context["title"] = self.title
        context["submit_label"] = self.submit_label
        return context

    def run(self, task, data):
        raise NotImplementedError

    def form_valid(self, form):
        task = self.get_task()
        try:
            self.run(task, form.cleaned_data)
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return redirect("task-detail", pk=task.pk)


class TaskReturnView(TaskFormActionView):
    form_class = TaskReturnForm
    required_action = catalog.TAREFA_DEVOLVER
    title = "Devolver tarefa"
    submit_label = "Devolver"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["task"] = self.get_task()
        return kwargs

    def run(self, task, data):
        TaskService.return_task(
            task,
            to_sector=data["to_sector"],
            reason=data["reason"],
            user=self.request.user,
            observation=data.get("observation") or "",
        )
        messages.success(self.request, "Tarefa devolvida.")


class TaskBlockView(TaskFormActionView):
    form_class = TaskBlockForm
    required_action = catalog.TAREFA_BLOQUEAR
    title = "Registrar bloqueio"
    submit_label = "Bloquear"

    def run(self, task, data):
        TaskService.block(
            task, self.request.user, data["reason"], observation=data.get("observation") or ""
        )
        messages.success(self.request, "Bloqueio registrado.")


class TaskMoveView(TaskFormActionView):
    form_class = MoveSectorForm
    required_action = catalog.TAREFA_MOVER_SETOR
    title = "Enviar para outro setor"
    submit_label = "Enviar"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["task"] = self.get_task()
        return kwargs

    def run(self, task, data):
        TaskService.move_to_sector(
            task, data["to_sector"], self.request.user, note=data.get("note") or ""
        )
        messages.success(self.request, "Tarefa enviada para o setor.")


class TaskCancelView(TaskFormActionView):
    form_class = CancelForm
    required_action = catalog.TAREFA_CANCELAR
    title = "Cancelar tarefa"
    submit_label = "Cancelar tarefa"

    def run(self, task, data):
        TaskService.cancel(task, self.request.user, data["reason"])
        messages.success(self.request, "Tarefa cancelada.")


class TaskReopenView(TaskFormActionView):
    """Popup "Reabrir tarefa" (motivo obrigatório). Mesmo formulário serve de
    janela sobre a ficha/painel/lista (JSON) ou de página, sem JavaScript."""

    form_class = CancelForm
    required_action = catalog.TAREFA_REABRIR
    title = "Reabrir tarefa"
    submit_label = "Reabrir tarefa"

    def run(self, task, data):
        TaskService.reopen(task, self.request.user, data["reason"])
        messages.success(self.request, "Tarefa reaberta.")


class TaskRetroactiveView(TaskFormActionView):
    """Popup "Já realizei este trabalho": a pessoa informa quando fez o
    trabalho e a tarefa é concluída agora (`TaskService.register_completed_work`).
    Janela (JSON) sobre a ficha/painel, ou página sem JavaScript."""

    template_name = "activities/task_retroactive_form.html"
    form_class = RetroactiveWorkForm
    required_action = catalog.TAREFA_CONCLUIR
    title = "Já realizei este trabalho"
    submit_label = "Registrar e concluir"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["justify_days"] = RETROACTIVE_JUSTIFICATION_DAYS
        context["today"] = timezone.localdate()
        return context

    def run(self, task, data):
        TaskService.register_completed_work(
            task,
            self.request.user,
            data["started_at"],
            data["ended_at"],
            data["reason"],
            note=data.get("note") or "",
        )
        messages.success(self.request, "Trabalho registrado e tarefa concluída.")


class TaskEditView(TaskFormActionView):
    """Editor único da tarefa, em janela (ou página, sem JavaScript): dados,
    prazo pedido, marcadores, responsável e participantes, salvos numa
    transação (`TaskService.edit_task`). Exige `tarefa.editar` já ao abrir.
    Setor e dependência ficam de fora: têm janela própria em Mais ações."""

    template_name = "activities/task_edit_form.html"
    form_class = TaskEditorForm
    required_action = catalog.TAREFA_EDITAR
    title = "Editar tarefa"
    submit_label = "Salvar alterações"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        task = self.get_task()
        user = self.request.user
        kwargs.update(
            organization=self.organization,
            task=task,
            can_change_responsavel=can(user, catalog.TAREFA_ALTERAR_RESPONSAVEL, task),
            can_assign=can(user, catalog.TAREFA_ATRIBUIR, task),
            can_create_person=can(user, catalog.USUARIO_CRIAR),
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = context["task"]
        context.update(
            activity=task.activity,
            activity_summary=activity_summary(task.activity),
            pending_assignments=task.assignments.filter(status=TaskAssignment.Status.PENDENTE).select_related("user"),
            current_responsavel=task.responsavel,
            current_participants=[
                link.user for link in task.executors.filter(removed_at__isnull=True).select_related("user")
            ],
        )
        return context

    def run(self, task, data):
        result = TaskService.edit_task(
            task,
            self.request.user,
            title=data["title"],
            description=data.get("description") or "",
            requested_deadline=data.get("requested_deadline"),
            tags=data.get("tags"),
            responsavel=data.get("responsavel"),
            participants=list(data["participantes"]) if data.get("participantes") is not None else None,
        )
        text = "Tarefa atualizada."
        if result["invited"]:
            names = ", ".join(person.get_username() for person in result["invited"])
            text += f" Convite enviado a {names}: a pessoa só entra como participante depois de aceitar."
        messages.success(self.request, text)


class TaskDependencyView(TaskFormActionView):
    """“Gerenciar dependência”: qual tarefa precisa terminar antes desta.
    Janela própria porque muda o fluxo operacional (fila e liberação)."""

    form_class = TaskDependencyForm
    required_action = catalog.TAREFA_EDITAR
    title = "Gerenciar dependência"
    submit_label = "Salvar dependência"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        task = self.get_task()
        kwargs.update(candidates=TaskService.dependency_candidates(task), current=task.depends_on)
        return kwargs

    def run(self, task, data):
        depends_on = data.get("depends_on")
        TaskService.change_dependency(task, self.request.user, depends_on)
        if depends_on is None:
            messages.success(self.request, "Dependência removida: a tarefa não espera mais por ninguém.")
        else:
            messages.success(self.request, f"Agora esta tarefa só começa depois de «{depends_on.title}».")


class TaskExecutorAddView(ServiceActionView):
    def perform(self, request, pk):
        task = get_object_or_404(Task, pk=pk, activity__organization=self.organization)
        form = ExecutorForm(request.POST, organization=self.organization)
        if not form.is_valid():
            raise ActivityError("Selecione um participante válido.")
        user = form.cleaned_data["user"]
        result = TaskService.add_executor(task, user, added_by=request.user)
        if isinstance(result, TaskAssignment):
            messages.success(request, "Atribuição enviada, aguardando aceite.")
        else:
            messages.success(request, "Participante incluído.")

    def redirect_to(self):
        return reverse("task-detail", args=[self.kwargs["pk"]])


class TaskExecutorRemoveView(ServiceActionView):
    def perform(self, request, pk, user_pk):
        task = get_object_or_404(Task, pk=pk, activity__organization=self.organization)
        executor = get_object_or_404(
            TaskExecutor, task=task, user_id=user_pk, removed_at__isnull=True
        )
        TaskService.remove_executor(task, executor.user, removed_by=request.user)
        messages.success(request, "Participante removido.")

    def redirect_to(self):
        return reverse("task-detail", args=[self.kwargs["pk"]])


class TaskChangeResponsavelView(OrganizationRequiredMixin, FormView):
    template_name = "activities/task_change_responsavel.html"
    form_class = TaskChangeResponsavelForm

    def get_task(self):
        return get_object_or_404(Task, pk=self.kwargs["pk"], activity__organization=self.organization)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["can_create_person"] = can(self.request.user, catalog.USUARIO_CRIAR)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task"] = self.get_task()
        return context

    def form_valid(self, form):
        task = self.get_task()
        try:
            TaskService.change_responsavel(task, form.cleaned_data["new_responsavel"], self.request.user)
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Responsável da tarefa alterado.")
        return redirect("task-detail", pk=task.pk)


class TaskAssignmentAcceptView(ServiceActionView):
    def get_assignment(self, pk, assignment_pk):
        return get_object_or_404(
            TaskAssignment,
            pk=assignment_pk,
            task_id=pk,
            task__activity__organization=self.organization,
        )

    def perform(self, request, pk, assignment_pk):
        assignment = self.get_assignment(pk, assignment_pk)
        TaskService.accept_assignment(assignment, request.user)
        messages.success(request, "Atribuição aceita.")

    def redirect_to(self):
        return reverse("task-detail", args=[self.kwargs["pk"]])


class TaskAssignmentRejectView(TaskFormActionView):
    form_class = AssignmentRejectForm
    required_action = catalog.TAREFA_RECUSAR
    title = "Recusar atribuição"
    submit_label = "Recusar"

    def get_assignment(self):
        return get_object_or_404(
            TaskAssignment,
            pk=self.kwargs["assignment_pk"],
            task_id=self.kwargs["pk"],
            task__activity__organization=self.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        return kwargs

    def run(self, task, data):
        assignment = self.get_assignment()
        TaskService.reject_assignment(
            assignment,
            self.request.user,
            reason=data["reason"],
            observation=data.get("observation") or "",
        )
        messages.success(self.request, "Atribuição recusada.")


class TaskMessageCreateView(ServiceActionView):
    def perform(self, request, pk):
        task = get_object_or_404(Task, pk=pk, activity__organization=self.organization)
        form = MessageForm(request.POST)
        if not form.is_valid():
            raise ActivityError("Escreva uma mensagem antes de enviar.")
        MessageService.post_task_message(
            task, request.user, form.cleaned_data["body"], kind=form.cleaned_data["kind"] or MessageKind.NORMAL
        )

    def redirect_to(self):
        return f"{reverse('task-detail', args=[self.kwargs['pk']])}#conversa"

    def post(self, request, *args, **kwargs):
        if _is_ajax(request):
            try:
                self.perform(request, *args, **kwargs)
            except ActivityError as exc:
                return JsonResponse({"error": str(exc)}, status=400)
            return JsonResponse({"ok": True})
        return super().post(request, *args, **kwargs)


class TaskManualTimeView(TaskFormActionView):
    form_class = ManualTimeForm
    required_action = catalog.TEMPO_LANCAR_MANUAL
    title = "Adicionar tempo trabalhado"
    submit_label = "Lançar tempo"

    def run(self, task, data):
        TaskService.log_manual_time(
            task,
            user=self.request.user,
            started_at=data["started_at"],
            ended_at=data["ended_at"],
            logged_by=self.request.user,
            reason=data["reason"],
            note=data.get("note") or "",
        )
        messages.success(self.request, "Tempo adicionado à tarefa.")


# ---------------------------------------------------------------------------
# Prazos
# ---------------------------------------------------------------------------


class DeadlineProposeView(TaskFormActionView):
    form_class = DeadlineProposalForm
    required_action = catalog.PRAZO_PROPOR
    title = "Propor novo prazo"
    submit_label = "Enviar proposta"

    def run(self, task, data):
        DeadlineService.propose(task, data["proposed_deadline"], self.request.user)
        messages.success(self.request, "Prazo enviado para aprovação do dono da demanda.")


class DeadlineDecisionView(OrganizationRequiredMixin, View):
    decision = None

    def post(self, request, pk):
        proposal = get_object_or_404(
            DeadlineProposal, pk=pk, task__activity__organization=self.organization
        )
        notification = None
        notification_id = request.POST.get("notification_id")
        if notification_id:
            if self.decision != "accept" or not notification_id.isdecimal():
                raise Http404
            notification = get_object_or_404(
                Notification, pk=notification_id, recipient=request.user,
                event_type=Notification.EventType.DEADLINE_PROPOSED,
                task_id=proposal.task_id, created_at__gte=proposal.proposed_at,
            )
            related_proposal = NotificationService.deadline_proposal(notification)
            if related_proposal is None or related_proposal.pk != proposal.pk:
                raise Http404
        note = request.POST.get("note", "")
        try:
            if self.decision == "accept":
                with transaction.atomic():
                    DeadlineService.accept(proposal, request.user)
                    if notification is not None:
                        NotificationService.mark_read(notification)
                messages.success(request, "Prazo aceito.")
            else:
                DeadlineService.reject(proposal, request.user, note)
                messages.warning(
                    request, "Prazo recusado. O conflito foi registrado e os responsáveis avisados."
                )
        except ActivityError as exc:
            messages.error(request, str(exc))
        return redirect("task-detail", pk=proposal.task_id)


class ConflictResolveView(OrganizationRequiredMixin, FormView):
    template_name = "activities/conflict_resolve.html"
    form_class = ConflictResolutionForm

    def get_conflict(self):
        return get_object_or_404(
            DeadlineConflict, pk=self.kwargs["pk"], task__activity__organization=self.organization
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["conflict"] = self.get_conflict()
        return context

    def form_valid(self, form):
        conflict = self.get_conflict()
        try:
            DeadlineService.resolve_conflict(
                conflict, self.request.user, form.cleaned_data["resolution_note"]
            )
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Conflito resolvido.")
        return redirect("task-detail", pk=conflict.task_id)


# ---------------------------------------------------------------------------
# Fila
# ---------------------------------------------------------------------------


class QueueView(OrganizationRequiredMixin, TemplateView):
    """Fila do setor. Quem é de fora só enxerga a própria posição (doc 09 §97-99)."""

    template_name = "activities/queue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        my_sectors = user_sectors(user)
        sectors = Sector.objects.filter(organization=self.organization, is_active=True)

        sector_id = self.kwargs.get("sector_pk") or self.request.GET.get("sector")
        sector = None
        if sector_id:
            sector = get_object_or_404(Sector, pk=sector_id, organization=self.organization)
        elif my_sectors.exists():
            sector = my_sectors.first()
        elif sectors.exists():
            sector = sectors.first()

        context["sectors"] = sectors
        context["sector"] = sector
        if sector is None:
            return context

        # Ver a fila inteira é uma ação autorizada, não consequência de
        # participar do setor (Regras 08 §14, doc 05 §24, §45).
        may_see_full = can(user, catalog.FILA_VISUALIZAR_COMPLETA, sector)
        entries = (
            QueueEntry.objects.filter(sector=sector, left_at__isnull=True)
            .select_related("task", "task__activity", "task__activity__owner")
            .order_by("position")
        )
        total = entries.count()

        context.update(
            {
                "may_see_full": may_see_full,
                "total": total,
                "can_reorder": can(user, catalog.FILA_REORDENAR, sector),
                "now": timezone.now(),
            }
        )

        from core.colors import EnumColorResolver

        status_colors = EnumColorResolver(self.organization, "task_status")

        if may_see_full:
            context["entries"] = list(entries)
            for entry in context["entries"]:
                entry.task._status_color = status_colors.color_for(entry.task.status)
                entry.task._status_label = status_colors.label_for(entry.task.status, entry.task.get_status_display())
            context["in_execution"] = sum(
                1 for e in entries if e.task.status == Task.Status.EM_EXECUCAO
            )
            context["blocked"] = sum(1 for e in entries if e.task.status == Task.Status.BLOQUEADA)
        else:
            # Só as próprias demandas: posição e prazo, sem título alheio.
            my_entries = list(
                entries.filter(
                    Q(task__activity__owner=user)
                    | Q(task__responsavel=user)
                    | Q(task__executors__user=user, task__executors__removed_at__isnull=True)
                ).distinct()
            )
            for entry in my_entries:
                entry.task._status_color = status_colors.color_for(entry.task.status)
                entry.task._status_label = status_colors.label_for(entry.task.status, entry.task.get_status_display())
            context["my_entries"] = my_entries
        return context


class QueueReorderView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        entry = get_object_or_404(
            QueueEntry, pk=pk, sector__organization=self.organization, left_at__isnull=True
        )
        form = ReorderForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Informe uma posição válida.")
        else:
            try:
                QueueService.reorder(
                    entry,
                    form.cleaned_data["new_position"],
                    request.user,
                    reason=form.cleaned_data.get("reason") or None,
                )
                messages.success(request, "Fila reordenada.")
            except ActivityError as exc:
                messages.error(request, str(exc))
        return redirect(f"{reverse('queue')}?sector={entry.sector_id}")


# ---------------------------------------------------------------------------
# Visão do gestor
# ---------------------------------------------------------------------------


class ManagementView(OrganizationRequiredMixin, TemplateView):
    """Gestão por exceção: mostra o que precisa de decisão (doc 09 §157-173).

    A checagem é própria porque a tela reúne vários setores: quem acompanha
    métricas em algum deles pode entrar, e cada bloco continua recortado.
    """

    template_name = "activities/management.html"

    def dispatch(self, request, *args, **kwargs):
        # Abre para quem acompanha métricas em qualquer setor; o conteúdo
        # continua recortado pelo escopo de cada bloco.
        if request.user.is_authenticated and not AuthorizationService.can_anywhere(
            request.user, catalog.METRICAS_VISUALIZAR
        ):
            raise PermissionDenied("Você não possui acesso a este conteúdo.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.organization
        now = timezone.now()

        sectors = (
            Sector.objects.filter(organization=org, is_active=True)
            .annotate(
                queue_size=Count(
                    "queue_entries", filter=Q(queue_entries__left_at__isnull=True), distinct=True
                )
            )
            .order_by("-queue_size", "name")
        )

        open_tasks = Task.objects.filter(
            activity__organization=org, status__in=OPEN_TASK_STATUSES
        ).select_related("activity", "sector", "activity__owner")

        overdue = open_tasks.filter(committed_deadline__lt=now).order_by("committed_deadline")
        blocked = open_tasks.filter(status=Task.Status.BLOQUEADA).prefetch_related("blocks")
        conflicts = (
            DeadlineConflict.objects.filter(
                task__activity__organization=org, status=DeadlineConflict.Status.ABERTO
            )
            .select_related("task", "task__activity", "proposal")
            .order_by("-opened_at")
        )

        stale_since = now - timedelta(days=3)
        stalled = (
            Activity.objects.filter(organization=org)
            .exclude(status__in=[Activity.Status.CONCLUIDA, Activity.Status.CANCELADA])
            .filter(Q(first_action_at__isnull=True) | Q(audit_entries__timestamp__lt=stale_since))
            .distinct()
            .order_by("created_at")[:10]
        )

        today = now.date()
        context.update(
            {
                "sectors": sectors,
                "overdue_tasks": overdue[:20],
                "overdue_count": overdue.count(),
                "blocked_tasks": blocked[:20],
                "blocked_count": blocked.count(),
                "conflicts": conflicts,
                "stalled_activities": stalled,
                "entered_today": Task.objects.filter(
                    activity__organization=org, created_at__date=today
                ).count(),
                "completed_today": Task.objects.filter(
                    activity__organization=org, completed_at__date=today
                ).count(),
                "open_total": open_tasks.count(),
                "can_resolve_conflicts": can(self.request.user, catalog.ESCALONAMENTO_RESOLVER),
            }
        )

        # ------------------------------------------------------------------
        # Painel filtrado — modelo enviado como exemplo (período, cliente,
        # responsável, status e centro de custo), acrescido do filtro de
        # setor e do quadro "Filas por setor" pedidos além da imagem.
        # ------------------------------------------------------------------
        dash_activities = Activity.objects.filter(organization=org)

        d_status = self.request.GET.get("status", "")
        if d_status:
            dash_activities = dash_activities.filter(status=d_status)

        d_client = self.request.GET.get("cliente", "")
        if d_client:
            dash_activities = dash_activities.filter(client_id=d_client)

        d_owner = self.request.GET.get("responsavel", "")
        if d_owner:
            dash_activities = dash_activities.filter(owner_id=d_owner)

        d_cost_center = self.request.GET.get("centro_custo", "")
        if d_cost_center:
            dash_activities = dash_activities.filter(cost_center_id=d_cost_center)

        d_sector = self.request.GET.get("grupo", "")
        if d_sector:
            dash_activities = dash_activities.filter(sector_id=d_sector)

        d_period_from = self.request.GET.get("periodo_de", "")
        if d_period_from:
            dash_activities = dash_activities.filter(created_at__date__gte=d_period_from)
        d_period_to = self.request.GET.get("periodo_ate", "")
        if d_period_to:
            dash_activities = dash_activities.filter(created_at__date__lte=d_period_to)

        dash_total = dash_activities.count()
        dash_em_andamento = dash_activities.filter(
            status__in=[Activity.Status.EM_ANDAMENTO, Activity.Status.BLOQUEADA]
        ).count()
        dash_pendentes = dash_activities.filter(status=Activity.Status.ABERTA).count()
        dash_concluidas = dash_activities.filter(status=Activity.Status.CONCLUIDA).count()
        # "Declinadas" (imagem) não existe como status próprio aqui — a
        # atividade equivalente, que não seguirá adiante, é a Cancelada.
        dash_declinadas = dash_activities.filter(status=Activity.Status.CANCELADA).count()
        dash_atrasadas = (
            dash_activities.filter(requested_deadline__lt=now)
            .exclude(status__in=[Activity.Status.CONCLUIDA, Activity.Status.CANCELADA])
            .count()
        )

        avg_duration = dash_activities.filter(
            status=Activity.Status.CONCLUIDA, completed_at__isnull=False
        ).aggregate(media=Avg(F("completed_at") - F("created_at")))["media"]
        dash_tempo_medio = round(avg_duration.total_seconds() / 86400, 1) if avg_duration else None

        dash_taxa_sucesso = round((dash_concluidas / dash_total) * 100, 1) if dash_total else None
        dash_taxa_declinio = round((dash_declinadas / dash_total) * 100, 1) if dash_total else None
        # "Concluídas com pendências": chegaram ao fim mas passaram por ao
        # menos uma devolução de tarefa no caminho (Regras 02 §36-39).
        dash_concluidas_pendencias = (
            dash_activities.filter(status=Activity.Status.CONCLUIDA, tasks__returns__isnull=False)
            .distinct()
            .count()
        )

        dash_maiores_atrasos = (
            dash_activities.filter(requested_deadline__lt=now)
            .exclude(status__in=[Activity.Status.CONCLUIDA, Activity.Status.CANCELADA])
            .select_related("client", "owner")
            .order_by("requested_deadline")[:10]
        )
        dash_recem_concluidas = (
            dash_activities.filter(status=Activity.Status.CONCLUIDA)
            .select_related("client", "owner")
            .order_by("-completed_at")[:10]
        )
        dash_por_cliente = (
            dash_activities.exclude(client__isnull=True)
            .values("client_id", "client__name")
            .annotate(total=Count("id", distinct=True))
            .order_by("-total")[:10]
        )
        dash_por_responsavel = (
            dash_activities.values("owner_id", "owner__username")
            .annotate(
                total=Count("id", distinct=True),
                concluidas=Count("id", filter=Q(status=Activity.Status.CONCLUIDA), distinct=True),
            )
            .order_by("-total")[:10]
        )
        dash_por_centro_custo = (
            dash_activities.exclude(cost_center__isnull=True)
            .values("cost_center_id", "cost_center__name")
            .annotate(total=Count("id", distinct=True))
            .order_by("-total")[:10]
        )

        from core.colors import EnumColorResolver

        dash_status_colors = EnumColorResolver(org, "activity_status")
        dash_status_choices = [
            (code, dash_status_colors.label_for(code, label))
            for code, label in Activity.Status.choices
            if not dash_status_colors.is_hidden(code)
        ]

        context.update(
            {
                "dash_clients": Client.objects.filter(organization=org, is_active=True),
                "dash_owners": User.objects.filter(
                    profile__organization=org, is_active=True
                ).order_by("first_name", "username"),
                "dash_cost_centers": CostCenter.objects.filter(organization=org, is_active=True),
                "dash_sectors": Sector.objects.filter(organization=org, is_active=True),
                "dash_status_choices": dash_status_choices,
                "f_periodo_de": d_period_from,
                "f_periodo_ate": d_period_to,
                "f_dash_cliente": d_client,
                "f_dash_responsavel": d_owner,
                "f_dash_status": d_status,
                "f_dash_centro_custo": d_cost_center,
                "f_dash_setor": d_sector,
                "dash_has_filters": bool(
                    d_status or d_client or d_owner or d_cost_center or d_sector or d_period_from or d_period_to
                ),
                "dash_total": dash_total,
                "dash_em_andamento": dash_em_andamento,
                "dash_pendentes": dash_pendentes,
                "dash_concluidas": dash_concluidas,
                "dash_declinadas": dash_declinadas,
                "dash_atrasadas": dash_atrasadas,
                "dash_tempo_medio": dash_tempo_medio,
                "dash_taxa_sucesso": dash_taxa_sucesso,
                "dash_taxa_declinio": dash_taxa_declinio,
                "dash_concluidas_pendencias": dash_concluidas_pendencias,
                "dash_maiores_atrasos": dash_maiores_atrasos,
                "dash_recem_concluidas": dash_recem_concluidas,
                "dash_por_cliente": dash_por_cliente,
                "dash_por_responsavel": dash_por_responsavel,
                "dash_por_centro_custo": dash_por_centro_custo,
                # Mesmo quadro de "Filas por setor" já existente na página,
                # trazido também para dentro do painel filtrado; respeita o
                # filtro de setor quando um setor específico é escolhido.
                "dash_filas_por_setor": sectors.filter(pk=d_sector) if d_sector else sectors,
                # Origem das horas registradas nas atividades filtradas:
                # cronômetro × informado pela pessoa, e por quê (Regras 04 §119).
                "dash_time_origin": WorkTimeService.origin_breakdown(dash_activities),
            }
        )
        return context


class HistoryView(OrganizationRequiredMixin, ListView):
    """Histórico em linguagem humana (doc 09 §122-130)."""

    template_name = "activities/history.html"
    context_object_name = "entries"
    paginate_by = 50

    def get_queryset(self):
        queryset = AuditLog.objects.filter(
            activity__organization=self.organization
        ).select_related("user", "activity", "task")

        event = self.request.GET.get("event")
        groups = {
            "tarefas": [
                AuditLog.Action.TASK_CREATED,
                AuditLog.Action.COMPLETE,
                AuditLog.Action.EXECUTOR_ADDED,
                AuditLog.Action.EXECUTOR_REMOVED,
            ],
            "prazos": [
                AuditLog.Action.DEADLINE_PROPOSED,
                AuditLog.Action.DEADLINE_ACCEPTED,
                AuditLog.Action.DEADLINE_REJECTED,
                AuditLog.Action.CONFLICT_OPENED,
                AuditLog.Action.CONFLICT_RESOLVED,
            ],
            "fila": [AuditLog.Action.QUEUE_POSITION_CHANGED, AuditLog.Action.SECTOR_MOVED],
            "devolucoes": [AuditLog.Action.RETURNED],
            "tempo": [AuditLog.Action.SESSION_STARTED, AuditLog.Action.SESSION_PAUSED],
        }
        if event in groups:
            queryset = queryset.filter(action__in=groups[event])
        return queryset.order_by("-timestamp")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = self.request.GET.get("event", "")
        return context
