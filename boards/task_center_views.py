"""Tela Tarefas (`/tarefas/`, `/tarefas/kanban/`, `/tarefas/calendario/`): view fina sobre `TaskCenterQuery`.

Só leitura. Criar tarefa pelo formulário inline da tela usa o endpoint existente `board-item-create` (a regra, a
autorização e a auditoria continuam no `ItemService.create`).
"""

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import TemplateView

from core.mixins import OrganizationRequiredMixin

from .demand_services import DemandBoardAccess
from .models import Board
from .task_center import PAGE_SIZE, TaskCenterQuery


class TaskCenterView(OrganizationRequiredMixin, TemplateView):
    template_name = "boards/task_center.html"
    view_mode = "list"  # list | kanban | calendar (as_view(view_mode=...) em activities/urls.py)

    def get(self, request, *args, **kwargs):
        demand = (request.GET.get("demanda") or "").strip()
        if demand:
            # Endereço antigo ("Abrir quadro" da ficha da Demanda): vai direto ao Quadro da Demanda.
            board = (
                Board.objects.filter(
                    organization=self.organization, kind=Board.Kind.DEMAND, is_active=True,
                    activity_id=int(demand) if demand.isdigit() else 0,
                ).select_related("activity").first()
            )
            if board is None or not DemandBoardAccess.can_view(request.user, board):
                raise Http404("Demanda não encontrada.")
            return redirect("board-detail", pk=board.pk)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = TaskCenterQuery(self.request.user, self.organization, self.request.GET)
        filters = query.filters()
        # Os filtros acompanham a pessoa ao trocar de aba; a semana só vale no calendário.
        keep = {key: value for key, value in filters.items() if value}
        context.update(
            nav_active="tasks",
            view_mode=self.view_mode,
            filters=filters,
            filter_querystring=urlencode(keep),
            can_filter_people=query.can_filter_people,
            people_options=query.people_options(),
            summary=query.summary(),
            add_payload=query.add_payload(),
        )
        if self.view_mode == "kanban":
            context["kanban_columns"] = query.kanban_columns()
        elif self.view_mode == "calendar":
            context.update(query.week())
        else:
            page = Paginator(query.list_rows(), PAGE_SIZE).get_page(self.request.GET.get("page"))
            context.update(page_obj=page, rows=page.object_list)
        return context
