/* Popup "Já realizei este trabalho" (static/js/retroactive-work.js).
   Requires jsdom@26.1.0 in NODE_PATH; no browser or production dependency.
   Run from workflow: node --test tests/retroactive-work.test.cjs
   Set PYTHON to the project's Python if it is not in .venv.

   O HTML vem do template Django real (activities/task_retroactive_form.html) com
   o formulário real (RetroactiveWorkForm), sem banco. Só o bloco `content` é
   usado, porque é ele que o LPSModal injeta na tela. "Hoje" é fixo no HTML
   (data-today), então o teste não depende do relógio. */
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
import os, re, json, datetime
from types import SimpleNamespace as NS
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.template import Context, Template
from activities.forms import RetroactiveWorkForm

source = open(os.path.join('templates', 'activities', 'task_retroactive_form.html'), encoding='utf-8').read()
body = re.search(r'{% block content %}(.*){% endblock %}\\s*$', source, re.S).group(1)
context = Context({
    'task': NS(pk=7, title='Entrevista com Jovem Aprendizes'),
    'form': RetroactiveWorkForm(),
    'justify_days': 7,
    'today': datetime.date(2026, 9, 30),
    'csrf_token': 'test-csrf-token',
})
print(json.dumps(Template(body).render(context)))
`], {cwd: root, encoding: "utf8"}).trim();

const fixture = JSON.parse(html);
const script = readFileSync(path.join(root, "static/js/retroactive-work.js"), "utf8");

function setup(t) {
    const dom = new JSDOM("<!doctype html><body>" + fixture + "</body>", {url: "http://localhost/tarefas/7/ja-realizei/", runScripts: "outside-only"});
    t.after(() => dom.window.close());
    const {window} = dom;
    window.eval(script);
    const $ = selector => window.document.querySelector(selector);
    const setDate = value => {
        $("[name=date]").value = value;
        $("[name=date]").dispatchEvent(new window.Event("input", {bubbles: true}));
    };
    const chooseReason = value => {
        const radio = $(`input[name=reason][value="${value}"]`);
        radio.checked = true;
        radio.dispatchEvent(new window.Event("change", {bubbles: true}));
    };
    return {window, $, setDate, chooseReason};
}

test("abre sem aviso e sem comentário, com 'Esqueci de iniciar' e a data de hoje", t => {
    const {$} = setup(t);
    assert.equal($("input[name=reason]:checked").value, "ESQUECI_INICIAR");
    assert.match($("[name=date]").value, /^\d{4}-\d{2}-\d{2}$/, "a data já vem preenchida (hoje)");
    assert.equal($("[data-past-day-warning]").hidden, true);
    assert.equal($("[data-note-row]").hidden, true);
    assert.equal($("[data-note-required]").hidden, true);
});

test("o motivo 'Outro' mostra o comentário como obrigatório", t => {
    const {$, chooseReason} = setup(t);
    chooseReason("OUTRO");
    assert.equal($("[data-note-row]").hidden, false);
    assert.equal($("[data-note-required]").hidden, false);
    chooseReason("FORA_DA_LPS");
    assert.equal($("[data-note-row]").hidden, true);
    chooseReason("AJUSTE_PERIODO");
    assert.equal($("[data-note-row]").hidden, true);
});

test("dia anterior avisa que ficará destacado, mas não pede comentário", t => {
    const {$, setDate} = setup(t);
    setDate("2026-09-29");
    assert.equal($("[data-past-day-warning]").hidden, false);
    assert.equal($("[data-note-row]").hidden, true);
    setDate("2026-09-30");
    assert.equal($("[data-past-day-warning]").hidden, true);
});

test("sete dias atrás ainda não pede comentário; oito dias atrás pede", t => {
    const {$, setDate} = setup(t);
    setDate("2026-09-23");  // 7 dias antes de 30/09
    assert.equal($("[data-past-day-warning]").hidden, false);
    assert.equal($("[data-note-row]").hidden, true);
    setDate("2026-09-22");  // 8 dias
    assert.equal($("[data-note-row]").hidden, false);
    assert.equal($("[data-note-required]").hidden, false);
    setDate("2026-09-30");
    assert.equal($("[data-note-row]").hidden, true);
});

test("o comentário continua visível enquanto o motivo for 'Outro', mesmo com a data de hoje", t => {
    const {$, setDate, chooseReason} = setup(t);
    chooseReason("OUTRO");
    setDate("2026-09-22");
    setDate("2026-09-30");
    assert.equal($("[data-note-row]").hidden, false);
});

test("data apagada não quebra nem mostra aviso", t => {
    const {$, setDate} = setup(t);
    setDate("");
    assert.equal($("[data-past-day-warning]").hidden, true);
    assert.equal($("[data-note-row]").hidden, true);
});

test("registra-se em LPSWidgets e não prepara o mesmo formulário duas vezes", t => {
    const {window, $, chooseReason} = setup(t);
    assert.ok(Array.isArray(window.LPSWidgets) && window.LPSWidgets.length === 1);
    window.LPSWidgets[0](window.document);
    window.LPSWidgets[0](window.document);
    chooseReason("OUTRO");
    assert.equal($("[data-note-row]").hidden, false);
    assert.equal($("[data-retroactive-form]").getAttribute("data-retro-ready"), "1");
});

test("sem JavaScript o formulário já traz todos os campos, o comentário e o envio", () => {
    const dom = new JSDOM("<!doctype html><body>" + fixture + "</body>");
    const {document} = dom.window;
    for (const name of ["date", "start_time", "end_time", "note"]) {
        assert.ok(document.querySelector(`[name=${name}]`), name);
    }
    assert.equal(document.querySelectorAll("input[name=reason]").length, 4);
    assert.ok(document.querySelector("form[method=post] button[type=submit]"));
    assert.match(document.querySelector("form button[type=submit]").textContent, /Registrar e concluir/);
    dom.window.close();
});
