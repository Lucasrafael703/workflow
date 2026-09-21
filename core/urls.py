from django.urls import path

from . import views

urlpatterns = [
    path("api/pessoas/", views.PersonSearchView.as_view(), name="person-search"),
    path("api/clientes/", views.ClientSearchView.as_view(), name="client-search"),
    path("cadastros/", views.CadastroHomeView.as_view(), name="cadastros"),
    path("cadastros/setores/novo/", views.SectorFormView.as_view(), name="sector-create"),
    path("cadastros/setores/<int:pk>/", views.SectorFormView.as_view(), name="sector-edit"),
    path("cadastros/empresas/nova/", views.CompanyFormView.as_view(), name="company-create"),
    path("cadastros/empresas/<int:pk>/", views.CompanyFormView.as_view(), name="company-edit"),
    path("cadastros/obras/nova/", views.SiteFormView.as_view(), name="site-create"),
    path("cadastros/obras/<int:pk>/", views.SiteFormView.as_view(), name="site-edit"),
    path("cadastros/centros-de-custo/novo/", views.CostCenterFormView.as_view(), name="costcenter-create"),
    path("cadastros/centros-de-custo/<int:pk>/", views.CostCenterFormView.as_view(), name="costcenter-edit"),
    path("cadastros/clientes/novo/", views.ClientFormView.as_view(), name="client-create"),
    path("cadastros/clientes/<int:pk>/", views.ClientFormView.as_view(), name="client-edit"),
    path("cadastros/motivos/novo/", views.ReturnReasonFormView.as_view(), name="returnreason-create"),
    path("cadastros/motivos/<int:pk>/", views.ReturnReasonFormView.as_view(), name="returnreason-edit"),
    path(
        "cadastros/<str:tab>/<int:pk>/situacao/",
        views.CadastroToggleActiveView.as_view(),
        name="cadastro-toggle",
    ),
    path("configuracoes/", views.SettingsView.as_view(), name="settings"),
    path("permissoes/", views.PermissionMatrixView.as_view(), name="permissions"),
    path("permissoes/<int:pk>/salvar/", views.PermissionUpdateView.as_view(), name="permissions-update"),
    path("perfis/novo/", views.ProfileFormView.as_view(), name="profile-create"),
    path("perfis/<int:pk>/", views.ProfileFormView.as_view(), name="profile-edit"),
    path("usuarios/", views.UserListView.as_view(), name="user-list"),
    path("usuarios/novo/", views.UserFormView.as_view(), name="user-create"),
    path("usuarios/<int:pk>/", views.UserFormView.as_view(), name="user-edit"),
    path("usuarios/<int:pk>/acessos/", views.UserAccessView.as_view(), name="user-access"),
    path(
        "usuarios/<int:pk>/acessos/<int:assignment_pk>/remover/",
        views.UserAccessRemoveView.as_view(),
        name="user-access-remove",
    ),
    path("usuarios/<int:pk>/concessoes/", views.UserGrantActionView.as_view(), name="user-grant"),
    path(
        "usuarios/<int:pk>/concessoes/<int:grant_pk>/remover/",
        views.UserGrantRemoveView.as_view(),
        name="user-grant-remove",
    ),
]
