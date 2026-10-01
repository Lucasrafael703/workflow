"""A "Atividade" passou a se chamar "Demanda": ajusta o texto que o sistema já gravou nas notificações.

Só mexe no texto fixo que o próprio sistema escreveu. O que a pessoa digitou (título da demanda,
motivo, comentário) fica como está: as trocas são exatas (títulos conhecidos) ou ancoradas em
trechos fixos da frase (começo, " assumiu a atividade '", "' da atividade '" e o final).
Reverter não desfaz o texto (não dá para saber o que foi digitado), e não é preciso.
"""

import re

from django.db import migrations

TITLES = {
    "Atividade criada": "Demanda criada",
    "Dono da atividade alterado": "Dono da demanda alterado",
    "Atividade assumida": "Demanda assumida",
    "Atividade concluída": "Demanda concluída",
    "Atividade cancelada": "Demanda cancelada",
    "Atividade reaberta": "Demanda reaberta",
    "Atividade finalizada": "Demanda finalizada",
    "Atividade aguardando sua aprovação": "Demanda aguardando sua aprovação",
    "Atividade pendente": "Demanda pendente",
    "Nova mensagem na atividade": "Nova mensagem na demanda",
    "Processo aplicado à atividade": "Processo aplicado à demanda",
}

# (padrão, troca) aplicados à mensagem; cada um só casa com o trecho fixo que o sistema escreve.
MESSAGE_RULES = [
    (re.compile(r"^A atividade '"), "A demanda '"),
    (re.compile(r"^(\S+) assumiu a atividade '"), r"\1 assumiu a demanda '"),
    (re.compile(r"(^A tarefa '.*?)' da atividade '", re.S), r"\1' da demanda '"),
    (re.compile(r"(^A pendência de '.*' foi aprovada\.) A atividade voltou para a sua fila\.$", re.S),
     r"\1 A demanda voltou para a sua fila."),
]


# A mensagem destes eventos é texto que a pessoa digitou (comentário, menção): não se mexe.
USER_TEXT_EVENTS = ("MENTIONED", "MESSAGE_POSTED")


def rewrite(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    for notification in Notification.objects.filter(title__in=list(TITLES)) | Notification.objects.filter(
        message__contains="ativid"
    ):
        title = TITLES.get(notification.title, notification.title)
        message = notification.message
        if notification.event_type not in USER_TEXT_EVENTS:
            for pattern, replacement in MESSAGE_RULES:
                message = pattern.sub(replacement, message, count=1)
        if (title, message) != (notification.title, notification.message):
            notification.title, notification.message = title, message
            notification.save(update_fields=["title", "message"])


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0007_atividade_vira_demanda_nos_rotulos"),
    ]

    operations = [
        migrations.RunPython(rewrite, migrations.RunPython.noop),
    ]
