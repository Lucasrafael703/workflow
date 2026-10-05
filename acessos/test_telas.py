"""Telas e níveis de acesso: o mapa tela → ações, grupos, menu, ajustes individuais e a migração
`0006_telas_do_menu` (que mantém visível o que já era visível)."""

import importlib

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from activities.testing import make_user
from audit.models import AuditLog
from core.models import Organization, Sector

from . import catalog, screens
from .models import Action, Profile, ProfileAction, Scope, UserAction, UserProfile
from .screen_services import (
    SCOPE_CUSTOM,
    SCOPE_MANAGED,
    SCOPE_ORG,
    SCOPE_TEAMS,
    GroupError,
    GroupService,
    UserAccessService,
    invitation_pending,
    menu_levels,
    profile_action_keys,
    profile_levels,
)
from .services import AuthorizationService, ScopeService
from .testing import assign_profile, ensure_catalog, grant_action, make_profile

migration = importlib.import_module("acessos.migrations.0006_telas_do_menu")
User = get_user_model()

ALL_KEYS = {key for _, _, actions in catalog.GROUPS for key, _, _, _ in actions}


class ScreenMapTests(SimpleTestCase):
    def test_every_mapped_action_exists_in_the_catalog(self):
        for screen in screens.SCREENS:
            self.assertLessEqual(screen.all_actions, ALL_KEYS, screen.key)

    def test_an_action_belongs_to_one_screen_only(self):
        """Duas telas sobre a mesma ação se desfariam uma à outra ao salvar."""
        seen = {}
        for screen in screens.SCREENS:
            for key in screen.all_actions:
                self.assertNotIn(key, seen, f"{key} em {screen.key} e {seen.get(key)}")
                seen[key] = screen.key

    def test_every_menu_action_is_used_by_a_screen(self):
        used = {key for screen in screens.SCREENS for key in screen.all_actions}
        self.assertEqual({k for k in ALL_KEYS if k.startswith("tela.")} - used, set())

    def test_every_screen_is_in_a_known_section(self):
        sections = {key for key, _ in screens.SECTIONS}
        self.assertTrue(all(screen.section in sections for screen in screens.SCREENS))
        self.assertEqual(len({screen.key for screen in screens.SCREENS}), len(screens.SCREENS))

    def test_the_marker_is_the_first_edit_action(self):
        for screen in screens.SCREENS:
            self.assertEqual(screen.marker, screen.edit[0] if screen.edit else None)

    def test_levels_offered_depend_on_whether_the_screen_can_be_edited(self):
        self.assertEqual(screens.SCREEN_BY_KEY["inicio"].levels, (screens.NONE, screens.VIEW))
        self.assertEqual(screens.SCREEN_BY_KEY["tarefas"].levels, screens.LEVELS)
        self.assertEqual(screens.normalize_level(screens.SCREEN_BY_KEY["inicio"], screens.EDIT), screens.VIEW)
        self.assertEqual(screens.normalize_level(screens.SCREEN_BY_KEY["tarefas"], "lixo"), screens.NONE)


class LevelReadingTests(SimpleTestCase):
    tarefas = screens.SCREEN_BY_KEY["tarefas"]

    def test_marker_means_edit_view_means_view_nothing_means_none(self):
        self.assertEqual(screens.level_from_actions(self.tarefas, {catalog.TAREFA_INICIAR}), screens.EDIT)
        self.assertEqual(screens.level_from_actions(self.tarefas, {catalog.TAREFA_VISUALIZAR}), screens.VIEW)
        self.assertEqual(screens.level_from_actions(self.tarefas, {catalog.TAREFA_CRIAR}), screens.VIEW)
        self.assertEqual(screens.level_from_actions(self.tarefas, set()), screens.NONE)

    def test_advanced_actions_never_change_the_level(self):
        self.assertEqual(screens.level_from_actions(self.tarefas, {catalog.TAREFA_REABRIR}), screens.NONE)

    def test_actions_for_each_level(self):
        self.assertEqual(screens.actions_for_level(self.tarefas, screens.NONE), frozenset())
        self.assertEqual(screens.actions_for_level(self.tarefas, screens.VIEW), {catalog.TAREFA_VISUALIZAR})
        edit = screens.actions_for_level(self.tarefas, screens.EDIT)
        self.assertIn(catalog.TAREFA_VISUALIZAR, edit)
        self.assertIn(catalog.TAREFA_CRIAR, edit)
        self.assertNotIn(catalog.TAREFA_CANCELAR, edit)  # sensível: só pelo ajuste fino

    def test_every_suggested_profile_reads_back_sensibly(self):
        colaborador = screens.levels_from_actions(catalog.SUGGESTED_PROFILES["Colaborador"])
        self.assertEqual(colaborador["tarefas"], screens.EDIT)
        self.assertEqual(colaborador["demandas"], screens.EDIT)
        self.assertEqual(colaborador["usuarios"], screens.NONE)
        self.assertEqual(colaborador["grupos"], screens.NONE)
        gestor = screens.levels_from_actions(catalog.SUGGESTED_PROFILES["Gestor de Setor"])
        self.assertEqual(gestor["visao_gestor"], screens.VIEW)
        self.assertEqual(gestor["fila"], screens.EDIT)
        self.assertEqual(gestor["usuarios"], screens.NONE)
        admin = screens.levels_from_actions(catalog.SUGGESTED_PROFILES["Administrador"])
        self.assertEqual(admin, screens.full_levels())

    def test_screens_count_ignores_none(self):
        self.assertEqual(screens.screens_count({"a": "none", "b": "ver", "c": "editar"}), 2)

    def test_org_only_levels_are_flagged(self):
        quadros = screens.SCREEN_BY_KEY["quadros"]
        self.assertTrue(screens.needs_organization(quadros, screens.VIEW))
        self.assertFalse(screens.needs_organization(screens.SCREEN_BY_KEY["tarefas"], screens.EDIT))
        # "Ver" cadastros é só menu: vale em qualquer escopo; "Editar" precisa da organização
        empresas = screens.SCREEN_BY_KEY["empresas"]
        self.assertFalse(screens.needs_organization(empresas, screens.VIEW))
        self.assertTrue(screens.needs_organization(empresas, screens.EDIT))


class GroupTestCase(TestCase):
    def setUp(self):
        ensure_catalog()
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Outra")
        # Quem administra grupos: tem as duas ações de segurança na organização inteira.
        self.admin = make_user(
            "admin", self.org, [catalog.SEGURANCA_GERIR_PERFIS, catalog.SEGURANCA_GERIR_AUTORIZACOES]
        )
        self.group = make_profile(
            self.org, "Equipe", [catalog.TAREFA_VISUALIZAR, catalog.TAREFA_INICIAR, catalog.TAREFA_REABRIR]
        )

    def keys(self, group=None):
        return profile_action_keys(group or self.group)


class GroupServiceTests(GroupTestCase):
    def test_raising_a_screen_grants_exactly_its_actions(self):
        GroupService.save_levels(self.group, {"clientes": screens.EDIT}, self.admin)
        self.assertLessEqual({catalog.TELA_CLIENTES, catalog.CLIENTE_GERIR}, self.keys())

    def test_screens_that_did_not_change_keep_everything_including_advanced_actions(self):
        before = self.keys()
        add, remove, changed = GroupService.changes_for(self.group, profile_levels(self.group))
        self.assertEqual((add, remove, changed), (set(), set(), []))
        GroupService.save_levels(self.group, {"clientes": screens.VIEW}, self.admin)
        self.assertLessEqual(before, self.keys())  # tarefa.reabrir (avançada) continua lá

    def test_none_removes_every_action_of_the_screen_including_advanced_ones(self):
        GroupService.save_levels(self.group, {"tarefas": screens.NONE}, self.admin)
        self.assertEqual(self.keys() & screens.SCREEN_BY_KEY["tarefas"].all_actions, set())

    def test_going_down_to_view_drops_edit_and_advanced_actions(self):
        GroupService.save_levels(self.group, {"tarefas": screens.VIEW}, self.admin)
        self.assertEqual(self.keys(), {catalog.TAREFA_VISUALIZAR})

    def test_other_screens_are_untouched_by_a_change(self):
        extra = make_profile(self.org, "Outra", [catalog.CLIENTE_GERIR, catalog.TELA_CLIENTES])
        GroupService.save_levels(self.group, {"tarefas": screens.NONE}, self.admin)
        self.assertEqual(self.keys(extra), {catalog.CLIENTE_GERIR, catalog.TELA_CLIENTES})

    def test_a_save_that_changes_nothing_writes_nothing(self):
        count, changed = GroupService.save_levels(self.group, {}, self.admin)
        self.assertEqual((count, changed), (0, []))
        self.assertFalse(AuditLog.objects.filter(action=AuditLog.Action.PROFILE_ACTIONS_CHANGED).exists())

    def test_the_change_is_audited(self):
        GroupService.save_levels(self.group, {"clientes": screens.EDIT}, self.admin)
        entry = AuditLog.objects.get(action=AuditLog.Action.PROFILE_ACTIONS_CHANGED)
        self.assertIn(catalog.CLIENTE_GERIR, entry.new_value)

    def test_unknown_or_invalid_levels_are_ignored_safely(self):
        GroupService.save_levels(self.group, {"nao_existe": "editar", "tarefas": "lixo"}, self.admin)
        self.assertEqual(self.keys() & screens.SCREEN_BY_KEY["tarefas"].all_actions, set())

    def test_an_administrator_cannot_lock_themselves_out(self):
        admins = make_profile(
            self.org, "Admins", [catalog.SEGURANCA_GERIR_PERFIS, catalog.SEGURANCA_GERIR_AUTORIZACOES]
        )
        UserAction.objects.filter(user=self.admin).update(is_active=False)
        assign_profile(self.admin, admins)
        with self.assertRaises(GroupError):
            GroupService.save_levels(admins, {"grupos": screens.NONE}, self.admin)
        self.assertIn(catalog.SEGURANCA_GERIR_AUTORIZACOES, self.keys(admins))

    def test_losing_the_screen_is_fine_when_another_source_still_grants_it(self):
        admins = make_profile(self.org, "Admins", [catalog.SEGURANCA_GERIR_AUTORIZACOES])
        assign_profile(self.admin, admins)  # o admin ainda tem a concessão direta
        GroupService.save_levels(admins, {"grupos": screens.NONE}, self.admin)
        self.assertEqual(self.keys(admins), set())

    def test_platform_admin_is_never_locked_out(self):
        root = User.objects.create_superuser("root", "root@example.com", "x")
        root.profile.organization = self.org
        root.profile.save()
        GroupService.save_levels(self.group, {"grupos": screens.NONE}, root)

    def test_create_blank_and_copy(self):
        blank = GroupService.create(self.org, "Em branco", "", self.admin)
        self.assertEqual(self.keys(blank), set())
        copy = GroupService.create(self.org, "Cópia", "igual", self.admin, copy_from=self.group)
        self.assertEqual(self.keys(copy), self.keys())
        self.assertEqual(copy.description, "igual")

    def test_group_names_are_unique_per_organization(self):
        with self.assertRaises(GroupError):
            GroupService.create(self.org, "equipe", "", self.admin)
        with self.assertRaises(GroupError):
            GroupService.create(self.org, "   ", "", self.admin)
        GroupService.create(self.other_org, "Equipe", "", self.admin)  # outra organização pode

    def test_rename(self):
        GroupService.rename(self.group, "Novo nome", "desc", self.admin)
        self.group.refresh_from_db()
        self.assertEqual((self.group.name, self.group.description), ("Novo nome", "desc"))
        make_profile(self.org, "Ocupado", [])
        with self.assertRaises(GroupError):
            GroupService.rename(self.group, "Ocupado", "", self.admin)

    def test_inactivating_is_refused_while_people_use_the_group(self):
        ana = make_user("ana", self.org)
        assign_profile(ana, self.group)
        with self.assertRaises(GroupError) as ctx:
            GroupService.inactivate(self.group, self.admin)
        self.assertIn("1 pessoa", str(ctx.exception))
        self.group.refresh_from_db()
        self.assertTrue(self.group.is_active)

    def test_inactivating_an_unused_group(self):
        GroupService.inactivate(self.group, self.admin)
        self.group.refresh_from_db()
        self.assertFalse(self.group.is_active)
        self.assertNotIn(self.group, GroupService.groups(self.org))

    def test_inactive_people_do_not_count_as_users_of_the_group(self):
        ana = make_user("ana", self.org)
        assign_profile(ana, self.group)
        ana.is_active = False
        ana.save(update_fields=["is_active"])
        self.assertEqual(GroupService.user_count(self.group), 0)
        GroupService.inactivate(self.group, self.admin)

    def test_groups_are_listed_with_their_people(self):
        ana = make_user("ana", self.org)
        assign_profile(ana, self.group)
        assign_profile(ana, make_profile(self.org, "Outro", []))
        listed = {g.name: g.user_count for g in GroupService.groups(self.org)}
        self.assertEqual(listed["Equipe"], 1)
        self.assertEqual(listed["Outro"], 1)

    def test_comparison_marks_the_rows_that_differ(self):
        other = make_profile(self.org, "Outro", [catalog.TAREFA_VISUALIZAR])
        comparison = GroupService.comparison(self.org)
        names = [g.name for g in comparison["groups"]]
        self.assertEqual(sorted(names), names)
        tarefas = next(
            row
            for section in comparison["sections"]
            for row in section["rows"]
            if row["screen"].key == "tarefas"
        )
        cells = dict(zip(names, tarefas["cells"]))
        self.assertEqual((cells["Equipe"], cells["Outro"]), (screens.EDIT, screens.VIEW))
        self.assertTrue(tarefas["differs"])
        inicio = next(
            row for section in comparison["sections"] for row in section["rows"] if row["screen"].key == "inicio"
        )
        self.assertFalse(inicio["differs"])
        self.assertIsNotNone(other)


class MenuLevelsTests(GroupTestCase):
    def levels(self, user):
        return menu_levels(user)

    def test_a_person_with_nothing_sees_nothing(self):
        nobody = make_user("ninguem", self.org)
        self.assertTrue(all(level == screens.NONE for level in self.levels(nobody).values()))

    def test_superuser_sees_everything(self):
        root = User.objects.create_superuser("root", "root@example.com", "x")
        root.profile.organization = self.org
        root.profile.save()
        self.assertEqual(self.levels(root), screens.full_levels())

    def test_levels_follow_the_profile(self):
        ana = make_user("ana", self.org)
        assign_profile(ana, self.group)
        levels = self.levels(ana)
        self.assertEqual(levels["tarefas"], screens.EDIT)
        self.assertEqual(levels["demandas"], screens.NONE)

    def test_a_direct_grant_also_counts(self):
        ana = make_user("ana", self.org, [catalog.TELA_INICIO])
        self.assertEqual(self.levels(ana)["inicio"], screens.VIEW)

    def test_screens_that_only_work_organization_wide_need_an_organization_scope(self):
        """Quadros só autoriza com escopo de organização: no escopo "equipes" o item não aparece."""
        quadros = make_profile(self.org, "Quadros", [catalog.QUADRO_VISUALIZAR, catalog.TAREFA_VISUALIZAR])
        team = make_user("equipe", self.org)
        assign_profile(team, quadros, relation=Scope.Relation.MEUS_SETORES)
        whole = make_user("toda", self.org)
        assign_profile(whole, quadros)
        self.assertEqual(self.levels(team)["quadros"], screens.NONE)
        self.assertEqual(self.levels(team)["tarefas"], screens.VIEW)
        self.assertEqual(self.levels(whole)["quadros"], screens.VIEW)

    def test_inactive_profiles_assignments_and_actions_do_not_count(self):
        ana = make_user("ana", self.org)
        assignment = assign_profile(ana, self.group)
        self.assertEqual(self.levels(ana)["tarefas"], screens.EDIT)
        assignment.is_active = False
        assignment.save()
        self.assertEqual(self.levels(ana)["tarefas"], screens.NONE)
        assignment.is_active = True
        assignment.save()
        self.group.is_active = False
        self.group.save()
        self.assertEqual(self.levels(ana)["tarefas"], screens.NONE)

    def test_the_menu_uses_a_constant_number_of_queries(self):
        ana = make_user("ana", self.org)
        assign_profile(ana, self.group)
        with self.assertNumQueries(2):
            menu_levels(ana)


class UserAccessServiceTests(GroupTestCase):
    def setUp(self):
        super().setUp()
        self.sector = Sector.objects.create(organization=self.org, name="Projetos")
        self.ana = make_user("ana", self.org)

    def apply(self, group=None, kind=SCOPE_TEAMS, desired=None, user=None):
        return UserAccessService.apply(
            user or self.ana, self.org, group or self.group, kind, desired or {}, self.admin
        )

    def test_assigns_the_group_in_the_chosen_scope(self):
        assignment = self.apply(kind=SCOPE_TEAMS)
        self.assertEqual((assignment.profile, assignment.scope.relation), (self.group, Scope.Relation.MEUS_SETORES))
        self.apply(kind=SCOPE_MANAGED)
        self.assertEqual(UserProfile.objects.filter(user=self.ana, is_active=True).count(), 1)
        self.assertEqual(
            UserProfile.objects.get(user=self.ana, is_active=True).scope.relation, Scope.Relation.SETORES_GERENCIADOS
        )
        self.apply(kind=SCOPE_ORG)
        self.assertEqual(UserProfile.objects.get(user=self.ana, is_active=True).scope.type, Scope.Type.ORGANIZACAO)

    def test_changing_the_group_revokes_the_previous_assignment_but_keeps_history(self):
        self.apply()
        other = make_profile(self.org, "Outro", [catalog.CLIENTE_GERIR])
        self.apply(group=other)
        self.assertEqual(list(UserProfile.objects.filter(user=self.ana, is_active=True)), [
            UserProfile.objects.get(user=self.ana, profile=other)
        ])
        self.assertTrue(UserProfile.objects.filter(user=self.ana, profile=self.group, is_active=False).exists())

    def test_saving_the_same_thing_twice_changes_nothing(self):
        self.apply()
        before = (UserProfile.objects.count(), UserAction.objects.count(), AuditLog.objects.count())
        self.apply()
        self.assertEqual(before, (UserProfile.objects.count(), UserAction.objects.count(), AuditLog.objects.count()))

    def test_individual_adjustment_is_a_direct_grant_for_that_person_only(self):
        self.apply(desired={"clientes": screens.EDIT})
        state = UserAccessService.state(self.ana)
        self.assertEqual(state["levels"]["clientes"], screens.EDIT)
        self.assertEqual(state["group_levels"]["clientes"], screens.NONE)
        self.assertTrue(state["individual"]["clientes"])
        self.assertFalse(state["individual"]["tarefas"])
        self.assertTrue(AuthorizationService.can(self.ana, catalog.CLIENTE_GERIR))
        outro = make_user("outro", self.org)
        self.apply(user=outro)
        self.assertFalse(AuthorizationService.can(outro, catalog.CLIENTE_GERIR))

    def test_actions_that_only_work_organization_wide_are_granted_in_the_organization_scope(self):
        self.apply(kind=SCOPE_TEAMS, desired={"clientes": screens.EDIT})
        grant = UserAction.objects.get(user=self.ana, action__key=catalog.CLIENTE_GERIR, is_active=True)
        self.assertEqual(grant.scope.type, Scope.Type.ORGANIZACAO)
        self.assertTrue(AuthorizationService.can(self.ana, catalog.CLIENTE_GERIR))

    def test_going_back_to_the_group_default_revokes_the_individual_grants(self):
        self.apply(desired={"clientes": screens.EDIT})
        self.apply(desired={"clientes": screens.NONE})
        self.assertFalse(AuthorizationService.can(self.ana, catalog.CLIENTE_GERIR))
        self.assertFalse(UserAccessService.state(self.ana)["individual"]["clientes"])
        self.assertFalse(UserAction.objects.filter(user=self.ana, is_active=True).exists())

    def test_an_individual_edit_can_step_down_to_view(self):
        self.apply(desired={"clientes": screens.EDIT})
        self.apply(desired={"clientes": screens.VIEW})
        state = UserAccessService.state(self.ana)
        self.assertEqual(state["levels"]["clientes"], screens.VIEW)
        self.assertFalse(AuthorizationService.can(self.ana, catalog.CLIENTE_GERIR))

    def test_a_level_below_the_group_is_ignored_because_the_engine_has_no_deny(self):
        self.apply(desired={"tarefas": screens.NONE})
        self.assertEqual(UserAccessService.state(self.ana)["levels"]["tarefas"], screens.EDIT)

    def test_screens_the_form_did_not_change_are_left_alone(self):
        """Uma concessão avançada feita em "Acessos" não some só porque a pessoa abriu e salvou."""
        grant_action(self.ana, catalog.CLIENTE_GERIR, organization=self.org)
        self.apply()
        self.assertTrue(UserAction.objects.filter(user=self.ana, action__key=catalog.CLIENTE_GERIR, is_active=True).exists())

    def test_grants_in_other_scopes_are_not_touched(self):
        grant_action(self.ana, catalog.CLIENTE_GERIR, sector=self.sector)  # exceção manual, escopo de setor
        self.apply(desired={"clientes": screens.NONE})
        self.assertTrue(UserAction.objects.filter(user=self.ana, action__key=catalog.CLIENTE_GERIR, is_active=True).exists())

    def test_more_than_one_group_is_not_edited_here(self):
        assign_profile(self.ana, self.group)
        assign_profile(self.ana, make_profile(self.org, "Outro", []), relation=Scope.Relation.MEUS_SETORES)
        self.assertTrue(UserAccessService.state(self.ana)["complex"])
        with self.assertRaises(GroupError):
            self.apply()

    def test_custom_scope_is_kept_when_only_the_screens_change(self):
        sector_scope = ScopeService.sector_scope(self.sector)
        from .models import UserProfile as UP

        UP.objects.create(organization=self.org, user=self.ana, profile=self.group, scope=sector_scope)
        self.assertEqual(UserAccessService.state(self.ana)["scope_kind"], SCOPE_CUSTOM)
        self.apply(kind=SCOPE_CUSTOM, desired={"clientes": screens.VIEW})
        self.assertEqual(UP.objects.get(user=self.ana, is_active=True).scope, sector_scope)

    def test_without_a_group_only_individual_grants_exist(self):
        UserAccessService.apply(self.ana, self.org, None, SCOPE_TEAMS, {}, self.admin)  # sem grupo e sem nada
        self.assertFalse(UserProfile.objects.filter(user=self.ana, is_active=True).exists())

    def test_removing_the_group_revokes_the_assignment(self):
        self.apply()
        UserAccessService.apply(self.ana, self.org, None, SCOPE_TEAMS, {}, self.admin)
        self.assertFalse(UserProfile.objects.filter(user=self.ana, is_active=True).exists())

    def test_overview_summarises_each_person(self):
        self.apply(desired={"clientes": screens.EDIT})
        boss = User.objects.create_superuser("chefe", "chefe@example.com", "x")
        boss.profile.organization = self.org
        boss.profile.save()
        nobody = make_user("ninguem", self.org)
        info = UserAccessService.overview([self.ana, boss, nobody])
        self.assertEqual(info[self.ana.pk]["groups"], [self.group])
        self.assertEqual(info[self.ana.pk]["individual"], 1)
        self.assertGreater(info[self.ana.pk]["screens"], 0)
        self.assertTrue(info[boss.pk]["full"])
        self.assertEqual(info[boss.pk]["screens"], len(screens.SCREENS))
        self.assertEqual(info[nobody.pk]["groups"], [])
        self.assertEqual(info[nobody.pk]["screens"], 0)

    def test_overview_does_not_query_per_person(self):
        people = [make_user(f"p{i}", self.org) for i in range(6)]
        for person in people:
            self.apply(user=person)
        with self.assertNumQueries(3):
            UserAccessService.overview(people)

    def test_invitation_pending(self):
        invited = User.objects.create_user("convidado", email="c@example.com")
        invited.set_unusable_password()
        invited.save()
        self.assertTrue(invitation_pending(invited))
        self.assertFalse(invitation_pending(self.ana))
        invited.is_active = False
        self.assertFalse(invitation_pending(invited))


class MenuMigrationTests(TestCase):
    """`0006`: quem já via cada item do menu continua vendo."""

    def setUp(self):
        ensure_catalog()
        self.org = Organization.objects.create(name="Biasi")
        # Estado "antes": sem nenhuma ação tela.* em lugar nenhum.
        ProfileAction.objects.filter(action__key__startswith="tela.").delete()
        UserAction.objects.filter(action__key__startswith="tela.").delete()

    def run_migration(self):
        migration.create_actions_and_grants(apps, None)

    def profile_keys(self, profile):
        return profile_action_keys(profile)

    def test_everybody_keeps_home_and_notifications(self):
        profile = make_profile(self.org, "Qualquer", [catalog.TAREFA_VISUALIZAR])
        empty = make_profile(self.org, "Vazio", [])
        self.run_migration()
        for item in (profile, empty):
            self.assertLessEqual({catalog.TELA_INICIO, catalog.TELA_NOTIFICACOES}, self.profile_keys(item))

    def test_management_menu_follows_metrics(self):
        manager = make_profile(self.org, "Gestor", [catalog.METRICAS_VISUALIZAR])
        worker = make_profile(self.org, "Operador", [catalog.TAREFA_VISUALIZAR])
        self.run_migration()
        self.assertLessEqual(
            {catalog.TELA_EQUIPE, catalog.TELA_GARGALOS, catalog.TELA_INSIGHTS}, self.profile_keys(manager)
        )
        self.assertFalse({catalog.TELA_EQUIPE, catalog.TELA_GARGALOS, catalog.TELA_INSIGHTS} & self.profile_keys(worker))

    def test_registers_keep_the_menu_they_already_had(self):
        client_manager = make_profile(self.org, "Clientes", [catalog.CLIENTE_GERIR])
        process_viewer = make_profile(self.org, "Processos", [catalog.PROCESSO_VISUALIZAR])
        nothing = make_profile(self.org, "Nada", [catalog.TAREFA_VISUALIZAR])
        self.run_migration()
        every_register = {
            catalog.TELA_EMPRESAS, catalog.TELA_SETORES, catalog.TELA_CLIENTES, catalog.TELA_OBRAS,
            catalog.TELA_CENTROS_CUSTO,
        }
        self.assertLessEqual(every_register, self.profile_keys(client_manager))
        self.assertLessEqual(every_register, self.profile_keys(process_viewer))  # abria Cadastros inteiro
        self.assertFalse(every_register & self.profile_keys(nothing))

    def test_administration_section_follows_who_could_see_it(self):
        users = make_profile(self.org, "Usuários", [catalog.USUARIO_VISUALIZAR])
        groups = make_profile(self.org, "Grupos", [catalog.SEGURANCA_GERIR_PERFIS])
        nothing = make_profile(self.org, "Nada", [catalog.TAREFA_VISUALIZAR])
        self.run_migration()
        for item in (users, groups):
            self.assertLessEqual({catalog.TELA_CONFIGURACOES, catalog.TELA_INTEGRACOES}, self.profile_keys(item))
        self.assertFalse({catalog.TELA_CONFIGURACOES, catalog.TELA_INTEGRACOES} & self.profile_keys(nothing))

    def test_direct_grants_are_kept_in_the_same_scope(self):
        sector = Sector.objects.create(organization=self.org, name="Projetos")
        ana = make_user("ana", self.org)
        grant_action(ana, catalog.METRICAS_VISUALIZAR, sector=sector)
        self.run_migration()
        grants = UserAction.objects.filter(user=ana, action__key=catalog.TELA_EQUIPE, is_active=True)
        self.assertEqual([g.scope.sector for g in grants], [sector])
        self.assertTrue(UserAction.objects.filter(user=ana, action__key=catalog.TELA_INICIO).exists())
        self.assertEqual(menu_levels(ana)["equipe"], screens.VIEW)

    def test_people_without_any_grant_get_nothing(self):
        nobody = make_user("ninguem", self.org)
        self.run_migration()
        self.assertFalse(UserAction.objects.filter(user=nobody).exists())

    def test_running_twice_changes_nothing_more(self):
        make_profile(self.org, "Gestor", [catalog.METRICAS_VISUALIZAR])
        ana = make_user("ana", self.org, [catalog.METRICAS_VISUALIZAR])
        self.run_migration()
        before = (ProfileAction.objects.count(), UserAction.objects.count())
        self.run_migration()
        self.assertEqual(before, (ProfileAction.objects.count(), UserAction.objects.count()))
        self.assertIsNotNone(ana)

    def test_reverse_removes_the_menu_actions_only(self):
        profile = make_profile(self.org, "Gestor", [catalog.METRICAS_VISUALIZAR, catalog.TAREFA_VISUALIZAR])
        self.run_migration()
        migration.remove_actions_and_grants(apps, None)
        self.assertEqual(self.profile_keys(profile), {catalog.METRICAS_VISUALIZAR, catalog.TAREFA_VISUALIZAR})
        self.assertFalse(Action.objects.filter(key__startswith="tela.").exists())
        migration.create_actions_and_grants(apps, None)  # e dá para refazer

    def test_the_suggested_administrator_has_every_menu_action(self):
        self.assertEqual(
            {k for k in catalog.SUGGESTED_PROFILES["Administrador"] if k.startswith("tela.")},
            {k for k in ALL_KEYS if k.startswith("tela.")},
        )
        self.assertIsNotNone(Profile)
