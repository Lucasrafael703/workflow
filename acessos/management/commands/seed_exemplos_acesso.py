"""Exemplos para ver as telas de usuários e grupos funcionando.

    python manage.py seed_exemplos_acesso            # cria (idempotente)
    python manage.py seed_exemplos_acesso --remover  # tira os usuários de exemplo

Cria alguns grupos de acesso (se ainda não existirem com o mesmo nome) e
pessoas de exemplo com e-mail @exemplo.com, cada uma em uma equipe e um grupo
diferentes. Grupos e usuários que já existem não são alterados.
"""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from acessos import screens
from acessos.models import Profile
from acessos.services import AccessService, ScreenAccessService
from core.models import Organization, Sector

User = get_user_model()

SENHA_EXEMPLO = "Exemplo@2026"
DOMINIO = "@exemplo.com"
EQUIPES_PADRAO = ["Engenharia", "Comercial", "Compras", "Financeiro", "Almoxarifado"]

GRUPO_ORCAMENTISTAS = {
    "name": "Orçamentistas",
    "description": "Exemplo de grupo da empresa: tarefas, clientes, obras e centros de custo.",
    "levels": {
        "atividades": screens.EDITAR,
        "tarefas": screens.EDITAR,
        "fila": screens.VER,
        "processos": screens.VER,
        "clientes": screens.EDITAR,
        "obras": screens.EDITAR,
        "centros_custo": screens.EDITAR,
    },
}

# (usuário, nome, índices das equipes, índices em que é gestor, grupo, vale para, ajustes, situação)
PESSOAS = [
    ("ana.martins", "Ana Martins", [0], [0], "gestor", "organizacao", {}, "ativo"),
    ("bruno.rocha", "Bruno Rocha", [0], [], "colaborador", "organizacao", {"clientes": screens.EDITAR}, "ativo"),
    ("carla.souza", "Carla Souza", [1, 0], [], "colaborador", "minhas_equipes", {}, "ativo"),
    ("diego.pereira", "Diego Pereira", [2], [], "orcamentistas", "organizacao", {}, "ativo"),
    ("elaine.ferreira", "Elaine Ferreira", [3], [], "consulta", "organizacao", {"usuarios": screens.VER}, "ativo"),
    ("fabio.lima", "Fábio Lima", [4], [], "colaborador", "organizacao", {}, "inativo"),
    ("gabriela.alves", "Gabriela Alves", [1], [], "colaborador", "organizacao", {}, "convite"),
]


class Command(BaseCommand):
    help = "Cria grupos de acesso e usuários de exemplo para visualizar as telas de acesso."

    def add_arguments(self, parser):
        parser.add_argument("--org", help="Nome da organização (padrão: a do primeiro administrador).")
        parser.add_argument("--remover", action="store_true", help="Remove os usuários de exemplo.")

    def _organization(self, name):
        if name:
            org = Organization.objects.filter(name=name).first()
            if org is None:
                raise CommandError(f"Organização “{name}” não encontrada.")
            return org
        admin = (
            User.objects.filter(is_superuser=True, profile__organization__isnull=False)
            .select_related("profile__organization")
            .order_by("pk")
            .first()
        )
        if admin is not None:
            return admin.profile.organization
        org = Organization.objects.order_by("pk").first()
        if org is None:
            call_command("seed_lps_demo")
            org = Organization.objects.order_by("pk").first()
        return org

    def handle(self, *args, **options):
        if options["remover"]:
            return self._remove()
        with transaction.atomic():
            self._create(options.get("org"))

    def _remove(self):
        usernames = [p[0] for p in PESSOAS]
        removed = kept = 0
        for user in User.objects.filter(username__in=usernames, email__endswith=DOMINIO):
            try:
                with transaction.atomic():
                    user.delete()
                removed += 1
            except Exception:  # histórico protegido: só inativa
                user.is_active = False
                user.save(update_fields=["is_active"])
                kept += 1
        self.stdout.write(self.style.SUCCESS(f"{removed} usuário(s) de exemplo removido(s); {kept} inativado(s)."))

    def _group(self, organization, name, description, levels):
        group = Profile.objects.filter(organization=organization, name__iexact=name).first()
        if group is not None:
            self.stdout.write(f"Grupo {group.name}: já existia (mantido como está)")
            return group
        group = AccessService.create_profile(organization, name, created_by=None, description=description)
        ScreenAccessService.set_profile_screens(group, levels, changed_by=None)
        self.stdout.write(f"Grupo {name}: criado com {screens.count_screens(levels)} telas")
        return group

    def _create(self, org_name):
        call_command("seed_acoes", verbosity=0)
        organization = self._organization(org_name)
        self.stdout.write(f"Organização: {organization.name}")

        sectors = list(Sector.objects.filter(organization=organization, is_active=True).order_by("name"))
        if not sectors:
            for name in EQUIPES_PADRAO:
                Sector.objects.get_or_create(organization=organization, name=name)
            sectors = list(Sector.objects.filter(organization=organization, is_active=True).order_by("name"))
            self.stdout.write(f"Equipes criadas: {', '.join(s.name for s in sectors)}")

        groups = {}
        for key, template in screens.TEMPLATES.items():
            groups[key] = self._group(organization, template["name"], template["description"], template["levels"])
        groups["orcamentistas"] = self._group(
            organization,
            GRUPO_ORCAMENTISTAS["name"],
            GRUPO_ORCAMENTISTAS["description"],
            GRUPO_ORCAMENTISTAS["levels"],
        )

        created = 0
        for username, name, team_idx, manager_idx, group_key, scope_key, extras, status in PESSOAS:
            if User.objects.filter(username=username).exists():
                self.stdout.write(f"Usuário {username}: já existia")
                continue
            user = User.objects.create_user(
                username=username,
                email=f"{username}{DOMINIO}",
                first_name=name,
                password=None if status == "convite" else SENHA_EXEMPLO,
            )
            user.is_active = status != "inativo"
            user.save(update_fields=["is_active"])

            profile = user.profile
            profile.organization = organization
            teams = list(dict.fromkeys(sectors[i % len(sectors)] for i in team_idx))
            profile.main_sector = teams[0] if teams else None
            profile.save(update_fields=["organization", "main_sector"])
            managed = [sectors[i % len(sectors)] for i in manager_idx]
            AccessService.sync_user_sectors(user, teams, managed, changed_by=None)

            group = groups[group_key]
            levels = ScreenAccessService.profile_levels(group)
            for screen_key, level in extras.items():
                levels[screen_key] = max(levels.get(screen_key, 0), level)
            ScreenAccessService.save_user_access(
                user,
                profile=group,
                scope=ScreenAccessService.standard_scope(organization, scope_key),
                levels=levels,
                changed_by=None,
            )
            created += 1
            self.stdout.write(f"Usuário {username}: criado ({group.name}, {', '.join(t.name for t in teams)})")

        self.stdout.write(
            self.style.SUCCESS(
                f"Pronto: {created} usuário(s) de exemplo criado(s). Senha de todos: {SENHA_EXEMPLO} "
                f"(exceto gabriela.alves, que está com convite pendente)."
            )
        )
