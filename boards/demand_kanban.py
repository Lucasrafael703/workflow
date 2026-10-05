"""Kanban de Demandas no formato do kit (templates/kanban/*): transforma as raias de `_group_items` e as células de
`build_cells` em raias e cartões simples. O modelo visual é o Kanban de Quadros; aqui só fica o que é do domínio.

O contrato de dados está documentado no cabeçalho de `templates/kanban/_lanes.html`. As regras de "pode soltar aqui?"
repetem, de propósito e só para dar resposta imediata, o que o serviço já valida (`StageService`, `ConditionService`,
`ActivityTransitionPolicy`); quem decide de verdade continua sendo o servidor, e `test_demand_kanban.py` compara os dois.

O que a tela NÃO adivinha, de propósito, porque custaria uma consulta por cartão e destino: a permissão de editar no setor
de DESTINO (`ActivityService.update_activity`), pendência aguardando aprovação (impede trocar o setor) e versão velha
(`updated_at`, 409). Nesses casos o servidor recusa, o cartão volta e a tela mostra a mensagem dele.
"""

from urllib.parse import quote

from django.urls import reverse

from activities.inline_edit import deadline_display
from activities.models import Activity
from activities.policies import ACTIVITY_TERMINAL

from .templatetags.lps_board import initials

BLANK_COLOR = "#C4C4C4"  # a mesma cor da raia "Em branco" de Quadros

# `stage` e `condition` têm AMBOS o rótulo "Status" no cadastro de campos (sem migração): no cartão ficam distintos.
CARD_LABELS = {
    "stage": "Etapa",
    "condition": "Status",
    "urgency": "Prioridade",
    "owner": "Responsável",
    "sector": "Setor",
    "requested_deadline": "Prazo",
    "tasks": "Tarefas",
}

SECTOR_SCOPED = {"stage", "condition"}  # etapa e status pertencem a UM setor: só aceitam cartões desse setor
# Agrupamentos cuja raia "sem valor" NÃO aceita soltar: o servidor recusa (setor, responsável e prioridade são obrigatórios).
# Só etapa e status podem voltar a "sem valor".
BLANK_CLOSED = {"sector", "owner", "responsavel", "urgency", "priority"}
# Mexer em setor ou responsável também é recusado em rascunho (a demanda ainda está sendo criada).
DRAFT_BLOCKED = {"sector", "owner"}


def blocked_by_status(item, group_by):
    """O servidor recusa mover esta demanda, qualquer que seja o destino, só pelo estado dela?"""
    if item.status in ACTIVITY_TERMINAL:
        return True
    return group_by in DRAFT_BLOCKED and item.status == Activity.Status.RASCUNHO


def _fields(item):
    """Campos visíveis do cartão, na ordem configurada (o título é o título do cartão)."""
    out = []
    for cell in getattr(item, "work_cells", []):
        key = cell["key"]
        if key == "title":
            continue
        label = CARD_LABELS.get(key, cell["field"].label)
        if key in {"owner", "responsavel"}:
            person = cell.get("person")
            if person:
                out.append({"kind": "person", "label": label, "name": cell["text"], "initials": initials(person)})
            else:
                out.append({"kind": "person", "label": label, "name": ""})
        elif key == "sector":
            out.append({"kind": "sector", "label": label, "sector": cell.get("sector")})
        elif key in {"urgency", "priority"}:
            out.append({"kind": "pill", "label": label, "text": cell["text"], "color": cell.get("color", "")})
        elif key in {"stage", "condition"}:
            choice = cell.get("choice")
            out.append({"kind": "pill", "label": label, "text": choice.name if choice else "", "color": getattr(choice, "color", "")})
        elif key == "requested_deadline":
            out.append({
                "kind": "date", "label": label, "text": deadline_display(cell.get("deadline")),
                "overdue": bool(getattr(item, "is_overdue", False)),
            })
        elif key == "tasks":
            out.append({
                "kind": "progress", "label": label, "done": getattr(item, "done_tasks", 0),
                "total": getattr(item, "total_tasks", 0), "percent": cell.get("progress", 0),
            })
        else:
            out.append({"kind": "text", "label": label, "text": "" if cell["raw"] in ("", None) else cell["text"]})
    return out


def build_demand_kanban(*, groups, group_by, sectors_by_id, show_field_names, can_create, create_url, return_url):
    """Devolve o dicionário `kanban` que `kanban/_lanes.html` consome.

    `groups` = saída de `DomainWorkBoardView._group_items` (com `sector_id`/`is_active` nas raias de etapa/status);
    `item.can_move_kanban` já diz se a pessoa pode mexer naquele campo."""
    sector_scoped = group_by in SECTOR_SCOPED
    sector_ids = {group.get("sector_id") for group in groups if group.get("sector_id")}
    mixed = sector_scoped and len(sector_ids) > 1  # raias de setores diferentes se misturam: dizer qual é qual

    lanes = []
    for group in groups:
        blank = group["key"] == "empty"
        sector_id = group.get("sector_id")
        scoped = sector_scoped and not blank and bool(sector_id)
        inactive = not group.get("is_active", True)  # etapa/status que o catálogo desativou: aparece (tem cartão), não recebe
        lanes.append({
            "key": group["key"],
            "label": group["label"],
            "color": BLANK_COLOR if blank else group["color"],
            "is_blank": blank,
            "accepts": not inactive and not (blank and group_by in BLANK_CLOSED),
            "scope": str(sector_id) if scoped else "",
            "sector": sectors_by_id.get(sector_id, "") if (mixed and scoped) else "",
            "count": len(group["items"]),
            "_items": group["items"],
        })
    if mixed:  # raia em branco primeiro; depois por setor, mantendo a ordem do fluxo dentro de cada um
        lanes.sort(key=lambda lane: (not lane["is_blank"], lane["sector"].lower()))

    receiving = {}  # escopo do cartão -> quantas raias aceitam soltá-lo (calculado uma vez por escopo)

    def receivers(scope):
        if scope not in receiving:
            receiving[scope] = sum(1 for lane in lanes if lane["accepts"] and lane["scope"] in ("", scope))
        return receiving[scope]

    add = None
    if can_create:
        add = {"label": "Adicionar demanda", "href": create_url, "attrs": [("data-activity-action", ""), ("data-activity-navigate", "")]}

    for lane in lanes:
        cards = []
        for item in lane.pop("_items"):
            scope = str(item.sector_id or "")
            # Existe OUTRA raia que receba este cartão? (a própria só conta se ele já não estiver nela)
            others = receivers(scope) - (1 if lane["accepts"] and lane["scope"] in ("", scope) else 0)
            can_move = bool(getattr(item, "can_move_kanban", False)) and not blocked_by_status(item, group_by) and others > 0
            cards.append({
                "id": item.pk,
                "title": item.title,
                "url": f"{reverse('activity-detail', args=[item.pk])}?next={quote(return_url)}",
                "updated_at": item.updated_at.isoformat(),
                "scope": scope,
                "can_move": can_move,
                "menu": can_move,  # hoje o ⋯ só oferece "Mover para"; com título editável passará a existir também sem mover
                "fields": _fields(item),
            })
        lane["cards"] = cards
        lane["add"] = add
        lane["empty_text"] = "Nenhuma demanda." + (" Arraste uma demanda para cá." if lane["accepts"] else "")
    return {
        "item_label": "demanda",
        "show_field_names": show_field_names,
        "empty_title": "Nenhuma demanda encontrada",
        "empty_text": "Ajuste os filtros ou crie uma nova demanda.",
        "lanes": lanes,
    }
