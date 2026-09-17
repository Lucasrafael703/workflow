from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import ListView, View

from .models import Notification
from .services import NotificationService

# ---------------------------------------------------------------------------
# Categoria de cada notificação.
#
# A tela não trata cada um dos 18 EventType como um card visualmente
# diferente — isso é o que gera inconsistência. Todo evento cai em uma de
# cinco categorias, e a categoria decide ícone, cor, quais campos de contexto
# aparecem e o rótulo pequeno do topo do card.
# ---------------------------------------------------------------------------

DELEGACAO = "delegacao"
PRAZO = "prazo"
MENCAO = "mencao"
ALERTA = "alerta"
CONCLUSAO = "conclusao"
INFORMATIVO = "informativo"

CATEGORY_PRESENTATION = {
    # categoria: (ícone, tom, rótulo do topo do card)
    DELEGACAO: ("task", "info", "Nova delegação"),
    PRAZO: ("clock", "warning", "Prazo proposto"),
    MENCAO: ("at", "mention", "Menção"),
    ALERTA: ("alert", "danger", "Atenção"),
    CONCLUSAO: ("check", "success", "Concluída"),
    INFORMATIVO: ("bell", "neutral", "Informativo"),
}

EVENT_CATEGORY = {
    Notification.EventType.TASK_ASSIGNED: DELEGACAO,
    Notification.EventType.TASK_ASSIGNMENT_PENDING: DELEGACAO,
    Notification.EventType.TASK_ASSIGNMENT_REJECTED: ALERTA,
    Notification.EventType.TASK_RETURNED: ALERTA,
    Notification.EventType.TASK_BLOCKED: ALERTA,
    Notification.EventType.TASK_UNBLOCKED: INFORMATIVO,
    Notification.EventType.TASK_COMPLETED: CONCLUSAO,
    Notification.EventType.QUEUE_POSITION_CHANGED: INFORMATIVO,
    Notification.EventType.DEADLINE_PROPOSED: PRAZO,
    Notification.EventType.DEADLINE_ACCEPTED: INFORMATIVO,
    Notification.EventType.DEADLINE_REJECTED: ALERTA,
    Notification.EventType.DEADLINE_CONFLICT: ALERTA,
    Notification.EventType.TASK_OVERDUE: ALERTA,
    Notification.EventType.ACTIVITY_CREATED: DELEGACAO,
    Notification.EventType.ACTIVITY_COMPLETED: CONCLUSAO,
    Notification.EventType.ACTIVITY_CANCELLED: INFORMATIVO,
    Notification.EventType.ACTIVITY_REOPENED: DELEGACAO,
    Notification.EventType.OWNER_CHANGED: DELEGACAO,
    Notification.EventType.MESSAGE_POSTED: INFORMATIVO,
    Notification.EventType.MENTIONED: MENCAO,
}

# Categorias que, por natureza, esperam uma decisão de quem recebe, não
# apenas ciência (doc 09 §144-145). `_still_needs_action` confere se a
# decisão real já foi tomada — uma proposta já aceita não deve continuar
# pedindo ação só porque o evento que a gerou é do tipo certo.
ACTION_REQUIRED_EVENTS = {
    Notification.EventType.DEADLINE_PROPOSED,
    Notification.EventType.DEADLINE_CONFLICT,
    Notification.EventType.TASK_RETURNED,
    Notification.EventType.TASK_OVERDUE,
    Notification.EventType.TASK_ASSIGNED,
    Notification.EventType.TASK_ASSIGNMENT_PENDING,
    Notification.EventType.TASK_BLOCKED,
}

# A mensagem gravada já repete o que os campos estruturados (tarefa, setor,
# prazo) mostram no card — mostrá-la de novo é ruído. Só vale a pena exibir
# quando ela carrega algo que os campos não cobrem: um motivo, uma nota de
# recusa, o "de quem para quem", ou o próprio texto de uma conversa/menção.
EVENTS_WITH_EXTRA_MESSAGE = {
    Notification.EventType.TASK_RETURNED,
    Notification.EventType.TASK_BLOCKED,
    Notification.EventType.ACTIVITY_CANCELLED,
    Notification.EventType.ACTIVITY_REOPENED,
    Notification.EventType.DEADLINE_REJECTED,
    Notification.EventType.TASK_ASSIGNMENT_REJECTED,
    Notification.EventType.OWNER_CHANGED,
    Notification.EventType.MESSAGE_POSTED,
    Notification.EventType.MENTIONED,
}


def _still_needs_action(notification):
    """Se a notificação ainda espera uma decisão, ou se já foi resolvida.

    Uma proposta de prazo aceita ontem não deve continuar pedindo "Aceitar
    ou recusar" hoje: o evento que a gerou é do tipo certo, mas a decisão
    já aconteceu. O mesmo vale para conflito já resolvido.
    """
    event = notification.event_type
    task = notification.task

    if event == Notification.EventType.DEADLINE_PROPOSED:
        if task is None:
            return False
        return task.deadline_proposals.filter(status="PENDENTE").exists()

    if event == Notification.EventType.DEADLINE_CONFLICT:
        if task is None:
            return False
        return task.deadline_conflicts.filter(status="ABERTO").exists()

    if event == Notification.EventType.TASK_RETURNED:
        if task is None:
            return False
        return task.status == "DEVOLVIDA"

    if event in (Notification.EventType.TASK_OVERDUE, Notification.EventType.TASK_ASSIGNED):
        if task is None:
            return False
        return task.status not in ("CONCLUIDA", "CANCELADA")

    if event == Notification.EventType.TASK_ASSIGNMENT_PENDING:
        if task is None:
            return False
        return task.assignments.filter(user=notification.recipient, status="PENDENTE").exists()

    if event == Notification.EventType.TASK_BLOCKED:
        # Só pede ação enquanto o bloqueio que a gerou seguir aberto —
        # resolvido o bloqueio, a notificação vira só um registro do que houve.
        if task is None:
            return False
        return task.blocks.filter(ended_at__isnull=True).exists()

    return event in ACTION_REQUIRED_EVENTS


def _pending_proposal_id(task):
    if task is None:
        return None
    proposal = task.deadline_proposals.filter(status="PENDENTE").order_by("-proposed_at").first()
    return proposal.pk if proposal else None


def _open_conflict_id(task):
    if task is None:
        return None
    conflict = task.deadline_conflicts.filter(status="ABERTO").order_by("-opened_at").first()
    return conflict.pk if conflict else None


def _open_block(task):
    if task is None:
        return None
    return task.blocks.filter(ended_at__isnull=True).order_by("-started_at").first()


def _decorate(notification):
    """Anexa à instância tudo que o template precisa — inclusive quais campos
    de contexto mostrar, que dependem da categoria (doc pedido do usuário):
    delegação mostra quem delegou / setor / prazo; prazo mostra proposto por
    / prazo atual / novo prazo; menção mostra quem mencionou / setor /
    horário; alerta mostra setor / tempo parado / prazo; conclusão mostra
    responsável / horário. Nenhuma categoria mostra os cinco campos juntos.
    """
    category = EVENT_CATEGORY.get(notification.event_type, INFORMATIVO)
    icon, tone, label = CATEGORY_PRESENTATION[category]
    notification.category = category
    notification.icon = icon
    notification.tone = tone
    notification.category_label = label
    notification.needs_action = _still_needs_action(notification)

    task = notification.task
    activity = notification.activity or (task.activity if task else None)

    notification.headline = (
        (task.title if task else None) or (activity.title if activity else None) or notification.title
    )

    # O ator é quem praticou a ação (delegou, propôs, mencionou, concluiu).
    # Notificações criadas antes do campo `actor` existir não têm essa
    # coluna preenchida — nesses casos, cai para quem criou a tarefa/
    # atividade, que é a mesma informação para os eventos de delegação.
    actor = notification.actor
    if actor is None:
        if task is not None:
            actor = task.created_by
        elif activity is not None:
            actor = activity.created_by
    is_self = actor is not None and actor.id == notification.recipient_id
    notification.actor_name = None if (actor is None or is_self) else (
        actor.get_full_name() or actor.get_username()
    )

    notification.pending_proposal_id = None
    notification.open_conflict_id = None
    if notification.event_type == Notification.EventType.DEADLINE_PROPOSED and notification.needs_action:
        notification.pending_proposal_id = _pending_proposal_id(task)
    if notification.event_type == Notification.EventType.DEADLINE_CONFLICT and notification.needs_action:
        notification.open_conflict_id = _open_conflict_id(task)

    # Campos de contexto, específicos por categoria — nunca os cinco juntos.
    notification.fields = _context_fields(notification, category, task, activity, is_self)

    # Frase da linha 3: "o que aconteceu", sempre curta.
    notification.summary = _summary_sentence(notification, category, task, activity, is_self)

    notification.show_message = notification.event_type in EVENTS_WITH_EXTRA_MESSAGE
    return notification


def _context_fields(n, category, task, activity, is_self):
    """Devolve uma lista curta de (ícone, texto) — no máximo 3 campos,
    escolhidos pela categoria, não pelo que existir."""
    fields = []

    if category == DELEGACAO:
        if n.actor_name:
            fields.append(("users", f"{n.actor_name} delegou"))
        # Delegação de tarefa tem setor; delegação de atividade nova (dono
        # trocado, reaberta) não tem tarefa — nesse caso mostra quem é o
        # dono, que é o outro dado central de "para quem isto foi delegado".
        if task is not None:
            fields.append(("folder", task.sector.name))
        elif activity is not None and activity.owner_id != n.recipient_id:
            owner = activity.owner
            fields.append(("users", f"Dono: {owner.get_full_name() or owner.get_username()}"))
        if task is not None:
            deadline = task.committed_deadline or task.requested_deadline
            is_committed = bool(task.committed_deadline)
        else:
            deadline = activity.requested_deadline if activity else None
            is_committed = False
        if deadline:
            label = "Prazo" if is_committed else "Solicitado para"
            fields.append(("clock", f"{label} {deadline:%d/%m %H:%M}"))

    elif category == PRAZO:
        if n.actor_name:
            fields.append(("users", f"Proposto por {n.actor_name}"))
        if task is not None and task.requested_deadline:
            fields.append(("clock", f"Prazo atual {task.requested_deadline:%d/%m}"))
        proposal = None
        if n.pending_proposal_id:
            proposal = task.deadline_proposals.filter(pk=n.pending_proposal_id).first()
        if proposal:
            fields.append(("clock", f"Novo prazo {proposal.proposed_deadline:%d/%m %H:%M}"))
        elif task is not None and task.committed_deadline:
            fields.append(("clock", f"Prazo {task.committed_deadline:%d/%m %H:%M}"))

    elif category == MENCAO:
        if n.actor_name:
            fields.append(("users", f"Mencionado por {n.actor_name}"))
        if task is not None:
            fields.append(("folder", task.sector.name))
        fields.append(("clock", n.created_at.strftime("%H:%M")))

    elif category == ALERTA:
        if task is not None:
            fields.append(("folder", task.sector.name))
        open_block = _open_block(task) if task is not None else None
        if open_block is not None:
            dias = max(0, (timezone.now() - open_block.started_at).days)
            texto = "Bloqueada hoje" if dias == 0 else f"Bloqueada há {dias} dia{'s' if dias != 1 else ''}"
            fields.append(("block", texto))
        deadline = task.committed_deadline if task else None
        if deadline:
            fields.append(("clock", f"Prazo {deadline:%d/%m %H:%M}"))

    elif category == CONCLUSAO:
        responsavel = n.actor_name or (activity.owner.get_full_name() or activity.owner.get_username() if activity else None)
        if responsavel:
            fields.append(("users", f"Responsável: {responsavel}"))
        fields.append(("clock", n.created_at.strftime("%H:%M")))

    else:  # informativo
        if task is not None:
            fields.append(("folder", task.sector.name))
        elif activity is not None:
            fields.append(("folder", activity.title[:40]))
        fields.append(("clock", n.created_at.strftime("%H:%M")))

    return fields[:3]


def _summary_sentence(n, category, task, activity, is_self):
    """Uma frase curta para a linha 3 — o que aconteceu, em português comum."""
    actor = n.actor_name

    if category == DELEGACAO:
        if is_self:
            return "Você criou esta atividade."
        if actor:
            return f"{actor} delegou esta atividade para você e aguarda sua ação."
        return "Uma nova atividade foi atribuída a você."

    if category == PRAZO:
        if actor:
            return f"{actor} propôs um novo prazo e aguarda sua decisão."
        return "Um novo prazo foi proposto e aguarda decisão."

    if category == MENCAO:
        # A própria mensagem já é o trecho citado — a frase fica curta.
        if actor:
            return f"{actor} mencionou você em um comentário."
        return "Você foi mencionado em um comentário."

    if category == ALERTA:
        if n.event_type == Notification.EventType.TASK_BLOCKED:
            return "Esta tarefa está bloqueada e aguarda solução."
        if n.event_type == Notification.EventType.TASK_OVERDUE:
            return "O prazo comprometido desta tarefa já passou."
        if n.event_type == Notification.EventType.DEADLINE_CONFLICT:
            return "O prazo proposto foi recusado e precisa de uma decisão."
        if n.event_type == Notification.EventType.TASK_RETURNED:
            return "Esta tarefa foi devolvida e precisa ser retomada."
        return "Esta atividade exige atenção."

    if category == CONCLUSAO:
        if actor:
            return f"{actor} concluiu {'a tarefa' if task else 'a atividade'}."
        return "Concluída."

    return n.message


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "notifications/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_base_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related(
            "activity",
            "activity__owner",
            "actor",
            "task",
            "task__sector",
            "task__created_by",
            "task__activity",
            "task__activity__owner",
        )

    def _apply_search_and_order(self, queryset):
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(message__icontains=search)
                | Q(activity__title__icontains=search)
                | Q(task__title__icontains=search)
            )
        ordem = self.request.GET.get("ordem", "recentes")
        return queryset.order_by("created_at" if ordem == "antigas" else "-created_at")

    def _active_filter(self):
        """"Ação necessária" é a aba padrão: é o que precisa da atenção da
        pessoa primeiro, não o feed completo. "Todas" continua existindo,
        mas como uma escolha explícita (?filter=todas), não o ponto de
        partida — evita a tela abrir parecendo um feed de tudo."""
        return self.request.GET.get("filter") or "acao"

    def get_queryset(self):
        """A aba "Ação necessária" não pode ser filtrada só pelo tipo do
        evento no banco: um DEADLINE_PROPOSED já aceito continua sendo do
        tipo DEADLINE_PROPOSED, mas não precisa mais de ação (ver
        `_still_needs_action`). Por isso essa aba é decidida em Python, sobre
        o conjunto pré-filtrado por tipo — o volume por pessoa é pequeno o
        bastante (uma caixa pessoal, não um log) para isso ser barato.
        """
        queryset = self._apply_search_and_order(self.get_base_queryset())

        view = self._active_filter()
        if view == "nao-lidas":
            return queryset.filter(is_read=False)
        if view == "mencoes":
            return queryset.filter(event_type=Notification.EventType.MENTIONED)
        if view == "alertas":
            alert_events = [e for e, c in EVENT_CATEGORY.items() if c == ALERTA]
            return queryset.filter(event_type__in=alert_events)
        if view == "acao":
            candidatos = queryset.filter(event_type__in=ACTION_REQUIRED_EVENTS)
            ids = [n.pk for n in candidatos if _still_needs_action(n)]
            preserved = {pk: i for i, pk in enumerate(ids)}
            return sorted(queryset.filter(pk__in=ids), key=lambda n: preserved[n.pk])
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notifications = [_decorate(n) for n in context["notifications"]]
        context["notifications"] = notifications

        context["filter"] = self._active_filter()
        context["search"] = self.request.GET.get("q", "")
        context["ordem"] = self.request.GET.get("ordem", "recentes")

        # Contadores das abas, sobre a base completa — não apenas a página
        # atual, para o número bater com o que a pessoa realmente tem.
        base = self.get_base_queryset()
        alert_events = [e for e, c in EVENT_CATEGORY.items() if c == ALERTA]
        context["total_count"] = base.count()
        context["unread_count"] = base.filter(is_read=False).count()
        context["mention_count"] = base.filter(event_type=Notification.EventType.MENTIONED, is_read=False).count()
        context["alert_count"] = base.filter(event_type__in=alert_events, is_read=False).count()
        context["action_count"] = sum(
            1 for n in base.filter(event_type__in=ACTION_REQUIRED_EVENTS) if _still_needs_action(n)
        )
        return context


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        NotificationService.mark_read(notification)

        # Leva direto ao ponto que originou o aviso (doc 09 §147).
        if notification.url:
            return redirect(notification.url)
        if notification.task_id:
            return redirect("task-detail", pk=notification.task_id)
        if notification.activity_id:
            return redirect("activity-detail", pk=notification.activity_id)
        return redirect("notification-list")


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return redirect("notification-list")
