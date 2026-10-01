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
            self.activity, self.sector, "Cotação de cabos", created_by=self.owner,
            responsavel=self.owner,
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
            self.activity, self.owner, f"@{self.executor.username} dá uma olhada na demanda"
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

class NotificationNavigationTests(NotificationsTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def notice(self, event=Notification.EventType.TASK_COMPLETED, **kwargs):
        defaults = dict(recipient=self.owner, event_type=event, task=self.task,
                        activity=self.activity, title="Aviso", message="Mensagem")
        defaults.update(kwargs)
        return Notification.objects.create(**defaults)

    def open(self, notice, **data):
        return self.client.post(reverse("notification-mark-read", args=[notice.pk]), data)

    def test_open_routes_and_persists_read_state(self):
        cases = [
            (Notification.EventType.TASK_COMPLETED, {}, "task-detail", self.task.pk, ""),
            (Notification.EventType.ACTIVITY_CREATED, {"task": None}, "activity-detail", self.activity.pk, ""),
            (Notification.EventType.MENTIONED, {}, "task-detail", self.task.pk, "#conversa"),
            (Notification.EventType.MENTIONED, {"task": None}, "activity-detail", self.activity.pk, "#feed-panel"),
            (Notification.EventType.DEADLINE_PROPOSED, {}, "task-detail", self.task.pk, "#prazo"),
            (Notification.EventType.ACTIVITY_APPROVAL_NEEDED, {}, "activity-detail", self.activity.pk, "#pendencia"),
        ]
        for event, fields, route, pk, fragment in cases:
            with self.subTest(event=event, fields=fields):
                n = self.notice(event, **fields)
                self.assertEqual(self.open(n).url, reverse(route, args=[pk]) + fragment)
                n.refresh_from_db()
                self.assertTrue(n.is_read)
                self.assertIsNotNone(n.read_at)

    def test_explicit_destinations_and_history_anchor(self):
        n = self.notice()
        for target, fragment in [("history", "#historico"), ("mention", "#conversa"), ("deadline", "#prazo")]:
            self.assertEqual(self.open(n, target=target).url, reverse("task-detail", args=[self.task.pk]) + fragment)
        self.assertContains(self.client.get(reverse("task-detail", args=[self.task.pk])), 'id="historico"')

    def test_conflict_opens_current_conflict_then_falls_back_to_deadline(self):
        proposal = DeadlineService.propose(self.task, timezone.now() + timedelta(days=2), self.executor)
        DeadlineService.reject(proposal, self.owner, "Ajustar")
        n = self.notice(Notification.EventType.DEADLINE_CONFLICT)
        conflict = self.task.deadline_conflicts.get(proposal=proposal)
        self.assertEqual(self.open(n).url, reverse("conflict-resolve", args=[conflict.pk]))
        conflict.status = "RESOLVIDO"
        conflict.save()
        self.assertEqual(self.open(n, target="conflict").url, reverse("task-detail", args=[self.task.pk]) + "#prazo")

    def test_read_only_preserves_list_query_without_open_redirect(self):
        from urllib.parse import parse_qs, urlsplit
        n = self.notice()
        response = self.open(n, mode="read", filter="todas", q="Aviso & revisão", ordem="antigas", page="2", next="https://evil.example")
        self.assertEqual(urlsplit(response.url).path, reverse("notification-list"))
        self.assertEqual(parse_qs(urlsplit(response.url).query), {
            "filter": ["todas"], "q": ["Aviso & revisão"], "ordem": ["antigas"], "page": ["2"],
        })
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_repeated_open_preserves_first_read_timestamp_even_for_stale_instance(self):
        from .services import NotificationService
        n = self.notice()
        stale = Notification.objects.get(pk=n.pk)
        self.open(n)
        n.refresh_from_db()
        first = n.read_at
        NotificationService.mark_read(stale)
        self.open(n)
        n.refresh_from_db()
        self.assertEqual(n.read_at, first)

    def test_open_updates_badges_and_unread_filter_but_keeps_pending_action(self):
        n = self.notice(Notification.EventType.TASK_OVERDUE)
        before = self.client.get(reverse("notification-list"), {"filter": "nao-lidas"})
        count = before.context["unread_notifications_count"]
        self.open(n)
        response = self.client.get(reverse("notification-list"), {"filter": "nao-lidas"})
        self.assertEqual(response.context["unread_notifications_count"], count - 1)
        self.assertNotIn(n.pk, [item.pk for item in response.context["notifications"]])
        pending = self.client.get(reverse("notification-list"), {"filter": "acao"})
        self.assertIn(n.pk, [item.pk for item in pending.context["notifications"]])
        self.assertNotIn('notif-row--unread', self.client.get(
            reverse("notification-list"), {"filter": "todas", "q": "Aviso"}
        ).content.decode())

    def test_no_target_marks_read_and_returns_message(self):
        n = self.notice(task=None, activity=None)
        response = self.open(n)
        self.assertEqual(response.url, reverse("notification-list"))
        response = self.client.get(response.url)
        self.assertContains(response, "O conteúdo relacionado não está disponível.")
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_stored_url_only_accepts_internal_related_detail(self):
        expected = reverse("task-detail", args=[self.task.pk])
        for url in ["https://evil.example/", "//evil.example/", "/\\evil.example/", "/missing/",
                    reverse("task-detail", args=[999999]), reverse("notification-mark-all-read"),
                    expected + "\n"]:
            with self.subTest(url=url):
                self.assertEqual(self.open(self.notice(url=url)).url, expected)
        self.assertEqual(self.open(self.notice(url=expected + "#conversa")).url, expected + "#conversa")

    def test_invalid_modes_and_targets_do_not_mutate(self):
        n = self.notice()
        for data in [{"mode": "invalid"}, {"target": "https://evil.example"}]:
            self.assertEqual(self.open(n, **data).status_code, 400)
            n.refresh_from_db()
            self.assertFalse(n.is_read)

    def test_reading_last_item_of_unread_page_returns_a_valid_list(self):
        Notification.objects.filter(recipient=self.owner).delete()
        notices = [self.notice() for _ in range(31)]
        response = self.open(notices[0], mode="read", filter="nao-lidas", page="2")
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(response.context["unread_count"], 30)

    def test_recipient_and_csrf_are_enforced(self):
        from django.test import Client
        n = self.notice(recipient=self.executor)
        self.assertEqual(self.open(n).status_code, 404)
        n = self.notice()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        url = reverse("notification-mark-read", args=[n.pk])
        self.assertEqual(client.get(url).status_code, 405)
        self.assertEqual(client.post(url).status_code, 403)
        n.refresh_from_db()
        self.assertFalse(n.is_read)
        client.get(reverse("notification-list"))
        response = client.post(url, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 302)

    def test_navigation_buttons_are_post_forms_including_generic_without_context(self):
        for event, fields in [
            (Notification.EventType.MENTIONED, {}),
            (Notification.EventType.TASK_ASSIGNED, {}),
            (Notification.EventType.ACTIVITY_CREATED, {"task": None}),
            (Notification.EventType.TASK_COMPLETED, {}),
            (Notification.EventType.DEADLINE_CONFLICT, {}),
            (Notification.EventType.ACTIVITY_APPROVAL_NEEDED, {}),
            (Notification.EventType.MENTIONED, {"task": None, "activity": None}),
        ]:
            with self.subTest(event=event, fields=fields):
                n = self.notice(event, **fields)
                response = self.client.get(reverse("notification-list"), {"filter": "todas"})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'action="' + reverse("notification-mark-read", args=[n.pk]) + '"')
                self.assertContains(response, 'name="mode" value="read"')
                self.assertNotContains(response, 'href="' + reverse("task-detail", args=[self.task.pk]))
        self.assertContains(response, "Abrir tarefa")
        self.assertContains(response, "Abrir demanda")


class NotificationDeadlineAcceptanceTests(NotificationsTestCase):
    def setUp(self):
        super().setUp()
        self.proposal = DeadlineService.propose(self.task, timezone.now() + timedelta(days=2), self.executor)
        self.notification = Notification.objects.get(
            task=self.task, recipient=self.owner, event_type=Notification.EventType.DEADLINE_PROPOSED
        )
        self.client.force_login(self.owner)

    def accept(self, notification=None, proposal=None):
        return self.client.post(reverse("deadline-accept", args=[(proposal or self.proposal).pk]),
                                {"notification_id": (notification or self.notification).pk})

    def test_success_marks_corresponding_notice_only(self):
        unrelated = Notification.objects.filter(recipient=self.owner).exclude(pk=self.notification.pk).first()
        self.assertEqual(self.accept().status_code, 302)
        self.notification.refresh_from_db()
        self.proposal.refresh_from_db()
        unrelated.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.assertFalse(unrelated.is_read)
        self.assertEqual(self.proposal.status, "ACEITO")

    def test_service_failure_leaves_notice_unread(self):
        DeadlineService.reject(self.proposal, self.owner, "Não aceito")
        self.assertEqual(self.accept().status_code, 302)
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_foreign_notice_rejected_before_accepting(self):
        self.client.force_login(self.executor)
        self.assertEqual(self.accept().status_code, 404)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, "PENDENTE")

    def test_wrong_task_or_event_rejected(self):
        other = TaskService.create_task(self.activity, self.sector, "Outra tarefa", responsavel=self.owner, created_by=self.owner)
        for task, event in [(other, Notification.EventType.DEADLINE_PROPOSED), (self.task, Notification.EventType.MENTIONED)]:
            n = Notification.objects.create(recipient=self.owner, task=task, activity=self.activity,
                                            event_type=event, title="Outro", message="Outro")
            self.assertEqual(self.accept(n).status_code, 404)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, "PENDENTE")

    def test_multiple_proposals_keep_their_own_notification_relationship(self):
        newer = DeadlineService.propose(self.task, timezone.now() + timedelta(days=3), self.executor)
        new_notice = Notification.objects.filter(task=self.task, event_type=Notification.EventType.DEADLINE_PROPOSED).latest("pk")
        self.assertEqual(_decorate(self.notification).pending_proposal_id, self.proposal.pk)
        self.assertEqual(_decorate(new_notice).pending_proposal_id, newer.pk)
        self.assertEqual(self.accept(self.notification, newer).status_code, 404)
        self.assertEqual(self.accept(new_notice, self.proposal).status_code, 404)
        self.assertEqual(self.accept().status_code, 302)
        self.assertFalse(_still_needs_action(self.notification))
        self.assertTrue(_still_needs_action(new_notice))
