from django import forms
from django.urls import reverse_lazy
from django.utils.html import format_html


class PersonPickerWidget(forms.HiddenInput):
    """Seletor de pessoa com busca, no lugar de um <select> que só cresce.

    Continua sendo um input escondido com o id do usuário por baixo: o campo
    do form (ModelChoiceField) não muda, só a apresentação. Busca e lista de
    resultados são client-side (static/js/person-picker.js), consultando
    `search_url`. Quando `create_url` é informado — a view decide isso
    checando autorização, o widget não conhece o catálogo de ações — o popup
    oferece "+ Criar novo usuário" sem sair da tela atual.

    Renderiza sem template próprio: o FormRenderer padrão do Django só olha
    os `templates/` de cada app (APP_DIRS), não o DIRS do TEMPLATES do
    projeto, onde vive o resto da UI da LPS — então o HTML é montado aqui em
    vez de depender de um segundo diretório de templates só para isto.
    """

    search_url_name = "person-search"

    def __init__(self, attrs=None, create_url=None, queryset=None):
        super().__init__(attrs)
        self.create_url = create_url
        self.queryset = queryset

    def _label_for(self, value):
        if not value or self.queryset is None:
            return ""
        try:
            user = self.queryset.get(pk=value)
        except (self.queryset.model.DoesNotExist, ValueError, TypeError):
            return ""
        return user.get_full_name() or user.get_username()

    def render(self, name, value, attrs=None, renderer=None):
        hidden_html = super().render(name, value, attrs, renderer)
        label = self._label_for(value)
        search_url = reverse_lazy(self.search_url_name)

        create_attr = format_html(' data-create-url="{}"', self.create_url) if self.create_url else ""
        label_class = "" if label else " muted"

        return format_html(
            '<div class="person-picker" data-person-picker data-search-url="{search_url}"{create_attr}>'
            '{hidden_html}'
            '<button type="button" class="person-picker__trigger">'
            '<span class="person-picker__icon">{icon}</span>'
            '<span class="person-picker__label{label_class}">{label}</span>'
            "</button>"
            "</div>",
            search_url=search_url,
            create_attr=create_attr,
            hidden_html=hidden_html,
            icon=_SEARCH_ICON,
            label_class=label_class,
            label=label or "Selecionar pessoa",
        )


_SEARCH_ICON = format_html(
    '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><use href="#i-search"></use></svg>'
)


class ClientPickerWidget(forms.HiddenInput):
    """Seletor de cliente com busca (Regras 1-2 da tela de atividade).

    Mesmo padrão do `PersonPickerWidget` — digitar filtra, "Cadastra cliente"
    cria sem sair da tela — mas aponta para o cadastro de clientes em vez de
    usuários. Reaproveita as classes `.person-picker*` do design system: o
    JS (`static/js/person-picker.js`) já é genérico o bastante para servir os
    dois, e diferencia só o rótulo do botão de criação via `data-create-label`.
    """

    search_url_name = "client-search"

    def __init__(self, attrs=None, create_url=None, queryset=None):
        super().__init__(attrs)
        self.create_url = create_url
        self.queryset = queryset

    def _label_for(self, value):
        if not value or self.queryset is None:
            return ""
        try:
            client = self.queryset.get(pk=value)
        except (self.queryset.model.DoesNotExist, ValueError, TypeError):
            return ""
        return client.name

    def render(self, name, value, attrs=None, renderer=None):
        hidden_html = super().render(name, value, attrs, renderer)
        label = self._label_for(value)
        search_url = reverse_lazy(self.search_url_name)

        create_attr = format_html(' data-create-url="{}"', self.create_url) if self.create_url else ""
        label_class = "" if label else " muted"

        return format_html(
            '<div class="person-picker" data-person-picker data-search-url="{search_url}"'
            ' data-create-label="Cadastrar cliente"{create_attr}>'
            '{hidden_html}'
            '<button type="button" class="person-picker__trigger">'
            '<span class="person-picker__icon">{icon}</span>'
            '<span class="person-picker__label{label_class}">{label}</span>'
            "</button>"
            "</div>",
            search_url=search_url,
            create_attr=create_attr,
            hidden_html=hidden_html,
            icon=_SEARCH_ICON,
            label_class=label_class,
            label=label or "Selecionar cliente",
        )
