from django.core.management.base import BaseCommand

from workflows.services import WorkflowService


class Command(BaseCommand):
    help = (
        "Verifica atividades com prazo vencido e ainda não notificadas, "
        "gerando notificação in-app e e-mail para o grupo responsável e administradores. "
        "Deve ser agendado periodicamente (ex.: Task Scheduler/cron), já que o MVP não usa Celery."
    )

    def handle(self, *args, **options):
        count = WorkflowService.marcar_atividades_atrasadas()
        self.stdout.write(self.style.SUCCESS(f"{count} atividade(s) marcada(s) como atrasada(s)."))
