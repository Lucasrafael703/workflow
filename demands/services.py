from django.db import transaction
from django.utils import timezone

from audit.models import AuditLog
from audit.services import AuditService

from .models import DemandDecision


class DemandServiceError(Exception):
    pass


class DemandService:
    @staticmethod
    @transaction.atomic
    def decide(demand, usuario, status, decision_fields, process_template=None, process_title=""):
        if not usuario.has_perm("demands.can_qualify_demand"):
            raise DemandServiceError("Você não tem permissão para qualificar demandas.")

        decision, _ = DemandDecision.objects.get_or_create(demand=demand)
        old_status = decision.status

        for field, value in decision_fields.items():
            setattr(decision, field, value)
        decision.status = status
        decision.decided_by = usuario
        decision.decided_at = timezone.now()

        if status == DemandDecision.Decision.CONVERTIDA and not decision.resulting_process_id:
            if not process_template:
                raise DemandServiceError("Selecione um template de processo para converter a demanda.")
            from workflows.services import WorkflowService

            process = WorkflowService.instanciar_processo(
                template=process_template,
                title=process_title or f"{demand.protocol} - {demand.client_name}",
                criado_por=usuario,
                demand=demand,
            )
            decision.resulting_process = process

        decision.save()

        AuditService.log(
            user=usuario,
            action=AuditLog.Action.DECIDE,
            demand=demand,
            field_name="status",
            old_value=old_status,
            new_value=decision.status,
        )
        return decision
