"""Ações `tela.*`: o menu passa a mostrar cada item conforme o acesso à tela.

Até aqui o menu escondia só alguns itens e o resto aparecia para todo mundo. Para o menu poder
esconder cada item sem tirar nada de quem já usa, esta migração cria as ações de menu e **concede,
a quem já enxergava cada item, a ação que o mantém visível** — nada some para ninguém:

- Início e Notificações: todo perfil e toda pessoa que já tem concessão direta (o menu mostrava para todos);
- Equipe, Filas e gargalos e Insights: quem tem `metricas.visualizar` (era a regra da seção Gestão);
- Empresas, Setores, Clientes, Obras e Centros de custo: quem já abria Cadastros (gerir setor, empresa,
  motivos, estágios, marcadores, ver processos…) ou gere o próprio cadastro;
- Configurações e Integrações: quem já via a seção Administração (cadastros, usuários ou perfis).

Vale para perfis (`ProfileAction`) e para concessões diretas (`UserAction`, no mesmo escopo da concessão
que justificou). Perfis e usuários novos não passam por aqui: seguem `SUGGESTED_PROFILES` e a tela de grupos.
Reversível: remove as concessões e as ações.
"""

from django.db import migrations

GROUP_KEY = "telas"

NEW_ACTIONS = {
    "tela.inicio": ("Ver Início", "Mostra o Início no menu."),
    "tela.notificacoes": ("Ver Notificações", "Mostra as Notificações no menu."),
    "tela.equipe": ("Ver Equipe", "Mostra Equipe (pessoas, capacidade e carga) no menu."),
    "tela.gargalos": ("Ver Filas e gargalos", "Mostra Filas e gargalos no menu."),
    "tela.insights": ("Ver Insights e resultados", "Mostra Insights, Desenvolvimento e Resultados no menu."),
    "tela.empresas": ("Ver Empresas", "Mostra o cadastro de empresas no menu."),
    "tela.setores": ("Ver Setores", "Mostra o cadastro de setores (equipes) no menu."),
    "tela.clientes": ("Ver Clientes", "Mostra o cadastro de clientes no menu."),
    "tela.obras": ("Ver Obras", "Mostra o cadastro de obras no menu."),
    "tela.centros_custo": ("Ver Centros de custo", "Mostra o cadastro de centros de custo no menu."),
    "tela.configuracoes": ("Ver Configurações", "Mostra as Configurações no menu."),
    "tela.integracoes": ("Ver Integrações", "Mostra as Integrações no menu."),
}

CADASTROS = (
    "tela.empresas", "tela.setores", "tela.clientes", "tela.obras", "tela.centros_custo",
)
CADASTRO_TRIGGERS = frozenset(
    {
        "setor.editar", "empresa.gerir", "motivo_devolucao.gerir", "estagio_tarefa.gerir", "tag.gerir",
        "processo.visualizar", "cliente.gerir", "obra.gerir", "centro_custo.gerir",
    }
)
ADMIN_TRIGGERS = CADASTRO_TRIGGERS | {"usuario.visualizar", "seguranca.gerir_perfis"}

#: (ações de menu a conceder, o que a pessoa já tinha para enxergar o item — None = todos)
RULES = [
    (("tela.inicio", "tela.notificacoes"), None),
    (("tela.equipe", "tela.gargalos", "tela.insights"), frozenset({"metricas.visualizar"})),
    (CADASTROS, CADASTRO_TRIGGERS),
    (("tela.configuracoes", "tela.integracoes"), ADMIN_TRIGGERS),
]


def _wanted(held_keys):
    """Ações `tela.*` que quem tem `held_keys` precisa para continuar vendo o que via."""
    wanted = set()
    for granted, triggers in RULES:
        if triggers is None or held_keys & triggers:
            wanted.update(granted)
    return wanted


def create_actions_and_grants(apps, schema_editor):
    Action = apps.get_model("acessos", "Action")
    ActionGroup = apps.get_model("acessos", "ActionGroup")
    Profile = apps.get_model("acessos", "Profile")
    ProfileAction = apps.get_model("acessos", "ProfileAction")
    UserAction = apps.get_model("acessos", "UserAction")

    group, _ = ActionGroup.objects.get_or_create(key=GROUP_KEY, defaults={"name": "Telas do menu", "order": 99})
    for key, (name, description) in NEW_ACTIONS.items():
        Action.objects.get_or_create(
            key=key,
            defaults={"group": group, "name": name, "description": description, "is_sensitive": False},
        )
    tela_ids = {action.key: action.pk for action in Action.objects.filter(key__in=NEW_ACTIONS)}

    # Perfis: o que o perfil já concede decide o que ele passa a mostrar no menu.
    for profile in Profile.objects.all():
        held = set(
            ProfileAction.objects.filter(profile_id=profile.pk).values_list("action__key", flat=True)
        )
        for key in _wanted(held):
            ProfileAction.objects.get_or_create(profile_id=profile.pk, action_id=tela_ids[key])

    # Concessões diretas: por pessoa e escopo, no mesmo escopo da concessão que justificou.
    pairs = {}
    rows = UserAction.objects.filter(is_active=True).exclude(action__key__in=NEW_ACTIONS)
    for user_id, scope_id, organization_id, key in rows.values_list(
        "user_id", "scope_id", "organization_id", "action__key"
    ):
        pairs.setdefault((user_id, scope_id, organization_id), set()).add(key)
    for (user_id, scope_id, organization_id), held in pairs.items():
        for key in _wanted(held):
            UserAction.objects.get_or_create(
                user_id=user_id,
                scope_id=scope_id,
                action_id=tela_ids[key],
                is_active=True,
                defaults={"organization_id": organization_id},
            )


def remove_actions_and_grants(apps, schema_editor):
    Action = apps.get_model("acessos", "Action")
    ActionGroup = apps.get_model("acessos", "ActionGroup")
    ProfileAction = apps.get_model("acessos", "ProfileAction")
    UserAction = apps.get_model("acessos", "UserAction")

    ids = list(Action.objects.filter(key__in=NEW_ACTIONS).values_list("pk", flat=True))
    ProfileAction.objects.filter(action_id__in=ids).delete()
    UserAction.objects.filter(action_id__in=ids).delete()
    Action.objects.filter(pk__in=ids).delete()
    ActionGroup.objects.filter(key=GROUP_KEY, actions__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [("acessos", "0005_quadros_actions")]

    operations = [migrations.RunPython(create_actions_and_grants, remove_actions_and_grants)]
