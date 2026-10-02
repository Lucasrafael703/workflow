import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserSector
from acessos import catalog
from acessos.testing import grant_action

from .models import EnumColor, Organization, Sector, WorkflowStatus
from .services import CadastroError, EnumColorService, SectorService, UserSectorService

User = get_user_model()


class SectorServiceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Instaladora X")
        self.user = User.objects.create_user("admin", password="x")

    def test_create_sector(self):
        sector = SectorService.create(self.org, "Compras", self.user)
        self.assertEqual(sector.name, "Compras")
        self.assertEqual(sector.color, "#3B82F6")
        self.assertTrue(sector.is_active)

    def test_create_and_update_sector_color_from_official_palette(self):
        sector = SectorService.create(self.org, "Compras", self.user, color="#facc15")
        self.assertEqual(sector.color, "#FACC15")
        self.assertEqual(sector.text_color, "#1F2937")

        SectorService.update(sector, color="#0E7490")
        sector.refresh_from_db()
        self.assertEqual(sector.color, "#0E7490")
        self.assertEqual(sector.text_color, "#FFFFFF")

    def test_sector_color_must_belong_to_official_palette(self):
        with self.assertRaises(CadastroError):
            SectorService.create(self.org, "Compras", self.user, color="#123456")

        sector = SectorService.create(self.org, "Compras", self.user)
        with self.assertRaises(CadastroError):
            SectorService.update(sector, color="#123456")

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


class SectorSearchViewTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.user = User.objects.create_user("paulo", password="x")
        self.user.profile.organization = self.org
        self.user.profile.save(update_fields=["organization"])
        self.sector = Sector.objects.create(organization=self.org, name="Comercial", color="#FACC15")
        self.client.force_login(self.user)

    def test_sector_search_returns_color_and_contrast(self):
        response = self.client.get(reverse("sector-search"), {"q": "com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"],
            [{"id": self.sector.pk, "name": "Comercial", "color": "#FACC15", "text_color": "#1F2937"}],
        )


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

    def _search(self, term="", sector=None):
        self.client.force_login(self.searcher)
        params = {"q": term}
        if sector is not None:
            params["sector"] = sector
        response = self.client.get(reverse("person-search"), params)
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

    def test_sector_filter_returns_only_active_members(self):
        sector = Sector.objects.create(organization=self.org, name="Comercial")
        UserSector.objects.create(user=self.jennifer, sector=sector)
        UserSector.objects.create(user=self.searcher, sector=sector, removed_at=timezone.now())
        results = self._search(sector=str(sector.pk))
        usernames = [result["username"] for result in results]
        self.assertEqual(usernames, ["jennifer"])

    def test_sector_filter_rejects_missing_or_invalid_sector(self):
        self.assertEqual(self._search(sector=""), [])
        self.assertEqual(self._search(sector="invalid"), [])


class UserFormAjaxTests(TestCase):
    """Criar usuário sem sair da tela (modal via JS) responde JSON; navegação
    normal continua redirecionando como antes."""

    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.admin = User.objects.create_user("admin", password="x")
        self.admin.profile.organization = self.org
        self.admin.profile.save(update_fields=["organization"])
        grant_action(self.admin, catalog.USUARIO_EDITAR, organization=self.org)
        grant_action(self.admin, catalog.USUARIO_VISUALIZAR, organization=self.org)
        self.client.force_login(self.admin)

    def _payload(self, **overrides):
        data = {
            "organization": self.org.pk,
            "first_name": "Nova Pessoa",
            "email": "nova@example.com",
            "username": "novapessoa",
            "password1": "senha-segura-123",
            "password2": "senha-segura-123",
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


class EnumColorServiceOverrideTests(TestCase):
    """Label/descricao/oculto de status nativos nunca tocam o code real
    gravado em Activity.status/Task.status — so a aparencia resolvida."""

    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.admin = User.objects.create_user("admin", password="x")

    def test_no_override_returns_empty_defaults(self):
        label, description, is_hidden = EnumColorService.get_overrides(self.org, "activity_status", "BLOQUEADA")
        self.assertEqual(label, "")
        self.assertEqual(description, "")
        self.assertFalse(is_hidden)

    def test_set_overrides_persists_label_description_and_hidden(self):
        EnumColorService.set_overrides(
            self.org,
            "activity_status",
            "BLOQUEADA",
            label="Travada",
            description="Impedimento externo",
            is_hidden=True,
            updated_by=self.admin,
        )
        label, description, is_hidden = EnumColorService.get_overrides(self.org, "activity_status", "BLOQUEADA")
        self.assertEqual(label, "Travada")
        self.assertEqual(description, "Impedimento externo")
        self.assertTrue(is_hidden)

    def test_set_overrides_preserves_existing_color(self):
        EnumColorService.set_color(self.org, "activity_status", "BLOQUEADA", "#EF4444", updated_by=self.admin)
        EnumColorService.set_overrides(self.org, "activity_status", "BLOQUEADA", label="Travada")
        row = EnumColor.objects.get(organization=self.org, domain="activity_status", code="BLOQUEADA")
        self.assertEqual(row.color, "#EF4444")
        self.assertEqual(row.label, "Travada")

    def test_set_overrides_rejects_unknown_code(self):
        with self.assertRaises(CadastroError):
            EnumColorService.set_overrides(self.org, "activity_status", "NAO_EXISTE", label="X")

    def test_reset_to_defaults_clears_label_description_and_hidden(self):
        EnumColorService.set_overrides(
            self.org, "activity_status", "BLOQUEADA", label="Travada", description="X", is_hidden=True
        )
        EnumColorService.reset_to_defaults(self.org, domain="activity_status")
        label, description, is_hidden = EnumColorService.get_overrides(self.org, "activity_status", "BLOQUEADA")
        self.assertEqual(label, "")
        self.assertEqual(description, "")
        self.assertFalse(is_hidden)

    def test_list_overrides_for_domain_only_returns_customized_codes(self):
        EnumColorService.set_overrides(self.org, "activity_status", "BLOQUEADA", label="Travada")
        overrides = EnumColorService.list_overrides_for_domain(self.org, "activity_status")
        self.assertEqual(set(overrides), {"BLOQUEADA"})
        self.assertEqual(overrides["BLOQUEADA"]["label"], "Travada")


class EnumColorLabelFormViewTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.admin = User.objects.create_user("admin", password="x")
        self.admin.profile.organization = self.org
        self.admin.profile.save(update_fields=["organization"])
        grant_action(self.admin, catalog.COR_STATUS_GERIR, organization=self.org)
        grant_action(self.admin, catalog.ETAPA_GERIR, organization=self.org)
        grant_action(self.admin, catalog.CONDICAO_GERIR, organization=self.org)
        self.client.force_login(self.admin)

    def test_post_saves_override_and_redirects_to_settings_tab(self):
        url = reverse("enumcolor-label-edit", kwargs={"domain": "activity_status", "code": "BLOQUEADA"})
        response = self.client.post(url, {"label": "Travada", "description": "Impedimento", "is_hidden": "on"})
        self.assertRedirects(response, f"{reverse('config-etapas-status')}?tab=status-demanda")
        label, description, is_hidden = EnumColorService.get_overrides(self.org, "activity_status", "BLOQUEADA")
        self.assertEqual(label, "Travada")
        self.assertEqual(description, "Impedimento")
        self.assertTrue(is_hidden)

    def test_old_tab_addresses_still_open_the_demand_flow(self):
        for old in ("status-atividade", "estagios-atividade", "atividade"):
            with self.subTest(old=old):
                response = self.client.get(reverse("config-etapas-status"), {"tab": old})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["domain"], "demandas")

    def test_unknown_code_is_404(self):
        url = reverse("enumcolor-label-edit", kwargs={"domain": "activity_status", "code": "NAO_EXISTE"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_settings_page_reflects_custom_condition(self):
        sector = Sector.objects.create(organization=self.org, name="Comercial")
        WorkflowStatus.objects.create(
            organization=self.org,
            sector=sector,
            domain=WorkflowStatus.Domain.ACTIVITY,
            name="Travada",
            description="Aguardando retorno externo",
            color="#ef4444",
        )
        response = self.client.get(
            reverse("config-etapas-status"), {"domain": "demandas", "sector": sector.pk}
        )
        self.assertContains(response, "Travada")
        self.assertContains(response, "Aguardando retorno externo")
        self.assertContains(response, "flow-stage-marker")
