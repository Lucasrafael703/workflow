from django.contrib.auth import get_user_model

User = get_user_model()


def _dedupe(*querysets):
    by_id = {}
    for qs in querysets:
        for user in qs:
            by_id[user.id] = user
    return set(by_id.values())


def resolve_sector_members(sector):
    """Quem participa operacionalmente do setor (Regras 05 §8)."""
    if sector is None:
        return set()
    return _dedupe(
        User.objects.filter(
            sector_memberships__sector=sector,
            sector_memberships__removed_at__isnull=True,
            is_active=True,
        )
    )


def resolve_sector_managers(sector):
    """Gestores do setor — usados para escalonamento e ciência (Regras 05 §10)."""
    from accounts.models import UserSector

    if sector is None:
        return set()
    return _dedupe(
        User.objects.filter(
            sector_memberships__sector=sector,
            sector_memberships__removed_at__isnull=True,
            sector_memberships__role=UserSector.Role.GESTOR,
            is_active=True,
        )
    )


def resolve_sector_and_admins(sector):
    """Destinatários naturais de um evento do setor.

    Retorna sempre um set, para compor com `|` nos chamadores.
    """
    return resolve_sector_members(sector) | resolve_sector_managers(sector)
