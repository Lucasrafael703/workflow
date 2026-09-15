from . import catalog
from .services import AuthorizationService


def navigation(request):
    """Esconde do menu o que a pessoa não pode usar (doc 09 §11).

    Isso é experiência do usuário, não segurança: a decisão real acontece na
    camada de serviço e é refeita a cada ação (Regras 05 §42).
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    can = AuthorizationService.can
    return {
        "lps_nav": {
            "management": AuthorizationService.can_anywhere(user, catalog.METRICAS_VISUALIZAR),
            "cadastros": (
                can(user, catalog.SETOR_EDITAR)
                or can(user, catalog.EMPRESA_GERIR)
                or can(user, catalog.MOTIVO_DEVOLUCAO_GERIR)
            ),
            "users": can(user, catalog.USUARIO_VISUALIZAR),
            "security": can(user, catalog.SEGURANCA_GERIR_PERFIS),
        }
    }
