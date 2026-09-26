from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_tag_color_hex_populate"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="tag",
            name="color",
        ),
        migrations.RenameField(
            model_name="tag",
            old_name="color_hex",
            new_name="color",
        ),
        migrations.AlterField(
            model_name="tag",
            name="color",
            field=models.CharField(default="#94A3B8", max_length=7, verbose_name="cor"),
        ),
    ]
