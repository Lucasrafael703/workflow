from django.urls import path

from . import views

urlpatterns = [
    path("", views.ProcessListView.as_view(), name="process-list"),
    path("novo/", views.ProcessCreateView.as_view(), name="process-create"),
    path("<int:pk>/", views.ProcessEditView.as_view(), name="process-edit"),
    path("<int:pk>/informacoes/", views.ProcessBasicInfoUpdateView.as_view(), name="process-basic-info"),
    path("<int:pk>/output/", views.ProcessOutputUpdateView.as_view(), name="process-output"),
    path("<int:pk>/inputs/", views.ProcessInputAddView.as_view(), name="process-input-add"),
    path("<int:pk>/inputs/<int:input_pk>/remover/", views.ProcessInputRemoveView.as_view(), name="process-input-remove"),
    path("<int:pk>/criterios/", views.ProcessCriterionAddView.as_view(), name="process-criterion-add"),
    path("<int:pk>/criterios/<int:criterion_pk>/remover/", views.ProcessCriterionRemoveView.as_view(), name="process-criterion-remove"),
    path("<int:pk>/fluxo/", views.ProcessStepAddView.as_view(), name="process-step-add"),
    path("<int:pk>/fluxo/reordenar/", views.ProcessStepReorderView.as_view(), name="process-step-reorder"),
    path("<int:pk>/fluxo/<int:step_pk>/remover/", views.ProcessStepRemoveView.as_view(), name="process-step-remove"),
    path("<int:pk>/publicar/", views.ProcessPublishView.as_view(), name="process-publish"),
    path("<int:pk>/nova-versao/", views.ProcessNewVersionView.as_view(), name="process-new-version"),
    path("<int:pk>/ativo/", views.ProcessToggleActiveView.as_view(), name="process-toggle-active"),
]
