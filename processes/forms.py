from django import forms

from .models import ProcessCriterion, ProcessInput, ProcessStep, ProcessVersion


class ProcessBasicInfoForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=200)
    activity_type = forms.ModelChoiceField(label="Tipo de atividade", queryset=None, required=False)
    description = forms.CharField(label="Descrição", widget=forms.Textarea(attrs={"rows": 3}), required=False)

    def __init__(self, *args, activity_types=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["activity_type"].queryset = activity_types


class ProcessOutputForm(forms.Form):
    output_description = forms.CharField(
        label="Entrega esperada",
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Ex.: Proposta comercial pronta para envio"}),
        help_text="Escreva como resultado verificável, não como ação (ex.: evite “Elaborar proposta”).",
    )
    output_evidence_type = forms.ChoiceField(
        label="Evidência do output", choices=[("", "—")] + list(ProcessVersion.EvidenceType.choices), required=False
    )


class ProcessInputForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=150)
    input_type = forms.ChoiceField(label="Tipo", choices=ProcessInput.InputType.choices)
    is_required = forms.BooleanField(label="Obrigatório", required=False, initial=True)
    source = forms.ChoiceField(label="Origem", choices=[("", "—")] + list(ProcessInput.Source.choices), required=False)
    help_text = forms.CharField(label="Ajuda de preenchimento", max_length=255, required=False)


class ProcessCriterionForm(forms.Form):
    name = forms.CharField(label="Critério", max_length=255)
    is_required = forms.BooleanField(label="Obrigatório", required=False, initial=True)


class ProcessStepForm(forms.Form):
    name = forms.CharField(label="Nome da tarefa", max_length=200)
    sector = forms.ModelChoiceField(label="Setor responsável", queryset=None)
    depends_on_previous = forms.BooleanField(label="Depende da etapa anterior", required=False, initial=True)

    def __init__(self, *args, sectors=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sector"].queryset = sectors
