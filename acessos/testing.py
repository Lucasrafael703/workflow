"""Auxiliares para conceder acesso nos testes.

Deixa explícito em cada teste **o que** foi concedido e **onde** vale — que é
justamente o que o motor passou a exigir.
"""

from .models import Action, Profile, ProfileAction, Scope, UserAction, UserProfile
from .services import ScopeService


def ensure_catalog():
    """Garante o catálogo de ações no banco de testes.

    Cria direto a partir do catálogo em memória: chamar o comando a cada teste
    seria lento e ruidoso.
    """
    from .catalog import GROUPS

    if Action.objects.exists():
        return

    from .models import ActionGroup

    for order, (group_key, group_name, actions) in enumerate(GROUPS, start=1):
        group = ActionGroup.objects.create(key=group_key, name=group_name, order=order)
        Action.objects.bulk_create(
            Action(
                group=group, key=key, name=name, description=description, is_sensitive=sensitive
            )
            for key, name, description, sensitive in actions
        )


def grant_action(user, action_key, organization=None, scope=None, sector=None, relation=None):
    """Concede uma ação diretamente ao usuário, dentro de um escopo.

    Sem `scope`, `sector` ou `relation`, vale para a organização inteira.
    """
    ensure_catalog()
    organization = organization or user.profile.organization
    action = Action.objects.get(key=action_key)

    if scope is None:
        if sector is not None:
            scope = ScopeService.sector_scope(sector)
        elif relation is not None:
            scope = ScopeService.relation_scope(organization, relation)
        else:
            scope = ScopeService.organization_scope(organization)

    return UserAction.objects.get_or_create(
        organization=organization, user=user, action=action, scope=scope, is_active=True
    )[0]


def grant_actions(user, action_keys, **kwargs):
    return [grant_action(user, key, **kwargs) for key in action_keys]


def make_profile(organization, name, action_keys):
    ensure_catalog()
    profile = Profile.objects.create(organization=organization, name=name)
    for key in action_keys:
        ProfileAction.objects.create(profile=profile, action=Action.objects.get(key=key))
    return profile


def assign_profile(user, profile, sector=None, relation=None):
    organization = profile.organization
    if sector is not None:
        scope = ScopeService.sector_scope(sector)
    elif relation is not None:
        scope = ScopeService.relation_scope(organization, relation)
    else:
        scope = ScopeService.organization_scope(organization)

    return UserProfile.objects.create(
        organization=organization, user=user, profile=profile, scope=scope
    )
