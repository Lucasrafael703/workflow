from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from acessos.catalog import SUGGESTED_PROFILES
from acessos.models import Action, Profile, ProfileAction
from core.models import Company, Organization, Sector

DEFAULT_SECTOR_NAMES = ["Comercial", "Engenharia", "Compras", "Financeiro", "Almoxarifado"]


class Command(BaseCommand):
    help = (
        "Cria uma organização de demonstração com empresa, setores e perfis de acesso "
        "sugeridos (idempotente). Os perfis são um ponto de partida: a organização pode "
        "renomeá-los, alterá-los e criar outros (Regras 05 §11)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--org-name", default="Biasi")
        parser.add_argument("--company-name", default="Biasi Engenharia")

    @transaction.atomic
    def handle(self, *args, **options):
        # O catálogo de ações precisa existir antes dos perfis.
        call_command("seed_acoes")

        organization, created = Organization.objects.get_or_create(name=options["org_name"])
        self.stdout.write(f"Organização {organization.name}: {'criada' if created else 'já existia'}")

        company, created = Company.objects.get_or_create(
            organization=organization, name=options["company_name"]
        )
        self.stdout.write(f"Empresa {company.name}: {'criada' if created else 'já existia'}")

        for name in DEFAULT_SECTOR_NAMES:
            sector, created = Sector.objects.get_or_create(organization=organization, name=name)
            self.stdout.write(f"Setor {name}: {'criado' if created else 'já existia'}")

        actions_by_key = {action.key: action for action in Action.objects.all()}

        for profile_name, action_keys in SUGGESTED_PROFILES.items():
            profile, created = Profile.objects.get_or_create(
                organization=organization, name=profile_name
            )
            self.stdout.write(f"Perfil {profile_name}: {'criado' if created else 'já existia'}")

            missing = [key for key in action_keys if key not in actions_by_key]
            if missing:
                self.stderr.write(
                    self.style.WARNING(f"Ações desconhecidas em {profile_name}: {', '.join(missing)}")
                )

            for key in action_keys:
                action = actions_by_key.get(key)
                if action:
                    ProfileAction.objects.get_or_create(profile=profile, action=action)

        self.stdout.write(self.style.SUCCESS("Seed de demonstração da LPS concluído."))
