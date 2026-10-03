from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """Quem entrou com uma senha provisória escolhe a própria antes de qualquer outra tela.

    A senha provisória é definida por um administrador em "Novo usuário" (Primeiro acesso). Enquanto
    `Profile.must_change_password` estiver ligado, tudo redireciona para a troca; sair e os arquivos
    estáticos continuam livres.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            profile = getattr(user, "profile", None)
            if profile is not None and profile.must_change_password and not self._allowed(request):
                return redirect("password-change-required")
        return self.get_response(request)

    @staticmethod
    def _allowed(request):
        path = request.path
        return path in {reverse("password-change-required"), reverse("logout")} or path.startswith("/static/")
