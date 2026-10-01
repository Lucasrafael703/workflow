"""One editor for creation, drafts and changes to published activities.

A atividade é criada e editada na mesma janela de três etapas (ver
`ActivityEditorForm` e `activity_form.html`): todas as etapas são campos de um
único formulário e nada é gravado até o envio final — a criação continua usando
`ActivityService.save_draft` + `publish_draft` e a edição `update_activity`.
"""

from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView

from acessos import catalog
from acessos.services import AuthorizationService
from core.mixins import OrganizationRequiredMixin

from .forms import ActivityEditorForm, activity_summary
from .models import Activity
from .navigation import activity_detail_url, activity_return_url
from .services import ActivityError, ActivityService

DRAFT_ACTIONS = {"rascunho", "sair", "continuar"}


class ActivityEditorView(OrganizationRequiredMixin, FormView):
    template_name = "activities/activity_form.html"
    form_class = ActivityEditorForm
    editing = False
    picker = False

    def is_ajax(self):
        return self.request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def saving_draft(self):
        return not self.editing and self.request.POST.get("acao") in DRAFT_ACTIONS

    def get_activity(self):
        if hasattr(self, "_activity"):
            return self._activity
        pk = self.kwargs.get("pk") if self.editing else self.request.GET.get("pk") or self.request.POST.get("pk")
        filters = {"pk": pk, "organization": self.organization}
        if not self.editing:
            filters.update(status=Activity.Status.RASCUNHO, created_by=self.request.user)
        self._activity = get_object_or_404(Activity, **filters) if pk else None
        if self._activity and self._activity.status == Activity.Status.RASCUNHO and self._activity.created_by_id != self.request.user.pk:
            raise Http404
        return self._activity

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        activity = self.get_activity()
        user = self.request.user
        if self.editing:
            if not AuthorizationService.can(user, catalog.ATIVIDADE_EDITAR, activity):
                raise PermissionDenied
        elif not AuthorizationService.can_anywhere(user, catalog.ATIVIDADE_CRIAR):
            raise PermissionDenied
        kwargs.update(
            organization=self.organization, instance=activity, user=user,
            drafting=not self.editing,
            can_change_owner=not self.editing or AuthorizationService.can(user, catalog.ATIVIDADE_ALTERAR_DONO, activity),
            # Nome, responsável e setor só deixam de ser exigidos no rascunho antigo.
            require_essentials=not self.saving_draft(),
        )
        for name, action in {
            "person": catalog.USUARIO_CRIAR, "client": catalog.CLIENTE_GERIR,
            "sector": catalog.SETOR_EDITAR, "company": catalog.EMPRESA_GERIR,
            "site": catalog.OBRA_GERIR, "cost_center": catalog.CENTRO_CUSTO_GERIR,
        }.items():
            kwargs[f"can_create_{name}"] = AuthorizationService.can(user, action)
        return kwargs

    def get(self, request, *args, **kwargs):
        activity = self.get_activity()
        if self.editing and activity.status == Activity.Status.RASCUNHO:
            return redirect(f"{reverse('activity-create')}?pk={activity.pk}")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        activity = self.get_activity()
        if self.editing and activity.status == Activity.Status.RASCUNHO:
            return redirect(f"{reverse('activity-create')}?pk={activity.pk}")
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activity = self.get_activity()
        return_url = activity_return_url(self.request)
        form = context["form"]
        context.update(
            activity=activity, draft=activity if not self.editing else None,
            editing=self.editing, picker=self.picker, return_url=return_url,
            cancel_url=activity_detail_url(activity, return_url) if self.editing else return_url,
            editor_title="Editar atividade" if self.editing else "Nova atividade",
            editor_subtitle=(
                "Atualize as informações da atividade."
                if self.editing
                else "Preencha as informações para criar uma nova atividade."
            ),
            submit_label="Salvar alterações" if self.editing else "Criar atividade",
            steps=form.steps,
            initial_step=form.step_with_errors() if form.is_bound else 1,
            # Anexos enviados antes desta tela perder o upload: continuam removíveis.
            attachments=activity.attachments.all() if activity else [],
        )
        return context

    def form_valid(self, form):
        activity = self.get_activity()
        data = dict(form.cleaned_data)
        save_draft = self.saving_draft()
        try:
            with transaction.atomic():
                if self.editing:
                    owner = data.pop("owner")
                    # Fetch a fresh instance: ModelForm validation mutates its instance.
                    activity.refresh_from_db()
                    ActivityService.update_activity(activity, self.request.user, **data)
                    if owner and owner.pk != activity.owner_id:
                        ActivityService.change_owner(activity, owner, self.request.user)
                else:
                    activity = ActivityService.save_draft(
                        self.organization, self.request.user, activity=activity, **data,
                    )
                    if not save_draft:
                        ActivityService.publish_draft(activity, self.request.user)
        except ActivityError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        return_url = activity_return_url(self.request)
        if self.picker and self.is_ajax():
            return JsonResponse(
                {"id": activity.pk, "name": f"{activity.code} — {activity.title}", "summary": activity_summary(activity)}
            )
        if save_draft:
            target = reverse("activity-create") + "?" + urlencode({"pk": activity.pk, "next": return_url})
            messages.success(self.request, "Rascunho salvo.")
        else:
            target = activity_detail_url(activity, return_url)
            messages.success(
                self.request,
                "Atividade atualizada." if self.editing else "Atividade criada. Adicione as tarefas para organizar a execução.",
            )
        if self.is_ajax():
            return JsonResponse({"redirect_url": target})
        return redirect(target)

    def form_invalid(self, form):
        if self.is_ajax():
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class ActivityCreateView(ActivityEditorView):
    pass


class ActivityEditView(ActivityEditorView):
    editing = True


class ActivityMiniCreateView(ActivityCreateView):
    """Same fields and validation when creating from a task's activity selector."""

    picker = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if kwargs.get("data") is not None and "owner" not in kwargs["data"]:
            # Compatibility with a title-only selector opened before this release:
            # no owner and no sector were ever sent, so they cannot be required.
            kwargs["data"] = kwargs["data"].copy()
            kwargs["data"]["owner"] = self.request.user.pk
            kwargs["require_essentials"] = False
        return kwargs
