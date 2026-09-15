from django.contrib import admin

from .models import Action, ActionGroup, Profile, ProfileAction, Scope, UserAction, UserProfile


@admin.register(ActionGroup)
class ActionGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "key")


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "group", "is_sensitive", "is_active")
    list_filter = ("group", "is_sensitive", "is_active")
    search_fields = ("name", "key", "description")


class ProfileActionInline(admin.TabularInline):
    model = ProfileAction
    extra = 0
    autocomplete_fields = ("action",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name",)
    inlines = [ProfileActionInline]


@admin.register(Scope)
class ScopeAdmin(admin.ModelAdmin):
    list_display = ("label", "organization", "type", "is_active")
    list_filter = ("organization", "type", "is_active")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "profile", "scope", "is_active", "created_at")
    list_filter = ("organization", "is_active", "profile")
    search_fields = ("user__username",)


@admin.register(UserAction)
class UserActionAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "scope", "is_active", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("user__username", "action__key")
