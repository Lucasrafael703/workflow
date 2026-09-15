from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .models import Company, CostCenter, Sector, Site

User = get_user_model()


class SectorForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=150)
    description = forms.CharField(label="Descrição", max_length=255, required=False)


class CompanyForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=150)
    document = forms.CharField(label="CNPJ/CPF", max_length=20, required=False)


class SiteForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=150)
    company = forms.ModelChoiceField(
        label="Empresa", queryset=Company.objects.none(), required=False
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company.objects.filter(
            organization=organization, is_active=True
        )


class CostCenterForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=150)
    site = forms.ModelChoiceField(label="Obra", queryset=Site.objects.none(), required=False)

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["site"].queryset = Site.objects.filter(
            organization=organization, is_active=True
        )


class ReturnReasonForm(forms.Form):
    name = forms.CharField(label="Motivo", max_length=150)


class UserForm(forms.Form):
    """Cadastro de usuário (doc 09 §210-214).

    "Setores em que atua" fica separado de "Perfis de acesso": participar de um
    setor não concede permissão (Regras 05 §25-27).
    """

    first_name = forms.CharField(label="Nome", max_length=150)
    email = forms.EmailField(label="E-mail")
    username = forms.CharField(label="Usuário", max_length=150)
    sectors = forms.ModelMultipleChoiceField(
        label="Setores em que atua",
        queryset=Sector.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    groups = forms.ModelMultipleChoiceField(
        label="Perfis de acesso",
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    is_active = forms.BooleanField(label="Ativo", required=False, initial=True)

    def __init__(self, *args, organization=None, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.fields["sectors"].queryset = Sector.objects.filter(
            organization=organization, is_active=True
        )
        if instance is not None and not self.is_bound:
            self.fields["first_name"].initial = instance.first_name
            self.fields["email"].initial = instance.email
            self.fields["username"].initial = instance.username
            self.fields["is_active"].initial = instance.is_active
            self.fields["groups"].initial = instance.groups.all()
            self.fields["sectors"].initial = Sector.objects.filter(
                user_memberships__user=instance, user_memberships__removed_at__isnull=True
            )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        queryset = User.objects.filter(username__iexact=username)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Já existe um usuário com este nome de usuário.")
        return username


class ProfileGroupForm(forms.Form):
    """Perfil de acesso = conjunto reutilizável de ações (Regras 05 §32-34)."""

    name = forms.CharField(label="Nome do perfil", max_length=150)
    permissions = forms.MultipleChoiceField(
        label="Ações", required=False, widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, *args, permission_choices=(), instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.fields["permissions"].choices = permission_choices
        if instance is not None and not self.is_bound:
            self.fields["name"].initial = instance.name
            self.fields["permissions"].initial = [
                f"{p.content_type.app_label}.{p.codename}" for p in instance.permissions.all()
            ]


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
