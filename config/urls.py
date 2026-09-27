from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/", include("accounts.urls")),
    path("notificacoes/", include("notifications.urls")),
    path("processos/", include("processes.urls")),
    path("painel/", include("painel.urls")),
    path("", include("core.urls")),
    path("", include("activities.urls")),
]

# Served directly by Django in every environment: there is no separate nginx/CDN
# in front of the app (e.g. on Render), unlike STATIC_URL which whitenoise handles.
urlpatterns += [
    re_path(r"^%s(?P<path>.*)$" % settings.MEDIA_URL.lstrip("/"), serve, {"document_root": settings.MEDIA_ROOT}),
    re_path(
        r"^%s(?P<path>.*)$" % settings.ACTIVITY_FILES_URL.lstrip("/"),
        serve,
        {"document_root": settings.ACTIVITY_FILES_ROOT},
    ),
]
