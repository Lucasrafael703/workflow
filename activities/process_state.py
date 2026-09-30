"""Leitura do estado de um processo já aplicado a uma atividade.

Só consultas, sem gravação e sem importar `services`: tanto `services.py`
(que precisa saber o que falta antes de iniciar uma tarefa ou finalizar a
atividade) quanto `process_application.py` e as views usam este módulo, e
por isso ele não pode depender de nenhum deles.

O molde (`ProcessVersion`, `ProcessInput`, `ProcessCriterion`) é imutável; o
que muda durante a execução são as linhas `ActivityInputValue` e
`ActivityCriterionCheck` da atividade (Regras 12 §19, §28-31).
"""

from processes.models import ActivityCriterionCheck, ActivityInputValue

from .models import Task


def input_values(activity):
    """Inputs da atividade, na ordem do molde."""
    return list(
        ActivityInputValue.objects.filter(activity=activity)
        .select_related("process_input", "received_by")
        .order_by("process_input__order", "pk")
    )


def criterion_checks(activity):
    """Critérios de aceite da atividade, na ordem do molde."""
    return list(
        ActivityCriterionCheck.objects.filter(activity=activity)
        .select_related("process_criterion", "met_by")
        .order_by("process_criterion__order", "pk")
    )


def missing_required_inputs(activity):
    """Inputs obrigatórios ainda não recebidos (Regras 12 §10)."""
    if not activity.process_version_id:
        return []
    return list(
        ActivityInputValue.objects.filter(
            activity=activity, process_input__is_required=True, is_received=False
        )
        .select_related("process_input")
        .order_by("process_input__order", "pk")
    )


def unmet_required_criteria(activity):
    """Critérios obrigatórios ainda não atendidos (Regras 12 §14)."""
    if not activity.process_version_id:
        return []
    return list(
        ActivityCriterionCheck.objects.filter(
            activity=activity, process_criterion__is_required=True, is_met=False
        )
        .select_related("process_criterion")
        .order_by("process_criterion__order", "pk")
    )


def unmet_optional_criteria(activity):
    if not activity.process_version_id:
        return []
    return list(
        ActivityCriterionCheck.objects.filter(
            activity=activity, process_criterion__is_required=False, is_met=False
        )
        .select_related("process_criterion")
        .order_by("process_criterion__order", "pk")
    )


def _names(rows, attr):
    return [getattr(row, attr).name for row in rows]


def missing_required_input_names(activity):
    return _names(missing_required_inputs(activity), "process_input")


def unmet_required_criterion_names(activity):
    return _names(unmet_required_criteria(activity), "process_criterion")


def step_state(task):
    """Situação de uma etapa do processo a partir da tarefa que a materializou.

    Devolve `(codigo, rotulo)`. "aguardando" cobre a tarefa que ainda não
    entrou na fila porque a etapa anterior não foi concluída.
    """
    if task.status == Task.Status.CONCLUIDA:
        return "concluida", "Concluída"
    if task.status == Task.Status.CANCELADA:
        return "cancelada", "Cancelada"
    if task.status == Task.Status.BLOQUEADA:
        return "bloqueada", "Bloqueada"
    if task.status == Task.Status.EM_EXECUCAO:
        return "em_execucao", "Em execução"
    dependency = task.depends_on
    if dependency is not None and dependency.status != Task.Status.CONCLUIDA:
        return "aguardando", "Aguardando etapa anterior"
    return "na_fila", "Na fila"


def process_panel(activity, tasks=None):
    """Tudo o que a ficha da atividade mostra sobre o processo aplicado.

    `tasks` permite reaproveitar a lista já carregada pela view (com
    `select_related("sector", "responsavel", "depends_on", "process_step")`);
    sem ela, a consulta é feita aqui. Retorna `None` quando a atividade não
    tem processo aplicado.
    """
    if not activity.process_version_id:
        return None

    version = activity.process_version
    process = version.process

    inputs = input_values(activity)
    checks = criterion_checks(activity)

    if tasks is None:
        tasks = list(
            activity.tasks.filter(process_step__isnull=False)
            .select_related("sector", "responsavel", "depends_on", "process_step")
            .order_by("process_step__order", "pk")
        )
    steps = []
    for task in tasks:
        if task.process_step_id is None:
            continue
        code, label = step_state(task)
        steps.append(
            {
                "task": task,
                "order": task.process_step.order,
                "state": code,
                "state_label": label,
            }
        )
    steps.sort(key=lambda row: (row["order"], row["task"].pk))

    received = sum(1 for row in inputs if row.is_received)
    met = sum(1 for row in checks if row.is_met)
    done_steps = sum(1 for row in steps if row["state"] == "concluida")

    missing_required = [row for row in inputs if row.process_input.is_required and not row.is_received]
    unmet_required = [row for row in checks if row.process_criterion.is_required and not row.is_met]

    return {
        "version": version,
        "process": process,
        "output_description": version.output_description,
        "output_evidence_label": version.get_output_evidence_type_display() if version.output_evidence_type else "",
        "inputs": inputs,
        "inputs_received": received,
        "inputs_total": len(inputs),
        "missing_required_inputs": missing_required,
        "steps": steps,
        "steps_done": done_steps,
        "steps_total": len(steps),
        "criteria": checks,
        "criteria_met": met,
        "criteria_total": len(checks),
        "unmet_required_criteria": unmet_required,
    }
