/* Visualização Kanban dos quadros (static/js/boards.js, modo Kanban).
   Requires jsdom@26.1.0 in NODE_PATH; no browser or production dependency.
   Run from workflow: node --test tests/boards-kanban.test.cjs
   Set PYTHON to the project's Python if it is not in .venv.

   O HTML vem dos templates Django reais (boards/board_kanban.html e parciais) renderizados com objetos em memória,
   sem banco, e as raias montadas por `boards.kanban.build_lanes` (a mesma função da tela). O servidor é simulado por
   um `fetch` falso: o contrato testado é "o que a tela manda" e "o que ela faz com a resposta". */
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
from boards.models import Board, BoardColumn, BoardColumnOption, BoardItem, BoardCell, BoardView, BoardGroup
from boards.kanban import build_lanes, clean_kanban_settings, resolve_card_columns, resolve_sum_column, sort_options
from boards.presentation import board_urls, type_catalog, type_icon, COLOR_PALETTE, SENTINEL, SENTINEL_COLUMN

permissions = json.loads(os.environ.get('BOARD_PERMISSIONS') or 'null') or {
    'view': True, 'edit': True, 'delete': True, 'manage_columns': True,
    'create_item': True, 'edit_item': True, 'delete_item': True,
}
User = get_user_model()
board = Board(pk=1, name='Orçamentos', item_label='Obra')
ana = User(pk=7, username='ana', first_name='Ana', last_name='Souza')

def col(pk, name, kind, **extra):
    return BoardColumn(pk=pk, board=board, board_id=1, name=name, type=kind, width=160, **extra)

columns = [
    col(11, 'Cliente', 'TEXT'),
    col(12, 'Responsável', 'PERSON'),
    col(13, 'Status', 'STATUS'),
    col(14, 'Prazo', 'DATE', settings={'is_deadline': True}),
    col(15, 'Valor', 'CURRENCY'),
    col(16, 'Probabilidade', 'NUMBER', settings={'decimal_places': 0, 'unit': '%'}),
    col(17, 'Visto', 'CHECKBOX'),
    col(18, 'Setor', 'DROPDOWN'),
]
by_id = {c.pk: c for c in columns}
options = {
    13: [(1, 'Novo', '#C4C4C4', True, False), (2, 'Levantamento', '#66CCFF', False, False), (3, 'Ganho', '#00C875', False, True)],
    18: [(4, 'Comercial', '#00C875', False, False), (5, 'Engenharia', '#A25DDC', False, False)],
}
opt_objs = {oid: BoardColumnOption(pk=oid, column=by_id[cid], column_id=cid, label=l, color=c, position=oid, is_default=d, is_done=n)
            for cid, rows in options.items() for (oid, l, c, d, n) in rows}

class FakeOptions:
    def __init__(self, items): self.items = items
    def all(self): return self.items

class FakeGroupColumn:
    pk = 13; type = 'STATUS'; name = 'Status'
    options = FakeOptions([opt_objs[1], opt_objs[2], opt_objs[3]])

group = BoardGroup(pk=1, board=board, name='Oportunidades', color='#579BFC')

def make_item(pk, name, values):
    item = BoardItem(pk=pk, board=board, group=group, group_id=1, name=name)
    item.cell_map = {}
    for column_id, value in values.items():
        column = by_id[column_id]
        cell = BoardCell(item=item, column=column)
        cell.option = None; cell.person = None; cell.display = ''
        if column.type == 'TEXT':
            cell.value_text = value; cell.display = value
        elif column.type == 'PERSON':
            cell.person = ana; cell.display = 'Ana Souza'
        elif column.type in ('STATUS', 'DROPDOWN'):
            cell.option = opt_objs[value]; cell.display = cell.option.label
        elif column.type == 'DATE':
            cell.value_date = value; cell.display = value.strftime('%d/%m/%Y')
        elif column.type == 'CURRENCY':
            cell.value_number = Decimal(value); cell.display = 'R$ ' + format(Decimal(value), ',.2f').replace(',', 'X').replace('.', ',').replace('X', '.')
        elif column.type == 'CHECKBOX':
            cell.value_boolean = value; cell.display = 'Sim' if value else 'Não'
        item.cell_map[column_id] = cell
    return item

items = [
    make_item(101, 'Arena Norte', {11: 'Shopping Norte', 12: 'x', 13: 2, 14: datetime.date(2025, 1, 15), 15: '2500000'}),
    make_item(102, 'Condomínio Cotia', {11: 'Residencial Cotia', 13: 1, 15: '1800000'}),
    make_item(103, 'Hospital Vida', {13: 3, 15: '1200000'}),
    make_item(104, 'Item sem etapa', {11: 'Sem etapa'}),
]
settings = clean_kanban_settings(columns, {'group_by': 13, 'sum_column': 15, 'card_fields': [11, 12, 13, 14, 15]})
sum_column = resolve_sum_column(settings, columns)
card_columns = resolve_card_columns(settings, columns, by_id[13])
lanes = build_lanes(FakeGroupColumn, items, settings, sum_column)

view = BoardView(pk=5, board=board, name='Kanban por Status', type='KANBAN')
other_view = BoardView(pk=6, board=board, name='Kanban por Setor', type='KANBAN')

meta_columns = []
for c in columns:
    meta_columns.append({
        'id': c.pk, 'name': c.name, 'type': c.type, 'type_label': c.get_type_display(), 'icon': type_icon(c.type),
        'width': c.width, 'description': '', 'is_required': False, 'is_visible': True, 'settings': c.settings or {},
        'options': [{'id': o[0], 'label': o[1], 'color': o[2], 'is_default': o[3], 'is_done': o[4]} for o in options.get(c.pk, [])],
    })
meta = {
    'board': {'id': 1, 'name': board.name, 'item_label': board.item_label},
    'permissions': permissions, 'urls': board_urls(board),
    'sentinels': {'id': SENTINEL, 'column': SENTINEL_COLUMN}, 'types': type_catalog(), 'columns': meta_columns,
    'groups': [{'id': 1, 'name': 'Oportunidades', 'color': '#579BFC'}],
    'sort': {'column': None, 'dir': 'asc'}, 'limits': {'min_width': 96, 'max_width': 640}, 'palette': COLOR_PALETTE,
    'kanban': {
        'view': {'id': 5, 'name': view.name}, 'settings': settings, 'group_column_id': 13, 'sum_column_id': 15,
        'card_column_ids': [c.pk for c in card_columns], 'groupable_ids': [13, 18], 'summable_ids': [15, 16], 'default_group_id': 1,
    },
}

source = open(os.path.join('templates', 'boards', 'board_kanban.html'), encoding='utf-8').read()
body = re.search(r'{% block content %}(.*){% endblock %}\\s*{% block scripts %}', source, re.S).group(1)
context = Context({
    'board': board, 'view': view, 'views': [view, other_view], 'active_view': view, 'permissions': permissions,
    'search': '', 'person_id': None, 'people': [ana], 'filtering': False,
    'group_candidates': [by_id[13], by_id[18]], 'group_column': by_id[13], 'sum_column': sum_column,
    'sort_options': sort_options(columns, settings), 'lanes': lanes, 'card_columns': card_columns,
    'show_field_names': False, 'meta': meta,
})
print(json.dumps({'html': Template('{% load static lps_board %}' + body).render(context), 'meta': meta}))
`;

function renderFixture(permissions) {
    const env = {...process.env};
    if (permissions) env.BOARD_PERMISSIONS = JSON.stringify(permissions);
    return JSON.parse(execFileSync(python, ["-c", PYTHON_FIXTURE], {cwd: root, encoding: "utf8", env}).trim());
}

const FULL = renderFixture();
const EDITOR = renderFixture({view: true, edit: false, delete: false, manage_columns: false, create_item: true, edit_item: true, delete_item: false});
const VIEWER = renderFixture({view: true, edit: false, delete: false, manage_columns: false, create_item: false, edit_item: false, delete_item: false});
const script = readFileSync(path.join(root, "static/js/boards.js"), "utf8");
const coreScript = readFileSync(path.join(root, "static/js/kanban-core.js"), "utf8");  // o Kanban é o componente único: carrega antes do boards.js
const tick = () => new Promise(resolve => setImmediate(resolve));
const flush = async () => { for (let i = 0; i < 8; i += 1) await tick(); };

function jsonResponse(body, status = 200) {
    return Promise.resolve({ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body)});
}

// O que o servidor devolve ao pedir as raias: aqui, uma versão simplificada das mesmas raias.
const LANES_HTML = (moved) => `
<section class="kanban-lane" data-lane data-lane-key="1" data-option-id="1" data-lane-label="Novo" style="--lane-color:#C4C4C4">
  <header class="kanban-lane__head"><span data-lane-title>Novo</span><span data-lane-count>1</span><button type="button" data-lane-menu></button></header>
  <div data-lane-body><article class="kanban-card" data-card data-item-id="102" draggable="true"><span data-card-title>Condomínio Cotia</span><button type="button" data-card-menu></button></article><p data-lane-empty hidden></p></div>
  <footer><button type="button" data-kanban-add>+ Adicionar obra</button></footer>
</section>
<section class="kanban-lane" data-lane data-lane-key="3" data-option-id="3" data-lane-label="Ganho" style="--lane-color:#00C875">
  <header class="kanban-lane__head"><span data-lane-title>Ganho</span><span data-lane-count>${moved ? 2 : 1}</span><button type="button" data-lane-menu></button></header>
  <div data-lane-body>${moved ? '<article class="kanban-card" data-card data-item-id="101" draggable="true"><span data-card-title>Arena Norte</span></article>' : ''}<article class="kanban-card" data-card data-item-id="103" draggable="true"><span data-card-title>Hospital Vida</span><button type="button" data-card-menu></button></article><p data-lane-empty hidden></p></div>
</section>`;

function lanesPayload(overrides = {}) {
    return {
        ok: true, lanes_html: LANES_HTML(true), total_items: 4, columns: FULL.meta.columns,
        settings: FULL.meta.kanban.settings, group_column_id: 13, sum_column_id: 15, card_column_ids: [11, 12, 13, 14, 15], ...overrides,
    };
}

function setup(t, {fixture = FULL, respond} = {}) {
    const dom = new JSDOM("<!doctype html><body>" + fixture.html + "</body>", {
        url: "http://localhost/quadros/visoes/5/", runScripts: "outside-only", pretendToBeVisual: true,
    });
    t.after(() => dom.window.close());
    const w = dom.window;
    const calls = [];
    w.fetch = (url, options = {}) => {
        const call = {url, method: options.method || "GET", headers: options.headers || {}, body: options.body ? JSON.parse(options.body) : null};
        calls.push(call);
        if (respond) return respond(call);
        return call.url.endsWith("/lanes/") ? jsonResponse(lanesPayload()) : jsonResponse({ok: true});
    };
    const timers = [];
    let timerId = 0;
    w.setTimeout = (fn, ms) => { timerId += 1; timers.push({id: timerId, fn, ms}); return timerId; };
    w.clearTimeout = id => { const index = timers.findIndex(timer => timer.id === id); if (index >= 0) timers.splice(index, 1); };
    w.eval(coreScript);
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
    const lane = id => $(`[data-lane][data-lane-key="${id}"]`);
    const card = id => $(`[data-card][data-item-id="${id}"]`);
    const runTimers = () => { while (timers.length) timers.shift().fn(); };
    const drag = (type, init = {}) => {
        const event = new w.MouseEvent(type, {bubbles: true, cancelable: true, ...init});
        event.dataTransfer = {setData() {}, setDragImage() {}, effectAllowed: ""};
        return event;
    };
    return {w, $, $$, click, key, lane, card, calls, runTimers, drag};
}

// ---------------------------------------------------------------------------------------------------
// Estrutura
// ---------------------------------------------------------------------------------------------------

test("boot in Kanban mode: lanes in label order with counts and sums, no table needed", t => {
    const {$$, lane} = setup(t);
    assert.deepEqual($$("[data-lane]").map(node => node.dataset.laneLabel), ["Novo", "Levantamento", "Ganho", "Em branco"]);
    assert.deepEqual($$("[data-lane-count]").map(node => node.textContent), ["1", "1", "1", "1"]);
    assert.match(lane(2).querySelector("[data-lane-total]").textContent, /R\$ 2\.500\.000,00/);
    assert.equal(lane("blank").querySelector("[data-lane-total]").textContent.trim(), "R$ 0,00"); // tem item, mas sem valor
    assert.deepEqual($$("[data-card]").map(node => node.dataset.itemId), ["102", "101", "103", "104"]);
});

test("cards show the chosen fields; cards are draggable only for who can edit items", t => {
    const {$$, card} = setup(t);
    assert.equal(card(101).querySelectorAll("[data-cell]").length, 5);
    assert.deepEqual(Array.from(card(101).querySelectorAll("[data-cell]")).map(n => n.dataset.columnId), ["11", "12", "13", "14", "15"]);
    assert.equal(card(101).getAttribute("draggable"), "true");
    const viewer = setup(t, {fixture: VIEWER});
    assert.equal(viewer.$$("[draggable=true]").length, 0);
    assert.equal(viewer.$("[data-kanban-add]"), null);
    assert.equal(viewer.$("[data-card-menu]"), null);
    assert.ok($$("[data-view-menu]").length >= 1); // quem edita o quadro gerencia as abas
    assert.equal(viewer.$("[data-view-menu]"), null);
});

test("viewer: nothing opens and nothing is sent", async t => {
    const {$$, click, card, calls, key} = setup(t, {fixture: VIEWER});
    click(card(101).querySelector('[data-column-id="11"]'));
    click(card(101).querySelector("[data-card-title]"));
    key(card(101).querySelector('[data-column-id="15"]'), "Enter");
    await flush();
    assert.equal($$(".board-inline-input, .board-pop").length, 0);
    assert.equal(calls.length, 0);
});

// ---------------------------------------------------------------------------------------------------
// Arrastar cartão
// ---------------------------------------------------------------------------------------------------

test("dragging a card to another lane saves the label, updates counts at once and then redraws the lanes", async t => {
    const respond = call => call.url.endsWith("/lanes/") ? jsonResponse(lanesPayload()) : jsonResponse({ok: true, display: "Ganho", cell_html: "<td></td>"});
    const {w, $$, lane, card, calls, drag} = setup(t, {respond});
    const source = card(101);
    source.dispatchEvent(drag("dragstart"));
    assert.ok(source.classList.contains("is-dragging"));
    const over = drag("dragover");
    lane(3).querySelector("[data-card-title]").dispatchEvent(over);
    assert.equal(over.defaultPrevented, true);
    assert.ok(lane(3).classList.contains("is-drop-target"));
    lane(3).querySelector("[data-card-title]").dispatchEvent(drag("drop"));
    // otimista: o cartão já está na raia nova e as contagens acompanharam
    assert.equal(source.closest("[data-lane]"), lane(3));
    assert.equal(lane(2).querySelector("[data-lane-count]").textContent, "0");
    assert.equal(lane(3).querySelector("[data-lane-count]").textContent, "2");
    assert.equal(lane(2).querySelector("[data-lane-empty]").hidden, false);
    assert.ok(!source.classList.contains("is-dragging"));
    assert.equal(w.document.querySelectorAll(".is-drop-target").length, 0);
    await flush();
    assert.equal(calls[0].url, "/quadros/itens/101/colunas/13/valor/");
    assert.deepEqual(calls[0].body, {value: 3});
    assert.equal(calls[1].url, "/quadros/visoes/5/lanes/");
    assert.deepEqual($$("[data-lane]").map(node => node.dataset.laneLabel), ["Novo", "Ganho"]); // o servidor redistribuiu
});

test("dropping on the blank lane sends an empty value; dropping on the same lane sends nothing", async t => {
    const {lane, card, calls, drag} = setup(t);
    card(101).dispatchEvent(drag("dragstart"));
    lane("blank").querySelector("[data-lane-body]").dispatchEvent(drag("dragover"));
    lane("blank").querySelector("[data-lane-body]").dispatchEvent(drag("drop"));
    await flush();
    assert.deepEqual(calls[0].body, {value: ""});
    const same = setup(t);
    same.card(101).dispatchEvent(same.drag("dragstart"));
    const over = same.drag("dragover");
    same.lane(2).querySelector("[data-lane-body]").dispatchEvent(over);
    assert.ok(!same.lane(2).classList.contains("is-drop-target")); // a própria raia não é destino
    same.lane(2).querySelector("[data-lane-body]").dispatchEvent(same.drag("drop"));
    await flush();
    assert.equal(same.calls.length, 0);
});

test("a refused move puts the card back in its lane, restores the counts and warns", async t => {
    const {$, lane, card, calls, drag} = setup(t, {respond: () => jsonResponse({ok: false, error: "“Status” é obrigatória."}, 400)});
    const source = card(101);
    source.dispatchEvent(drag("dragstart"));
    lane(3).querySelector("[data-lane-body]").dispatchEvent(drag("drop"));
    assert.equal(source.closest("[data-lane]"), lane(3));
    await flush();
    assert.equal(calls.length, 1); // não pediu as raias: nada mudou no servidor
    assert.equal(source.closest("[data-lane]"), lane(2));
    assert.equal(lane(2).querySelector("[data-lane-count]").textContent, "1");
    assert.equal(lane(3).querySelector("[data-lane-count]").textContent, "1");
    assert.equal($("[data-board-toasts] .board-toast.is-error").textContent, "“Status” é obrigatória.");
});

test("the card menu offers the other lanes as an alternative to dragging; deleting needs its own permission", t => {
    const {$$, click, card} = setup(t, {fixture: EDITOR});
    click(card(102).querySelector("[data-card-menu]"));
    const labels = $$(".board-pop .board-menu__item").map(node => node.textContent);
    assert.deepEqual(labels, ["Levantamento", "Ganho", "Em branco", "Renomear"]); // o perfil de preenchimento não exclui itens
});

test("card menu: move, rename and delete with confirmation", async t => {
    const {$, $$, click, card, lane, calls} = setup(t, {respond: call => call.url.endsWith("/lanes/") ? jsonResponse(lanesPayload()) : jsonResponse({ok: true})});
    click(card(102).querySelector("[data-card-menu]"));
    const labels = $$(".board-pop .board-menu__item").map(node => node.textContent);
    assert.deepEqual(labels, ["Levantamento", "Ganho", "Em branco", "Renomear", "Excluir item"]);
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Ganho"));
    assert.equal(card(102).closest("[data-lane]"), lane(3));
    await flush();
    assert.deepEqual(calls[0].body, {value: 3});

    click($("[data-lane] [data-card-menu]"));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Excluir item"));
    assert.match($(".board-dialog__body").textContent, /Excluir “/);
    click($$(".board-dialog .btn--danger")[0]);
    await flush();
    assert.ok(calls.some(call => /\/excluir\/$/.test(call.url)));
});

// ---------------------------------------------------------------------------------------------------
// Editar no cartão
// ---------------------------------------------------------------------------------------------------

test("the card title renames inline", async t => {
    const {click, key, card, calls} = setup(t, {respond: () => jsonResponse({ok: true, name: "Arena Sul"})});
    click(card(101).querySelector("[data-card-title]"));
    const input = card(101).querySelector(".board-inline-input");
    assert.equal(input.value, "Arena Norte");
    input.value = "Arena Sul";
    key(input, "Enter");
    assert.equal(card(101).querySelector("[data-card-title]").textContent, "Arena Sul");
    await flush();
    assert.equal(calls[0].url, "/quadros/itens/101/renomear/");
    assert.deepEqual(calls[0].body, {name: "Arena Sul"});
});

test("a refused title rename restores the text", async t => {
    const {click, key, card, calls} = setup(t, {respond: () => jsonResponse({ok: false, error: "Sem permissão."}, 403)});
    click(card(101).querySelector("[data-card-title]"));
    const input = card(101).querySelector(".board-inline-input");
    input.value = "Outro";
    key(input, "Enter");
    await flush();
    assert.equal(calls.length, 1);
    assert.equal(card(101).querySelector("[data-card-title]").textContent, "Arena Norte");
});

test("a text field on the card edits inline and keeps the same element (it is not a table cell)", async t => {
    const respond = () => jsonResponse({ok: true, display: "Novo cliente",
        cell_html: '<td class="board-td" data-cell data-item-id="101" data-column-id="11" data-type="TEXT" data-value="Novo cliente"><span class="board-text">Novo cliente</span></td>'});
    const {click, key, card, calls} = setup(t, {respond});
    const field = card(101).querySelector('[data-column-id="11"]');
    click(field);
    const input = field.querySelector(".board-inline-input");
    assert.equal(input.value, "Shopping Norte");
    input.value = "Novo cliente";
    key(input, "Enter");
    assert.equal(field.textContent.trim(), "Novo cliente");
    await flush();
    assert.deepEqual(calls[0].body, {value: "Novo cliente"});
    assert.equal(calls.length, 1); // coluna comum: não precisa redistribuir as raias
    assert.equal(card(101).querySelector('[data-column-id="11"]'), field);
    assert.equal(field.tagName, "DD");
    assert.equal(field.dataset.value, "Novo cliente");
    assert.ok(!field.classList.contains("is-saving"));
});

test("a failed field save brings the old value back on the card", async t => {
    const {click, key, card} = setup(t, {respond: () => jsonResponse({ok: false, error: "Informe um número válido."}, 400)});
    const field = card(101).querySelector('[data-column-id="15"]');
    click(field);
    const input = field.querySelector(".board-inline-input");
    input.value = "abc";
    key(input, "Enter");
    await flush();
    assert.match(card(101).querySelector('[data-column-id="15"]').textContent, /R\$ 2\.500\.000,00/);
});

test("changing the group column from a card (o status field) redistributes the lanes", async t => {
    const respond = call => call.url.endsWith("/lanes/") ? jsonResponse(lanesPayload()) : jsonResponse({ok: true, display: "Ganho", cell_html: ""});
    const {$$, click, card, calls} = setup(t, {respond, fixture: FULL});
    const field = card(101).querySelector('[data-column-id="13"]'); // o Status também é um campo do cartão
    assert.equal(field.dataset.value, "2");
    click(field);
    click($$(".board-pop .board-option").find(node => node.textContent === "Ganho"));
    await flush();
    assert.deepEqual(calls[0].body, {value: 3});
    assert.equal(calls[1].url, "/quadros/visoes/5/lanes/");
});

// ---------------------------------------------------------------------------------------------------
// Criar na raia
// ---------------------------------------------------------------------------------------------------

test("adding in a lane creates the item already filled with that label, redraws and starts renaming", async t => {
    const withNew = lanesPayload({lanes_html: LANES_HTML(true).replace('<p data-lane-empty hidden></p></div>\n  <footer>', '<article class="kanban-card" data-card data-item-id="200" draggable="true"><span data-card-title class="is-empty">Sem título</span></article><p data-lane-empty hidden></p></div>\n  <footer>')});
    const respond = call => call.url.endsWith("/lanes/") ? jsonResponse(withNew) : jsonResponse({ok: true, item: {id: 200, group_id: 1, name: ""}, row_html: "<tr></tr>"});
    const {click, lane, card, calls} = setup(t, {respond});
    click(lane(1).querySelector("[data-kanban-add]"));
    await flush();
    assert.equal(calls[0].url, "/quadros/1/itens/novo/");
    assert.deepEqual(calls[0].body, {group_id: 1, name: "", initial: {column_id: 13, value: 1}});
    assert.equal(calls[1].url, "/quadros/visoes/5/lanes/");
    assert.ok(card(200));
    assert.ok(card(200).querySelector(".board-inline-input"));
});

test("adding in the blank lane sends an empty initial value", async t => {
    const {click, lane, calls} = setup(t, {respond: call => call.url.endsWith("/lanes/") ? jsonResponse(lanesPayload()) : jsonResponse({ok: true, item: {id: 201, group_id: 1, name: ""}})});
    const blank = lane("blank");
    assert.equal(blank.querySelector("[data-kanban-add]") !== null, true);
    click(blank.querySelector("[data-kanban-add]"));
    await flush();
    assert.deepEqual(calls[0].body.initial, {column_id: 13, value: ""});
});

test("a refused creation shows the message and does not redraw", async t => {
    const {$, click, lane, calls} = setup(t, {respond: () => jsonResponse({ok: false, error: "Opção inválida."}, 400)});
    click(lane(1).querySelector("[data-kanban-add]"));
    await flush();
    assert.equal(calls.length, 1);
    assert.equal($("[data-board-toasts] .board-toast.is-error").textContent, "Opção inválida.");
});

// ---------------------------------------------------------------------------------------------------
// Raias: etiqueta
// ---------------------------------------------------------------------------------------------------

test("renaming a lane renames the label and redraws", async t => {
    const respond = call => call.url.endsWith("/lanes/") ? jsonResponse(lanesPayload()) : jsonResponse({ok: true, option: {id: 2, label: "Em execução", color: "#66CCFF", is_default: false, is_done: false}});
    const {$$, click, key, lane, calls} = setup(t, {respond});
    click(lane(2).querySelector("[data-lane-menu]"));
    assert.deepEqual($$(".board-pop .board-menu__item").map(node => node.textContent), ["Renomear etiqueta", "Mudar a cor", "Editar etiquetas"]);
    click($$(".board-pop .board-menu__item")[0]);
    const input = lane(2).querySelector(".board-inline-input");
    assert.equal(input.value, "Levantamento");
    input.value = "Em execução";
    key(input, "Enter");
    assert.equal(lane(2).querySelector("[data-lane-title]").textContent, "Em execução");
    await flush();
    assert.equal(calls[0].url, "/quadros/etiquetas/2/editar/");
    assert.deepEqual(calls[0].body, {label: "Em execução"});
    assert.equal(calls[1].url, "/quadros/visoes/5/lanes/");
});

test("double click on a lane title renames; the blank lane has no menu and cannot be renamed", async t => {
    const {w, lane} = setup(t);
    lane(2).querySelector("[data-lane-title]").dispatchEvent(new w.MouseEvent("click", {bubbles: true, detail: 2}));
    assert.ok(lane(2).querySelector(".board-inline-input"));
    assert.equal(lane("blank").querySelector("[data-lane-menu]"), null);
    lane("blank").querySelector("[data-lane-title]").dispatchEvent(new w.MouseEvent("click", {bubbles: true, detail: 2}));
    assert.equal(lane("blank").querySelector(".board-inline-input"), null);
});

test("changing a lane color uses the palette and redraws", async t => {
    const respond = call => call.url.endsWith("/lanes/") ? jsonResponse(lanesPayload()) : jsonResponse({ok: true});
    const {$$, click, lane, calls} = setup(t, {respond});
    click(lane(2).querySelector("[data-lane-menu]"));
    click($$(".board-pop .board-menu__item")[1]);
    click($$(".board-pop .board-swatch")[2]);
    await flush();
    assert.equal(calls[0].url, "/quadros/etiquetas/2/editar/");
    assert.deepEqual(calls[0].body, {color: "#E2445C"});
    assert.equal(calls[1].url, "/quadros/visoes/5/lanes/");
});

test("editing labels from a lane opens the labels dialog and redraws the lanes when it closes", async t => {
    const respond = call => {
        if (call.url.endsWith("/lanes/")) return jsonResponse(lanesPayload());
        if (call.url.endsWith("/etiquetas/novo/")) return jsonResponse({ok: true, option: {id: 40, label: "Em revisão", color: "#C4C4C4", is_default: false, is_done: false}});
        return jsonResponse({ok: true});
    };
    const {$, $$, click, lane, calls} = setup(t, {respond});
    click(lane(2).querySelector("[data-lane-menu]"));
    click($$(".board-pop .board-menu__item")[2]);
    assert.equal($$(".board-label-row").length, 3);
    $(".board-label-add input").value = "Em revisão";
    click($(".board-label-add .btn"));
    await flush();
    click($$(".board-dialog__foot .btn").find(node => node.textContent === "Concluir"));
    await flush();
    assert.equal(calls[calls.length - 1].url, "/quadros/visoes/5/lanes/");
    assert.ok(!calls.some(call => call.url.endsWith("/fragmento/"))); // no Kanban não existe o fragmento da tabela
});

// ---------------------------------------------------------------------------------------------------
// Barra de ferramentas e configuração
// ---------------------------------------------------------------------------------------------------

test("group-by and sort selects save the view and redraw", async t => {
    const respond = call => call.url.endsWith("/lanes/") ? jsonResponse(lanesPayload({group_column_id: 18})) : jsonResponse({ok: true, view: {id: 5, name: "Kanban por Status"}, settings: {...FULL.meta.kanban.settings, group_by: 18}});
    const {w, $, calls} = setup(t, {respond});
    const group = $("[data-kanban-group-by]");
    assert.equal(group.value, "13");
    assert.deepEqual(Array.from(group.options).map(o => o.textContent), ["Status", "Setor"]);
    group.value = "18";
    group.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.equal(calls[0].url, "/quadros/visoes/5/editar/");
    assert.deepEqual(calls[0].body, {settings: {group_by: 18}});
    assert.equal(calls[1].url, "/quadros/visoes/5/lanes/");
    assert.equal($("[data-kanban-group-by]").value, "18");

    const sort = $("[data-kanban-sort]");
    assert.equal(sort.value, "manual|asc");
    sort.value = "15|desc";
    sort.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.deepEqual(calls[2].body, {settings: {sort: {by: 15, dir: "desc"}}});
    sort.value = "name|asc";
    sort.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.deepEqual(calls[4].body, {settings: {sort: {by: "name", dir: "asc"}}});
});

test("a refused group-by puts the select back", async t => {
    const {w, $, calls} = setup(t, {respond: () => jsonResponse({ok: false, error: "Escolha uma coluna de Status ou de Lista suspensa para agrupar."}, 400)});
    const group = $("[data-kanban-group-by]");
    group.value = "18";
    group.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.equal(calls.length, 1);
    assert.equal($("[data-kanban-group-by]").value, "13");
    assert.match($("[data-board-toasts] .board-toast.is-error").textContent, /Status ou de Lista/);
});

test("the search form keeps working as plain GET (no JavaScript needed)", t => {
    const {$} = setup(t);
    const form = $("[data-board-toolbar]");
    assert.equal(form.method, "get");
    assert.ok(form.querySelector("input[name=q]"));
    assert.ok(form.querySelector("select[name=pessoa]"));
});

test("card configuration: toggles save by themselves and the preview follows the first card", async t => {
    const respond = call => call.url.endsWith("/lanes/") ? jsonResponse(lanesPayload()) : jsonResponse({ok: true, view: {id: 5, name: "x"}, settings: FULL.meta.kanban.settings});
    const {w, $, $$, click, calls, runTimers} = setup(t, {respond});
    click($("[data-kanban-config]"));
    const dialog = $(".board-dialog");
    assert.ok(dialog.classList.contains("board-dialog--wide"));
    assert.ok($(".kanban-config__preview .kanban-card"));
    assert.equal($(".kanban-config__preview .kanban-card").getAttribute("draggable"), null);
    assert.equal($(".kanban-config__preview [data-cell]"), null); // a pré-visualização não é editável

    const names = $$(".kanban-config__field label").map(node => node.textContent.trim());
    assert.deepEqual(names.slice(0, 5), ["Cliente", "Responsável", "Status", "Prazo", "Valor"]); // os do cartão primeiro, na ordem
    const boxes = $$(".kanban-config__field input[type=checkbox]");
    assert.deepEqual(boxes.map(box => box.checked), [true, true, true, true, true, false, false, false]);

    const showEmpty = $$(".kanban-config__controls input[type=checkbox]")[0];
    showEmpty.checked = false;
    showEmpty.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.deepEqual(calls[0].body, {settings: {show_empty: false}});
    assert.equal(calls[1].url, "/quadros/visoes/5/lanes/");

    // campos do cartão: marcar um novo e subir outro; grava uma vez, depois da pausa
    boxes[5].checked = true;
    boxes[5].dispatchEvent(new w.Event("change", {bubbles: true}));
    $$(".kanban-config__field button").find(node => node.getAttribute("aria-label") === "Subir Valor").click();
    assert.equal(calls.length, 2);
    runTimers();
    await flush();
    assert.equal(calls[2].url, "/quadros/visoes/5/editar/");
    assert.deepEqual(JSON.parse(JSON.stringify(calls[2].body.settings.card_fields)), [11, 12, 13, 15, 14, 16]); // Valor subiu, Probabilidade entrou
});

test("card configuration: sum column, blank lane and field names", async t => {
    const respond = call => call.url.endsWith("/lanes/") ? jsonResponse(lanesPayload()) : jsonResponse({ok: true, view: {id: 5, name: "x"}, settings: FULL.meta.kanban.settings});
    const {w, $, $$, click, calls} = setup(t, {respond});
    click($("[data-kanban-config]"));
    const selects = $$(".kanban-config__controls select");
    assert.deepEqual(Array.from(selects[0].options).map(o => o.value), ["auto", "always", "never"]);
    selects[0].value = "never";
    selects[0].dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.deepEqual(calls[0].body, {settings: {blank_lane: "never"}});
    assert.deepEqual(Array.from(selects[1].options).map(o => o.textContent), ["Não somar", "Valor", "Probabilidade"]);
    assert.equal(selects[1].value, "15");
    selects[1].value = "";
    selects[1].dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.deepEqual(calls[2].body, {settings: {sum_column: null}});
    const names = $$(".kanban-config__controls input[type=checkbox]")[1];
    names.checked = true;
    names.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.deepEqual(calls[4].body, {settings: {show_field_names: true}});
});

// ---------------------------------------------------------------------------------------------------
// Abas
// ---------------------------------------------------------------------------------------------------

test("tabs: main table first, the Kanbans after, current one marked, + only for who edits", t => {
    const {$, $$} = setup(t);
    assert.deepEqual($$(".board-tab span").map(node => node.textContent), ["Quadro principal", "Kanban por Status", "Kanban por Setor"]);
    assert.equal($$(".board-tab.is-active").length, 1);
    assert.equal($$(".board-tab-wrap.is-active").length, 1);
    assert.equal($('[aria-current="page"]').textContent.trim(), "Kanban por Status");
    assert.ok($("[data-view-add]"));
    assert.equal(setup(t, {fixture: VIEWER}).$("[data-view-add]"), null);
});

test("adding a view: the dialog lists the types, Kanban and Calendar are available, and creating goes to the new view", async t => {
    const {$, $$, click, calls} = setup(t, {respond: () => jsonResponse({ok: true, view: {id: 9, name: "Kanban 2"}, redirect_url: "/quadros/visoes/9/"})});
    click($("[data-view-add]"));
    assert.deepEqual($$(".board-view-type strong").map(node => node.textContent), ["Tabela", "Kanban", "Calendário", "Linha do tempo", "Dashboard"]);
    assert.deepEqual($$(".board-view-type.is-disabled").map(node => node.querySelector("strong").textContent), ["Tabela", "Linha do tempo", "Dashboard"]);
    assert.equal($(".board-view-type.is-selected strong").textContent, "Kanban");
    const name = $(".board-dialog input[type=text]");
    assert.equal(name.value, "Kanban");
    name.value = "Kanban Comercial";
    click($$(".board-dialog .btn").find(node => node.textContent === "Criar visualização"));
    await flush();
    assert.equal(calls[0].url, "/quadros/1/visoes/novo/");
    assert.deepEqual(calls[0].body, {name: "Kanban Comercial", type: "KANBAN"});
});

test("a refused view creation keeps the dialog open with the message", async t => {
    const {$, $$, click} = setup(t, {respond: () => jsonResponse({ok: false, error: "Você não possui permissão."}, 403)});
    click($("[data-view-add]"));
    click($$(".board-dialog .btn").find(node => node.textContent === "Criar visualização"));
    await flush();
    assert.ok($(".board-dialog"));
    assert.equal($(".board-dialog__error").textContent, "Você não possui permissão.");
});

test("view menu: rename updates the tab text; delete asks first", async t => {
    const respond = call => call.url.endsWith("/editar/") ? jsonResponse({ok: true, view: {id: 6, name: "Por Setor"}, settings: {}}) : jsonResponse({ok: true, redirect_url: "/quadros/1/"});
    const {$, $$, click, calls} = setup(t, {respond});
    const menu = $$("[data-view-menu]").find(node => node.dataset.viewId === "6");
    click(menu);
    assert.deepEqual($$(".board-pop .board-menu__item").map(node => node.textContent), ["Renomear", "Excluir visualização"]);
    click($$(".board-pop .board-menu__item")[0]);
    const input = $(".board-dialog input[type=text]");
    assert.equal(input.value, "Kanban por Setor");
    input.value = "Por Setor";
    click($$(".board-dialog .btn").find(node => node.textContent === "Salvar"));
    await flush();
    assert.deepEqual(calls[0].body, {name: "Por Setor"});
    assert.equal($('a.board-tab[data-view-id="6"] span').textContent, "Por Setor");

    click($$("[data-view-menu]").find(node => node.dataset.viewId === "6"));
    click($$(".board-pop .board-menu__item")[1]);
    assert.match($(".board-dialog__body").textContent, /Os itens do quadro não são afetados/);
    assert.equal(calls.length, 1);
    click($$(".board-dialog .btn--danger")[0]);
    await flush();
    assert.equal(calls[1].url, "/quadros/visoes/6/excluir/");
});
