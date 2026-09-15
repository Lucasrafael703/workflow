from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


def _dedupe(*querysets):
    by_id = {}
    for qs in querysets:
        for user in qs:
            by_id[user.id] = user
    return set(by_id.values())


def resolve_admins():
    return set(User.objects.filter(groups__name=settings.ADMIN_GROUP_NAME).distinct())


def resolve_sector_and_admins(sector):
    """Usuários com participação ativa no setor (accounts.UserSector) + membros
    do grupo de administradores (settings.ADMIN_GROUP_NAME), sem duplicar.

    Retorna sempre um set, para permitir composição com `|` nos chamadores.
    """
    admins = User.objects.filter(groups__name=settings.ADMIN_GROUP_NAME)
    if sector is None:
        return _dedupe(admins)
    members = User.objects.filter(
        sector_memberships__sector=sector, sector_memberships__removed_at__isnull=True
    )
    return _dedupe(admins, members)
