"""Ações `quadro.*` (app `boards`) e quem já pode usá-las.

O `seed_acoes` cria as ações novas, mas não as acrescenta a perfis que já existem: sem esta migração, o
administrador de uma organização em produção não conseguiria nem abrir um quadro. As concessões seguem a
autoridade que a pessoa já tem, como fez a `0004`:

- quem gere perfis (`seguranca.gerir_perfis`, o administrador) recebe todas as ações de quadro;
- quem cria demandas (`demanda.criar`) recebe ver quadros e criar/editar itens;
- quem aprova pendência (`demanda.aprovar_pendencia`, o gestor) recebe também criar/editar quadros, gerir
  colunas e excluir itens.

Concessões diretas a pessoas (fora de perfil) não são copiadas. Reversível: remove as concessões e as ações.
"""

from django.db import migrations

GROUP_KEY = "quadros"

NEW_ACTIONS = {
    "quadro.visualizar": ("Ver quadros", "Permite abrir os quadros da organização e ler seus itens e o histórico de alterações.", False),
    "quadro.criar": ("Criar quadros", "Permite criar um quadro novo, inclusive a partir de um modelo.", False),
    "quadro.editar": ("Editar quadros", "Permite renomear o quadro e criar, renomear e remover grupos.", False),
    "quadro.excluir": ("Excluir quadros", "Permite excluir um quadro (o histórico é preservado).", True),
    "quadro.gerir_colunas": ("Gerir colunas do quadro", "Permite criar, renomear, mover, redimensionar, configurar, ocultar, duplicar, converter e excluir colunas, e manter as etiquetas de status e lista.", False),
    "quadro.criar_item": ("Criar itens do quadro", "Permite adicionar itens (linhas) a um quadro.", False),
    "quadro.editar_item": ("Editar itens do quadro", "Permite alterar o nome dos itens, o valor das células e mover itens entre grupos.", False),
    "quadro.excluir_item": ("Excluir itens do quadro", "Permite excluir itens de um quadro (o histórico é preservado).", False),
}

WORKER = ("quadro.visualizar", "quadro.criar_item", "quadro.editar_item")
MANAGER = WORKER + ("quadro.criar", "quadro.editar", "quadro.gerir_colunas", "quadro.excluir_item")
ADMIN = tuple(NEW_ACTIONS)

#: ação que a pessoa já tem -> o que ela passa a ter em quadros
MAPPINGS = {
    "demanda.criar": WORKER,
    "demanda.aprovar_pendencia": MANAGER,
    "seguranca.gerir_perfis": ADMIN,
}


def create_actions_and_grants(apps, schema_editor):
    Action = apps.get_model("acessos", "Action")
    ActionGroup = apps.get_model("acessos", "ActionGroup")
    ProfileAction = apps.get_model("acessos", "ProfileAction")

    group, _ = ActionGroup.objects.get_or_create(key=GROUP_KEY, defaults={"name": "Quadros", "order": 99})
    for key, (name, description, sensitive) in NEW_ACTIONS.items():
        Action.objects.get_or_create(
            key=key,
            defaults={"group": group, "name": name, "description": description, "is_sensitive": sensitive},
        )

    new_actions = {action.key: action for action in Action.objects.filter(key__in=NEW_ACTIONS)}
    held = {action.key: action for action in Action.objects.filter(key__in=MAPPINGS)}
    for existing_key, granted_keys in MAPPINGS.items():
        existing = held.get(existing_key)
        if existing is None:
            continue
        for profile_id in ProfileAction.objects.filter(action_id=existing.pk).values_list("profile_id", flat=True):
            for key in granted_keys:
                ProfileAction.objects.get_or_create(profile_id=profile_id, action_id=new_actions[key].pk)


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

    dependencies = [("acessos", "0004_etapas_condicoes_actions")]

    operations = [migrations.RunPython(create_actions_and_grants, remove_actions_and_grants)]
