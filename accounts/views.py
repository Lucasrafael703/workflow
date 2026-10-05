from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, UpdateView

from .forms import EmailChangeForm, ProfileForm, SignUpForm, VerifyEmailForm
from .models import EmailVerification, Profile

User = get_user_model()


class ProfileView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("profile")

    def get_object(self, queryset=None):
        return self.request.user.profile

    def form_valid(self, form):
        messages.success(self.request, "Perfil atualizado.")
        return super().form_valid(form)


def _send_verification_email(user, verification):
    send_mail(
        subject="Confirme seu e-mail — LPS",
        message=(
            f"Olá, {user.first_name}!\n\n"
            f"Seu código de confirmação é: {verification.code}\n\n"
            f"Ele expira em {int(EmailVerification.CODE_TTL.total_seconds() // 60)} minutos."
        ),
        from_email=None,
        recipient_list=[user.email],
    )


class PendingVerificationMixin:
    """Views do fluxo de confirmação de e-mail (Telas/09_03) compartilham o
    mesmo estado: a conta recém-criada e ainda inativa, referenciada pela
    sessão até o e-mail ser confirmado."""

    redirect_url_name = "signup"

    def get_pending_user(self):
        user_id = self.request.session.get("pending_verification_user_id")
        if not user_id:
            return None
        return User.objects.filter(pk=user_id, is_active=False).first()

    def dispatch(self, request, *args, **kwargs):
        self.pending_user = self.get_pending_user()
        if self.pending_user is None:
            return redirect(self.redirect_url_name)
        return super().dispatch(request, *args, **kwargs)


class SignUpView(FormView):
    """Criar conta (Telas/09_02): só a identidade da pessoa, sem organização."""

    template_name = "accounts/signup.html"
    form_class = SignUpForm

    def form_valid(self, form):
        user = form.save()
        verification = EmailVerification.issue(user)
        _send_verification_email(user, verification)
        self.request.session["pending_verification_user_id"] = user.pk
        return redirect("verify-email")


class VerifyEmailView(PendingVerificationMixin, FormView):
    """Confirmar e-mail (Telas/09_03): código de 6 dígitos, reenvio e troca de e-mail."""

    template_name = "accounts/verify_email.html"
    form_class = VerifyEmailForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        local, _, domain = self.pending_user.email.partition("@")
        visible = local[:2] if len(local) > 2 else local[:1]
        context["masked_email"] = f"{visible}***@{domain}"
        verification = getattr(self.pending_user, "email_verification", None)
        context["can_resend"] = bool(verification and verification.can_resend)
        return context

    def form_valid(self, form):
        verification = self.pending_user.email_verification
        code = form.cleaned_data["code"]

        if verification.is_expired:
            form.add_error(None, "Este código expirou. Solicite um novo código para continuar.")
            return self.form_invalid(form)
        if verification.attempts >= EmailVerification.MAX_ATTEMPTS:
            form.add_error(None, "Muitas tentativas. Solicite um novo código para continuar.")
            return self.form_invalid(form)
        if not verification.verify(code):
            form.add_error("code", "Código inválido. Confira e tente novamente.")
            return self.form_invalid(form)

        self.pending_user.is_active = True
        self.pending_user.save(update_fields=["is_active"])
        del self.request.session["pending_verification_user_id"]
        messages.success(self.request, "E-mail confirmado com sucesso.")
        return redirect("login")


class ResendVerificationCodeView(PendingVerificationMixin, View):
    def post(self, request, *args, **kwargs):
        verification = getattr(self.pending_user, "email_verification", None)
        if verification and not verification.can_resend:
            messages.error(request, "Aguarde um instante antes de solicitar um novo código.")
            return redirect("verify-email")

        verification = EmailVerification.issue(self.pending_user)
        _send_verification_email(self.pending_user, verification)
        messages.success(request, "Novo código enviado.")
        return redirect("verify-email")


class ChangeVerificationEmailView(PendingVerificationMixin, FormView):
    template_name = "accounts/change_email.html"
    form_class = EmailChangeForm

    def form_valid(self, form):
        self.pending_user.email = form.cleaned_data["email"]
        self.pending_user.save(update_fields=["email"])
        verification = EmailVerification.issue(self.pending_user)
        _send_verification_email(self.pending_user, verification)
        messages.success(self.request, "E-mail atualizado. Enviamos um novo código.")
        return redirect("verify-email")


class RequiredPasswordChangeView(LoginRequiredMixin, FormView):
    """Troca obrigatória após uma senha provisória (ver `ForcePasswordChangeMiddleware`)."""

    template_name = "accounts/password_change_required.html"
    form_class = PasswordChangeForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.profile.must_change_password:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)
        profile = user.profile
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password"])
        messages.success(self.request, "Senha criada. Bem-vindo à LPS!")
        return redirect("home")
