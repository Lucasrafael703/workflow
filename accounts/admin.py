from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone", "area_group"]
    list_filter = ["area_group"]
    search_fields = ["user__username", "user__email"]
