/* Adaptador do Kanban de Demandas (static/js/demand-kanban.js) sobre o núcleo (static/js/kanban-core.js).
   Requires jsdom@26.1.0 in NODE_PATH. Run from workflow: node --test tests/demand-kanban.test.cjs

   O que se prova aqui é a CONVERSA com o servidor: endereço e corpo do POST, o token CSRF certo mesmo quando não é o primeiro
   cookie, uma mensagem para cada resposta possível (400/403/404/409/rede/sessão vencida), o redesenho pelo fragmento com o
   mesmo recorte da página e a confirmação ao mudar de setor. A marcação vem do construtor real, sem banco. */
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

stage = render([group('empty', 'Sem estágio'), group(10, 'A fazer', [item(1), item(2)], sector_id=1), group(11, 'Levantamento', [item(4)], sector_id=1)], 'stage')
sector = render([group('empty', 'Sem setor'), group(1, 'Orçamento', [item(1)]), group(2, 'Financeiro', [item(2, sector_id=2)])], 'sector')
print(json.dumps({'stage': stage, 'sector': sector}))
`], {cwd: root, encoding: "utf8"}).trim());

const coreScript = readFileSync(path.join(root, "static/js/kanban-core.js"), "utf8");
const adapterScript = readFileSync(path.join(root, "static/js/demand-kanban.js"), "utf8");

function response(status, body, extra = {}) {
    const json = typeof body === "string" ? () => Promise.reject(new SyntaxError("não é JSON")) : () => Promise.resolve(body);
    return Object.assign({
        ok: status >= 200 && status < 300, status, redirected: false, json,
        text: () => Promise.resolve(typeof body === "string" ? body : JSON.stringify(body)),
    }, extra);
}

function setup(t, {html = fixtures.stage, groupBy = "stage", moveUrl = "/quadros/dominio/3/campos/9/itens/0/valor/", search = "?tab=todas&q=obra", handler, cookie = true} = {}) {
    const attrs = `data-kanban data-group-by="${groupBy}"${moveUrl ? ` data-move-url="${moveUrl}"` : ""}`;
    const dom = new JSDOM(`<!doctype html><body><div class="kanban-scroll" ${attrs}><div class="kanban-lanes" data-kanban-lanes>${html}</div></div><div data-board-toasts></div></body>`,
        {url: `http://localhost/demandas/kanban/${search}`, runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => dom.window.close());
    const {window} = dom;
    const {document} = window;
    if (cookie) {
        document.cookie = "sessionid=abc";
        document.cookie = "csrftoken=tok%2B1";
    }
    const requests = [];
    window.fetch = (url, options = {}) => {
        requests.push({url, options, body: options.body ? JSON.parse(options.body) : null});
        return Promise.resolve().then(() => handler(url, options, requests.length));
    };
    window.eval(coreScript);
    window.eval(adapterScript);
    const h = {
        window, document, requests,
        lane: (key) => document.querySelector(`[data-lane][data-lane-key="${key}"]`),
        card: (id) => document.querySelector(`[data-card][data-item-id="${id}"]`),
        ids: (key) => [...h.lane(key).querySelectorAll("[data-card]")].map((node) => node.dataset.itemId),
        toasts: () => [...document.querySelectorAll(".board-toast")].map((node) => node.textContent),
        fire(node, type) { node.dispatchEvent(new window.Event(type, {bubbles: true, cancelable: true})); },
        async dropOn(cardId, laneKey) {
            h.fire(h.card(cardId), "dragstart");
            h.fire(h.lane(laneKey).querySelector("[data-lane-body]"), "drop");
            await h.tick();
        },
        tick: () => new Promise((resolve) => window.setTimeout(resolve, 8)),
    };
    return h;
}

const ok = (message) => response(200, {success: true, message: message || "Alteração salva.", updated_at: "2026-10-03T11:00:00+00:00"});

test("sem endereço de gravação (sem o campo do agrupamento) o adaptador não liga o núcleo", (t) => {
    const h = setup(t, {moveUrl: "", handler: () => ok()});
    assert.equal(h.document.querySelector("[data-kanban]").lpsKanbanCore, undefined);
});

test("mover grava no endereço do cartão com o valor da raia e a versão que a tela tinha", async (t) => {
    const h = setup(t, {handler: (url) => (url.includes("fragmento") ? response(200, fixtures.stage) : ok())});
    await h.dropOn(1, 11);
    const [post] = h.requests;
    assert.equal(post.url, "/quadros/dominio/3/campos/9/itens/1/valor/");
    assert.equal(post.options.method, "POST");
    assert.equal(post.options.credentials, "same-origin");
    assert.deepEqual(post.body, {value: "11", updated_at: "2026-10-03T10:00:00+00:00"});
    assert.equal(post.options.headers["Content-Type"], "application/json");
    assert.equal(post.options.headers["X-Requested-With"], "XMLHttpRequest");
});

test("o token CSRF vem do cookie certo mesmo quando não é o primeiro", async (t) => {
    const h = setup(t, {handler: () => ok()});
    await h.dropOn(1, 11);
    assert.equal(h.requests[0].options.headers["X-CSRFToken"], "tok+1");
});

test("sem cookie, o token vem do campo do formulário", async (t) => {
    const h = setup(t, {cookie: false, handler: () => ok()});
    const field = h.document.createElement("input");
    field.type = "hidden";
    field.name = "csrfmiddlewaretoken";
    field.value = "do-campo";
    h.document.body.appendChild(field);
    await h.dropOn(1, 11);
    assert.equal(h.requests[0].options.headers["X-CSRFToken"], "do-campo");
});

test("a raia em branco grava vazio (limpa a etapa), não a palavra 'empty'", async (t) => {
    const h = setup(t, {handler: () => ok()});
    await h.dropOn(1, "empty");
    assert.deepEqual(h.requests[0].body.value, "");
});

test("depois de gravar, pede as raias à própria página com o mesmo recorte e troca o conteúdo", async (t) => {
    const server = fixtures.stage.replace(/<article class="kanban-card" data-card data-item-id="2"[\s\S]*?<\/article>/, "");
    assert.notEqual(server, fixtures.stage);
    const h = setup(t, {handler: (url) => (url.includes("fragmento") ? response(200, server) : ok())});
    await h.dropOn(1, 11);
    await h.tick();
    assert.equal(h.requests.length, 2);
    const get = h.requests[1];
    assert.deepEqual([get.url.split("?")[0], Object.fromEntries(new URLSearchParams(get.url.split("?")[1]))],
        ["/demandas/kanban/", {tab: "todas", q: "obra", fragmento: "raias"}]);
    assert.equal(get.options.credentials, "same-origin");
    assert.equal(get.options.headers["X-Requested-With"], "XMLHttpRequest");
    assert.equal(get.options.method, undefined, "é um GET");
    assert.equal(h.card(2), null, "o que o servidor mandou é o que vale");
    assert.deepEqual(h.toasts(), ["Demanda movida para “Levantamento”."]);
});

test("400: mostra a mensagem do servidor, devolve o cartão e não redesenha", async (t) => {
    const h = setup(t, {handler: () => response(400, {success: false, message: "A etapa escolhida não pertence ao setor atual."})});
    await h.dropOn(1, 11);
    assert.deepEqual(h.toasts(), ["A etapa escolhida não pertence ao setor atual."]);
    assert.deepEqual(h.ids(10), ["1", "2"]);
    assert.equal(h.requests.length, 1);
});

test("409: mostra a mensagem, devolve o cartão e traz as raias de novo", async (t) => {
    const h = setup(t, {handler: (url) => (url.includes("fragmento")
        ? response(200, fixtures.stage)
        : response(409, {success: false, message: "Esta informação foi alterada por outra pessoa."}))});
    await h.dropOn(1, 11);
    await h.tick();
    assert.deepEqual(h.toasts(), ["Esta informação foi alterada por outra pessoa."]);
    assert.equal(h.requests.length, 2);
    assert.ok(h.requests[1].url.includes("fragmento=raias"));
    assert.deepEqual(h.ids(10), ["1", "2"]);
});

test("403 (a página de permissão não é JSON): mensagem própria, sem redesenhar", async (t) => {
    const h = setup(t, {handler: () => response(403, "<h1>Acesso negado</h1>")});
    await h.dropOn(1, 11);
    assert.match(h.toasts()[0], /sem permissão ou sessão expirada/);
    assert.deepEqual(h.ids(10), ["1", "2"]);
    assert.equal(h.requests.length, 1);
});

test("404: a demanda sumiu; avisa e atualiza as raias", async (t) => {
    const h = setup(t, {handler: (url) => (url.includes("fragmento") ? response(200, fixtures.stage) : response(404, "<h1>404</h1>"))});
    await h.dropOn(1, 11);
    await h.tick();
    assert.deepEqual(h.toasts(), ["Esta demanda não está mais disponível."]);
    assert.equal(h.requests.length, 2);
});

test("erro do servidor (500): mensagem genérica e o cartão volta", async (t) => {
    const h = setup(t, {handler: () => response(500, "<h1>Erro</h1>")});
    await h.dropOn(1, 11);
    assert.deepEqual(h.toasts(), ["Não foi possível mover a demanda. Tente de novo."]);
    assert.deepEqual(h.ids(10), ["1", "2"]);
});

test("sem rede: mensagem de conexão e o cartão volta", async (t) => {
    const h = setup(t, {handler: () => Promise.reject(new TypeError("Failed to fetch"))});
    await h.dropOn(1, 11);
    assert.deepEqual(h.toasts(), ["Sem conexão com o servidor. Tente de novo."]);
    assert.deepEqual(h.ids(10), ["1", "2"]);
});

test("sessão vencida (a página de login volta com 200): NÃO é sucesso", async (t) => {
    const h = setup(t, {handler: () => response(200, "<html>Entrar</html>", {redirected: true})});
    await h.dropOn(1, 11);
    assert.deepEqual(h.toasts(), ["Sua sessão expirou. Entre de novo para continuar."]);
    assert.deepEqual(h.ids(10), ["1", "2"]);
    assert.equal(h.requests.length, 1, "e nada de redesenhar com a página de login");
});

test("200 sem success:true também não vale como sucesso", async (t) => {
    const h = setup(t, {handler: () => response(200, {message: "talvez"})});
    await h.dropOn(1, 11);
    assert.deepEqual(h.ids(10), ["1", "2"]);
    assert.equal(h.toasts()[0], "Não foi possível mover a demanda. Tente de novo.");
});

test("se as raias que voltam não são raias (uma página inteira), não são injetadas", async (t) => {
    const h = setup(t, {handler: (url) => (url.includes("fragmento") ? response(200, "<html><body>Entrar no sistema</body></html>") : ok())});
    await h.dropOn(1, 11);
    await h.tick();
    assert.equal(h.document.querySelectorAll("[data-lane]").length, 3, "as raias continuam as que estavam");
    assert.ok(h.toasts().includes("Não foi possível atualizar as raias. Recarregue a página."));
});

test("falha ao atualizar as raias (500) avisa sem apagar a tela", async (t) => {
    const h = setup(t, {handler: (url) => (url.includes("fragmento") ? response(500, "<h1>Erro</h1>") : ok())});
    await h.dropOn(1, 11);
    await h.tick();
    assert.equal(h.document.querySelectorAll("[data-lane]").length, 3);
    assert.ok(h.toasts().includes("Não foi possível atualizar as raias. Recarregue a página."));
});

test("agrupado por setor, mudar de setor pede confirmação com o título e o setor de destino", async (t) => {
    const h = setup(t, {html: fixtures.sector, groupBy: "sector", handler: (url) => (url.includes("fragmento") ? response(200, fixtures.sector) : ok())});
    h.fire(h.card(1), "dragstart");
    h.fire(h.lane(2).querySelector("[data-lane-body]"), "drop");
    await h.tick();
    const dialog = h.document.querySelector(".board-dialog");
    assert.ok(dialog, "a confirmação aparece antes de qualquer coisa");
    assert.equal(h.requests.length, 0);
    assert.equal(h.ids(1).includes("1"), true, "e o cartão ainda não saiu do lugar");
    assert.match(dialog.textContent, /“Demanda 1” vai para o setor Financeiro/);
    assert.match(dialog.textContent, /A etapa e o status dela voltam ao padrão desse setor/);

    [...dialog.querySelectorAll("button")].find((node) => node.textContent === "Cancelar").click();
    await h.tick();
    assert.equal(h.requests.length, 0);
    assert.equal(h.document.querySelector(".board-dialog"), null);

    h.fire(h.card(1), "dragstart");
    h.fire(h.lane(2).querySelector("[data-lane-body]"), "drop");
    await h.tick();
    [...h.document.querySelectorAll(".board-dialog button")].find((node) => node.textContent === "Mudar setor").click();
    await h.tick();
    assert.equal(h.requests[0].body.value, "2");
});

test("só o agrupamento por setor pede confirmação", async (t) => {
    for (const groupBy of ["stage", "condition", "owner", "urgency"]) {
        const h = setup(t, {groupBy, handler: () => ok()});
        await h.dropOn(1, 11);
        assert.equal(h.document.querySelector(".board-dialog"), null, groupBy);
        assert.equal(h.requests.length >= 1, true, groupBy);
    }
});

test("na raia de setor em branco ninguém solta (o setor é obrigatório)", (t) => {
    const h = setup(t, {html: fixtures.sector, groupBy: "sector", handler: () => ok()});
    assert.equal(h.lane("empty").hasAttribute("data-lane-closed"), true);
    h.fire(h.card(1), "dragstart");
    const over = new h.window.Event("dragover", {bubbles: true, cancelable: true});
    h.lane("empty").querySelector("[data-lane-body]").dispatchEvent(over);
    assert.equal(over.defaultPrevented, false);
});
