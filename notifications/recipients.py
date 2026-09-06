from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


def _dedupe(*querysets):
    by_id = {}
    for qs in querysets:
        for user in qs:
            by_id[user.id] = user
    return list(by_id.values())


def resolve_admins():
    return list(User.objects.filter(groups__name=settings.ADMIN_GROUP_NAME).distinct())


def resolve_group_and_admins(group):
    """Usuários de um Group específico + membros do grupo de administradores
    (settings.ADMIN_GROUP_NAME), sem duplicar quem estiver nos dois."""
    admins = User.objects.filter(groups__name=settings.ADMIN_GROUP_NAME)
    if group is None:
        return _dedupe(admins)
    members = User.objects.filter(groups=group)
    return _dedupe(admins, members)
