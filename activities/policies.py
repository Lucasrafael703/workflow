"""Políticas de transição: "dado este objeto e o estado em que ele está, o que
pode acontecer com ele?".

Uma só fonte para a regra de **estado** (e para as pré-condições que dependem
do objeto: dependência pendente, inputs do processo, ser responsável ou
participante, pendência aberta...). Os *services* continuam executando e
autorizando (`require_action`), mas perguntam aqui antes de gravar; as telas
perguntam aqui o que oferecer. Assim o botão que aparece e a recusa do servidor
nunca divergem.

- `check(obj, acao, user=None)` devolve a mensagem de recusa ou `None`.
- `assert_allowed(...)` levanta `ActivityError` com essa mensagem.
- `available(obj, user=None)` lista as ações que o estado permite (a permissão
  do catálogo é outro eixo: ver `*_PERMISSIONS` e `AuthorizationService.can_many`).

Sem `user`, só valem as regras de estado; com `user`, valem também as que
dependem da pessoa (ser responsável/participante, ter sessão aberta).
"""

from acessos import catalog

from . import process_state
from .errors import ActivityError
from .models import Activity, ActivityPendency, Task, TaskExecutor, WorkSession

TASK_TERMINAL = (Task.Status.CONCLUIDA, Task.Status.CANCELADA)
ACTIVITY_TERMINAL = (Activity.Status.CONCLUIDA, Activity.Status.CANCELADA)

#: Ação da política → ação do catálogo que a autoriza (o serviço continua exigindo).
TASK_PERMISSIONS = {
    "assume": catalog.TAREFA_ASSUMIR,
    "start": catalog.TAREFA_INICIAR,
    "pause": catalog.TAREFA_PAUSAR,
    "complete": catalog.TAREFA_CONCLUIR,
    "retroactive": catalog.TAREFA_CONCLUIR,
    "block": catalog.TAREFA_BLOQUEAR,
    "unblock": catalog.TAREFA_BLOQUEAR,
    "return": catalog.TAREFA_DEVOLVER,
    "cancel": catalog.TAREFA_CANCELAR,
    "reopen": catalog.TAREFA_REABRIR,
    "move_sector": catalog.TAREFA_MOVER_SETOR,
    "change_responsavel": catalog.TAREFA_ALTERAR_RESPONSAVEL,
    "edit": catalog.TAREFA_EDITAR,
}
ACTIVITY_PERMISSIONS = {
    "claim": catalog.ATIVIDADE_ASSUMIR,
    "edit": catalog.ATIVIDADE_EDITAR,
    "change_owner": catalog.ATIVIDADE_ALTERAR_DONO,
    "change_sector": catalog.ATIVIDADE_EDITAR,
    "complete": catalog.ATIVIDADE_CONCLUIR,
    "cancel": catalog.ATIVIDADE_CANCELAR,
    "reopen": catalog.ATIVIDADE_REABRIR,
    "mark_pending": catalog.ATIVIDADE_MARCAR_PENDENTE,
    "approve_pendency": catalog.ATIVIDADE_APROVAR_PENDENCIA,
    "resolve_pendency": catalog.ATIVIDADE_MARCAR_PENDENTE,
}


# ---------------------------------------------------------------------------
# Pré-condições compartilhadas
# ---------------------------------------------------------------------------


def pending_dependency(task):
    """A predecessora que ainda impede a tarefa de andar, ou `None`.

    Só `CONCLUIDA` satisfaz a dependência: predecessora cancelada, bloqueada
    ou devolvida continua segurando a sucessora. Consulta o estado atual no
    banco em vez de confiar em `task.depends_on`, que pode estar em cache.
    """
    if task.depends_on_id is None:
        return None
    dependency = Task.objects.filter(pk=task.depends_on_id).only("id", "title", "status").first()
    if dependency is not None and dependency.status != Task.Status.CONCLUIDA:
        return dependency
    return None


def dependency_message(task):
    dependency = pending_dependency(task)
    if dependency is None:
        return None
    return f"Esta tarefa depende da conclusão de «{dependency.title}»."


def process_inputs_message(task):
    """Tarefa gerada por processo só anda com os inputs obrigatórios recebidos
    (Regras 12 §10 / 08:1284). Tarefa manual não é afetada."""
    if task.process_step_id is None:
        return None
    missing = process_state.missing_required_input_names(task.activity)
    if not missing:
        return None
    return (
        "Antes de trabalhar nesta tarefa, registre o recebimento dos inputs obrigatórios do processo: "
        + "; ".join(missing)
        + "."
    )


def is_active_participant(task, user):
    return TaskExecutor.objects.filter(task=task, user=user, removed_at__isnull=True).exists()


def is_responsavel_or_participant(task, user):
    return task.responsavel_id == user.id or is_active_participant(task, user)


def has_active_queue_entry(task):
    return task.queue_entries.filter(left_at__isnull=True).exists()


class _Policy:
    """Mecânica comum: `_check_<ação>` devolve a mensagem de recusa ou `None`."""

    ACTIONS = ()

    @classmethod
    def check(cls, obj, action, user=None):
        rule = getattr(cls, f"_check_{action}", None)
        if rule is None:
            raise KeyError(f"Ação desconhecida: {action}")
        return rule(obj, user)

    @classmethod
    def assert_allowed(cls, obj, action, user=None):
        reason = cls.check(obj, action, user)
        if reason:
            raise ActivityError(reason)

    @classmethod
    def allows(cls, obj, action, user=None):
        return cls.check(obj, action, user) is None

    @classmethod
    def available(cls, obj, user=None):
        return [action for action in cls.ACTIONS if cls.check(obj, action, user) is None]


# ---------------------------------------------------------------------------
# Tarefa
# ---------------------------------------------------------------------------


class TaskTransitionPolicy(_Policy):
    """Estados: `DISPONIVEL` (inclui "aguardando etapa anterior"), `EM_FILA`,
    `DEVOLVIDA` (na fila do setor que recebeu, até alguém agir), `EM_EXECUCAO`,
    `BLOQUEADA`, `CONCLUIDA`, `CANCELADA`."""

    ACTIONS = (
        "start", "pause", "complete", "retroactive", "block", "unblock", "return", "cancel",
        "reopen", "move_sector", "change_responsavel", "edit", "assume",
    )

    #: Onde a tarefa pode ser iniciada/retomada.
    START_STATES = (Task.Status.DISPONIVEL, Task.Status.EM_FILA, Task.Status.DEVOLVIDA, Task.Status.EM_EXECUCAO)
    #: Onde pode ser concluída direto.
    COMPLETE_STATES = (Task.Status.EM_EXECUCAO, Task.Status.EM_FILA, Task.Status.DISPONIVEL, Task.Status.DEVOLVIDA)
    #: Ainda não iniciada: serve para "Já realizei este trabalho".
    NOT_STARTED_STATES = (Task.Status.EM_FILA, Task.Status.DISPONIVEL, Task.Status.DEVOLVIDA)

    @staticmethod
    def _check_start(task, user):
        if user is not None and not is_responsavel_or_participant(task, user):
            return "Somente o responsável ou participantes atribuídos podem iniciar a tarefa."
        if task.status not in TaskTransitionPolicy.START_STATES:
            return "Esta tarefa não pode ser iniciada no status atual."
        return dependency_message(task) or process_inputs_message(task)

    @staticmethod
    def _check_pause(task, user):
        if user is None:
            return None if task.status == Task.Status.EM_EXECUCAO else "Esta tarefa não está em execução."
        if not WorkSession.objects.filter(task=task, user=user, ended_at__isnull=True).exists():
            return "Você não possui uma sessão de trabalho ativa nesta tarefa."
        return None

    @staticmethod
    def _check_complete(task, user):
        if task.status not in TaskTransitionPolicy.COMPLETE_STATES:
            return "Esta tarefa não pode ser concluída no status atual."
        # Concluir também é "andar": sem isto, uma etapa que aguarda a anterior
        # (DISPONIVEL, fora da fila) poderia ser concluída fora de ordem.
        return dependency_message(task) or process_inputs_message(task)

    @staticmethod
    def _check_retroactive(task, user):
        if user is not None and not is_responsavel_or_participant(task, user):
            return "Só o responsável ou um participante da tarefa pode informar o trabalho feito."
        if task.status == Task.Status.EM_EXECUCAO:
            return "Esta tarefa já está em execução. Use “Concluir tarefa”."
        if task.status not in TaskTransitionPolicy.NOT_STARTED_STATES:
            return "Só dá para informar o trabalho de uma tarefa que ainda não foi iniciada."
        return dependency_message(task) or process_inputs_message(task)

    @staticmethod
    def _check_block(task, user):
        if task.status == Task.Status.BLOQUEADA:
            return "Esta tarefa já está bloqueada."
        if task.status in TASK_TERMINAL:
            return "Não é possível bloquear uma tarefa concluída ou cancelada."
        return None

    @staticmethod
    def _check_unblock(task, user):
        return None if task.status == Task.Status.BLOQUEADA else "Esta tarefa não está bloqueada."

    @staticmethod
    def _check_cancel(task, user):
        return "Esta tarefa já está concluída ou cancelada." if task.status in TASK_TERMINAL else None

    @staticmethod
    def _check_reopen(task, user):
        return None if task.status == Task.Status.CONCLUIDA else "Somente tarefas concluídas podem ser reabertas."

    @staticmethod
    def _check_move_sector(task, user):
        if task.status in TASK_TERMINAL:
            return "Não é possível mover uma tarefa concluída ou cancelada."
        return None

    @staticmethod
    def _check_return(task, user):
        if task.status in TASK_TERMINAL:
            return "Não é possível devolver uma tarefa concluída ou cancelada."
        if pending_dependency(task) is not None and not has_active_queue_entry(task):
            return "Esta tarefa ainda aguarda a etapa anterior e não chegou a ser trabalhada; não há o que devolver."
        return None

    @staticmethod
    def _check_change_responsavel(task, user):
        if task.status in TASK_TERMINAL:
            return "Não é possível alterar o responsável de uma tarefa concluída ou cancelada."
        return None

    @staticmethod
    def _check_edit(task, user):
        if task.status in TASK_TERMINAL:
            return "Não é possível editar uma tarefa concluída ou cancelada."
        return None

    @staticmethod
    def _check_assume(task, user):
        """Só orienta a tela (o serviço tem as próprias regras de participante)."""
        if task.status in TASK_TERMINAL:
            return "Não é possível assumir uma tarefa concluída ou cancelada."
        if user is not None and is_responsavel_or_participant(task, user):
            return "Você já acompanha esta tarefa."
        return None


# ---------------------------------------------------------------------------
# Atividade
# ---------------------------------------------------------------------------


def open_pendency(activity, requires_approval):
    """Pendência aberta com (ou sem) aprovação do gestor, ou `None`."""
    pendency = activity.pendencies.filter(status=ActivityPendency.Status.ABERTA).order_by("-opened_at").first()
    if pendency is None or pendency.requires_approval != requires_approval:
        return None
    return pendency


class ActivityTransitionPolicy(_Policy):
    """Estados: `RASCUNHO`, `ABERTA`, `EM_ANDAMENTO`, `PENDENTE`, `CONCLUIDA`, `CANCELADA`
    (`BLOQUEADA` existe no modelo mas nenhum fluxo a grava)."""

    ACTIONS = (
        "edit", "change_owner", "change_sector", "claim", "complete", "cancel", "reopen",
        "mark_pending", "approve_pendency", "resolve_pendency",
    )

    @staticmethod
    def _check_edit(activity, user):
        if activity.status in ACTIVITY_TERMINAL:
            return "Não é possível editar uma atividade concluída ou cancelada."
        return None

    @staticmethod
    def _check_change_owner(activity, user):
        if activity.status in ACTIVITY_TERMINAL:
            return "Não é possível alterar o dono de uma atividade concluída ou cancelada."
        if activity.status == Activity.Status.RASCUNHO:
            return "Termine de criar a atividade antes de transferir o responsável."
        return None

    @staticmethod
    def _check_change_sector(activity, user):
        if activity.status in ACTIVITY_TERMINAL:
            return "Não é possível alterar o setor de uma atividade concluída ou cancelada."
        if activity.status == Activity.Status.RASCUNHO:
            return "Termine de criar a atividade antes de alterar o setor."
        # O setor define quem aprova e o dono já foi trocado para o gestor.
        if open_pendency(activity, requires_approval=True) is not None:
            return "Resolva a pendência antes de trocar o setor."
        return None

    @staticmethod
    def _check_claim(activity, user):
        if activity.status in ACTIVITY_TERMINAL:
            return "Não é possível assumir uma atividade concluída ou cancelada."
        return None

    @staticmethod
    def _check_complete(activity, user):
        if activity.status in ACTIVITY_TERMINAL:
            return "Esta atividade já está concluída ou cancelada."
        if activity.tasks.exclude(status__in=TASK_TERMINAL).exists():
            return "Existem tarefas ainda não concluídas ou canceladas nesta atividade."
        return None

    @staticmethod
    def _check_cancel(activity, user):
        if activity.status in ACTIVITY_TERMINAL:
            return "Esta atividade já está concluída ou cancelada."
        return None

    @staticmethod
    def _check_reopen(activity, user):
        if activity.status != Activity.Status.CONCLUIDA:
            return "Somente atividades concluídas podem ser reabertas."
        return None

    @staticmethod
    def _check_mark_pending(activity, user):
        if activity.status not in (Activity.Status.ABERTA, Activity.Status.EM_ANDAMENTO):
            return "Só é possível marcar como pendente uma atividade aberta ou em andamento."
        return None

    @staticmethod
    def _check_approve_pendency(activity, user):
        if activity.status != Activity.Status.PENDENTE:
            return "Esta atividade não está pendente de aprovação."
        if open_pendency(activity, requires_approval=True) is None:
            return "Não há uma pendência aguardando aprovação nesta atividade."
        return None

    @staticmethod
    def _check_resolve_pendency(activity, user):
        if activity.status != Activity.Status.PENDENTE:
            return "Esta atividade não está pendente."
        if open_pendency(activity, requires_approval=False) is None:
            return "Não há uma pendência simples aberta nesta atividade."
        return None
