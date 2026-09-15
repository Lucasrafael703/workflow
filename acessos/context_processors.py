from . import catalog
from .services import AuthorizationService


def navigation(request):
    """Alimenta o menu lateral: o que aparece, o contexto e os contadores.

    Esconder do menu o que a pessoa não pode usar é experiência do usuário, não
    segurança (doc 09 §11): a decisão real acontece na camada de serviço e é
    refeita a cada ação (Regras 05 §42).

    O contador só existe para o que é acionável — quantidade de tarefas
    esperando a pessoa, não volume de trabalho em geral (Benchmark §3).
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    can = AuthorizationService.can
    profile = getattr(user, "profile", None)
    organization = getattr(profile, "organization", None)

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
        },
        "lps_org": organization,
        "lps_open_tasks": _open_task_count(user),
        "nav_active": _active_nav(request),
    }


# Cada item do menu cobre uma família de rotas; o destaque vem do nome da URL
# para não precisar repetir "nav_active" em toda view.
_NAV_BY_URL_NAME = {
    "home": "home",
    "activity-list": "activities",
    "activity-detail": "activities",
    "activity-create": "activities",
    "activity-edit": "activities",
    "activity-cancel": "activities",
    "activity-reopen": "activities",
    "activity-change-owner": "activities",
    "task-list": "tasks",
    "task-detail": "tasks",
    "task-create": "tasks",
    "task-edit": "tasks",
    "queue": "queue",
    "queue-sector": "queue",
    "notification-list": "notifications",
    "management": "management",
    "history": "management",
    "cadastros": "cadastros",
    "sector-create": "cadastros",
    "sector-edit": "cadastros",
    "company-create": "cadastros",
    "company-edit": "cadastros",
    "site-create": "cadastros",
    "site-edit": "cadastros",
    "costcenter-create": "cadastros",
    "costcenter-edit": "cadastros",
    "returnreason-create": "cadastros",
    "returnreason-edit": "cadastros",
    "user-list": "users",
    "user-create": "users",
    "user-edit": "users",
    "user-access": "users",
    "permissions": "permissions",
    "profile-create": "permissions",
    "profile-edit": "permissions",
    "settings": "settings",
}


def _active_nav(request):
    match = getattr(request, "resolver_match", None)
    if match is None:
        return ""
    return _NAV_BY_URL_NAME.get(match.url_name, "")


def _open_task_count(user):
    """Tarefas em aberto em que a pessoa é executora — o que ela precisa tocar."""
    from activities.models import Task

    return Task.objects.filter(
        executors__user=user,
        executors__removed_at__isnull=True,
        status__in=[
            Task.Status.NAO_INICIADA,
            Task.Status.DISPONIVEL,
            Task.Status.EM_FILA,
            Task.Status.EM_EXECUCAO,
            Task.Status.DEVOLVIDA,
        ],
    ).distinct().count()
