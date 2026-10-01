from django.contrib import admin

from .models import IntakeEvent, IntakeItem


class IntakeEventInline(admin.TabularInline):
    model = IntakeEvent
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in IntakeEvent._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(IntakeItem)
class IntakeItemAdmin(admin.ModelAdmin):
    list_display = ["received_at", "status", "source", "sender_display", "subject", "confidence", "organization"]
    list_filter = ["status", "source", "organization"]
    search_fields = ["subject", "sender_name", "sender_email", "raw_content"]
    readonly_fields = [f.name for f in IntakeItem._meta.fields]
    inlines = [IntakeEventInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
