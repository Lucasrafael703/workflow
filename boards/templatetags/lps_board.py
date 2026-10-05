"""Filtros do quadro: ler a célula de um item sem consulta, o valor bruto que o editor precisa e a cor do texto
que contrasta com a etiqueta."""

from decimal import Decimal

from django import template
from django.utils import timezone

from ..models import BoardColumn
from ..presentation import type_icon as _type_icon

register = template.Library()

DARK_TEXT = "#1F2937"
LIGHT_TEXT = "#FFFFFF"


@register.filter
def cell_of(item, column_id):
    """A célula do item na coluna, ou `None` (célula nunca preenchida). `item.cell_map` vem de `attach_cells`."""
    return getattr(item, "cell_map", {}).get(column_id)


@register.filter
def get_item(mapping, key):
    return (mapping or {}).get(key)


@register.filter
def contrast(color):
    """Texto claro sobre cor escura, escuro sobre cor clara (luminância percebida)."""
    value = (color or "").lstrip("#")
    if len(value) != 6:
        return DARK_TEXT
    try:
        red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return DARK_TEXT
    luminance = (0.299 * red + 0.587 * green + 0.114 * blue) / 255
    return DARK_TEXT if luminance > 0.62 else LIGHT_TEXT


@register.filter
def initials(user):
    name = (user.get_full_name() or user.get_username() or "").split()
    if not name:
        return "?"
    return (name[0][0] + (name[-1][0] if len(name) > 1 else "")).upper()


@register.filter
def type_icon(column_type):
    return _type_icon(column_type)


@register.filter
def person_name(user):
    return user.get_full_name() or user.get_username()


@register.simple_tag
def raw_value(cell, column):
    """Valor no formato que o editor entende: texto, número com vírgula, data ISO, id de pessoa/etiqueta, 1/0."""
    if cell is None:
        return ""
    column_type = column.type
    if column_type == BoardColumn.Type.TEXT:
        return cell.value_text
    if column_type in (BoardColumn.Type.NUMBER, BoardColumn.Type.CURRENCY):
        if cell.value_number is None:
            return ""
        text = format(Decimal(cell.value_number).normalize(), "f")
        return text.replace(".", ",")
    if column_type == BoardColumn.Type.DATE:
        if cell.value_date is None:
            return ""
        if (column.settings or {}).get("show_time") and cell.value_datetime:
            return timezone.localtime(cell.value_datetime).strftime("%Y-%m-%dT%H:%M")
        return cell.value_date.isoformat()
    if column_type == BoardColumn.Type.CHECKBOX:
        return "" if cell.value_boolean is None else ("1" if cell.value_boolean else "0")
    if column_type == BoardColumn.Type.PERSON:
        return cell.person.pk if getattr(cell, "person", None) else ""
    if column_type in BoardColumn.OPTION_TYPES:
        return cell.option.pk if getattr(cell, "option", None) else ""
    return ""


@register.simple_tag
def is_overdue(cell, column):
    """Prazo vencido: só colunas de data marcadas como prazo, e só se a data já passou."""
    if cell is None or cell.value_date is None:
        return False
    if column.type != BoardColumn.Type.DATE or not (column.settings or {}).get("is_deadline"):
        return False
    return cell.value_date < timezone.localdate()


KANBAN_LANE_EMPTY = "Nenhum item. Arraste um cartão para cá."


@register.simple_tag(takes_context=True)
def board_kanban(context):
    """O Kanban de Quadros no contrato do kit (`templates/kanban/_lanes.html`): a MESMA marcação e o MESMO comportamento do
    Kanban de Demandas. Lê o que a página e o fragmento das raias já passam (`lanes`, `card_columns`, `group_column`,
    `sum_column`, `permissions`, `board`, `show_field_names`) e só traduz: nada de marcação própria."""
    permissions = context.get("permissions") or {}
    board = context["board"]
    item_label = board.item_label or "item"
    group_column = context.get("group_column")
    sum_column = context.get("sum_column")
    card_columns = context.get("card_columns") or []
    can_edit = bool(permissions.get("edit_item"))
    can_delete = bool(permissions.get("delete_item"))
    can_add = bool(permissions.get("create_item")) and bool(group_column)
    can_manage = bool(permissions.get("manage_columns"))

    lanes = []
    for lane in context.get("lanes") or []:
        cards = []
        for item in lane["items"]:
            fields = []
            for column in card_columns:
                cell = cell_of(item, column.id)
                fields.append({
                    "kind": "template", "template": "boards/_cell.html", "cell": cell, "column": column,
                    "label": column.name, "css": column.type.lower(), "editable": can_edit,
                    "attrs": [
                        ("data-cell", ""), ("data-item-id", item.pk), ("data-column-id", column.id),
                        ("data-type", column.type), ("data-value", raw_value(cell, column)),
                    ],
                })
            cards.append({
                "id": item.pk, "title": getattr(item, "display_name", "") or item.name or "", "url": "", "updated_at": "", "scope": "",
                "can_move": can_edit, "menu": can_edit or can_delete, "title_editable": can_edit, "title_label": item_label,
                "attrs": [], "fields": fields,
            })
        option = lane.get("option")
        lanes.append({
            "key": lane["key"], "label": lane["label"], "color": lane["color"], "is_blank": lane["is_blank"],
            "accepts": True, "scope": "", "sector": "", "option_id": option.pk if option is not None else None,
            "menu": can_manage and not lane["is_blank"],
            "total": (lane.get("total_display") or "") if sum_column else None,
            "count": lane["count"], "empty_text": KANBAN_LANE_EMPTY,
            "add": {"label": f"Adicionar {item_label.lower()}", "attrs": []} if can_add else None,
            "cards": cards,
        })
    return {
        "item_label": item_label, "menu_label": "Opções da tarefa",  # o texto de sempre de Quadros
        "show_field_names": bool(context.get("show_field_names")),
        "empty_template": "boards/_kanban_empty.html", "lanes": lanes,
    }
