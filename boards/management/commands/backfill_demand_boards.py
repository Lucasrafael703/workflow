"""Migra, de forma idempotente, o quadro de domínio de Tarefas para Boards.

O comando é deliberadamente separado das migrations de schema: ele pode ser
executado em pré-voo, repetido sem duplicar valores e interrompe antes de
escrever qualquer coisa quando encontra um tipo legado sem equivalente.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from activities.models import Activity, Task
from audit.models import AuditLog
from audit.services import AuditService
from boards.demand_services import BoardInstantiationService
from boards.models import (
    Board,
    BoardCell,
    BoardCellOption,
    BoardColumn,
    BoardColumnOption,
    DomainBoard,
    DomainBoardField,
    DomainCustomValue,
)


User = get_user_model()


TYPE_MAP = {
    DomainBoardField.Type.TEXT: BoardColumn.Type.TEXT,
    DomainBoardField.Type.NUMBER: BoardColumn.Type.NUMBER,
    DomainBoardField.Type.CURRENCY: BoardColumn.Type.CURRENCY,
    DomainBoardField.Type.DATETIME: BoardColumn.Type.DATE,
    DomainBoardField.Type.SELECT: BoardColumn.Type.DROPDOWN,
    DomainBoardField.Type.BOOLEAN: BoardColumn.Type.CHECKBOX,
}


class Command(BaseCommand):
    help = "Cria Boards de Demanda e transfere campos/valores do DomainBoard de Tarefas."

    def add_arguments(self, parser):
        parser.add_argument("--organization", type=int, help="ID da organização a migrar.")
        parser.add_argument("--actor-id", type=int, help="Usuário a registrar como executor quando necessário.")
        parser.add_argument("--dry-run", action="store_true", help="Só executa o pré-voo e mostra as contagens.")

    def handle(self, *args, **options):
        raise CommandError(
            "O backfill de tarefas operacionais foi desativado. "
            "Use a migration 0008 para centralizar os dados existentes em itens de quadro."
        )

        organization_id = options.get("organization")
        boards = DomainBoard.objects.filter(domain=DomainBoard.Domain.TASK)
        if organization_id:
            boards = boards.filter(organization_id=organization_id)
        boards = list(boards.select_related("organization"))
        if not boards:
            self.stdout.write(self.style.WARNING("Nenhum DomainBoard de Tarefas encontrado."))
            return

        actor = None
        if options.get("actor_id"):
            actor = User.objects.filter(pk=options["actor_id"], is_active=True).first()
            if actor is None:
                raise CommandError("--actor-id não corresponde a um usuário ativo.")

        fields_by_org = {}
        incompatible = []
        for legacy_board in boards:
            fields = list(
                legacy_board.fields.filter(is_active=True, is_system=False)
                .prefetch_related("choices")
                .order_by("position", "id")
            )
            fields_by_org[legacy_board.organization_id] = fields
            for field in fields:
                if field.type not in TYPE_MAP:
                    incompatible.append(
                        f"organização {legacy_board.organization_id}: campo '{field.label}' ({field.type})"
                    )
        if incompatible:
            report = "\n".join(f"- {line}" for line in incompatible)
            raise CommandError(
                "Pré-voo interrompido: há tipos de campo sem conversão segura.\n" + report
            )

        activities = Activity.objects.exclude(status=Activity.Status.RASCUNHO)
        if organization_id:
            activities = activities.filter(organization_id=organization_id)
        activities = list(activities.select_related("organization", "sector", "owner", "created_by"))
        task_count = Task.objects.filter(activity__in=activities).count()
        custom_count = DomainCustomValue.objects.filter(task__activity__in=activities, field__is_system=False).count()
        self.stdout.write(
            f"Pré-voo aprovado: {len(activities)} Demandas, {task_count} Tasks e {custom_count} valores customizados."
        )
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry-run concluído; nada foi alterado."))
            return

        result = {"boards": 0, "tasks": 0, "values": 0}
        # Cada Demanda é atômica: uma falha nunca deixa metade dos seus dados convertidos.
        for activity in activities:
            with transaction.atomic():
                executor = actor or activity.created_by or activity.owner
                if executor is None:
                    raise CommandError(f"Demanda {activity.pk} não possui criador nem dono para auditoria.")
                existing = Board.objects.filter(activity=activity, kind=Board.Kind.DEMAND).first()
                board = BoardInstantiationService.create_for_activity(user=executor, activity=activity)
                if existing is None:
                    result["boards"] += 1
                fields = fields_by_org.get(activity.organization_id, [])
                columns = self._ensure_columns(board, fields, executor)
                tasks = list(activity.tasks.select_related("created_by", "responsavel", "sector").order_by("pk"))
                for task in tasks:
                    item = BoardTaskLinkService.ensure_for_task(task=task, user=executor)
                    result["tasks"] += 1
                    values = DomainCustomValue.objects.filter(task=task, field__in=fields).select_related("field", "updated_by")
                    for legacy_value in values:
                        column = columns[legacy_value.field_id]
                        self._copy_value(item, column, legacy_value, executor)
                        result["values"] += 1
                AuditService.log(
                    user=executor,
                    action=AuditLog.Action.UPDATE,
                    activity=activity,
                    field_name="migration.demand_board_v1",
                    new_value=f"Board {board.pk}: {len(tasks)} tarefas",
                    reason="Backfill integral do Quadro de Demanda.",
                    metadata={"migration": "demand_boards_v1", "board_id": board.pk},
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Backfill concluído: {boards} novos Boards, {tasks} vínculos de Task verificados, "
                "{values} valores customizados transferidos.".format(**result)
            )
        )

    @staticmethod
    def _ensure_columns(board, fields, user):
        """Cria uma coluna por campo legado, marcada no settings para reexecução idempotente."""
        current = list(board.columns.filter(is_active=True).prefetch_related("options").order_by("position", "id"))
        by_legacy_id = {
            column.settings.get("legacy_domain_field_id"): column
            for column in current
            if column.settings.get("legacy_domain_field_id") is not None
        }
        last_position = current[-1].position if current else 0
        columns = {}
        for field in fields:
            column = by_legacy_id.get(field.pk)
            if column is None:
                last_position += 1000
                column = BoardColumn.objects.create(
                    board=board,
                    name=field.label,
                    type=TYPE_MAP[field.type],
                    position=last_position,
                    settings={
                        "legacy_domain_field_id": field.pk,
                        "show_time": field.type == DomainBoardField.Type.DATETIME,
                    },
                    created_by=user,
                )
                if field.type == DomainBoardField.Type.SELECT:
                    for choice in field.choices.filter(is_active=True).order_by("position", "id"):
                        BoardColumnOption.objects.create(
                            column=column,
                            label=choice.label,
                            color=choice.color,
                            position=choice.position,
                        )
            columns[field.pk] = column
        return columns

    @staticmethod
    def _copy_value(item, column, legacy_value, fallback_user):
        raw = (legacy_value.value or {}).get("value")
        cell, _ = BoardCell.objects.get_or_create(
            item=item,
            column=column,
            defaults={"updated_by": legacy_value.updated_by or fallback_user},
        )
        cell.value_text = ""
        cell.value_number = None
        cell.value_date = None
        cell.value_datetime = None
        cell.value_boolean = None
        cell.value_json = {}
        BoardCellOption.objects.filter(cell=cell).delete()

        if raw not in (None, ""):
            if column.type == BoardColumn.Type.TEXT:
                cell.value_text = str(raw)
            elif column.type in (BoardColumn.Type.NUMBER, BoardColumn.Type.CURRENCY):
                try:
                    cell.value_number = Decimal(str(raw).replace(",", "."))
                except (InvalidOperation, ValueError) as exc:
                    raise CommandError(f"Valor numérico incompatível na Task {item.task_id}: {raw!r}") from exc
            elif column.type == BoardColumn.Type.DATE:
                parsed_datetime = parse_datetime(str(raw)) if not isinstance(raw, datetime) else raw
                parsed_date = parse_date(str(raw)) if not isinstance(raw, date) else raw
                if parsed_datetime:
                    cell.value_datetime = parsed_datetime
                    cell.value_date = parsed_datetime.date()
                elif parsed_date:
                    cell.value_date = parsed_date
                else:
                    raise CommandError(f"Data incompatível na Task {item.task_id}: {raw!r}")
            elif column.type == BoardColumn.Type.CHECKBOX:
                cell.value_boolean = raw if isinstance(raw, bool) else str(raw).strip().lower() in {"1", "true", "sim", "yes"}
            elif column.type == BoardColumn.Type.DROPDOWN:
                label = str(raw)
                # Alguns bancos legados gravaram o id da escolha; outros, o
                # rótulo. Aceitamos ambos e ainda validamos contra as opções.
                try:
                    legacy_choice_id = int(raw)
                except (TypeError, ValueError):
                    legacy_choice_id = None
                legacy_choice = (
                    legacy_value.field.choices.filter(pk=legacy_choice_id, is_active=True).first()
                    if legacy_choice_id is not None else None
                )
                if legacy_choice is not None:
                    label = legacy_choice.label
                option = BoardColumnOption.objects.filter(column=column, label=label, is_active=True).first()
                if option is None:
                    raise CommandError(f"Opção incompatível na Task {item.task_id}: {raw!r}")
                BoardCellOption.objects.create(cell=cell, option=option, position=0)
        cell.updated_by = legacy_value.updated_by or fallback_user
        cell.save()
