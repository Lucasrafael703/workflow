from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserSector
from core.models import Organization, Sector

from .models import QueueEntry, Task
from .services import ActivityService, TaskService

User = get_user_model()


def grant(user, codename):
    user.user_permissions.add(Permission.objects.get(codename=codename))


class ViewTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Instaladora X")
        self.sector = Sector.objects.create(organization=self.org, name="Compras")

        self.member = self._user("membro", self.org)
        UserSector.objects.create(user=self.member, sector=self.sector)

        self.requester = self._user("solicitante", self.org)
        self.outsider = self._user("externo", self.other_org)

        self.activity = ActivityService.create_activity(
            organization=self.org, title="Material na obra", owner=self.requester, created_by=self.requester
        )
        self.task = TaskService.create_task(
            self.activity, self.sector, "Realizar cotação", created_by=self.requester
        )

    def _user(self, username, organization):
        user = User.objects.create_user(username, password="x")
        user.profile.organization = organization
        user.profile.save()
        return user


class OrganizationIsolationViewTests(ViewTestCase):
    def test_user_from_another_organization_cannot_open_activity(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("activity-detail", args=[self.activity.pk]))
        self.assertEqual(response.status_code, 404)

    def test_user_from_another_organization_cannot_open_task(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("task-detail", args=[self.task.pk]))
        self.assertEqual(response.status_code, 404)

    def test_activity_list_only_shows_own_organization(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("activity-list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Material na obra")

    def test_user_without_organization_is_redirected_to_profile(self):
        orphan = User.objects.create_user("sem-org", password="x")
        self.client.force_login(orphan)
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("profile"))


class QueuePrivacyViewTests(ViewTestCase):
    """O solicitante vê a própria posição, nunca o conteúdo alheio (doc 09 §97-99)."""

    def setUp(self):
        super().setUp()
        secret_activity = ActivityService.create_activity(
            organization=self.org, title="Atividade do membro", owner=self.member, created_by=self.member
        )
        self.secret_task = TaskService.create_task(
            secret_activity, self.sector, "TAREFA SIGILOSA", created_by=self.member
        )

    def test_sector_member_sees_full_queue(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertContains(response, "TAREFA SIGILOSA")
        self.assertContains(response, "Realizar cotação")

    def test_requester_never_sees_other_task_titles(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "TAREFA SIGILOSA")

    def test_requester_sees_own_position_and_live_total(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        # Duas tarefas na fila: a própria em 1ª, a do membro em 2ª.
        self.assertContains(response, "Posição: 1 de 2")

    def test_position_total_is_recalculated_after_completion(self):
        TaskService.complete(self.secret_task, self.member)
        self.client.force_login(self.requester)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertContains(response, "Posição: 1 de 1")


class QueueReorderViewTests(ViewTestCase):
    def test_reorder_requires_permission(self):
        entry = QueueEntry.objects.get(task=self.task)
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("queue-reorder", args=[entry.pk]), {"new_position": 1}, follow=True
        )
        self.assertContains(response, "não tem permissão")

    def test_reorder_with_permission_succeeds(self):
        other = TaskService.create_task(
            self.activity, self.sector, "Segunda tarefa", created_by=self.requester
        )
        entry = QueueEntry.objects.get(task=other)
        grant(self.member, "can_reorder_queue")
        self.client.force_login(self.member)

        self.client.post(reverse("queue-reorder", args=[entry.pk]), {"new_position": 1})

        entry.refresh_from_db()
        self.assertEqual(entry.position, 1)


class ManagementViewTests(ViewTestCase):
    def test_management_requires_action(self):
        self.client.force_login(self.requester)
        self.assertEqual(self.client.get(reverse("management")).status_code, 403)

    def test_management_allowed_with_action(self):
        grant(self.member, "can_view_full_queue")
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("management")).status_code, 200)


class TaskActionViewTests(ViewTestCase):
    def test_assume_requires_permission(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("task-assume", args=[self.task.pk]), follow=True)
        self.assertContains(response, "não tem permissão")

    def test_assume_then_start_flow(self):
        grant(self.member, "can_assume_task")
        self.client.force_login(self.member)

        self.client.post(reverse("task-assume", args=[self.task.pk]))
        self.client.post(reverse("task-start", args=[self.task.pk]))

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_EXECUCAO)
        self.assertTrue(self.task.work_sessions.filter(user=self.member, ended_at__isnull=True).exists())

    def test_non_executor_cannot_start(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("task-start", args=[self.task.pk]), follow=True)
        self.assertContains(response, "executores atribuídos")


class TaskAuthorizationTests(ViewTestCase):
    """Nenhuma ação de tarefa pode ficar aberta a qualquer usuário da organização."""

    def setUp(self):
        super().setUp()
        self.stranger = self._user("estranho", self.org)

    def test_stranger_cannot_open_block_form(self):
        self.client.force_login(self.stranger)
        self.assertEqual(
            self.client.get(reverse("task-block", args=[self.task.pk])).status_code, 403
        )

    def test_stranger_cannot_block_task(self):
        self.client.force_login(self.stranger)
        response = self.client.post(
            reverse("task-block", args=[self.task.pk]), {"reason": "Invadido"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.task.blocks.count(), 0)

    def test_stranger_cannot_return_or_move_task(self):
        self.client.force_login(self.stranger)
        for name in ("task-return", "task-move", "task-cancel", "task-manual-time"):
            self.assertEqual(
                self.client.get(reverse(name, args=[self.task.pk])).status_code,
                403,
                msg=name,
            )

    def test_stranger_cannot_post_task_message(self):
        self.client.force_login(self.stranger)
        self.client.post(reverse("task-message", args=[self.task.pk]), {"body": "oi"})
        self.assertEqual(self.task.messages.count(), 0)

    def test_sector_member_may_act(self):
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.get(reverse("task-block", args=[self.task.pk])).status_code, 200
        )

    def test_owner_may_act(self):
        self.client.force_login(self.requester)
        self.assertEqual(
            self.client.get(reverse("task-block", args=[self.task.pk])).status_code, 200
        )

    def test_manual_time_only_for_executors(self):
        grant(self.member, "can_assume_task")
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("task-manual-time", args=[self.task.pk]),
            {"started_at": "2026-09-01T08:00", "ended_at": "2026-09-01T09:00"},
        )
        self.assertContains(response, "executor da tarefa")
        self.assertEqual(self.task.work_sessions.count(), 0)


class ActivityAuthorizationTests(ViewTestCase):
    def test_stranger_cannot_complete_activity(self):
        stranger = self._user("estranho", self.org)
        self.client.force_login(stranger)
        self.client.post(reverse("activity-complete", args=[self.activity.pk]))
        self.activity.refresh_from_db()
        self.assertNotEqual(self.activity.status, "CONCLUIDA")

    def test_stranger_cannot_post_activity_message(self):
        stranger = self._user("estranho", self.org)
        self.client.force_login(stranger)
        self.client.post(reverse("activity-message", args=[self.activity.pk]), {"body": "oi"})
        self.assertEqual(self.activity.messages.count(), 0)


class CadastroAuthorizationTests(ViewTestCase):
    """Cadastro é ação administrativa: exige autorização explícita."""

    def test_plain_user_cannot_deactivate_sector(self):
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("cadastro-toggle", args=["setores", self.sector.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.sector.refresh_from_db()
        self.assertTrue(self.sector.is_active)

    def test_plain_user_cannot_open_sector_form(self):
        self.client.force_login(self.requester)
        self.assertEqual(self.client.get(reverse("sector-create")).status_code, 403)

    def test_authorized_user_can_deactivate_sector(self):
        grant(self.member, "change_sector")
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("cadastro-toggle", args=["setores", self.sector.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.sector.refresh_from_db()
        self.assertFalse(self.sector.is_active)


class ActivityCreateViewTests(ViewTestCase):
    def test_create_activity_through_the_screen(self):
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("activity-create"),
            {"title": "Orçamento entregue ao cliente", "owner": self.requester.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.activity.organization.activities.filter(title="Orçamento entregue ao cliente").exists()
        )

    def test_owner_choices_are_limited_to_the_organization(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("activity-create"))
        owners = response.context["form"].fields["owner"].queryset
        self.assertIn(self.member, owners)
        self.assertNotIn(self.outsider, owners)
