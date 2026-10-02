"""Serviços do quadro que acompanha uma Demanda.

O quadro é a única fonte de verdade para seus itens.  A Demanda só fornece o
escopo de acesso e o ciclo de vida do quadro; ela não cria tarefas operacionais.
"""

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.db import transaction

from acessos import catalog
from acessos.services import AuthorizationService
from audit.models import AuditLog
from activities.models import Activity, Task
from activities.services import ActivityError, TaskService

from .models import Board, BoardCell, BoardCellOption, BoardCellUser, BoardColumn, BoardColumnOption, BoardGroup, BoardItem, BoardView
from .services import (
    DEFAULT_GROUP_COLOR,
    DEFAULT_OPTION_COLOR,
    POSITION_STEP,
    BoardError,
    BoardPermissionError,
    CellService,
    PositionService,
    _audit,
)
from .validators import default_settings_for


User = get_user_model()


class DemandBoardAccess:
    """Regra relacional de acesso ao quadro de uma demanda.

    Permissões administrativas existentes continuam valendo; a relação com
    uma Task adiciona acesso colaborativo sem transformar o participante em
    administrador de colunas ou visualizações.
    """

    @staticmethod
    def _same_organization(user, activity):
        return bool(
            getattr(getattr(user, "profile", None), "organization_id", None)
            and getattr(user.profile, "organization_id", None) == activity.organization_id
        )

    @classmethod
    def participates(cls, user, activity):
        if not cls._same_organization(user, activity):
            return False
        if activity.owner_id == user.id or activity.created_by_id == user.id:
            return True
        return BoardCellUser.objects.filter(
            user=user,
            cell__item__board__activity=activity,
            cell__item__board__kind=Board.Kind.DEMAND,
            cell__item__is_active=True,
            cell__column__is_active=True,
        ).exists()

    @classmethod
    def can_view_activity(cls, user, activity):
        """Acesso relacional central para uma Demanda, inclusive sem Board carregado."""
        return cls.participates(user, activity) or AuthorizationService.can(
            user, catalog.ATIVIDADE_VISUALIZAR, activity
        )

    @classmethod
    def can_view(cls, user, board):
        if board.kind != Board.Kind.DEMAND:
            return AuthorizationService.can(user, catalog.QUADRO_VISUALIZAR, board)
        return cls.can_view_activity(user, board.activity) or AuthorizationService.can(
            user, catalog.QUADRO_VISUALIZAR, board
        )

    @classmethod
    def can_collaborate(cls, user, board):
        if board.kind != Board.Kind.DEMAND:
            return AuthorizationService.can(user, catalog.QUADRO_EDITAR_ITEM, board)
        return cls.participates(user, board.activity) or AuthorizationService.can(
            user, catalog.QUADRO_EDITAR_ITEM, board
        )

    @classmethod
    def can_manage_structure(cls, user, board):
        if board.kind != Board.Kind.DEMAND:
            return AuthorizationService.can(user, catalog.QUADRO_GERIR_COLUNAS, board)
        activity = board.activity
        return (
            activity.owner_id == user.id
            or activity.created_by_id == user.id
            or AuthorizationService.can(user, catalog.QUADRO_GERIR_COLUNAS, board)
        )

    @classmethod
    def require_view(cls, user, board):
        if not cls.can_view(user, board):
            raise BoardPermissionError("Você não possui acesso a este Quadro de Demanda.")

    @classmethod
    def require_collaborate(cls, user, board):
        if not cls.can_collaborate(user, board):
            raise BoardPermissionError("Você não pode editar tarefas neste Quadro de Demanda.")

    @classmethod
    def require_structure(cls, user, board):
        if not cls.can_manage_structure(user, board):
            raise BoardPermissionError("Você não pode configurar este Quadro de Demanda.")

    @classmethod
    def require_task(cls, user, board, task):
        cls.require_collaborate(user, board)
        if board.kind != Board.Kind.DEMAND or task.activity_id != board.activity_id:
            raise BoardError("A tarefa não pertence à Demanda deste quadro.")

    @classmethod
    def require_create_task(cls, user, board, activity, sector):
        cls.require_collaborate(user, board)
        if board.activity_id != activity.pk:
            raise BoardError("A tarefa deve pertencer à Demanda deste quadro.")
        # O contexto do Quadro é a autorização explícita para criar em outro
        # setor; os demais fluxos continuam sujeitos ao escopo setorial normal.
        return True


class BoardInstantiationService:
    """Cria a instância independente que acompanha uma Demanda publicada."""

    @staticmethod
    def _validate_template(activity, template):
        if template is None:
            return
        if (
            template.organization_id != activity.organization_id
            or template.kind != Board.Kind.TEMPLATE
            or not template.is_active
        ):
            raise BoardError("O modelo de quadro não está disponível nesta organização.")

    @staticmethod
    def _new_board(activity, user, template=None):
        return Board.objects.create(
            organization=activity.organization,
            name=activity.title,
            description=(template.description if template else ""),
            item_label="Nome da Tarefa",
            kind=Board.Kind.DEMAND,
            sector=activity.sector,
            activity=activity,
            source_template=template,
            created_by=user,
        )

    @staticmethod
    def _default_group(board):
        group = board.groups.filter(is_active=True).order_by("position", "id").first()
        if group is None:
            group = BoardGroup.objects.create(
                board=board, name="Tarefas", color=DEFAULT_GROUP_COLOR, position=POSITION_STEP
            )
        return group

    @staticmethod
    def _copy_column(board, source, user):
        return BoardColumn.objects.create(
            board=board,
            name=source.name,
            type=source.type,
            position=source.position,
            width=source.width,
            description=source.description,
            settings=deepcopy(source.settings or {}),
            is_required=source.is_required,
            is_visible=source.is_visible,
            is_active=source.is_active,
            created_by=user,
        )

    @staticmethod
    def _copy_options(columns, sources):
        options = {}
        for source in sources:
            target = columns[source.column_id]
            options[source.pk] = BoardColumnOption.objects.create(
                column=target,
                label=source.label,
                color=source.color,
                position=source.position,
                is_default=source.is_default,
                is_done=source.is_done,
                is_active=source.is_active,
            )
        return options

    @staticmethod
    def _remap_view_settings(settings, column_ids):
        value = deepcopy(settings or {})
        for key in ("group_by", "sum_column", "color_by", "date_column"):
            if value.get(key) in column_ids:
                value[key] = column_ids[value[key]].pk
        if isinstance(value.get("card_fields"), list):
            value["card_fields"] = [column_ids[item].pk for item in value["card_fields"] if item in column_ids]
        if isinstance(value.get("sort"), dict) and value["sort"].get("by") in column_ids:
            value["sort"] = {**value["sort"], "by": column_ids[value["sort"]["by"]].pk}
        return value

    @classmethod
    def _ensure_default_schema(cls, board, user):
        group = cls._default_group(board)
        responsible = board.columns.filter(type=BoardColumn.Type.PERSON, is_active=True).order_by("position", "id").first()
        if responsible is None:
            responsible = BoardColumn.objects.create(
                board=board,
                name="Responsável",
                type=BoardColumn.Type.PERSON,
                position=POSITION_STEP,
                width=180,
                created_by=user,
            )
        if not board.columns.filter(type=BoardColumn.Type.STATUS, is_active=True).exists():
            status = BoardColumn.objects.create(
                board=board, name="Status", type=BoardColumn.Type.STATUS,
                position=responsible.position + POSITION_STEP, width=160, created_by=user,
            )
            for index, (label, color, is_default, is_done) in enumerate(
                (("Não iniciado", "#C4C4C4", True, False), ("Em andamento", "#579BFC", False, False), ("Concluído", "#00C875", False, True)),
                start=1,
            ):
                BoardColumnOption.objects.create(
                    column=status, label=label, color=color, position=POSITION_STEP * index,
                    is_default=is_default, is_done=is_done,
                )
        if not board.columns.filter(type=BoardColumn.Type.DATE, is_active=True).exists():
            BoardColumn.objects.create(
                board=board, name="Data", type=BoardColumn.Type.DATE,
                position=board.columns.order_by("-position").first().position + POSITION_STEP,
                width=150, created_by=user,
            )
        return group

    @classmethod
    def _copy_structure(cls, board, template, user):
        groups = {}
        for source in template.groups.filter(is_active=True).order_by("position", "id"):
            groups[source.pk] = BoardGroup.objects.create(
                board=board, name=source.name, color=source.color, position=source.position, is_active=source.is_active
            )
        if not groups:
            cls._default_group(board)
        columns = {}
        for source in template.columns.filter(is_active=True).order_by("position", "id"):
            columns[source.pk] = cls._copy_column(board, source, user)
        cls._copy_options(
            columns,
            BoardColumnOption.objects.filter(column__board=template, column__is_active=True).order_by("position", "id"),
        )
        # Views carry column ids in their JSON settings.  Copy only after all
        # columns are known so Kanban and Calendar stay independent snapshots.
        for source in template.views.filter(is_active=True).order_by("position", "id"):
            BoardView.objects.create(
                board=board,
                name=source.name,
                type=source.type,
                position=source.position,
                settings=cls._remap_view_settings(source.settings, columns),
                is_active=source.is_active,
                created_by=user,
            )
        cls._ensure_default_schema(board, user)
        if not board.views.filter(type=BoardView.Type.KANBAN, is_active=True).exists():
            BoardView.objects.create(board=board, name="Kanban", type=BoardView.Type.KANBAN, position=POSITION_STEP, settings={}, created_by=user)
        if not board.views.filter(type=BoardView.Type.CALENDAR, is_active=True).exists():
            BoardView.objects.create(board=board, name="Calendário", type=BoardView.Type.CALENDAR, position=POSITION_STEP * 2, settings={}, created_by=user)
        return groups, columns

    @classmethod
    def _copy_template_items(cls, board, template, groups, columns, user, activity):
        source_items = template.items.filter(is_active=True).select_related("group").prefetch_related(
            "cells__user_values__user", "cells__option_values__option"
        ).order_by("group__position", "position", "id")
        for source in source_items:
            group = groups.get(source.group_id) or cls._default_group(board)
            target = BoardItem.objects.create(
                board=board,
                group=group,
                name=source.name,
                position=source.position,
                created_by=user,
                updated_by=user,
            )
            for cell in source.cells.all():
                target_column = columns.get(cell.column_id)
                if target_column is None:
                    continue
                copied = BoardCell.objects.create(
                    item=target,
                    column=target_column,
                    value_text=cell.value_text,
                    value_number=cell.value_number,
                    value_date=cell.value_date,
                    value_datetime=cell.value_datetime,
                    value_boolean=cell.value_boolean,
                    value_json=deepcopy(cell.value_json or {}),
                    updated_by=user,
                )
                for link in cell.user_values.all():
                    BoardCellUser.objects.create(cell=copied, user=link.user, position=link.position)
                for link in cell.option_values.all():
                    target_option = BoardColumnOption.objects.filter(
                        column=target_column, label=link.option.label, is_active=True
                    ).first()
                    if target_option:
                        BoardCellOption.objects.create(cell=copied, option=target_option, position=link.position)

    @classmethod
    @transaction.atomic
    def create_for_activity(cls, *, user, activity, template=None):
        activity = Activity.objects.select_for_update().select_related("sector", "owner", "created_by").get(pk=activity.pk)
        existing = Board.objects.filter(activity=activity).first()
        if existing is not None:
            if existing.kind != Board.Kind.DEMAND:
                raise BoardError("A Demanda já possui um quadro incompatível.")
            return existing
        cls._validate_template(activity, template)
        board = cls._new_board(activity, user, template)
        if template is None:
            cls._ensure_default_schema(board, user)
            BoardView.objects.create(board=board, name="Kanban", type=BoardView.Type.KANBAN, position=POSITION_STEP, settings={}, created_by=user)
            BoardView.objects.create(board=board, name="Calendário", type=BoardView.Type.CALENDAR, position=POSITION_STEP * 2, settings={}, created_by=user)
        else:
            groups, columns = cls._copy_structure(board, template, user)
            cls._copy_template_items(board, template, groups, columns, user, activity)
        _audit(user, AuditLog.Action.BOARD_CREATED, board, "board", board, new=board.name, extra={"activity_id": activity.pk})
        return board


class _RetiredDemandBoardTaskService:
    """Compatibilidade privada temporária para referências importadas antigas.

    Não há rota, view ou serviço ativo que a invoque.  Ela será removida junto
    com o código legado em uma limpeza posterior, depois que todas as
    instalações tiverem aplicado a migration que retira os campos antigos.
    """
    @classmethod
    @transaction.atomic
    def create_inline(cls, *, user, board, group, title, responsavel, sector=None, initial=None):
        DemandBoardAccess.require_create_task(user, board, board.activity, sector)
        if board.activity.status in (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA):
            raise BoardError("Não é possível criar tarefa em uma Demanda encerrada.")
        if group.board_id != board.pk or not group.is_active:
            raise BoardError("Grupo inválido.")
        if responsavel is None:
            raise BoardError("Informe o responsável pela tarefa.")
        sector = BoardInstantiationService._sector_for(board.activity, responsavel, sector)
        try:
            task = TaskService.create_task(
                board.activity, sector, (title or "").strip(), user, responsavel,
                board=board, board_group=group,
            )
        except ActivityError as exc:
            raise BoardError(str(exc)) from exc
        item = task.board_item
        for entry in initial or []:
            column = BoardColumn.objects.filter(pk=entry.get("column_id"), board=board, is_active=True).first()
            if column and column.binding == BoardColumn.Binding.CUSTOM:
                CellService.set_value(user=user, item=item, column=column, raw_value=entry.get("value"))
        return item

    @classmethod
    def rename(cls, *, user, item, title):
        DemandBoardAccess.require_task(user, item.board, item.task)
        try:
            return TaskService.update_task(item.task, user, board=item.board, title=(title or "").strip())
        except ActivityError as exc:
            raise BoardError(str(exc)) from exc

    @classmethod
    def change_responsavel(cls, *, user, item, responsavel):
        DemandBoardAccess.require_task(user, item.board, item.task)
        if responsavel is None:
            raise BoardError("Informe o responsável pela tarefa.")
        try:
            return TaskService.change_responsavel(item.task, responsavel, user, board=item.board)
        except ActivityError as exc:
            raise BoardError(str(exc)) from exc

    @classmethod
    def cancel(cls, *, user, item, reason):
        if item.task_id is None:
            raise BoardError("Este item não representa uma tarefa operacional.")
        try:
            # Cancelamento deliberadamente não recebe o contexto colaborativo:
            # permanece uma transição operacional com a autorização existente.
            return TaskService.cancel(item.task, user, reason)
        except ActivityError as exc:
            raise BoardError(str(exc)) from exc
