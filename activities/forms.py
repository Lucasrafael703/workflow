import datetime

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Count
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
    sprite_icon,
)

from .models import Activity, ActivityPendency, MessageKind, ReturnReason, Task, WorkSession
from .services import RETROACTIVE_JUSTIFICATION_DAYS

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

    def id_for_label(self, id_):
        # O rótulo do campo aponta para a data (o primeiro dos dois inputs).
        return f"{id_}_0" if id_ else id_

    def render_parts(self, name, value, attrs=None, renderer=None):
        """Os dois inputs prontos, data e hora, para quem dá a cada um o seu rótulo.
        Os ids seguem a convenção do `MultiWidget` (`<id>_0`, `<id>_1`)."""
        if not isinstance(value, (list, tuple)):
            value = self.decompress(value)
        attrs = {**self.attrs, **(attrs or {})}
        base_id = attrs.get("id")
        parts = []
        for index, widget in enumerate(self.widgets):
            sub_attrs = {**attrs, "class": "activity-input"}
            if base_id:
                sub_attrs["id"] = f"{base_id}_{index}"
            parts.append(widget.render(f"{name}_{index}", value[index], sub_attrs, renderer))
        return parts

    def render(self, name, value, attrs=None, renderer=None):
        """Data e hora lado a lado, cada uma com o seu ícone (calendário e
        relógio). O rótulo do campo continua apontando para a data."""
        parts = self.render_parts(name, value, attrs, renderer)
        cells = [
            format_html(
                '<div class="activity-input-wrap"><span class="activity-input-icon">{}</span>{}</div>',
                sprite_icon(icon),
                html,
            )
            for html, icon in zip(parts, ("calendar", "clock"))
        ]
        return format_html('<div class="activity-date-time">{}{}</div>', *cells)


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
    "title": "Nome da demanda",
    "client": "Para qual cliente?",
    "owner": "Quem acompanha esta demanda?",
    "urgency": "Qual é a urgência?",
    "sector": "Qual equipe cuida desta demanda?",
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
    "tags": "Escolha palavras-chave para encontrar e agrupar esta demanda depois.",
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


class ActivityEditorForm(OrganizationScopedFormMixin, forms.ModelForm):
    """Criar e editar atividade: o mesmo formulário, em três etapas.

        1. Informações principais  — nome, atribuído a, setor, prazo, urgência, organização
        2. Informações do cliente  — cliente, obra, centro de custo, solicitante externo, endereço
        3. Descrição e arquivos    — observações e o link/caminho dos arquivos (sem upload)

    Não tem: marcadores, solicitante interno, anotações internas nem envio de
    arquivo. Esses campos continuam no modelo, mas ficam **fora** do formulário
    de propósito: um campo que não está no `ModelForm` nunca é alterado ao salvar,
    então editar uma atividade antiga não apaga o que ela já tinha.

    Nome, responsável e setor são obrigatórios ao criar e ao salvar uma edição.
    O rascunho antigo (`acao=rascunho`) e o envio só com título do seletor
    legado passam `require_essentials=False`.
    """

    STEP_FIELDS = {
        1: ("title", "owner", "sector", "requested_deadline", "urgency", "company"),
        2: ("client", "site", "cost_center", "external_requester", "address"),
        3: ("description", "files_location"),
    }
    STEP_TITLES = {
        1: ("Informações principais", "Dados básicos da demanda e responsáveis."),
        2: ("Informações do cliente", "Dados relacionados ao cliente, obra e centro de custo."),
        3: ("Descrição e arquivos", "Informações complementares para a execução da demanda."),
    }
    DESCRIPTION_LIMIT = 2000

    requested_deadline = SplitDateOptionalTimeField(
        label="Prazo de vencimento",
        required=False,
        help_text="Data e horário para conclusão da demanda. Sem horário, vale até o fim do dia.",
    )

    class Meta:
        model = Activity
        fields = [
            "title", "owner", "sector", "requested_deadline", "urgency", "company",
            "client", "site", "cost_center", "external_requester", "address",
            "description", "files_location",
        ]
        labels = {
            "title": "Nome da demanda",
            "owner": "Atribuído a",
            "sector": "Setor responsável",
            "urgency": "Urgência",
            "company": "Organização",
            "client": "Cliente",
            "site": "Obra",
            "cost_center": "Centro de custo",
            "external_requester": "Solicitante (Externo)",
            "address": "Endereço complementar",
            "description": "Observações",
            "files_location": "Link / caminho dos arquivos",
        }
        help_texts = {
            "title": "Descreva a entrega esperada. Ex.: Orçamento do gerador aprovado.",
            "owner": "Essa pessoa será responsável pela entrega e acompanhará as tarefas.",
            "sector": "Escolha o setor que será responsável por esta demanda.",
            "urgency": "Indique o quanto esta demanda precisa de atenção.",
            "company": "Ex.: Comercial, Engenharia, Operações, etc.",
            "client": "Selecione o cliente relacionado a esta demanda.",
            "site": "Selecione a obra relacionada, se houver.",
            "cost_center": "Escolha o centro de custo para apropriação desta demanda.",
            "external_requester": "Pessoa que solicitou a demanda (cliente, fornecedor, etc.).",
            "address": "Informações adicionais do local, se necessário.",
            "description": "Inclua todas as informações necessárias para a execução desta demanda.",
            "files_location": "Você pode colar o link ou o caminho da pasta/arquivo relacionado a esta demanda "
            "(Google Drive, OneDrive, Dropbox, etc.), ou um caminho de rede.",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "activity-input", "placeholder": "Ex.: Material disponível na obra", "autofocus": True}
            ),
            "owner": PersonPickerWidget(icon="user", selection_label="Buscar pessoa..."),
            "sector": SectorPickerWidget(icon="users"),
            "urgency": forms.RadioSelect(),
            "company": CompanyPickerWidget(icon="building", empty_label="Selecionar organização"),
            "client": ClientPickerWidget(icon="building"),
            "site": SitePickerWidget(icon="hardhat", filter_field_id="id_client", filter_param="client"),
            "cost_center": CostCenterPickerWidget(icon="dollar", filter_field_id="id_site", filter_param="site"),
            "external_requester": forms.TextInput(attrs={"class": "activity-input", "placeholder": "Nome do solicitante"}),
            "address": forms.TextInput(
                attrs={"class": "activity-input", "placeholder": "Ex.: Rua, número, complemento, bairro, cidade"}
            ),
            "description": RichTextWidget(
                placeholder="Descreva aqui os detalhes da demanda, orientações, observações e outras informações "
                "importantes...",
                limit=2000,
            ),
            "files_location": forms.TextInput(
                attrs={"class": "activity-input", "placeholder": "Cole aqui o link ou caminho dos arquivos"}
            ),
        }

    def __init__(
        self,
        *args,
        organization=None,
        user=None,
        drafting=False,
        can_change_owner=False,
        require_essentials=True,
        can_create_person=False,
        can_create_client=False,
        can_create_sector=False,
        can_create_company=False,
        can_create_site=False,
        can_create_cost_center=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.require_essentials = require_essentials
        self.scope_querysets(
            organization,
            can_create_person=can_create_person,
            can_create_client=can_create_client,
            can_create_sector=can_create_sector,
            can_create_company=can_create_company,
            can_create_site=can_create_site,
            can_create_cost_center=can_create_cost_center,
        )
        fields = self.fields
        fields["owner"].empty_label = None
        fields["client"].empty_label = None
        # A obrigatoriedade é tratada em `clean()` (e marcada na tela com `*`),
        # não no campo: o rascunho antigo e o seletor legado precisam aceitar vazio.
        for name in self._meta.fields:
            fields[name].required = False
        fields["owner"].disabled = not can_change_owner
        if not can_change_owner:
            fields["owner"].help_text = "A transferência de responsabilidade exige permissão específica."
        if drafting and not self.is_bound and not self.instance.pk:
            self.initial["owner"] = user
        if self.initial.get("title") == Activity.DRAFT_TITLE_PLACEHOLDER:
            self.initial["title"] = ""

    # -- etapas ------------------------------------------------------------------------

    @property
    def steps(self):
        """Para o template: número, título, descrição e campos de cada etapa."""
        return [
            {
                "number": number,
                "title": self.STEP_TITLES[number][0],
                "description": self.STEP_TITLES[number][1],
                "fields": [self[name] for name in names],
            }
            for number, names in self.STEP_FIELDS.items()
        ]

    def step_with_errors(self):
        """Primeira etapa com erro (1 se não houver): onde a janela deve abrir."""
        for number, names in self.STEP_FIELDS.items():
            if any(self[name].errors for name in names):
                return number
        return 1

    # -- validação -------------------------------------------------------------------------

    def clean_description(self):
        return sanitize_description(self.cleaned_data.get("description"))

    def clean_urgency(self):
        return self.cleaned_data.get("urgency") or Activity.Urgency.MEDIA

    def clean_external_requester(self):
        return (self.cleaned_data.get("external_requester") or "").strip()

    def clean_files_location(self):
        return (self.cleaned_data.get("files_location") or "").strip()

    def clean(self):
        cleaned = super().clean()
        if self.require_essentials:
            title = (cleaned.get("title") or "").strip()
            if not title or title == Activity.DRAFT_TITLE_PLACEHOLDER:
                self.add_error("title", "Informe o nome da demanda.")
            if not cleaned.get("owner"):
                self.add_error("owner", "Escolha quem fica com a demanda.")
            if not cleaned.get("sector"):
                self.add_error("sector", "Escolha o setor responsável.")
        # Cliente → Obra → Centro de custo: a escolha de baixo precisa pertencer à de cima
        # (obra ou centro de custo sem vínculo valem para qualquer um).
        client, site, cost_center = cleaned.get("client"), cleaned.get("site"), cleaned.get("cost_center")
        if client and site and site.client_id not in (None, client.pk):
            self.add_error("site", "Esta obra pertence a outro cliente. Escolha uma obra de quem foi selecionado.")
        if site and cost_center and cost_center.site_id not in (None, site.pk):
            self.add_error("cost_center", "Este centro de custo pertence a outra obra.")
        return cleaned


class ChangeOwnerForm(forms.Form):
    new_owner = forms.ModelChoiceField(
        queryset=User.objects.none(), label="Quem vai acompanhar esta demanda?", widget=PersonPickerWidget(),
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
        help_text="Informe até quando a demanda precisa ficar pronta. Deixe em branco para retirar o prazo."
    )


# Mesmas palavras nos dois lugares em que se descreve uma tarefa (criar e editar):
# quem compara as duas janelas vê as mesmas perguntas e as mesmas ajudas.
TASK_LABELS = {
    "title": "O que precisa ser feito?",
    "sector": "Setor",
    "responsavel": "Responsável",
    "participantes": "Participantes",
    "requested_deadline": "Data do prazo",
    "description": "Instruções",
    "tags": "Marcadores",
}
TASK_HELP = {
    "title": "Comece com uma ação. Ex.: Conferir os preços da planilha.",
    "sector": "Equipe que recebe a tarefa na fila de trabalho.",
    "responsavel": "Quem acompanha a tarefa até a conclusão.",
    "participantes": "Quem ajuda a executar a tarefa. Uma pessoa que você convida só entra depois de aceitar.",
    "requested_deadline": "Quando quem pediu precisa receber a entrega. O prazo que a equipe se compromete a "
    "cumprir é combinado depois, em Mais ações → Propor novo prazo.",
    "description": "Explique o que fazer e como saber que o trabalho está pronto.",
    "tags": "Palavras-chave para organizar e encontrar a tarefa depois.",
}
TASK_TITLE_PLACEHOLDER = "Ex.: Levantar quantitativo da garagem"
# O nome da tarefa é o campo principal da janela: mesmo visual dos campos da atividade, com destaque.
TASK_TITLE_ATTRS = {"autofocus": True, "placeholder": TASK_TITLE_PLACEHOLDER, "class": "activity-input task-title-input"}
TASK_DESCRIPTION_PLACEHOLDER = (
    "Descreva as instruções para executar a tarefa, critérios de conclusão e outras informações importantes..."
)


class TaskDeadlineField(SplitDateOptionalTimeField):
    """Prazo da tarefa em dois campos, “Data do prazo” e “Hora do prazo”.

    Mesma regra do prazo da atividade: sem hora, vale até 23:59 do dia. Uma hora
    sem data é um erro explícito (a atividade a ignora em silêncio): quem
    preencheu a hora esperava um prazo, e perder isso sem avisar engana."""

    def __init__(self, **kwargs):
        kwargs.setdefault("widget", SplitDateOptionalTimeWidget(attrs={"class": "activity-input"}))
        kwargs.setdefault("label", TASK_LABELS["requested_deadline"])
        kwargs.setdefault("required", False)
        kwargs.setdefault("help_text", TASK_HELP["requested_deadline"])
        super().__init__(**kwargs)

    def compress(self, data_list):
        if data_list and data_list[0] in (None, "") and data_list[1] not in (None, ""):
            raise forms.ValidationError("Informe a data do prazo.", code="date_required")
        return super().compress(data_list)


class TaskDeadlineInputsMixin:
    """`form.deadline_inputs`: os inputs de data e de hora do prazo, separados, para o
    template dar a cada um o seu rótulo ("Data do prazo", "Hora do prazo")."""

    @property
    def deadline_inputs(self):
        bound = self["requested_deadline"]
        return bound.field.widget.render_parts(
            bound.html_name, bound.value(), {"id": bound.auto_id}, self.renderer
        )


def activity_summary(activity):
    """Resumo da atividade para o cartão da janela de tarefa: título e uma linha
    “Cliente • Setor: X • N tarefas”. Sem atividade, `None`."""
    if activity is None:
        return None
    total = getattr(activity, "task_total", None)
    if total is None:
        total = activity.tasks.count()
    parts = []
    if activity.client_id:
        parts.append(activity.client.name)
    if activity.sector_id:
        parts.append(f"Setor: {activity.sector.name}")
    parts.append("Sem tarefas ainda" if not total else f"{total} tarefa" if total == 1 else f"{total} tarefas")
    return {"id": activity.pk, "title": activity.title, "meta": " • ".join(parts)}


class TaskEditorForm(TaskDeadlineInputsMixin, forms.Form):
    """Editor único da tarefa (popup no padrão do editor de atividade): dados,
    prazo pedido, marcadores, responsável e participantes num só lugar.

    O que a pessoa não pode mudar **sai do formulário** (em vez de aparecer
    desabilitado): responsável exige `tarefa.alterar_responsavel`; participantes,
    `tarefa.atribuir`. O setor e a dependência não são editados aqui — mexem no
    fluxo e têm janela própria (“Enviar para outro setor” e “Gerenciar
    dependência”, em Mais ações). É um `Form` comum, não um `ModelForm`, para
    não alterar a instância antes de o serviço comparar o antes e o depois.
    """

    title = forms.CharField(
        label=TASK_LABELS["title"],
        max_length=200,
        help_text=TASK_HELP["title"],
        widget=forms.TextInput(attrs=TASK_TITLE_ATTRS),
    )
    description = forms.CharField(
        label=TASK_LABELS["description"],
        required=False,
        help_text=TASK_HELP["description"],
        widget=RichTextWidget(placeholder=TASK_DESCRIPTION_PLACEHOLDER),
    )
    requested_deadline = TaskDeadlineField()
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        required=False,
        label=TASK_LABELS["tags"],
        help_text=TASK_HELP["tags"],
        widget=TagPickerWidget(),
    )
    responsavel = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label=TASK_LABELS["responsavel"],
        help_text=TASK_HELP["responsavel"],
        widget=PersonPickerWidget(placeholder="Buscar responsável...", selection_label="Selecionar responsável..."),
    )
    participantes = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        label=TASK_LABELS["participantes"],
        help_text=TASK_HELP["participantes"],
        widget=PersonMultiPickerWidget(),
    )

    def __init__(
        self, *args, organization=None, task=None, can_change_responsavel=False, can_assign=False,
        can_create_person=False, **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.task = task
        people = User.objects.filter(profile__organization=organization, is_active=True).order_by(
            "first_name", "username"
        )
        tags = Tag.objects.filter(organization=organization, is_active=True)
        self.fields["tags"].queryset = tags
        self.fields["tags"].widget.queryset = tags
        self.fields["responsavel"].queryset = people
        self.fields["responsavel"].widget.queryset = people
        self.fields["participantes"].queryset = people
        self.fields["participantes"].widget.queryset = people
        if can_create_person:
            self.fields["responsavel"].widget.create_url = reverse("user-create")
            self.fields["participantes"].widget.create_url = reverse("user-create")
        if not can_change_responsavel:
            del self.fields["responsavel"]
        if not can_assign:
            del self.fields["participantes"]
        if task is not None and not self.is_bound:
            self.initial.update(
                title=task.title,
                description=task.description,
                requested_deadline=task.requested_deadline,
                tags=list(task.tags.values_list("pk", flat=True)),
                responsavel=task.responsavel_id,
                participantes=list(
                    task.executors.filter(removed_at__isnull=True).values_list("user_id", flat=True)
                ),
            )

    def clean_description(self):
        return sanitize_description(self.cleaned_data.get("description"))

    def clean(self):
        cleaned = super().clean()
        participantes = cleaned.get("participantes")
        responsavel = cleaned.get("responsavel") or (self.task.responsavel if self.task is not None else None)
        if participantes is not None and responsavel is not None:
            # Responsável e participantes são conjuntos disjuntos.
            cleaned["participantes"] = participantes.exclude(pk=responsavel.pk)
        return cleaned


class TaskDependencyForm(forms.Form):
    """“Gerenciar dependência”: só oferece as tarefas que podem ser predecessoras
    (da mesma atividade, não canceladas e sem ciclo — ver
    `TaskService.dependency_candidates`)."""

    depends_on = forms.ModelChoiceField(
        queryset=Task.objects.none(),
        required=False,
        empty_label="Nenhuma — esta tarefa não espera por ninguém",
        label="Qual tarefa precisa terminar antes desta?",
        help_text="Enquanto ela não for concluída, esta tarefa fica aguardando a etapa anterior e não entra "
        "na fila do setor.",
    )

    def __init__(self, *args, candidates=None, current=None, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["depends_on"]
        field.queryset = candidates if candidates is not None else Task.objects.none()
        field.label_from_instance = lambda item: f"{item.title} — {item.get_status_display()}"
        if current is not None and not self.is_bound:
            self.initial["depends_on"] = current.pk


class TaskQuickCreateForm(TaskDeadlineInputsMixin, OrganizationScopedFormMixin, forms.ModelForm):
    """Popup "+ Adicionar tarefa" (Regra 12): uma ação rápida, numa janela só,
    com as mesmas quatro seções do editor (Tarefa, Prazo e organização,
    Participantes, Instruções). O setor vem pré-preenchido com o "Grupo
    designado" da atividade quando houver, mas continua visível e editável — e
    a busca de responsável nunca se restringe a um setor, para ter o mesmo
    comportamento em qualquer ponto de entrada (Regra: um único padrão de tela
    de "Nova tarefa")."""

    requested_deadline = TaskDeadlineField()
    responsavel = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label=TASK_LABELS["responsavel"],
        help_text=TASK_HELP["responsavel"],
        required=True,
        widget=PersonPickerWidget(
            placeholder="Buscar responsável...",
            selection_label="Selecionar responsável...",
        ),
    )
    participantes = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        label=TASK_LABELS["participantes"],
        help_text=TASK_HELP["participantes"],
        required=False,
        widget=PersonMultiPickerWidget(),
    )

    class Meta:
        model = Task
        fields = ["title", "sector", "requested_deadline", "tags", "description"]
        labels = {name: TASK_LABELS[name] for name in fields}
        help_texts = {name: TASK_HELP[name] for name in fields}
        widgets = {
            "title": forms.TextInput(attrs=TASK_TITLE_ATTRS),
            "sector": SectorPickerWidget(),
            "description": RichTextWidget(placeholder=TASK_DESCRIPTION_PLACEHOLDER),
            "tags": TagPickerWidget(),
        }

    def __init__(self, *args, organization=None, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_querysets(organization)
        self.order_fields(["title", "sector", "responsavel", "participantes", "requested_deadline", "tags", "description"])
        self.fields["description"].required = False
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
        queryset=Activity.objects.none(), label="De qual demanda esta tarefa faz parte?", widget=ActivityPickerWidget(),
        help_text="A demanda é o resultado maior; esta tarefa é um dos passos para chegar lá.",
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

    @property
    def selected_activity(self):
        """A atividade já escolhida (ao reabrir a janela com erro, por exemplo), ou `None`."""
        value = self["activity"].value()
        if not value:
            return None
        try:
            return self.fields["activity"].queryset.select_related("client", "sector").annotate(
                task_total=Count("tasks")
            ).get(pk=value)
        except (ValueError, TypeError, Activity.DoesNotExist):
            return None


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
                                          help_text="Informe a data e o horário propostos. O responsável pela demanda receberá a proposta para decidir.")


class ConflictResolutionForm(forms.Form):
    resolution_note = forms.CharField(
        label="O que foi combinado para resolver o prazo?", widget=forms.Textarea(attrs={"rows": 3, "data-mention": "1"}),
        help_text="Explique a decisão e o próximo passo para as pessoas envolvidas.",
    )


class ManualTimeForm(forms.Form):
    """“Adicionar tempo trabalhado” (Regras 04 §110-113): acrescenta um período
    já trabalhado, com motivo, sem concluir a tarefa. Mesmas regras de motivo e
    comentário de “Já realizei este trabalho”, aplicadas pelo serviço."""

    started_at = forms.DateTimeField(label="Quando você começou a trabalhar?", widget=DateTimeLocalInput())
    ended_at = forms.DateTimeField(label="Quando você parou?", widget=DateTimeLocalInput(),
                                   help_text="Informe um período já trabalhado. O sistema calcula a duração entre o início e o fim.")
    reason = forms.ChoiceField(
        label="Motivo",
        choices=WorkSession.ManualReason.choices,
        initial=WorkSession.ManualReason.ESQUECI_INICIAR,
    )
    note = forms.CharField(
        label="Comentário",
        required=False,
        max_length=255,
        widget=forms.Textarea(attrs={"rows": 2, "maxlength": 255, "data-mention": "1"}),
        help_text=f"Explique quando escolher “Outro” ou quando o trabalho foi há mais de "
        f"{RETROACTIVE_JUSTIFICATION_DAYS} dias.",
    )


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
        label="Como esta demanda terminou?",
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
            "invalid_choice": "Este processo não está disponível para esta demanda.",
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
