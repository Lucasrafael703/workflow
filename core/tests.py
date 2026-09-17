import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserSector
from acessos import catalog
from acessos.testing import grant_action

from .models import Organization, Sector
from .services import CadastroError, SectorService, UserSectorService

User = get_user_model()


class SectorServiceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Instaladora X")
        self.user = User.objects.create_user("admin", password="x")

    def test_create_sector(self):
        sector = SectorService.create(self.org, "Compras", self.user)
        self.assertEqual(sector.name, "Compras")
        self.assertTrue(sector.is_active)

    def test_duplicate_name_is_blocked_ignoring_case(self):
        SectorService.create(self.org, "Financeiro", self.user)
        with self.assertRaises(CadastroError):
            SectorService.create(self.org, "  financeiro ", self.user)

    def test_similar_names_are_allowed(self):
        SectorService.create(self.org, "Financeiro", self.user)
        sector = SectorService.create(self.org, "Financeiro e Administrativo", self.user)
        self.assertIsNotNone(sector.pk)

    def test_same_name_in_another_organization_is_allowed(self):
        SectorService.create(self.org, "Compras", self.user)
        sector = SectorService.create(self.other_org, "Compras", self.user)
        self.assertEqual(sector.organization, self.other_org)

    def test_empty_name_is_rejected(self):
        with self.assertRaises(CadastroError):
            SectorService.create(self.org, "   ", self.user)

    def test_deactivate_preserves_the_record(self):
        sector = SectorService.create(self.org, "Compras", self.user)
        SectorService.deactivate(sector)
        sector.refresh_from_db()
        self.assertFalse(sector.is_active)
        self.assertTrue(Sector.objects.filter(pk=sector.pk).exists())


class UserSectorServiceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.sector = Sector.objects.create(organization=self.org, name="Compras")
        self.user = User.objects.create_user("ryan", password="x")

    def test_add_and_remove_membership(self):
        UserSectorService.add(self.user, self.sector)
        self.assertTrue(
            UserSector.objects.filter(
                user=self.user, sector=self.sector, removed_at__isnull=True
            ).exists()
        )

        UserSectorService.remove(self.user, self.sector)
        membership = UserSector.objects.get(user=self.user, sector=self.sector)
        self.assertIsNotNone(membership.removed_at)

    def test_readding_opens_a_new_period_preserving_history(self):
        """Sair e voltar gera um novo período; quando a pessoa saiu continua registrado."""
        UserSectorService.add(self.user, self.sector)
        UserSectorService.remove(self.user, self.sector)
        UserSectorService.add(self.user, self.sector)

        memberships = UserSector.objects.filter(user=self.user, sector=self.sector)
        self.assertEqual(memberships.count(), 2)
        self.assertEqual(memberships.filter(removed_at__isnull=True).count(), 1)
        self.assertEqual(memberships.filter(removed_at__isnull=False).count(), 1)

    def test_manager_role_is_recorded(self):
        """Ser gestor é vínculo estrutural, não autorização (Regras 05 §10)."""
        UserSectorService.add(self.user, self.sector, role=UserSector.Role.GESTOR)
        membership = UserSector.objects.get(user=self.user, sector=self.sector, removed_at__isnull=True)
        self.assertEqual(membership.role, UserSector.Role.GESTOR)

    def test_removing_someone_who_is_not_a_member_fails(self):
        with self.assertRaises(CadastroError):
            UserSectorService.remove(self.user, self.sector)


class PersonSearchViewTests(TestCase):
    """Busca usada pelo seletor de pessoa (substitui dropdown de usuário)."""

    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Instaladora X")

        self.searcher = User.objects.create_user("paulo", password="x")
        self.searcher.profile.organization = self.org
        self.searcher.profile.save(update_fields=["organization"])

        self.jennifer = User.objects.create_user("jennifer", password="x", first_name="Jennifer")
        self.jennifer.profile.organization = self.org
        self.jennifer.profile.save(update_fields=["organization"])

        self.inactive = User.objects.create_user("ex-func", password="x", is_active=False)
        self.inactive.profile.organization = self.org
        self.inactive.profile.save(update_fields=["organization"])

        self.outsider = User.objects.create_user("de-outra-empresa", password="x")
        self.outsider.profile.organization = self.other_org
        self.outsider.profile.save(update_fields=["organization"])

    def _search(self, term=""):
        self.client.force_login(self.searcher)
        response = self.client.get(reverse("person-search"), {"q": term})
        return json.loads(response.content)["results"]

    def test_filters_by_name(self):
        results = self._search("jenni")
        usernames = [r["username"] for r in results]
        self.assertIn("jennifer", usernames)
        self.assertNotIn("paulo", usernames)

    def test_only_returns_people_from_the_same_organization(self):
        results = self._search("outra")
        self.assertEqual(results, [])

    def test_excludes_inactive_users(self):
        results = self._search("ex-func")
        self.assertEqual(results, [])

    def test_empty_term_returns_a_default_list(self):
        results = self._search("")
        usernames = [r["username"] for r in results]
        self.assertIn("paulo", usernames)
        self.assertIn("jennifer", usernames)


class UserFormAjaxTests(TestCase):
    """Criar usuário sem sair da tela (modal via JS) responde JSON; navegação
    normal continua redirecionando como antes."""

    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.admin = User.objects.create_user("admin", password="x")
        self.admin.profile.organization = self.org
        self.admin.profile.save(update_fields=["organization"])
        grant_action(self.admin, catalog.USUARIO_EDITAR, organization=self.org)
        self.client.force_login(self.admin)

    def _payload(self, **overrides):
        data = {
            "first_name": "Nova Pessoa",
            "email": "nova@example.com",
            "username": "novapessoa",
            "is_active": "on",
        }
        data.update(overrides)
        return data

    def test_ajax_request_returns_json_without_redirect(self):
        response = self.client.post(
            reverse("user-create"), self._payload(), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(User.objects.filter(pk=data["id"], username="novapessoa").exists())

    def test_non_ajax_request_still_redirects(self):
        response = self.client.post(reverse("user-create"), self._payload())
        self.assertRedirects(response, reverse("user-list"))

    def test_ajax_invalid_data_returns_json_errors_without_creating_user(self):
        response = self.client.post(
            reverse("user-create"),
            self._payload(username=""),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("username", data["errors"])
        self.assertFalse(User.objects.filter(email="nova@example.com").exists())
