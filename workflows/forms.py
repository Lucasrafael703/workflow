from django import forms

from .models import Attachment, Process, ProcessTemplate


class ProcessCreateForm(forms.ModelForm):
    template = forms.ModelChoiceField(queryset=ProcessTemplate.objects.filter(is_active=True), label="Template")

    class Meta:
        model = Process
        fields = ["template", "title"]


class ActivityCompleteForm(forms.Form):
    observations = forms.CharField(label="Observações", widget=forms.Textarea, required=False)


class ActivityReopenForm(forms.Form):
    motivo = forms.CharField(label="Motivo da reabertura", widget=forms.Textarea)


class ActivityBlockForm(forms.Form):
    observations = forms.CharField(label="Descreva o bloqueio", widget=forms.Textarea)


class ActivityCancelForm(forms.Form):
    motivo = forms.CharField(label="Motivo do cancelamento", widget=forms.Textarea)


class ProcessCancelForm(forms.Form):
    motivo = forms.CharField(label="Motivo do cancelamento", widget=forms.Textarea)


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ["file", "category", "description", "step"]

    def __init__(self, *args, process=None, **kwargs):
        super().__init__(*args, **kwargs)
        if process is not None:
            self.fields["step"].queryset = process.steps.all()
        self.fields["step"].required = False
