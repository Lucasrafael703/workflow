/* Popup "Aplicar processo" (static/js/process-apply.js).
   Requires jsdom@26.1.0 in NODE_PATH; no browser or production dependency.
   Run from workflow: node --test tests/process-apply.test.cjs
   Set PYTHON to the project's Python if it is not in .venv.

   O HTML vem do template Django real (activities/activity_process_apply.html),
   renderizado com objetos de mentira — sem banco. Só o bloco `content` é usado,
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
from types import SimpleNamespace as NS
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.conf import settings
from django.template import Context, Template

def person(pk, name):
    return NS(pk=pk, get_full_name=lambda: name, get_username=lambda: name.lower())

ryan, vitor, ana = person(1, 'Ryan'), person(2, 'Vitor'), person(3, 'Ana')

def version(pk, name, number, n_steps, n_inputs):
    return NS(pk=pk, number=number, step_count=n_steps, input_count=n_inputs, criterion_count=2,
              output_description='Proposta pronta',
              process=NS(name=name, company=NS(name='Biasi Engenharia'), activity_type=None))

def step_row(pk, order, name, sector, default, sector_people, other_people, depends=True):
    step = NS(pk=pk, order=order, name=name, sector=NS(name=sector), depends_on_previous=depends)
    return {'step': step, 'field_name': 'responsavel_%d' % pk, 'selected': str(default.pk) if default else '',
            'has_default': bool(default), 'sector_people': sector_people, 'other_people': other_people, 'errors': []}

def input_row(pk, name, kind, widget, required):
    item = NS(pk=pk, name=name, input_type=kind, is_required=required, source='', help_text='',
              get_source_display=lambda: '', get_input_type_display=lambda: kind.title())
    return {'input': item, 'widget': widget, 'value_name': 'input_%d' % pk, 'received_name': 'input_received_%d' % pk,
            'value': '', 'received': False, 'errors': []}

panels = [
    {'version': version(10, 'Orçamento', 3, 3, 3),
     'steps': [
         step_row(101, 1, 'Levantamento', 'Comercial', ryan, [ryan], [vitor, ana], depends=False),
         step_row(102, 2, 'Cotação', 'Compras', None, [vitor], [ryan, ana]),
         step_row(103, 3, 'Revisão', 'Comercial', ana, [ryan], [vitor, ana]),
     ],
     'inputs': [
         input_row(201, 'Projetos', 'TEXTO', 'text', True),
         input_row(202, 'Prazo', 'DATA', 'date', False),
         input_row(203, 'Planta', 'ARQUIVO', 'confirm', True),
     ]},
    {'version': version(11, 'Manutenção', 1, 1, 1),
     'steps': [step_row(111, 1, 'Vistoria', 'Comercial', ryan, [ryan], [vitor])],
     'inputs': [input_row(211, 'Chamado', 'TEXTO', 'text', False)]},
]
source = open(os.path.join('templates', 'activities', 'activity_process_apply.html'), encoding='utf-8').read()
body = re.search(r'{% block content %}(.*){% endblock %}\\s*$', source, re.S).group(1)
context = Context({
    'activity': NS(pk=5, code='DEM-2026-00005', title='Obra', company=NS(name='Biasi Engenharia')),
    'panels': panels, 'no_company': False, 'csrf_token': 'test-csrf-token',
    'form': NS(process_version=NS(value=None, errors=[]), non_field_errors=[]),
})
print(json.dumps(Template(body).render(context)))
`], {cwd: root, encoding: "utf8"}).trim();

const fixture = JSON.parse(html);
const script = readFileSync(path.join(root, "static/js/process-apply.js"), "utf8");
const flush = () => new Promise(resolve => setImmediate(resolve));

function setup(t) {
    const dom = new JSDOM("<!doctype html><body>" + fixture + "</body>", {url: "http://localhost/demandas/5/processo/aplicar/", runScripts: "outside-only"});
    t.after(() => dom.window.close());
    const {window} = dom;
    window.eval(script);
    const $ = selector => window.document.querySelector(selector);
    const $$ = selector => Array.from(window.document.querySelectorAll(selector));
    const visiblePane = () => $$("[data-pane]").filter(pane => !pane.hidden).map(pane => pane.getAttribute("data-pane"));
    const next = () => $("[data-apply-next]").click();
    const back = () => $("[data-apply-back]").click();
    const choose = value => {
        const radio = $(`input[name=process_version][value="${value}"]`);
        radio.checked = true;
        radio.dispatchEvent(new window.Event("change", {bubbles: true}));
    };
    const message = () => $("[data-form-errors]").textContent.trim();
    const formKeys = () => Array.from(new window.FormData($("form")).keys());
    return {window, $, $$, visiblePane, next, back, choose, message, formKeys};
}

test("abre no passo 1, sem voltar e com Continuar", t => {
    const {visiblePane, $} = setup(t);
    assert.deepEqual(visiblePane(), ["1"]);
    assert.equal($("[data-apply-back]").hidden, true);
    assert.equal($("[data-apply-next]").hidden, false);
    assert.equal($("[data-apply-submit]").hidden, true);
    assert.equal($("[data-step-tab='1']").classList.contains("is-active"), true);
});

test("não avança sem escolher o processo", t => {
    const {visiblePane, next, message} = setup(t);
    next();
    assert.deepEqual(visiblePane(), ["1"]);
    assert.match(message(), /Escolha o processo/);
});

test("só os campos do processo escolhido ficam habilitados e são enviados", t => {
    const {choose, $$, formKeys} = setup(t);
    choose(10);
    const enabledSelects = $$("select").filter(select => !select.disabled).map(select => select.name);
    assert.deepEqual(enabledSelects, ["responsavel_101", "responsavel_102", "responsavel_103"]);
    const keys = formKeys();
    assert.ok(keys.includes("process_version"));
    assert.ok(keys.includes("input_201"));
    assert.ok(!keys.includes("responsavel_111"), "campos da outra versão não podem ser enviados");
    assert.ok(!keys.includes("input_211"));
    choose(11);
    assert.deepEqual($$("select").filter(select => !select.disabled).map(select => select.name), ["responsavel_111"]);
});

test("passo 2 preenche o responsável padrão e exige os demais", t => {
    const {choose, next, visiblePane, message, $, window} = setup(t);
    choose(10);
    next();
    assert.deepEqual(visiblePane(), ["2"]);
    assert.equal($("select[name=responsavel_101]").value, "1");  // padrão da etapa
    assert.equal($("select[name=responsavel_102]").value, "");   // sem padrão
    next();
    assert.deepEqual(visiblePane(), ["2"], "a etapa 2 ficou sem responsável");
    assert.match(message(), /2\. Cotação/);
    $("select[name=responsavel_102]").value = "2";
    next();
    assert.deepEqual(visiblePane(), ["3"]);
    assert.equal(message(), "");
    assert.ok(window.document.querySelector("[data-step-tab='2']").classList.contains("is-done"));
});

test("sugere primeiro as pessoas do setor da etapa", t => {
    const {choose, $$} = setup(t);
    choose(10);
    const groups = $$("select[name=responsavel_102] optgroup").map(group => group.label);
    assert.deepEqual(groups, ["Do setor Compras", "Outras pessoas"]);
    assert.deepEqual($$("select[name=responsavel_102] optgroup:first-of-type option").map(o => o.textContent.trim()), ["Vitor"]);
});

test("a confirmação resume processo, etapas, entradas e critérios", t => {
    const {choose, next, visiblePane, $, window} = setup(t);
    choose(10);
    next();
    $("select[name=responsavel_102]").value = "2";
    next();
    $("input[name=input_201]").value = "Projeto rev. B";
    next();
    assert.deepEqual(visiblePane(), ["4"]);
    const summary = $("[data-apply-summary]").textContent.replace(/\s+/g, " ");
    assert.match(summary, /Processo: Orçamento — versão 3/);
    assert.match(summary, /1\. Levantamento — Comercial — Ryan/);
    assert.match(summary, /2\. Cotação — Compras — Vitor/);
    assert.match(summary, /3\. Revisão — Comercial — Ana/);
    assert.match(summary, /Entradas: 1 informada · 2 aguardando/);
    assert.match(summary, /Faltam entradas obrigatórias \(Planta\)/);
    assert.match(summary, /Critérios de aceite: 2 serão criados/);
    assert.equal($("[data-apply-submit]").hidden, false);
    assert.equal($("[data-apply-next]").hidden, true);
    assert.ok(window.document.querySelector("[data-step-tab='4']").classList.contains("is-active"));
});

test("marcar 'Já recebi' em um input de arquivo conta como informado", t => {
    const {choose, next, $} = setup(t);
    choose(10);
    next();
    $("select[name=responsavel_102]").value = "2";
    next();
    $("input[name=input_received_203]").checked = true;
    next();
    const summary = $("[data-apply-summary]").textContent.replace(/\s+/g, " ");
    assert.match(summary, /Entradas: 1 informada · 2 aguardando/);
    assert.match(summary, /Faltam entradas obrigatórias \(Projetos\)/);
});

test("observação de um input de arquivo, sem 'Já recebi', não conta como informado", t => {
    const {choose, next, $} = setup(t);
    choose(10);
    next();
    $("select[name=responsavel_102]").value = "2";
    next();
    $("input[name=input_203]").value = "está na pasta da obra";  // só a observação
    next();
    const summary = $("[data-apply-summary]").textContent.replace(/\s+/g, " ");
    assert.match(summary, /Entradas: 0 informadas · 3 aguardando/);
    assert.match(summary, /Faltam entradas obrigatórias \(Projetos; Planta\)/);
});

test("voltar mantém o que foi preenchido", t => {
    const {choose, next, back, visiblePane, $} = setup(t);
    choose(10);
    next();
    $("select[name=responsavel_102]").value = "2";
    next();
    back();
    assert.deepEqual(visiblePane(), ["2"]);
    assert.equal($("select[name=responsavel_102]").value, "2");
    back();
    assert.deepEqual(visiblePane(), ["1"]);
    assert.equal($("[data-apply-back]").hidden, true);
});

test("trocar de processo troca as etapas do passo 2", t => {
    const {choose, next, $$} = setup(t);
    choose(10);
    next();
    choose(11);
    const visible = $$(".apply-pane[data-pane='2'] .apply-version").filter(block => !block.hidden);
    assert.equal(visible.length, 1);
    assert.equal(visible[0].getAttribute("data-version"), "11");
});

test("Enter num campo não envia o formulário antes do último passo", t => {
    const {choose, window, $, visiblePane} = setup(t);
    let submitted = false;
    $("form").addEventListener("submit", () => { submitted = true; });
    choose(10);
    const event = new window.KeyboardEvent("keydown", {key: "Enter", bubbles: true, cancelable: true});
    $("input[name=process_version]").dispatchEvent(event);
    assert.equal(event.defaultPrevented, true);
    assert.equal(submitted, false);
    assert.deepEqual(visiblePane(), ["2"]);
});

test("erro do servidor num campo volta para o passo dele", async t => {
    const {choose, next, visiblePane, $, window} = setup(t);
    choose(10);
    next();
    $("select[name=responsavel_102]").value = "2";
    next();
    next();
    assert.deepEqual(visiblePane(), ["4"]);
    const row = $("select[name=responsavel_102]").closest(".form-row");
    const list = window.document.createElement("ul");
    list.className = "errorlist";
    list.innerHTML = "<li>Escolha uma pessoa ativa da organização.</li>";
    row.appendChild(list);
    await flush();
    assert.deepEqual(visiblePane(), ["2"]);
});

test("erro do formulário como um todo sobe para o espaço reservado no topo", async t => {
    const {choose, next, $, window} = setup(t);
    choose(10);
    next();
    $("select[name=responsavel_102]").value = "2";
    next();
    next();
    const list = window.document.createElement("ul");
    list.className = "errorlist";
    list.innerHTML = "<li>Esta demanda já tem um processo aplicado.</li>";
    $(".modal__body").appendChild(list);  // onde o LPSModal anexa erros sem campo
    await flush();
    assert.match($("[data-form-errors]").textContent, /já tem um processo aplicado/);
    assert.equal($(".modal__body > .errorlist"), null);
});

test("sem processo elegível não há assistente para inicializar", t => {
    const dom = new JSDOM('<!doctype html><body><div class="modal" data-process-apply><form><div data-form-errors></div></form></div></body>',
        {url: "http://localhost/", runScripts: "outside-only"});
    t.after(() => dom.window.close());
    assert.doesNotThrow(() => dom.window.eval(script));
});
