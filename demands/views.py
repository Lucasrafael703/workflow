from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from .forms import DemandDecisionForm, DemandForm
from .models import Demand
from .services import DemandService, DemandServiceError


def _display_value(demand, field_name):
    field = demand._meta.get_field(field_name)
    if getattr(field, "choices", None):
        return getattr(demand, f"get_{field_name}_display")()
    value = getattr(demand, field_name)
    if isinstance(value, bool):
        return "Sim" if value else "Não"
    return value


class DemandListView(LoginRequiredMixin, ListView):
    model = Demand
    template_name = "demands/demand_list.html"
    context_object_name = "demands"
    paginate_by = 25

    def get_queryset(self):
        qs = Demand.objects.select_related("created_by").order_by("-created_at")
        user = self.request.user
        if user.has_perm("demands.can_view_all_demands"):
            return qs
        return qs.filter(created_by=user)


class DemandCreateView(LoginRequiredMixin, CreateView):
    model = Demand
    form_class = DemandForm
    template_name = "demands/demand_form.html"

    def get_success_url(self):
        return reverse("demand-detail", args=[self.object.pk])

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Demanda {self.object.protocol} registrada.")
        return response


class DemandUpdateView(LoginRequiredMixin, UpdateView):
    model = Demand
    form_class = DemandForm
    template_name = "demands/demand_form.html"

    def get_success_url(self):
        return reverse("demand-detail", args=[self.object.pk])

    def form_valid(self, form):
        messages.success(self.request, "Demanda atualizada.")
        return super().form_valid(form)


class DemandDetailView(LoginRequiredMixin, DetailView):
    model = Demand
    template_name = "demands/demand_detail.html"
    context_object_name = "demand"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["decision"] = getattr(self.object, "decision", None)
        demand = self.object
        sections = []
        for legend, field_names in DemandForm.FIELDSETS:
            rows = [
                (demand._meta.get_field(name).verbose_name, _display_value(demand, name))
                for name in field_names
            ]
            sections.append((legend, rows))
        ctx["sections"] = sections
        return ctx


class DemandDecisionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demands.can_qualify_demand"

    def get(self, request, pk):
        demand = get_object_or_404(Demand, pk=pk)
        instance = getattr(demand, "decision", None)
        form = DemandDecisionForm(instance=instance)
        return self._render(request, demand, form)

    def post(self, request, pk):
        demand = get_object_or_404(Demand, pk=pk)
        instance = getattr(demand, "decision", None)
        form = DemandDecisionForm(request.POST, instance=instance)
        if not form.is_valid():
            return self._render(request, demand, form)

        decision_fields = {
            k: v
            for k, v in form.cleaned_data.items()
            if k not in ("status", "process_template", "process_title")
        }
        try:
            DemandService.decide(
                demand=demand,
                usuario=request.user,
                status=form.cleaned_data["status"],
                decision_fields=decision_fields,
                process_template=form.cleaned_data.get("process_template"),
                process_title=form.cleaned_data.get("process_title", ""),
            )
            messages.success(request, "Decisão registrada.")
        except DemandServiceError as exc:
            form.add_error(None, str(exc))
            return self._render(request, demand, form)
        return redirect("demand-detail", pk=demand.pk)

    def _render(self, request, demand, form):
        return render(request, "demands/demand_decision_form.html", {"demand": demand, "form": form})
