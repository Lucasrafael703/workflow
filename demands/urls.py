from django.urls import path

from . import views

urlpatterns = [
    path("", views.DemandListView.as_view(), name="demand-list"),
    path("new/", views.DemandCreateView.as_view(), name="demand-create"),
    path("<int:pk>/", views.DemandDetailView.as_view(), name="demand-detail"),
    path("<int:pk>/edit/", views.DemandUpdateView.as_view(), name="demand-update"),
    path("<int:pk>/decide/", views.DemandDecisionView.as_view(), name="demand-decide"),
]
