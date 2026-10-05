"""Kanban de Demandas no formato do kit (templates/kanban/*): transforma as raias de `_group_items` e as células de
`build_cells` em raias e cartões simples. O modelo visual é o Kanban de Quadros; aqui só fica o que é do domínio.

O contrato de dados está documentado no cabeçalho de `templates/kanban/_lanes.html`. As regras de "pode soltar aqui?"
repetem, de propósito e só para dar resposta imediata, o que o serviço já valida (`StageService`, `ConditionService`,
`ActivityTransitionPolicy`); quem decide de verdade continua sendo o servidor, e `test_demand_kanban.py` compara os dois.

O que a tela NÃO adivinha, de propósito, porque custaria uma consulta por cartão e destino: a permissão de editar no setor
de DESTINO (`ActivityService.update_activity`), pendência aguardando aprovação (impede trocar o setor) e versão velha
(`updated_at`, 409). Nesses casos o servidor recusa, o cartão volta e a tela mostra a mensagem dele.
"""

import json
from urllib.parse import quote, urlencode

from django.urls import reverse

from activities.inline_edit import deadline_display, option_data
from activities.models import Activity
from activities.policies import ACTIVITY_TERMINAL
from core.colors import get_contrast_text

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


def _hook(field, model, option_id=None):
    """Os atributos que ligam o campo à edição inline (activity-inline-edit.js, a mesma da Lista): qual campo é e o modelo
    do valor atual em JSON (o navegador o lê dali; o desenho é o do kit)."""
    attrs = [("data-inline-field", field), ("data-inline-model", json.dumps(model, ensure_ascii=False, separators=(",", ":")))]
    if option_id is not None:
        attrs.append(("data-option-id", option_id))
    return attrs


def _fields(item):
    """Campos visíveis do cartão, na ordem configurada (o título é o título do cartão). Quem pode editar um campo (`item.inline`,
    de `inline_flags`) o recebe como editável: clicar nele abre o mesmo editor da Lista."""
    out = []
    can = getattr(item, "inline", None) or {}
    for cell in getattr(item, "work_cells", []):
        key = cell["key"]
        if key == "title":
            continue
        label = CARD_LABELS.get(key, cell["field"].label)
        if key in {"owner", "responsavel"}:
            person = cell.get("person")
            model = {"value": str(person.pk) if person else "", "text": cell["text"] if person else "", "initials": "", "avatarClass": ""}
            field = {"kind": "person", "label": label, "name": cell["text"], "initials": initials(person)} if person else {"kind": "person", "label": label, "name": ""}
            if key == "owner" and can.get("owner"):
                field.update(editable=True, attrs=_hook("owner", model))
            out.append(field)
        elif key == "sector":
            sector = cell.get("sector")
            field = {"kind": "sector", "label": label, "sector": sector}
            if can.get("sector"):
                field.update(editable=True, attrs=_hook("sector", option_data(sector), sector.pk if sector else ""))
            out.append(field)
        elif key in {"urgency", "priority"}:
            color = cell.get("color", "")
            field = {"kind": "pill", "label": label, "text": cell["text"], "color": color}
            if key == "urgency" and can.get("urgency"):
                model = {"id": cell["raw"], "name": cell["text"], "color": color, "text_color": get_contrast_text(color) if color else ""}
                field.update(editable=True, attrs=_hook("urgency", model, cell["raw"]))
            out.append(field)
        elif key in {"stage", "condition"}:
            choice = cell.get("choice")
            field = {"kind": "pill", "label": label, "text": choice.name if choice else "", "color": getattr(choice, "color", "")}
            if can.get(key):
                field.update(editable=True, attrs=_hook(key, option_data(choice), choice.pk if choice else ""))
            out.append(field)
        elif key == "requested_deadline":
            text = deadline_display(cell.get("deadline"))
            overdue = bool(getattr(item, "is_overdue", False))
            field = {"kind": "date", "label": label, "text": text, "overdue": overdue}
            if can.get("requested_deadline"):
                model = {"date": can.get("deadline_date", ""), "time": can.get("deadline_time", ""), "text": text or "Sem prazo", "isLate": overdue}
                field.update(editable=True, attrs=_hook("requested_deadline", model))
            out.append(field)
        elif key == "tasks":
            out.append({
                "kind": "progress", "label": label, "done": getattr(item, "done_tasks", 0),
                "total": getattr(item, "total_tasks", 0), "percent": cell.get("progress", 0),
            })
        else:
            out.append({"kind": "text", "label": label, "text": "" if cell["raw"] in ("", None) else cell["text"]})
    return out


# O que cada agrupamento diz sobre a demanda nova criada na raia: o parâmetro da janela "Nova demanda" que ele preenche.
CREATE_PARAM = {"stage": "etapa", "condition": "condicao", "sector": "setor", "owner": "pessoa", "responsavel": "pessoa", "urgency": "urgencia"}


def _preset(group_by, lane, default_sector_id):
    """Parâmetros iniciais da janela "Nova demanda" para esta raia (pares, na ordem em que aparecem no endereço), ou `None` quando
    a raia não tem como receber uma demanda nova. Etapa e status são de um setor: a raia leva o setor junto. Nos agrupamentos que
    não dizem o setor (responsável, prioridade), vale o setor do filtro quando há um só."""
    key = lane["key"]
    if group_by in SECTOR_SCOPED:
        return [(CREATE_PARAM[group_by], key), ("setor", lane["scope"])] if lane["scope"] else None
    if group_by not in CREATE_PARAM:
        return []
    params = [(CREATE_PARAM[group_by], key)]
    if group_by != "sector" and default_sector_id:
        params.append(("setor", default_sector_id))
    return params


def build_demand_kanban(
    *, groups, group_by, sectors_by_id, show_field_names, can_create, create_url, return_url, can_rename=False,
    can_create_in=None, can_manage=None, default_sector_id=None, config_url="",
):
    """Devolve o dicionário `kanban` que `kanban/_lanes.html` consome.

    `groups` = saída de `DomainWorkBoardView._group_items` (com `sector_id`/`is_active` nas raias de etapa/status);
    `item.can_move_kanban` já diz se a pessoa pode mexer naquele campo e `item.inline` (de `inline_flags`) o que ela pode
    editar. Com `can_rename`, o título renomeia no lugar (como em Quadros) e a ficha abre pelo código e pelo ⋯ "Abrir
    demanda"; quem não pode renomear continua com o título como link para a ficha."""
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

    def add_for(lane):
        """"+ Adicionar" da raia: abre a janela "Nova demanda" JÁ com o que a raia diz (setor, etapa, status, responsável ou
        prioridade). Só existe onde a demanda nova pode mesmo ficar: raia "sem valor" ou de etapa/status desativado não recebe, e
        o setor da raia precisa deixar a pessoa criar (o servidor valida de novo ao enviar)."""
        if not can_create or lane["is_blank"] or not lane["accepts"]:
            return None
        preset = _preset(group_by, lane, default_sector_id)
        if preset is None:
            return None
        sector_id = next((int(value) for name, value in preset if name == "setor"), None)
        owner_id = int(lane["key"]) if group_by in {"owner", "responsavel"} else None
        if can_create_in is not None and not can_create_in(sector_id, owner_id):
            return None
        href = create_url + ("&" if "?" in create_url else "?") + urlencode(preset) if preset else create_url
        return {"label": "Adicionar demanda", "href": href, "attrs": [("data-activity-action", ""), ("data-activity-navigate", "")]}

    def menu_for(lane):
        """⋮ da raia: o que dá para fazer com a etapa/status dela e não é mover cartão. Etapa e status são cadastro do setor
        (valem para todas as demandas dele), então o caminho é a tela própria deles, só para quem gere aquele setor."""
        if group_by not in SECTOR_SCOPED or lane["is_blank"] or not lane["scope"] or can_manage is None or not config_url:
            return []
        if not can_manage(group_by, int(lane["scope"])):
            return []
        label = "Editar as etapas do setor" if group_by == "stage" else "Editar os status do setor"
        return [{"label": label, "icon": "sliders", "href": f"{config_url}?domain=demandas&sector={lane['scope']}"}]

    for lane in lanes:
        cards = []
        for item in lane.pop("_items"):
            scope = str(item.sector_id or "")
            # Existe OUTRA raia que receba este cartão? (a própria só conta se ele já não estiver nela)
            others = receivers(scope) - (1 if lane["accepts"] and lane["scope"] in ("", scope) else 0)
            can_move = bool(getattr(item, "can_move_kanban", False)) and not blocked_by_status(item, group_by) and others > 0
            detail = f"{reverse('activity-detail', args=[item.pk])}?next={quote(return_url)}"
            cards.append({
                "id": item.pk,
                "title": item.title,
                "url": detail,  # o título só é link para quem não pode renomear (o kit prefere o título editável)
                "link": {"text": getattr(item, "code", "") or "Abrir", "url": detail, "label": f"Abrir a demanda {item.title}"},
                "updated_at": item.updated_at.isoformat(),
                "scope": scope,
                "can_move": can_move,
                "menu": True,  # todo cartão tem o ⋯: pelo menos "Abrir demanda"
                "title_editable": bool(can_rename and (getattr(item, "inline", None) or {}).get("title")),
                "title_label": "Título da demanda",
                "attrs": [("data-activity-id", item.pk), ("data-detail-url", detail)],
                "fields": _fields(item),
            })
        lane["cards"] = cards
        lane["add"] = add_for(lane)
        links = menu_for(lane)
        lane["menu"] = bool(links)
        if links:  # o navegador abre estes itens no menu da raia (`data-lane-menu-items`)
            lane["menu_attrs"] = [("data-lane-menu-items", json.dumps(links, ensure_ascii=False, separators=(",", ":")))]
        lane["empty_text"] = "Nenhuma demanda." + (" Arraste uma demanda para cá." if lane["accepts"] else "")
    return {
        "item_label": "demanda",
        "show_field_names": show_field_names,
        "empty_title": "Nenhuma demanda encontrada",
        "empty_text": "Ajuste os filtros ou crie uma nova demanda.",
        "lanes": lanes,
    }
