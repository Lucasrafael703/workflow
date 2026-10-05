"""Páginas e endpoints das visualizações de domínio."""

import json
from collections import OrderedDict
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from acessos import catalog
from acessos.services import AuthorizationService
from activities.filtering import normalize_workspace_filters
from activities.models import Activity, Task
from core.colors import EnumColorResolver
from core.mixins import OrganizationRequiredMixin
from core.feature_flags import workspace_v2_enabled
from core.models import ActivityStage, Sector, TaskStage, WorkflowStatus

from .domain_defaults import ensure_domain_board
from .domain_services import DomainBoardConflict, DomainBoardError, DomainBoardMutationService, build_cells
from .models import DomainBoard, DomainBoardCardField, DomainBoardField, DomainBoardView, DomainBoardViewColumn


def _request_data(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise DomainBoardError("Dados da alteração inválidos.") from exc
    return request.POST


def _is_async(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")


class DomainWorkBoardView(OrganizationRequiredMixin, TemplateView):
    template_name = "boards/work_board.html"
    domain = None
    forced_view_type = None

    def get_board(self):
        return ensure_domain_board(self.organization, self.domain)

    def get_view(self, board):
        requested = self.request.GET.get("view") or self.request.GET.get("visao")
        views = board.views.filter(is_active=True).prefetch_related(
            "columns__field", "card_fields__field"
        )
        if requested and str(requested).isdigit():
            selected = views.filter(pk=requested).first()
            if selected:
                return selected
        if self.forced_view_type:
            selected = views.filter(type=self.forced_view_type).first()
            if selected:
                return selected
        return views.filter(is_default=True).first() or views.first()

    def get_items(self):
        # Reaproveita o único filtro de cada domínio. Import atrasado evita
        # circularidade durante o carregamento de URLs.
        from activities.views import (
            decorate_activity_cards,
            decorate_task_statuses,
            filtered_activities_queryset,
            filtered_tasks_queryset,
        )
        if self.domain == DomainBoard.Domain.DEMAND:
            items = list(self.arrange_activities(filtered_activities_queryset(self.request, self.organization)))
            decorate_activity_cards(items, self.organization)
            action = catalog.ATIVIDADE_VISUALIZAR
        else:
            items = list(
                filtered_tasks_queryset(self.request, self.organization).annotate(
                    checklist_total=Count("checklist_items", distinct=True),
                    checklist_done=Count("checklist_items", filter=Q(checklist_items__is_done=True), distinct=True),
                )
            )
            decorate_task_statuses(items, self.organization)
            action = catalog.TAREFA_VISUALIZAR
        access = AuthorizationService.can_many(self.request.user, [(action, item) for item in items])
        return [item for item in items if access[(action, item.pk)]]

    def arrange_activities(self, queryset):
        """Gancho: o Workspace reordena (nulos no fim, sentido aplicado); a tela de sempre não muda."""
        return queryset

    def requested_group_by(self):
        """Gancho: agrupamento pedido na URL (só o Workspace usa). `None` = o padrão salvo da visualização."""
        return None

    @staticmethod
    def _group_items(items, group_by, organization, *, domain=None, show_empty=False, sector_id=None):
        """Agrupa os registros e, no Kanban, mantém as raias do fluxo visíveis.

        O Kanban dos Quadros sempre mostra as etiquetas/raias vazias quando a
        visualização pede isso. A tela de Demandas precisa seguir a mesma
        regra: esconder uma etapa vazia faz o fluxo parecer incompleto e tira
        o destino do arrastar-e-soltar.
        """
        groups = OrderedDict()
        demand_priorities = EnumColorResolver(organization, "activity_urgency")
        task_priorities = EnumColorResolver(organization, "task_priority")

        def add_group(key, label, color, choice=None):
            # `sector_id`/`is_active` (só etapa e status) dizem ao Kanban do Workspace onde a raia aceita soltar cartões;
            # chaves a mais não afetam a tela de sempre.
            group = {"key": key, "label": label, "color": color, "items": []}
            if choice is not None and group_by in {"stage", "condition"}:
                group.update(sector_id=getattr(choice, "sector_id", None), is_active=getattr(choice, "is_active", True))
            return groups.setdefault(key, group)

        for item in items:
            value = getattr(item, group_by, None) if group_by else None
            if group_by == "urgency" and isinstance(item, Activity):
                key = value or "empty"
                label = demand_priorities.label_for(value, item.get_urgency_display()) if value else "Sem prioridade"
                color = demand_priorities.color_for(value) if value else "#E2E8F0"
            elif group_by == "priority" and isinstance(item, Task):
                key = value or "empty"
                label = task_priorities.label_for(value, item.get_priority_display()) if value else "Sem prioridade"
                color = task_priorities.color_for(value) if value else "#E2E8F0"
            elif group_by in {"owner", "responsavel"} and value:
                key = value.pk
                label = value.get_full_name() or value.get_username()
                color = "#E2E8F0"
            else:
                key = getattr(value, "pk", None) or "empty"
                blank_labels = {
                    "stage": "Sem estágio",
                    "condition": "Sem status",
                    "sector": "Sem setor",
                    "owner": "Sem responsável",
                    "responsavel": "Sem responsável",
                }
                label = getattr(value, "name", None) or blank_labels.get(group_by, "Sem valor")
                color = getattr(value, "color", "#E2E8F0")
            add_group(key, label, color, value)["items"].append(item)

        # As raias têm uma ordem própria, independente de qual cartão aparece
        # primeiro no resultado da busca. Isso é especialmente importante ao
        # ordenar os cartões por prazo.
        ordered_keys = []
        if group_by in {"stage", "condition"}:
            if show_empty or "empty" in groups:
                add_group("empty", "Sem estágio" if group_by == "stage" else "Sem status", "#94A3B8")
                ordered_keys.append("empty")
            if group_by == "stage":
                model = ActivityStage if domain == DomainBoard.Domain.DEMAND else TaskStage
                choices = model.objects.filter(organization=organization, is_active=True)
            else:
                condition_domain = (
                    WorkflowStatus.Domain.ACTIVITY
                    if domain == DomainBoard.Domain.DEMAND
                    else WorkflowStatus.Domain.TASK
                )
                choices = WorkflowStatus.objects.filter(
                    organization=organization, domain=condition_domain, is_active=True
                )
            if sector_id:
                choices = choices.filter(sector_id=sector_id)
            for choice in choices.order_by("order", "name", "pk"):
                if show_empty or choice.pk in groups:
                    add_group(choice.pk, choice.name, choice.color, choice)
                    ordered_keys.append(choice.pk)
        elif group_by == "sector":
            if show_empty or "empty" in groups:
                add_group("empty", "Sem setor", "#94A3B8")
                ordered_keys.append("empty")
            for sector in Sector.objects.filter(organization=organization, is_active=True).order_by("name", "pk"):
                if show_empty or sector.pk in groups:
                    add_group(sector.pk, sector.name, getattr(sector, "color", "#E2E8F0"))
                    ordered_keys.append(sector.pk)
        elif group_by in {"owner", "responsavel"}:
            if show_empty or "empty" in groups:
                add_group("empty", "Sem responsável", "#E2E8F0")
                ordered_keys.append("empty")
            if show_empty:
                User = get_user_model()
                for person in User.objects.filter(
                    profile__organization=organization, is_active=True
                ).order_by("first_name", "last_name", "username", "pk"):
                    add_group(person.pk, person.get_full_name() or person.get_username(), "#E2E8F0")
                    ordered_keys.append(person.pk)
        elif group_by in {"urgency", "priority"}:
            if show_empty or "empty" in groups:
                add_group("empty", "Sem prioridade", "#E2E8F0")
                ordered_keys.append("empty")
            choices = Activity.Urgency.choices if group_by == "urgency" else Task.Priority.choices
            resolver = demand_priorities if group_by == "urgency" else task_priorities
            for code, default_label in choices:
                if show_empty or code in groups:
                    add_group(code, resolver.label_for(code, default_label), resolver.color_for(code))
                    ordered_keys.append(code)

        # Valores antigos/inativos ainda não podem desaparecer só porque não
        # pertencem mais ao catálogo ativo. Deixamo-los ao fim para correção.
        ordered_keys.extend(key for key in groups if key not in ordered_keys)
        return [groups[key] for key in ordered_keys]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        board = self.get_board()
        view = self.get_view(board)
        table_layout = [column for column in view.columns.all() if column.is_visible]
        for column in table_layout:
            # A largura pertence à visualização, não ao campo compartilhado.
            # O atributo efêmero evita uma consulta/loop adicional no template.
            column.field.work_width = column.width
        fields = [column.field for column in table_layout]
        if view.type == DomainBoardView.Type.KANBAN:
            fields = [card_field.field for card_field in view.card_fields.all() if card_field.is_visible]
        if not fields:
            fields = list(board.fields.filter(is_active=True))
        all_fields = list(board.fields.filter(is_active=True))
        visible_card_fields = [card_field.field for card_field in view.card_fields.all() if card_field.is_visible]
        card_settings_fields = visible_card_fields + [
            field for field in all_fields if field.pk not in {visible.pk for visible in visible_card_fields}
        ]
        items = build_cells(self.get_items(), fields, self.organization)
        group_by = self.requested_group_by() or (view.settings or {}).get("group_by", "stage")
        group_field = board.fields.filter(key=group_by, is_active=True).first()
        move_actions = {
            DomainBoard.Domain.DEMAND: {
                "stage": catalog.ATIVIDADE_MOVER_ESTAGIO,
                "condition": catalog.ATIVIDADE_DEFINIR_CONDICAO,
                "sector": catalog.ATIVIDADE_EDITAR,
                "owner": catalog.ATIVIDADE_ALTERAR_DONO,
                "urgency": catalog.ATIVIDADE_EDITAR,
            },
            DomainBoard.Domain.TASK: {
                "stage": catalog.TAREFA_MOVER_ESTAGIO,
                "sector": catalog.TAREFA_MOVER_SETOR,
                "responsavel": catalog.TAREFA_ALTERAR_RESPONSAVEL,
                "priority": catalog.TAREFA_EDITAR,
            },
        }
        move_action = move_actions.get(self.domain, {}).get(group_by)
        if view.type == DomainBoardView.Type.KANBAN and move_action:
            can_move = AuthorizationService.can_many(
                self.request.user, [(move_action, item) for item in items]
            )
            for item in items:
                item.can_move_kanban = can_move[(move_action, item.pk)]
        else:
            for item in items:
                item.can_move_kanban = False
        context.update(
            nav_active="activities" if self.domain == DomainBoard.Domain.DEMAND else "tasks",
            board=board,
            work_view=view,
            work_views=board.views.filter(is_active=True),
            fields=fields,
            all_fields=all_fields,
            card_settings_fields=card_settings_fields,
            items=items,
            groups=self._group_items(
                items,
                group_by,
                self.organization,
                domain=self.domain,
                show_empty=bool((view.settings or {}).get("show_empty", False)),
                sector_id=normalize_workspace_filters(self.request)["setor"],  # só dígitos; valor inválido vira "sem setor"
            ),
            group_by=group_by,
            group_field=group_field,
            show_field_names=bool((view.settings or {}).get("show_field_names", True)),
            can_create=AuthorizationService.can(
                self.request.user,
                catalog.ATIVIDADE_CRIAR if self.domain == DomainBoard.Domain.DEMAND else catalog.TAREFA_CRIAR,
                None,
            ),
            can_configure=AuthorizationService.can(self.request.user, catalog.QUADRO_GERIR_COLUNAS, board),
            title="Demandas" if self.domain == DomainBoard.Domain.DEMAND else "Tarefas",
            singular="demanda" if self.domain == DomainBoard.Domain.DEMAND else "tarefa",
            list_url_name="activity-list" if self.domain == DomainBoard.Domain.DEMAND else "task-list",
            kanban_url_name="activity-kanban" if self.domain == DomainBoard.Domain.DEMAND else "task-kanban",
            calendar_url_name="activity-calendar" if self.domain == DomainBoard.Domain.DEMAND else "task-calendar",
            create_url_name="activity-create" if self.domain == DomainBoard.Domain.DEMAND else "task-quick-create-standalone",
            activities=items if self.domain == DomainBoard.Domain.DEMAND else None,
            tasks=items if self.domain == DomainBoard.Domain.TASK else None,
        )
        return context


class DemandWorkBoardView(DomainWorkBoardView):
    """A superfície operacional de Demandas.

    O ``DomainBoard`` continua sendo a fonte dos dados e das permissões, mas
    Demandas é uma área de trabalho (não um quadro genérico). Por isso ela
    tem as abas de escopo, os atalhos de prazo e a leitura de entrega que o
    dia a dia pede.
    """

    domain = DomainBoard.Domain.DEMAND
    template_name = "boards/demand_work_board.html"
    workspace_template_name = "workspace/demandas.html"
    lanes_fragment_template = "kanban/_lanes.html"

    def use_workspace(self):
        """Workspace (shell único) ligado para esta pessoa? Flag `WORKSPACE_V2`; desligada = a tela de sempre."""
        if not hasattr(self, "_use_workspace"):
            self._use_workspace = workspace_v2_enabled(self.request.user)
        return self._use_workspace

    def get_template_names(self):
        if getattr(self, "_lanes_fragment", False):
            return [self.lanes_fragment_template]
        return [self.workspace_template_name if self.use_workspace() else self.template_name]

    def wants_lanes_fragment(self):
        """O Kanban redesenha as raias depois de mover um cartão: `?fragmento=raias` devolve só elas (mesma autorização,
        mesmo recorte). Só no Workspace e só na visão Kanban; nas outras o parâmetro é ignorado."""
        return self.use_workspace() and self.request.GET.get("fragmento") == "raias"

    def requested_group_by(self):
        if not self.use_workspace():
            return None
        from .demand_workspace import GROUPING_KEYS

        value = self.request.GET.get("agrupar", "")
        return value if value in GROUPING_KEYS else None

    def arrange_activities(self, queryset):
        if not self.use_workspace():
            return queryset
        from .demand_workspace import order_expressions

        return queryset.order_by(*order_expressions(normalize_workspace_filters(self.request)))

    def _lanes(self, activities):
        """Inclui etapas vazias para que o quadro mostre o fluxo completo."""
        stages = list(
            ActivityStage.objects.filter(
                organization=self.organization, is_active=True
            ).order_by("order", "name", "pk")
        )
        items_by_stage = {}
        for activity in activities:
            items_by_stage.setdefault(activity.stage_id, []).append(activity)

        lanes = [{
            "key": "empty",
            "label": "Sem estágio",
            "color": "#94A3B8",
            "items": items_by_stage.pop(None, []),
        }]
        for stage in stages:
            lanes.append({
                "key": stage.pk,
                "label": stage.name,
                "color": stage.color,
                "items": items_by_stage.pop(stage.pk, []),
            })

        # Uma etapa inativada não pode sumir enquanto ainda houver uma demanda
        # nela: a pessoa precisa conseguir encontrá-la e corrigir o fluxo.
        for stage_id, items in items_by_stage.items():
            stage = next((item.stage for item in items if item.stage_id == stage_id), None)
            lanes.append({
                "key": stage_id,
                "label": stage.name if stage else "Etapa indisponível",
                "color": stage.color if stage else "#94A3B8",
                "items": items,
            })
        return lanes

    def kanban_context(self, context, sectors):
        """Raias e cartões do Kanban no formato do kit (`kanban/_lanes.html`); a montagem fica em `demand_kanban.py`."""
        from .demand_kanban import build_demand_kanban

        from .demand_workspace import GROUPINGS

        request = self.request
        items = context["items"]
        group_by = context["group_by"]
        context["group_label"] = dict(GROUPINGS).get(group_by, group_by)
        if context["group_field"] is None:  # sem o campo do agrupamento não há para onde gravar: ninguém arrasta
            for item in items:
                item.can_move_kanban = False
        elif group_by == "stage":
            # O serviço aceita mover a etapa com `ATIVIDADE_DEFINIR_ETAPA` OU `ATIVIDADE_MOVER_ESTAGIO`; a base só olha a segunda.
            pending = [item for item in items if not item.can_move_kanban]
            if pending:
                allowed = AuthorizationService.can_many(request.user, [(catalog.ATIVIDADE_DEFINIR_ETAPA, item) for item in pending])
                for item in pending:
                    item.can_move_kanban = allowed[(catalog.ATIVIDADE_DEFINIR_ETAPA, item.pk)]
        # No Workspace o nome dos campos só aparece se a pessoa pediu (igual a Quadros); o painel Personalizar lê o mesmo valor.
        show_field_names = bool((context["work_view"].settings or {}).get("show_field_names", False))
        context["show_field_names"] = show_field_names
        params = request.GET.copy()
        params.pop("fragmento", None)  # o endereço que a ficha usa para voltar é o da página, nunca o do fragmento
        query = params.urlencode()
        return_url = f"{request.path}?{query}" if query else request.path
        context["kanban"] = build_demand_kanban(
            groups=context["groups"],
            group_by=group_by,
            sectors_by_id={sector.pk: sector.name for sector in sectors},
            show_field_names=show_field_names,
            can_create=context["can_create"],
            create_url=f"{reverse('activity-create')}?next={quote(return_url)}",
            return_url=return_url,
        )

    def workspace_context(self, context, view_mode):
        """Contexto do shell novo (flag `WORKSPACE_V2`): só a barra; os dados já vieram da consulta de sempre."""
        from .demand_workspace import build_workspace

        User = get_user_model()
        sectors = list(Sector.objects.filter(organization=self.organization, is_active=True).order_by("name"))
        context["view_mode"] = view_mode
        if view_mode == "kanban":
            self.kanban_context(context, sectors)
            if self.wants_lanes_fragment():
                self._lanes_fragment = True  # só as raias: a barra, as abas e os avisos não são desenhados
                return context
        people = list(User.objects.filter(profile__organization=self.organization, is_active=True).order_by("first_name", "username"))
        grouped_list = view_mode == "lista" and self.requested_group_by() is not None
        context["ws"] = build_workspace(
            self.request,
            organization=self.organization,
            view_mode=view_mode,
            filters=normalize_workspace_filters(self.request),
            activities=context["activities"],
            groups=context["groups"],
            people=people,
            sectors=sectors,
            group_by=context["group_by"],
            grouped_list=grouped_list,
        )
        if view_mode == "lista":
            from activities.inline_edit import inline_flags

            inline_flags(self.request.user, context["activities"])
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mode_by_type = {
            DomainBoardView.Type.TABLE: "lista",
            DomainBoardView.Type.KANBAN: "kanban",
            DomainBoardView.Type.CALENDAR: "calendario",
        }
        view_mode = mode_by_type.get(context["work_view"].type, "lista")
        if self.use_workspace():
            return self.workspace_context(context, view_mode)

        from activities.views import (
            activity_filter_context,
            build_filter_toolbar_state,
            visual_filter_choice_groups,
        )
        from activities.filtering import canonical_filter_querystring

        sectors = Sector.objects.filter(
            organization=self.organization, is_active=True
        ).order_by("name")
        selected_sector = normalize_workspace_filters(self.request)["setor"]
        stage_groups, condition_groups = visual_filter_choice_groups(
            self.organization, "demanda", selected_sector
        )

        context.update(activity_filter_context(self.request, self.organization))
        url_name_by_mode = {
            "lista": "activity-list",
            "kanban": "activity-kanban",
            "calendario": "activity-calendar",
        }
        filter_state = build_filter_toolbar_state(
            self.request,
            self.organization,
            domain="demanda",
            view_mode=view_mode,
            sectors=sectors,
            stage_groups=stage_groups,
            condition_groups=condition_groups,
            orderings=[
                ("prazo", "Prazo mais próximo"),
                ("recentes", "Mais recentes"),
                ("titulo", "Demanda (A-Z)"),
            ],
        )
        context.update(
            view_mode=view_mode,
            # As abas sempre usam a URL canônica: elimina parâmetros de
            # visualização/paginação e também transforma o alias legado
            # ``responsavel`` em ``pessoa`` (inclusive quando repetido).
            filter_querystring=canonical_filter_querystring(self.request),
            sectors=sectors,
            stage_choice_groups=stage_groups,
            condition_choice_groups=condition_groups,
            filter_state=filter_state,
            clear_filters_url=f"{reverse(url_name_by_mode[view_mode])}{filter_state['clear_url']}",
        )
        if view_mode == "lista":
            # Edição inline da tabela: o que cada linha mostra como editável (uma consulta de autorização para a
            # lista toda). Só decide o afeto de clique; quem manda é o ActivityService a cada gravação.
            from activities.inline_edit import inline_flags

            inline_flags(self.request.user, context["activities"])
        return context


class TaskWorkBoardView(DomainWorkBoardView):
    domain = DomainBoard.Domain.TASK


class WorkBoardValueView(OrganizationRequiredMixin, View):
    def post(self, request, board_pk, field_pk, object_pk):
        board = get_object_or_404(DomainBoard, pk=board_pk, organization=self.organization)
        field = get_object_or_404(DomainBoardField, pk=field_pk, board=board, is_active=True)
        model = Activity if board.domain == DomainBoard.Domain.DEMAND else Task
        lookup = {"pk": object_pk, "organization": self.organization} if model is Activity else {"pk": object_pk, "activity__organization": self.organization}
        if model is Activity:
            queryset = model.objects.select_related("sector", "stage", "condition", "owner")
        else:
            queryset = model.objects.select_related("sector", "stage", "condition", "responsavel", "activity", "activity__owner")
        item = get_object_or_404(queryset, **lookup)
        action = catalog.ATIVIDADE_VISUALIZAR if model is Activity else catalog.TAREFA_VISUALIZAR
        if not AuthorizationService.can(request.user, action, item):
            raise PermissionDenied("Você não possui acesso a este registro.")
        try:
            data = _request_data(request)
            item = DomainBoardMutationService.set_value(
                board, field, item, data.get("value"), request.user, data.get("updated_at")
            )
        except DomainBoardConflict as exc:
            return self._response(request, item, field, False, str(exc), status=409)
        except (DomainBoardError, Exception) as exc:
            # Services levantam ActivityError (subclasse normal Exception). A
            # mensagem permanece controlada; nada do traceback vai para a UI.
            from activities.services import ActivityError
            if isinstance(exc, (DomainBoardError, ActivityError)):
                return JsonResponse({"success": False, "message": str(exc), "errors": {field.key: [str(exc)]}}, status=400)
            raise
        return self._response(request, item, field, True, "Alteração salva.")

    def _response(self, request, item, field, success, message, status=200):
        organization = item.organization if isinstance(item, Activity) else item.activity.organization
        item = self._refetch(item, organization)
        build_cells([item], [field], organization)
        cell = item.work_cells[0]
        return JsonResponse(
            {
                "success": success,
                "message": message,
                "target": f"work-cell-{item.pk}-{field.pk}",
                "html": render_to_string("boards/_work_cell.html", {"item": item, "cell": cell}, request=request),
                "updated_at": item.updated_at.isoformat(),
                "errors": {},
            },
            status=status,
        )

    @staticmethod
    def _refetch(item, organization):
        if isinstance(item, Activity):
            return Activity.objects.select_related("owner", "sector", "stage", "condition").get(pk=item.pk, organization=organization)
        return Task.objects.select_related("activity", "activity__owner", "responsavel", "sector", "stage", "condition").get(pk=item.pk, activity__organization=organization)


class WorkBoardLayoutView(OrganizationRequiredMixin, View):
    """Persiste largura, ordem e visibilidade por visualização sem mexer no domínio."""
    def post(self, request, view_pk, field_pk):
        view = get_object_or_404(DomainBoardView.objects.select_related("board"), pk=view_pk, board__organization=self.organization)
        if not AuthorizationService.can(request.user, catalog.QUADRO_GERIR_COLUNAS, view.board):
            raise PermissionDenied("Você não possui permissão para configurar este quadro.")
        field = get_object_or_404(DomainBoardField, pk=field_pk, board=view.board)
        data = _request_data(request)
        layout, _ = DomainBoardViewColumn.objects.get_or_create(view=view, field=field)
        if "width" in data:
            layout.width = max(96, min(640, int(data["width"])))
        if "position" in data:
            layout.position = data["position"]
        if "is_visible" in data:
            layout.is_visible = bool(data["is_visible"])
        layout.save()
        return JsonResponse({"success": True, "message": "Layout salvo.", "errors": {}})


class WorkBoardCardFieldsView(OrganizationRequiredMixin, View):
    def post(self, request, view_pk):
        view = get_object_or_404(DomainBoardView.objects.select_related("board"), pk=view_pk, board__organization=self.organization)
        if not AuthorizationService.can(request.user, catalog.QUADRO_GERIR_COLUNAS, view.board):
            raise PermissionDenied("Você não possui permissão para configurar este quadro.")
        data = _request_data(request)
        field_ids = [int(value) for value in data.get("field_ids", [])]
        allowed = set(view.board.fields.filter(pk__in=field_ids, is_active=True).values_list("pk", flat=True))
        DomainBoardCardField.objects.filter(view=view).update(is_visible=False)
        for position, field_id in enumerate(field_ids, start=1):
            if field_id not in allowed:
                continue
            row, _ = DomainBoardCardField.objects.get_or_create(view=view, field_id=field_id)
            row.position, row.is_visible = position * 1000, True
            row.save(update_fields=["position", "is_visible"])
        return JsonResponse({"success": True, "message": "Cartões atualizados.", "errors": {}})


class WorkBoardFieldCreateView(OrganizationRequiredMixin, View):
    """Adiciona campo customizado à configuração; o valor fica em DomainCustomValue."""
    allowed_types = {
        DomainBoardField.Type.TEXT, DomainBoardField.Type.NUMBER, DomainBoardField.Type.CURRENCY,
        DomainBoardField.Type.DATETIME, DomainBoardField.Type.SELECT, DomainBoardField.Type.BOOLEAN,
    }

    def post(self, request, board_pk):
        board = get_object_or_404(DomainBoard, pk=board_pk, organization=self.organization)
        if not AuthorizationService.can(request.user, catalog.QUADRO_GERIR_COLUNAS, board):
            raise PermissionDenied("Você não possui permissão para configurar este quadro.")
        data = _request_data(request)
        label = (data.get("label") or "").strip()
        kind = data.get("type")
        if not label or kind not in self.allowed_types:
            return JsonResponse({"success": False, "message": "Informe nome e tipo válidos.", "errors": {"label": ["Obrigatório"]}}, status=400)
        base_key = "".join(char.lower() if char.isalnum() else "-" for char in label).strip("-") or "campo"
        key, suffix = base_key[:55], 2
        while board.fields.filter(key=key).exists():
            key = f"{base_key[:50]}-{suffix}"
            suffix += 1
        last = board.fields.order_by("-position").first()
        field = DomainBoardField.objects.create(
            board=board, key=key, label=label, type=kind,
            position=(last.position if last else 0) + 1000,
        )
        for view in board.views.filter(type=DomainBoardView.Type.TABLE, is_active=True):
            DomainBoardViewColumn.objects.get_or_create(view=view, field=field, defaults={"position": field.position})
        return JsonResponse({"success": True, "message": "Campo adicionado.", "field_id": field.pk, "errors": {}})


class WorkBoardViewSettingsView(OrganizationRequiredMixin, View):
    def post(self, request, view_pk):
        view = get_object_or_404(DomainBoardView.objects.select_related("board"), pk=view_pk, board__organization=self.organization)
        if not AuthorizationService.can(request.user, catalog.QUADRO_GERIR_COLUNAS, view.board):
            raise PermissionDenied("Você não possui permissão para configurar este quadro.")
        data = _request_data(request)
        settings = dict(view.settings or {})
        group_by = data.get("group_by")
        if group_by:
            allowed = {"stage", "condition", "sector", "owner", "responsavel", "urgency", "priority"}
            if group_by not in allowed or not view.board.fields.filter(key=group_by, is_active=True).exists():
                return JsonResponse({"success": False, "message": "Campo de agrupamento inválido.", "errors": {}}, status=400)
            settings["group_by"] = group_by
        if "show_empty" in data:
            settings["show_empty"] = bool(data["show_empty"])
        if "show_field_names" in data:
            settings["show_field_names"] = bool(data["show_field_names"])
        view.settings = settings
        view.save(update_fields=["settings", "updated_at"])
        return JsonResponse({"success": True, "message": "Visualização atualizada.", "errors": {}})
