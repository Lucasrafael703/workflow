"""Leituras do quadro: ordenação feita no banco (cada tipo ordena do seu jeito), busca, filtro por pessoa e a
montagem do mapa de células, que evita uma consulta por célula na tela."""

from django.db.models import Exists, F, OuterRef, Prefetch, Q, Subquery, TextField, Value
from django.db.models.functions import Coalesce, Lower, NullIf

from audit.models import AuditLog

from .models import (
    BoardCell,
    BoardCellOption,
    BoardCellUser,
    BoardColumn,
    BoardGroup,
    BoardItem,
)
from .kanban import SORT_CREATED, SORT_MANUAL, SORT_NAME
from .services import CellService


class BoardQueryService:
    #: campo da célula pelo qual cada tipo ordena (texto e pessoa têm tratamento próprio abaixo)
    SORT_FIELD_BY_TYPE = {
        BoardColumn.Type.NUMBER: "value_number",
        BoardColumn.Type.CURRENCY: "value_number",
        BoardColumn.Type.DATE: "value_date",
        BoardColumn.Type.CHECKBOX: "value_boolean",
    }

    @staticmethod
    def columns(board, *, visible=True):
        queryset = BoardColumn.objects.filter(board=board, is_active=True)
        if visible is not None:
            queryset = queryset.filter(is_visible=visible)
        return queryset.prefetch_related("options").order_by("position", "id")

    @staticmethod
    def groups(board):
        return BoardGroup.objects.filter(board=board, is_active=True).order_by("position", "id")

    @staticmethod
    def sort_expression(column):
        """Subconsulta com o valor que a coluna usa para ordenar, ou `None` se o tipo não ordena."""
        cells = BoardCell.objects.filter(item_id=OuterRef("pk"), column=column)
        column_type = column.type
        if column_type == BoardColumn.Type.TEXT:
            return Subquery(cells.annotate(_v=NullIf(Lower("value_text"), Value("", output_field=TextField()))).values("_v")[:1])
        if column_type == BoardColumn.Type.DATE:
            field = "value_datetime" if (column.settings or {}).get("show_time") else "value_date"
            return Subquery(cells.values(field)[:1])
        if column_type in BoardQueryService.SORT_FIELD_BY_TYPE:
            return Subquery(cells.values(BoardQueryService.SORT_FIELD_BY_TYPE[column_type])[:1])
        if column_type in BoardColumn.OPTION_TYPES:
            options = BoardCellOption.objects.filter(cell__item_id=OuterRef("pk"), cell__column=column, option__is_active=True)
            return Subquery(options.values("option__position")[:1])
        if column_type == BoardColumn.Type.PERSON:
            people = BoardCellUser.objects.filter(cell__item_id=OuterRef("pk"), cell__column=column).annotate(
                _v=Coalesce(NullIf(Lower("user__first_name"), Value("")), Lower("user__username"))
            )
            return Subquery(people.values("_v")[:1])
        return None

    @staticmethod
    def search_filter(term):
        cells = BoardCell.objects.filter(item_id=OuterRef("pk"), column__is_active=True)
        return (
            Q(name__icontains=term)
            | Q(Exists(cells.filter(value_text__icontains=term)))
            | Q(Exists(cells.filter(option_values__option__label__icontains=term, option_values__option__is_active=True)))
            | Q(Exists(cells.filter(user_values__user__first_name__icontains=term)))
            | Q(Exists(cells.filter(user_values__user__last_name__icontains=term)))
            | Q(Exists(cells.filter(user_values__user__username__icontains=term)))
        )

    @staticmethod
    def _filtered_items(board, search, person_id):
        queryset = BoardItem.objects.filter(board=board, is_active=True, group__is_active=True).select_related("group")

        term = (search or "").strip()
        if term:
            queryset = queryset.filter(BoardQueryService.search_filter(term))
        if person_id:
            queryset = queryset.filter(
                Exists(
                    BoardCellUser.objects.filter(
                        cell__item_id=OuterRef("pk"), cell__column__is_active=True, user_id=person_id
                    )
                )
            )
        return queryset

    @staticmethod
    def items(board, *, sort_column=None, direction="asc", search="", person_id=None):
        queryset = BoardQueryService._filtered_items(board, search, person_id)
        expression = BoardQueryService.sort_expression(sort_column) if sort_column is not None else None
        if expression is None:
            return queryset.order_by("group__position", "position", "id")
        sort = F("_sort").desc(nulls_last=True) if direction == "desc" else F("_sort").asc(nulls_last=True)
        return queryset.annotate(_sort=expression).order_by("group__position", sort, "position", "id")

    @staticmethod
    def kanban_items(board, *, sort=SORT_MANUAL, direction="asc", search="", person_id=None):
        """Itens para os cartões. `sort` é uma palavra-chave (`manual` = a ordem da tabela, `name`, `created`) ou uma
        coluna. A ordem vale DENTRO de cada raia; o desempate é sempre a ordem do quadro (grupo, posição)."""
        queryset = BoardQueryService._filtered_items(board, search, person_id)
        manual = ("group__position", "position", "id")
        descending = direction == "desc"
        if sort == SORT_NAME:
            queryset = queryset.annotate(_sort=Lower("name"))
        elif sort == SORT_CREATED:
            queryset = queryset.annotate(_sort=F("created_at"))
        elif sort != SORT_MANUAL and sort is not None:
            expression = BoardQueryService.sort_expression(sort)
            if expression is not None:
                queryset = queryset.annotate(_sort=expression)
            else:
                sort = SORT_MANUAL
        if sort == SORT_MANUAL or sort is None:
            return queryset.order_by(*manual)
        key = F("_sort").desc(nulls_last=True) if descending else F("_sort").asc(nulls_last=True)
        return queryset.order_by(key, *manual)

    @staticmethod
    def with_cells(queryset):
        cells = BoardCell.objects.filter(column__is_active=True).prefetch_related(
            Prefetch("user_values", queryset=BoardCellUser.objects.select_related("user").order_by("position", "id")),
            Prefetch("option_values", queryset=BoardCellOption.objects.select_related("option").order_by("position", "id")),
        ).select_related("column")
        return queryset.prefetch_related(Prefetch("cells", queryset=cells))

    @staticmethod
    def attach_cells(items, columns_by_id):
        """`item.cell_map[column_id]` com `cell.display`, `cell.option` e `cell.person` já resolvidos: o
        template só lê, nunca consulta."""
        for item in items:
            item.cell_map = {}
            for cell in item.cells.all():
                column = columns_by_id.get(cell.column_id)
                if column is None:
                    continue
                cell.column = column
                options = [row for row in cell.option_values.all() if row.option.is_active]
                cell.option = options[0].option if options else None
                people = list(cell.user_values.all())
                cell.person = people[0].user if people else None
                cell.display = CellService.display_value(cell, column)
                item.cell_map[cell.column_id] = cell
        return items

    @staticmethod
    def history(board):
        return AuditLog.objects.filter(metadata__board_id=board.pk).select_related("user").order_by("-timestamp", "-id")
