from decimal import Decimal

from django.db import migrations


STEP = Decimal("1000")


FIELDS = {
    "DEMAND": [
        ("title", "Título da demanda", "TEXT"), ("owner", "Responsável", "PERSON"),
        ("sector", "Setor", "SECTOR"), ("urgency", "Prioridade", "PRIORITY"),
        ("requested_deadline", "Prazo", "DATETIME"), ("stage", "Status", "STAGE"),
        ("condition", "Condição", "SELECT"), ("tasks", "Tarefas", "CHECKLIST"),
    ],
    "TASK": [
        ("title", "Título da tarefa", "TEXT"), ("activity", "Demanda vinculada", "RELATION"),
        ("responsavel", "Responsável", "PERSON"), ("sector", "Setor", "SECTOR"),
        ("priority", "Prioridade", "PRIORITY"), ("requested_deadline", "Prazo", "DATETIME"),
        ("stage", "Status", "STAGE"), ("checklist", "Checklist", "CHECKLIST"),
    ],
}


def seed(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    Board = apps.get_model("boards", "DomainBoard")
    Field = apps.get_model("boards", "DomainBoardField")
    View = apps.get_model("boards", "DomainBoardView")
    Column = apps.get_model("boards", "DomainBoardViewColumn")
    CardField = apps.get_model("boards", "DomainBoardCardField")
    for organization in Organization.objects.all().iterator():
        for domain, name in (("DEMAND", "Demandas"), ("TASK", "Tarefas")):
            board, _ = Board.objects.get_or_create(organization=organization, domain=domain, defaults={"name": name})
            field_rows = []
            for position, (key, label, kind) in enumerate(FIELDS[domain], 1):
                field, _ = Field.objects.get_or_create(board=board, key=key, defaults={"label": label, "type": kind, "position": STEP * position, "is_system": True})
                field_rows.append(field)
            view_rows = []
            for position, (view_name, kind, settings) in enumerate((
                ("Quadro principal", "TABLE", {"group_by": "stage"}),
                ("Kanban", "KANBAN", {"group_by": "stage", "show_empty": True}),
                ("Calendário", "CALENDAR", {"date_field": "requested_deadline"}),
            ), 1):
                view, _ = View.objects.get_or_create(board=board, name=view_name, defaults={"type": kind, "position": STEP * position, "settings": settings, "is_default": position == 1})
                view_rows.append(view)
            for position, field in enumerate(field_rows, 1):
                Column.objects.get_or_create(view=view_rows[0], field=field, defaults={"position": STEP * position, "width": 250 if field.key == "title" else 168})
            for position, field in enumerate(field_rows, 1):
                if field.key in {"title", "owner", "responsavel", "sector", "priority", "urgency", "requested_deadline", "checklist", "activity"}:
                    CardField.objects.get_or_create(view=view_rows[1], field=field, defaults={"position": STEP * position, "is_visible": True})


class Migration(migrations.Migration):
    dependencies = [("boards", "0004_quadros_de_dominio")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
