"""One editor for creation, drafts and changes to published activities.

A demanda é criada e editada na mesma janela de quatro etapas (ver
`ActivityEditorForm` e `activity_form.html`): todas as etapas são campos de um
único formulário e nada é gravado até o envio final — a criação continua usando
`ActivityService.save_draft` + `publish_draft` e a edição `update_activity`. Ao editar, o passo do quadro pode
trocá-lo (`BoardInstantiationService.replace_for_activity`, na mesma transação, com confirmação).
"""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView

from acessos import catalog
from acessos.services import AuthorizationService
from core.mixins import OrganizationRequiredMixin
from core.models import ActivityStage, Sector, WorkflowStatus

from boards.demand_services import BoardInstantiationService
from boards.services import BoardError

from .forms import ActivityEditorForm, activity_summary
from .models import Activity
from .navigation import activity_detail_url, activity_return_url
from .services import ActivityError, ActivityService

DRAFT_ACTIONS = {"rascunho", "sair", "continuar"}


def _pk(value):
    return int(value) if str(value or "").isdigit() else None


def creation_presets(params, organization):
    """Valores iniciais da janela "Nova demanda" quando ela abre de uma raia do Kanban (`?setor=&etapa=&condicao=&urgencia=&pessoa=`).

    Só vale o que existe na organização e combina entre si; o resto é ignorado em silêncio (a janela abre normal, como sem o
    parâmetro), porque um endereço antigo ou editado à mão nunca deve impedir de criar. Etapa e status são de UM setor: se o setor
    não veio, o dela é o setor da demanda; se veio outro, ela é ignorada. A janela continua sendo quem valida tudo ao enviar."""
    initial = {}
    sector = Sector.objects.filter(pk=_pk(params.get("setor")), organization=organization, is_active=True).first() if _pk(params.get("setor")) else None
    stage_id, condition_id = _pk(params.get("etapa")), _pk(params.get("condicao"))
    stage = ActivityStage.objects.filter(pk=stage_id, organization=organization, is_active=True).first() if stage_id else None
    condition = (
        WorkflowStatus.objects.filter(pk=condition_id, organization=organization, domain=WorkflowStatus.Domain.ACTIVITY, is_active=True).first()
        if condition_id else None
    )
    for option in (stage, condition):
        if option is not None and sector is None:
            sector = Sector.objects.filter(pk=option.sector_id, organization=organization, is_active=True).first()
    if sector is not None:
        initial["sector"] = sector.pk
        if stage is not None and stage.sector_id == sector.pk:
            initial["stage"] = stage.pk
        if condition is not None and condition.sector_id == sector.pk:
            initial["condition"] = condition.pk
    if params.get("urgencia") in Activity.Urgency.values:
        initial["urgency"] = params["urgencia"]
    person_id = _pk(params.get("pessoa"))
    if person_id:
        person = get_user_model().objects.filter(pk=person_id, profile__organization=organization, is_active=True).first()
        if person is not None:
            initial["owner"] = person
    return initial


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

    def get_initial(self):
        initial = super().get_initial()
        if not self.editing and self.request.method == "GET" and not self.request.GET.get("pk"):
            initial.update(creation_presets(self.request.GET, self.organization))
        return initial

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

    def requested_step(self, total):
        """Etapa em que a janela abre. `?passo=2` abre a edição direto em "Informações do cliente" (clique em
        Cliente / Obra na lista de Demandas). Só vale para editar e para o GET; valor inválido cai na primeira
        etapa. Com o formulário enviado, quem decide é `step_with_errors`."""
        if not self.editing:
            return 1
        try:
            step = int(self.request.GET.get("passo", ""))
        except (TypeError, ValueError):
            return 1
        return step if 1 <= step <= total else 1

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activity = self.get_activity()
        return_url = activity_return_url(self.request)
        form = context["form"]
        context.update(
            activity=activity, draft=activity if not self.editing else None,
            editing=self.editing, picker=self.picker, return_url=return_url,
            cancel_url=activity_detail_url(activity, return_url) if self.editing else return_url,
            editor_title="Editar demanda" if self.editing else "Nova demanda",
            editor_subtitle=(
                "Atualize as informações da demanda."
                if self.editing
                else "Preencha as informações para criar uma nova demanda."
            ),
            submit_label="Salvar alterações" if self.editing else "Criar demanda",
            steps=form.steps,
            initial_step=form.step_with_errors() if form.is_bound else self.requested_step(len(form.steps)),
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
                    data.pop("board_setup_mode", None)
                    template = data.pop("board_template", None)
                    confirmed = bool(data.pop("confirm_board_replace", False))
                    # Fetch a fresh instance: ModelForm validation mutates its instance.
                    activity.refresh_from_db()
                    ActivityService.update_activity(activity, self.request.user, **data)
                    if owner and owner.pk != activity.owner_id:
                        ActivityService.change_owner(activity, owner, self.request.user)
                    # O quadro: mesma escolha = nada; outra = troca (exclui as tarefas do quadro atual, já confirmada no
                    # formulário); demanda antiga sem quadro ganha o dela. Tudo na mesma transação da edição.
                    BoardInstantiationService.replace_for_activity(
                        user=self.request.user, activity=activity, template=template, confirmed=confirmed
                    )
                else:
                    activity = ActivityService.save_draft(
                        self.organization, self.request.user, activity=activity, **data,
                    )
                    if not save_draft:
                        ActivityService.publish_draft(activity, self.request.user)
        except (ActivityError, BoardError) as exc:
            # Falha ao montar o quadro (modelo indisponível...) vira erro do formulário, não 500; nada é gravado.
            # Pedir confirmação (ou recusar o quadro) aparece no passo 3: no campo do modelo só se ele está à vista.
            field = None
            if isinstance(exc, BoardError):
                field = "board_template" if form.cleaned_data.get("board_template") else "board_setup_mode"
            form.add_error(field, str(exc))
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
                "Demanda atualizada." if self.editing else "Demanda criada. Adicione as tarefas para organizar a execução.",
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
