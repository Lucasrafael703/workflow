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
const {JSDOM, VirtualConsole} = require("jsdom");

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
    return SimpleNamespace(pk=pk, title='Demanda %s' % pk, code='DEM-2026-%05d' % pk, sector_id=sector_id, status=status, can_move_kanban=True, work_cells=[],
                           inline={'title': True}, updated_at=datetime.datetime(2026, 10, 3, 10, 0, tzinfo=datetime.timezone.utc))

def group(key, label, items=(), **extra):
    return {'key': key, 'label': label, 'color': '#3B82F6', 'items': list(items), **extra}

def render(groups, group_by, **extra):
    kanban = build_demand_kanban(groups=groups, group_by=group_by, sectors_by_id={1: 'Orçamento', 2: 'Financeiro'}, show_field_names=False,
                                 can_create=True, create_url='/demandas/nova/', return_url='/demandas/kanban/', can_rename=True, **extra)
    return render_to_string('kanban/_lanes.html', {'kanban': kanban})

stage = render([group('empty', 'Sem estágio'), group(10, 'A fazer', [item(1), item(2)], sector_id=1), group(11, 'Levantamento', [item(4)], sector_id=1)], 'stage')
sector = render([group('empty', 'Sem setor'), group(1, 'Orçamento', [item(1)]), group(2, 'Financeiro', [item(2, sector_id=2)])], 'sector')
menu = render([group('empty', 'Sem estágio'), group(10, 'A fazer', [item(1)], sector_id=1), group(20, 'A fazer', [item(5, sector_id=2)], sector_id=2)], 'stage',
              can_manage=lambda kind, sector_id: sector_id == 1, config_url='/painel/etapas/')
print(json.dumps({'stage': stage, 'sector': sector, 'menu': menu}))
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

const CONFIG = {
    fields_url: "/quadros/dominio/visoes/5/cartoes/", settings_url: "/quadros/dominio/visoes/5/configuracao/",
    settings: {show_empty: true, show_field_names: false},
    fields: [{id: 21, name: "Responsável"}, {id: 22, name: "Setor"}, {id: 23, name: "Prioridade"}, {id: 24, name: "Prazo"}],
    selected: [23, 21], always: [20],
};

function setup(t, {html = fixtures.stage, groupBy = "stage", moveUrl = "/quadros/dominio/3/campos/9/itens/0/valor/", renameUrl = "/quadros/dominio/3/campos/7/itens/0/valor/", search = "?tab=todas&q=obra", handler, cookie = true, config = CONFIG} = {}) {
    const attrs = `data-kanban data-group-by="${groupBy}"${moveUrl ? ` data-move-url="${moveUrl}"` : ""}${renameUrl ? ` data-rename-url="${renameUrl}"` : ""}`;
    const navigations = [];
    const virtualConsole = new VirtualConsole();
    virtualConsole.on("jsdomError", (error) => { if (/navigation/.test(error.message)) navigations.push(error.message); });
    const dom = new JSDOM(`<!doctype html><body><div class="kanban-scroll" ${attrs}><div class="kanban-lanes" data-kanban-lanes>${html}</div></div><div data-board-toasts></div>${config ? `<script type="application/json" id="kanban-config">${JSON.stringify(config)}</script>` : ""}<button type="button" data-kanban-config>Configurar cartões</button></body>`,
        {url: `http://localhost/demandas/kanban/${search}`, runScripts: "outside-only", pretendToBeVisual: true, virtualConsole});
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
        window, document, requests, navigations,
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
        tick: () => new Promise((resolve) => setTimeout(resolve, 8)),  // o do Node: os testes trocam window.setTimeout
    };
    return h;
}

const ok = (message) => response(200, {success: true, message: message || "Alteração salva.", updated_at: "2026-10-03T11:00:00+00:00"});

test("sem endereço de gravação do agrupamento o núcleo liga mesmo assim (abrir/renomear), mas nenhum movimento é enviado", async (t) => {
    const h = setup(t, {moveUrl: "", handler: () => ok()});
    assert.ok(h.document.querySelector("[data-kanban]").lpsKanbanCore, "o núcleo está de pé");
    await h.dropOn(1, 11);
    assert.equal(h.requests.length, 0, "sem endereço não há para onde gravar");
    assert.deepEqual(h.ids(10), ["1", "2"], "o cartão volta");
    assert.deepEqual(h.toasts(), ["Esta tela não consegue gravar o agrupamento."]);
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

// -- renomear no lugar e o ⋯ ------------------------------------------------------------------------------

const enter = (h, node) => node.dispatchEvent(new h.window.KeyboardEvent("keydown", {key: "Enter", bubbles: true, cancelable: true}));

async function renameTo(h, id, text) {
    h.card(id).querySelector("[data-card-title]").click();
    const input = h.card(id).querySelector(".board-inline-input");
    input.value = text;
    enter(h, input);
    await h.tick();
}

test("renomear grava o título no endereço do campo Título, com a versão do cartão, e guarda a versão nova", async (t) => {
    const h = setup(t, {handler: (url) => (url.includes("fragmento") ? response(200, fixtures.stage) : response(200, {success: true, updated_at: "2026-10-03T12:00:00+00:00"}))});
    await renameTo(h, 1, "Proposta Aurora");
    const [post] = h.requests;
    assert.equal(post.url, "/quadros/dominio/3/campos/7/itens/1/valor/");
    assert.deepEqual(post.body, {value: "Proposta Aurora", updated_at: "2026-10-03T10:00:00+00:00"});
    assert.equal(post.options.headers["X-CSRFToken"], "tok+1");
    assert.equal(h.card(1).querySelector("[data-card-title]").textContent, "Proposta Aurora");
    assert.equal(h.card(1).getAttribute("data-updated-at"), "2026-10-03T12:00:00+00:00", "o próximo movimento leva a versão que o servidor devolveu");
    assert.equal(h.requests.length, 1, "renomear não redesenha as raias");
});

test("renomear: o servidor recusa (400) e o título antigo volta com a mensagem dele", async (t) => {
    const h = setup(t, {handler: () => response(400, {success: false, message: "Informe o título da demanda."})});
    await renameTo(h, 1, "x");
    assert.equal(h.card(1).querySelector("[data-card-title]").textContent, "Demanda 1");
    assert.deepEqual(h.toasts(), ["Informe o título da demanda."]);
    assert.equal(h.requests.length, 1);
});

test("renomear: conflito de versão (409) desfaz e traz as raias do servidor", async (t) => {
    const server = fixtures.stage.replace("Demanda 1", "Demanda 1 (outra pessoa)");
    const h = setup(t, {handler: (url) => (url.includes("fragmento") ? response(200, server) : response(409, {success: false, message: "Esta informação foi alterada por outra pessoa."}))});
    await renameTo(h, 1, "Meu título");
    await h.tick();
    assert.deepEqual(h.toasts(), ["Esta informação foi alterada por outra pessoa."]);
    assert.equal(h.requests.length, 2);
    assert.ok(h.requests[1].url.includes("fragmento=raias"));
    assert.equal(h.card(1).querySelector("[data-card-title]").textContent, "Demanda 1 (outra pessoa)", "vale o que o servidor mandou");
});

test("renomear: 403 e rede têm mensagem própria dizendo 'renomear'", async (t) => {
    const forbidden = setup(t, {handler: () => response(403, "<h1>Acesso negado</h1>")});
    await renameTo(forbidden, 1, "x");
    assert.match(forbidden.toasts()[0], /Você não pode renomear esta demanda/);
    const offline = setup(t, {handler: () => Promise.reject(new TypeError("Failed to fetch"))});
    await renameTo(offline, 1, "x");
    assert.deepEqual(offline.toasts(), ["Sem conexão com o servidor. Tente de novo."]);
    const broken = setup(t, {handler: () => response(500, "<h1>Erro</h1>")});
    await renameTo(broken, 1, "x");
    assert.deepEqual(broken.toasts(), ["Não foi possível renomear a demanda. Tente de novo."]);
});

test("sem endereço do campo Título, o título não renomeia", (t) => {
    const h = setup(t, {renameUrl: "", handler: () => ok()});
    h.card(1).querySelector("[data-card-title]").click();
    assert.equal(h.card(1).querySelector(".board-inline-input"), null);
});

test("o ⋯ oferece Mover para, Abrir demanda e Renomear; abrir leva à ficha", (t) => {
    const h = setup(t, {handler: () => ok()});
    h.card(1).querySelector("[data-card-menu]").click();
    const pop = h.document.querySelector(".board-pop");
    assert.deepEqual([...pop.querySelectorAll(".board-menu__item")].map((n) => n.textContent), ["Sem estágio", "Levantamento", "Abrir demanda", "Renomear"]);
    assert.equal(h.document.querySelectorAll(".board-menu__sep").length, 1);
    [...pop.querySelectorAll(".board-menu__item")].find((n) => n.textContent === "Abrir demanda").click();
    assert.equal(h.navigations.length, 1, "pediu para navegar (o jsdom só avisa)");
});

test("o ⋮ da raia abre o que o servidor mandou e escolher leva à tela de etapas do setor", (t) => {
    const h = setup(t, {html: fixtures.menu, handler: () => ok()});
    const button = h.lane(10).querySelector("[data-lane-menu]");
    assert.ok(button, "a raia da etapa que a pessoa gere tem o ⋮");
    assert.equal(h.lane(20).querySelector("[data-lane-menu]"), null, "a do setor que ela não gere, não");
    assert.equal(h.lane("empty").querySelector("[data-lane-menu]"), null, "a raia 'sem valor' também não");
    button.click();
    const pop = h.document.querySelector(".board-pop");
    assert.equal(pop.getAttribute("aria-label"), "Opções da raia A fazer");
    assert.deepEqual([...pop.querySelectorAll(".board-menu__item")].map((n) => n.textContent), ["Editar as etapas do setor"]);
    assert.equal(pop.querySelector("svg use").getAttribute("href"), "#i-sliders");
    pop.querySelector(".board-menu__item").click();
    assert.equal(h.navigations.length, 1, "pediu para navegar para /painel/etapas/?domain=demandas&sector=1");
    assert.equal(h.requests.length, 0, "abrir o menu e escolher não grava nada");
});

test("o ⋮ da raia com dados estragados não quebra: sem itens válidos não abre nada", (t) => {
    const h = setup(t, {html: fixtures.menu, handler: () => ok()});
    const button = h.lane(10).querySelector("[data-lane-menu]");
    for (const value of ["não é json", "[]", '[{"label":"Sem endereço"}]', "null"]) {
        button.setAttribute("data-lane-menu-items", value);
        button.click();
        assert.equal(h.document.querySelector(".board-pop"), null, value);
    }
    assert.deepEqual(h.toasts(), []);
});

test("o '+ Adicionar' da raia é o link da janela Nova demanda com a etapa e o setor da raia", (t) => {
    const h = setup(t, {handler: () => ok()});
    const link = h.lane(10).querySelector("a[data-kanban-add]");
    assert.equal(link.getAttribute("href"), "/demandas/nova/?etapa=10&setor=1");
    assert.equal(h.lane("empty").querySelector("[data-kanban-add]"), null, "a raia 'sem valor' não recebe demanda nova");
    const click = new h.window.Event("click", {bubbles: true, cancelable: true});
    link.dispatchEvent(click);
    assert.equal(click.defaultPrevented, false, "o link segue sozinho");
});

test("o ⋯ → Renomear abre a edição do título", (t) => {
    const h = setup(t, {handler: () => ok()});
    h.card(1).querySelector("[data-card-menu]").click();
    [...h.document.querySelectorAll(".board-pop .board-menu__item")].find((n) => n.textContent === "Renomear").click();
    assert.equal(h.card(1).querySelector(".board-inline-input").value, "Demanda 1");
});

test("o cartão guarda o endereço da ficha e mostra o código como link (o título renomeia)", (t) => {
    const h = setup(t, {handler: () => ok()});
    assert.equal(h.card(1).getAttribute("data-detail-url"), "/demandas/1/?next=/demandas/kanban/");
    const code = h.card(1).querySelector("a.kanban-card__code");
    assert.equal(code.textContent, "DEM-2026-00001");
    assert.equal(code.getAttribute("href"), "/demandas/1/?next=/demandas/kanban/");
    assert.equal(h.card(1).querySelector("[data-card-title]").getAttribute("role"), "textbox");
    assert.equal(h.card(1).querySelector("a[data-card-title]"), null);
});

// -- Configurar cartões: o diálogo de Quadros com os dados desta visualização ---------------------------------------

const openConfig = (h) => h.document.querySelector("[data-kanban-config]").click();
const change = (h, node) => node.dispatchEvent(new h.window.Event("change", {bubbles: true}));
const plain = (value) => JSON.parse(JSON.stringify(value));

function captureTimers(h) {
    const timers = [];
    h.window.setTimeout = (fn, ms) => { timers.push({fn, ms}); return timers.length; };
    h.window.clearTimeout = (id) => { if (timers[id - 1]) timers[id - 1].fn = () => {}; };
    return timers;
}

test("o botão abre o diálogo de Quadros com as opções de Demandas e os campos do cartão primeiro", (t) => {
    const h = setup(t, {handler: () => ok()});
    openConfig(h);
    assert.equal(h.document.querySelector(".board-dialog h2").textContent, "Configurar cartões");
    assert.equal(h.document.querySelector(".board-dialog").classList.contains("board-dialog--wide"), true);
    const labels = [...h.document.querySelectorAll(".kanban-config__controls > .board-field")].map((n) => n.textContent.trim());
    assert.deepEqual(labels, ["Mostrar raias vazias", "Mostrar o nome de cada campo no cartão"], "só o que existe em Demandas: nada de soma nem de raia em branco");
    const boxes = [...h.document.querySelectorAll(".kanban-config__controls > .board-field input")];
    assert.deepEqual(boxes.map((b) => b.checked), [true, false]);
    assert.deepEqual([...h.document.querySelectorAll(".kanban-config__field label")].map((n) => n.textContent.trim()), ["Prioridade", "Responsável", "Setor", "Prazo"]);
    assert.ok(h.document.querySelector(".kanban-config__preview .kanban-card"));
});

test("as opções de exibição gravam no endereço da visualização e as raias vêm do servidor de novo", async (t) => {
    const server = fixtures.stage.replace("Demanda 4", "Demanda 4 (servidor)");
    const h = setup(t, {handler: (url) => (url.includes("fragmento") ? response(200, server) : response(200, {success: true}))});
    openConfig(h);
    const names = [...h.document.querySelectorAll(".kanban-config__controls > .board-field input")][1];
    names.checked = true;
    change(h, names);
    await h.tick();
    await h.tick();
    const [post, get] = h.requests;
    assert.equal(post.url, "/quadros/dominio/visoes/5/configuracao/");
    assert.deepEqual(post.body, {show_field_names: true});
    assert.equal(post.options.headers["X-CSRFToken"], "tok+1");
    assert.ok(get.url.includes("fragmento=raias"), "e as raias são pedidas de novo");
    assert.equal(h.document.querySelector('[data-item-id="4"] [data-card-title]').textContent, "Demanda 4 (servidor)");
    const empty = [...h.document.querySelectorAll(".kanban-config__controls > .board-field input")][0];
    empty.checked = false;
    change(h, empty);
    await h.tick();
    assert.deepEqual(h.requests[2].body, {show_empty: false});
});

test("a ordem dos campos grava UMA vez depois da pausa, sempre com o Título na frente", async (t) => {
    const h = setup(t, {handler: (url) => (url.includes("fragmento") ? response(200, fixtures.stage) : response(200, {success: true}))});
    const timers = captureTimers(h);
    openConfig(h);
    const boxes = () => [...h.document.querySelectorAll(".kanban-config__field input[type=checkbox]")];
    boxes()[3].checked = true;  // Prazo entra
    change(h, boxes()[3]);
    [...h.document.querySelectorAll(".kanban-config__field button")].find((n) => n.getAttribute("aria-label") === "Subir Prazo").click();
    assert.equal(h.requests.length, 0, "ainda esperando a pausa");
    timers.filter((timer) => timer.ms === 250).forEach((timer) => timer.fn());
    await h.tick();
    await h.tick();
    assert.equal(h.requests[0].url, "/quadros/dominio/visoes/5/cartoes/");
    assert.deepEqual(plain(h.requests[0].body), {field_ids: [20, 23, 21, 24]}, "Título (sempre), Prioridade, Responsável e o Prazo que entrou; o Setor não está marcado");
    // ordem na tela: Prioridade, Responsável, Setor, Prazo → o Prazo sobe para antes do Setor (desmarcado) → ficam os marcados, em ordem
    assert.ok(h.requests[1].url.includes("fragmento=raias"));
});

test("a configuração recusada (403) avisa com a mensagem própria e não redesenha", async (t) => {
    const h = setup(t, {handler: () => response(403, "<h1>Acesso negado</h1>")});
    openConfig(h);
    const names = [...h.document.querySelectorAll(".kanban-config__controls > .board-field input")][1];
    names.checked = true;
    change(h, names);
    await h.tick();
    assert.match(h.toasts()[0], /Você não pode configurar os cartões/);
    assert.equal(h.requests.length, 1);
});

test("a configuração recusada pelo servidor (400) mostra a mensagem dele", async (t) => {
    const h = setup(t, {handler: () => response(400, {success: false, message: "Campo de agrupamento inválido."})});
    openConfig(h);
    const names = [...h.document.querySelectorAll(".kanban-config__controls > .board-field input")][1];
    names.checked = true;
    change(h, names);
    await h.tick();
    assert.deepEqual(h.toasts(), ["Campo de agrupamento inválido."]);
});

test("sem os dados da configuração (quem não configura o quadro) o botão não faz nada", (t) => {
    const h = setup(t, {config: null, handler: () => ok()});
    openConfig(h);
    assert.equal(h.document.querySelector(".board-dialog"), null);
});

test("a pré-visualização do diálogo é o primeiro cartão sem edição e sem arrastar, e acompanha as raias redesenhadas", async (t) => {
    const h = setup(t, {handler: (url) => (url.includes("fragmento") ? response(200, fixtures.stage.replace("Demanda 1", "Demanda 1 (nova)")) : response(200, {success: true}))});
    openConfig(h);
    const preview = () => h.document.querySelector(".kanban-config__preview .kanban-card");
    assert.equal(preview().querySelector("[data-card-title]").textContent, "Demanda 1");
    assert.equal(preview().getAttribute("draggable"), null);
    assert.equal(preview().querySelector('[role="textbox"]'), null, "o título da prévia não renomeia");
    const names = [...h.document.querySelectorAll(".kanban-config__controls > .board-field input")][1];
    names.checked = true;
    change(h, names);
    await h.tick();
    await h.tick();
    assert.equal(preview().querySelector("[data-card-title]").textContent, "Demanda 1 (nova)");
});
