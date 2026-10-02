"""Modelos de quadro para começar. São só um ponto de partida: depois de criado, o quadro é do usuário e
cada alteração segue as permissões normais.

Criar um quadro a partir de um modelo exige só `quadro.criar`, porque quem cria o quadro inteiro recebe
junto as colunas e as etiquetas que o modelo traz. Os itens de exemplo (usados na demonstração) exigem
também criar e editar itens, como qualquer outro item.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from acessos import catalog
from acessos.services import ResourceContext
from audit.models import AuditLog

from .models import Board, BoardColumn, BoardColumnOption, BoardGroup
from .services import POSITION_STEP, BoardError, CellService, ItemService, ViewService, _audit, _require
from .validators import default_settings_for

T = BoardColumn.Type

ORCAMENTOS = {
    "key": "orcamentos",
    "label": "Orçamentos",
    "name": "Orçamentos",
    "description": "Gestão de orçamentos e oportunidades comerciais.",
    "item_label": "Obra",
    "groups": [
        ("Oportunidades", "#C4C4C4"),
        ("Em andamento", "#579BFC"),
        ("Propostas enviadas", "#00C875"),
        ("Concluídos", "#A25DDC"),
    ],
    # O Kanban que o quadro já nasce com: raias = etiquetas do Status, soma do Valor no cabeçalho de cada raia
    "kanban": {
        "name": "Kanban por Status", "group_by": "Status", "sum_column": "Valor",
        "card_fields": ["Cliente", "Responsável", "Prazo", "Valor"],
    },
    "columns": [
        {"name": "Cliente", "type": T.TEXT, "width": 190},
        {"name": "Responsável", "type": T.PERSON, "width": 170},
        {
            "name": "Setor", "type": T.DROPDOWN, "width": 150,
            "options": [
                ("Comercial", "#00C875"), ("Engenharia", "#A25DDC"), ("Suprimentos", "#0086C0"), ("Financeiro", "#FDAB3D"),
            ],
        },
        {"name": "Prazo", "type": T.DATE, "width": 130, "settings": {"is_deadline": True}},
        {
            "name": "Status", "type": T.STATUS, "width": 170,
            "options": [
                ("Novo", "#C4C4C4", True, False), ("Levantamento", "#66CCFF", False, False),
                ("Cotação", "#579BFC", False, False), ("Em revisão", "#FDAB3D", False, False),
                ("Validação diretoria", "#A25DDC", False, False), ("Proposta enviada", "#9CD326", False, False),
                ("Revisão cliente", "#CAB641", False, False), ("Ganho", "#00C875", False, True),
                ("Perdido", "#E2445C", False, True),
            ],
        },
        {"name": "Valor", "type": T.CURRENCY, "width": 140},
        {
            "name": "Probabilidade", "type": T.NUMBER, "width": 130,
            "settings": {"decimal_places": 0, "unit": "%", "minimum": 0, "maximum": 100},
        },
        {
            "name": "Pendência", "type": T.STATUS, "width": 160,
            "options": [
                ("Sem pendência", "#C4C4C4", True, True), ("Visita técnica", "#FDAB3D", False, False),
                ("Definir equipe", "#E2445C", False, False), ("Ajustar escopo", "#A25DDC", False, False),
            ],
        },
        {"name": "Visita técnica", "type": T.DATE, "width": 140},
    ],
    # `prazo` e `visita` são dias a partir de hoje, para o exemplo nunca nascer vencido.
    "examples": [
        {"name": "Arena Center Norte", "group": 1, "Cliente": "Shopping Center Norte", "prazo": 12,
         "Status": "Levantamento", "Valor": "2500000", "Probabilidade": "40"},
        {"name": "Condomínio Cotia", "group": 1, "Cliente": "Residencial Cotia", "prazo": 30,
         "Status": "Cotação", "Valor": "1800000", "Probabilidade": "30"},
        {"name": "Hospital Vida Plena", "group": 2, "Cliente": "Grupo Vida Plena", "prazo": 9,
         "Status": "Proposta enviada", "Valor": "1200000", "Probabilidade": "70"},
        {"name": "Galpão Logístico ABC", "group": 0, "Cliente": "Log ABC", "prazo": 21, "visita": 6,
         "Status": "Novo", "Valor": "2500000", "Probabilidade": "40", "Pendência": "Visita técnica"},
    ],
}

TEMPLATES = {ORCAMENTOS["key"]: ORCAMENTOS}


def template_choices():
    return [(key, spec["label"]) for key, spec in TEMPLATES.items()]


@transaction.atomic
def create_board_from_template(*, user, organization, key, name=None, with_examples=False):
    spec = TEMPLATES.get(key)
    if spec is None:
        raise BoardError("Modelo de quadro desconhecido.")
    _require(user, catalog.QUADRO_CRIAR, ResourceContext.for_new(organization))

    board = Board.objects.create(
        organization=organization,
        name=" ".join((name or "").split())[:160] or spec["name"],
        description=spec["description"],
        item_label=spec["item_label"],
        created_by=user,
    )
    groups = [
        BoardGroup.objects.create(board=board, name=group_name, color=color, position=POSITION_STEP * index)
        for index, (group_name, color) in enumerate(spec["groups"], start=1)
    ]
    columns, options = {}, {}
    for index, column_spec in enumerate(spec["columns"], start=1):
        column = BoardColumn.objects.create(
            board=board,
            name=column_spec["name"],
            type=column_spec["type"],
            position=POSITION_STEP * index,
            width=column_spec.get("width", 160),
            settings={**default_settings_for(column_spec["type"]), **column_spec.get("settings", {})},
            created_by=user,
        )
        columns[column.name] = column
        for option_index, (label, color, *flags) in enumerate(column_spec.get("options", ()), start=1):
            is_default, is_done = (list(flags) + [False, False])[:2]
            options[(column.name, label)] = BoardColumnOption.objects.create(
                column=column, label=label, color=color, is_default=is_default, is_done=is_done,
                position=POSITION_STEP * option_index,
            )
    kanban = spec.get("kanban")
    if kanban:
        ViewService.create_default_kanban(
            user=user, board=board, name=kanban["name"],
            settings={
                "group_by": columns[kanban["group_by"]].pk,
                "sum_column": columns[kanban["sum_column"]].pk if kanban.get("sum_column") else None,
                "card_fields": [columns[name].pk for name in kanban.get("card_fields", ())],
            },
        )
    else:
        ViewService.create_default_kanban(user=user, board=board)
    _audit(user, AuditLog.Action.BOARD_CREATED, board, "board", board, new=board.name, extra={"template": key})
    if with_examples:
        _add_examples(user, board, spec, groups, columns, options)
    return board


def _add_examples(user, board, spec, groups, columns, options):
    today = timezone.localdate()
    for example in spec["examples"]:
        item = ItemService.create(user=user, board=board, group=groups[example["group"]], name=example["name"])
        values = {name: value for name, value in example.items() if name in columns}
        if "prazo" in example:
            values["Prazo"] = (today + timedelta(days=example["prazo"])).isoformat()
        if "visita" in example:
            values["Visita técnica"] = (today + timedelta(days=example["visita"])).isoformat()
        for column_name, value in values.items():
            column = columns[column_name]
            raw = options[(column_name, value)].pk if column.uses_options else value
            CellService.set_value(user=user, item=item, column=column, raw_value=raw)
