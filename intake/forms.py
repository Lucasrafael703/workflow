"""Formulários da Caixa de Entrada.

São `forms.Form` simples e de propósito não herdam de `ActivityEditorForm`: o
editor de atividade está em refatoração. Reaproveitam só as peças estáveis: o
mixin que limita cada seleção à organização, o campo de data+hora opcional e os
seletores de `core.widgets`. Mantenha os ids padrão (`id_client`, `id_site`):
o filtro cliente → obra do seletor depende deles.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from activities.forms import OrganizationScopedFormMixin, SplitDateOptionalTimeField
from activities.models import Activity
from core.models import Client, Company, Sector, Site
from core.widgets import (
    ClientPickerWidget,
    CompanyPickerWidget,
    PersonPickerWidget,
    SectorPickerWidget,
    SitePickerWidget,
)

from .models import IntakeItem
from .services import MAX_CONTENT_LENGTH, MAX_NOTE_LENGTH, MAX_SENDER_NAME_LENGTH, MAX_SUBJECT_LENGTH

User = get_user_model()

# O registro manual não oferece "Formulário": esse canal ainda não existe.
MANUAL_SOURCES = [
    (IntakeItem.Source.EMAIL, IntakeItem.Source.EMAIL.label),
    (IntakeItem.Source.TEAMS, IntakeItem.Source.TEAMS.label),
    (IntakeItem.Source.USUARIO, IntakeItem.Source.USUARIO.label),
]


def _text(widget=forms.TextInput, **attrs):
    """Campo de texto com o visual dos campos da janela de atividade."""
    return widget(attrs={"class": "activity-input", **attrs})


def _client_field():
    return forms.ModelChoiceField(
        queryset=Client.objects.none(), required=False, label="Cliente", widget=ClientPickerWidget(icon="building")
    )


def _site_field():
    return forms.ModelChoiceField(
        queryset=Site.objects.none(), required=False, label="Obra",
        widget=SitePickerWidget(icon="hardhat", filter_field_id="id_client", filter_param="client"),
    )


def _sector_field(label):
    return forms.ModelChoiceField(
        queryset=Sector.objects.none(), required=False, label=label, widget=SectorPickerWidget(icon="users")
    )


def _check_site_belongs_to_client(form, cleaned):
    client, site = cleaned.get("client"), cleaned.get("site")
    if client and site and site.client_id not in (None, client.pk):
        form.add_error("site", "Esta obra pertence a outro cliente. Escolha uma obra de quem foi selecionado.")


class IntakeCaptureForm(forms.Form):
    """Registrar uma solicitação: cola o texto e diz de quem veio."""

    source = forms.ChoiceField(label="De onde veio?", choices=MANUAL_SOURCES, initial=IntakeItem.Source.EMAIL)
    sender_name = forms.CharField(
        label="Quem pediu?", max_length=MAX_SENDER_NAME_LENGTH, required=False,
        widget=_text(placeholder="Nome de quem enviou"),
    )
    sender_email = forms.EmailField(
        label="E-mail de quem pediu", required=False, widget=_text(forms.EmailInput, placeholder="nome@empresa.com.br"),
    )
    subject = forms.CharField(
        label="Assunto", max_length=MAX_SUBJECT_LENGTH, required=False,
        widget=_text(placeholder="Assunto do e-mail, se houver"),
    )
    raw_content = forms.CharField(
        label="Texto da solicitação", max_length=MAX_CONTENT_LENGTH,
        help_text="Cole aqui o e-mail ou a mensagem, do jeito que chegou. A LPS tenta identificar cliente, obra e prazo.",
        widget=forms.Textarea(attrs={"rows": 9, "placeholder": "Cole o texto aqui…"}),
        error_messages={"required": "Cole o texto da solicitação."},
    )
    received_at = forms.DateTimeField(
        label="Recebida em", required=False,
        help_text="Deixe como está se chegou agora; ajuste se o pedido chegou antes.",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial.setdefault("received_at", timezone.localtime().replace(second=0, microsecond=0))

    def service_kwargs(self):
        data = self.cleaned_data
        return dict(
            raw_content=data["raw_content"],
            subject=data["subject"],
            sender_name=data["sender_name"],
            sender_email=data["sender_email"],
            source=data["source"],
            received_at=data["received_at"],
        )


class IntakeEditForm(OrganizationScopedFormMixin, forms.Form):
    """Corrigir o que a LPS sugeriu, sem sair da Caixa de Entrada."""

    title = forms.CharField(
        label="Nome da atividade", max_length=200, required=False,
        help_text="Descreva a entrega esperada. Ex.: Orçamento do gerador aprovado.",
        widget=_text(),
    )
    client = _client_field()
    site = _site_field()
    sector = _sector_field("Setor responsável")
    deadline = SplitDateOptionalTimeField(
        label="Prazo", required=False, help_text="Sem horário, vale até o fim do dia."
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_querysets(organization)

    @classmethod
    def initial_from(cls, item):
        return {
            "title": item.suggested_title,
            "client": item.suggested_client,
            "site": item.suggested_site,
            "sector": item.suggested_sector,
            "deadline": item.suggested_deadline,
        }

    def clean(self):
        cleaned = super().clean()
        _check_site_belongs_to_client(self, cleaned)
        return cleaned

    def service_kwargs(self):
        data = self.cleaned_data
        return dict(
            suggested_title=data["title"],
            suggested_client=data["client"],
            suggested_site=data["site"],
            suggested_sector=data["sector"],
            suggested_deadline=data["deadline"],
        )


class IntakeConvertForm(OrganizationScopedFormMixin, forms.Form):
    """Criar a demanda: só o que a atividade exige, já preenchido pelo que foi entendido."""

    title = forms.CharField(
        label="Nome da atividade", max_length=200,
        help_text="Descreva a entrega esperada. Ex.: Orçamento do gerador aprovado.",
        widget=_text(autofocus=True),
    )
    client = _client_field()
    site = _site_field()
    sector = _sector_field("Setor responsável")
    owner = forms.ModelChoiceField(
        queryset=User.objects.none(), label="Atribuído a",
        help_text="Essa pessoa responde pela entrega e acompanha as tarefas.",
        widget=PersonPickerWidget(icon="user", selection_label="Buscar pessoa..."),
        empty_label=None,
    )
    requested_deadline = SplitDateOptionalTimeField(
        label="Prazo de vencimento", required=False, help_text="Sem horário, vale até o fim do dia."
    )
    # Em "Mais detalhes":
    urgency = forms.ChoiceField(
        label="Urgência", choices=Activity.Urgency.choices, initial=Activity.Urgency.MEDIA, required=False,
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.none(), required=False, label="Organização",
        help_text="Empresa do grupo que presta o serviço. Necessária para aplicar um processo depois.",
        widget=CompanyPickerWidget(icon="building", empty_label="Selecionar organização"),
    )
    external_requester = forms.CharField(
        label="Solicitante (externo)", max_length=150, required=False,
        help_text="Pessoa que pediu fora da organização.", widget=_text(placeholder="Nome do solicitante"),
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_querysets(organization)

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise forms.ValidationError("Informe o nome da atividade.")
        return title

    def clean_owner(self):
        owner = self.cleaned_data.get("owner")
        if not owner:
            raise forms.ValidationError("Escolha quem fica com a atividade.")
        return owner

    def clean_sector(self):
        sector = self.cleaned_data.get("sector")
        if not sector:
            raise forms.ValidationError("Escolha o setor responsável.")
        return sector

    def clean_urgency(self):
        return self.cleaned_data.get("urgency") or Activity.Urgency.MEDIA

    def clean_external_requester(self):
        return (self.cleaned_data.get("external_requester") or "").strip()

    def clean(self):
        cleaned = super().clean()
        _check_site_belongs_to_client(self, cleaned)
        return cleaned

    def service_kwargs(self):
        data = self.cleaned_data
        return dict(
            title=data["title"],
            owner=data["owner"],
            sector=data["sector"],
            client=data["client"],
            site=data["site"],
            company=data["company"],
            requested_deadline=data["requested_deadline"],
            urgency=data["urgency"],
            external_requester=data["external_requester"],
        )


class IntakeIgnoreForm(forms.Form):
    reason = forms.CharField(
        label="Motivo", max_length=MAX_NOTE_LENGTH, required=False,
        help_text="Opcional. Ajuda a lembrar por que esta solicitação não virou trabalho.",
        widget=_text(placeholder="Ex.: duplicada, não é conosco, já resolvido", autofocus=True),
    )
