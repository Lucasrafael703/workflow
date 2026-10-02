"""Quadros dinâmicos: Board -> BoardGroup / BoardColumn -> BoardItem -> BoardCell.

O usuário configura o quadro (colunas, grupos, etiquetas) e a LPS entende o que ele montou. Nada aqui
substitui `Activity`/`Task`: o quadro é a camada flexível; o motor operacional (fila, tempo, prazo,
bloqueio) continua nas demandas e tarefas.

Todo modelo expõe `organization_id` por um caminho curto, porque a autorização e o isolamento entre
organizações dependem dele (doc 05). Posições são decimais (passo 1000): mover algo é gravar UMA posição
entre as vizinhas, nunca regravar a lista inteira.
"""

from decimal import Decimal

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

POSITION_DEFAULT = Decimal("1000")
MIN_COLUMN_WIDTH = 96
DEFAULT_COLUMN_WIDTH = 160
MAX_COLUMN_WIDTH = 640


def _position_field(verbose_name="posição"):
    return models.DecimalField(verbose_name, max_digits=20, decimal_places=6, default=POSITION_DEFAULT)


class Board(models.Model):
    class Kind(models.TextChoices):
        TEMPLATE = "TEMPLATE", "Modelo"
        DEMAND = "DEMAND", "Demanda"

    organization = models.ForeignKey(
        "core.Organization", verbose_name="organização", on_delete=models.CASCADE, related_name="boards"
    )
    name = models.CharField("nome", max_length=160)
    description = models.TextField("descrição", blank=True)
    item_label = models.CharField(
        "título da coluna principal",
        max_length=60,
        default="Nome da Tarefa",
        help_text="Como a primeira coluna (o nome de cada tarefa) se chama neste quadro.",
    )
    kind = models.CharField("tipo", max_length=16, choices=Kind.choices, default=Kind.TEMPLATE)
    sector = models.ForeignKey(
        "core.Sector",
        verbose_name="setor do modelo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="boards",
        help_text="Obrigatório para novos modelos; quadros legados podem não ter setor.",
    )
    activity = models.OneToOneField(
        "activities.Activity",
        verbose_name="demanda",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="task_board",
    )
    source_template = models.ForeignKey(
        "self",
        verbose_name="modelo de origem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="instances",
    )
    is_active = models.BooleanField("ativo", default=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, verbose_name="criado por", on_delete=models.PROTECT, related_name="boards_created"
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("alterado em", auto_now=True)

    class Meta:
        verbose_name = "quadro"
        verbose_name_plural = "quadros"
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "kind", "is_active"], name="boards_boar_organiz_99861b_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(kind="TEMPLATE", activity__isnull=True)
                    | models.Q(kind="DEMAND", activity__isnull=False)
                ),
                name="board_kind_matches_activity",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.kind == self.Kind.DEMAND and self.activity_id:
            if self.sector_id != self.activity.sector_id:
                raise ValidationError({"sector": "O setor do Quadro deve ser o setor da Demanda."})


class BoardView(models.Model):
    """Uma forma de enxergar os MESMOS itens do quadro (Kanban e Calendário). Não guarda dado de negócio, só a
    configuração da lente: por qual coluna agrupar (Kanban) ou qual coluna de Data usar (Calendário), quais campos
    aparecem no cartão, ordenação. A tabela do quadro ("Quadro principal") é implícita: existe em todo quadro e não
    tem registro aqui."""

    class Type(models.TextChoices):
        KANBAN = "KANBAN", "Kanban"
        CALENDAR = "CALENDAR", "Calendário"

    board = models.ForeignKey(Board, verbose_name="quadro", on_delete=models.CASCADE, related_name="views")
    name = models.CharField("nome", max_length=80)
    type = models.CharField("tipo", max_length=16, choices=Type.choices, default=Type.KANBAN)
    position = _position_field()
    settings = models.JSONField("configuração", default=dict, blank=True)
    is_active = models.BooleanField("ativa", default=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, verbose_name="criada por", on_delete=models.PROTECT, related_name="board_views_created"
    )
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("alterada em", auto_now=True)

    class Meta:
        verbose_name = "visualização do quadro"
        verbose_name_plural = "visualizações do quadro"
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["board", "is_active", "position"])]

    def __str__(self):
        return self.name

    @property
    def organization_id(self):
        return self.board.organization_id


class BoardGroup(models.Model):
    """Organização visual do quadro (ex.: "Em andamento"). Não é um status: mover um item de grupo não muda dado."""

    board = models.ForeignKey(Board, verbose_name="quadro", on_delete=models.CASCADE, related_name="groups")
    name = models.CharField("nome", max_length=120)
    color = models.CharField("cor", max_length=7, default="#579BFC")
    position = _position_field()
    is_active = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "grupo do quadro"
        verbose_name_plural = "grupos do quadro"
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["board", "is_active", "position"])]

    def __str__(self):
        return self.name

    @property
    def organization_id(self):
        return self.board.organization_id


class BoardColumn(models.Model):
    class Type(models.TextChoices):
        TEXT = "TEXT", "Texto"
        NUMBER = "NUMBER", "Número"
        CURRENCY = "CURRENCY", "Moeda"
        DATE = "DATE", "Data"
        PERSON = "PERSON", "Pessoa"
        STATUS = "STATUS", "Status"
        DROPDOWN = "DROPDOWN", "Lista suspensa"
        CHECKBOX = "CHECKBOX", "Sinal de confirmação"

        # Reservados para fases futuras: existem no catálogo mas ainda não se criam nem se editam.
        FILE = "FILE", "Arquivo"
        TIMELINE = "TIMELINE", "Cronograma"
        PRIORITY = "PRIORITY", "Prioridade"
        CONFIRMATION = "CONFIRMATION", "Confirmação"
        RELATION = "RELATION", "Conectar quadros"
        FORMULA = "FORMULA", "Fórmula"
        AI_EXTRACT = "AI_EXTRACT", "Extração por IA"

    #: Tipos que o D0 cria e edita, na ordem em que o seletor os oferece.
    ACTIVE_TYPES = (
        Type.STATUS, Type.DROPDOWN, Type.TEXT, Type.DATE, Type.PERSON, Type.NUMBER, Type.CURRENCY, Type.CHECKBOX,
    )
    #: Tipos cujas células escolhem entre etiquetas cadastradas na coluna.
    OPTION_TYPES = (Type.STATUS, Type.DROPDOWN)

    board = models.ForeignKey(Board, verbose_name="quadro", on_delete=models.CASCADE, related_name="columns")
    name = models.CharField("nome", max_length=120)
    type = models.CharField("tipo", max_length=32, choices=Type.choices)
    position = _position_field()
    width = models.PositiveIntegerField(
        "largura",
        default=DEFAULT_COLUMN_WIDTH,
        validators=[MinValueValidator(MIN_COLUMN_WIDTH), MaxValueValidator(MAX_COLUMN_WIDTH)],
    )
    description = models.TextField("descrição", blank=True)
    settings = models.JSONField("configuração do tipo", default=dict, blank=True)
    is_required = models.BooleanField("obrigatória", default=False)
    is_visible = models.BooleanField("visível", default=True)
    is_active = models.BooleanField("ativa", default=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        verbose_name="criada por",
        on_delete=models.PROTECT,
        related_name="board_columns_created",
    )
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("alterada em", auto_now=True)

    class Meta:
        verbose_name = "coluna do quadro"
        verbose_name_plural = "colunas do quadro"
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["board", "is_active", "position"])]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    @property
    def organization_id(self):
        return self.board.organization_id

    @property
    def uses_options(self):
        return self.type in self.OPTION_TYPES


class BoardColumnOption(models.Model):
    """Etiqueta de uma coluna de Status ou Lista. Fica em tabela própria (e não no JSON da coluna) para poder
    ordenar, referenciar, filtrar e trocar a cor sem regravar as células."""

    column = models.ForeignKey(BoardColumn, verbose_name="coluna", on_delete=models.CASCADE, related_name="options")
    label = models.CharField("rótulo", max_length=120)
    color = models.CharField("cor", max_length=7, default="#C4C4C4")
    position = _position_field()
    is_default = models.BooleanField("etiqueta padrão", default=False)
    is_done = models.BooleanField("representa conclusão", default=False)
    is_active = models.BooleanField("ativa", default=True)

    class Meta:
        verbose_name = "etiqueta da coluna"
        verbose_name_plural = "etiquetas da coluna"
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["column", "is_active", "position"])]

    def __str__(self):
        return self.label

    @property
    def organization_id(self):
        return self.column.board.organization_id


class BoardItem(models.Model):
    board = models.ForeignKey(Board, verbose_name="quadro", on_delete=models.CASCADE, related_name="items")
    group = models.ForeignKey(BoardGroup, verbose_name="grupo", on_delete=models.PROTECT, related_name="items")
    name = models.CharField("nome", max_length=255, blank=True)
    position = _position_field()
    is_active = models.BooleanField("ativo", default=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        verbose_name="criado por",
        on_delete=models.PROTECT,
        related_name="board_items_created",
    )
    updated_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        verbose_name="alterado por",
        on_delete=models.PROTECT,
        related_name="board_items_updated",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("alterado em", auto_now=True)

    class Meta:
        verbose_name = "item do quadro"
        verbose_name_plural = "itens do quadro"
        ordering = ["group__position", "position", "id"]
        indexes = [models.Index(fields=["board", "group", "is_active", "position"])]

    def __str__(self):
        return self.name or "Sem título"

    @property
    def organization_id(self):
        return self.board.organization_id


class BoardCell(models.Model):
    """Valor de um item numa coluna. Colunas tipadas (e não um JSON só) porque número precisa ordenar como
    número, data como data, e filtros e relatórios futuros precisam do banco."""

    item = models.ForeignKey(BoardItem, verbose_name="item", on_delete=models.CASCADE, related_name="cells")
    column = models.ForeignKey(BoardColumn, verbose_name="coluna", on_delete=models.PROTECT, related_name="cells")
    value_text = models.TextField("texto", blank=True)
    value_number = models.DecimalField("número", max_digits=24, decimal_places=6, null=True, blank=True)
    value_date = models.DateField("data", null=True, blank=True)
    value_datetime = models.DateTimeField("data e hora", null=True, blank=True)
    value_boolean = models.BooleanField("sim/não", null=True, blank=True)
    value_json = models.JSONField("dados extras", default=dict, blank=True)
    updated_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        verbose_name="alterada por",
        on_delete=models.PROTECT,
        related_name="board_cells_updated",
    )
    updated_at = models.DateTimeField("alterada em", auto_now=True)

    class Meta:
        verbose_name = "célula do quadro"
        verbose_name_plural = "células do quadro"
        constraints = [models.UniqueConstraint(fields=["item", "column"], name="uniq_board_cell_item_column")]
        indexes = [
            models.Index(fields=["column", "value_number"]),
            models.Index(fields=["column", "value_date"]),
            models.Index(fields=["column", "value_boolean"]),
        ]

    @property
    def organization_id(self):
        return self.item.board.organization_id


class BoardCellUser(models.Model):
    cell = models.ForeignKey(BoardCell, verbose_name="célula", on_delete=models.CASCADE, related_name="user_values")
    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, verbose_name="pessoa", on_delete=models.PROTECT, related_name="board_cell_values"
    )
    position = models.PositiveIntegerField("posição", default=0)

    class Meta:
        verbose_name = "pessoa da célula"
        verbose_name_plural = "pessoas da célula"
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=["cell", "user"], name="uniq_board_cell_user")]


class BoardCellOption(models.Model):
    cell = models.ForeignKey(BoardCell, verbose_name="célula", on_delete=models.CASCADE, related_name="option_values")
    option = models.ForeignKey(
        BoardColumnOption, verbose_name="etiqueta", on_delete=models.PROTECT, related_name="cell_values"
    )
    position = models.PositiveIntegerField("posição", default=0)

    class Meta:
        verbose_name = "etiqueta da célula"
        verbose_name_plural = "etiquetas da célula"
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=["cell", "option"], name="uniq_board_cell_option")]


# Quadros de domínio guardam apenas a configuração das lentes de Demandas e
# Tarefas. Os registros continuam sendo Activity e Task; não há cópia de dado
# operacional nesta camada.
class DomainBoard(models.Model):
    class Domain(models.TextChoices):
        DEMAND = "DEMAND", "Demandas"
        TASK = "TASK", "Tarefas"

    organization = models.ForeignKey(
        "core.Organization", verbose_name="organização", on_delete=models.CASCADE, related_name="domain_boards"
    )
    domain = models.CharField("domínio", max_length=12, choices=Domain.choices)
    name = models.CharField("nome", max_length=120)
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("alterado em", auto_now=True)

    class Meta:
        verbose_name = "quadro de domínio"
        verbose_name_plural = "quadros de domínio"
        constraints = [models.UniqueConstraint(fields=["organization", "domain"], name="uniq_domain_board_org_domain")]

    def __str__(self):
        return f"{self.organization} · {self.get_domain_display()}"


class DomainBoardField(models.Model):
    class Type(models.TextChoices):
        TEXT = "TEXT", "Texto"
        NUMBER = "NUMBER", "Número"
        CURRENCY = "CURRENCY", "Moeda"
        DATETIME = "DATETIME", "Data e hora"
        PERSON = "PERSON", "Pessoa"
        STAGE = "STAGE", "Etapa"
        SECTOR = "SECTOR", "Setor"
        PRIORITY = "PRIORITY", "Prioridade"
        SELECT = "SELECT", "Lista"
        BOOLEAN = "BOOLEAN", "Confirmação"
        CHECKLIST = "CHECKLIST", "Checklist"
        RELATION = "RELATION", "Relação"

    board = models.ForeignKey(DomainBoard, verbose_name="quadro", on_delete=models.CASCADE, related_name="fields")
    key = models.SlugField("chave", max_length=64)
    label = models.CharField("rótulo", max_length=120)
    type = models.CharField("tipo", max_length=16, choices=Type.choices)
    position = _position_field()
    settings = models.JSONField("configuração", default=dict, blank=True)
    is_system = models.BooleanField("campo do sistema", default=False)
    is_active = models.BooleanField("ativo", default=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("alterado em", auto_now=True)

    class Meta:
        verbose_name = "campo do quadro de domínio"
        verbose_name_plural = "campos do quadro de domínio"
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=["board", "key"], name="uniq_domain_board_field_key")]

    def __str__(self):
        return f"{self.board}: {self.label}"

    @property
    def organization_id(self):
        return self.board.organization_id


class DomainBoardChoice(models.Model):
    field = models.ForeignKey(DomainBoardField, verbose_name="campo", on_delete=models.CASCADE, related_name="choices")
    label = models.CharField("rótulo", max_length=120)
    color = models.CharField("cor", max_length=7, default="#94A3B8")
    position = _position_field()
    is_active = models.BooleanField("ativa", default=True)

    class Meta:
        verbose_name = "opção do quadro de domínio"
        verbose_name_plural = "opções do quadro de domínio"
        ordering = ["position", "id"]

    @property
    def organization_id(self):
        return self.field.board.organization_id


class DomainBoardView(models.Model):
    class Type(models.TextChoices):
        TABLE = "TABLE", "Quadro principal"
        KANBAN = "KANBAN", "Kanban"
        CALENDAR = "CALENDAR", "Calendário"

    board = models.ForeignKey(DomainBoard, verbose_name="quadro", on_delete=models.CASCADE, related_name="views")
    name = models.CharField("nome", max_length=80)
    type = models.CharField("tipo", max_length=12, choices=Type.choices)
    position = _position_field()
    settings = models.JSONField("configuração", default=dict, blank=True)
    is_default = models.BooleanField("padrão", default=False)
    is_active = models.BooleanField("ativa", default=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("alterada em", auto_now=True)

    class Meta:
        verbose_name = "visualização de domínio"
        verbose_name_plural = "visualizações de domínio"
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=["board", "name"], name="uniq_domain_board_view_name")]

    @property
    def organization_id(self):
        return self.board.organization_id


class DomainBoardViewColumn(models.Model):
    view = models.ForeignKey(DomainBoardView, verbose_name="visualização", on_delete=models.CASCADE, related_name="columns")
    field = models.ForeignKey(DomainBoardField, verbose_name="campo", on_delete=models.CASCADE, related_name="view_columns")
    position = _position_field()
    width = models.PositiveIntegerField("largura", default=DEFAULT_COLUMN_WIDTH)
    is_visible = models.BooleanField("visível", default=True)

    class Meta:
        verbose_name = "coluna da visualização de domínio"
        verbose_name_plural = "colunas da visualização de domínio"
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=["view", "field"], name="uniq_domain_view_column_field")]

    @property
    def organization_id(self):
        return self.view.board.organization_id


class DomainBoardCardField(models.Model):
    view = models.ForeignKey(DomainBoardView, verbose_name="visualização", on_delete=models.CASCADE, related_name="card_fields")
    field = models.ForeignKey(DomainBoardField, verbose_name="campo", on_delete=models.CASCADE, related_name="card_fields")
    position = _position_field()
    is_visible = models.BooleanField("visível", default=True)

    class Meta:
        verbose_name = "campo do cartão de domínio"
        verbose_name_plural = "campos do cartão de domínio"
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=["view", "field"], name="uniq_domain_card_field")]

    @property
    def organization_id(self):
        return self.view.board.organization_id


class DomainCustomValue(models.Model):
    field = models.ForeignKey(DomainBoardField, verbose_name="campo", on_delete=models.CASCADE, related_name="custom_values")
    activity = models.ForeignKey(
        "activities.Activity", verbose_name="demanda", null=True, blank=True, on_delete=models.CASCADE, related_name="board_values"
    )
    task = models.ForeignKey(
        "activities.Task", verbose_name="tarefa", null=True, blank=True, on_delete=models.CASCADE, related_name="board_values"
    )
    value = models.JSONField("valor", default=dict, blank=True)
    updated_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, verbose_name="alterado por", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="domain_board_values_updated"
    )
    updated_at = models.DateTimeField("alterado em", auto_now=True)

    class Meta:
        verbose_name = "valor customizado de domínio"
        verbose_name_plural = "valores customizados de domínio"
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(activity__isnull=False, task__isnull=True) | models.Q(activity__isnull=True, task__isnull=False)),
                name="domain_custom_value_one_target",
            ),
            models.UniqueConstraint(fields=["field", "activity"], condition=models.Q(activity__isnull=False), name="uniq_domain_value_activity"),
            models.UniqueConstraint(fields=["field", "task"], condition=models.Q(task__isnull=False), name="uniq_domain_value_task"),
        ]

    @property
    def organization_id(self):
        return self.field.board.organization_id
