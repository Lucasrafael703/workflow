"""Visualização Kanban do quadro.

O Kanban não tem dados próprios: lê as colunas e os itens do quadro e só decide COMO mostrá-los. Cada etiqueta da
coluna agrupadora vira uma raia (então renomear ou recolorir a etiqueta muda a raia na hora: não existe outro cadastro
de nome ou de cor), e cada item continua sendo o mesmo item da tabela.

Este módulo é a parte que não depende de tela: limpar a configuração da visualização, descobrir a coluna agrupadora e
os campos do cartão, e montar as raias com contagem e soma.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError

from .models import BoardColumn
from .validators import CURRENCY_SYMBOLS, _bool, default_settings_for, format_number

T = BoardColumn.Type

#: Só colunas com etiquetas viram raias. (Pessoa e outros agrupamentos ficam para uma próxima versão.)
GROUPABLE_TYPES = BoardColumn.OPTION_TYPES
SUMMABLE_TYPES = (T.NUMBER, T.CURRENCY)

SORT_MANUAL = "manual"
SORT_NAME = "name"
SORT_CREATED = "created"
SORT_KEYWORDS = (SORT_MANUAL, SORT_NAME, SORT_CREATED)

BLANK_AUTO, BLANK_ALWAYS, BLANK_NEVER = "auto", "always", "never"
BLANK_MODES = (BLANK_AUTO, BLANK_ALWAYS, BLANK_NEVER)
BLANK_KEY = "blank"
BLANK_LABEL = "Em branco"
BLANK_COLOR = "#C4C4C4"

DEFAULT_CARD_FIELD_COUNT = 4
MAX_CARD_FIELDS = 12

DEFAULT_SETTINGS = {
    "group_by": None,  # id da coluna; vazio = a primeira coluna de Status (ou, na falta, de Lista suspensa)
    "show_empty": True,  # mostrar raias sem cartão
    "blank_lane": BLANK_AUTO,  # raia "Em branco" (itens sem etiqueta): só quando houver itens / sempre / nunca
    "sort": {"by": SORT_MANUAL, "dir": "asc"},
    "sum_column": None,  # id de uma coluna de Número ou Moeda: soma no cabeçalho da raia
    "card_fields": None,  # lista de ids de colunas, na ordem do cartão; vazio = os primeiros campos do quadro
    "show_field_names": False,
}


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def clean_kanban_settings(columns, raw, current=None):
    """Configuração completa e válida: `current` + o que veio em `raw`. `columns` são as colunas ativas do quadro.

    Só se aceitam as chaves conhecidas, e toda referência a coluna tem de ser de uma coluna ATIVA DESTE quadro do tipo
    certo (o JSON vem do navegador: um id de outro quadro ou de outro tipo é recusado).
    """
    by_id = {column.pk: column for column in columns}
    clean = {key: (dict(value) if isinstance(value, dict) else value) for key, value in DEFAULT_SETTINGS.items()}
    for key, value in (current or {}).items():
        if key in clean:
            clean[key] = dict(value) if isinstance(value, dict) else value
    clean["sort"] = {**DEFAULT_SETTINGS["sort"], **(clean.get("sort") if isinstance(clean.get("sort"), dict) else {})}

    for key, value in (raw or {}).items():
        if key == "group_by":
            if value in (None, ""):
                clean[key] = None
                continue
            column = by_id.get(_to_int(value))
            if column is None or column.type not in GROUPABLE_TYPES:
                raise ValidationError("Escolha uma coluna de Status ou de Lista suspensa para agrupar.")
            clean[key] = column.pk
        elif key in ("show_empty", "show_field_names"):
            clean[key] = _bool(value)
        elif key == "blank_lane":
            if value not in BLANK_MODES:
                raise ValidationError("Opção inválida para a raia “Em branco”.")
            clean[key] = value
        elif key == "sum_column":
            if value in (None, ""):
                clean[key] = None
                continue
            column = by_id.get(_to_int(value))
            if column is None or column.type not in SUMMABLE_TYPES:
                raise ValidationError("A soma só vale para colunas de Número ou de Moeda.")
            clean[key] = column.pk
        elif key == "card_fields":
            if value is None:
                clean[key] = None
                continue
            if not isinstance(value, (list, tuple)):
                raise ValidationError("Lista de campos do cartão inválida.")
            ids = []
            for entry in value:
                column = by_id.get(_to_int(entry))
                if column is None:
                    raise ValidationError("Um dos campos do cartão não existe mais neste quadro.")
                if column.pk not in ids:
                    ids.append(column.pk)
            if len(ids) > MAX_CARD_FIELDS:
                raise ValidationError(f"O cartão aceita até {MAX_CARD_FIELDS} campos.")
            clean[key] = ids
        elif key == "sort":
            if not isinstance(value, dict):
                raise ValidationError("Ordenação inválida.")
            by = value.get("by", clean["sort"]["by"])
            direction = value.get("dir", clean["sort"]["dir"])
            if by not in SORT_KEYWORDS:
                column = by_id.get(_to_int(by))
                if column is None:
                    raise ValidationError("Escolha uma coluna do quadro para ordenar.")
                by = column.pk
            if direction not in ("asc", "desc"):
                raise ValidationError("Direção de ordenação inválida.")
            clean["sort"] = {"by": by, "dir": direction}
    return clean


def resolve_group_column(settings, columns):
    """A coluna que define as raias: a escolhida (se ainda existe e serve) ou a primeira de Status, depois de Lista."""
    candidates = [column for column in columns if column.type in GROUPABLE_TYPES]
    chosen = _to_int((settings or {}).get("group_by"))
    for column in candidates:
        if column.pk == chosen:
            return column
    for kind in GROUPABLE_TYPES:
        for column in candidates:
            if column.type == kind:
                return column
    return None


def resolve_sum_column(settings, columns):
    chosen = _to_int((settings or {}).get("sum_column"))
    for column in columns:
        if column.pk == chosen and column.type in SUMMABLE_TYPES:
            return column
    return None


def resolve_card_columns(settings, columns, group_column):
    """Os campos do cartão, na ordem. Sem escolha, os primeiros campos VISÍVEIS do quadro (menos o agrupador, que já
    aparece como raia): mostrar tudo por padrão deixaria o cartão ilegível."""
    chosen = (settings or {}).get("card_fields")
    by_id = {column.pk: column for column in columns}
    if isinstance(chosen, list):
        return [by_id[pk] for pk in (_to_int(entry) for entry in chosen) if pk in by_id]
    defaults = [
        column for column in columns
        if column.is_visible and (group_column is None or column.pk != group_column.pk)
    ]
    return defaults[:DEFAULT_CARD_FIELD_COUNT]


def sort_choice(settings, columns):
    """`(by, direction)` já resolvido: uma palavra-chave, ou a coluna (se ainda existe)."""
    sort = (settings or {}).get("sort") or {}
    direction = "desc" if sort.get("dir") == "desc" else "asc"
    by = sort.get("by", SORT_MANUAL)
    if by in SORT_KEYWORDS:
        return by, direction
    by_id = {column.pk: column for column in columns}
    column = by_id.get(_to_int(by))
    return (column, direction) if column is not None else (SORT_MANUAL, "asc")


def sort_options(columns, settings):
    """Opções do seletor "Ordenar" (`valor` = "<por>|<direção>"), marcando a que está salva na visualização."""
    sort = (settings or {}).get("sort") or {}
    current = f"{sort.get('by', SORT_MANUAL)}|{'desc' if sort.get('dir') == 'desc' else 'asc'}"
    choices = [
        (f"{SORT_MANUAL}|asc", "Ordem do quadro"),
        (f"{SORT_NAME}|asc", "Título (A → Z)"),
        (f"{SORT_NAME}|desc", "Título (Z → A)"),
        (f"{SORT_CREATED}|desc", "Mais recentes primeiro"),
        (f"{SORT_CREATED}|asc", "Mais antigos primeiro"),
    ]
    for column in columns:
        choices.append((f"{column.pk}|asc", f"{column.name} (crescente)"))
        choices.append((f"{column.pk}|desc", f"{column.name} (decrescente)"))
    return [{"value": value, "label": label, "selected": value == current} for value, label in choices]


def format_total(total, column):
    """O total formatado como a coluna mostra o valor (símbolo da moeda, unidade, casas decimais)."""
    config = {**default_settings_for(column.type), **(column.settings or {})}
    text = format_number(total, config.get("decimal_places"))
    if column.type == T.CURRENCY:
        return f"{CURRENCY_SYMBOLS.get(config.get('currency'), 'R$')} {text}"
    return f"{text} {config['unit']}".strip() if config.get("unit") else text


def build_lanes(group_column, items, settings, sum_column=None):
    """Raias na ordem das etiquetas, com os itens já distribuídos. Cada raia: `key` ("blank" ou o id da etiqueta), `label`,
    `color`, `option`, `items`, `count`, `total` (Decimal, se há coluna de soma), `total_display` e `is_blank`.

    `items` precisam de `cell_map` (ver `BoardQueryService.attach_cells`): a etiqueta do item é a da célula agrupadora.
    """
    settings = settings or {}
    lanes = []
    by_option = {}
    if group_column is not None:
        for option in sorted((o for o in group_column.options.all() if o.is_active), key=lambda o: (o.position, o.pk)):
            lane = {"key": str(option.pk), "label": option.label, "color": option.color, "option": option,
                    "is_blank": False, "items": []}
            lanes.append(lane)
            by_option[option.pk] = lane
    blank = {"key": BLANK_KEY, "label": BLANK_LABEL, "color": BLANK_COLOR, "option": None, "is_blank": True, "items": []}

    for item in items:
        cell = item.cell_map.get(group_column.pk) if group_column is not None else None
        option = getattr(cell, "option", None) if cell is not None else None
        (by_option.get(option.pk, blank) if option is not None else blank)["items"].append(item)

    for lane in lanes + [blank]:
        lane["count"] = len(lane["items"])
        if sum_column is not None:
            total = Decimal("0")
            for item in lane["items"]:
                cell = item.cell_map.get(sum_column.pk)
                if cell is not None and cell.value_number is not None:
                    total += cell.value_number
            lane["total"] = total
            lane["total_display"] = format_total(total, sum_column) if lane["items"] else ""
        else:
            lane["total"], lane["total_display"] = None, ""

    mode = settings.get("blank_lane", BLANK_AUTO)
    show_empty = settings.get("show_empty", True)
    visible = [lane for lane in lanes if lane["items"] or show_empty]
    if mode == BLANK_ALWAYS or (mode == BLANK_AUTO and blank["items"]):
        visible.append(blank)
    return visible
