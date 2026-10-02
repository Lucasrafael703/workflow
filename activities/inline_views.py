"""Endpoints da edição inline da lista de Demandas. View fina: resolve a demanda da organização certa, entrega ao
adapter (`activities.inline_edit`) e converte o resultado em JSON. Regra, autorização e auditoria vivem no Service."""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from core.mixins import OrganizationRequiredMixin

from .errors import ActivityError, ActivityPermissionError
from .inline_edit import ActivityInlineService, inline_options, manage_option
from .models import Activity


def _error(exc):
    """Permissão negada = 403 (`ActivityPermissionError`); regra de negócio = 400 (`ActivityError`)."""
    if isinstance(exc, ActivityPermissionError):
        return JsonResponse({"ok": False, "error": str(exc) or "Você não tem permissão para fazer isso."}, status=403)
    return JsonResponse({"ok": False, "error": str(exc)}, status=400)


class InlineActivityMixin:
    """A demanda é sempre da organização da pessoa; rascunho não aparece na lista, então também é 404."""

    def get_activity(self, pk):
        return get_object_or_404(
            Activity.objects.select_related("owner").exclude(status=Activity.Status.RASCUNHO),
            pk=pk,
            organization=self.organization,
        )


class ActivityInlineUpdateView(InlineActivityMixin, OrganizationRequiredMixin, View):
    """POST `field` + `value` (ou `date` e `time` no prazo; `new_name` e `new_color` ao criar setor). Permissão negada =
    403; regra de negócio = 400; demanda de outra organização (ou rascunho) = 404. Nunca usa `messages.*`: a resposta é
    só JSON."""

    http_method_names = ["post"]

    def post(self, request, pk):
        activity = self.get_activity(pk)
        field = (request.POST.get("field") or "").strip()
        try:
            result = ActivityInlineService.update(user=request.user, activity=activity, field=field, data=request.POST)
        except ActivityError as exc:  # inclui ActivityPermissionError
            return _error(exc)
        return JsonResponse({"ok": True, "field": field, **result})


class ActivityInlineOptionsView(InlineActivityMixin, OrganizationRequiredMixin, View):
    """GET `?campo=sector|stage|condition`: lista de opções do pop-over, no contexto da demanda (o setor vem dela, nunca
    do cliente). POST `campo`, `acao=criar|editar`, `name`, `color`, `option_id`: cria ou edita (nome e cor) uma etapa ou
    status do setor da demanda; exige a permissão de gerir etapas/status no setor."""

    http_method_names = ["get", "post"]

    def post(self, request, pk):
        activity = self.get_activity(pk)
        try:
            data, created = manage_option(request.user, activity, request.POST)
        except ActivityError as exc:  # inclui ActivityPermissionError
            return _error(exc)
        return JsonResponse({"ok": True, **data}, status=201 if created else 200)

    def get(self, request, pk):
        activity = self.get_activity(pk)
        field = (request.GET.get("campo") or "").strip()
        try:
            data = inline_options(request.user, activity, field)
        except ActivityError as exc:  # inclui ActivityPermissionError
            return _error(exc)
        return JsonResponse({"ok": True, "field": field, **data})
