from django.core.management.base import BaseCommand

from boards.domain_defaults import ensure_domain_board
from boards.models import DomainBoard
from core.models import Organization


class Command(BaseCommand):
    help = "Cria de forma idempotente os quadros padrão de Demandas e Tarefas."

    def handle(self, *args, **options):
        for organization in Organization.objects.iterator():
            ensure_domain_board(organization, DomainBoard.Domain.DEMAND)
            ensure_domain_board(organization, DomainBoard.Domain.TASK)
        self.stdout.write(self.style.SUCCESS("Quadros padrão sincronizados."))
