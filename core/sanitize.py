import nh3

# Allowlist mínima para o editor de descrição (negrito/itálico/sublinhado/
# lista/link) — qualquer outra tag ou atributo é removido pelo nh3, nunca
# apenas "escapado". Esta é a ÚNICA porta de entrada de HTML de usuário no
# projeto: nenhum campo pode ser renderizado com `|safe` sem passar por aqui.
ALLOWED_TAGS = {"p", "br", "strong", "em", "u", "ul", "ol", "li", "a"}
ALLOWED_ATTRIBUTES = {"a": {"href"}}


def sanitize_description(raw):
    """Limpa HTML de um campo de descrição rica antes de salvar no banco."""
    return nh3.clean(
        raw or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        link_rel="noopener noreferrer nofollow",
    )
