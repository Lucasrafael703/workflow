from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    # Atividades
    path("atividades/", views.ActivityListView.as_view(), name="activity-list"),
    path("atividades/nova/", views.ActivityCreateView.as_view(), name="activity-create"),
    path("atividades/<int:pk>/", views.ActivityDetailView.as_view(), name="activity-detail"),
    path("atividades/<int:pk>/editar/", views.ActivityEditView.as_view(), name="activity-edit"),
    path("atividades/<int:pk>/concluir/", views.ActivityCompleteView.as_view(), name="activity-complete"),
    path("atividades/<int:pk>/cancelar/", views.ActivityCancelView.as_view(), name="activity-cancel"),
    path("atividades/<int:pk>/reabrir/", views.ActivityReopenView.as_view(), name="activity-reopen"),
    path("atividades/<int:pk>/dono/", views.ActivityChangeOwnerView.as_view(), name="activity-change-owner"),
    path("atividades/<int:pk>/mensagem/", views.ActivityMessageCreateView.as_view(), name="activity-message"),
    path("atividades/<int:activity_pk>/tarefas/nova/", views.TaskCreateView.as_view(), name="task-create"),
    # Tarefas
    path("tarefas/", views.TaskListView.as_view(), name="task-list"),
    path("tarefas/<int:pk>/", views.TaskDetailView.as_view(), name="task-detail"),
    path("tarefas/<int:pk>/editar/", views.TaskEditView.as_view(), name="task-edit"),
    path("tarefas/<int:pk>/assumir/", views.TaskActionView.as_view(action="assume"), name="task-assume"),
    path("tarefas/<int:pk>/iniciar/", views.TaskActionView.as_view(action="start"), name="task-start"),
    path("tarefas/<int:pk>/pausar/", views.TaskActionView.as_view(action="pause"), name="task-pause"),
    path("tarefas/<int:pk>/retomar/", views.TaskActionView.as_view(action="resume"), name="task-resume"),
    path("tarefas/<int:pk>/concluir/", views.TaskActionView.as_view(action="complete"), name="task-complete"),
    path("tarefas/<int:pk>/desbloquear/", views.TaskActionView.as_view(action="unblock"), name="task-unblock"),
    path("tarefas/<int:pk>/devolver/", views.TaskReturnView.as_view(), name="task-return"),
    path("tarefas/<int:pk>/bloquear/", views.TaskBlockView.as_view(), name="task-block"),
    path("tarefas/<int:pk>/mover/", views.TaskMoveView.as_view(), name="task-move"),
    path("tarefas/<int:pk>/cancelar/", views.TaskCancelView.as_view(), name="task-cancel"),
    path("tarefas/<int:pk>/executores/", views.TaskExecutorAddView.as_view(), name="task-executor-add"),
    path(
        "tarefas/<int:pk>/executores/<int:user_pk>/remover/",
        views.TaskExecutorRemoveView.as_view(),
        name="task-executor-remove",
    ),
    path(
        "tarefas/<int:pk>/atribuicoes/<int:assignment_pk>/aceitar/",
        views.TaskAssignmentAcceptView.as_view(),
        name="task-assignment-accept",
    ),
    path(
        "tarefas/<int:pk>/atribuicoes/<int:assignment_pk>/recusar/",
        views.TaskAssignmentRejectView.as_view(),
        name="task-assignment-reject",
    ),
    path("tarefas/<int:pk>/tempo/", views.TaskManualTimeView.as_view(), name="task-manual-time"),
    path("tarefas/<int:pk>/mensagem/", views.TaskMessageCreateView.as_view(), name="task-message"),
    # Prazos
    path("tarefas/<int:pk>/prazo/propor/", views.DeadlineProposeView.as_view(), name="deadline-propose"),
    path(
        "prazos/<int:pk>/aceitar/",
        views.DeadlineDecisionView.as_view(decision="accept"),
        name="deadline-accept",
    ),
    path(
        "prazos/<int:pk>/recusar/",
        views.DeadlineDecisionView.as_view(decision="reject"),
        name="deadline-reject",
    ),
    path("conflitos/<int:pk>/resolver/", views.ConflictResolveView.as_view(), name="conflict-resolve"),
    # Fila, gestão e histórico
    path("fila/", views.QueueView.as_view(), name="queue"),
    path("fila/<int:sector_pk>/", views.QueueView.as_view(), name="queue-sector"),
    path("fila/entrada/<int:pk>/reordenar/", views.QueueReorderView.as_view(), name="queue-reorder"),
    path("gestao/", views.ManagementView.as_view(), name="management"),
    path("historico/", views.HistoryView.as_view(), name="history"),
]
