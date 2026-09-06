from django import forms

from workflows.models import ProcessTemplate

from .models import Demand, DemandDecision


class DemandForm(forms.ModelForm):
    FIELDSETS = [
        ("Identificação", ["communication_channel"]),
        (
            "Relacionamento",
            [
                "client_name",
                "client_document",
                "client_contact_name",
                "client_contact_phone",
                "client_contact_email",
                "intermediary_name",
                "final_client_name",
                "is_existing_client",
            ],
        ),
        ("Obra", ["site_name", "site_address", "site_city", "site_state", "site_type", "site_phase"]),
        (
            "Solicitação",
            [
                "request_summary",
                "disciplines_requested",
                "supply_materials",
                "supply_labor",
                "supply_equipment",
                "supply_project_development",
                "request_details",
            ],
        ),
        ("Documentação", ["documentation_received", "documentation_missing", "documentation_invalid"]),
        (
            "Qualidade da informação",
            [
                "project_level",
                "disciplines_with_project",
                "disciplines_without_project",
                "information_completeness",
                "conflicts_identified",
                "confidence_notes",
            ],
        ),
        (
            "Prazos",
            [
                "confirmation_deadline",
                "questions_deadline",
                "proposal_deadline",
                "expected_construction_start",
                "expected_execution_duration",
            ],
        ),
        (
            "Condições comerciais",
            [
                "contracting_modality",
                "payment_terms",
                "direct_billing",
                "retentions_notes",
                "guarantees_notes",
                "specific_taxes_notes",
                "proposal_validity_days",
                "price_adjustment_notes",
            ],
        ),
        (
            "Entregáveis",
            [
                "deliverable_technical_proposal",
                "deliverable_commercial_proposal",
                "deliverable_client_spreadsheet",
                "deliverable_wbs",
                "deliverable_schedule",
                "deliverable_histogram",
                "deliverable_other_notes",
            ],
        ),
        (
            "Comunicação",
            [
                "reference_email",
                "verbal_information_notes",
                "whatsapp_information_notes",
                "technical_contact_notes",
                "proposal_recipient",
                "requires_intermediary_approval",
            ],
        ),
    ]

    class Meta:
        model = Demand
        exclude = ["protocol", "created_by", "created_at"]
        widgets = {
            "confirmation_deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "questions_deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "proposal_deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "expected_construction_start": forms.DateInput(attrs={"type": "date"}),
        }

    def fieldsets(self):
        for legend, field_names in self.FIELDSETS:
            yield legend, [self[name] for name in field_names]


class DemandDecisionForm(forms.ModelForm):
    process_template = forms.ModelChoiceField(
        queryset=ProcessTemplate.objects.filter(is_active=True),
        required=False,
        label="Template do processo (obrigatório se a decisão for 'Convertida')",
    )
    process_title = forms.CharField(required=False, label="Título do processo (opcional)")

    class Meta:
        model = DemandDecision
        fields = [
            "status",
            "pending_items",
            "pending_impact_notes",
            "pending_disciplines_affected",
            "can_budget",
            "can_budget_partially",
            "risks_notes",
            "deadline_is_viable",
            "decision_notes",
        ]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == DemandDecision.Decision.CONVERTIDA and not cleaned.get("process_template"):
            self.add_error("process_template", "Selecione um template para converter a demanda em processo.")
        return cleaned
