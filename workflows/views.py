from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, View

from .forms import (
    ActivityBlockForm,
    ActivityCancelForm,
    ActivityCompleteForm,
    ActivityReopenForm,
    AttachmentForm,
    ProcessCancelForm,
    ProcessCreateForm,
)
from .models import Process, ProcessStep
from .services import WorkflowError, WorkflowService


class ProcessListView(LoginRequiredMixin, ListView):
    model = Process
    template_name = "workflows/process_list.html"
    context_object_name = "processes"
    paginate_by = 25

    def get_queryset(self):
        qs = Process.objects.select_related("template", "created_by").order_by("-created_at")
        user = self.request.user
        if user.has_perm("workflows.can_view_all_processes"):
            return qs
        return qs.filter(
            Q(created_by=user) | Q(steps__responsible_group__in=user.groups.all())
        ).distinct()


class ProcessCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Process
    form_class = ProcessCreateForm
    template_name = "workflows/process_form.html"
    permission_required = "workflows.can_create_process"

    def form_valid(self, form):
        try:
            process = WorkflowService.instanciar_processo(
                template=form.cleaned_data["template"],
                title=form.cleaned_data["title"],
                criado_por=self.request.user,
            )
        except WorkflowError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f"Processo '{process.title}' criado.")
        self.object = process
        return redirect("process-detail", pk=process.pk)


class ProcessDetailView(LoginRequiredMixin, DetailView):
    model = Process
    template_name = "workflows/process_detail.html"
    context_object_name = "process"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["steps"] = self.object.steps.select_related("responsible_group", "assigned_to").order_by("order")
        ctx["attachments"] = self.object.attachments.select_related("uploaded_by", "step")
        ctx["attachment_form"] = AttachmentForm(process=self.object)
        ctx["cancel_form"] = ProcessCancelForm()
        return ctx


class ProcessCancelView(LoginRequiredMixin, FormView):
    form_class = ProcessCancelForm

    def form_valid(self, form):
        process = get_object_or_404(Process, pk=self.kwargs["pk"])
        try:
            WorkflowService.cancelar_processo(process, self.request.user, form.cleaned_data["motivo"])
            messages.success(self.request, "Processo cancelado.")
        except WorkflowError as exc:
            messages.error(self.request, str(exc))
        return redirect("process-detail", pk=process.pk)

    def form_invalid(self, form):
        messages.error(self.request, "Informe o motivo do cancelamento.")
        return redirect("process-detail", pk=self.kwargs["pk"])

    def get(self, request, *args, **kwargs):
        return redirect("process-detail", pk=self.kwargs["pk"])


class ProcessTimelineView(LoginRequiredMixin, DetailView):
    model = Process
    template_name = "workflows/process_timeline.html"
    context_object_name = "process"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["entries"] = self.object.audit_entries.select_related("user", "step").order_by("timestamp")
        return ctx


class AttachmentUploadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        process = get_object_or_404(Process, pk=pk)
        form = AttachmentForm(request.POST, request.FILES, process=process)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.process = process
            attachment.uploaded_by = request.user
            attachment.save()
            messages.success(request, "Arquivo anexado.")
        else:
            messages.error(request, "Não foi possível anexar o arquivo. Verifique os campos.")
        return redirect("process-detail", pk=pk)


class MyActivitiesListView(LoginRequiredMixin, ListView):
    model = ProcessStep
    template_name = "workflows/activity_list.html"
    context_object_name = "activities"
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        qs = ProcessStep.objects.select_related("process", "responsible_group", "assigned_to").exclude(
            status__in=[ProcessStep.Status.CONCLUIDA, ProcessStep.Status.CANCELADA]
        )
        return qs.filter(
            Q(assigned_to=user)
            | Q(responsible_group__in=user.groups.all(), status=ProcessStep.Status.PENDENTE, released_at__isnull=False)
        ).distinct().order_by("deadline_at")


class ActivityDetailView(LoginRequiredMixin, DetailView):
    model = ProcessStep
    template_name = "workflows/activity_detail.html"
    context_object_name = "step"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        step = self.object
        user = self.request.user
        in_group = user.groups.filter(pk=step.responsible_group_id).exists()

        ctx["complete_form"] = ActivityCompleteForm()
        ctx["reopen_form"] = ActivityReopenForm()
        ctx["block_form"] = ActivityBlockForm()
        ctx["cancel_form"] = ActivityCancelForm()

        ctx["can_claim"] = (
            step.status == ProcessStep.Status.PENDENTE
            and step.released_at is not None
            and (in_group or user.has_perm("workflows.can_claim_any_activity"))
        )
        ctx["can_complete"] = step.status in (
            ProcessStep.Status.EM_ANDAMENTO,
            ProcessStep.Status.EM_REVISAO,
        ) and (step.assigned_to_id == user.id or user.has_perm("workflows.can_override_assignment"))
        ctx["can_reopen"] = step.status == ProcessStep.Status.CONCLUIDA and user.has_perm(
            "workflows.can_reopen_activity"
        )
        ctx["can_block"] = step.status in (
            ProcessStep.Status.PENDENTE,
            ProcessStep.Status.EM_ANDAMENTO,
        ) and (in_group or user.has_perm("workflows.can_block_activity"))
        ctx["can_unblock"] = step.status == ProcessStep.Status.BLOQUEADA and (
            in_group or user.has_perm("workflows.can_block_activity")
        )
        ctx["can_cancel"] = step.status in (
            ProcessStep.Status.PENDENTE,
            ProcessStep.Status.EM_ANDAMENTO,
        ) and user.has_perm("workflows.can_cancel_process")
        return ctx


class BaseActivityActionView(LoginRequiredMixin, View):
    def get_step(self):
        return get_object_or_404(ProcessStep, pk=self.kwargs["pk"])

    def get(self, request, *args, **kwargs):
        return redirect("activity-detail", pk=self.kwargs["pk"])


class ActivityClaimView(BaseActivityActionView):
    def post(self, request, pk):
        step = self.get_step()
        try:
            WorkflowService.assumir_atividade(step, request.user)
            messages.success(request, "Atividade assumida.")
        except WorkflowError as exc:
            messages.error(request, str(exc))
        return redirect("activity-detail", pk=pk)


class ActivityCompleteView(BaseActivityActionView):
    def post(self, request, pk):
        step = self.get_step()
        form = ActivityCompleteForm(request.POST)
        observations = form.cleaned_data["observations"] if form.is_valid() else ""
        try:
            WorkflowService.concluir_atividade(step, request.user, observations)
            messages.success(request, "Atividade concluída.")
        except WorkflowError as exc:
            messages.error(request, str(exc))
        return redirect("activity-detail", pk=pk)


class ActivityReopenView(BaseActivityActionView):
    def post(self, request, pk):
        step = self.get_step()
        form = ActivityReopenForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Informe o motivo da reabertura.")
            return redirect("activity-detail", pk=pk)
        try:
            WorkflowService.reabrir_atividade(step, request.user, form.cleaned_data["motivo"])
            messages.success(request, "Atividade reaberta.")
        except WorkflowError as exc:
            messages.error(request, str(exc))
        return redirect("activity-detail", pk=pk)


class ActivityBlockView(BaseActivityActionView):
    def post(self, request, pk):
        step = self.get_step()
        form = ActivityBlockForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Descreva o motivo do bloqueio.")
            return redirect("activity-detail", pk=pk)
        try:
            WorkflowService.bloquear_atividade(step, request.user, form.cleaned_data["observations"])
            messages.success(request, "Atividade bloqueada.")
        except WorkflowError as exc:
            messages.error(request, str(exc))
        return redirect("activity-detail", pk=pk)


class ActivityUnblockView(BaseActivityActionView):
    def post(self, request, pk):
        step = self.get_step()
        try:
            WorkflowService.desbloquear_atividade(step, request.user)
            messages.success(request, "Atividade desbloqueada.")
        except WorkflowError as exc:
            messages.error(request, str(exc))
        return redirect("activity-detail", pk=pk)


class ActivityCancelView(BaseActivityActionView):
    def post(self, request, pk):
        step = self.get_step()
        form = ActivityCancelForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Informe o motivo do cancelamento.")
            return redirect("activity-detail", pk=pk)
        try:
            WorkflowService.cancelar_atividade(step, request.user, form.cleaned_data["motivo"])
            messages.success(request, "Atividade cancelada.")
        except WorkflowError as exc:
            messages.error(request, str(exc))
        return redirect("activity-detail", pk=pk)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "workflows/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()

        my_steps = ProcessStep.objects.filter(assigned_to=user).exclude(
            status__in=[ProcessStep.Status.CONCLUIDA, ProcessStep.Status.CANCELADA]
        )
        claimable_steps = ProcessStep.objects.filter(
            responsible_group__in=user.groups.all(),
            status=ProcessStep.Status.PENDENTE,
            released_at__isnull=False,
        )
        ctx["my_pending_count"] = my_steps.count()
        ctx["my_overdue"] = my_steps.filter(deadline_at__lt=now)
        ctx["my_urgent"] = my_steps.filter(priority__in=["ALTA", "URGENTE"])
        ctx["claimable_count"] = claimable_steps.count()

        if user.has_perm("workflows.can_view_dashboard"):
            ctx["show_aggregate"] = True
            ctx["processes_active"] = Process.objects.filter(status=Process.Status.ABERTO).count()
            ctx["processes_finalized"] = Process.objects.filter(status=Process.Status.FINALIZADO).count()
            ctx["processes_cancelled"] = Process.objects.filter(status=Process.Status.CANCELADO).count()
            open_steps = ProcessStep.objects.exclude(
                status__in=[ProcessStep.Status.CONCLUIDA, ProcessStep.Status.CANCELADA]
            )
            ctx["activities_overdue_count"] = open_steps.filter(deadline_at__lt=now).count()
            ctx["activities_in_progress_count"] = open_steps.filter(status=ProcessStep.Status.EM_ANDAMENTO).count()

            from django.contrib.auth.models import Group

            by_group = []
            for group in Group.objects.all():
                pending = open_steps.filter(responsible_group=group).count()
                overdue = open_steps.filter(responsible_group=group, deadline_at__lt=now).count()
                if pending:
                    by_group.append({"group": group, "pending": pending, "overdue": overdue})
            ctx["activities_by_group"] = by_group

        return ctx
