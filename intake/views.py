"""Telas da Caixa de Entrada.

Views finas: carregam o item da organização certa, checam a permissão e deixam a
regra para `IntakeService`. Sem JavaScript tudo funciona como página; com JS os
mesmos endereços abrem em janela (`LPSModal`) e respondem JSON.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView

from acessos import catalog
from acessos.services import AuthorizationService
from core.mixins import OrganizationRequiredMixin

from .forms import IntakeCaptureForm, IntakeConvertForm, IntakeEditForm, IntakeIgnoreForm
from .models import IntakeItem
from .policies import IntakePolicy
from .services import IntakeError, IntakeService

PAGE_SIZE = 25
ITEM_RELATED = ("suggested_client", "suggested_site", "suggested_sector", "activity")
UI_ACTIONS = ("edit", "convert", "ignore", "restore")

TABS = [
    ("novos", "Novas", IntakeItem.Status.NOVO),
    ("convertidos", "Viraram demanda", IntakeItem.Status.CONVERTIDO),
    ("ignorados", "Ignoradas", IntakeItem.Status.IGNORADO),
]
TAB_STATUS = {key: status for key, _, status in TABS}


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def item_actions(user, items):
    """{pk: {"edit": bool, …}} — o que a pessoa pode fazer agora, juntando estado e catálogo.

    Uma consulta de autorização para a página inteira (`can_many`), não uma por cartão.
    """
    items = list(items)
    if not items:
        return {}
    allowed = AuthorizationService.can_many(user, [(catalog.ENTRADA_TRIAR, item) for item in items])
    result = {}
    for item in items:
        can_triage = allowed.get((catalog.ENTRADA_TRIAR, item.pk), False)
        available = IntakePolicy.available_actions(item)
        result[item.pk] = {action: can_triage and action in available for action in UI_ACTIONS}
    return result


class AnywhereActionMixin:
    """Abre a tela para quem pode a ação em algum lugar (o conteúdo é filtrado depois).

    Registrar e listar não têm setor ainda: `ActionRequiredMixin` só olharia o
    escopo de organização e negaria quem cuida de um setor.
    """

    anywhere_action = None

    def dispatch(self, request, *args, **kwargs):
        if not AuthorizationService.can_anywhere(request.user, self.anywhere_action):
            raise PermissionDenied("Você não possui acesso a este conteúdo.")
        return super().dispatch(request, *args, **kwargs)


class ItemActionMixin:
    """Carrega a solicitação da própria organização (outra = 404) e exige a ação sobre ela."""

    required_action = None
    #: ação de tela exigida do estado do item ("edit", "convert"…); None = qualquer estado
    state_action = None

    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(
            IntakeItem.objects.select_related(*ITEM_RELATED, "created_by", "resolved_by"),
            pk=kwargs["pk"],
            organization=self.organization,
        )
        if not AuthorizationService.can(request.user, self.required_action, self.item):
            raise PermissionDenied("Você não possui acesso a este conteúdo.")
        if self.state_action and self.state_action not in IntakePolicy.available_actions(self.item):
            messages.error(request, "Esta solicitação já foi tratada.")
            return redirect("intake-detail", pk=self.item.pk)
        return super().dispatch(request, *args, **kwargs)


class IntakeListView(OrganizationRequiredMixin, AnywhereActionMixin, TemplateView):
    template_name = "intake/intake_list.html"
    anywhere_action = catalog.ENTRADA_VISUALIZAR

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        tab = request.GET.get("status", "novos")
        if tab not in TAB_STATUS:
            tab = "novos"
        search = (request.GET.get("q") or "").strip()

        visible = IntakeService.visible_queryset(request.user, self.organization)
        counts = {row["status"]: row["total"] for row in visible.values("status").annotate(total=Count("pk"))}

        queryset = visible.filter(status=TAB_STATUS[tab]).select_related(*ITEM_RELATED)
        if search:
            queryset = queryset.filter(
                Q(subject__icontains=search)
                | Q(sender_name__icontains=search)
                | Q(sender_email__icontains=search)
                | Q(raw_content__icontains=search)
                | Q(suggested_title__icontains=search)
            )
        page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
        actions = item_actions(request.user, page.object_list)
        for item in page.object_list:
            item.ui = actions[item.pk]

        context.update(
            tab=tab,
            search=search,
            page_obj=page,
            is_paginated=page.paginator.num_pages > 1,
            tabs=[{"key": key, "label": label, "count": counts.get(status, 0)} for key, label, status in TABS],
            can_register=AuthorizationService.can_anywhere(request.user, catalog.ENTRADA_REGISTRAR),
        )
        return context


class IntakeDetailView(OrganizationRequiredMixin, ItemActionMixin, TemplateView):
    template_name = "intake/intake_detail.html"
    required_action = catalog.ENTRADA_VISUALIZAR

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.item.ui = item_actions(self.request.user, [self.item])[self.item.pk]
        context.update(item=self.item, events=self.item.events.select_related("user"))
        return context


class ModalFormMixin:
    """Formulário que funciona como página e como janela (JSON)."""

    #: o formulário escolhe cliente/obra/setor/pessoa e por isso precisa da organização
    scope_form = True
    success_message = ""
    #: a janela segue para outra página e o aviso (toast) some junto: grava também como mensagem da próxima
    flash_when_navigating = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.scope_form:
            kwargs["organization"] = self.organization
        return kwargs

    def perform(self, form):
        """Chama o serviço e devolve o resultado (item ou atividade)."""
        raise NotImplementedError

    def message_for(self, result):
        return self.success_message

    def success_payload(self, result):
        """Corpo JSON do sucesso, além da mensagem (a janela aplica `remove`/`html`/`redirect_url`)."""
        return {}

    def success_url_for(self, result):
        return reverse("intake-detail", args=[self.item.pk])

    def form_valid(self, form):
        try:
            result = self.perform(form)
        except IntakeError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        message = self.message_for(result)
        if _is_ajax(self.request):
            if self.flash_when_navigating:
                messages.success(self.request, message)
            return JsonResponse({"message": message, **self.success_payload(result)})
        messages.success(self.request, message)
        return redirect(self.success_url_for(result))

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class IntakeCaptureView(OrganizationRequiredMixin, AnywhereActionMixin, ModalFormMixin, FormView):
    template_name = "intake/intake_capture.html"
    form_class = IntakeCaptureForm
    anywhere_action = catalog.ENTRADA_REGISTRAR
    scope_form = False
    flash_when_navigating = True
    success_message = "Solicitação registrada na Caixa de Entrada."

    def landing_url(self):
        """Quem não pode ver a Caixa de Entrada volta para o início depois de registrar."""
        if AuthorizationService.can_anywhere(self.request.user, catalog.ENTRADA_VISUALIZAR):
            return reverse("intake-list")
        return reverse("home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.landing_url()
        return context

    def perform(self, form):
        return IntakeService.register(self.organization, self.request.user, **form.service_kwargs())

    def success_url_for(self, result):
        return self.landing_url()

    def success_payload(self, result):
        return {"redirect_url": self.landing_url()}


class _ItemFormView(OrganizationRequiredMixin, ItemActionMixin, ModalFormMixin, FormView):
    required_action = catalog.ENTRADA_TRIAR

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(item=self.item, cancel_url=reverse("intake-detail", args=[self.item.pk]))
        return context


class IntakeEditView(_ItemFormView):
    template_name = "intake/intake_edit.html"
    form_class = IntakeEditForm
    state_action = "edit"
    success_message = "Sugestões atualizadas."

    def get_initial(self):
        return IntakeEditForm.initial_from(self.item)

    def perform(self, form):
        return IntakeService.update_suggestions(self.item, self.request.user, **form.service_kwargs())

    def success_payload(self, result):
        # Troca o cartão na lista; no detalhe não existe cartão com este id e a janela recarrega a tela.
        item = IntakeItem.objects.select_related(*ITEM_RELATED).get(pk=result.pk)
        item.ui = item_actions(self.request.user, [item])[item.pk]
        html = render_to_string("intake/_item_card.html", {"item": item}, request=self.request)
        return {"html": html, "target": f"#intake-item-{item.pk}"}


class IntakeConvertView(_ItemFormView):
    template_name = "intake/intake_convert.html"
    form_class = IntakeConvertForm
    state_action = "convert"
    flash_when_navigating = True
    success_message = "Demanda criada a partir da solicitação."

    def get_initial(self):
        item = self.item
        _, external_requester = IntakeService.requester_defaults(item)
        profile = getattr(self.request.user, "profile", None)
        return {
            "title": item.suggested_title,
            "client": item.suggested_client,
            "site": item.suggested_site,
            "sector": item.suggested_sector or getattr(profile, "main_sector", None),
            "owner": self.request.user,
            "requested_deadline": item.suggested_deadline,
            "external_requester": external_requester,
        }

    def perform(self, form):
        return IntakeService.convert(self.item, self.request.user, **form.service_kwargs())

    def message_for(self, activity):
        return f"Demanda {activity.code} criada. Adicione as tarefas para organizar a execução."

    def success_url_for(self, activity):
        return reverse("activity-detail", args=[activity.pk])

    def success_payload(self, activity):
        return {"redirect_url": self.success_url_for(activity)}


class IntakeIgnoreView(_ItemFormView):
    template_name = "intake/intake_ignore.html"
    form_class = IntakeIgnoreForm
    state_action = "ignore"
    scope_form = False
    success_message = "Solicitação ignorada. Ela continua na aba Ignoradas, caso precise voltar."

    def perform(self, form):
        return IntakeService.ignore(self.item, self.request.user, form.cleaned_data["reason"])

    def success_payload(self, result):
        return {"remove": f"#intake-item-{result.pk}"}


class IntakeRestoreView(OrganizationRequiredMixin, ItemActionMixin, View):
    """Só POST: restaurar não precisa de formulário, só do clique."""

    http_method_names = ["post"]
    required_action = catalog.ENTRADA_TRIAR

    def post(self, request, *args, **kwargs):
        try:
            item = IntakeService.restore(self.item, request.user)
        except IntakeError as exc:
            if _is_ajax(request):
                return JsonResponse({"error": str(exc)}, status=400)
            messages.error(request, str(exc))
            return redirect("intake-detail", pk=self.item.pk)

        message = "Solicitação restaurada. Ela voltou para as novas."
        if _is_ajax(request):
            return JsonResponse({"message": message, "remove": f"#intake-item-{item.pk}"})
        messages.success(request, message)
        return redirect("intake-detail", pk=item.pk)
