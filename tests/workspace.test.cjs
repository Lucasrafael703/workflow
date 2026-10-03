/* Workspace de Demandas (static/js/workspace.js): a regra de interação da barra.
   Requires jsdom@26.1.0 in NODE_PATH. Run from workflow: node --test tests/workspace.test.cjs
   Set PYTHON to the project's Python if it is not in .venv.

   O HTML vem do template Django real (workspace/_filter_bar.html + _view_tabs.html) com um contexto `ws` montado à mão,
   sem banco. Regra testada, em uma frase: controles simples aplicam ao escolher; o painel "Filtros" é um rascunho com
   um único "Aplicar filtros" (Esc/clicar fora descarta); a busca só aplica com Enter. */
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync, existsSync} = require("node:fs");
const {execFileSync} = require("node:child_process");
const path = require("node:path");
const {JSDOM} = require("jsdom");

const root = path.resolve(__dirname, "..");
const localPython = path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const python = process.env.PYTHON || (existsSync(localPython) ? localPython : "python");

const html = execFileSync(python, ["-c", `
import os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from types import SimpleNamespace
from django.template.loader import render_to_string

def opts(*items):
    return [{'key': k, 'label': l, 'url': u, 'active': a} for k, l, u, a in items]

ws = {
    'view': 'lista', 'title': 'Demandas', 'subtitle': 'Acompanhe.', 'count': 3,
    'tabs': [
        {'key': 'lista', 'label': 'Lista', 'icon': 'menu', 'url': '/demandas/?tab=todas', 'active': True},
        {'key': 'kanban', 'label': 'Kanban', 'icon': 'kanban', 'url': '/demandas/kanban/?tab=todas', 'active': False},
        {'key': 'calendario', 'label': 'Calendário', 'icon': 'calendar', 'url': '/demandas/calendario/?tab=todas', 'active': False},
    ],
    'scope': {'options': opts(('minhas', 'Minhas', '/demandas/', False), ('todas', 'Todas', '/demandas/?tab=todas', True))},
    'show': {'options': opts(('abertas', 'Em aberto', '/demandas/?tab=todas', True), ('concluidas', 'Concluídas', '/demandas/?tab=todas&concluidas=1', False))},
    'group': {'options': opts(('', 'Sem agrupar', '/demandas/?tab=todas', True), ('stage', 'Etapa', '/demandas/?tab=todas&agrupar=stage', False))},
    'sort': {'options': opts(('prazo:asc', 'Prazo: mais próximo primeiro', '/demandas/?tab=todas', True), ('titulo:asc', 'Demanda (A–Z)', '/demandas/?tab=todas&ordem=titulo', False))},
    'search': {'value': '', 'hidden': [('tab', 'todas')]},
    'chips': [{'label': 'Setor', 'value': 'Comercial', 'url': '/demandas/?tab=todas'}],
    'clear_url': '/demandas/?tab=todas',
    'notices': [],
    'panel': {
        'sectors': [{'pk': 5, 'name': 'Comercial'}, {'pk': 6, 'name': 'Compras'}],
        'selected_sector': '5',
        'stage_groups': [
            {'sector_id': 5, 'sector_name': 'Comercial', 'items': [{'pk': 51, 'name': 'Proposta'}, {'pk': 52, 'name': 'Negociação'}]},
            {'sector_id': 6, 'sector_name': 'Compras', 'items': [{'pk': 61, 'name': 'Cotação'}]},
        ],
        'selected_stage': '51',
        'status_groups': [{'sector_id': 6, 'sector_name': 'Compras', 'items': [{'pk': 71, 'name': 'Aguardando'}]}],
        'selected_status': '',
        'people': [{'pk': 1, 'get_full_name': 'Ana Silva', 'get_username': 'ana'}],
        'selected_people': ['1'],
        'client': None, 'site': None,
        'deadlines': [('', 'Todos os prazos'), ('atrasadas', 'Atrasadas')], 'selected_deadline': '',
        'hidden': [('tab', 'todas'), ('q', 'obra')],
        'open': False, 'active_count': 1, 'clear_url': '/demandas/?tab=todas',
    },
}
context = {'ws': ws, 'request': SimpleNamespace(path='/demandas/'), 'can_configure': False}
body = render_to_string('workspace/_view_tabs.html', context) + render_to_string('workspace/_filter_bar.html', context)
print(json.dumps(body))
`], {cwd: root, encoding: "utf8"}).trim();

const markup = JSON.parse(html);
const script = readFileSync(path.join(root, "static/js/workspace.js"), "utf8");

function setup(t, {withScript = true, open = false} = {}) {
    const dom = new JSDOM(`<!doctype html><body><section class="ws" data-ws>${markup}</section></body>`,
        {url: "http://localhost/demandas/?tab=todas", runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => dom.window.close());
    const {window} = dom;
    const {document} = window;
    if (open) document.querySelector("[data-ws-panel]").hidden = false;
    // jsdom não navega: trocamos a função de navegação do script e impedimos o clique em links.
    const visited = [];
    if (withScript) {
        window.eval(script);
        window.LPSWorkspace.navigate = url => visited.push(url);
    }
    document.addEventListener("click", event => { if (event.target.closest("a[href]")) event.preventDefault(); });
    const $ = selector => document.querySelector(selector);
    const $$ = selector => Array.from(document.querySelectorAll(selector));
    const change = (node, value) => {
        if (value !== undefined) node.value = value;
        node.dispatchEvent(new window.Event("change", {bubbles: true}));
    };
    return {window, document, $, $$, visited, change};
}

test("a barra tem os controles na ordem do Workspace e o painel começa fechado", t => {
    const {$, $$} = setup(t);
    assert.deepEqual($$(".ws__tab").map(el => el.textContent.trim()), ["Lista", "Kanban", "Calendário"]);
    assert.equal($(".ws__tab.is-active").getAttribute("aria-current"), "page");
    assert.deepEqual($$(".ws-segment__label").map(el => el.textContent), ["Escopo", "Mostrar"]);
    assert.equal($("[data-ws-panel]").hidden, true);
    assert.equal($("[data-ws-panel-toggle]").getAttribute("aria-expanded"), "false");
    assert.match($("[data-ws-panel-toggle]").textContent, /Filtros\s*1/);
});

test("as abas levam a querystring inteira (o recorte não muda ao trocar de visão)", t => {
    const {$$} = setup(t);
    for (const link of $$(".ws__tab")) assert.match(link.getAttribute("href"), /tab=todas/);
});

test("Agrupar e Ordenar aplicam ao escolher (uma escolha, uma navegação)", t => {
    const {$$, change, visited} = setup(t);
    const [group, sort] = $$("select[data-ws-nav]");
    change(group, "/demandas/?tab=todas&agrupar=stage");
    change(sort, "/demandas/?tab=todas&ordem=titulo");
    assert.deepEqual(visited, ["/demandas/?tab=todas&agrupar=stage", "/demandas/?tab=todas&ordem=titulo"]);
    assert.ok($$("select[data-ws-nav]").length === 2);
});

test("a busca não tem tratador automático: digitar não envia, só o formulário (Enter) envia", t => {
    const {$, window, visited} = setup(t);
    let submitted = 0;
    $("[data-ws-search]").addEventListener("submit", event => { submitted += 1; event.preventDefault(); });
    const input = $("[data-ws-search] input[name=q]");
    input.value = "obra";
    input.dispatchEvent(new window.Event("input", {bubbles: true}));
    input.dispatchEvent(new window.Event("change", {bubbles: true}));
    assert.equal(submitted, 0);
    assert.deepEqual(visited, []);
    $("[data-ws-search]").dispatchEvent(new window.Event("submit", {bubbles: true, cancelable: true}));
    assert.equal(submitted, 1);
    assert.ok($("html").classList.contains("ws-loading"), "mostra o carregando");
});

test("os formulários reenviam o resto do estado como campos ocultos (nada se perde ao filtrar)", t => {
    const {$} = setup(t);
    assert.equal($("[data-ws-search] input[type=hidden][name=tab]").value, "todas");
    assert.equal($("[data-ws-panel] input[type=hidden][name=tab]").value, "todas");
    assert.equal($("[data-ws-panel] input[type=hidden][name=q]").value, "obra");
    assert.equal($("[data-ws-search] input[type=hidden][name=q]"), null, "a busca não duplica o próprio campo");
});

test("o painel abre e fecha pelo botão Filtros e devolve o foco", t => {
    const {$} = setup(t);
    const toggle = $("[data-ws-panel-toggle]");
    toggle.click();
    assert.equal($("[data-ws-panel]").hidden, false);
    assert.equal(toggle.getAttribute("aria-expanded"), "true");
    toggle.click();
    assert.equal($("[data-ws-panel]").hidden, true);
    assert.equal(toggle.getAttribute("aria-expanded"), "false");
});

test("o painel acumula várias escolhas SEM recarregar; só 'Aplicar filtros' envia (uma vez)", t => {
    const {$, $$, window, change, visited} = setup(t, {open: true});
    let submits = 0;
    $("[data-ws-panel]").addEventListener("submit", event => { submits += 1; event.preventDefault(); });
    change($("select[name=setor]"), "6");
    change($("select[name=prazo]"), "atrasadas");
    $("input[name=pessoa][value=\"1\"]").checked = false;
    change($("select[name=condicao]"), "71");
    assert.equal(submits, 0, "nenhuma escolha enviou");
    assert.deepEqual(visited, [], "nenhuma escolha navegou");
    assert.equal($("[data-ws-panel] button[type=submit]").textContent.trim(), "Aplicar filtros");
    $("[data-ws-panel]").dispatchEvent(new window.Event("submit", {bubbles: true, cancelable: true}));
    assert.equal(submits, 1, "um envio só");
    assert.ok($("html").classList.contains("ws-loading"));
});

test("Esc descarta o rascunho: o painel volta ao que está de fato aplicado", t => {
    const {$, $$, window, change} = setup(t, {open: true});
    change($("select[name=setor]"), "6");
    change($("select[name=prazo]"), "atrasadas");
    $("input[name=pessoa][value=\"1\"]").checked = false;
    $("[data-ws-panel]").dispatchEvent(new window.KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
    assert.equal($("[data-ws-panel]").hidden, true);
    $("[data-ws-panel-toggle]").click();
    assert.equal($("select[name=setor]").value, "5", "setor aplicado");
    assert.equal($("select[name=prazo]").value, "");
    assert.equal($("input[name=pessoa][value=\"1\"]").checked, true, "Ana continua marcada");
});

test("Esc fecha o painel de onde o foco estiver; com um seletor aberto o Esc é só do seletor", t => {
    const {$, document, window, change} = setup(t, {open: true});
    change($("select[name=prazo]"), "atrasadas");
    document.body.dispatchEvent(new window.KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
    assert.equal($("[data-ws-panel]").hidden, true, "foco fora do painel: fecha mesmo assim");
    assert.equal($("select[name=prazo]").value, "", "e descarta");
    $("[data-ws-panel-toggle]").click();
    $(".person-picker").classList.add("is-open");  // um popup de seletor aberto (person-picker.js)
    document.body.dispatchEvent(new window.KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
    assert.equal($("[data-ws-panel]").hidden, false, "o Esc ficou com o seletor");
});

test("clicar fora do painel também descarta; clicar dentro não", t => {
    const {$, document, window, change} = setup(t, {open: true});
    change($("select[name=prazo]"), "atrasadas");
    $("[data-ws-panel] .ws-panel__grid").dispatchEvent(new window.MouseEvent("click", {bubbles: true}));
    assert.equal($("[data-ws-panel]").hidden, false, "dentro: continua aberto");
    assert.equal($("select[name=prazo]").value, "atrasadas");
    document.body.dispatchEvent(new window.MouseEvent("click", {bubbles: true}));
    assert.equal($("[data-ws-panel]").hidden, true, "fora: fecha");
    $("[data-ws-panel-toggle]").click();
    assert.equal($("select[name=prazo]").value, "", "e descarta o rascunho");
});

test("Setor → Etapa e Status só oferecem as opções do setor escolhido e limpam a que deixou de valer", t => {
    const {$, $$, change} = setup(t, {open: true});
    const stages = () => $$("select[name=estagio] option").map(o => o.textContent.trim());
    assert.deepEqual(stages(), ["Todas as etapas", "Proposta", "Negociação"], "setor 5 já filtrado ao abrir");
    assert.equal($("select[name=estagio]").value, "51");
    change($("select[name=setor]"), "6");
    assert.deepEqual(stages(), ["Todas as etapas", "Cotação"]);
    assert.equal($("select[name=estagio]").value, "", "a etapa do setor anterior não vale mais");
    change($("select[name=setor]"), "");
    assert.deepEqual(stages(), ["Todas as etapas", "Proposta", "Negociação", "Cotação"], "sem setor: todas");
});

test("remover um chip e trocar escopo/mostrar são links (aplicam na hora) e ligam o carregando", t => {
    const {$, $$} = setup(t);
    const links = $$(".ws-chip a, .ws-segment a, .ws__tab");
    assert.ok(links.length >= 6);
    $(".ws-chip a").click();
    assert.ok($("html").classList.contains("ws-loading"));
});

test("voltar pelo botão do navegador não deixa o carregando ligado", t => {
    const {$, window} = setup(t);
    $(".ws-segment a").click();
    assert.ok($("html").classList.contains("ws-loading"));
    window.dispatchEvent(new window.Event("pageshow"));
    assert.ok(!$("html").classList.contains("ws-loading"));
});

test("o foco volta ao controle usado depois de aplicar (sessionStorage)", t => {
    const first = setup(t, {open: true});
    first.$("[data-ws-panel]").dispatchEvent(new first.window.Event("submit", {bubbles: true, cancelable: true}));
    assert.equal(first.window.sessionStorage.getItem("lps-ws-focus"), "panel-toggle");
    // "recarrega": mesma sessão, página nova
    const dom = new JSDOM(`<!doctype html><body><section class="ws" data-ws>${markup}</section></body>`,
        {url: "http://localhost/demandas/?tab=todas", runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => dom.window.close());
    dom.window.sessionStorage.setItem("lps-ws-focus", "search");
    dom.window.eval(script);
    assert.equal(dom.window.document.activeElement, dom.window.document.querySelector("[data-ws-search] input[type=search]"));
    assert.equal(dom.window.sessionStorage.getItem("lps-ws-focus"), null, "usa uma vez só");
});

test("sem JavaScript o painel fica fechado mas utilizável e os links continuam links", t => {
    const {$, $$} = setup(t, {withScript: false});
    assert.equal($("[data-ws-panel]").hidden, true);
    assert.ok($$("a.ws-segment__item").every(a => a.getAttribute("href")));
    assert.equal($("[data-ws-panel]").tagName, "FORM");
    assert.equal($("[data-ws-panel]").getAttribute("method"), "get");
});

test("não liga duas vezes a mesma barra", t => {
    const {$, window} = setup(t);
    window.LPSWorkspace.init($("[data-ws]"));
    window.LPSWorkspace.init($("[data-ws]"));
    $("[data-ws-panel-toggle]").click();
    assert.equal($("[data-ws-panel]").hidden, false, "um clique abre uma vez (não abre e fecha)");
});

test("no celular o painel de filtros nunca abre sozinho (folha inferior cobriria a tela)", t => {
    const dom = new JSDOM(`<!doctype html><body><section class="ws" data-ws>${markup}</section></body>`,
        {url: "http://localhost/demandas/?tab=todas&setor=5", runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => dom.window.close());
    dom.window.matchMedia = query => ({matches: /max-width: 760px/.test(query)});
    dom.window.document.querySelector("[data-ws-panel]").hidden = false;  // o servidor abriu (há filtro secundário)
    dom.window.eval(script);
    assert.equal(dom.window.document.querySelector("[data-ws-panel]").hidden, true);
    assert.equal(dom.window.document.querySelector("[data-ws-panel-toggle]").getAttribute("aria-expanded"), "false");
    dom.window.document.querySelector("[data-ws-panel-toggle]").click();
    assert.equal(dom.window.document.querySelector("[data-ws-panel]").hidden, false, "mas abre pelo botão");
});

test("abrir uma demanda guarda a rolagem do endereço e a mesma lista restaura uma vez ao voltar", t => {
    const html = `<!doctype html><body><section class="ws" data-ws>${markup}<div data-ws-content><a id="open" href="/demandas/12/?next=%2Fdemandas%2F">abrir</a><a id="other" href="/demandas/?tab=minhas">outra</a></div></section></body>`;
    const first = new JSDOM(html, {url: "http://localhost/demandas/?tab=todas&q=o", runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => first.window.close());
    first.window.eval(script);
    Object.defineProperty(first.window, "scrollY", {value: 420, configurable: true});
    first.window.document.addEventListener("click", event => event.preventDefault());
    first.window.document.querySelector("#other").click();
    assert.equal(first.window.sessionStorage.length, 0, "links que não abrem demanda não guardam nada");
    first.window.document.querySelector("#open").click();
    const key = "lps-ws-scroll:/demandas/?tab=todas&q=o";
    assert.equal(first.window.sessionStorage.getItem(key), "420");
    // "volta": a mesma lista, página nova na mesma sessão
    const second = new JSDOM(html, {url: "http://localhost/demandas/?tab=todas&q=o", runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => second.window.close());
    second.window.sessionStorage.setItem(key, "420");
    let scrolledTo = null;
    second.window.scrollTo = (x, y) => { scrolledTo = y; };
    second.window.eval(script);
    assert.equal(scrolledTo, 420);
    assert.equal(second.window.sessionStorage.getItem(key), null, "restaura uma vez só");
    // outra URL (outro filtro) não herda a rolagem
    const third = new JSDOM(html, {url: "http://localhost/demandas/?tab=todas&q=x", runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => third.window.close());
    third.window.sessionStorage.setItem(key, "420");
    let moved = false;
    third.window.scrollTo = () => { moved = true; };
    third.window.eval(script);
    assert.equal(moved, false);
});
