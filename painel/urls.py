from django.urls import path

from core.views import EtapasEStatusView, PrioridadesView

from . import views

# Cada rota é uma tela em branco: existe, é clicável, mas ainda não tem
# implementação. Ver Telas/MENU_E_SUBMENUS_LPS.md para a árvore completa.
urlpatterns = [
    path(
        "equipe/pessoas/",
        views.TelaEmBrancoView.as_view(titulo="Pessoas", subtitulo="Equipe"),
        name="equipe-pessoas",
    ),
    path(
        "equipe/capacidade/",
        views.TelaEmBrancoView.as_view(titulo="Capacidade", subtitulo="Equipe"),
        name="equipe-capacidade",
    ),
    path(
        "equipe/carga-de-trabalho/",
        views.TelaEmBrancoView.as_view(titulo="Carga de trabalho", subtitulo="Equipe"),
        name="equipe-carga-trabalho",
    ),
    path(
        "filas-e-gargalos/filas/",
        views.TelaEmBrancoView.as_view(titulo="Filas", subtitulo="Filas e gargalos"),
        name="gargalos-filas",
    ),
    path(
        "filas-e-gargalos/gargalos/",
        views.TelaEmBrancoView.as_view(titulo="Gargalos", subtitulo="Filas e gargalos"),
        name="gargalos-gargalos",
    ),
    path(
        "filas-e-gargalos/bloqueios/",
        views.TelaEmBrancoView.as_view(titulo="Bloqueios", subtitulo="Filas e gargalos"),
        name="gargalos-bloqueios",
    ),
    path(
        "filas-e-gargalos/devolucoes/",
        views.TelaEmBrancoView.as_view(titulo="Devoluções", subtitulo="Filas e gargalos"),
        name="gargalos-devolucoes",
    ),
    path(
        "processos/modelos/",
        views.TelaEmBrancoView.as_view(titulo="Modelos", subtitulo="Processos"),
        name="processos-modelos",
    ),
    path(
        "insights/",
        views.TelaEmBrancoView.as_view(titulo="Insights"),
        name="insights",
    ),
    path(
        "desenvolvimento/",
        views.TelaEmBrancoView.as_view(titulo="Desenvolvimento"),
        name="desenvolvimento",
    ),
    path(
        "resultados/",
        views.TelaEmBrancoView.as_view(titulo="Resultados"),
        name="resultados",
    ),
    path(
        "configuracoes/etapas-e-status/",
        EtapasEStatusView.as_view(),
        name="config-etapas-status",
    ),
    path(
        "configuracoes/prioridades/",
        PrioridadesView.as_view(),
        name="config-prioridades",
    ),
    path(
        "configuracoes/motivos-de-bloqueio/",
        views.TelaEmBrancoView.as_view(titulo="Motivos de bloqueio", subtitulo="Configurações"),
        name="config-motivos-bloqueio",
    ),
    path(
        "configuracoes/motivos-de-devolucao/",
        views.TelaEmBrancoView.as_view(titulo="Motivos de devolução", subtitulo="Configurações"),
        name="config-motivos-devolucao",
    ),
    path(
        "integracoes/",
        views.TelaEmBrancoView.as_view(titulo="Integrações"),
        name="integracoes",
    ),
]
