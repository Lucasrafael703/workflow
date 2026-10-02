from django.db import migrations


def seed_default_conditions(apps, schema_editor):
    """Gives each sector workflow a safe, manual initial condition.

    This never converts queue/execution/blocking states. It only provides a
    ``Normal`` condition where the sector has not configured a default yet.
    """
    Sector = apps.get_model("core", "Sector")
    WorkflowStatus = apps.get_model("core", "WorkflowStatus")

    for sector in Sector.objects.all().iterator():
        for domain in ("activity", "task"):
            rows = WorkflowStatus.objects.filter(
                organization_id=sector.organization_id,
                sector_id=sector.pk,
                domain=domain,
            )
            if rows.filter(is_default=True).exists():
                continue
            normal = rows.filter(name__iexact="Normal").first()
            if normal is None:
                last = rows.order_by("-order").values_list("order", flat=True).first() or 0
                normal = WorkflowStatus.objects.create(
                    organization_id=sector.organization_id,
                    sector_id=sector.pk,
                    domain=domain,
                    name="Normal",
                    color="#94A3B8",
                    order=last + 1,
                    is_active=True,
                    is_default=True,
                    behavior="",
                )
            else:
                normal.is_default = True
                normal.save(update_fields=["is_default"])


class Migration(migrations.Migration):
    dependencies = [("core", "0013_stage_column_limit")]

    operations = [migrations.RunPython(seed_default_conditions, migrations.RunPython.noop)]
