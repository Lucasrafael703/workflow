from django.db import migrations


def populate_responsavel(apps, schema_editor):
    """Para cada tarefa sem responsável, usa o primeiro TaskExecutor (por
    added_at, priorizando quem ainda está ativo) como responsável -- os
    demais continuam como participantes. Sem nenhum executor histórico,
    cai para created_by (unica pessoa garantidamente nao-nula em toda
    Task). A linha de TaskExecutor escolhida vira responsavel e e' soft-
    deletada (removed_at), nunca apagada -- preserva o rastro de que essa
    pessoa ja foi executora antes da reestruturacao. Trocas humanas depois
    desta migracao geram TaskResponsavelChangeLog normalmente; esta carga
    inicial nao gera log, so popula o campo."""
    Task = apps.get_model("activities", "Task")
    TaskExecutor = apps.get_model("activities", "TaskExecutor")

    count = 0
    for task in Task.objects.filter(responsavel__isnull=True).iterator():
        link = (
            TaskExecutor.objects.filter(task=task, removed_at__isnull=True).order_by("added_at").first()
            or TaskExecutor.objects.filter(task=task).order_by("added_at").first()
        )
        if link is not None:
            task.responsavel_id = link.user_id
            task.save(update_fields=["responsavel"])
            if link.removed_at is None:
                from django.utils import timezone

                link.removed_at = timezone.now()
                link.save(update_fields=["removed_at"])
        else:
            task.responsavel_id = task.created_by_id
            task.save(update_fields=["responsavel"])
        count += 1
    print(f"Responsavel populado para {count} tarefa(s).")


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0013_task_responsavel"),
    ]

    operations = [
        migrations.RunPython(populate_responsavel, migrations.RunPython.noop),
    ]
