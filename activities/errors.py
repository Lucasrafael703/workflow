"""Erro de regra de negócio do núcleo de atividades.

Fica num módulo próprio para que serviços e políticas de transição possam
levantá-lo sem depender um do outro (`activities.services` o reexporta, então
`from .services import ActivityError` continua valendo).
"""


class ActivityError(Exception):
    """Levantado para qualquer transição/ação inválida do núcleo de atividades.
    Views capturam esta exceção e exibem a mensagem via django.contrib.messages."""


class ActivityPermissionError(ActivityError):
    """A pessoa não tem a ação do catálogo no escopo do recurso (negação do motor de autorização).

    É subclasse de `ActivityError`: todo `except ActivityError` existente continua tratando a negação como antes.
    Quem precisa distinguir (as respostas JSON da edição inline: 403 para permissão, 400 para regra de negócio)
    captura este tipo primeiro."""
