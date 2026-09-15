from django.contrib import admin

from .models import Profile, UserSector


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "main_sector", "phone"]
    list_filter = ["organization", "main_sector"]
    search_fields = ["user__username", "user__email"]


@admin.register(UserSector)
class UserSectorAdmin(admin.ModelAdmin):
    list_display = ["user", "sector", "joined_at", "removed_at"]
    list_filter = ["sector"]
    search_fields = ["user__username", "user__email"]
