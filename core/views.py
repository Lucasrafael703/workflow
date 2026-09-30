from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView, View

from acessos import catalog
from acessos.models import Action, ActionGroup
from acessos.models import Profile as AccessProfile
from acessos.models import UserAction as UserActionGrant
from acessos.models import UserProfile as UserProfileAssignment
from acessos.services import AccessService, AuthorizationService

from .forms import (
    AccessGroupForm,
    AccessProfileForm,
    ActivityStageForm,
    AssignProfileForm,
    ClientForm,
    CompanyForm,
    CostCenterForm,
    EnumColorLabelForm,
    GrantActionForm,
    NotificationPreferencesForm,
    ReturnReasonForm,
    SectorForm,
    SiteForm,
    TagForm,
    TaskStageForm,
    UserForm,
    WorkflowStatusForm,
)
from .colors import is_valid_palette_color, valid_codes_for
from .mixins import ActionRequiredMixin, OrganizationRequiredMixin
from .models import ActivityStage, Client, Company, CostCenter, Sector, Site, Tag, TaskStage, WorkflowStatus
from .services import (
    ActivityStageService,
    CadastroError,
    ClientService,
    CompanyService,
    CostCenterService,
    EnumColorService,
    ReturnReasonService,
    SectorService,
    SimpleCadastroService,
    SiteService,
    TagService,
    TaskStageService,
    WorkflowStatusService,
)

User = get_user_model()


def _is_ajax(request):
    """Requisição feita pelo modal via JS (openModal), não navegação de página."""
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


class CadastroHomeView(OrganizationRequiredMixin, TemplateView):
    template_name = "core/cadastros.html"

    def get_context_data(self, **kwargs):
        from activities.models import ReturnReason

        context = super().get_context_data(**kwargs)
        org = self.organization
        search = self.request.GET.get("q", "").strip()

        sectors = Sector.objects.filter(organization=org).annotate(
            open_tasks=Count(
                "tasks",
                filter=Q(tasks__status__in=["DISPONIVEL", "EM_FILA", "EM_EXECUCAO", "BLOQUEADA"]),
                distinct=True,
            )
        )
        companies = Company.objects.filter(organization=org)
        sites = Site.objects.filter(organization=org).select_related("client")
        cost_centers = CostCenter.objects.filter(organization=org).select_related("site")
        clients = Client.objects.filter(organization=org)
        reasons = ReturnReason.objects.filter(organization=org)
        task_stages = TaskStage.objects.filter(organization=org).order_by("order")
        tags = Tag.objects.filter(organization=org)

        if search:
            sectors = sectors.filter(name__icontains=search)
            companies = companies.filter(name__icontains=search)
            sites = sites.filter(name__icontains=search)
            cost_centers = cost_centers.filter(name__icontains=search)
            clients = clients.filter(name__icontains=search)
            reasons = reasons.filter(name__icontains=search)
            task_stages = task_stages.filter(name__icontains=search)
            tags = tags.filter(name__icontains=search)

        context.update(
            {
                "tab": self.request.GET.get("tab", "setores"),
                "search": search,
                "sectors": sectors,
                "companies": companies,
                "sites": sites,
                "cost_centers": cost_centers,
                "clients": clients,
                "return_reasons": reasons,
                "task_stages": task_stages,
                "tags": tags,
            }
        )
        return context


class PersonSearchView(OrganizationRequiredMixin, View):
    """Busca de pessoas para o seletor com autocomplete (substitui dropdowns
    de usuário que só crescem — ex.: dono da atividade, executor da tarefa)."""

    MAX_RESULTS = 20

    def get(self, request):
        term = request.GET.get("q", "").strip()
        queryset = User.objects.filter(
            profile__organization=self.organization, is_active=True
        ).order_by("first_name", "username")
        if "sector" in request.GET:
            sector_id = request.GET.get("sector", "").strip()
            try:
                sector_id = int(sector_id)
            except (TypeError, ValueError):
                return JsonResponse({"results": []})
            queryset = queryset.filter(
                sector_memberships__sector_id=sector_id,
                sector_memberships__sector__organization=self.organization,
                sector_memberships__removed_at__isnull=True,
            ).distinct()
        if term:
            queryset = queryset.filter(
                Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(username__icontains=term)
            )
        results = [
            {
                "id": user.pk,
                "name": user.get_full_name() or user.get_username(),
                "username": user.get_username(),
            }
            for user in queryset[: self.MAX_RESULTS]
        ]
        return JsonResponse({"results": results})


class ClientSearchView(OrganizationRequiredMixin, View):
    """Busca de clientes para o seletor com autocomplete (Regra 1: digitar
    "P" mostra Paulo, Pedro etc.), mesmo padrão de `PersonSearchView`."""

    MAX_RESULTS = 20

    def get(self, request):
        term = request.GET.get("q", "").strip()
        queryset = Client.objects.filter(organization=self.organization, is_active=True).order_by("name")
        if term:
            queryset = queryset.filter(
                Q(name__icontains=term) | Q(document__icontains=term)
            )
        results = [
            {"id": client.pk, "name": client.name}
            for client in queryset[: self.MAX_RESULTS]
        ]
        return JsonResponse({"results": results})


class _SimpleSearchView(OrganizationRequiredMixin, View):
    """Base para buscas "por nome" simples (Setor/Empresa/Obra/Centro de
    custo) — mesmo padrão de `ClientSearchView`, só troca o model. Subclasses
    só declaram `model`."""

    MAX_RESULTS = 20
    model = None

    def get(self, request):
        term = request.GET.get("q", "").strip()
        queryset = self.model.objects.filter(organization=self.organization, is_active=True).order_by("name")
        if term:
            queryset = queryset.filter(name__icontains=term)
        results = [{"id": obj.pk, "name": str(obj)} for obj in queryset[: self.MAX_RESULTS]]
        return JsonResponse({"results": results})


class SectorSearchView(_SimpleSearchView):
    model = Sector


class CompanySearchView(_SimpleSearchView):
    model = Company


class SiteSearchView(_SimpleSearchView):
    model = Site


class CostCenterSearchView(_SimpleSearchView):
    model = CostCenter


class TagSearchView(OrganizationRequiredMixin, View):
    """Busca de marcadores para o `TagPickerWidget` (M2M em Activity/Task),
    mesmo padrão de `ClientSearchView`."""

    MAX_RESULTS = 20

    def get(self, request):
        term = request.GET.get("q", "").strip()
        queryset = Tag.objects.filter(organization=self.organization, is_active=True).order_by("name")
        if term:
            queryset = queryset.filter(name__icontains=term)
        results = [
            {"id": tag.pk, "name": tag.name, "color": tag.color}
            for tag in queryset[: self.MAX_RESULTS]
        ]
        return JsonResponse({"results": results})


class CadastroFormView(OrganizationRequiredMixin, ActionRequiredMixin, FormView):
    """Base dos formulários de cadastro: criar e editar compartilham a tela.

    Criar e alterar cadastro é ação administrativa e exige autorização
    explícita — participar da organização não basta (Regras 05 §87-89).

    Também serve como popup ajax (mesmo padrão de `UserFormView`): quando a
    tela de atividade cria um cliente, uma obra ou um centro de custo sem
    sair do formulário, a resposta vira JSON em vez de redirect.
    """

    template_name = "core/cadastro_form.html"
    model = None
    service = None
    tab = ""
    title = ""
    required_action = catalog.SETOR_EDITAR

    def get_model(self):
        return self.model

    def get_instance(self):
        pk = self.kwargs.get("pk")
        if pk is None:
            return None
        return get_object_or_404(self.get_model(), pk=pk, organization=self.organization)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = self.get_instance()
        if instance is not None and not self.request.POST:
            kwargs["initial"] = self.initial_from(instance)
        if self.form_class in (SiteForm, CostCenterForm):
            kwargs["organization"] = self.organization
        return kwargs

    def initial_from(self, instance):
        return {"name": instance.name}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["instance"] = self.get_instance()
        context["tab"] = self.tab
        context["return_url"] = self.success_url_for_tab()
        return context

    def success_url_for_tab(self):
        return f"{reverse('cadastros')}?tab={self.tab}"

    def create(self, data):
        raise NotImplementedError

    def update(self, instance, data):
        raise NotImplementedError

    def form_valid(self, form):
        instance = self.get_instance()
        try:
            if instance is None:
                instance = self.create(form.cleaned_data)
                messages.success(self.request, "Cadastro criado.")
            else:
                instance = self.update(instance, form.cleaned_data)
                messages.success(self.request, "Cadastro atualizado.")
        except CadastroError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        if _is_ajax(self.request):
            return JsonResponse({"id": instance.pk, "name": str(instance)})
        return redirect(self.success_url_for_tab())

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class SectorFormView(CadastroFormView):
    form_class = SectorForm
    model = Sector
    tab = "setores"
    title = "Setor"
    required_action = catalog.SETOR_EDITAR

    def initial_from(self, instance):
        return {"name": instance.name, "description": instance.description}

    def create(self, data):
        return SectorService.create(
            self.organization, data["name"], self.request.user, description=data.get("description", "")
        )

    def update(self, instance, data):
        return SectorService.update(instance, name=data["name"], description=data.get("description", ""))


class CompanyFormView(CadastroFormView):
    form_class = CompanyForm
    model = Company
    tab = "empresas"
    title = "Empresa"
    required_action = catalog.EMPRESA_GERIR

    def initial_from(self, instance):
        return {"name": instance.name, "document": instance.document}

    def create(self, data):
        return CompanyService.create(self.organization, data["name"], document=data.get("document", ""))

    def update(self, instance, data):
        return CompanyService.update(instance, name=data["name"], document=data.get("document", ""))


class SiteFormView(CadastroFormView):
    form_class = SiteForm
    model = Site
    tab = "obras"
    title = "Obra"
    required_action = catalog.OBRA_GERIR

    def initial_from(self, instance):
        return {"name": instance.name, "client": instance.client_id}

    def create(self, data):
        return SiteService.create(self.organization, data["name"], client=data.get("client"))

    def update(self, instance, data):
        return SiteService.update(instance, name=data["name"], client=data.get("client"))


class CostCenterFormView(CadastroFormView):
    form_class = CostCenterForm
    model = CostCenter
    tab = "centros-de-custo"
    title = "Centro de custo"
    required_action = catalog.CENTRO_CUSTO_GERIR

    def initial_from(self, instance):
        return {"name": instance.name, "site": instance.site_id}

    def create(self, data):
        return CostCenterService.create(self.organization, data["name"], site=data.get("site"))

    def update(self, instance, data):
        return CostCenterService.update(instance, name=data["name"], site=data.get("site"))


class ClientFormView(CadastroFormView):
    """Cadastro de cliente, também acionado como popup a partir da tela de
    atividade (Regra 2: "Cadastra cliente" sem sair do formulário)."""

    form_class = ClientForm
    model = Client
    tab = "clientes"
    title = "Cliente"
    required_action = catalog.CLIENTE_GERIR

    def initial_from(self, instance):
        return {
            "name": instance.name,
            "document": instance.document,
            "phone": instance.phone,
            "email": instance.email,
            "address": instance.address,
        }

    def create(self, data):
        return ClientService.create(
            self.organization,
            data["name"],
            document=data.get("document", ""),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            address=data.get("address", ""),
        )

    def update(self, instance, data):
        return ClientService.update(
            instance,
            name=data["name"],
            document=data.get("document", ""),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            address=data.get("address", ""),
        )


class ReturnReasonFormView(CadastroFormView):
    form_class = ReturnReasonForm
    tab = "motivos"
    title = "Motivo de devolução"
    required_action = catalog.MOTIVO_DEVOLUCAO_GERIR

    def get_model(self):
        from activities.models import ReturnReason

        return ReturnReason

    def create(self, data):
        return ReturnReasonService.create(self.organization, data["name"])

    def update(self, instance, data):
        return ReturnReasonService.update(instance, name=data["name"])


class ActivityStageFormView(CadastroFormView):
    form_class = ActivityStageForm
    model = ActivityStage
    tab = "estagios-atividade"
    title = "Estagio de atividade"
    required_action = catalog.ESTAGIO_TAREFA_GERIR

    def initial_from(self, instance):
        return {"name": instance.name, "color": instance.color}

    def success_url_for_tab(self):
        return f"{reverse('config-etapas-status')}?tab=estagios-atividade"

    def create(self, data):
        return ActivityStageService.create(
            self.organization, data["name"], created_by=self.request.user, color=data.get("color", "#94A3B8")
        )

    def update(self, instance, data):
        return ActivityStageService.update(instance, name=data["name"], color=data.get("color", "#94A3B8"))


class TaskStageFormView(CadastroFormView):
    form_class = TaskStageForm
    model = TaskStage
    tab = "estagios-de-tarefa"
    title = "Estágio de tarefa"
    required_action = catalog.ESTAGIO_TAREFA_GERIR

    def initial_from(self, instance):
        return {"name": instance.name, "color": instance.color}

    def success_url_for_tab(self):
        referer = self.request.META.get("HTTP_REFERER", "")
        if "etapas-e-status" in referer:
            return f"{reverse('config-etapas-status')}?tab=estagios-tarefa"
        return f"{reverse('cadastros')}?tab={self.tab}"

    def create(self, data):
        return TaskStageService.create(
            self.organization, data["name"], created_by=self.request.user, color=data.get("color", "#94A3B8")
        )

    def update(self, instance, data):
        return TaskStageService.update(instance, name=data["name"], color=data.get("color", "#94A3B8"))


class WorkflowStatusFormView(OrganizationRequiredMixin, ActionRequiredMixin, FormView):
    template_name = "core/cadastro_form.html"
    form_class = WorkflowStatusForm
    required_action = catalog.COR_STATUS_GERIR

    def dispatch(self, request, *args, **kwargs):
        if kwargs.get("domain") not in ("activity", "task"):
            raise Http404("Tipo de status desconhecido.")
        return super().dispatch(request, *args, **kwargs)

    def get_instance(self):
        pk = self.kwargs.get("pk")
        if pk is None:
            return None
        return get_object_or_404(
            WorkflowStatus,
            pk=pk,
            organization=self.organization,
            domain=self.kwargs["domain"],
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["domain"] = self.kwargs["domain"]
        instance = self.get_instance()
        if instance is not None and not self.request.POST:
            kwargs["initial"] = {
                "name": instance.name,
                "description": instance.description,
                "behavior": instance.behavior,
                "color": instance.color,
            }
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain = self.kwargs["domain"]
        context["title"] = "Status de atividade" if domain == "activity" else "Status de tarefa"
        context["instance"] = self.get_instance()
        context["tab"] = "status-atividade" if domain == "activity" else "status-tarefa"
        context["return_url"] = f"{reverse('config-etapas-status')}?tab={context['tab']}"
        return context

    def form_valid(self, form):
        domain = self.kwargs["domain"]
        instance = self.get_instance()
        try:
            if instance is None:
                instance = WorkflowStatusService.create(
                    self.organization,
                    form.cleaned_data["name"],
                    domain=domain,
                    behavior=form.cleaned_data["behavior"],
                    created_by=self.request.user,
                    description=form.cleaned_data.get("description", ""),
                    color=form.cleaned_data["color"],
                )
                messages.success(self.request, "Status criado.")
            else:
                instance = WorkflowStatusService.update(
                    instance,
                    name=form.cleaned_data["name"],
                    description=form.cleaned_data.get("description", ""),
                    behavior=form.cleaned_data["behavior"],
                    color=form.cleaned_data["color"],
                )
                messages.success(self.request, "Status atualizado.")
        except CadastroError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        if _is_ajax(self.request):
            return JsonResponse({"id": instance.pk, "name": instance.name})
        tab = "status-atividade" if domain == "activity" else "status-tarefa"
        return redirect(f"{reverse('config-etapas-status')}?tab={tab}")

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class EnumColorLabelFormView(OrganizationRequiredMixin, ActionRequiredMixin, FormView):
    """Edita nome/descricao exibidos e o estado oculto de um status nativo
    (Activity.Status/Task.Status) — nunca o `code`, que continua sendo o
    valor real gravado e comparado pela regra de negocio."""

    template_name = "core/cadastro_form.html"
    form_class = EnumColorLabelForm
    required_action = catalog.COR_STATUS_GERIR

    def dispatch(self, request, *args, **kwargs):
        domain = kwargs.get("domain")
        if domain not in ("activity_status", "task_status"):
            raise Http404("Dominio de status desconhecido.")
        if kwargs.get("code") not in valid_codes_for(domain):
            raise Http404("Codigo de status desconhecido.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not self.request.POST:
            label, description, is_hidden = EnumColorService.get_overrides(
                self.organization, self.kwargs["domain"], self.kwargs["code"]
            )
            kwargs["initial"] = {"label": label, "description": description, "is_hidden": is_hidden}
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain = self.kwargs["domain"]
        tab = "status-atividade" if domain == "activity_status" else "status-tarefa"
        context["title"] = f"Status: {self.kwargs['code']}"
        context["instance"] = True
        context["tab"] = tab
        context["return_url"] = f"{reverse('config-etapas-status')}?tab={tab}"
        return context

    def form_valid(self, form):
        domain = self.kwargs["domain"]
        code = self.kwargs["code"]
        EnumColorService.set_overrides(
            self.organization,
            domain,
            code,
            label=form.cleaned_data["label"],
            description=form.cleaned_data["description"],
            is_hidden=form.cleaned_data["is_hidden"],
            updated_by=self.request.user,
        )
        messages.success(self.request, "Status atualizado.")
        if _is_ajax(self.request):
            return JsonResponse({"ok": True})
        tab = "status-atividade" if domain == "activity_status" else "status-tarefa"
        return redirect(f"{reverse('config-etapas-status')}?tab={tab}")

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class TaskStageReorderView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    """Recebe a ordem final das colunas do Kanban (drag-and-drop na tela de
    cadastro) e renumera — nunca expõe `order` como campo editável à mão."""

    required_action = catalog.ESTAGIO_TAREFA_GERIR

    def post(self, request):
        ordered_ids = [int(value) for value in request.POST.getlist("stage_id") if value.isdigit()]
        TaskStageService.reorder(self.organization, ordered_ids)
        if _is_ajax(request):
            return JsonResponse({"ok": True})
        messages.success(request, "Ordem dos estágios atualizada.")
        return redirect(f"{reverse('cadastros')}?tab=estagios-de-tarefa")


class TagFormView(CadastroFormView):
    form_class = TagForm
    model = Tag
    tab = "tags"
    title = "Marcador"
    required_action = catalog.TAG_GERIR

    def initial_from(self, instance):
        return {"name": instance.name, "color": instance.color}

    def create(self, data):
        return TagService.create(self.organization, data["name"], color=data["color"])

    def update(self, instance, data):
        return TagService.update(instance, name=data["name"], color=data["color"])


class SwatchColorSaveView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    """Salva a cor (campo direto do model) de UM Tag ou TaskStage por vez —
    clique direto no chip da listagem, sem reabrir o form de editar
    completo. Mesmo padrão de TaskStageReorderView: POST simples, JSON
    quando XHR."""

    swatch_models = {
        "tags": (Tag, TagService, catalog.TAG_GERIR),
        "estagios-de-atividade": (ActivityStage, ActivityStageService, catalog.ESTAGIO_TAREFA_GERIR),
        "estagios-de-tarefa": (TaskStage, TaskStageService, catalog.ESTAGIO_TAREFA_GERIR),
    }

    def dispatch(self, request, *args, **kwargs):
        _model, _service, action = self.swatch_models.get(kwargs.get("tab"), (None, None, None))
        if action is None:
            raise Http404("Cadastro desconhecido.")
        self.required_action = action
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, tab, pk):
        model, service, _action = self.swatch_models[tab]
        instance = get_object_or_404(model, pk=pk, organization=self.organization)
        color = request.POST.get("color", "")
        if not is_valid_palette_color(color):
            return JsonResponse({"error": "Escolha uma cor da paleta oficial."}, status=400)
        service.update(instance, color=color)
        if _is_ajax(request):
            return JsonResponse({"ok": True, "id": instance.pk, "color": color})
        messages.success(request, "Cor atualizada.")
        return redirect(f"{reverse('cadastros')}?tab={tab}")


class CadastroToggleActiveView(OrganizationRequiredMixin, View):
    """Inativar preserva o histórico; excluir não é oferecido (Regras 05 §89-90)."""

    # Cada cadastro é governado pela sua própria ação; inativar um setor
    # afeta filas e tarefas de toda a organização.
    cadastros = {
        "setores": (Sector, catalog.SETOR_INATIVAR),
        "empresas": (Company, catalog.EMPRESA_GERIR),
        "obras": (Site, catalog.OBRA_GERIR),
        "centros-de-custo": (CostCenter, catalog.CENTRO_CUSTO_GERIR),
        "clientes": (Client, catalog.CLIENTE_GERIR),
        "estagios-de-atividade": (ActivityStage, catalog.ESTAGIO_TAREFA_GERIR),
        "estagios-de-tarefa": (TaskStage, catalog.ESTAGIO_TAREFA_GERIR),
        "status-configuravel": (WorkflowStatus, catalog.COR_STATUS_GERIR),
        "tags": (Tag, catalog.TAG_GERIR),
    }

    def resolve(self, tab):
        if tab == "motivos":
            from activities.models import ReturnReason

            return ReturnReason, catalog.MOTIVO_DEVOLUCAO_GERIR
        return self.cadastros.get(tab, (None, None))

    def post(self, request, tab, pk):
        model, action = self.resolve(tab)
        if model is None:
            messages.error(request, "Cadastro desconhecido.")
            return redirect("cadastros")
        instance = get_object_or_404(model, pk=pk, organization=self.organization)
        if not AuthorizationService.can(request.user, action, instance):
            raise PermissionDenied("Você não possui acesso para alterar este cadastro.")
        SimpleCadastroService.set_active(instance, not instance.is_active)
        messages.success(
            request, "Cadastro reativado." if instance.is_active else "Cadastro inativado."
        )
        return redirect(f"{reverse('cadastros')}?tab={tab}")


class FlowConfigDeleteView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    models_by_kind = {
        "activity-stage": (ActivityStage, catalog.ESTAGIO_TAREFA_GERIR),
        "task-stage": (TaskStage, catalog.ESTAGIO_TAREFA_GERIR),
        "workflow-status": (WorkflowStatus, catalog.COR_STATUS_GERIR),
    }

    def dispatch(self, request, *args, **kwargs):
        _model, action = self.models_by_kind.get(kwargs.get("kind"), (None, None))
        if action is None:
            raise Http404("Item desconhecido.")
        self.required_action = action
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, kind, pk):
        model, _action = self.models_by_kind[kind]
        instance = get_object_or_404(model, pk=pk, organization=self.organization)
        if isinstance(instance, WorkflowStatus):
            tab = "status-atividade" if instance.domain == WorkflowStatus.Domain.ACTIVITY else "status-tarefa"
        elif isinstance(instance, ActivityStage):
            tab = "estagios-atividade"
        else:
            tab = "estagios-tarefa"
        instance.delete()
        messages.success(request, "Item excluido.")
        return redirect(f"{reverse('config-etapas-status')}?tab={tab}")


class EtapasEStatusView(OrganizationRequiredMixin, ActionRequiredMixin, TemplateView):
    """Configurações → Etapas e status: uma tela com 3 sub-seções (abas
    internas ?tab=), reaproveitando o mesmo idioma de templates/core/cadastros.html."""

    template_name = "core/etapas_e_status.html"

    def dispatch(self, request, *args, **kwargs):
        tab = request.GET.get("tab", "estagios-atividade")
        self.required_action = catalog.ESTAGIO_TAREFA_GERIR if tab.startswith("estagios") or tab == "etapas" else catalog.COR_STATUS_GERIR
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from activities.models import Activity, Task

        context = super().get_context_data(**kwargs)
        tab = self.request.GET.get("tab", "estagios-atividade")
        tab = {"atividade": "status-atividade", "tarefa": "status-tarefa", "etapas": "estagios-tarefa"}.get(tab, tab)
        context["tab"] = tab
        activity_status_meta = {
            Activity.Status.ABERTA: {
                "description": "Item aberto e pronto para entrar no fluxo.",
                "behavior": "Mantem a atividade aberta",
            },
            Activity.Status.EM_ANDAMENTO: {
                "description": "Trabalho iniciado, com tarefas em andamento.",
                "behavior": "Conta como trabalho ativo",
            },
            Activity.Status.BLOQUEADA: {
                "description": "Existe impedimento travando o andamento.",
                "behavior": "Exige desbloqueio",
            },
            Activity.Status.PENDENTE: {
                "description": "Aguardando retorno, ajuste ou decisao.",
                "behavior": "Mantem aberta com pendencia",
            },
            Activity.Status.CONCLUIDA: {
                "description": "Atividade encerrada com entrega concluida.",
                "behavior": "Encerra a atividade",
            },
            Activity.Status.CANCELADA: {
                "description": "Atividade encerrada sem continuidade.",
                "behavior": "Encerra sem entrega",
            },
        }
        task_status_meta = {
            Task.Status.NAO_INICIADA: {
                "description": "Ainda nao liberada para execucao.",
                "behavior": "Fora da fila ativa",
            },
            Task.Status.DISPONIVEL: {
                "description": "Pode ser puxada por quem executa.",
                "behavior": "Disponivel para iniciar",
            },
            Task.Status.EM_FILA: {
                "description": "Esta aguardando sua vez no setor.",
                "behavior": "Conta na fila",
            },
            Task.Status.EM_EXECUCAO: {
                "description": "Alguem esta trabalhando nela agora.",
                "behavior": "Conta como execucao",
            },
            Task.Status.BLOQUEADA: {
                "description": "Existe bloqueio impedindo progresso.",
                "behavior": "Exige resolucao de bloqueio",
            },
            Task.Status.DEVOLVIDA: {
                "description": "Voltou por ajuste ou retrabalho.",
                "behavior": "Registra devolucao",
            },
            Task.Status.CONCLUIDA: {
                "description": "Tarefa finalizada.",
                "behavior": "Encerra a tarefa",
            },
            Task.Status.CANCELADA: {
                "description": "Tarefa cancelada sem continuidade.",
                "behavior": "Encerra sem execucao",
            },
        }

        if tab == "status-atividade":
            colors = EnumColorService.list_for_domain(self.organization, "activity_status")
            overrides = EnumColorService.list_overrides_for_domain(self.organization, "activity_status")
            context["rows"] = [
                {
                    "code": code,
                    "label": overrides.get(code, {}).get("label") or label,
                    "color": colors[code],
                    "is_system": True,
                    "is_hidden": overrides.get(code, {}).get("is_hidden", False),
                    "enum_domain": "activity_status",
                    **activity_status_meta.get(code, {}),
                    **({"description": overrides[code]["description"]} if overrides.get(code, {}).get("description") else {}),
                }
                for code, label in Activity.Status.choices
            ]
            context["custom_rows"] = WorkflowStatus.objects.filter(
                organization=self.organization, domain=WorkflowStatus.Domain.ACTIVITY
            ).order_by("name")
            context["status_domain"] = "activity"
            context["section_title"] = "Status de atividades"
            context["section_description"] = "Configure a aparencia dos estados reais das atividades."
        elif tab == "status-tarefa":
            colors = EnumColorService.list_for_domain(self.organization, "task_status")
            overrides = EnumColorService.list_overrides_for_domain(self.organization, "task_status")
            context["rows"] = [
                {
                    "code": code,
                    "label": overrides.get(code, {}).get("label") or label,
                    "color": colors[code],
                    "is_system": True,
                    "is_hidden": overrides.get(code, {}).get("is_hidden", False),
                    "enum_domain": "task_status",
                    **task_status_meta.get(code, {}),
                    **({"description": overrides[code]["description"]} if overrides.get(code, {}).get("description") else {}),
                }
                for code, label in Task.Status.choices
            ]
            context["custom_rows"] = WorkflowStatus.objects.filter(
                organization=self.organization, domain=WorkflowStatus.Domain.TASK
            ).order_by("name")
            context["status_domain"] = "task"
            context["section_title"] = "Status de tarefas"
            context["section_description"] = "A cor ajuda a leitura; o comportamento continua protegido pelas regras da LPS."
        elif tab == "estagios-atividade":
            context["stages"] = ActivityStage.objects.filter(organization=self.organization).order_by("order")
            context["stage_kind"] = "activity-stage"
            context["stage_color_tab"] = "estagios-de-atividade"
            context["stage_create_url"] = reverse("activitystage-create")
            context["section_title"] = "Estagios de atividades"
            context["section_description"] = "Organize o fluxo visual das atividades em Lista, Kanban e Calendario."
        elif tab == "estagios-tarefa":
            context["stages"] = TaskStage.objects.filter(organization=self.organization).order_by("order")
            context["stage_kind"] = "task-stage"
            context["stage_color_tab"] = "estagios-de-tarefa"
            context["stage_create_url"] = reverse("taskstage-create")
            context["section_title"] = "Estagios de tarefas"
            context["section_description"] = "Organize as colunas visuais usadas em Lista, Kanban e Calendario."

        context["domain"] = {"status-atividade": "activity_status", "status-tarefa": "task_status"}.get(tab)
        return context


class PrioridadesView(OrganizationRequiredMixin, ActionRequiredMixin, TemplateView):
    """Configurações → Prioridades: lista única (Activity.urgency tem só 3
    valores, sem necessidade de sub-seções)."""

    template_name = "core/prioridades.html"
    required_action = catalog.COR_PRIORIDADE_GERIR

    def get_context_data(self, **kwargs):
        from activities.models import Activity

        context = super().get_context_data(**kwargs)
        colors = EnumColorService.list_for_domain(self.organization, "activity_urgency")
        context["rows"] = [
            {"code": code, "label": label, "color": colors[code]} for code, label in Activity.Urgency.choices
        ]
        context["domain"] = "activity_urgency"
        return context


class EnumColorSaveView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    """Salva a cor de UM (domain, code) por vez — o clique no swatch da
    listagem, sem modal, sem form tradicional."""

    domains = {
        "activity_status": catalog.COR_STATUS_GERIR,
        "task_status": catalog.COR_STATUS_GERIR,
        "activity_urgency": catalog.COR_PRIORIDADE_GERIR,
    }

    def dispatch(self, request, *args, **kwargs):
        action = self.domains.get(kwargs.get("domain"))
        if action is None:
            raise Http404("Domínio de cor desconhecido.")
        self.required_action = action
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, domain):
        code = request.POST.get("code", "")
        color = request.POST.get("color", "")
        try:
            EnumColorService.set_color(self.organization, domain, code, color, updated_by=request.user)
        except CadastroError as exc:
            if _is_ajax(request):
                return JsonResponse({"error": str(exc)}, status=400)
            messages.error(request, str(exc))
            return redirect(request.META.get("HTTP_REFERER", "cadastros"))
        if _is_ajax(request):
            return JsonResponse({"ok": True, "code": code, "color": color})
        messages.success(request, "Cor atualizada.")
        return redirect(request.META.get("HTTP_REFERER", "cadastros"))


class EnumColorResetView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    """"Restaurar cores padrão LPS" — apaga as customizações de um domínio.
    A confirmação acontece no client (confirm() antes do submit)."""

    domains = EnumColorSaveView.domains

    def dispatch(self, request, *args, **kwargs):
        action = self.domains.get(kwargs.get("domain"))
        if action is None:
            raise Http404("Domínio de cor desconhecido.")
        self.required_action = action
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, domain):
        EnumColorService.reset_to_defaults(self.organization, domain=domain)
        messages.success(request, "Cores restauradas ao padrão LPS.")
        return redirect(request.META.get("HTTP_REFERER", "cadastros"))


class SettingsView(OrganizationRequiredMixin, FormView):
    """Configurações: como a LPS se comporta, distinto dos cadastros (doc 09 §186)."""

    template_name = "core/settings.html"
    form_class = NotificationPreferencesForm

    def get_initial(self):
        return self.request.session.get("notification_preferences", {})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sectors"] = Sector.objects.filter(organization=self.organization, is_active=True)
        return context

    def form_valid(self, form):
        self.request.session["notification_preferences"] = form.cleaned_data
        messages.success(self.request, "Preferências salvas.")
        return redirect("settings")


class PermissionMatrixView(OrganizationRequiredMixin, ActionRequiredMixin, TemplateView):
    """Responde "O que este perfil pode fazer?" (doc 05 §32, §38)."""

    template_name = "core/permissions.html"
    required_action = catalog.SEGURANCA_GERIR_PERFIS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profiles = AccessProfile.objects.filter(organization=self.organization).annotate(
            user_count=Count("assignments", filter=Q(assignments__is_active=True), distinct=True)
        )
        selected = self.request.GET.get("profile")
        profile = profiles.filter(pk=selected).first() if selected else profiles.first()

        granted = set()
        if profile:
            granted = set(profile.profile_actions.values_list("action_id", flat=True))

        search = self.request.GET.get("q", "").strip().lower()
        show = self.request.GET.get("show", "todas")

        blocks = []
        for group in ActionGroup.objects.filter(is_active=True).prefetch_related("actions"):
            rows = []
            for action in group.actions.filter(is_active=True):
                is_granted = action.id in granted
                if show == "autorizadas" and not is_granted:
                    continue
                if show == "nao-autorizadas" and is_granted:
                    continue
                if search and search not in action.name.lower() and search not in action.key.lower():
                    continue
                rows.append({"action": action, "granted": is_granted})
            if rows:
                blocks.append({"group": group, "rows": rows})

        context.update(
            {
                "profiles": profiles,
                "profile": profile,
                "blocks": blocks,
                "search": self.request.GET.get("q", ""),
                "show": show,
                "assignments": (
                    profile.assignments.filter(is_active=True).select_related("user", "scope")
                    if profile
                    else []
                ),
            }
        )
        return context


class PermissionUpdateView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    required_action = catalog.SEGURANCA_GERIR_AUTORIZACOES

    def post(self, request, pk):
        profile = get_object_or_404(AccessProfile, pk=pk, organization=self.organization)
        selected = {int(value) for value in request.POST.getlist("actions") if value.isdigit()}
        # Só as ações exibidas podem ser desmarcadas: com busca ou filtro ativo,
        # o que ficou fora da tela precisa ser preservado.
        visible = {int(value) for value in request.POST.getlist("visible") if value.isdigit()}

        AccessService.set_profile_actions(
            profile, granted_ids=selected & visible, visible_ids=visible, changed_by=request.user
        )
        messages.success(request, f"Permissões do perfil {profile.name} atualizadas.")
        return redirect(f"{reverse('permissions')}?profile={profile.pk}")


class ProfileFormView(OrganizationRequiredMixin, ActionRequiredMixin, FormView):
    template_name = "core/profile_form.html"
    form_class = AccessProfileForm
    required_action = catalog.SEGURANCA_GERIR_PERFIS

    def get_instance(self):
        pk = self.kwargs.get("pk")
        if pk is None:
            return None
        return get_object_or_404(AccessProfile, pk=pk, organization=self.organization)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = self.get_instance()
        if instance is not None and not self.request.POST:
            kwargs["initial"] = {"name": instance.name, "description": instance.description}
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["instance"] = self.get_instance()
        return context

    def form_valid(self, form):
        instance = self.get_instance()
        try:
            if instance is None:
                instance = AccessService.create_profile(
                    self.organization,
                    form.cleaned_data["name"],
                    created_by=self.request.user,
                    description=form.cleaned_data.get("description", ""),
                )
            else:
                instance = AccessService.update_profile(
                    instance,
                    name=form.cleaned_data["name"],
                    description=form.cleaned_data.get("description", ""),
                    changed_by=self.request.user,
                )
        except CadastroError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, "Perfil salvo.")
        return redirect(f"{reverse('permissions')}?profile={instance.pk}")


def _screens_payload():
    """Catálogo de telas em JSON, para a prévia do menu e os botões de nível."""
    from acessos import screens

    return [
        {
            "name": section.name,
            "screens": [
                {
                    "key": screen.key,
                    "name": screen.name,
                    "hasView": screen.has_view_level,
                    "editLabel": screen.edit_label,
                }
                for screen in section.screens
            ],
        }
        for section in screens.SECTIONS
    ]


class UserListView(OrganizationRequiredMixin, ActionRequiredMixin, TemplateView):
    template_name = "core/user_list.html"
    required_action = catalog.USUARIO_VISUALIZAR

    def get_context_data(self, **kwargs):
        from accounts.models import UserSector
        from acessos import screens
        from acessos.services import ScreenAccessService

        context = super().get_context_data(**kwargs)
        users = (
            User.objects.filter(profile__organization=self.organization)
            .select_related("profile")
            .prefetch_related("access_profiles__profile", "access_profiles__scope")
            .order_by("first_name", "username")
        )
        search = self.request.GET.get("q", "").strip()
        if search:
            users = users.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )

        sector_filter = self.request.GET.get("equipe", "")
        if sector_filter.isdigit():
            users = users.filter(
                sector_memberships__sector_id=int(sector_filter), sector_memberships__removed_at__isnull=True
            ).distinct()

        group_filter = self.request.GET.get("grupo", "")
        if group_filter == "sem":
            users = users.exclude(access_profiles__is_active=True)
        elif group_filter.isdigit():
            users = users.filter(
                access_profiles__profile_id=int(group_filter), access_profiles__is_active=True
            ).distinct()

        status = self.request.GET.get("situacao", "ativos")
        if status == "ativos":
            users = users.filter(is_active=True)
        elif status == "inativos":
            users = users.filter(is_active=False)

        users = list(users)
        memberships = {}
        for row in (
            UserSector.objects.filter(user__in=users, removed_at__isnull=True)
            .select_related("sector")
            .order_by("sector__name")
        ):
            memberships.setdefault(row.user_id, []).append(row)

        direct = {}
        for grant in UserActionGrant.objects.filter(
            user__in=users, is_active=True, action__is_active=True
        ).select_related("action"):
            direct.setdefault(grant.user_id, set()).add(grant.action.key)

        profile_keys_cache = {}
        full_access = 0
        rows = []
        total_screens = len(screens.SCREENS)
        for person in users:
            assignments = [a for a in person.access_profiles.all() if a.is_active and a.profile.is_active]
            group_keys = set()
            for assignment in assignments:
                if assignment.profile_id not in profile_keys_cache:
                    profile_keys_cache[assignment.profile_id] = ScreenAccessService.profile_keys(assignment.profile)
                group_keys |= profile_keys_cache[assignment.profile_id]
            own = direct.get(person.pk, set())
            levels = screens.levels_from_actions(group_keys | own)
            group_levels = screens.levels_from_actions(group_keys)
            extras = sum(1 for key, value in levels.items() if value > group_levels[key])
            count = screens.count_screens(levels)
            is_full = person.is_superuser or all(value == screens.EDITAR for value in levels.values())
            if is_full and person.is_active:
                full_access += 1
            main_sector_id = getattr(person.profile, "main_sector_id", None)
            words = (person.get_full_name() or person.get_username()).split()
            initials = (words[0][:1] + (words[-1][:1] if len(words) > 1 else "")).upper()
            rows.append(
                {
                    "user": person,
                    "initials": initials,
                    "teams": memberships.get(person.pk, []),
                    "main_sector_id": main_sector_id,
                    "groups": assignments,
                    "screen_count": count,
                    "all_screens": count == total_screens,
                    "extras": extras,
                    "is_superuser": person.is_superuser,
                    "never_logged": person.last_login is None and not person.has_usable_password(),
                }
            )

        context.update(
            {
                "rows": rows,
                "search": search,
                "sectors": Sector.objects.filter(organization=self.organization, is_active=True).order_by("name"),
                "groups": AccessProfile.objects.filter(organization=self.organization, is_active=True).order_by("name"),
                "sector_filter": sector_filter,
                "group_filter": group_filter,
                "status": status,
                "full_access_count": full_access,
                "can_edit": AuthorizationService.can(self.request.user, catalog.USUARIO_EDITAR),
                "can_manage_groups": AuthorizationService.can(self.request.user, catalog.SEGURANCA_GERIR_PERFIS),
            }
        )
        return context


class UserFormView(OrganizationRequiredMixin, ActionRequiredMixin, FormView):
    """Cadastro/edição de usuário: dados, equipes, grupo e telas numa tela só."""

    template_name = "core/user_form.html"
    form_class = UserForm
    required_action = catalog.USUARIO_EDITAR

    def get_instance(self):
        if not hasattr(self, "_instance"):
            pk = self.kwargs.get("pk")
            self._instance = (
                None if pk is None else get_object_or_404(User, pk=pk, profile__organization=self.organization)
            )
        return self._instance

    @property
    def manage_access(self):
        # Mexer em acesso é segurança: quem só cadastra pessoas não escolhe o
        # que elas podem fazer.
        return AuthorizationService.can(self.request.user, catalog.SEGURANCA_GERIR_AUTORIZACOES)

    def get_access_summary(self):
        from acessos.services import ScreenAccessService

        if not hasattr(self, "_summary"):
            instance = self.get_instance()
            self._summary = ScreenAccessService.user_summary(instance) if instance is not None else None
        return self._summary

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["instance"] = self.get_instance()
        kwargs["access_summary"] = self.get_access_summary()
        return kwargs

    def get_context_data(self, **kwargs):
        from acessos.services import ScreenAccessService

        context = super().get_context_data(**kwargs)
        instance = self.get_instance()
        context["instance"] = instance
        context["manage_access"] = self.manage_access
        context["summary"] = self.get_access_summary()
        groups = AccessProfile.objects.filter(organization=self.organization, is_active=True).order_by("name")
        group_levels = {str(group.pk): ScreenAccessService.profile_levels(group) for group in groups}
        context["group_cards"] = [
            {
                "group": group,
                "count": sum(1 for v in group_levels[str(group.pk)].values() if v),
                "all": all(v == 2 for v in group_levels[str(group.pk)].values()),
            }
            for group in groups
        ]
        context["access_data"] = {"sections": _screens_payload(), "groups": group_levels}
        form = context["form"]
        context["screen_sections"] = form.screen_fields()

        def _values(name):
            value = form[name].value()
            if value in (None, ""):
                return set()
            if not isinstance(value, (list, tuple)):
                value = [value]
            return {str(v) for v in value if v not in (None, "")}

        members, managers, main = _values("sectors"), _values("managed_sectors"), _values("main_sector")
        context["team_rows"] = [
            {
                "sector": sector,
                "member": str(sector.pk) in members,
                "manager": str(sector.pk) in managers,
                "main": str(sector.pk) in main,
            }
            for sector in form.fields["sectors"].queryset.order_by("name")
        ]
        group_value = form["access_group"].value()
        context["selected_group"] = "" if group_value in (None, "") else str(group_value)
        context["can_manage_groups"] = AuthorizationService.can(self.request.user, catalog.SEGURANCA_GERIR_PERFIS)
        if instance is not None:
            from activities.models import Activity, Task

            context["open_activities"] = (
                Activity.objects.filter(organization=self.organization, owner=instance)
                .exclude(status__in=["CONCLUIDA", "CANCELADA"])
                .count()
            )
            context["open_tasks"] = (
                Task.objects.filter(
                    activity__organization=self.organization,
                    executors__user=instance,
                    executors__removed_at__isnull=True,
                    status__in=["DISPONIVEL", "EM_FILA", "EM_EXECUCAO", "BLOQUEADA"],
                )
                .distinct()
                .count()
            )
        return context

    def _send_invite(self, user):
        """Link para a pessoa criar a própria senha (mesmo fluxo do "esqueci a senha")."""
        from django.contrib.auth.tokens import default_token_generator
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        path = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": urlsafe_base64_encode(force_bytes(user.pk)), "token": default_token_generator.make_token(user)},
        )
        body = render_to_string(
            "registration/convite_email.txt",
            {
                "user": user,
                "link": self.request.build_absolute_uri(path),
                "organization": self.organization,
                "invited_by": self.request.user,
            },
        )
        send_mail(f"Seu acesso à LPS — {self.organization.name}", body, None, [user.email])

    def form_valid(self, form):
        from audit.models import AuditLog
        from audit.services import AuditService
        from acessos.services import ScreenAccessService

        instance = self.get_instance()
        data = form.cleaned_data

        if instance is None:
            instance = User.objects.create_user(
                username=data["username"],
                email=data["email"],
                first_name=data["first_name"],
                password=None if data.get("send_invite") else data["password1"],
            )
            AuditService.log(
                user=self.request.user,
                action=AuditLog.Action.USER_CREATED,
                target_user=instance,
                reason=f"Usuário {instance.username} cadastrado.",
            )
            if data.get("send_invite"):
                self._send_invite(instance)
                messages.success(
                    self.request, f"Usuário {instance.username} criado. O link para criar a senha foi enviado para {instance.email}."
                )
            else:
                messages.success(self.request, f"Usuário {instance.username} criado.")
        else:
            instance.username = data["username"]
            instance.email = data["email"]
            instance.first_name = data["first_name"]
            instance.is_active = data["is_active"]
            if data.get("password1"):
                instance.set_password(data["password1"])
                AuditService.log(
                    user=self.request.user,
                    action=AuditLog.Action.PASSWORD_RESET,
                    target_user=instance,
                    reason=f"Senha de {instance.username} redefinida.",
                )
            instance.save()
            messages.success(self.request, "Usuário atualizado.")

        profile = instance.profile
        fields = []
        organization = data["organization"]
        if profile.organization_id != organization.id:
            profile.organization = organization
            fields.append("organization")
        sectors = list(data["sectors"])
        main = data.get("main_sector") or (sectors[0] if len(sectors) == 1 else None)
        if (main.pk if main else None) != profile.main_sector_id:
            profile.main_sector = main
            fields.append("main_sector")
        if fields:
            profile.save(update_fields=fields)

        AccessService.sync_user_sectors(
            instance,
            sectors=data["sectors"],
            managed_sectors=data.get("managed_sectors") or [],
            changed_by=self.request.user,
        )

        # O formulário pelo modal (AJAX) e quem não gerencia acessos não
        # mandam a parte de telas: nada muda no acesso da pessoa.
        if self.manage_access and "access_scope" in self.request.POST:
            try:
                ScreenAccessService.save_user_access(
                    instance,
                    profile=data.get("access_group"),
                    scope=form.resolve_scope(),
                    levels=form.screen_levels(),
                    changed_by=self.request.user,
                )
            except CadastroError as exc:
                messages.error(self.request, str(exc))

        if _is_ajax(self.request):
            return JsonResponse(
                {"id": instance.pk, "name": instance.get_full_name() or instance.get_username()}
            )
        if self.request.POST.get("next") == "novo":
            return redirect("user-create")
        return redirect("user-list")

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class GroupView(OrganizationRequiredMixin, ActionRequiredMixin, FormView):
    """Grupos de acesso: cada grupo diz quais telas aparecem para quem é dele."""

    template_name = "core/groups.html"
    form_class = AccessGroupForm
    required_action = catalog.SEGURANCA_GERIR_PERFIS

    def post(self, request, *args, **kwargs):
        if not AuthorizationService.can(request.user, catalog.SEGURANCA_GERIR_AUTORIZACOES):
            raise PermissionDenied("Você não possui acesso a este conteúdo.")
        return super().post(request, *args, **kwargs)

    def get_groups(self):
        return AccessProfile.objects.filter(organization=self.organization).annotate(
            member_count=Count("assignments", filter=Q(assignments__is_active=True), distinct=True)
        ).order_by("-is_active", "name")

    def get_instance(self):
        if not hasattr(self, "_instance"):
            pk = self.kwargs.get("pk")
            if pk is not None:
                self._instance = get_object_or_404(AccessProfile, pk=pk, organization=self.organization)
            elif self.kwargs.get("new"):
                self._instance = None
            else:
                self._instance = self.get_groups().filter(is_active=True).first()
        return self._instance

    def get(self, request, *args, **kwargs):
        if self.kwargs.get("pk") is None and not self.kwargs.get("new") and self.get_instance() is None:
            if request.GET.get("comparar"):
                return super().get(request, *args, **kwargs)
            return redirect("group-create")
        return super().get(request, *args, **kwargs)

    def _template_key(self):
        from acessos import screens

        key = self.request.GET.get("modelo", "")
        if key in screens.TEMPLATES:
            return key
        if key.isdigit():
            return key
        return ""

    def get_levels(self):
        from acessos import screens
        from acessos.services import ScreenAccessService

        instance = self.get_instance()
        if instance is not None:
            return ScreenAccessService.profile_levels(instance)
        key = self._template_key()
        if key in screens.TEMPLATES:
            return dict(screens.TEMPLATES[key]["levels"])
        if key.isdigit():
            source = AccessProfile.objects.filter(pk=int(key), organization=self.organization).first()
            if source is not None:
                return ScreenAccessService.profile_levels(source)
        return {}

    def get_form_kwargs(self):
        from acessos import screens

        kwargs = super().get_form_kwargs()
        kwargs["levels"] = self.get_levels()
        instance = self.get_instance()
        if instance is not None and not self.request.POST:
            kwargs["initial"] = {"name": instance.name, "description": instance.description}
        elif instance is None and not self.request.POST:
            key = self._template_key()
            if key in screens.TEMPLATES:
                kwargs["initial"] = {"description": screens.TEMPLATES[key]["description"]}
        return kwargs

    def get_context_data(self, **kwargs):
        from acessos import screens
        from acessos.services import ScreenAccessService

        context = super().get_context_data(**kwargs)
        instance = self.get_instance()
        groups = list(self.get_groups())
        levels_by_group = {}
        for group in groups:
            keys = ScreenAccessService.profile_keys(group)
            levels_by_group[group.pk] = screens.levels_from_actions(keys)
            group.screen_count = screens.count_screens(levels_by_group[group.pk])
            group.all_screens = group.screen_count == len(screens.SCREENS)

        partial = set()
        if instance is not None:
            keys = ScreenAccessService.profile_keys(instance)
            partial = {screen.key for screen in screens.SCREENS if screen.is_partial(keys)}

        compare = bool(self.request.GET.get("comparar"))
        compare_groups = [g for g in groups if g.is_active]
        compare_rows = []
        if compare:
            for section in screens.SECTIONS:
                compare_rows.append({"section": section.name})
                for screen in section.screens:
                    cells = []
                    for group in compare_groups:
                        level = levels_by_group[group.pk][screen.key]
                        label = screens.LEVEL_LABELS[level]
                        if level == screens.EDITAR:
                            label = screen.edit_label
                        cells.append({"level": level, "label": label})
                    compare_rows.append({"screen": screen, "cells": cells})

        context.update(
            {
                "instance": instance,
                "is_new": instance is None,
                "groups": groups,
                "screen_sections": context["form"].screen_fields(partial=partial),
                "partial_count": len(partial),
                "templates": screens.TEMPLATES,
                "template_key": self._template_key(),
                "members": (
                    instance.assignments.filter(is_active=True, user__is_active=True)
                    .select_related("user", "scope")
                    .order_by("user__first_name")
                    if instance is not None
                    else []
                ),
                "compare": compare,
                "compare_groups": compare_groups,
                "compare_rows": compare_rows,
                "screen_total": len(screens.SCREENS),
                "access_data": {"sections": _screens_payload()},
            }
        )
        return context

    def form_valid(self, form):
        from acessos.services import ScreenAccessService

        instance = self.get_instance()
        try:
            if instance is None:
                instance = AccessService.create_profile(
                    self.organization,
                    form.cleaned_data["name"],
                    created_by=self.request.user,
                    description=form.cleaned_data.get("description", ""),
                )
            else:
                instance = AccessService.update_profile(
                    instance,
                    name=form.cleaned_data["name"],
                    description=form.cleaned_data.get("description", ""),
                    changed_by=self.request.user,
                )
        except CadastroError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        ScreenAccessService.set_profile_screens(instance, form.screen_levels(), changed_by=self.request.user)
        messages.success(self.request, f"Grupo {instance.name} salvo.")
        return redirect("group-edit", pk=instance.pk)


class GroupToggleActiveView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    required_action = catalog.SEGURANCA_GERIR_AUTORIZACOES

    def post(self, request, pk):
        group = get_object_or_404(AccessProfile, pk=pk, organization=self.organization)
        group.is_active = not group.is_active
        group.save(update_fields=["is_active"])
        if group.is_active:
            messages.success(request, f"Grupo {group.name} reativado.")
        else:
            messages.success(
                request, f"Grupo {group.name} inativado. Quem estava nele perdeu as telas que vinham deste grupo."
            )
        return redirect("group-edit", pk=group.pk)


class UserAccessView(OrganizationRequiredMixin, ActionRequiredMixin, FormView):
    """Perfis e concessões diretas de uma pessoa, com a origem de cada acesso
    (doc 05 §31, §37)."""

    template_name = "core/user_access.html"
    form_class = AssignProfileForm
    required_action = catalog.SEGURANCA_GERIR_AUTORIZACOES

    def get_target(self):
        return get_object_or_404(
            User, pk=self.kwargs["pk"], profile__organization=self.organization
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target = self.get_target()
        context["target"] = target
        context["assignments"] = target.access_profiles.filter(is_active=True).select_related(
            "profile", "scope"
        )
        context["direct_grants"] = target.direct_actions.filter(is_active=True).select_related(
            "action", "scope"
        )
        context["effective_actions"] = AuthorizationService.effective_actions(target)
        context["unrestricted"] = AuthorizationService.has_unrestricted_access(target)
        context["grant_form"] = GrantActionForm(organization=self.organization)
        return context

    def form_valid(self, form):
        target = self.get_target()
        try:
            AccessService.assign_profile(
                user=target,
                profile=form.cleaned_data["profile"],
                scope_type=form.cleaned_data["scope_type"],
                sector=form.cleaned_data.get("sector"),
                company=form.cleaned_data.get("company"),
                site=form.cleaned_data.get("site"),
                cost_center=form.cleaned_data.get("cost_center"),
                relation=form.cleaned_data.get("relation") or "",
                granted_by=self.request.user,
            )
            messages.success(self.request, "Perfil atribuído.")
        except CadastroError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return redirect("user-access", pk=target.pk)


class UserAccessRemoveView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    required_action = catalog.SEGURANCA_GERIR_AUTORIZACOES

    def post(self, request, pk, assignment_pk):
        target = get_object_or_404(User, pk=pk, profile__organization=self.organization)
        assignment = get_object_or_404(
            UserProfileAssignment, pk=assignment_pk, user=target, organization=self.organization
        )
        AccessService.revoke_profile(assignment, changed_by=request.user)
        messages.success(request, "Atribuição removida.")
        return redirect("user-access", pk=target.pk)


class UserGrantActionView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    """Concessão direta para exceção pontual (doc 05 §27)."""

    required_action = catalog.SEGURANCA_GERIR_AUTORIZACOES

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk, profile__organization=self.organization)
        form = GrantActionForm(request.POST, organization=self.organization)
        if not form.is_valid():
            messages.error(request, "Verifique os dados da concessão.")
            return redirect("user-access", pk=target.pk)

        try:
            AccessService.grant_action(
                user=target,
                action=form.cleaned_data["action"],
                scope_type=form.cleaned_data["scope_type"],
                sector=form.cleaned_data.get("sector"),
                company=form.cleaned_data.get("company"),
                site=form.cleaned_data.get("site"),
                cost_center=form.cleaned_data.get("cost_center"),
                relation=form.cleaned_data.get("relation") or "",
                granted_by=request.user,
            )
            messages.success(request, "Concessão direta registrada.")
        except CadastroError as exc:
            messages.error(request, str(exc))
        return redirect("user-access", pk=target.pk)


class UserGrantRemoveView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    required_action = catalog.SEGURANCA_GERIR_AUTORIZACOES

    def post(self, request, pk, grant_pk):
        target = get_object_or_404(User, pk=pk, profile__organization=self.organization)
        grant = get_object_or_404(
            UserActionGrant, pk=grant_pk, user=target, organization=self.organization
        )
        AccessService.revoke_action(grant, changed_by=request.user)
        messages.success(request, "Concessão removida.")
        return redirect("user-access", pk=target.pk)
