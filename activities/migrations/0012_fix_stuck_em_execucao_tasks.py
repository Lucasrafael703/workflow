from django.db import migrations
from django.db.models import Exists, OuterRef


def fix_stuck_tasks(apps, schema_editor):
    """Corrige tarefas que ficaram com status EM_EXECUCAO sem nenhuma
    WorkSession aberta -- efeito colateral da antiga Regra 04 §115, que
    pausava a sessao de uma tarefa sem rebaixar seu status quando a pessoa
    iniciava outra. Mesma logica que TaskService.pause ja usa."""
    Task = apps.get_model("activities", "Task")
    WorkSession = apps.get_model("activities", "WorkSession")

    open_sessions = WorkSession.objects.filter(task=OuterRef("pk"), ended_at__isnull=True)
    stuck = Task.objects.filter(status="EM_EXECUCAO").annotate(
        has_open_session=Exists(open_sessions)
    ).filter(has_open_session=False)

    count = stuck.update(status="EM_FILA")
    print(f"Corrigidas {count} tarefa(s) presas em EM_EXECUCAO sem sessao aberta.")


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0011_activity_internal_notes_activity_requested_by_and_more"),
    ]

    operations = [
        migrations.RunPython(fix_stuck_tasks, migrations.RunPython.noop),
    ]
