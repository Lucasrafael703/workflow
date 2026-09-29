def my_active_sessions(request):
    """Sessões de trabalho abertas da pessoa logada, disponíveis em toda
    página — alimenta o indicador de cronômetro na topbar (Regra 04 §115
    revista: várias tarefas podem estar em execução ao mesmo tempo)."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    from .models import WorkSession

    sessions = list(
        WorkSession.objects.filter(user=user, ended_at__isnull=True)
        .select_related("task", "task__activity")
        .order_by("started_at")
    )
    return {"my_active_sessions": sessions, "my_active_sessions_count": len(sessions)}
