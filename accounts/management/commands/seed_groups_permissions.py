from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

# Group names are only a starting suggestion -- fully editable later through
# the Django Admin (Groups). This command is idempotent: rerunning it never
# duplicates groups/permissions, it only ensures the baseline mapping exists.
GROUP_NAMES = [
    "ADMIN",
    "COMERCIAL",
    "ENGENHARIA",
    "SUPRIMENTOS",
    "FINANCEIRO",
    "PLANEJAMENTO",
    "RH",
]

CUSTOM_PERMISSION_CODENAMES = [
    "can_manage_templates",
    "can_create_process",
    "can_cancel_process",
    "can_view_all_processes",
    "can_view_dashboard",
    "can_claim_any_activity",
    "can_override_assignment",
    "can_reopen_activity",
    "can_edit_workflow",
    "can_block_activity",
    "can_qualify_demand",
    "can_view_all_demands",
]

GROUP_PERMISSIONS = {
    "ADMIN": CUSTOM_PERMISSION_CODENAMES,
    "COMERCIAL": [
        "can_qualify_demand",
        "can_create_process",
        "can_view_all_processes",
        "can_view_dashboard",
    ],
    "ENGENHARIA": [],
    "SUPRIMENTOS": [],
    "FINANCEIRO": [],
    "PLANEJAMENTO": [],
    "RH": [],
}


class Command(BaseCommand):
    help = "Cria (idempotentemente) os grupos padrão e associa as permissões customizadas iniciais."

    def handle(self, *args, **options):
        permissions_by_codename = {
            perm.codename: perm
            for perm in Permission.objects.filter(codename__in=CUSTOM_PERMISSION_CODENAMES)
        }
        missing = set(CUSTOM_PERMISSION_CODENAMES) - set(permissions_by_codename)
        if missing:
            self.stderr.write(
                self.style.WARNING(
                    f"Permissões não encontradas (rode migrate antes): {', '.join(sorted(missing))}"
                )
            )

        for group_name in GROUP_NAMES:
            group, created = Group.objects.get_or_create(name=group_name)
            action = "criado" if created else "já existia"
            self.stdout.write(f"Grupo {group_name}: {action}")

            codenames = GROUP_PERMISSIONS.get(group_name, [])
            perms_to_add = [permissions_by_codename[c] for c in codenames if c in permissions_by_codename]
            if perms_to_add:
                group.permissions.add(*perms_to_add)

        self.stdout.write(self.style.SUCCESS("Seed de grupos/permissões concluído."))
