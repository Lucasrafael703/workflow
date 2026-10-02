from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0014_seed_default_conditions"),
    ]

    operations = [
        migrations.AddField(
            model_name="sector",
            name="color",
            field=models.CharField(
                default="#3B82F6",
                help_text="Cor visual do setor nas listas, filtros e cartões.",
                max_length=7,
                verbose_name="cor",
            ),
        ),
    ]
