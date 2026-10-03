"""Feature flag do Workspace de Demandas (`WORKSPACE_V2`): off | allowlist | on."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, TestCase, override_settings

from .feature_flags import workspace_v2_enabled, workspace_v2_mode

User = get_user_model()


class WorkspaceFlagTests(TestCase):
    def setUp(self):
        self.paulo = User.objects.create_user("paulo", email="Paulo@Biasi.com.br", password="x")
        self.maria = User.objects.create_user("maria", email="maria@biasi.com.br", password="x")

    def test_default_is_off_for_everyone(self):
        self.assertEqual(workspace_v2_mode(), "off")
        self.assertFalse(workspace_v2_enabled(self.paulo))
        self.assertFalse(workspace_v2_enabled(self.maria))

    @override_settings(WORKSPACE_V2="on")
    def test_on_is_for_every_signed_in_person(self):
        self.assertTrue(workspace_v2_enabled(self.paulo))
        self.assertTrue(workspace_v2_enabled(self.maria))
        self.assertFalse(workspace_v2_enabled(AnonymousUser()))
        self.assertFalse(workspace_v2_enabled(None))

    @override_settings(WORKSPACE_V2="allowlist", WORKSPACE_V2_USERS=["paulo@biasi.com.br"])
    def test_allowlist_matches_the_email_ignoring_case(self):
        self.assertTrue(workspace_v2_enabled(self.paulo))  # o e-mail do usuário tem maiúsculas
        self.assertFalse(workspace_v2_enabled(self.maria))

    @override_settings(WORKSPACE_V2="allowlist", WORKSPACE_V2_USERS=["Maria"])
    def test_allowlist_also_matches_the_username(self):
        self.assertTrue(workspace_v2_enabled(self.maria))
        self.assertFalse(workspace_v2_enabled(self.paulo))

    @override_settings(WORKSPACE_V2="allowlist", WORKSPACE_V2_USERS=[])
    def test_empty_allowlist_is_nobody(self):
        self.assertFalse(workspace_v2_enabled(self.paulo))

    @override_settings(WORKSPACE_V2="allowlist", WORKSPACE_V2_USERS=["", "  "])
    def test_blank_entries_never_match_a_person_without_email(self):
        nobody = User.objects.create_user("sem-email", password="x")  # e-mail vazio
        self.assertFalse(workspace_v2_enabled(nobody))

    @override_settings(WORKSPACE_V2="allowlist", WORKSPACE_V2_USERS=["paulo"])
    def test_anonymous_is_never_enabled(self):
        self.assertFalse(workspace_v2_enabled(AnonymousUser()))


class WorkspaceFlagModeTests(SimpleTestCase):
    def test_unknown_values_mean_off(self):
        for value in ("", "ligado", "true", "1", "ON ", None):
            with override_settings(WORKSPACE_V2=value):
                expected = "on" if str(value).strip().lower() == "on" else "off"
                self.assertEqual(workspace_v2_mode(), expected, repr(value))

    @override_settings(WORKSPACE_V2="  Allowlist ")
    def test_mode_is_normalised(self):
        self.assertEqual(workspace_v2_mode(), "allowlist")
