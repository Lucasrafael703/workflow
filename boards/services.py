"""Regras do app `boards`. As views só resolvem o objeto e chamam estes serviços; aqui se autoriza, valida,
grava e audita, sempre dentro de `transaction.atomic`.

Convenções:
- `BoardPermissionError` é a recusa do motor de autorização (a view responde 403); `BoardError` é regra de
  negócio (400); `needs_confirmation` marca o que só vale com a confirmação explícita da pessoa (409).
- O cliente nunca manda uma posição numérica: manda os vizinhos (`before_id` à esquerda/acima, `after_id` à
  direita/abaixo) e o servidor calcula a posição entre eles.
- Todo registro de auditoria leva `metadata["board_id"]`, que é o que alimenta o histórico do quadro.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from acessos import catalog
from acessos.services import AuthorizationError, AuthorizationService, ResourceContext
from audit.models import AuditLog
from audit.services import AuditService

from .models import (
    MAX_COLUMN_WIDTH,
    MIN_COLUMN_WIDTH,
    Board,
    BoardCell,
    BoardCellOption,
    BoardCellUser,
    BoardColumn,
    BoardColumnOption,
    BoardGroup,
    BoardItem,
    BoardView,
)
from .calendar_view import clean_calendar_settings, complete_new_settings
from .kanban import clean_kanban_settings
from .validators import (
    CURRENCY_SYMBOLS,
    _as_decimal,
    _normalize_date,
    _parse_br_date,
    clean_color,
    clean_column_settings,
    default_settings_for,
    format_date,
    format_number,
    normalize_cell_value,
)

User = get_user_model()

POSITION_STEP = Decimal("1000")
MIN_POSITION_GAP = Decimal("0.001")
NAME_MAX = {"board": 160, "group": 120, "column": 120, "option": 120, "item": 255, "view": 80}
DEFAULT_GROUP_COLOR = "#579BFC"
DEFAULT_OPTION_COLOR = "#C4C4C4"
DEFAULT_STATUS_OPTIONS = (
    ("Não iniciado", "#C4C4C4", True, False),
    ("Em andamento", "#579BFC", False, False),
    ("Concluído", "#00C875", False, True),
)


class BoardError(Exception):
    def __init__(self, message, *, needs_confirmation=False):
        super().__init__(message)
        self.needs_confirmation = needs_confirmation


class BoardPermissionError(BoardError):
    pass


def _require(user, action, resource):
    # Quadros de Demanda possuem uma regra relacional adicional. O import é
    # local para não criar ciclo durante o carregamento de models/services.
    board = resource
    if getattr(resource, "_meta", None) and resource._meta.model_name != "board":
        board = getattr(resource, "board", None) or getattr(getattr(resource, "item", None), "board", None)
    if board is not None and getattr(board, "kind", None) == Board.Kind.DEMAND:
        from .demand_services import DemandBoardAccess

        if action == catalog.QUADRO_VISUALIZAR:
            DemandBoardAccess.require_view(user, board)
            return
        if action in {catalog.QUADRO_CRIAR_ITEM, catalog.QUADRO_EDITAR_ITEM}:
            DemandBoardAccess.require_collaborate(user, board)
            return
        if action in {catalog.QUADRO_EDITAR, catalog.QUADRO_GERIR_COLUNAS, catalog.QUADRO_EXCLUIR}:
            DemandBoardAccess.require_structure(user, board)
            return
    try:
        AuthorizationService.require(user, action, resource)
    except AuthorizationError as exc:
        raise BoardPermissionError(str(exc)) from exc


def _clean_name(value, kind, *, required=True, fallback=""):
    text = " ".join((value or "").split())
    if not text:
        if required:
            raise BoardError("Informe um nome.")
        return fallback
    return text[: NAME_MAX[kind]]


def _audit(user, action, board, target_type, target, *, field="", old="", new="", reason="", extra=None):
    return AuditService.log(
        user=user,
        action=action,
        field_name=field,
        old_value=old,
        new_value=new,
        reason=reason,
        target_type=target_type,
        target_id=getattr(target, "pk", None),
        metadata={"board_id": board.pk, **(extra or {})},
    )


# ---------------------------------------------------------------------------
# Posição
# ---------------------------------------------------------------------------


class PositionService:
    @staticmethod
    def between(previous, following):
        """Posição entre duas vizinhas; `None` quando não cabe mais (é hora de rebalancear)."""
        if previous is None and following is None:
            return POSITION_STEP
        if previous is None:
            return following - POSITION_STEP
        if following is None:
            return previous + POSITION_STEP
        gap = following - previous
        if gap <= MIN_POSITION_GAP:
            return None
        return previous + (gap / 2)

    @staticmethod
    def rebalance(queryset):
        objects = list(queryset.order_by("position", "id"))
        for index, obj in enumerate(objects, start=1):
            obj.position = POSITION_STEP * index
        queryset.model.objects.bulk_update(objects, ["position"])

    @classmethod
    def place(cls, siblings, *, before_id=None, after_id=None):
        """Nova posição para algo que fica entre `before_id` (esquerda/acima) e `after_id` (direita/abaixo).

        `siblings` é o conjunto das irmãs SEM o que está sendo movido, já travado (`select_for_update`).
        Só um vizinho informado: fica colado nele. Nenhum: vai para o fim. Vizinhas que já não estão
        adjacentes (tela desatualizada): vale a da esquerda.
        """

        def neighbours():
            before = siblings.filter(pk=before_id).first() if before_id else None
            after = siblings.filter(pk=after_id).first() if after_id else None
            if (before_id and before is None) or (after_id and after is None):
                raise BoardError("A posição escolhida não existe mais. Recarregue o quadro.")
            if before is not None:
                # vale a da esquerda: a vizinha da direita é sempre a que de fato vem depois dela hoje
                after = siblings.filter(position__gt=before.position).order_by("position", "id").first()
            elif after is not None:
                before = siblings.filter(position__lt=after.position).order_by("-position", "-id").first()
            elif before is None and after is None:
                before = siblings.order_by("-position", "-id").first()
            return before, after

        before, after = neighbours()
        position = cls.between(before.position if before else None, after.position if after else None)
        if position is None:
            cls.rebalance(siblings)
            before, after = neighbours()
            position = cls.between(before.position if before else None, after.position if after else None)
        return position


# ---------------------------------------------------------------------------
# Quadro e grupos
# ---------------------------------------------------------------------------


class BoardService:
    @staticmethod
    @transaction.atomic
    def create(*, user, organization, name, description="", sector=None):
        _require(user, catalog.QUADRO_CRIAR, ResourceContext.for_new(organization))
        if sector is not None and sector.organization_id != organization.id:
            raise BoardError("O setor informado pertence a outra organização.")
        board = Board.objects.create(
            organization=organization,
            name=_clean_name(name, "board", required=False, fallback="Novo quadro"),
            description=(description or "").strip(),
            item_label="Nome da Tarefa",
            kind=Board.Kind.TEMPLATE,
            sector=sector,
            created_by=user,
        )
        BoardGroup.objects.create(board=board, name="Grupo", position=POSITION_STEP)
        ViewService.create_default_kanban(user=user, board=board)
        _audit(user, AuditLog.Action.BOARD_CREATED, board, "board", board, new=board.name)
        return board

    @staticmethod
    @transaction.atomic
    def update(*, user, board, name=None, description=None):
        _require(user, catalog.QUADRO_EDITAR, board)
        if name is not None:
            old, board.name = board.name, _clean_name(name, "board")
            if old != board.name:
                _audit(user, AuditLog.Action.BOARD_UPDATED, board, "board", board, field="name", old=old, new=board.name)
        if description is not None:
            old, board.description = board.description, description.strip()
            if old != board.description:
                _audit(user, AuditLog.Action.BOARD_UPDATED, board, "board", board, field="description", old=old, new=board.description)
        board.save(update_fields=["name", "description", "updated_at"])
        return board

    @staticmethod
    @transaction.atomic
    def soft_delete(*, user, board):
        _require(user, catalog.QUADRO_EXCLUIR, board)
        board.is_active = False
        board.save(update_fields=["is_active", "updated_at"])
        _audit(user, AuditLog.Action.BOARD_DELETED, board, "board", board, old=board.name)


def clean_view_settings(view_type, columns, raw, current=None):
    """Configuração válida de uma visualização, pelas regras do tipo dela. `ValidationError` quando algo não serve."""
    if view_type == BoardView.Type.CALENDAR:
        return clean_calendar_settings(columns, raw, current=current)
    return clean_kanban_settings(columns, raw, current=current)


class ViewService:
    """Visualizações do quadro (Kanban e Calendário). São compartilhadas por todos que veem o quadro, então criar,
    renomear, configurar e excluir pedem `quadro.editar`; já usar a visualização (arrastar cartão, preencher campo) segue
    as permissões de item de sempre."""

    DEFAULT_NAMES = {BoardView.Type.KANBAN: "Kanban", BoardView.Type.CALENDAR: "Calendário"}

    @staticmethod
    def _unique_name(board, base):
        names = set(BoardView.objects.filter(board=board, is_active=True).values_list("name", flat=True))
        if base not in names:
            return base
        index = 2
        while f"{base} {index}" in names:
            index += 1
        return f"{base} {index}"

    @staticmethod
    def _make(user, board, name, settings, view_type=BoardView.Type.KANBAN):
        columns = list(BoardColumn.objects.filter(board=board, is_active=True))
        try:
            if view_type == BoardView.Type.CALENDAR:
                # o calendário nasce já apontando para a coluna de Data (e a de cor) que o servidor resolveria
                clean = complete_new_settings(columns, settings)
            else:
                clean = clean_kanban_settings(columns, settings)
        except ValidationError as exc:
            raise BoardError(exc.messages[0]) from exc
        siblings = BoardView.objects.select_for_update().filter(board=board, is_active=True)
        view = BoardView.objects.create(
            board=board,
            name=ViewService._unique_name(
                board, _clean_name(name, "view", required=False, fallback=ViewService.DEFAULT_NAMES[view_type])
            ),
            type=view_type,
            position=PositionService.place(siblings),
            settings=clean,
            created_by=user,
        )
        _audit(user, AuditLog.Action.BOARD_VIEW_CREATED, board, "board_view", view, new=view.name,
               extra={"type": view.type})
        return view

    @staticmethod
    @transaction.atomic
    def create_default_kanban(*, user, board, name="Kanban", settings=None):
        """O Kanban que todo quadro ganha ao nascer. Não pede `quadro.editar` porque quem cria o quadro (já autorizado
        por `quadro.criar`) está montando o quadro inteiro."""
        return ViewService._make(user, board, name, settings)

    @staticmethod
    @transaction.atomic
    def create(*, user, board, name="", view_type=BoardView.Type.KANBAN, settings=None):
        _require(user, catalog.QUADRO_EDITAR, board)
        if view_type not in (BoardView.Type.KANBAN, BoardView.Type.CALENDAR):
            raise BoardError("Tipo de visualização inválido.")
        return ViewService._make(user, board, name, settings, view_type)

    @staticmethod
    @transaction.atomic
    def update(*, user, view, name=None, settings=None):
        _require(user, catalog.QUADRO_EDITAR, view.board)
        if name is not None:
            old, view.name = view.name, _clean_name(name, "view")
            if old != view.name:
                _audit(user, AuditLog.Action.BOARD_VIEW_UPDATED, view.board, "board_view", view, field="name",
                       old=old, new=view.name)
        if settings:
            columns = list(BoardColumn.objects.filter(board=view.board, is_active=True))
            try:
                clean = clean_view_settings(view.type, columns, settings, current=view.settings)
            except ValidationError as exc:
                raise BoardError(exc.messages[0]) from exc
            old = view.settings or {}
            view.settings = clean
            for key in settings:
                if key in clean and old.get(key) != clean[key]:
                    _audit(user, AuditLog.Action.BOARD_VIEW_UPDATED, view.board, "board_view", view, field=key,
                           old=old.get(key), new=clean[key])
        view.save(update_fields=["name", "settings", "updated_at"])
        return view

    @staticmethod
    @transaction.atomic
    def soft_delete(*, user, view):
        _require(user, catalog.QUADRO_EDITAR, view.board)
        view.is_active = False
        view.save(update_fields=["is_active", "updated_at"])
        _audit(user, AuditLog.Action.BOARD_VIEW_DELETED, view.board, "board_view", view, old=view.name)


class GroupService:
    @staticmethod
    @transaction.atomic
    def create(*, user, board, name="Novo grupo", color=None):
        _require(user, catalog.QUADRO_EDITAR, board)
        siblings = BoardGroup.objects.select_for_update().filter(board=board, is_active=True)
        try:
            color = clean_color(color, DEFAULT_GROUP_COLOR)
        except ValidationError as exc:
            raise BoardError(exc.messages[0]) from exc
        group = BoardGroup.objects.create(
            board=board,
            name=_clean_name(name, "group", required=False, fallback="Novo grupo"),
            color=color,
            position=PositionService.place(siblings),
        )
        _audit(user, AuditLog.Action.BOARD_GROUP_CREATED, board, "board_group", group, new=group.name)
        return group

    @staticmethod
    @transaction.atomic
    def update(*, user, group, name=None, color=None):
        _require(user, catalog.QUADRO_EDITAR, group.board)
        if name is not None:
            old, group.name = group.name, _clean_name(name, "group")
            if old != group.name:
                _audit(user, AuditLog.Action.BOARD_GROUP_UPDATED, group.board, "board_group", group, field="name", old=old, new=group.name)
        if color is not None:
            try:
                new_color = clean_color(color, group.color)
            except ValidationError as exc:
                raise BoardError(exc.messages[0]) from exc
            old, group.color = group.color, new_color
            if old != new_color:
                _audit(user, AuditLog.Action.BOARD_GROUP_UPDATED, group.board, "board_group", group, field="color", old=old, new=new_color)
        group.save(update_fields=["name", "color"])
        return group

    @staticmethod
    @transaction.atomic
    def reorder(*, user, group, before_id=None, after_id=None):
        _require(user, catalog.QUADRO_EDITAR, group.board)
        siblings = BoardGroup.objects.select_for_update().filter(board=group.board, is_active=True).exclude(pk=group.pk)
        old = group.position
        group.position = PositionService.place(siblings, before_id=before_id, after_id=after_id)
        group.save(update_fields=["position"])
        _audit(user, AuditLog.Action.BOARD_GROUP_MOVED, group.board, "board_group", group, field="position", old=old, new=group.position)
        return group

    @staticmethod
    @transaction.atomic
    def soft_delete(*, user, group):
        _require(user, catalog.QUADRO_EDITAR, group.board)
        if group.items.filter(is_active=True).exists():
            raise BoardError("Mova ou exclua os itens do grupo antes de removê-lo.")
        group.is_active = False
        group.save(update_fields=["is_active"])
        _audit(user, AuditLog.Action.BOARD_GROUP_DELETED, group.board, "board_group", group, old=group.name)


# ---------------------------------------------------------------------------
# Colunas
# ---------------------------------------------------------------------------


class ColumnService:
    DEFAULT_NAMES = {
        BoardColumn.Type.TEXT: "Texto",
        BoardColumn.Type.NUMBER: "Números",
        BoardColumn.Type.CURRENCY: "Valor",
        BoardColumn.Type.DATE: "Data",
        BoardColumn.Type.PERSON: "Pessoa",
        BoardColumn.Type.STATUS: "Status",
        BoardColumn.Type.DROPDOWN: "Lista suspensa",
        BoardColumn.Type.CHECKBOX: "Confirmação",
    }

    @staticmethod
    def siblings(board, *, lock=True):
        queryset = BoardColumn.objects.filter(board=board, is_active=True)
        return queryset.select_for_update() if lock else queryset

    @staticmethod
    def _unique_name(board, base, *, exclude_pk=None):
        names = set(
            BoardColumn.objects.filter(board=board, is_active=True).exclude(pk=exclude_pk).values_list("name", flat=True)
        )
        if base not in names:
            return base
        index = 2
        while f"{base} {index}" in names:
            index += 1
        return f"{base} {index}"

    @staticmethod
    def _seed_options(column):
        if column.type == BoardColumn.Type.STATUS:
            for index, (label, color, is_default, is_done) in enumerate(DEFAULT_STATUS_OPTIONS, start=1):
                BoardColumnOption.objects.create(
                    column=column, label=label, color=color, is_default=is_default, is_done=is_done,
                    position=POSITION_STEP * index,
                )

    @staticmethod
    @transaction.atomic
    def create(*, user, board, column_type, after_column=None):
        _require(user, catalog.QUADRO_GERIR_COLUNAS, board)
        if column_type not in {str(t) for t in BoardColumn.ACTIVE_TYPES}:
            raise BoardError("Tipo de coluna inválido.")
        siblings = ColumnService.siblings(board)
        column = BoardColumn.objects.create(
            board=board,
            name=ColumnService._unique_name(board, ColumnService.DEFAULT_NAMES[column_type]),
            type=column_type,
            position=PositionService.place(siblings, before_id=after_column.pk if after_column else None),
            settings=default_settings_for(column_type),
            created_by=user,
        )
        ColumnService._seed_options(column)
        _audit(user, AuditLog.Action.BOARD_COLUMN_CREATED, board, "board_column", column, new=column.name,
               extra={"type": column.type})
        return column

    @staticmethod
    @transaction.atomic
    def rename(*, user, column, name):
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        old, column.name = column.name, _clean_name(name, "column")
        if old != column.name:
            column.save(update_fields=["name", "updated_at"])
            _audit(user, AuditLog.Action.BOARD_COLUMN_UPDATED, column.board, "board_column", column, field="name", old=old, new=column.name)
        return column

    @staticmethod
    @transaction.atomic
    def resize(*, user, column, width):
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        try:
            width = int(width)
        except (TypeError, ValueError):
            raise BoardError("Largura inválida.")
        width = max(MIN_COLUMN_WIDTH, min(MAX_COLUMN_WIDTH, width))
        old = column.width
        if old != width:
            column.width = width
            column.save(update_fields=["width", "updated_at"])
            _audit(user, AuditLog.Action.BOARD_COLUMN_RESIZED, column.board, "board_column", column, field="width", old=old, new=width)
        return column

    @staticmethod
    @transaction.atomic
    def reorder(*, user, column, before_id=None, after_id=None):
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        siblings = ColumnService.siblings(column.board).exclude(pk=column.pk)
        old = column.position
        column.position = PositionService.place(siblings, before_id=before_id, after_id=after_id)
        column.save(update_fields=["position", "updated_at"])
        _audit(user, AuditLog.Action.BOARD_COLUMN_MOVED, column.board, "board_column", column, field="position", old=old, new=column.position)
        return column

    @staticmethod
    @transaction.atomic
    def update_common(*, user, column, description=None, is_required=None):
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        if description is not None:
            old, column.description = column.description, description.strip()[:500]
            if old != column.description:
                _audit(user, AuditLog.Action.BOARD_COLUMN_UPDATED, column.board, "board_column", column, field="description", old=old, new=column.description)
        if is_required is not None:
            old, column.is_required = column.is_required, bool(is_required)
            if old != column.is_required:
                _audit(user, AuditLog.Action.BOARD_COLUMN_UPDATED, column.board, "board_column", column, field="is_required", old=old, new=column.is_required)
        column.save(update_fields=["description", "is_required", "updated_at"])
        return column

    @staticmethod
    @transaction.atomic
    def update_settings(*, user, column, settings):
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        try:
            clean = clean_column_settings(column.type, {**(column.settings or {}), **(settings or {})})
        except ValidationError as exc:
            raise BoardError(exc.messages[0]) from exc
        old = column.settings
        if old != clean:
            column.settings = clean
            column.save(update_fields=["settings", "updated_at"])
            _audit(user, AuditLog.Action.BOARD_COLUMN_UPDATED, column.board, "board_column", column, field="settings", old=old, new=clean)
        return column

    @staticmethod
    @transaction.atomic
    def set_visible(*, user, column, visible):
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        visible = bool(visible)
        if column.is_visible != visible:
            column.is_visible = visible
            column.save(update_fields=["is_visible", "updated_at"])
            _audit(user, AuditLog.Action.BOARD_COLUMN_UPDATED, column.board, "board_column", column,
                   field="is_visible", old=not visible, new=visible)
        return column

    @staticmethod
    @transaction.atomic
    def soft_delete(*, user, column):
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        column.is_active = False
        column.save(update_fields=["is_active", "updated_at"])
        _audit(user, AuditLog.Action.BOARD_COLUMN_DELETED, column.board, "board_column", column, old=column.name)

    @staticmethod
    @transaction.atomic
    def duplicate(*, user, column):
        """Cópia ao lado da original, com as mesmas etiquetas e os mesmos valores nas células."""
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        siblings = ColumnService.siblings(column.board)
        copy = BoardColumn.objects.create(
            board=column.board,
            name=ColumnService._unique_name(column.board, f"{column.name} (cópia)"[: NAME_MAX["column"]]),
            type=column.type,
            position=PositionService.place(siblings, before_id=column.pk),
            width=column.width,
            description=column.description,
            settings=dict(column.settings or {}),
            is_required=column.is_required,
            created_by=user,
        )
        option_map = {}
        for option in column.options.filter(is_active=True):
            option_map[option.pk] = BoardColumnOption.objects.create(
                column=copy, label=option.label, color=option.color, position=option.position,
                is_default=option.is_default, is_done=option.is_done,
            )
        cells = column.cells.filter(item__is_active=True).prefetch_related("user_values", "option_values")
        for cell in cells:
            new_cell = BoardCell.objects.create(
                item=cell.item, column=copy, value_text=cell.value_text, value_number=cell.value_number,
                value_date=cell.value_date, value_datetime=cell.value_datetime, value_boolean=cell.value_boolean,
                value_json=cell.value_json, updated_by=user,
            )
            for link in cell.user_values.all():
                BoardCellUser.objects.create(cell=new_cell, user=link.user, position=link.position)
            for link in cell.option_values.all():
                if link.option_id in option_map:
                    BoardCellOption.objects.create(cell=new_cell, option=option_map[link.option_id], position=link.position)
        _audit(user, AuditLog.Action.BOARD_COLUMN_CREATED, column.board, "board_column", copy, new=copy.name,
               extra={"type": copy.type, "duplicated_from": column.pk})
        return copy

    # -- conversão de tipo (R09) ----------------------------------------------

    SAFE_PAIRS = {
        (BoardColumn.Type.NUMBER, BoardColumn.Type.CURRENCY),
        (BoardColumn.Type.CURRENCY, BoardColumn.Type.NUMBER),
        (BoardColumn.Type.STATUS, BoardColumn.Type.DROPDOWN),
        (BoardColumn.Type.DROPDOWN, BoardColumn.Type.STATUS),
    }
    TO_TEXT_FROM = {
        BoardColumn.Type.DATE, BoardColumn.Type.NUMBER, BoardColumn.Type.CURRENCY, BoardColumn.Type.CHECKBOX,
        BoardColumn.Type.STATUS, BoardColumn.Type.DROPDOWN, BoardColumn.Type.PERSON,
    }
    PARSED_FROM_TEXT = {BoardColumn.Type.NUMBER, BoardColumn.Type.CURRENCY, BoardColumn.Type.DATE}

    @staticmethod
    def conversion_plan(column, new_type):
        """Como seria a conversão: `safe` (nada se perde), `parsed` (texto virando número/data: o que não
        converte é limpo) ou `destructive` (os valores da coluna são limpos)."""
        old = column.type
        if new_type not in {str(t) for t in BoardColumn.ACTIVE_TYPES}:
            raise BoardError("Tipo de coluna inválido.")
        if new_type == old:
            raise BoardError("A coluna já é deste tipo.")
        filled = column.cells.filter(item__is_active=True)
        total = filled.count()
        if (old, new_type) in ColumnService.SAFE_PAIRS:
            return {"mode": "safe", "filled": total, "lost": 0}
        if new_type == BoardColumn.Type.TEXT and old in ColumnService.TO_TEXT_FROM:
            return {"mode": "safe", "filled": total, "lost": 0}
        if old == BoardColumn.Type.TEXT and new_type in ColumnService.PARSED_FROM_TEXT:
            lost = 0
            for cell in filled.exclude(value_text=""):
                try:
                    ColumnService._parse_text_for(new_type, cell.value_text)
                except ValidationError:
                    lost += 1
            return {"mode": "parsed" if lost else "safe", "filled": total, "lost": lost}
        return {"mode": "destructive", "filled": total, "lost": total}

    @staticmethod
    def _parse_text_for(new_type, text):
        if new_type == BoardColumn.Type.DATE:
            parsed = _parse_br_date(text.strip())
            if parsed is None:
                return _normalize_date(text, {})[0]
            return parsed
        return _as_decimal(text)

    @staticmethod
    @transaction.atomic
    def change_type(*, user, column, new_type, confirm=False):
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        plan = ColumnService.conversion_plan(column, new_type)
        if plan["mode"] != "safe" and not confirm:
            noun = "valor" if plan["lost"] == 1 else "valores"
            raise BoardError(
                f"{plan['lost']} {noun} desta coluna não "
                f"{'pode' if plan['lost'] == 1 else 'podem'} ser convertido{'' if plan['lost'] == 1 else 's'} e "
                f"{'será' if plan['lost'] == 1 else 'serão'} apagado{'' if plan['lost'] == 1 else 's'}. Confirme para continuar.",
                needs_confirmation=True,
            )
        old_type = column.type
        cleared = 0
        cells = list(column.cells.filter(item__is_active=True).prefetch_related("user_values__user", "option_values__option"))

        if (old_type, new_type) in ColumnService.SAFE_PAIRS:
            pass  # os valores já servem ao tipo novo
        elif new_type == BoardColumn.Type.TEXT and old_type in ColumnService.TO_TEXT_FROM:
            for cell in cells:
                text = CellService.display_value(cell, column)
                CellService._clear(cell)
                cell.value_text = text
                cell.updated_by = user
                cell.save()
        elif old_type == BoardColumn.Type.TEXT and new_type in ColumnService.PARSED_FROM_TEXT:
            for cell in cells:
                text = cell.value_text
                CellService._clear(cell)
                if text:
                    try:
                        value = ColumnService._parse_text_for(new_type, text)
                    except ValidationError:
                        cleared += 1
                        cell.updated_by = user
                        cell.save()
                        continue
                    if new_type == BoardColumn.Type.DATE:
                        cell.value_date = value
                    else:
                        cell.value_number = value
                cell.updated_by = user
                cell.save()
        else:
            for cell in cells:
                CellService._clear(cell)
                cell.updated_by = user
                cell.save()
            cleared = len(cells)
            column.options.update(is_active=False)

        column.type = new_type
        column.settings = default_settings_for(new_type)
        column.save(update_fields=["type", "settings", "updated_at"])
        if new_type in BoardColumn.OPTION_TYPES and not column.options.filter(is_active=True).exists():
            ColumnService._seed_options(column)
        _audit(user, AuditLog.Action.BOARD_COLUMN_UPDATED, column.board, "board_column", column, field="type",
               old=old_type, new=new_type, extra={"cleared_values": cleared})
        return column


# ---------------------------------------------------------------------------
# Etiquetas de Status e Lista
# ---------------------------------------------------------------------------


class OptionService:
    @staticmethod
    def _check_column(column):
        if not column.uses_options:
            raise BoardError("Só colunas de Status e de Lista têm etiquetas.")

    @staticmethod
    @transaction.atomic
    def create(*, user, column, label, color=None):
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        OptionService._check_column(column)
        label = _clean_name(label, "option")
        if column.options.filter(is_active=True, label__iexact=label).exists():
            raise BoardError(f"Já existe a etiqueta “{label}” nesta coluna.")
        try:
            color = clean_color(color, DEFAULT_OPTION_COLOR)
        except ValidationError as exc:
            raise BoardError(exc.messages[0]) from exc
        siblings = BoardColumnOption.objects.select_for_update().filter(column=column, is_active=True)
        option = BoardColumnOption.objects.create(
            column=column, label=label, color=color, position=PositionService.place(siblings)
        )
        _audit(user, AuditLog.Action.BOARD_COLUMN_UPDATED, column.board, "board_column", column,
               field="etiqueta", new=label, extra={"option_id": option.pk, "change": "created"})
        return option

    @staticmethod
    @transaction.atomic
    def update(*, user, option, label=None, color=None, is_default=None, is_done=None):
        column = option.column
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        changes = []
        if label is not None:
            label = _clean_name(label, "option")
            if column.options.filter(is_active=True, label__iexact=label).exclude(pk=option.pk).exists():
                raise BoardError(f"Já existe a etiqueta “{label}” nesta coluna.")
            changes.append(("label", option.label, label))
            option.label = label
        if color is not None:
            try:
                new_color = clean_color(color, option.color)
            except ValidationError as exc:
                raise BoardError(exc.messages[0]) from exc
            changes.append(("color", option.color, new_color))
            option.color = new_color
        if is_default is not None:
            if is_default:
                column.options.filter(is_default=True).exclude(pk=option.pk).update(is_default=False)
            changes.append(("is_default", option.is_default, bool(is_default)))
            option.is_default = bool(is_default)
        if is_done is not None:
            changes.append(("is_done", option.is_done, bool(is_done)))
            option.is_done = bool(is_done)
        option.save()
        for field, old, new in changes:
            if old != new:
                _audit(user, AuditLog.Action.BOARD_COLUMN_UPDATED, column.board, "board_column", column,
                       field=f"etiqueta.{field}", old=old, new=new, extra={"option_id": option.pk})
        return option

    @staticmethod
    @transaction.atomic
    def reorder(*, user, option, before_id=None, after_id=None):
        column = option.column
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        siblings = BoardColumnOption.objects.select_for_update().filter(column=column, is_active=True).exclude(pk=option.pk)
        option.position = PositionService.place(siblings, before_id=before_id, after_id=after_id)
        option.save(update_fields=["position"])
        return option

    @staticmethod
    @transaction.atomic
    def soft_delete(*, user, option):
        """Remove a etiqueta: as células que a usavam ficam vazias (a tela já pede a confirmação)."""
        column = option.column
        _require(user, catalog.QUADRO_GERIR_COLUNAS, column.board)
        cleared = BoardCellOption.objects.filter(option=option).count()
        BoardCellOption.objects.filter(option=option).delete()
        option.is_active = False
        option.is_default = False
        option.save(update_fields=["is_active", "is_default"])
        _audit(user, AuditLog.Action.BOARD_COLUMN_UPDATED, column.board, "board_column", column,
               field="etiqueta", old=option.label, extra={"option_id": option.pk, "change": "deleted", "cleared_cells": cleared})
        return cleared


# ---------------------------------------------------------------------------
# Itens
# ---------------------------------------------------------------------------


class ItemService:
    @staticmethod
    @transaction.atomic
    def create(*, user, board, group, name=""):
        _require(user, catalog.QUADRO_CRIAR_ITEM, board)
        if group.board_id != board.id or not group.is_active:
            raise BoardError("Grupo inválido.")
        siblings = BoardItem.objects.select_for_update().filter(board=board, group=group, is_active=True)
        item = BoardItem.objects.create(
            board=board,
            group=group,
            name=_clean_name(name, "item", required=False),
            position=PositionService.place(siblings),
            created_by=user,
            updated_by=user,
        )
        # Colunas de Status/Lista com etiqueta padrão já nascem preenchidas ("Não iniciado").
        defaults = BoardColumnOption.objects.filter(
            column__board=board, column__is_active=True, is_active=True, is_default=True
        ).select_related("column")
        for option in defaults:
            cell = BoardCell.objects.create(item=item, column=option.column, updated_by=user)
            BoardCellOption.objects.create(cell=cell, option=option, position=0)
        _audit(user, AuditLog.Action.BOARD_ITEM_CREATED, board, "board_item", item, new=item.name)
        return item

    @staticmethod
    @transaction.atomic
    def rename(*, user, item, name):
        _require(user, catalog.QUADRO_EDITAR_ITEM, item.board)
        old, item.name = item.name, _clean_name(name, "item", required=False)
        if old != item.name:
            item.updated_by = user
            item.save(update_fields=["name", "updated_by", "updated_at"])
            _audit(user, AuditLog.Action.BOARD_ITEM_UPDATED, item.board, "board_item", item, field="name", old=old, new=item.name)
        return item

    @staticmethod
    @transaction.atomic
    def move(*, user, item, group=None, before_id=None, after_id=None):
        _require(user, catalog.QUADRO_EDITAR_ITEM, item.board)
        group = group or item.group
        if group.board_id != item.board_id or not group.is_active:
            raise BoardError("Grupo inválido.")
        siblings = (
            BoardItem.objects.select_for_update().filter(board=item.board, group=group, is_active=True).exclude(pk=item.pk)
        )
        old_group = item.group
        item.group = group
        item.position = PositionService.place(siblings, before_id=before_id, after_id=after_id)
        item.updated_by = user
        item.save(update_fields=["group", "position", "updated_by", "updated_at"])
        _audit(user, AuditLog.Action.BOARD_ITEM_MOVED, item.board, "board_item", item,
               field="group", old=old_group.name, new=group.name)
        return item

    @staticmethod
    @transaction.atomic
    def soft_delete(*, user, item):
        _require(user, catalog.QUADRO_EXCLUIR_ITEM, item.board)
        item.is_active = False
        item.updated_by = user
        item.save(update_fields=["is_active", "updated_by", "updated_at"])
        _audit(user, AuditLog.Action.BOARD_ITEM_DELETED, item.board, "board_item", item, old=item.name)


# ---------------------------------------------------------------------------
# Células
# ---------------------------------------------------------------------------


class CellService:
    @staticmethod
    def _clear(cell):
        cell.value_text = ""
        cell.value_number = None
        cell.value_date = None
        cell.value_datetime = None
        cell.value_boolean = None
        cell.value_json = {}
        if cell.pk:
            BoardCellUser.objects.filter(cell=cell).delete()
            BoardCellOption.objects.filter(cell=cell).delete()

    @staticmethod
    @transaction.atomic
    def set_value(*, user, item, column, raw_value):
        _require(user, catalog.QUADRO_EDITAR_ITEM, item.board)
        if item.board_id != column.board_id or not column.is_active:
            raise BoardError("A coluna não pertence ao quadro do item.")
        try:
            normalized = normalize_cell_value(column, raw_value)
        except ValidationError as exc:
            raise BoardError("; ".join(exc.messages)) from exc

        cell, _created = BoardCell.objects.select_for_update().get_or_create(
            item=item, column=column, defaults={"updated_by": user}
        )
        old_display = CellService.display_value(cell, column)

        kind, value = normalized["kind"], normalized["value"]
        # Valida o destino ANTES de limpar a célula, para uma recusa não apagar o valor antigo.
        person = option = None
        if kind == "person_id":
            person = User.objects.filter(
                pk=value, profile__organization=item.board.organization, is_active=True
            ).first()
            if person is None:
                raise BoardError("Pessoa inválida.")
        elif kind == "option_id":
            option = BoardColumnOption.objects.filter(pk=value, column=column, is_active=True).first()
            if option is None:
                raise BoardError("Opção inválida.")

        CellService._clear(cell)
        cell.updated_by = user
        if kind == "text":
            cell.value_text = value
        elif kind == "number":
            cell.value_number = value
        elif kind == "date":
            cell.value_date, cell.value_datetime = value
        elif kind == "boolean":
            cell.value_boolean = value
        cell.save()
        if person is not None:
            BoardCellUser.objects.create(cell=cell, user=person, position=0)
        if option is not None:
            BoardCellOption.objects.create(cell=cell, option=option, position=0)

        item.updated_by = user
        item.save(update_fields=["updated_by", "updated_at"])
        cell = BoardCell.objects.select_related("column").get(pk=cell.pk)
        new_display = CellService.display_value(cell, column)
        if old_display != new_display:
            _audit(user, AuditLog.Action.BOARD_CELL_UPDATED, item.board, "board_cell", cell, field=column.name,
                   old=old_display, new=new_display, extra={"item_id": item.pk, "column_id": column.pk})
        return cell

    @staticmethod
    def display_value(cell, column=None):
        """Texto da célula, o mesmo que a tela mostra (e que a auditoria grava)."""
        column = column or cell.column
        config = {**default_settings_for(column.type), **(column.settings or {})}
        column_type = column.type

        if column_type == BoardColumn.Type.TEXT:
            return cell.value_text
        if column_type in (BoardColumn.Type.NUMBER, BoardColumn.Type.CURRENCY):
            if cell.value_number is None:
                return ""
            text = format_number(cell.value_number, config.get("decimal_places"))
            if column_type == BoardColumn.Type.CURRENCY:
                return f"{CURRENCY_SYMBOLS.get(config.get('currency'), 'R$')} {text}"
            return f"{text} {config['unit']}".strip() if config.get("unit") else text
        if column_type == BoardColumn.Type.DATE:
            if cell.value_date is None:
                return ""
            text = format_date(cell.value_date, config.get("format", "DD/MM/YYYY"))
            if config.get("show_time") and cell.value_datetime:
                text += f" {timezone.localtime(cell.value_datetime):%H:%M}"
            return text
        if column_type == BoardColumn.Type.CHECKBOX:
            if cell.value_boolean is None:
                return ""
            return "Sim" if cell.value_boolean else "Não"
        if column_type == BoardColumn.Type.PERSON:
            link = sorted(cell.user_values.all(), key=lambda row: (row.position, row.pk))
            return (link[0].user.get_full_name() or link[0].user.get_username()) if link else ""
        if column_type in BoardColumn.OPTION_TYPES:
            link = sorted(cell.option_values.all(), key=lambda row: (row.position, row.pk))
            return link[0].option.label if link and link[0].option.is_active else ""
        return ""
