/* Tela Tarefas (static/js/task-center.js): "+ Adicionar" na Lista e nas colunas do Kanban.
   Requires jsdom@26.1.0 in NODE_PATH. Run from workflow: node --test tests/task-center.test.cjs */
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const path = require("node:path");
const {JSDOM} = require("jsdom");

const script = readFileSync(path.resolve(__dirname, "..", "static/js/task-center.js"), "utf8");
const tick = () => new Promise(resolve => setImmediate(resolve));
const flush = async () => { for (let i = 0; i < 10; i += 1) await tick(); };

const PAYLOAD = {
    me: 7, url: "/quadros/0/itens/novo/",
    boards: [
        {board_id: 11, label: "DEM-1 · Orçamento A", group_id: 21, person_column_id: 31, status_column_id: 32, status_options: {todo: 41, doing: 42, done: 43}},
        {board_id: 12, label: "DEM-2 · Sem status", group_id: 22, person_column_id: 33, status_column_id: null, status_options: {}},
    ],
};

function setup(t, {respond, payload = PAYLOAD} = {}) {
    const dom = new JSDOM(`<!doctype html><body>
        <table><tbody><tr class="task-center__add-row"><td><button type="button" data-task-add data-state="todo">+ Adicionar tarefa</button></td></tr></tbody></table>
        <section><button type="button" data-task-add data-state="doing">+ Adicionar</button></section>
        <script type="application/json" id="task-center-add">${JSON.stringify(payload)}</script></body>`,
        {url: "http://localhost/tarefas/", runScripts: "outside-only"});
    t.after(() => dom.window.close());
    const doc = dom.window.document;
    doc.cookie = "csrftoken=tok123";
    const calls = [];
    let reloads = 0;
    const fakeWindow = {
        fetch: (url, options) => { calls.push({url, options, body: JSON.parse(options.body)}); return respond ? respond() : Promise.resolve({ok: true, json: () => Promise.resolve({ok: true})}); },
        location: {reload: () => { reloads += 1; }},
    };
    dom.window.eval(script);
    dom.window.LPSTaskCenter.init(doc, fakeWindow);
    const $ = selector => doc.querySelector(selector);
    const click = node => node.dispatchEvent(new dom.window.MouseEvent("click", {bubbles: true, cancelable: true}));
    return {dom, doc, $, click, calls, reloads: () => reloads, api: dom.window.LPSTaskCenter};
}

test("buildBody: responsável sempre; Status só quando a coluna não é A fazer e o quadro tem a etiqueta", t => {
    const {api: raw} = setup(t);
    const api = {buildBody: (...args) => JSON.parse(JSON.stringify(raw.buildBody(...args)))}; // objetos de outro "realm" (jsdom)
    const [a, b] = PAYLOAD.boards;
    assert.deepEqual(api.buildBody(a, "X", "todo", 7), {group_id: 21, name: "X", initial: [{column_id: 31, value: 7}]});
    assert.deepEqual(api.buildBody(a, "X", "doing", 7).initial, [{column_id: 31, value: 7}, {column_id: 32, value: 42}]);
    assert.deepEqual(api.buildBody(a, "X", "done", 7).initial[1], {column_id: 32, value: 43});
    assert.deepEqual(api.buildBody(b, "X", "doing", 7).initial, [{column_id: 33, value: 7}], "quadro sem Status não manda Status");
});

test("clicar em '+ Adicionar' abre o formulário no lugar do botão, com as demandas oferecidas", t => {
    const {$, doc, click} = setup(t);
    const button = $("[data-state=todo]");
    click(button);
    const form = $("[data-task-add-form]");
    assert.ok(form);
    assert.equal(button.hidden, true);
    assert.deepEqual([...form.querySelectorAll("option")].map(o => o.textContent), ["DEM-1 · Orçamento A", "DEM-2 · Sem status"]);
    assert.equal(doc.activeElement, form.querySelector("input"));
    assert.equal(form.querySelector(".task-center__add-error").hidden, true);
});

test("nome vazio não envia e mostra o erro; Esc e Cancelar fecham e devolvem o botão", t => {
    const {$, $$, click, calls, doc} = setup(t);
    click($("[data-state=doing]"));
    const form = $("[data-task-add-form]");
    form.dispatchEvent(new (doc.defaultView.Event)("submit", {bubbles: true, cancelable: true}));
    assert.equal(calls.length, 0);
    assert.match(form.querySelector(".task-center__add-error").textContent, /nome da tarefa/);
    form.dispatchEvent(new (doc.defaultView.KeyboardEvent)("keydown", {key: "Escape", bubbles: true}));
    assert.equal($("[data-task-add-form]"), null);
    assert.equal($("[data-state=doing]").hidden, false);
    click($("[data-state=doing]"));
    click([...document_buttons(doc)].find(b => b.textContent === "Cancelar"));
    assert.equal($("[data-task-add-form]"), null);
});

function document_buttons(doc) { return doc.querySelectorAll("[data-task-add-form] button"); }

test("enviar: POST JSON no endereço do quadro escolhido, com CSRF, e recarrega ao concluir", async t => {
    const {$, click, calls, reloads, doc} = setup(t);
    click($("[data-state=doing]"));
    const form = $("[data-task-add-form]");
    form.querySelector("input").value = "  Comprar cabos ";
    form.querySelector("select").value = "11";
    form.dispatchEvent(new (doc.defaultView.Event)("submit", {bubbles: true, cancelable: true}));
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "/quadros/11/itens/novo/");
    assert.equal(calls[0].options.method, "POST");
    assert.equal(calls[0].options.headers["X-CSRFToken"], "tok123");
    assert.equal(calls[0].options.headers["Content-Type"], "application/json");
    assert.deepEqual(calls[0].body, {group_id: 21, name: "Comprar cabos", initial: [{column_id: 31, value: 7}, {column_id: 32, value: 42}]});
    await flush();
    assert.equal(reloads(), 1);
});

test("recusa do servidor (403/400) aparece no formulário, que continua aberto e utilizável; nada recarrega", async t => {
    const {$, click, reloads, doc} = setup(t, {respond: () => Promise.resolve({ok: false, status: 403, json: () => Promise.resolve({ok: false, error: "Você não pode editar tarefas neste Quadro de Demanda."})})});
    click($("[data-state=todo]"));
    const form = $("[data-task-add-form]");
    form.querySelector("input").value = "Algo";
    form.dispatchEvent(new (doc.defaultView.Event)("submit", {bubbles: true, cancelable: true}));
    assert.equal(form.querySelector("button[type=submit]").disabled, true, "travado enquanto envia");
    await flush();
    const error = form.querySelector(".task-center__add-error");
    assert.equal(error.hidden, false);
    assert.equal(error.textContent, "Você não pode editar tarefas neste Quadro de Demanda.");
    assert.equal(form.querySelector("button[type=submit]").disabled, false);
    assert.equal(reloads(), 0);
});

test("queda de conexão vira aviso e o texto do servidor entra como texto, nunca como HTML", async t => {
    const down = setup(t, {respond: () => Promise.reject(new Error("falhou"))});
    down.click(down.$("[data-state=todo]"));
    const form = down.$("[data-task-add-form]");
    form.querySelector("input").value = "Algo";
    form.dispatchEvent(new (down.doc.defaultView.Event)("submit", {bubbles: true, cancelable: true}));
    await flush();
    assert.equal(form.querySelector(".task-center__add-error").hidden, false);

    const evil = {...PAYLOAD, boards: [{...PAYLOAD.boards[0], label: "<img src=x onerror=alert(1)>"}]};
    const safe = setup(t, {payload: evil});
    safe.click(safe.$("[data-state=todo]"));
    assert.equal(safe.doc.querySelectorAll("[data-task-add-form] img").length, 0);
    assert.equal(safe.$("[data-task-add-form] option").textContent, "<img src=x onerror=alert(1)>");
});

test("sem demanda para adicionar ou sem os dados da tela, nada é ligado", t => {
    const dom = new JSDOM("<!doctype html><body><button data-task-add data-state='todo'>+</button></body>", {runScripts: "outside-only"});
    t.after(() => dom.window.close());
    dom.window.eval(script);
    assert.equal(dom.window.LPSTaskCenter.init(dom.window.document, dom.window), null);
});
