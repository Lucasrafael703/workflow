from django.contrib import admin

from .models import Demand, DemandDecision


class DemandDecisionInline(admin.StackedInline):
    model = DemandDecision
    extra = 0
    can_delete = False
    readonly_fields = ["decided_at"]


@admin.register(Demand)
class DemandAdmin(admin.ModelAdmin):
    list_display = ["protocol", "client_name", "communication_channel", "created_by", "created_at"]
    list_filter = ["communication_channel", "information_completeness"]
    search_fields = ["protocol", "client_name", "site_name"]
    readonly_fields = ["protocol", "created_at"]
    inlines = [DemandDecisionInline]

    fieldsets = (
        ("Identificação", {"fields": ("protocol", "created_by", "created_at", "communication_channel")}),
        (
            "Relacionamento",
            {
                "fields": (
                    "client_name",
                    "client_document",
                    "client_contact_name",
                    "client_contact_phone",
                    "client_contact_email",
                    "intermediary_name",
                    "final_client_name",
                    "is_existing_client",
                )
            },
        ),
        (
            "Obra",
            {"fields": ("site_name", "site_address", "site_city", "site_state", "site_type", "site_phase")},
        ),
        (
            "Solicitação",
            {
                "fields": (
                    "request_summary",
                    "disciplines_requested",
                    "supply_materials",
                    "supply_labor",
                    "supply_equipment",
                    "supply_project_development",
                    "request_details",
                )
            },
        ),
        (
            "Documentação",
            {"fields": ("documentation_received", "documentation_missing", "documentation_invalid")},
        ),
        (
            "Qualidade da informação",
            {
                "fields": (
                    "project_level",
                    "disciplines_with_project",
                    "disciplines_without_project",
                    "information_completeness",
                    "conflicts_identified",
                    "confidence_notes",
                )
            },
        ),
        (
            "Prazos",
            {
                "fields": (
                    "confirmation_deadline",
                    "questions_deadline",
                    "proposal_deadline",
                    "expected_construction_start",
                    "expected_execution_duration",
                )
            },
        ),
        (
            "Condições comerciais",
            {
                "fields": (
                    "contracting_modality",
                    "payment_terms",
                    "direct_billing",
                    "retentions_notes",
                    "guarantees_notes",
                    "specific_taxes_notes",
                    "proposal_validity_days",
                    "price_adjustment_notes",
                )
            },
        ),
        (
            "Entregáveis",
            {
                "fields": (
                    "deliverable_technical_proposal",
                    "deliverable_commercial_proposal",
                    "deliverable_client_spreadsheet",
                    "deliverable_wbs",
                    "deliverable_schedule",
                    "deliverable_histogram",
                    "deliverable_other_notes",
                )
            },
        ),
        (
            "Comunicação",
            {
                "fields": (
                    "reference_email",
                    "verbal_information_notes",
                    "whatsapp_information_notes",
                    "technical_contact_notes",
                    "proposal_recipient",
                    "requires_intermediary_approval",
                )
            },
        ),
    )


@admin.register(DemandDecision)
class DemandDecisionAdmin(admin.ModelAdmin):
    list_display = ["demand", "status", "decided_by", "decided_at", "resulting_process"]
    list_filter = ["status"]
    readonly_fields = ["decided_at"]
