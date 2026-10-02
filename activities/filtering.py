"""Parâmetros compartilhados pelas superfícies de Demandas e Tarefas.

Os links antigos continuam sendo aceitos, mas os novos toolbars sempre
escrevem os nomes canônicos. Isso permite trocar Lista, Kanban e Calendário
sem mudar a URL das telas nem perder filtros salvos.
"""

DEADLINE_FILTERS = {"atrasadas", "hoje", "7_dias", "30_dias", "sem_prazo"}
QUICK_FILTERS = {
    "atrasadas",
    "hoje",
    "bloqueadas",
    "em-fila",
    "em-execucao",
    "devolvidas",
    "concluidas",
}

FORM_FILTER_FIELDS = {
    "q", "tab", "setor", "pessoa", "condicao", "estagio", "filtro", "cliente", "obra",
    "tag", "participante", "prazo", "bloqueio", "concluidas", "status", "ordem", "dir", "visao", "ano",
    "mes", "page", "grupo", "sector", "sort",
}


def _first(params, *names):
    for name in names:
        value = params.get(name)
        if value not in (None, ""):
            return value
    return ""


def normalize_workspace_filters(request, *, default_order="prazo"):
    """Return one filter state for both the list and the Kanban.

    ``grupo``/``sector`` and ``sort`` are compatibility aliases. The caller
    remains responsible for applying domain-specific visibility rules.
    """
    params = request.GET
    raw_status = params.get("status", "")
    quick = params.get("filtro", "")
    deadline = params.get("prazo", "")

    if quick in DEADLINE_FILTERS:
        deadline = quick
    if raw_status == "BLOQUEADA":
        quick = "bloqueadas"
    if params.get("bloqueio"):
        quick = "bloqueadas"
    if raw_status == "concluidas" or params.get("concluidas") or params.get("tab") == "concluidas":
        quick = "concluidas" if not quick else quick

    if quick not in QUICK_FILTERS:
        quick = ""
    if deadline not in DEADLINE_FILTERS:
        deadline = ""

    order = _first(params, "ordem", "sort") or default_order
    return {
        "q": params.get("q", "").strip(),
        "tab": params.get("tab", "minhas"),
        "pessoa": _first(params, "pessoa", "responsavel"),
        "setor": _first(params, "setor", "sector", "grupo"),
        "condicao": params.get("condicao", ""),
        "estagio": params.get("estagio", ""),
        "filtro": quick,
        "cliente": params.get("cliente", ""),
        "obra": params.get("obra", ""),
        "tag": params.get("tag", ""),
        "participante": params.get("participante", ""),
        "prazo": deadline,
        "bloqueio": bool(params.get("bloqueio")) or quick == "bloqueadas" or raw_status == "BLOQUEADA",
        "concluidas": bool(params.get("concluidas")) or raw_status == "concluidas" or quick == "concluidas" or params.get("tab") == "concluidas",
        "status": raw_status if raw_status not in {"BLOQUEADA", "concluidas"} else "",
        "ordem": order,
        "dir": params.get("dir", ""),
        "ano": params.get("ano", ""),
        "mes": params.get("mes", ""),
    }


def canonical_filter_querystring(request, *, keep_calendar=False):
    """Build a view-switching query string with canonical filter names."""
    params = request.GET.copy()
    params.pop("page", None)
    params.pop("visao", None)

    if not keep_calendar:
        params.pop("ano", None)
        params.pop("mes", None)

    state = normalize_workspace_filters(request)
    for legacy in ("grupo", "sector", "sort"):
        params.pop(legacy, None)

    if state["setor"]:
        params["setor"] = state["setor"]
    else:
        params.pop("setor", None)

    if request.GET.get("ordem") or request.GET.get("sort"):
        params["ordem"] = state["ordem"]
    else:
        params.pop("ordem", None)

    if state["status"]:
        params["status"] = state["status"]
    elif state["bloqueio"]:
        params["bloqueio"] = "1"
        params.pop("status", None)
    elif state["concluidas"]:
        params["concluidas"] = "1"
        params.pop("status", None)

    return params.urlencode()


def clear_filter_querystring(request, *, keep_sector=False, keep_calendar=False):
    params = request.GET.copy()
    filter_names = {
        "q", "pessoa", "responsavel", "condicao", "estagio", "filtro", "cliente", "obra",
        "tag", "participante", "prazo", "bloqueio", "concluidas", "status", "ordem", "sort", "dir",
        "grupo", "sector", "setor", "urgencia", "centro_custo", "criado_de", "criado_ate", "prazo_de", "prazo_ate",
        "ano", "mes", "page",
    }
    if keep_sector:
        filter_names -= {"setor"}
    if keep_calendar:
        filter_names -= {"ano", "mes"}
    for name in filter_names:
        params.pop(name, None)
    query = params.urlencode()
    return f"?{query}" if query else "?"


def filter_state_for_template(request, *, domain, view_mode, sectors, people=None, clients=None, sites=None, tags=None, stage_groups=None, condition_groups=None, board=False, orderings=None, default_order="prazo", year="", month=""):
    """Add display metadata to the normalized state used by the shared partial."""
    state = normalize_workspace_filters(request, default_order=default_order)
    preserved_fields = [
        {"name": name, "value": value}
        for name in request.GET
        if name not in FORM_FILTER_FIELDS
        for value in request.GET.getlist(name)
    ]
    state.update(
        {
            "domain": domain,
            "view_mode": view_mode,
            "noun": "demanda" if domain == "demanda" else "tarefa",
            "is_board": board,
            "sectors": sectors,
            "people": people or [],
            "clients": clients or [],
            "sites": sites or [],
            "tags": tags or [],
            "stage_groups": stage_groups or [],
            "condition_groups": condition_groups or [],
            "orderings": orderings or [],
            "default_order": default_order,
            "preserved_fields": preserved_fields,
            "calendar_year": year or state["ano"],
            "calendar_month": month or state["mes"],
            "active_count": sum(
                bool(state[key])
                for key in ("q", "pessoa", "setor", "condicao", "estagio", "filtro", "cliente", "obra", "tag", "participante", "prazo", "bloqueio", "concluidas", "status")
            ) + int(state["ordem"] != default_order),
            "filter_querystring": canonical_filter_querystring(
                request, keep_calendar=bool(state["ano"] or state["mes"])
            ),
            "clear_url": clear_filter_querystring(request, keep_sector=board, keep_calendar=view_mode == "calendario"),
        }
    )
    return state
