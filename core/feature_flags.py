"""Feature flags da LPS (lidas das settings a cada chamada, para poderem ser trocadas em teste e no ambiente)."""

from django.conf import settings

WORKSPACE_V2_MODES = ("off", "allowlist", "on")


def workspace_v2_mode():
    """`off`, `allowlist` ou `on`. Qualquer valor desconhecido vale `off`: na dúvida, a tela de sempre."""
    mode = str(getattr(settings, "WORKSPACE_V2", "off") or "off").strip().lower()
    return mode if mode in WORKSPACE_V2_MODES else "off"


def workspace_v2_enabled(user):
    """O Workspace de Demandas (shell único) está ligado para esta pessoa?

    - `off`: ninguém;
    - `on`: toda pessoa autenticada;
    - `allowlist`: só quem está em `WORKSPACE_V2_USERS`, por e-mail ou por nome de usuário (sem diferenciar
      maiúsculas de minúsculas).
    Pessoa não autenticada nunca vê o Workspace (a tela exige login de qualquer forma)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    mode = workspace_v2_mode()
    if mode == "on":
        return True
    if mode != "allowlist":
        return False
    allowed = {str(item).strip().lower() for item in getattr(settings, "WORKSPACE_V2_USERS", []) if str(item).strip()}
    identities = {str(getattr(user, "email", "") or "").strip().lower(), str(user.get_username() or "").strip().lower()}
    return bool(allowed & (identities - {""}))
