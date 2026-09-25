from django import forms
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import Client, Company, CostCenter, Sector, Site, Tag
from core.sanitize import sanitize_description
from core.widgets import (
    ActivityPickerWidget,
    ClientPickerWidget,
    PersonPickerWidget,
    RichTextWidget,
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


class OrganizationScopedFormMixin:
    """Todo select só pode oferecer registros da própria organização."""

    def scope_querysets(self, organization, can_create_person=False, can_create_client=False):
        fields = self.fields
        if "owner" in fields:
            fields["owner"].queryset = User.objects.filter(
                profile__organization=organization, is_active=True
            ).order_by("first_name", "username")
            if isinstance(fields["owner"].widget, PersonPickerWidget):
                fields["owner"].widget.queryset = fields["owner"].queryset
                if can_create_person:
                    fields["owner"].widget.create_url = reverse("user-create")
        if "client" in fields:
            fields["client"].queryset = Client.objects.filter(organization=organization, is_active=True)
            if isinstance(fields["client"].widget, ClientPickerWidget):
                fields["client"].widget.queryset = fields["client"].queryset
                if can_create_client:
                    fields["client"].widget.create_url = reverse("client-create")
        if "company" in fields:
            fields["company"].queryset = Company.objects.filter(
                organization=organization, is_active=True
            )
        if "site" in fields:
            fields["site"].queryset = Site.objects.filter(organization=organization, is_active=True)
        if "cost_center" in fields:
            fields["cost_center"].queryset = CostCenter.objects.filter(
                organization=organization, is_active=True
            )
        if "sector" in fields:
            fields["sector"].queryset = Sector.objects.filter(
                organization=organization, is_active=True
            )
        if "tags" in fields:
            queryset = Tag.objects.filter(organization=organization, is_active=True)
            fields["tags"].queryset = queryset
            if isinstance(fields["tags"].widget, TagPickerWidget):
                fields["tags"].widget.queryset = queryset


class ActivityQuickCreateForm(OrganizationScopedFormMixin, forms.ModelForm):
    """Criação em segundos: o essencial à vista, o resto em "Mais opções"
    (doc 09 §43-56, ampliado pelas Regras 1-13 da tela de nova atividade)."""

    class Meta:
        model = Activity
        # Ordem pensada para o layout de campo único em duas colunas (sem a
        # coluna de resumo): cliente/título, urgência/prazo, responsável/
        # grupo, empresa/obra, centro de custo, endereço e descrição por
        # último, cada um ocupando a linha inteira.
        fields = [
            "client",
            "title",
            "urgency",
            "requested_deadline",
            "owner",
            "sector",
            "company",
            "site",
            "cost_center",
            "address",
            "tags",
            "description",
        ]
        labels = {
            "title": "O que precisa ser resolvido?",
            "client": "Cliente",
            "owner": "Atribuir para",
            "urgency": "Urgência",
            "requested_deadline": "Prazo da solicitação",
            "sector": "Grupo designado",
            "description": "Descrição",
            "company": "Empresa",
            "site": "Obra",
            "cost_center": "Centro de custo",
            "address": "Endereço",
            "tags": "Marcadores",
        }
        help_texts = {
            "title": "Descreva o resultado esperado, não a ação. Ex.: “Material disponível na obra”.",
            "client": "Quem solicitou o serviço.",
            "owner": "Quem responde pelo resultado até a resolução.",
            "requested_deadline": "Quando quem pediu precisa da entrega.",
            "sector": "Setor para quem esta atividade é endereçada.",
            "address": "Endereço adicional, além do que já está no cadastro do cliente.",
        }
        widgets = {
            "title": forms.TextInput(attrs={"autofocus": True, "placeholder": "Ex.: Material disponível na obra"}),
            "client": ClientPickerWidget(),
            "owner": PersonPickerWidget(),
            "urgency": forms.RadioSelect(),
            "description": RichTextWidget(),
            "requested_deadline": DateTimeLocalInput(),
            "address": forms.TextInput(attrs={"placeholder": "Ex.: Rua, número, bairro"}),
            "tags": TagPickerWidget(),
        }

    def __init__(
        self, *args, organization=None, user=None, can_create_person=False, can_create_client=False, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.scope_querysets(organization, can_create_person=can_create_person, can_create_client=can_create_client)
        self.fields["owner"].empty_label = None
        self.fields["client"].required = False
        self.fields["client"].empty_label = None
        if user is not None and not self.is_bound:
            self.fields["owner"].initial = user
        for optional in (
            "description",
            "company",
            "site",
            "cost_center",
            "sector",
            "address",
            "requested_deadline",
            "tags",
        ):
            self.fields[optional].required = False

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
    class Meta:
        model = Activity
        fields = [
            "client",
            "title",
            "urgency",
            "requested_deadline",
            "sector",
            "company",
            "site",
            "cost_center",
            "address",
            "tags",
            "description",
        ]
        labels = ActivityQuickCreateForm.Meta.labels
        widgets = {
            "client": ClientPickerWidget(),
            "urgency": forms.RadioSelect(),
            "description": RichTextWidget(),
            "requested_deadline": DateTimeLocalInput(),
            "tags": TagPickerWidget(),
        }

    def __init__(self, *args, organization=None, can_create_client=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_querysets(organization, can_create_client=can_create_client)
        self.fields["client"].required = False
        self.fields["client"].empty_label = None
        for optional in (
            "description",
            "company",
            "site",
            "cost_center",
            "sector",
            "address",
            "requested_deadline",
            "tags",
        ):
            self.fields[optional].required = False

    def clean_description(self):
        return sanitize_description(self.cleaned_data.get("description"))


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
    """Adicionar tarefa: o mínimo para a atividade avançar (doc 09 §81-84)."""

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
    opcional escondida até a pessoa abrir. Quando a atividade já tem um
    "Grupo designado" (Regra 6), o setor da tarefa é herdado dele e nem
    aparece no popup — só quando não há grupo definido é que a pessoa escolhe."""

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
            "description": RichTextWidget(),
            "requested_deadline": DateTimeLocalInput(),
            "tags": TagPickerWidget(),
        }

    def __init__(self, *args, organization=None, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_querysets(organization)
        self.fields["description"].required = False
        self.fields["requested_deadline"].required = False
        self.fields["tags"].required = False
        if activity is not None and activity.sector_id:
            # Herda o "Grupo designado" da atividade: o campo some do popup,
            # mas o hidden ainda submete o valor inicial normalmente.
            self.fields["sector"].initial = activity.sector_id
            self.fields["sector"].widget = forms.HiddenInput()
        else:
            self.fields["sector"].required = True

    def clean_description(self):
        return sanitize_description(self.cleaned_data.get("description"))


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
        # `activity=None` para o TaskQuickCreateForm.__init__: aqui o setor
        # nunca é herdado automaticamente, porque a atividade só é conhecida
        # depois do campo `activity` ser escolhido — o campo sector permanece
        # sempre visível e obrigatório nesta variante.
        super().__init__(*args, organization=organization, activity=None, **kwargs)
        self.order_fields(["activity", "title", "sector", "requested_deadline", "tags", "description"])
        queryset = Activity.objects.filter(organization=organization, status__in=self.OPEN_ACTIVITY_STATUSES)
        self.fields["activity"].queryset = queryset
        self.fields["activity"].widget.queryset = queryset
        if can_create_activity:
            self.fields["activity"].widget.create_url = reverse("activity-mini-create")
        self.fields["sector"].required = True


class ActivityAttachmentForm(forms.Form):
    """Upload de anexo (Regra 13): o arquivo vai para uma pasta própria da
    atividade, nomeada pelo código gerado automaticamente."""

    file = forms.FileField(label="Arquivo")


class TaskReturnForm(forms.Form):
    """Devolução: motivo sempre obrigatório (Regras 02 §36)."""

    to_sector = forms.ModelChoiceField(queryset=Sector.objects.none(), label="Devolver para")
    reason = forms.ModelChoiceField(queryset=ReturnReason.objects.none(), label="Motivo")
    observation = forms.CharField(
        label="Observação", required=False, widget=forms.Textarea(attrs={"rows": 3})
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
        label="Observação", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reason"].queryset = ReturnReason.objects.filter(
            organization=organization, is_active=True
        )


class TaskBlockForm(forms.Form):
    reason = forms.CharField(label="Motivo do bloqueio", max_length=255)
    observation = forms.CharField(
        label="Observação", required=False, widget=forms.Textarea(attrs={"rows": 3})
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
        queryset=User.objects.none(), label="Executor", widget=PersonPickerWidget()
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


class DeadlineProposalForm(forms.Form):
    proposed_deadline = forms.DateTimeField(label="Novo prazo", widget=DateTimeLocalInput())


class ConflictResolutionForm(forms.Form):
    resolution_note = forms.CharField(
        label="Decisão", widget=forms.Textarea(attrs={"rows": 3}),
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
            attrs={"rows": 3, "placeholder": "Escreva uma mensagem… use @usuario para mencionar alguém"}
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
    reason = forms.CharField(label="Motivo", widget=forms.Textarea(attrs={"rows": 3}))


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
            attrs={"rows": 4, "maxlength": 1000, "placeholder": "Descreva o resultado, o que foi realizado, observações finais, próximos passos…"}
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
            attrs={"rows": 4, "maxlength": 1000, "placeholder": "Descreva o motivo da pendência e o que já foi feito."}
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
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 1000, "placeholder": "Observações da aprovação, se houver."}),
    )
