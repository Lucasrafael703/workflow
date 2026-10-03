/* Nova / Editar demanda em quatro etapas — a mesma janela nos dois casos (static/js/activity-steps.js).
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
from activities.models import Activity

source = open(os.path.join('templates', 'activities', 'activity_form.html'), encoding='utf-8').read()
body = re.search(r'{% block content %}(.*){% endblock %}\\s*$', source, re.S).group(1)
form = ActivityEditorForm(organization=None, can_change_owner=True)
context = Context({
    'form': form, 'steps': form.steps, 'initial_step': 1, 'editor_title': 'Nova demanda',
    'editor_subtitle': 'Preencha as informações para criar uma nova demanda.', 'submit_label': 'Criar demanda',
    'cancel_url': '/demandas/', 'return_url': '/demandas/', 'draft': None, 'activity': None, 'attachments': [],
    'csrf_token': 'test-csrf-token',
})
# Editar: a MESMA janela, com o quadro que a demanda tem hoje (em branco, 3 tarefas); o banco fica fora do teste.
from unittest import mock
from boards.models import Board
from boards.demand_services import BoardInstantiationService
instance = Activity(pk=9, status='ABERTA')
instance.task_board = Board(pk=5, name='Quadro da demanda', kind='DEMAND')
with mock.patch.object(BoardInstantiationService, 'item_count', staticmethod(lambda board: 3)):
    edit_form = ActivityEditorForm(organization=None, can_change_owner=True, instance=instance)
edit_context = Context({**context.flatten(), 'form': edit_form, 'steps': edit_form.steps, 'editing': True, 'initial_step': 2,
    'editor_title': 'Editar demanda', 'submit_label': 'Salvar alterações'})
print(json.dumps([Template(body).render(context), Template(body).render(edit_context)]))
`], {cwd: root, encoding: "utf8"}).trim();

// [janela de criar, janela de editar]: a edição abre pela lista de Demandas, direto na etapa 2.
const [fixture, editFixture] = JSON.parse(html);
const script = readFileSync(path.join(root, "static/js/activity-steps.js"), "utf8");
const flush = () => new Promise(resolve => setImmediate(resolve));

function setup(t, {initialStep, withScript = true, edit = false, board} = {}) {
    const dom = new JSDOM("<!doctype html><body>" + (edit ? editFixture : fixture) + "</body>", {url: "http://localhost/demandas/nova/", runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => dom.window.close());
    const {window} = dom;
    const {document} = window;
    const stepper = document.querySelector("[data-activity-stepper]");
    if (initialStep) stepper.setAttribute("data-initial-step", String(initialStep));
    // Quadro atual da demanda (só na edição): o servidor o descreve em atributos; o teste escolhe outro cenário.
    if (board) for (const [name, value] of Object.entries(board)) stepper.setAttribute(`data-board-${name}`, String(value));
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
    assert.deepEqual($$(".activity-step-label").map(el => el.textContent.trim()), ["Informações principais", "Cliente e obra", "Quadro de tarefas", "Descrição e arquivos"]);
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
    assert.match($("[data-field=title] .activity-error").textContent, /nome da demanda/);
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

test("na etapa 4 o botão final aparece e o Continuar some", t => {
    const {$, visiblePanels, indicator, next, fillRequired} = setup(t);
    fillRequired();
    next();
    next();
    next();
    assert.deepEqual(visiblePanels(), ["4"]);
    assert.equal($("[data-step-next]").hidden, true);
    assert.equal($("[data-step-submit]").hidden, false);
    assert.equal($("[data-step-prev]").disabled, false);
    assert.ok(indicator(1).classList.contains("is-complete"));
    assert.ok(indicator(2).classList.contains("is-complete"));
    assert.ok(indicator(3).classList.contains("is-complete"));
    assert.ok(indicator(4).classList.contains("is-active"));
    assert.match($("[data-step-submit]").textContent, /Criar demanda/);
});

test("voltar e avançar não apagam nada do que foi preenchido", t => {
    const {$, visiblePanels, next, prev, fillRequired} = setup(t);
    fillRequired();
    next();
    $("[name=external_requester]").value = "Maria Silva";
    $("[name=address]").value = "Rua das Flores, 100";
    next();
    next();
    $("[name=files_location]").value = "\\\\Servidor\\Comercial\\Projeto X";
    prev();
    prev();
    prev();
    assert.deepEqual(visiblePanels(), ["1"]);
    assert.equal($("[name=title]").value, "Material disponível na obra");
    assert.equal($("[name=owner]").value, "1");
    assert.equal($("[name=sector]").value, "2");
    next();
    next();
    next();
    assert.equal($("[name=external_requester]").value, "Maria Silva");
    assert.equal($("[name=address]").value, "Rua das Flores, 100");
    assert.equal($("[name=files_location]").value, "\\\\Servidor\\Comercial\\Projeto X");
});

test("todos os campos das quatro etapas seguem dentro do mesmo formulário", t => {
    const {$, $$} = setup(t);
    const form = $("form");
    for (const name of ["board_setup_mode", "board_template", "stage", "condition", "title", "owner", "sector", "requested_deadline_0", "requested_deadline_1", "urgency", "company", "client", "site", "cost_center", "external_requester", "address", "description", "files_location"]) {
        assert.ok(form.querySelector(`[name=${name}]`), name);
    }
    assert.equal($$("form").length, 1);
    assert.equal($$("input[type=file]").length, 0, "não há upload");
});

test("o envio nas três primeiras etapas vira 'continuar' e não chega ao LPSModal", t => {
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

    submit();  // etapa 3 (quadro): avança
    assert.equal(reached, 0);
    assert.deepEqual(visiblePanels(), ["4"]);

    submit();  // etapa 4: agora sim envia
    assert.equal(reached, 1);
});

test("na última etapa, se algo obrigatório ficou vazio, volta à etapa 1 em vez de enviar", t => {
    const {$, window, visiblePanels, next, fillRequired} = setup(t);
    let reached = 0;
    $("form").addEventListener("submit", event => { reached += 1; event.preventDefault(); });
    fillRequired();
    next();
    next();
    next();
    $("[name=sector]").value = "";  // limpado por fora da etapa 1
    $("form").dispatchEvent(new window.Event("submit", {bubbles: true, cancelable: true}));
    assert.equal(reached, 0);
    assert.deepEqual(visiblePanels(), ["1"]);
    assert.ok($("[data-field=sector]").classList.contains("has-error"));
});

test("Enter num campo de texto avança em vez de enviar", t => {
    const {$, window, visiblePanels, fillRequired, next} = setup(t);
    fillRequired();
    const press = target => target.dispatchEvent(new window.KeyboardEvent("keydown", {key: "Enter", bubbles: true, cancelable: true}));
    press($("[name=title]"));
    assert.deepEqual(visiblePanels(), ["2"]);
    press($("[name=external_requester]"));
    assert.deepEqual(visiblePanels(), ["3"]);
    next();
    assert.deepEqual(visiblePanels(), ["4"]);
    press($("[name=files_location]"));  // última etapa: Enter envia (comportamento do navegador)
    assert.deepEqual(visiblePanels(), ["4"]);
});

test("abre direto na etapa indicada pelo servidor", t => {
    const {visiblePanels, indicator} = setup(t, {initialStep: 2});
    assert.deepEqual(visiblePanels(), ["2"]);
    assert.ok(indicator(1).classList.contains("is-complete"));
    assert.ok(indicator(2).classList.contains("is-active"));
});

test("editar: o servidor abre a janela direto na etapa 2 (clique em Cliente / Obra)", t => {
    const {$, visiblePanels, indicator} = setup(t, {edit: true});
    assert.equal($("[data-activity-stepper]").getAttribute("data-initial-step"), "2");
    assert.deepEqual(visiblePanels(), ["2"]);
    assert.ok(indicator(1).classList.contains("is-complete"));
    assert.ok(indicator(2).classList.contains("is-active"));
});

test("editar e criar: os mesmos botões — Continuar em toda etapa e o final só na última", t => {
    for (const edit of [false, true]) {
        const {$, visiblePanels, indicator, next, prev, fillRequired} = setup(t, {edit, initialStep: 1});
        const mode = edit ? "editar" : "criar";
        assert.ok(!$("[data-activity-stepper]").hasAttribute("data-submit-anywhere"), mode);
        assert.ok($("[data-step-next]").classList.contains("activity-btn-primary"), mode);
        assert.equal($("[data-step-submit]").hidden, true, mode);
        fillRequired();
        for (const step of ["2", "3"]) {
            next();
            assert.deepEqual(visiblePanels(), [step], mode);
            assert.equal($("[data-step-submit]").hidden, true, `${mode}: etapa ${step} ainda não salva`);
            assert.equal($("[data-step-next]").hidden, false, mode);
        }
        next();
        assert.deepEqual(visiblePanels(), ["4"], mode);
        assert.equal($("[data-step-submit]").hidden, false, mode);
        assert.equal($("[data-step-next]").hidden, true, mode);
        assert.match($("[data-step-submit]").textContent, edit ? /Salvar alterações/ : /Criar demanda/);
        assert.ok(indicator(4).classList.contains("is-active"), mode);
        prev();
        assert.equal($("[data-step-submit]").hidden, true, `${mode}: voltar esconde o botão final`);
    }
});

test("editar tem as mesmas quatro etapas de criar", t => {
    const {$$} = setup(t, {edit: true});
    assert.deepEqual($$(".activity-step-label").map(el => el.textContent.trim()), ["Informações principais", "Cliente e obra", "Quadro de tarefas", "Descrição e arquivos"]);
    assert.equal($$("[data-step-panel]").length, 4);
});

test("editar: Enter num campo continua avançando em vez de enviar", t => {
    const {$, window, visiblePanels} = setup(t, {edit: true});
    const event = new window.KeyboardEvent("keydown", {key: "Enter", bubbles: true, cancelable: true});
    $("[name=external_requester]").dispatchEvent(event);
    assert.equal(event.defaultPrevented, true);
    assert.deepEqual(visiblePanels(), ["3"]);
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

test("sem JavaScript as quatro etapas aparecem empilhadas e o botão final está visível", t => {
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
   Integração com o LPSModal real (static/js/modal.js): abrir, preencher as quatro
   etapas, enviar e receber o que o servidor responde. `fetch` é simulado. */
const modalScript = readFileSync(path.join(root, "static/js/modal.js"), "utf8");

function modalSetup(t, answers) {
    const dom = new JSDOM("<!doctype html><body></body>", {url: "http://localhost/demandas/", runScripts: "outside-only", pretendToBeVisual: true});
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
    await ctx.window.LPSModal.open("/demandas/nova/", {onSuccess});
    ctx.$("[name=title]").value = "Material disponível na obra";
    ctx.$("[name=owner]").value = "1";
    ctx.$("[name=sector]").value = "2";
    ctx.$("[data-step-next]").click();
    ctx.$("[name=external_requester]").value = "Maria Silva";
    ctx.$("[data-step-next]").click();
    ctx.$("[data-step-next]").click();  // etapa 3: quadro em branco (padrão)
    ctx.$("[name=files_location]").value = "https://drive.example.com/pasta";
}

test("LPSModal: a demanda só é enviada no botão final, com as quatro etapas juntas", async t => {
    const ctx = modalSetup(t, [{html: fixture}, {json: {redirect_url: "/demandas/9/"}}]);
    let result = null;
    await openAndFill(ctx, value => { result = value; });
    assert.equal(ctx.calls.length, 1, "avançar de etapa não envia nada");
    assert.deepEqual(ctx.visiblePanels(), ["4"]);

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
    assert.deepEqual(result, {redirect_url: "/demandas/9/"});
    assert.equal(ctx.$(".activity-modal"), null, "a janela fecha ao concluir");
});

test("LPSModal editar: abre na etapa 2, segue até a última e salva as quatro etapas juntas", async t => {
    const ctx = modalSetup(t, [{html: editFixture}, {json: {redirect_url: "/demandas/9/"}}]);
    let result = null;
    await ctx.window.LPSModal.open("/demandas/9/editar/?passo=2&next=%2Fdemandas%2F", {onSuccess: value => { result = value; }});
    assert.deepEqual(ctx.visiblePanels(), ["2"]);
    ctx.$("[name=title]").value = "Material disponível na obra";
    ctx.$("[name=owner]").value = "1";
    ctx.$("[name=sector]").value = "2";
    ctx.$("[name=external_requester]").value = "Maria Silva";
    ctx.$("[name=files_location]").value = "https://drive.example.com/pasta";
    ctx.$("[data-step-next]").click();
    ctx.$("[data-step-next]").click();
    assert.deepEqual(ctx.visiblePanels(), ["4"]);
    assert.equal(ctx.calls.length, 1, "avançar não envia nada");
    ctx.$("[data-step-submit]").click();
    await flush();
    assert.equal(ctx.calls.length, 2);
    assert.equal(ctx.calls[1].url, "/demandas/9/editar/?passo=2&next=%2Fdemandas%2F", "o envio usa o mesmo endereço da abertura");
    const sent = ctx.calls[1].options.body;
    assert.equal(sent.get("title"), "Material disponível na obra");
    assert.equal(sent.get("external_requester"), "Maria Silva");
    assert.equal(sent.get("files_location"), "https://drive.example.com/pasta", "campos de etapas sem visita também vão");
    assert.deepEqual(result, {redirect_url: "/demandas/9/"});
    assert.equal(ctx.$(".activity-modal"), null);
});

test("LPSModal editar: salvar com obrigatório vazio volta à etapa 1 e não envia nada", async t => {
    const ctx = modalSetup(t, [{html: editFixture}]);
    await ctx.window.LPSModal.open("/demandas/9/editar/?passo=2", {});
    ctx.$("[data-step-next]").click();
    ctx.$("[data-step-next]").click();
    assert.deepEqual(ctx.visiblePanels(), ["4"]);
    ctx.$("[data-step-submit]").click();
    await flush();
    assert.equal(ctx.calls.length, 1, "nenhum POST");
    assert.deepEqual(ctx.visiblePanels(), ["1"]);
    assert.ok(ctx.$("[data-field=title]").classList.contains("has-error"));
});

test("LPSModal: Enter nas primeiras etapas não envia o formulário", async t => {
    const ctx = modalSetup(t, [{html: fixture}]);
    await ctx.window.LPSModal.open("/demandas/nova/", {});
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
    await ctx.window.LPSModal.open("/demandas/nova/", {});
    ctx.$("[name=title]").value = "x";
    ctx.$("[name=owner]").value = "1";
    ctx.$("[name=sector]").value = "2";
    ctx.$("[data-step-next]").click();
    assert.deepEqual(ctx.visiblePanels(), ["2"]);
    ctx.window.LPSModal.close();
    assert.equal(ctx.$(".activity-modal"), null);
    await ctx.window.LPSModal.open("/demandas/nova/", {});
    assert.deepEqual(ctx.visiblePanels(), ["1"]);
});


/* ---------------------------------------------------------------------------
   Passo 3 — Quadro de tarefas: o "Modelo de quadro" só existe em "Usar quadro existente". */
test("quadro: começar em branco é o padrão e o campo de modelo fica escondido e não obrigatório", t => {
    const {$} = setup(t);
    assert.equal($("[name=board_setup_mode]:checked").value, "BLANK");
    assert.equal($("[data-board-template-field]").hidden, true);
    assert.equal($("[data-board-template-field] [data-field=board_template]").hasAttribute("data-required"), false);
});

test("quadro: escolher 'Usar quadro existente' mostra o modelo e passa a exigi-lo antes de seguir", t => {
    const {$, window, visiblePanels, next, fillRequired} = setup(t);
    fillRequired();
    next();
    next();
    assert.deepEqual(visiblePanels(), ["3"]);
    const radio = $("[name=board_setup_mode][value=TEMPLATE]");
    radio.checked = true;
    radio.dispatchEvent(new window.Event("change", {bubbles: true}));
    assert.equal($("[data-board-template-field]").hidden, false);
    assert.ok($("[data-board-template-field] [data-field=board_template]").hasAttribute("data-required"));
    next();  // sem modelo: não avança e mostra o erro junto do campo
    assert.deepEqual(visiblePanels(), ["3"]);
    assert.match($("[data-field=board_template] .activity-error").textContent, /modelo de quadro/);
    // voltando para "em branco" o campo some e nada mais é exigido
    const blank = $("[name=board_setup_mode][value=BLANK]");
    blank.checked = true;
    blank.dispatchEvent(new window.Event("change", {bubbles: true}));
    assert.equal($("[data-board-template-field]").hidden, true);
    assert.equal($("[data-field=board_template] .activity-error"), null);
    next();
    assert.deepEqual(visiblePanels(), ["4"]);
});

test("etapa e status ficam no passo 1, independentes, e o quadro não aparece ali", t => {
    const {$} = setup(t);
    const panel1 = $('[data-step-panel="1"]');
    assert.ok(panel1.querySelector("[data-field=stage]"));
    assert.ok(panel1.querySelector("[data-field=condition]"));
    assert.equal(panel1.querySelector("[name=board_setup_mode]"), null);
});

test("editar: o passo do quadro existe, com o quadro atual marcado e o campo de modelo escondido", t => {
    const {$, $$} = setup(t, {edit: true});
    assert.equal($$("[data-step-panel]").length, 4);
    assert.equal($$("[name=board_setup_mode]").length, 2);
    assert.equal($("[name=board_setup_mode]:checked").value, "BLANK");
    assert.equal($("[data-board-template-field]").hidden, true);
});


/* ---------------------------------------------------------------------------
   Editar: trocar o quadro de tarefas exclui as tarefas do quadro atual, então o envio pede confirmação.
   O fixture de edição descreve o quadro atual como "em branco, 3 tarefas". */
function addTemplates(document, options = [["7", "Modelo A"], ["8", "Modelo B"]]) {
    const select = document.querySelector("[name=board_template]");
    for (const [value, label] of options) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        select.appendChild(option);
    }
}

function chooseBoard({window, $}, mode, template) {
    const radio = $(`input[name=board_setup_mode][value=${mode}]`);
    radio.checked = true;
    radio.dispatchEvent(new window.Event("change", {bubbles: true}));
    if (template !== undefined) {
        const select = $("[name=board_template]");
        select.value = template;
        select.dispatchEvent(new window.Event("change", {bubbles: true}));
    }
}

function editAtLastStep(t, options = {}) {
    const ctx = setup(t, {edit: true, initialStep: 3, ...options});
    addTemplates(ctx.document);
    ctx.fillRequired();
    ctx.next();
    assert.deepEqual(ctx.visiblePanels(), ["4"]);
    const sent = [];
    ctx.$("form").addEventListener("submit", event => { sent.push(event.submitter ? event.submitter.name : null); event.preventDefault(); });
    const submit = () => ctx.$("[data-step-submit]").click();
    const dialogOpen = () => ctx.$("[data-board-confirm]") && !ctx.$("[data-board-confirm]").hidden;
    return {...ctx, sent, submit, dialogOpen, flag: () => ctx.$("[name=confirm_board_replace]")};
}

test("editar: sem trocar o quadro, salvar não abre confirmação", t => {
    const ctx = editAtLastStep(t);
    ctx.submit();
    assert.equal(ctx.sent.length, 1);
    assert.equal(ctx.dialogOpen(), false);
    assert.equal(ctx.flag().checked, false);
});

test("editar: o aviso de exclusão só aparece quando a escolha difere do quadro atual", t => {
    const ctx = setup(t, {edit: true, initialStep: 3});
    addTemplates(ctx.document);
    const warning = ctx.$("[data-board-change-warning]");
    assert.equal(warning.hidden, true, "mesma escolha do quadro atual");
    chooseBoard(ctx, "TEMPLATE", "7");
    assert.equal(warning.hidden, false);
    chooseBoard(ctx, "BLANK");
    assert.equal(warning.hidden, true);
});

test("editar: escolher outro modelo abre o diálogo com a contagem e não envia", t => {
    const ctx = editAtLastStep(t);
    chooseBoard(ctx, "TEMPLATE", "7");
    ctx.submit();
    assert.equal(ctx.sent.length, 0, "nada foi enviado");
    assert.equal(ctx.dialogOpen(), true);
    assert.ok(ctx.$("[data-board-confirm] [role=alertdialog][aria-modal=true]"));
    assert.match(ctx.$("[data-board-confirm-message]").textContent, /As 3 tarefas do quadro atual serão excluídas definitivamente\. Esta ação não pode ser desfeita\./);
    assert.match(ctx.$("[data-board-confirm-target]").textContent, /Novo quadro: a partir do modelo Modelo A/);
    assert.equal(ctx.document.activeElement, ctx.$("[data-board-confirm-cancel]"), "o botão seguro é o padrão");
    assert.equal(ctx.flag().checked, false);
    assert.ok(ctx.$("form").hasAttribute("inert") && ctx.$(".activity-modal-header").hasAttribute("inert"), "o fundo fica inerte");
});

test("editar: o diálogo diz 'em branco' quando a escolha nova é começar em branco", t => {
    const ctx = editAtLastStep(t, {board: {mode: "TEMPLATE", template: "7"}});
    chooseBoard(ctx, "TEMPLATE", "7");  // mesma escolha do quadro atual: nada
    ctx.submit();
    assert.equal(ctx.sent.length, 1);
    assert.equal(ctx.dialogOpen(), false);
    chooseBoard(ctx, "BLANK");
    ctx.submit();
    assert.equal(ctx.sent.length, 1, "não enviou de novo");
    assert.equal(ctx.dialogOpen(), true);
    assert.match(ctx.$("[data-board-confirm-target]").textContent, /Novo quadro: em branco/);
});

test("editar: de um modelo para outro também confirma", t => {
    const ctx = editAtLastStep(t, {board: {mode: "TEMPLATE", template: "7"}});
    chooseBoard(ctx, "TEMPLATE", "8");
    ctx.submit();
    assert.equal(ctx.sent.length, 0);
    assert.equal(ctx.dialogOpen(), true);
    assert.match(ctx.$("[data-board-confirm-target]").textContent, /Modelo B/);
});

test("editar: o texto do diálogo acompanha o número de tarefas (singular, plural, nenhuma)", t => {
    for (const [items, pattern] of [[1, /^A tarefa do quadro atual será excluída definitivamente/], [12, /^As 12 tarefas do quadro atual/], [0, /^O quadro atual será substituído por um novo/]]) {
        const ctx = editAtLastStep(t, {board: {items}});
        chooseBoard(ctx, "TEMPLATE", "7");
        ctx.submit();
        assert.match(ctx.$("[data-board-confirm-message]").textContent, pattern, String(items));
    }
});

test("editar: Confirmar marca a confirmação e reenvia o formulário pelo botão final", t => {
    const ctx = editAtLastStep(t);
    chooseBoard(ctx, "TEMPLATE", "7");
    ctx.submit();
    ctx.$("[data-board-confirm-accept]").click();
    assert.equal(ctx.dialogOpen(), false);
    assert.equal(ctx.flag().checked, true);
    assert.equal(ctx.sent.length, 1, "reenviado uma única vez");
    assert.equal(ctx.sent[0], "acao", "o reenvio sai pelo botão final (acao=publicar)");
    assert.equal(ctx.$("form").closest("[inert]"), null);
});

test("editar: Cancelar fecha o diálogo, volta ao passo do quadro e não envia nada", t => {
    const ctx = editAtLastStep(t);
    chooseBoard(ctx, "TEMPLATE", "7");
    ctx.submit();
    ctx.$("[data-board-confirm-cancel]").click();
    assert.equal(ctx.dialogOpen(), false);
    assert.deepEqual(ctx.visiblePanels(), ["3"]);
    assert.equal(ctx.sent.length, 0);
    assert.equal(ctx.flag().checked, false);
    assert.equal(ctx.$("input[name=board_setup_mode]:checked").value, "TEMPLATE", "a escolha continua para a pessoa corrigir");
});

test("editar: Esc fecha só o diálogo e o foco fica preso nele", t => {
    const ctx = editAtLastStep(t);
    let escapes = 0;
    ctx.document.addEventListener("keydown", event => { if (event.key === "Escape") escapes += 1; });
    chooseBoard(ctx, "TEMPLATE", "7");
    ctx.submit();
    const key = (target, init) => {
        const event = new ctx.window.KeyboardEvent("keydown", {bubbles: true, cancelable: true, ...init});
        target.dispatchEvent(event);
        return event;
    };
    const cancel = ctx.$("[data-board-confirm-cancel]"), accept = ctx.$("[data-board-confirm-accept]");
    assert.equal(ctx.document.activeElement, cancel);
    key(cancel, {key: "Tab"});
    assert.equal(ctx.document.activeElement, accept);
    key(accept, {key: "Tab"});
    assert.equal(ctx.document.activeElement, cancel, "Tab no último volta ao primeiro");
    key(cancel, {key: "Tab", shiftKey: true});
    assert.equal(ctx.document.activeElement, accept, "Shift+Tab no primeiro vai ao último");
    key(accept, {key: "Escape"});
    assert.equal(escapes, 0, "o Esc não chega ao que fecharia a janela inteira");
    assert.equal(ctx.dialogOpen(), false);
    assert.equal(ctx.sent.length, 0);
    assert.deepEqual(ctx.visiblePanels(), ["3"]);
});

test("editar: clicar fora do cartão só cancela, nunca confirma", t => {
    const ctx = editAtLastStep(t);
    chooseBoard(ctx, "TEMPLATE", "7");
    ctx.submit();
    ctx.$(".activity-confirm__card").click();  // dentro do cartão: nada
    assert.equal(ctx.dialogOpen(), true);
    ctx.$("[data-board-confirm]").click();     // fundo
    assert.equal(ctx.dialogOpen(), false);
    assert.equal(ctx.flag().checked, false);
    assert.equal(ctx.sent.length, 0);
});

test("editar: mudar a escolha depois de confirmar zera a confirmação", t => {
    const ctx = editAtLastStep(t);
    chooseBoard(ctx, "TEMPLATE", "7");
    ctx.submit();
    ctx.$("[data-board-confirm-accept]").click();
    assert.equal(ctx.flag().checked, true);
    chooseBoard(ctx, "TEMPLATE", "8");
    assert.equal(ctx.flag().checked, false);
    ctx.submit();
    assert.equal(ctx.sent.length, 1, "o segundo envio pede confirmação de novo");
    assert.equal(ctx.dialogOpen(), true);
});

test("editar: se o servidor recusar depois de confirmar, a próxima tentativa pergunta de novo", async t => {
    const ctx = editAtLastStep(t);
    chooseBoard(ctx, "TEMPLATE", "7");
    ctx.submit();
    ctx.$("[data-board-confirm-accept]").click();
    assert.equal(ctx.flag().checked, true);
    const list = ctx.document.createElement("ul");
    list.className = "errorlist";
    list.innerHTML = "<li>O modelo de quadro não está disponível nesta organização.</li>";
    ctx.$("[data-field=board_template]").appendChild(list);
    await flush();
    assert.equal(ctx.flag().checked, false);
});

test("editar: texto vindo do servidor entra como texto, nunca como HTML", t => {
    const ctx = editAtLastStep(t);
    addTemplates(ctx.document, [["9", "<img src=x onerror=alert(1)>"]]);
    chooseBoard(ctx, "TEMPLATE", "9");
    ctx.submit();
    assert.equal(ctx.$("[data-board-confirm] img"), null);
    assert.match(ctx.$("[data-board-confirm-target]").textContent, /<img src=x onerror=alert\(1\)>/);
});

test("criar nunca mostra o diálogo, mesmo escolhendo um modelo", t => {
    const ctx = setup(t, {initialStep: 3});
    addTemplates(ctx.document);
    assert.equal(ctx.$("[data-board-confirm]"), null);
    assert.equal(ctx.$("[name=confirm_board_replace]"), null);
    ctx.fillRequired();
    chooseBoard(ctx, "TEMPLATE", "7");
    ctx.next();
    let reached = 0;
    ctx.$("form").addEventListener("submit", event => { reached += 1; event.preventDefault(); });
    ctx.$("[data-step-submit]").click();
    assert.equal(reached, 1);
});

test("a caixa 'Confirmo a troca' fica escondida com JavaScript e visível sem ele", t => {
    assert.equal(setup(t, {edit: true}).$("[data-board-confirm-fallback]").hidden, true);
    const plain = setup(t, {edit: true, withScript: false});
    assert.equal(plain.$("[data-board-confirm-fallback]").hidden, false);
    assert.equal(plain.$("[data-board-confirm]").hidden, true, "o diálogo só existe com JavaScript");
});

test("LPSModal editar: trocar o quadro abre o diálogo; Confirmar envia confirm_board_replace=1", async t => {
    const ctx = modalSetup(t, [{html: editFixture}, {json: {redirect_url: "/demandas/9/"}}]);
    let result = null;
    await ctx.window.LPSModal.open("/demandas/9/editar/?passo=2", {onSuccess: value => { result = value; }});
    addTemplates(ctx.window.document);
    ctx.$("[name=title]").value = "Material disponível na obra";
    ctx.$("[name=owner]").value = "1";
    ctx.$("[name=sector]").value = "2";
    chooseBoard(ctx, "TEMPLATE", "7");
    ctx.$("[data-step-next]").click();  // a janela abre na etapa 2 (clique em Cliente / Obra)
    ctx.$("[data-step-next]").click();
    ctx.$("[data-step-submit]").click();
    await flush();
    assert.equal(ctx.calls.length, 1, "o diálogo abre antes de qualquer envio");
    assert.equal(ctx.$("[data-board-confirm]").hidden, false);
    ctx.$("[data-board-confirm-accept]").click();
    await flush();
    assert.equal(ctx.calls.length, 2);
    const sent = ctx.calls[1].options.body;
    assert.equal(sent.get("confirm_board_replace"), "1");
    assert.equal(sent.get("board_setup_mode"), "TEMPLATE");
    assert.equal(sent.get("board_template"), "7");
    assert.equal(sent.get("acao"), "publicar");
    assert.deepEqual(result, {redirect_url: "/demandas/9/"});
    assert.equal(ctx.$(".activity-modal"), null);
});

test("LPSModal editar: Esc com o diálogo aberto fecha só o diálogo; a janela continua aberta", async t => {
    const ctx = modalSetup(t, [{html: editFixture}]);
    await ctx.window.LPSModal.open("/demandas/9/editar/?passo=2", {});
    addTemplates(ctx.window.document);
    ctx.$("[name=title]").value = "x";
    ctx.$("[name=owner]").value = "1";
    ctx.$("[name=sector]").value = "2";
    chooseBoard(ctx, "TEMPLATE", "7");
    ctx.$("[data-step-next]").click();
    ctx.$("[data-step-next]").click();
    ctx.$("[data-step-submit]").click();
    assert.equal(ctx.$("[data-board-confirm]").hidden, false);
    ctx.window.document.activeElement.dispatchEvent(new ctx.window.KeyboardEvent("keydown", {key: "Escape", bubbles: true, cancelable: true}));
    assert.equal(ctx.$("[data-board-confirm]").hidden, true);
    assert.ok(ctx.$(".activity-modal"), "a janela de edição não fechou");
    assert.equal(ctx.calls.length, 1, "nada foi enviado");
});
