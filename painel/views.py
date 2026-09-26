from django.views.generic import TemplateView

from core.mixins import OrganizationRequiredMixin


class TelaEmBrancoView(OrganizationRequiredMixin, TemplateView):
    """Placeholder clicável para itens do menu ainda sem implementação.

    Mantém o menu fiel a Telas/MENU_E_SUBMENUS_LPS.md sem simular
    permissões que o catálogo (acessos/catalog.py) ainda não define.
    """

    template_name = "painel/em_construcao.html"
    titulo = ""
    subtitulo = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = self.titulo
        context["subtitulo"] = self.subtitulo
        return context
