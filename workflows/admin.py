from django.contrib import admin

from .models import Attachment, Process, ProcessStep, ProcessTemplate, ProcessTemplateStep


class ProcessTemplateStepInline(admin.TabularInline):
    model = ProcessTemplateStep
    extra = 1
    ordering = ["order"]


@admin.register(ProcessTemplate)
class ProcessTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_by", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    inlines = [ProcessTemplateStepInline]


class ProcessStepInline(admin.TabularInline):
    model = ProcessStep
    extra = 0
    ordering = ["order"]
    fields = [
        "order",
        "name",
        "responsible_group",
        "priority",
        "status",
        "assigned_to",
        "released_at",
        "deadline_at",
        "completed_at",
    ]
    readonly_fields = ["released_at", "completed_at"]


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    fields = ["file", "category", "description", "step", "uploaded_by", "uploaded_at"]
    readonly_fields = ["uploaded_at"]


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ["title", "template", "status", "created_by", "created_at", "demand"]
    list_filter = ["status", "template"]
    search_fields = ["title"]
    inlines = [ProcessStepInline, AttachmentInline]
    readonly_fields = ["created_at", "cancelled_at", "finalized_at"]


@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = [
        "process",
        "order",
        "name",
        "responsible_group",
        "status",
        "priority",
        "assigned_to",
        "deadline_at",
    ]
    list_filter = ["status", "priority", "responsible_group"]
    search_fields = ["name", "process__title"]
    autocomplete_fields = []


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ["description", "process", "step", "category", "uploaded_by", "uploaded_at"]
    list_filter = ["category"]
    readonly_fields = ["uploaded_at"]
