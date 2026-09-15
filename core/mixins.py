from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class OrganizationRequiredMixin(LoginRequiredMixin):
    """Resolve a organização do usuário e a deixa disponível em `self.organization`.

    Nenhuma tela da LPS pode consultar dados sem esse recorte: o isolamento entre
    organizações é estrutural (Regras 01 §23, 05 §8) e não pode depender apenas
    de esconder botões.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        profile = getattr(request.user, "profile", None)
        organization = getattr(profile, "organization", None)
        if organization is None:
            messages.error(
                request,
                "Seu usuário ainda não está vinculado a uma organização. "
                "Peça a um administrador para concluir seu cadastro.",
            )
            return redirect("profile")

        self.organization = organization
        return super().dispatch(request, *args, **kwargs)


class ActionRequiredMixin:
    """Exige uma ação (permissão) que a camada de serviço não valida sozinha.

    Os serviços já barram as ações sensíveis que conhecem; estas aqui são as que
    dependem exclusivamente da tela (ex.: enxergar a fila completa do setor).
    """

    required_action = None

    def dispatch(self, request, *args, **kwargs):
        if self.required_action and not request.user.has_perm(self.required_action):
            raise PermissionDenied("Você não possui acesso a este conteúdo.")
        return super().dispatch(request, *args, **kwargs)


def user_sectors(user):
    """Setores em que o usuário participa operacionalmente (Regras 05 §24-26)."""
    from core.models import Sector

    return Sector.objects.filter(
        user_memberships__user=user, user_memberships__removed_at__isnull=True, is_active=True
    ).distinct()
