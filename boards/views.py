"""Telas e endpoints do motor de quadros.

Views finas: resolvem o objeto da organização certa (outra organização = 404), chamam o serviço e devolvem o
resultado. Toda regra, autorização e auditoria vive em `boards.services`. Os endpoints de edição respondem
JSON e, quando a tela precisa redesenhar algo, devolvem o fragmento HTML pronto (`header_html`, `cell_html`,
`row_html`), para o navegador não precisar conhecer a regra de como cada tipo se desenha.
"""

import json
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from acessos import catalog
from acessos.services import AuthorizationService, ResourceContext
from core.mixins import OrganizationRequiredMixin
from core.models import Sector

from .calendar_view import (
    DEFAULT_CARD_FIELD_COUNT,
    MAX_CARD_FIELDS,
    MAX_VISIBLE_PER_DAY,
    PANEL_LIMIT,
    build_month,
    clean_calendar_settings,
    date_columns,
    grid_range,
    colorable_columns,
    parse_month,
    resolve_card_columns as resolve_calendar_card_columns,
    resolve_color_source,
    resolve_date_column,
    resolve_status_column,
    month_key,
    month_title,
    shift_month,
)
from .kanban import (
    GROUPABLE_TYPES,
    SUMMABLE_TYPES,
    build_lanes,
    clean_kanban_settings,
    resolve_card_columns,
    resolve_group_column,
    resolve_sum_column,
    sort_choice,
    sort_options,
)
from .models import Board, BoardColumn, BoardColumnOption, BoardGroup, BoardItem, BoardView
from .presentation import board_meta, board_permissions, column_meta
from .queries import BoardQueryService
from .services import (
    BoardError,
    BoardPermissionError,
    BoardService,
    CellService,
    ColumnService,
    GroupService,
    ItemService,
    OptionService,
    ViewService,
    clean_view_settings,
    _require as require_action,
)
from .starter_templates import create_board_from_template, template_choices

User = get_user_model()

HISTORY_PAGE_SIZE = 50
NAME_COLUMN_WIDTH = 280  # a primeira coluna (nome do item) tem largura fixa, igual no CSS e no JS
ADD_COLUMN_WIDTH = 64
SEARCH_MAX_LENGTH = 120
MAX_INITIAL_VALUES = 30
DRAWER_HISTORY_LIMIT = 8


# ---------------------------------------------------------------------------
# Carregamento (sempre pela organização da pessoa: outra organização = 404)
# ---------------------------------------------------------------------------


def get_board(organization, pk):
    return get_object_or_404(Board, pk=pk, organization=organization, is_active=True)


def get_group(organization, pk):
    return get_object_or_404(
        BoardGroup.objects.select_related("board"),
        pk=pk, board__organization=organization, board__is_active=True, is_active=True,
    )


def get_column(organization, pk):
    return get_object_or_404(
        BoardColumn.objects.select_related("board").prefetch_related("options"),
        pk=pk, board__organization=organization, board__is_active=True, is_active=True,
    )


def get_option(organization, pk):
    return get_object_or_404(
        BoardColumnOption.objects.select_related("column__board"),
        pk=pk, column__board__organization=organization, column__board__is_active=True,
        column__is_active=True, is_active=True,
    )


def get_view(organization, pk):
    return get_object_or_404(
        BoardView.objects.select_related("board"),
        pk=pk, is_active=True, board__organization=organization, board__is_active=True,
    )


def board_people(board):
    """Pessoas que aparecem em alguma célula de Pessoa do quadro (alimenta o filtro por pessoa)."""
    people = User.objects.filter(
        board_cell_values__cell__item__board=board,
        board_cell_values__cell__item__is_active=True,
        board_cell_values__cell__column__is_active=True,
    )
    return list(people.distinct().order_by("first_name", "username"))


def get_item(organization, pk):
    return get_object_or_404(
        BoardItem.objects.select_related("board", "group"),
        pk=pk, board__organization=organization, board__is_active=True, is_active=True,
    )


def _int_or_none(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Fragmentos HTML
# ---------------------------------------------------------------------------


def _item_for_render(board, item_id, columns):
    queryset = BoardQueryService.with_cells(BoardItem.objects.filter(pk=item_id, board=board).select_related("group"))
    items = BoardQueryService.attach_cells(list(queryset), {column.pk: column for column in columns})
    return items[0]


def render_header(request, board, column, permissions, *, sort_column_id=None, direction="asc"):
    return render_to_string(
        "boards/_column_header.html",
        {
            "board": board, "column": column, "permissions": permissions,
            "sort_column_id": sort_column_id, "sort_dir": direction,
        },
        request=request,
    )


def render_cell(request, board, item, column, permissions):
    return render_to_string(
        "boards/_cell_td.html",
        {"board": board, "item": item, "column": column, "cell": getattr(item, "cell_map", {}).get(column.pk),
         "permissions": permissions},
        request=request,
    )


def render_row(request, board, item, columns, permissions):
    return render_to_string(
        "boards/_item_row.html",
        {"board": board, "item": item, "columns": columns, "permissions": permissions},
        request=request,
    )


# ---------------------------------------------------------------------------
# Base dos endpoints JSON
# ---------------------------------------------------------------------------


class BoardAPIView(OrganizationRequiredMixin, View):
    """POST com corpo JSON. Recusa de permissão = 403, regra de negócio = 400, pede confirmação = 409.

    Subclasses implementam `handle(request, data, **kwargs)` e devolvem um dict (vira `{"ok": true, ...}`)
    ou uma `JsonResponse`.
    """

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        data = self.read_json(request)
        if data is None:
            return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)
        try:
            result = self.handle(request, data, **kwargs)
        except BoardPermissionError as exc:
            return JsonResponse({"ok": False, "error": str(exc) or "Você não tem permissão para isso."}, status=403)
        except BoardError as exc:
            status = 409 if exc.needs_confirmation else 400
            return JsonResponse(
                {"ok": False, "error": str(exc), "needs_confirmation": exc.needs_confirmation}, status=status
            )
        if isinstance(result, JsonResponse):
            return result
        return JsonResponse({"ok": True, **(result or {})})

    @staticmethod
    def read_json(request):
        if not request.body:
            return {}
        try:
            data = json.loads(request.body)
        except (ValueError, UnicodeDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def handle(self, request, data, **kwargs):  # pragma: no cover - contrato
        raise NotImplementedError

    # -- apoio comum -----------------------------------------------------------

    def require(self, action, resource):
        """Para o que o serviço não cobre sozinho (resposta que só lê, prévia): a mesma recusa dos serviços."""
        require_action(self.request.user, action, resource)

    def permissions(self, board):
        return board_permissions(self.request.user, board)

    def columns_of(self, board):
        return list(BoardQueryService.columns(board, visible=True))


# ---------------------------------------------------------------------------
# Lista, criação, detalhe e histórico
# ---------------------------------------------------------------------------


class BoardListView(OrganizationRequiredMixin, TemplateView):
    template_name = "boards/board_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scope = ResourceContext.for_new(self.organization)
        if not AuthorizationService.can(self.request.user, catalog.QUADRO_VISUALIZAR, scope):
            raise PermissionDenied("Você não possui acesso a este conteúdo.")
        boards = list(
            Board.objects.filter(
                organization=self.organization, is_active=True, kind=Board.Kind.TEMPLATE
            ).select_related("sector").order_by("name", "id")
        )
        context.update(
            boards=boards,
            can_create=AuthorizationService.can(self.request.user, catalog.QUADRO_CRIAR, scope),
            template_choices=template_choices(),
            sectors=Sector.objects.filter(organization=self.organization, is_active=True).order_by("name"),
        )
        return context


class BoardCreateView(OrganizationRequiredMixin, View):
    """Formulário simples (funciona sem JavaScript): cria o quadro em branco ou a partir de um modelo."""

    http_method_names = ["post"]

    def post(self, request):
        name = request.POST.get("name", "")
        template_key = request.POST.get("template", "").strip()
        sector = get_object_or_404(
            Sector, pk=_int_or_none(request.POST.get("sector_id")) or 0,
            organization=self.organization, is_active=True,
        )
        try:
            if template_key:
                board = create_board_from_template(
                    user=request.user, organization=self.organization, key=template_key, name=name, sector=sector
                )
            else:
                board = BoardService.create(user=request.user, organization=self.organization, name=name, sector=sector)
        except BoardPermissionError:
            raise PermissionDenied("Você não possui permissão para criar quadros.")
        except BoardError as exc:
            messages.error(request, str(exc))
            return redirect("board-list")
        messages.success(request, f"Quadro “{board.name}” criado.")
        return redirect("board-detail", pk=board.pk)


class BoardDetailView(OrganizationRequiredMixin, TemplateView):
    template_name = "boards/board_detail.html"

    def get_context_data(self, pk, **kwargs):
        context = super().get_context_data(**kwargs)
        board = get_board(self.organization, pk)
        user = self.request.user
        permissions = board_permissions(user, board)
        if not permissions["view"]:
            raise PermissionDenied("Você não possui acesso a este conteúdo.")

        all_columns = list(BoardQueryService.columns(board, visible=None))
        columns = [column for column in all_columns if column.is_visible]
        hidden_columns = [column for column in all_columns if not column.is_visible]
        groups = list(BoardQueryService.groups(board))

        sort_column = None
        sort_id = _int_or_none(self.request.GET.get("sort"))
        direction = "desc" if self.request.GET.get("dir") == "desc" else "asc"
        if sort_id is not None:
            sort_column = next((column for column in columns if column.pk == sort_id), None)
            if sort_column is not None and BoardQueryService.sort_expression(sort_column) is None:
                sort_column = None
        search = (self.request.GET.get("q") or "").strip()[:SEARCH_MAX_LENGTH]
        person_id = _int_or_none(self.request.GET.get("pessoa"))

        items = BoardQueryService.with_cells(
            BoardQueryService.items(
                board, sort_column=sort_column, direction=direction, search=search, person_id=person_id
            )
        )
        items = BoardQueryService.attach_cells(list(items), {column.pk: column for column in columns})
        items_by_group = {group.pk: [] for group in groups}
        for item in items:
            items_by_group.setdefault(item.group_id, []).append(item)
        for group in groups:
            group.board_items = items_by_group.get(group.pk, [])

        context.update(
            board=board,
            groups=groups,
            columns=columns,
            hidden_columns=hidden_columns,
            permissions=permissions,
            meta=board_meta(board, columns, groups, permissions=permissions, sort_column=sort_column, direction=direction),
            sort_column_id=sort_column.pk if sort_column else None,
            sort_dir=direction,
            search=search,
            person_id=person_id,
            people=board_people(board),
            views=list(board.views.filter(is_active=True)),
            active_view=None,
            table_width=NAME_COLUMN_WIDTH + ADD_COLUMN_WIDTH + sum(column.width for column in columns),
            total_items=len(items),
            filtering=bool(search or person_id),
        )
        return context


class DemandTaskBoardView(BoardDetailView):
    """Entrada única de Tarefas: seleciona uma Demanda e abre seu Board próprio."""

    template_name = "boards/task_board.html"

    def _available_boards(self):
        from .demand_services import DemandBoardAccess

        boards = list(
            Board.objects.filter(
                organization=self.organization,
                kind=Board.Kind.DEMAND,
                is_active=True,
                activity__status__in=(
                    "ABERTA", "EM_ANDAMENTO", "PENDENTE", "CONCLUIDA", "CANCELADA",
                ),
            )
            .select_related("activity", "activity__owner", "activity__created_by")
            .order_by("activity__title", "activity_id")
        )
        return [board for board in boards if DemandBoardAccess.can_view(self.request.user, board)]

    def get_context_data(self, **kwargs):
        boards = self._available_boards()
        board_id = _int_or_none(self.request.GET.get("demanda"))
        selected = next((entry for entry in boards if entry.activity_id == board_id), None)
        if board_id is not None and selected is None:
            raise Http404("Demanda nÃ£o encontrada.")

        if selected is None:
            context = TemplateView.get_context_data(self, **kwargs)
        else:
            context = super().get_context_data(pk=selected.pk, **kwargs)
        context["accessible_demands"] = [entry.activity for entry in boards]
        return context


def kanban_context(view, *, permissions, search="", person_id=None):
    """O que a página e o fragmento das raias precisam: as mesmas colunas e os mesmos itens da tabela, só reorganizados."""
    board = view.board
    all_columns = list(BoardQueryService.columns(board, visible=None))
    group_column = resolve_group_column(view.settings, all_columns)
    sum_column = resolve_sum_column(view.settings, all_columns)
    card_columns = resolve_card_columns(view.settings, all_columns, group_column)
    sort, direction = sort_choice(view.settings, all_columns)

    used = {column.pk: column for column in card_columns}
    for extra in (group_column, sum_column):
        if extra is not None:
            used[extra.pk] = extra
    items = BoardQueryService.with_cells(
        BoardQueryService.kanban_items(board, sort=sort, direction=direction, search=search, person_id=person_id)
    )
    items = BoardQueryService.attach_cells(list(items), used)
    lanes = build_lanes(group_column, items, view.settings, sum_column)
    settings = clean_kanban_settings(all_columns, {}, current=view.settings)
    return {
        "board": board,
        "view": view,
        "lanes": lanes,
        "group_column": group_column,
        "sum_column": sum_column,
        "card_columns": card_columns,
        "show_field_names": bool(settings["show_field_names"]),
        "permissions": permissions,
        "all_columns": all_columns,
        "settings": settings,
        "total_items": len(items),
        "kanban_meta": {
            "view": {"id": view.pk, "name": view.name},
            "settings": settings,
            "group_column_id": group_column.pk if group_column else None,
            "sum_column_id": sum_column.pk if sum_column else None,
            "card_column_ids": [column.pk for column in card_columns],
            "groupable_ids": [c.pk for c in all_columns if c.type in GROUPABLE_TYPES],
            "summable_ids": [c.pk for c in all_columns if c.type in SUMMABLE_TYPES],
        },
    }


def _keep_query(search, person_id):
    """Busca e pessoa em formato de query string, para os links de mês levarem os filtros junto."""
    params = {}
    if search:
        params["q"] = search
    if person_id:
        params["pessoa"] = person_id
    return "&" + urlencode(params) if params else ""


def calendar_context(view, *, permissions, month=None, search="", person_id=None):
    """O que a página e o fragmento do calendário precisam: os mesmos itens da tabela, só que posicionados no dia da coluna
    de Data escolhida. Só se busca o intervalo da grade (o mês e a margem das semanas de ponta), nunca o histórico todo."""
    board = view.board
    all_columns = list(BoardQueryService.columns(board, visible=None))
    settings = clean_calendar_settings(all_columns, {}, current=view.settings)
    date_column = resolve_date_column(settings, all_columns)
    status_column = resolve_status_column(all_columns)
    color_kind, color_column = resolve_color_source(settings, all_columns)
    card_columns = resolve_calendar_card_columns(settings, all_columns, date_column, color_column)
    today = timezone.localdate()
    year, number = parse_month(month, today)

    context = {
        "board": board,
        "view": view,
        "permissions": permissions,
        "all_columns": all_columns,
        "settings": settings,
        "date_column": date_column,
        "color_kind": color_kind,
        "color_column": color_column,
        "card_columns": card_columns,
        "calendar": None,
        "month_title": month_title(year, number),
        "month_key": month_key(year, number),
        "prev_month": month_key(*shift_month(year, number, -1)),
        "next_month": month_key(*shift_month(year, number, 1)),
        "today_month": month_key(today.year, today.month),
        "max_visible": MAX_VISIBLE_PER_DAY,
        "nodate_items": [], "nodate_count": 0, "nodate_more": 0,
        "overdue_items": [], "overdue_count": 0, "overdue_more": 0,
        "keep_query": _keep_query(search, person_id),
        "search": search,
        "person_id": person_id,
        "calendar_meta": {
            "view": {"id": view.pk, "name": view.name},
            "settings": settings,
            "date_column_id": date_column.pk if date_column else None,
            "status_column_id": status_column.pk if status_column else None,
            "color_kind": color_kind,
            "color_column_id": color_column.pk if color_column else None,
            "card_column_ids": [column.pk for column in card_columns],
            "dateable_ids": [column.pk for column in date_columns(all_columns)],
            "colorable_ids": [column.pk for column in colorable_columns(all_columns)],
            "month": month_key(year, number),
            "today": today.isoformat(),
            "max_visible": MAX_VISIBLE_PER_DAY,
            "max_card_fields": MAX_CARD_FIELDS,
            "recommended_card_fields": DEFAULT_CARD_FIELD_COUNT,
        },
    }
    if date_column is None:
        return context

    used = {column.pk: column for column in card_columns}
    for extra in (date_column, status_column, color_column):
        if extra is not None:
            used[extra.pk] = extra
    start, end = grid_range(year, number)
    show_completed = bool(settings["show_completed"])
    filters = {"search": search, "person_id": person_id}
    items = BoardQueryService.with_cells(
        BoardQueryService.calendar_items(
            board, date_column, start, end, status_column=status_column, show_completed=show_completed, **filters
        )
    )
    items = BoardQueryService.attach_cells(list(items), used)
    context["calendar"] = build_month(
        year, number, items, date_column=date_column, status_column=status_column, color_kind=color_kind,
        color_column=color_column, card_columns=card_columns, show_weekends=bool(settings["show_weekends"]),
        show_completed=show_completed, today=today,
    )

    undated = BoardQueryService.calendar_undated(
        board, date_column, status_column=status_column, show_completed=show_completed, **filters
    )
    context["nodate_count"] = undated.count()
    context["nodate_items"] = list(undated[:PANEL_LIMIT])
    context["nodate_more"] = max(0, context["nodate_count"] - len(context["nodate_items"]))
    if (date_column.settings or {}).get("is_deadline"):
        overdue = BoardQueryService.calendar_overdue(board, date_column, today, status_column=status_column, **filters)
        context["overdue_count"] = overdue.count()
        context["overdue_items"] = list(overdue[:PANEL_LIMIT])
        context["overdue_more"] = max(0, context["overdue_count"] - len(context["overdue_items"]))
    context["has_deadline"] = bool((date_column.settings or {}).get("is_deadline"))
    return context


class BoardViewDetailView(OrganizationRequiredMixin, TemplateView):
    """A visualização escolhida na aba. Cada tipo tem a sua página (Kanban, Calendário), todas sobre os mesmos itens."""

    template_name = "boards/board_kanban.html"

    def get_template_names(self):
        if getattr(self, "board_view", None) is not None and self.board_view.type == BoardView.Type.CALENDAR:
            return ["boards/board_calendar.html"]
        return [self.template_name]

    def get_context_data(self, pk, **kwargs):
        context = super().get_context_data(**kwargs)
        view = get_view(self.organization, pk)
        self.board_view = view
        board = view.board
        permissions = board_permissions(self.request.user, board)
        if not permissions["view"]:
            raise PermissionDenied("Você não possui acesso a este conteúdo.")
        search = (self.request.GET.get("q") or "").strip()[:SEARCH_MAX_LENGTH]
        person_id = _int_or_none(self.request.GET.get("pessoa"))

        if view.type == BoardView.Type.CALENDAR:
            context.update(
                calendar_context(
                    view, permissions=permissions, month=self.request.GET.get("mes"), search=search, person_id=person_id
                )
            )
            groups = list(BoardQueryService.groups(board))
            meta = board_meta(board, context["all_columns"], groups, permissions=permissions)
            meta["calendar"] = {**context["calendar_meta"], "default_group_id": groups[0].pk if groups else None}
            context.update(
                meta=meta,
                views=list(board.views.filter(is_active=True)),
                active_view=view,
                people=board_people(board),
                filtering=bool(search or person_id),
            )
            return context

        context.update(kanban_context(view, permissions=permissions, search=search, person_id=person_id))
        groups = list(BoardQueryService.groups(board))
        all_columns = context["all_columns"]
        meta = board_meta(board, all_columns, groups, permissions=permissions)
        meta["kanban"] = {**context["kanban_meta"], "default_group_id": groups[0].pk if groups else None}
        context.update(
            meta=meta,
            views=list(board.views.filter(is_active=True)),
            active_view=view,
            group_candidates=[c for c in all_columns if c.type in GROUPABLE_TYPES],
            sort_options=sort_options(all_columns, view.settings),
            search=search,
            person_id=person_id,
            people=board_people(board),
            filtering=bool(search or person_id),
        )
        return context


class ViewCreateView(BoardAPIView):
    def handle(self, request, data, pk):
        board = get_board(self.organization, pk)
        settings = data.get("settings")
        if settings is not None and not isinstance(settings, dict):
            raise BoardError("Configuração inválida.")
        view = ViewService.create(
            user=request.user, board=board, name=data.get("name", ""),
            view_type=str(data.get("type") or BoardView.Type.KANBAN), settings=settings,
        )
        return {"view": {"id": view.pk, "name": view.name}, "redirect_url": reverse("board-view-detail", args=[view.pk])}


class ViewUpdateView(BoardAPIView):
    def handle(self, request, data, pk):
        view = get_view(self.organization, pk)
        settings = data.get("settings")
        if settings is not None and not isinstance(settings, dict):
            raise BoardError("Configuração inválida.")
        ViewService.update(
            user=request.user, view=view, name=data.get("name") if "name" in data else None, settings=settings
        )
        columns = list(BoardQueryService.columns(view.board, visible=None))
        return {
            "view": {"id": view.pk, "name": view.name},
            "settings": clean_view_settings(view.type, columns, {}, current=view.settings),
        }


class ViewDeleteView(BoardAPIView):
    def handle(self, request, data, pk):
        view = get_view(self.organization, pk)
        ViewService.soft_delete(user=request.user, view=view)
        return {"redirect_url": reverse("board-detail", args=[view.board_id])}


class ViewLanesView(BoardAPIView):
    """Redesenha as raias (depois de mudar a coluna agrupadora, a configuração do cartão, uma etiqueta ou mover um
    cartão): o servidor é quem sabe distribuir os itens, então o navegador só troca o HTML."""

    def handle(self, request, data, pk):
        view = get_view(self.organization, pk)
        if view.type != BoardView.Type.KANBAN:
            raise Http404()  # as raias são do Kanban; o calendário tem a sua rota
        permissions = self.permissions(view.board)
        if not permissions["view"]:
            raise BoardPermissionError("Você não possui acesso a este conteúdo.")
        search = str(data.get("q") or "").strip()[:SEARCH_MAX_LENGTH]
        context = kanban_context(view, permissions=permissions, search=search, person_id=_int_or_none(data.get("pessoa")))
        return {
            "lanes_html": render_to_string("boards/_kanban_lanes.html", context, request=request),
            "total_items": context["total_items"],
            "columns": [column_meta(column) for column in context["all_columns"]],
            **{key: context["kanban_meta"][key] for key in ("settings", "group_column_id", "sum_column_id", "card_column_ids")},
        }


class ViewCalendarView(BoardAPIView):
    """Redesenha o corpo do calendário (trocar de mês, depois de mover/criar/editar um item ou de mudar a configuração): o
    servidor é quem sabe posicionar os cartões, então o navegador só troca o HTML. Mantém busca e pessoa."""

    def handle(self, request, data, pk):
        view = get_view(self.organization, pk)
        if view.type != BoardView.Type.CALENDAR:
            raise Http404()
        permissions = self.permissions(view.board)
        if not permissions["view"]:
            raise BoardPermissionError("Você não possui acesso a este conteúdo.")
        search = str(data.get("q") or "").strip()[:SEARCH_MAX_LENGTH]
        context = calendar_context(
            view, permissions=permissions, month=data.get("mes"), search=search, person_id=_int_or_none(data.get("pessoa"))
        )
        return {
            "body_html": render_to_string("boards/_calendar_body.html", context, request=request),
            "title": context["month_title"],
            "month": context["month_key"],
            "prev": context["prev_month"],
            "next": context["next_month"],
            "today": context["today_month"],
            "columns": [column_meta(column) for column in context["all_columns"]],
            **{
                key: context["calendar_meta"][key]
                for key in (
                    "settings", "date_column_id", "color_kind", "color_column_id", "card_column_ids",
                    "dateable_ids", "colorable_ids",
                )
            },
        }


class BoardHistoryView(OrganizationRequiredMixin, TemplateView):
    template_name = "boards/board_history.html"

    def get_context_data(self, pk, **kwargs):
        context = super().get_context_data(**kwargs)
        board = get_board(self.organization, pk)
        permissions = board_permissions(self.request.user, board)
        if not permissions["view"]:
            raise PermissionDenied("Você não possui acesso a este conteúdo.")
        page = Paginator(BoardQueryService.history(board), HISTORY_PAGE_SIZE).get_page(self.request.GET.get("page"))
        context.update(board=board, page=page, permissions=permissions)
        return context


# ---------------------------------------------------------------------------
# Quadro
# ---------------------------------------------------------------------------


class BoardRenameView(BoardAPIView):
    def handle(self, request, data, pk):
        board = get_board(self.organization, pk)
        BoardService.update(
            user=request.user, board=board,
            name=data.get("name") if "name" in data else None,
            description=data.get("description") if "description" in data else None,
        )
        return {"name": board.name, "description": board.description}


class BoardDeleteView(BoardAPIView):
    def handle(self, request, data, pk):
        board = get_board(self.organization, pk)
        BoardService.soft_delete(user=request.user, board=board)
        messages.success(request, f"Quadro “{board.name}” excluído.")
        return {"redirect_url": reverse("board-list")}


# ---------------------------------------------------------------------------
# Grupos
# ---------------------------------------------------------------------------


class GroupCreateView(BoardAPIView):
    def handle(self, request, data, pk):
        board = get_board(self.organization, pk)
        group = GroupService.create(user=request.user, board=board, name=data.get("name", "Novo grupo"),
                                    color=data.get("color"))
        group.board_items = []
        columns = self.columns_of(board)
        html = render_to_string(
            "boards/_group.html",
            {"board": board, "group": group, "columns": columns, "permissions": self.permissions(board),
             "colspan": len(columns) + 2, "sort_column_id": None, "sort_dir": "asc"},
            request=request,
        )
        return {"group": {"id": group.pk, "name": group.name, "color": group.color}, "group_html": html}


class GroupUpdateView(BoardAPIView):
    def handle(self, request, data, pk):
        group = get_group(self.organization, pk)
        GroupService.update(
            user=request.user, group=group,
            name=data.get("name") if "name" in data else None,
            color=data.get("color") if "color" in data else None,
        )
        return {"group": {"id": group.pk, "name": group.name, "color": group.color}}


class GroupReorderView(BoardAPIView):
    def handle(self, request, data, pk):
        group = get_group(self.organization, pk)
        GroupService.reorder(
            user=request.user, group=group,
            before_id=_int_or_none(data.get("before_id")), after_id=_int_or_none(data.get("after_id")),
        )
        return {"position": str(group.position)}


class GroupDeleteView(BoardAPIView):
    def handle(self, request, data, pk):
        group = get_group(self.organization, pk)
        GroupService.soft_delete(user=request.user, group=group)
        return {}


# ---------------------------------------------------------------------------
# Colunas
# ---------------------------------------------------------------------------


class ColumnFragmentMixin:
    """Resposta com o cabeçalho da coluna e as células dela já desenhados (cada item, uma célula)."""

    def column_payload(self, request, board, column, *, with_cells=True, sort_column_id=None, direction="asc"):
        permissions = self.permissions(board)
        column = get_column(self.organization, column.pk)
        payload = {
            "column": column_meta(column),
            "header_html": render_header(request, board, column, permissions,
                                         sort_column_id=sort_column_id, direction=direction),
        }
        if with_cells and column.is_visible:
            items = BoardQueryService.with_cells(
                BoardItem.objects.filter(board=board, is_active=True, group__is_active=True)
            )
            items = BoardQueryService.attach_cells(list(items), {column.pk: column})
            payload["cells"] = {str(item.pk): render_cell(request, board, item, column, permissions) for item in items}
        return payload


class ColumnCreateView(ColumnFragmentMixin, BoardAPIView):
    def handle(self, request, data, pk):
        board = get_board(self.organization, pk)
        after = None
        after_id = _int_or_none(data.get("after_column_id"))
        if after_id:
            after = get_column(self.organization, after_id)
            if after.board_id != board.pk:
                raise Http404()
        column = ColumnService.create(
            user=request.user, board=board, column_type=str(data.get("type", "")), after_column=after
        )
        payload = self.column_payload(request, board, column)
        payload["after_column_id"] = after.pk if after else None
        return payload


class ColumnRenameView(ColumnFragmentMixin, BoardAPIView):
    def handle(self, request, data, pk):
        column = get_column(self.organization, pk)
        ColumnService.rename(user=request.user, column=column, name=data.get("name", ""))
        return self.column_payload(request, column.board, column, with_cells=False)


class ColumnResizeView(BoardAPIView):
    def handle(self, request, data, pk):
        column = get_column(self.organization, pk)
        ColumnService.resize(user=request.user, column=column, width=data.get("width"))
        return {"width": column.width}


class ColumnReorderView(BoardAPIView):
    def handle(self, request, data, pk):
        column = get_column(self.organization, pk)
        ColumnService.reorder(
            user=request.user, column=column,
            before_id=_int_or_none(data.get("before_id")), after_id=_int_or_none(data.get("after_id")),
        )
        return {"position": str(column.position)}


class ColumnSettingsView(ColumnFragmentMixin, BoardAPIView):
    """Descrição, obrigatoriedade e as configurações próprias do tipo, numa só gravação."""

    def handle(self, request, data, pk):
        column = get_column(self.organization, pk)
        self.require(catalog.QUADRO_GERIR_COLUNAS, column.board)
        if "description" in data or "is_required" in data:
            ColumnService.update_common(
                user=request.user, column=column,
                description=data.get("description") if "description" in data else None,
                is_required=data.get("is_required") if "is_required" in data else None,
            )
        if isinstance(data.get("settings"), dict):
            ColumnService.update_settings(user=request.user, column=column, settings=data["settings"])
        return self.column_payload(request, column.board, column)


class ColumnHideView(BoardAPIView):
    def handle(self, request, data, pk):
        column = get_column(self.organization, pk)
        ColumnService.set_visible(user=request.user, column=column, visible=bool(data.get("visible", False)))
        return {"visible": column.is_visible}


class ColumnDuplicateView(ColumnFragmentMixin, BoardAPIView):
    def handle(self, request, data, pk):
        column = get_column(self.organization, pk)
        copy = ColumnService.duplicate(user=request.user, column=column)
        payload = self.column_payload(request, column.board, copy)
        payload["after_column_id"] = column.pk
        return payload


class ColumnTypeView(ColumnFragmentMixin, BoardAPIView):
    def handle(self, request, data, pk):
        column = get_column(self.organization, pk)
        new_type = str(data.get("type", ""))
        if data.get("preview"):
            self.require(catalog.QUADRO_GERIR_COLUNAS, column.board)
            return {"plan": ColumnService.conversion_plan(column, new_type)}
        ColumnService.change_type(
            user=request.user, column=column, new_type=new_type, confirm=bool(data.get("confirm"))
        )
        return self.column_payload(request, column.board, column)


class ColumnDeleteView(BoardAPIView):
    def handle(self, request, data, pk):
        column = get_column(self.organization, pk)
        ColumnService.soft_delete(user=request.user, column=column)
        return {}


class ColumnFragmentView(ColumnFragmentMixin, BoardAPIView):
    """Redesenha cabeçalho e células de uma coluna (depois de editar etiquetas, por exemplo)."""

    def handle(self, request, data, pk):
        column = get_column(self.organization, pk)
        if not self.permissions(column.board)["view"]:
            raise BoardPermissionError("Você não possui acesso a este conteúdo.")
        return self.column_payload(
            request, column.board, column,
            sort_column_id=_int_or_none(data.get("sort")),
            direction="desc" if data.get("dir") == "desc" else "asc",
        )


# ---------------------------------------------------------------------------
# Etiquetas
# ---------------------------------------------------------------------------


def option_payload(option):
    return {"id": option.pk, "label": option.label, "color": option.color,
            "is_default": option.is_default, "is_done": option.is_done}


class OptionCreateView(BoardAPIView):
    def handle(self, request, data, pk):
        column = get_column(self.organization, pk)
        option = OptionService.create(user=request.user, column=column, label=data.get("label", ""),
                                      color=data.get("color"))
        return {"option": option_payload(option)}


class OptionUpdateView(BoardAPIView):
    def handle(self, request, data, pk):
        option = get_option(self.organization, pk)
        OptionService.update(
            user=request.user, option=option,
            label=data.get("label") if "label" in data else None,
            color=data.get("color") if "color" in data else None,
            is_default=data.get("is_default") if "is_default" in data else None,
            is_done=data.get("is_done") if "is_done" in data else None,
        )
        return {"option": option_payload(option)}


class OptionReorderView(BoardAPIView):
    def handle(self, request, data, pk):
        option = get_option(self.organization, pk)
        OptionService.reorder(
            user=request.user, option=option,
            before_id=_int_or_none(data.get("before_id")), after_id=_int_or_none(data.get("after_id")),
        )
        return {"position": str(option.position)}


class OptionDeleteView(BoardAPIView):
    def handle(self, request, data, pk):
        option = get_option(self.organization, pk)
        cleared = OptionService.soft_delete(user=request.user, option=option)
        return {"cleared_cells": cleared}


# ---------------------------------------------------------------------------
# Itens e células
# ---------------------------------------------------------------------------


class ItemCreateView(BoardAPIView):
    def handle(self, request, data, pk):
        board = get_board(self.organization, pk)
        group = get_group(self.organization, _int_or_none(data.get("group_id")) or 0)
        if group.board_id != board.pk:
            raise Http404()
        initial = data.get("initial")
        if initial is None:
            initials = []
        elif isinstance(initial, dict):
            initials = [initial]
        elif isinstance(initial, list) and len(initial) <= MAX_INITIAL_VALUES and all(isinstance(e, dict) for e in initial):
            initials = initial
        else:
            raise BoardError("Valor inicial inválido.")
        with transaction.atomic():
            item = ItemService.create(user=request.user, board=board, group=group, name=data.get("name", ""))
            # criar já preenchendo campos (o Kanban cria o cartão dentro de uma raia; o Calendário, no dia clicado): tudo ou nada
            for entry in initials:
                column = get_column(self.organization, _int_or_none(entry.get("column_id")) or 0)
                if column.board_id != board.pk:
                    raise Http404()
                CellService.set_value(user=request.user, item=item, column=column, raw_value=entry.get("value"))
        columns = self.columns_of(board)
        item = _item_for_render(board, item.pk, columns)
        return {
            "item": {"id": item.pk, "group_id": item.group_id, "name": getattr(item, "display_name", item.name)},
            "row_html": render_row(request, board, item, columns, self.permissions(board)),
        }


class ItemRenameView(BoardAPIView):
    def handle(self, request, data, pk):
        item = get_item(self.organization, pk)
        ItemService.rename(user=request.user, item=item, name=data.get("name", ""))
        item = _item_for_render(item.board, item.pk, self.columns_of(item.board))
        return {"name": item.display_name}


class ItemMoveView(BoardAPIView):
    def handle(self, request, data, pk):
        item = get_item(self.organization, pk)
        group = None
        group_id = _int_or_none(data.get("group_id"))
        if group_id:
            group = get_group(self.organization, group_id)
            if group.board_id != item.board_id:
                raise Http404()
        ItemService.move(
            user=request.user, item=item, group=group,
            before_id=_int_or_none(data.get("before_id")), after_id=_int_or_none(data.get("after_id")),
        )
        return {"group_id": item.group_id, "position": str(item.position)}


class ItemDeleteView(BoardAPIView):
    def handle(self, request, data, pk):
        item = get_item(self.organization, pk)
        ItemService.soft_delete(user=request.user, item=item)
        return {}


class ItemDetailView(BoardAPIView):
    """A gaveta de um item: todos os campos (editáveis no lugar, pelos mesmos editores da tabela) e as últimas mudanças.
    Só lê, então a permissão é conferida aqui: o serviço não roda."""

    def handle(self, request, data, pk):
        item = get_item(self.organization, pk)
        board = item.board
        permissions = self.permissions(board)
        if not permissions["view"]:
            raise BoardPermissionError("Você não possui acesso a este conteúdo.")
        columns = list(BoardQueryService.columns(board, visible=None))
        item = _item_for_render(board, item.pk, columns)
        return {
            "drawer_html": render_to_string(
                "boards/_item_drawer.html",
                {
                    "board": board, "item": item, "columns": columns, "permissions": permissions,
                    "history": list(BoardQueryService.item_history(item, DRAWER_HISTORY_LIMIT)),
                },
                request=request,
            ),
        }


class CellUpdateView(BoardAPIView):
    def handle(self, request, data, item_pk, column_pk):
        item = get_item(self.organization, item_pk)
        column = get_column(self.organization, column_pk)
        if column.board_id != item.board_id:
            raise Http404()
        CellService.set_value(user=request.user, item=item, column=column, raw_value=data.get("value"))
        item = _item_for_render(item.board, item.pk, [column])
        cell = item.cell_map.get(column.pk)
        return {
            "display": cell.display if cell else "",
            "cell_html": render_cell(request, item.board, item, column, self.permissions(item.board)),
        }
