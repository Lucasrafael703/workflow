from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView, View

from .forms import (
    CompanyForm,
    CostCenterForm,
    NotificationPreferencesForm,
    ProfileGroupForm,
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
    UserSectorService,
)

User = get_user_model()


# Rótulo humano primeiro, código técnico depois (doc 09 §203-205).
PERMISSION_GROUPS = [
    (
        "Atividades",
        [
            ("activities.add_activity", "Criar atividade"),
            ("activities.change_activity", "Editar atividade"),
            ("activities.can_view_all_activities", "Visualizar todas as atividades"),
            ("activities.can_change_owner", "Alterar dono da atividade"),
            ("activities.can_cancel_activity", "Cancelar atividade"),
            ("activities.can_reopen_activity", "Reabrir atividade"),
        ],
    ),
    (
        "Tarefas",
        [
            ("activities.add_task", "Criar tarefa"),
            ("activities.change_task", "Editar tarefa"),
            ("activities.can_assume_task", "Assumir tarefa"),
            ("activities.can_assign_task", "Atribuir executor"),
        ],
    ),
    (
        "Filas",
        [
            ("activities.can_view_full_queue", "Visualizar fila completa"),
            ("activities.can_reorder_queue", "Reordenar fila"),
        ],
    ),
    (
        "Prazos",
        [("activities.can_resolve_deadline_conflict", "Resolver conflito de prazo")],
    ),
    (
        "Cadastros",
        [
            ("core.change_sector", "Criar e editar setores"),
            ("core.change_company", "Criar e editar empresas"),
            ("core.change_site", "Criar e editar obras"),
            ("core.change_costcenter", "Criar e editar centros de custo"),
            ("activities.change_returnreason", "Criar e editar motivos de devolução"),
        ],
    ),
    (
        "Segurança",
        [
            ("auth.add_user", "Criar usuário"),
            ("auth.change_user", "Editar usuário"),
            ("auth.change_group", "Editar perfis e permissões"),
        ],
    ),
]

PERMISSION_DESCRIPTIONS = {
    "activities.can_view_full_queue": "Permite ver todas as tarefas e detalhes da fila do setor, não apenas a própria posição.",
    "activities.can_reorder_queue": "Permite alterar a ordem de execução das tarefas do setor.",
    "activities.can_change_owner": "Permite transferir a responsabilidade de uma atividade para outra pessoa.",
    "activities.can_resolve_deadline_conflict": "Permite encerrar um conflito de prazo registrando a decisão.",
}


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
    required_action = "core.change_sector"

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
    required_action = "core.change_sector"

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
    required_action = "core.change_company"

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
    required_action = "core.change_site"

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
    required_action = "core.change_costcenter"

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
    required_action = "activities.change_returnreason"

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
        "setores": (Sector, "core.change_sector"),
        "empresas": (Company, "core.change_company"),
        "obras": (Site, "core.change_site"),
        "centros-de-custo": (CostCenter, "core.change_costcenter"),
    }

    def resolve(self, tab):
        if tab == "motivos":
            from activities.models import ReturnReason

            return ReturnReason, "activities.change_returnreason"
        return self.cadastros.get(tab, (None, None))

    def post(self, request, tab, pk):
        model, action = self.resolve(tab)
        if model is None:
            messages.error(request, "Cadastro desconhecido.")
            return redirect("cadastros")
        if not request.user.has_perm(action):
            raise PermissionDenied("Você não possui acesso para alterar este cadastro.")

        instance = get_object_or_404(model, pk=pk, organization=self.organization)
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
    """Responde "O que este perfil pode fazer?" (doc 09 §196-209)."""

    template_name = "core/permissions.html"
    required_action = "auth.change_group"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        groups = Group.objects.annotate(user_count=Count("user")).order_by("name")
        selected = self.request.GET.get("group")
        group = groups.filter(pk=selected).first() if selected else groups.first()

        granted = set()
        if group:
            granted = {
                f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.all()
            }

        search = self.request.GET.get("q", "").strip().lower()
        blocks = []
        for label, actions in PERMISSION_GROUPS:
            rows = [
                {
                    "code": code,
                    "label": human,
                    "description": PERMISSION_DESCRIPTIONS.get(code, ""),
                    "granted": code in granted,
                }
                for code, human in actions
                if not search or search in human.lower() or search in code.lower()
            ]
            if rows:
                blocks.append({"label": label, "rows": rows})

        context.update(
            {
                "groups": groups,
                "group": group,
                "blocks": blocks,
                "search": self.request.GET.get("q", ""),
                "members": User.objects.filter(groups=group).order_by("username") if group else [],
            }
        )
        return context


class PermissionUpdateView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    required_action = "auth.change_group"

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        selected = set(request.POST.getlist("permissions"))
        # Só as ações exibidas podem ser desmarcadas: com um filtro de busca
        # ativo, o que ficou fora da tela precisa ser preservado. Se nada foi
        # exibido, não há o que desmarcar.
        visible = set(request.POST.getlist("visible"))

        keep = [
            p
            for p in group.permissions.all()
            if f"{p.content_type.app_label}.{p.codename}" not in visible
        ]
        known = {code for _, actions in PERMISSION_GROUPS for code, _ in actions}

        permissions = []
        for code in selected & known & visible:
            app_label, codename = code.split(".", 1)
            permission = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            ).first()
            if permission:
                permissions.append(permission)

        group.permissions.set(permissions + keep)
        messages.success(request, f"Permissões do perfil {group.name} atualizadas.")
        return redirect(f"{reverse('permissions')}?group={group.pk}")


class ProfileGroupCreateView(OrganizationRequiredMixin, ActionRequiredMixin, FormView):
    template_name = "core/profile_group_form.html"
    form_class = ProfileGroupForm
    required_action = "auth.change_group"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["permission_choices"] = [
            (code, human) for _, actions in PERMISSION_GROUPS for code, human in actions
        ]
        pk = self.kwargs.get("pk")
        kwargs["instance"] = get_object_or_404(Group, pk=pk) if pk else None
        return kwargs

    def form_valid(self, form):
        pk = self.kwargs.get("pk")
        group = get_object_or_404(Group, pk=pk) if pk else None
        name = form.cleaned_data["name"].strip()

        if Group.objects.filter(name__iexact=name).exclude(pk=group.pk if group else None).exists():
            form.add_error("name", "Já existe um perfil com este nome.")
            return self.form_invalid(form)

        if group is None:
            group = Group.objects.create(name=name)
        else:
            group.name = name
            group.save(update_fields=["name"])

        permissions = []
        for code in form.cleaned_data["permissions"]:
            app_label, codename = code.split(".", 1)
            permission = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            ).first()
            if permission:
                permissions.append(permission)
        group.permissions.set(permissions)

        messages.success(self.request, "Perfil salvo.")
        return redirect(f"{reverse('permissions')}?group={group.pk}")


class UserListView(OrganizationRequiredMixin, ActionRequiredMixin, TemplateView):
    template_name = "core/user_list.html"
    required_action = "auth.change_user"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = (
            User.objects.filter(profile__organization=self.organization)
            .prefetch_related("groups")
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
        return context


class UserFormView(OrganizationRequiredMixin, ActionRequiredMixin, FormView):
    template_name = "core/user_form.html"
    form_class = UserForm
    required_action = "auth.change_user"

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

            context["open_activities"] = Activity.objects.filter(
                organization=self.organization, owner=instance
            ).exclude(status__in=["CONCLUIDA", "CANCELADA"]).count()
            context["open_tasks"] = Task.objects.filter(
                activity__organization=self.organization,
                executors__user=instance,
                executors__removed_at__isnull=True,
                status__in=["DISPONIVEL", "EM_FILA", "EM_EXECUCAO", "BLOQUEADA"],
            ).distinct().count()
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

        instance.groups.set(data["groups"])

        selected = set(data["sectors"])
        current = set(
            Sector.objects.filter(
                user_memberships__user=instance, user_memberships__removed_at__isnull=True
            )
        )
        for sector in selected - current:
            UserSectorService.add(instance, sector)
        for sector in current - selected:
            UserSectorService.remove(instance, sector)

        return redirect("user-list")
