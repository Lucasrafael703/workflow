from django import forms
from django.urls import reverse_lazy
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe


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


class ActivityPickerWidget(forms.HiddenInput):
    """Seletor de atividade com busca, para o fluxo "+ Nova tarefa" fora do
    contexto de uma atividade já aberta: toda tarefa continua pertencendo a
    uma atividade, mas a pessoa escolhe/cria a atividade sem sair do popup.
    Mesmo padrão de `ClientPickerWidget` — busca e criação rápida via
    `static/js/person-picker.js`, já genérico o bastante para os dois.
    """

    search_url_name = "activity-search"

    def __init__(self, attrs=None, create_url=None, queryset=None):
        super().__init__(attrs)
        self.create_url = create_url
        self.queryset = queryset

    def _label_for(self, value):
        if not value or self.queryset is None:
            return ""
        try:
            activity = self.queryset.get(pk=value)
        except (self.queryset.model.DoesNotExist, ValueError, TypeError):
            return ""
        return f"{activity.code} — {activity.title}" if activity.code else activity.title

    def render(self, name, value, attrs=None, renderer=None):
        hidden_html = super().render(name, value, attrs, renderer)
        label = self._label_for(value)
        search_url = reverse_lazy(self.search_url_name)

        create_attr = format_html(' data-create-url="{}"', self.create_url) if self.create_url else ""
        label_class = "" if label else " muted"

        return format_html(
            '<div class="person-picker" data-person-picker data-search-url="{search_url}"'
            ' data-create-label="Criar nova atividade"{create_attr}>'
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
            label=label or "Selecionar atividade",
        )


class RichTextWidget(forms.Textarea):
    """Editor de descrição com formatação básica (negrito/itálico/sublinhado/
    lista/link) sobre `contenteditable` nativo do navegador — sem editor
    colaborativo nem versionado, só o suficiente para ser mais legível que
    texto puro. O `<textarea>` real fica escondido mas continua sendo o que
    o form de fato submete (funciona sem JS); `static/js/rich-text.js`
    sincroniza seu conteúdo com a área editável visível.

    O valor aqui é renderizado com `mark_safe` porque já passou por
    `core.sanitize.sanitize_description()` no momento de salvar — nunca usar
    este widget para exibir um campo que não passa por aquela sanitização.
    """

    def __init__(self, attrs=None):
        attrs = {**(attrs or {}), "hidden": True}
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        textarea_html = super().render(name, value, attrs, renderer)
        body_html = mark_safe(value) if value else ""

        return format_html(
            '<div class="rich-text" data-rich-text>'
            '<div class="rich-text__toolbar">'
            '<button type="button" class="rich-text__btn" data-command="bold" title="Negrito"><strong>B</strong></button>'
            '<button type="button" class="rich-text__btn" data-command="italic" title="Itálico"><em>I</em></button>'
            '<button type="button" class="rich-text__btn" data-command="underline" title="Sublinhado"><u>S</u></button>'
            '<button type="button" class="rich-text__btn" data-command="insertUnorderedList" title="Lista">&bull;</button>'
            '<button type="button" class="rich-text__btn" data-command="createLink" title="Link">&#128279;</button>'
            "</div>"
            '<div class="rich-text__body" contenteditable="true">{body_html}</div>'
            "{textarea_html}"
            "</div>",
            body_html=body_html,
            textarea_html=textarea_html,
        )


class TagPickerWidget(forms.SelectMultiple):
    """Seletor de marcadores (M2M) com busca e chips removíveis — variante de
    múltipla escolha dos pickers de valor único acima (PersonPickerWidget
    etc). O `<select multiple>` real fica escondido mas funcional (a tela
    continua operando sem JS); `static/js/tag-picker.js` o substitui
    visualmente por chips coloridos + popup de busca, reaproveitando a mesma
    API `{"results": [...]}` do `search_url`.
    """

    search_url_name = "tag-search"

    def __init__(self, attrs=None, queryset=None):
        attrs = {**(attrs or {}), "hidden": True}
        super().__init__(attrs)
        self.queryset = queryset

    def _selected_options(self, value):
        if not value or self.queryset is None:
            return []
        ids = [v for v in value if v not in (None, "")]
        if not ids:
            return []
        return list(self.queryset.filter(pk__in=ids))

    def render(self, name, value, attrs=None, renderer=None):
        select_html = super().render(name, value, attrs, renderer)
        search_url = reverse_lazy(self.search_url_name)
        selected = self._selected_options(value)
        chips = format_html_join(
            "",
            '<span class="tag-picker__chip tag-chip tag-chip--{}" data-tag-id="{}">{}'
            '<button type="button" class="tag-picker__remove" aria-label="Remover">&times;</button></span>',
            ((tag.color, tag.pk, tag.name) for tag in selected),
        )

        return format_html(
            '<div class="tag-picker" data-tag-picker data-search-url="{search_url}">'
            '{select_html}'
            '<div class="tag-picker__chips">{chips}'
            '<button type="button" class="tag-picker__add">'
            '<span class="tag-picker__add-icon">{icon}</span> Adicionar marcador'
            "</button>"
            "</div>"
            "</div>",
            search_url=search_url,
            select_html=select_html,
            chips=chips,
            icon=_SEARCH_ICON,
        )
