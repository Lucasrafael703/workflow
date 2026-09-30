"""Return to the originating activity collection without accepting external URLs."""

from urllib.parse import urlencode, urlsplit

from django.urls import reverse


def activity_return_url(request):
    value = request.POST.get("next") or request.GET.get("next", "")
    try:
        target = urlsplit(value)
    except ValueError:
        return reverse("activity-list")
    allowed = {reverse(name) for name in ("activity-list", "activity-kanban", "activity-calendar")}
    if not target.scheme and not target.netloc and target.path in allowed and "\\" not in value:
        return target.path + ("?" + target.query if target.query else "")
    return reverse("activity-list")


def activity_detail_url(activity, return_url):
    return reverse("activity-detail", args=[activity.pk]) + "?" + urlencode({"next": return_url})
