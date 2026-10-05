"""Senha provisória: quem entra com ela escolhe a própria antes de usar qualquer tela."""

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.models import Organization

from .invitations import invitation_link, send_invitation

User = get_user_model()


class ForcedPasswordChangeTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.user = User.objects.create_user("ana", email="ana@empresa.com", password="Provisoria-123", first_name="Ana")
        self.user.profile.organization = self.org
        self.user.profile.must_change_password = True
        self.user.profile.save()
        self.client.force_login(self.user)

    def test_every_page_sends_the_person_to_the_change_screen(self):
        for name in ("home", "user-list", "task-list", "notification-list"):
            response = self.client.get(reverse(name))
            self.assertRedirects(response, reverse("password-change-required"), fetch_redirect_response=False)

    def test_the_change_screen_logout_and_static_files_stay_open(self):
        self.assertEqual(self.client.get(reverse("password-change-required")).status_code, 200)
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)

    def test_choosing_a_password_releases_the_person(self):
        response = self.client.post(
            reverse("password-change-required"),
            {"old_password": "Provisoria-123", "new_password1": "Minha-senha-9876", "new_password2": "Minha-senha-9876"},
        )
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile.must_change_password)
        self.assertTrue(self.user.check_password("Minha-senha-9876"))
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)  # continua logado

    def test_a_wrong_provisional_password_changes_nothing(self):
        response = self.client.post(
            reverse("password-change-required"),
            {"old_password": "errada", "new_password1": "Minha-senha-9876", "new_password2": "Minha-senha-9876"},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile.must_change_password)
        self.assertTrue(self.user.check_password("Provisoria-123"))

    def test_a_weak_new_password_is_refused(self):
        response = self.client.post(
            reverse("password-change-required"),
            {"old_password": "Provisoria-123", "new_password1": "123", "new_password2": "123"},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile.must_change_password)

    def test_someone_who_does_not_need_it_is_sent_home(self):
        self.user.profile.must_change_password = False
        self.user.profile.save()
        self.assertRedirects(
            self.client.get(reverse("password-change-required")), reverse("home"), fetch_redirect_response=False
        )

    def test_anonymous_visitors_are_not_affected(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)


class InvitationTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.admin = User.objects.create_user("admin", first_name="Chefe", password="x")
        self.user = User.objects.create_user("ana", email="ana@empresa.com", first_name="Ana")
        self.user.set_unusable_password()
        self.user.save()
        self.user.profile.organization = self.org
        self.user.profile.save()
        self.request = RequestFactory().get("/", HTTP_HOST="testserver")

    def test_the_link_is_absolute_and_works_for_people_without_a_password(self):
        link = invitation_link(self.request, self.user)
        self.assertTrue(link.startswith("http://testserver/accounts/redefinir-senha/"))
        page = self.client.get(link[len("http://testserver"):], follow=True)
        self.assertEqual(page.status_code, 200)
        self.assertTrue(page.context["validlink"])

    def test_the_email_names_who_invited_and_the_organization(self):
        send_invitation(self.request, self.user, self.admin)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["ana@empresa.com"])
        self.assertIn("Chefe", message.body)
        self.assertIn("Biasi", message.body)
        self.assertIn("Olá, Ana!", message.body)
