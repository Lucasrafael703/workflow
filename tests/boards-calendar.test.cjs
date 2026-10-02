/* Visualização Calendário dos quadros (static/js/boards.js, modo Calendário).
   Requires jsdom@26.1.0 in NODE_PATH; no browser or production dependency.
   Run from workflow: node --test tests/boards-calendar.test.cjs
   Set PYTHON to the project's Python if it is not in .venv.

   O HTML vem dos templates Django reais (boards/board_calendar.html e parciais) renderizados com objetos em memória,
   sem banco, e a grade montada por `boards.calendar_view.build_month` (a mesma função da tela). O servidor é simulado
   por um `fetch` falso: o contrato testado é "o que a tela manda" e "o que ela faz com a resposta".
   Referência fixa: hoje = 10/10/2026; outubro de 2026 vai de segunda 28/09 a domingo 01/11. */
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync, existsSync} = require("node:fs");
const {execFileSync} = require("node:child_process");
const path = require("node:path");
const {JSDOM} = require("jsdom");

const root = path.resolve(__dirname, "..");
const localPython = path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const python = process.env.PYTHON || (existsSync(localPython) ? localPython : "python");

const PYTHON_FIXTURE = `
import os, re, json, datetime
from decimal import Decimal
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.utils import timezone
from boards.models import Board, BoardColumn, BoardColumnOption, BoardItem, BoardCell, BoardView, BoardGroup
from boards.calendar_view import (
    build_month, clean_calendar_settings, resolve_card_columns, resolve_color_source, resolve_date_column, resolve_status_column,
)
from boards.presentation import board_urls, type_catalog, type_icon, COLOR_PALETTE, SENTINEL, SENTINEL_COLUMN

permissions = json.loads(os.environ.get('BOARD_PERMISSIONS') or 'null') or {
    'view': True, 'edit': True, 'delete': True, 'manage_columns': True,
    'create_item': True, 'edit_item': True, 'delete_item': True,
}
variant = os.environ.get('VARIANT', '')
User = get_user_model()
board = Board(pk=1, name='Orçamentos', item_label='Obra')
ana = User(pk=7, username='ana', first_name='Ana', last_name='Souza')

def col(pk, name, kind, **extra):
    return BoardColumn(pk=pk, board=board, board_id=1, name=name, type=kind, width=160, **extra)

columns = [
    col(11, 'Cliente', 'TEXT'),
    col(12, 'Responsável', 'PERSON'),
    col(13, 'Status', 'STATUS'),
    col(14, 'Prazo', 'DATE', settings={'is_deadline': True, 'show_time': True, 'allow_weekends': False}),
    col(15, 'Valor', 'CURRENCY'),
    col(16, 'Probabilidade', 'NUMBER', settings={'decimal_places': 0, 'unit': '%'}),
    col(17, 'Visto', 'CHECKBOX'),
    col(18, 'Setor', 'DROPDOWN'),
]
if variant == 'nodate':
    columns = [c for c in columns if c.pk != 14]
by_id = {c.pk: c for c in columns}
options = {
    13: [(1, 'Novo', '#C4C4C4', True, False), (2, 'Levantamento', '#66CCFF', False, False), (3, 'Ganho', '#00C875', False, True)],
    18: [(4, 'Comercial', '#00C875', False, False), (5, 'Engenharia', '#A25DDC', False, False)],
}
opt_objs = {oid: BoardColumnOption(pk=oid, column=by_id[cid], column_id=cid, label=l, color=c, position=oid, is_default=d, is_done=n)
            for cid, rows in options.items() for (oid, l, c, d, n) in rows}

group = BoardGroup(pk=1, board=board, name='Oportunidades', color='#579BFC')

def make_item(pk, name, values):
    item = BoardItem(pk=pk, board=board, group=group, group_id=1, name=name)
    item.cell_map = {}
    for column_id, value in values.items():
        column = by_id.get(column_id)
        if column is None:
            continue
        cell = BoardCell(item=item, column=column)
        cell.option = None; cell.person = None; cell.display = ''
        if column.type == 'TEXT':
            cell.value_text = value; cell.display = value
        elif column.type == 'PERSON':
            cell.person = ana; cell.display = 'Ana Souza'
        elif column.type in ('STATUS', 'DROPDOWN'):
            cell.option = opt_objs[value]; cell.display = cell.option.label
        elif column.type == 'DATE':
            if isinstance(value, datetime.datetime):
                cell.value_datetime = timezone.make_aware(value); cell.value_date = value.date()
            else:
                cell.value_date = value
            cell.display = cell.value_date.strftime('%d/%m/%Y')
        item.cell_map[column_id] = cell
    return item

d = datetime.date
items = [
    make_item(101, 'Arena Norte', {11: 'Shopping Norte', 12: 'x', 13: 2, 14: d(2026, 10, 15)}),
    make_item(102, 'Condomínio Cotia', {11: 'Residencial Cotia', 13: 1, 14: datetime.datetime(2026, 10, 15, 14, 0)}),
    make_item(103, 'Hospital Vida', {13: 3, 14: d(2026, 10, 20)}),
    make_item(104, 'Item sem data', {11: 'Sem data', 13: 1}),
    make_item(105, 'Contrato atrasado', {13: 2, 14: d(2026, 9, 30)}),
] + [make_item(200 + n, 'Extra %d' % n, {13: 1, 14: d(2026, 10, 27)}) for n in range(1, 6)]
if variant == 'weekend':
    items.append(make_item(300, 'No sábado', {13: 1, 14: d(2026, 10, 17)}))

show_weekends = variant != 'weekend'
settings = clean_calendar_settings(columns, {'date_field': 14 if variant != 'nodate' else None, 'color_by': 13, 'card_fields': [13, 12, 11], 'show_weekends': show_weekends})
date_column = resolve_date_column(settings, columns)
color_kind, color_column = resolve_color_source(settings, columns)
card_columns = resolve_card_columns(settings, columns, date_column, color_column)
dated = [i for i in items if i.cell_map.get(14) is not None]
calendar = None
if date_column is not None:
    calendar = build_month(
        2026, 10, dated, date_column=date_column, status_column=by_id[13], color_kind=color_kind, color_column=color_column,
        card_columns=card_columns, show_weekends=show_weekends, today=d(2026, 10, 10),
    )
overdue_item = items[4]
overdue_item.due_date = d(2026, 9, 30)

view = BoardView(pk=5, board=board, name='Calendário', type='CALENDAR')
kanban_view = BoardView(pk=6, board=board, name='Kanban', type='KANBAN')

meta_columns = []
for c in columns:
    meta_columns.append({
        'id': c.pk, 'name': c.name, 'type': c.type, 'type_label': c.get_type_display(), 'icon': type_icon(c.type),
        'width': c.width, 'description': '', 'is_required': False, 'is_visible': True,
        'settings': ({'show_time': False, 'allow_weekends': True, 'is_deadline': False, 'format': 'DD/MM/YYYY', **(c.settings or {})} if c.type == 'DATE' else (c.settings or {})),
        'options': [{'id': o[0], 'label': o[1], 'color': o[2], 'is_default': o[3], 'is_done': o[4]} for o in options.get(c.pk, [])],
    })
meta = {
    'board': {'id': 1, 'name': board.name, 'item_label': board.item_label},
    'permissions': permissions, 'urls': board_urls(board),
    'sentinels': {'id': SENTINEL, 'column': SENTINEL_COLUMN}, 'types': type_catalog(), 'columns': meta_columns,
    'groups': [{'id': 1, 'name': 'Oportunidades', 'color': '#579BFC'}],
    'sort': {'column': None, 'dir': 'asc'}, 'limits': {'min_width': 96, 'max_width': 640}, 'palette': COLOR_PALETTE,
    'calendar': {
        'view': {'id': 5, 'name': view.name}, 'settings': settings,
        'date_column_id': date_column.pk if date_column else None, 'status_column_id': 13,
        'color_kind': color_kind, 'color_column_id': color_column.pk if color_column else None,
        'card_column_ids': [c.pk for c in card_columns],
        'dateable_ids': [c.pk for c in columns if c.type == 'DATE'], 'colorable_ids': [13, 18],
        'month': '2026-10', 'today': '2026-10-10', 'max_visible': 3, 'max_card_fields': 6, 'recommended_card_fields': 3,
        'default_group_id': 1,
    },
}

source = open(os.path.join('templates', 'boards', 'board_calendar.html'), encoding='utf-8').read()
body = re.search(r'{% block content %}(.*){% endblock %}\\s*{% block scripts %}', source, re.S).group(1)
context = Context({
    'board': board, 'view': view, 'views': [kanban_view, view], 'active_view': view, 'permissions': permissions,
    'search': '', 'person_id': None, 'people': [ana], 'filtering': False, 'keep_query': '',
    'month_key': '2026-10', 'month_title': 'outubro 2026', 'prev_month': '2026-09', 'next_month': '2026-11', 'today_month': '2026-10',
    'calendar': calendar, 'date_column': date_column, 'settings': settings, 'has_deadline': True,
    'nodate_items': [items[3]] if date_column else [], 'nodate_count': 1 if date_column else 0, 'nodate_more': 0,
    'overdue_items': [overdue_item] if date_column else [], 'overdue_count': 1 if date_column else 0, 'overdue_more': 0,
    'max_visible': 3, 'meta': meta,
})
print(json.dumps({'html': Template('{% load static lps_board %}' + body).render(context), 'meta': meta}))
`;

function renderFixture({permissions, variant} = {}) {
    const env = {...process.env};
    if (permissions) env.BOARD_PERMISSIONS = JSON.stringify(permissions);
    if (variant) env.VARIANT = variant;
    return JSON.parse(execFileSync(python, ["-c", PYTHON_FIXTURE], {cwd: root, encoding: "utf8", env}).trim());
}

const FULL = renderFixture();
const EDITOR = renderFixture({permissions: {view: true, edit: false, delete: false, manage_columns: false, create_item: true, edit_item: true, delete_item: false}});
const VIEWER = renderFixture({permissions: {view: true, edit: false, delete: false, manage_columns: false, create_item: false, edit_item: false, delete_item: false}});
const NODATE = renderFixture({variant: "nodate"});
const WEEKEND = renderFixture({variant: "weekend"});
const script = readFileSync(path.join(root, "static/js/boards.js"), "utf8");
const tick = () => new Promise(resolve => setImmediate(resolve));
const flush = async () => { for (let i = 0; i < 12; i += 1) await tick(); };

function jsonResponse(body, status = 200) {
    return Promise.resolve({ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body)});
}

const CALENDAR_SETTINGS = FULL.meta.calendar.settings;

// O que o servidor devolve ao pedir o corpo do calendário: uma versão simplificada, com o cartão 101 no dia 16.
const BODY_HTML = (month = "2026-11") => `
<div class="cal-grid" data-cal-grid data-month="${month}">
  <div class="cal-day" data-cal-day data-date="${month}-16"><div data-cal-items>
    <article class="cal-card" data-cal-card data-item-id="101" data-date="${month}-16" data-time="" draggable="true"><span class="cal-card__title">Arena Norte</span></article>
  </div></div>
</div>`;

function calendarPayload(overrides = {}) {
    return {
        ok: true, body_html: BODY_HTML(), title: "novembro 2026", month: "2026-11", prev: "2026-10", next: "2026-12", today: "2026-10",
        columns: FULL.meta.columns, settings: CALENDAR_SETTINGS, date_column_id: 14, color_kind: "column", color_column_id: 13,
        card_column_ids: [13, 12, 11], dateable_ids: [14], colorable_ids: [13, 18], ...overrides,
    };
}

// A gaveta como o servidor a desenha (resumida): título, um Status e uma Data com hora.
const DRAWER_HTML = (itemId = 101, dateValue = "2026-10-15") => `
<div class="board-drawer__panel" data-drawer data-item-id="${itemId}" tabindex="-1">
  <header><span data-drawer-title class="board-drawer__title" tabindex="0" role="textbox">Arena Norte</span><button type="button" data-drawer-close>×</button></header>
  <dl>
    <div><dd class="board-drawer__value is-editable" data-cell data-item-id="${itemId}" data-column-id="13" data-type="STATUS" data-value="2" tabindex="0"><span class="board-pill">Levantamento</span></dd></div>
    <div><dd class="board-drawer__value is-editable" data-cell data-item-id="${itemId}" data-column-id="14" data-type="DATE" data-value="${dateValue}" tabindex="0">15/10/2026</dd></div>
  </dl>
  <footer><button type="button" data-drawer-delete>Excluir item</button></footer>
</div>`;

function defaultRespond(call) {
    const u = call.url;
    if (u.startsWith("/api/pessoas/")) return jsonResponse({results: [{id: 7, name: "Ana Souza", username: "ana"}, {id: 8, name: "Bruno Lima", username: "bruno"}]});
    if (u.endsWith("/calendario/")) return jsonResponse(calendarPayload());
    if (u.endsWith("/detalhe/")) return jsonResponse({ok: true, drawer_html: DRAWER_HTML(Number(u.match(/itens\/(\d+)\//)[1]))});
    if (u.endsWith("/itens/novo/")) return jsonResponse({ok: true, item: {id: 300, group_id: 1, name: call.body.name}, row_html: ""});
    if (u.endsWith("/valor/")) return jsonResponse({ok: true, display: "", cell_html: "<td></td>"});
    if (u.endsWith("/editar/")) return jsonResponse({ok: true, view: {id: 5, name: "Calendário"}, settings: {...CALENDAR_SETTINGS, ...((call.body && call.body.settings) || {})}});
    return jsonResponse({ok: true});
}

function setup(t, {fixture = FULL, respond, url = "http://localhost/quadros/visoes/5/?mes=2026-10", tweak} = {}) {
    const dom = new JSDOM("<!doctype html><body>" + fixture.html + "</body>", {url, runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => dom.window.close());
    const w = dom.window;
    if (tweak) {
        const node = w.document.getElementById("board-meta");
        const meta = JSON.parse(node.textContent);
        tweak(meta);
        node.textContent = JSON.stringify(meta);
    }
    const calls = [];
    w.fetch = (target, options = {}) => {
        const call = {url: target, method: options.method || "GET", headers: options.headers || {}, body: options.body ? JSON.parse(options.body) : null};
        calls.push(call);
        return (respond && respond(call)) || defaultRespond(call);
    };
    const timers = [];
    let timerId = 0;
    w.setTimeout = (fn, ms) => { timerId += 1; timers.push({id: timerId, fn, ms}); return timerId; };
    w.clearTimeout = id => { const index = timers.findIndex(timer => timer.id === id); if (index >= 0) timers.splice(index, 1); };
    w.eval(script);
    if (!w.LPSBoards.instance) w.LPSBoards.boot();
    const $ = selector => w.document.querySelector(selector);
    const $$ = selector => Array.from(w.document.querySelectorAll(selector));
    const click = (element, init = {}) => {
        const event = new w.MouseEvent("click", {bubbles: true, cancelable: true, button: 0, ...init});
        element.dispatchEvent(event);
        return event;
    };
    const key = (element, keyName, init = {}) => {
        const event = new w.KeyboardEvent("keydown", {key: keyName, bubbles: true, cancelable: true, ...init});
        element.dispatchEvent(event);
        return event;
    };
    const day = iso => $(`[data-cal-day][data-date="${iso}"]`);
    const card = id => $(`[data-cal-card][data-item-id="${id}"]`);
    const button = label => $$(".board-dialog .btn").find(node => node.textContent === label);
    const to = fragment => calls.filter(call => call.url.includes(fragment));
    const runTimers = () => { while (timers.length) timers.shift().fn(); };
    const drag = (type, init = {}) => {
        const event = new w.MouseEvent(type, {bubbles: true, cancelable: true, ...init});
        event.dataTransfer = {setData() {}, setDragImage() {}, effectAllowed: ""};
        return event;
    };
    const toasts = () => $$(".board-toast").map(node => node.textContent);
    return {w, $, $$, click, key, day, card, button, calls, to, runTimers, drag, toasts};
}

// ---------------------------------------------------------------------------------------------------
// Funções puras
// ---------------------------------------------------------------------------------------------------

test("helpers: parseTimeInput, splitDateValue and composeDateValue", t => {
    const {w} = setup(t);
    const h = w.LPSBoards.helpers;
    for (const [input, expected] of [["14:30", "14:30"], ["9:05", "09:05"], ["0930", "09:30"], ["14h", "14:00"], ["14h30", "14:30"], ["9", "09:00"], [" 08:00 ", "08:00"], ["00:00", "00:00"]]) {
        assert.equal(h.parseTimeInput(input), expected, input);
    }
    for (const bad of ["", "24:00", "12:60", "99", "abc", "9:5", "12:3", "1:2:3", null, undefined]) {
        assert.equal(h.parseTimeInput(bad), null, String(bad));
    }
    assert.deepEqual(JSON.parse(JSON.stringify(h.splitDateValue("2026-10-15T14:00"))), {date: "2026-10-15", time: "14:00"});
    assert.deepEqual(JSON.parse(JSON.stringify(h.splitDateValue("2026-10-15"))), {date: "2026-10-15", time: ""});
    assert.deepEqual(JSON.parse(JSON.stringify(h.splitDateValue(""))), {date: "", time: ""});
    assert.equal(h.composeDateValue("2026-10-15", "14:00"), "2026-10-15T14:00");
    assert.equal(h.composeDateValue("2026-10-15", ""), "2026-10-15"); // sem hora: nunca se inventa 00:00
    assert.equal(h.composeDateValue("", "14:00"), "");
});

// ---------------------------------------------------------------------------------------------------
// Estrutura
// ---------------------------------------------------------------------------------------------------

test("boot: five weeks, cards on their days, time on timed cards, today marked, no table needed", t => {
    const {$$, $, day, card} = setup(t);
    assert.equal($$("[data-cal-day]").length, 35);
    assert.equal($$(".cal-weekday").length, 7);
    assert.deepEqual($$("[data-cal-card]").filter(node => node.dataset.date === "2026-10-15").map(node => node.dataset.itemId), ["101", "102"]); // sem hora primeiro
    assert.equal(card(102).querySelector(".cal-card__time").textContent, "14:00");
    assert.equal(card(101).querySelector(".cal-card__time"), null); // dia inteiro: sem hora inventada
    assert.ok(day("2026-10-10").classList.contains("is-today"));
    assert.equal($$(".is-today").length, 1);
    assert.ok(day("2026-09-28").classList.contains("is-outside"));
    assert.equal(card(103).dataset.date, "2026-10-20");
    assert.equal($(".cal-title").textContent, "outubro 2026");
});

test("cards: color from the Status option, the label is written, only filled fields, overdue says so", t => {
    const {card, $$} = setup(t);
    assert.equal(card(101).style.getPropertyValue("--card-color"), "#66CCFF");
    assert.match(card(101).textContent, /Levantamento/);
    assert.match(card(101).textContent, /Status: Levantamento/); // texto para leitor de tela: não é só cor
    assert.deepEqual(Array.from(card(101).querySelectorAll("[data-cell]")).map(node => node.dataset.columnId), ["13", "12", "11"]);
    assert.deepEqual(Array.from(card(103).querySelectorAll("[data-cell]")).map(node => node.dataset.columnId), ["13"]); // só o que tem valor
    assert.ok(card(103).classList.contains("is-done"));
    assert.ok(card(105).classList.contains("is-overdue"));
    assert.match(card(105).textContent, /Atrasada/);
    assert.equal($$(".cal-card__flag").length, 1);
});

test("a day with more cards than the limit shows the first ones and '+ N mais'", t => {
    const {day, $$} = setup(t);
    const cards = Array.from(day("2026-10-27").querySelectorAll("[data-cal-card]"));
    assert.equal(cards.length, 5);
    assert.deepEqual(cards.map(node => node.classList.contains("is-overflow")), [false, false, false, true, true]);
    assert.equal(day("2026-10-27").querySelector("[data-cal-more]").textContent, "+ 2 mais");
    assert.equal($$("[data-cal-more]").length, 1);
});

test("blocked days (the column refuses weekends) have no add button and are marked", t => {
    const {day} = setup(t);
    for (const iso of ["2026-10-17", "2026-10-18"]) {
        assert.ok(day(iso).classList.contains("is-blocked"), iso);
        assert.equal(day(iso).querySelector("[data-cal-add]"), null, iso);
    }
    assert.ok(day("2026-10-16").querySelector("[data-cal-add]"));
});

test("controls depend on the permission: viewer reads, editor fills, admin configures", t => {
    const viewer = setup(t, {fixture: VIEWER});
    for (const selector of ["[data-cal-add]", "[draggable=true]", "[data-cal-config]", "[data-view-add]"]) assert.equal(viewer.$(selector), null, selector);
    const editor = setup(t, {fixture: EDITOR});
    assert.ok(editor.$("[data-cal-add]"));
    assert.ok(editor.$("[draggable=true]"));
    assert.equal(editor.$("[data-cal-config]"), null);
    const admin = setup(t);
    assert.ok(admin.$("[data-cal-config]"));
    assert.ok(admin.$("[data-view-add]"));
});

test("chips: items without a date and overdue items, with the exact counts", t => {
    const {$} = setup(t);
    assert.match($('[data-cal-panel-open="nodate"]').textContent, /Sem data\s*1/);
    assert.match($('[data-cal-panel-open="overdue"]').textContent, /Atrasados\s*1/);
});

// ---------------------------------------------------------------------------------------------------
// Criar no dia
// ---------------------------------------------------------------------------------------------------

test("clicking '+ Adicionar' opens the dialog over the calendar with the day's date filled", async t => {
    const {$, $$, click, day, w} = setup(t);
    click(day("2026-10-16").querySelector("[data-cal-add]"));
    assert.equal($(".board-dialog h2").textContent, "Criar obra");
    const dateInput = $(".cal-form input[type=date]");
    assert.equal(dateInput.value, "2026-10-16");
    assert.ok($(".cal-form [aria-label='Horário (opcional)']")); // a coluna mostra horário: opcional
    assert.deepEqual($$(".cal-form .board-field > span").map(node => node.textContent), ["Título", "Prazo", "Horário (opcional)", "Status", "Responsável", "Cliente"]);
    assert.equal($(".cal-form select[aria-label=Status]").value, "1"); // a etiqueta padrão já vem escolhida
    assert.ok(w.document.querySelector(".cal-grid")); // o calendário continua atrás
    await flush();
});

test("creating on a day sends the title, the group and every filled field in one request, then redraws", async t => {
    const {$, click, day, button, to, w} = setup(t);
    click(day("2026-10-16").querySelector("[data-cal-add]"));
    $(".cal-form input[aria-label=Título]").value = "Visita técnica";
    $(".cal-form [aria-label='Horário (opcional)']").value = "9h30";
    $(".cal-form select[aria-label=Status]").value = "2";
    $(".cal-form input[aria-label=Cliente]").value = "Shopping Norte";
    click(button("Criar obra"));
    await flush();
    const created = to("/itens/novo/");
    assert.equal(created.length, 1);
    assert.equal(created[0].url, "/quadros/1/itens/novo/");
    assert.deepEqual(created[0].body, {
        group_id: 1, name: "Visita técnica",
        initial: [{column_id: 14, value: "2026-10-16T09:30"}, {column_id: 13, value: 2}, {column_id: 11, value: "Shopping Norte"}],
    });
    assert.equal($(".board-dialog"), null);
    assert.deepEqual(to("/calendario/").map(call => call.body), [{mes: "2026-10", q: "", pessoa: ""}]);
    assert.ok(w.document.querySelector('[data-cal-card][data-item-id="101"]'));
});

test("the title is required and a bad time is refused before anything is sent", async t => {
    const {$, click, day, button, calls, to} = setup(t);
    click(day("2026-10-16").querySelector("[data-cal-add]"));
    click(button("Criar obra"));
    assert.equal($(".board-dialog__error").textContent, "Informe o título.");
    $(".cal-form input[aria-label=Título]").value = "X";
    $(".cal-form [aria-label='Horário (opcional)']").value = "25:99";
    click(button("Criar obra"));
    assert.match($(".board-dialog__error").textContent, /HH:MM/);
    $(".cal-form [aria-label='Horário (opcional)']").value = "";
    $(".cal-form input[type=date]").value = "";
    click(button("Criar obra"));
    assert.equal($(".board-dialog__error").textContent, "Informe a data.");
    await flush();
    assert.equal(to("/itens/novo/").length, 0);
    assert.ok(calls.every(call => call.url.startsWith("/api/pessoas/"))); // só a busca de pessoas da própria janela
});

test("without a time typed only the day is sent (no invented 00:00)", async t => {
    const {$, click, day, button, to} = setup(t);
    click(day("2026-10-16").querySelector("[data-cal-add]"));
    $(".cal-form input[aria-label=Título]").value = "Dia inteiro";
    click(button("Criar obra"));
    await flush();
    assert.equal(to("/itens/novo/")[0].body.initial[0].value, "2026-10-16");
});

test("cancelling closes the dialog and leaves the calendar exactly where it was", async t => {
    const {$, click, day, button, to} = setup(t);
    click(day("2026-10-16").querySelector("[data-cal-add]"));
    click(button("Cancelar"));
    await flush();
    assert.equal($(".board-dialog"), null);
    assert.equal(to("/itens/novo/").length + to("/calendario/").length, 0);
    assert.equal($(".cal-title").textContent, "outubro 2026");
});

test("a refused creation keeps the dialog open with the message and lets try again", async t => {
    const respond = call => call.url.endsWith("/itens/novo/") ? jsonResponse({ok: false, error: "Esta coluna não aceita sábado nem domingo."}, 400) : null;
    const {$, click, day, button, to} = setup(t, {respond});
    click(day("2026-10-16").querySelector("[data-cal-add]"));
    $(".cal-form input[aria-label=Título]").value = "X";
    click(button("Criar obra"));
    await flush();
    assert.ok($(".board-dialog"));
    assert.equal($(".board-dialog__error").textContent, "Esta coluna não aceita sábado nem domingo.");
    assert.equal(button("Criar obra").disabled, false);
    assert.equal(to("/calendario/").length, 0);
});

test("the person field searches and the chosen person goes with the new item", async t => {
    const {$, $$, click, day, button, to, runTimers, w} = setup(t);
    click(day("2026-10-16").querySelector("[data-cal-add]"));
    await flush();
    assert.deepEqual($$(".cal-form .board-people__item").map(node => node.textContent), ["ASAna Souza", "BLBruno Lima"]);
    const search = $(".cal-form .board-people__search");
    search.value = "bru";
    search.dispatchEvent(new w.Event("input", {bubbles: true}));
    runTimers();
    await flush();
    assert.ok(to("/api/pessoas/?q=bru").length);
    click($$(".cal-form .board-people__item")[1]);
    assert.match($(".cal-form__chosen").textContent, /Bruno Lima/);
    $(".cal-form input[aria-label=Título]").value = "Com pessoa";
    click(button("Criar obra"));
    await flush();
    assert.deepEqual(to("/itens/novo/")[0].body.initial.find(entry => entry.column_id === 12), {column_id: 12, value: 8});
});

test("a board with a single group does not ask for the group; with several it does", t => {
    const one = setup(t);
    one.click(one.day("2026-10-16").querySelector("[data-cal-add]"));
    assert.equal(one.$(".cal-form select[aria-label=Grupo]"), null);
    const many = setup(t, {tweak: meta => { meta.groups.push({id: 2, name: "Em andamento", color: "#00C875"}); }});
    many.click(many.day("2026-10-16").querySelector("[data-cal-add]"));
    assert.deepEqual(Array.from(many.$$(".cal-form select[aria-label=Grupo] option")).map(node => node.textContent), ["Oportunidades", "Em andamento"]);
});

test("a board without groups explains instead of opening the dialog", t => {
    const {$, click, day, toasts} = setup(t, {tweak: meta => { meta.calendar.default_group_id = null; }});
    click(day("2026-10-16").querySelector("[data-cal-add]"));
    assert.equal($(".board-dialog"), null);
    assert.match(toasts()[0], /Crie um grupo/);
});

// ---------------------------------------------------------------------------------------------------
// Arrastar entre dias
// ---------------------------------------------------------------------------------------------------

test("dragging a card to another day moves it at once, saves ONLY the date and then redraws", async t => {
    const {day, card, to, drag, calls} = setup(t);
    const source = card(101);
    source.dispatchEvent(drag("dragstart"));
    assert.ok(source.classList.contains("is-dragging"));
    const target = day("2026-10-16");
    const over = drag("dragover");
    target.dispatchEvent(over);
    assert.equal(over.defaultPrevented, true);
    assert.ok(target.classList.contains("is-drop-target"));
    target.dispatchEvent(drag("drop"));
    assert.equal(card(101).closest("[data-cal-day]"), target); // otimista: antes da resposta
    assert.equal(card(101).dataset.date, "2026-10-16");
    assert.equal(source.classList.contains("is-dragging"), false);
    assert.equal(target.classList.contains("is-drop-target"), false);
    await flush();
    assert.equal(calls.filter(call => call.url.endsWith("/valor/")).length, 1);
    assert.equal(to("/valor/")[0].url, "/quadros/itens/101/colunas/14/valor/");
    assert.deepEqual(to("/valor/")[0].body, {value: "2026-10-16"}); // só a data: nada de status, pessoa ou setor
    assert.equal(to("/calendario/").length, 1); // o servidor reposiciona e recalcula tudo
});

test("a timed card keeps its time when it changes day", async t => {
    const {day, card, to, drag} = setup(t);
    card(102).dispatchEvent(drag("dragstart"));
    day("2026-10-16").dispatchEvent(drag("drop"));
    await flush();
    assert.deepEqual(to("/valor/")[0].body, {value: "2026-10-16T14:00"});
});

test("if the server refuses, the card goes back and the message says which day it returned to", async t => {
    const respond = call => call.url.endsWith("/valor/") ? jsonResponse({ok: false, error: "Você não possui permissão."}, 403) : null;
    const {day, card, drag, toasts, to} = setup(t, {respond});
    const original = day("2026-10-15");
    card(101).dispatchEvent(drag("dragstart"));
    day("2026-10-16").dispatchEvent(drag("drop"));
    await flush();
    assert.equal(card(101).closest("[data-cal-day]"), original);
    assert.equal(original.querySelector("[data-cal-card]").dataset.itemId, "101"); // no mesmo lugar de antes
    assert.equal(card(101).dataset.date, "2026-10-15");
    assert.match(toasts()[0], /Não foi possível alterar a data\. O item voltou para 15\/10\/2026\./);
    assert.match(toasts()[0], /Você não possui permissão\./);
    assert.equal(to("/calendario/").length, 0);
});

test("a network failure also restores the card, without leaking the technical message", async t => {
    const respond = call => call.url.endsWith("/valor/") ? Promise.reject(new Error("offline")) : null;
    const {day, card, drag, toasts} = setup(t, {respond});
    card(101).dispatchEvent(drag("dragstart"));
    day("2026-10-16").dispatchEvent(drag("drop"));
    await flush();
    assert.equal(card(101).closest("[data-cal-day]"), day("2026-10-15"));
    assert.equal(toasts()[0], "Não foi possível alterar a data. O item voltou para 15/10/2026.");
});

test("dropping on a blocked day or on the same day sends nothing", async t => {
    const {day, card, drag, to} = setup(t);
    card(101).dispatchEvent(drag("dragstart"));
    const blocked = drag("dragover");
    day("2026-10-17").dispatchEvent(blocked);
    assert.equal(blocked.defaultPrevented, false); // sem "soltar aqui" no dia que a coluna recusa
    day("2026-10-17").dispatchEvent(drag("drop"));
    card(101).dispatchEvent(drag("dragstart"));
    day("2026-10-15").dispatchEvent(drag("drop"));
    await flush();
    assert.equal(to("/valor/").length, 0);
    assert.equal(card(101).closest("[data-cal-day]"), day("2026-10-15"));
});

test("dropping on a full day keeps the moved card visible and recounts '+ N mais'", async t => {
    const respond = call => call.url.endsWith("/valor/") ? new Promise(() => {}) : null; // servidor "pensando"
    const {day, card, drag} = setup(t, {respond});
    card(101).dispatchEvent(drag("dragstart"));
    day("2026-10-27").dispatchEvent(drag("drop"));
    const target = day("2026-10-27");
    assert.equal(target.querySelectorAll("[data-cal-card]").length, 6);
    assert.equal(target.querySelector("[data-cal-card]").dataset.itemId, "101");
    assert.equal(target.querySelector("[data-cal-card]").classList.contains("is-overflow"), false);
    assert.equal(target.querySelector("[data-cal-more]").textContent, "+ 3 mais");
    assert.equal(day("2026-10-15").querySelector("[data-cal-more]"), null);
});

test("viewer: dragging does nothing", async t => {
    const {day, card, drag, to} = setup(t, {fixture: VIEWER});
    card(101).dispatchEvent(drag("dragstart"));
    assert.equal(card(101).classList.contains("is-dragging"), false);
    day("2026-10-16").dispatchEvent(drag("drop"));
    await flush();
    assert.equal(to("/valor/").length, 0);
});

// ---------------------------------------------------------------------------------------------------
// Navegar entre meses
// ---------------------------------------------------------------------------------------------------

test("next month: no page reload, only the new range is requested, title and links follow, address is updated", async t => {
    const {$, click, to, w} = setup(t);
    const event = click($("[data-cal-next]"));
    assert.equal(event.defaultPrevented, true);
    await flush();
    assert.deepEqual(to("/calendario/").map(call => call.body), [{mes: "2026-11", q: "", pessoa: ""}]);
    assert.equal(to("/calendario/")[0].url, "/quadros/visoes/5/calendario/");
    assert.equal($(".cal-title").textContent, "novembro 2026");
    assert.equal($("[data-cal-grid]").dataset.month, "2026-11");
    assert.match($("[data-cal-prev]").getAttribute("href"), /mes=2026-10/);
    assert.match($("[data-cal-next]").getAttribute("href"), /mes=2026-12/);
    assert.equal($("[data-cal-month-input]").value, "2026-11");
    assert.match(w.location.search, /mes=2026-11/);
    assert.equal($("[data-board-status]").textContent, ""); // navegar não é "Salvando…"
});

// o servidor de mentira devolve o mês pedido, com os vizinhos certos
const monthRespond = call => {
    if (!call.url.endsWith("/calendario/")) return null;
    const [year, month] = call.body.mes.split("-").map(Number);
    const key = (y, m) => `${y + Math.floor((m - 1) / 12)}-${String(((m - 1) % 12 + 12) % 12 + 1).padStart(2, "0")}`;
    return jsonResponse(calendarPayload({month: call.body.mes, title: call.body.mes, prev: key(year, month - 1), next: key(year, month + 1), body_html: BODY_HTML(call.body.mes)}));
};

test("navigating keeps the search and the person filter", async t => {
    const {$, click, to, w} = setup(t, {url: "http://localhost/quadros/visoes/5/?mes=2026-10&q=arena&pessoa=7", respond: monthRespond});
    click($("[data-cal-today]"));
    await flush();
    assert.deepEqual(to("/calendario/")[0].body, {mes: "2026-10", q: "arena", pessoa: "7"});
    click($("[data-cal-next]"));
    await flush();
    assert.deepEqual(to("/calendario/")[1].body, {mes: "2026-11", q: "arena", pessoa: "7"});
    assert.match(w.location.search, /q=arena/);
    assert.match(w.location.search, /pessoa=7/);
    assert.match($("[data-cal-prev]").getAttribute("href"), /q=arena/);
});

test("ctrl/cmd-click on a month link is left to the browser (open in another tab)", async t => {
    const {$, click, to} = setup(t);
    assert.equal(click($("[data-cal-next]"), {ctrlKey: true}).defaultPrevented, false);
    assert.equal(click($("[data-cal-prev]"), {metaKey: true}).defaultPrevented, false);
    await flush();
    assert.equal(to("/calendario/").length, 0);
});

test("a failed month change keeps the current month and shows the error", async t => {
    const respond = call => call.url.endsWith("/calendario/") ? jsonResponse({ok: false, error: "Você não possui acesso a este conteúdo."}, 403) : null;
    const {$, click, toasts, w} = setup(t, {respond});
    click($("[data-cal-next]"));
    await flush();
    assert.equal($(".cal-title").textContent, "outubro 2026");
    assert.match(w.location.search, /mes=2026-10/);
    assert.match(toasts()[0], /Você não possui acesso/);
});

// ---------------------------------------------------------------------------------------------------
// "+ N mais", "Sem data" e "Atrasados"
// ---------------------------------------------------------------------------------------------------

test("'+ N mais' lists every item of the day in a pop-over, without leaving the calendar", async t => {
    const {$, $$, click, day, to} = setup(t);
    click(day("2026-10-27").querySelector("[data-cal-more]"));
    assert.equal($$(".board-pop .cal-pop-day .cal-card").length, 5);
    assert.equal($$(".board-pop .cal-card.is-overflow").length, 0);
    assert.equal($$(".board-pop [draggable], .board-pop [data-cell]").length, 0);
    click($$(".board-pop .cal-card")[4]);
    await flush();
    assert.equal($(".board-pop"), null);
    assert.equal(to("/detalhe/")[0].url, "/quadros/itens/205/detalhe/");
    assert.ok($("[data-cal-grid]"));
});

test("'Sem data' lists the items that have none and opens them in the drawer", async t => {
    const {$, $$, click, to} = setup(t);
    click($('[data-cal-panel-open="nodate"]'));
    assert.deepEqual($$(".board-pop .cal-panel__name").map(node => node.textContent), ["Item sem data"]);
    click($(".board-pop [data-cal-open]"));
    await flush();
    assert.equal(to("/detalhe/")[0].url, "/quadros/itens/104/detalhe/");
    assert.equal($("[data-cal-drawer]").hidden, false);
});

test("'Atrasados' shows open overdue items with the date they were due", t => {
    const {$, $$, click} = setup(t);
    click($('[data-cal-panel-open="overdue"]'));
    assert.deepEqual($$(".board-pop .cal-panel__name").map(node => node.textContent), ["Contrato atrasado"]);
    assert.match($(".board-pop .cal-panel__sub").textContent, /30\/09\/2026/);
});

test("clicking the same chip again closes its pop-over", t => {
    const {$, click} = setup(t);
    click($('[data-cal-panel-open="nodate"]'));
    assert.ok($(".board-pop"));
    click($('[data-cal-panel-open="nodate"]'));
    assert.equal($(".board-pop"), null);
});

// ---------------------------------------------------------------------------------------------------
// Gaveta
// ---------------------------------------------------------------------------------------------------

test("clicking a card opens the drawer (no page change, no 'Salvando…'), Enter and Space too", async t => {
    const {$, click, key, card, to} = setup(t);
    assert.equal($("[data-cal-drawer]").hidden, true);
    click(card(101).querySelector(".cal-card__title"));
    await flush();
    assert.equal(to("/detalhe/")[0].url, "/quadros/itens/101/detalhe/");
    assert.equal($("[data-cal-drawer]").hidden, false);
    assert.equal($("[data-drawer]").dataset.itemId, "101");
    assert.equal($("[data-board-status]").textContent, "");
    key(card(103), "Enter");
    await flush();
    assert.equal($("[data-drawer]").dataset.itemId, "103");
    key(card(102), " ");
    await flush();
    assert.equal($("[data-drawer]").dataset.itemId, "102");
    assert.ok($(".cal-grid")); // o calendário continua visível atrás
});

test("clicking a field inside the card edits that field and does NOT open the drawer", async t => {
    const {$, $$, click, card, to} = setup(t);
    click(card(101).querySelector('[data-cell][data-column-id="13"]'));
    assert.deepEqual($$(".board-pop .board-option").map(node => node.textContent), ["Novo", "Levantamento", "Ganho"]);
    await flush();
    assert.equal(to("/detalhe/").length, 0);
    assert.equal($("[data-cal-drawer]").hidden, true);
});

test("changing a card's status from the card saves the cell, redraws the calendar and nothing else", async t => {
    const {$$, click, card, to} = setup(t);
    click(card(101).querySelector('[data-cell][data-column-id="13"]'));
    click($$(".board-pop .board-option")[2]);
    await flush();
    assert.equal(to("/valor/")[0].url, "/quadros/itens/101/colunas/13/valor/");
    assert.deepEqual(to("/valor/")[0].body, {value: 3});
    assert.equal(to("/calendario/").length, 1);
});

test("closing the drawer: the button and Escape; Escape closes a pop-over first", async t => {
    const {$, $$, click, key, card, w} = setup(t);
    click(card(101));
    await flush();
    click($("[data-drawer-close]"));
    assert.equal($("[data-cal-drawer]").hidden, true);
    assert.equal($("[data-cal-drawer]").innerHTML, "");
    click(card(101));
    await flush();
    click($('[data-drawer] [data-cell][data-column-id="13"]'));
    assert.ok($(".board-pop"));
    key(w.document.body, "Escape");
    assert.equal($(".board-pop"), null);
    assert.equal($("[data-cal-drawer]").hidden, false); // o primeiro Escape fechou só o pop-over
    key(w.document.body, "Escape");
    assert.equal($("[data-cal-drawer]").hidden, true);
    assert.equal($$(".board-dialog").length, 0);
});

test("editing a field in the drawer saves it, redraws the calendar and refreshes the drawer's history", async t => {
    const {$, $$, click, card, to} = setup(t);
    click(card(101));
    await flush();
    click($('[data-drawer] [data-cell][data-column-id="13"]'));
    click($$(".board-pop .board-option")[2]);
    await flush();
    assert.deepEqual(to("/valor/")[0].body, {value: 3});
    assert.equal(to("/calendario/").length, 1);
    assert.equal(to("/detalhe/").length, 2); // abrir + atualizar depois de gravar
});

test("renaming from the drawer: Enter saves, the calendar and the drawer are refreshed", async t => {
    const {$, click, card, to, w} = setup(t);
    click(card(101));
    await flush();
    click($("[data-drawer-title]"));
    const input = $("[data-drawer] .board-inline-input");
    assert.equal(input.value, "Arena Norte");
    input.value = "Arena Center Norte";
    input.dispatchEvent(new w.KeyboardEvent("keydown", {key: "Enter", bubbles: true, cancelable: true}));
    await flush();
    assert.equal(to("/renomear/")[0].url, "/quadros/itens/101/renomear/");
    assert.deepEqual(to("/renomear/")[0].body, {name: "Arena Center Norte"});
    assert.equal(to("/calendario/").length, 1);
});

test("deleting from the drawer asks first, then closes the drawer and redraws the calendar", async t => {
    const {$, click, card, to, button} = setup(t);
    click(card(101));
    await flush();
    click($("[data-drawer-delete]"));
    assert.match($(".board-dialog__body").textContent, /Arena Norte/);
    assert.equal(to("/excluir/").length, 0);
    click(button("Excluir"));
    await flush();
    assert.equal(to("/excluir/")[0].url, "/quadros/itens/101/excluir/");
    assert.equal($("[data-cal-drawer]").hidden, true);
    assert.equal(to("/calendario/").length, 1);
});

test("viewer: the drawer opens read-only and fields do not open editors", async t => {
    const {$, click, card, to} = setup(t, {fixture: VIEWER});
    click(card(101));
    await flush();
    assert.equal($("[data-cal-drawer]").hidden, false);
    click($("[data-drawer-title]")); // sem permissão de editar: não vira campo de texto
    assert.equal($("[data-drawer] .board-inline-input"), null);
    click($('[data-drawer] [data-cell][data-column-id="13"]'));
    assert.equal($(".board-pop"), null);
    assert.equal(to("/valor/").length + to("/renomear/").length, 0);
});

// ---------------------------------------------------------------------------------------------------
// Data com hora opcional
// ---------------------------------------------------------------------------------------------------

test("the date pop-over: date, optional time with quick choices, and a hint that the time is not required", async t => {
    const {$, $$, click, card} = setup(t);
    click(card(101));
    await flush();
    click($('[data-drawer] [data-cell][data-column-id="14"]'));
    assert.equal($(".cal-datepop input[type=date]").value, "2026-10-15");
    assert.deepEqual($$(".cal-datepop__times .btn").map(node => node.textContent), ["08:00", "09:00", "10:00", "14:00", "15:00", "16:00"]);
    assert.match($(".cal-datepop__time label").textContent, /opcional/i);
    assert.ok($$(".board-pop__foot .btn").some(node => node.textContent === "Hoje"));
    assert.ok($$(".board-pop__foot .btn").some(node => node.textContent === "Limpar data"));
    assert.equal($$(".board-pop__foot .btn").some(node => node.textContent === "Limpar horário"), false); // não há hora para limpar
});

test("picking a quick time saves the date with that time", async t => {
    const {$, $$, click, card, to} = setup(t);
    click(card(101));
    await flush();
    click($('[data-drawer] [data-cell][data-column-id="14"]'));
    click($$(".cal-datepop__times .btn")[3]);
    await flush();
    assert.deepEqual(to("/valor/")[0].body, {value: "2026-10-15T14:00"});
    assert.equal($(".board-pop"), null);
});

test("typing a time: Enter saves it normalised; an impossible time shows the error and sends nothing", async t => {
    const {$, click, card, to, w} = setup(t);
    click(card(101));
    await flush();
    click($('[data-drawer] [data-cell][data-column-id="14"]'));
    const input = $(".cal-datepop__time input[type=text]");
    input.value = "99:99";
    input.dispatchEvent(new w.KeyboardEvent("keydown", {key: "Enter", bubbles: true, cancelable: true}));
    assert.equal($(".cal-datepop__error").hidden, false);
    assert.equal(to("/valor/").length, 0);
    input.value = "9h30";
    input.dispatchEvent(new w.KeyboardEvent("keydown", {key: "Enter", bubbles: true, cancelable: true}));
    await flush();
    assert.deepEqual(to("/valor/")[0].body, {value: "2026-10-15T09:30"});
});

test("changing the day keeps the time; clearing the time keeps the day; clearing the day sends an empty value", async t => {
    const respond = call => call.url.endsWith("/detalhe/") ? jsonResponse({ok: true, drawer_html: DRAWER_HTML(101, "2026-10-15T14:00")}) : null;
    const {$, $$, click, card, to, w} = setup(t, {respond});
    click(card(101));
    await flush();
    const field = '[data-drawer] [data-cell][data-column-id="14"]';
    click($(field));
    assert.equal($(".cal-datepop__time input[type=text]").value, "14:00");
    const date = $(".cal-datepop input[type=date]");
    date.value = "2026-10-18";
    date.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.deepEqual(to("/valor/")[0].body, {value: "2026-10-18T14:00"}); // mantém a hora

    click($(field));
    click($$(".board-pop__foot .btn").find(node => node.textContent === "Limpar horário"));
    await flush();
    assert.deepEqual(to("/valor/")[1].body, {value: "2026-10-15"}); // a data fica, só a hora sai

    click($(field));
    click($$(".board-pop__foot .btn").find(node => node.textContent === "Limpar data"));
    await flush();
    assert.deepEqual(to("/valor/")[2].body, {value: ""}); // sai da grade, mas o item não é excluído
    assert.equal(to("/excluir/").length, 0);
});

test("'Hoje' in the date pop-over sends today's date", async t => {
    const {$, $$, click, card, to} = setup(t);
    click(card(101));
    await flush();
    click($('[data-drawer] [data-cell][data-column-id="14"]'));
    click($$(".board-pop__foot .btn").find(node => node.textContent === "Hoje"));
    await flush();
    assert.match(to("/valor/")[0].body.value, /^\d{4}-\d{2}-\d{2}$/);
});

test("a column that stores only the day: hint, and who manages columns can turn the time on", async t => {
    const respond = call => call.url.endsWith("/configuracoes/")
        ? jsonResponse({ok: true, column: {...FULL.meta.columns.find(c => c.id === 14), settings: {show_time: true, allow_weekends: false, is_deadline: true}}, header_html: "", cells: {}})
        : null;
    const noTime = meta => { meta.columns.find(c => c.id === 14).settings.show_time = false; };
    const {$, $$, click, card, to} = setup(t, {respond, tweak: noTime});
    click(card(101));
    await flush();
    click($('[data-drawer] [data-cell][data-column-id="14"]'));
    assert.equal($(".cal-datepop__time"), null);
    assert.match($(".cal-datepop__hint").textContent, /só o dia/);
    click($$(".cal-datepop .btn").find(node => node.textContent === "Ativar horário nesta coluna"));
    await flush();
    assert.deepEqual(to("/configuracoes/")[0].body, {settings: {show_time: true}});
    assert.equal(to("/configuracoes/")[0].url, "/quadros/colunas/14/configuracoes/");
    assert.ok($(".cal-datepop__time")); // o pop-over reabre já com o horário
});

test("without permission to manage columns there is no button to turn the time on", async t => {
    const noTime = meta => { meta.columns.find(c => c.id === 14).settings.show_time = false; };
    const {$, click, card} = setup(t, {fixture: EDITOR, tweak: noTime});
    click(card(101));
    await flush();
    click($('[data-drawer] [data-cell][data-column-id="14"]'));
    assert.ok($(".cal-datepop input[type=date]"));
    assert.equal($(".cal-datepop__hint"), null);
    assert.equal($(".cal-datepop__time"), null);
});

// ---------------------------------------------------------------------------------------------------
// Configurar
// ---------------------------------------------------------------------------------------------------

test("configuring: the dialog autosaves each change and the calendar is redrawn", async t => {
    const {$, $$, click, to, w} = setup(t);
    click($("[data-cal-config]"));
    assert.equal($(".board-dialog h2").textContent, "Configurar calendário");
    const colorSelect = $(".kanban-config select[aria-label='Colorir por']");
    assert.deepEqual(Array.from(colorSelect.options).map(node => node.textContent), ["Status", "Setor", "Grupo do item", "Sem cor"]);
    assert.equal(colorSelect.value, "13");
    colorSelect.value = "group";
    colorSelect.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.equal(to("/editar/")[0].url, "/quadros/visoes/5/editar/");
    assert.deepEqual(to("/editar/")[0].body, {settings: {color_by: "group"}});
    assert.equal(to("/calendario/").length, 1);

    colorSelect.value = "18"; // uma coluna: o id vai como número
    colorSelect.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.deepEqual(to("/editar/")[1].body, {settings: {color_by: 18}});

    const weekends = $$(".kanban-config .board-field--check").find(node => /finais de semana/.test(node.textContent)).querySelector("input");
    assert.equal(weekends.checked, true);
    weekends.checked = false;
    weekends.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.deepEqual(to("/editar/")[2].body, {settings: {show_weekends: false}});
    const completed = $$(".kanban-config .board-field--check").find(node => /concluídos/.test(node.textContent)).querySelector("input");
    completed.checked = false;
    completed.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.deepEqual(to("/editar/")[3].body, {settings: {show_completed: false}});
});

test("the scale select offers Mês only (the others are marked 'em breve' and disabled)", t => {
    const {$, $$, click} = setup(t);
    click($("[data-cal-config]"));
    const select = $(".kanban-config select[aria-label=Escala]");
    assert.equal(select.value, "month");
    assert.deepEqual(Array.from(select.options).map(node => [node.value, node.disabled]), [["month", false], ["week", true], ["day", true], ["agenda", true]]);
    assert.deepEqual($$("select[data-cal-period] option:disabled").map(node => node.value), ["week", "day", "agenda"]);
});

test("a refused setting goes back to the previous value and shows the error", async t => {
    const respond = call => call.url.endsWith("/editar/") ? jsonResponse({ok: false, error: "Colorir por: escolha uma coluna de Status."}, 400) : null;
    const {$, click, toasts, w} = setup(t, {respond});
    click($("[data-cal-config]"));
    const colorSelect = $(".kanban-config select[aria-label='Colorir por']");
    colorSelect.value = "18";
    colorSelect.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.equal(colorSelect.value, "13");
    assert.match(toasts()[0], /Colorir por/);
});

test("card fields: reorder and pick with autosave, limited to the maximum", async t => {
    const {$, $$, click, to, runTimers, toasts, w} = setup(t);
    click($("[data-cal-config]"));
    assert.match($(".kanban-config").textContent, /até 3 campos/);
    const rows = () => $$(".kanban-config__field");
    assert.deepEqual(rows().map(row => row.querySelector("span").textContent), ["Status", "Responsável", "Cliente", "Valor", "Probabilidade", "Visto", "Setor"]); // sem a coluna de Data
    click(rows()[1].querySelectorAll("button")[1]); // desce "Responsável"
    runTimers();
    await flush();
    assert.deepEqual(to("/editar/")[0].body, {settings: {card_fields: [13, 11, 12]}});
    // marca mais três (total 6) e tenta a sétima
    for (const label of ["Valor", "Probabilidade", "Visto"]) {
        const box = rows().find(row => row.textContent.includes(label)).querySelector("input");
        box.checked = true;
        box.dispatchEvent(new w.Event("change", {bubbles: true}));
    }
    const seventh = rows().find(row => row.textContent.includes("Setor")).querySelector("input");
    seventh.checked = true;
    seventh.dispatchEvent(new w.Event("change", {bubbles: true}));
    assert.equal(seventh.checked, false);
    assert.match(toasts()[0], /até 6 campos/);
});

test("a Date column created on the screen shows up in the configuration after the redraw", async t => {
    const column = {...FULL.meta.columns.find(c => c.id === 14), id: 20, name: "Visita técnica"};
    const respond = call => call.url.endsWith("/calendario/")
        ? jsonResponse(calendarPayload({columns: [...FULL.meta.columns, column], dateable_ids: [14, 20]})) : null;
    const {$, $$, click} = setup(t, {respond});
    click($("[data-cal-next]"));
    await flush();
    click($("[data-cal-config]"));
    assert.deepEqual(Array.from($(".kanban-config select[aria-label='Data utilizada']").options).map(node => node.textContent), ["Prazo", "Visita técnica"]);
    assert.ok($$(".kanban-config__field").some(row => row.textContent.includes("Visita técnica")));
});

test("the preview shows a real card and is refreshed after each change", async t => {
    const {$, click} = setup(t);
    click($("[data-cal-config]"));
    assert.ok($(".kanban-config__preview .cal-card.is-preview"));
    assert.equal($(".kanban-config__preview [data-cell]"), null);
    assert.equal($(".kanban-config__preview [draggable]"), null);
});

test("the hidden-weekend notice offers to show them (only to whoever can edit the view)", async t => {
    const admin = setup(t, {fixture: WEEKEND});
    assert.equal(admin.$$(".cal-weekday").length, 5);
    assert.match(admin.$("[data-cal-show-weekends]").textContent, /1 item em fim de semana oculto/);
    admin.click(admin.$("[data-cal-show-weekends]"));
    await flush();
    assert.deepEqual(admin.to("/editar/")[0].body, {settings: {show_weekends: true}});
    assert.equal(admin.to("/calendario/").length, 1);
    const viewer = setup(t, {fixture: renderFixture({permissions: {view: true, edit: false, delete: false, manage_columns: false, create_item: false, edit_item: false, delete_item: false}, variant: "weekend"})});
    assert.equal(viewer.$("[data-cal-show-weekends]"), null);
    assert.match(viewer.$(".cal-chip--note").textContent, /em fim de semana oculto/);
});

// ---------------------------------------------------------------------------------------------------
// Sem coluna de Data
// ---------------------------------------------------------------------------------------------------

test("without a Date column: explains, and who manages columns creates one without leaving the screen", async t => {
    const column = {...FULL.meta.columns.find(c => c.id === 14), id: 20, name: "Data"};
    const respond = call => call.url.endsWith("/colunas/novo/") ? jsonResponse({ok: true, column, header_html: "", cells: {}}) : null;
    const {$, click, to} = setup(t, {fixture: NODATE, respond});
    assert.equal($("[data-cal-grid]"), null);
    assert.match($(".cal-state").textContent, /Escolha uma coluna de Data/);
    click($("[data-cal-create-date]"));
    await flush();
    assert.equal(to("/colunas/novo/")[0].url, "/quadros/1/colunas/novo/");
    assert.deepEqual(to("/colunas/novo/")[0].body, {type: "DATE"});
    assert.deepEqual(to("/editar/")[0].body, {settings: {date_field: 20}}); // fixa a coluna escolhida na visualização
    assert.equal(to("/calendario/").length, 1);
});

test("without a Date column and without permission: only the explanation", t => {
    const fixture = renderFixture({permissions: {view: true, edit: false, delete: false, manage_columns: false, create_item: true, edit_item: true, delete_item: false}, variant: "nodate"});
    const {$} = setup(t, {fixture});
    assert.equal($("[data-cal-create-date]"), null);
    assert.match($(".cal-state").textContent, /Peça a quem gerencia/);
});

// ---------------------------------------------------------------------------------------------------
// Aba "+": criar um Calendário
// ---------------------------------------------------------------------------------------------------

test("tabs: the calendar has its own icon and the current tab is marked", t => {
    const {$, $$} = setup(t);
    assert.deepEqual($$(".board-tab span").map(node => node.textContent), ["Quadro principal", "Kanban", "Calendário"]);
    assert.equal($('[aria-current="page"]').textContent.trim(), "Calendário");
    assert.ok($('a.board-tab[data-view-id="5"] use[href="#i-calendar"]'));
    assert.ok($('a.board-tab[data-view-id="6"] use[href="#i-kanban"]'));
});

test("adding a Calendar: choosing the type renames the default, a typed name is kept, and it creates a CALENDAR view", async t => {
    const respond = call => call.url.endsWith("/visoes/novo/") ? jsonResponse({ok: true, view: {id: 9, name: "Calendário"}, redirect_url: "/quadros/visoes/9/"}) : null;
    const {$, $$, click, button, to} = setup(t, {respond});
    click($("[data-view-add]"));
    const name = $(".board-dialog input[type=text]");
    assert.equal(name.value, "Kanban");
    click($$(".board-view-type").find(node => node.textContent.startsWith("Calendário")));
    assert.equal(name.value, "Calendário");
    assert.equal($(".board-view-type.is-selected strong").textContent, "Calendário");
    name.value = "Prazos";
    name.dispatchEvent(new (name.ownerDocument.defaultView.Event)("input", {bubbles: true}));
    click($$(".board-view-type").find(node => node.textContent.startsWith("Kanban")));
    assert.equal(name.value, "Prazos"); // o nome digitado não é trocado
    click($$(".board-view-type").find(node => node.textContent.startsWith("Calendário")));
    click(button("Criar visualização"));
    await flush();
    assert.deepEqual(to("/visoes/novo/")[0].body, {name: "Prazos", type: "CALENDAR"});
});

test("adding a Calendar to a board with no Date column: notice, button disabled, and a way to create the column", async t => {
    const column = {...FULL.meta.columns.find(c => c.id === 14), id: 20, name: "Data"};
    const respond = call => call.url.endsWith("/colunas/novo/") ? jsonResponse({ok: true, column, header_html: "", cells: {}}) : null;
    const {$, $$, click, button, to} = setup(t, {fixture: NODATE, respond});
    click($("[data-view-add]"));
    click($$(".board-view-type").find(node => node.textContent.startsWith("Calendário")));
    assert.equal($(".board-dialog .board-field__hint").hidden, false);
    assert.match($(".board-dialog .board-field__hint").textContent, /escolha ou crie uma coluna de Data/);
    assert.equal(button("Criar visualização").disabled, true);
    click($$(".board-dialog .btn").find(node => node.textContent === "+ Criar coluna de Data"));
    await flush();
    assert.deepEqual(to("/colunas/novo/")[0].body, {type: "DATE"});
    assert.equal($(".board-dialog .board-field__hint").hidden, true);
    assert.equal(button("Criar visualização").disabled, false);
});

test("a Kanban keeps working from the same dialog (default type)", async t => {
    const respond = call => call.url.endsWith("/visoes/novo/") ? jsonResponse({ok: true, view: {id: 9, name: "Kanban 2"}, redirect_url: "/quadros/visoes/9/"}) : null;
    const {$, click, button, to} = setup(t, {respond});
    click($("[data-view-add]"));
    click(button("Criar visualização"));
    await flush();
    assert.deepEqual(to("/visoes/novo/")[0].body, {name: "Kanban", type: "KANBAN"});
});
