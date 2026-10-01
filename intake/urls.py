from functools import wraps

from django.conf import settings
from django.http import Http404
from django.urls import path

from . import views


def only_when_enabled(view):
    """A Caixa de Entrada está inativa por padrão (`settings.INTAKE_ENABLED`): desligada, toda rota dela dá 404.

    A checagem é feita a cada pedido, então ligar ou desligar a chave não exige mexer nas rotas.
    """

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not settings.INTAKE_ENABLED:
            raise Http404("A Caixa de Entrada não está ativa.")
        return view(request, *args, **kwargs)

    return wrapped


urlpatterns = [
    path("", only_when_enabled(views.IntakeListView.as_view()), name="intake-list"),
    path("registrar/", only_when_enabled(views.IntakeCaptureView.as_view()), name="intake-capture"),
    path("<int:pk>/", only_when_enabled(views.IntakeDetailView.as_view()), name="intake-detail"),
    path("<int:pk>/editar/", only_when_enabled(views.IntakeEditView.as_view()), name="intake-edit"),
    path("<int:pk>/criar-demanda/", only_when_enabled(views.IntakeConvertView.as_view()), name="intake-convert"),
    path("<int:pk>/ignorar/", only_when_enabled(views.IntakeIgnoreView.as_view()), name="intake-ignore"),
    path("<int:pk>/restaurar/", only_when_enabled(views.IntakeRestoreView.as_view()), name="intake-restore"),
]
