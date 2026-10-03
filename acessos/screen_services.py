"""Serviços das telas de acesso: grupos, usuários e menu em termos de **tela + nível**.

Tudo aqui se apoia no motor que já existe (`Profile`, `UserProfile`, `UserAction`, `Scope`) e
no mapa de `screens.py`. Não há modelo novo:

- **Grupo de acesso** = `Profile`; as telas do grupo viram `ProfileAction`;
- **Equipe** = `accounts.UserSector` (já tratada por `AccessService.sync_user_sectors`);
- **Vale para** = `Scope` da atribuição do grupo;
- **Ajuste individual** = `UserAction` (concessão direta) para aquela pessoa;
- **Menu** = o nível de cada tela, lido das ações efetivas da pessoa.

Duas regras de segurança atravessam o arquivo: só se reescreve o que a pessoa **mudou** na
interface (o resto do perfil, inclusive ações avançadas, fica como estava) e ninguém consegue se
trancar para fora da própria tela de grupos.
"""

from django.db import transaction
from django.db.models import Count, Q

from audit.models import AuditLog

from . import catalog, screens
from .models import Action, Profile, ProfileAction, Scope, UserAction, UserProfile
from .screens import NONE, ORG_ONLY_ACTIONS, SCREENS
from .services import AccessService, AuthorizationService, ScopeService


# ---------------------------------------------------------------------------
# Níveis lidos do banco
# ---------------------------------------------------------------------------


def profile_action_keys(profile):
    """Chaves das ações ativas de um perfil."""
    return set(
        ProfileAction.objects.filter(profile=profile, action__is_active=True).values_list("action__key", flat=True)
    )


def profile_levels(profile):
    return screens.levels_from_actions(profile_action_keys(profile))


def keys_by_profile(profile_ids):
    """{perfil: ações ativas} de vários perfis, em uma consulta."""
    result = {pk: set() for pk in profile_ids}
    rows = ProfileAction.objects.filter(profile_id__in=profile_ids, action__is_active=True).values_list(
        "profile_id", "action__key"
    )
    for profile_id, key in rows:
        result[profile_id].add(key)
    return result


def advanced_summary(keys):
    """(ações avançadas que o perfil mantém, ações fora de qualquer tela).

    Nenhuma das duas aparece nos botões de nível: a primeira é preservada quando o nível não muda,
    a segunda só existe em perfis montados à mão na matriz de permissões.
    """
    extras = {key for screen in SCREENS for key in screen.extra} & keys
    mapped = {key for screen in SCREENS for key in screen.all_actions}
    return len(extras), len(keys - mapped)


def reach_keys(user):
    """(ações em qualquer escopo, ações no escopo da organização inteira) da pessoa.

    O menu precisa saber "ela pode isto em algum lugar?" sem testar recurso por recurso. Ações que
    a tela só verifica sobre a organização inteira (`ORG_ONLY_ACTIONS`) contam só se vierem de um
    escopo de organização; senão o item apareceria e a tela daria 403.
    """
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return set(), set()

    from_profiles = ProfileAction.objects.filter(
        profile__is_active=True,
        profile__assignments__user=user,
        profile__assignments__is_active=True,
        profile__assignments__scope__is_active=True,
        action__is_active=True,
    ).values_list("action__key", "profile__assignments__scope__type")
    from_grants = UserAction.objects.filter(
        user=user, is_active=True, scope__is_active=True, action__is_active=True
    ).values_list("action__key", "scope__type")

    anywhere, organization = set(), set()
    for key, scope_type in list(from_profiles) + list(from_grants):
        anywhere.add(key)
        if scope_type == Scope.Type.ORGANIZACAO:
            organization.add(key)
    return anywhere, organization


def menu_levels(user):
    """Nível de cada tela para a pessoa — o que o menu lateral usa."""
    if AuthorizationService.is_platform_admin(user):
        return screens.full_levels()

    anywhere, organization = reach_keys(user)
    levels = {}
    for screen in SCREENS:
        effective = {
            key
            for key in (*screen.view, *screen.edit)
            if key in (organization if key in ORG_ONLY_ACTIONS else anywhere)
        }
        levels[screen.key] = screens.level_from_actions(screen, effective)
    return levels


# ---------------------------------------------------------------------------
# Grupos
# ---------------------------------------------------------------------------


class GroupError(Exception):
    """Pedido inválido na administração de grupos (mensagem já em português)."""


class GroupService:
    @staticmethod
    def groups(organization, include_inactive=False):
        queryset = Profile.objects.filter(organization=organization)
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        return queryset.annotate(
            user_count=Count(
                "assignments__user",
                filter=Q(assignments__is_active=True, assignments__user__is_active=True),
                distinct=True,
            )
        ).order_by("name")

    @staticmethod
    def user_count(profile):
        return (
            UserProfile.objects.filter(profile=profile, is_active=True, user__is_active=True)
            .values("user")
            .distinct()
            .count()
        )

    @staticmethod
    def changes_for(profile, desired):
        """(ações a conceder, ações a retirar, telas alteradas) para o pedido `desired`.

        Telas cujo nível não mudou ficam fora: o que o perfil tem de avançado nelas permanece.
        """
        current = profile_action_keys(profile)
        current_levels = screens.levels_from_actions(current)
        add, remove, changed = set(), set(), []
        for screen in SCREENS:
            have = current_levels[screen.key]
            want = screens.normalize_level(screen, desired.get(screen.key, have))
            if want == have:
                continue
            changed.append(screen.key)
            keep = screens.actions_for_level(screen, want)
            add |= keep - current
            remove |= (screen.all_actions - keep) & current
        return add, remove, changed

    @staticmethod
    def new_keys(profile, desired):
        add, remove, _ = GroupService.changes_for(profile, desired)
        return (profile_action_keys(profile) - remove) | add

    @staticmethod
    def would_lock_out(user, profile, desired):
        """Salvar tiraria de `user` o poder de administrar grupos?"""
        if AuthorizationService.is_platform_admin(user):
            return False
        needed = catalog.SEGURANCA_GERIR_AUTORIZACOES

        organization_scope = Q(scope__type=Scope.Type.ORGANIZACAO)
        others = (
            ProfileAction.objects.filter(
                profile__is_active=True,
                profile__assignments__user=user,
                profile__assignments__is_active=True,
                profile__assignments__scope__is_active=True,
                profile__assignments__scope__type=Scope.Type.ORGANIZACAO,
                action__key=needed,
                action__is_active=True,
            )
            .exclude(profile=profile)
            .exists()
        ) or UserAction.objects.filter(
            organization_scope, user=user, is_active=True, action__key=needed, action__is_active=True
        ).exists()
        if others:
            return False

        uses_profile = UserProfile.objects.filter(
            user=user, profile=profile, is_active=True, scope__type=Scope.Type.ORGANIZACAO
        ).exists()
        if not uses_profile:
            return False
        return needed not in GroupService.new_keys(profile, desired)

    @staticmethod
    @transaction.atomic
    def save_levels(profile, desired, changed_by):
        """Grava as telas do grupo e devolve (quantas ações mudaram, telas alteradas)."""
        if GroupService.would_lock_out(changed_by, profile, desired):
            raise GroupError(
                "Você perderia o acesso a Grupos de acesso com esta mudança. "
                "Mantenha “Grupos de acesso” em Editar neste grupo, ou peça a outra pessoa para alterá-lo."
            )

        add, remove, changed = GroupService.changes_for(profile, desired)
        if not changed:
            return 0, []

        ids = dict(Action.objects.filter(key__in=add | remove, is_active=True).values_list("key", "id"))
        granted_ids = {ids[key] for key in add if key in ids}
        visible_ids = granted_ids | {ids[key] for key in remove if key in ids}
        AccessService.set_profile_actions(profile, granted_ids, visible_ids, changed_by)
        return len(add) + len(remove), changed

    @staticmethod
    @transaction.atomic
    def create(organization, name, description, created_by, copy_from=None):
        """Cria um grupo em branco ou a partir de outro (as telas são copiadas)."""
        from core.services import CadastroError

        try:
            profile = AccessService.create_profile(organization, name, created_by, description=description)
        except CadastroError as exc:
            raise GroupError(str(exc)) from exc

        if copy_from is not None:
            ids = list(
                ProfileAction.objects.filter(profile=copy_from, action__is_active=True).values_list(
                    "action_id", flat=True
                )
            )
            AccessService.set_profile_actions(profile, set(ids), set(ids), created_by)
        return profile

    @staticmethod
    @transaction.atomic
    def rename(profile, name, description, changed_by):
        from core.services import CadastroError

        try:
            return AccessService.update_profile(profile, name, changed_by, description=description)
        except CadastroError as exc:
            raise GroupError(str(exc)) from exc

    @staticmethod
    @transaction.atomic
    def inactivate(profile, changed_by):
        """Inativa o grupo — só quando ninguém depende dele (inativo, ele deixa de conceder)."""
        in_use = GroupService.user_count(profile)
        if in_use:
            raise GroupError(
                f"{in_use} pessoa{'s' if in_use != 1 else ''} ainda "
                f"{'usam' if in_use != 1 else 'usa'} este grupo. Mude o grupo delas antes de inativar."
            )
        profile.is_active = False
        profile.save(update_fields=["is_active"])
        AccessService._audit(
            changed_by,
            AuditLog.Action.PROFILE_UPDATED,
            description=f"Grupo inativado: {profile.name}",
            before="ativo",
            after="inativo",
        )
        return profile

    @staticmethod
    def comparison(organization):
        """Telas em linhas e grupos em colunas, para comparar de uma vez."""
        groups = list(GroupService.groups(organization))
        levels_by_group = {group.pk: profile_levels(group) for group in groups}
        sections = []
        for key, name, section_screens in screens.sections():
            rows = []
            for screen in section_screens:
                cells = [levels_by_group[group.pk][screen.key] for group in groups]
                rows.append({"screen": screen, "cells": cells, "differs": len(set(cells)) > 1})
            sections.append({"key": key, "name": name, "rows": rows})
        return {"groups": groups, "sections": sections}


# ---------------------------------------------------------------------------
# Pessoas
# ---------------------------------------------------------------------------

SCOPE_ORG = "org"
SCOPE_TEAMS = "teams"
SCOPE_MANAGED = "managed"
SCOPE_CUSTOM = "custom"

SCOPE_CHOICES = [
    (SCOPE_TEAMS, "As equipes da pessoa"),
    (SCOPE_MANAGED, "As equipes que a pessoa gerencia"),
    (SCOPE_ORG, "A organização inteira"),
]


def scope_kind(scope):
    if scope.type == Scope.Type.ORGANIZACAO:
        return SCOPE_ORG
    if scope.type == Scope.Type.RELACIONAL and scope.relation == Scope.Relation.MEUS_SETORES:
        return SCOPE_TEAMS
    if scope.type == Scope.Type.RELACIONAL and scope.relation == Scope.Relation.SETORES_GERENCIADOS:
        return SCOPE_MANAGED
    return SCOPE_CUSTOM


def scope_for_kind(organization, kind):
    if kind == SCOPE_ORG:
        return ScopeService.organization_scope(organization)
    if kind == SCOPE_MANAGED:
        return ScopeService.relation_scope(organization, Scope.Relation.SETORES_GERENCIADOS)
    return ScopeService.relation_scope(organization, Scope.Relation.MEUS_SETORES)


def default_scope_kind(levels):
    """Sugestão de "Vale para": organização inteira se alguma tela só funciona assim."""
    for screen in SCREENS:
        if screens.needs_organization(screen, levels.get(screen.key, NONE)):
            return SCOPE_ORG
    return SCOPE_TEAMS


def active_assignments(user):
    return list(
        UserProfile.objects.filter(user=user, is_active=True, profile__is_active=True)
        .select_related("profile", "scope")
        .order_by("created_at", "pk")
    )


class UserAccessService:
    @staticmethod
    def state(user):
        """O que a tela da pessoa mostra: grupo, "vale para", níveis e ajustes individuais."""
        assignments = active_assignments(user)
        assignment = assignments[0] if len(assignments) == 1 else None
        group_keys = set()
        for item in assignments:
            group_keys |= profile_action_keys(item.profile)
        group_levels = screens.levels_from_actions(group_keys)

        direct_keys = UserAccessService._direct_keys(user, assignment)
        effective = screens.levels_from_actions(group_keys | direct_keys)
        individual = {
            screen.key: effective[screen.key] != group_levels[screen.key] for screen in SCREENS
        }
        return {
            "assignments": assignments,
            "assignment": assignment,
            "complex": len(assignments) > 1,
            "group": assignment.profile if assignment else None,
            "scope_kind": scope_kind(assignment.scope) if assignment else None,
            "group_levels": group_levels,
            "levels": effective,
            "individual": individual,
        }

    @staticmethod
    def _relevant_scopes(user, assignment):
        """Escopos em que o formulário lê e grava ajustes individuais."""
        scopes = set(
            Scope.objects.filter(
                organization_id=user.profile.organization_id, type=Scope.Type.ORGANIZACAO
            ).values_list("pk", flat=True)
        )
        if assignment is not None:
            scopes.add(assignment.scope_id)
        return scopes

    @staticmethod
    def _direct_rows(user, assignment):
        return UserAction.objects.filter(
            user=user, is_active=True, action__is_active=True,
            scope_id__in=UserAccessService._relevant_scopes(user, assignment),
        ).select_related("action", "scope")

    @staticmethod
    def _direct_keys(user, assignment):
        if user.profile.organization_id is None:
            return set()
        return {row.action.key for row in UserAccessService._direct_rows(user, assignment)}

    @staticmethod
    @transaction.atomic
    def apply(user, organization, group, kind, desired, changed_by):
        """Aplica grupo, "vale para" e ajustes individuais da pessoa.

        `desired` mapeia tela -> nível já escolhido na interface. Só telas cujo nível mudou em
        relação ao que a pessoa tem hoje são tocadas.
        """
        assignments = active_assignments(user)
        if len(assignments) > 1:
            raise GroupError(
                "Esta pessoa tem mais de um grupo atribuído. Ajuste em “Acessos avançados”."
            )
        if group is None:
            if assignments:
                AccessService.revoke_profile(assignments[0], changed_by)
            assignment = None
        else:
            current = assignments[0] if assignments else None
            # "Personalizado" (empresa, obra, setor fixo…) só se muda nos acessos avançados:
            # aqui o escopo que a pessoa já tem é mantido.
            if kind == SCOPE_CUSTOM and current is not None:
                scope = current.scope
            else:
                scope = scope_for_kind(organization, kind)
            if current is not None and (current.profile_id != group.pk or current.scope_id != scope.pk):
                AccessService.revoke_profile(current, changed_by)
                current = None
            if current is None:
                current = AccessService.assign_profile_to_scope(user, group, scope, changed_by)
            assignment = current

        group_keys = profile_action_keys(group) if group is not None else set()
        group_levels = screens.levels_from_actions(group_keys)
        rows = list(UserAccessService._direct_rows(user, assignment))
        held = {row.action.key for row in rows}
        shown = screens.levels_from_actions(group_keys | held)
        organization_scope = ScopeService.organization_scope(organization)
        base_scope = assignment.scope if assignment is not None else organization_scope

        for screen in SCREENS:
            want = screens.normalize_level(screen, desired.get(screen.key, shown[screen.key]))
            # Não existe "negar" no motor: abaixo do grupo não dá — o grupo vale.
            want = want if screens.rank(want) >= screens.rank(group_levels[screen.key]) else group_levels[screen.key]
            if want == shown[screen.key]:
                continue

            target = screens.actions_for_level(screen, want)
            if want == group_levels[screen.key]:
                target = set()
            else:
                target = set(target) - group_keys

            for row in rows:
                key = row.action.key
                if key in screen.all_actions and key not in target:
                    AccessService.revoke_action(row, changed_by)
            held_here = {row.action.key for row in rows if row.action.key in screen.all_actions}
            actions = {a.key: a for a in Action.objects.filter(key__in=target - held_here, is_active=True)}
            for key, action in actions.items():
                scope = organization_scope if key in ORG_ONLY_ACTIONS else base_scope
                AccessService.grant_action_to_scope(user, action, scope, changed_by)
        return assignment

    @staticmethod
    def overview(users):
        """Grupo(s), nº de telas e nº de ajustes individuais de cada pessoa, em poucas consultas."""
        users = list(users)
        ids = [user.pk for user in users]

        assignments_by_user = {}
        for item in UserProfile.objects.filter(
            user_id__in=ids, is_active=True, profile__is_active=True
        ).select_related("profile", "scope").order_by("created_at", "pk"):
            assignments_by_user.setdefault(item.user_id, []).append(item)

        profile_ids = {item.profile_id for items in assignments_by_user.values() for item in items}
        keys_by_profile = {}
        for profile_id, key in ProfileAction.objects.filter(
            profile_id__in=profile_ids, action__is_active=True
        ).values_list("profile_id", "action__key"):
            keys_by_profile.setdefault(profile_id, set()).add(key)

        direct_by_user = {}
        for user_id, key in UserAction.objects.filter(
            user_id__in=ids, is_active=True, action__is_active=True, scope__is_active=True
        ).values_list("user_id", "action__key"):
            direct_by_user.setdefault(user_id, set()).add(key)

        result = {}
        for user in users:
            items = assignments_by_user.get(user.pk, [])
            group_keys = set()
            for item in items:
                group_keys |= keys_by_profile.get(item.profile_id, set())
            direct = direct_by_user.get(user.pk, set())
            group_levels = screens.levels_from_actions(group_keys)
            levels = screens.levels_from_actions(group_keys | direct)
            if user.is_superuser:
                levels = screens.full_levels()
            individual = sum(
                1 for screen in SCREENS if screens.rank(levels[screen.key]) > screens.rank(group_levels[screen.key])
            ) if not user.is_superuser else 0
            result[user.pk] = {
                "groups": [item.profile for item in items],
                "levels": levels,
                "screens": screens.screens_count(levels),
                "individual": individual,
                "full": levels == screens.full_levels(),
            }
        return result


def invitation_pending(user):
    """Convite enviado e ainda não aceito: sem senha utilizável e nunca entrou."""
    return user.is_active and not user.has_usable_password() and user.last_login is None
