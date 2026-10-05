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
print(json.dumps({'stage': stage, 'owner': owner}))
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
        tick: () => new Promise((resolve) => window.setTimeout(resolve, 5)),
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

test("um cartão sem destino não tem ⋯ (nada desabilitado)", (t) => {
    const h = setup(t);
    assert.equal(h.card(3).querySelector("[data-card-menu]"), null);
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
