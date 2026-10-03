"""Telas de acesso: lista de usuários, usuário numa página só, grupos de acesso e menu por tela."""

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserSector
from acessos import catalog, screens
from acessos.models import Profile as AccessProfile
from acessos.models import Scope, UserAction, UserProfile
from acessos.screen_services import profile_action_keys, profile_levels
from acessos.services import AuthorizationService
from acessos.testing import assign_profile, ensure_catalog, grant_action, make_profile
from activities.testing import make_user
from audit.models import AuditLog
from core.models import Organization, Sector

User = get_user_model()

ADMIN_ACTIONS = [
    catalog.USUARIO_VISUALIZAR,
    catalog.USUARIO_CRIAR,
    catalog.USUARIO_EDITAR,
    catalog.SEGURANCA_GERIR_PERFIS,
    catalog.SEGURANCA_GERIR_AUTORIZACOES,
]


class AccessTestCase(TestCase):
    def setUp(self):
        ensure_catalog()
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Outra")
        self.admin = make_user("admin", self.org, ADMIN_ACTIONS)
        self.admin.first_name = "Admin"
        self.admin.save()
        self.projetos = Sector.objects.create(organization=self.org, name="Projetos")
        self.orcamentos = Sector.objects.create(organization=self.org, name="Orçamentos")
        self.colaborador = make_profile(
            self.org,
            "Colaborador",
            [catalog.TELA_INICIO, catalog.TELA_NOTIFICACOES, catalog.TAREFA_VISUALIZAR, catalog.TAREFA_INICIAR,
             catalog.ATIVIDADE_VISUALIZAR, catalog.ATIVIDADE_CRIAR],
        )
        self.gestor = make_profile(
            self.org, "Gestor de setor", [catalog.TAREFA_VISUALIZAR, catalog.TAREFA_INICIAR, catalog.METRICAS_VISUALIZAR]
        )
        self.client.force_login(self.admin)

    def person(self, username="ana", groups=(), teams=(), **extra):
        user = make_user(username, self.org)
        user.first_name = extra.get("first_name", username.title())
        user.email = extra.get("email", f"{username}@empresa.com")
        user.save()
        for group in groups:
            assign_profile(user, group, relation=Scope.Relation.MEUS_SETORES)
        for sector in teams:
            UserSector.objects.create(user=user, sector=sector)
        return user


# ---------------------------------------------------------------------------
# Lista
# ---------------------------------------------------------------------------


class UserListTests(AccessTestCase):
    def get(self, **params):
        return self.client.get(reverse("user-list"), params)

    def names(self, response):
        return [row["user"].username for row in response.context["rows"]]

    def test_needs_the_view_permission(self):
        self.client.force_login(make_user("sem", self.org))
        self.assertEqual(self.get().status_code, 403)

    def test_lists_only_the_people_of_the_organization(self):
        self.person("ana")
        make_user("estranho", self.other_org)
        self.assertIn("ana", self.names(self.get()))
        self.assertNotIn("estranho", self.names(self.get(situacao="todos")))

    def test_shows_team_group_and_screen_count(self):
        self.person("ana", groups=[self.colaborador], teams=[self.projetos])
        response = self.get()
        row = next(r for r in response.context["rows"] if r["user"].username == "ana")
        self.assertEqual([t.name for t in row["teams"]], ["Projetos"])
        self.assertEqual([g.name for g, _ in row["groups"]], ["Colaborador"])
        self.assertEqual(row["screens"], 4)  # início, notificações, tarefas e demandas
        self.assertContains(response, "Colaborador")
        self.assertContains(response, "4 telas")

    def test_inactive_people_and_pending_invites_have_their_own_state(self):
        gone = self.person("saiu")
        gone.is_active = False
        gone.save()
        invited = self.person("convidado")
        invited.set_unusable_password()
        invited.save()
        self.assertNotIn("saiu", self.names(self.get()))  # padrão: só ativos
        self.assertIn("convidado", self.names(self.get()))  # convite pendente conta como ativo
        self.assertEqual(self.names(self.get(situacao="inativos")), ["saiu"])
        self.assertEqual(self.names(self.get(situacao="convite")), ["convidado"])
        states = {r["user"].username: r["state"][0] for r in self.get(situacao="todos").context["rows"]}
        self.assertEqual((states["saiu"], states["convidado"]), ("inactive", "pending"))
        self.assertContains(self.get(situacao="convite"), "Convite pendente")

    def test_filters(self):
        self.person("ana", groups=[self.colaborador], teams=[self.projetos])
        self.person("bia", groups=[self.gestor], teams=[self.orcamentos])
        self.assertEqual(self.names(self.get(grupo=self.gestor.pk)), ["bia"])
        self.assertEqual(self.names(self.get(equipe=self.projetos.pk)), ["ana"])
        self.assertEqual(self.names(self.get(q="BIA")), ["bia"])
        self.assertEqual(self.names(self.get(q="ana@empresa")), ["ana"])
        self.assertEqual(self.names(self.get(equipe=self.projetos.pk, grupo=self.gestor.pk)), [])

    def test_the_team_chips_keep_the_other_filters(self):
        chips = self.get(q="x", situacao="todos").context["team_chips"]
        self.assertEqual(chips[0]["label"], "Todas as equipes")
        projetos = next(c for c in chips if c["label"] == "Projetos")
        self.assertIn("q=x", projetos["url"])
        self.assertIn(f"equipe={self.projetos.pk}", projetos["url"])

    def test_people_with_a_removed_team_do_not_show_it(self):
        ana = self.person("ana", teams=[self.projetos])
        UserSector.objects.filter(user=ana).update(removed_at="2026-01-01T00:00:00Z")
        row = next(r for r in self.get().context["rows"] if r["user"].username == "ana")
        self.assertEqual(row["teams"], [])

    def test_superusers_are_flagged_and_counted_as_administrators(self):
        root = self.person("root")
        root.is_superuser = True
        root.save()
        admins = make_profile(
            self.org, "Administrador", [k for _, _, a in catalog.GROUPS for k, _, _, _ in a]
        )
        self.person("chefe", groups=[admins])
        self.person("ana", groups=[self.colaborador])
        response = self.get()
        self.assertEqual(response.context["full_count"], 2)
        self.assertContains(response, "2 pessoas estão como Administrador")
        self.assertContains(response, "Super usuário")
        self.assertEqual(sorted(self.names(self.get(acesso="total", situacao="todos"))), ["chefe", "root"])
        row = next(r for r in response.context["rows"] if r["user"].username == "root")
        self.assertTrue(row["all_screens"])

    def test_no_banner_without_administrators(self):
        self.person("ana", groups=[self.colaborador])
        self.assertNotContains(self.get(), "como Administrador")

    def test_the_new_user_button_needs_the_create_permission(self):
        self.assertContains(self.get(), reverse("user-create"))
        limited = make_user("viewer", self.org, [catalog.USUARIO_VISUALIZAR])
        self.client.force_login(limited)
        self.assertNotContains(self.get(), reverse("user-create"))
        self.assertNotContains(self.get(), reverse("access-groups"))

    def test_the_number_of_queries_does_not_grow_with_the_people(self):
        self.person("p0", groups=[self.colaborador], teams=[self.projetos])
        with self.assertNumQueries(self._count()):
            self.get()
        for index in range(1, 8):
            self.person(f"p{index}", groups=[self.colaborador], teams=[self.projetos])
        with self.assertNumQueries(self._count()):
            self.get()

    def _count(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            self.get()
        return len(ctx)


# ---------------------------------------------------------------------------
# Usuário
# ---------------------------------------------------------------------------


class UserEditorTests(AccessTestCase):
    def payload(self, **overrides):
        data = {
            "first_name": "Maria Oliveira",
            "email": "maria@empresa.com",
            "username": "",
            "phone": "(11) 99999-0000",
            "first_access": "invite",
            "is_active": "on",
            "teams": [self.projetos.pk],
            f"role_{self.projetos.pk}": "MEMBRO",
            "main_sector": self.projetos.pk,
            "group": self.colaborador.pk,
            "scope": "teams",
        }
        data.update(overrides)
        return data

    def create(self, **overrides):
        return self.client.post(reverse("user-create"), self.payload(**overrides))

    # -- acesso ------------------------------------------------------

    def test_creating_needs_the_create_permission_and_editing_the_edit_permission(self):
        only_edit = make_user("editor", self.org, [catalog.USUARIO_EDITAR])
        self.client.force_login(only_edit)
        self.assertEqual(self.client.get(reverse("user-create")).status_code, 403)
        target = self.person("ana")
        self.assertEqual(self.client.get(reverse("user-edit", args=[target.pk])).status_code, 200)
        only_create = make_user("criador", self.org, [catalog.USUARIO_CRIAR])
        self.client.force_login(only_create)
        self.assertEqual(self.client.get(reverse("user-create")).status_code, 200)
        self.assertEqual(self.client.get(reverse("user-edit", args=[target.pk])).status_code, 403)

    def test_another_organization_is_a_404(self):
        outsider = make_user("alheio", self.other_org)
        self.assertEqual(self.client.get(reverse("user-edit", args=[outsider.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("user-edit", args=[outsider.pk]), self.payload()).status_code, 404)

    def test_the_new_user_page_has_every_section_and_screen(self):
        response = self.client.get(reverse("user-create"))
        self.assertEqual(response.status_code, 200)
        for text in ("Dados da pessoa", "Equipe", "Grupo de acesso", "Telas que a pessoa pode acessar", "Assim o menu vai aparecer"):
            self.assertContains(response, text)
        self.assertContains(response, "Enviar convite por e-mail")
        self.assertContains(response, "Definir senha provisória")
        for screen in screens.SCREENS:
            self.assertContains(response, f'name="screen_{screen.key}"')
        self.assertEqual(len(response.context["group_cards"]), 2)
        # o grupo "Colaborador" já vem escolhido, com as telas dele marcadas
        self.assertEqual(response.context["selection"]["group"], self.colaborador.pk)
        self.assertEqual(response.context["selection"]["levels"]["tarefas"], screens.EDIT)

    # -- criar --------------------------------------------------------

    def test_create_with_an_invitation(self):
        response = self.create()
        self.assertRedirects(response, reverse("user-list"))
        user = User.objects.get(email="maria@empresa.com")
        self.assertEqual((user.first_name, user.username), ("Maria Oliveira", "maria"))
        self.assertFalse(user.has_usable_password())
        self.assertTrue(user.is_active)
        self.assertEqual(user.profile.organization, self.org)
        self.assertEqual(user.profile.phone, "(11) 99999-0000")
        self.assertEqual(user.profile.main_sector, self.projetos)
        self.assertFalse(user.profile.must_change_password)
        # equipe
        membership = UserSector.objects.get(user=user, removed_at__isnull=True)
        self.assertEqual((membership.sector, membership.role), (self.projetos, UserSector.Role.MEMBRO))
        # grupo e "vale para"
        assignment = UserProfile.objects.get(user=user, is_active=True)
        self.assertEqual(assignment.profile, self.colaborador)
        self.assertEqual(assignment.scope.relation, Scope.Relation.MEUS_SETORES)
        # convite
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["maria@empresa.com"])
        self.assertIn("/accounts/redefinir-senha/", mail.outbox[0].body)
        actions = set(AuditLog.objects.filter(target_user=user).values_list("action", flat=True))
        self.assertLessEqual(
            {AuditLog.Action.USER_CREATED, AuditLog.Action.USER_INVITED, AuditLog.Action.PROFILE_ASSIGNED,
             AuditLog.Action.SECTORS_CHANGED},
            actions,
        )

    def test_the_invitation_link_lets_the_person_choose_a_password_and_log_in(self):
        self.create()
        link = next(line for line in mail.outbox[0].body.splitlines() if "/accounts/redefinir-senha/" in line)
        path = link[link.index("/accounts/"):].strip()
        self.client.logout()
        response = self.client.get(path, follow=True)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(response.request["PATH_INFO"], {"new_password1": "Senha-boa-9876", "new_password2": "Senha-boa-9876"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.login(username="maria@empresa.com", password="Senha-boa-9876"))

    def test_create_with_a_provisional_password_forces_a_change(self):
        response = self.create(
            first_access="password", password1="Provisoria-123", password2="Provisoria-123"
        )
        self.assertRedirects(response, reverse("user-list"))
        user = User.objects.get(email="maria@empresa.com")
        self.assertTrue(user.check_password("Provisoria-123"))
        self.assertTrue(user.profile.must_change_password)
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.USER_CREATED, target_user=user).exists())

    def test_username_is_derived_from_the_email_and_kept_unique(self):
        self.create()
        self.create(email="maria@outra.com", first_name="Maria Dois")
        self.assertEqual(
            sorted(User.objects.filter(email__startswith="maria@").values_list("username", flat=True)),
            ["maria", "maria2"],
        )

    def test_a_chosen_username_is_respected(self):
        self.create(username="m.oliveira")
        self.assertTrue(User.objects.filter(username="m.oliveira").exists())

    def test_validation_errors_save_nothing_and_keep_what_was_typed(self):
        self.person("ana", email="maria@empresa.com")
        response = self.create()
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.filter(first_name="Maria Oliveira").count(), 0)
        self.assertEqual(response.context["selection"]["teams"], [self.projetos.pk])
        self.assertEqual(response.context["selection"]["group"], self.colaborador.pk)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_is_unique_regardless_of_case_because_login_is_by_email(self):
        self.person("ana", email="Maria@Empresa.com")
        self.assertIn("email", self.create().context["form"].errors)

    def test_a_group_is_required_for_a_new_person(self):
        response = self.create(group="")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Escolha um grupo de acesso", status_code=400)
        self.assertFalse(User.objects.filter(email="maria@empresa.com").exists())

    def test_a_group_from_another_organization_is_not_accepted(self):
        foreign = AccessProfile.objects.create(organization=self.other_org, name="Alheio")
        response = self.create(group=foreign.pk)
        self.assertEqual(response.status_code, 400)

    def test_teams_from_another_organization_are_ignored(self):
        foreign = Sector.objects.create(organization=self.other_org, name="Alheio")
        self.create(teams=[self.projetos.pk, foreign.pk])
        user = User.objects.get(email="maria@empresa.com")
        self.assertEqual(
            list(UserSector.objects.filter(user=user, removed_at__isnull=True).values_list("sector", flat=True)),
            [self.projetos.pk],
        )

    def test_password_rules_apply_to_the_provisional_password(self):
        weak = self.create(first_access="password", password1="123", password2="123")
        self.assertIn("password1", weak.context["form"].errors)
        different = self.create(first_access="password", password1="Provisoria-123", password2="Outra-123456")
        self.assertIn("password2", different.context["form"].errors)
        missing = self.create(first_access="password")
        self.assertIn("password1", missing.context["form"].errors)
        self.assertFalse(User.objects.filter(email="maria@empresa.com").exists())

    def test_team_roles_and_main_team(self):
        self.create(
            teams=[self.projetos.pk, self.orcamentos.pk],
            **{f"role_{self.projetos.pk}": "MEMBRO", f"role_{self.orcamentos.pk}": "GESTOR"},
            main_sector=self.orcamentos.pk,
        )
        user = User.objects.get(email="maria@empresa.com")
        roles = {m.sector.name: m.role for m in UserSector.objects.filter(user=user, removed_at__isnull=True)}
        self.assertEqual(roles, {"Projetos": "MEMBRO", "Orçamentos": "GESTOR"})
        self.assertEqual(user.profile.main_sector, self.orcamentos)

    def test_the_main_team_falls_back_to_a_selected_team(self):
        self.create(main_sector=self.orcamentos.pk)  # não selecionada
        user = User.objects.get(email="maria@empresa.com")
        self.assertEqual(user.profile.main_sector, self.projetos)
        self.create(email="b@empresa.com", teams=[])
        self.assertIsNone(User.objects.get(email="b@empresa.com").profile.main_sector)

    def test_individual_adjustments_become_direct_grants(self):
        self.create(**{"screen_clientes": "editar", "screen_tarefas": "editar"})
        user = User.objects.get(email="maria@empresa.com")
        self.assertTrue(AuthorizationService.can(user, catalog.CLIENTE_GERIR))
        grants = set(UserAction.objects.filter(user=user, is_active=True).values_list("action__key", flat=True))
        self.assertIn(catalog.CLIENTE_GERIR, grants)
        self.assertNotIn(catalog.TAREFA_INICIAR, grants)  # já vinha do grupo

    def test_cannot_go_below_the_group(self):
        self.create(**{"screen_tarefas": "none"})
        user = User.objects.get(email="maria@empresa.com")
        from acessos.screen_services import UserAccessService

        self.assertEqual(UserAccessService.state(user)["levels"]["tarefas"], screens.EDIT)

    def test_creating_is_all_or_nothing(self):
        from unittest import mock

        with mock.patch("core.access_views.UserAccessService.apply", side_effect=__import__("acessos.screen_services", fromlist=["GroupError"]).GroupError("falhou")):
            response = self.create()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="maria@empresa.com").exists())
        self.assertFalse(UserSector.objects.filter(sector=self.projetos).exists())

    def test_without_permission_to_manage_access_the_person_is_saved_without_a_group(self):
        creator = make_user("criador", self.org, [catalog.USUARIO_CRIAR, catalog.USUARIO_EDITAR])
        self.client.force_login(creator)
        response = self.client.get(reverse("user-create"))
        self.assertFalse(response.context["can_manage_access"])
        self.assertContains(response, "não alterar, o grupo")
        self.create(group=self.gestor.pk, **{"screen_clientes": "editar"})
        user = User.objects.get(email="maria@empresa.com")
        self.assertFalse(UserProfile.objects.filter(user=user).exists())
        self.assertFalse(UserAction.objects.filter(user=user).exists())

    # -- editar -------------------------------------------------------

    def edit_url(self, user):
        return reverse("user-edit", args=[user.pk])

    def edit_payload(self, user, **overrides):
        data = self.payload(
            first_name=user.first_name, email=user.email, username=user.username, first_access="keep"
        )
        data.update(overrides)
        return data

    def test_the_edit_page_shows_what_the_person_has_today(self):
        ana = self.person("ana", groups=[self.colaborador], teams=[self.projetos])
        ana.profile.main_sector = self.projetos
        ana.profile.save()
        grant_action(ana, catalog.CLIENTE_GERIR, organization=self.org)
        response = self.client.get(self.edit_url(ana))
        selection = response.context["selection"]
        self.assertEqual(selection["group"], self.colaborador.pk)
        self.assertEqual(selection["teams"], [self.projetos.pk])
        self.assertEqual(selection["main"], self.projetos.pk)
        self.assertEqual(selection["scope"], "teams")
        self.assertEqual(selection["levels"]["clientes"], screens.EDIT)
        row = next(r for s in response.context["sections"] for r in s["rows"] if r["screen"].key == "clientes")
        self.assertTrue(row["individual"])
        self.assertEqual(response.context["counts"]["individual"], 1)
        self.assertContains(response, "Ajuste individual")
        self.assertContains(response, "Voltar ao padrão do grupo")

    def test_editing_without_changing_anything_keeps_every_access(self):
        ana = self.person("ana", groups=[self.colaborador], teams=[self.projetos])
        ana.set_password("senha-antiga-1")
        ana.save()
        grant_action(ana, catalog.CLIENTE_GERIR, organization=self.org)
        grant_action(ana, catalog.TAREFA_REABRIR, sector=self.projetos)  # exceção manual, escopo de setor
        before = (
            UserProfile.objects.filter(user=ana, is_active=True).count(),
            sorted(UserAction.objects.filter(user=ana, is_active=True).values_list("pk", flat=True)),
        )
        response = self.client.post(
            self.edit_url(ana), self.edit_payload(ana, teams=[self.projetos.pk], **{
                "screen_clientes": "editar", "scope": "teams",
                **{f"screen_{s.key}": lvl for s, lvl in self._levels_of(ana).items()},
            })
        )
        self.assertRedirects(response, reverse("user-list"))
        ana.refresh_from_db()
        self.assertTrue(ana.check_password("senha-antiga-1"))
        after = (
            UserProfile.objects.filter(user=ana, is_active=True).count(),
            sorted(UserAction.objects.filter(user=ana, is_active=True).values_list("pk", flat=True)),
        )
        self.assertEqual(before, after)
        self.assertEqual(len(mail.outbox), 0)

    def _levels_of(self, user):
        from acessos.screen_services import UserAccessService

        state = UserAccessService.state(user)
        return {screens.SCREEN_BY_KEY[key]: level for key, level in state["levels"].items()}

    def test_change_the_group_and_drop_an_individual_adjustment(self):
        ana = self.person("ana", groups=[self.colaborador], teams=[self.projetos])
        grant_action(ana, catalog.CLIENTE_GERIR, organization=self.org)
        response = self.client.post(
            self.edit_url(ana),
            self.edit_payload(ana, group=self.gestor.pk, **{"screen_clientes": "none"}),
        )
        self.assertRedirects(response, reverse("user-list"))
        self.assertEqual(UserProfile.objects.get(user=ana, is_active=True).profile, self.gestor)
        self.assertFalse(AuthorizationService.can(ana, catalog.CLIENTE_GERIR))
        self.assertTrue(AuthorizationService.can_anywhere(ana, catalog.METRICAS_VISUALIZAR))

    def test_changing_the_personal_data(self):
        ana = self.person("ana", groups=[self.colaborador])
        self.client.post(self.edit_url(ana), self.edit_payload(ana, first_name="Ana Souza", phone="(21) 90000-0000"))
        ana.refresh_from_db()
        self.assertEqual(ana.first_name, "Ana Souza")
        self.assertEqual(ana.profile.phone, "(21) 90000-0000")
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.USER_UPDATED, target_user=ana).exists())

    def test_editing_keeps_the_email_unique_but_lets_the_person_keep_their_own(self):
        ana = self.person("ana")
        bia = self.person("bia")
        ok = self.client.post(self.edit_url(ana), self.edit_payload(ana))
        self.assertEqual(ok.status_code, 302)
        clash = self.client.post(self.edit_url(ana), self.edit_payload(ana, email=bia.email))
        self.assertEqual(clash.status_code, 400)

    def test_leaving_a_team_closes_the_period(self):
        ana = self.person("ana", groups=[self.colaborador], teams=[self.projetos, self.orcamentos])
        self.client.post(self.edit_url(ana), self.edit_payload(ana, teams=[self.orcamentos.pk], main_sector=self.orcamentos.pk))
        active = UserSector.objects.filter(user=ana, removed_at__isnull=True)
        self.assertEqual([m.sector for m in active], [self.orcamentos])
        self.assertTrue(UserSector.objects.filter(user=ana, sector=self.projetos, removed_at__isnull=False).exists())

    def test_inactivating_keeps_the_history_and_the_access_rows(self):
        ana = self.person("ana", groups=[self.colaborador])
        data = self.edit_payload(ana)
        del data["is_active"]
        self.client.post(self.edit_url(ana), data)
        ana.refresh_from_db()
        self.assertFalse(ana.is_active)
        self.assertTrue(UserProfile.objects.filter(user=ana, is_active=True).exists())

    def test_nobody_can_deactivate_their_own_access(self):
        data = self.edit_payload(self.admin, first_access="keep")
        del data["is_active"]
        response = self.client.post(self.edit_url(self.admin), data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("is_active", response.context["form"].errors)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_resending_the_invitation_to_someone_who_never_logged_in(self):
        ana = self.person("ana", groups=[self.colaborador])
        ana.set_unusable_password()
        ana.save()
        response = self.client.get(self.edit_url(ana))
        self.assertTrue(response.context["pending_invite"])
        self.client.post(self.edit_url(ana), self.edit_payload(ana, first_access="invite"))
        self.assertEqual(len(mail.outbox), 1)

    def test_setting_a_provisional_password_on_an_existing_person(self):
        ana = self.person("ana", groups=[self.colaborador])
        self.client.post(
            self.edit_url(ana),
            self.edit_payload(ana, first_access="password", password1="Provisoria-123", password2="Provisoria-123"),
        )
        ana.refresh_from_db()
        self.assertTrue(ana.check_password("Provisoria-123"))
        self.assertTrue(ana.profile.must_change_password)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.PASSWORD_RESET, target_user=ana).exists())

    def test_a_person_with_two_groups_keeps_both(self):
        ana = self.person("ana", groups=[self.colaborador, self.gestor], teams=[self.projetos])
        response = self.client.get(self.edit_url(ana))
        self.assertTrue(response.context["complex"])
        self.assertContains(response, "2 grupos atribuídos")
        self.client.post(
            self.edit_url(ana),
            self.edit_payload(ana, first_name="Ana Nova", group=self.gestor.pk, scope="org", **{"screen_clientes": "editar"}),
        )
        ana.refresh_from_db()
        self.assertEqual(ana.first_name, "Ana Nova")
        self.assertEqual(UserProfile.objects.filter(user=ana, is_active=True).count(), 2)
        self.assertFalse(UserAction.objects.filter(user=ana).exists())

    def test_a_custom_scope_assignment_is_kept(self):
        from acessos.services import ScopeService

        ana = self.person("ana", teams=[self.projetos])
        scope = ScopeService.sector_scope(self.projetos)
        UserProfile.objects.create(organization=self.org, user=ana, profile=self.colaborador, scope=scope)
        response = self.client.get(self.edit_url(ana))
        self.assertEqual(response.context["selection"]["scope"], "custom")
        self.assertContains(response, "Personalizado")
        self.client.post(self.edit_url(ana), self.edit_payload(ana, scope="custom", group=self.colaborador.pk))
        self.assertEqual(UserProfile.objects.get(user=ana, is_active=True).scope, scope)

    # -- super usuário -------------------------------------------------

    def test_only_a_platform_administrator_sees_and_changes_the_superuser_flag(self):
        ana = self.person("ana", groups=[self.colaborador])
        self.assertNotContains(self.client.get(self.edit_url(ana)), "is_superuser_field")
        self.client.post(self.edit_url(ana), self.edit_payload(ana, is_superuser="on", is_superuser_field="1"))
        ana.refresh_from_db()
        self.assertFalse(ana.is_superuser)

    def test_a_superuser_can_hand_out_and_take_back_the_flag(self):
        root = self.person("root")
        root.is_superuser = True
        root.save()
        self.client.force_login(root)
        ana = self.person("ana", groups=[self.colaborador])
        self.assertContains(self.client.get(self.edit_url(ana)), "is_superuser_field")
        self.client.post(self.edit_url(ana), self.edit_payload(ana, is_superuser="on", is_superuser_field="1"))
        ana.refresh_from_db()
        self.assertTrue(ana.is_superuser)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.SUPERUSER_CHANGED, target_user=ana).exists())
        # tirar: o grupo passa a valer
        self.client.post(self.edit_url(ana), self.edit_payload(ana, is_superuser_field="1"))
        ana.refresh_from_db()
        self.assertFalse(ana.is_superuser)
        self.assertEqual(AuditLog.objects.filter(action=AuditLog.Action.SUPERUSER_CHANGED, target_user=ana).count(), 2)

    def test_the_last_superuser_cannot_be_removed(self):
        root = self.person("root")
        root.is_superuser = True
        root.save()
        self.client.force_login(root)
        response = self.client.post(self.edit_url(root), self.edit_payload(root, is_superuser_field="1"))
        self.assertEqual(response.status_code, 400)
        root.refresh_from_db()
        self.assertTrue(root.is_superuser)

    def test_a_superuser_can_be_created_without_a_group(self):
        root = self.person("root")
        root.is_superuser = True
        root.save()
        self.client.force_login(root)
        response = self.create(group="", is_superuser="on", is_superuser_field="1")
        self.assertRedirects(response, reverse("user-list"))
        self.assertTrue(User.objects.get(email="maria@empresa.com").is_superuser)

    def test_a_superuser_is_told_so_on_the_page(self):
        ana = self.person("ana", groups=[self.colaborador])
        ana.is_superuser = True
        ana.save()
        self.assertContains(self.client.get(self.edit_url(ana)), "Esta pessoa enxerga e faz tudo")

    # -- trancar a si mesmo -----------------------------------------------

    def test_nobody_can_lock_themselves_out_of_the_users_screen(self):
        me = make_user("eu", self.org, [catalog.USUARIO_EDITAR, catalog.USUARIO_VISUALIZAR, catalog.SEGURANCA_GERIR_AUTORIZACOES])
        me.first_name = "Eu"
        me.save()
        everything = make_profile(self.org, "Tudo", [catalog.USUARIO_EDITAR, catalog.USUARIO_VISUALIZAR, catalog.SEGURANCA_GERIR_AUTORIZACOES])
        UserAction.objects.filter(user=me).update(is_active=False)
        assign_profile(me, everything)
        self.client.force_login(me)
        response = self.client.post(
            self.edit_url(me), self.edit_payload(me, group=self.colaborador.pk, scope="org")
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "tiraria o seu próprio acesso", status_code=400)
        self.assertEqual(UserProfile.objects.get(user=me, is_active=True).profile, everything)


# ---------------------------------------------------------------------------
# Grupos
# ---------------------------------------------------------------------------


class AccessGroupsTests(AccessTestCase):
    def test_needs_the_groups_permission(self):
        self.client.force_login(make_user("sem", self.org))
        for name in ("access-groups", "access-groups-compare"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_lists_the_groups_with_people_and_screens(self):
        ana = self.person("ana", groups=[self.colaborador])
        self.assertIsNotNone(ana)
        response = self.client.get(reverse("access-groups"), {"grupo": self.colaborador.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["group"], self.colaborador)
        item = next(i for i in response.context["items"] if i["group"] == self.colaborador)
        self.assertEqual((item["group"].user_count, item["screens"]), (1, 4))
        self.assertEqual(response.context["people"], 1)
        self.assertContains(response, "Alterações valem para <strong>1 pessoa</strong>")
        self.assertContains(response, "4</strong> de 21 telas liberadas", html=False)
        self.assertEqual(
            {r["screen"].key for s in response.context["sections"] for r in s["rows"]},
            {s.key for s in screens.SCREENS},
        )

    def test_the_first_group_opens_by_default_and_a_wrong_id_falls_back(self):
        self.assertEqual(self.client.get(reverse("access-groups")).context["group"], self.colaborador)
        self.assertEqual(self.client.get(reverse("access-groups"), {"grupo": "9999"}).context["group"], self.colaborador)
        foreign = AccessProfile.objects.create(organization=self.other_org, name="Alheio")
        self.assertEqual(
            self.client.get(reverse("access-groups"), {"grupo": foreign.pk}).context["group"], self.colaborador
        )

    def test_empty_state(self):
        AccessProfile.objects.all().delete()
        self.assertContains(self.client.get(reverse("access-groups")), "Crie o primeiro grupo")

    def test_save_changes_only_the_screens_that_changed(self):
        self.person("ana", groups=[self.colaborador])
        levels = {f"screen_{key}": level for key, level in profile_levels(self.colaborador).items()}
        levels["screen_clientes"] = "editar"
        levels["screen_inicio"] = "none"
        response = self.client.post(
            reverse("access-group-save", args=[self.colaborador.pk]),
            {"name": "Colaborador", "description": "", **levels},
        )
        self.assertRedirects(response, f"{reverse('access-groups')}?grupo={self.colaborador.pk}")
        keys = profile_action_keys(self.colaborador)
        self.assertIn(catalog.CLIENTE_GERIR, keys)
        self.assertNotIn(catalog.TELA_INICIO, keys)
        self.assertIn(catalog.TAREFA_INICIAR, keys)
        messages = [str(m) for m in response.wsgi_request._messages]
        self.assertIn("A mudança já vale para 1 pessoa", messages[0])

    def test_saving_a_screen_changes_what_the_people_in_it_can_do_right_away(self):
        ana = self.person("ana", groups=[self.colaborador], teams=[self.projetos])
        self.assertFalse(AuthorizationService.can_anywhere(ana, catalog.METRICAS_VISUALIZAR))
        levels = {f"screen_{key}": level for key, level in profile_levels(self.colaborador).items()}
        levels["screen_visao_gestor"] = "ver"
        self.client.post(reverse("access-group-save", args=[self.colaborador.pk]), {"name": "Colaborador", **levels})
        self.assertTrue(AuthorizationService.can_anywhere(ana, catalog.METRICAS_VISUALIZAR))

    def test_rename(self):
        self.client.post(
            reverse("access-group-save", args=[self.colaborador.pk]), {"name": "Operação", "description": "Quem executa"}
        )
        self.colaborador.refresh_from_db()
        self.assertEqual((self.colaborador.name, self.colaborador.description), ("Operação", "Quem executa"))

    def test_a_duplicate_name_is_refused_and_nothing_else_is_saved(self):
        levels = {f"screen_{key}": "none" for key in profile_levels(self.colaborador)}
        response = self.client.post(
            reverse("access-group-save", args=[self.colaborador.pk]), {"name": "Gestor de setor", **levels}
        )
        self.assertEqual(response.status_code, 302)
        self.colaborador.refresh_from_db()
        self.assertEqual(self.colaborador.name, "Colaborador")
        self.assertIn(catalog.TAREFA_INICIAR, profile_action_keys(self.colaborador))

    def test_without_the_authorization_permission_the_page_is_read_only(self):
        viewer = make_user("viewer", self.org, [catalog.SEGURANCA_GERIR_PERFIS])
        self.client.force_login(viewer)
        response = self.client.get(reverse("access-groups"))
        self.assertTrue(response.context["read_only"])
        self.assertNotContains(response, "Salvar grupo")
        self.assertNotContains(response, "Novo grupo")
        before = profile_action_keys(self.colaborador)
        post = self.client.post(
            reverse("access-group-save", args=[self.colaborador.pk]),
            {"name": "X", **{f"screen_{k}": "editar" for k in profile_levels(self.colaborador)}},
        )
        self.assertRedirects(post, reverse("access-groups") + f"?grupo={self.colaborador.pk}")
        self.assertEqual(profile_action_keys(self.colaborador), before)
        self.assertEqual([str(m) for m in post.wsgi_request._messages], ["Você não tem permissão para alterar grupos."])

    def test_another_organizations_group_is_a_404(self):
        foreign = AccessProfile.objects.create(organization=self.other_org, name="Alheio")
        self.assertEqual(self.client.post(reverse("access-group-save", args=[foreign.pk]), {"name": "x"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("access-group-inactivate", args=[foreign.pk])).status_code, 404)

    def test_creating_a_group_blank_or_from_another(self):
        response = self.client.post(reverse("access-group-create"), {"name": "Orçamentistas", "description": "Orçamentos"})
        created = AccessProfile.objects.get(organization=self.org, name="Orçamentistas")
        self.assertRedirects(response, f"{reverse('access-groups')}?grupo={created.pk}")
        self.assertEqual(profile_action_keys(created), set())
        self.client.post(reverse("access-group-create"), {"name": "Cópia", "copy_from": self.gestor.pk})
        copy = AccessProfile.objects.get(name="Cópia")
        self.assertEqual(profile_action_keys(copy), profile_action_keys(self.gestor))

    def test_cannot_copy_from_another_organization(self):
        foreign = AccessProfile.objects.create(organization=self.other_org, name="Alheio")
        response = self.client.post(reverse("access-group-create"), {"name": "Cópia", "copy_from": foreign.pk})
        self.assertEqual(response.status_code, 404)

    def test_creating_with_an_existing_name_shows_the_reason(self):
        response = self.client.post(reverse("access-group-create"), {"name": "colaborador"}, follow=True)
        self.assertContains(response, "Já existe um perfil chamado")

    def test_inactivate(self):
        spare = make_profile(self.org, "Sobra", [])
        self.client.post(reverse("access-group-inactivate", args=[spare.pk]))
        spare.refresh_from_db()
        self.assertFalse(spare.is_active)
        self.person("ana", groups=[self.colaborador])
        response = self.client.post(reverse("access-group-inactivate", args=[self.colaborador.pk]), follow=True)
        self.assertContains(response, "ainda usa este grupo")
        self.colaborador.refresh_from_db()
        self.assertTrue(self.colaborador.is_active)

    def test_an_administrator_is_stopped_from_removing_their_own_access(self):
        admins = make_profile(self.org, "Admins", [catalog.SEGURANCA_GERIR_PERFIS, catalog.SEGURANCA_GERIR_AUTORIZACOES])
        UserAction.objects.filter(user=self.admin).update(is_active=False)
        assign_profile(self.admin, admins)
        levels = {f"screen_{k}": v for k, v in profile_levels(admins).items()}
        levels["screen_grupos"] = "none"
        response = self.client.post(reverse("access-group-save", args=[admins.pk]), {"name": "Admins", **levels}, follow=True)
        self.assertContains(response, "Você perderia o acesso a Grupos de acesso")
        self.assertIn(catalog.SEGURANCA_GERIR_AUTORIZACOES, profile_action_keys(admins))

    def test_compare(self):
        response = self.client.get(reverse("access-groups-compare"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([g.name for g in response.context["groups"]], ["Colaborador", "Gestor de setor"])
        self.assertContains(response, "Comparar grupos")
        self.assertContains(response, "Visão do gestor")

    def test_compare_can_show_only_the_differences(self):
        everything = self.client.get(reverse("access-groups-compare"))
        only = self.client.get(reverse("access-groups-compare"), {"so_diferencas": "1"})
        count = lambda r: sum(len(s["rows"]) for s in r.context["sections"])  # noqa: E731
        self.assertLess(count(only), count(everything))
        self.assertTrue(only.context["only_diff"])
        for section in only.context["sections"]:
            self.assertTrue(all(row["differs"] for row in section["rows"]))


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------


class MenuTests(AccessTestCase):
    def html(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("home")).content.decode()

    def test_each_item_follows_the_screen_level(self):
        ana = self.person("ana", groups=[self.colaborador])
        html = self.html(ana)
        self.assertIn(">Início<", html)
        self.assertIn(">Tarefas<", html)
        self.assertIn(">Demandas<", html)
        self.assertIn(">Notificações<", html)
        self.assertNotIn(">Visão do gestor<", html)
        self.assertNotIn(">Usuários<", html)
        self.assertNotIn(">Grupos de acesso<", html)
        self.assertNotIn("Administração", html)
        self.assertNotIn(">Insights<", html)

    def test_removing_a_screen_from_the_group_removes_the_menu_item_everywhere(self):
        ana = self.person("ana", groups=[self.colaborador])
        self.assertIn(">Demandas<", self.html(ana))
        levels = {f"screen_{k}": v for k, v in profile_levels(self.colaborador).items()}
        levels["screen_demandas"] = "none"
        self.client.force_login(self.admin)
        self.client.post(reverse("access-group-save", args=[self.colaborador.pk]), {"name": "Colaborador", **levels})
        self.assertNotIn(">Demandas<", self.html(ana))

    def test_management_and_administration_sections(self):
        gestor = self.person("gestor", groups=[self.gestor])
        html = self.html(gestor)
        self.assertIn(">Visão do gestor<", html)  # tem métricas
        self.assertNotIn(">Equipe<", html)  # mas não a tela de Equipe
        self.assertNotIn("Administração", html)
        html = self.html(self.admin)
        self.assertIn("Administração", html)
        self.assertIn(">Usuários<", html)
        self.assertIn(">Grupos de acesso<", html)
        self.assertNotIn("Perfis e permissões", html)

    def test_a_superuser_sees_the_whole_menu(self):
        root = self.person("root")
        root.is_superuser = True
        root.save()
        html = self.html(root)
        for label in ("Início", "Demandas", "Tarefas", "Visão do gestor", "Usuários", "Grupos de acesso", "Integrações", "Insights"):
            self.assertIn(label, html)

    def test_registers_appear_one_by_one(self):
        ana = self.person("ana", groups=[make_profile(self.org, "Cadastros", [catalog.TELA_CLIENTES, catalog.TELA_OBRAS])])
        html = self.html(ana)
        self.assertIn("?tab=clientes", html)
        self.assertIn("?tab=obras", html)
        self.assertNotIn("?tab=empresas", html)
        self.assertNotIn("?tab=setores", html)

    def test_screen_levels_reach_the_template_context(self):
        ana = self.person("ana", groups=[self.colaborador])
        self.client.force_login(ana)
        nav = self.client.get(reverse("home")).context["lps_nav"]
        self.assertEqual(nav["screens"]["tarefas"], "editar")
        self.assertEqual(nav["screens"]["usuarios"], "")
        self.assertFalse(nav["administration"])
        self.assertFalse(nav["management"])
