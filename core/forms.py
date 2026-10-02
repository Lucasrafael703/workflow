from django import forms
from django.contrib.auth import get_user_model, password_validation

from acessos.models import Action
from acessos.models import Profile as AccessProfile
from acessos.models import Scope

from .colors import DEFAULTS, is_valid_palette_color
from .models import Client, Company, CostCenter, Organization, Sector, Site
from .widgets import (
    ClientPickerWidget,
    ColorPaletteWidget,
    SectorCheckboxSelectMultiple,
    SectorPickerWidget,
    SitePickerWidget,
)

User = get_user_model()


class SectorForm(forms.Form):
    name = forms.CharField(label="Nome do setor", max_length=150, help_text="Ex.: Compras, Orçamento ou Engenharia.")
    description = forms.CharField(label="O que este setor faz", max_length=255, required=False)
    color = forms.CharField(label="Cor de visualização", widget=ColorPaletteWidget, initial="#3B82F6")

    def clean_color(self):
        color = (self.cleaned_data.get("color") or "#3B82F6").upper()
        if not is_valid_palette_color(color):
            raise forms.ValidationError("Escolha uma cor da paleta oficial.")
        return color


class CompanyForm(forms.Form):
    name = forms.CharField(label="Nome da empresa", max_length=150, help_text="Informe a empresa da sua organização que realiza o trabalho.")
    document = forms.CharField(label="CNPJ/CPF", max_length=20, required=False)


class SiteForm(forms.Form):
    name = forms.CharField(label="Nome da obra", max_length=150, help_text="Use o nome pelo qual a equipe reconhece a obra.")
    client = forms.ModelChoiceField(
        label="Cliente desta obra", queryset=Client.objects.none(), required=False, widget=ClientPickerWidget(),
        help_text="Selecione quem contratou ou solicitou o trabalho nesta obra.",
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = Client.objects.filter(
            organization=organization, is_active=True
        )
        self.fields["client"].widget.queryset = self.fields["client"].queryset


class CostCenterForm(forms.Form):
    name = forms.CharField(label="Nome do centro de custo", max_length=150, help_text="Grupo usado para acompanhar onde o tempo e o trabalho são gastos.")
    site = forms.ModelChoiceField(
        label="Obra relacionada", queryset=Site.objects.none(), required=False, widget=SitePickerWidget()
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
    name = forms.CharField(label="Motivo da devolução", max_length=150, help_text="Ex.: Faltam informações ou é necessário corrigir o documento.")


class SectorScopedVisualForm(forms.Form):
    sector = forms.ModelChoiceField(label="Setor", queryset=Sector.objects.none(), widget=SectorPickerWidget())
    name = forms.CharField(label="Nome", max_length=150)
    color = forms.CharField(label="Cor", widget=ColorPaletteWidget, initial="#94A3B8")
    is_default = forms.BooleanField(label="Usar como padrão deste setor", required=False)

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        sectors = Sector.objects.filter(organization=organization, is_active=True)
        self.fields["sector"].queryset = sectors
        self.fields["sector"].widget.queryset = sectors


class TaskStageForm(SectorScopedVisualForm):
    """Etapa de tarefa; a ordem só muda por arrastar."""


class ActivityStageForm(SectorScopedVisualForm):
    """Etapa de demanda; a ordem só muda por arrastar."""


class WorkflowStatusForm(SectorScopedVisualForm):
    name = forms.CharField(label="Nome", max_length=150)
    description = forms.CharField(label="O que este status indica", max_length=255, required=False)

    # ``domain`` é aceito por compatibilidade com as URLs antigas; status
    # não recebe comportamento operacional.
    def __init__(self, *args, domain=None, organization=None, **kwargs):
        super().__init__(*args, organization=organization, **kwargs)


class EnumColorLabelForm(forms.Form):
    """Edita o nome/descricao exibidos e o estado oculto de um status
    nativo (Activity.Status/Task.Status) — nunca o comportamento interno,
    que continua fixo no code."""

    label = forms.CharField(label="Nome exibido", max_length=100, required=False)
    description = forms.CharField(label="O que este status significa", max_length=255, required=False)
    is_hidden = forms.BooleanField(label="Ocultar este status das opções", required=False)


class TagForm(forms.Form):
    name = forms.CharField(label="Nome do marcador", max_length=80, help_text="Uma palavra curta para encontrar trabalhos parecidos. Ex.: Revisão.")
    color = forms.CharField(label="Cor", widget=ColorPaletteWidget, initial="#94A3B8")


class UserForm(forms.Form):
    """Cadastro de usuário (doc 05 §7, §37).

    "Setores em que atua" descreve onde a pessoa trabalha; o que ela pode fazer
    é definido na tela de acessos, sempre dentro de um escopo (doc 05 §8, §45).
    """

    first_name = forms.CharField(label="Nome da pessoa", max_length=150)
    email = forms.EmailField(label="E-mail para entrar na LPS")
    username = forms.CharField(label="Nome de usuário", max_length=150, help_text="Identificador único da conta. Ex.: maria.silva.")
    organization = forms.ModelChoiceField(
        label="Organização", queryset=Organization.objects.none(), required=True, empty_label=None
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
        label="Setores em que atua",
        queryset=Sector.objects.none(),
        required=False,
        widget=SectorCheckboxSelectMultiple,
    )
    managed_sectors = forms.ModelMultipleChoiceField(
        label="Setores que gerencia",
        queryset=Sector.objects.none(),
        required=False,
        widget=SectorCheckboxSelectMultiple,
        help_text="Escolha apenas setores marcados acima. As permissões são definidas depois, em Acessos.",
    )
    is_active = forms.BooleanField(label="Permitir que esta pessoa entre na LPS", required=False, initial=True,
                                 help_text="Ao desmarcar, a conta fica inativa e o histórico é preservado.")

    def __init__(self, *args, organization=None, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        sectors = Sector.objects.filter(organization=organization, is_active=True)
        self.fields["sectors"].queryset = sectors
        self.fields["managed_sectors"].queryset = sectors
        self.fields["organization"].queryset = Organization.objects.filter(pk=organization.pk)
        self.fields["organization"].initial = organization

        if instance is None:
            # Cadastrar exige senha na hora — não existe fluxo de convite por
            # e-mail nesta versão, então a pessoa não teria como entrar.
            self.fields["password1"].required = True
            self.fields["password2"].required = True
            self.fields["password1"].help_text = "Defina uma senha inicial e informe à pessoa como entrar com seu e-mail."
        else:
            self.fields["password1"].help_text = "Deixe em branco para manter a senha atual."
            self.fields["password2"].help_text = "Repita a nova senha, se estiver redefinindo."

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
                "Só é possível gerenciar um setor do qual a pessoa participa.",
            )

        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "As senhas não coincidem.")
            elif password1:
                try:
                    password_validation.validate_password(password1, user=self.instance)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)
        return cleaned


class AccessProfileForm(forms.Form):
    """Perfil de acesso = conjunto reutilizável de ações (doc 05 §11, §32)."""

    name = forms.CharField(label="Nome do perfil", max_length=120, help_text="Ex.: Colaborador, Gestor de setor ou Administrador.")
    description = forms.CharField(label="Para quem é este perfil?", max_length=255, required=False)


class ScopedGrantForm(forms.Form):
    """Base das telas que concedem algo: a concessão sempre tem um "onde"."""

    scope_type = forms.ChoiceField(label="Onde a pessoa poderá usar este acesso?", choices=Scope.Type.choices,
                                  help_text="Escolha toda a organização ou limite o acesso a uma empresa, setor, obra ou aos trabalhos da pessoa.")
    company = forms.ModelChoiceField(label="Empresa", queryset=Company.objects.none(), required=False)
    sector = forms.ModelChoiceField(
        label="Setor", queryset=Sector.objects.none(), required=False, widget=SectorPickerWidget()
    )
    site = forms.ModelChoiceField(label="Obra", queryset=Site.objects.none(), required=False)
    cost_center = forms.ModelChoiceField(
        label="Centro de custo", queryset=CostCenter.objects.none(), required=False
    )
    relation = forms.ChoiceField(
        label="Quais trabalhos da pessoa?", choices=[("", "Selecione a relação")] + list(Scope.Relation.choices), required=False
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company.objects.filter(
            organization=organization, is_active=True
        )
        sectors = Sector.objects.filter(
            organization=organization, is_active=True
        )
        self.fields["sector"].queryset = sectors
        self.fields["sector"].widget.queryset = sectors
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
        kwargs.setdefault("auto_id", "grant_%s")
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
        label="Novas mensagens nas minhas demandas", required=False, initial=True
    )
    notify_completion = forms.BooleanField(
        label="Conclusão das minhas demandas", required=False, initial=True
    )
