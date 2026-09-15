from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DetailView, FormView, ListView, TemplateView, View

from audit.models import AuditLog
from acessos import catalog
from acessos.services import AuthorizationService
from core.mixins import ActionRequiredMixin, OrganizationRequiredMixin, user_sectors
from core.models import Sector

from .forms import (
    ActivityEditForm,
    ActivityQuickCreateForm,
    CancelForm,
    ChangeOwnerForm,
    ConflictResolutionForm,
    DeadlineProposalForm,
    ExecutorForm,
    ManualTimeForm,
    MessageForm,
    MoveSectorForm,
    ReorderForm,
    TaskBlockForm,
    TaskForm,
    TaskReturnForm,
)
from .models import (
    Activity,
    DeadlineConflict,
    DeadlineProposal,
    QueueEntry,
    Task,
    TaskExecutor,
    WorkSession,
)
from .services import (
    ActivityError,
    ActivityService,
    DeadlineService,
    MessageService,
    QueueService,
    TaskService,
)

OPEN_TASK_STATUSES = [
    Task.Status.DISPONIVEL,
    Task.Status.EM_FILA,
    Task.Status.EM_EXECUCAO,
    Task.Status.BLOQUEADA,
]


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


def active_session(user):
    return (
        WorkSession.objects.filter(user=user, ended_at__isnull=True)
        .select_related("task", "task__activity")
        .first()
    )


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
    return {"proposals": proposals, "conflicts": conflicts}


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

        session = active_session(user)
        my_sectors = user_sectors(user)

        next_tasks = (
            Task.objects.filter(
                activity__organization=org,
                status__in=[Task.Status.DISPONIVEL, Task.Status.EM_FILA],
            )
            .filter(Q(executors__user=user, executors__removed_at__isnull=True) | Q(sector__in=my_sectors))
            .select_related("activity", "sector")
            .distinct()
            .order_by("requested_deadline", "created_at")[:8]
        )

        followed = (
            Activity.objects.filter(organization=org, owner=user)
            .exclude(status__in=[Activity.Status.CONCLUIDA, Activity.Status.CANCELADA])
            .annotate(
                total_tasks=Count("tasks", distinct=True),
                done_tasks=Count("tasks", filter=Q(tasks__status=Task.Status.CONCLUIDA), distinct=True),
            )
            .order_by("requested_deadline", "-created_at")[:6]
        )

        pending = pending_items(user, org)

        # Cartões do topo: só número que leva a uma ação (Benchmark §8.3).
        my_open = Task.objects.filter(
            activity__organization=org,
            executors__user=user,
            executors__removed_at__isnull=True,
        ).exclude(status__in=[Task.Status.CONCLUIDA, Task.Status.CANCELADA]).distinct()

        summary = {
            "open_tasks": my_open.count(),
            "overdue": my_open.filter(
                committed_deadline__lt=timezone.now(),
            ).exclude(status=Task.Status.CONCLUIDA).count(),
            "blocked": my_open.filter(status=Task.Status.BLOQUEADA).count(),
            "waiting_decision": pending["proposals"].count() + pending["conflicts"].count(),
        }

        context.update(
            {
                "active_session": session,
                "active_task": session.task if session else None,
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


class ActivityListView(OrganizationRequiredMixin, ListView):
    template_name = "activities/activity_list.html"
    context_object_name = "activities"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        tab = self.request.GET.get("tab", "minhas")
        queryset = Activity.objects.filter(organization=self.organization)

        if tab == "participando":
            queryset = queryset.filter(
                tasks__executors__user=user, tasks__executors__removed_at__isnull=True
            ).exclude(owner=user)
        elif tab == "concluidas":
            queryset = queryset.filter(
                Q(owner=user) | Q(tasks__executors__user=user, tasks__executors__removed_at__isnull=True),
                status__in=[Activity.Status.CONCLUIDA, Activity.Status.CANCELADA],
            )
        elif tab == "todas":
            if not can(user, catalog.ATIVIDADE_VISUALIZAR_TODAS):
                queryset = queryset.filter(owner=user)
        else:
            queryset = queryset.filter(owner=user)

        if tab != "concluidas":
            queryset = queryset.exclude(
                status__in=[Activity.Status.CONCLUIDA, Activity.Status.CANCELADA]
            )

        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(site__name__icontains=search)
            )

        sector = self.request.GET.get("sector")
        if sector:
            queryset = queryset.filter(tasks__sector_id=sector)

        return (
            queryset.select_related("owner", "company", "site")
            .annotate(
                total_tasks=Count("tasks", distinct=True),
                done_tasks=Count("tasks", filter=Q(tasks__status=Task.Status.CONCLUIDA), distinct=True),
            )
            .distinct()
            .order_by(*self._ordering())
        )

    ORDERINGS = {
        "prazo": ("requested_deadline", "-created_at"),
        "recentes": ("-created_at",),
        "titulo": ("title",),
    }

    def _ordering(self):
        return self.ORDERINGS.get(self.request.GET.get("ordem"), self.ORDERINGS["prazo"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tab"] = self.request.GET.get("tab", "minhas")
        context["search"] = self.request.GET.get("q", "")
        context["ordem"] = self.request.GET.get("ordem", "prazo")
        context["sectors"] = Sector.objects.filter(organization=self.organization, is_active=True)
        context["selected_sector"] = self.request.GET.get("sector", "")
        context["can_view_all"] = can(self.request.user, catalog.ATIVIDADE_VISUALIZAR_TODAS)
        return context


class ActivityCreateView(OrganizationRequiredMixin, FormView):
    template_name = "activities/activity_form.html"
    form_class = ActivityQuickCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            activity = ActivityService.create_activity(
                organization=self.organization,
                title=data["title"],
                owner=data["owner"],
                created_by=self.request.user,
                description=data.get("description") or "",
                company=data.get("company"),
                site=data.get("site"),
                cost_center=data.get("cost_center"),
                requested_deadline=data.get("requested_deadline"),
            )
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        # Ação encadeada: criar e já abrir a primeira tarefa (Benchmark §6).
        if "salvar_e_tarefas" in self.request.POST:
            messages.success(self.request, "Atividade criada. Agora defina a primeira tarefa.")
            return redirect("task-create", activity_pk=activity.pk)

        messages.success(self.request, "Atividade criada. Próximo passo: adicionar a primeira tarefa.")
        return redirect("activity-detail", pk=activity.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class ActivityDetailView(OrganizationRequiredMixin, DetailView):
    template_name = "activities/activity_detail.html"
    context_object_name = "activity"

    def get_queryset(self):
        return Activity.objects.filter(organization=self.organization).select_related(
            "owner", "created_by", "company", "site", "cost_center", "completed_by"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activity = self.object

        tasks = list(
            activity.tasks.select_related("sector", "depends_on")
            .prefetch_related(
                Prefetch(
                    "executors",
                    queryset=TaskExecutor.objects.filter(removed_at__isnull=True).select_related("user"),
                    to_attr="active_executors",
                )
            )
            .order_by("order", "created_at")
        )
        for task in tasks:
            task.queue_info = queue_position(task)

        done = sum(1 for t in tasks if t.status == Task.Status.CONCLUIDA)
        open_tasks = [t for t in tasks if t.status in OPEN_TASK_STATUSES]

        context.update(
            {
                "tab": self.request.GET.get("tab", "visao-geral"),
                "tasks": tasks,
                "tasks_done": done,
                "tasks_total": len(tasks),
                "open_tasks": open_tasks,
                "sectors_involved": sorted({t.sector.name for t in tasks}),
                "history": activity.audit_entries.select_related("user", "task").order_by("-timestamp")[:100],
                "history_filter": self.request.GET.get("event", ""),
                "activity_messages": activity.messages.select_related("author"),
                "message_form": MessageForm(),
                "owner_changes": activity.owner_changes.select_related(
                    "previous_owner", "new_owner", "changed_by"
                ),
                "can_change_owner": can(self.request.user, catalog.ATIVIDADE_ALTERAR_DONO, activity),
                "can_cancel": can(self.request.user, catalog.ATIVIDADE_CANCELAR, activity),
                "can_reopen": can(self.request.user, catalog.ATIVIDADE_REABRIR, activity),
                "can_complete": can(self.request.user, catalog.ATIVIDADE_CONCLUIR, activity),
                "can_edit": can(self.request.user, catalog.ATIVIDADE_EDITAR, activity),
                "can_add_task": can(self.request.user, catalog.TAREFA_CRIAR, activity),
                "can_message": can(self.request.user, catalog.COMUNICACAO_PARTICIPAR, activity),
                "is_owner": activity.owner_id == self.request.user.id,
            }
        )
        return context


class ActivityEditView(OrganizationRequiredMixin, FormView):
    template_name = "activities/activity_form.html"
    form_class = ActivityEditForm

    def get_activity(self):
        return get_object_or_404(Activity, pk=self.kwargs["pk"], organization=self.organization)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["instance"] = self.get_activity()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.get_activity()
        context["is_edit"] = True
        return context

    def form_valid(self, form):
        activity = self.get_activity()
        try:
            ActivityService.update_activity(activity, self.request.user, **form.cleaned_data)
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Atividade atualizada.")
        return redirect("activity-detail", pk=activity.pk)


class ActivityCompleteView(ServiceActionView):
    def perform(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        ActivityService.complete_activity(activity, request.user)
        messages.success(request, "Atividade concluída.")

    def redirect_to(self):
        return reverse("activity-detail", args=[self.kwargs["pk"]])


class ActivityCancelView(OrganizationRequiredMixin, FormView):
    template_name = "activities/activity_cancel.html"
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
            ActivityService.cancel_activity(activity, self.request.user, form.cleaned_data["reason"])
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Atividade cancelada.")
        return redirect("activity-detail", pk=activity.pk)


class ActivityReopenView(OrganizationRequiredMixin, FormView):
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
        messages.success(self.request, "Atividade reaberta.")
        return redirect("activity-detail", pk=activity.pk)


class ActivityChangeOwnerView(OrganizationRequiredMixin, FormView):
    template_name = "activities/activity_change_owner.html"
    form_class = ChangeOwnerForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
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
        messages.success(self.request, "Dono da atividade alterado.")
        return redirect("activity-detail", pk=activity.pk)


class ActivityMessageCreateView(ServiceActionView):
    def perform(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk, organization=self.organization)
        form = MessageForm(request.POST)
        if not form.is_valid():
            raise ActivityError("Escreva uma mensagem antes de enviar.")
        MessageService.post_activity_message(activity, request.user, form.cleaned_data["body"])

    def redirect_to(self):
        return f"{reverse('activity-detail', args=[self.kwargs['pk']])}?tab=conversa"


# ---------------------------------------------------------------------------
# Tarefas
# ---------------------------------------------------------------------------


class TaskListView(OrganizationRequiredMixin, ListView):
    template_name = "activities/task_list.html"
    context_object_name = "tasks"
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        tab = self.request.GET.get("tab", "minhas")
        queryset = Task.objects.filter(activity__organization=self.organization)

        if tab == "setor":
            queryset = queryset.filter(sector__in=user_sectors(user))
        else:
            queryset = queryset.filter(executors__user=user, executors__removed_at__isnull=True)

        if self.request.GET.get("status") == "concluidas":
            queryset = queryset.filter(status=Task.Status.CONCLUIDA)
        else:
            queryset = queryset.filter(status__in=OPEN_TASK_STATUSES)

        # Visões salvas por condição operacional, no lugar de segmentações
        # comerciais (Benchmark §3: atrasadas, bloqueadas, devolvidas).
        view = self.request.GET.get("filtro")
        if view == "atrasadas":
            queryset = queryset.filter(committed_deadline__lt=timezone.now()).exclude(
                status=Task.Status.CONCLUIDA
            )
        elif view == "bloqueadas":
            queryset = queryset.filter(status=Task.Status.BLOQUEADA)
        elif view == "devolvidas":
            queryset = queryset.filter(status=Task.Status.DEVOLVIDA)
        elif view == "em-execucao":
            queryset = queryset.filter(status=Task.Status.EM_EXECUCAO)

        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(activity__title__icontains=search)
            )

        sector = self.request.GET.get("sector")
        if sector:
            queryset = queryset.filter(sector_id=sector)

        return (
            queryset.select_related("activity", "sector")
            .distinct()
            .order_by("requested_deadline", "created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tab"] = self.request.GET.get("tab", "minhas")
        context["status"] = self.request.GET.get("status", "abertas")
        context["view_filter"] = self.request.GET.get("filtro", "")
        context["search"] = self.request.GET.get("q", "")
        context["sectors"] = Sector.objects.filter(organization=self.organization, is_active=True)
        context["selected_sector"] = self.request.GET.get("sector", "")
        return context


class TaskDetailView(OrganizationRequiredMixin, DetailView):
    template_name = "activities/task_detail.html"
    context_object_name = "task"

    def get_queryset(self):
        return Task.objects.filter(activity__organization=self.organization).select_related(
            "activity", "sector", "depends_on", "created_by", "completed_by"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.object
        user = self.request.user

        executors = task.executors.filter(removed_at__isnull=True).select_related("user")
        sessions = task.work_sessions.select_related("user").order_by("-started_at")
        closed = [s for s in sessions if s.ended_at]
        man_hours = sum((s.duration for s in closed), timedelta())

        my_open_session = task.work_sessions.filter(user=user, ended_at__isnull=True).first()
        is_executor = executors.filter(user=user).exists()
        open_block = task.blocks.filter(ended_at__isnull=True).order_by("-started_at").first()
        pending_proposal = task.deadline_proposals.filter(
            status=DeadlineProposal.Status.PENDENTE
        ).select_related("proposed_by").first()

        context.update(
            {
                "activity": task.activity,
                "executors": executors,
                "is_executor": is_executor,
                "my_open_session": my_open_session,
                "sessions": sessions,
                "man_hours": man_hours,
                "queue_info": queue_position(task),
                "open_block": open_block,
                "pending_proposal": pending_proposal,
                "conflicts": task.deadline_conflicts.select_related("resolved_by").order_by("-opened_at"),
                "proposals": task.deadline_proposals.select_related("proposed_by", "decided_by"),
                "returns": task.returns.select_related("from_sector", "to_sector", "reason", "returned_by"),
                "transfers": task.sector_transfers.select_related("from_sector", "to_sector", "moved_by"),
                "history": task.audit_entries.select_related("user").order_by("-timestamp")[:60],
                "task_messages": task.messages.select_related("author"),
                "message_form": MessageForm(),
                "is_owner": task.activity.owner_id == user.id,
                "can_assume": can(user, catalog.TAREFA_ASSUMIR, task),
                "can_assign": can(user, catalog.TAREFA_ATRIBUIR, task),
                "can_start": can(user, catalog.TAREFA_INICIAR, task),
                "can_complete": can(user, catalog.TAREFA_CONCLUIR, task),
                "can_return": can(user, catalog.TAREFA_DEVOLVER, task),
                "can_block": can(user, catalog.TAREFA_BLOQUEAR, task),
                "can_move": can(user, catalog.TAREFA_MOVER_SETOR, task),
                "can_cancel_task": can(user, catalog.TAREFA_CANCELAR, task),
                "can_edit_task": can(user, catalog.TAREFA_EDITAR, task),
                "can_log_time": can(user, catalog.TEMPO_LANCAR_MANUAL, task),
                "can_propose": can(user, catalog.PRAZO_PROPOR, task),
                "can_resolve_conflict": can(user, catalog.ESCALONAMENTO_RESOLVER, task),
                "can_message": can(user, catalog.COMUNICACAO_PARTICIPAR, task),
                "executor_form": ExecutorForm(organization=self.organization),
                "manual_time_form": ManualTimeForm(),
                "deadline_form": DeadlineProposalForm(),
                "return_form": TaskReturnForm(organization=self.organization, task=task),
                "block_form": TaskBlockForm(),
                "move_form": MoveSectorForm(organization=self.organization, task=task),
                "dependency_blocking": (
                    task.depends_on is not None
                    and task.depends_on.status != Task.Status.CONCLUIDA
                ),
            }
        )
        return context


class TaskCreateView(OrganizationRequiredMixin, FormView):
    template_name = "activities/task_form.html"
    form_class = TaskForm

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
        context["activity"] = self.get_activity()
        return context

    def form_valid(self, form):
        activity = self.get_activity()
        data = form.cleaned_data
        next_order = (activity.tasks.count() or 0) + 1
        try:
            TaskService.create_task(
                activity=activity,
                sector=data["sector"],
                title=data["title"],
                created_by=self.request.user,
                description=data.get("description") or "",
                order=next_order,
                depends_on=data.get("depends_on"),
                requested_deadline=data.get("requested_deadline"),
            )
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, "Tarefa adicionada.")
        if "save_and_add" in self.request.POST:
            return redirect("task-create", activity_pk=activity.pk)
        return redirect("activity-detail", pk=activity.pk)


class TaskEditView(OrganizationRequiredMixin, FormView):
    template_name = "activities/task_form.html"
    form_class = TaskForm

    def get_task(self):
        return get_object_or_404(
            Task, pk=self.kwargs["pk"], activity__organization=self.organization
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        task = self.get_task()
        kwargs["organization"] = self.organization
        kwargs["activity"] = task.activity
        kwargs["instance"] = task
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.get_task()
        context["activity"] = task.activity
        context["task"] = task
        context["is_edit"] = True
        return context

    def form_valid(self, form):
        task = self.get_task()
        data = dict(form.cleaned_data)
        # Setor tem serviço próprio (movimentação com histórico); não entra no update.
        data.pop("sector", None)
        try:
            TaskService.update_task(task, self.request.user, **data)
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Tarefa atualizada.")
        return redirect("task-detail", pk=task.pk)


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


class TaskFormActionView(OrganizationRequiredMixin, FormView):
    """Ações que exigem dados extras (devolver, bloquear, mover, prazo...)."""

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


class TaskExecutorAddView(ServiceActionView):
    def perform(self, request, pk):
        task = get_object_or_404(Task, pk=pk, activity__organization=self.organization)
        form = ExecutorForm(request.POST, organization=self.organization)
        if not form.is_valid():
            raise ActivityError("Selecione um executor válido.")
        TaskService.add_executor(task, form.cleaned_data["user"], added_by=request.user)
        messages.success(request, "Executor incluído.")

    def redirect_to(self):
        return reverse("task-detail", args=[self.kwargs["pk"]])


class TaskExecutorRemoveView(ServiceActionView):
    def perform(self, request, pk, user_pk):
        task = get_object_or_404(Task, pk=pk, activity__organization=self.organization)
        executor = get_object_or_404(
            TaskExecutor, task=task, user_id=user_pk, removed_at__isnull=True
        )
        TaskService.remove_executor(task, executor.user, removed_by=request.user)
        messages.success(request, "Executor removido.")

    def redirect_to(self):
        return reverse("task-detail", args=[self.kwargs["pk"]])


class TaskMessageCreateView(ServiceActionView):
    def perform(self, request, pk):
        task = get_object_or_404(Task, pk=pk, activity__organization=self.organization)
        form = MessageForm(request.POST)
        if not form.is_valid():
            raise ActivityError("Escreva uma mensagem antes de enviar.")
        MessageService.post_task_message(task, request.user, form.cleaned_data["body"])

    def redirect_to(self):
        return f"{reverse('task-detail', args=[self.kwargs['pk']])}#conversa"


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
        )
        messages.success(self.request, "Tempo lançado manualmente.")


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
        messages.success(self.request, "Prazo enviado para aprovação do dono da atividade.")


class DeadlineDecisionView(OrganizationRequiredMixin, View):
    decision = None

    def post(self, request, pk):
        proposal = get_object_or_404(
            DeadlineProposal, pk=pk, task__activity__organization=self.organization
        )
        note = request.POST.get("note", "")
        try:
            if self.decision == "accept":
                DeadlineService.accept(proposal, request.user)
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

        if may_see_full:
            context["entries"] = entries
            context["in_execution"] = sum(
                1 for e in entries if e.task.status == Task.Status.EM_EXECUCAO
            )
            context["blocked"] = sum(1 for e in entries if e.task.status == Task.Status.BLOQUEADA)
        else:
            # Só as próprias demandas: posição e prazo, sem título alheio.
            context["my_entries"] = entries.filter(
                Q(task__activity__owner=user)
                | Q(task__executors__user=user, task__executors__removed_at__isnull=True)
            ).distinct()
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
