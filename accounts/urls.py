from django.urls import path

from . import views

urlpatterns = [
    path("me/", views.ProfileView.as_view(), name="profile"),
    path("criar-conta/", views.SignUpView.as_view(), name="signup"),
    path("confirmar-email/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("confirmar-email/reenviar/", views.ResendVerificationCodeView.as_view(), name="verify-email-resend"),
    path("confirmar-email/alterar/", views.ChangeVerificationEmailView.as_view(), name="verify-email-change"),
]
