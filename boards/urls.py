from django.urls import path

from . import views
from . import work_views

# Sem `app_name`: as rotas do projeto são globais e em kebab-case (`board-*`).
urlpatterns = [
    # Configuração e mutações das lentes sobre Demandas/Tarefas. Elas não usam
    # BoardItem: o alvo continua sendo o objeto operacional do app activities.
    path(
        "dominio/<int:board_pk>/campos/<int:field_pk>/itens/<int:object_pk>/valor/",
        work_views.WorkBoardValueView.as_view(),
        name="workboard-value",
    ),
    path(
        "dominio/visoes/<int:view_pk>/campos/<int:field_pk>/layout/",
        work_views.WorkBoardLayoutView.as_view(),
        name="workboard-layout",
    ),
    path(
        "dominio/visoes/<int:view_pk>/cartoes/",
        work_views.WorkBoardCardFieldsView.as_view(),
        name="workboard-card-fields",
    ),
    path("dominio/<int:board_pk>/campos/novo/", work_views.WorkBoardFieldCreateView.as_view(), name="workboard-field-create"),
    path("dominio/visoes/<int:view_pk>/configuracao/", work_views.WorkBoardViewSettingsView.as_view(), name="workboard-view-settings"),
    path("", views.BoardListView.as_view(), name="board-list"),
    path("novo/", views.BoardCreateView.as_view(), name="board-create"),
    path("<int:pk>/", views.BoardDetailView.as_view(), name="board-detail"),
    path("<int:pk>/renomear/", views.BoardRenameView.as_view(), name="board-rename"),
    path("<int:pk>/excluir/", views.BoardDeleteView.as_view(), name="board-delete"),
    path("<int:pk>/historico/", views.BoardHistoryView.as_view(), name="board-history"),
    # visualizações (Kanban)
    path("<int:pk>/visoes/novo/", views.ViewCreateView.as_view(), name="board-view-create"),
    path("visoes/<int:pk>/", views.BoardKanbanView.as_view(), name="board-view-detail"),
    path("visoes/<int:pk>/editar/", views.ViewUpdateView.as_view(), name="board-view-update"),
    path("visoes/<int:pk>/excluir/", views.ViewDeleteView.as_view(), name="board-view-delete"),
    path("visoes/<int:pk>/lanes/", views.ViewLanesView.as_view(), name="board-view-lanes"),
    # grupos
    path("<int:pk>/grupos/novo/", views.GroupCreateView.as_view(), name="board-group-create"),
    path("grupos/<int:pk>/editar/", views.GroupUpdateView.as_view(), name="board-group-update"),
    path("grupos/<int:pk>/mover/", views.GroupReorderView.as_view(), name="board-group-reorder"),
    path("grupos/<int:pk>/excluir/", views.GroupDeleteView.as_view(), name="board-group-delete"),
    # colunas
    path("<int:pk>/colunas/novo/", views.ColumnCreateView.as_view(), name="board-column-create"),
    path("colunas/<int:pk>/renomear/", views.ColumnRenameView.as_view(), name="board-column-rename"),
    path("colunas/<int:pk>/largura/", views.ColumnResizeView.as_view(), name="board-column-resize"),
    path("colunas/<int:pk>/mover/", views.ColumnReorderView.as_view(), name="board-column-reorder"),
    path("colunas/<int:pk>/configuracoes/", views.ColumnSettingsView.as_view(), name="board-column-settings"),
    path("colunas/<int:pk>/ocultar/", views.ColumnHideView.as_view(), name="board-column-hide"),
    path("colunas/<int:pk>/duplicar/", views.ColumnDuplicateView.as_view(), name="board-column-duplicate"),
    path("colunas/<int:pk>/tipo/", views.ColumnTypeView.as_view(), name="board-column-type"),
    path("colunas/<int:pk>/excluir/", views.ColumnDeleteView.as_view(), name="board-column-delete"),
    path("colunas/<int:pk>/fragmento/", views.ColumnFragmentView.as_view(), name="board-column-fragment"),
    # etiquetas de Status e Lista
    path("colunas/<int:pk>/etiquetas/novo/", views.OptionCreateView.as_view(), name="board-option-create"),
    path("etiquetas/<int:pk>/editar/", views.OptionUpdateView.as_view(), name="board-option-update"),
    path("etiquetas/<int:pk>/mover/", views.OptionReorderView.as_view(), name="board-option-reorder"),
    path("etiquetas/<int:pk>/excluir/", views.OptionDeleteView.as_view(), name="board-option-delete"),
    # itens e células
    path("<int:pk>/itens/novo/", views.ItemCreateView.as_view(), name="board-item-create"),
    path("itens/<int:pk>/renomear/", views.ItemRenameView.as_view(), name="board-item-rename"),
    path("itens/<int:pk>/mover/", views.ItemMoveView.as_view(), name="board-item-move"),
    path("itens/<int:pk>/excluir/", views.ItemDeleteView.as_view(), name="board-item-delete"),
    path(
        "itens/<int:item_pk>/colunas/<int:column_pk>/valor/",
        views.CellUpdateView.as_view(),
        name="board-cell-update",
    ),
]
