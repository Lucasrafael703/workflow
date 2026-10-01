from django.urls import path

from . import views

urlpatterns = [
    path("", views.IntakeListView.as_view(), name="intake-list"),
    path("registrar/", views.IntakeCaptureView.as_view(), name="intake-capture"),
    path("<int:pk>/", views.IntakeDetailView.as_view(), name="intake-detail"),
    path("<int:pk>/editar/", views.IntakeEditView.as_view(), name="intake-edit"),
    path("<int:pk>/criar-demanda/", views.IntakeConvertView.as_view(), name="intake-convert"),
    path("<int:pk>/ignorar/", views.IntakeIgnoreView.as_view(), name="intake-ignore"),
    path("<int:pk>/restaurar/", views.IntakeRestoreView.as_view(), name="intake-restore"),
]
