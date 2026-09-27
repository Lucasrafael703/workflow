from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailBackend(ModelBackend):
    """Autentica por e-mail (case-insensitive) em vez de username.

    O username continua existindo como identificador interno do Django
    (FKs, admin, etc.) — só o login passa a pedir e-mail, como na tela
    oficial (Telas/09_01_LOGIN.md).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email", username)
        if email is None or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=email)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
