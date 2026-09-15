from django.contrib import admin

from .models import (
    Activity,
    ActivityMessage,
    DeadlineConflict,
    DeadlineProposal,
    OwnerChangeLog,
    QueueEntry,
    QueuePositionChange,
    ReturnReason,
    SectorTransfer,
    Task,
    TaskBlock,
    TaskExecutor,
    TaskMessage,
    TaskReturn,
    WorkSession,
)


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ("order", "title", "sector", "status", "requested_deadline", "committed_deadline")
    show_change_link = True


class OwnerChangeLogInline(admin.TabularInline):
    model = OwnerChangeLog
    extra = 0
    fk_name = "activity"
    readonly_fields = ("previous_owner", "new_owner", "changed_by", "changed_at")
    can_delete = False


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "owner", "status", "requested_deadline", "created_at")
    list_filter = ("organization", "status")
    search_fields = ("title", "owner__username", "created_by__username")
    autocomplete_fields = ("owner", "created_by", "company", "site", "cost_center")
    inlines = [TaskInline, OwnerChangeLogInline]
    readonly_fields = ("created_at", "first_action_at", "completed_at", "cancelled_at", "reopened_at")


@admin.register(ActivityMessage)
class ActivityMessageAdmin(admin.ModelAdmin):
    list_display = ("activity", "author", "created_at")
    search_fields = ("activity__title", "author__username", "body")


@admin.register(ReturnReason)
class ReturnReasonAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name",)


class TaskExecutorInline(admin.TabularInline):
    model = TaskExecutor
    extra = 0
    readonly_fields = ("added_by", "added_at")


class WorkSessionInline(admin.TabularInline):
    model = WorkSession
    extra = 0


class TaskBlockInline(admin.TabularInline):
    model = TaskBlock
    extra = 0
    readonly_fields = ("started_by", "started_at")


class TaskReturnInline(admin.TabularInline):
    model = TaskReturn
    extra = 0
    fk_name = "task"
    readonly_fields = ("returned_by", "returned_at")


class SectorTransferInline(admin.TabularInline):
    model = SectorTransfer
    extra = 0
    readonly_fields = ("moved_by", "moved_at")


class DeadlineProposalInline(admin.TabularInline):
    model = DeadlineProposal
    extra = 0
    readonly_fields = ("proposed_by", "proposed_at", "decided_by", "decided_at")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "activity", "sector", "status", "requested_deadline", "committed_deadline")
    list_filter = ("sector", "status")
    search_fields = ("title", "activity__title")
    autocomplete_fields = ("activity", "sector", "depends_on", "created_by")
    inlines = [
        TaskExecutorInline,
        WorkSessionInline,
        TaskBlockInline,
        TaskReturnInline,
        SectorTransferInline,
        DeadlineProposalInline,
    ]


@admin.register(TaskMessage)
class TaskMessageAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "created_at")
    search_fields = ("task__title", "author__username", "body")


class QueuePositionChangeInline(admin.TabularInline):
    model = QueuePositionChange
    extra = 0
    readonly_fields = ("old_position", "new_position", "old_total", "new_total", "reason", "changed_by", "changed_at")
    can_delete = False


@admin.register(QueueEntry)
class QueueEntryAdmin(admin.ModelAdmin):
    list_display = ("task", "sector", "position", "queue_size_at_entry", "entered_at", "left_at")
    list_filter = ("sector",)
    search_fields = ("task__title",)
    inlines = [QueuePositionChangeInline]


@admin.register(DeadlineProposal)
class DeadlineProposalAdmin(admin.ModelAdmin):
    list_display = ("task", "proposed_deadline", "proposed_by", "status", "decided_by", "decided_at")
    list_filter = ("status",)
    search_fields = ("task__title",)


@admin.register(DeadlineConflict)
class DeadlineConflictAdmin(admin.ModelAdmin):
    list_display = ("task", "status", "opened_at", "resolved_by", "resolved_at")
    list_filter = ("status",)
    search_fields = ("task__title",)
