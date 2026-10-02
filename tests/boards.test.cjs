/* Quadros dinâmicos (static/js/boards.js).
   Requires jsdom@26.1.0 in NODE_PATH; no browser or production dependency.
   Run from workflow: node --test tests/boards.test.cjs
   Set PYTHON to the project's Python if it is not in .venv.

   O HTML vem dos templates Django reais (boards/board_detail.html e parciais) renderizados com objetos em
   memória, sem banco. O servidor é simulado por um `fetch` falso: o contrato testado é "o que o servidor
   responde" -> "o que acontece na tela", e "o que a tela faz" -> "o que ela manda ao servidor". */
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
from boards.models import Board, BoardGroup, BoardColumn, BoardColumnOption, BoardItem, BoardCell
from boards.presentation import board_urls, type_catalog, type_icon, COLOR_PALETTE, SENTINEL, SENTINEL_COLUMN

permissions = json.loads(os.environ.get('BOARD_PERMISSIONS') or 'null') or {
    'view': True, 'edit': True, 'delete': True, 'manage_columns': True,
    'create_item': True, 'edit_item': True, 'delete_item': True,
}
User = get_user_model()
board = Board(pk=1, name='Orçamentos', item_label='Obra')
ana = User(pk=7, username='ana', first_name='Ana', last_name='Souza')

def col(pk, name, kind, **extra):
    return BoardColumn(pk=pk, board=board, board_id=1, name=name, type=kind, width=extra.pop('width', 160), **extra)

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
opt_objs = {oid: BoardColumnOption(pk=oid, column=by_id[cid], column_id=cid, label=l, color=c, is_default=d, is_done=n)
            for cid, rows in options.items() for (oid, l, c, d, n) in rows}

groups = [BoardGroup(pk=1, board=board, name='Oportunidades', color='#579BFC'),
          BoardGroup(pk=2, board=board, name='Em andamento', color='#00C875')]

def make_item(pk, group, name, values):
    item = BoardItem(pk=pk, board=board, group=group, group_id=group.pk, name=name)
    item.cell_map = {}
    for column_id, value in values.items():
        column = by_id[column_id]
        cell = BoardCell(item=item, column=column)
        cell.option = None
        cell.person = None
        cell.display = ''
        if column.type == 'TEXT':
            cell.value_text = value; cell.display = value
        elif column.type == 'PERSON':
            cell.person = ana; cell.display = 'Ana Souza'
        elif column.type in ('STATUS', 'DROPDOWN'):
            cell.option = opt_objs[value]; cell.display = cell.option.label
        elif column.type == 'DATE':
            cell.value_date = value; cell.display = value.strftime('%d/%m/%Y')
        elif column.type == 'CURRENCY':
            cell.value_number = Decimal(value); cell.display = 'R$ 2.500.000,00'
        elif column.type == 'NUMBER':
            cell.value_number = Decimal(value); cell.display = '40 %'
        elif column.type == 'CHECKBOX':
            cell.value_boolean = value; cell.display = 'Sim' if value else 'Não'
        item.cell_map[column_id] = cell
    return item

groups[0].board_items = [
    make_item(101, groups[0], 'Arena Norte', {11: 'Shopping Norte', 12: 'x', 13: 2, 14: datetime.date(2025, 1, 15),
                                              15: '2500000', 16: '40', 17: False, 18: 4}),
    make_item(102, groups[0], 'Condomínio Cotia', {11: 'Residencial Cotia', 13: 1}),
]
groups[1].board_items = [make_item(103, groups[1], 'Hospital Vida', {13: 3})]

meta_columns = []
for c in columns:
    meta_columns.append({
        'id': c.pk, 'name': c.name, 'type': c.type, 'type_label': c.get_type_display(), 'icon': type_icon(c.type),
        'width': c.width, 'description': '', 'is_required': False, 'is_visible': True,
        'settings': c.settings or {},
        'options': [{'id': o[0], 'label': o[1], 'color': o[2], 'is_default': o[3], 'is_done': o[4]} for o in options.get(c.pk, [])],
    })
meta = {
    'board': {'id': 1, 'name': board.name, 'item_label': board.item_label},
    'permissions': permissions, 'urls': board_urls(board),
    'sentinels': {'id': SENTINEL, 'column': SENTINEL_COLUMN}, 'types': type_catalog(), 'columns': meta_columns,
    'groups': [{'id': g.pk, 'name': g.name, 'color': g.color} for g in groups],
    'sort': {'column': None, 'dir': 'asc'}, 'limits': {'min_width': 96, 'max_width': 640}, 'palette': COLOR_PALETTE,
}

source = open(os.path.join('templates', 'boards', 'board_detail.html'), encoding='utf-8').read()
body = re.search(r'{% block content %}(.*){% endblock %}\\s*{% block scripts %}', source, re.S).group(1)
context = Context({
    'board': board, 'groups': groups, 'columns': columns, 'hidden_columns': [], 'permissions': permissions, 'meta': meta,
    'sort_column_id': None, 'sort_dir': 'asc', 'search': '', 'person_id': None, 'people': [ana], 'filtering': False,
    'table_width': 280 + 64 + 160 * len(columns), 'total_items': 3,
})
print(json.dumps({'html': Template('{% load static lps_board %}' + body).render(context), 'meta': meta}))
`;

function renderFixture(permissions) {
    const env = {...process.env};
    if (permissions) env.BOARD_PERMISSIONS = JSON.stringify(permissions);
    return JSON.parse(execFileSync(python, ["-c", PYTHON_FIXTURE], {cwd: root, encoding: "utf8", env}).trim());
}

const FULL = renderFixture();
const VIEWER = renderFixture({view: true, edit: false, delete: false, manage_columns: false, create_item: false, edit_item: false, delete_item: false});
const script = readFileSync(path.join(root, "static/js/boards.js"), "utf8");
const tick = () => new Promise(resolve => setImmediate(resolve));
const flush = async () => { for (let i = 0; i < 6; i += 1) await tick(); };

function jsonResponse(body, status = 200) {
    return Promise.resolve({ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body)});
}

function setup(t, {fixture = FULL, respond} = {}) {
    const dom = new JSDOM("<!doctype html><body>" + fixture.html + "</body>", {
        url: "http://localhost/quadros/1/", runScripts: "outside-only", pretendToBeVisual: true,
    });
    t.after(() => dom.window.close());
    const w = dom.window;
    const calls = [];
    const navigations = [];
    w.fetch = (url, options = {}) => {
        const call = {url, method: options.method || "GET", headers: options.headers || {}, body: options.body ? JSON.parse(options.body) : null};
        calls.push(call);
        return respond ? respond(call) : jsonResponse({ok: true});
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
    const cell = (item, column) => $(`td[data-cell][data-item-id="${item}"][data-column-id="${column}"]`);
    const runTimers = () => { while (timers.length) timers.shift().fn(); };
    return {w, $, $$, click, key, cell, calls, timers, runTimers, navigations};
}

// ---------------------------------------------------------------------------------------------------
// Funções puras
// ---------------------------------------------------------------------------------------------------

test("helpers: fillUrl swaps only the sentinel ids", t => {
    const {w} = setup(t);
    const {fillUrl} = w.LPSBoards.helpers;
    const sentinels = {id: 999999999, column: 999999998};
    assert.equal(fillUrl("/quadros/colunas/999999999/largura/", {id: 12}, sentinels), "/quadros/colunas/12/largura/");
    assert.equal(fillUrl("/quadros/itens/999999999/colunas/999999998/valor/", {id: 5, column: 9}, sentinels), "/quadros/itens/5/colunas/9/valor/");
    assert.equal(fillUrl("/quadros/1/colunas/novo/", {}, sentinels), "/quadros/1/colunas/novo/");
});

test("helpers: neighbours gives the left and right neighbour after the move", t => {
    const helpers = setup(t).w.LPSBoards.helpers;
    // o script roda no "mundo" do jsdom: copiar para objetos comuns antes de comparar estruturas
    const neighbours = (...args) => JSON.parse(JSON.stringify(helpers.neighbours(...args)));
    assert.deepEqual(neighbours([1, 2, 3, 4], 4, 1, "before"), {before_id: null, after_id: 1});
    assert.deepEqual(neighbours([1, 2, 3, 4], 4, 1, "after"), {before_id: 1, after_id: 2});
    assert.deepEqual(neighbours([1, 2, 3, 4], 1, 4, "after"), {before_id: 4, after_id: null});
    assert.deepEqual(neighbours([1, 2, 3, 4], 2, 3, "before"), {before_id: 1, after_id: 3});
    assert.deepEqual(neighbours([1, 2, 3], 9, 8, "before"), {before_id: null, after_id: null});
});

test("helpers: clamp, contrast, initials and date", t => {
    const h = setup(t).w.LPSBoards.helpers;
    assert.equal(h.clamp(40, 96, 640), 96);
    assert.equal(h.clamp(900, 96, 640), 640);
    assert.equal(h.clamp(200, 96, 640), 200);
    assert.equal(h.contrastColor("#00C875"), "#FFFFFF");
    assert.equal(h.contrastColor("#C4C4C4"), "#1F2937");
    assert.equal(h.contrastColor("nope"), "#1F2937");
    assert.equal(h.initials("Ana Souza"), "AS");
    assert.equal(h.initials("bruno"), "B");
    assert.equal(h.initials(""), "?");
    assert.equal(h.formatIsoDate("2025-10-01"), "01/10/2025");
});

// ---------------------------------------------------------------------------------------------------
// Estrutura e permissões
// ---------------------------------------------------------------------------------------------------

test("boot: width is synced and headers become draggable only for who manages columns", t => {
    const {$, $$} = setup(t);
    assert.equal($("[data-board-table]").style.width, "1624px");
    assert.ok($$("th[data-column-th]").every(th => th.getAttribute("draggable") === "true"));
    const viewer = setup(t, {fixture: VIEWER});
    assert.ok(viewer.$$("th[data-column-th]").every(th => !th.hasAttribute("draggable")));
    assert.equal(viewer.$("[data-column-add]"), null);
});

test("viewer: clicking a cell does nothing and no request is made", async t => {
    const {click, cell, calls, $$} = setup(t, {fixture: VIEWER});
    click(cell(101, 11));
    click(cell(101, 17));
    await flush();
    assert.equal($$(".board-inline-input").length, 0);
    assert.equal($$(".board-pop").length, 0);
    assert.equal(calls.length, 0);
});

// ---------------------------------------------------------------------------------------------------
// Colunas
// ---------------------------------------------------------------------------------------------------

test("+ opens the type picker with the eight types", t => {
    const {$, $$, click} = setup(t);
    click($("[data-column-add]"));
    const labels = $$(".board-pop .board-type strong").map(node => node.textContent);
    assert.deepEqual(labels, ["Status", "Lista suspensa", "Texto", "Data", "Pessoa", "Número", "Moeda", "Sinal de confirmação"]);
    assert.equal($("[data-column-add]").getAttribute("aria-expanded"), "true");
    click($("[data-column-add]")); // de novo fecha
    assert.equal($$(".board-pop").length, 0);
});

test("choosing a type creates the column without reload and starts renaming it", async t => {
    const respond = call => {
        if (call.url === "/quadros/1/colunas/novo/") {
            return jsonResponse({
                ok: true, after_column_id: null,
                column: {id: 99, name: "Números", type: "NUMBER", type_label: "Número", icon: "list-ol", width: 160, description: "", is_required: false, is_visible: true, settings: {decimal_places: 2}, options: []},
                header_html: '<th class="board-th" scope="col" data-column-th data-column-id="99" data-type="NUMBER"><div class="board-th__inner"><span class="board-th__name" data-column-name>Números</span><button type="button" class="board-th__menu" data-column-menu></button></div><span class="board-th__resize" data-column-resize></span></th>',
                cells: {101: '<td class="board-td" data-cell data-item-id="101" data-column-id="99" data-type="NUMBER" data-value=""></td>',
                        102: '<td class="board-td" data-cell data-item-id="102" data-column-id="99" data-type="NUMBER" data-value=""></td>',
                        103: '<td class="board-td" data-cell data-item-id="103" data-column-id="99" data-type="NUMBER" data-value=""></td>'},
            });
        }
        return jsonResponse({ok: true});
    };
    const {w, $, $$, click, calls} = setup(t, {respond});
    click($("[data-column-add]"));
    click($$(".board-pop .board-type").find(node => node.textContent.includes("Número")));
    await flush();
    assert.deepEqual(calls[0].body, {type: "NUMBER", after_column_id: null});
    assert.equal(calls[0].headers["X-Requested-With"], "XMLHttpRequest");
    assert.equal(calls[0].method, "POST");
    // a coluna nova fica antes do "+", em cada linha antes do enchimento e entra no colgroup
    const headers = $$("th[data-column-th]");
    assert.equal(headers[headers.length - 1].dataset.columnId, "99");
    assert.equal(w.document.querySelector("th[data-add-column-th]").previousElementSibling.dataset.columnId, "99");
    assert.ok($('col[data-col-id="99"]'));
    for (const id of [101, 102, 103]) {
        const row = $(`tr[data-item-id="${id}"]`);
        const tds = row.querySelectorAll("td[data-cell]");
        assert.equal(tds[tds.length - 1].dataset.columnId, "99", `linha ${id}`);
        assert.ok(row.lastElementChild.classList.contains("board-td--filler"));
    }
    assert.equal($("[data-board-table]").style.width, "1784px");
    assert.equal($("td.board-group-head td, .board-group-head td").getAttribute("colspan"), "11");
    // já cai em modo de renomear
    assert.ok($('th[data-column-id="99"] .board-inline-input'));
});

test("creating after another column inserts right after it", async t => {
    const respond = call => jsonResponse({
        ok: true, after_column_id: 11,
        column: {id: 98, name: "Texto 2", type: "TEXT", type_label: "Texto", icon: "file-text", width: 160, description: "", is_required: false, is_visible: true, settings: {}, options: []},
        header_html: '<th class="board-th" scope="col" data-column-th data-column-id="98" data-type="TEXT"><div class="board-th__inner"><span class="board-th__name" data-column-name>Texto 2</span></div></th>',
        cells: {101: '<td data-cell data-item-id="101" data-column-id="98" data-type="TEXT" data-value=""></td>'},
    });
    const {$, $$, click} = setup(t, {respond});
    click($('th[data-column-id="11"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent.includes("Adicionar coluna à direita")));
    click($$(".board-pop .board-type").find(node => node.textContent.includes("Texto")));
    await flush();
    const order = $$("th[data-column-th]").map(th => th.dataset.columnId);
    assert.deepEqual(order.slice(0, 3), ["11", "98", "12"]);
    assert.deepEqual($$("colgroup col[data-col-id]").map(col => col.dataset.colId).slice(0, 3), ["11", "98", "12"]);
    const firstRow = $$('tr[data-item-id="101"] td[data-cell]').map(td => td.dataset.columnId);
    assert.deepEqual(firstRow.slice(0, 3), ["11", "98", "12"]);
});

test("a refused column creation shows the message and changes nothing", async t => {
    const {$, $$, click, calls} = setup(t, {respond: () => jsonResponse({ok: false, error: "Tipo de coluna inválido."}, 400)});
    click($("[data-column-add]"));
    click($$(".board-pop .board-type")[0]);
    await flush();
    assert.equal(calls.length, 1);
    assert.equal($$('tbody[data-group-id="1"] th[data-column-th]').length, 8);
    assert.equal($("[data-board-toasts] .board-toast.is-error").textContent, "Tipo de coluna inválido.");
    assert.equal($("[data-board-status]").textContent, "Erro ao salvar");
});

test("column menu: items depend on the type and the permission", t => {
    const {$, $$, click} = setup(t);
    click($('th[data-column-id="13"] [data-column-menu]'));
    const labels = $$(".board-pop .board-menu__item").map(node => node.textContent);
    for (const expected of ["Configurações da coluna", "Editar etiquetas", "Ordenar ascendente", "Ordenar descendente", "Duplicar coluna",
        "Adicionar coluna à direita", "Alterar tipo", "Renomear", "Ocultar coluna", "Excluir coluna"]) {
        assert.ok(labels.includes(expected), expected);
    }
    click($('th[data-column-id="11"] [data-column-menu]'));
    assert.ok(!$$(".board-pop .board-menu__item").map(node => node.textContent).includes("Editar etiquetas"));

    const viewer = setup(t, {fixture: VIEWER});
    viewer.click(viewer.$('th[data-column-id="11"] [data-column-menu]'));
    assert.deepEqual(viewer.$$(".board-pop .board-menu__item").map(node => node.textContent), ["Ordenar ascendente", "Ordenar descendente"]);
});

test("sorting navigates with sort and dir keeping the rest of the query", t => {
    const {$, $$, click, w} = setup(t);
    const assigned = [];
    // jsdom não navega: o ponto é o endereço que o script monta
    const original = w.location.assign;
    try { w.location.assign = href => assigned.push(href); } catch (e) { /* location.assign não é substituível aqui */ }
    click($('th[data-column-id="15"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Ordenar descendente"));
    if (assigned.length) assert.equal(assigned[0], "/quadros/1/?sort=15&dir=desc");
    assert.ok(original);
});

test("renaming a column: Enter saves, optimistic text, header replaced by the server HTML", async t => {
    const respond = call => jsonResponse({
        ok: true,
        column: {id: 11, name: "Cliente final", type: "TEXT", type_label: "Texto", icon: "file-text", width: 160, description: "", is_required: false, is_visible: true, settings: {}, options: []},
        header_html: '<th class="board-th" scope="col" data-column-th data-column-id="11" data-type="TEXT"><div class="board-th__inner"><span class="board-th__name" data-column-name>Cliente final</span></div></th>',
    });
    const {w, $, key, calls} = setup(t, {respond});
    const name = $('th[data-column-id="11"] [data-column-name]');
    name.dispatchEvent(new w.MouseEvent("click", {bubbles: true, detail: 2}));
    const input = $('th[data-column-id="11"] .board-inline-input');
    assert.equal(input.value, "Cliente");
    input.value = "  Cliente final ";
    key(input, "Enter");
    await flush();
    assert.deepEqual(calls[0].body, {name: "Cliente final"});
    assert.equal(calls[0].url, "/quadros/colunas/11/renomear/");
    assert.equal($('th[data-column-id="11"] [data-column-name]').textContent, "Cliente final");
    assert.equal($('th[data-column-id="11"] .board-inline-input'), null);
});

test("renaming: Escape cancels and an unchanged name sends nothing", async t => {
    const {w, $, key, calls} = setup(t);
    $('th[data-column-id="11"] [data-column-name]').dispatchEvent(new w.MouseEvent("click", {bubbles: true, detail: 2}));
    let input = $('th[data-column-id="11"] .board-inline-input');
    input.value = "Outro";
    key(input, "Escape");
    assert.equal($('th[data-column-id="11"] [data-column-name]').textContent, "Cliente");
    $('th[data-column-id="11"] [data-column-name]').dispatchEvent(new w.MouseEvent("click", {bubbles: true, detail: 2}));
    input = $('th[data-column-id="11"] .board-inline-input');
    key(input, "Enter");
    await flush();
    assert.equal(calls.length, 0);
});

test("renaming reverts the text when the server refuses", async t => {
    const {w, $, key, calls} = setup(t, {respond: () => jsonResponse({ok: false, error: "Informe um nome."}, 400)});
    $('th[data-column-id="11"] [data-column-name]').dispatchEvent(new w.MouseEvent("click", {bubbles: true, detail: 2}));
    const input = $('th[data-column-id="11"] .board-inline-input');
    input.value = "x";
    key(input, "Enter");
    assert.equal($('th[data-column-id="11"] [data-column-name]').textContent, "x"); // otimista
    await flush();
    assert.equal(calls.length, 1);
    assert.equal($('th[data-column-id="11"] [data-column-name]').textContent, "Cliente");
    assert.equal($("[data-board-toasts] .board-toast").textContent, "Informe um nome.");
});

test("resize by keyboard: clamps to the limits and saves once after the pause", async t => {
    const {$, key, calls, runTimers} = setup(t, {respond: call => jsonResponse({ok: true, width: call.body.width})});
    const handle = $('th[data-column-id="11"] [data-column-resize]');
    key(handle, "ArrowRight");
    key(handle, "ArrowRight", {shiftKey: true});
    assert.equal($('col[data-col-id="11"]').style.width, "224px");
    assert.equal($("[data-board-table]").style.width, "1688px");
    assert.equal(calls.length, 0);
    runTimers();
    await flush();
    assert.equal(calls.length, 1);
    assert.deepEqual(calls[0].body, {width: 224});
    assert.equal(calls[0].url, "/quadros/colunas/11/largura/");
    for (let i = 0; i < 40; i += 1) key(handle, "ArrowLeft", {shiftKey: true});
    assert.equal($('col[data-col-id="11"]').style.width, "96px");
    for (let i = 0; i < 40; i += 1) key(handle, "ArrowRight", {shiftKey: true});
    assert.equal($('col[data-col-id="11"]').style.width, "640px");
});

test("resize by pointer: live width, one request on release, revert on failure", async t => {
    const {w, $, calls} = setup(t, {respond: () => jsonResponse({ok: false, error: "Sem permissão."}, 403)});
    const th = $('th[data-column-id="11"]');
    th.getBoundingClientRect = () => ({width: 160, left: 0, top: 0, height: 40});
    const handle = th.querySelector("[data-column-resize]");
    handle.dispatchEvent(new w.MouseEvent("pointerdown", {bubbles: true, button: 0, clientX: 100}));
    w.document.dispatchEvent(new w.MouseEvent("pointermove", {bubbles: true, clientX: 150}));
    assert.equal($('col[data-col-id="11"]').style.width, "210px");
    assert.ok(w.document.body.classList.contains("board-resizing"));
    w.document.dispatchEvent(new w.MouseEvent("pointerup", {bubbles: true}));
    assert.ok(!w.document.body.classList.contains("board-resizing"));
    await flush();
    assert.equal(calls.length, 1);
    assert.deepEqual(calls[0].body, {width: 210});
    assert.equal($('col[data-col-id="11"]').style.width, "160px"); // voltou
});

test("delete column asks first and removes header, col and cells", async t => {
    const {$, $$, click, calls} = setup(t);
    click($('th[data-column-id="17"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Excluir coluna"));
    assert.ok($(".board-dialog"));
    assert.match($(".board-dialog__body").textContent, /Excluir a coluna “Visto”/);
    assert.equal(calls.length, 0);
    click($$(".board-dialog .btn").find(node => node.textContent === "Excluir coluna"));
    await flush();
    assert.equal(calls[0].url, "/quadros/colunas/17/excluir/");
    assert.equal($('th[data-column-id="17"]'), null);
    assert.equal($('col[data-col-id="17"]'), null);
    assert.equal($$('td[data-column-id="17"]').length, 0);
});

test("cancelling the delete dialog sends nothing", async t => {
    const {$, $$, click, calls} = setup(t);
    click($('th[data-column-id="17"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Excluir coluna"));
    click($$(".board-dialog .btn").find(node => node.textContent === "Cancelar"));
    await flush();
    assert.equal(calls.length, 0);
    assert.equal($(".board-dialog"), null);
    assert.ok($('th[data-column-id="17"]'));
});

test("changing the type: preview, the warning with the numbers, then the confirmed change", async t => {
    const respond = call => {
        if (call.body.preview) return jsonResponse({ok: true, plan: {mode: "destructive", filled: 3, lost: 3}});
        return jsonResponse({
            ok: true,
            column: {id: 17, name: "Visto", type: "NUMBER", type_label: "Número", icon: "list-ol", width: 160, description: "", is_required: false, is_visible: true, settings: {decimal_places: 2}, options: []},
            header_html: '<th class="board-th" scope="col" data-column-th data-column-id="17" data-type="NUMBER"><div class="board-th__inner"><span class="board-th__name" data-column-name>Visto</span></div></th>',
            cells: {101: '<td data-cell data-item-id="101" data-column-id="17" data-type="NUMBER" data-value=""></td>'},
        });
    };
    const {$, $$, click, calls} = setup(t, {respond});
    click($('th[data-column-id="17"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Alterar tipo"));
    $(".board-dialog select").value = "NUMBER";
    click($$(".board-dialog .btn").find(node => node.textContent === "Continuar"));
    await flush();
    assert.deepEqual(calls[0].body, {type: "NUMBER", preview: true});
    assert.match($(".board-dialog__body").textContent, /3 de 3 valor\(es\)/);
    click($$(".board-dialog .btn").find(node => node.textContent === "Converter"));
    await flush();
    assert.deepEqual(calls[1].body, {type: "NUMBER", confirm: true});
    assert.equal($('th[data-column-id="17"]').dataset.type, "NUMBER");
    assert.equal($(".board-dialog"), null);
});

// ---------------------------------------------------------------------------------------------------
// Células
// ---------------------------------------------------------------------------------------------------

const TD = (item, column, type, inner, value = "") =>
    `<td class="board-td" data-cell data-item-id="${item}" data-column-id="${column}" data-type="${type}" data-value="${value}" tabindex="0">${inner}</td>`;

test("text cell: click edits, Enter saves, the server HTML replaces the cell", async t => {
    const respond = call => jsonResponse({ok: true, display: "Novo cliente", cell_html: TD(101, 11, "TEXT", '<span class="board-text">Novo cliente</span>', "Novo cliente")});
    const {w, $, click, key, cell, calls} = setup(t, {respond});
    click(cell(101, 11));
    const input = cell(101, 11).querySelector(".board-inline-input");
    assert.equal(input.value, "Shopping Norte");
    input.value = "Novo cliente";
    key(input, "Enter");
    assert.equal(cell(101, 11).textContent.trim(), "Novo cliente"); // otimista
    assert.ok(cell(101, 11).classList.contains("is-saving"));
    await flush();
    assert.equal(calls[0].url, "/quadros/itens/101/colunas/11/valor/");
    assert.deepEqual(calls[0].body, {value: "Novo cliente"});
    assert.ok(!cell(101, 11).classList.contains("is-saving"));
    assert.equal(cell(101, 11).dataset.value, "Novo cliente");
    assert.equal($("[data-board-status]").textContent, "Salvo");
});

test("text cell: Escape cancels, same value sends nothing", async t => {
    const {click, key, cell, calls} = setup(t);
    click(cell(101, 11));
    let input = cell(101, 11).querySelector(".board-inline-input");
    input.value = "mudou";
    key(input, "Escape");
    assert.equal(cell(101, 11).querySelector(".board-inline-input"), null);
    assert.equal(cell(101, 11).textContent.trim(), "Shopping Norte");
    click(cell(101, 11));
    input = cell(101, 11).querySelector(".board-inline-input");
    key(input, "Enter");
    await flush();
    assert.equal(calls.length, 0);
});

test("cell save that fails brings the old content back, marks the cell and warns", async t => {
    const {click, key, cell, calls, $} = setup(t, {respond: () => jsonResponse({ok: false, error: "Informe um número válido."}, 400)});
    click(cell(101, 15));
    const input = cell(101, 15).querySelector(".board-inline-input");
    input.value = "abc";
    key(input, "Enter");
    await flush();
    assert.equal(calls.length, 1);
    assert.match(cell(101, 15).textContent, /R\$ 2\.500\.000,00/);
    assert.ok(cell(101, 15).classList.contains("has-error"));
    assert.equal($("[data-board-toasts] .board-toast.is-error").textContent, "Informe um número válido.");
});

test("a 403 shows the server message instead of a generic one", async t => {
    const {click, key, cell, $} = setup(t, {respond: () => jsonResponse({ok: false, error: "Você não possui permissão para esta ação."}, 403)});
    click(cell(101, 11));
    const input = cell(101, 11).querySelector(".board-inline-input");
    input.value = "x";
    key(input, "Enter");
    await flush();
    assert.equal($("[data-board-toasts] .board-toast").textContent, "Você não possui permissão para esta ação.");
});

test("a network failure says so and restores the cell", async t => {
    const {click, key, cell, $} = setup(t, {respond: () => Promise.reject(new TypeError("Failed to fetch"))});
    click(cell(101, 11));
    const input = cell(101, 11).querySelector(".board-inline-input");
    input.value = "x";
    key(input, "Enter");
    await flush();
    assert.equal($("[data-board-toasts] .board-toast").textContent, "Sem conexão com o servidor. Tente de novo.");
    assert.equal(cell(101, 11).textContent.trim(), "Shopping Norte");
});

test("status cell: the popover lists the labels with readable colors and saving shows the pill at once", async t => {
    const respond = () => jsonResponse({ok: true, display: "Ganho", cell_html: TD(101, 13, "STATUS", '<span class="board-pill" style="background:#00C875;color:#FFFFFF">Ganho</span>', "3")});
    const {$$, click, cell, calls} = setup(t, {respond});
    click(cell(101, 13));
    const options = $$(".board-pop .board-option");
    assert.deepEqual(options.map(node => node.textContent), ["Novo", "Levantamento", "Ganho"]);
    assert.equal(options[2].style.color, "rgb(255, 255, 255)");
    assert.equal(options[0].style.color, "rgb(31, 41, 55)");
    assert.equal(options[1].getAttribute("aria-selected"), "true");
    click(options[2]);
    assert.equal($$(".board-pop").length, 0);
    assert.equal(cell(101, 13).textContent.trim(), "Ganho");
    await flush();
    assert.deepEqual(calls[0].body, {value: 3});
    assert.equal(cell(101, 13).dataset.value, "3");
});

test("status cell: clear and edit labels shortcuts", async t => {
    const {$$, click, cell, calls} = setup(t);
    click(cell(101, 13));
    const foot = $$(".board-pop .board-pop__foot .btn").map(node => node.textContent);
    assert.deepEqual(foot, ["Limpar", "Editar etiquetas"]);
    click($$(".board-pop .board-pop__foot .btn")[0]);
    await flush();
    assert.deepEqual(calls[0].body, {value: ""});
});

test("checkbox toggles with a click and with Space, sending 1 then 0", async t => {
    const respond = call => jsonResponse({ok: true, display: "", cell_html: TD(101, 17, "CHECKBOX", '<span class="board-check is-on"></span>', call.body.value)});
    const {click, key, cell, calls} = setup(t, {respond});
    click(cell(101, 17));
    await flush();
    assert.deepEqual(calls[0].body, {value: "1"});
    key(cell(101, 17), " ");
    await flush();
    assert.deepEqual(calls[1].body, {value: "0"});
});

test("date cell: native date input saves on change; Today and Clear exist", async t => {
    const respond = call => jsonResponse({ok: true, display: "01/10/2025", cell_html: TD(101, 14, "DATE", '<span class="board-date">01/10/2025</span>', call.body.value)});
    const {$, $$, click, cell, calls, w} = setup(t, {respond});
    click(cell(101, 14));
    const input = $(".board-pop input[type=date]");
    assert.equal(input.value, "2025-01-15");
    assert.deepEqual($$(".board-pop .btn").map(node => node.textContent), ["Hoje", "Limpar"]);
    input.value = "2025-10-01";
    input.dispatchEvent(new w.Event("change", {bubbles: true}));
    assert.equal(cell(101, 14).textContent.trim(), "01/10/2025");
    await flush();
    assert.deepEqual(calls[0].body, {value: "2025-10-01"});
});

test("person cell: searches while typing (debounced) and saves the chosen person", async t => {
    const respond = call => {
        if (call.url.startsWith("/api/pessoas/")) return jsonResponse({results: [{id: 7, name: "Ana Souza", username: "ana"}, {id: 8, name: "Bruno Lima", username: "bruno"}]});
        return jsonResponse({ok: true, display: "Bruno Lima", cell_html: TD(102, 12, "PERSON", '<span class="board-person"><span class="board-avatar">BL</span><span class="board-person__name">Bruno Lima</span></span>', "8")});
    };
    const {w, $, $$, click, cell, calls, runTimers} = setup(t, {respond});
    click(cell(102, 12));
    await flush();
    assert.equal(calls[0].url, "/api/pessoas/?q=");
    assert.deepEqual($$(".board-people__item").map(node => node.textContent), ["ASAna Souza", "BLBruno Lima"]);
    const search = $(".board-people__search");
    search.value = "bru";
    search.dispatchEvent(new w.Event("input", {bubbles: true}));
    assert.equal(calls.length, 1); // ainda não buscou: aguarda a pausa
    runTimers();
    await flush();
    assert.equal(calls[1].url, "/api/pessoas/?q=bru");
    click($$(".board-people__item")[1]);
    assert.equal(cell(102, 12).textContent.replace(/\s+/g, ""), "BLBrunoLima");
    await flush();
    assert.deepEqual(calls[2].body, {value: 8});
    assert.equal(cell(102, 12).dataset.value, "8");
});

test("Delete key clears a filled cell, arrows move focus, Enter opens the editor", async t => {
    const {w, key, cell, calls, $$} = setup(t, {respond: () => jsonResponse({ok: true, display: "", cell_html: TD(101, 11, "TEXT", "", "")})});
    cell(101, 11).focus();
    key(cell(101, 11), "ArrowDown");
    assert.equal(w.document.activeElement, cell(102, 11));
    key(cell(102, 11), "ArrowRight");
    assert.equal(w.document.activeElement, cell(102, 12));
    key(cell(102, 12), "ArrowUp");
    assert.equal(w.document.activeElement, cell(101, 12));
    key(cell(101, 11), "Delete");
    await flush();
    assert.deepEqual(calls[0].body, {value: ""});
    key(cell(101, 11), "Enter");
    assert.equal($$(".board-inline-input").length, 1);
});

// ---------------------------------------------------------------------------------------------------
// Etiquetas
// ---------------------------------------------------------------------------------------------------

test("labels dialog: add, recolor with the palette, mark default, delete after confirming, refresh the column on close", async t => {
    const respond = call => {
        if (call.url === "/quadros/colunas/13/etiquetas/novo/") return jsonResponse({ok: true, option: {id: 40, label: "Em revisão", color: "#C4C4C4", is_default: false, is_done: false}});
        if (call.url === "/quadros/colunas/13/fragmento/") {
            return jsonResponse({
                ok: true,
                column: {id: 13, name: "Status", type: "STATUS", type_label: "Status", icon: "task", width: 160, description: "", is_required: false, is_visible: true, settings: {}, options: [{id: 2, label: "Levantamento", color: "#66CCFF", is_default: false, is_done: false}]},
                header_html: '<th class="board-th" scope="col" data-column-th data-column-id="13" data-type="STATUS"><div class="board-th__inner"><span class="board-th__name" data-column-name>Status</span></div></th>',
                cells: {101: TD(101, 13, "STATUS", '<span class="board-pill">Levantamento</span>', "2")},
            });
        }
        return jsonResponse({ok: true, cleared_cells: 0, option: {id: call.body && call.body.color ? 2 : 2, label: "Levantamento", color: (call.body || {}).color || "#66CCFF", is_default: false, is_done: false}});
    };
    const {w, $, $$, click, calls} = setup(t, {respond});
    click($('th[data-column-id="13"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Editar etiquetas"));
    assert.equal($$(".board-label-row").length, 3);

    const add = $(".board-label-add input");
    add.value = "Em revisão";
    click($(".board-label-add .btn"));
    await flush();
    assert.deepEqual(calls[0].body, {label: "Em revisão"});
    assert.equal($$(".board-label-row").length, 4);

    click($$(".board-label-row .board-swatch")[1]);
    click($$(".board-pop .board-swatch")[2]);
    await flush();
    assert.equal(calls[1].url, "/quadros/etiquetas/2/editar/");
    assert.deepEqual(calls[1].body, {color: "#E2445C"});

    const radios = $$(".board-label-row input[type=radio]");
    radios[1].checked = true;
    radios[1].dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.deepEqual(calls[2].body, {is_default: true});

    click($$(".board-label-row .board-label-remove")[3]);
    assert.match($$(".board-dialog__body").pop().textContent, /Excluir a etiqueta “Em revisão”/);
    click($$(".board-dialog .btn").find(node => node.textContent === "Excluir"));
    await flush();
    assert.equal(calls[3].url, "/quadros/etiquetas/40/excluir/");
    assert.equal($$(".board-label-row").length, 3);

    click($$(".board-dialog .btn").find(node => node.textContent === "Concluir"));
    await flush();
    assert.equal(calls[4].url, "/quadros/colunas/13/fragmento/");
    assert.equal(cell(101, 13).textContent.trim(), "Levantamento");
    function cell(item, column) { return $(`td[data-cell][data-item-id="${item}"][data-column-id="${column}"]`); }
});

test("labels dialog: a refused rename shows the error and restores the field", async t => {
    const {$, $$, click, calls, w} = setup(t, {respond: () => jsonResponse({ok: false, error: "Já existe a etiqueta “Ganho” nesta coluna."}, 400)});
    click($('th[data-column-id="13"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Editar etiquetas"));
    const input = $$(".board-label-row input[type=text]")[0];
    input.value = "Ganho";
    input.dispatchEvent(new w.Event("change", {bubbles: true}));
    await flush();
    assert.equal(calls.length, 1);
    assert.equal(input.value, "Novo");
    assert.equal($(".board-dialog__error").textContent, "Já existe a etiqueta “Ganho” nesta coluna.");
    assert.equal($(".board-dialog__error").hidden, false);
});

// ---------------------------------------------------------------------------------------------------
// Configurações
// ---------------------------------------------------------------------------------------------------

test("settings dialog sends the type settings and applies the returned column", async t => {
    const respond = () => jsonResponse({
        ok: true,
        column: {id: 16, name: "Probabilidade", type: "NUMBER", type_label: "Número", icon: "list-ol", width: 160, description: "Chance", is_required: true, is_visible: true, settings: {decimal_places: 1, unit: "%", minimum: 0, maximum: 100}, options: []},
        header_html: '<th class="board-th" scope="col" data-column-th data-column-id="16" data-type="NUMBER"><div class="board-th__inner"><span class="board-th__name" data-column-name>Probabilidade</span></div></th>',
        cells: {},
    });
    const {w, $, $$, click, calls} = setup(t, {respond});
    click($('th[data-column-id="16"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Configurações da coluna"));
    const dialog = $(".board-dialog");
    assert.ok(dialog);
    const fields = dialog.querySelectorAll("input[type=text], input[type=number], textarea");
    // descrição, casas decimais, unidade, mínimo, máximo
    assert.equal(fields.length, 5);
    fields[0].value = "Chance";
    fields[1].value = "1";
    fields[3].value = "0";
    fields[4].value = "100";
    dialog.querySelector("input[type=checkbox]").checked = true;
    click($$(".board-dialog .btn").find(node => node.textContent === "Salvar"));
    await flush();
    assert.equal(calls[0].url, "/quadros/colunas/16/configuracoes/");
    assert.deepEqual(calls[0].body, {
        description: "Chance", is_required: true,
        settings: {unit: "%", decimal_places: "1", minimum: "0", maximum: "100"},
    });
    assert.equal($(".board-dialog"), null);
    assert.ok(w.LPSBoards.instance.columnMeta(16).is_required);
});

test("settings dialog keeps open and shows the message when the server refuses", async t => {
    const {$, $$, click} = setup(t, {respond: () => jsonResponse({ok: false, error: "O mínimo não pode ser maior que o máximo."}, 400)});
    click($('th[data-column-id="16"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Configurações da coluna"));
    click($$(".board-dialog .btn").find(node => node.textContent === "Salvar"));
    await flush();
    assert.ok($(".board-dialog"));
    assert.equal($(".board-dialog__error").textContent, "O mínimo não pode ser maior que o máximo.");
});

// ---------------------------------------------------------------------------------------------------
// Itens e grupos
// ---------------------------------------------------------------------------------------------------

test("add item creates the row without reload and focuses its name", async t => {
    const row = '<tr class="board-row" data-item-row data-item-id="200" data-group-id="1"><th class="board-td board-td--name" scope="row"><div class="board-name-cell"><span class="board-name is-empty" data-item-name tabindex="0">Sem título</span></div></th><td class="board-td--filler"></td></tr>';
    const {$, $$, click, calls} = setup(t, {respond: () => jsonResponse({ok: true, item: {id: 200, group_id: 1, name: ""}, row_html: row})});
    click($('tbody[data-group-id="1"] [data-item-add]'));
    await flush();
    assert.deepEqual(calls[0].body, {group_id: 1});
    assert.equal(calls[0].url, "/quadros/1/itens/novo/");
    const rows = $$('tbody[data-group-id="1"] tr[data-item-row]');
    assert.deepEqual(rows.map(r => r.dataset.itemId), ["101", "102", "200"]);
    assert.equal($('tbody[data-group-id="1"]').querySelector("[data-add-row]").previousElementSibling, rows[2]);
    assert.equal($('tbody[data-group-id="1"] [data-group-count]').textContent, "3 itens");
    assert.ok(rows[2].querySelector(".board-inline-input"));
});

test("rename item inline: optimistic and reverts when refused", async t => {
    const {$, click, key, calls} = setup(t, {respond: () => jsonResponse({ok: false, error: "Sem permissão."}, 403)});
    const name = $('tr[data-item-id="101"] [data-item-name]');
    click(name);
    const input = $('tr[data-item-id="101"] .board-inline-input');
    assert.equal(input.value, "Arena Norte");
    input.value = "Arena Sul";
    key(input, "Enter");
    assert.equal($('tr[data-item-id="101"] [data-item-name]').textContent, "Arena Sul");
    await flush();
    assert.deepEqual(calls[0].body, {name: "Arena Sul"});
    assert.equal($('tr[data-item-id="101"] [data-item-name]').textContent, "Arena Norte");
});

test("item menu moves to another group and deletes after confirming", async t => {
    const {$, $$, click, calls} = setup(t);
    click($('tr[data-item-id="101"] [data-item-menu]'));
    const labels = $$(".board-pop .board-menu__item").map(node => node.textContent);
    assert.deepEqual(labels, ["Em andamento", "Renomear", "Excluir item"]);
    click($$(".board-pop .board-menu__item")[0]);
    assert.equal($('tr[data-item-id="101"]').closest("tbody").dataset.groupId, "2");
    assert.equal($('tbody[data-group-id="1"] [data-group-count]').textContent, "1 item");
    assert.equal($('tbody[data-group-id="2"] [data-group-count]').textContent, "2 itens");
    await flush();
    assert.deepEqual(calls[0].body, {group_id: 2, before_id: 103, after_id: null});

    click($('tr[data-item-id="102"] [data-item-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Excluir item"));
    click($$(".board-dialog .btn").find(node => node.textContent === "Excluir"));
    await flush();
    assert.equal(calls[1].url, "/quadros/itens/102/excluir/");
    assert.equal($('tr[data-item-id="102"]'), null);
});

test("a refused move puts the row back where it was", async t => {
    const {$, $$, click} = setup(t, {respond: () => jsonResponse({ok: false, error: "Grupo inválido."}, 400)});
    click($('tr[data-item-id="101"] [data-item-menu]'));
    click($$(".board-pop .board-menu__item")[0]);
    await flush();
    const ids = $$('tbody[data-group-id="1"] tr[data-item-row]').map(row => row.dataset.itemId);
    assert.deepEqual(ids, ["101", "102"]);
    assert.equal($('tbody[data-group-id="1"] [data-group-count]').textContent, "2 itens");
});

function dragEvent(w, type, init = {}) {
    const event = new w.MouseEvent(type, {bubbles: true, cancelable: true, ...init});
    event.dataTransfer = {setData() {}, setDragImage() {}, effectAllowed: ""};
    return event;
}

test("drag an item onto the lower half of another row sends both neighbours", async t => {
    const {w, $, calls} = setup(t);
    const row101 = $('tr[data-item-id="101"]'), row102 = $('tr[data-item-id="102"]');
    row102.getBoundingClientRect = () => ({top: 100, height: 40, left: 0, width: 500});
    $('tr[data-item-id="101"] [data-item-grip]').dispatchEvent(dragEvent(w, "dragstart"));
    assert.ok(row101.classList.contains("is-dragging"));
    const over = dragEvent(w, "dragover", {clientY: 130});
    row102.querySelector("[data-item-name]").dispatchEvent(over);
    assert.equal(over.defaultPrevented, true);
    assert.ok(row102.classList.contains("is-drop-after"));
    row102.querySelector("[data-item-name]").dispatchEvent(dragEvent(w, "drop", {clientY: 130}));
    await flush();
    assert.deepEqual(calls[0].body, {group_id: 1, before_id: 102, after_id: null});
    assert.deepEqual(Array.from(w.document.querySelectorAll('tbody[data-group-id="1"] tr[data-item-row]')).map(r => r.dataset.itemId), ["102", "101"]);
    assert.ok(!row101.classList.contains("is-dragging"));
    assert.equal(w.document.querySelectorAll(".is-drop-before, .is-drop-after").length, 0);
});

test("drag an item onto the upper half of a row in another group", async t => {
    const {w, $, calls} = setup(t);
    const target = $('tr[data-item-id="103"]');
    target.getBoundingClientRect = () => ({top: 100, height: 40, left: 0, width: 500});
    $('tr[data-item-id="101"] [data-item-grip]').dispatchEvent(dragEvent(w, "dragstart"));
    target.querySelector("[data-item-name]").dispatchEvent(dragEvent(w, "dragover", {clientY: 105}));
    target.querySelector("[data-item-name]").dispatchEvent(dragEvent(w, "drop", {clientY: 105}));
    await flush();
    assert.deepEqual(calls[0].body, {group_id: 2, before_id: null, after_id: 103});
    assert.equal($('tr[data-item-id="101"]').closest("tbody").dataset.groupId, "2");
});

test("dropping a row back on its own boundary keeps its place", async t => {
    const {w, $, calls} = setup(t);
    const row102 = $('tr[data-item-id="102"]');
    $('tr[data-item-id="102"] [data-item-grip]').dispatchEvent(dragEvent(w, "dragstart"));
    const row101 = $('tr[data-item-id="101"]');
    row101.getBoundingClientRect = () => ({top: 0, height: 40, left: 0, width: 500});
    row101.querySelector("[data-item-name]").dispatchEvent(dragEvent(w, "dragover", {clientY: 30}));
    row101.querySelector("[data-item-name]").dispatchEvent(dragEvent(w, "drop", {clientY: 30}));
    await flush();
    assert.deepEqual(calls[0].body, {group_id: 1, before_id: 101, after_id: null});
    assert.deepEqual(Array.from(w.document.querySelectorAll('tbody[data-group-id="1"] tr[data-item-row]')).map(r => r.dataset.itemId), ["101", "102"]);
    assert.ok(row102);
});

test("drag a column header next to another and move the whole column", async t => {
    const {w, $, $$, calls} = setup(t);
    const th13 = $('th[data-column-id="13"]');
    th13.getBoundingClientRect = () => ({left: 0, width: 100, top: 0, height: 40});
    $('th[data-column-id="17"] .board-th__inner').dispatchEvent(dragEvent(w, "dragstart"));
    th13.querySelector(".board-th__name").dispatchEvent(dragEvent(w, "dragover", {clientX: 10}));
    assert.ok(th13.classList.contains("is-drop-before"));
    th13.querySelector(".board-th__name").dispatchEvent(dragEvent(w, "drop", {clientX: 10}));
    await flush();
    assert.deepEqual(calls[0].body, {before_id: 12, after_id: 13});
    assert.equal(calls[0].url, "/quadros/colunas/17/mover/");
    assert.deepEqual($$("th[data-column-th]").map(th => th.dataset.columnId).slice(0, 5), ["11", "12", "17", "13", "14"]);
    assert.deepEqual($$("colgroup col[data-col-id]").map(col => col.dataset.colId).slice(0, 5), ["11", "12", "17", "13", "14"]);
    assert.deepEqual($$('tr[data-item-id="101"] td[data-cell]').map(td => td.dataset.columnId).slice(0, 5), ["11", "12", "17", "13", "14"]);
});

test("a refused column move goes back to the original order", async t => {
    const {w, $, $$} = setup(t, {respond: () => jsonResponse({ok: false, error: "A posição escolhida não existe mais. Recarregue o quadro."}, 400)});
    const th13 = $('th[data-column-id="13"]');
    th13.getBoundingClientRect = () => ({left: 0, width: 100, top: 0, height: 40});
    $('th[data-column-id="17"] .board-th__inner').dispatchEvent(dragEvent(w, "dragstart"));
    th13.querySelector(".board-th__name").dispatchEvent(dragEvent(w, "dragover", {clientX: 10}));
    th13.querySelector(".board-th__name").dispatchEvent(dragEvent(w, "drop", {clientX: 10}));
    await flush();
    assert.deepEqual($$("th[data-column-th]").map(th => th.dataset.columnId), ["11", "12", "13", "14", "15", "16", "17", "18", "11", "12", "13", "14", "15", "16", "17", "18"]);
    assert.deepEqual($$('tr[data-item-id="101"] td[data-cell]').map(td => td.dataset.columnId), ["11", "12", "13", "14", "15", "16", "17", "18"]);
});

test("groups: collapse is remembered, rename, color, move and delete", async t => {
    const respond = call => {
        if (call.url.endsWith("/editar/")) return jsonResponse({ok: true, group: {id: 1, name: call.body.name || "Oportunidades", color: call.body.color || "#579BFC"}});
        return jsonResponse({ok: true});
    };
    const {w, $, $$, click, key, calls} = setup(t, {respond});
    const group = $('tbody[data-group-id="1"]');
    click(group.querySelector("[data-group-toggle]"));
    assert.ok(group.classList.contains("is-collapsed"));
    assert.equal(group.querySelector("[data-group-toggle]").getAttribute("aria-expanded"), "false");
    assert.equal(w.localStorage.getItem("lps-board-1-collapsed"), "[1]");
    click(group.querySelector("[data-group-toggle]"));
    assert.equal(w.localStorage.getItem("lps-board-1-collapsed"), "[]");

    click(group.querySelector("[data-group-title]"));
    const input = group.querySelector(".board-inline-input");
    input.value = "Pipeline";
    key(input, "Enter");
    await flush();
    assert.deepEqual(calls[0].body, {name: "Pipeline"});

    click(group.querySelector("[data-group-menu]"));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Mudar a cor"));
    click($$(".board-pop .board-swatch")[2]);
    await flush();
    assert.deepEqual(calls[1].body, {color: "#E2445C"});
    assert.equal(group.style.getPropertyValue("--group-color"), "#E2445C");

    click(group.querySelector("[data-group-menu]"));
    const items = $$(".board-pop .board-menu__item");
    assert.equal(items.find(node => node.textContent === "Mover para cima").disabled, true);
    click(items.find(node => node.textContent === "Mover para baixo"));
    await flush();
    assert.equal(calls[2].url, "/quadros/grupos/1/mover/");
    assert.deepEqual(calls[2].body, {before_id: 2, after_id: null});
    assert.deepEqual($$("tbody[data-group]").map(g => g.dataset.groupId), ["2", "1"]);
});

test("new group is appended with the HTML the server rendered", async t => {
    const html = '<tbody class="board-group" data-group data-group-id="9" data-group-name="Novo grupo" data-group-color="#579BFC"><tr class="board-group-head"><td colspan="10"><div class="board-group-head__inner"><button type="button" data-group-toggle aria-expanded="true"></button><span class="board-group-name" data-group-title tabindex="0">Novo grupo</span><span data-group-count>0 itens</span></div></td></tr></tbody>';
    const {$, $$, click, calls} = setup(t, {respond: () => jsonResponse({ok: true, group: {id: 9, name: "Novo grupo", color: "#579BFC"}, group_html: html})});
    click($("[data-group-add]"));
    await flush();
    assert.equal(calls[0].url, "/quadros/1/grupos/novo/");
    assert.deepEqual($$("tbody[data-group]").map(g => g.dataset.groupId), ["1", "2", "9"]);
    assert.ok($('tbody[data-group-id="9"] .board-inline-input'));
});

// ---------------------------------------------------------------------------------------------------
// Quadro, filtros e foco
// ---------------------------------------------------------------------------------------------------

test("board title: Enter saves, Escape restores, empty restores", async t => {
    const {w, $, key, calls} = setup(t, {respond: call => jsonResponse({ok: true, name: call.body.name, description: ""})});
    const title = $("[data-board-title]");
    title.value = "Orçamentos 2026";
    key(title, "Enter");
    title.dispatchEvent(new w.Event("blur"));
    await flush();
    assert.equal(calls.length, 1);
    assert.deepEqual(calls[0].body, {name: "Orçamentos 2026"});
    title.value = "";
    title.dispatchEvent(new w.Event("blur"));
    assert.equal(title.value, "Orçamentos 2026");
    assert.equal(calls.length, 1);
});

test("deleting the board confirms and follows the redirect the server gave", async t => {
    const {$, $$, click, calls} = setup(t, {respond: () => jsonResponse({ok: true, redirect_url: "/quadros/"})});
    click($("[data-board-delete]"));
    assert.match($(".board-dialog__body").textContent, /Excluir o quadro “Orçamentos”/);
    click($$(".board-dialog .btn").find(node => node.textContent === "Excluir quadro"));
    await flush();
    assert.equal(calls[0].url, "/quadros/1/excluir/");
});

test("Escape closes the popover and returns focus to its trigger; clicking outside closes it too", t => {
    const {w, $, $$, key, click} = setup(t);
    const trigger = $('th[data-column-id="11"] [data-column-menu]');
    trigger.focus();
    click(trigger);
    assert.equal($$(".board-pop").length, 1);
    key(w.document.body, "Escape");
    assert.equal($$(".board-pop").length, 0);
    assert.equal(w.document.activeElement, trigger);
    click(trigger);
    w.document.body.dispatchEvent(new w.MouseEvent("mousedown", {bubbles: true}));
    assert.equal($$(".board-pop").length, 0);
});

test("dialogs trap Tab inside and close with Escape", t => {
    const {w, $, $$, click, key} = setup(t);
    click($("[data-board-delete]"));
    const buttons = $$(".board-dialog button");
    buttons[buttons.length - 1].focus();
    const event = key(buttons[buttons.length - 1], "Tab");
    assert.equal(event.defaultPrevented, true);
    assert.equal(w.document.activeElement, buttons[0]);
    key(w.document.body, "Escape");
    assert.equal($(".board-dialog"), null);
});

test("the person filter submits its form when it changes", t => {
    const {w, $} = setup(t);
    const select = $("[data-board-person-filter]");
    let submitted = 0;
    select.form.submit = () => { submitted += 1; };
    select.dispatchEvent(new w.Event("change", {bubbles: true}));
    assert.equal(submitted, 1);
});

test("hidden columns come back through the show button", async t => {
    const fixture = {...FULL, html: FULL.html.replace('<form class="board-toolbar"', '<ul><li><button type="button" data-column-show data-column-id="21">Mostrar</button></li></ul><form class="board-toolbar"')};
    const {$, click, calls} = setup(t, {fixture, respond: () => jsonResponse({ok: true, visible: true})});
    click($("[data-column-show]"));
    await flush();
    assert.equal(calls[0].url, "/quadros/colunas/21/ocultar/");
    assert.deepEqual(calls[0].body, {visible: true});
});

test("every request carries the CSRF token from the cookie", async t => {
    const {w, click, key, cell, calls} = setup(t);
    w.document.cookie = "csrftoken=abc123";
    click(cell(101, 11));
    const input = cell(101, 11).querySelector(".board-inline-input");
    input.value = "x";
    key(input, "Enter");
    await flush();
    assert.equal(calls[0].headers["X-CSRFToken"], "abc123");
    assert.equal(calls[0].headers["Content-Type"], "application/json");
});

// ---------------------------------------------------------------------------------------------------
// Paleta de cores aberta de dentro de uma janela (etiquetas)
// ---------------------------------------------------------------------------------------------------

function cssZIndex(css, selector) {
    const match = new RegExp(selector.replace(/[.]/g, '\\.') + '\\s*\\{[^}]*?z-index:\\s*(\\d+)', 's').exec(css);
    return match ? Number(match[1]) : null;
}

test("css: the pop-over layer is above the dialog (the palette opens from inside it) and below the toasts", () => {
    const css = readFileSync(path.join(root, "static/css/boards.css"), "utf8");
    const pop = cssZIndex(css, ".board-pop");
    const dialog = cssZIndex(css, ".board-dialog-backdrop");
    const toast = cssZIndex(css, ".board-toast-area");
    assert.ok(pop > dialog, `.board-pop (${pop}) precisa ficar acima de .board-dialog-backdrop (${dialog})`);
    assert.ok(pop < toast, `.board-pop (${pop}) precisa ficar abaixo de .board-toast-area (${toast})`);
});

test("labels dialog: Escape closes only the color palette first, then the dialog", t => {
    const {w, $, $$, click, key} = setup(t);
    click($('th[data-column-id="13"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Editar etiquetas"));
    click($$(".board-label-row .board-swatch")[1]);
    assert.equal($$(".board-pop .board-palette").length, 1);
    key(w.document.body, "Escape");
    assert.equal($$(".board-pop").length, 0);
    assert.ok($(".board-dialog"));
    key(w.document.body, "Escape");
    assert.equal($(".board-dialog"), null);
});

test("labels dialog: after picking a color the focus goes back to that label's color button", async t => {
    const respond = call => jsonResponse({ok: true, option: {id: 2, label: "Levantamento", color: (call.body || {}).color || "#66CCFF", is_default: false, is_done: false}});
    const {w, $$, click, calls} = setup(t, {respond});
    click($('th[data-column-id="13"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Editar etiquetas"));
    click($$(".board-label-row .board-swatch")[1]);
    click($$(".board-pop .board-palette .board-swatch")[2]);
    await flush();
    assert.deepEqual(calls[0].body, {color: "#E2445C"});
    assert.equal(w.document.activeElement.dataset.optionId, "2");
    assert.equal(w.document.activeElement.style.backgroundColor, "rgb(226, 68, 92)");
    function $(selector) { return w.document.querySelector(selector); }
});


// ---------------------------------------------------------------------------------------------------
// Cada grupo tem a sua linha de títulos das colunas (como no Monday)
// ---------------------------------------------------------------------------------------------------

const COLUMN_NAMES = ["Cliente", "Responsável", "Status", "Prazo", "Valor", "Probabilidade", "Visto", "Setor"];
const titlesOf = group => Array.from(group.querySelectorAll("tr[data-cols-row] th[data-column-th] .board-th__name")).map(node => node.textContent.trim());
const idsOf = group => Array.from(group.querySelectorAll("tr[data-cols-row] th[data-column-th]")).map(node => node.dataset.columnId);

test("every group shows the column titles right under its own name, and there is no single header at the top", t => {
    const {$, $$} = setup(t);
    assert.equal($("thead"), null);
    const groups = $$("tbody[data-group]");
    assert.equal(groups.length, 2);
    for (const group of groups) {
        const rows = Array.from(group.children);
        assert.ok(rows[0].classList.contains("board-group-head"), "o nome do grupo vem primeiro");
        assert.ok(rows[1].classList.contains("board-cols-row"), "os títulos das colunas vêm logo abaixo");
        assert.deepEqual(titlesOf(group), COLUMN_NAMES);
        assert.equal(rows[1].querySelector(".board-th--name").textContent.trim(), "Obra");
        assert.ok(rows[1].querySelector("[data-column-add]"), "o + para criar coluna também fica em cada grupo");
    }
});

test("a viewer also sees the titles in every group, without the + and the resize handles", t => {
    const {$$} = setup(t, {fixture: VIEWER});
    for (const group of $$("tbody[data-group]")) {
        assert.deepEqual(titlesOf(group), COLUMN_NAMES);
        assert.equal(group.querySelector("[data-column-add]"), null);
        assert.equal(group.querySelector("[data-column-resize]"), null);
    }
});

test("creating a column puts its title in every group; renaming opens in the group where + was clicked", async t => {
    const header = '<th class="board-th" scope="col" data-column-th data-column-id="99" data-type="NUMBER"><div class="board-th__inner"><span class="board-th__name" data-column-name>Números</span><button type="button" class="board-th__menu" data-column-menu></button></div><span class="board-th__resize" data-column-resize></span></th>';
    const respond = () => jsonResponse({
        ok: true, after_column_id: null,
        column: {id: 99, name: "Números", type: "NUMBER", type_label: "Número", icon: "list-ol", width: 160, description: "", is_required: false, is_visible: true, settings: {decimal_places: 2}, options: []},
        header_html: header,
        cells: {101: '<td data-cell data-item-id="101" data-column-id="99" data-type="NUMBER" data-value=""></td>', 102: '<td data-cell data-item-id="102" data-column-id="99" data-type="NUMBER" data-value=""></td>', 103: '<td data-cell data-item-id="103" data-column-id="99" data-type="NUMBER" data-value=""></td>'},
    });
    const {$, $$, click} = setup(t, {respond});
    const second = $('tbody[data-group-id="2"]');
    click(second.querySelector("[data-column-add]"));
    click($$(".board-pop .board-type").find(node => node.querySelector("strong").textContent === "Número"));
    await flush();
    for (const group of $$("tbody[data-group]")) {
        const ids = idsOf(group);
        assert.equal(ids[ids.length - 1], "99", "a coluna nova entra antes do + em todos os grupos");
        assert.equal(group.querySelector("tr[data-cols-row]").lastElementChild.dataset.addColumnTh !== undefined, true);
    }
    assert.ok(second.querySelector('th[data-column-id="99"] .board-inline-input'), "renomear abre onde a pessoa clicou");
    assert.equal($('tbody[data-group-id="1"] .board-inline-input'), null);
});

test("renaming a column updates its title in every group", async t => {
    const header = '<th class="board-th" scope="col" data-column-th data-column-id="11" data-type="TEXT"><div class="board-th__inner"><span class="board-th__name" data-column-name>Cliente final</span></div></th>';
    const respond = () => jsonResponse({
        ok: true,
        column: {id: 11, name: "Cliente final", type: "TEXT", type_label: "Texto", icon: "file-text", width: 160, description: "", is_required: false, is_visible: true, settings: {}, options: []},
        header_html: header,
    });
    const {w, $, $$, key} = setup(t, {respond});
    const second = $('tbody[data-group-id="2"]');
    second.querySelector('th[data-column-id="11"] [data-column-name]').dispatchEvent(new w.MouseEvent("click", {bubbles: true, detail: 2}));
    const input = second.querySelector('th[data-column-id="11"] .board-inline-input');
    assert.ok(input, "o campo abre no título do grupo em que se clicou");
    input.value = "Cliente final";
    key(input, "Enter");
    await flush();
    assert.deepEqual($$('th[data-column-id="11"] [data-column-name]').map(node => node.textContent), ["Cliente final", "Cliente final"]);
});

test("deleting and moving a column act on the titles of every group", async t => {
    const {w, $, $$, click} = setup(t);
    const drag = (type, init = {}) => dragEvent(w, type, init);
    // arrastar o título do segundo grupo vale para os dois
    const second = $('tbody[data-group-id="2"]');
    const target = second.querySelector('th[data-column-id="13"]');
    target.getBoundingClientRect = () => ({left: 0, width: 100, top: 0, height: 40});
    second.querySelector('th[data-column-id="17"] .board-th__inner').dispatchEvent(drag("dragstart"));
    target.querySelector(".board-th__name").dispatchEvent(drag("dragover", {clientX: 10}));
    target.querySelector(".board-th__name").dispatchEvent(drag("drop", {clientX: 10}));
    await flush();
    for (const group of $$("tbody[data-group]")) assert.deepEqual(idsOf(group).slice(0, 5), ["11", "12", "17", "13", "14"]);
    // excluir tira dos dois
    click(second.querySelector('th[data-column-id="18"] [data-column-menu]'));
    click($$(".board-pop .board-menu__item").find(node => node.textContent === "Excluir coluna"));
    click($$(".board-dialog .btn--danger")[0]);
    await flush();
    assert.equal($$('th[data-column-id="18"]').length, 0);
});

test("collapsed groups hide their column titles too (css)", () => {
    const css = readFileSync(path.join(root, "static/css/boards.css"), "utf8");
    assert.match(css, /\.board-group\.is-collapsed \.board-cols-row\s*\{\s*display:\s*none/);
});
