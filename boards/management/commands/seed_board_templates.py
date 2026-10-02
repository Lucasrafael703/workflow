from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from boards.models import Board
from boards.services import BoardError
from boards.starter_templates import TEMPLATES, create_board_from_template
from core.models import Organization


class Command(BaseCommand):
    help = (
        "Cria um quadro a partir de um modelo (hoje: Orçamentos) numa organização, para demonstração ou "
        "para começar de algo pronto. Não roda sozinho no deploy: quadros são do usuário."
    )

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True, help="Nome (ou id) da organização.")
        parser.add_argument("--user", required=True, help="Usuário que será o autor (precisa poder criar quadros).")
        parser.add_argument("--modelo", default="orcamentos", choices=sorted(TEMPLATES))
        parser.add_argument("--nome", default=None, help="Nome do quadro (padrão: o do modelo).")
        parser.add_argument("--exemplos", action="store_true", help="Inclui itens de exemplo.")

    def handle(self, *args, **options):
        organization = self._organization(options["organization"])
        user = get_user_model().objects.filter(username=options["user"]).first()
        if user is None:
            raise CommandError(f"Usuário “{options['user']}” não existe.")
        name = options["nome"] or TEMPLATES[options["modelo"]]["name"]
        if Board.objects.filter(organization=organization, name=name, is_active=True).exists():
            self.stdout.write(self.style.WARNING(f"Já existe um quadro “{name}” em {organization}: nada a fazer."))
            return
        try:
            board = create_board_from_template(
                user=user, organization=organization, key=options["modelo"], name=name,
                with_examples=options["exemplos"],
            )
        except BoardError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Quadro “{board.name}” criado (id {board.pk})."))

    @staticmethod
    def _organization(value):
        queryset = Organization.objects.all()
        found = queryset.filter(pk=value).first() if str(value).isdigit() else None
        found = found or queryset.filter(name__iexact=value).first()
        if found is None:
            raise CommandError(f"Organização “{value}” não encontrada.")
        return found
