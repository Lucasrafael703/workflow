from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, ListView, View

from acessos import catalog
from core.mixins import OrganizationRequiredMixin
from core.models import Company, Sector

from .forms import (
    ProcessBasicInfoForm,
    ProcessCriterionForm,
    ProcessInputForm,
    ProcessOutputForm,
    ProcessStepForm,
)
from .models import ActivityType, Process, ProcessCriterion, ProcessInput, ProcessStep, ProcessVersion
from .services import (
    ProcessCriterionService,
    ProcessError,
    ProcessInputService,
    ProcessService,
    ProcessStepService,
)


class ProcessListView(OrganizationRequiredMixin, ListView):
    template_name = "processes/process_list.html"
    context_object_name = "processes"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            Process.objects.filter(organization=self.organization)
            .select_related("company", "activity_type")
            .prefetch_related("versions")
        )
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        status = self.request.GET.get("status", "").strip()
        if status == "publicado":
            queryset = queryset.filter(versions__status=ProcessVersion.Status.PUBLICADO).distinct()
        elif status == "rascunho":
            queryset = queryset.filter(versions__status=ProcessVersion.Status.RASCUNHO).distinct()
        elif status == "inativo":
            queryset = queryset.filter(is_active=False)
        activity_type_id = self.request.GET.get("tipo", "").strip()
        if activity_type_id:
            queryset = queryset.filter(activity_type_id=activity_type_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_processes = Process.objects.filter(organization=self.organization)
        context.update(
            {
                "search": self.request.GET.get("q", ""),
                "status": self.request.GET.get("status", ""),
                "activity_type_id": self.request.GET.get("tipo", ""),
                "activity_types": ActivityType.objects.filter(organization=self.organization, is_active=True),
                "stat_active": all_processes.filter(is_active=True).count(),
                "stat_draft": all_processes.filter(versions__status=ProcessVersion.Status.RASCUNHO).distinct().count(),
                "stat_types": ActivityType.objects.filter(organization=self.organization, is_active=True).count(),
            }
        )
        return context


class ProcessCreateView(OrganizationRequiredMixin, View):
    def get(self, request):
        if not _can(request.user, catalog.PROCESSO_CRIAR):
            messages.error(request, "Você não tem permissão para criar processos.")
            return redirect("process-list")
        companies = Company.objects.filter(organization=request.user.profile.organization, is_active=True)
        return _render_new_process_form(request, companies)

    def post(self, request):
        companies = Company.objects.filter(organization=request.user.profile.organization, is_active=True)
        company = get_object_or_404(Company, pk=request.POST.get("company"), organization=self.organization)
        activity_type_id = request.POST.get("activity_type") or None
        activity_type = ActivityType.objects.filter(pk=activity_type_id, organization=self.organization).first()
        try:
            process, version = ProcessService.create(
                organization=self.organization,
                company=company,
                name=request.POST.get("name", ""),
                created_by=request.user,
                description=request.POST.get("description", ""),
                activity_type=activity_type,
            )
        except ProcessError as exc:
            messages.error(request, str(exc))
            return _render_new_process_form(request, companies)
        messages.success(request, f"Processo “{process.name}” criado como rascunho.")
        return redirect("process-edit", pk=process.pk)


def _render_new_process_form(request, companies):
    from django.shortcuts import render

    return render(
        request,
        "processes/process_new.html",
        {
            "companies": companies,
            "activity_types": ActivityType.objects.filter(organization=request.user.profile.organization, is_active=True),
        },
    )


def _can(user, action_key, resource=None):
    from acessos.services import AuthorizationService

    return AuthorizationService.can(user, action_key, resource)


class ProcessEditView(OrganizationRequiredMixin, DetailView):
    template_name = "processes/process_edit.html"
    context_object_name = "process"
    model = Process

    def get_queryset(self):
        return Process.objects.filter(organization=self.organization)

    def get_version(self, process):
        pk = self.request.GET.get("v")
        if pk:
            return get_object_or_404(ProcessVersion, pk=pk, process=process)
        return process.draft_version or process.published_version or process.versions.order_by("-number").first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process = context["process"]
        version = self.get_version(process)
        context.update(
            {
                "version": version,
                "versions": process.versions.order_by("-number"),
                "inputs": version.inputs.all() if version else [],
                "criteria": version.criteria.all() if version else [],
                "steps": version.steps.select_related("sector").all() if version else [],
                "sectors": Sector.objects.filter(organization=self.organization, is_active=True),
                "input_form": ProcessInputForm(),
                "output_form": ProcessOutputForm(),
                "criterion_form": ProcessCriterionForm(),
                "step_form": ProcessStepForm(sectors=Sector.objects.filter(organization=self.organization, is_active=True)),
                "basic_form": ProcessBasicInfoForm(
                    activity_types=ActivityType.objects.filter(organization=self.organization, is_active=True),
                    initial={
                        "name": process.name,
                        "description": process.description,
                        "activity_type": process.activity_type_id,
                    },
                ),
                "can_edit": bool(version and version.is_editable),
                "can_publish": _can(self.request.user, catalog.PROCESSO_PUBLICAR),
            }
        )
        return context


class ProcessBasicInfoUpdateView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        version = process.draft_version
        if version is None:
            messages.error(request, "Não há rascunho em edição.")
            return redirect("process-edit", pk=process.pk)
        activity_type_id = request.POST.get("activity_type") or None
        activity_type = ActivityType.objects.filter(pk=activity_type_id, organization=self.organization).first()
        try:
            ProcessService.update_basic_info(
                version,
                request.user,
                name=request.POST.get("name"),
                description=request.POST.get("description", ""),
                activity_type=activity_type,
            )
            messages.success(request, "Informações básicas atualizadas.")
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect("process-edit", pk=process.pk)


class ProcessOutputUpdateView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        version = process.draft_version
        if version is None:
            messages.error(request, "Não há rascunho em edição.")
            return redirect("process-edit", pk=process.pk)
        try:
            ProcessService.update_output(
                version, request.user, request.POST.get("output_description", ""), request.POST.get("output_evidence_type", "")
            )
            messages.success(request, "Output atualizado.")
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("process-edit", args=[process.pk]) + "#output")


class ProcessInputAddView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        version = process.draft_version
        if version is None:
            messages.error(request, "Não há rascunho em edição.")
            return redirect("process-edit", pk=process.pk)
        try:
            ProcessInputService.add(
                version, request.user,
                name=request.POST.get("name", ""),
                input_type=request.POST.get("input_type", ProcessInput.InputType.TEXTO),
                is_required=bool(request.POST.get("is_required")),
                source=request.POST.get("source", ""),
                help_text=request.POST.get("help_text", ""),
            )
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("process-edit", args=[process.pk]) + "#inputs")


class ProcessInputRemoveView(OrganizationRequiredMixin, View):
    def post(self, request, pk, input_pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        item = get_object_or_404(ProcessInput, pk=input_pk, version__process=process)
        try:
            ProcessInputService.remove(item, request.user)
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("process-edit", args=[process.pk]) + "#inputs")


class ProcessCriterionAddView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        version = process.draft_version
        if version is None:
            messages.error(request, "Não há rascunho em edição.")
            return redirect("process-edit", pk=process.pk)
        try:
            ProcessCriterionService.add(
                version, request.user,
                name=request.POST.get("name", ""),
                is_required=bool(request.POST.get("is_required")),
            )
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("process-edit", args=[process.pk]) + "#criterios")


class ProcessCriterionRemoveView(OrganizationRequiredMixin, View):
    def post(self, request, pk, criterion_pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        item = get_object_or_404(ProcessCriterion, pk=criterion_pk, version__process=process)
        try:
            ProcessCriterionService.remove(item, request.user)
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("process-edit", args=[process.pk]) + "#criterios")


class ProcessStepAddView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        version = process.draft_version
        if version is None:
            messages.error(request, "Não há rascunho em edição.")
            return redirect("process-edit", pk=process.pk)
        sector = Sector.objects.filter(pk=request.POST.get("sector"), organization=self.organization).first()
        try:
            ProcessStepService.add(
                version, request.user,
                sector=sector,
                name=request.POST.get("name", ""),
                depends_on_previous=bool(request.POST.get("depends_on_previous")),
            )
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("process-edit", args=[process.pk]) + "#fluxo")


class ProcessStepRemoveView(OrganizationRequiredMixin, View):
    def post(self, request, pk, step_pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        item = get_object_or_404(ProcessStep, pk=step_pk, version__process=process)
        try:
            ProcessStepService.remove(item, request.user)
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("process-edit", args=[process.pk]) + "#fluxo")


class ProcessStepReorderView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        version = process.draft_version
        if version is None:
            messages.error(request, "Não há rascunho em edição.")
            return redirect("process-edit", pk=process.pk)
        ordered_ids = [int(v) for v in request.POST.getlist("order")]
        try:
            ProcessStepService.reorder(version, request.user, ordered_ids)
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect(reverse("process-edit", args=[process.pk]) + "#fluxo")


class ProcessPublishView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        version = process.draft_version
        if version is None:
            messages.error(request, "Não há rascunho para publicar.")
            return redirect("process-edit", pk=process.pk)
        try:
            ProcessService.publish(version, request.user)
            messages.success(request, f"Versão {version.number} publicada.")
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect("process-edit", pk=process.pk)


class ProcessNewVersionView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        try:
            version = ProcessService.create_new_version(process, request.user)
            messages.success(request, f"Rascunho da versão {version.number} criado.")
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect("process-edit", pk=process.pk)


class ProcessToggleActiveView(OrganizationRequiredMixin, View):
    def post(self, request, pk):
        process = get_object_or_404(Process, pk=pk, organization=self.organization)
        try:
            ProcessService.set_active(process, request.user, not process.is_active)
        except ProcessError as exc:
            messages.error(request, str(exc))
        return redirect("process-list")
