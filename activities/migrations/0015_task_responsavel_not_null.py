import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def check_no_task_without_responsavel(apps, schema_editor):
    Task = apps.get_model("activities", "Task")
    missing = Task.objects.filter(responsavel__isnull=True).count()
    if missing:
        raise RuntimeError(
            f"{missing} tarefa(s) ainda sem responsavel -- a migracao 0014 nao cobriu todos os "
            "casos. Corrija manualmente antes de aplicar esta migracao."
        )


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0014_populate_task_responsavel"),
    ]

    operations = [
        migrations.RunPython(check_no_task_without_responsavel, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="task",
            name="responsavel",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tasks_responsavel",
                to=settings.AUTH_USER_MODEL,
                verbose_name="responsável",
                help_text="Quem responde pela conclusão da tarefa.",
            ),
        ),
    ]
