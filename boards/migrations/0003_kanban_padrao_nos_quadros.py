from django.db import migrations

POSITION_STEP = 1000


def create_default_views(apps, schema_editor):
    """Todo quadro ganha um Kanban. Quadros criados antes das visualizações não têm: cria o padrão para eles."""
    Board = apps.get_model("boards", "Board")
    BoardView = apps.get_model("boards", "BoardView")
    for board in Board.objects.filter(is_active=True):
        if BoardView.objects.filter(board=board).exists():
            continue
        BoardView.objects.create(
            board=board, name="Kanban", type="KANBAN", position=POSITION_STEP, settings={}, created_by_id=board.created_by_id
        )


class Migration(migrations.Migration):
    dependencies = [("boards", "0002_boardview")]

    operations = [migrations.RunPython(create_default_views, migrations.RunPython.noop)]
