from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from acessos.testing import grant_actions
from activities.models import Activity, DeadlineProposal, Task
from activities.services import ActivityService, DeadlineService, MessageService, TaskService
from core.models import Organization, Sector

from .models import Notification
from .views import (
    CATEGORY_PRESENTATION,
    EVENT_CATEGORY,
    _decorate,
    _still_needs_action,
)

User = get_user_model()

OPERATOR_ACTIONS = [
    catalog.ATIVIDADE_CRIAR,
    catalog.ATIVIDADE_EDITAR,
    catalog.TAREFA_CRIAR,
    catalog.TAREFA_ATRIBUIR,
    catalog.TAREFA_ACEITAR,
    catalog.TAREFA_RECUSAR,
    catalog.TAREFA_INICIAR,
    catalog.TAREFA_CONCLUIR,
    catalog.TAREFA_BLOQUEAR,
    catalog.PRAZO_PROPOR,
    catalog.PRAZO_ACEITAR,
    catalog.PRAZO_RECUSAR,
    catalog.COMUNICACAO_PARTICIPAR,
]


class NotificationsTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.sector = Sector.objects.create(organization=self.org, name="Compras")
        self.owner = User.objects.create_user("paulo", password="x")
        self.executor = User.objects.create_user("ryan", password="x")

        for user in (self.owner, self.executor):
            user.profile.organization = self.org
            user.profile.save(update_fields=["organization"])
            grant_actions(user, OPERATOR_ACTIONS, organization=self.org)

        self.activity = ActivityService.create_activity(
            organization=self.org, title="Material disponível na obra", owner=self.owner, created_by=self.owner
        )
        self.task = TaskService.create_task(
            self.activity, self.sector, "Cotação de cabos", created_by=self.owner
        )
        assignment = TaskService.add_executor(self.task, self.executor, added_by=self.owner)
        TaskService.accept_assignment(assignment, self.executor)


class StaleActionRequiredTests(NotificationsTestCase):
    """Uma notificação de prazo/tarefa não deve pedir ação para sempre —
    apenas enquanto a decisão real (aceitar/recusar, concluir) não aconteceu."""

    def test_deadline_proposed_stops_needing_action_once_accepted(self):
        from django.utils import timezone
        from datetime import timedelta

        proposal = DeadlineService.propose(self.task, timezone.now() + timedelta(days=2), self.executor)
        notification = Notification.objects.get(
            recipient=self.owner, event_type=Notification.EventType.DEADLINE_PROPOSED
        )
        self.assertTrue(_still_needs_action(notification))

        DeadlineService.accept(proposal, self.owner)
        notification.refresh_from_db()
        self.assertFalse(_still_needs_action(notification))

    def test_deadline_proposed_stops_needing_action_once_rejected(self):
        from django.utils import timezone
        from datetime import timedelta

        proposal = DeadlineService.propose(self.task, timezone.now() + timedelta(days=2), self.executor)
        notification = Notification.objects.get(
            recipient=self.owner, event_type=Notification.EventType.DEADLINE_PROPOSED
        )
        DeadlineService.reject(proposal, self.owner, "Prazo muito longo")
        notification.refresh_from_db()
        self.assertFalse(_still_needs_action(notification))

    def test_task_assigned_stops_needing_action_once_completed(self):
        notification = Notification.objects.filter(
            recipient=self.executor, event_type=Notification.EventType.TASK_ASSIGNED
        ).first()
        self.assertIsNotNone(notification)
        self.assertTrue(_still_needs_action(notification))

        TaskService.start(self.task, self.executor)
        TaskService.complete(self.task, self.executor)
        notification.refresh_from_db()
        self.assertFalse(_still_needs_action(notification))

    def test_task_without_related_object_never_needs_action(self):
        """Notificação sem tarefa/proposta associada não pode travar como
        pendente para sempre — sem como resolver, ela não deve contar."""
        notification = Notification.objects.create(
            recipient=self.owner,
            event_type=Notification.EventType.DEADLINE_PROPOSED,
            title="Prazo proposto",
            message="teste",
        )
        self.assertFalse(_still_needs_action(notification))


class NotificationListViewTests(NotificationsTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_action_count_matches_actual_pending_items(self):
        from django.utils import timezone
        from datetime import timedelta

        DeadlineService.propose(self.task, timezone.now() + timedelta(days=2), self.executor)
        response = self.client.get(reverse("notification-list"))
        self.assertEqual(response.status_code, 200)
        # ACTIVITY_CREATED (não acionável) + DEADLINE_PROPOSED (acionável)
        self.assertEqual(response.context["action_count"], 1)

    def test_accepting_a_resolved_proposal_removes_it_from_action_required(self):
        from django.utils import timezone
        from datetime import timedelta

        proposal = DeadlineService.propose(self.task, timezone.now() + timedelta(days=2), self.executor)
        DeadlineService.accept(proposal, self.owner)

        response = self.client.get(reverse("notification-list"), {"filter": "acao"})
        self.assertEqual(response.context["action_count"], 0)
        pks_com_acao = {n.pk for n in response.context["notifications"]}
        proposta_notif = Notification.objects.get(
            recipient=self.owner, event_type=Notification.EventType.DEADLINE_PROPOSED
        )
        self.assertNotIn(proposta_notif.pk, pks_com_acao)

    def test_search_filters_by_title_and_message(self):
        response = self.client.get(reverse("notification-list"), {"q": "Material disponível", "filter": "todas"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["notifications"]) >= 1)

        response = self.client.get(reverse("notification-list"), {"q": "não existe nada assim", "filter": "todas"})
        self.assertEqual(len(response.context["notifications"]), 0)

    def test_filter_acao_only_returns_notifications_still_needing_action(self):
        from django.utils import timezone
        from datetime import timedelta

        proposal = DeadlineService.propose(self.task, timezone.now() + timedelta(days=2), self.executor)
        DeadlineService.accept(proposal, self.owner)

        response = self.client.get(reverse("notification-list"), {"filter": "acao"})
        for n in response.context["notifications"]:
            self.assertNotEqual(str(n.event_type), str(Notification.EventType.DEADLINE_PROPOSED))

    def test_unread_count_and_mark_all_read(self):
        response = self.client.get(reverse("notification-list"))
        self.assertGreater(response.context["unread_count"], 0)

        self.client.post(reverse("notification-mark-all-read"))
        response = self.client.get(reverse("notification-list"))
        self.assertEqual(response.context["unread_count"], 0)


class NotificationActionButtonTests(NotificationsTestCase):
    """A notificação de prazo proposto precisa levar direto ao botão de
    aceitar/recusar certo — nunca a um id de proposta errado ou vazio."""

    def test_pending_proposal_id_resolves_to_the_actual_pending_proposal(self):
        from django.utils import timezone
        from datetime import timedelta

        proposal = DeadlineService.propose(self.task, timezone.now() + timedelta(days=2), self.executor)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("notification-list"))

        notif = next(
            n for n in response.context["notifications"]
            if n.event_type == Notification.EventType.DEADLINE_PROPOSED
        )
        self.assertEqual(notif.pending_proposal_id, proposal.pk)

        accept_url = reverse("deadline-accept", args=[notif.pending_proposal_id])
        self.assertIn(accept_url, response.content.decode())

    def test_mark_read_redirects_to_the_related_task(self):
        self.client.force_login(self.executor)
        notification = Notification.objects.filter(
            recipient=self.executor, event_type=Notification.EventType.TASK_ASSIGNED
        ).first()
        response = self.client.post(reverse("notification-mark-read", args=[notification.pk]))
        self.assertRedirects(response, reverse("task-detail", args=[self.task.pk]))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_cannot_mark_another_users_notification_as_read(self):
        notification = Notification.objects.filter(recipient=self.owner).first()
        self.client.force_login(self.executor)
        response = self.client.post(reverse("notification-mark-read", args=[notification.pk]))
        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)


class MentionTests(NotificationsTestCase):
    """Menções seguem a Regras 06 §28-32: apenas @usuário individual, só
    notifica quem já tem acesso ao contexto, e nunca concede acesso por si só."""

    def test_mentioning_someone_with_access_creates_a_mention_notification(self):
        MessageService.post_task_message(self.task, self.owner, f"@{self.executor.username}, pode revisar isto?")
        mention = Notification.objects.filter(
            recipient=self.executor, event_type=Notification.EventType.MENTIONED
        ).first()
        self.assertIsNotNone(mention)
        self.assertEqual(mention.actor, self.owner)
        self.assertIn("pode revisar isto?", mention.message)

    def test_mentioning_someone_without_access_is_silently_ignored(self):
        outsider = User.objects.create_user("fora", password="x")
        # Sem organização/perfil/ação: não participa desta tarefa.
        MessageService.post_task_message(self.task, self.owner, f"@{outsider.username}, confirma pra mim?")
        self.assertFalse(
            Notification.objects.filter(recipient=outsider, event_type=Notification.EventType.MENTIONED).exists()
        )

    def test_mentioning_yourself_does_not_create_a_notification(self):
        MessageService.post_task_message(self.task, self.owner, f"@{self.owner.username} nota para mim mesmo")
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.owner, event_type=Notification.EventType.MENTIONED
            ).exists()
        )

    def test_mentioned_user_is_not_also_notified_as_a_generic_message(self):
        """Quem foi mencionado recebe a notificação de menção, não a genérica
        de "nova mensagem" duplicada para o mesmo evento."""
        MessageService.post_task_message(self.task, self.owner, f"@{self.executor.username}, revisa isto?")
        generic = Notification.objects.filter(
            recipient=self.executor, event_type=Notification.EventType.MESSAGE_POSTED
        )
        self.assertFalse(generic.exists())

    def test_message_without_mention_still_notifies_participants_generically(self):
        Notification.objects.all().delete()
        MessageService.post_task_message(self.task, self.owner, "Só um alinhamento geral, sem menção.")
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.executor, event_type=Notification.EventType.MESSAGE_POSTED
            ).exists()
        )

    def test_activity_message_mention_resolves_against_activity_access(self):
        Notification.objects.all().delete()
        MessageService.post_activity_message(
            self.activity, self.owner, f"@{self.executor.username} dá uma olhada na atividade"
        )
        mention = Notification.objects.filter(
            recipient=self.executor, event_type=Notification.EventType.MENTIONED
        ).first()
        self.assertIsNotNone(mention)
        self.assertEqual(mention.activity_id, self.activity.pk)


class CardCategoryTests(NotificationsTestCase):
    """Todo EventType precisa mapear para uma categoria com apresentação
    definida — sem isso, uma notificação de tipo novo quebraria a tela."""

    def test_every_event_type_has_a_mapped_category(self):
        all_events = set(Notification.EventType.values)
        self.assertEqual(all_events - set(EVENT_CATEGORY.keys()), set())

    def test_every_category_has_a_presentation(self):
        all_categories = set(EVENT_CATEGORY.values())
        self.assertEqual(all_categories - set(CATEGORY_PRESENTATION.keys()), set())

    def test_task_blocked_needs_action_while_block_is_open_only(self):
        TaskService.block(self.task, self.owner, "Aguardando aprovação", "")
        notification = Notification.objects.filter(
            recipient=self.owner, event_type=Notification.EventType.TASK_BLOCKED
        ).first()
        self.assertIsNotNone(notification)
        self.assertTrue(_still_needs_action(notification))

        TaskService.unblock(self.task, self.owner)
        notification.refresh_from_db()
        self.assertFalse(_still_needs_action(notification))

    def test_actor_falls_back_to_creator_when_not_recorded(self):
        """Notificações antigas, criadas antes do campo actor existir, ainda
        precisam mostrar quem delegou — usando quem criou a tarefa/atividade."""
        notification = Notification.objects.filter(
            recipient=self.executor, event_type=Notification.EventType.TASK_ASSIGNED
        ).first()
        notification.actor = None
        notification.save(update_fields=["actor"])
        notification.refresh_from_db()

        decorated = _decorate(notification)
        self.assertEqual(decorated.actor_name, self.owner.get_username())

    def test_actor_name_is_blank_when_the_actor_is_the_recipient(self):
        """"Você delegou para você" não faz sentido — a frase fica neutra."""
        notification = Notification.objects.filter(
            recipient=self.owner, event_type=Notification.EventType.ACTIVITY_CREATED
        ).first()
        decorated = _decorate(notification)
        self.assertIsNone(decorated.actor_name)
        self.assertIn("Você criou", decorated.summary)
