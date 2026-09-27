import uuid

from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django import forms

from .models import Profile

User = get_user_model()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["phone", "main_sector"]


class EmailAuthenticationForm(AuthenticationForm):
    """Login por e-mail (Telas/09_01_LOGIN.md) — autenticação real fica a
    cargo de accounts.auth_backends.EmailBackend; aqui só troca o campo."""

    username = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"autofocus": True}))


class SignUpForm(forms.Form):
    """Cria a conta (Telas/09_02_CRIAR_CONTA.md) — só a identidade da pessoa,
    sem organização/setor/perfil, que pertencem a outro fluxo (§21)."""

    display_name = forms.CharField(label="Nome de exibição", max_length=150)
    email = forms.EmailField(label="E-mail")
    password1 = forms.CharField(label="Senha", widget=forms.PasswordInput, strip=False)
    password2 = forms.CharField(label="Confirmar senha", widget=forms.PasswordInput, strip=False)
    accepted_terms = forms.BooleanField(
        label="Li e aceito os Termos de Uso e a Política de Privacidade.",
        error_messages={"required": "Aceite os Termos de Uso e a Política de Privacidade para continuar."},
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.", code="email_taken")
        return email

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        password_validation.validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "As senhas não coincidem.")
        return cleaned

    def save(self):
        email = self.cleaned_data["email"]
        user = User.objects.create_user(
            username=f"conta-{uuid.uuid4().hex[:20]}",
            email=email,
            first_name=self.cleaned_data["display_name"].strip(),
            password=self.cleaned_data["password1"],
            is_active=False,
        )
        return user


class VerifyEmailForm(forms.Form):
    code = forms.CharField(
        label="Código de confirmação",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "pattern": "[0-9]*", "autocomplete": "one-time-code"}),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise forms.ValidationError("Código inválido. Confira e tente novamente.")
        return code


class EmailChangeForm(forms.Form):
    email = forms.EmailField(label="Novo e-mail")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email
