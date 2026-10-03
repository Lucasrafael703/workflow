from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def invitation_link(request, user):
    """Link para a pessoa criar a própria senha (o mesmo mecanismo da recuperação de senha)."""
    path = reverse(
        "password_reset_confirm",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        },
    )
    return request.build_absolute_uri(path)


def send_invitation(request, user, invited_by):
    """Envia o convite por e-mail e devolve o link (para o administrador copiar se o e-mail falhar)."""
    link = invitation_link(request, user)
    organization = getattr(getattr(user, "profile", None), "organization", None)
    where = f" na {organization.name}" if organization else ""
    inviter = invited_by.get_full_name() or invited_by.get_username()
    send_mail(
        subject="Você foi convidado para a LPS",
        message=(
            f"Olá, {user.first_name or user.get_username()}!\n\n"
            f"{inviter} cadastrou você{where} na LPS.\n"
            f"Para entrar, crie a sua senha neste link:\n\n{link}\n\n"
            "Depois é só entrar com o seu e-mail e a senha que você escolheu."
        ),
        from_email=None,
        recipient_list=[user.email],
    )
    return link
