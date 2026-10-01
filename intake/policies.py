"""O que o estado da solicitação permite, separado do que o catálogo permite.

Estado e permissão são perguntas diferentes: uma solicitação já convertida não
pode ser ignorada nem por quem tem `entrada.triar`, e quem não tem `entrada.triar`
não pode ignorar nem uma solicitação nova. A tela cruza as duas respostas.
"""

from .models import IntakeItem

Status = IntakeItem.Status

TRANSITIONS = {
    Status.NOVO: frozenset({Status.CONVERTIDO, Status.IGNORADO}),
    Status.IGNORADO: frozenset({Status.NOVO}),
    Status.CONVERTIDO: frozenset(),
}

# Ações de tela por estado. "edit", "convert" e "ignore" só existem enquanto a
# solicitação está nova; "restore" só para a ignorada.
ACTIONS = {
    Status.NOVO: frozenset({"edit", "convert", "ignore"}),
    Status.IGNORADO: frozenset({"restore"}),
    Status.CONVERTIDO: frozenset(),
}


class IntakePolicy:
    @staticmethod
    def can_transition(item, target):
        return target in TRANSITIONS.get(item.status, frozenset())

    @staticmethod
    def available_actions(item):
        return ACTIONS.get(item.status, frozenset())
