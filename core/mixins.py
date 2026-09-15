from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.shortcuts import redirect


class OrganizationRequiredMixin(LoginRequiredMixin):
    """Resolve a organização do usuário e a deixa disponível em `self.organization`.

    Nenhuma tela da LPS pode consultar dados sem esse recorte: o isolamento entre
    organizações é estrutural (Regras 05 §43) e não pode depender apenas de
    esconder botões.
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
    """Exige uma ação do catálogo, avaliada dentro do escopo do recurso.

    Uma capacidade sem "onde" é ambígua: quem pode reordenar a fila do
    Comercial não reordena a de Compras (Regras 05 §19). Por isso a view
    informa qual objeto está sendo acessado através de `get_scope_object()`.

    Deve ser combinado com `OrganizationRequiredMixin`, declarado antes dele
    na lista de bases, para que quem ainda não tem organização seja levado ao
    cadastro em vez de receber um 403 sem explicação.
    """

    required_action = None

    def get_scope_object(self):
        """Objeto que situa a ação na estrutura da organização.

        `None` significa avaliar apenas escopos de organização — use quando a
        tela não trata de um recurso específico.
        """
        return None

    def dispatch(self, request, *args, **kwargs):
        from acessos.services import AuthorizationService

        # Nega por padrão: esquecer de declarar a ação fecha a tela, nunca abre.
        if self.required_action is None:
            raise ImproperlyConfigured(
                f"{type(self).__name__} usa ActionRequiredMixin sem declarar `required_action`."
            )
        if not request.user.is_authenticated:
            raise PermissionDenied("Você não possui acesso a este conteúdo.")
        if not AuthorizationService.can(request.user, self.required_action, self.get_scope_object()):
            raise PermissionDenied("Você não possui acesso a este conteúdo.")
        return super().dispatch(request, *args, **kwargs)


def user_sectors(user):
    """Setores em que o usuário participa operacionalmente (Regras 05 §8).

    Participação descreve onde a pessoa atua; não concede autorização.
    """
    from core.models import Sector

    return Sector.objects.filter(
        user_memberships__user=user, user_memberships__removed_at__isnull=True, is_active=True
    ).distinct()


def managed_sectors(user):
    """Setores que o usuário gerencia (Regras 05 §10)."""
    from accounts.models import UserSector
    from core.models import Sector

    return Sector.objects.filter(
        user_memberships__user=user,
        user_memberships__removed_at__isnull=True,
        user_memberships__role=UserSector.Role.GESTOR,
        is_active=True,
    ).distinct()
