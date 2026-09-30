"""Erro de regra de negócio do núcleo de atividades.

Fica num módulo próprio para que serviços e políticas de transição possam
levantá-lo sem depender um do outro (`activities.services` o reexporta, então
`from .services import ActivityError` continua valendo).
"""


class ActivityError(Exception):
    """Levantado para qualquer transição/ação inválida do núcleo de atividades.
    Views capturam esta exceção e exibem a mensagem via django.contrib.messages."""
