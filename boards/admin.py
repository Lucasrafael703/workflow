from django.contrib import admin

from .models import (
    Board, BoardCell, BoardColumn, BoardColumnOption, BoardGroup, BoardItem, BoardView,
    DomainBoard, DomainBoardCardField, DomainBoardChoice, DomainBoardField, DomainBoardView, DomainBoardViewColumn,
    DomainCustomValue,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    """O quadro é montado e alterado pela tela (que autoriza, valida e audita). O admin só consulta."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Board)
class BoardAdmin(ReadOnlyAdmin):
    list_display = ["name", "organization", "is_active", "created_by", "created_at"]
    list_filter = ["organization", "is_active"]
    search_fields = ["name"]


@admin.register(BoardView)
class BoardViewAdmin(ReadOnlyAdmin):
    list_display = ["name", "board", "type", "is_active", "created_by"]
    list_filter = ["type", "is_active"]
    search_fields = ["name", "board__name"]


@admin.register(BoardGroup)
class BoardGroupAdmin(ReadOnlyAdmin):
    list_display = ["name", "board", "color", "position", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "board__name"]


@admin.register(BoardColumn)
class BoardColumnAdmin(ReadOnlyAdmin):
    list_display = ["name", "board", "type", "width", "is_visible", "is_active"]
    list_filter = ["type", "is_active", "is_visible"]
    search_fields = ["name", "board__name"]


@admin.register(BoardColumnOption)
class BoardColumnOptionAdmin(ReadOnlyAdmin):
    list_display = ["label", "column", "color", "is_default", "is_done", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["label", "column__name"]


@admin.register(BoardItem)
class BoardItemAdmin(ReadOnlyAdmin):
    list_display = ["name", "board", "group", "is_active", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "board__name"]


@admin.register(BoardCell)
class BoardCellAdmin(ReadOnlyAdmin):
    list_display = ["item", "column", "updated_by", "updated_at"]
    search_fields = ["item__name", "column__name"]


@admin.register(DomainBoard)
class DomainBoardAdmin(ReadOnlyAdmin):
    list_display = ["name", "domain", "organization", "updated_at"]
    list_filter = ["domain", "organization"]
    search_fields = ["name", "organization__name"]


@admin.register(DomainBoardField)
class DomainBoardFieldAdmin(ReadOnlyAdmin):
    list_display = ["label", "key", "board", "type", "is_system", "is_active"]
    list_filter = ["type", "is_system", "is_active"]


@admin.register(DomainBoardChoice)
class DomainBoardChoiceAdmin(ReadOnlyAdmin):
    list_display = ["label", "field", "color", "is_active"]


@admin.register(DomainBoardView)
class DomainBoardViewAdmin(ReadOnlyAdmin):
    list_display = ["name", "board", "type", "is_default", "is_active"]
    list_filter = ["type", "is_active"]


@admin.register(DomainBoardViewColumn)
class DomainBoardViewColumnAdmin(ReadOnlyAdmin):
    list_display = ["view", "field", "position", "width", "is_visible"]


@admin.register(DomainBoardCardField)
class DomainBoardCardFieldAdmin(ReadOnlyAdmin):
    list_display = ["view", "field", "position", "is_visible"]


@admin.register(DomainCustomValue)
class DomainCustomValueAdmin(ReadOnlyAdmin):
    list_display = ["field", "activity", "task", "updated_by", "updated_at"]
