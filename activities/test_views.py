from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserSector
from acessos import catalog
from acessos.models import Scope
from acessos.testing import grant_action, grant_actions
from core.models import Organization, Sector

from .models import QueueEntry, Task
from .services import ActivityService, TaskService

User = get_user_model()

# O mínimo para uma pessoa operar: criar o que é seu e enxergar o próprio
# trabalho. Nada além disso — o resto é concedido explicitamente em cada teste.
BASE_ACTIONS = [
    catalog.ATIVIDADE_CRIAR,
    catalog.ATIVIDADE_VISUALIZAR,
    catalog.TAREFA_CRIAR,
    catalog.TAREFA_VISUALIZAR,
    catalog.FILA_VISUALIZAR_POSICAO_PROPRIA,
]


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
            organization=self.org,
            title="Material na obra",
            owner=self.requester,
            created_by=self.requester,
        )
        self.task = TaskService.create_task(
            self.activity, self.sector, "Realizar cotação", created_by=self.requester
        )

    def _user(self, username, organization, actions=BASE_ACTIONS):
        user = User.objects.create_user(username, password="x")
        user.profile.organization = organization
        user.profile.save()
        if actions:
            grant_actions(user, actions, organization=organization)
        return user


class OrganizationIsolationViewTests(ViewTestCase):
    def test_user_from_another_organization_cannot_open_activity(self):
        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(reverse("activity-detail", args=[self.activity.pk])).status_code, 404
        )

    def test_user_from_another_organization_cannot_open_task(self):
        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(reverse("task-detail", args=[self.task.pk])).status_code, 404
        )

    def test_activity_list_only_shows_own_organization(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("activity-list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Material na obra")

    def test_user_without_organization_is_redirected_to_profile(self):
        orphan = User.objects.create_user("sem-org", password="x")
        self.client.force_login(orphan)
        self.assertRedirects(self.client.get(reverse("home")), reverse("profile"))


class QueuePrivacyViewTests(ViewTestCase):
    """O solicitante vê a própria posição, nunca o conteúdo alheio (doc 05 §24)."""

    def setUp(self):
        super().setUp()
        secret_activity = ActivityService.create_activity(
            organization=self.org,
            title="Atividade do membro",
            owner=self.member,
            created_by=self.member,
        )
        self.secret_task = TaskService.create_task(
            secret_activity, self.sector, "TAREFA SIGILOSA", created_by=self.member
        )

    def test_full_queue_requires_the_action(self):
        """Participar do setor não basta: ver a fila inteira é ação autorizada.

        Testado contra a tarefa de outra pessoa — a própria demanda o usuário
        sempre enxerga, com posição e prazo.
        """
        self.client.force_login(self.member)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertNotContains(response, "Realizar cotação")

        grant_action(self.member, catalog.FILA_VISUALIZAR_COMPLETA, sector=self.sector)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertContains(response, "Realizar cotação")
        self.assertContains(response, "TAREFA SIGILOSA")

    def test_requester_never_sees_other_task_titles(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "TAREFA SIGILOSA")

    def test_requester_sees_own_position_and_live_total(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertContains(response, "Posição: 1 de 2")

    def test_position_total_is_recalculated_after_completion(self):
        grant_action(self.member, catalog.TAREFA_CONCLUIR, sector=self.sector)
        TaskService.complete(self.secret_task, self.member)

        self.client.force_login(self.requester)
        response = self.client.get(reverse("queue"), {"sector": self.sector.pk})
        self.assertContains(response, "Posição: 1 de 1")

    def test_queue_permission_does_not_leak_across_sectors(self):
        """Autorização em um setor não vale no outro (doc 05 §19)."""
        other_sector = Sector.objects.create(organization=self.org, name="Engenharia")
        TaskService.create_task(
            self.activity, other_sector, "Tarefa de Engenharia", created_by=self.requester
        )
        grant_action(self.member, catalog.FILA_VISUALIZAR_COMPLETA, sector=self.sector)

        self.client.force_login(self.member)
        response = self.client.get(reverse("queue"), {"sector": other_sector.pk})
        self.assertNotContains(response, "Tarefa de Engenharia")


class QueueReorderViewTests(ViewTestCase):
    def test_reorder_requires_the_action(self):
        entry = QueueEntry.objects.get(task=self.task)
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("queue-reorder", args=[entry.pk]), {"new_position": 1}, follow=True
        )
        self.assertContains(response, "autorização")

    def test_reorder_with_the_action_succeeds(self):
        other = TaskService.create_task(
            self.activity, self.sector, "Segunda tarefa", created_by=self.requester
        )
        entry = QueueEntry.objects.get(task=other)
        grant_action(self.member, catalog.FILA_REORDENAR, sector=self.sector)
        self.client.force_login(self.member)

        self.client.post(reverse("queue-reorder", args=[entry.pk]), {"new_position": 1})

        entry.refresh_from_db()
        self.assertEqual(entry.position, 1)

    def test_reorder_granted_in_one_sector_does_not_apply_to_another(self):
        other_sector = Sector.objects.create(organization=self.org, name="Engenharia")
        other_task = TaskService.create_task(
            self.activity, other_sector, "Tarefa de Engenharia", created_by=self.requester
        )
        entry = QueueEntry.objects.get(task=other_task)
        grant_action(self.member, catalog.FILA_REORDENAR, sector=self.sector)

        self.client.force_login(self.member)
        response = self.client.post(
            reverse("queue-reorder", args=[entry.pk]), {"new_position": 1}, follow=True
        )
        self.assertContains(response, "autorização")


class ManagementViewTests(ViewTestCase):
    def test_management_requires_action(self):
        self.client.force_login(self.requester)
        self.assertEqual(self.client.get(reverse("management")).status_code, 403)

    def test_management_allowed_with_action(self):
        grant_action(self.member, catalog.METRICAS_VISUALIZAR, organization=self.org)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("management")).status_code, 200)


class TaskActionViewTests(ViewTestCase):
    def test_assume_requires_the_action(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("task-assume", args=[self.task.pk]), follow=True)
        self.assertContains(response, "autorização")

    def test_assume_then_start_flow(self):
        grant_actions(
            self.member,
            [catalog.TAREFA_ASSUMIR, catalog.TAREFA_INICIAR],
            sector=self.sector,
        )
        self.client.force_login(self.member)

        self.client.post(reverse("task-assume", args=[self.task.pk]))
        self.client.post(reverse("task-start", args=[self.task.pk]))

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.EM_EXECUCAO)
        self.assertTrue(
            self.task.work_sessions.filter(user=self.member, ended_at__isnull=True).exists()
        )

    def test_non_executor_cannot_start_even_with_the_action(self):
        """Autorização não substitui regra de negócio (doc 05 §30, §212)."""
        grant_action(self.member, catalog.TAREFA_INICIAR, sector=self.sector)
        self.client.force_login(self.member)
        response = self.client.post(reverse("task-start", args=[self.task.pk]), follow=True)
        self.assertContains(response, "executores atribuídos")


class TaskAuthorizationTests(ViewTestCase):
    """Nenhuma ação de tarefa fica aberta a qualquer usuário da organização."""

    def test_stranger_cannot_open_block_form(self):
        self.client.force_login(self.requester)
        self.assertEqual(
            self.client.get(reverse("task-block", args=[self.task.pk])).status_code, 403
        )

    def test_stranger_cannot_block_task(self):
        self.client.force_login(self.requester)
        response = self.client.post(
            reverse("task-block", args=[self.task.pk]), {"reason": "Invadido"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.task.blocks.count(), 0)

    def test_stranger_cannot_reach_other_task_actions(self):
        self.client.force_login(self.requester)
        for name in ("task-return", "task-move", "task-cancel", "task-manual-time"):
            self.assertEqual(
                self.client.get(reverse(name, args=[self.task.pk])).status_code, 403, msg=name
            )

    def test_stranger_cannot_post_task_message(self):
        self.client.force_login(self.requester)
        self.client.post(reverse("task-message", args=[self.task.pk]), {"body": "oi"})
        self.assertEqual(self.task.messages.count(), 0)

    def test_authorized_user_may_block(self):
        grant_action(self.member, catalog.TAREFA_BLOQUEAR, sector=self.sector)
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.get(reverse("task-block", args=[self.task.pk])).status_code, 200
        )

    def test_relational_scope_lets_the_owner_act_on_own_activity(self):
        """Escopo relacional "minhas atividades" (doc 05 §22)."""
        grant_action(
            self.requester,
            catalog.TAREFA_BLOQUEAR,
            organization=self.org,
            relation=Scope.Relation.MINHAS_ATIVIDADES,
        )
        self.client.force_login(self.requester)
        self.assertEqual(
            self.client.get(reverse("task-block", args=[self.task.pk])).status_code, 200
        )

    def test_relational_scope_does_not_reach_other_peoples_activities(self):
        other_activity = ActivityService.create_activity(
            organization=self.org, title="De outra pessoa", owner=self.member, created_by=self.member
        )
        other_task = TaskService.create_task(
            other_activity, self.sector, "Tarefa alheia", created_by=self.member
        )
        grant_action(
            self.requester,
            catalog.TAREFA_BLOQUEAR,
            organization=self.org,
            relation=Scope.Relation.MINHAS_ATIVIDADES,
        )
        self.client.force_login(self.requester)
        self.assertEqual(
            self.client.get(reverse("task-block", args=[other_task.pk])).status_code, 403
        )

    def test_manual_time_only_for_executors(self):
        grant_action(self.member, catalog.TEMPO_LANCAR_MANUAL, sector=self.sector)
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

    def test_owner_with_the_action_can_complete(self):
        grant_action(self.requester, catalog.ATIVIDADE_CONCLUIR, organization=self.org)
        grant_action(self.requester, catalog.TAREFA_CANCELAR, sector=self.sector)
        TaskService.cancel(self.task, self.requester, reason="Não é mais necessária")

        self.client.force_login(self.requester)
        self.client.post(reverse("activity-complete", args=[self.activity.pk]))
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, "CONCLUIDA")


class CadastroAuthorizationTests(ViewTestCase):
    """Cadastro é ação administrativa: exige autorização explícita."""

    def test_plain_user_cannot_deactivate_sector(self):
        self.client.force_login(self.requester)
        response = self.client.post(reverse("cadastro-toggle", args=["setores", self.sector.pk]))
        self.assertEqual(response.status_code, 403)
        self.sector.refresh_from_db()
        self.assertTrue(self.sector.is_active)

    def test_plain_user_cannot_open_sector_form(self):
        self.client.force_login(self.requester)
        self.assertEqual(self.client.get(reverse("sector-create")).status_code, 403)

    def test_authorized_user_can_deactivate_sector(self):
        grant_action(self.member, catalog.SETOR_INATIVAR, organization=self.org)
        self.client.force_login(self.member)
        response = self.client.post(reverse("cadastro-toggle", args=["setores", self.sector.pk]))
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
            self.org.activities.filter(title="Orçamento entregue ao cliente").exists()
        )

    def test_owner_choices_are_limited_to_the_organization(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse("activity-create"))
        owners = response.context["form"].fields["owner"].queryset
        self.assertIn(self.member, owners)
        self.assertNotIn(self.outsider, owners)
