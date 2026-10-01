"""O código da demanda passa de `ATV-AAAA-NNNNN` para `DEM-AAAA-NNNNN` (01/10/2026).

Reescreve os códigos já emitidos e acompanha os anexos: a pasta `<empresa>/<código>/` é renomeada e o
nome guardado de cada arquivo aponta para ela. Só o prefixo muda; ano e número ficam, então a sequência
do ano segue de onde parou. Reversível e idempotente (rodar de novo não encontra mais nada para trocar).

Texto digitado pelas pessoas (título, descrição, comentários) não é tocado: a busca aceita o prefixo
antigo (`activities.models.code_search_term`) e os endereços antigos redirecionam.
"""

import os
import shutil

from django.conf import settings
from django.db import migrations

OLD_PREFIX = "ATV"
NEW_PREFIX = "DEM"


def _move_attachment_folder(Attachment, activity_id, old_code, new_code):
    """Leva os arquivos da demanda para a pasta do código novo e atualiza o nome guardado.

    Um arquivo que não está no disco (ex.: disco não persistente) só tem o nome ajustado. Um que não
    pôde ser movido (já existe um com o mesmo nome no destino, falta de permissão) mantém o nome antigo:
    continua sendo servido de onde está."""
    root = settings.ACTIVITY_FILES_ROOT
    old_folders = set()
    for attachment in Attachment.objects.filter(activity_id=activity_id):
        parts = attachment.file.name.split("/")
        if old_code not in parts[:-1]:
            continue
        new_parts = [new_code if part == old_code else part for part in parts]
        old_path = os.path.join(root, *parts)
        new_path = os.path.join(root, *new_parts)
        if os.path.isfile(old_path):
            if os.path.exists(new_path):
                continue
            try:
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                shutil.move(old_path, new_path)
            except OSError:
                continue
            old_folders.add(os.path.dirname(old_path))
        Attachment.objects.filter(pk=attachment.pk).update(file="/".join(new_parts))
    for folder in old_folders:
        try:
            os.rmdir(folder)
        except OSError:
            pass


def _rename_codes(apps, old_prefix, new_prefix):
    Activity = apps.get_model("activities", "Activity")
    Attachment = apps.get_model("activities", "ActivityAttachment")
    taken = set(Activity.objects.filter(code__startswith=f"{new_prefix}-").values_list("code", flat=True))
    for activity in Activity.objects.filter(code__startswith=f"{old_prefix}-").order_by("pk"):
        old_code = activity.code
        new_code = f"{new_prefix}{old_code[len(old_prefix):]}"
        if new_code in taken:
            # Não deveria acontecer (o deploy migra antes de o código novo emitir `DEM-`); deixar como está
            # é melhor do que travar a migração.
            continue
        Activity.objects.filter(pk=activity.pk).update(code=new_code)
        taken.add(new_code)
        _move_attachment_folder(Attachment, activity.pk, old_code, new_code)


def to_demanda(apps, schema_editor):
    _rename_codes(apps, OLD_PREFIX, NEW_PREFIX)


def to_atividade(apps, schema_editor):
    _rename_codes(apps, NEW_PREFIX, OLD_PREFIX)


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0019_atividade_vira_demanda_nos_rotulos"),
    ]

    operations = [
        migrations.RunPython(to_demanda, to_atividade),
    ]
