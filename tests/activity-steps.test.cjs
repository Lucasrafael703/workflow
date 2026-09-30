/* Nova / Editar atividade em três etapas (static/js/activity-steps.js).
   Requires jsdom@26.1.0 in NODE_PATH; no browser or production dependency.
   Run from workflow: node --test tests/activity-steps.test.cjs
   Set PYTHON to the project's Python if it is not in .venv.

   O HTML vem do template Django real (activities/activity_form.html) com o
   formulário real (ActivityEditorForm), sem banco. Só o bloco `content` é usado,
   porque é ele que o LPSModal injeta na tela. */
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
import os, re, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.template import Context, Template
from activities.forms import ActivityEditorForm

source = open(os.path.join('templates', 'activities', 'activity_form.html'), encoding='utf-8').read()
body = re.search(r'{% block content %}(.*){% endblock %}\\s*$', source, re.S).group(1)
form = ActivityEditorForm(organization=None, can_change_owner=True)
context = Context({
    'form': form, 'steps': form.steps, 'initial_step': 1, 'editor_title': 'Nova atividade',
    'editor_subtitle': 'Preencha as informações para criar uma nova atividade.', 'submit_label': 'Criar atividade',
    'cancel_url': '/atividades/', 'return_url': '/atividades/', 'draft': None, 'activity': None, 'attachments': [],
    'csrf_token': 'test-csrf-token',
})
print(json.dumps(Template(body).render(context)))
`], {cwd: root, encoding: "utf8"}).trim();

const fixture = JSON.parse(html);
const script = readFileSync(path.join(root, "static/js/activity-steps.js"), "utf8");
const flush = () => new Promise(resolve => setImmediate(resolve));

function setup(t, {initialStep, withScript = true} = {}) {
    const dom = new JSDOM("<!doctype html><body>" + fixture + "</body>", {url: "http://localhost/atividades/nova/", runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => dom.window.close());
    const {window} = dom;
    const {document} = window;
    if (initialStep) document.querySelector("[data-activity-stepper]").setAttribute("data-initial-step", String(initialStep));
    if (withScript) window.eval(script);
    const $ = selector => document.querySelector(selector);
    const $$ = selector => Array.from(document.querySelectorAll(selector));
    const visiblePanels = () => $$("[data-step-panel]").filter(panel => !panel.hidden).map(panel => panel.getAttribute("data-step-panel"));
    const indicator = number => $(`[data-step-indicator="${number}"]`);
    const fillRequired = () => {
        $("[name=title]").value = "Material disponível na obra";
        $("[name=owner]").value = "1";
        $("[name=sector]").value = "2";
    };
    const next = () => $("[data-step-next]").click();
    const prev = () => $("[data-step-prev]").click();
    return {window, document, $, $$, visiblePanels, indicator, fillRequired, next, prev};
}

test("abre na etapa 1, com o indicador visível e Voltar desabilitado", t => {
    const {$, visiblePanels, indicator} = setup(t);
    assert.deepEqual(visiblePanels(), ["1"]);
    assert.equal($("[data-stepper]").hidden, false);
    assert.equal($("[data-step-prev]").hidden, false);
    assert.equal($("[data-step-prev]").disabled, true);
    assert.equal($("[data-step-next]").hidden, false);
    assert.equal($("[data-step-submit]").hidden, true);
    assert.ok(indicator(1).classList.contains("is-active"));
    assert.ok(!indicator(2).classList.contains("is-active"));
    assert.equal(indicator(1).querySelector(".activity-step-number").textContent, "1");
});

test("os nomes das etapas estão no indicador", t => {
    const {$$} = setup(t);
    assert.deepEqual($$(".activity-step-label").map(el => el.textContent.trim()), ["Informações principais", "Informações do cliente", "Descrição e arquivos"]);
});

test("continuar com os obrigatórios vazios fica na etapa 1 e mostra o erro junto do campo", t => {
    const {$, $$, visiblePanels, next} = setup(t);
    next();
    assert.deepEqual(visiblePanels(), ["1"]);
    const groups = $$("[data-required]");
    assert.deepEqual(groups.map(group => group.getAttribute("data-field")), ["title", "owner", "sector"]);
    for (const group of groups) {
        assert.ok(group.classList.contains("has-error"), group.getAttribute("data-field"));
        assert.ok(group.querySelector(".activity-error"), group.getAttribute("data-field"));
    }
    assert.match($("[data-field=title] .activity-error").textContent, /nome da atividade/);
    assert.match($("[data-field=sector] .activity-error").textContent, /setor/);
});

test("espaços em branco não contam como preenchido", t => {
    const {$, visiblePanels, next, fillRequired} = setup(t);
    fillRequired();
    $("[name=title]").value = "    ";
    next();
    assert.deepEqual(visiblePanels(), ["1"]);
    assert.ok($("[data-field=title]").classList.contains("has-error"));
});

test("o erro some assim que o campo é preenchido", t => {
    const {$, window, next} = setup(t);
    next();
    assert.ok($("[data-field=title]").classList.contains("has-error"));
    $("[name=title]").value = "Algo";
    $("[name=title]").dispatchEvent(new window.Event("input", {bubbles: true}));
    assert.ok(!$("[data-field=title]").classList.contains("has-error"));
    assert.equal($("[data-field=title] .activity-error"), null);
    assert.ok($("[data-field=owner]").classList.contains("has-error"), "os outros continuam marcados");
});

test("avança para a etapa 2 e marca a 1 como concluída com o ✓", t => {
    const {visiblePanels, indicator, next, fillRequired} = setup(t);
    fillRequired();
    next();
    assert.deepEqual(visiblePanels(), ["2"]);
    assert.ok(indicator(1).classList.contains("is-complete"));
    assert.equal(indicator(1).querySelector(".activity-step-number").textContent, "✓");
    assert.ok(indicator(2).classList.contains("is-active"));
    assert.ok(!indicator(3).classList.contains("is-complete"));
    assert.equal(indicator(3).querySelector(".activity-step-number").textContent, "3");
});

test("na etapa 3 o botão final aparece e o Continuar some", t => {
    const {$, visiblePanels, indicator, next, fillRequired} = setup(t);
    fillRequired();
    next();
    next();
    assert.deepEqual(visiblePanels(), ["3"]);
    assert.equal($("[data-step-next]").hidden, true);
    assert.equal($("[data-step-submit]").hidden, false);
    assert.equal($("[data-step-prev]").disabled, false);
    assert.ok(indicator(1).classList.contains("is-complete"));
    assert.ok(indicator(2).classList.contains("is-complete"));
    assert.ok(indicator(3).classList.contains("is-active"));
    assert.match($("[data-step-submit]").textContent, /Criar atividade/);
});

test("voltar e avançar não apagam nada do que foi preenchido", t => {
    const {$, visiblePanels, next, prev, fillRequired} = setup(t);
    fillRequired();
    next();
    $("[name=external_requester]").value = "Maria Silva";
    $("[name=address]").value = "Rua das Flores, 100";
    next();
    $("[name=files_location]").value = "\\\\Servidor\\Comercial\\Projeto X";
    prev();
    prev();
    assert.deepEqual(visiblePanels(), ["1"]);
    assert.equal($("[name=title]").value, "Material disponível na obra");
    assert.equal($("[name=owner]").value, "1");
    assert.equal($("[name=sector]").value, "2");
    next();
    next();
    assert.equal($("[name=external_requester]").value, "Maria Silva");
    assert.equal($("[name=address]").value, "Rua das Flores, 100");
    assert.equal($("[name=files_location]").value, "\\\\Servidor\\Comercial\\Projeto X");
});

test("todos os campos das três etapas seguem dentro do mesmo formulário", t => {
    const {$, $$} = setup(t);
    const form = $("form");
    for (const name of ["title", "owner", "sector", "requested_deadline_0", "requested_deadline_1", "urgency", "company", "client", "site", "cost_center", "external_requester", "address", "description", "files_location"]) {
        assert.ok(form.querySelector(`[name=${name}]`), name);
    }
    assert.equal($$("form").length, 1);
    assert.equal($$("input[type=file]").length, 0, "não há upload");
});

test("o envio nas duas primeiras etapas vira 'continuar' e não chega ao LPSModal", t => {
    const {$, window, visiblePanels, fillRequired} = setup(t);
    let reached = 0;
    $("form").addEventListener("submit", event => { reached += 1; event.preventDefault(); });
    const submit = () => $("form").dispatchEvent(new window.Event("submit", {bubbles: true, cancelable: true}));

    submit();  // etapa 1, vazia: não avança e não envia
    assert.equal(reached, 0);
    assert.deepEqual(visiblePanels(), ["1"]);

    fillRequired();
    submit();  // etapa 1, preenchida: avança
    assert.equal(reached, 0);
    assert.deepEqual(visiblePanels(), ["2"]);

    submit();  // etapa 2: avança
    assert.equal(reached, 0);
    assert.deepEqual(visiblePanels(), ["3"]);

    submit();  // etapa 3: agora sim envia
    assert.equal(reached, 1);
});

test("na última etapa, se algo obrigatório ficou vazio, volta à etapa 1 em vez de enviar", t => {
    const {$, window, visiblePanels, next, fillRequired} = setup(t);
    let reached = 0;
    $("form").addEventListener("submit", event => { reached += 1; event.preventDefault(); });
    fillRequired();
    next();
    next();
    $("[name=sector]").value = "";  // limpado por fora da etapa 1
    $("form").dispatchEvent(new window.Event("submit", {bubbles: true, cancelable: true}));
    assert.equal(reached, 0);
    assert.deepEqual(visiblePanels(), ["1"]);
    assert.ok($("[data-field=sector]").classList.contains("has-error"));
});

test("Enter num campo de texto avança em vez de enviar", t => {
    const {$, window, visiblePanels, fillRequired} = setup(t);
    fillRequired();
    const press = target => target.dispatchEvent(new window.KeyboardEvent("keydown", {key: "Enter", bubbles: true, cancelable: true}));
    press($("[name=title]"));
    assert.deepEqual(visiblePanels(), ["2"]);
    press($("[name=external_requester]"));
    assert.deepEqual(visiblePanels(), ["3"]);
    press($("[name=files_location]"));  // última etapa: Enter envia (comportamento do navegador)
    assert.deepEqual(visiblePanels(), ["3"]);
});

test("abre direto na etapa indicada pelo servidor", t => {
    const {visiblePanels, indicator} = setup(t, {initialStep: 2});
    assert.deepEqual(visiblePanels(), ["2"]);
    assert.ok(indicator(1).classList.contains("is-complete"));
    assert.ok(indicator(2).classList.contains("is-active"));
});

test("erro devolvido pelo servidor em outra etapa abre essa etapa", async t => {
    const {$, document, visiblePanels, fillRequired, next} = setup(t);
    fillRequired();
    next();
    next();
    assert.deepEqual(visiblePanels(), ["3"]);
    // o LPSModal insere a lista de erros dentro do grupo do campo
    const list = document.createElement("ul");
    list.className = "errorlist";
    list.innerHTML = "<li>Esta obra pertence a outro cliente.</li>";
    $("[data-field=site]").appendChild(list);
    await flush();
    assert.deepEqual(visiblePanels(), ["2"]);
});

test("erro geral do servidor vai para a área de avisos do topo", async t => {
    const {$, document} = setup(t);
    const list = document.createElement("ul");
    list.className = "errorlist";
    list.innerHTML = "<li>Permissão alterada.</li>";
    $("form").appendChild(list);
    await flush();
    assert.equal(list.parentElement, $("[data-form-errors]"));
});

test("página devolvida com erro numa etapa abre nela", t => {
    const dom = new JSDOM("<!doctype html><body>" + fixture + "</body>", {url: "http://localhost/", runScripts: "outside-only"});
    t.after(() => dom.window.close());
    const {document} = dom.window;
    const list = document.createElement("ul");
    list.className = "errorlist";
    list.innerHTML = "<li>erro</li>";
    document.querySelector("[data-field=client]").appendChild(list);
    dom.window.eval(script);
    const visible = Array.from(document.querySelectorAll("[data-step-panel]")).filter(panel => !panel.hidden).map(panel => panel.getAttribute("data-step-panel"));
    assert.deepEqual(visible, ["2"]);
});

test("sem JavaScript as três etapas aparecem empilhadas e o botão final está visível", t => {
    const {$, $$} = setup(t, {withScript: false});
    assert.equal($$("[data-step-panel]").filter(panel => panel.hidden).length, 0);
    assert.equal($("[data-stepper]").hidden, true);
    assert.equal($("[data-step-next]").hidden, true);
    assert.equal($("[data-step-submit]").hidden, false);
});

test("registra-se em LPSWidgets e não prepara a mesma janela duas vezes", t => {
    const {window, $, visiblePanels, next, fillRequired} = setup(t);
    assert.ok(Array.isArray(window.LPSWidgets) && window.LPSWidgets.length === 1);
    window.LPSWidgets[0](window.document);
    window.LPSWidgets[0](window.document);
    fillRequired();
    next();
    assert.deepEqual(visiblePanels(), ["2"], "um único clique avança uma única etapa");
    assert.equal($("[data-activity-stepper]").getAttribute("data-steps-ready"), "1");
});

/* ---------------------------------------------------------------------------
   Integração com o LPSModal real (static/js/modal.js): abrir, preencher as três
   etapas, enviar e receber o que o servidor responde. `fetch` é simulado. */
const modalScript = readFileSync(path.join(root, "static/js/modal.js"), "utf8");

function modalSetup(t, answers) {
    const dom = new JSDOM("<!doctype html><body></body>", {url: "http://localhost/atividades/", runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => dom.window.close());
    const {window} = dom;
    const calls = [];
    window.fetch = async (url, options = {}) => {
        calls.push({url, options});
        const answer = answers.shift();
        return {
            ok: answer.ok !== false, redirected: false,
            headers: {get: () => (answer.json ? "application/json" : "text/html")},
            text: async () => answer.html || "",
            json: async () => answer.json,
        };
    };
    window.eval(modalScript);
    window.eval(script);
    const $ = selector => window.document.querySelector(selector);
    const $$ = selector => Array.from(window.document.querySelectorAll(selector));
    const visiblePanels = () => $$("[data-step-panel]").filter(panel => !panel.hidden).map(panel => panel.getAttribute("data-step-panel"));
    return {window, calls, $, $$, visiblePanels};
}

async function openAndFill(ctx, onSuccess) {
    await ctx.window.LPSModal.open("/atividades/nova/", {onSuccess});
    ctx.$("[name=title]").value = "Material disponível na obra";
    ctx.$("[name=owner]").value = "1";
    ctx.$("[name=sector]").value = "2";
    ctx.$("[data-step-next]").click();
    ctx.$("[name=external_requester]").value = "Maria Silva";
    ctx.$("[data-step-next]").click();
    ctx.$("[name=files_location]").value = "https://drive.example.com/pasta";
}

test("LPSModal: a atividade só é enviada no botão final, com as três etapas juntas", async t => {
    const ctx = modalSetup(t, [{html: fixture}, {json: {redirect_url: "/atividades/9/"}}]);
    let result = null;
    await openAndFill(ctx, value => { result = value; });
    assert.equal(ctx.calls.length, 1, "avançar de etapa não envia nada");
    assert.deepEqual(ctx.visiblePanels(), ["3"]);

    ctx.$("[data-step-submit]").click();
    await flush();
    assert.equal(ctx.calls.length, 2);
    const {options} = ctx.calls[1];
    assert.equal(options.method, "POST");
    assert.equal(options.headers["X-Requested-With"], "XMLHttpRequest");
    const sent = options.body;
    assert.equal(sent.get("title"), "Material disponível na obra");
    assert.equal(sent.get("owner"), "1");
    assert.equal(sent.get("sector"), "2");
    assert.equal(sent.get("external_requester"), "Maria Silva");
    assert.equal(sent.get("files_location"), "https://drive.example.com/pasta");
    assert.equal(sent.get("acao"), "publicar");
    assert.deepEqual(result, {redirect_url: "/atividades/9/"});
    assert.equal(ctx.$(".activity-modal"), null, "a janela fecha ao concluir");
});

test("LPSModal: Enter nas primeiras etapas não envia o formulário", async t => {
    const ctx = modalSetup(t, [{html: fixture}]);
    await ctx.window.LPSModal.open("/atividades/nova/", {});
    ctx.$("[name=title]").value = "x";
    ctx.$("[name=owner]").value = "1";
    ctx.$("[name=sector]").value = "2";
    ctx.$("[name=title]").dispatchEvent(new ctx.window.KeyboardEvent("keydown", {key: "Enter", bubbles: true, cancelable: true}));
    ctx.$("form").dispatchEvent(new ctx.window.Event("submit", {bubbles: true, cancelable: true}));
    await flush();
    assert.equal(ctx.calls.length, 1, "nenhum POST");
    assert.deepEqual(ctx.visiblePanels(), ["3"]);
});

test("LPSModal: erro de campo de outra etapa abre essa etapa e a janela continua aberta", async t => {
    const ctx = modalSetup(t, [
        {html: fixture},
        {ok: false, json: {errors: {site: ["Esta obra pertence a outro cliente. Escolha uma obra de quem foi selecionado."]}}},
    ]);
    await openAndFill(ctx, () => {});
    ctx.$("[data-step-submit]").click();
    await flush();
    await flush();
    assert.deepEqual(ctx.visiblePanels(), ["2"]);
    assert.match(ctx.$("[data-field=site] .errorlist").textContent, /pertence a outro cliente/);
    assert.ok(ctx.$(".activity-modal"), "a janela não fecha");
    assert.equal(ctx.$("[data-step-submit]").disabled, false, "o botão volta a funcionar");
    assert.equal(ctx.$("[name=external_requester]").value, "Maria Silva", "nada foi apagado");
});

test("LPSModal: erro de obrigatório devolvido pelo servidor abre a etapa 1", async t => {
    const ctx = modalSetup(t, [{html: fixture}, {ok: false, json: {errors: {sector: ["Escolha o setor responsável."]}}}]);
    await openAndFill(ctx, () => {});
    ctx.$("[data-step-submit]").click();
    await flush();
    await flush();
    assert.deepEqual(ctx.visiblePanels(), ["1"]);
    assert.match(ctx.$("[data-field=sector] .errorlist").textContent, /setor responsável/);
});

test("LPSModal: erro geral do servidor aparece na área de avisos, não debaixo do rodapé", async t => {
    const ctx = modalSetup(t, [{html: fixture}, {ok: false, json: {errors: {__all__: ["Permissão alterada."]}}}]);
    await openAndFill(ctx, () => {});
    ctx.$("[data-step-submit]").click();
    await flush();
    await flush();
    assert.match(ctx.$("[data-form-errors]").textContent, /Permissão alterada/);
    assert.equal(ctx.$("form > .errorlist"), null);
});

test("LPSModal: fechar e abrir de novo começa na etapa 1", async t => {
    const ctx = modalSetup(t, [{html: fixture}, {html: fixture}]);
    await ctx.window.LPSModal.open("/atividades/nova/", {});
    ctx.$("[name=title]").value = "x";
    ctx.$("[name=owner]").value = "1";
    ctx.$("[name=sector]").value = "2";
    ctx.$("[data-step-next]").click();
    assert.deepEqual(ctx.visiblePanels(), ["2"]);
    ctx.window.LPSModal.close();
    assert.equal(ctx.$(".activity-modal"), null);
    await ctx.window.LPSModal.open("/atividades/nova/", {});
    assert.deepEqual(ctx.visiblePanels(), ["1"]);
});
