from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# Atividade
# ---------------------------------------------------------------------------


class Activity(models.Model):
    """Representa um resultado/problema que precisa ser resolvido (Regras 02).

    Possui sempre um único dono (Regras 01 §6.1, 02 §6).
    """

    class Status(models.TextChoices):
        ABERTA = "ABERTA", "Aberta"
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        BLOQUEADA = "BLOQUEADA", "Bloqueada"
        CONCLUIDA = "CONCLUIDA", "Concluída"
        CANCELADA = "CANCELADA", "Cancelada"

    organization = models.ForeignKey(
        "core.Organization", verbose_name="organização", on_delete=models.PROTECT, related_name="activities"
    )
    company = models.ForeignKey(
        "core.Company",
        verbose_name="empresa",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="activities",
    )
    site = models.ForeignKey(
        "core.Site", verbose_name="obra", null=True, blank=True, on_delete=models.SET_NULL, related_name="activities"
    )
    cost_center = models.ForeignKey(
        "core.CostCenter",
        verbose_name="centro de custo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities",
    )

    title = models.CharField("resultado esperado", max_length=200)
    description = models.TextField("descrição", blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="dono",
        on_delete=models.PROTECT,
        related_name="activities_owned",
        help_text="Responsável único pelo acompanhamento até a resolução (Regras 01 §6.1).",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="criado por",
        on_delete=models.PROTECT,
        related_name="activities_created",
    )

    requested_deadline = models.DateTimeField("prazo solicitado", null=True, blank=True)

    process_version = models.ForeignKey(
        "processes.ProcessVersion",
        verbose_name="versão do processo aplicada",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="activities",
        help_text="Vínculo travado no momento da criação — publicar nova versão não altera atividades antigas (Regras 11 §19).",
    )

    status = models.CharField("status", max_length=14, choices=Status.choices, default=Status.ABERTA)

    created_at = models.DateTimeField("criada em", auto_now_add=True)
    first_action_at = models.DateTimeField(
        "primeira ação em",
        null=True,
        blank=True,
        help_text="Marco de avanço operacional real, não apenas visualização (Regras 02 §45).",
    )
    completed_at = models.DateTimeField("concluída em", null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="concluída por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    cancelled_at = models.DateTimeField("cancelada em", null=True, blank=True)
    cancelled_reason = models.TextField("motivo do cancelamento", blank=True)
    reopened_at = models.DateTimeField("reaberta em", null=True, blank=True)

    class Meta:
        verbose_name = "atividade"
        verbose_name_plural = "atividades"
        ordering = ["-created_at"]
        permissions = [
            ("can_view_all_activities", "Pode visualizar todas as atividades da organização"),
            ("can_change_owner", "Pode alterar o dono da atividade"),
            ("can_reopen_activity", "Pode reabrir atividade concluída"),
            ("can_cancel_activity", "Pode cancelar atividade"),
        ]

    def __str__(self):
        return self.title


class OwnerChangeLog(models.Model):
    """Histórico de troca de dono da atividade (Regras 02 §113-114). Nunca sobrescrito."""

    activity = models.ForeignKey(Activity, verbose_name="atividade", on_delete=models.CASCADE, related_name="owner_changes")
    previous_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="dono anterior", on_delete=models.PROTECT, related_name="+"
    )
    new_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="novo dono", on_delete=models.PROTECT, related_name="+"
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="alterado por", on_delete=models.PROTECT, related_name="+"
    )
    changed_at = models.DateTimeField("alterado em", auto_now_add=True)

    class Meta:
        verbose_name = "alteração de dono"
        verbose_name_plural = "alterações de dono"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.activity}: {self.previous_owner} → {self.new_owner}"


class ActivityMessage(models.Model):
    """Comunicação contextual ligada à atividade (Regras 06). Não altera dados oficiais."""

    activity = models.ForeignKey(Activity, verbose_name="atividade", on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="autor", on_delete=models.PROTECT, related_name="+"
    )
    body = models.TextField("mensagem")
    created_at = models.DateTimeField("enviada em", auto_now_add=True)

    class Meta:
        verbose_name = "mensagem da atividade"
        verbose_name_plural = "mensagens da atividade"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} em {self.activity}"


# ---------------------------------------------------------------------------
# Tarefa
# ---------------------------------------------------------------------------


class ReturnReason(models.Model):
    """Motivo de devolução, cadastro configurável por organização (Regras 02 §37)."""

    organization = models.ForeignKey(
        "core.Organization", verbose_name="organização", on_delete=models.CASCADE, related_name="return_reasons"
    )
    name = models.CharField("motivo", max_length=150)
    is_active = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "motivo de devolução"
        verbose_name_plural = "motivos de devolução"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_return_reason_per_org"),
        ]

    def __str__(self):
        return self.name


class Task(models.Model):
    """Parte do trabalho necessária para a atividade avançar (Regras 02 §10)."""

    class Status(models.TextChoices):
        NAO_INICIADA = "NAO_INICIADA", "Não iniciada"
        DISPONIVEL = "DISPONIVEL", "Disponível"
        EM_FILA = "EM_FILA", "Em fila"
        EM_EXECUCAO = "EM_EXECUCAO", "Em execução"
        BLOQUEADA = "BLOQUEADA", "Bloqueada"
        DEVOLVIDA = "DEVOLVIDA", "Devolvida"
        CONCLUIDA = "CONCLUIDA", "Concluída"
        CANCELADA = "CANCELADA", "Cancelada"

    activity = models.ForeignKey(Activity, verbose_name="atividade", on_delete=models.CASCADE, related_name="tasks")
    sector = models.ForeignKey(
        "core.Sector", verbose_name="setor responsável", on_delete=models.PROTECT, related_name="tasks"
    )
    order = models.PositiveIntegerField("ordem", default=1)
    title = models.CharField("título", max_length=200)
    description = models.TextField("descrição", blank=True)

    depends_on = models.ForeignKey(
        "self",
        verbose_name="depende de",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dependents",
        help_text="Dependência simples: esta tarefa não deveria iniciar antes da conclusão da anterior (Regras 02 §29).",
    )

    status = models.CharField("status", max_length=14, choices=Status.choices, default=Status.NAO_INICIADA)

    requested_deadline = models.DateTimeField("prazo solicitado", null=True, blank=True)
    committed_deadline = models.DateTimeField("prazo comprometido", null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="criada por", on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    first_action_at = models.DateTimeField("primeira ação em", null=True, blank=True)
    completed_at = models.DateTimeField("concluída em", null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="concluída por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    cancelled_at = models.DateTimeField("cancelada em", null=True, blank=True)
    overdue_notified_at = models.DateTimeField(
        "notificação de atraso enviada em",
        null=True,
        blank=True,
        help_text="Evita reenviar a notificação/e-mail de atraso a cada verificação.",
    )

    class Meta:
        verbose_name = "tarefa"
        verbose_name_plural = "tarefas"
        ordering = ["activity", "order"]
        permissions = [
            ("can_assume_task", "Pode assumir tarefa disponível"),
            ("can_assign_task", "Pode atribuir executor a uma tarefa"),
            ("can_reorder_queue", "Pode reordenar a fila do setor"),
            ("can_view_full_queue", "Pode visualizar a fila completa do setor"),
        ]

    def __str__(self):
        return f"{self.activity} - {self.title}"


class TaskExecutor(models.Model):
    """Vínculo executor↔tarefa (Regras 02 §17-19, §87-89). Remoção não apaga histórico."""

    task = models.ForeignKey(Task, verbose_name="tarefa", on_delete=models.CASCADE, related_name="executors")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="executor", on_delete=models.PROTECT, related_name="tasks_executed"
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="incluído por", on_delete=models.PROTECT, related_name="+"
    )
    added_at = models.DateTimeField("incluído em", auto_now_add=True)
    removed_at = models.DateTimeField("removido em", null=True, blank=True)

    class Meta:
        verbose_name = "executor da tarefa"
        verbose_name_plural = "executores da tarefa"
        ordering = ["added_at"]

    def __str__(self):
        return f"{self.user} em {self.task}"


class WorkSession(models.Model):
    """Sessão de trabalho de um executor em uma tarefa (Regras 04 §26-32)."""

    task = models.ForeignKey(Task, verbose_name="tarefa", on_delete=models.CASCADE, related_name="work_sessions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="executor", on_delete=models.PROTECT, related_name="work_sessions"
    )
    started_at = models.DateTimeField("início")
    ended_at = models.DateTimeField("fim", null=True, blank=True)
    is_manual = models.BooleanField(
        "lançamento manual", default=False, help_text="Diferencia tempo capturado pelo timer de apropriação posterior (Regras 04 §113)."
    )

    class Meta:
        verbose_name = "sessão de trabalho"
        verbose_name_plural = "sessões de trabalho"
        ordering = ["started_at"]

    def __str__(self):
        return f"{self.user} em {self.task} ({self.started_at:%d/%m %H:%M})"

    @property
    def duration(self):
        if self.ended_at is None:
            return None
        return self.ended_at - self.started_at


class TaskBlock(models.Model):
    """Bloqueio de tarefa (Regras 02 §67-69, 04 §46-48)."""

    task = models.ForeignKey(Task, verbose_name="tarefa", on_delete=models.CASCADE, related_name="blocks")
    reason = models.CharField("motivo", max_length=255)
    observation = models.TextField("observação", blank=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="bloqueada por", on_delete=models.PROTECT, related_name="+"
    )
    started_at = models.DateTimeField("bloqueada em", auto_now_add=True)
    ended_at = models.DateTimeField("desbloqueada em", null=True, blank=True)
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="desbloqueada por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "bloqueio de tarefa"
        verbose_name_plural = "bloqueios de tarefa"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.task}: {self.reason}"


class SectorTransfer(models.Model):
    """Histórico de movimentação de uma tarefa entre setores (Regras 02 §90, 04 §101-105)."""

    task = models.ForeignKey(Task, verbose_name="tarefa", on_delete=models.CASCADE, related_name="sector_transfers")
    from_sector = models.ForeignKey(
        "core.Sector", verbose_name="setor de origem", null=True, on_delete=models.PROTECT, related_name="+"
    )
    to_sector = models.ForeignKey(
        "core.Sector", verbose_name="setor de destino", on_delete=models.PROTECT, related_name="+"
    )
    moved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="movido por", on_delete=models.PROTECT, related_name="+"
    )
    moved_at = models.DateTimeField("movido em", auto_now_add=True)
    note = models.CharField("observação", max_length=255, blank=True)

    class Meta:
        verbose_name = "movimentação de setor"
        verbose_name_plural = "movimentações de setor"
        ordering = ["-moved_at"]

    def __str__(self):
        return f"{self.task}: {self.from_sector} → {self.to_sector}"


class TaskReturn(models.Model):
    """Devolução de tarefa para setor/etapa anterior. Motivo sempre obrigatório (Regras 02 §36-39)."""

    task = models.ForeignKey(Task, verbose_name="tarefa", on_delete=models.CASCADE, related_name="returns")
    from_sector = models.ForeignKey(
        "core.Sector", verbose_name="setor de origem", on_delete=models.PROTECT, related_name="+"
    )
    to_sector = models.ForeignKey(
        "core.Sector", verbose_name="setor de destino", on_delete=models.PROTECT, related_name="+"
    )
    reason = models.ForeignKey(
        ReturnReason, verbose_name="motivo", on_delete=models.PROTECT, related_name="returns"
    )
    observation = models.TextField("observação", blank=True)
    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="devolvida por", on_delete=models.PROTECT, related_name="+"
    )
    returned_at = models.DateTimeField("devolvida em", auto_now_add=True)

    class Meta:
        verbose_name = "devolução"
        verbose_name_plural = "devoluções"
        ordering = ["-returned_at"]

    def __str__(self):
        return f"{self.task}: {self.from_sector} → {self.to_sector} ({self.reason})"


class TaskMessage(models.Model):
    """Comunicação contextual ligada à tarefa (Regras 06). Não altera dados oficiais."""

    task = models.ForeignKey(Task, verbose_name="tarefa", on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="autor", on_delete=models.PROTECT, related_name="+"
    )
    body = models.TextField("mensagem")
    created_at = models.DateTimeField("enviada em", auto_now_add=True)

    class Meta:
        verbose_name = "mensagem da tarefa"
        verbose_name_plural = "mensagens da tarefa"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} em {self.task}"


# ---------------------------------------------------------------------------
# Fila
# ---------------------------------------------------------------------------


class QueueEntry(models.Model):
    """Uma passagem de uma tarefa pela fila de um setor (Regras 03).

    Uma mesma tarefa pode ter várias QueueEntry ao longo do tempo (uma por
    passagem/devolução) — Regras 04 §37.
    """

    task = models.ForeignKey(Task, verbose_name="tarefa", on_delete=models.CASCADE, related_name="queue_entries")
    sector = models.ForeignKey("core.Sector", verbose_name="setor", on_delete=models.PROTECT, related_name="queue_entries")
    position = models.PositiveIntegerField("posição atual")
    queue_size_at_entry = models.PositiveIntegerField("total da fila na entrada")
    entered_at = models.DateTimeField("entrou na fila em", auto_now_add=True)
    left_at = models.DateTimeField("saiu da fila em", null=True, blank=True)

    class Meta:
        verbose_name = "entrada na fila"
        verbose_name_plural = "entradas na fila"
        ordering = ["sector", "position"]

    def __str__(self):
        return f"{self.task} — {self.sector} (pos. {self.position})"

    @property
    def is_active(self):
        return self.left_at is None


class QueuePositionChange(models.Model):
    """Histórico de mudança de posição na fila (Regras 03 §7-9, §19-21)."""

    class Reason(models.TextChoices):
        AUTOMATICA_CONCLUSAO = "AUTOMATICA_CONCLUSAO", "Automática (conclusão de tarefa anterior)"
        AUTOMATICA_ENTRADA = "AUTOMATICA_ENTRADA", "Automática (nova entrada)"
        MANUAL = "MANUAL", "Reordenação manual"
        ENTRADA_PRIORITARIA = "ENTRADA_PRIORITARIA", "Entrada prioritária"

    queue_entry = models.ForeignKey(
        QueueEntry, verbose_name="entrada na fila", on_delete=models.CASCADE, related_name="position_changes"
    )
    old_position = models.PositiveIntegerField("posição anterior")
    new_position = models.PositiveIntegerField("nova posição")
    old_total = models.PositiveIntegerField("total anterior")
    new_total = models.PositiveIntegerField("novo total")
    reason = models.CharField("motivo", max_length=24, choices=Reason.choices)
    note = models.CharField("observação", max_length=255, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="alterado por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Nulo quando a mudança é automática.",
    )
    changed_at = models.DateTimeField("alterado em", auto_now_add=True)

    class Meta:
        verbose_name = "mudança de posição na fila"
        verbose_name_plural = "mudanças de posição na fila"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.queue_entry}: {self.old_position} → {self.new_position}"


# ---------------------------------------------------------------------------
# Prazo
# ---------------------------------------------------------------------------


class DeadlineProposal(models.Model):
    """Proposta de novo prazo comprometido pelo setor executor (Regras 03 §31-39)."""

    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Aguardando decisão"
        ACEITO = "ACEITO", "Aceito"
        RECUSADO = "RECUSADO", "Recusado"

    task = models.ForeignKey(Task, verbose_name="tarefa", on_delete=models.CASCADE, related_name="deadline_proposals")
    proposed_deadline = models.DateTimeField("prazo proposto")
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="proposto por", on_delete=models.PROTECT, related_name="+"
    )
    proposed_at = models.DateTimeField("proposto em", auto_now_add=True)

    status = models.CharField("status", max_length=10, choices=Status.choices, default=Status.PENDENTE)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="decidido por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    decided_at = models.DateTimeField("decidido em", null=True, blank=True)
    decision_note = models.TextField("motivo da recusa", blank=True)

    class Meta:
        verbose_name = "proposta de prazo"
        verbose_name_plural = "propostas de prazo"
        ordering = ["-proposed_at"]

    def __str__(self):
        return f"{self.task}: {self.proposed_deadline:%d/%m/%Y %H:%M} ({self.get_status_display()})"


class DeadlineConflict(models.Model):
    """Conflito registrado quando uma proposta de prazo é recusada (Regras 03 §34, roadmap §31).

    No D0 apenas registra e notifica os responsáveis; o motor completo de
    escalonamento por níveis é D1 (Regras 10 §57).
    """

    class Status(models.TextChoices):
        ABERTO = "ABERTO", "Aberto"
        RESOLVIDO = "RESOLVIDO", "Resolvido"

    task = models.ForeignKey(Task, verbose_name="tarefa", on_delete=models.CASCADE, related_name="deadline_conflicts")
    proposal = models.OneToOneField(
        DeadlineProposal, verbose_name="proposta recusada", on_delete=models.CASCADE, related_name="conflict"
    )
    status = models.CharField("status", max_length=10, choices=Status.choices, default=Status.ABERTO)
    opened_at = models.DateTimeField("aberto em", auto_now_add=True)
    resolution_note = models.TextField("resolução", blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="resolvido por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    resolved_at = models.DateTimeField("resolvido em", null=True, blank=True)

    class Meta:
        verbose_name = "conflito de prazo"
        verbose_name_plural = "conflitos de prazo"
        ordering = ["-opened_at"]
        permissions = [
            ("can_resolve_deadline_conflict", "Pode resolver conflito de prazo"),
        ]

    def __str__(self):
        return f"Conflito em {self.task} ({self.get_status_display()})"
