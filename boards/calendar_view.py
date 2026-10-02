"""Visualização Calendário do quadro.

O Calendário não tem dados próprios: lê os mesmos itens da tabela e do Kanban e só decide EM QUE DIA mostrá-los, pela
coluna de Data escolhida. Mover um cartão de dia grava aquela mesma célula de data (pelo mesmo serviço da tabela), então
não existe sincronização: é o mesmo dado visto por outra lente.

Este módulo é a parte que não depende de tela: limpar a configuração da visualização, descobrir a coluna de Data, a de
cor e os campos do cartão, e montar a grade do mês (semanas, dias, cartões, indicadores).
"""

import calendar
import datetime
import re

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import BoardColumn
from .validators import _bool

T = BoardColumn.Type

DATE_TYPES = (T.DATE,)
#: Colunas que dão cor ao cartão: as que têm etiquetas coloridas.
COLORABLE_TYPES = BoardColumn.OPTION_TYPES

COLOR_GROUP = "group"  # cor do grupo do item
COLOR_NONE = "none"  # cartões sem cor
NEUTRAL_COLOR = "#C4C4C4"

PERIOD_MONTH = "month"
#: Escalas que existem hoje. O formato da configuração já comporta Semana/Dia/Agenda sem mudar o que o item guarda.
PERIODS = (PERIOD_MONTH,)

MAX_VISIBLE_PER_DAY = 3  # cartões que cabem na célula do dia; o resto vai para "+ N mais"
DEFAULT_CARD_FIELD_COUNT = 3  # o cartão do mês é compacto: título + até 3 informações
MAX_CARD_FIELDS = 6
PANEL_LIMIT = 100  # linhas das listas "Sem data" e "Atrasados" (a contagem mostrada é sempre a exata)

MONTH_NAMES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)
MONTH_ABBR = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
WEEKDAY_LABELS = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")

DEFAULT_SETTINGS = {
    "date_field": None,  # id da coluna de Data; vazio = a coluna de prazo (ou a primeira Data) do quadro
    "period": PERIOD_MONTH,
    "color_by": None,  # vazio = automático (primeira coluna de Status, depois de Lista); id; "group"; "none"
    "card_fields": None,  # lista de ids de colunas, na ordem do cartão; vazio = os campos padrão
    "show_weekends": True,
    "show_completed": True,
}


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def clean_calendar_settings(columns, raw, current=None):
    """Configuração completa e válida: `current` + o que veio em `raw`. `columns` são as colunas ativas do quadro.

    Só se aceitam as chaves conhecidas, e toda referência a coluna tem de ser de uma coluna ATIVA DESTE quadro do tipo
    certo (o JSON vem do navegador: um id de outro quadro ou de outro tipo é recusado).
    """
    by_id = {column.pk: column for column in columns}
    clean = {key: (list(value) if isinstance(value, list) else value) for key, value in DEFAULT_SETTINGS.items()}
    for key, value in (current or {}).items():
        if key in clean:
            clean[key] = list(value) if isinstance(value, list) else value

    for key, value in (raw or {}).items():
        if key == "date_field":
            if value in (None, ""):
                clean[key] = None
                continue
            column = by_id.get(_to_int(value))
            if column is None or column.type not in DATE_TYPES:
                raise ValidationError("Para usar o Calendário, escolha uma coluna de Data.")
            clean[key] = column.pk
        elif key == "period":
            if value not in PERIODS:
                raise ValidationError("Escala do calendário inválida.")
            clean[key] = value
        elif key == "color_by":
            if value in (None, ""):
                clean[key] = None
            elif value in (COLOR_GROUP, COLOR_NONE):
                clean[key] = value
            else:
                column = by_id.get(_to_int(value))
                if column is None or column.type not in COLORABLE_TYPES:
                    raise ValidationError("Colorir por: escolha uma coluna de Status ou de Lista suspensa, o grupo ou sem cor.")
                clean[key] = column.pk
        elif key in ("show_weekends", "show_completed"):
            clean[key] = _bool(value)
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
                raise ValidationError(f"O cartão do calendário aceita até {MAX_CARD_FIELDS} campos.")
            clean[key] = ids
    return clean


def complete_new_settings(columns, settings):
    """Ao criar a visualização, grava as escolhas que o servidor faria sozinho (a coluna de Data e a de cor): o calendário
    passa a ler EXATAMENTE a coluna escolhida, e criar outra coluna de Data depois não troca a lente de lugar."""
    clean = clean_calendar_settings(columns, settings or {})
    date_column = resolve_date_column(clean, columns)
    if date_column is None:
        raise ValidationError("Para usar o Calendário, escolha ou crie uma coluna de Data.")
    clean["date_field"] = date_column.pk
    if clean["color_by"] is None:
        kind, column = resolve_color_source(clean, columns)
        clean["color_by"] = column.pk if column is not None else kind
    return clean


# ---------------------------------------------------------------------------
# Colunas que a configuração aponta
# ---------------------------------------------------------------------------


def date_columns(columns):
    return [column for column in columns if column.type in DATE_TYPES]


def colorable_columns(columns):
    return [column for column in columns if column.type in COLORABLE_TYPES]


def resolve_date_column(settings, columns):
    """A coluna de Data da lente: a escolhida (se ainda existe e é Data) ou, na falta, a coluna marcada como prazo, ou a
    primeira Data do quadro. `None` quando o quadro não tem nenhuma."""
    candidates = date_columns(columns)
    chosen = _to_int((settings or {}).get("date_field"))
    for column in candidates:
        if column.pk == chosen:
            return column
    for column in candidates:
        if (column.settings or {}).get("is_deadline"):
            return column
    return candidates[0] if candidates else None


def resolve_status_column(columns):
    """A coluna que diz se o item está concluído: a primeira de Status. (Listas suspensas e outras colunas de etiqueta
    não decidem isso: uma "Sem pendência" marcada como concluída não pode esconder o item do calendário.)"""
    for column in columns:
        if column.type == T.STATUS:
            return column
    return None


def resolve_color_source(settings, columns):
    """`("column", coluna)`, `("group", None)` ou `("none", None)`. Automático = a primeira coluna de Status, depois a
    primeira de Lista suspensa; quadro sem nenhuma das duas usa a cor do grupo."""
    choice = (settings or {}).get("color_by")
    if choice == COLOR_NONE:
        return COLOR_NONE, None
    if choice == COLOR_GROUP:
        return COLOR_GROUP, None
    chosen = _to_int(choice)
    candidates = colorable_columns(columns)
    for column in candidates:
        if column.pk == chosen:
            return "column", column
    for kind in COLORABLE_TYPES:
        for column in candidates:
            if column.type == kind:
                return "column", column
    return COLOR_GROUP, None


def resolve_card_columns(settings, columns, date_column, color_column):
    """Campos do cartão, na ordem. Sem escolha: a cor (Status, para o texto dizer o que a cor diz), a primeira Pessoa e
    depois os demais campos visíveis, no máximo `DEFAULT_CARD_FIELD_COUNT`. A coluna de Data da lente não entra: o dia
    já a mostra."""
    by_id = {column.pk: column for column in columns}
    chosen = (settings or {}).get("card_fields")
    if isinstance(chosen, list):
        return [by_id[pk] for pk in (_to_int(entry) for entry in chosen) if pk in by_id]
    pool = [
        column for column in columns
        if column.is_visible and (date_column is None or column.pk != date_column.pk)
    ]
    ordered = []
    if color_column is not None and color_column in pool:
        ordered.append(color_column)
    person = next((column for column in pool if column.type == T.PERSON and column not in ordered), None)
    if person is not None:
        ordered.append(person)
    ordered.extend(column for column in pool if column not in ordered)
    return ordered[:DEFAULT_CARD_FIELD_COUNT]


# ---------------------------------------------------------------------------
# Período
# ---------------------------------------------------------------------------


def parse_month(value, today=None):
    """"2026-10" -> (2026, 10). Ausente ou inválido: o mês de hoje."""
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", str(value or "").strip())
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        if 1900 <= year <= 2200 and 1 <= month <= 12:
            return year, month
    today = today or timezone.localdate()
    return today.year, today.month


def month_key(year, month):
    return f"{year:04d}-{month:02d}"


def shift_month(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def month_title(year, month):
    return f"{MONTH_NAMES[month - 1]} {year}"


def grid_range(year, month):
    """Primeiro e último dia da grade: a semana (segunda a domingo) que contém o dia 1 até a que contém o último dia."""
    first = datetime.date(year, month, 1)
    last = datetime.date(year, month, calendar.monthrange(year, month)[1])
    return first - datetime.timedelta(days=first.weekday()), last + datetime.timedelta(days=6 - last.weekday())


# ---------------------------------------------------------------------------
# Itens no calendário
# ---------------------------------------------------------------------------


def cell_has_value(cell, column):
    if cell is None:
        return False
    if column.type in COLORABLE_TYPES:
        return getattr(cell, "option", None) is not None
    if column.type == T.PERSON:
        return getattr(cell, "person", None) is not None
    if column.type == T.CHECKBOX:
        return cell.value_boolean is not None
    return bool(getattr(cell, "display", ""))


def item_is_done(item, status_column):
    if status_column is None:
        return False
    cell = item.cell_map.get(status_column.pk)
    option = getattr(cell, "option", None) if cell is not None else None
    return bool(option is not None and option.is_done)


def item_when(item, date_column):
    """`(dia, hora "HH:MM" ou "")` do item na coluna de Data. A hora só existe quando a coluna exibe horário E a célula foi
    preenchida com um (dia sem hora é "dia inteiro": nunca se inventa 00:00)."""
    cell = item.cell_map.get(date_column.pk)
    if cell is None or cell.value_date is None:
        return None, ""
    if (date_column.settings or {}).get("show_time") and cell.value_datetime is not None:
        return cell.value_date, timezone.localtime(cell.value_datetime).strftime("%H:%M")
    return cell.value_date, ""


def entry_color(item, color_kind, color_column):
    """`(cor, texto)`: a cor do cartão e o que ela quer dizer, para o leitor de tela e para quem não distingue cores."""
    if color_kind == "column" and color_column is not None:
        cell = item.cell_map.get(color_column.pk)
        option = getattr(cell, "option", None) if cell is not None else None
        if option is not None:
            return option.color, f"{color_column.name}: {option.label}"
        return NEUTRAL_COLOR, f"{color_column.name}: sem etiqueta"
    if color_kind == COLOR_GROUP:
        group = item.group
        return group.color, f"Grupo: {group.name}"
    return NEUTRAL_COLOR, ""


def build_month(year, month, items, *, date_column, status_column, color_kind, color_column, card_columns,
                show_weekends=True, show_completed=True, today=None):
    """A grade do mês. `items` precisam de `cell_map` (ver `BoardQueryService.attach_cells`) e já vêm no intervalo da grade.

    Devolve `weeks` (cada semana, uma lista de dias), `weekdays` (rótulos das colunas) e contagens. Cada dia traz `entries`
    (todos os cartões do dia: sem hora primeiro, na ordem do quadro; depois os com hora, por horário), `more` (quantos
    passam do limite visual) e `blocked` (dia que a coluna de Data não aceita, ex.: fim de semana proibido).
    """
    today = today or timezone.localdate()
    start, end = grid_range(year, month)
    allow_weekends = (date_column.settings or {}).get("allow_weekends", True)
    is_deadline = bool((date_column.settings or {}).get("is_deadline"))

    by_day = {}
    hidden_weekend = 0
    for position, item in enumerate(items):
        day, clock = item_when(item, date_column)
        if day is None or not (start <= day <= end):
            continue
        done = item_is_done(item, status_column)
        if done and not show_completed:
            continue
        if not show_weekends and day.weekday() >= 5:
            hidden_weekend += 1
            continue
        color, color_label = entry_color(item, color_kind, color_column)
        fields = [
            {"column": column, "cell": item.cell_map[column.pk]}
            for column in card_columns
            if cell_has_value(item.cell_map.get(column.pk), column)
        ]
        by_day.setdefault(day, []).append({
            "item": item,
            "date": day,
            "iso": day.isoformat(),
            "time": clock,
            "color": color,
            "color_label": color_label,
            "done": done,
            "overdue": bool(is_deadline and not done and day < today),
            "fields": fields,
            "_order": (clock != "", clock, position),
        })

    weeks, total = [], 0
    cursor = start
    while cursor <= end:
        week = []
        for offset in range(7):
            day = cursor + datetime.timedelta(days=offset)
            if not show_weekends and day.weekday() >= 5:
                continue
            entries = sorted(by_day.get(day, []), key=lambda entry: entry["_order"])
            for index, entry in enumerate(entries):
                entry["overflow"] = index >= MAX_VISIBLE_PER_DAY
            total += len(entries)
            week.append({
                "date": day,
                "iso": day.isoformat(),
                "number": day.day,
                "label": f"{day.day} de {MONTH_NAMES[day.month - 1]}",
                "month_abbr": MONTH_ABBR[day.month - 1],
                "show_month": day.day == 1,
                "in_month": day.month == month and day.year == year,
                "is_today": day == today,
                "is_weekend": day.weekday() >= 5,
                "blocked": day.weekday() >= 5 and not allow_weekends,
                "entries": entries,
                "more": max(0, len(entries) - MAX_VISIBLE_PER_DAY),
            })
        weeks.append(week)
        cursor += datetime.timedelta(days=7)

    prev_year, prev_month = shift_month(year, month, -1)
    next_year, next_month = shift_month(year, month, 1)
    labels = WEEKDAY_LABELS if show_weekends else WEEKDAY_LABELS[:5]
    return {
        "weeks": weeks,
        "weekdays": list(labels),
        "columns": len(labels),
        "key": month_key(year, month),
        "title": month_title(year, month),
        "prev": month_key(prev_year, prev_month),
        "next": month_key(next_year, next_month),
        "today": month_key(today.year, today.month),
        "start": start,
        "end": end,
        "total": total,
        "hidden_weekend": hidden_weekend,
        "is_current": (year, month) == (today.year, today.month),
    }
