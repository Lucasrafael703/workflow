from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from core.models import Company, Organization, Sector

# Perfis (Group) representam apenas "o que se pode fazer" (Regras 05 §32-37).
# Nunca representam setor. Totalmente editável depois pelo Admin.
PROFILE_PERMISSIONS = {
    "Administrador": [
        "add_activity",
        "change_activity",
        "can_view_all_activities",
        "can_change_owner",
        "can_reopen_activity",
        "can_cancel_activity",
        "add_task",
        "change_task",
        "can_assume_task",
        "can_assign_task",
        "can_reorder_queue",
        "can_view_full_queue",
        "can_resolve_deadline_conflict",
        "change_sector",
        "change_company",
        "change_site",
        "change_costcenter",
        "change_returnreason",
        "add_user",
        "change_user",
        "change_group",
    ],
    "Gestor": [
        "can_view_all_activities",
        "can_assume_task",
        "can_assign_task",
        "can_reorder_queue",
        "can_view_full_queue",
        "can_resolve_deadline_conflict",
    ],
    "Colaborador": [
        "add_activity",
        "can_assume_task",
    ],
}

DEFAULT_SECTOR_NAMES = ["Comercial", "Engenharia", "Compras", "Financeiro", "Almoxarifado"]


class Command(BaseCommand):
    help = "Cria uma organização de demonstração com empresa, setores e perfis básicos (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--org-name", default="Biasi")
        parser.add_argument("--company-name", default="Biasi Engenharia")

    def handle(self, *args, **options):
        organization, created = Organization.objects.get_or_create(name=options["org_name"])
        self.stdout.write(f"Organização {organization.name}: {'criada' if created else 'já existia'}")

        company, created = Company.objects.get_or_create(organization=organization, name=options["company_name"])
        self.stdout.write(f"Empresa {company.name}: {'criada' if created else 'já existia'}")

        for name in DEFAULT_SECTOR_NAMES:
            sector, created = Sector.objects.get_or_create(organization=organization, name=name)
            self.stdout.write(f"Setor {name}: {'criado' if created else 'já existia'}")

        Group.objects.get_or_create(name=settings.ADMIN_GROUP_NAME)

        for profile_name, codenames in PROFILE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=profile_name)
            self.stdout.write(f"Perfil {profile_name}: {'criado' if created else 'já existia'}")
            perms = Permission.objects.filter(codename__in=codenames)
            found = set(perms.values_list("codename", flat=True))
            missing = set(codenames) - found
            if missing:
                self.stderr.write(
                    self.style.WARNING(
                        f"Permissões não encontradas para {profile_name} (rode migrate antes): {', '.join(sorted(missing))}"
                    )
                )
            if perms:
                group.permissions.add(*perms)

        self.stdout.write(self.style.SUCCESS("Seed de demonstração da LPS concluído."))
