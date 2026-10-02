from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0007_demand_boards"),
        ("activities", "0023_activity_message_threads"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="board_setup_mode",
            field=models.CharField(
                choices=[("BLANK", "Começar em branco"), ("TEMPLATE", "Usar quadro existente")],
                default="BLANK",
                max_length=12,
                verbose_name="modo de quadro de tarefas",
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="board_template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="draft_activities",
                to="boards.board",
                verbose_name="modelo de quadro selecionado",
            ),
        ),
    ]
