import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def notify(users, event_type, title, message, activity=None, task=None, url="", actor=None):
        """Cria uma notificação in-app para cada usuário em `users`.

        `actor` é quem gerou o evento (delegou, propôs, mencionou, concluiu)
        — o sujeito da frase que a notificação mostra na linha "o que
        aconteceu". Quem chama decide se o próprio ator deve estar em
        `users` ou não: às vezes uma pessoa conclui a própria atividade e
        ainda faz sentido confirmar isso a ela mesma.
        """
        users = list({u.id: u for u in users}.values())
        notifications = [
            Notification(
                recipient=user,
                event_type=event_type,
                activity=activity,
                task=task,
                title=title,
                message=message,
                url=url,
                actor=actor,
            )
            for user in users
        ]
        return Notification.objects.bulk_create(notifications)

    @staticmethod
    def mark_read(notification):
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return notification


class EmailService:
    """Único ponto de envio de e-mail do sistema (django.core.mail, síncrono)."""

    @staticmethod
    def _send(subject, template_prefix, context, recipients):
        emails = [u.email for u in recipients if u.email]
        if not emails:
            return
        text_body = render_to_string(f"notifications/email/{template_prefix}.txt", context)
        try:
            send_mail(
                subject=subject,
                message=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=emails,
                fail_silently=False,
            )
        except Exception:
            logger.exception("Falha ao enviar e-mail '%s' para %s", subject, emails)

    @classmethod
    def send_task_overdue(cls, task, recipients):
        cls._send(
            subject=f"[{task.activity.title}] Tarefa atrasada: {task.title}",
            template_prefix="task_overdue",
            context={"task": task, "activity": task.activity},
            recipients=recipients,
        )

    @classmethod
    def send_activity_approval_needed(cls, activity, pendency, recipients):
        """E-mail para quem pode aprovar a pendência (Regras avulsas — fila do
        gestor): motivo, comentário e prazo para a decisão."""
        cls._send(
            subject=f"[{activity.title}] Aguardando sua aprovação",
            template_prefix="activity_approval_needed",
            context={"activity": activity, "pendency": pendency},
            recipients=recipients,
        )

    @classmethod
    def send_client_information_request(cls, activity, pendency):
        """E-mail ao cliente pedindo as informações pendentes — só quando a
        pessoa marca a caixa correspondente no popup de pendência."""
        client = activity.client
        if client is None or not client.email:
            return
        cls._send(
            subject=f"[{activity.title}] Informações pendentes",
            template_prefix="activity_client_information_request",
            context={"activity": activity, "pendency": pendency, "client": client},
            recipients=[client],
        )
