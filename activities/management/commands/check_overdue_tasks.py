from django.core.management.base import BaseCommand

from activities.services import TaskService


class Command(BaseCommand):
    help = (
        "Verifica tarefas com prazo comprometido vencido e ainda não notificadas, "
        "gerando notificação in-app e e-mail para o setor responsável, o dono da atividade "
        "e administradores. Deve ser agendado periodicamente (ex.: Task Scheduler/cron)."
    )

    def handle(self, *args, **options):
        count = TaskService.mark_overdue_tasks()
        self.stdout.write(self.style.SUCCESS(f"{count} tarefa(s) marcada(s) como atrasada(s)."))
