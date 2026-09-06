import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def notify(users, event_type, title, message, process=None, step=None, url=""):
        """Cria uma notificação in-app para cada usuário em `users`."""
        users = list({u.id: u for u in users}.values())
        notifications = [
            Notification(
                recipient=user,
                event_type=event_type,
                process=process,
                step=step,
                title=title,
                message=message,
                url=url,
            )
            for user in users
        ]
        return Notification.objects.bulk_create(notifications)

    @staticmethod
    def mark_read(notification):
        from django.utils import timezone

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return notification


class EmailService:
    """Único ponto de envio de e-mail do sistema (django.core.mail, síncrono).
    Chamado apenas para os dois eventos definidos pela regra de negócio:
    liberação de atividade e atividade atrasada."""

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
    def send_step_released(cls, step, recipients):
        cls._send(
            subject=f"[{step.process.title}] Nova atividade liberada: {step.name}",
            template_prefix="step_released",
            context={"step": step, "process": step.process},
            recipients=recipients,
        )

    @classmethod
    def send_step_overdue(cls, step, recipients):
        cls._send(
            subject=f"[{step.process.title}] Atividade atrasada: {step.name}",
            template_prefix="step_overdue",
            context={"step": step, "process": step.process},
            recipients=recipients,
        )
