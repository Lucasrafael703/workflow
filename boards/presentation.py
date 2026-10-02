"""O que a tela precisa saber do quadro além dos dados: permissões da pessoa, endereços dos endpoints e a
descrição das colunas que o JavaScript recebe (`json_script`).

O JavaScript nunca monta URL à mão: recebe modelos com um id fictício e só troca o número.
"""

from django.urls import reverse

from acessos import catalog
from acessos.services import AuthorizationService

from .models import MAX_COLUMN_WIDTH, MIN_COLUMN_WIDTH, BoardColumn
from .validators import default_settings_for

#: ids fictícios que o JavaScript troca pelo id real (o segundo existe nas rotas com dois ids)
SENTINEL = 999999999
SENTINEL_COLUMN = 999999998

#: cores oferecidas ao escolher etiqueta ou grupo (as do mockup, com o cinza neutro primeiro)
COLOR_PALETTE = [
    "#C4C4C4", "#797E93", "#E2445C", "#FF158A", "#FDAB3D", "#FFCB00", "#CAB641", "#9CD326",
    "#00C875", "#037F4C", "#66CCFF", "#579BFC", "#0086C0", "#7F5347", "#A25DDC", "#784BD1",
]

TYPE_INFO = {
    BoardColumn.Type.STATUS: ("Status", "Acompanhe o andamento com etiquetas coloridas.", "task"),
    BoardColumn.Type.DROPDOWN: ("Lista suspensa", "Escolha uma opção de uma lista que você define.", "chevron-down"),
    BoardColumn.Type.TEXT: ("Texto", "Escreva livremente: nomes, observações, números de documento.", "file-text"),
    BoardColumn.Type.DATE: ("Data", "Prazos, vistorias e outros compromissos com dia marcado.", "calendar"),
    BoardColumn.Type.PERSON: ("Pessoa", "Atribua a quem da equipe cabe o item.", "user"),
    BoardColumn.Type.NUMBER: ("Número", "Quantidades, percentuais e outras medidas.", "list-ol"),
    BoardColumn.Type.CURRENCY: ("Moeda", "Valores em dinheiro, já formatados.", "dollar"),
    BoardColumn.Type.CHECKBOX: ("Sinal de confirmação", "Um sim ou não: feito, recebido, aprovado.", "check"),
}


def type_catalog():
    """Os tipos que o seletor oferece, na ordem de `ACTIVE_TYPES`."""
    return [
        {"value": str(kind), "label": TYPE_INFO[kind][0], "description": TYPE_INFO[kind][1], "icon": TYPE_INFO[kind][2]}
        for kind in BoardColumn.ACTIVE_TYPES
    ]


def type_icon(column_type):
    info = TYPE_INFO.get(column_type)
    return info[2] if info else "list-ul"


PERMISSION_KEYS = {
    "view": catalog.QUADRO_VISUALIZAR,
    "edit": catalog.QUADRO_EDITAR,
    "delete": catalog.QUADRO_EXCLUIR,
    "manage_columns": catalog.QUADRO_GERIR_COLUNAS,
    "create_item": catalog.QUADRO_CRIAR_ITEM,
    "edit_item": catalog.QUADRO_EDITAR_ITEM,
    "delete_item": catalog.QUADRO_EXCLUIR_ITEM,
}


def board_permissions(user, board):
    """O que esta pessoa pode fazer neste quadro, numa única consulta de autorização."""
    if board.kind == board.Kind.DEMAND:
        from .demand_services import DemandBoardAccess

        can_collaborate = DemandBoardAccess.can_collaborate(user, board)
        return {
            "view": DemandBoardAccess.can_view(user, board),
            "edit": DemandBoardAccess.can_manage_structure(user, board),
            "delete": False,
            "manage_columns": DemandBoardAccess.can_manage_structure(user, board),
            "create_item": can_collaborate,
            "edit_item": can_collaborate,
            # A permissão efetiva é conferida sobre a Task no cancelamento
            # (inclusive seu setor). Aqui só liberamos o menu; não usamos o
            # setor da Demanda como aproximação que esconderia Tasks cruzadas.
            "delete_item": can_collaborate,
        }
    allowed = AuthorizationService.can_many(user, [(action, board) for action in PERMISSION_KEYS.values()])
    return {name: allowed.get((action, board.pk), False) for name, action in PERMISSION_KEYS.items()}


def board_urls(board):
    """Endereços dos endpoints do quadro. As rotas com `id` de grupo/coluna/etiqueta/item vêm com o id fictício."""
    s, c = SENTINEL, SENTINEL_COLUMN
    return {
        "board_rename": reverse("board-rename", args=[board.pk]),
        "board_delete": reverse("board-delete", args=[board.pk]),
        "board_list": reverse("board-list"),
        "history": reverse("board-history", args=[board.pk]),
        "group_create": reverse("board-group-create", args=[board.pk]),
        "group_update": reverse("board-group-update", args=[s]),
        "group_reorder": reverse("board-group-reorder", args=[s]),
        "group_delete": reverse("board-group-delete", args=[s]),
        "column_create": reverse("board-column-create", args=[board.pk]),
        "column_rename": reverse("board-column-rename", args=[s]),
        "column_resize": reverse("board-column-resize", args=[s]),
        "column_reorder": reverse("board-column-reorder", args=[s]),
        "column_settings": reverse("board-column-settings", args=[s]),
        "column_hide": reverse("board-column-hide", args=[s]),
        "column_duplicate": reverse("board-column-duplicate", args=[s]),
        "column_type": reverse("board-column-type", args=[s]),
        "column_delete": reverse("board-column-delete", args=[s]),
        "column_fragment": reverse("board-column-fragment", args=[s]),
        "option_create": reverse("board-option-create", args=[s]),
        "option_update": reverse("board-option-update", args=[s]),
        "option_reorder": reverse("board-option-reorder", args=[s]),
        "option_delete": reverse("board-option-delete", args=[s]),
        "item_create": reverse("board-item-create", args=[board.pk]),
        "item_rename": reverse("board-item-rename", args=[s]),
        "item_move": reverse("board-item-move", args=[s]),
        "item_delete": reverse("board-item-delete", args=[s]),
        "cell_update": reverse("board-cell-update", args=[s, c]),
        "view_create": reverse("board-view-create", args=[board.pk]),
        "view_update": reverse("board-view-update", args=[s]),
        "view_delete": reverse("board-view-delete", args=[s]),
        "view_lanes": reverse("board-view-lanes", args=[s]),
        "view_detail": reverse("board-view-detail", args=[s]),
        "view_calendar": reverse("board-view-calendar", args=[s]),
        "item_detail": reverse("board-item-detail", args=[s]),
        "person_search": reverse("person-search"),
    }


def column_meta(column):
    """Dados da coluna para o JavaScript. As etiquetas ativas vão junto, já ordenadas."""
    return {
        "id": column.pk,
        "name": column.name,
        "type": column.type,
        "type_label": column.get_type_display(),
        "icon": type_icon(column.type),
        "width": column.width,
        "description": column.description,
        "is_required": column.is_required,
        "is_visible": column.is_visible,
        "settings": {**default_settings_for(column.type), **(column.settings or {})},
        "options": [
            {"id": o.pk, "label": o.label, "color": o.color, "is_default": o.is_default, "is_done": o.is_done}
            for o in sorted(column.options.all(), key=lambda o: (o.position, o.pk))
            if o.is_active
        ]
        if column.uses_options
        else [],
    }


def board_meta(board, columns, groups, *, permissions, sort_column=None, direction="asc"):
    return {
        "board": {"id": board.pk, "name": board.name, "kind": board.kind, "item_label": board.item_label},
        "permissions": permissions,
        "urls": board_urls(board),
        "sentinels": {"id": SENTINEL, "column": SENTINEL_COLUMN},
        "types": type_catalog(),
        "columns": [column_meta(column) for column in columns],
        "groups": [{"id": group.pk, "name": group.name, "color": group.color} for group in groups],
        "sort": {"column": sort_column.pk if sort_column else None, "dir": direction},
        "limits": {"min_width": MIN_COLUMN_WIDTH, "max_width": MAX_COLUMN_WIDTH},
        "palette": COLOR_PALETTE,
    }
