from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "recipient", "actor", "event_type", "is_read", "created_at"]
    list_filter = ["event_type", "is_read"]
    search_fields = ["title", "message", "recipient__username", "actor__username"]
    readonly_fields = ["created_at", "read_at"]
    list_select_related = ["recipient", "actor"]
