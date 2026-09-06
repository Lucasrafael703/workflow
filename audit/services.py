from .models import AuditLog


class AuditService:
    """Único caminho de escrita de AuditLog. Nenhum outro código deve chamar
    AuditLog.objects.create(...) diretamente."""

    @staticmethod
    def log(
        user,
        action,
        demand=None,
        process=None,
        step=None,
        field_name="",
        old_value="",
        new_value="",
        reason="",
    ):
        return AuditLog.objects.create(
            user=user,
            demand=demand,
            process=process,
            step=step,
            action=action,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else "",
            new_value=str(new_value) if new_value is not None else "",
            reason=reason,
        )
