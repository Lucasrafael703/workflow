from django.contrib import admin

from .models import Client, Company, CostCenter, Organization, Sector, Site


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "document", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "document")


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active", "created_by", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name",)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "company", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name",)


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "site", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "document", "phone", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "document", "phone", "email")
