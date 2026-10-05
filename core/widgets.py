from django import forms
from django.urls import reverse_lazy
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe


class VisibleHiddenInput(forms.HiddenInput):
    """Guarda o valor num `<input type="hidden">`, mas o controle que a pessoa
    vê e usa (busca, lista, botão) é desenhado pelo widget.

    O Django trata todo widget "hidden" como campo sem rótulo: `hidden_fields()`
    o separa dos demais e os parciais de formulário (`_form_field.html`) pulam o
    rótulo e o texto de ajuda. Para os seletores isso significava tela sem
    rótulo e, onde havia um laço de `hidden_fields`, o seletor desenhado duas
    vezes. `is_hidden = False` faz o campo ser tratado como visível.
    """

    is_hidden = False

    #: nome do símbolo do sprite (`#i-<nome>`) desenhado no botão; `None` = lupa.
    icon = None

    def _icon(self):
        return sprite_icon(self.icon) if self.icon else _SEARCH_ICON


def sprite_icon(name):
    """Ícone do sprite de `templates/_icons.html`, para widgets que montam o HTML à mão."""
    return format_html(
        '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><use href="#i-{}"></use></svg>', name
    )


class PersonPickerWidget(VisibleHiddenInput):
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

    def __init__(
        self, attrs=None, create_url=None, queryset=None, sector_field_id=None, placeholder=None, selection_label=None,
        icon=None,
    ):
        super().__init__(attrs)
        self.icon = icon
        self.create_url = create_url
        self.queryset = queryset
        self.sector_field_id = sector_field_id
        self.placeholder = placeholder or "Buscar pessoa..."
        self.selection_label = selection_label or "Selecionar pessoa"

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
        sector_attr = format_html(' data-sector-field="{}"', self.sector_field_id) if self.sector_field_id else ""
        label_class = "" if label else " muted"

        return format_html(
            '<div class="person-picker" data-person-picker data-search-url="{search_url}"{create_attr}{sector_attr} data-placeholder="{placeholder}" data-empty-label="{empty_label}">'
            '{hidden_html}'
            '<button type="button" class="person-picker__trigger" aria-haspopup="listbox" aria-expanded="false">'
            '<span class="person-picker__icon">{icon}</span>'
            '<span class="person-picker__label{label_class}">{label}</span>'
            "</button>"
            "</div>",
            search_url=search_url,
            create_attr=create_attr,
            sector_attr=sector_attr,
            placeholder=self.placeholder,
            empty_label=self.selection_label,
            hidden_html=hidden_html,
            icon=self._icon(),
            label_class=label_class,
            label=label or self.selection_label,
        )


_SEARCH_ICON = format_html(
    '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><use href="#i-search"></use></svg>'
)


class ClientPickerWidget(VisibleHiddenInput):
    """Seletor de cliente com busca (Regras 1-2 da tela de atividade).

    Mesmo padrão do `PersonPickerWidget` — digitar filtra, "Cadastra cliente"
    cria sem sair da tela — mas aponta para o cadastro de clientes em vez de
    usuários. Reaproveita as classes `.person-picker*` do design system: o
    JS (`static/js/person-picker.js`) já é genérico o bastante para servir os
    dois, e diferencia só o rótulo do botão de criação via `data-create-label`.
    """

    search_url_name = "client-search"

    def __init__(self, attrs=None, create_url=None, queryset=None, icon=None):
        super().__init__(attrs)
        self.icon = icon
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
            ' data-create-label="Cadastrar cliente" data-placeholder="Buscar cliente..."'
            ' data-empty-label="Selecionar cliente"{create_attr}>'
            '{hidden_html}'
            '<button type="button" class="person-picker__trigger" aria-haspopup="listbox" aria-expanded="false">'
            '<span class="person-picker__icon">{icon}</span>'
            '<span class="person-picker__label{label_class}">{label}</span>'
            "</button>"
            "</div>",
            search_url=search_url,
            create_attr=create_attr,
            hidden_html=hidden_html,
            icon=self._icon(),
            label_class=label_class,
            label=label or "Selecionar cliente",
        )


class ActivityPickerWidget(VisibleHiddenInput):
    """Seletor de atividade com busca, para o fluxo "+ Nova tarefa" fora do
    contexto de uma atividade já aberta: toda tarefa continua pertencendo a
    uma atividade, mas a pessoa escolhe/cria a atividade sem sair do popup.
    Mesmo padrão de `ClientPickerWidget` — busca e criação rápida via
    `static/js/person-picker.js`, já genérico o bastante para os dois.
    """

    search_url_name = "activity-search"

    def __init__(self, attrs=None, create_url=None, queryset=None, icon=None):
        super().__init__(attrs)
        self.icon = icon
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
            ' data-create-label="Criar nova demanda"{create_attr}>'
            '{hidden_html}'
            '<button type="button" class="person-picker__trigger" aria-haspopup="listbox" aria-expanded="false">'
            '<span class="person-picker__icon">{icon}</span>'
            '<span class="person-picker__label{label_class}">{label}</span>'
            "</button>"
            "</div>",
            search_url=search_url,
            create_attr=create_attr,
            hidden_html=hidden_html,
            icon=self._icon(),
            label_class=label_class,
            label=label or "Selecionar demanda",
        )


class _SimpleSearchPickerWidget(VisibleHiddenInput):
    """Base para pickers "busca por nome" simples (Setor/Empresa/Obra/Centro
    de custo): mesmo padrão de `ClientPickerWidget`, só troca o endpoint de
    busca e os textos. Subclasses só declaram `search_url_name`,
    `create_label`, `empty_label` e `placeholder`."""

    search_url_name = None
    picker_kind = ""
    create_label = "Cadastrar"
    empty_label = "Selecionar"
    placeholder = "Buscar..."

    def __init__(
        self, attrs=None, create_url=None, queryset=None, icon=None, empty_label=None, placeholder=None,
        filter_field_id=None, filter_param=None,
    ):
        super().__init__(attrs)
        self.create_url = create_url
        self.queryset = queryset
        self.icon = icon
        if empty_label:
            self.empty_label = empty_label
        if placeholder:
            self.placeholder = placeholder
        # Quando `filter_field_id` é informado (ex.: obra depende do cliente), o
        # JS zera a escolha ao mudar o outro campo e manda o valor dele na busca
        # como `filter_param` (ver static/js/person-picker.js).
        self.filter_field_id = filter_field_id
        self.filter_param = filter_param

    def _label_for(self, value):
        if not value or self.queryset is None:
            return ""
        try:
            obj = self.queryset.get(pk=value)
        except (self.queryset.model.DoesNotExist, ValueError, TypeError):
            return ""
        return str(obj)

    def render(self, name, value, attrs=None, renderer=None):
        hidden_html = super().render(name, value, attrs, renderer)
        label = self._label_for(value)
        search_url = reverse_lazy(self.search_url_name)
        selected_color = ""
        selected_text_color = ""
        if value and self.queryset is not None and self.picker_kind == "sector":
            try:
                selected = self.queryset.get(pk=value)
                selected_color = getattr(selected, "color", "")
                selected_text_color = getattr(selected, "text_color", "")
            except (self.queryset.model.DoesNotExist, ValueError, TypeError):
                pass

        create_attr = format_html(' data-create-url="{}"', self.create_url) if self.create_url else mark_safe("")
        if self.filter_field_id and self.filter_param:
            create_attr = format_html(
                '{} data-filter-field="{}" data-filter-param="{}"', create_attr, self.filter_field_id, self.filter_param
            )
        label_class = "" if label else " muted"

        return format_html(
            '<div class="person-picker{if_kind}" data-person-picker data-picker-kind="{picker_kind}" data-search-url="{search_url}"'
            ' data-create-label="{create_label}" data-placeholder="{placeholder}"'
            ' data-empty-label="{empty_label}" data-selected-color="{selected_color}"'
            ' data-selected-text-color="{selected_text_color}"{create_attr}>'
            "{hidden_html}"
            '<button type="button" class="person-picker__trigger" aria-haspopup="listbox" aria-expanded="false">'
            '<span class="person-picker__icon">{icon}</span>'
            '<span class="person-picker__label{label_class}">{label}</span>'
            "</button>"
            "</div>",
            search_url=search_url,
            if_kind=" sector-picker" if self.picker_kind == "sector" else "",
            picker_kind=self.picker_kind,
            create_label=self.create_label,
            placeholder=self.placeholder,
            empty_label=self.empty_label,
            create_attr=create_attr,
            hidden_html=hidden_html,
            icon=self._icon(),
            label_class=label_class,
            label=label or self.empty_label,
            selected_color=selected_color,
            selected_text_color=selected_text_color,
        )


class SectorPickerWidget(_SimpleSearchPickerWidget):
    """Seletor de setor com busca, mesmo padrão do `ClientPickerWidget`."""

    search_url_name = "sector-search"
    picker_kind = "sector"
    create_label = "Cadastrar setor"
    empty_label = "Selecionar setor"
    placeholder = "Buscar setor..."


class SectorCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Checkboxes múltiplos de setores com a amostra da cor atual.

    O queryset é resolvido uma única vez por renderização do widget; a cor
    continua vindo do próprio setor e não cria consultas por opção.
    """

    def _sector_map(self):
        if hasattr(self, "_cached_sector_map"):
            return self._cached_sector_map
        queryset = getattr(self.choices, "queryset", None)
        if queryset is None:
            self._cached_sector_map = {}
        else:
            self._cached_sector_map = {str(item.pk): item for item in queryset}
        return self._cached_sector_map

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        sector = self._sector_map().get(str(value))
        if sector:
            option["label"] = format_html(
                '<span class="sector-checkbox__swatch" style="--sector-color: {};" aria-hidden="true"></span><span>{}</span>',
                sector.color,
                sector.name,
            )
            option["attrs"]["title"] = sector.name
        return option


class CompanyPickerWidget(_SimpleSearchPickerWidget):
    """Seletor de empresa com busca, mesmo padrão do `ClientPickerWidget`."""

    search_url_name = "company-search"
    create_label = "Cadastrar empresa"
    empty_label = "Selecionar empresa"
    placeholder = "Buscar empresa..."


class SitePickerWidget(_SimpleSearchPickerWidget):
    """Seletor de obra com busca, mesmo padrão do `ClientPickerWidget`."""

    search_url_name = "site-search"
    create_label = "Cadastrar obra"
    empty_label = "Selecionar obra"
    placeholder = "Buscar obra..."


class CostCenterPickerWidget(_SimpleSearchPickerWidget):
    """Seletor de centro de custo com busca, mesmo padrão do `ClientPickerWidget`."""

    search_url_name = "costcenter-search"
    create_label = "Cadastrar centro de custo"
    empty_label = "Selecionar centro de custo"
    placeholder = "Buscar centro de custo..."


class ColorPaletteWidget(forms.HiddenInput):
    """Escolha de cor via grade de 36 cores (popover), no lugar de um
    <select> de cores ou de <input type="color">.

    O <input hidden> continua sendo o valor real submetido; o swatch visível
    ao lado é só a apresentação. static/js/color-palette-picker.js abre o
    popover e escreve o hex escolhido diretamente no input escondido — não
    dispara nenhuma requisição neste modo (é usado dentro de um form
    tradicional, que quem submete é o próprio form).
    """

    def render(self, name, value, attrs=None, renderer=None):
        hidden_html = super().render(name, value, attrs, renderer)
        color = value or "#94A3B8"
        return format_html(
            '<div class="color-palette-field">'
            "{hidden_html}"
            '<button type="button" class="color-swatch color-swatch--form" '
            'data-color-swatch style="--swatch-color: {color};" '
            'data-current-color="{color}" aria-haspopup="true" '
            'aria-label="Escolher cor"></button>'
            "</div>",
            hidden_html=hidden_html,
            color=color,
        )


class RichTextWidget(forms.Textarea):
    """Editor de descrição com formatação básica (negrito/itálico/tachado/
    listas/link) sobre `contenteditable` nativo do navegador — sem editor
    colaborativo nem versionado, só o suficiente para ser mais legível que
    texto puro. O `<textarea>` real fica escondido mas continua sendo o que
    o form de fato submete (funciona sem JS); `static/js/rich-text.js`
    sincroniza seu conteúdo com a área editável visível.

    `placeholder` aparece enquanto o editor está vazio e `limit` mostra o
    contador "0/2000" (só orientação: o servidor não corta o texto).

    O valor aqui é renderizado com `mark_safe` porque já passou por
    `core.sanitize.sanitize_description()` no momento de salvar — nunca usar
    este widget para exibir um campo que não passa por aquela sanitização.
    """

    def __init__(self, attrs=None, placeholder="", limit=None):
        attrs = {**(attrs or {}), "hidden": True}
        super().__init__(attrs)
        self.placeholder = placeholder
        self.limit = limit

    def render(self, name, value, attrs=None, renderer=None):
        textarea_html = super().render(name, value, attrs, renderer)
        body_html = mark_safe(value) if value else ""
        counter_html = (
            format_html(
                '<div class="rich-text__counter" data-rich-text-counter data-limit="{limit}">0/{limit}</div>',
                limit=self.limit,
            )
            if self.limit
            else ""
        )

        return format_html(
            '<div class="rich-text" data-rich-text>'
            '<div class="rich-text__toolbar">'
            '<button type="button" class="rich-text__btn" data-command="bold" title="Negrito" aria-label="Negrito"><strong>B</strong></button>'
            '<button type="button" class="rich-text__btn" data-command="italic" title="Itálico" aria-label="Itálico"><em>I</em></button>'
            '<button type="button" class="rich-text__btn" data-command="strikeThrough" title="Tachado" aria-label="Tachado"><s>S</s></button>'
            '<span class="rich-text__sep" aria-hidden="true"></span>'
            '<button type="button" class="rich-text__btn" data-command="insertUnorderedList" title="Lista com marcadores" aria-label="Lista com marcadores">{ul_icon}</button>'
            '<button type="button" class="rich-text__btn" data-command="insertOrderedList" title="Lista numerada" aria-label="Lista numerada">{ol_icon}</button>'
            '<span class="rich-text__sep" aria-hidden="true"></span>'
            '<button type="button" class="rich-text__btn" data-command="createLink" title="Link" aria-label="Link">{link_icon}</button>'
            "</div>"
            '<div class="rich-text__body" contenteditable="true" role="textbox" aria-multiline="true" '
            'data-placeholder="{placeholder}" data-mention data-mention-search-url="{search_url}">{body_html}</div>'
            "{counter_html}"
            "{textarea_html}"
            "</div>",
            ul_icon=sprite_icon("list-ul"),
            ol_icon=sprite_icon("list-ol"),
            link_icon=sprite_icon("link"),
            placeholder=self.placeholder,
            body_html=body_html,
            counter_html=counter_html,
            textarea_html=textarea_html,
            search_url=reverse_lazy("person-search"),
        )


class PersonMultiPickerWidget(forms.SelectMultiple):
    """Seletor de múltiplas pessoas (M2M) com busca e chips removíveis —
    mesmo padrão estrutural de `TagPickerWidget`, mas para pessoas: reaproveita
    o endpoint `person-search` (mesmo do `PersonPickerWidget`, sem view nova)
    e mostra avatar+nome no lugar de cor+nome. O `<select multiple>` real
    fica escondido mas funcional; `static/js/person-multi-picker.js` o
    substitui visualmente por chips + popup de busca.
    """

    search_url_name = "person-search"

    def __init__(self, attrs=None, queryset=None, create_url=None):
        attrs = {**(attrs or {}), "hidden": True}
        super().__init__(attrs)
        self.queryset = queryset
        self.create_url = create_url

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
        create_attr = format_html(' data-create-url="{}"', self.create_url) if self.create_url else ""
        chips = format_html_join(
            "",
            '<span class="person-multi-picker__chip" data-person-id="{}">'
            '<span class="avatar avatar--{}">{}</span>{}'
            '<button type="button" class="person-multi-picker__remove" aria-label="Remover">&times;</button></span>',
            (
                (
                    person.pk,
                    person.pk % 6,
                    (person.get_full_name() or person.get_username())[:2].upper(),
                    person.get_full_name() or person.get_username(),
                )
                for person in selected
            ),
        )

        return format_html(
            '<div class="person-multi-picker" data-person-multi-picker data-search-url="{search_url}"'
            ' data-create-label="Cadastrar novo usuário"{create_attr}>'
            '{select_html}'
            '<div class="person-multi-picker__chips">{chips}'
            '<button type="button" class="person-multi-picker__add">'
            '<span class="person-multi-picker__add-icon">{icon}</span> Adicionar participante'
            "</button>"
            "</div>"
            "</div>",
            search_url=search_url,
            create_attr=create_attr,
            select_html=select_html,
            chips=chips,
            icon=_SEARCH_ICON,
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
            '<span class="tag-picker__chip tag-chip" data-tag-id="{}" '
            'style="--tag-bg: {}1A; --tag-fg: {};">{}'
            '<button type="button" class="tag-picker__remove" aria-label="Remover">&times;</button></span>',
            ((tag.pk, tag.color, tag.color, tag.name) for tag in selected),
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
