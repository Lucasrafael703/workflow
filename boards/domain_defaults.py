"""Configuração idempotente dos quadros que leem os objetos operacionais.

Não há fixtures: organizações criadas antes e depois desta entrega recebem a
mesma estrutura sob demanda, sem requerer dados fictícios.
"""

from decimal import Decimal

from .models import DomainBoard, DomainBoardCardField, DomainBoardField, DomainBoardView, DomainBoardViewColumn


STEP = Decimal("1000")


DEFAULT_FIELDS = {
    DomainBoard.Domain.DEMAND: (
        ("title", "Título da demanda", "TEXT"),
        ("owner", "Responsável", "PERSON"),
        ("sector", "Setor", "SECTOR"),
        ("urgency", "Prioridade", "PRIORITY"),
        ("requested_deadline", "Prazo", "DATETIME"),
        ("stage", "Status", "STAGE"),
        ("condition", "Status", "SELECT"),
        ("tasks", "Tarefas", "CHECKLIST"),
    ),
    DomainBoard.Domain.TASK: (
        ("title", "Título da tarefa", "TEXT"),
        ("activity", "Demanda vinculada", "RELATION"),
        ("responsavel", "Responsável", "PERSON"),
        ("sector", "Setor", "SECTOR"),
        ("priority", "Prioridade", "PRIORITY"),
        ("requested_deadline", "Prazo", "DATETIME"),
        ("stage", "Status", "STAGE"),
        ("checklist", "Checklist", "CHECKLIST"),
    ),
}


DEFAULT_VIEWS = (
    ("Quadro principal", DomainBoardView.Type.TABLE, {"group_by": "stage"}),
    ("Kanban", DomainBoardView.Type.KANBAN, {"group_by": "stage", "show_empty": True}),
    ("Calendário", DomainBoardView.Type.CALENDAR, {"date_field": "requested_deadline"}),
)


def ensure_domain_board(organization, domain):
    """Retorna a configuração padrão, criando somente o que estiver ausente."""
    label = "Demandas" if domain == DomainBoard.Domain.DEMAND else "Tarefas"
    board, _created = DomainBoard.objects.get_or_create(
        organization=organization, domain=domain, defaults={"name": label}
    )
    fields = []
    for index, (key, label, field_type) in enumerate(DEFAULT_FIELDS[domain], start=1):
        field, _ = DomainBoardField.objects.get_or_create(
            board=board,
            key=key,
            defaults={
                "label": label,
                "type": field_type,
                "position": STEP * index,
                "is_system": True,
            },
        )
        fields.append(field)

    for index, (name, view_type, settings) in enumerate(DEFAULT_VIEWS, start=1):
        view, _ = DomainBoardView.objects.get_or_create(
            board=board,
            name=name,
            defaults={
                "type": view_type,
                "position": STEP * index,
                "settings": settings,
                "is_default": index == 1,
            },
        )
        if view.type == DomainBoardView.Type.TABLE:
            for field_index, field in enumerate(fields, start=1):
                DomainBoardViewColumn.objects.get_or_create(
                    view=view,
                    field=field,
                    defaults={"position": STEP * field_index, "width": 250 if field.key == "title" else 168},
                )
        if view.type == DomainBoardView.Type.KANBAN:
            for field_index, field in enumerate(fields, start=1):
                if field.key in {"title", "owner", "responsavel", "sector", "priority", "urgency", "requested_deadline", "checklist", "activity"}:
                    DomainBoardCardField.objects.get_or_create(
                        view=view, field=field, defaults={"position": STEP * field_index}
                    )
    return board
