"""A nota do evento "Demanda criada" guarda o código da demanda (`IntakeService.convert`). Acompanha a troca
do prefixo `ATV-` por `DEM-` feita em `activities/0020_codigo_da_demanda`. Só mexe em nota que é exatamente
um código (o que o sistema gravou); reversível e idempotente."""

import re

from django.db import migrations

OLD_PREFIX = "ATV"
NEW_PREFIX = "DEM"
CODE_NUMBER = r"-\d{4}-\d{5}"


def _swap_prefix(apps, old_prefix, new_prefix):
    Event = apps.get_model("intake", "IntakeEvent")
    exactly_a_code = re.compile(rf"^{old_prefix}{CODE_NUMBER}$")
    for event in Event.objects.filter(kind="CONVERTIDA", note__startswith=f"{old_prefix}-"):
        if exactly_a_code.match(event.note):
            Event.objects.filter(pk=event.pk).update(note=f"{new_prefix}{event.note[len(old_prefix):]}")


def to_demanda(apps, schema_editor):
    _swap_prefix(apps, OLD_PREFIX, NEW_PREFIX)


def to_atividade(apps, schema_editor):
    _swap_prefix(apps, NEW_PREFIX, OLD_PREFIX)


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0020_codigo_da_demanda"),
        ("intake", "0002_atividade_vira_demanda_nos_rotulos"),
    ]

    operations = [
        migrations.RunPython(to_demanda, to_atividade),
    ]
