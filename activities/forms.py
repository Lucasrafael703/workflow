import datetime

from django import forms
from django.contrib.auth import get_user_model
from django.forms.utils import from_current_timezone
from django.urls import reverse
from django.utils.html import format_html

from core.models import Client, Company, CostCenter, Sector, Site, Tag
from core.sanitize import sanitize_description
from core.widgets import (
    ActivityPickerWidget,
    ClientPickerWidget,
    CompanyPickerWidget,
    CostCenterPickerWidget,
    PersonMultiPickerWidget,
    PersonPickerWidget,
    RichTextWidget,
    SectorPickerWidget,
    SitePickerWidget,
    TagPickerWidget,
)

from .models import Activity, ActivityPendency, MessageKind, ReturnReason, Task

User = get_user_model()


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def format_value(self, value):
        if value is None:
            return ""
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%dT%H:%M")
        return value


class SplitDateOptionalTimeWidget(forms.SplitDateTimeWidget):
    """Data obrigatória + hora opcional, lado a lado. Quando a hora fica em
    branco, `SplitDateOptionalTimeField.compress` assume 23:59 daquele dia —
    "prazo é tal dia" sem horário específico continua fazendo sentido."""

    def __init__(self, attrs=None):
        date_widget = forms.DateInput(attrs=attrs, format="%Y-%m-%d")
        date_widget.input_type = "date"
        time_widget = forms.TimeInput(attrs=attrs, format="%H:%M")
        time_widget.input_type = "time"
        forms.MultiWidget.__init__(self, (date_widget, time_widget), attrs)

    def decompress(self, value):
        if value:
            return [value.date(), value.time().replace(microsecond=0)]
        return [None, None]

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        return format_html('<div class="split-datetime-input">{}</div>', html)


class SplitDateOptionalTimeField(forms.MultiValueField):
    """Par (data, hora) que vira um único `datetime` — data obrigatória
    (quando o campo geral é preenchido), hora opcional com default 23:59."""

    widget = SplitDateOptionalTimeWidget

    def __init__(self, **kwargs):
        fields = (
            forms.DateField(required=False),
            forms.TimeField(required=False),
        )
        kwargs.setdefault("require_all_fields", False)
        super().__init__(fields=fields, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return None
        date_value, time_value = data_list
        if date_value in (None, ""):
            return None
        if time_value in (None, ""):
            time_value = datetime.time(23, 59)
        return from_current_timezone(datetime.datetime.combine(date_value, time_value))


class OrganizationScopedFormMixin:
    """Todo select só pode oferecer registros da própria organização."""

    def scope_querysets(
        self,
        organization,
        can_create_person=False,
        can_create_client=False,
        can_create_sector=False,
        can_create_company=False,
        can_create_site=False,
        can_create_cost_center=False,
    ):
        fields = self.fields
        if "owner" in fields:
            fields["owner"].queryset = User.objects.filter(
                profile__organization=organization, is_active=True
            ).order_by("first_name", "username")
            if isinstance(fields["owner"].widget, PersonPickerWidget):
                fields["owner"].widget.queryset = fields["owner"].queryset
                if can_create_person:
                    fields["owner"].widget.create_url = reverse("user-create")
        if "requested_by" in fields:
            fields["requested_by"].queryset = User.objects.filter(
                profile__organization=organization, is_active=True
            ).order_by("first_name", "username")
            if isinstance(fields["requested_by"].widget, PersonPickerWidget):
                fields["requested_by"].widget.queryset = fields["requested_by"].queryset
        if "client" in fields:
            fields["client"].queryset = Client.objects.filter(organization=organization, is_active=True)
            if isinstance(fields["client"].widget, ClientPickerWidget):
                fields["client"].widget.queryset = fields["client"].queryset
                if can_create_client:
                    fields["client"].widget.create_url = reverse("client-create")
        if "company" in fields:
            fields["company"].queryset = Company.objects.filter(organization=organization, is_active=True)
            if isinstance(fields["company"].widget, CompanyPickerWidget):
                fields["company"].widget.queryset = fields["company"].queryset
                if can_create_company:
                    fields["company"].widget.create_url = reverse("company-create")
        if "site" in fields:
            fields["site"].queryset = Site.objects.filter(organization=organization, is_active=True)
            if isinstance(fields["site"].widget, SitePickerWidget):
                fields["site"].widget.queryset = fields["site"].queryset
                if can_create_site:
                    fields["site"].widget.create_url = reverse("site-create")
        if "cost_center" in fields:
            fields["cost_center"].queryset = CostCenter.objects.filter(organization=organization, is_active=True)
            if isinstance(fields["cost_center"].widget, CostCenterPickerWidget):
                fields["cost_center"].widget.queryset = fields["cost_center"].queryset
                if can_create_cost_center:
                    fields["cost_center"].widget.create_url = reverse("costcenter-create")
        if "sector" in fields:
            fields["sector"].queryset = Sector.objects.filter(organization=organization, is_active=True)
            if isinstance(fields["sector"].widget, SectorPickerWidget):
                fields["sector"].widget.queryset = fields["sector"].queryset
                if can_create_sector:
                    fields["sector"].widget.create_url = reverse("sector-create")
        if "tags" in fields:
            queryset = Tag.objects.filter(organization=organization, is_active=True)
            fields["tags"].queryset = queryset
            if isinstance(fields["tags"].widget, TagPickerWidget):
                fields["tags"].widget.queryset = queryset


# Labels/help_texts compartilhados entre os 3 passos do wizard de criação e
# o formulário de edição — um único lugar para o texto de cada campo do
# Activity, independente de em qual tela ele aparece.
ACTIVITY_FIELD_LABELS = {
    "title": "O que precisa ser resolvido?",
    "client": "Cliente",
    "owner": "Responsável",
    "urgency": "Urgência",
    "sector": "Setor Responsável",
    "description": "Descrição",
    "internal_notes": "Observações internas",
    "company": "Empresa",
    "site": "Obra",
    "cost_center": "Centro de custo",
    "requested_by": "Solicitante",
    "address": "Endereço complementar",
    "tags": "Marcadores",
}
ACTIVITY_FIELD_HELP_TEXTS = {
    "title": "Descreva o resultado esperado, não a ação. Ex.: “Material disponível na obra”.",
    "client": "Quem solicitou o serviço.",
    "owner": "Quem responde pelo resultado até a resolução.",
    "sector": "Setor responsável por esta atividade.",
    "requested_by": "Alguém da própria organização que pediu informalmente — não é o cliente. Opcional.",
    "internal_notes": "Nunca aparece para o cliente; só para uso interno da equipe.",
    "address": "Endereço adicional, além do que já está no cadastro do cliente.",
}


class ActivityWizardStep1Form(OrganizationScopedFormMixin, forms.ModelForm):
    """Etapa 1 (Essencial) do wizard de nova atividade: o mínimo para existir
    como rascunho. Nada aqui é obrigatório no nível do form — a cobrança de
    título/responsável de verdade só acontece ao publicar
    (`ActivityService.publish_draft`), nunca ao simplesmente salvar o
    rascunho e avançar/sair."""

    requested_deadline = SplitDateOptionalTimeField(
        label="Prazo da solicitação",
        required=False,
        help_text="Quando quem pediu precisa da entrega. Sem horário, vale até o fim do dia.",
    )

    class Meta:
        model = Activity
        fields = ["title", "client", "site", "sector", "owner", "requested_deadline", "urgency"]
        labels = ACTIVITY_FIELD_LABELS
        help_texts = ACTIVITY_FIELD_HELP_TEXTS
        widgets = {
            "title": forms.TextInput(attrs={"autofocus": True, "placeholder": "Ex.: Material disponível na obra"}),
            "client": ClientPickerWidget(),
            "site": SitePickerWidget(),
            "sector": SectorPickerWidget(),
            "owner": PersonPickerWidget(),
            "urgency": forms.RadioSelect(),
        }

    def __init__(
        self,
        *args,
        organization=None,
        user=None,
        can_create_person=False,
        can_create_client=False,
        can_create_sector=False,
        can_create_site=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.scope_querysets(
            organization,
            can_create_person=can_create_person,
            can_create_client=can_create_client,
            can_create_sector=can_create_sector,
            can_create_site=can_create_site,
        )
        self.fields["client"].empty_label = None
        self.fields["owner"].empty_label = None
        if not self.is_bound and not self.initial.get("urgency"):
            self.fields["urgency"].initial = Activity.Urgency.MEDIA
        if user is not None and not self.is_bound and not self.instance.pk:
            self.fields["owner"].initial = user
        for optional in ("title", "client", "site", "sector", "owner", "requested_deadline", "urgency"):
            self.fields[optional].required = False


class ActivityWizardStep2Form(OrganizationScopedFormMixin, forms.ModelForm):
    """Etapa 2 (Contexto) do wizard: tudo opcional, todos os campos já
    salvos direto na mesma linha de rascunho criada na etapa 1."""

    class Meta:
        model = Activity
        fields = ["company", "cost_center", "requested_by", "address", "tags"]
        labels = ACTIVITY_FIELD_LABELS
        help_texts = ACTIVITY_FIELD_HELP_TEXTS
        widgets = {
            "company": CompanyPickerWidget(),
            "cost_center": CostCenterPickerWidget(),
            "requested_by": PersonPickerWidget(),
            "address": forms.TextInput(attrs={"placeholder": "Ex.: Bloco B, acesso lateral, portaria 2"}),
            "tags": TagPickerWidget(),
        }

    def __init__(
        self,
        *args,
        organization=None,
        can_create_company=False,
        can_create_cost_center=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.scope_querysets(
            organization,
            can_create_company=can_create_company,
            can_create_cost_center=can_create_cost_center,
        )
        self.fields["requested_by"].empty_label = None
        for optional in ("company", "cost_center", "requested_by", "address", "tags"):
            self.fields[optional].required = False


class ActivityWizardStep3Form(forms.ModelForm):
    """Etapa 3 (Detalhes) do wizard: descrição pública e observações
    internas — anexos são tratados fora deste form, via
    `ActivityAttachmentUploadView` já existente, apontando pro rascunho."""

    class Meta:
        model = Activity
        fields = ["description", "internal_notes"]
        labels = ACTIVITY_FIELD_LABELS
        help_texts = ACTIVITY_FIELD_HELP_TEXTS
        widgets = {
            "description": RichTextWidget(),
            "internal_notes": forms.Textarea(attrs={"placeholder": "Digite observações internas...", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False
        self.fields["internal_notes"].required = False

    def clean_description(self):
        return sanitize_description(self.cleaned_data.get("description"))


class ActivityMiniCreateForm(forms.Form):
    """Criação mínima de atividade dentro do popup aninhado do "+ Nova
    tarefa": só o título — dono é sempre quem está criando."""

    title = forms.CharField(
        label="O que precisa ser resolvido?",
        max_length=200,
        widget=forms.TextInput(attrs={"autofocus": True, "placeholder": "Ex.: Material disponível na obra"}),
    )


class ActivityEditForm(OrganizationScopedFormMixin, forms.ModelForm):
    requested_deadline = SplitDateOptionalTimeField(
        label="Prazo da solicitação",
        required=False,
        help_text="Quando quem pediu precisa da entrega. Sem horário, vale até o fim do dia.",
    )

    class Meta:
        model = Activity
        fields = [
            "client",
            "title",
            "urgency",
            "requested_deadline",
            "owner",
            "requested_by",
            "sector",
            "company",
            "site",
            "cost_center",
            "address",
            "tags",
            "description",
            "internal_notes",
        ]
        labels = ACTIVITY_FIELD_LABELS
        help_texts = ACTIVITY_FIELD_HELP_TEXTS
        widgets = {
            "client": ClientPickerWidget(),
            "owner": PersonPickerWidget(),
            "requested_by": PersonPickerWidget(),
            "urgency": forms.RadioSelect(),
            "description": RichTextWidget(),
            "sector": SectorPickerWidget(),
            "company": CompanyPickerWidget(),
            "site": SitePickerWidget(),
            "cost_center": CostCenterPickerWidget(),
            "tags": TagPickerWidget(),
        }

    def __init__(
        self,
        *args,
        organization=None,
        can_create_person=False,
        can_create_client=False,
        can_create_sector=False,
        can_create_company=False,
        can_create_site=False,
        can_create_cost_center=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.scope_querysets(
            organization,
            can_create_person=can_create_person,
            can_create_client=can_create_client,
            can_create_sector=can_create_sector,
            can_create_company=can_create_company,
            can_create_site=can_create_site,
            can_create_cost_center=can_create_cost_center,
        )
        self.fields["client"].required = False
        self.fields["client"].empty_label = None
        self.fields["owner"].empty_label = None
        self.fields["requested_by"].empty_label = None
        for optional in (
            "description",
            "internal_notes",
            "company",
            "site",
            "cost_center",
            "sector",
            "requested_by",
            "address",
            "requested_deadline",
            "tags",
            "urgency",
        ):
            self.fields[optional].required = False

    def clean_description(self):
        return sanitize_description(self.cleaned_data.get("description"))

    def clean_urgency(self):
        return self.cleaned_data.get("urgency") or Activity.Urgency.MEDIA


class ChangeOwnerForm(forms.Form):
    new_owner = forms.ModelChoiceField(
        queryset=User.objects.none(), label="Novo dono", widget=PersonPickerWidget()
    )

    def __init__(self, *args, organization=None, can_create_person=False, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = User.objects.filter(
            profile__organization=organization, is_active=True
        ).order_by("first_name", "username")
        self.fields["new_owner"].queryset = queryset
        self.fields["new_owner"].widget.queryset = queryset
        if can_create_person:
            self.fields["new_owner"].widget.create_url = reverse("user-create")


class ActivityDeadlineChangeForm(forms.Form):
    requested_deadline = forms.DateTimeField(
        label="Novo prazo solicitado", widget=DateTimeLocalInput(), required=False
    )


class TaskForm(OrganizationScopedFormMixin, forms.ModelForm):
    """Editar tarefa (doc 09 §81-84). O setor aparece só para contexto — sua
    edição de fato tem serviço próprio (movimentação com histórico), então
    `TaskEditView.form_valid` descarta esse campo antes de chamar
    `TaskService.update_task`."""

    class Meta:
        model = Task
        fields = ["title", "sector", "requested_deadline", "tags", "description", "depends_on"]
        labels = {
            "title": "O que precisa ser feito?",
            "sector": "Setor responsável",
            "requested_deadline": "Prazo solicitado",
            "description": "Descrição",
            "depends_on": "Depende de",
            "tags": "Marcadores",
        }
        widgets = {
            "title": forms.TextInput(attrs={"autofocus": True, "placeholder": "Ex.: Realizar cotação"}),
            "sector": SectorPickerWidget(),
            "description": RichTextWidget(),
            "requested_deadline": DateTimeLocalInput(),
            "tags": TagPickerWidget(),
        }

    def __init__(self, *args, organization=None, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_querysets(organization)
        for optional in ("description", "requested_deadline", "depends_on", "tags"):
            self.fields[optional].required = False

        siblings = Task.objects.none()
        if activity is not None:
            siblings = activity.tasks.exclude(status=Task.Status.CANCELADA)
            if self.instance.pk:
                siblings = siblings.exclude(pk=self.instance.pk)
        self.fields["depends_on"].queryset = siblings
        self.fields["depends_on"].empty_label = "Nenhuma"

    def clean_description(self):
        return sanitize_description(self.cleaned_data.get("description"))


class TaskQuickCreateForm(OrganizationScopedFormMixin, forms.ModelForm):
    """Popup "+ Adicionar tarefa" (Regra 12): título e prazo à vista, descrição
    opcional escondida até a pessoa abrir. O setor vem pré-preenchido com o
    "Grupo designado" da atividade quando houver, mas continua visível e
    editável — e a busca de responsável nunca se restringe a um setor, para
    ter o mesmo comportamento em qualquer ponto de entrada (Regra: um único
    padrão de tela de "Nova tarefa")."""

    responsavel = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Responsável pela tarefa",
        required=True,
        widget=PersonPickerWidget(
            placeholder="Buscar responsável...",
            selection_label="Selecionar responsável...",
        ),
    )
    participantes = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        label="Participantes",
        required=False,
        widget=PersonMultiPickerWidget(),
    )

    class Meta:
        model = Task
        fields = ["title", "sector", "requested_deadline", "tags", "description"]
        labels = {
            "title": "Título da tarefa",
            "sector": "Setor responsável",
            "requested_deadline": "Prazo",
            "description": "Descrição",
            "tags": "Marcadores",
        }
        help_texts = {
            "title": "Use #marcador e @usuario no título para preenchê-los automaticamente.",
        }
        widgets = {
            "title": forms.TextInput(attrs={"autofocus": True, "placeholder": "Ex.: Realizar cotação"}),
            "sector": SectorPickerWidget(),
            "description": RichTextWidget(),
            "requested_deadline": DateTimeLocalInput(),
            "tags": TagPickerWidget(),
        }

    def __init__(self, *args, organization=None, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_querysets(organization)
        self.order_fields(["title", "sector", "responsavel", "participantes", "requested_deadline", "tags", "description"])
        self.fields["description"].required = False
        self.fields["requested_deadline"].required = False
        self.fields["tags"].required = False
        self.fields["sector"].required = True
        if activity is not None and activity.sector_id and not self.is_bound:
            self.fields["sector"].initial = activity.sector_id
        if organization is not None:
            people = User.objects.filter(
                profile__organization=organization, is_active=True
            ).order_by("first_name", "username")
            self.fields["responsavel"].queryset = people
            self.fields["participantes"].queryset = people
        self.fields["responsavel"].widget.queryset = self.fields["responsavel"].queryset
        self.fields["participantes"].widget.queryset = self.fields["participantes"].queryset

    def clean_description(self):
        return sanitize_description(self.cleaned_data.get("description"))

    def clean(self):
        cleaned_data = super().clean()
        responsavel = cleaned_data.get("responsavel")
        participantes = cleaned_data.get("participantes")
        if responsavel is not None and participantes:
            cleaned_data["participantes"] = participantes.exclude(pk=responsavel.pk)
        return cleaned_data


class TaskQuickCreateStandaloneForm(TaskQuickCreateForm):
    """Variante do popup "+ Adicionar tarefa" acessível fora do contexto de
    uma atividade já aberta (botão "+ Nova tarefa" em Minhas tarefas): ganha
    um campo `activity` real, resolvido por busca/criação no
    `ActivityPickerWidget`, em vez de vir fixo da URL."""

    # Mesmo conjunto de `ActivitySearchView.OPEN_STATUSES`: só atividades
    # ainda não encerradas fazem sentido como destino de uma tarefa nova.
    OPEN_ACTIVITY_STATUSES = [
        Activity.Status.ABERTA,
        Activity.Status.EM_ANDAMENTO,
        Activity.Status.BLOQUEADA,
        Activity.Status.PENDENTE,
    ]

    activity = forms.ModelChoiceField(
        queryset=Activity.objects.none(), label="Atividade", widget=ActivityPickerWidget()
    )

    def __init__(self, *args, organization=None, can_create_activity=False, **kwargs):
        # A atividade só é conhecida depois de escolhida no próprio popup,
        # então nunca há um `activity` fixo para herdar o setor dele.
        super().__init__(*args, organization=organization, activity=None, **kwargs)
        self.order_fields(["activity", "title", "sector", "responsavel", "participantes", "requested_deadline", "tags", "description"])
        queryset = Activity.objects.filter(organization=organization, status__in=self.OPEN_ACTIVITY_STATUSES)
        self.fields["activity"].queryset = queryset
        self.fields["activity"].widget.queryset = queryset
        if can_create_activity:
            self.fields["activity"].widget.create_url = reverse("activity-mini-create")


class ActivityAttachmentForm(forms.Form):
    """Upload de anexo (Regra 13): o arquivo vai para uma pasta própria da
    atividade, nomeada pelo código gerado automaticamente."""

    file = forms.FileField(label="Arquivo")


class TaskReturnForm(forms.Form):
    """Devolução: motivo sempre obrigatório (Regras 02 §36)."""

    to_sector = forms.ModelChoiceField(queryset=Sector.objects.none(), label="Devolver para")
    reason = forms.ModelChoiceField(queryset=ReturnReason.objects.none(), label="Motivo")
    observation = forms.CharField(
        label="Observação", required=False, widget=forms.Textarea(attrs={"rows": 3, "data-mention": "1"})
    )

    def __init__(self, *args, organization=None, task=None, **kwargs):
        super().__init__(*args, **kwargs)
        sectors = Sector.objects.filter(organization=organization, is_active=True)
        if task is not None:
            # Destinos válidos: setores por onde a tarefa já passou (Regras 02 §35),
            # nunca uma lista solta com todos os setores (doc 09 §116).
            visited = list(
                task.sector_transfers.values_list("from_sector_id", flat=True)
            )
            if visited:
                sectors = sectors.filter(pk__in=[s for s in visited if s])
            sectors = sectors.exclude(pk=task.sector_id)
        self.fields["to_sector"].queryset = sectors
        self.fields["reason"].queryset = ReturnReason.objects.filter(
            organization=organization, is_active=True
        )


class AssignmentRejectForm(forms.Form):
    """Recusa de atribuição: motivo sempre obrigatório, mesmo princípio da devolução."""

    reason = forms.ModelChoiceField(queryset=ReturnReason.objects.none(), label="Motivo")
    observation = forms.CharField(
        label="Observação", required=False, widget=forms.Textarea(attrs={"rows": 3, "data-mention": "1"})
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reason"].queryset = ReturnReason.objects.filter(
            organization=organization, is_active=True
        )


class TaskBlockForm(forms.Form):
    reason = forms.CharField(label="Motivo do bloqueio", max_length=255)
    observation = forms.CharField(
        label="Observação", required=False, widget=forms.Textarea(attrs={"rows": 3, "data-mention": "1"})
    )


class MoveSectorForm(forms.Form):
    to_sector = forms.ModelChoiceField(queryset=Sector.objects.none(), label="Enviar para o setor")
    note = forms.CharField(label="Observação", required=False, max_length=255)

    def __init__(self, *args, organization=None, task=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Sector.objects.filter(organization=organization, is_active=True)
        if task is not None:
            queryset = queryset.exclude(pk=task.sector_id)
        self.fields["to_sector"].queryset = queryset


class ExecutorForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(), label="Participante", widget=PersonPickerWidget()
    )

    def __init__(self, *args, organization=None, can_create_person=False, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = User.objects.filter(
            profile__organization=organization, is_active=True
        ).order_by("first_name", "username")
        self.fields["user"].queryset = queryset
        self.fields["user"].widget.queryset = queryset
        if can_create_person:
            self.fields["user"].widget.create_url = reverse("user-create")


class TaskChangeResponsavelForm(forms.Form):
    new_responsavel = forms.ModelChoiceField(
        queryset=User.objects.none(), label="Novo responsável", widget=PersonPickerWidget()
    )

    def __init__(self, *args, organization=None, can_create_person=False, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = User.objects.filter(
            profile__organization=organization, is_active=True
        ).order_by("first_name", "username")
        self.fields["new_responsavel"].queryset = queryset
        self.fields["new_responsavel"].widget.queryset = queryset
        if can_create_person:
            self.fields["new_responsavel"].widget.create_url = reverse("user-create")


class DeadlineProposalForm(forms.Form):
    proposed_deadline = forms.DateTimeField(label="Novo prazo", widget=DateTimeLocalInput())


class ConflictResolutionForm(forms.Form):
    resolution_note = forms.CharField(
        label="Decisão", widget=forms.Textarea(attrs={"rows": 3, "data-mention": "1"}),
        help_text="Registre o que foi decidido — o conflito precisa terminar em decisão (Regras 03 §66).",
    )


class ManualTimeForm(forms.Form):
    """Apropriação posterior de tempo (Regras 04 §110-113)."""

    started_at = forms.DateTimeField(label="Início", widget=DateTimeLocalInput())
    ended_at = forms.DateTimeField(label="Fim", widget=DateTimeLocalInput())


class MessageForm(forms.Form):
    body = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Escreva uma mensagem… use @ para mencionar alguém",
                "data-mention": "1",
            }
        ),
    )
    kind = forms.ChoiceField(
        choices=MessageKind.choices, initial=MessageKind.NORMAL, required=False, label="Tipo"
    )


class ReorderForm(forms.Form):
    """Reordenação da fila; o motivo é pedido depois do movimento (doc 09 §95)."""

    new_position = forms.IntegerField(min_value=1, label="Nova posição")
    reason = forms.CharField(label="Motivo da mudança", required=False, max_length=255)


class CancelForm(forms.Form):
    reason = forms.CharField(label="Motivo", widget=forms.Textarea(attrs={"rows": 3, "data-mention": "1"}))


class ActivityFinalizeForm(forms.Form):
    """Popup único de finalização: um resultado explícito, sempre com
    comentário — no lugar de "Concluir" e "Cancelar" em ações separadas."""

    outcome = forms.ChoiceField(
        choices=Activity.CompletionOutcome.choices,
        label="Resultado da finalização",
        widget=forms.RadioSelect,
    )
    comment = forms.CharField(
        label="Comentário de finalização",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "maxlength": 1000,
                "placeholder": "Descreva o resultado, o que foi realizado, observações finais, próximos passos…",
                "data-mention": "1",
            }
        ),
    )

    def clean_comment(self):
        comment = (self.cleaned_data.get("comment") or "").strip()
        if not comment:
            raise forms.ValidationError("Descreva o resultado da finalização.")
        return comment


class ActivityPendingForm(forms.Form):
    """Popup de "Definir como pendente": motivo, comentário sempre
    obrigatório e, só para os motivos que pedem aprovação do gestor, um
    prazo obrigatório para essa decisão."""

    reason = forms.ChoiceField(choices=ActivityPendency.Reason.choices, label="Motivo da pendência")
    comment = forms.CharField(
        label="Comentário",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "maxlength": 1000,
                "placeholder": "Descreva o motivo da pendência e o que já foi feito.",
                "data-mention": "1",
            }
        ),
    )
    decision_deadline = forms.DateTimeField(
        label="Prazo para decisão do gestor", required=False, widget=DateTimeLocalInput
    )
    notify_client = forms.BooleanField(
        label="Enviar e-mail para o cliente solicitando as informações pendentes", required=False
    )

    def clean_comment(self):
        comment = (self.cleaned_data.get("comment") or "").strip()
        if not comment:
            raise forms.ValidationError("O comentário é obrigatório.")
        return comment

    def clean(self):
        cleaned = super().clean()
        reason = cleaned.get("reason")
        deadline = cleaned.get("decision_deadline")
        if reason in ActivityPendency.APPROVAL_REASONS and not deadline:
            self.add_error("decision_deadline", "Informe o prazo para o gestor decidir.")
        return cleaned


class ActivityApprovePendencyForm(forms.Form):
    """Popup de aprovação: comentário opcional — a decisão em si é o próprio
    clique em "Aprovar", já protegido por `ATIVIDADE_APROVAR_PENDENCIA`."""

    comment = forms.CharField(
        label="Comentário (opcional)",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "maxlength": 1000,
                "placeholder": "Observações da aprovação, se houver.",
                "data-mention": "1",
            }
        ),
    )
