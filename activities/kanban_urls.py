"""Rotas de ação do quadro Kanban (as telas `demandas/kanban/` e `tarefas/kanban/` ficam em `urls.py`).

`<domain>` é `demandas` ou `tarefas`; qualquer outro valor dá 404.
"""

from django.urls import path

from . import kanban

urlpatterns = [
    path("kanban/<slug:domain>/<int:pk>/cartao/", kanban.KanbanCardView.as_view(), name="kanban-card"),
    path("kanban/<slug:domain>/<int:pk>/etapa/", kanban.KanbanSetStageView.as_view(), name="kanban-set-stage"),
    path("kanban/<slug:domain>/<int:pk>/condicao/", kanban.KanbanSetConditionView.as_view(), name="kanban-set-condition"),
    path("kanban/<slug:domain>/criar/", kanban.KanbanCreateCardView.as_view(), name="kanban-create-card"),
    path("kanban/<slug:domain>/limite/", kanban.KanbanColumnLimitView.as_view(), name="kanban-column-limit"),
    path("kanban/<slug:domain>/opcoes/", kanban.KanbanCreateOptionView.as_view(), name="kanban-create-option"),
    path("demandas/<int:pk>/gaveta/", kanban.ActivityKanbanDrawerView.as_view(), name="activity-kanban-drawer"),
]
