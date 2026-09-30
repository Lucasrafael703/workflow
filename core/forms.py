from django import forms
from django.contrib.auth import get_user_model, password_validation

from acessos.models import Action
from acessos.models import Profile as AccessProfile
from acessos.models import Scope

from .colors import DEFAULTS
from .models import Client, Company, CostCenter, Organization, Sector, Site
from .widgets import ClientPickerWidget, ColorPaletteWidget, SitePickerWidget

User = get_user_model()


class SectorForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=150)
    description = forms.CharField(label="Descrição", max_length=255, required=False)


class CompanyForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=150)
    document = forms.CharField(label="CNPJ/CPF", max_length=20, required=False)


class SiteForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=150)
    client = forms.ModelChoiceField(
        label="Cliente", queryset=Client.objects.none(), required=False, widget=ClientPickerWidget()
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = Client.objects.filter(
            organization=organization, is_active=True
        )
        self.fields["client"].widget.queryset = self.fields["client"].queryset


class CostCenterForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=150)
    site = forms.ModelChoiceField(
        label="Obra", queryset=Site.objects.none(), required=False, widget=SitePickerWidget()
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["site"].queryset = Site.objects.filter(
            organization=organization, is_active=True
        )
        self.fields["site"].widget.queryset = self.fields["site"].queryset


class ClientForm(forms.Form):
    """Cadastro de cliente (Regra 1-2 da tela de atividade): quem solicita o
    serviço, distinto das empresas internas da própria organização."""

    name = forms.CharField(label="Nome", max_length=150)
    document = forms.CharField(label="CNPJ/CPF", max_length=20, required=False)
    phone = forms.CharField(label="Telefone", max_length=30, required=False)
    email = forms.EmailField(label="E-mail", required=False)
    address = forms.CharField(label="Endereço", max_length=255, required=False)


class ReturnReasonForm(forms.Form):
    name = forms.CharField(label="Motivo", max_length=150)


class TaskStageForm(forms.Form):
    """Estágio de Kanban de tarefa — a ordem nunca é digitada, só arrastada."""

    name = forms.CharField(label="Nome", max_length=150)
    color = forms.CharField(label="Cor", widget=ColorPaletteWidget, initial="#94A3B8")


class ActivityStageForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=150)
    color = forms.CharField(label="Cor", widget=ColorPaletteWidget, initial="#94A3B8")


class WorkflowStatusForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=150)
    description = forms.CharField(label="Descricao", max_length=255, required=False)
    behavior = forms.ChoiceField(label="Comportamento base", choices=())
    color = forms.CharField(label="Cor", widget=ColorPaletteWidget, initial="#94A3B8")

    def __init__(self, *args, domain=None, **kwargs):
        super().__init__(*args, **kwargs)
        color_domain = "activity_status" if domain == "activity" else "task_status"
        self.fields["behavior"].choices = [
            (code, code.replace("_", " ").title()) for code in DEFAULTS.get(color_domain, {})
        ]


class EnumColorLabelForm(forms.Form):
    """Edita o nome/descricao exibidos e o estado oculto de um status
    nativo (Activity.Status/Task.Status) — nunca o comportamento interno,
    que continua fixo no code."""

    label = forms.CharField(label="Nome exibido", max_length=100, required=False)
    description = forms.CharField(label="Descricao", max_length=255, required=False)
    is_hidden = forms.BooleanField(label="Ocultar este status das opcoes", required=False)


class TagForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=80)
    color = forms.CharField(label="Cor", widget=ColorPaletteWidget, initial="#94A3B8")


class UserForm(forms.Form):
    """Cadastro de usuário numa tela só: quem é, em qual equipe trabalha e o
    que pode acessar (grupo + telas).

    "Equipes" continua sendo participação em setor — onde a pessoa trabalha.
    O que ela pode fazer vem do grupo de acesso e dos ajustes por tela, que
    por baixo viram perfil e concessões do motor de autorização.
    """

    FIRST_ACCESS_PASSWORD = "senha"
    FIRST_ACCESS_INVITE = "convite"

    first_name = forms.CharField(label="Nome completo", max_length=150)
    email = forms.EmailField(label="E-mail")
    username = forms.CharField(label="Usuário (login)", max_length=150)
    organization = forms.ModelChoiceField(
        label="Organização", queryset=Organization.objects.none(), required=True, empty_label=None
    )
    first_access = forms.ChoiceField(
        label="Primeiro acesso",
        choices=[
            (FIRST_ACCESS_PASSWORD, "Definir uma senha agora"),
            (FIRST_ACCESS_INVITE, "Enviar link por e-mail para a pessoa criar a senha"),
        ],
        initial=FIRST_ACCESS_PASSWORD,
        required=False,
        widget=forms.RadioSelect,
    )
    password1 = forms.CharField(
        label="Senha",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar senha",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    sectors = forms.ModelMultipleChoiceField(
        label="Equipes em que trabalha",
        queryset=Sector.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    managed_sectors = forms.ModelMultipleChoiceField(
        label="Equipes que gerencia",
        queryset=Sector.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Ser gestor é um vínculo estrutural: não concede autorização por si só.",
    )
    main_sector = forms.ModelChoiceField(
        label="Equipe principal",
        queryset=Sector.objects.none(),
        required=False,
    )
    is_active = forms.BooleanField(label="Ativo", required=False, initial=True)

    access_group = forms.ModelChoiceField(
        label="Grupo de acesso",
        queryset=AccessProfile.objects.none(),
        required=False,
        empty_label="Sem grupo",
        widget=forms.RadioSelect,
    )
    access_scope = forms.ChoiceField(label="Vale para", required=False)

    def __init__(self, *args, organization=None, instance=None, access_summary=None, **kwargs):
        from acessos import screens
        from acessos.services import ScreenAccessService

        super().__init__(*args, **kwargs)
        self.instance = instance
        self.organization = organization
        self.access_summary = access_summary
        sectors = Sector.objects.filter(organization=organization, is_active=True)
        self.fields["sectors"].queryset = sectors
        self.fields["managed_sectors"].queryset = sectors
        self.fields["organization"].queryset = Organization.objects.filter(pk=organization.pk)
        self.fields["organization"].initial = organization
        self.fields["main_sector"].queryset = sectors
        self.fields["access_group"].queryset = AccessProfile.objects.filter(
            organization=organization, is_active=True
        ).order_by("name")

        scope_choices = [
            (ScreenAccessService.SCOPE_ORGANIZACAO, "Toda a organização (recomendado)"),
            (ScreenAccessService.SCOPE_MINHAS_EQUIPES, "Só nas equipes da pessoa"),
        ]
        primary = (access_summary or {}).get("primary")
        standard_ids = {
            ScreenAccessService.standard_scope(organization, choice).id for choice, _ in scope_choices
        } if organization is not None else set()
        if primary is not None and primary.scope_id not in standard_ids:
            scope_choices.append((f"escopo:{primary.scope_id}", f"Como está hoje: {primary.scope.label}"))
        self.fields["access_scope"].choices = scope_choices
        self.fields["access_scope"].initial = ScreenAccessService.SCOPE_ORGANIZACAO

        for screen in screens.SCREENS:
            choices = [(screens.SEM_ACESSO, "Sem acesso")]
            if screen.has_view_level:
                choices.append((screens.VER, "Ver"))
            choices.append((screens.EDITAR, screen.edit_label))
            self.fields[f"screen_{screen.key}"] = forms.TypedChoiceField(
                label=screen.name,
                choices=choices,
                coerce=int,
                required=False,
                empty_value=screens.SEM_ACESSO,
                widget=forms.RadioSelect,
                initial=screens.SEM_ACESSO,
            )

        if instance is None:
            self.fields["password1"].help_text = "A pessoa poderá alterá-la depois, em Perfil."
        else:
            self.fields["password1"].help_text = "Deixe em branco para manter a senha atual."
            self.fields["password2"].help_text = "Repita a nova senha, se estiver redefinindo."

        if access_summary is not None and not self.is_bound:
            if primary is not None:
                self.fields["access_group"].initial = primary.profile_id
                if primary.scope_id in standard_ids:
                    self.fields["access_scope"].initial = (
                        ScreenAccessService.SCOPE_MINHAS_EQUIPES
                        if primary.scope.type == Scope.Type.RELACIONAL
                        else ScreenAccessService.SCOPE_ORGANIZACAO
                    )
                else:
                    self.fields["access_scope"].initial = f"escopo:{primary.scope_id}"
            for key, level in access_summary["levels"].items():
                self.fields[f"screen_{key}"].initial = level

        if instance is not None and not self.is_bound:
            from accounts.models import UserSector

            self.fields["first_name"].initial = instance.first_name
            self.fields["email"].initial = instance.email
            self.fields["username"].initial = instance.username
            self.fields["is_active"].initial = instance.is_active
            memberships = UserSector.objects.filter(user=instance, removed_at__isnull=True)
            self.fields["sectors"].initial = [m.sector_id for m in memberships]
            self.fields["managed_sectors"].initial = [
                m.sector_id for m in memberships if m.role == UserSector.Role.GESTOR
            ]
            profile = getattr(instance, "profile", None)
            self.fields["main_sector"].initial = getattr(profile, "main_sector_id", None)

    # -- telas -------------------------------------------------------------

    def screen_fields(self):
        """Campos de tela agrupados por seção, para o template."""
        from acessos import screens

        sections = []
        for section in screens.SECTIONS:
            rows = []
            for screen in section.screens:
                rows.append({"screen": screen, "field": self[f"screen_{screen.key}"]})
            sections.append(
                {"name": section.name, "rows": rows, "has_view": any(r["screen"].has_view_level for r in rows)}
            )
        return sections

    def screen_levels(self):
        from acessos import screens

        return {
            screen.key: int(self.cleaned_data.get(f"screen_{screen.key}") or 0) for screen in screens.SCREENS
        }

    def resolve_scope(self):
        from acessos.services import ScreenAccessService

        choice = self.cleaned_data.get("access_scope") or ScreenAccessService.SCOPE_ORGANIZACAO
        if choice.startswith("escopo:"):
            return Scope.objects.get(pk=int(choice.split(":", 1)[1]), organization=self.organization)
        return ScreenAccessService.standard_scope(self.organization, choice)

    # -- validação ---------------------------------------------------------

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        queryset = User.objects.filter(username__iexact=username)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Já existe um usuário com este nome de usuário.")
        return username

    def clean(self):
        cleaned = super().clean()
        sectors = set(cleaned.get("sectors") or [])
        managed = set(cleaned.get("managed_sectors") or [])
        if not managed <= sectors:
            self.add_error(
                "managed_sectors",
                "Só é possível gerenciar uma equipe da qual a pessoa participa.",
            )
        main = cleaned.get("main_sector")
        if main is not None and main not in sectors:
            self.add_error("main_sector", "A equipe principal precisa estar entre as equipes marcadas.")

        invite = cleaned.get("first_access") == self.FIRST_ACCESS_INVITE and self.instance is None
        cleaned["send_invite"] = invite
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if self.instance is None and not invite and not password1:
            self.add_error("password1", "Informe uma senha ou escolha enviar o link por e-mail.")
        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "As senhas não coincidem.")
            elif password1:
                try:
                    password_validation.validate_password(password1, user=self.instance)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)

        access_scope = cleaned.get("access_scope") or ""
        if access_scope.startswith("escopo:"):
            try:
                self.resolve_scope()
            except (Scope.DoesNotExist, ValueError):
                self.add_error("access_scope", "Escopo inválido.")
        return cleaned


class AccessGroupForm(forms.Form):
    """Grupo de acesso = um perfil, editado por tela."""

    name = forms.CharField(label="Nome do grupo", max_length=120)
    description = forms.CharField(label="Descrição", max_length=255, required=False)

    def __init__(self, *args, levels=None, **kwargs):
        from acessos import screens

        super().__init__(*args, **kwargs)
        levels = levels or {}
        for screen in screens.SCREENS:
            choices = [(screens.SEM_ACESSO, "Sem acesso")]
            if screen.has_view_level:
                choices.append((screens.VER, "Ver"))
            choices.append((screens.EDITAR, screen.edit_label))
            self.fields[f"screen_{screen.key}"] = forms.TypedChoiceField(
                label=screen.name,
                choices=choices,
                coerce=int,
                required=False,
                empty_value=screens.SEM_ACESSO,
                widget=forms.RadioSelect,
                initial=levels.get(screen.key, screens.SEM_ACESSO),
            )

    def screen_fields(self, partial=()):
        from acessos import screens

        sections = []
        for section in screens.SECTIONS:
            rows = [
                {"screen": screen, "field": self[f"screen_{screen.key}"], "partial": screen.key in partial}
                for screen in section.screens
            ]
            sections.append(
                {"name": section.name, "rows": rows, "has_view": any(r["screen"].has_view_level for r in rows)}
            )
        return sections

    def screen_levels(self):
        from acessos import screens

        return {
            screen.key: int(self.cleaned_data.get(f"screen_{screen.key}") or 0) for screen in screens.SCREENS
        }


class AccessProfileForm(forms.Form):
    """Perfil de acesso = conjunto reutilizável de ações (doc 05 §11, §32)."""

    name = forms.CharField(label="Nome do perfil", max_length=120)
    description = forms.CharField(label="Descrição", max_length=255, required=False)


class ScopedGrantForm(forms.Form):
    """Base das telas que concedem algo: a concessão sempre tem um "onde"."""

    scope_type = forms.ChoiceField(label="Onde vale", choices=Scope.Type.choices)
    company = forms.ModelChoiceField(label="Empresa", queryset=Company.objects.none(), required=False)
    sector = forms.ModelChoiceField(label="Setor", queryset=Sector.objects.none(), required=False)
    site = forms.ModelChoiceField(label="Obra", queryset=Site.objects.none(), required=False)
    cost_center = forms.ModelChoiceField(
        label="Centro de custo", queryset=CostCenter.objects.none(), required=False
    )
    relation = forms.ChoiceField(
        label="Relação", choices=[("", "---------")] + list(Scope.Relation.choices), required=False
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company.objects.filter(
            organization=organization, is_active=True
        )
        self.fields["sector"].queryset = Sector.objects.filter(
            organization=organization, is_active=True
        )
        self.fields["site"].queryset = Site.objects.filter(organization=organization, is_active=True)
        self.fields["cost_center"].queryset = CostCenter.objects.filter(
            organization=organization, is_active=True
        )

    def clean(self):
        cleaned = super().clean()
        scope_type = cleaned.get("scope_type")
        required_field = {
            Scope.Type.EMPRESA: "company",
            Scope.Type.SETOR: "sector",
            Scope.Type.OBRA: "site",
            Scope.Type.CENTRO_CUSTO: "cost_center",
            Scope.Type.RELACIONAL: "relation",
        }.get(scope_type)
        if required_field and not cleaned.get(required_field):
            self.add_error(required_field, "Obrigatório para este tipo de escopo.")
        return cleaned


class AssignProfileForm(ScopedGrantForm):
    profile = forms.ModelChoiceField(label="Perfil", queryset=AccessProfile.objects.none())

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, organization=organization, **kwargs)
        self.fields["profile"].queryset = AccessProfile.objects.filter(
            organization=organization, is_active=True
        )
        self.order_fields(["profile", "scope_type", "company", "sector", "site", "cost_center", "relation"])


class GrantActionForm(ScopedGrantForm):
    """Concessão direta: exceção pontual, não a forma padrão de administrar
    (doc 05 §27)."""

    action = forms.ModelChoiceField(label="Ação", queryset=Action.objects.none())

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, organization=organization, **kwargs)
        self.fields["action"].queryset = Action.objects.filter(is_active=True).select_related("group")
        self.order_fields(["action", "scope_type", "company", "sector", "site", "cost_center", "relation"])


class NotificationPreferencesForm(forms.Form):
    """Preferências pessoais de notificação (doc 09 §193)."""

    notify_mentions = forms.BooleanField(label="Menções a mim", required=False, initial=True)
    notify_position = forms.BooleanField(
        label="Mudança de posição nas minhas demandas", required=False, initial=True
    )
    notify_messages = forms.BooleanField(
        label="Novas mensagens nas minhas atividades", required=False, initial=True
    )
    notify_completion = forms.BooleanField(
        label="Conclusão das minhas atividades", required=False, initial=True
    )
