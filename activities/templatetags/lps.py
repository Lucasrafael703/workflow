from django import template

from audit.models import AuditLog

register = template.Library()

# O histórico precisa ser lido por qualquer pessoa, não parecer log técnico
# (doc 09 §124). Cada evento vira uma frase em português.
ACTION_PHRASES = {
    AuditLog.Action.CREATE: "criou a atividade",
    AuditLog.Action.UPDATE: "alterou {field}",
    AuditLog.Action.OWNER_CHANGED: "transferiu a responsabilidade de {old} para {new}",
    AuditLog.Action.TASK_CREATED: "criou a tarefa {new}",
    AuditLog.Action.EXECUTOR_ADDED: "incluiu {new} como executor",
    AuditLog.Action.EXECUTOR_REMOVED: "removeu {new} dos executores",
    AuditLog.Action.SESSION_STARTED: "iniciou a execução",
    AuditLog.Action.SESSION_PAUSED: "pausou a execução",
    AuditLog.Action.SESSION_RESUMED: "retomou a execução",
    AuditLog.Action.SECTOR_MOVED: "enviou de {old} para {new}",
    AuditLog.Action.RETURNED: "devolveu a tarefa",
    AuditLog.Action.QUEUE_POSITION_CHANGED: "mudou a posição na fila de {old} para {new}",
    AuditLog.Action.DEADLINE_PROPOSED: "propôs um novo prazo",
    AuditLog.Action.DEADLINE_ACCEPTED: "aceitou o prazo proposto",
    AuditLog.Action.DEADLINE_REJECTED: "recusou o prazo proposto",
    AuditLog.Action.CONFLICT_OPENED: "abriu um conflito de prazo",
    AuditLog.Action.CONFLICT_RESOLVED: "resolveu o conflito de prazo",
    AuditLog.Action.BLOCK: "bloqueou a tarefa",
    AuditLog.Action.UNBLOCK: "resolveu o bloqueio",
    AuditLog.Action.COMPLETE: "concluiu",
    AuditLog.Action.REOPEN: "reabriu",
    AuditLog.Action.CANCEL: "cancelou",
}

FIELD_LABELS = {
    "title": "o título",
    "description": "a descrição",
    "requested_deadline": "o prazo solicitado",
    "company": "a empresa",
    "site": "a obra",
    "cost_center": "o centro de custo",
    "order": "a ordem",
    "depends_on": "a dependência",
}


@register.filter
def audit_phrase(entry):
    """Transforma um registro de auditoria em uma frase legível."""
    template_text = ACTION_PHRASES.get(entry.action, entry.get_action_display().lower())
    return template_text.format(
        field=FIELD_LABELS.get(entry.field_name, entry.field_name or "um campo"),
        old=entry.old_value or "—",
        new=entry.new_value or "—",
    )


@register.filter
def duration_hm(value):
    """Formata um timedelta como "4h20" ou "35min"."""
    if value is None:
        return "—"
    total_minutes = int(value.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h{minutes:02d}"
    if hours:
        return f"{hours}h"
    return f"{minutes}min"
