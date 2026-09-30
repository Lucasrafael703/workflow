import datetime

from django import forms
from django.contrib.auth import get_user_model
from django.forms.utils import from_current_timezone, to_current_timezone
from django.urls import reverse
from django.utils import timezone
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

from .models import Activity, ActivityPendency, MessageKind, ReturnReason, Task, WorkSession

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
            value = to_current_timezone(value)
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


# Labels compartilhados pelo editor único e pelos POSTs legados de rascunho.
ACTIVITY_FIELD_LABELS = {
    "title": "Nome da atividade",
    "client": "Para qual cliente?",
    "owner": "Quem acompanha esta atividade?",
    "urgency": "Qual é a urgência?",
    "sector": "Qual equipe cuida desta atividade?",
    "description": "O que precisa ser entregue?",
    "internal_notes": "Anotações para a equipe",
    "company": "Empresa que presta o serviço",
    "site": "Em qual obra?",
    "cost_center": "Centro de custo",
    "requested_by": "Quem pediu dentro da equipe?",
    "address": "Local ou complemento do endereço",
    "tags": "Marcadores para organizar",
}
ACTIVITY_FIELD_HELP_TEXTS = {
    "title": "Descreva a entrega esperada. Ex.: Orçamento do gerador aprovado.",
    "client": "Escolha o cliente que vai receber a entrega.",
    "owner": "Essa pessoa responde pela entrega e acompanha as tarefas.",
    "sector": "Escolha o setor que vai organizar o trabalho.",
    "urgency": "Indique o quanto esta entrega precisa de atenção.",
    "description": "Explique o resultado esperado e o que a equipe precisa saber para trabalhar.",
    "company": "Escolha a empresa da sua organização responsável pelo serviço.",
    "site": "Selecione a obra relacionada, se houver.",
    "cost_center": "Use o grupo que sua empresa utiliza para acompanhar os custos deste trabalho.",
    "requested_by": "Selecione a pessoa da sua equipe que fez o pedido, se houver.",
    "internal_notes": "Espaço para informações de uso interno da equipe.",
    "address": "Acrescente bloco, portaria ou outro detalhe que ajude a encontrar o local.",
    "tags": "Escolha palavras-chave para encontrar e agrupar esta atividade depois.",
}


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


class ActivityFilesInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ActivityFilesField(forms.FileField):
    widget = ActivityFilesInput

    def clean(self, data, initial=None):
        if not data:
            return []
        values = data if isinstance(data, (list, tuple)) else [data]
        return [super(ActivityFilesField, self).clean(value, initial) for value in values]


class ActivityEditorForm(ActivityEditForm):
    """Creation and editing share field order, widgets and validation."""

    files = ActivityFilesField(label="Adicionar arquivos", required=False)

    def __init__(self, *args, user=None, drafting=False, can_change_owner=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].widget.attrs.update(placeholder="Ex.: Material disponível na obra", autofocus=True)
        self.fields["internal_notes"].widget.attrs["rows"] = 3
        self.fields["owner"].disabled = not can_change_owner
        if not can_change_owner:
            self.fields["owner"].help_text = "A transferência de responsabilidade exige permissão específica."
        if drafting:
            self.fields["title"].required = False
            self.fields["owner"].required = False
            if not self.is_bound and not self.instance.pk:
                self.initial["owner"] = user
            if self.initial.get("title") == Activity.DRAFT_TITLE_PLACEHOLDER:
                self.initial["title"] = ""

    @property
    def essential_fields(self):
        return [self[name] for name in ("title", "owner", "sector", "requested_deadline", "urgency")]

    @property
    def context_fields(self):
        return [self[name] for name in ("client", "site", "company", "cost_center", "requested_by", "address", "tags")]

    @property
    def context_expanded(self):
        return any(field.errors or field.value() for field in self.context_fields)


class ChangeOwnerForm(forms.Form):
    new_owner = forms.ModelChoiceField(
        queryset=User.objects.none(), label="Quem vai acompanhar esta atividade?", widget=PersonPickerWidget(),
        help_text="A pessoa escolhida passa a responder pela entrega e pelo acompanhamento das tarefas."
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
        label="Nova data para a entrega", widget=DateTimeLocalInput(), required=False,
        help_text="Informe até quando a atividade precisa ficar pronta. Deixe em branco para retirar o prazo."
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
            "description": "Instruções para fazer a tarefa",
            "depends_on": "Qual tarefa precisa terminar antes desta?",
            "tags": "Marcadores",
        }
        help_texts = {
            "title": "Comece com uma ação. Ex.: Conferir os preços da planilha.",
            "sector": "Equipe que recebe esta tarefa. Para trocar de equipe, use Enviar para outro setor na tarefa.",
            "requested_deadline": "Data e horário em que você precisa da entrega.",
            "description": "Explique o que fazer e como saber que o trabalho está pronto.",
            "depends_on": "Se escolher uma tarefa, esta só poderá começar depois que ela for concluída.",
            "tags": "Use palavras-chave para organizar e encontrar a tarefa depois.",
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
        help_text="Pessoa que acompanha esta tarefa até a conclusão.",
        required=True,
        widget=PersonPickerWidget(
            placeholder="Buscar responsável...",
            selection_label="Selecionar responsável...",
        ),
    )
    participantes = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        label="Participantes",
        help_text="Outras pessoas que vão ajudar a executar a tarefa. É opcional.",
        required=False,
        widget=PersonMultiPickerWidget(),
    )

    class Meta:
        model = Task
        fields = ["title", "sector", "requested_deadline", "tags", "description"]
        labels = {
            "title": "O que precisa ser feito?",
            "sector": "Setor responsável",
            "requested_deadline": "Prazo solicitado",
            "description": "Instruções para fazer a tarefa",
            "tags": "Marcadores",
        }
        help_texts = {
            "title": "Escreva uma ação clara. Ex.: Conferir os preços da planilha.",
            "sector": "Equipe que receberá a tarefa na sua fila de trabalho.",
            "requested_deadline": "Data e horário em que você precisa da entrega. Pode ser definido depois.",
            "description": "Explique os passos, cuidados ou informações de apoio.",
            "tags": "Palavras-chave para organizar e encontrar a tarefa depois.",
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
        queryset=Activity.objects.none(), label="De qual atividade esta tarefa faz parte?", widget=ActivityPickerWidget(),
        help_text="A atividade é o resultado maior; esta tarefa é um dos passos para chegar lá.",
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

    to_sector = forms.ModelChoiceField(queryset=Sector.objects.none(), label="Setor que receberá a devolução")
    reason = forms.ModelChoiceField(queryset=ReturnReason.objects.none(), label="Por que a tarefa precisa voltar?")
    observation = forms.CharField(
        label="O que precisa ser corrigido?", required=False, widget=forms.Textarea(attrs={"rows": 3, "data-mention": "1"}),
        help_text="Explique o ajuste necessário para que o setor saiba como continuar.",
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

    reason = forms.ModelChoiceField(queryset=ReturnReason.objects.none(), label="Por que você não pode aceitar?")
    observation = forms.CharField(
        label="Explique o motivo, se necessário", required=False, widget=forms.Textarea(attrs={"rows": 3, "data-mention": "1"})
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reason"].queryset = ReturnReason.objects.filter(
            organization=organization, is_active=True
        )


class TaskBlockForm(forms.Form):
    reason = forms.CharField(label="O que impede a tarefa de continuar?", max_length=255,
                            help_text="Ex.: Aguardando a aprovação do cliente.")
    observation = forms.CharField(
        label="O que falta para liberar a tarefa?", required=False, widget=forms.Textarea(attrs={"rows": 3, "data-mention": "1"})
    )


class MoveSectorForm(forms.Form):
    to_sector = forms.ModelChoiceField(queryset=Sector.objects.none(), label="Enviar para o setor")
    note = forms.CharField(label="Orientação para o próximo setor", required=False, max_length=255,
                          help_text="Explique o que a equipe precisa fazer ao receber a tarefa.")

    def __init__(self, *args, organization=None, task=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Sector.objects.filter(organization=organization, is_active=True)
        if task is not None:
            queryset = queryset.exclude(pk=task.sector_id)
        self.fields["to_sector"].queryset = queryset


class ExecutorForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(), label="Quem vai ajudar nesta tarefa?", widget=PersonPickerWidget()
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
        queryset=User.objects.none(), label="Quem será o novo responsável?", widget=PersonPickerWidget(),
        help_text="Escolha a pessoa que acompanhará a tarefa até a conclusão.",
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
    proposed_deadline = forms.DateTimeField(label="Quando você consegue entregar?", widget=DateTimeLocalInput(),
                                          help_text="Informe a data e o horário propostos. O responsável pela atividade receberá a proposta para decidir.")


class ConflictResolutionForm(forms.Form):
    resolution_note = forms.CharField(
        label="O que foi combinado para resolver o prazo?", widget=forms.Textarea(attrs={"rows": 3, "data-mention": "1"}),
        help_text="Explique a decisão e o próximo passo para as pessoas envolvidas.",
    )


class ManualTimeForm(forms.Form):
    """Apropriação posterior de tempo (Regras 04 §110-113)."""

    started_at = forms.DateTimeField(label="Quando você começou a trabalhar?", widget=DateTimeLocalInput())
    ended_at = forms.DateTimeField(label="Quando você parou?", widget=DateTimeLocalInput(),
                                   help_text="Informe um período já trabalhado. O sistema calcula a duração entre o início e o fim.")


class RetroactiveWorkForm(forms.Form):
    """"Já realizei este trabalho": a pessoa esqueceu de iniciar a tarefa, já a
    fez, e informa quando (data + hora de início e de fim). Sem jargão na tela.

    O formulário só valida o formato e monta `started_at`/`ended_at` no fuso
    do usuário; quem decide (permissão, status, limites, justificativa) é
    `TaskService.register_completed_work`.
    """

    date = forms.DateField(
        label="Data",
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    start_time = forms.TimeField(
        label="Comecei às", widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
    )
    end_time = forms.TimeField(
        label="Terminei às",
        initial=lambda: timezone.localtime().time().replace(second=0, microsecond=0),
        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
    )
    reason = forms.ChoiceField(
        label="Motivo",
        choices=WorkSession.ManualReason.choices,
        initial=WorkSession.ManualReason.ESQUECI_INICIAR,
        widget=forms.RadioSelect,
    )
    note = forms.CharField(
        label="Comentário",
        required=False,
        max_length=255,
        widget=forms.Textarea(attrs={"rows": 2, "maxlength": 255, "data-mention": "1"}),
    )

    def clean(self):
        cleaned = super().clean()
        day, start, end = cleaned.get("date"), cleaned.get("start_time"), cleaned.get("end_time")
        if day and day > timezone.localdate():
            self.add_error("date", "A data não pode ser futura.")
        elif day and start and end:
            if end <= start:
                self.add_error("end_time", "A hora em que você terminou precisa ser depois da hora em que começou.")
            else:
                zone = timezone.get_current_timezone()
                cleaned["started_at"] = timezone.make_aware(datetime.datetime.combine(day, start), zone)
                cleaned["ended_at"] = timezone.make_aware(datetime.datetime.combine(day, end), zone)
        if cleaned.get("reason") == WorkSession.ManualReason.OUTRO and not (cleaned.get("note") or "").strip():
            self.add_error("note", "Explique o motivo.")
        return cleaned


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
        label="Como esta atividade terminou?",
        widget=forms.RadioSelect,
    )
    comment = forms.CharField(
        label="Explique o resultado",
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

    reason = forms.ChoiceField(choices=ActivityPendency.Reason.choices, label="O que está impedindo a entrega?")
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
        label="Até quando o gestor precisa decidir?", required=False, widget=DateTimeLocalInput
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


class ProcessApplyForm(forms.Form):
    """Aplicar um processo publicado a uma atividade (Regras 12 §20).

    Um único formulário, em quatro passos na tela: processo → responsáveis →
    inputs iniciais → confirmação. Os campos de responsável (`responsavel_<etapa>`)
    e de input (`input_<id>`, `input_received_<id>`) existem para todas as
    versões elegíveis; só os da versão escolhida contam (a tela desabilita os
    das demais). Toda regra de negócio fica em `ProcessApplicationService`;
    aqui só a validação de formato e o desenho do formulário.
    """

    process_version = forms.ModelChoiceField(
        queryset=None,
        label="Processo",
        empty_label=None,
        error_messages={
            "required": "Escolha o processo que será aplicado.",
            "invalid_choice": "Este processo não está disponível para esta atividade.",
        },
    )

    def __init__(self, *args, activity, versions, **kwargs):
        from processes.models import ProcessInput, ProcessStep, ProcessVersion

        super().__init__(*args, **kwargs)
        self.activity = activity
        self.versions = list(versions)
        version_ids = [version.pk for version in self.versions]
        self.fields["process_version"].queryset = ProcessVersion.objects.filter(pk__in=version_ids)

        people = User.objects.filter(profile__organization_id=activity.organization_id, is_active=True)
        steps = list(
            ProcessStep.objects.filter(version_id__in=version_ids)
            .select_related("sector", "default_responsavel")
            .order_by("order", "pk")
        )
        inputs = list(ProcessInput.objects.filter(version_id__in=version_ids).order_by("order", "pk"))
        self._steps = {pk: [] for pk in version_ids}
        self._inputs = {pk: [] for pk in version_ids}
        for step in steps:
            self._steps[step.version_id].append(step)
            self.fields[f"responsavel_{step.pk}"] = forms.ModelChoiceField(
                queryset=people,
                required=False,
                error_messages={"invalid_choice": "Escolha uma pessoa ativa da organização."},
            )
        for item in inputs:
            self._inputs[item.version_id].append(item)
            self.fields[f"input_{item.pk}"] = forms.CharField(required=False, max_length=5000)
            self.fields[f"input_received_{item.pk}"] = forms.BooleanField(required=False)

    def clean(self):
        from .process_application import normalize_input_value
        from .services import ActivityError

        cleaned = super().clean()
        version = cleaned.get("process_version")
        if version is None:
            return cleaned

        responsible_by_step = {}
        for step in self._steps.get(version.pk, []):
            name = f"responsavel_{step.pk}"
            person = cleaned.get(name)
            if person is not None:
                responsible_by_step[step.pk] = person
            elif name not in self.errors and step.default_responsavel_id is None:
                self.add_error(name, "Escolha o responsável desta etapa.")

        input_values = {}
        for item in self._inputs.get(version.pk, []):
            value = (cleaned.get(f"input_{item.pk}") or "").strip()
            received = bool(cleaned.get(f"input_received_{item.pk}"))
            if not value and not received:
                continue
            try:
                normalize_input_value(item, value, received)
            except ActivityError as exc:
                self.add_error(f"input_{item.pk}", str(exc))
                continue
            input_values[item.pk] = {"value": value, "is_received": received}

        cleaned["responsible_by_step"] = responsible_by_step
        cleaned["input_values"] = input_values
        return cleaned

    def panels(self):
        """Dados prontos para desenhar, por versão elegível, os passos 2 e 3.

        Em cada etapa, as pessoas do setor vêm primeiro e as demais logo
        depois; o responsável padrão (ou o valor reenviado, se o formulário
        voltou com erro) já vem selecionado.
        """
        from .process_application import ProcessApplicationService

        all_steps = [step for steps in self._steps.values() for step in steps]
        people, members = ProcessApplicationService.people_for_steps(self.activity.organization, all_steps)

        widgets = {
            "TEXTO": "text",
            "DATA": "date",
            "NUMERO": "number",
            "LINK": "url",
            "ARQUIVO": "confirm",
            "SELECAO": "confirm",
        }
        panels = []
        for version in self.versions:
            step_rows = []
            for step in self._steps[version.pk]:
                field_name = f"responsavel_{step.pk}"
                if self.is_bound:
                    selected = self.data.get(field_name, "")
                else:
                    selected = step.default_responsavel_id or ""
                sector_members = members.get(step.sector_id, set())
                step_rows.append(
                    {
                        "step": step,
                        "field_name": field_name,
                        "selected": str(selected),
                        "has_default": step.default_responsavel_id is not None,
                        "sector_people": [person for person in people if person.pk in sector_members],
                        "other_people": [person for person in people if person.pk not in sector_members],
                        "errors": self.errors.get(field_name, []),
                    }
                )
            input_rows = []
            for item in self._inputs[version.pk]:
                value_name = f"input_{item.pk}"
                received_name = f"input_received_{item.pk}"
                input_rows.append(
                    {
                        "input": item,
                        "widget": widgets.get(item.input_type, "text"),
                        "value_name": value_name,
                        "received_name": received_name,
                        "value": self.data.get(value_name, "") if self.is_bound else "",
                        "received": bool(self.data.get(received_name)) if self.is_bound else False,
                        "errors": self.errors.get(value_name, []),
                    }
                )
            panels.append({"version": version, "steps": step_rows, "inputs": input_rows})
        return panels
