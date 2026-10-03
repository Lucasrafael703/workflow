"""Painel Tarefas (`/tarefas/`): o que está DENTRO dos Quadros de Demanda em que a pessoa é responsável.

Só leitura: nenhuma mutação, nenhuma auditoria, nenhum model novo. A "tarefa" de hoje é o `BoardItem` do Quadro da
Demanda (a `Task` antiga ficou só como histórico); o responsável é a célula Pessoa, o Status é a célula de etiqueta e o
prazo é a coluna de Data. Os valores são lidos com os mesmos resolvedores do calendário de quadros.

Estado derivado (Kanban e card "Em andamento"): etiqueta de conclusão -> `done`; etiqueta padrão (ex.: "Não iniciado")
ou sem Status -> `todo`; qualquer outra -> `doing`. "Atrasada" é um selo calculado (prazo anterior a hoje e não
concluída), não um estado.

Desempenho: os itens do escopo vêm em uma consulta (com Demanda, cliente e obra), as colunas de todos os quadros em
outra, e as células em mais quatro (`BoardQueryService.with_cells`): o total não cresce com o número de itens.
"""

import datetime
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Q
from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from acessos.services import AuthorizationService, ResourceContext
from notifications.models import Notification

from .calendar_view import WEEKDAY_LABELS, item_when, resolve_date_column, resolve_status_column
from .models import Board, BoardCellOption, BoardCellUser, BoardColumn, BoardGroup, BoardItem
from .queries import BoardQueryService

User = get_user_model()

TODO, DOING, DONE = "todo", "doing", "done"
STATE_LABELS = {TODO: "A fazer", DOING: "Em andamento", DONE: "Concluídas"}
STATE_ORDER = (TODO, DOING, DONE)
#: Demandas que não aparecem (rascunho nunca foi publicado; cancelada não tem mais trabalho a fazer).
EXCLUDED_ACTIVITY_STATUSES = ("RASCUNHO", "CANCELADA")
#: Demandas em que ainda faz sentido adicionar tarefa.
CLOSED_ACTIVITY_STATUSES = ("RASCUNHO", "CONCLUIDA", "CANCELADA")
ITEM_CAP = 2000  # teto de itens lidos de uma vez
KANBAN_CAP = 50  # cartões por coluna
PAGE_SIZE = 50
DEADLINE_FILTERS = ("overdue", "today", "week", "none")


@dataclass
class TaskRow:
    item: object
    board: object
    activity: object
    name: str
    person: object
    status_label: str
    status_color: str
    due: datetime.date | None
    state: str
    overdue: bool
    due_today: bool
    board_url: str

    @property
    def sort_key(self):
        # sem prazo por último; dentro do mesmo prazo, pelo nome
        return (self.due is None, self.due or datetime.date.max, (self.name or "").lower(), self.item.pk)


def parse_week(value, today=None):
    """`"2026-10-05"` -> a segunda-feira dessa semana. Ausente ou inválido: a semana de hoje."""
    try:
        day = datetime.date.fromisoformat(str(value or "").strip())
        if not 1900 <= day.year <= 2200:
            raise ValueError
    except ValueError:
        day = today or timezone.localdate()
    return day - datetime.timedelta(days=day.weekday())


def derive_state(status_option, status_column):
    if status_column is None or status_option is None:
        return TODO
    if status_option.is_done:
        return DONE
    if status_option.is_default:
        return TODO
    return DOING


class TaskCenterQuery:
    def __init__(self, user, organization, params=None, *, today=None):
        self.user = user
        self.organization = organization
        self.params = params if params is not None else {}
        self.today = today or timezone.localdate()
        self._rows = None

    # -- permissões e filtros ----------------------------------------------------------------------

    @property
    def can_filter_people(self):
        """Ver o trabalho de outras pessoas exige poder ver os quadros além dos próprios."""
        scope = ResourceContext.for_new(self.organization)
        return AuthorizationService.can(self.user, catalog.QUADRO_VISUALIZAR, scope) or AuthorizationService.can(
            self.user, catalog.ATIVIDADE_VISUALIZAR_TODAS, scope
        )

    def filters(self):
        get = self.params.get
        status = (get("status") or "").strip()
        deadline = (get("prazo") or "").strip()
        person = (get("pessoa") or "").strip()
        if not self.can_filter_people:
            person = ""  # sem autorização: sempre o próprio escopo, não importa o que venha na URL
        return {
            "q": (get("q") or "").strip(),
            "status": status if status in STATE_ORDER else "",
            "prazo": deadline if deadline in DEADLINE_FILTERS else "",
            "pessoa": person,
        }

    def _person_scope(self, filters):
        """`(None, usuário)` = um usuário; `("todas", None)` = todas as pessoas."""
        person = filters["pessoa"]
        if person == "todas":
            return "todas", None
        if person.isdigit() and int(person) != self.user.pk:
            other = User.objects.filter(
                pk=int(person), is_active=True, profile__organization=self.organization
            ).first()
            if other is not None:
                return None, other
        return None, self.user

    # -- leitura -----------------------------------------------------------------------------------

    def _base_items(self):
        return BoardItem.objects.filter(
            is_active=True,
            group__is_active=True,
            board__kind=Board.Kind.DEMAND,
            board__is_active=True,
            board__organization=self.organization,
        ).exclude(board__activity__status__in=EXCLUDED_ACTIVITY_STATUSES)

    @staticmethod
    def _assigned_to(user):
        return Exists(
            BoardCellUser.objects.filter(
                cell__item_id=OuterRef("pk"), user=user,
                cell__column__is_active=True, cell__column__type=BoardColumn.Type.PERSON,
            )
        )

    def _visible_boards(self, board_ids):
        """Dos quadros candidatos, os que a pessoa pode ver. Em lote: nunca uma consulta de acesso por quadro."""
        if self.user.pk is None:
            return set()
        scope = ResourceContext.for_new(self.organization)
        if AuthorizationService.can(self.user, catalog.QUADRO_VISUALIZAR, scope):
            return set(board_ids)
        boards = list(Board.objects.filter(pk__in=board_ids).select_related("activity"))
        mine = set(
            Board.objects.filter(pk__in=board_ids).filter(
                Q(activity__owner=self.user) | Q(activity__created_by=self.user)
                | Exists(
                    BoardCellUser.objects.filter(
                        user=self.user, cell__item__board_id=OuterRef("pk"), cell__item__is_active=True,
                        cell__column__is_active=True,
                    )
                )
            ).values_list("pk", flat=True)
        )
        rest = [board for board in boards if board.pk not in mine]
        allowed = AuthorizationService.can_many(
            self.user, [(catalog.ATIVIDADE_VISUALIZAR, board.activity) for board in rest]
        ) if rest else {}
        return mine | {board.pk for board in rest if allowed.get((catalog.ATIVIDADE_VISUALIZAR, board.activity.pk))}

    def rows(self):
        """Todas as linhas do escopo (antes de busca, status e prazo), já resolvidas. Uma vez por requisição."""
        if self._rows is not None:
            return self._rows
        filters = self.filters()
        everyone, person = self._person_scope(filters)
        queryset = self._base_items()
        if person is not None:
            queryset = queryset.filter(self._assigned_to(person))
        else:
            queryset = queryset.filter(
                Exists(BoardCellUser.objects.filter(
                    cell__item_id=OuterRef("pk"), cell__column__is_active=True, cell__column__type=BoardColumn.Type.PERSON
                ))
            )
        queryset = queryset.select_related(
            "board", "board__activity", "board__activity__client", "board__activity__site", "group"
        ).order_by("-id")[:ITEM_CAP]
        items = list(queryset)
        if person is None or person.pk != self.user.pk:
            visible = self._visible_boards({item.board_id for item in items})
            items = [item for item in items if item.board_id in visible]
        self._rows = self._build_rows(items)
        return self._rows

    def _build_rows(self, items):
        if not items:
            return []
        board_ids = {item.board_id for item in items}
        columns_by_board = {}
        columns_by_id = {}
        for column in BoardColumn.objects.filter(board_id__in=board_ids, is_active=True).prefetch_related(
            "options"
        ).order_by("position", "id"):
            columns_by_board.setdefault(column.board_id, []).append(column)
            columns_by_id[column.pk] = column
        # as células vêm numa leitura própria (4 consultas no total, qualquer que seja o número de itens)
        by_id = {item.pk: item for item in items}
        loaded = list(BoardQueryService.with_cells(BoardItem.objects.filter(pk__in=list(by_id))))
        BoardQueryService.attach_cells(loaded, columns_by_id)
        for fresh in loaded:
            by_id[fresh.pk].cell_map = fresh.cell_map
        urls = {board_id: reverse("board-detail", args=[board_id]) for board_id in board_ids}
        rows = []
        for item in items:
            columns = columns_by_board.get(item.board_id, [])
            status_column = resolve_status_column(columns)
            date_column = resolve_date_column({}, columns)
            person_column = next((column for column in columns if column.type == BoardColumn.Type.PERSON), None)
            status_cell = item.cell_map.get(status_column.pk) if status_column is not None else None
            option = getattr(status_cell, "option", None) if status_cell is not None else None
            person_cell = item.cell_map.get(person_column.pk) if person_column is not None else None
            due = item_when(item, date_column)[0] if date_column is not None else None
            state = derive_state(option, status_column)
            done = state == DONE
            rows.append(TaskRow(
                item=item, board=item.board, activity=item.board.activity,
                name=item.name or "Sem título",
                person=getattr(person_cell, "person", None) if person_cell is not None else None,
                status_label=option.label if option is not None else "Sem status",
                status_color=option.color if option is not None else "#94A3B8",
                due=due, state=DONE if done else state,
                overdue=bool(due and due < self.today and not done),
                due_today=bool(due and due == self.today and not done),
                board_url=urls[item.board_id],
            ))
        return rows

    # -- recortes ----------------------------------------------------------------------------------

    def apply_filters(self, rows, *, hide_done=False):
        filters = self.filters()
        needle = filters["q"].lower()
        out = []
        for row in rows:
            if needle:
                activity = row.activity
                haystack = " ".join(filter(None, (
                    row.name, activity.title, activity.code,
                    activity.client.name if activity.client_id else "", activity.site.name if activity.site_id else "",
                ))).lower()
                if needle not in haystack:
                    continue
            if filters["status"] and row.state != filters["status"]:
                continue
            if hide_done and not filters["status"] and row.state == DONE:
                continue
            deadline = filters["prazo"]
            if deadline == "overdue" and not row.overdue:
                continue
            if deadline == "today" and not row.due_today:
                continue
            if deadline == "week" and not (row.due and row.state != DONE and self.today <= row.due <= self.today + datetime.timedelta(days=7)):
                continue
            if deadline == "none" and row.due is not None:
                continue
            out.append(row)
        return sorted(out, key=lambda row: row.sort_key)

    def summary(self):
        rows = self.rows()
        return {
            "overdue": sum(1 for row in rows if row.overdue),
            "due_today": sum(1 for row in rows if row.due_today),
            "doing": sum(1 for row in rows if row.state == DOING),
            "mentions": Notification.objects.filter(
                recipient=self.user, event_type=Notification.EventType.MENTIONED, is_read=False
            ).count(),
            "total": sum(1 for row in rows if row.state != DONE),
        }

    def list_rows(self):
        return self.apply_filters(self.rows(), hide_done=True)

    def kanban_columns(self):
        rows = self.apply_filters(self.rows())
        columns = []
        for state in STATE_ORDER:
            chosen = [row for row in rows if row.state == state]
            columns.append({
                "key": state, "label": STATE_LABELS[state], "count": len(chosen), "items": chosen[:KANBAN_CAP],
                "hidden": max(0, len(chosen) - KANBAN_CAP),
            })
        return columns

    def week(self):
        start = parse_week(self.params.get("semana"), self.today)
        days = [start + datetime.timedelta(days=offset) for offset in range(7)]
        rows = self.apply_filters(self.rows())
        grid = [
            {
                "date": day, "label": WEEKDAY_LABELS[day.weekday()], "is_today": day == self.today,
                "is_weekend": day.weekday() >= 5, "items": [row for row in rows if row.due == day],
            }
            for day in days
        ]
        previous = start - datetime.timedelta(days=7)
        following = start + datetime.timedelta(days=7)
        return {
            "week_days": grid, "week_start": start, "week_end": days[-1],
            "week_previous": previous.isoformat(), "week_next": following.isoformat(),
            "week_today": parse_week(None, self.today).isoformat(),
            "week_undated": sum(1 for row in rows if row.due is None and row.state != DONE),
            "week_total": sum(len(day["items"]) for day in grid),
        }

    def people_options(self):
        if not self.can_filter_people:
            return []
        return list(
            User.objects.filter(is_active=True, profile__organization=self.organization)
            .order_by("first_name", "username")[:300]
        )

    # -- adicionar tarefa --------------------------------------------------------------------------

    def addable_boards(self):
        """Quadros de Demanda em que a pessoa pode criar item (a regra de verdade continua no `ItemService.create`):
        os que ela participa (responsável, criadora ou presente numa célula Pessoa) ou todos, com a ação de editar item."""
        queryset = Board.objects.filter(
            organization=self.organization, kind=Board.Kind.DEMAND, is_active=True,
        ).exclude(activity__status__in=CLOSED_ACTIVITY_STATUSES).select_related("activity")
        scope = ResourceContext.for_new(self.organization)
        if not AuthorizationService.can(self.user, catalog.QUADRO_EDITAR_ITEM, scope):
            queryset = queryset.filter(
                Q(activity__owner=self.user) | Q(activity__created_by=self.user)
                | Exists(BoardCellUser.objects.filter(
                    user=self.user, cell__item__board_id=OuterRef("pk"), cell__item__is_active=True,
                    cell__column__is_active=True,
                ))
            )
        boards = list(queryset.order_by("activity__title", "id")[:200])
        if not boards:
            return []
        columns = {}
        for column in BoardColumn.objects.filter(board__in=boards, is_active=True).prefetch_related("options").order_by(
            "position", "id"
        ):
            columns.setdefault(column.board_id, []).append(column)
        groups = {}
        for group in BoardGroup.objects.filter(board__in=boards, is_active=True).order_by("position", "id"):
            groups.setdefault(group.board_id, group)
        entries = []
        for board in boards:
            group = groups.get(board.pk)
            if group is None:
                continue
            cols = columns.get(board.pk, [])
            person_column = next((column for column in cols if column.type == BoardColumn.Type.PERSON), None)
            status_column = resolve_status_column(cols)
            options = {}
            if status_column is not None:
                active = [option for option in status_column.options.all() if option.is_active]
                options[DONE] = next((option.pk for option in active if option.is_done), None)
                options[TODO] = next((option.pk for option in active if option.is_default), None)
                options[DOING] = next((option.pk for option in active if not option.is_done and not option.is_default), None)
            entries.append({
                "board_id": board.pk,
                "label": f"{board.activity.code} · {board.activity.title}" if board.activity.code else board.activity.title,
                "group_id": group.pk,
                "person_column_id": person_column.pk if person_column is not None else None,
                "status_column_id": status_column.pk if status_column is not None else None,
                "status_options": options,
            })
        return entries

    def add_payload(self):
        return {
            "me": self.user.pk,
            "boards": self.addable_boards(),
            "url": reverse("board-item-create", args=[0]),
        }


def open_task_count(user):
    """Tarefas abertas em que a pessoa é responsável (selo do menu): uma contagem leve, sem montar linhas."""
    organization_id = getattr(getattr(user, "profile", None), "organization_id", None)
    if organization_id is None:
        return 0
    open_item = ~Exists(
        _done_options(OuterRef("pk"))
    )
    return (
        BoardItem.objects.filter(
            is_active=True, group__is_active=True, board__kind=Board.Kind.DEMAND, board__is_active=True,
            board__organization_id=organization_id,
        )
        .exclude(board__activity__status__in=EXCLUDED_ACTIVITY_STATUSES + ("CONCLUIDA",))
        .filter(TaskCenterQuery._assigned_to(user))
        .filter(open_item)
        .count()
    )


def _done_options(item_ref):
    return BoardCellOption.objects.filter(
        cell__item_id=item_ref, cell__column__type=BoardColumn.Type.STATUS, cell__column__is_active=True,
        option__is_done=True, option__is_active=True,
    )
