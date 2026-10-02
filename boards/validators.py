"""Validação e formatação do valor de uma célula, sempre pelo tipo da coluna (e pela configuração dela).

O navegador pode validar para ajudar, mas aqui é onde vale: moeda vira `Decimal`, data vira `date`, pessoa é
alguém da mesma organização, etiqueta é uma etiqueta ativa da mesma coluna, checkbox é booleano.
"""

import datetime
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from .models import BoardColumn

MAX_TEXT_LENGTH = 5000
#: Cabe em Decimal(24, 6) com folga.
MAX_ABSOLUTE_NUMBER = Decimal("1000000000000000")
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
TRUE_VALUES = {True, 1, "1", "true", "True", "on", "sim", "Sim"}
FALSE_VALUES = {False, 0, "0", "false", "False", "off", "nao", "não", "Não"}

DEFAULT_SETTINGS = {
    BoardColumn.Type.DATE: {"show_time": False, "allow_weekends": True, "is_deadline": False, "format": "DD/MM/YYYY"},
    BoardColumn.Type.NUMBER: {"decimal_places": 2, "unit": "", "minimum": None, "maximum": None},
    BoardColumn.Type.CURRENCY: {"currency": "BRL", "decimal_places": 2, "minimum": None, "maximum": None},
    BoardColumn.Type.PERSON: {"multiple": False},
}
CURRENCY_SYMBOLS = {"BRL": "R$", "USD": "US$", "EUR": "€"}


def default_settings_for(column_type):
    return dict(DEFAULT_SETTINGS.get(column_type, {}))


def clean_color(value, default):
    value = (value or default or "").strip()
    if not HEX_COLOR.match(value):
        raise ValidationError("Escolha uma cor válida.")
    return value.upper()


def _as_decimal(raw):
    text = str(raw).strip().replace(" ", "")
    if "," in text and "." in text:
        # 1.234,56 (pt-BR): o ponto é separador de milhar
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        raise ValidationError("Informe um número válido.")
    if not value.is_finite() or abs(value) >= MAX_ABSOLUTE_NUMBER:
        raise ValidationError("Informe um número válido.")
    return value


def _quantize(value, places):
    if places is None:
        return value
    return value.quantize(Decimal(1).scaleb(-int(places)), rounding=ROUND_HALF_UP)


def normalize_cell_value(column, raw_value):
    """Devolve {"kind": ..., "value": ...}. `kind == "empty"` significa limpar a célula."""
    column_type = column.type
    config = {**default_settings_for(column_type), **(column.settings or {})}

    if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
        if column.is_required:
            raise ValidationError(f"“{column.name}” é obrigatória.")
        return {"kind": "empty", "value": None}

    if column_type == BoardColumn.Type.TEXT:
        text = str(raw_value).strip()
        if len(text) > MAX_TEXT_LENGTH:
            raise ValidationError(f"O texto pode ter até {MAX_TEXT_LENGTH} caracteres.")
        return {"kind": "text", "value": text}

    if column_type in (BoardColumn.Type.NUMBER, BoardColumn.Type.CURRENCY):
        value = _quantize(_as_decimal(raw_value), config.get("decimal_places"))
        minimum, maximum = config.get("minimum"), config.get("maximum")
        if minimum is not None and value < Decimal(str(minimum)):
            raise ValidationError(f"O valor mínimo é {minimum}.")
        if maximum is not None and value > Decimal(str(maximum)):
            raise ValidationError(f"O valor máximo é {maximum}.")
        return {"kind": "number", "value": value}

    if column_type == BoardColumn.Type.DATE:
        return {"kind": "date", "value": _normalize_date(raw_value, config)}

    if column_type == BoardColumn.Type.CHECKBOX:
        if raw_value in TRUE_VALUES:
            return {"kind": "boolean", "value": True}
        if raw_value in FALSE_VALUES:
            return {"kind": "boolean", "value": False}
        raise ValidationError("Valor inválido para a confirmação.")

    if column_type == BoardColumn.Type.PERSON:
        try:
            return {"kind": "person_id", "value": int(raw_value)}
        except (TypeError, ValueError):
            raise ValidationError("Pessoa inválida.")

    if column_type in BoardColumn.OPTION_TYPES:
        try:
            return {"kind": "option_id", "value": int(raw_value)}
        except (TypeError, ValueError):
            raise ValidationError("Opção inválida.")

    raise ValidationError("Este tipo de coluna ainda não aceita edição.")


def _normalize_date(raw, config):
    """Data pura, ou data e hora quando a coluna mostra horário. Devolve (data, datetime|None)."""
    if isinstance(raw, datetime.datetime):
        moment = raw
    elif isinstance(raw, datetime.date):
        moment = None
        day = raw
    else:
        text = str(raw).strip()
        try:
            # `parse_*` levantam ValueError para data bem formada mas impossível (2025-13-01, 2025-02-30)
            moment = parse_datetime(text) if ("T" in text or " " in text) else None
            day = None if moment else (parse_date(text) or _parse_br_date(text))
        except ValueError:
            raise ValidationError("Informe uma data válida.")
        if moment is None and day is None:
            raise ValidationError("Informe uma data válida.")
    if moment is not None:
        if timezone.is_naive(moment):
            moment = timezone.make_aware(moment)
        day = timezone.localtime(moment).date()
    if not config.get("allow_weekends", True) and day.weekday() >= 5:
        raise ValidationError("Esta coluna não aceita sábado nem domingo.")
    if config.get("show_time") and moment is not None:
        return (day, moment)
    return (day, None)


def _parse_br_date(text):
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
    if not match:
        return None
    try:
        return datetime.date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Configuração do tipo (R07): só chaves conhecidas, com tipo e limite conferidos.
# ---------------------------------------------------------------------------

ALLOWED_SETTINGS = {
    BoardColumn.Type.DATE: {"show_time", "allow_weekends", "is_deadline", "format"},
    BoardColumn.Type.NUMBER: {"decimal_places", "unit", "minimum", "maximum"},
    BoardColumn.Type.CURRENCY: {"currency", "decimal_places", "minimum", "maximum"},
    BoardColumn.Type.PERSON: {"multiple"},
}
DATE_FORMATS = ("DD/MM/YYYY", "DD/MM/YY", "YYYY-MM-DD")


def _bool(value):
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ValidationError("Valor inválido na configuração.")


def _optional_decimal(value):
    if value in (None, ""):
        return None
    return float(_as_decimal(value))


def clean_column_settings(column_type, raw):
    """Valida a configuração enviada e devolve o dicionário completo (padrões + o que veio)."""
    allowed = ALLOWED_SETTINGS.get(column_type, set())
    raw = {key: value for key, value in (raw or {}).items() if key in allowed}
    clean = default_settings_for(column_type)
    for key, value in raw.items():
        if key in {"show_time", "allow_weekends", "is_deadline"}:
            clean[key] = _bool(value)
        elif key == "multiple":
            if _bool(value):
                raise ValidationError("Várias pessoas ficam para uma versão futura.")
            clean[key] = False
        elif key == "decimal_places":
            try:
                places = int(value)
            except (TypeError, ValueError):
                raise ValidationError("Casas decimais inválidas.")
            if not 0 <= places <= 6:
                raise ValidationError("Use de 0 a 6 casas decimais.")
            clean[key] = places
        elif key in {"minimum", "maximum"}:
            clean[key] = _optional_decimal(value)
        elif key == "currency":
            if value not in CURRENCY_SYMBOLS:
                raise ValidationError("Moeda não aceita.")
            clean[key] = value
        elif key == "format":
            if value not in DATE_FORMATS:
                raise ValidationError("Formato de data não aceito.")
            clean[key] = value
        elif key == "unit":
            clean[key] = str(value or "").strip()[:12]
    minimum, maximum = clean.get("minimum"), clean.get("maximum")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValidationError("O mínimo não pode ser maior que o máximo.")
    return clean


# ---------------------------------------------------------------------------
# Texto exibido (auditoria, JSON e células) — um só lugar para o formato brasileiro.
# ---------------------------------------------------------------------------


def format_number(value, places):
    if value is None:
        return ""
    places = 6 if places is None else int(places)
    text = f"{Decimal(value):,.{places}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def format_date(value, pattern="DD/MM/YYYY"):
    if value is None:
        return ""
    if pattern == "YYYY-MM-DD":
        return value.isoformat()
    year = f"{value.year:04d}"
    return f"{value.day:02d}/{value.month:02d}/{year[2:] if pattern == 'DD/MM/YY' else year}"
