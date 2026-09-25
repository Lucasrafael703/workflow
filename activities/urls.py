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
    path(
        "atividades/<int:pk>/prazo/",
        views.ActivityChangeDeadlineView.as_view(),
        name="activity-change-deadline",
    ),
    path("atividades/<int:pk>/assumir/", views.ActivityClaimView.as_view(), name="activity-claim"),
    path("atividades/<int:pk>/finalizar/", views.ActivityFinalizeView.as_view(), name="activity-finalize"),
    path("atividades/<int:pk>/pendente/", views.ActivityMarkPendingView.as_view(), name="activity-mark-pending"),
    path(
        "atividades/<int:pk>/pendencia/aprovar/",
        views.ActivityApprovePendencyView.as_view(),
        name="activity-approve-pendency",
    ),
    path("atividades/<int:pk>/mensagem/", views.ActivityMessageCreateView.as_view(), name="activity-message"),
    path("atividades/<int:pk>/continuar/", views.ActivityContinueView.as_view(), name="activity-continue"),
    path("atividades/<int:activity_pk>/tarefas/nova/", views.TaskCreateView.as_view(), name="task-create"),
    path(
        "atividades/<int:activity_pk>/tarefas/rapida/",
        views.TaskQuickCreateView.as_view(),
        name="task-quick-create",
    ),
    path("atividades/nova-rapida/", views.ActivityMiniCreateView.as_view(), name="activity-mini-create"),
    path("atividades/busca/", views.ActivitySearchView.as_view(), name="activity-search"),
    path("atividades/<int:pk>/anexos/", views.ActivityAttachmentUploadView.as_view(), name="activity-attachment-upload"),
    path(
        "atividades/<int:pk>/anexos/<int:attachment_pk>/remover/",
        views.ActivityAttachmentDeleteView.as_view(),
        name="activity-attachment-delete",
    ),
    # Tarefas
    path("tarefas/", views.TaskListView.as_view(), name="task-list"),
    path("tarefas/nova-rapida/", views.TaskQuickCreateStandaloneView.as_view(), name="task-quick-create-standalone"),
    path("tarefas/kanban/", views.TaskKanbanView.as_view(), name="task-kanban"),
    path("tarefas/calendario/", views.TaskCalendarView.as_view(), name="task-calendar"),
    path("tarefas/<int:pk>/mover-estagio/", views.TaskMoveStageView.as_view(), name="task-move-stage"),
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
    # Painel lateral (drawer) da tarefa
    path("tarefas/<int:pk>/painel/", views.TaskDrawerView.as_view(), name="task-drawer"),
    path(
        "tarefas/<int:pk>/iniciar/ajax/",
        views.TaskAjaxActionView.as_view(action="start"),
        name="task-start-ajax",
    ),
    path(
        "tarefas/<int:pk>/pausar/ajax/",
        views.TaskAjaxActionView.as_view(action="pause"),
        name="task-pause-ajax",
    ),
    path(
        "tarefas/<int:pk>/concluir/ajax/",
        views.TaskAjaxActionView.as_view(action="complete"),
        name="task-complete-ajax",
    ),
    path("tarefas/<int:pk>/checklist/", views.TaskChecklistAddView.as_view(), name="task-checklist-add"),
    path(
        "checklist/<int:pk>/alternar/",
        views.TaskChecklistToggleView.as_view(),
        name="task-checklist-toggle",
    ),
    path(
        "checklist/<int:pk>/remover/",
        views.TaskChecklistRemoveView.as_view(),
        name="task-checklist-remove",
    ),
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
