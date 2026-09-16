from django import forms
from django.contrib.auth import get_user_model

from core.models import Company, CostCenter, Sector, Site

from .models import Activity, ReturnReason, Task

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

    def scope_querysets(self, organization):
        fields = self.fields
        if "owner" in fields:
            fields["owner"].queryset = User.objects.filter(
                profile__organization=organization, is_active=True
            ).order_by("first_name", "username")
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


class ActivityQuickCreateForm(OrganizationScopedFormMixin, forms.ModelForm):
    """Criação em segundos: três campos à vista, o resto em "Mais opções" (doc 09 §43-56)."""

    class Meta:
        model = Activity
        fields = ["title", "owner", "requested_deadline", "description", "company", "site", "cost_center"]
        labels = {
            "title": "O que precisa ser resolvido?",
            "owner": "Dono",
            "requested_deadline": "Prazo solicitado",
            "description": "Descrição",
            "company": "Empresa",
            "site": "Obra",
            "cost_center": "Centro de custo",
        }
        help_texts = {
            "title": "Descreva o resultado esperado, não a ação. Ex.: “Material disponível na obra”.",
            "owner": "Quem responde pelo resultado até a resolução.",
            "requested_deadline": "Quando quem pediu precisa da entrega.",
        }
        widgets = {
            "title": forms.TextInput(attrs={"autofocus": True, "placeholder": "Ex.: Material disponível na obra"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "requested_deadline": DateTimeLocalInput(),
        }

    def __init__(self, *args, organization=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_querysets(organization)
        self.fields["owner"].empty_label = None
        if user is not None and not self.is_bound:
            self.fields["owner"].initial = user
        for optional in ("description", "company", "site", "cost_center", "requested_deadline"):
            self.fields[optional].required = False


class ActivityEditForm(OrganizationScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["title", "description", "requested_deadline", "company", "site", "cost_center"]
        labels = ActivityQuickCreateForm.Meta.labels
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "requested_deadline": DateTimeLocalInput(),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_querysets(organization)
        for optional in ("description", "company", "site", "cost_center", "requested_deadline"):
            self.fields[optional].required = False


class ChangeOwnerForm(forms.Form):
    new_owner = forms.ModelChoiceField(queryset=User.objects.none(), label="Novo dono")

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_owner"].queryset = User.objects.filter(
            profile__organization=organization, is_active=True
        ).order_by("first_name", "username")


class TaskForm(OrganizationScopedFormMixin, forms.ModelForm):
    """Adicionar tarefa: o mínimo para a atividade avançar (doc 09 §81-84)."""

    class Meta:
        model = Task
        fields = ["title", "sector", "requested_deadline", "description", "depends_on"]
        labels = {
            "title": "O que precisa ser feito?",
            "sector": "Setor responsável",
            "requested_deadline": "Prazo solicitado",
            "description": "Descrição",
            "depends_on": "Depende de",
        }
        widgets = {
            "title": forms.TextInput(attrs={"autofocus": True, "placeholder": "Ex.: Realizar cotação"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "requested_deadline": DateTimeLocalInput(),
        }

    def __init__(self, *args, organization=None, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_querysets(organization)
        for optional in ("description", "requested_deadline", "depends_on"):
            self.fields[optional].required = False

        siblings = Task.objects.none()
        if activity is not None:
            siblings = activity.tasks.exclude(status=Task.Status.CANCELADA)
            if self.instance.pk:
                siblings = siblings.exclude(pk=self.instance.pk)
        self.fields["depends_on"].queryset = siblings
        self.fields["depends_on"].empty_label = "Nenhuma"


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
    user = forms.ModelChoiceField(queryset=User.objects.none(), label="Executor")

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(
            profile__organization=organization, is_active=True
        ).order_by("first_name", "username")


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


class ReorderForm(forms.Form):
    """Reordenação da fila; o motivo é pedido depois do movimento (doc 09 §95)."""

    new_position = forms.IntegerField(min_value=1, label="Nova posição")
    reason = forms.CharField(label="Motivo da mudança", required=False, max_length=255)


class CancelForm(forms.Form):
    reason = forms.CharField(label="Motivo", widget=forms.Textarea(attrs={"rows": 3}))
