from django.db import migrations, models


class Migration(migrations.Migration):
    """Limite informativo de itens por coluna do Kanban (etapa de demanda e de tarefa)."""

    dependencies = [
        ("core", "0012_sector_scoped_stages_conditions"),
    ]

    operations = [
        migrations.AddField(
            model_name="activitystage",
            name="column_limit",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Máximo de itens esperado nesta etapa no quadro Kanban. Só avisa: nunca impede de mover ou criar.",
                null=True,
                verbose_name="limite da coluna",
            ),
        ),
        migrations.AddField(
            model_name="taskstage",
            name="column_limit",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Máximo de itens esperado nesta etapa no quadro Kanban. Só avisa: nunca impede de mover ou criar.",
                null=True,
                verbose_name="limite da coluna",
            ),
        ),
    ]
