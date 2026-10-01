"""A "Atividade" passou a se chamar "Demanda" na interface: renomeia as chaves de permissão
(`atividade.criar` → `demanda.criar`, …) e a do grupo (`atividades` → `demandas`).

A chave aparece na tela de permissões, então ela acompanha o nome. Renomeia **no próprio
registro**: perfis e concessões diretas apontam para a ação pelo id e continuam valendo. Só se o
`seed_acoes` do código novo tiver rodado antes desta migração (as chaves novas já existem) é que
os registros antigos são fundidos nos novos, passando para eles os perfis e as concessões.
"""

from django.db import migrations

OLD_PREFIX, NEW_PREFIX = "atividade.", "demanda."
OLD_GROUP, NEW_GROUP = "atividades", "demandas"


def _merge_into(apps, old, new):
    """Passa perfis e concessões diretas de `old` para `new` e remove `old`."""
    ProfileAction = apps.get_model("acessos", "ProfileAction")
    UserAction = apps.get_model("acessos", "UserAction")
    for link in ProfileAction.objects.filter(action=old):
        if ProfileAction.objects.filter(profile_id=link.profile_id, action=new).exists():
            link.delete()
        else:
            link.action = new
            link.save(update_fields=["action"])
    for grant in UserAction.objects.filter(action=old):
        if UserAction.objects.filter(
            user_id=grant.user_id, action=new, scope_id=grant.scope_id, is_active=grant.is_active
        ).exists():
            grant.delete()
        else:
            grant.action = new
            grant.save(update_fields=["action"])
    old.delete()


def _rename(apps, old_prefix, new_prefix, old_group, new_group):
    Action = apps.get_model("acessos", "Action")
    ActionGroup = apps.get_model("acessos", "ActionGroup")

    for action in Action.objects.filter(key__startswith=old_prefix):
        new_key = new_prefix + action.key[len(old_prefix):]
        existing = Action.objects.filter(key=new_key).exclude(pk=action.pk).first()
        if existing is None:
            action.key = new_key
            action.save(update_fields=["key"])
        else:
            _merge_into(apps, action, existing)

    old = ActionGroup.objects.filter(key=old_group).first()
    if old is None:
        return
    new = ActionGroup.objects.filter(key=new_group).first()
    if new is None:
        old.key = new_group
        old.save(update_fields=["key"])
    else:
        Action.objects.filter(group=old).update(group=new)
        old.delete()


def to_demanda(apps, schema_editor):
    _rename(apps, OLD_PREFIX, NEW_PREFIX, OLD_GROUP, NEW_GROUP)


def to_atividade(apps, schema_editor):
    _rename(apps, NEW_PREFIX, OLD_PREFIX, NEW_GROUP, OLD_GROUP)


class Migration(migrations.Migration):

    dependencies = [
        ("acessos", "0002_atividade_vira_demanda_nos_rotulos"),
    ]

    operations = [
        migrations.RunPython(to_demanda, to_atividade),
    ]
