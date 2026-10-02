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
