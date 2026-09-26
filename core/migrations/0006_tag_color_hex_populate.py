from django.db import migrations

# Duplicado deliberadamente aqui: migrações não devem depender de código de
# app (core/colors.py) que pode mudar depois que esta migração já rodou.
LEGACY_TO_HEX = {
    0: "#94A3B8",  # CINZA
    1: "#3B82F6",  # AZUL
    2: "#22C55E",  # VERDE
    3: "#FACC15",  # AMARELO
    4: "#F97316",  # LARANJA
    5: "#EF4444",  # VERMELHO
    6: "#9333EA",  # ROXO
}
HEX_TO_LEGACY = {hex_value: legacy for legacy, hex_value in LEGACY_TO_HEX.items()}
DEFAULT_LEGACY = 0
DEFAULT_HEX = "#94A3B8"


def populate_hex(apps, schema_editor):
    Tag = apps.get_model("core", "Tag")
    tags = list(Tag.objects.all())
    for tag in tags:
        tag.color_hex = LEGACY_TO_HEX.get(tag.color, DEFAULT_HEX)
    Tag.objects.bulk_update(tags, ["color_hex"])


def revert_hex(apps, schema_editor):
    """Best-effort: cores livres escolhidas fora do mapa antigo (já usando a
    paleta de 36) caem no cinza legado, pois não têm equivalente exato entre
    as 7 cores antigas."""
    Tag = apps.get_model("core", "Tag")
    tags = list(Tag.objects.all())
    for tag in tags:
        tag.color = HEX_TO_LEGACY.get((tag.color_hex or "").upper(), DEFAULT_LEGACY)
    Tag.objects.bulk_update(tags, ["color"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_enumcolor_and_color_fields"),
    ]

    operations = [
        migrations.RunPython(populate_hex, revert_hex),
    ]
