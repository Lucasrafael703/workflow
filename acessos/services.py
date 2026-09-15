"""Motor de autorização da LPS.

Responde à pergunta central do documento 05: **quem pode fazer o quê, onde e
por quê?** Uma permissão nunca é global: ela vale dentro de um escopo
(organização, empresa, setor, obra, centro de custo ou uma relação com o
objeto), e o motor sempre sabe dizer de onde ela veio.

    SUJEITO + AÇÃO + ESCOPO + ORIGEM = AUTORIZAÇÃO EXPLICÁVEL
"""

from dataclasses import dataclass

from django.db import transaction

from audit.models import AuditLog

from .models import Action, Profile, Scope, UserAction, UserProfile


class AuthorizationError(Exception):
    """Levantada quando a ação é negada. Views traduzem em mensagem ou 403."""


@dataclass(frozen=True)
class Grant:
    """Uma concessão que autoriza a ação, com a origem que a explica."""

    action_key: str
    scope: Scope
    origin_type: str  # "perfil" ou "concessao_direta"
    origin_id: int
    origin_name: str

    @property
    def explanation(self):
        if self.origin_type == "perfil":
            return f"Perfil: {self.origin_name} · Escopo: {self.scope.label}"
        return f"Concessão direta · Escopo: {self.scope.label}"


# ---------------------------------------------------------------------------
# Resolução do recurso: de qual empresa/setor/obra este objeto faz parte?
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResourceContext:
    """O endereço de um objeto dentro da estrutura da organização.

    É contra este endereço que um escopo é testado. Manter a resolução em um
    único lugar evita que cada tela invente sua própria regra.
    """

    organization_id: int = None
    company_id: int = None
    sector_id: int = None
    site_id: int = None
    cost_center_id: int = None
    owner_id: int = None
    executor_ids: frozenset = frozenset()
    # Recurso cujo endereço não pôde ser resolvido nega tudo. Preferimos
    # falhar fechado a deixar um modelo desconhecido passar pelo teto do tenant.
    unresolved: bool = False

    @classmethod
    def for_new(cls, organization, company=None, sector=None, site=None, cost_center=None, owner=None):
        """Endereço de algo que ainda vai existir.

        Criar não tem objeto para inspecionar, mas tem contexto: sem isto, uma
        concessão por setor ou empresa nunca autorizaria uma criação, e a
        organização acabaria concedendo tudo no escopo mais amplo.
        """
        return cls(
            organization_id=getattr(organization, "id", organization),
            company_id=getattr(company, "id", None),
            sector_id=getattr(sector, "id", None),
            site_id=getattr(site, "id", None),
            cost_center_id=getattr(cost_center, "id", None),
            owner_id=getattr(owner, "id", None),
        )

    @classmethod
    def of(cls, resource):
        if resource is None:
            return cls()

        if isinstance(resource, cls):
            return resource

        model_name = resource._meta.model_name

        if model_name in {"deadlineproposal", "deadlineconflict"}:
            # Não possuem organização própria: o endereço vem da tarefa.
            return cls.of(resource.task)

        if model_name == "task":
            activity = resource.activity
            return cls(
                organization_id=activity.organization_id,
                company_id=activity.company_id,
                sector_id=resource.sector_id,
                site_id=activity.site_id,
                cost_center_id=activity.cost_center_id,
                owner_id=activity.owner_id,
                executor_ids=frozenset(
                    resource.executors.filter(removed_at__isnull=True).values_list("user_id", flat=True)
                ),
            )

        if model_name == "activity":
            return cls(
                organization_id=resource.organization_id,
                company_id=resource.company_id,
                site_id=resource.site_id,
                cost_center_id=resource.cost_center_id,
                owner_id=resource.owner_id,
            )

        if model_name == "sector":
            return cls(organization_id=resource.organization_id, sector_id=resource.pk)

        if model_name == "queueentry":
            activity = resource.task.activity
            return cls(
                organization_id=resource.sector.organization_id,
                company_id=activity.company_id,
                sector_id=resource.sector_id,
                site_id=activity.site_id,
                cost_center_id=activity.cost_center_id,
                owner_id=activity.owner_id,
                executor_ids=frozenset(
                    resource.task.executors.filter(removed_at__isnull=True).values_list(
                        "user_id", flat=True
                    )
                ),
            )

        if model_name == "company":
            return cls(organization_id=resource.organization_id, company_id=resource.pk)

        if model_name == "site":
            return cls(
                organization_id=resource.organization_id,
                company_id=resource.company_id,
                site_id=resource.pk,
            )

        if model_name == "costcenter":
            return cls(organization_id=resource.organization_id, cost_center_id=resource.pk)

        organization_id = getattr(resource, "organization_id", None)
        if organization_id is None:
            # Modelo que o motor não sabe endereçar: nega, em vez de deixar
            # passar pelo teto da organização.
            return cls(unresolved=True)
        return cls(organization_id=organization_id)


# Alterar um vínculo de setor invalida todos os caches em memória: o contador
# é comparado com o que foi guardado junto do cache.
_SECTOR_CACHE_EPOCH = [0]


def invalidate_sector_cache():
    """Descarta os caches de participação. Chamado por signal em accounts."""
    _SECTOR_CACHE_EPOCH[0] += 1


def _sector_memberships(user):
    """Setores do usuário e quais deles gerencia, em uma única consulta.

    Memoizado na instância do usuário porque o motor avalia vários escopos por
    página, e esta é a consulta mais repetida.
    """
    epoch = _SECTOR_CACHE_EPOCH[0]
    cached = getattr(user, "_lps_sector_memberships", None)
    if cached is not None and cached[0] == epoch:
        return cached[1]

    from accounts.models import UserSector

    member, managed = set(), set()
    rows = UserSector.objects.filter(user=user, removed_at__isnull=True).values_list(
        "sector_id", "role"
    )
    for sector_id, role in rows:
        member.add(sector_id)
        if role == UserSector.Role.GESTOR:
            managed.add(sector_id)

    value = (member, managed)
    try:
        user._lps_sector_memberships = (epoch, value)
    except AttributeError:  # pragma: no cover - usuário anônimo
        pass
    return value


def _user_sector_ids(user):
    return _sector_memberships(user)[0]


def _managed_sector_ids(user):
    return _sector_memberships(user)[1]


def scope_contains(scope, context, user):
    """O escopo cobre este recurso? (Regras 08 §28, passo 4.)"""
    if context.unresolved:
        return False

    if scope.type == Scope.Type.ORGANIZACAO:
        return True

    if scope.type == Scope.Type.EMPRESA:
        return context.company_id is not None and context.company_id == scope.company_id

    if scope.type == Scope.Type.SETOR:
        return context.sector_id is not None and context.sector_id == scope.sector_id

    if scope.type == Scope.Type.OBRA:
        return context.site_id is not None and context.site_id == scope.site_id

    if scope.type == Scope.Type.CENTRO_CUSTO:
        return context.cost_center_id is not None and context.cost_center_id == scope.cost_center_id

    if scope.type == Scope.Type.RELACIONAL:
        if scope.relation == Scope.Relation.MINHAS_ATIVIDADES:
            return context.owner_id == user.id
        if scope.relation == Scope.Relation.MINHAS_TAREFAS:
            return user.id in context.executor_ids
        if scope.relation == Scope.Relation.MEUS_SETORES:
            return context.sector_id in _user_sector_ids(user)
        if scope.relation == Scope.Relation.SETORES_GERENCIADOS:
            return context.sector_id in _managed_sector_ids(user)

    return False


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------


class AuthorizationService:
    @staticmethod
    def _organization_of(user):
        profile = getattr(user, "profile", None)
        return getattr(profile, "organization_id", None)

    @staticmethod
    def grants_for(user, action_key, resource=None):
        """Todas as concessões que autorizam a ação sobre o recurso.

        Vazio significa negado — a LPS nega por padrão (doc 05 §29).
        """
        if not getattr(user, "is_authenticated", False) or not user.is_active:
            return []

        user_organization_id = AuthorizationService._organization_of(user)
        if user_organization_id is None:
            return []

        context = ResourceContext.of(resource)
        # Organização é o limite máximo: nada atravessa o tenant (doc 05 §43).
        if context.organization_id is not None and context.organization_id != user_organization_id:
            return []

        found = []

        assignments = (
            UserProfile.objects.filter(
                user=user,
                is_active=True,
                profile__is_active=True,
                scope__is_active=True,
                profile__profile_actions__action__key=action_key,
                profile__profile_actions__action__is_active=True,
            )
            .select_related("profile", "scope", "scope__company", "scope__sector", "scope__site", "scope__cost_center")
            .distinct()
        )
        for assignment in assignments:
            if scope_contains(assignment.scope, context, user):
                found.append(
                    Grant(
                        action_key=action_key,
                        scope=assignment.scope,
                        origin_type="perfil",
                        origin_id=assignment.profile_id,
                        origin_name=assignment.profile.name,
                    )
                )

        direct = (
            UserAction.objects.filter(
                user=user, is_active=True, action__key=action_key, action__is_active=True, scope__is_active=True
            )
            .select_related("action", "scope", "scope__company", "scope__sector", "scope__site", "scope__cost_center")
        )
        for grant in direct:
            if scope_contains(grant.scope, context, user):
                found.append(
                    Grant(
                        action_key=action_key,
                        scope=grant.scope,
                        origin_type="concessao_direta",
                        origin_id=grant.pk,
                        origin_name=grant.action.name,
                    )
                )

        return found

    @staticmethod
    def can(user, action_key, resource=None):
        """Permitido? Superusuário do Django administra a plataforma e passa direto."""
        if AuthorizationService.is_platform_admin(user):
            return True
        return bool(AuthorizationService.grants_for(user, action_key, resource))

    @staticmethod
    def require(user, action_key, resource=None, message=None):
        if not AuthorizationService.can(user, action_key, resource):
            action = Action.objects.filter(key=action_key).first()
            label = action.name.lower() if action else action_key
            raise AuthorizationError(message or f"Você não possui autorização para: {label}.")

    @staticmethod
    def is_platform_admin(user):
        """Operador da plataforma: atravessa o motor, mas sempre de forma visível."""
        return bool(getattr(user, "is_superuser", False)) and user.is_active

    @staticmethod
    def explain(user, action_key, resource=None):
        """Por que esta pessoa pode fazer isto? (doc 05 §31, doc 08 §29.)"""
        reasons = [
            grant.explanation
            for grant in AuthorizationService.grants_for(user, action_key, resource)
        ]
        if AuthorizationService.is_platform_admin(user):
            reasons.insert(0, "Administrador da plataforma")
        return reasons

    @staticmethod
    def effective_actions(user):
        """Ações efetivas do usuário com a origem de cada uma.

        Alimenta a tela do usuário e o relatório de segurança (doc 05 §37, §40).
        """
        if not getattr(user, "is_authenticated", False):
            return []

        rows = []
        assignments = (
            UserProfile.objects.filter(user=user, is_active=True, profile__is_active=True)
            .select_related("profile", "scope")
            .prefetch_related("profile__profile_actions__action")
        )
        for assignment in assignments:
            for profile_action in assignment.profile.profile_actions.all():
                if not profile_action.action.is_active:
                    continue
                rows.append(
                    {
                        "action": profile_action.action,
                        "scope": assignment.scope,
                        "origin_type": "perfil",
                        "origin_name": assignment.profile.name,
                    }
                )

        direct = UserAction.objects.filter(user=user, is_active=True, action__is_active=True).select_related(
            "action", "scope"
        )
        for grant in direct:
            rows.append(
                {
                    "action": grant.action,
                    "scope": grant.scope,
                    "origin_type": "concessao_direta",
                    "origin_name": "Concessão direta",
                }
            )

        return sorted(rows, key=lambda row: (row["action"].group_id, row["action"].key))

    @staticmethod
    def has_unrestricted_access(user):
        """O acesso irrestrito do operador da plataforma precisa ficar visível
        nas telas de segurança, em vez de parecer "nenhuma permissão"."""
        return AuthorizationService.is_platform_admin(user)

    @staticmethod
    def can_anywhere(user, action_key):
        """A pessoa pode esta ação em algum lugar?

        Útil para abrir uma tela que lista vários setores: o conteúdo de cada
        um continua sendo filtrado pelo escopo.
        """
        if AuthorizationService.is_platform_admin(user):
            return True
        if AuthorizationService.can(user, action_key):
            return True
        return bool(AuthorizationService.accessible_sector_ids(user, action_key))

    @staticmethod
    def accessible_sector_ids(user, action_key):
        """Setores em que o usuário pode executar a ação.

        Permite filtrar listas sem testar escopo item a item.
        """
        from core.models import Sector

        organization_id = AuthorizationService._organization_of(user)
        if organization_id is None:
            return set()

        sector_ids = set(
            Sector.objects.filter(organization_id=organization_id, is_active=True).values_list(
                "id", flat=True
            )
        )
        if AuthorizationService.is_platform_admin(user):
            return sector_ids

        # Uma passada pelos escopos concedidos, em vez de uma consulta por setor.
        member_sectors, managed_sectors = _sector_memberships(user)
        accessible = set()

        for scope in AuthorizationService._scopes_granting(user, action_key):
            if scope.type == Scope.Type.ORGANIZACAO:
                return sector_ids
            if scope.type == Scope.Type.SETOR and scope.sector_id in sector_ids:
                accessible.add(scope.sector_id)
            elif scope.type == Scope.Type.RELACIONAL:
                if scope.relation == Scope.Relation.MEUS_SETORES:
                    accessible |= member_sectors & sector_ids
                elif scope.relation == Scope.Relation.SETORES_GERENCIADOS:
                    accessible |= managed_sectors & sector_ids

        return accessible

    @staticmethod
    def _scopes_granting(user, action_key):
        """Escopos ativos que concedem a ação, por perfil ou concessão direta."""
        from_profiles = Scope.objects.filter(
            is_active=True,
            user_profiles__user=user,
            user_profiles__is_active=True,
            user_profiles__profile__is_active=True,
            user_profiles__profile__profile_actions__action__key=action_key,
            user_profiles__profile__profile_actions__action__is_active=True,
        )
        from_direct = Scope.objects.filter(
            is_active=True,
            user_actions__user=user,
            user_actions__is_active=True,
            user_actions__action__key=action_key,
            user_actions__action__is_active=True,
        )
        return (from_profiles | from_direct).distinct()


class AccessService:
    """Administração de perfis, atribuições e concessões.

    Toda alteração aqui muda o que alguém pode fazer, então tudo é auditado
    (Regras 05 §41, doc 08 §30).
    """

    @staticmethod
    def _audit(changed_by, action, target_user=None, description="", before="", after=""):
        from audit.services import AuditService

        AuditService.log(
            user=changed_by,
            action=action,
            target_user=target_user,
            old_value=before,
            new_value=after,
            reason=description,
        )

    @staticmethod
    @transaction.atomic
    def create_profile(organization, name, created_by, description=""):
        from core.services import CadastroError

        name = (name or "").strip()
        if not name:
            raise CadastroError("Informe o nome do perfil.")
        if Profile.objects.filter(organization=organization, name__iexact=name).exists():
            raise CadastroError(f"Já existe um perfil chamado “{name}” nesta organização.")

        profile = Profile.objects.create(
            organization=organization, name=name, description=description, created_by=created_by
        )
        AccessService._audit(
            created_by, AuditLog.Action.PROFILE_CREATED, description=f"Perfil criado: {name}", after=name
        )
        return profile

    @staticmethod
    @transaction.atomic
    def update_profile(profile, name, changed_by, description=""):
        from core.services import CadastroError

        name = (name or "").strip()
        if not name:
            raise CadastroError("Informe o nome do perfil.")
        if (
            Profile.objects.filter(organization=profile.organization, name__iexact=name)
            .exclude(pk=profile.pk)
            .exists()
        ):
            raise CadastroError(f"Já existe um perfil chamado “{name}” nesta organização.")

        before = profile.name
        profile.name = name
        profile.description = description
        profile.save(update_fields=["name", "description"])
        AccessService._audit(
            changed_by,
            AuditLog.Action.PROFILE_UPDATED,
            description=f"Perfil alterado: {before} → {name}",
            before=before,
            after=name,
        )
        return profile

    @staticmethod
    @transaction.atomic
    def set_profile_actions(profile, granted_ids, visible_ids, changed_by):
        """Marca e desmarca ações de um perfil (Regras 08 §21).

        Só mexe no que estava visível na tela: o que ficou fora do filtro
        permanece como estava.
        """
        from .models import ProfileAction

        current = set(
            ProfileAction.objects.filter(profile=profile, action_id__in=visible_ids).values_list(
                "action_id", flat=True
            )
        )
        to_add = set(granted_ids) - current
        to_remove = current - set(granted_ids)

        for action_id in to_add:
            ProfileAction.objects.get_or_create(
                profile=profile, action_id=action_id, defaults={"created_by": changed_by}
            )
        if to_remove:
            ProfileAction.objects.filter(profile=profile, action_id__in=to_remove).delete()

        if to_add or to_remove:
            added = list(Action.objects.filter(id__in=to_add).values_list("key", flat=True))
            removed = list(Action.objects.filter(id__in=to_remove).values_list("key", flat=True))
            AccessService._audit(
                changed_by,
                AuditLog.Action.PROFILE_ACTIONS_CHANGED,
                description=f"Ações do perfil {profile.name} alteradas",
                before=", ".join(removed),
                after=", ".join(added),
            )
        return profile

    @staticmethod
    def _resolve_scope(organization, scope_type, sector, company, site, cost_center, relation):
        from core.services import CadastroError

        required = {
            Scope.Type.SETOR: sector,
            Scope.Type.EMPRESA: company,
            Scope.Type.OBRA: site,
            Scope.Type.CENTRO_CUSTO: cost_center,
            Scope.Type.RELACIONAL: relation,
        }
        if scope_type in required and not required[scope_type]:
            raise CadastroError("Informe onde esta autorização vale.")

        # O alvo do escopo precisa ser da mesma organização: um escopo que
        # aponta para fora do tenant não pode sequer ser gravado (doc 05 §43).
        for target in (sector, company, site, cost_center):
            if target is not None and target.organization_id != organization.id:
                raise CadastroError("O escopo informado pertence a outra organização.")

        return ScopeService.get_or_create(
            organization,
            scope_type,
            company=company if scope_type == Scope.Type.EMPRESA else None,
            sector=sector if scope_type == Scope.Type.SETOR else None,
            site=site if scope_type == Scope.Type.OBRA else None,
            cost_center=cost_center if scope_type == Scope.Type.CENTRO_CUSTO else None,
            relation=relation if scope_type == Scope.Type.RELACIONAL else "",
        )

    @staticmethod
    @transaction.atomic
    def assign_profile(
        user, profile, scope_type, granted_by, sector=None, company=None, site=None, cost_center=None, relation=""
    ):
        from core.services import CadastroError

        organization = profile.organization
        if user.profile.organization_id != organization.id:
            raise CadastroError("Usuário e perfil pertencem a organizações diferentes.")

        scope = AccessService._resolve_scope(
            organization, scope_type, sector, company, site, cost_center, relation
        )
        assignment, created = UserProfile.objects.get_or_create(
            user=user,
            profile=profile,
            scope=scope,
            is_active=True,
            defaults={"organization": organization, "created_by": granted_by},
        )
        if created:
            AccessService._audit(
                granted_by,
                AuditLog.Action.PROFILE_ASSIGNED,
                target_user=user,
                description=f"Perfil {profile.name} atribuído em {scope.label}",
                after=f"{profile.name} / {scope.label}",
            )
        return assignment

    @staticmethod
    @transaction.atomic
    def revoke_profile(assignment, changed_by):
        assignment.is_active = False
        assignment.save(update_fields=["is_active"])
        AccessService._audit(
            changed_by,
            AuditLog.Action.PROFILE_REVOKED,
            target_user=assignment.user,
            description=f"Perfil {assignment.profile.name} removido em {assignment.scope.label}",
            before=f"{assignment.profile.name} / {assignment.scope.label}",
        )
        return assignment

    @staticmethod
    @transaction.atomic
    def grant_action(
        user, action, scope_type, granted_by, sector=None, company=None, site=None, cost_center=None, relation=""
    ):
        organization = user.profile.organization
        scope = AccessService._resolve_scope(
            organization, scope_type, sector, company, site, cost_center, relation
        )
        grant, created = UserAction.objects.get_or_create(
            user=user,
            action=action,
            scope=scope,
            is_active=True,
            defaults={"organization": organization, "created_by": granted_by},
        )
        if created:
            AccessService._audit(
                granted_by,
                AuditLog.Action.ACTION_GRANTED,
                target_user=user,
                description=f"Concessão direta {action.key} em {scope.label}",
                after=f"{action.key} / {scope.label}",
            )
        return grant

    @staticmethod
    @transaction.atomic
    def revoke_action(grant, changed_by):
        grant.is_active = False
        grant.save(update_fields=["is_active"])
        AccessService._audit(
            changed_by,
            AuditLog.Action.ACTION_REVOKED,
            target_user=grant.user,
            description=f"Concessão direta {grant.action.key} removida em {grant.scope.label}",
            before=f"{grant.action.key} / {grant.scope.label}",
        )
        return grant

    @staticmethod
    @transaction.atomic
    def sync_user_sectors(user, sectors, managed_sectors, changed_by):
        """Ajusta a participação do usuário nos setores, com o papel de cada um."""
        from accounts.models import UserSector
        from core.services import UserSectorService

        selected = set(sectors)
        managed = set(managed_sectors) & selected
        current = set(
            UserSector.objects.filter(user=user, removed_at__isnull=True).values_list(
                "sector_id", flat=True
            )
        )

        for sector in selected:
            role = UserSector.Role.GESTOR if sector in managed else UserSector.Role.MEMBRO
            UserSectorService.add(user, sector, role=role)

        for sector_id in current - {s.id for s in selected}:
            from core.models import Sector

            UserSectorService.remove(user, Sector.objects.get(pk=sector_id))

        AccessService._audit(
            changed_by,
            AuditLog.Action.SECTORS_CHANGED,
            target_user=user,
            description="Setores do usuário atualizados",
            after=", ".join(sorted(s.name for s in selected)),
        )


class ScopeService:
    @staticmethod
    @transaction.atomic
    def get_or_create(organization, type, company=None, sector=None, site=None, cost_center=None, relation=""):
        """Escopos são reutilizáveis: a mesma combinação não deve virar linhas repetidas."""
        scope, _ = Scope.objects.get_or_create(
            organization=organization,
            type=type,
            company=company,
            sector=sector,
            site=site,
            cost_center=cost_center,
            relation=relation or "",
            defaults={"is_active": True},
        )
        return scope

    @staticmethod
    def organization_scope(organization):
        return ScopeService.get_or_create(organization, Scope.Type.ORGANIZACAO)

    @staticmethod
    def sector_scope(sector):
        return ScopeService.get_or_create(sector.organization, Scope.Type.SETOR, sector=sector)

    @staticmethod
    def relation_scope(organization, relation):
        return ScopeService.get_or_create(organization, Scope.Type.RELACIONAL, relation=relation)
