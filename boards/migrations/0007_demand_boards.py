from django.db import migrations, models
import django.db.models.deletion


def rename_default_item_label(apps, schema_editor):
    Board = apps.get_model("boards", "Board")
    Board.objects.filter(item_label="Elemento").update(item_label="Nome da Tarefa")


class Migration(migrations.Migration):
    dependencies = [
        ("activities", "0023_activity_message_threads"),
        ("boards", "0006_visualizacao_calendario"),
    ]

    operations = [
        migrations.AddField(
            model_name="board",
            name="kind",
            field=models.CharField(
                choices=[("TEMPLATE", "Modelo"), ("DEMAND", "Demanda")],
                default="TEMPLATE",
                max_length=16,
                verbose_name="tipo",
            ),
        ),
        migrations.AddField(
            model_name="board",
            name="sector",
            field=models.ForeignKey(
                blank=True,
                help_text="Obrigatório para novos modelos; quadros legados podem não ter setor.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="boards",
                to="core.sector",
                verbose_name="setor do modelo",
            ),
        ),
        migrations.AddField(
            model_name="board",
            name="activity",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="task_board",
                to="activities.activity",
                verbose_name="demanda",
            ),
        ),
        migrations.AddField(
            model_name="board",
            name="source_template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="instances",
                to="boards.board",
                verbose_name="modelo de origem",
            ),
        ),
        migrations.AddField(
            model_name="boardcolumn",
            name="binding",
            field=models.CharField(
                choices=[("CUSTOM", "Campo customizado"), ("TASK_RESPONSAVEL", "Responsável da tarefa")],
                default="CUSTOM",
                max_length=24,
                verbose_name="vínculo de domínio",
            ),
        ),
        migrations.AddField(
            model_name="boarditem",
            name="task",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="board_item",
                to="activities.task",
                verbose_name="tarefa operacional",
            ),
        ),
        migrations.AlterField(
            model_name="board",
            name="item_label",
            field=models.CharField(
                default="Nome da Tarefa",
                help_text="Como a primeira coluna (o nome de cada tarefa) se chama neste quadro.",
                max_length=60,
                verbose_name="título da coluna principal",
            ),
        ),
        migrations.AddIndex(
            model_name="board",
            index=models.Index(fields=["organization", "kind", "is_active"], name="boards_boar_organiz_99861b_idx"),
        ),
        migrations.AddConstraint(
            model_name="board",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(kind="TEMPLATE", activity__isnull=True)
                    | models.Q(kind="DEMAND", activity__isnull=False)
                ),
                name="board_kind_matches_activity",
            ),
        ),
        migrations.AddConstraint(
            model_name="boardcolumn",
            constraint=models.CheckConstraint(
                condition=(
                    ~models.Q(binding="TASK_RESPONSAVEL")
                    | models.Q(type="PERSON")
                ),
                name="board_responsavel_binding_is_person",
            ),
        ),
        migrations.AddConstraint(
            model_name="boardcolumn",
            constraint=models.UniqueConstraint(
                fields=("board", "binding"),
                condition=models.Q(binding="TASK_RESPONSAVEL", is_active=True),
                name="one_active_task_responsavel_binding",
            ),
        ),
        migrations.RunPython(rename_default_item_label, migrations.RunPython.noop),
    ]
