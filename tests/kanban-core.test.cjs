/* Núcleo do Kanban (static/js/kanban-core.js). Requires jsdom@26.1.0 in NODE_PATH. Run from workflow: node --test tests/kanban-core.test.cjs
   Set PYTHON to the project's Python if it is not in .venv.

   A marcação vem do construtor REAL (boards/demand_kanban.py) renderizado pelos templates REAIS (templates/kanban/*), sem
   banco: se o contrato de dados mudar, este teste quebra aqui e não só no navegador. Cenário (agrupado por etapa, dois setores):
     raia "empty"  Sem estágio (aceita qualquer cartão)        raia 20  A fazer — Financeiro   [cartão 5]
     raia 10       A fazer — Orçamento  [cartões 1, 2, 3(concluída)]   raia 11  Levantamento — Orçamento  [cartão 4] */
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync, existsSync} = require("node:fs");
const {execFileSync} = require("node:child_process");
const path = require("node:path");
const {JSDOM} = require("jsdom");

const root = path.resolve(__dirname, "..");
const localPython = path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const python = process.env.PYTHON || (existsSync(localPython) ? localPython : "python");

const fixtures = JSON.parse(execFileSync(python, ["-c", `
import os, json, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from types import SimpleNamespace
from django.template.loader import render_to_string
from boards.demand_kanban import build_demand_kanban

def item(pk, sector_id=1, status='ABERTA'):
    return SimpleNamespace(pk=pk, title='Demanda %s' % pk, sector_id=sector_id, status=status, can_move_kanban=True, work_cells=[],
                           updated_at=datetime.datetime(2026, 10, 3, 10, 0, tzinfo=datetime.timezone.utc))

def group(key, label, items=(), **extra):
    return {'key': key, 'label': label, 'color': '#3B82F6', 'items': list(items), **extra}

def render(groups, group_by):
    kanban = build_demand_kanban(groups=groups, group_by=group_by, sectors_by_id={1: 'Orçamento', 2: 'Financeiro'}, show_field_names=False,
                                 can_create=True, create_url='/demandas/nova/', return_url='/demandas/kanban/')
    return render_to_string('kanban/_lanes.html', {'kanban': kanban})

stage = render([
    group('empty', 'Sem estágio'),
    group(10, 'A fazer', [item(1), item(2), item(3, status='CONCLUIDA')], sector_id=1),
    group(11, 'Levantamento', [item(4)], sector_id=1),
    group(20, 'A fazer', [item(5, sector_id=2)], sector_id=2),
], 'stage')
owner = render([group('empty', 'Sem responsável'), group(1, 'ana', [item(1)]), group(2, 'bia', [item(2)])], 'owner')
def v2_card(pk, title, **extra):
    base = {'id': pk, 'title': title, 'url': '', 'updated_at': '2026-10-03T10:00:00+00:00', 'scope': '', 'can_move': True, 'menu': True,
            'title_editable': True, 'title_label': 'Obra', 'attrs': [],
            'fields': [{'kind': 'text', 'label': 'Cliente', 'text': 'Shopping Norte', 'editable': True, 'css': 'text',
                        'attrs': [('data-cell', ''), ('data-item-id', pk), ('data-column-id', 11), ('data-type', 'TEXT'), ('data-value', 'Shopping Norte')]}]}
    base.update(extra)
    return base

v2 = render_to_string('kanban/_lanes.html', {'kanban': {
    'item_label': 'obra', 'show_field_names': False, 'lanes': [
        {'key': '1', 'label': 'Novo', 'color': '#C4C4C4', 'is_blank': False, 'accepts': True, 'scope': '', 'sector': '', 'option_id': 1, 'menu': True,
         'total': 'R$ 10,00', 'count': 2, 'empty_text': 'Nenhum item. Arraste um cartão para cá.', 'add': {'label': 'Adicionar obra', 'attrs': []},
         'cards': [v2_card(101, 'Arena Norte'), v2_card(102, 'Hospital Vida', can_move=False, title_editable=False)]},
        {'key': '2', 'label': 'Ganho', 'color': '#00C875', 'is_blank': False, 'accepts': True, 'scope': '', 'sector': '', 'option_id': 2, 'menu': True,
         'total': '', 'count': 0, 'empty_text': 'Nenhum item. Arraste um cartão para cá.', 'add': {'label': 'Adicionar obra', 'attrs': []}, 'cards': []},
    ]}})
print(json.dumps({'stage': stage, 'owner': owner, 'v2': v2}))
`], {cwd: root, encoding: "utf8"}).trim());

const script = readFileSync(path.join(root, "static/js/kanban-core.js"), "utf8");

function setup(t, {html = fixtures.stage, adapter = {}} = {}) {
    const dom = new JSDOM(`<!doctype html><body><div class="kanban-scroll" data-kanban><div class="kanban-lanes" data-kanban-lanes>${html}</div></div><div data-board-toasts></div></body>`,
        {url: "http://localhost/demandas/kanban/", runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => dom.window.close());
    const {window} = dom;
    const {document} = window;
    window.eval(script);
    const calls = [];
    const base = {
        move(ctx) { return new Promise((resolve, reject) => calls.push({ctx, resolve, reject})); },
    };
    const api = window.LPSKanbanCore.init(document.querySelector("[data-kanban]"), Object.assign(base, adapter));
    const h = {
        window, document, api, calls,
        lane: (key) => document.querySelector(`[data-lane][data-lane-key="${key}"]`),
        card: (id) => document.querySelector(`[data-card][data-item-id="${id}"]`),
        ids: (key) => [...h.lane(key).querySelectorAll("[data-card]")].map((node) => node.dataset.itemId),
        count: (key) => h.lane(key).querySelector("[data-lane-count]").textContent,
        emptyHidden: (key) => h.lane(key).querySelector("[data-lane-empty]").hidden,
        toasts: () => [...document.querySelectorAll(".board-toast")].map((node) => node.textContent),
        fire(node, type, init) {
            const event = new window.Event(type, Object.assign({bubbles: true, cancelable: true}, init));
            node.dispatchEvent(event);
            return event;
        },
        drag(card) { h.fire(card, "dragstart"); },
        over(lane) { return h.fire(lane.querySelector("[data-lane-body]"), "dragover"); },
        drop(lane) { return h.fire(lane.querySelector("[data-lane-body]"), "drop"); },
        tick: () => new Promise((resolve) => setTimeout(resolve, 5)),  // o do Node: os testes trocam window.setTimeout
    };
    return h;
}

// -- arrastar ----------------------------------------------------------------------------------------

test("só as raias que recebem o cartão marcam 'solte aqui'; a de outro setor e a própria não convidam", (t) => {
    const h = setup(t);
    h.drag(h.card(1));
    assert.equal(h.card(1).classList.contains("is-dragging"), true);

    assert.equal(h.over(h.lane(11)).defaultPrevented, true);  // outra etapa do mesmo setor
    assert.equal(h.lane(11).classList.contains("is-drop-target"), true);
    assert.equal(h.over(h.lane("empty")).defaultPrevented, true);  // a raia em branco recebe qualquer cartão
    assert.equal(h.lane(11).classList.contains("is-drop-target"), false, "a marca anda junto com o ponteiro");
    assert.equal(h.lane("empty").classList.contains("is-drop-target"), true);

    const other = h.over(h.lane(20));  // etapa do Financeiro: o cartão é do Orçamento
    assert.equal(other.defaultPrevented, false, "sem preventDefault o cursor mostra 'não pode'");
    assert.equal(h.lane(20).classList.contains("is-drop-target"), false);
    assert.equal(h.lane("empty").classList.contains("is-drop-target"), false, "passar por uma raia recusada limpa a marca anterior");

    const own = h.over(h.lane(10));
    assert.equal(own.defaultPrevented, true);
    assert.equal(h.lane(10).classList.contains("is-drop-target"), false, "a própria raia não convida");
});

test("uma raia fechada nunca recebe (responsável sem valor)", (t) => {
    const h = setup(t, {html: fixtures.owner});
    h.drag(h.card(1));
    assert.equal(h.over(h.lane("empty")).defaultPrevented, false);
    assert.equal(h.lane("empty").hasAttribute("data-lane-closed"), true);
    assert.equal(h.over(h.lane(2)).defaultPrevented, true);
});

test("um cartão que não é arrastável não inicia arrasto", (t) => {
    const h = setup(t);
    assert.equal(h.card(3).hasAttribute("draggable"), false, "concluída: sem draggable no HTML");
    h.drag(h.card(3));
    assert.equal(h.card(3).classList.contains("is-dragging"), false);
    assert.equal(h.over(h.lane(11)).defaultPrevented, false);
});

test("soltar move o cartão na hora, atualiza as contagens e o vazio, e confirma com o servidor", async (t) => {
    let reloaded = 0;
    const h = setup(t, {adapter: {reload() { reloaded += 1; return Promise.resolve(fixtures.stage); }}});
    h.drag(h.card(4));
    h.over(h.lane(10));
    h.drop(h.lane(10));
    await h.tick();

    assert.equal(h.calls.length, 1);
    assert.deepEqual([h.calls[0].ctx.itemId, h.calls[0].ctx.laneKey, h.calls[0].ctx.laneLabel, h.calls[0].ctx.updatedAt],
        ["4", "10", "A fazer", "2026-10-03T10:00:00+00:00"]);
    assert.deepEqual(h.ids(10), ["1", "2", "3", "4"], "o cartão entra no fim da raia");
    assert.deepEqual([h.count(10), h.count(11)], ["4", "0"]);
    assert.equal(h.emptyHidden(11), false, "a raia que ficou sem cartões mostra o vazio");
    assert.equal(h.card(4).classList.contains("is-saving"), true);
    assert.equal(h.lane(10).classList.contains("is-drop-target"), false);
    assert.equal(h.card(4).classList.contains("is-dragging"), false);

    h.calls[0].resolve({message: "Demanda movida para “A fazer”."});
    await h.tick();
    assert.equal(h.card(4) === null || h.card(4).classList.contains("is-saving"), false);
    assert.deepEqual(h.toasts(), ["Demanda movida para “A fazer”."]);
    assert.equal(reloaded, 1, "depois de gravar, as raias vêm do servidor");
});

test("soltar na mesma raia, numa raia que recusa ou fora das raias não grava nada", async (t) => {
    const h = setup(t);
    h.drag(h.card(1));
    h.drop(h.lane(10));
    h.drag(h.card(1));
    h.drop(h.lane(20));
    h.drag(h.card(1));
    h.fire(h.document.querySelector("[data-kanban-lanes]"), "drop");
    await h.tick();
    assert.equal(h.calls.length, 0);
    assert.deepEqual(h.ids(10), ["1", "2", "3"]);
});

test("se o servidor recusa, o cartão volta ao lugar de antes com a mensagem dele e nada é redesenhado", async (t) => {
    let reloaded = 0;
    const h = setup(t, {adapter: {reload() { reloaded += 1; return Promise.resolve(fixtures.stage); }}});
    h.drag(h.card(2));
    h.drop(h.lane("empty"));
    await h.tick();
    assert.deepEqual(h.ids("empty"), ["2"]);
    assert.deepEqual(h.ids(10), ["1", "3"]);

    h.calls[0].reject(new Error("A etapa escolhida não pertence ao setor atual."));
    await h.tick();
    assert.deepEqual(h.ids(10), ["1", "2", "3"], "voltou para o MEIO, não para o fim");
    assert.deepEqual([h.count("empty"), h.count(10)], ["0", "3"]);
    assert.equal(h.emptyHidden("empty"), false);
    assert.equal(h.card(2).classList.contains("is-saving"), false);
    assert.deepEqual(h.toasts(), ["A etapa escolhida não pertence ao setor atual."]);
    assert.equal(h.document.querySelector(".board-toast").classList.contains("is-error"), true);
    assert.equal(reloaded, 0);
});

test("versão velha (409): desfaz e traz as raias do servidor (que já não têm o cartão que outra pessoa tirou)", async (t) => {
    const server = fixtures.stage.replace(/<article class="kanban-card" data-card data-item-id="2"[\s\S]*?<\/article>/, "");
    assert.notEqual(server, fixtures.stage);
    const h = setup(t, {adapter: {reload() { return Promise.resolve(server); }}});
    h.drag(h.card(1));
    h.drop(h.lane(11));
    await h.tick();
    const conflict = new Error("Esta informação foi alterada por outra pessoa.");
    conflict.refresh = true;
    h.calls[0].reject(conflict);
    await h.tick();
    await h.tick();
    assert.deepEqual(h.ids(10), ["1", "3"], "o que vale é o que o servidor mandou");
    assert.deepEqual(h.ids(11), ["4"], "o cartão 1 voltou: o movimento dele foi desfeito");
    assert.deepEqual(h.toasts(), ["Esta informação foi alterada por outra pessoa."]);
});

test("beforeMove que nega: nada muda na tela e nada é enviado; que aceita: segue", async (t) => {
    const answers = [false, true];
    const h = setup(t, {adapter: {beforeMove() { return Promise.resolve(answers.shift()); }}});
    h.drag(h.card(1));
    h.drop(h.lane(11));
    await h.tick();
    assert.equal(h.calls.length, 0);
    assert.deepEqual(h.ids(10), ["1", "2", "3"], "cancelou: o cartão nem saiu do lugar");

    h.drag(h.card(1));
    h.drop(h.lane(11));
    await h.tick();
    assert.equal(h.calls.length, 1);
    assert.deepEqual(h.ids(11), ["4", "1"]);
});

test("um erro síncrono do adaptador também desfaz", async (t) => {
    const h = setup(t, {adapter: {move() { throw new Error("quebrou"); }}});
    h.drag(h.card(1));
    h.drop(h.lane(11));
    await h.tick();
    assert.deepEqual(h.ids(10), ["1", "2", "3"]);
    assert.deepEqual(h.toasts(), ["quebrou"]);
});

test("redesenhar só acontece quando tudo terminou: duas gravações em andamento = um redesenho no fim", async (t) => {
    let reloaded = 0;
    const h = setup(t, {adapter: {reload() { reloaded += 1; return Promise.resolve(fixtures.stage); }}});
    h.drag(h.card(1));
    h.drop(h.lane(11));
    h.drag(h.card(2));
    h.drop(h.lane(11));
    await h.tick();
    assert.equal(h.calls.length, 2);
    h.calls[0].resolve({});
    await h.tick();
    assert.equal(reloaded, 0, "a segunda ainda está gravando: trocar as raias agora arrancaria o cartão dela");
    h.calls[1].resolve({});
    await h.tick();
    assert.equal(reloaded, 1);
});

test("sem reload no adaptador a tela fica como o movimento otimista deixou", async (t) => {
    const h = setup(t);
    h.drag(h.card(1));
    h.drop(h.lane(11));
    await h.tick();
    h.calls[0].resolve({updatedAt: "2026-10-03T11:00:00+00:00"});
    await h.tick();
    assert.deepEqual(h.ids(11), ["4", "1"]);
    assert.equal(h.card(1).dataset.updatedAt, "2026-10-03T11:00:00+00:00", "a próxima gravação leva a versão nova");
});

test("sem a área de avisos nada quebra", async (t) => {
    const h = setup(t);
    h.document.querySelector("[data-board-toasts]").remove();
    h.drag(h.card(1));
    h.drop(h.lane(11));
    await h.tick();
    h.calls[0].resolve({});
    await h.tick();
    assert.deepEqual(h.ids(11), ["4", "1"]);
});

// -- menu "Mover para…" ---------------------------------------------------------------------------

function openMenu(h, id) {
    const button = h.card(id).querySelector("[data-card-menu]");
    button.focus();
    button.click();
    return button;
}
const popover = (h) => h.document.querySelector(".board-pop");
const menuLabels = (h) => [...popover(h).querySelectorAll("[role=menuitem]")].map((node) => node.textContent);

test("o menu lista só os destinos válidos, com o setor quando há mistura, e foca o primeiro", (t) => {
    const h = setup(t);
    const button = openMenu(h, 1);
    assert.deepEqual(menuLabels(h), ["Sem estágio", "Levantamento — Orçamento"], "nem a própria raia nem a de outro setor");
    assert.equal(popover(h).getAttribute("role"), "menu");
    assert.equal(button.getAttribute("aria-expanded"), "true");
    assert.equal(h.document.activeElement, popover(h).querySelector("[role=menuitem]"));
    assert.equal(popover(h).querySelector("svg use").getAttribute("href"), "#i-arrow-right");
});

test("setas, Home e End percorrem o menu; Esc fecha e devolve o foco ao ⋯", (t) => {
    const h = setup(t);
    const button = openMenu(h, 1);
    const items = [...popover(h).querySelectorAll("[role=menuitem]")];
    const key = (name) => popover(h).dispatchEvent(new h.window.KeyboardEvent("keydown", {key: name, bubbles: true, cancelable: true}));
    key("ArrowDown");
    assert.equal(h.document.activeElement, items[1]);
    key("ArrowDown");
    assert.equal(h.document.activeElement, items[0], "dá a volta");
    key("ArrowUp");
    assert.equal(h.document.activeElement, items[1]);
    key("Home");
    assert.equal(h.document.activeElement, items[0]);
    key("End");
    assert.equal(h.document.activeElement, items[1]);
    key("Escape");
    assert.equal(popover(h), null);
    assert.equal(button.hasAttribute("aria-expanded"), false);
    assert.equal(h.document.activeElement, button);
});

test("clicar no ⋯ de novo fecha; clicar fora fecha; abrir outro menu fecha o anterior", (t) => {
    const h = setup(t);
    const button = openMenu(h, 1);
    button.click();
    assert.equal(popover(h), null);
    openMenu(h, 1);
    h.document.body.dispatchEvent(new h.window.Event("mousedown", {bubbles: true}));
    assert.equal(popover(h), null);
    openMenu(h, 1);
    openMenu(h, 4);
    assert.equal(h.document.querySelectorAll(".board-pop").length, 1);
});

test("girar a tela (a largura muda) fecha o menu; só a altura mudar (barra do navegador no celular) não", (t) => {
    const h = setup(t);
    openMenu(h, 1);
    h.window.innerHeight = 500;
    h.window.dispatchEvent(new h.window.Event("resize"));
    assert.notEqual(popover(h), null, "só a altura mudou: o menu continua");
    h.window.innerWidth = 700;
    h.window.dispatchEvent(new h.window.Event("resize"));
    assert.equal(popover(h), null, "a largura mudou: fecha");
});

test("escolher no menu move o cartão como o arrasto e leva o foco ao ⋯ dele", async (t) => {
    const h = setup(t);
    openMenu(h, 1);
    [...popover(h).querySelectorAll("[role=menuitem]")].find((node) => node.textContent.startsWith("Levantamento")).click();
    await h.tick();
    assert.equal(popover(h), null);
    assert.deepEqual(h.ids(11), ["4", "1"]);
    assert.equal(h.calls[0].ctx.laneKey, "11");
    assert.equal(h.document.activeElement, h.card(1).querySelector("[data-card-menu]"));
});

test("um erro depois do menu devolve o cartão e o foco continua nele", async (t) => {
    const h = setup(t);
    openMenu(h, 2);
    popover(h).querySelector("[role=menuitem]").click();
    await h.tick();
    h.calls[0].reject(new Error("Sem permissão."));
    await h.tick();
    assert.deepEqual(h.ids(10), ["1", "2", "3"]);
    assert.equal(h.document.activeElement, h.card(2).querySelector("[data-card-menu]"));
});

test("beforeMove também vale para o menu", async (t) => {
    const h = setup(t, {adapter: {beforeMove() { return false; }}});
    openMenu(h, 1);
    popover(h).querySelector("[role=menuitem]").click();
    await h.tick();
    assert.equal(h.calls.length, 0);
    assert.deepEqual(h.ids(10), ["1", "2", "3"]);
});

test("um cartão sem destino tem o ⋯ só pelas ações do anfitrião: nunca 'Mover para', nunca desabilitado", (t) => {
    const h = setup(t, {adapter: {menuItems() { return [{label: "Abrir demanda", icon: "eye", onClick() {}}]; }}});
    assert.equal(h.card(3).hasAttribute("draggable"), false, "concluída: não arrasta");
    h.card(3).querySelector("[data-card-menu]").click();
    assert.deepEqual([...h.document.querySelectorAll(".board-pop .board-menu__item")].map((n) => n.textContent), ["Abrir demanda"]);
    assert.equal(h.document.querySelector(".board-menu__label"), null);
    assert.equal(h.document.querySelectorAll("[disabled]").length, 0);
});

// -- redesenho ----------------------------------------------------------------------------------------

test("redesenhar preserva a rolagem lateral e a de cada raia", (t) => {
    const h = setup(t);
    const scroller = h.document.querySelector("[data-kanban]");
    scroller.scrollLeft = 340;
    h.lane(10).querySelector("[data-lane-body]").scrollTop = 120;
    h.api.redraw(fixtures.stage);
    assert.equal(scroller.scrollLeft, 340);
    assert.equal(h.lane(10).querySelector("[data-lane-body]").scrollTop, 120);
    assert.equal(h.lane(11).querySelector("[data-lane-body]").scrollTop, 0);
});

test("redesenhar devolve o foco ao mesmo cartão (no ⋯ se estava nele)", (t) => {
    const h = setup(t);
    h.card(2).querySelector("[data-card-menu]").focus();
    h.api.redraw(fixtures.stage);
    assert.equal(h.document.activeElement, h.card(2).querySelector("[data-card-menu]"));
    h.card(1).querySelector("[data-card-title]").focus();
    h.api.redraw(fixtures.stage);
    assert.equal(h.document.activeElement, h.card(1).querySelector("[data-card-title]"));
});

test("se o filtro tirou o cartão da tela, o foco vai para o título da raia onde ele estava", (t) => {
    const h = setup(t);
    h.card(4).querySelector("[data-card-menu]").focus();
    const without = fixtures.stage.replace(/<article class="kanban-card" data-card data-item-id="4"[\s\S]*?<\/article>/, "");
    assert.notEqual(without, fixtures.stage, "o cenário precisa realmente remover o cartão 4");
    h.api.redraw(without);
    assert.equal(h.card(4), null);
    assert.equal(h.document.activeElement, h.lane(11).querySelector("[data-lane-title]"));
});

test("redesenhar sem foco nas raias não rouba o foco de quem está em outro lugar", (t) => {
    const h = setup(t);
    const outside = h.document.createElement("input");
    h.document.body.appendChild(outside);
    outside.focus();
    h.api.redraw(fixtures.stage);
    assert.equal(h.document.activeElement, outside);
});

test("um redesenho que não é texto é ignorado", (t) => {
    const h = setup(t);
    h.api.redraw(undefined);
    h.api.redraw(null);
    assert.equal(h.document.querySelectorAll("[data-lane]").length, 4);
});

test("falha ao recarregar as raias avisa e não apaga a tela", async (t) => {
    const h = setup(t, {adapter: {reload() { return Promise.reject(new Error("Sem conexão com o servidor.")); }}});
    h.drag(h.card(1));
    h.drop(h.lane(11));
    await h.tick();
    h.calls[0].resolve({});
    await h.tick();
    await h.tick();
    assert.equal(h.document.querySelectorAll("[data-lane]").length, 4);
    assert.ok(h.toasts().includes("Sem conexão com o servidor."));
});

// -- confirmação --------------------------------------------------------------------------------------

function dialogOf(h) { return h.document.querySelector(".board-dialog"); }

test("a confirmação: Confirmar resolve true, Cancelar/Esc/× /fundo resolvem false e o foco volta", async (t) => {
    const h = setup(t);
    const opener = h.document.createElement("button");
    h.document.body.appendChild(opener);
    const ask = () => { opener.focus(); return h.window.LPSKanbanCore.confirm({title: "Mudar o setor", message: "Etapa e status voltam ao padrão.", confirmLabel: "Mudar setor"}); };

    let answer = ask();
    assert.equal(dialogOf(h).getAttribute("role"), "alertdialog");
    assert.equal(dialogOf(h).querySelector("h2").textContent, "Mudar o setor");
    assert.equal(h.document.activeElement.textContent, "Mudar setor");
    h.document.activeElement.click();
    assert.equal(await answer, true);
    assert.equal(dialogOf(h), null);
    assert.equal(h.document.activeElement, opener);

    answer = ask();
    [...dialogOf(h).querySelectorAll("button")].find((node) => node.textContent === "Cancelar").click();
    assert.equal(await answer, false);

    answer = ask();
    h.document.dispatchEvent(new h.window.KeyboardEvent("keydown", {key: "Escape", bubbles: true, cancelable: true}));
    assert.equal(await answer, false);
    assert.equal(h.document.activeElement, opener);

    answer = ask();
    dialogOf(h).querySelector(".board-dialog__close").click();
    assert.equal(await answer, false);

    answer = ask();
    h.document.querySelector(".board-dialog-backdrop").dispatchEvent(new h.window.Event("mousedown", {bubbles: true}));
    assert.equal(await answer, false);
});

test("a confirmação prende o Tab dentro dela", (t) => {
    const h = setup(t);
    h.window.LPSKanbanCore.confirm({title: "T", message: "M"});
    const stops = [...dialogOf(h).querySelectorAll("button")];
    assert.equal(stops.length, 3);
    const tab = (shiftKey) => h.document.dispatchEvent(new h.window.KeyboardEvent("keydown", {key: "Tab", shiftKey, bubbles: true, cancelable: true}));
    assert.equal(h.document.activeElement, stops[2]);
    tab(false);
    assert.equal(h.document.activeElement, stops[0], "do último volta ao primeiro");
    tab(true);
    assert.equal(h.document.activeElement, stops[2]);
});

// -- contrato v2: movimento síncrono, aviso silencioso, renomear, ações do anfitrião, configurar cartões, primitivas --------

const v2 = (t, adapter = {}) => setup(t, {html: fixtures.v2, adapter});
const enter = (h, node) => node.dispatchEvent(new h.window.KeyboardEvent("keydown", {key: "Enter", bubbles: true, cancelable: true}));
const escape = (h, node) => node.dispatchEvent(new h.window.KeyboardEvent("keydown", {key: "Escape", bubbles: true, cancelable: true}));

test("v2: sem confirmação o cartão se mexe no mesmo instante, antes de qualquer espera", (t) => {
    const h = v2(t);
    h.drag(h.card(101));
    h.drop(h.lane(2));
    assert.deepEqual(h.ids(2), ["101"], "nada de esperar um microtask: o cartão já está na raia nova");
    assert.deepEqual([h.count(1), h.count(2)], ["1", "1"]);
});

test("v2: um movimento 'silent' não avisa; o padrão avisa", async (t) => {
    const h = v2(t);
    h.drag(h.card(101));
    h.drop(h.lane(2));
    h.calls[0].resolve({silent: true});
    await h.tick();
    assert.deepEqual(h.toasts(), [], "Quadros nunca avisou sucesso ao mover e continua assim");
    h.drag(h.card(101));
    h.drop(h.lane(1));
    h.calls[1].resolve({});
    await h.tick();
    assert.deepEqual(h.toasts(), ["Movido para “Novo”."]);
});

test("v2: clicar no título editável renomeia no lugar e grava com a versão do cartão", async (t) => {
    const renames = [];
    const h = v2(t, {rename(ctx) { renames.push({itemId: ctx.itemId, title: ctx.title, previous: ctx.previous}); return Promise.resolve({updatedAt: "2026-10-03T12:00:00+00:00"}); }});
    h.card(101).querySelector("[data-card-title]").click();
    const input = h.card(101).querySelector(".board-inline-input");
    assert.equal(input.value, "Arena Norte");
    input.value = "Arena Sul";
    enter(h, input);
    assert.equal(h.card(101).querySelector("[data-card-title]").textContent, "Arena Sul", "o título muda na hora");
    await h.tick();
    assert.deepEqual(renames, [{itemId: "101", title: "Arena Sul", previous: "Arena Norte"}]);
    assert.equal(h.card(101).dataset.updatedAt, "2026-10-03T12:00:00+00:00", "a próxima gravação leva a versão nova");
});

test("v2: se o servidor recusa o novo título, o texto antigo volta com a mensagem", async (t) => {
    const h = v2(t, {rename() { return Promise.reject(new Error("O título não pode ficar vazio.")); }});
    h.card(101).querySelector("[data-card-title]").click();
    const input = h.card(101).querySelector(".board-inline-input");
    input.value = "x";
    enter(h, input);
    await h.tick();
    assert.equal(h.card(101).querySelector("[data-card-title]").textContent, "Arena Norte");
    assert.deepEqual(h.toasts(), ["O título não pode ficar vazio."]);
});

test("v2: Esc e título igual não gravam nada; o servidor pode devolver o título que valeu", async (t) => {
    const calls = [];
    const h = v2(t, {rename(ctx) { calls.push(ctx.title); return Promise.resolve({title: "Arena Sul (ajustado)"}); }});
    const open = () => { h.card(101).querySelector("[data-card-title]").click(); return h.card(101).querySelector(".board-inline-input"); };
    let input = open();
    input.value = "Outro";
    escape(h, input);
    input = open();
    enter(h, input);  // não mudou
    await h.tick();
    assert.deepEqual(calls, []);
    assert.equal(h.card(101).querySelector("[data-card-title]").textContent, "Arena Norte");
    input = open();
    input.value = "Arena Sul";
    enter(h, input);
    await h.tick();
    assert.equal(h.card(101).querySelector("[data-card-title]").textContent, "Arena Sul (ajustado)");
});

test("v2: título vazio vira 'Sem título' e é gravado vazio (quem não aceita recusa no servidor)", async (t) => {
    const calls = [];
    const h = v2(t, {rename(ctx) { calls.push(ctx.title); return Promise.resolve({}); }});
    h.card(101).querySelector("[data-card-title]").click();
    const input = h.card(101).querySelector(".board-inline-input");
    input.value = "   ";
    enter(h, input);
    await h.tick();
    assert.deepEqual(calls, [""]);
    assert.equal(h.card(101).querySelector("[data-card-title]").textContent, "Sem título");
    assert.equal(h.card(101).querySelector("[data-card-title]").classList.contains("is-empty"), true);
});

test("v2: o título que não é editável (sem role=textbox) não abre edição", (t) => {
    const h = v2(t, {rename() { throw new Error("não devia chamar"); }});
    h.card(102).querySelector("[data-card-title]").click();
    assert.equal(h.card(102).querySelector(".board-inline-input"), null);
});

test("v2: Enter no título focado também renomeia; startRename funciona por chamada (depois de criar um cartão)", (t) => {
    const h = v2(t, {rename() { return Promise.resolve({}); }});
    enter(h, h.card(101).querySelector("[data-card-title]"));
    assert.ok(h.card(101).querySelector(".board-inline-input"));
    // um cartão vindo do servidor sem o role (marcação mínima): a chamada direta não exige o role, o gatilho por clique sim
    h.api.redraw('<section data-lane data-lane-key="9" data-lane-label="X"><div data-lane-body><article data-card data-item-id="300"><span data-card-title class="is-empty">Sem título</span></article><p data-lane-empty hidden></p></div></section>');
    h.api.startRename(h.card(300));
    assert.ok(h.card(300).querySelector(".board-inline-input"));
    assert.equal(h.card(300).querySelector(".board-inline-input").value, "", "estava vazio: a edição começa vazia, não em 'Sem título'");
});

test("v2: sem adapter.rename o núcleo não abre edição", (t) => {
    const h = v2(t);
    h.card(101).querySelector("[data-card-title]").click();
    assert.equal(h.card(101).querySelector(".board-inline-input"), null);
});

test("v2: o ⋯ junta 'Mover para' e as ações do anfitrião, com ícone, separador e perigo", (t) => {
    const done = [];
    const h = v2(t, {menuItems(ctx) {
        return [{label: "Renomear", icon: "file-text", onClick: () => done.push("renomear " + ctx.itemId)}, {label: "Excluir item", icon: "trash", danger: true, onClick: () => done.push("excluir")}];
    }});
    h.card(101).querySelector("[data-card-menu]").click();
    const pop = h.document.querySelector(".board-pop");
    assert.deepEqual([...pop.querySelectorAll(".board-menu__label, .board-menu__item, .board-menu__sep")].map((n) => n.className.split(" ")[0] + ":" + n.textContent.trim()),
        ["board-menu__label:Mover para", "board-menu__item:Ganho", "board-menu__sep:", "board-menu__item:Renomear", "board-menu__item:Excluir item"]);
    assert.equal(pop.querySelector(".is-danger span").textContent, "Excluir item");
    assert.equal(pop.querySelectorAll("svg use")[1].getAttribute("href"), "#i-file-text");
    [...pop.querySelectorAll(".board-menu__item")].find((n) => n.textContent === "Renomear").click();
    assert.deepEqual(done, ["renomear 101"]);
    assert.equal(h.document.querySelector(".board-pop"), null, "escolher fecha o menu");
});

test("v2: um cartão que não arrasta mostra só as ações do anfitrião (sem 'Mover para')", (t) => {
    const h = v2(t, {menuItems() { return [{label: "Excluir item", icon: "trash", danger: true}]; }});
    h.card(102).querySelector("[data-card-menu]").click();
    assert.deepEqual([...h.document.querySelectorAll(".board-pop .board-menu__item")].map((n) => n.textContent), ["Excluir item"]);
    assert.equal(h.document.querySelector(".board-menu__label"), null);
});

test("v2: sem destino e sem ação o ⋯ avisa em vez de abrir um menu vazio", (t) => {
    const h = v2(t);
    h.card(102).querySelector("[data-card-menu]").click();
    assert.equal(h.document.querySelector(".board-pop"), null);
    assert.deepEqual(h.toasts(), ["Não há ações disponíveis para este cartão."]);
});

test("v2: o ⋮ da raia abre os itens do anfitrião, fecha ao clicar de novo e escolher fecha", (t) => {
    const seen = [];
    const done = [];
    const h = v2(t, {laneMenu(ctx) {
        seen.push([ctx.laneKey, ctx.lane.dataset.laneLabel, ctx.anchor.hasAttribute("data-lane-menu")]);
        return [{label: "Renomear etiqueta", icon: "file-text", onClick: () => done.push("renomear")}, {label: "Editar etiquetas", onClick: () => done.push("editar")}];
    }});
    const button = h.lane(1).querySelector("[data-lane-menu]");
    button.click();
    const pop = h.document.querySelector(".board-pop");
    assert.equal(pop.getAttribute("aria-label"), "Opções da raia Novo");
    assert.deepEqual([...pop.querySelectorAll(".board-menu__item")].map((n) => n.textContent), ["Renomear etiqueta", "Editar etiquetas"]);
    assert.deepEqual(seen, [["1", "Novo", true]]);
    assert.equal(button.getAttribute("aria-expanded"), "true");
    button.click();
    assert.equal(h.document.querySelector(".board-pop"), null, "o mesmo botão de novo fecha");
    button.click();
    [...h.document.querySelectorAll(".board-menu__item")].find((n) => n.textContent === "Editar etiquetas").click();
    assert.deepEqual(done, ["editar"]);
    assert.equal(h.document.querySelector(".board-pop"), null);
});

test("v2: o ⋮ da raia sem itens não abre menu vazio, e sem o gancho o núcleo nem o intercepta", (t) => {
    const empty = v2(t, {laneMenu() { return []; }});
    empty.lane(1).querySelector("[data-lane-menu]").click();
    assert.equal(empty.document.querySelector(".board-pop"), null);
    assert.deepEqual(empty.toasts(), [], "sem itens, sem aviso: o servidor só mostra o botão quando há o que oferecer");

    const bare = v2(t);
    const click = bare.fire(bare.lane(1).querySelector("[data-lane-menu]"), "click");
    assert.equal(bare.document.querySelector(".board-pop"), null);
    assert.equal(click.defaultPrevented, false);
});

test("v2: o '+ Adicionar' chama o anfitrião com a raia; sem o gancho o link segue o endereço dele", (t) => {
    const asked = [];
    const h = v2(t, {addCard(ctx) { asked.push([ctx.lane.dataset.laneKey, ctx.anchor.hasAttribute("data-kanban-add")]); }});
    const click = h.fire(h.lane(2).querySelector("[data-kanban-add]"), "click");
    assert.deepEqual(asked, [["2", true]]);
    assert.equal(click.defaultPrevented, true);

    const link = setup(t);  // Demandas: o "+ Adicionar" é um link para a janela "Nova demanda"
    const anchor = link.lane(10).querySelector("a[data-kanban-add]");
    assert.match(anchor.getAttribute("href"), /^\/demandas\/nova\/\?etapa=10&setor=1$/);
    assert.equal(link.fire(anchor, "click").defaultPrevented, false, "o núcleo não atrapalha o link");
});

test("v2: as primitivas do núcleo servem ao anfitrião (menu avulso, janela, edição de texto)", (t) => {
    const h = v2(t);
    const picked = [];
    h.api.openMenu(h.lane(1).querySelector("[data-lane-menu]"), [{label: "Renomear etiqueta", icon: "file-text", onClick: () => picked.push("r")}, {separator: true}, {label: "Editar etiquetas", onClick: () => picked.push("e")}], "Opções da raia Novo");
    assert.equal(h.document.querySelector(".board-pop").getAttribute("aria-label"), "Opções da raia Novo");
    h.document.querySelectorAll(".board-menu__item")[1].click();
    assert.deepEqual(picked, ["e"]);

    const dialog = h.window.LPSKanbanCore.ui.openDialog("Etiquetas", h.document.createElement("p"), [{label: "Concluir", kind: "primary"}]);
    dialog.error("Algo deu errado.");
    assert.equal(h.document.querySelector(".board-dialog__error").textContent, "Algo deu errado.");
    assert.equal(h.document.querySelector(".board-dialog__error").hidden, false);
    escape(h, h.document);
    assert.equal(h.document.querySelector(".board-dialog"), null);

    const target = h.card(101).querySelector("[data-card-title]");
    const committed = [];
    h.window.LPSKanbanCore.ui.inlineEdit(target, {value: "Arena Norte", onCommit: (v) => committed.push(v)});
    const input = h.card(101).querySelector(".board-inline-input");
    input.value = "Novo";
    enter(h, input);
    assert.deepEqual(committed, ["Novo"]);
    assert.equal(target.style.display, "");
});

// os objetos criados dentro do jsdom têm outro protótipo: comparar só a estrutura
const plain = (value) => JSON.parse(JSON.stringify(value));

function configSpec(saved, extra = {}) {
    return Object.assign({
        controls: [
            {type: "check", key: "show_empty", label: "Mostrar raias vazias", value: true},
            {type: "select", key: "sum_column", label: "Somar valor no cabeçalho da raia", choices: [["", "Não somar"], ["15", "Valor"]], value: "15", parse: (v) => (v ? Number(v) : null)},
            {type: "check", key: "show_field_names", label: "Mostrar o nome de cada campo no cartão", value: false},
        ],
        fields: [{id: 11, name: "Cliente"}, {id: 12, name: "Responsável"}, {id: 13, name: "Status"}, {id: 14, name: "Prazo"}],
        selected: [13, 11],
        save: (change) => { saved.push(change); return Promise.resolve(); },
    }, extra);
}
const controlBoxes = (h) => [...h.document.querySelectorAll(".kanban-config__controls input[type=checkbox]")].filter((box) => !box.closest(".kanban-config__field"));

test("v2: Configurar cartões — controles gravam sozinhos, com o valor já convertido", (t) => {
    const saved = [];
    const h = v2(t);
    const dialog = h.api.openConfig(configSpec(saved));
    assert.equal(dialog.root.classList.contains("board-dialog--wide"), true);
    assert.equal(h.document.querySelector(".board-dialog h2").textContent, "Configurar cartões");
    const [empty, names] = controlBoxes(h);
    assert.equal(empty.checked, true);
    assert.equal(names.checked, false);
    empty.checked = false;
    empty.dispatchEvent(new h.window.Event("change", {bubbles: true}));
    const select = h.document.querySelector(".kanban-config__controls select");
    assert.equal(select.value, "15");
    select.value = "";
    select.dispatchEvent(new h.window.Event("change", {bubbles: true}));
    names.checked = true;
    names.dispatchEvent(new h.window.Event("change", {bubbles: true}));
    assert.deepEqual(plain(saved), [{show_empty: false}, {sum_column: null}, {show_field_names: true}]);
});

function captureTimers(h) {
    const timers = [];
    h.window.setTimeout = (fn, ms) => { timers.push({fn, ms}); return timers.length; };
    h.window.clearTimeout = (id) => { if (timers[id - 1]) timers[id - 1].fn = () => {}; };
    return timers;
}

test("v2: Configurar cartões — os campos do cartão vêm primeiro, mudam de ordem e gravam UMA vez depois da pausa", async (t) => {
    const saved = [];
    const h = v2(t);
    const timers = captureTimers(h);
    h.api.openConfig(configSpec(saved));
    const labels = () => [...h.document.querySelectorAll(".kanban-config__field label")].map((n) => n.textContent.trim());
    assert.deepEqual(labels(), ["Status", "Cliente", "Responsável", "Prazo"], "os do cartão primeiro, na ordem do cartão");
    const boxes = () => [...h.document.querySelectorAll(".kanban-config__field input[type=checkbox]")];
    assert.deepEqual(boxes().map((b) => b.checked), [true, true, false, false]);
    boxes()[2].checked = true;
    boxes()[2].dispatchEvent(new h.window.Event("change", {bubbles: true}));
    [...h.document.querySelectorAll(".kanban-config__field button")].find((n) => n.getAttribute("aria-label") === "Subir Responsável").click();
    assert.equal(saved.length, 0, "ainda esperando a pausa");
    timers.filter((timer) => timer.ms === 250).forEach((timer) => timer.fn());
    await h.tick();
    assert.deepEqual(plain(saved), [{card_fields: [13, 12, 11]}], "Responsável subiu e entrou; uma única gravação");
    assert.equal([...h.document.querySelectorAll(".kanban-config__field button")][0].disabled, true, "o primeiro não sobe");
});

test("v2: Configurar cartões — a pré-visualização é o primeiro cartão sem nada editável e acompanha o redesenho", (t) => {
    const h = v2(t);
    h.api.openConfig(configSpec([]));
    const preview = () => h.document.querySelector(".kanban-config__preview .kanban-card");
    assert.ok(preview());
    assert.equal(preview().classList.contains("is-preview"), true);
    assert.equal(preview().getAttribute("draggable"), null);
    assert.equal(preview().querySelector("[data-cell]"), null);
    assert.equal(preview().querySelector("[tabindex]"), null);
    assert.equal(preview().querySelector(".is-editable"), null);
    assert.equal(preview().querySelector("[data-card-title]").textContent, "Arena Norte");
    h.api.redraw(fixtures.v2.replace("Arena Norte", "Arena Renomeada"));
    assert.equal(preview().querySelector("[data-card-title]").textContent, "Arena Renomeada");
    h.api.redraw('<div class="kanban-state"></div>');
    assert.match(h.document.querySelector(".kanban-config__preview").textContent, /Ainda não há cartões para mostrar/);
});

test("v2: Configurar cartões — fechar a janela cancela a gravação pendente", (t) => {
    const saved = [];
    const h = v2(t);
    const timers = captureTimers(h);
    h.api.openConfig(configSpec(saved));
    const box = h.document.querySelector(".kanban-config__field input[type=checkbox]");
    box.checked = false;
    box.dispatchEvent(new h.window.Event("change", {bubbles: true}));
    [...h.document.querySelectorAll(".board-dialog__foot .btn")].find((n) => n.textContent === "Concluir").click();
    timers.forEach((timer) => timer.fn());
    assert.deepEqual(saved, []);
    assert.equal(h.document.querySelector(".board-dialog"), null);
});

test("v2: Configurar cartões — se gravar falha, o aviso vem do núcleo", async (t) => {
    const h = v2(t);
    h.api.openConfig(configSpec([], {save: () => Promise.reject(new Error("Sem permissão."))}));
    const [empty] = controlBoxes(h);
    empty.checked = false;
    empty.dispatchEvent(new h.window.Event("change", {bubbles: true}));
    await h.tick();
    assert.deepEqual(h.toasts(), ["Sem permissão."]);
});
