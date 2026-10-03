"""Prévia do Quadro da Demanda na ficha da Demanda (bloco "Tarefas"): só leitura, direto do Quadro real.

Não existe uma segunda fonte de tarefas: o resumo e as linhas vêm dos itens do Quadro (`BoardItem`), lidos com os mesmos
resolvedores do calendário de quadros (Status, Data, Pessoa). O Quadro pode ter 30 colunas; a prévia usa só três.
"""

import datetime

from django.db.models import Exists, OuterRef
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification

from .calendar_view import item_when, resolve_date_column, resolve_status_column
from .models import BoardCellOption, BoardColumn, BoardItem
from .queries import BoardQueryService
from .task_center import DONE, derive_state

PREVIEW_LIMIT = 5
PREVIEW_SCAN = 300  # teto de itens lidos para escolher as linhas da prévia


class DemandBoardPreviewQuery:
    @classmethod
    def build(cls, *, user, activity, limit=PREVIEW_LIMIT, today=None):
        """`None` quando a Demanda não tem Quadro ativo (demanda antiga); senão um dicionário simples para o template."""
        board = getattr(activity, "task_board", None)  # sem Quadro: RelatedObjectDoesNotExist (é um AttributeError)
        if board is None or not board.is_active:
            return None
        today = today or timezone.localdate()
        columns = list(BoardQueryService.columns(board, visible=None))
        status_column = resolve_status_column(columns)
        date_column = resolve_date_column({}, columns)
        person_column = next((column for column in columns if column.type == BoardColumn.Type.PERSON), None)

        items = BoardItem.objects.filter(board=board, is_active=True, group__is_active=True)
        total = items.count()
        done = items.filter(BoardQueryService._done(status_column)).count() if status_column is not None else 0
        doing = 0
        if status_column is not None:
            doing = items.filter(
                Exists(BoardCellOption.objects.filter(
                    cell__item_id=OuterRef("pk"), cell__column=status_column, option__is_active=True,
                    option__is_done=False, option__is_default=False,
                ))
            ).count()

        loaded = BoardQueryService.attach_cells(
            list(BoardQueryService.with_cells(items.order_by("group__position", "position", "id")[:PREVIEW_SCAN])),
            {column.pk: column for column in columns},
        )
        rows = []
        for item in loaded:
            cell = item.cell_map.get(status_column.pk) if status_column is not None else None
            option = getattr(cell, "option", None) if cell is not None else None
            state = derive_state(option, status_column)
            person_cell = item.cell_map.get(person_column.pk) if person_column is not None else None
            due = item_when(item, date_column)[0] if date_column is not None else None
            rows.append({
                "name": item.name or "Sem título",
                "person": getattr(person_cell, "person", None) if person_cell is not None else None,
                "status_label": option.label if option is not None else "Sem status",
                "status_color": option.color if option is not None else "#94A3B8",
                "due": due,
                "done": state == DONE,
                "overdue": bool(due and due < today and state != DONE),
                "state": state,
                "_order": (state == DONE, due is None, due or datetime.date.max, item.pk),
            })
        rows.sort(key=lambda row: row["_order"])
        mentions = Notification.objects.filter(
            recipient=user, activity=activity, event_type=Notification.EventType.MENTIONED, is_read=False
        ).count()
        return {
            "board": board,
            "board_url": reverse("board-detail", args=[board.pk]),
            "total": total,
            "done": done,
            "in_progress": doing,
            "todo": max(0, total - done - doing),
            "unread_mentions": mentions,
            "rows": rows[:limit],
            "more": max(0, total - limit),
        }
