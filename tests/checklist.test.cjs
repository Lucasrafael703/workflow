/* Requires jsdom@26.1.0 in NODE_PATH; no browser or production dependency.
   Run from workflow: node --test tests/checklist.test.cjs
   Set PYTHON to the project's Python if it is not in .venv. */
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
import os, json
from types import SimpleNamespace
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.template.loader import render_to_string
result = {}
for role in ('editor', 'executor', 'reader'):
    result[role] = render_to_string('activities/_task_checklist.html', {
        'task': SimpleNamespace(pk=7), 'csrf_token': 'test-csrf-token',
        'can_edit_task': role == 'editor', 'can_toggle_checklist': role != 'reader',
        'checklist_done': 0,
        'checklist_items': [SimpleNamespace(pk=1, text='Conferir valores', is_done=False)]
    })
print(json.dumps(result))
`], {cwd: root, encoding: "utf8"}));
const script = readFileSync(path.join(root, "static/js/checklist.js"), "utf8");
const flush = () => new Promise(resolve => setImmediate(resolve));
const ok = data => ({ok: true, status: 200, redirected: false, json: async () => data});
const added = {id: 2, text: "Novo passo", is_done: false, toggle_url: "/checklist/2/alternar/", remove_url: "/checklist/2/remover/"};

function setup(t, role = "editor", injected = false) {
    const dom = new JSDOM('<div class="drawer__body"><span id="timer">00:10:40</span><textarea id="comment">Comentário em andamento</textarea>' +
        (injected ? "" : fixtures[role]) + "</div>", {url: "http://localhost/tarefas/7/", runScripts: "outside-only"});
    t.after(() => dom.window.close());
    const {window} = dom;
    const calls = [], responses = [];
    window.fetch = (url, options) => {
        calls.push({url, options});
        const response = responses.shift();
        if (response instanceof Error) return Promise.reject(response);
        return Promise.resolve(response);
    };
    window.eval(script);
    if (injected) {
        window.document.querySelector(".drawer__body").insertAdjacentHTML("beforeend", fixtures[role]);
        window.LPSWidgets.forEach(init => init(window.document));
    }
    const $ = selector => window.document.querySelector(selector);
    const submit = () => $(".js-checklist-add").requestSubmit($(".js-checklist-add button"));
    const change = checked => {
        const checkbox = $(".js-checklist-toggle");
        checkbox.checked = checked;
        checkbox.dispatchEvent(new window.Event("change", {bubbles: true}));
    };
    return {window, $, calls, responses, submit, change};
}

test("adiciona por submit, restaura foco e preserva timer, comentário e scroll", async t => {
    const x = setup(t);
    const timer = x.$("#timer"), comment = x.$("#comment"), body = x.$(".drawer__body");
    body.scrollTop = 180;
    x.$("input[name=text]").value = " Novo passo ";
    x.responses.push(ok(added));
    x.submit();
    assert.equal(x.$("input[name=text]").disabled, true);
    await flush();
    assert.equal(x.calls.length, 1);
    assert.equal(x.calls[0].options.body, "text=Novo+passo");
    assert.equal(x.calls[0].options.headers["X-CSRFToken"], "test-csrf-token");
    assert.equal(x.$("input[name=text]").value, "");
    assert.equal(x.window.document.activeElement, x.$("input[name=text]"));
    assert.equal(x.$(".js-checklist-count").textContent, "0 de 2 concluídos");
    assert.equal(x.$("#timer"), timer);
    assert.equal(x.$("#comment"), comment);
    assert.equal(comment.value, "Comentário em andamento");
    assert.equal(body.scrollTop, 180);
});

test("componente injetado inicializa uma vez e bloqueia envio duplicado pendente", async t => {
    const x = setup(t, "editor", true);
    x.window.LPSWidgets.forEach(init => init(x.window.document));
    let resolve;
    x.responses.push(new Promise(done => { resolve = done; }));
    x.$("input[name=text]").value = "Novo passo";
    x.submit();
    x.$(".js-checklist-add").dispatchEvent(new x.window.Event("submit", {bubbles: true, cancelable: true}));
    assert.equal(x.calls.length, 1);
    resolve(ok(added));
    await flush();
    assert.equal(x.$(".js-checklist").children.length, 2);
});

test("executor marca e desmarca, sem controles para criar ou remover", async t => {
    const x = setup(t, "executor");
    assert.equal(x.$(".js-checklist-add"), null);
    assert.equal(x.$(".js-checklist-remove"), null);
    x.responses.push(ok({id: 1, is_done: true}));
    x.change(true);
    await flush();
    assert.equal(x.$(".js-checklist-count").textContent, "1 de 1 concluídos");
    x.responses.push(ok({id: 1, is_done: false}));
    x.change(false);
    await flush();
    assert.equal(x.$(".js-checklist-count").textContent, "0 de 1 concluídos");
    assert.equal(x.$(".js-checklist-toggle").disabled, false);
});

test("leitor não envia alterações", async t => {
    const x = setup(t, "reader");
    assert.equal(x.$(".js-checklist-toggle").disabled, true);
    x.change(true);
    await flush();
    assert.equal(x.calls.length, 0);
});

test("remoção só atualiza após confirmação e restaura estado vazio", async t => {
    const x = setup(t);
    let resolve;
    x.responses.push(new Promise(done => { resolve = done; }));
    const remove = x.$(".js-checklist-remove");
    remove.click();
    remove.click();
    assert.equal(x.calls.length, 1);
    assert.ok(x.$("[data-item-id]"));
    resolve(ok({ok: true}));
    await flush();
    assert.equal(x.$("[data-item-id]"), null);
    assert.equal(x.$(".js-checklist-empty").hidden, false);
    assert.equal(x.$(".js-checklist-count").textContent, "0 de 0 concluídos");
});

test("marcação rejeitada restaura checkbox e contagem", async t => {
    const x = setup(t);
    x.responses.push({ok: false, status: 400, json: async () => ({error: "Sem permissão"})});
    x.change(true);
    await flush();
    assert.equal(x.$(".js-checklist-toggle").checked, false);
    assert.equal(x.$(".js-checklist-toggle").disabled, false);
    assert.equal(x.$(".js-checklist-count").textContent, "0 de 1 concluídos");
    assert.equal(x.$(".js-checklist-error").textContent, "Sem permissão");
});

test("remoção rejeitada mantém item e permite nova tentativa", async t => {
    const x = setup(t);
    x.responses.push({ok: false, status: 400, json: async () => ({error: "Sem permissão"})});
    x.$(".js-checklist-remove").click();
    await flush();
    assert.ok(x.$("[data-item-id]"));
    assert.equal(x.$(".js-checklist-remove").disabled, false);
    assert.equal(x.$(".js-checklist-error").hidden, false);
});

for (const [name, response] of [
    ["validação", {ok: false, status: 400, json: async () => ({error: "Texto inválido"})}],
    ["CSRF", {ok: false, status: 403, json: async () => {throw new Error("HTML");}}],
    ["erro de servidor", {ok: false, status: 500, json: async () => {throw new Error("HTML");}}],
    ["sessão expirada", {ok: true, status: 200, redirected: true}],
    ["resposta incompleta", ok({})],
    ["resposta nula", ok(null)],
    ["rede", new Error("offline")],
]) {
    test("inclusão com falha de " + name + " preserva texto e não repete POST", async t => {
        const x = setup(t);
        x.responses.push(response);
        x.$("input[name=text]").value = "Meu texto";
        x.submit();
        await flush();
        assert.equal(x.calls.length, 1);
        assert.equal(x.$("input[name=text]").value, "Meu texto");
        assert.equal(x.$("input[name=text]").disabled, false);
        assert.equal(x.$(".js-checklist").children.length, 1);
        assert.equal(x.$(".js-checklist-error").hidden, false);
    });
}

test("espaços e texto longo são rejeitados sem POST", async t => {
    const x = setup(t);
    for (const text of ["   ", "a".repeat(256)]) {
        x.$("input[name=text]").value = text;
        x.submit();
        await flush();
        assert.equal(x.calls.length, 0);
        assert.equal(x.$(".js-checklist-error").hidden, false);
    }
});

test("texto recebido é conteúdo literal, sem executar HTML", async t => {
    const x = setup(t);
    const text = '<img src=x onerror="alert(1)">';
    x.responses.push(ok({...added, text}));
    x.$("input[name=text]").value = text;
    x.submit();
    await flush();
    const item = x.$('[data-item-id="2"]');
    assert.equal(item.querySelector("img"), null);
    assert.equal(item.querySelector("label span").textContent, text);
});
