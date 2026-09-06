from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("processes/", views.ProcessListView.as_view(), name="process-list"),
    path("processes/new/", views.ProcessCreateView.as_view(), name="process-create"),
    path("processes/<int:pk>/", views.ProcessDetailView.as_view(), name="process-detail"),
    path("processes/<int:pk>/cancel/", views.ProcessCancelView.as_view(), name="process-cancel"),
    path("processes/<int:pk>/timeline/", views.ProcessTimelineView.as_view(), name="process-timeline"),
    path("processes/<int:pk>/attachments/upload/", views.AttachmentUploadView.as_view(), name="attachment-upload"),
    path("activities/", views.MyActivitiesListView.as_view(), name="my-activities"),
    path("activities/<int:pk>/", views.ActivityDetailView.as_view(), name="activity-detail"),
    path("activities/<int:pk>/claim/", views.ActivityClaimView.as_view(), name="activity-claim"),
    path("activities/<int:pk>/complete/", views.ActivityCompleteView.as_view(), name="activity-complete"),
    path("activities/<int:pk>/reopen/", views.ActivityReopenView.as_view(), name="activity-reopen"),
    path("activities/<int:pk>/block/", views.ActivityBlockView.as_view(), name="activity-block"),
    path("activities/<int:pk>/unblock/", views.ActivityUnblockView.as_view(), name="activity-unblock"),
    path("activities/<int:pk>/cancel/", views.ActivityCancelView.as_view(), name="activity-cancel"),
]
