"""Paleta oficial de cores configuráveis (36 cores fixas) e resolução de cor
por organização para os enums de status/prioridade (Regras: cor é só visual,
nunca regra de negócio).

Espelha `static/js/color-utils.js` — mesma paleta, mesma fórmula de
contraste. Qualquer mudança aqui precisa ser replicada lá também.
"""

PALETTE = [
    # Verdes
    ("#84CC16", "Lima"),
    ("#22C55E", "Verde"),
    ("#16A34A", "Verde escuro"),
    ("#10B981", "Esmeralda"),
    ("#14B8A6", "Turquesa"),
    ("#0F766E", "Petróleo"),
    # Amarelos e laranjas
    ("#FACC15", "Amarelo"),
    ("#EAB308", "Ouro"),
    ("#F59E0B", "Âmbar"),
    ("#FB923C", "Laranja claro"),
    ("#F97316", "Laranja"),
    ("#EA580C", "Laranja escuro"),
    # Vermelhos e rosas
    ("#FF6B4A", "Coral"),
    ("#F87171", "Vermelho claro"),
    ("#EF4444", "Vermelho"),
    ("#EC4899", "Rosa"),
    ("#DB2777", "Pink"),
    ("#BE123C", "Vinho"),
    # Roxos
    ("#C084FC", "Lilás"),
    ("#A855F7", "Roxo claro"),
    ("#9333EA", "Roxo"),
    ("#7C3AED", "Violeta"),
    ("#6D28D9", "Roxo escuro"),
    ("#4F46E5", "Índigo"),
    # Azuis
    ("#60A5FA", "Azul claro"),
    ("#3B82F6", "Azul"),
    ("#2563EB", "Azul forte"),
    ("#1D4ED8", "Azul escuro"),
    ("#38BDF8", "Ciano"),
    ("#0E7490", "Azul petróleo"),
    # Neutros e terrosos
    ("#CBD5E1", "Cinza claro"),
    ("#94A3B8", "Cinza"),
    ("#64748B", "Cinza médio"),
    ("#475569", "Grafite"),
    ("#8B5E4A", "Marrom"),
    ("#BFA98A", "Bege"),
]

PALETTE_NAMES = dict(PALETTE)
PALETTE_HEX_SET = frozenset(hex_value for hex_value, _ in PALETTE)

DEFAULT_COLOR = "#94A3B8"

# Domínios reconhecidos por EnumColor — cada um mapeia para o TextChoices
# Python real que continua sendo a única fonte do significado operacional.
DOMAIN_ACTIVITY_STATUS = "activity_status"
DOMAIN_TASK_STATUS = "task_status"
DOMAIN_ACTIVITY_URGENCY = "activity_urgency"

# Defaults LPS — nunca vivem no banco: são a fonte de verdade em runtime
# sempre que a organização não customizou o code correspondente.
DEFAULTS = {
    DOMAIN_ACTIVITY_STATUS: {
        "RASCUNHO": "#CBD5E1",
        "ABERTA": "#94A3B8",
        "EM_ANDAMENTO": "#3B82F6",
        "BLOQUEADA": "#EF4444",
        "PENDENTE": "#F59E0B",
        "CONCLUIDA": "#22C55E",
        "CANCELADA": "#475569",
    },
    DOMAIN_TASK_STATUS: {
        "NAO_INICIADA": "#94A3B8",
        "DISPONIVEL": "#CBD5E1",
        "EM_FILA": "#64748B",
        "EM_EXECUCAO": "#3B82F6",
        "BLOQUEADA": "#EF4444",
        "DEVOLVIDA": "#F59E0B",
        "CONCLUIDA": "#22C55E",
        "CANCELADA": "#475569",
    },
    DOMAIN_ACTIVITY_URGENCY: {
        "BAIXA": "#64748B",
        "MEDIA": "#F59E0B",
        "ALTA": "#EF4444",
    },
}

# Remapeamento de Tag.color (antigo IntegerChoices 0-6) para a nova paleta
# hex — usado apenas pela migração de dados, duplicado lá para que a
# migração nunca dependa deste módulo (código de app pode mudar; migrações
# não devem).
TAG_LEGACY_COLOR_MAP = {
    0: "#94A3B8",  # CINZA
    1: "#3B82F6",  # AZUL
    2: "#22C55E",  # VERDE
    3: "#FACC15",  # AMARELO
    4: "#F97316",  # LARANJA
    5: "#EF4444",  # VERMELHO
    6: "#9333EA",  # ROXO
}


def valid_codes_for(domain):
    """Codes reais aceitos para um domínio — nunca um valor arbitrário
    digitado, sempre o vocabulário fixo do TextChoices Python correspondente."""
    return frozenset(DEFAULTS.get(domain, {}))


def is_valid_palette_color(hex_value):
    return (hex_value or "").upper() in {h.upper() for h in PALETTE_HEX_SET}


def _hex_to_rgb(hex_value):
    value = hex_value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _relative_luminance(hex_value):
    r, g, b = _hex_to_rgb(hex_value)
    channels = []
    for component in (r, g, b):
        c = component / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_ratio(luminance_a, luminance_b):
    lighter, darker = max(luminance_a, luminance_b), min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)


def get_contrast_text(background_hex):
    """Luminância relativa WCAG: nunca deixa o texto ilegível sobre a cor
    escolhida. Espelha getContrastText() em static/js/color-utils.js."""
    try:
        bg_luminance = _relative_luminance(background_hex)
    except (ValueError, IndexError):
        return "#1F2937"
    contrast_with_white = _contrast_ratio(bg_luminance, 1.0)
    contrast_with_black = _contrast_ratio(bg_luminance, 0.0)
    return "#1F2937" if contrast_with_black > contrast_with_white else "#FFFFFF"


class EnumColorResolver:
    """Resolve a aparência efetiva (customizada pela organização, ou default
    LPS) de todos os codes de um domínio — uma única query por instância,
    nunca por code, para não reintroduzir N+1 ao listar muitas
    atividades/tarefas. Cor, nome exibido, descrição e oculto vêm todos
    dessa mesma query."""

    def __init__(self, organization, domain):
        from .models import EnumColor

        self.domain = domain
        self._defaults = DEFAULTS.get(domain, {})
        if organization is None:
            self._overrides = {}
        else:
            self._overrides = {
                code: (color, label, description, is_hidden)
                for code, color, label, description, is_hidden in EnumColor.objects.filter(
                    organization=organization, domain=domain
                ).values_list("code", "color", "label", "description", "is_hidden")
            }

    def color_for(self, code):
        override = self._overrides.get(code)
        color = override[0] if override else None
        return color or self._defaults.get(code, DEFAULT_COLOR)

    def text_for(self, code):
        return get_contrast_text(self.color_for(code))

    def label_for(self, code, default_label):
        override = self._overrides.get(code)
        label = override[1] if override else None
        return label or default_label

    def description_for(self, code, default_description=""):
        override = self._overrides.get(code)
        description = override[2] if override else None
        return description or default_description

    def is_hidden(self, code):
        override = self._overrides.get(code)
        return bool(override[3]) if override else False
