from django.conf import settings

from . import catalog
from .services import AuthorizationService, ResourceContext


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
    intake = _intake_nav(user, organization)

    return {
        "lps_nav": {
            "intake": intake["visible"],
            "intake_can_view": intake["can_view"],
            "boards": _boards_nav(user, organization),
            "management": AuthorizationService.can_anywhere(user, catalog.METRICAS_VISUALIZAR),
            "cadastros": (
                can(user, catalog.SETOR_EDITAR)
                or can(user, catalog.EMPRESA_GERIR)
                or can(user, catalog.MOTIVO_DEVOLUCAO_GERIR)
                or can(user, catalog.ESTAGIO_TAREFA_GERIR)
                or can(user, catalog.TAG_GERIR)
                or AuthorizationService.can_anywhere(user, catalog.PROCESSO_VISUALIZAR)
            ),
            "users": can(user, catalog.USUARIO_VISUALIZAR),
            "security": can(user, catalog.SEGURANCA_GERIR_PERFIS),
        },
        "lps_org": organization,
        "lps_open_tasks": _open_task_count(user),
        "lps_intake_new": intake["new"],
        "nav_active": _active_nav(request),
        "nav_active2": _active_nav2(request),
        "nav_cadastros_tab": _active_cadastros_tab(request),
    }


# Cada item do menu cobre uma família de rotas; o destaque vem do nome da URL
# para não precisar repetir "nav_active" em toda view.
_NAV_BY_URL_NAME = {
    "home": "home",
    "activity-list": "activities",
    "activity-detail": "activities",
    "activity-create": "activities",
    "activity-kanban": "activities",
    "activity-edit": "activities",
    "activity-cancel": "activities",
    "activity-reopen": "activities",
    "activity-change-owner": "activities",
    "intake-list": "intake",
    "intake-capture": "intake",
    "intake-detail": "intake",
    "intake-edit": "intake",
    "intake-convert": "intake",
    "intake-ignore": "intake",
    "intake-restore": "intake",
    "board-list": "boards",
    "board-create": "boards",
    "board-detail": "boards",
    "board-rename": "boards",
    "board-delete": "boards",
    "board-history": "boards",
    "board-view-create": "boards",
    "board-view-detail": "boards",
    "board-view-update": "boards",
    "board-view-delete": "boards",
    "board-view-lanes": "boards",
    "board-view-calendar": "boards",
    "board-group-create": "boards",
    "board-group-update": "boards",
    "board-group-reorder": "boards",
    "board-group-delete": "boards",
    "board-column-create": "boards",
    "board-column-rename": "boards",
    "board-column-resize": "boards",
    "board-column-reorder": "boards",
    "board-column-settings": "boards",
    "board-column-hide": "boards",
    "board-column-duplicate": "boards",
    "board-column-type": "boards",
    "board-column-delete": "boards",
    "board-column-fragment": "boards",
    "board-option-create": "boards",
    "board-option-update": "boards",
    "board-option-reorder": "boards",
    "board-option-delete": "boards",
    "board-item-create": "boards",
    "board-item-rename": "boards",
    "board-item-move": "boards",
    "board-item-delete": "boards",
    "board-item-detail": "boards",
    "board-cell-update": "boards",
    "task-list": "tasks",
    "task-kanban": "tasks",
    "task-calendar": "tasks",
    "task-detail": "tasks",
    "task-reopen": "tasks",
    "task-retroactive": "tasks",
    "task-dependency": "tasks",
    "task-return": "tasks",
    "task-block": "tasks",
    "task-move": "tasks",
    "task-cancel": "tasks",
    "task-manual-time": "tasks",
    "task-change-responsavel": "tasks",
    "task-assignment-reject": "tasks",
    "deadline-propose": "tasks",
    "conflict-resolve": "management",
    "task-quick-create": "tasks",
    "task-quick-create-standalone": "tasks",
    "task-edit": "tasks",
    "task-set-condition": "tasks",
    "queue": "queue",
    "queue-sector": "queue",
    "notification-list": "notifications",
    "management": "management",
    "history": "management",
    "cadastros": "cadastros",
    "process-list": "cadastros",
    "process-create": "cadastros",
    "process-edit": "cadastros",
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
    "taskstage-create": "cadastros",
    "taskstage-edit": "cadastros",
    "tag-create": "cadastros",
    "tag-edit": "cadastros",
    "user-list": "users",
    "user-create": "users",
    "user-edit": "users",
    "user-access": "users",
    "permissions": "permissions",
    "profile-create": "permissions",
    "profile-edit": "permissions",
    "settings": "settings",
    "equipe-pessoas": "equipe",
    "equipe-capacidade": "equipe",
    "equipe-carga-trabalho": "equipe",
    "gargalos-filas": "gargalos",
    "gargalos-gargalos": "gargalos",
    "gargalos-bloqueios": "gargalos",
    "gargalos-devolucoes": "gargalos",
    "processos-modelos": "processos",
    "config-etapas-status": "config-lps",
    "config-prioridades": "config-lps",
    "config-motivos-bloqueio": "config-lps",
    "config-motivos-devolucao": "config-lps",
}


# Telas do app "painel" (placeholders do menu) usam o próprio url_name como
# identidade — cada uma se destaca individualmente dentro do seu grupo.
_NAV2_URL_NAMES = {
    "equipe-pessoas",
    "equipe-capacidade",
    "equipe-carga-trabalho",
    "gargalos-filas",
    "gargalos-gargalos",
    "gargalos-bloqueios",
    "gargalos-devolucoes",
    "processos-modelos",
    "insights",
    "desenvolvimento",
    "resultados",
    "config-etapas-status",
    "config-prioridades",
    "config-motivos-bloqueio",
    "config-motivos-devolucao",
    "integracoes",
}


def _active_nav(request):
    match = getattr(request, "resolver_match", None)
    if match is None:
        return ""
    return _NAV_BY_URL_NAME.get(match.url_name, "")


def _active_nav2(request):
    """Identidade do subitem ativo entre as telas do app "painel"."""
    match = getattr(request, "resolver_match", None)
    if match is None:
        return ""
    return match.url_name if match.url_name in _NAV2_URL_NAMES else ""


# Dentro de Cadastros, cada URL de criar/editar já pertence a uma aba fixa —
# só a própria listagem depende do "?tab=" da querystring.
_CADASTROS_TAB_BY_URL_NAME = {
    "process-list": "processos",
    "process-create": "processos",
    "process-edit": "processos",
    "sector-create": "setores",
    "sector-edit": "setores",
    "company-create": "empresas",
    "company-edit": "empresas",
    "site-create": "obras",
    "site-edit": "obras",
    "costcenter-create": "centros-de-custo",
    "costcenter-edit": "centros-de-custo",
    "returnreason-create": "motivos",
    "returnreason-edit": "motivos",
    "taskstage-create": "estagios-de-tarefa",
    "taskstage-edit": "estagios-de-tarefa",
    "tag-create": "tags",
    "tag-edit": "tags",
}


def _active_cadastros_tab(request):
    """Qual aba de Cadastros destacar no submenu — usada para abrir o grupo
    já expandido e marcar o item certo, mesmo em telas de criar/editar que
    não carregam "?tab=" na própria URL."""
    match = getattr(request, "resolver_match", None)
    if match is None:
        return ""
    if match.url_name == "cadastros":
        return request.GET.get("tab", "setores")
    return _CADASTROS_TAB_BY_URL_NAME.get(match.url_name, "")


def _intake_nav(user, organization):
    """Menu "Entrada": aparece para quem pode ver ou registrar solicitações.

    O contador só conta o que está novo e a pessoa enxerga — é o que espera
    uma decisão dela. Roda a cada página, então é uma avaliação e um COUNT, e
    só quando a pessoa pode ver a Caixa de Entrada.

    Com a Caixa de Entrada inativa (`settings.INTAKE_ENABLED` desligado) o item
    não aparece e nada disso é consultado.
    """
    if not settings.INTAKE_ENABLED:
        return {"visible": False, "can_view": False, "new": 0}
    can_view = AuthorizationService.can_anywhere(user, catalog.ENTRADA_VISUALIZAR)
    visible = can_view or AuthorizationService.can_anywhere(user, catalog.ENTRADA_REGISTRAR)
    new = 0
    if can_view and organization is not None:
        from intake.services import IntakeService

        new = IntakeService.new_count(user, organization)
    return {"visible": visible, "can_view": can_view, "new": new}


def _boards_nav(user, organization):
    """Menu "Quadros": aparece para quem pode ver quadros da própria organização.

    Quadros só têm escopo de organização (não pertencem a um setor), então a pergunta é a mesma que a
    lista de quadros faz: `quadro.visualizar` no contexto da organização.
    """
    if organization is None:
        return False
    return AuthorizationService.can(user, catalog.QUADRO_VISUALIZAR, ResourceContext.for_new(organization))


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
