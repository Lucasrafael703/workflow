from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
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
    AccessProfileForm,
    AssignProfileForm,
    CompanyForm,
    CostCenterForm,
    GrantActionForm,
    NotificationPreferencesForm,
    ReturnReasonForm,
    SectorForm,
    SiteForm,
    UserForm,
)
from .mixins import ActionRequiredMixin, OrganizationRequiredMixin
from .models import Company, CostCenter, Sector, Site
from .services import (
    CadastroError,
    CompanyService,
    CostCenterService,
    ReturnReasonService,
    SectorService,
    SimpleCadastroService,
    SiteService,
)

User = get_user_model()


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
        sites = Site.objects.filter(organization=org).select_related("company")
        cost_centers = CostCenter.objects.filter(organization=org).select_related("site")
        reasons = ReturnReason.objects.filter(organization=org)

        if search:
            sectors = sectors.filter(name__icontains=search)
            companies = companies.filter(name__icontains=search)
            sites = sites.filter(name__icontains=search)
            cost_centers = cost_centers.filter(name__icontains=search)
            reasons = reasons.filter(name__icontains=search)

        context.update(
            {
                "tab": self.request.GET.get("tab", "setores"),
                "search": search,
                "sectors": sectors,
                "companies": companies,
                "sites": sites,
                "cost_centers": cost_centers,
                "return_reasons": reasons,
            }
        )
        return context


class CadastroFormView(OrganizationRequiredMixin, ActionRequiredMixin, FormView):
    """Base dos formulários de cadastro: criar e editar compartilham a tela.

    Criar e alterar cadastro é ação administrativa e exige autorização
    explícita — participar da organização não basta (Regras 05 §87-89).
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
                self.create(form.cleaned_data)
                messages.success(self.request, "Cadastro criado.")
            else:
                self.update(instance, form.cleaned_data)
                messages.success(self.request, "Cadastro atualizado.")
        except CadastroError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return redirect(self.success_url_for_tab())


class SectorFormView(CadastroFormView):
    form_class = SectorForm
    model = Sector
    tab = "setores"
    title = "Setor"
    required_action = catalog.SETOR_EDITAR

    def initial_from(self, instance):
        return {"name": instance.name, "description": instance.description}

    def create(self, data):
        SectorService.create(
            self.organization, data["name"], self.request.user, description=data.get("description", "")
        )

    def update(self, instance, data):
        SectorService.update(instance, name=data["name"], description=data.get("description", ""))


class CompanyFormView(CadastroFormView):
    form_class = CompanyForm
    model = Company
    tab = "empresas"
    title = "Empresa"
    required_action = catalog.EMPRESA_GERIR

    def initial_from(self, instance):
        return {"name": instance.name, "document": instance.document}

    def create(self, data):
        CompanyService.create(self.organization, data["name"], document=data.get("document", ""))

    def update(self, instance, data):
        CompanyService.update(instance, name=data["name"], document=data.get("document", ""))


class SiteFormView(CadastroFormView):
    form_class = SiteForm
    model = Site
    tab = "obras"
    title = "Obra"
    required_action = catalog.OBRA_GERIR

    def initial_from(self, instance):
        return {"name": instance.name, "company": instance.company_id}

    def create(self, data):
        SiteService.create(self.organization, data["name"], company=data.get("company"))

    def update(self, instance, data):
        SiteService.update(instance, name=data["name"], company=data.get("company"))


class CostCenterFormView(CadastroFormView):
    form_class = CostCenterForm
    model = CostCenter
    tab = "centros-de-custo"
    title = "Centro de custo"
    required_action = catalog.CENTRO_CUSTO_GERIR

    def initial_from(self, instance):
        return {"name": instance.name, "site": instance.site_id}

    def create(self, data):
        CostCenterService.create(self.organization, data["name"], site=data.get("site"))

    def update(self, instance, data):
        CostCenterService.update(instance, name=data["name"], site=data.get("site"))


class ReturnReasonFormView(CadastroFormView):
    form_class = ReturnReasonForm
    tab = "motivos"
    title = "Motivo de devolução"
    required_action = catalog.MOTIVO_DEVOLUCAO_GERIR

    def get_model(self):
        from activities.models import ReturnReason

        return ReturnReason

    def create(self, data):
        ReturnReasonService.create(self.organization, data["name"])

    def update(self, instance, data):
        ReturnReasonService.update(instance, name=data["name"])


class CadastroToggleActiveView(OrganizationRequiredMixin, View):
    """Inativar preserva o histórico; excluir não é oferecido (Regras 05 §89-90)."""

    # Cada cadastro é governado pela sua própria ação; inativar um setor
    # afeta filas e tarefas de toda a organização.
    cadastros = {
        "setores": (Sector, catalog.SETOR_INATIVAR),
        "empresas": (Company, catalog.EMPRESA_GERIR),
        "obras": (Site, catalog.OBRA_GERIR),
        "centros-de-custo": (CostCenter, catalog.CENTRO_CUSTO_GERIR),
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


class UserListView(OrganizationRequiredMixin, ActionRequiredMixin, TemplateView):
    template_name = "core/user_list.html"
    required_action = catalog.USUARIO_VISUALIZAR

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = (
            User.objects.filter(profile__organization=self.organization)
            .prefetch_related("access_profiles__profile", "access_profiles__scope")
            .order_by("username")
        )
        search = self.request.GET.get("q", "").strip()
        if search:
            users = users.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(email__icontains=search)
            )
        context["users"] = users
        context["search"] = search
        context["can_edit"] = AuthorizationService.can(self.request.user, catalog.USUARIO_EDITAR)
        return context


class UserFormView(OrganizationRequiredMixin, ActionRequiredMixin, FormView):
    template_name = "core/user_form.html"
    form_class = UserForm
    required_action = catalog.USUARIO_EDITAR

    def get_instance(self):
        pk = self.kwargs.get("pk")
        if pk is None:
            return None
        return get_object_or_404(User, pk=pk, profile__organization=self.organization)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["instance"] = self.get_instance()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.get_instance()
        context["instance"] = instance
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

    def form_valid(self, form):
        instance = self.get_instance()
        data = form.cleaned_data

        if instance is None:
            instance = User.objects.create_user(
                username=data["username"], email=data["email"], first_name=data["first_name"]
            )
            messages.success(
                self.request,
                f"Usuário {instance.username} criado. Defina a senha pelo fluxo de acesso.",
            )
        else:
            instance.username = data["username"]
            instance.email = data["email"]
            instance.first_name = data["first_name"]
            instance.is_active = data["is_active"]
            instance.save()
            messages.success(self.request, "Usuário atualizado.")

        profile = instance.profile
        if profile.organization_id != self.organization.id:
            profile.organization = self.organization
            profile.save(update_fields=["organization"])

        AccessService.sync_user_sectors(
            instance,
            sectors=data["sectors"],
            managed_sectors=data.get("managed_sectors") or [],
            changed_by=self.request.user,
        )
        return redirect("user-list")


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
