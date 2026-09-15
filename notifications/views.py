from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import ListView, View

from .models import Notification
from .services import NotificationService


# Eventos que esperam uma decisão de quem recebe, não apenas ciência
# (doc 09 §144-145).
ACTION_REQUIRED_EVENTS = {
    Notification.EventType.DEADLINE_PROPOSED,
    Notification.EventType.DEADLINE_CONFLICT,
    Notification.EventType.TASK_RETURNED,
    Notification.EventType.TASK_OVERDUE,
    Notification.EventType.TASK_ASSIGNED,
}


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "notifications/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user).select_related(
            "activity", "task"
        )
        view = self.request.GET.get("filter")
        if view == "nao-lidas":
            queryset = queryset.filter(is_read=False)
        elif view == "acao":
            queryset = queryset.filter(event_type__in=ACTION_REQUIRED_EVENTS)
        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notifications = context["notifications"]
        context["action_required"] = [
            n for n in notifications if n.event_type in ACTION_REQUIRED_EVENTS
        ]
        context["informative"] = [
            n for n in notifications if n.event_type not in ACTION_REQUIRED_EVENTS
        ]
        context["filter"] = self.request.GET.get("filter", "")
        return context


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        NotificationService.mark_read(notification)

        # Leva direto ao ponto que originou o aviso (doc 09 §147).
        if notification.url:
            return redirect(notification.url)
        if notification.task_id:
            return redirect("task-detail", pk=notification.task_id)
        if notification.activity_id:
            return redirect("activity-detail", pk=notification.activity_id)
        return redirect("notification-list")


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return redirect("notification-list")
