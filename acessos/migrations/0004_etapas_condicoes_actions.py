from django.db import migrations


NEW_ACTIONS = {
    "demanda.definir_etapa": ("demandas", "Definir etapa da demanda", "Permite selecionar a etapa visual da demanda dentro do seu setor."),
    "demanda.definir_condicao": ("demandas", "Definir condição da demanda", "Permite selecionar a condição manual da demanda dentro do seu setor."),
    "tarefa.definir_etapa": ("tarefas", "Definir etapa da tarefa", "Permite selecionar a etapa visual da tarefa dentro do seu setor."),
    "tarefa.definir_condicao": ("tarefas", "Definir condição da tarefa", "Permite selecionar a condição manual da tarefa dentro do seu setor."),
    "etapa.gerir": ("cadastros", "Gerir etapas", "Permite manter etapas de demandas e tarefas por setor."),
    "condicao.gerir": ("cadastros", "Gerir condições", "Permite manter condições manuais por setor."),
}


def copy_grants(apps, schema_editor):
    Action = apps.get_model("acessos", "Action")
    ActionGroup = apps.get_model("acessos", "ActionGroup")
    ProfileAction = apps.get_model("acessos", "ProfileAction")
    UserAction = apps.get_model("acessos", "UserAction")

    groups = {group.key: group for group in ActionGroup.objects.all()}
    for key, (group_key, name, description) in NEW_ACTIONS.items():
        group = groups.get(group_key)
        if group is None:
            group = ActionGroup.objects.create(key=group_key, name=group_key.title(), order=99)
            groups[group_key] = group
        Action.objects.get_or_create(
            key=key,
            defaults={"group": group, "name": name, "description": description, "is_sensitive": False},
        )

    # Preserve actual authority: someone who could move a visual stage can
    # select it in the new list control; existing configuration authority maps
    # to the equivalent sector-scoped maintenance actions.
    mappings = {
        "demanda.mover_estagio": ("demanda.definir_etapa", "demanda.definir_condicao"),
        "tarefa.mover_estagio": ("tarefa.definir_etapa", "tarefa.definir_condicao"),
        "estagio_tarefa.gerir": ("etapa.gerir",),
        "cor_status.gerir": ("condicao.gerir",),
    }
    actions = {action.key: action for action in Action.objects.filter(key__in=set(mappings) | set(NEW_ACTIONS))}
    for old_key, new_keys in mappings.items():
        old = actions.get(old_key)
        if old is None:
            continue
        for new_key in new_keys:
            new = actions[new_key]
            for row in ProfileAction.objects.filter(action_id=old.pk):
                ProfileAction.objects.get_or_create(profile_id=row.profile_id, action_id=new.pk)
            for row in UserAction.objects.filter(action_id=old.pk):
                UserAction.objects.get_or_create(
                    organization_id=row.organization_id,
                    user_id=row.user_id,
                    action_id=new.pk,
                    scope_id=row.scope_id,
                    is_active=row.is_active,
                    defaults={"created_by_id": row.created_by_id},
                )


class Migration(migrations.Migration):

    dependencies = [("acessos", "0003_chaves_demanda")]

    operations = [migrations.RunPython(copy_grants, migrations.RunPython.noop)]
