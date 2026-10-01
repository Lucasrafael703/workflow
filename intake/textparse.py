"""Leitura de texto livre em português, sem banco e sem dependências externas.

Tudo aqui é função pura: recebe texto (e uma data de referência) e devolve o que
conseguiu entender, ou nada. As regras são de propósito simples e explicáveis;
quando houver dúvida, o resultado é "não identificado", nunca um palpite.
"""

import datetime
import hashlib
import re
import unicodedata
from dataclasses import dataclass

from django.utils import timezone

SUBJECT_LIMIT = 200
TITLE_FROM_LINE_LIMIT = 120

# Provedores gratuitos não dizem nada sobre qual é o cliente.
FREE_EMAIL_LABELS = frozenset(
    {"gmail", "hotmail", "outlook", "yahoo", "uol", "bol", "icloud", "terra", "live", "msn", "ig", "globo", "proton", "protonmail"}
)

_COMBINING = re.compile(r"[̀-ͯ]")
_SPACES = re.compile(r"\s+")


def normalize(text):
    """Minúsculas, sem acento e com espaços colapsados — base de todo casamento."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return _SPACES.sub(" ", _COMBINING.sub("", decomposed).casefold()).strip()


def content_signature(sender_email, subject, raw_content):
    """Assinatura (sha256) do que foi recebido, para reconhecer a mesma solicitação colada duas vezes."""
    parts = (normalize(sender_email), normalize(subject), normalize(raw_content))
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def contains_phrase(normalized_text, normalized_phrase):
    """A frase aparece como palavra(s) inteira(s)? ("Aurora" não casa "auroras")."""
    if not normalized_phrase:
        return False
    pattern = r"(?<!\w)" + re.escape(normalized_phrase) + r"(?!\w)"
    return re.search(pattern, normalized_text) is not None


# ---------------------------------------------------------------------------
# Assunto, domínio e primeira linha útil
# ---------------------------------------------------------------------------

_SUBJECT_PREFIX = re.compile(r"^\s*(?:(?:re|res|enc|fw|fwd|rv)\s*(?:\[\d+\])?\s*:\s*)+", re.IGNORECASE)


def clean_subject(subject):
    """Tira os "RE:", "ENC:", "FW:" repetidos do começo e limita o tamanho."""
    cleaned = _SPACES.sub(" ", _SUBJECT_PREFIX.sub("", subject or "")).strip()
    return cleaned[:SUBJECT_LIMIT].strip()


def email_domain(email):
    """Domínio do e-mail em minúsculas, ou "" se não houver."""
    email = (email or "").strip().lower()
    return email.rsplit("@", 1)[1] if "@" in email else ""


def is_free_domain(domain):
    return bool(domain) and domain.split(".")[0] in FREE_EMAIL_LABELS


def same_domain(first, second):
    """Mesmo domínio, aceitando subdomínio (mail.convivy.com.br ~ convivy.com.br)."""
    if not first or not second:
        return False
    return first == second or first.endswith("." + second) or second.endswith("." + first)


_GREETING = re.compile(
    r"^\s*(?:bom dia|boa tarde|boa noite|ol[aá]|oi|prezad[oa]s?(?:\s+senhor[ae]s?)?|caro|cara|senhor[ae]s?)\b[\s,!.:;\-–—]*",
    re.IGNORECASE,
)
_HEADER_LINE = re.compile(
    r"^\s*(?:de|para|cc|cco|enviado|enviada|assunto|data|from|to|subject|sent|date)\s*:", re.IGNORECASE
)


def first_useful_line(text, limit=TITLE_FROM_LINE_LIMIT):
    """Primeira linha com conteúdo, sem saudação nem cabeçalho de e-mail colado."""
    for line in (text or "").splitlines():
        if not line.strip() or _HEADER_LINE.match(line):
            continue
        remainder = line
        while True:
            stripped = _GREETING.sub("", remainder, count=1)
            if stripped == remainder:
                break
            remainder = stripped
        remainder = _SPACES.sub(" ", remainder).strip()
        if not remainder:
            continue
        if len(remainder) <= limit:
            return remainder
        cut = remainder[: limit - 1].rsplit(" ", 1)[0] or remainder[: limit - 1]
        return f"{cut.rstrip(' ,;:.-')}…"
    return ""


# ---------------------------------------------------------------------------
# Prazo em português
# ---------------------------------------------------------------------------

WEEKDAYS = {
    "segunda": 0,
    "terca": 1,
    "quarta": 2,
    "quinta": 3,
    "sexta": 4,
    "sabado": 5,
    "domingo": 6,
}
WEEKDAY_NAMES = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
DEFAULT_TIME = datetime.time(23, 59)

# Uma só expressão: em cada posição vale a primeira alternativa que casa, então
# "dia 15/10" é lido como data completa e não como "dia 15".
_DEADLINE_EXPRESSION = re.compile(
    r"""
    (?P<relative>(?<!\w)(?:depois\ de\ amanha|amanha|hoje)(?!\w))
    | (?P<iso>(?<![\d/\-.])(?P<iso_year>\d{4})-(?P<iso_month>\d{2})-(?P<iso_day>\d{2})(?!\d))
    | (?P<numeric>(?<![\d/\-.])(?:dia\s+)?(?P<n_day>\d{1,2})\s*[/\-]\s*(?P<n_month>\d{1,2})
        (?:\s*[/\-]\s*(?P<n_year>\d{4}|\d{2}))?(?![\d/\-]))
    | (?P<written>(?<!\w)(?:dia\s+)?(?P<w_day>\d{1,2})\s+de\s+(?P<w_month>janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)
        (?:\s+de\s+(?P<w_year>\d{4}))?(?!\w))
    | (?P<weekday>(?<!\w)(?P<wd>segunda|terca|quarta|quinta|sexta|sabado|domingo)(?:[-\ ]feira)?(?!\w))
    | (?P<day_only>(?<!\w)dia\s+(?P<d_day>\d{1,2})(?![\d/\-]))
    """,
    re.VERBOSE,
)
_CUE = re.compile(r"(?<!\w)(?:ate|para|prazo|entrega|entregar|entregue|vence|vencimento|maximo|limite)(?!\w)")
_CUE_WINDOW = 30
_TIME_AFTER = re.compile(
    r"^[\s,;.\-]*(?:(?:as|a|ate as|ate|pelas|por volta das)\s+)?(\d{1,2})\s*"
    r"(?::\s*(\d{2})|h(?![a-z])\s*(\d{2})?|hs(?![a-z])|horas?(?![a-z]))"
)


@dataclass(frozen=True)
class ParsedDeadline:
    value: datetime.datetime  # com fuso, no horário local
    reason: str


def _reference_date(reference):
    if reference is None:
        reference = timezone.now()
    if timezone.is_aware(reference):
        reference = timezone.localtime(reference)
    return reference.date()


def _safe_date(year, month, day):
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def _next_day_of_month(reference, day):
    """Próximo dia N, neste mês se ainda não passou, senão no primeiro mês que o tenha."""
    year, month = reference.year, reference.month
    for _ in range(13):
        candidate = _safe_date(year, month, day)
        if candidate and candidate >= reference:
            return candidate
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return None


def _next_day_month(reference, day, month):
    """Próxima ocorrência de dia/mês em ou depois da referência (vira o ano se já passou)."""
    for year in (reference.year, reference.year + 1):
        candidate = _safe_date(year, month, day)
        if candidate and candidate >= reference:
            return candidate
    return None


def _full_year(year):
    year = int(year)
    return year + 2000 if year < 100 else year


def _resolve(match, reference):
    """Data que a expressão representa, ou None (inválida / já passou)."""
    groups = match.groupdict()

    if groups["relative"]:
        word = groups["relative"]
        return reference + datetime.timedelta(days=2 if word.startswith("depois") else 1 if word == "amanha" else 0)

    if groups["iso"]:
        explicit = _safe_date(int(groups["iso_year"]), int(groups["iso_month"]), int(groups["iso_day"]))
        return explicit if explicit and explicit >= reference else None

    if groups["numeric"]:
        day, month = int(groups["n_day"]), int(groups["n_month"])
        if groups["n_year"]:
            explicit = _safe_date(_full_year(groups["n_year"]), month, day)
            return explicit if explicit and explicit >= reference else None
        return _next_day_month(reference, day, month)

    if groups["written"]:
        day, month = int(groups["w_day"]), MONTHS[groups["w_month"]]
        if groups["w_year"]:
            explicit = _safe_date(int(groups["w_year"]), month, day)
            return explicit if explicit and explicit >= reference else None
        return _next_day_month(reference, day, month)

    if groups["weekday"]:
        # Estritamente depois da referência: "até sexta" escrito numa sexta é a próxima.
        delta = (WEEKDAYS[groups["wd"]] - reference.weekday()) % 7 or 7
        return reference + datetime.timedelta(days=delta)

    if groups["day_only"]:
        return _next_day_of_month(reference, int(groups["d_day"]))

    return None


def _time_after(normalized_text, end):
    found = _TIME_AFTER.match(normalized_text[end : end + 30])
    if not found:
        return DEFAULT_TIME
    hour = int(found.group(1))
    minute = int(found.group(2) or found.group(3) or 0)
    if hour > 23 or minute > 59:
        return DEFAULT_TIME
    return datetime.time(hour, minute)


def _spoken(match):
    """Como a pessoa escreveu, já com acento, para mostrar na dica da tela."""
    groups = match.groupdict()
    if groups["relative"]:
        return {"amanha": "amanhã", "depois de amanha": "depois de amanhã"}.get(groups["relative"], groups["relative"])
    if groups["weekday"]:
        return WEEKDAY_NAMES[WEEKDAYS[groups["wd"]]]
    return match.group(0).strip().replace("marco", "março")


def _describe(match, resolved):
    weekday = WEEKDAY_NAMES[resolved.weekday()]
    verb = "interpretado como" if match.group("weekday") else "lido como"
    return f"Prazo: \"{_spoken(match)}\" {verb} {weekday}, {resolved:%d/%m/%Y}"


def parse_deadline(text, reference=None, *, require_cue=True):
    """Primeiro prazo que o texto indica, ou None.

    `require_cue=True` (texto livre) só aceita uma data precedida de uma pista de
    prazo ("até", "para", "prazo", "entregar", "vence"…) logo antes; num assunto
    (`require_cue=False`) qualquer data conta. Sem hora, vale até 23:59, como no
    editor de atividade. Não entende "semana que vem", "fim do mês" nem "urgente".
    """
    normalized = normalize(text)
    if not normalized:
        return None
    reference_date = _reference_date(reference)

    for match in _DEADLINE_EXPRESSION.finditer(normalized):
        if require_cue:
            window = normalized[max(0, match.start() - _CUE_WINDOW) : match.start()]
            if not _CUE.search(window):
                continue
        resolved = _resolve(match, reference_date)
        if resolved is None:
            continue
        moment = datetime.datetime.combine(resolved, _time_after(normalized, match.end()))
        return ParsedDeadline(
            value=timezone.make_aware(moment, timezone.get_current_timezone()),
            reason=_describe(match, resolved),
        )
    return None


def weekday_label(value):
    """Dia da semana por extenso, para o rótulo "sexta, 10/10" na tela."""
    local = timezone.localtime(value) if timezone.is_aware(value) else value
    return WEEKDAY_NAMES[local.weekday()]
