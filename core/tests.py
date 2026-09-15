from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserSector

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

    def test_readding_reactivates_instead_of_duplicating(self):
        """O UniqueConstraint é incondicional: precisa reativar a linha existente."""
        UserSectorService.add(self.user, self.sector)
        UserSectorService.remove(self.user, self.sector)
        UserSectorService.add(self.user, self.sector)

        self.assertEqual(UserSector.objects.filter(user=self.user, sector=self.sector).count(), 1)
        membership = UserSector.objects.get(user=self.user, sector=self.sector)
        self.assertIsNone(membership.removed_at)

    def test_removing_someone_who_is_not_a_member_fails(self):
        with self.assertRaises(CadastroError):
            UserSectorService.remove(self.user, self.sector)
