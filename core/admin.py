from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .colors import is_valid_palette_color
from .models import Client, Company, CostCenter, Organization, Sector, Site
from .widgets import ColorPaletteWidget


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
    class form(forms.ModelForm):
        color = forms.CharField(label="cor", widget=ColorPaletteWidget)

        class Meta:
            model = Sector
            fields = "__all__"

        def clean_color(self):
            color = (self.cleaned_data.get("color") or "#3B82F6").upper()
            if not is_valid_palette_color(color):
                raise forms.ValidationError("Escolha uma cor da paleta oficial.")
            return color

    list_display = ("name", "color_preview", "organization", "is_active", "created_by", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name",)

    @admin.display(description="cor")
    def color_preview(self, obj):
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;">'
            '<span style="display:inline-block;width:18px;height:18px;border-radius:4px;background:{};border:1px solid #cbd5e1;" aria-hidden="true"></span>{}'
            '</span>',
            obj.color,
            obj.color,
        )


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "client", "is_active")
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
