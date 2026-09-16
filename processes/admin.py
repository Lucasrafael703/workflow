from django.contrib import admin

from .models import (
    ActivityCriterionCheck,
    ActivityInputValue,
    ActivityType,
    Process,
    ProcessCriterion,
    ProcessInput,
    ProcessStep,
    ProcessVersion,
)


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name",)


class ProcessInputInline(admin.TabularInline):
    model = ProcessInput
    extra = 0


class ProcessCriterionInline(admin.TabularInline):
    model = ProcessCriterion
    extra = 0


class ProcessStepInline(admin.TabularInline):
    model = ProcessStep
    extra = 0


@admin.register(ProcessVersion)
class ProcessVersionAdmin(admin.ModelAdmin):
    list_display = ("process", "number", "status", "published_at")
    list_filter = ("status",)
    search_fields = ("process__name",)
    inlines = [ProcessInputInline, ProcessCriterionInline, ProcessStepInline]


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "activity_type", "is_active", "created_at")
    list_filter = ("company", "activity_type", "is_active")
    search_fields = ("name",)


@admin.register(ActivityInputValue)
class ActivityInputValueAdmin(admin.ModelAdmin):
    list_display = ("activity", "process_input", "is_received")
    list_filter = ("is_received",)


@admin.register(ActivityCriterionCheck)
class ActivityCriterionCheckAdmin(admin.ModelAdmin):
    list_display = ("activity", "process_criterion", "is_met")
    list_filter = ("is_met",)
