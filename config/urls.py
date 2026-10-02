from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve

from accounts.forms import EmailAuthenticationForm
from core.legacy_redirects import MovedActivityFileView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html", authentication_form=EmailAuthenticationForm
        ),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "accounts/esqueci-senha/",
        auth_views.PasswordResetView.as_view(template_name="accounts/password_reset.html"),
        name="password_reset",
    ),
    path(
        "accounts/esqueci-senha/enviado/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "accounts/redefinir-senha/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        "accounts/redefinir-senha/concluido/",
        auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("accounts/", include("accounts.urls")),
    path("notificacoes/", include("notifications.urls")),
    path("processos/", include("processes.urls")),
    path("painel/", include("painel.urls")),
    path("entrada/", include("intake.urls")),
    path("quadros/", include("boards.urls")),
    path("", include("core.urls")),
    path("", include("activities.urls")),
]

# Served directly by Django in every environment: there is no separate nginx/CDN
# in front of the app (e.g. on Render), unlike STATIC_URL which whitenoise handles.
urlpatterns += [
    # Endereço dos anexos antes da troca de "atividade" por "demanda" (01/10/2026).
    re_path(r"^atividade-arquivos/(?P<rest>.*)$", MovedActivityFileView.as_view(), name="legacy-activity-files"),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^%s(?P<path>.*)$" % settings.MEDIA_URL.lstrip("/"), serve, {"document_root": settings.MEDIA_ROOT}),
    ]
