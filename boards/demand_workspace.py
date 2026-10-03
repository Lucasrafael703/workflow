"""Workspace de Demandas (shell único com Lista / Kanban / Calendário), atrás da flag `WORKSPACE_V2`.

Este módulo só **monta o contexto da barra** (abas, escopo, "mostrar", agrupar, ordenar, painel de filtros, chips,
avisos). Os dados continuam vindo da MESMA consulta de sempre (`activities.views.filtered_activities_queryset`) e a
view é a de sempre (`DemandWorkBoardView`). Nada aqui é genérico de propósito: só se extrai alguma abstração quando
Tarefas for a segunda implementação real.

Estado da tela (três camadas): a **URL** guarda visão, busca, filtros, agrupar, ordenar e mês; o que é efêmero
(painel aberto, rascunho dos filtros) vive só no navegador; o padrão salvo (colunas/campos) é de outra fase.
"""

from django.db.models import F
from django.urls import reverse

from acessos import catalog
from acessos.services import AuthorizationService
from core.models import ActivityStage, Client, Sector, Site, WorkflowStatus

# (chave, rótulo, ícone, nome da rota). O rótulo "Kanban" (e não "Quadro") evita colidir com o módulo Quadros.
VIEWS = (
    ("lista", "Lista", "menu", "activity-list"),
    ("kanban", "Kanban", "kanban", "activity-kanban"),
    ("calendario", "Calendário", "calendar", "activity-calendar"),
)

# Parâmetros com apelidos antigos: ao escrever um, os apelidos saem para não haver dois valores na URL.
ALIASES = {"setor": ("sector", "grupo"), "pessoa": ("responsavel",), "ordem": ("sort",)}

SCOPES = (("minhas", "Minhas"), ("grupo", "Do meu setor"), ("participando", "Participando"), ("todas", "Todas"))
SHOW = (("abertas", "Em aberto"), ("concluidas", "Concluídas"))

GROUPINGS = (
    ("stage", "Etapa"),
    ("condition", "Status"),
    ("sector", "Setor"),
    ("owner", "Responsável"),
    ("urgency", "Urgência"),
)
GROUPING_KEYS = {key for key, _label in GROUPINGS}

# (ordem, sentido) -> rótulo. O sentido padrão de cada ordem fica fora da URL.
SORTS = (
    ("prazo", "asc", "Prazo: mais próximo primeiro"),
    ("prazo", "desc", "Prazo: mais distante primeiro"),
    ("recentes", "desc", "Mais recentes"),
    ("recentes", "asc", "Mais antigas"),
    ("titulo", "asc", "Demanda (A–Z)"),
    ("titulo", "desc", "Demanda (Z–A)"),
)
DEFAULT_DIRECTION = {"prazo": "asc", "recentes": "desc", "titulo": "asc"}

DEADLINE_OPTIONS = (
    ("", "Todos os prazos"),
    ("atrasadas", "Atrasadas"),
    ("hoje", "Vencem hoje"),
    ("7_dias", "Próximos 7 dias"),
    ("30_dias", "Próximos 30 dias"),
    ("sem_prazo", "Sem prazo"),
)
DEADLINE_LABELS = dict(DEADLINE_OPTIONS)

# Parâmetros que o painel de filtros controla (o resto da URL volta como campo oculto do formulário).
PANEL_PARAMS = ("setor", "pessoa", "estagio", "condicao", "cliente", "obra", "prazo", "filtro")
SEARCH_PARAMS = ("q",)
NEVER_FORWARD = ("page", "view", "visao")


# -- URLs -------------------------------------------------------------------------------------


def canonical_params(params):
    """Cópia de `params` com os apelidos antigos trocados pelo nome canônico (`responsavel`→`pessoa`, `grupo`/`sector`→
    `setor`, `sort`→`ordem`). A tela aceita os dois, mas todo link e formulário novo escreve só o canônico."""
    query = params.copy()
    for name, aliases in ALIASES.items():
        values = None
        for candidate in (name, *aliases):
            found = [value for value in query.getlist(candidate) if value not in ("", None)]
            if found:
                values = list(dict.fromkeys(found))
                break
        for alias in aliases:
            query.pop(alias, None)
        if values is not None:
            query.setlist(name, values)
    return query


def query_with(params, changes=None, drop=()):
    """Querystring a partir de `params` (QueryDict): troca/remove o que foi pedido, leva o resto e **nunca** leva
    `page`/`view`/`visao`. Os apelidos antigos viram o nome canônico (`responsavel`→`pessoa`…)."""
    query = canonical_params(params)
    for name in (*NEVER_FORWARD, *drop):
        query.pop(name, None)
        for alias in ALIASES.get(name, ()):
            query.pop(alias, None)
    for name, value in (changes or {}).items():
        for alias in ALIASES.get(name, ()):
            query.pop(alias, None)
        if value in (None, "", [], ()):
            query.pop(name, None)
        elif isinstance(value, (list, tuple)):
            query.setlist(name, [str(item) for item in value])
        else:
            query[name] = str(value)
    return query.urlencode()


def url_with(path, params, changes=None, drop=()):
    query = query_with(params, changes, drop)
    return f"{path}?{query}" if query else path


def hidden_fields(params, exclude=()):
    """Campos ocultos (nome, valor) que um formulário da barra precisa reenviar para **não perder** o resto do estado
    (escopo, mostrar, agrupar, ordenar, mês…). Os controles do próprio formulário e os apelidos deles ficam de fora."""
    skip = set(NEVER_FORWARD) | set(exclude)
    query = canonical_params(params)
    return [(name, value) for name in query for value in query.getlist(name) if name not in skip]


# -- ordenação --------------------------------------------------------------------------------


def sort_state(filters):
    """(ordem, sentido) efetivos. Valor desconhecido cai no padrão (prazo, do mais próximo)."""
    order = filters.get("ordem") or "prazo"
    if order not in DEFAULT_DIRECTION:
        order = "prazo"
    direction = filters.get("dir") if filters.get("dir") in ("asc", "desc") else DEFAULT_DIRECTION[order]
    return order, direction


def order_expressions(filters):
    """Expressões de `order_by` da Lista/Kanban/Calendário. **Nulos sempre no fim** (SQLite e PostgreSQL ordenam NULL
    de formas opostas) e desempate estável por criação."""
    order, direction = sort_state(filters)
    ascending = direction == "asc"
    if order == "titulo":
        primary = F("title").asc() if ascending else F("title").desc()
        return [primary, "-created_at", "pk"]
    if order == "recentes":
        primary = F("created_at").asc() if ascending else F("created_at").desc()
        return [primary, "pk"]
    primary = F("requested_deadline").asc(nulls_last=True) if ascending else F("requested_deadline").desc(nulls_last=True)
    return [primary, "-created_at", "pk"]


# -- grupos de Etapa/Status por setor ---------------------------------------------------------


def stage_and_status_groups(organization):
    """Etapas e Status (da Demanda) agrupados por setor, com o id do setor para o painel filtrar sem recarregar."""
    sectors = {sector.pk: sector for sector in Sector.objects.filter(organization=organization, is_active=True)}
    stages, statuses = {}, {}
    for stage in ActivityStage.objects.filter(organization=organization, is_active=True).order_by("order", "name", "pk"):
        stages.setdefault(stage.sector_id, []).append(stage)
    for status in WorkflowStatus.objects.filter(
        organization=organization, domain=WorkflowStatus.Domain.ACTIVITY, is_active=True
    ).order_by("order", "name", "pk"):
        statuses.setdefault(status.sector_id, []).append(status)

    def build(source):
        return [
            {"sector_id": sector.pk, "sector_name": sector.name, "items": source[sector.pk]}
            for sector in sorted(sectors.values(), key=lambda item: item.name.lower())
            if source.get(sector.pk)
        ]

    return build(stages), build(statuses)


# -- o contexto da barra ----------------------------------------------------------------------


def build_workspace(request, *, organization, view_mode, filters, activities, groups, people, sectors, group_by, grouped_list):
    """Tudo o que `templates/workspace/*.html` precisa para desenhar cabeçalho, abas e barra.

    `filters` é o dicionário de `activities.filtering.normalize_workspace_filters`; `group_by` é o agrupamento
    **efetivo** (URL > padrão salvo da visão); `grouped_list` diz se a Lista deve vir em seções (só com `agrupar`
    explícito na URL)."""
    params = request.GET
    user = request.user
    can_view_all = AuthorizationService.can(user, catalog.ATIVIDADE_VISUALIZAR_TODAS)

    def link(path, changes=None, drop=()):
        return url_with(path, params, changes, drop)

    current_path = request.path
    tabs = [
        {
            "key": key,
            "label": label,
            "icon": icon,
            "url": link(reverse(url_name)),
            "active": key == view_mode,
        }
        for key, label, icon, url_name in VIEWS
    ]

    # Escopo (quem/alcance) e "Mostrar" (estado) são DUAS dimensões. `tab=concluidas` é só o link antigo das duas juntas.
    legacy_done_tab = filters["tab"] == "concluidas"
    scope_key = filters["tab"] if filters["tab"] in {key for key, _l in SCOPES} else "minhas"
    scope_options = []
    for key, label in SCOPES:
        if key == "todas" and not can_view_all:
            continue
        changes = {"tab": None if key == "minhas" else key}
        if legacy_done_tab:
            changes["concluidas"] = "1"
        scope_options.append({"key": key, "label": label, "url": link(current_path, changes), "active": key == scope_key})

    showing_done = bool(filters["concluidas"])
    show_options = []
    for key, label in SHOW:
        if key == "concluidas":
            changes, drop = {"concluidas": "1"}, ()
        else:
            changes = {"tab": None} if legacy_done_tab else {}
            drop = ("concluidas", "status") if params.get("status") == "concluidas" else ("concluidas",)
        show_options.append({"key": key, "label": label, "url": link(current_path, changes, drop), "active": (key == "concluidas") == showing_done})

    # Agrupar: Lista e Kanban. Na Lista, "Sem agrupar" é o padrão; no Kanban sempre há um agrupamento (as raias).
    group = None
    if view_mode in ("lista", "kanban"):
        options = []
        if view_mode == "lista":
            options.append({"key": "", "label": "Sem agrupar", "url": link(current_path, {"agrupar": None}), "active": not grouped_list})
        for key, label in GROUPINGS:
            active = key == group_by if (view_mode == "kanban" or grouped_list) else False
            options.append({"key": key, "label": label, "url": link(current_path, {"agrupar": key}), "active": active})
        group = {"options": options}

    # Ordenar: Lista e Kanban (dentro das raias). Calendário não tem controle, mas o estado continua na URL.
    sort = None
    if view_mode in ("lista", "kanban"):
        order, direction = sort_state(filters)
        options = []
        for key, sense, label in SORTS:
            changes = {"ordem": None if (key == "prazo" and sense == "asc") else key,
                       "dir": None if sense == DEFAULT_DIRECTION[key] else sense}
            options.append({"key": f"{key}:{sense}", "label": label, "url": link(current_path, changes),
                            "active": (key, sense) == (order, direction)})
        sort = {"options": options}

    # Painel de filtros (rascunho; um único "Aplicar filtros").
    stage_groups, status_groups = stage_and_status_groups(organization)
    selected_people = [str(value) for value in filters["pessoas"]]
    client = Client.objects.filter(organization=organization, pk=filters["cliente"]).first() if filters["cliente"] else None
    site = Site.objects.filter(organization=organization, pk=filters["obra"]).first() if filters["obra"] else None
    sector_by_id = {str(sector.pk): sector for sector in sectors}
    people_by_id = {str(person.pk): person for person in people}

    def person_name(person):
        return person.get_full_name() or person.get_username()

    # Chips dos filtros ativos (cada remoção aplica na hora).
    chips = []

    def chip(label, value, drop):
        chips.append({"label": label, "value": value, "url": link(current_path, drop=drop)})

    if filters["q"]:
        chip("Busca", filters["q"], ("q",))
    if filters["setor"] and filters["setor"] in sector_by_id:
        chip("Setor", sector_by_id[filters["setor"]].name, ("setor",))
    if selected_people:
        names = []
        for value in selected_people:
            if value == "sem":
                names.append("Sem responsável")
            elif value == "eu":
                names.append("Eu")
            elif value in people_by_id:
                names.append(person_name(people_by_id[value]))
        if names:
            chip("Responsável", ", ".join(names), ("pessoa",))
    if filters["estagio"]:
        stage = next((item for group in stage_groups for item in group["items"] if str(item.pk) == filters["estagio"]), None)
        if stage:
            chip("Etapa", stage.name, ("estagio",))
    if filters["condicao"]:
        status = next((item for group in status_groups for item in group["items"] if str(item.pk) == filters["condicao"]), None)
        if status:
            chip("Status", status.name, ("condicao",))
    if client:
        chip("Cliente", client.name, ("cliente",))
    if site:
        chip("Obra", site.name, ("obra",))
    if filters["prazo"]:
        chip("Prazo", DEADLINE_LABELS.get(filters["prazo"], filters["prazo"]), ("prazo", "filtro"))

    panel_active = [item for item in chips if item["label"] != "Busca"]
    clear_drop = ("q", *PANEL_PARAMS)
    panel = {
        "sectors": sectors,
        "selected_sector": filters["setor"],
        "stage_groups": stage_groups,
        "selected_stage": filters["estagio"],
        "status_groups": status_groups,
        "selected_status": filters["condicao"],
        "people": people,
        "selected_people": selected_people,
        "client": client,
        "site": site,
        "deadlines": DEADLINE_OPTIONS,
        "selected_deadline": filters["prazo"],
        "hidden": hidden_fields(params, exclude=PANEL_PARAMS),
        "open": bool(panel_active),
        "active_count": len(panel_active),
        "clear_url": link(current_path, drop=clear_drop),
    }
    search = {"value": filters["q"], "hidden": hidden_fields(params, exclude=SEARCH_PARAMS)}

    # Avisos: filtro inválido ignorado e escopo "Minhas" com responsável de outra pessoa (sem mudar nada escondido).
    notices = []
    invalid = filters.get("invalid") or []
    if invalid:
        notices.append({"kind": "info", "text": "Ignoramos o filtro inválido: " + ", ".join(invalid) + "."})
    if scope_key == "minhas":
        others = [value for value in selected_people if value not in ("eu", str(user.pk))]
        if others:
            names = []
            for value in others:
                if value == "sem":
                    names.append("Sem responsável")
                elif value in people_by_id:
                    names.append(person_name(people_by_id[value]))
            text = "Você está vendo só “Minhas”. " + (", ".join(names) or "Essa pessoa") + " pode não aparecer."
            action = {"label": "Ver Todas", "url": link(current_path, {"tab": "todas"})} if can_view_all else None
            notices.append({"kind": "warning", "text": text, "action": action})

    # Escopo é "quem/alcance", não filtro: só chips e "Concluídas" contam para o vazio "com esses filtros".
    has_filters = bool(chips) or showing_done
    return {
        "view": view_mode,
        "title": "Demandas",
        "subtitle": "Acompanhe cada entrega e abra uma demanda para ver suas tarefas, prazos e conversas.",
        "location": "Demandas",
        "tabs": tabs,
        "count": len(activities),
        # Seções da Lista (só com `agrupar` na URL): raias vazias não viram seção.
        "list_groups": [group for group in groups if group["items"]] if (view_mode == "lista" and grouped_list) else None,
        "scope": {"options": scope_options},
        "show": {"options": show_options},
        "group": group,
        "sort": sort,
        "search": search,
        "panel": panel,
        "chips": chips,
        "notices": notices,
        "has_filters": has_filters,
        "clear_url": panel["clear_url"],
        "can_view_all": can_view_all,
    }
