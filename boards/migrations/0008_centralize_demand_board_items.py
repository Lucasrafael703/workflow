"""Centraliza as tarefas de Demanda como itens genéricos de Quadro.

A conversão é intencionalmente feita antes de remover os campos de ligação:
os registros operacionais continuam no histórico, mas não participam mais do
fluxo ativo.  Não usamos os serviços de domínio aqui para evitar notificações,
regras de fila ou efeitos colaterais durante a migração.
"""

from decimal import Decimal

from django.db import migrations
from django.utils import timezone


MIGRATION_REASON = "Tarefa operacional arquivada na centralização do quadro."


def _person_column(BoardColumn, board, actor_id):
    """Retorna a antiga coluna vinculada ou cria uma Pessoa genérica segura."""
    column = BoardColumn.objects.filter(
        board_id=board.pk,
        is_active=True,
        binding="TASK_RESPONSAVEL",
    ).first()
    if column is not None:
        return column

    column = BoardColumn.objects.filter(
        board_id=board.pk,
        is_active=True,
        type="PERSON",
        name__iexact="Responsável",
    ).first()
    if column is not None:
        return column

    last = BoardColumn.objects.filter(board_id=board.pk).order_by("-position", "-pk").first()
    return BoardColumn.objects.create(
        board_id=board.pk,
        name="Responsável",
        type="PERSON",
        binding="CUSTOM",
        position=(last.position if last else Decimal("0")) + Decimal("1000"),
        width=220,
        settings={},
        created_by_id=actor_id,
    )


def _cell(BoardCell, *, item_id, column_id, actor_id):
    cell, _ = BoardCell.objects.get_or_create(
        item_id=item_id,
        column_id=column_id,
        defaults={"updated_by_id": actor_id},
    )
    return cell


def centralize_demand_board_items(apps, schema_editor):
    Board = apps.get_model("boards", "Board")
    BoardColumn = apps.get_model("boards", "BoardColumn")
    BoardColumnOption = apps.get_model("boards", "BoardColumnOption")
    BoardItem = apps.get_model("boards", "BoardItem")
    BoardCell = apps.get_model("boards", "BoardCell")
    BoardCellUser = apps.get_model("boards", "BoardCellUser")
    BoardCellOption = apps.get_model("boards", "BoardCellOption")
    Task = apps.get_model("activities", "Task")
    WorkSession = apps.get_model("activities", "WorkSession")
    QueueEntry = apps.get_model("activities", "QueueEntry")
    AuditLog = apps.get_model("audit", "AuditLog")

    # Título e responsável deixam de ser projeções da Task.  Os valores de
    # célula existentes têm precedência; somente a etiqueta padrão ausente é
    # preenchida para que cada linha nova/conversão tenha o estado inicial.
    linked_items = (
        BoardItem.objects.filter(board__kind="DEMAND", task__isnull=False)
        .select_related("board", "task")
        .order_by("pk")
    )
    options_by_board = {}
    for item in linked_items.iterator():
        task = item.task
        actor_id = item.updated_by_id or item.created_by_id or task.created_by_id
        item.name = task.title or ""
        item.save(update_fields=["name"])

        person_column = _person_column(BoardColumn, item.board, actor_id)
        person_cell = _cell(
            BoardCell,
            item_id=item.pk,
            column_id=person_column.pk,
            actor_id=actor_id,
        )
        BoardCellUser.objects.filter(cell_id=person_cell.pk).delete()
        if task.responsavel_id:
            BoardCellUser.objects.create(cell_id=person_cell.pk, user_id=task.responsavel_id, position=0)

        board_options = options_by_board.get(item.board_id)
        if board_options is None:
            board_options = list(
                BoardColumnOption.objects.filter(
                    column__board_id=item.board_id,
                    column__is_active=True,
                    is_active=True,
                    is_default=True,
                ).order_by("column_id", "position", "pk")
            )
            options_by_board[item.board_id] = board_options
        for option in board_options:
            cell = _cell(
                BoardCell,
                item_id=item.pk,
                column_id=option.column_id,
                actor_id=actor_id,
            )
            if not BoardCellOption.objects.filter(cell_id=cell.pk).exists():
                BoardCellOption.objects.create(cell_id=cell.pk, option_id=option.pk, position=0)

    # Arquiva somente os fluxos ainda operacionais; os registros que já eram
    # concluídos/cancelados permanecem exatamente como estavam.
    now = timezone.now()
    active_tasks = list(
        Task.objects.exclude(status__in=("CONCLUIDA", "CANCELADA"))
        .only("pk", "activity_id", "sector_id", "status")
        .order_by("pk")
    )
    if not active_tasks:
        return

    active_task_ids = [task.pk for task in active_tasks]
    affected_sector_ids = list(
        QueueEntry.objects.filter(task_id__in=active_task_ids, left_at__isnull=True)
        .values_list("sector_id", flat=True)
        .distinct()
    )
    WorkSession.objects.filter(task_id__in=active_task_ids, ended_at__isnull=True).update(ended_at=now)
    QueueEntry.objects.filter(task_id__in=active_task_ids, left_at__isnull=True).update(left_at=now)

    AuditLog.objects.bulk_create(
        [
            AuditLog(
                user_id=None,
                activity_id=task.activity_id,
                task_id=task.pk,
                action="CANCEL",
                old_value=task.status,
                new_value="CANCELADA",
                reason=MIGRATION_REASON,
                metadata={"migration": "centralize_demand_board_items"},
            )
            for task in active_tasks
        ],
        batch_size=500,
    )
    Task.objects.filter(pk__in=active_task_ids).update(status="CANCELADA", cancelled_at=now)

    # Reordena as filas que perderam entradas, sem gerar novos eventos nem
    # notificações. `queue_size_at_entry` passa a refletir o total restante.
    for sector_id in affected_sector_ids:
        entries = list(
            QueueEntry.objects.filter(sector_id=sector_id, left_at__isnull=True).order_by("entered_at", "pk")
        )
        total = len(entries)
        for position, entry in enumerate(entries, start=1):
            entry.position = position
            entry.queue_size_at_entry = total
        if entries:
            QueueEntry.objects.bulk_update(entries, ["position", "queue_size_at_entry"])


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0011_visualizacoes_de_quadro"),
        ("activities", "0024_activity_board_setup"),
        ("boards", "0007_demand_boards"),
    ]

    operations = [
        migrations.RunPython(centralize_demand_board_items, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="boardcolumn",
            name="board_responsavel_binding_is_person",
        ),
        migrations.RemoveConstraint(
            model_name="boardcolumn",
            name="one_active_task_responsavel_binding",
        ),
        migrations.RemoveField(model_name="boardcolumn", name="binding"),
        migrations.RemoveField(model_name="boarditem", name="task"),
    ]
