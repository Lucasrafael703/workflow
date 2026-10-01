"""Migração `0008_demanda_nas_mensagens_gravadas`: troca "atividade" por "demanda" só no texto fixo que o
sistema escreveu nas notificações; o que a pessoa digitou não muda."""

import importlib

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Notification

migration = importlib.import_module("notifications.migrations.0008_demanda_nas_mensagens_gravadas")
Event = Notification.EventType
User = get_user_model()


class DemandaNasMensagensGravadasTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ana", password="x")

    def make(self, event, title, message):
        return Notification.objects.create(recipient=self.user, event_type=event, title=title, message=message)

    def rewrite(self):
        migration.rewrite(apps, None)

    def test_titles_the_system_wrote_are_replaced(self):
        for old, new in migration.TITLES.items():
            note = self.make(Event.ACTIVITY_CREATED, old, "texto")
            self.rewrite()
            note.refresh_from_db()
            self.assertEqual(note.title, new, msg=old)

    def test_the_fixed_part_changes_but_the_users_own_text_does_not(self):
        note = self.make(Event.ACTIVITY_CREATED, "Atividade criada", "A atividade 'Atividade de campo' foi criada.")
        self.rewrite()
        note.refresh_from_db()
        self.assertEqual(note.title, "Demanda criada")
        self.assertEqual(note.message, "A demanda 'Atividade de campo' foi criada.")  # o título digitado fica

    def test_only_the_first_fixed_phrase_changes_in_a_message_with_a_reason(self):
        note = self.make(
            Event.ACTIVITY_CANCELLED, "Atividade cancelada",
            "A atividade 'Obra' foi cancelada. Motivo: a atividade saiu do escopo",
        )
        self.rewrite()
        note.refresh_from_db()
        self.assertEqual(note.message, "A demanda 'Obra' foi cancelada. Motivo: a atividade saiu do escopo")

    def test_assumed_overdue_and_approved_messages(self):
        assumed = self.make(Event.OWNER_CHANGED, "Atividade assumida", "ryan assumiu a atividade 'Gerador'.")
        overdue = self.make(
            Event.TASK_OVERDUE, "Tarefa atrasada", "A tarefa 'Revisar a atividade' da atividade 'Gerador' está atrasada."
        )
        approved = self.make(
            Event.ACTIVITY_APPROVED, "Pendência aprovada",
            "A pendência de 'Gerador' foi aprovada. A atividade voltou para a sua fila.",
        )
        self.rewrite()
        for note in (assumed, overdue, approved):
            note.refresh_from_db()
        self.assertEqual(assumed.message, "ryan assumiu a demanda 'Gerador'.")
        self.assertEqual(overdue.message, "A tarefa 'Revisar a atividade' da demanda 'Gerador' está atrasada.")
        self.assertEqual(approved.message, "A pendência de 'Gerador' foi aprovada. A demanda voltou para a sua fila.")

    def test_comments_and_mentions_are_never_touched(self):
        mention = self.make(Event.MENTIONED, "Você foi mencionado", "A atividade 'x' está ok? @ana")
        posted = self.make(Event.MESSAGE_POSTED, "Nova mensagem na atividade", "A atividade 'x' mudou de prazo")
        self.rewrite()
        mention.refresh_from_db()
        posted.refresh_from_db()
        self.assertEqual(mention.message, "A atividade 'x' está ok? @ana")
        self.assertEqual(posted.message, "A atividade 'x' mudou de prazo")  # texto do comentário
        self.assertEqual(posted.title, "Nova mensagem na demanda")  # o título é fixo do sistema

    def test_notifications_without_the_term_are_left_alone_and_running_twice_is_harmless(self):
        other = self.make(Event.TASK_ASSIGNED, "Tarefa atribuída", "Você recebeu uma tarefa.")
        note = self.make(Event.ACTIVITY_COMPLETED, "Atividade concluída", "A atividade 'Obra' foi concluída.")
        self.rewrite()
        self.rewrite()
        other.refresh_from_db()
        note.refresh_from_db()
        self.assertEqual((other.title, other.message), ("Tarefa atribuída", "Você recebeu uma tarefa."))
        self.assertEqual((note.title, note.message), ("Demanda concluída", "A demanda 'Obra' foi concluída."))
