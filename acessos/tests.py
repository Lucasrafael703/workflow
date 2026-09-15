"""Testes de aceite do motor de autorização (Regras 05 §51, doc 08 §113)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import Company, CostCenter, Organization, Sector, Site

from . import catalog
from .models import Action, Scope, UserAction
from .services import AuthorizationService, ScopeService
from .testing import assign_profile, ensure_catalog, grant_action, grant_actions, make_profile

User = get_user_model()


class AuthorizationTestCase(TestCase):
    def setUp(self):
        ensure_catalog()
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Instaladora X")
        self.company = Company.objects.create(organization=self.org, name="Biasi Engenharia")
        self.comercial = Sector.objects.create(organization=self.org, name="Comercial")
        self.compras = Sector.objects.create(organization=self.org, name="Compras")

        self.paulo = self._user("paulo", self.org)
        self.ryan = self._user("ryan", self.org)
        self.externo = self._user("externo", self.other_org)

    def _user(self, username, organization):
        user = User.objects.create_user(username, password="x")
        user.profile.organization = organization
        user.profile.save()
        return user


class DefaultDenyTests(AuthorizationTestCase):
    def test_new_user_can_do_nothing(self):
        """Sem concessão válida, nega-se (doc 05 §28-29, §51.6)."""
        self.assertFalse(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.comercial))
        self.assertFalse(AuthorizationService.can(self.paulo, catalog.ATIVIDADE_CRIAR))

    def test_inactive_user_is_denied(self):
        grant_action(self.paulo, catalog.FILA_REORDENAR, sector=self.comercial)
        self.paulo.is_active = False
        self.paulo.save(update_fields=["is_active"])
        self.assertFalse(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.comercial))

    def test_user_without_organization_is_denied(self):
        orphan = User.objects.create_user("orfao", password="x")
        self.assertFalse(AuthorizationService.can(orphan, catalog.ATIVIDADE_CRIAR))


class ScopeTests(AuthorizationTestCase):
    def test_sector_scope_does_not_reach_another_sector(self):
        """§51.3 — mesmo perfil, escopos diferentes."""
        grant_action(self.paulo, catalog.FILA_REORDENAR, sector=self.comercial)

        self.assertTrue(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.comercial))
        self.assertFalse(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.compras))

    def test_organization_scope_reaches_every_sector(self):
        grant_action(self.paulo, catalog.FILA_REORDENAR, organization=self.org)
        self.assertTrue(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.comercial))
        self.assertTrue(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.compras))

    def test_two_users_same_profile_different_scopes(self):
        profile = make_profile(self.org, "Gestor de Setor", [catalog.FILA_REORDENAR])
        assign_profile(self.paulo, profile, sector=self.comercial)
        assign_profile(self.ryan, profile, sector=self.compras)

        self.assertTrue(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.comercial))
        self.assertFalse(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.compras))
        self.assertTrue(AuthorizationService.can(self.ryan, catalog.FILA_REORDENAR, self.compras))
        self.assertFalse(AuthorizationService.can(self.ryan, catalog.FILA_REORDENAR, self.comercial))

    def test_two_profiles_add_up(self):
        """§51.4 — perfis somam capacidades."""
        executor = make_profile(self.org, "Executor", [catalog.TAREFA_INICIAR])
        visualizador = make_profile(self.org, "Visualizador", [catalog.ATIVIDADE_VISUALIZAR])
        assign_profile(self.paulo, executor, sector=self.comercial)
        assign_profile(self.paulo, visualizador)

        self.assertTrue(AuthorizationService.can(self.paulo, catalog.TAREFA_INICIAR, self.comercial))
        self.assertTrue(AuthorizationService.can(self.paulo, catalog.ATIVIDADE_VISUALIZAR))

    def test_direct_grant_adds_an_exception(self):
        """§51.5 — concessão direta cobre a exceção."""
        profile = make_profile(self.org, "Orçamento", [catalog.TAREFA_INICIAR])
        assign_profile(self.paulo, profile, sector=self.comercial)
        self.assertFalse(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.comercial))

        grant_action(self.paulo, catalog.FILA_REORDENAR, sector=self.comercial)
        self.assertTrue(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.comercial))

    def test_company_scope(self):
        grant_action(
            self.paulo,
            catalog.ATIVIDADE_VISUALIZAR,
            organization=self.org,
            scope=ScopeService.get_or_create(self.org, Scope.Type.EMPRESA, company=self.company),
        )
        self.assertTrue(AuthorizationService.can(self.paulo, catalog.ATIVIDADE_VISUALIZAR, self.company))

    def test_inactive_scope_stops_granting(self):
        grant = grant_action(self.paulo, catalog.FILA_REORDENAR, sector=self.comercial)
        grant.scope.is_active = False
        grant.scope.save(update_fields=["is_active"])
        self.assertFalse(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.comercial))


class TenantIsolationTests(AuthorizationTestCase):
    def test_no_access_across_organizations(self):
        """§51.7 — organização é o limite máximo."""
        grant_action(self.externo, catalog.FILA_REORDENAR, organization=self.other_org)
        # Mesmo com a ação concedida na própria organização, o recurso alheio é negado.
        self.assertFalse(AuthorizationService.can(self.externo, catalog.FILA_REORDENAR, self.comercial))

    def test_organization_scope_of_another_tenant_does_not_leak(self):
        outsider_scope = ScopeService.organization_scope(self.other_org)
        UserAction.objects.create(
            organization=self.other_org,
            user=self.externo,
            action=Action.objects.get(key=catalog.ATIVIDADE_VISUALIZAR),
            scope=outsider_scope,
        )
        self.assertFalse(
            AuthorizationService.can(self.externo, catalog.ATIVIDADE_VISUALIZAR, self.comercial)
        )


class ExplainabilityTests(AuthorizationTestCase):
    def test_permission_explains_its_origin(self):
        """§51.11 — de onde veio esta permissão? (doc 05 §31.)"""
        profile = make_profile(self.org, "Gestor Comercial", [catalog.FILA_REORDENAR])
        assign_profile(self.paulo, profile, sector=self.comercial)

        reasons = AuthorizationService.explain(self.paulo, catalog.FILA_REORDENAR, self.comercial)
        self.assertEqual(len(reasons), 1)
        self.assertIn("Gestor Comercial", reasons[0])
        self.assertIn("Comercial", reasons[0])

    def test_direct_grant_is_distinguishable_from_profile(self):
        grant_action(self.paulo, catalog.FILA_REORDENAR, sector=self.comercial)
        reasons = AuthorizationService.explain(self.paulo, catalog.FILA_REORDENAR, self.comercial)
        self.assertIn("Concessão direta", reasons[0])

    def test_effective_actions_lists_origin_for_each(self):
        profile = make_profile(self.org, "Colaborador", [catalog.TAREFA_INICIAR])
        assign_profile(self.paulo, profile, sector=self.comercial)
        grant_action(self.paulo, catalog.FILA_REORDENAR, sector=self.compras)

        rows = AuthorizationService.effective_actions(self.paulo)
        by_key = {row["action"].key: row for row in rows}
        self.assertEqual(by_key[catalog.TAREFA_INICIAR]["origin_name"], "Colaborador")
        self.assertEqual(by_key[catalog.FILA_REORDENAR]["origin_type"], "concessao_direta")


class RelationalScopeTests(AuthorizationTestCase):
    def setUp(self):
        super().setUp()
        from activities.services import ActivityService, TaskService

        grant_action(self.paulo, catalog.ATIVIDADE_CRIAR, organization=self.org)
        grant_action(self.paulo, catalog.TAREFA_CRIAR, organization=self.org)
        self.activity = ActivityService.create_activity(
            organization=self.org, title="Minha atividade", owner=self.paulo, created_by=self.paulo
        )
        self.task = TaskService.create_task(
            self.activity, self.comercial, "Tarefa", created_by=self.paulo
        )

    def test_my_activities_scope(self):
        grant_action(
            self.ryan,
            catalog.ATIVIDADE_VISUALIZAR,
            organization=self.org,
            relation=Scope.Relation.MINHAS_ATIVIDADES,
        )
        # Ryan não é dono: a relação não o alcança.
        self.assertFalse(
            AuthorizationService.can(self.ryan, catalog.ATIVIDADE_VISUALIZAR, self.activity)
        )

        grant_action(
            self.paulo,
            catalog.ATIVIDADE_EDITAR,
            organization=self.org,
            relation=Scope.Relation.MINHAS_ATIVIDADES,
        )
        self.assertTrue(AuthorizationService.can(self.paulo, catalog.ATIVIDADE_EDITAR, self.activity))

    def test_my_sectors_scope_follows_membership(self):
        from accounts.models import UserSector

        grant_action(
            self.ryan,
            catalog.FILA_VISUALIZAR_COMPLETA,
            organization=self.org,
            relation=Scope.Relation.MEUS_SETORES,
        )
        self.assertFalse(
            AuthorizationService.can(self.ryan, catalog.FILA_VISUALIZAR_COMPLETA, self.comercial)
        )

        UserSector.objects.create(user=self.ryan, sector=self.comercial)
        self.assertTrue(
            AuthorizationService.can(self.ryan, catalog.FILA_VISUALIZAR_COMPLETA, self.comercial)
        )

    def test_managed_sectors_scope_requires_the_manager_role(self):
        from accounts.models import UserSector

        grant_action(
            self.ryan,
            catalog.FILA_REORDENAR,
            organization=self.org,
            relation=Scope.Relation.SETORES_GERENCIADOS,
        )
        membership = UserSector.objects.create(user=self.ryan, sector=self.comercial)
        self.assertFalse(AuthorizationService.can(self.ryan, catalog.FILA_REORDENAR, self.comercial))

        membership.role = UserSector.Role.GESTOR
        membership.save(update_fields=["role"])
        self.assertTrue(AuthorizationService.can(self.ryan, catalog.FILA_REORDENAR, self.comercial))


class ScopeIntegrityTests(AuthorizationTestCase):
    def test_sector_scope_requires_a_sector(self):
        """O banco valida coerência entre tipo e campos (doc 08 §22)."""
        with self.assertRaises(ValidationError):
            Scope.objects.create(organization=self.org, type=Scope.Type.SETOR)

    def test_sector_scope_rejects_unrelated_fields(self):
        site = Site.objects.create(organization=self.org, name="Obra")
        with self.assertRaises(ValidationError):
            Scope.objects.create(
                organization=self.org, type=Scope.Type.SETOR, sector=self.comercial, site=site
            )

    def test_scopes_are_reused_not_duplicated(self):
        first = ScopeService.sector_scope(self.comercial)
        second = ScopeService.sector_scope(self.comercial)
        self.assertEqual(first.pk, second.pk)


class FailClosedTests(AuthorizationTestCase):
    """O motor prefere negar a deixar passar o que não sabe endereçar."""

    def test_unknown_model_is_denied_even_with_organization_scope(self):
        from django.contrib.sessions.models import Session

        grant_action(self.paulo, catalog.ATIVIDADE_VISUALIZAR, organization=self.org)
        # Modelo sem organização e que o motor não conhece: nega.
        self.assertFalse(
            AuthorizationService.can(self.paulo, catalog.ATIVIDADE_VISUALIZAR, Session())
        )

    def test_deadline_objects_resolve_through_their_task(self):
        """Proposta e conflito não têm organização própria (doc 08 §48)."""
        from activities.services import ActivityService, DeadlineService, TaskService
        from django.utils import timezone

        grant_actions(
            self.paulo,
            [catalog.ATIVIDADE_CRIAR, catalog.TAREFA_CRIAR, catalog.PRAZO_PROPOR],
            organization=self.org,
        )
        activity = ActivityService.create_activity(
            organization=self.org, title="A", owner=self.paulo, created_by=self.paulo
        )
        task = TaskService.create_task(activity, self.comercial, "T", created_by=self.paulo)
        proposal = DeadlineService.propose(
            task, timezone.now() + timezone.timedelta(days=1), self.paulo
        )

        # Usuário de outra organização não alcança a proposta, mesmo com escopo
        # de organização na própria.
        grant_action(self.externo, catalog.PRAZO_ACEITAR, organization=self.other_org)
        self.assertFalse(AuthorizationService.can(self.externo, catalog.PRAZO_ACEITAR, proposal))


class CrossOrganizationScopeTests(AuthorizationTestCase):
    def test_cannot_grant_scope_pointing_to_another_organization(self):
        """Um escopo não pode apontar para fora do tenant (doc 05 §43)."""
        from acessos.services import AccessService
        from core.services import CadastroError

        outsider_sector = Sector.objects.create(organization=self.other_org, name="Alheio")
        profile = make_profile(self.org, "Gestor", [catalog.FILA_REORDENAR])

        with self.assertRaises(CadastroError):
            AccessService.assign_profile(
                user=self.paulo,
                profile=profile,
                scope_type=Scope.Type.SETOR,
                sector=outsider_sector,
                granted_by=self.paulo,
            )

    def test_cannot_grant_direct_action_scoped_to_another_organization(self):
        from acessos.services import AccessService
        from core.services import CadastroError

        outsider_company = Company.objects.create(organization=self.other_org, name="Alheia")
        with self.assertRaises(CadastroError):
            AccessService.grant_action(
                user=self.paulo,
                action=Action.objects.get(key=catalog.FILA_REORDENAR),
                scope_type=Scope.Type.EMPRESA,
                company=outsider_company,
                granted_by=self.paulo,
            )


class CreationScopeTests(AuthorizationTestCase):
    """Criar precisa poder ser autorizado por escopo, não só na organização."""

    def test_sector_scoped_grant_authorizes_creating_a_task_in_that_sector(self):
        from activities.services import ActivityError, ActivityService, TaskService

        grant_action(self.paulo, catalog.ATIVIDADE_CRIAR, organization=self.org)
        grant_action(self.paulo, catalog.TAREFA_CRIAR, sector=self.comercial)
        activity = ActivityService.create_activity(
            organization=self.org, title="A", owner=self.paulo, created_by=self.paulo
        )

        task = TaskService.create_task(activity, self.comercial, "No Comercial", created_by=self.paulo)
        self.assertIsNotNone(task.pk)

        with self.assertRaises(ActivityError):
            TaskService.create_task(activity, self.compras, "Em Compras", created_by=self.paulo)

    def test_company_scoped_grant_authorizes_creating_an_activity_there(self):
        from activities.services import ActivityError, ActivityService
        from acessos.services import ScopeService

        scope = ScopeService.get_or_create(self.org, Scope.Type.EMPRESA, company=self.company)
        grant_action(self.paulo, catalog.ATIVIDADE_CRIAR, organization=self.org, scope=scope)

        activity = ActivityService.create_activity(
            organization=self.org,
            title="Com empresa",
            owner=self.paulo,
            created_by=self.paulo,
            company=self.company,
        )
        self.assertIsNotNone(activity.pk)

        with self.assertRaises(ActivityError):
            ActivityService.create_activity(
                organization=self.org, title="Sem empresa", owner=self.paulo, created_by=self.paulo
            )


class SelfServiceTests(AuthorizationTestCase):
    def test_user_can_leave_a_task_they_assumed(self):
        """Sair de uma tarefa é o oposto de assumir, não atribuição."""
        from activities.services import ActivityService, TaskService

        grant_actions(
            self.paulo,
            [catalog.ATIVIDADE_CRIAR, catalog.TAREFA_CRIAR, catalog.TAREFA_ASSUMIR],
            organization=self.org,
        )
        activity = ActivityService.create_activity(
            organization=self.org, title="A", owner=self.paulo, created_by=self.paulo
        )
        task = TaskService.create_task(activity, self.comercial, "T", created_by=self.paulo)

        TaskService.add_executor(task, self.paulo, added_by=self.paulo)
        TaskService.remove_executor(task, self.paulo, removed_by=self.paulo)
        self.assertFalse(task.executors.filter(removed_at__isnull=True).exists())


class PlatformAdminTests(AuthorizationTestCase):
    def test_platform_admin_access_is_visible_in_the_report(self):
        self.paulo.is_superuser = True
        self.paulo.save(update_fields=["is_superuser"])

        self.assertTrue(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.comercial))
        self.assertTrue(AuthorizationService.has_unrestricted_access(self.paulo))
        self.assertIn(
            "Administrador da plataforma",
            AuthorizationService.explain(self.paulo, catalog.FILA_REORDENAR, self.comercial),
        )

    def test_inactive_superuser_has_no_access(self):
        self.paulo.is_superuser = True
        self.paulo.is_active = False
        self.paulo.save(update_fields=["is_superuser", "is_active"])

        self.assertFalse(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.comercial))
        self.assertFalse(AuthorizationService.has_unrestricted_access(self.paulo))
        self.assertEqual(
            AuthorizationService.explain(self.paulo, catalog.FILA_REORDENAR, self.comercial), []
        )


class AccessibleSectorsTests(AuthorizationTestCase):
    def test_lists_only_sectors_where_the_action_applies(self):
        grant_action(self.paulo, catalog.FILA_REORDENAR, sector=self.comercial)
        self.assertEqual(
            AuthorizationService.accessible_sector_ids(self.paulo, catalog.FILA_REORDENAR),
            {self.comercial.id},
        )

    def test_organization_scope_covers_every_sector(self):
        grant_action(self.paulo, catalog.FILA_REORDENAR, organization=self.org)
        self.assertEqual(
            AuthorizationService.accessible_sector_ids(self.paulo, catalog.FILA_REORDENAR),
            {self.comercial.id, self.compras.id},
        )

    def test_managed_sectors_relation_is_resolved(self):
        from accounts.models import UserSector

        UserSector.objects.create(
            user=self.paulo, sector=self.compras, role=UserSector.Role.GESTOR
        )
        grant_action(
            self.paulo,
            catalog.FILA_REORDENAR,
            organization=self.org,
            relation=Scope.Relation.SETORES_GERENCIADOS,
        )
        self.assertEqual(
            AuthorizationService.accessible_sector_ids(self.paulo, catalog.FILA_REORDENAR),
            {self.compras.id},
        )

    def test_does_not_run_a_query_per_sector(self):
        """Era o pior gargalo: uma consulta por setor a cada verificação."""
        for index in range(12):
            Sector.objects.create(organization=self.org, name=f"Setor {index}")
        grant_action(self.paulo, catalog.FILA_REORDENAR, sector=self.comercial)

        with self.assertNumQueries(3):
            AuthorizationService.accessible_sector_ids(self.paulo, catalog.FILA_REORDENAR)


class SectorMembershipIsNotAuthorizationTests(AuthorizationTestCase):
    def test_belonging_to_a_sector_grants_nothing(self):
        """§51.1 e doc 08 §14 — vínculo não é autorização."""
        from accounts.models import UserSector

        UserSector.objects.create(user=self.paulo, sector=self.comercial)
        self.assertFalse(
            AuthorizationService.can(self.paulo, catalog.FILA_VISUALIZAR_COMPLETA, self.comercial)
        )
        self.assertFalse(AuthorizationService.can(self.paulo, catalog.TAREFA_INICIAR, self.comercial))

    def test_two_users_in_the_same_sector_can_have_different_access(self):
        """§51.2."""
        from accounts.models import UserSector

        UserSector.objects.create(user=self.paulo, sector=self.comercial)
        UserSector.objects.create(user=self.ryan, sector=self.comercial)
        grant_action(self.paulo, catalog.FILA_REORDENAR, sector=self.comercial)

        self.assertTrue(AuthorizationService.can(self.paulo, catalog.FILA_REORDENAR, self.comercial))
        self.assertFalse(AuthorizationService.can(self.ryan, catalog.FILA_REORDENAR, self.comercial))
