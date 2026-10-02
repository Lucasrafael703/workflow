/* Edição inline da lista de Demandas (static/js/activity-inline-edit.js + activity-inline-options.js):
   título, responsável e prazo (Entrega 1); Setor (com criação de setor ali mesmo), Estágio e Status (Entrega 2).
   Requires jsdom@26.1.0 in NODE_PATH or node_modules; no browser or production dependency.
   Run from workflow: node --test tests/activity-inline-edit.test.cjs
   Set PYTHON to the project's Python if it is not in .venv.

   O HTML vem do template Django real (boards/demand_work_board.html, bloco `content`) renderizado com objetos em
   memória, sem banco. O servidor é simulado por um `fetch` falso: o contrato testado é "o que a tela manda" e "o que
   ela faz com a resposta". */
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync, existsSync} = require("node:fs");
const {execFileSync} = require("node:child_process");
const path = require("node:path");
const {JSDOM} = require("jsdom");

const root = path.resolve(__dirname, "..");
const localPython = path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const python = process.env.PYTHON || (existsSync(localPython) ? localPython : "python");

const PYTHON_FIXTURE = `
import os, re, json, datetime
from types import SimpleNamespace as NS
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import RequestFactory
from django.utils import timezone
from core.models import Sector

User = get_user_model()
ana = User(pk=7, username='ana', first_name='Ana', last_name='Souza')
sector = Sector(pk=1, name='Comercial', color='#F5B800')
stage = NS(text_color='#FFFFFF')
condition = NS(text_color='#FFFFFF')

def row(pk, title, flags, deadline=None, deadline_text='', overdue=False, owner=ana, sector=sector, overdue_days=0):
    return NS(
        pk=pk, title=title, code='DEM-2026-%05d' % pk, client=None, site=None, sector=sector, owner=owner, owner_id=owner.pk if owner else None,
        done_tasks=0, total_tasks=0, progress_percent=0, requested_deadline=deadline, inline_deadline_text=deadline_text,
        is_overdue=overdue, overdue_days=overdue_days, stage=stage, stage_id=31, stage_name='Orçamento', stage_color='#EF4444',
        condition=condition, condition_id=41, condition_name='Normal', condition_color='#94A3B8', inline=flags,
    )

full = {'locked': False, 'title': True, 'client': True, 'sector': True, 'stage': True, 'condition': True, 'owner': True, 'requested_deadline': True, 'deadline_date': '', 'deadline_time': ''}
aware = timezone.make_aware(datetime.datetime(2026, 10, 14, 17, 47))
activities = [
    row(101, 'Teste', dict(full)),
    row(102, 'Atualizar o ASO', dict(full, deadline_date='2026-10-14', deadline_time='17:47'), aware, '14/10/2026 17:47'),
    row(103, 'Já concluída', {'locked': True, 'title': False, 'client': False, 'sector': False, 'stage': False, 'condition': False, 'owner': False, 'requested_deadline': False, 'deadline_date': '', 'deadline_time': ''}),
    row(104, 'Sem responsável', dict(full, owner=False), owner=None),
    row(105, 'Sem setor', dict(full), sector=None),
    row(106, 'Atrasada', dict(full), aware, '14/10/2026 17:47', overdue=True, overdue_days=3),
]
activities[3].inline['owner'] = True

fs = NS(tab='minhas', q='', prazo='', filtro='', bloqueio='', condicao='', estagio='', setor='', ordem='prazo', active_count=0)
request = RequestFactory().get('/demandas/?tab=minhas')
source = open(os.path.join('templates', 'boards', 'demand_work_board.html'), encoding='utf-8').read()
body = re.search(r'{% block content %}(.*){% endblock %}\\s*{% block scripts %}', source, re.S).group(1)
context = Context({
    'request': request, 'can_create': True, 'view_mode': 'lista', 'tab': 'minhas', 'can_view_all': True, 'filter_querystring': '',
    'clear_filters_url': '/demandas/', 'filter_state': fs, 'condition_choice_groups': [], 'stage_choice_groups': [], 'sectors': [sector],
    'activities': activities,
})
context.request = request  # {% querystring %} lê context.request.GET
print(json.dumps({'html': Template('{% load lps static %}' + body).render(context)}))
`;

const FIXTURE = JSON.parse(execFileSync(python, ["-c", PYTHON_FIXTURE], {cwd: root, encoding: "utf8"}).trim());
const script = readFileSync(path.join(root, "static/js/activity-inline-edit.js"), "utf8");
const optionsScript = readFileSync(path.join(root, "static/js/activity-inline-options.js"), "utf8");
const colorScript = readFileSync(path.join(root, "static/js/color-utils.js"), "utf8");
const tick = () => new Promise(resolve => setImmediate(resolve));
const flush = async () => { for (let i = 0; i < 10; i += 1) await tick(); };

function jsonResponse(body, status = 200) {
    return Promise.resolve({ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body)});
}

const PEOPLE = [{id: 7, name: "Ana Souza", username: "ana"}, {id: 8, name: "Bruno Lima", username: "bruno"}, {id: 9, name: "Carla Dias", username: "carla"}];

const SECTORS = [
    {id: 1, name: "Comercial", color: "#F5B800", text_color: "#1F2937"},
    {id: 2, name: "Engenharia", color: "#2563EB", text_color: "#FFFFFF"},
    {id: 3, name: "Qualidade", color: "#16A34A", text_color: "#FFFFFF"},
];
const NEW_STAGE = {id: 32, name: "Projeto", color: "#22C55E", text_color: "#1F2937"};
const NEW_CONDITION = {id: 42, name: "Em análise", color: "#F59E0B", text_color: "#1F2937"};

function sectorOptions(extra = {}) {
    return jsonResponse({ok: true, field: "sector", current_id: 1, allow_clear: false, can_create: true, items: SECTORS, ...extra});
}

const STAGES = [
    {id: 31, name: "Orçamento", color: "#EF4444", text_color: "#FFFFFF"},
    {id: 32, name: "Projeto", color: "#22C55E", text_color: "#1F2937"},
    {id: 33, name: "Execução", color: "#2563EB", text_color: "#FFFFFF"},
];
const CONDITIONS = [
    {id: 41, name: "Normal", color: "#94A3B8", text_color: "#FFFFFF"},
    {id: 42, name: "Em análise", color: "#F59E0B", text_color: "#1F2937"},
];
let LAST_OPTION = null; // a última opção criada/editada pelo servidor falso

function optionOptions(field, extra = {}) {
    const items = field === "stage" ? STAGES : CONDITIONS;
    return jsonResponse({
        ok: true, field, current_id: field === "stage" ? 31 : 41, allow_clear: field === "condition", can_create: true, can_manage: true,
        manage_url: "/configuracoes/etapas-status/?domain=demandas&sector=1", sector_name: "Comercial", items, ...extra,
    });
}

function defaultRespond(call) {
    if (call.url.startsWith("/api/pessoas/")) return jsonResponse({results: PEOPLE});
    if (call.url.includes("/inline/opcoes/")) {
        if (call.method === "POST") {
            const b = call.body;
            LAST_OPTION = {id: b.get("acao") === "criar" ? 50 : Number(b.get("option_id")), name: b.get("name"), color: b.get("color"), text_color: "#FFFFFF"};
            return jsonResponse({ok: true, item: LAST_OPTION}, b.get("acao") === "criar" ? 201 : 200);
        }
        const campo = new URL(call.url, "http://localhost").searchParams.get("campo");
        return campo === "sector" ? sectorOptions() : optionOptions(campo);
    }
    const body = call.body;
    const field = body.get("field");
    if (field === "title") return jsonResponse({ok: true, field, value: body.get("value").trim(), display: {text: body.get("value").trim()}});
    if (field === "owner") {
        const person = PEOPLE.find(p => String(p.id) === body.get("value"));
        return jsonResponse({ok: true, field, value: person.id, display: {text: person.name, initials: person.name.slice(0, 2).toUpperCase(), avatar_class: "avatar--" + (person.id % 6)}});
    }
    if (field === "requested_deadline") {
        const date = body.get("date"), time = body.get("time");
        if (!date) return jsonResponse({ok: true, field, value: {date: "", time: ""}, display: {text: "Sem prazo", is_late: false}, derived: {overdue_days: 0}});
        const [y, m, d] = date.split("-");
        return jsonResponse({ok: true, field, value: {date, time}, display: {text: `${d}/${m}/${y}` + (time ? " " + time : ""), is_late: date < "2026-10-10"}, derived: {overdue_days: 0}});
    }
    if (field === "stage" || field === "condition") {
        const items = field === "stage" ? STAGES : CONDITIONS;
        const raw = body.get("value");
        const found = raw === "" ? null : (LAST_OPTION && String(LAST_OPTION.id) === raw ? LAST_OPTION : items.find(i => String(i.id) === raw));
        return jsonResponse({ok: true, field, value: found ? found.id : "", display: found});
    }
    if (field === "sector") {
        const created = body.get("new_name");
        const target = created ? {id: 9, name: created, color: body.get("new_color"), text_color: "#FFFFFF"} : SECTORS.find(s => String(s.id) === body.get("value"));
        const derived = created ? {stage: null, condition: null} : {stage: NEW_STAGE, condition: NEW_CONDITION};
        return jsonResponse({ok: true, field, value: target.id, display: target, derived, ...(created ? {created_sector: target} : {})});
    }
    return jsonResponse({ok: false, error: "campo?"}, 400);
}

function setup(t, {respond} = {}) {
    LAST_OPTION = null;
    const dom = new JSDOM("<!doctype html><body>" + FIXTURE.html + "</body>", {
        url: "http://localhost/demandas/?tab=minhas", runScripts: "outside-only", pretendToBeVisual: true,
    });
    t.after(() => dom.window.close());
    const w = dom.window;
    w.document.cookie = "csrftoken=tok123";
    const calls = [];
    w.fetch = (url, options = {}) => {
        const call = {url, method: options.method || "GET", headers: options.headers || {}, body: options.body || null};
        calls.push(call);
        return (respond && respond(call)) || defaultRespond(call);
    };
    const timers = [];
    let timerId = 0;
    w.setTimeout = (fn, ms) => { timerId += 1; timers.push({id: timerId, fn, ms}); return timerId; };
    w.clearTimeout = id => { const index = timers.findIndex(timer => timer.id === id); if (index >= 0) timers.splice(index, 1); };
    w.eval(colorScript);
    w.eval(script);
    w.eval(optionsScript);
    if (!w.LPSInlineEdit.instance) w.LPSInlineEdit.boot();
    const $ = selector => w.document.querySelector(selector);
    const $$ = selector => Array.from(w.document.querySelectorAll(selector));
    const click = element => {
        const event = new w.MouseEvent("click", {bubbles: true, cancelable: true, button: 0});
        element.dispatchEvent(event);
        return event;
    };
    const key = (element, keyName) => {
        const event = new w.KeyboardEvent("keydown", {key: keyName, bubbles: true, cancelable: true});
        element.dispatchEvent(event);
        return event;
    };
    const cell = (activityId, field) => $(`tr[data-activity-id="${activityId}"] [data-inline-field="${field}"]`);
    const saves = () => calls.filter(call => call.url.endsWith("/inline/"));
    const optionCalls = () => calls.filter(call => call.url.includes("/inline/opcoes/"));
    const sectorCell = id => $(`tr[data-activity-id="${id}"] td[data-inline-field="sector"]`);
    const stageCell = id => $(`tr[data-activity-id="${id}"] td[data-column="stage"]`);
    const conditionCell = id => $(`tr[data-activity-id="${id}"] td[data-column="condition"]`);
    const optionButtons = () => $$(".activity-inline-popover .activity-inline-color-option");
    const chip = td => td.querySelector(".demand-board__status");
    const runTimers = () => { while (timers.length) timers.shift().fn(); };
    const toasts = () => $$(".lps-toast.is-error").map(node => node.textContent);
    return {w, $, $$, click, key, cell, calls, saves, runTimers, toasts, optionCalls, sectorCell, stageCell, conditionCell, optionButtons, chip};
}

const type = (w, input, value) => { input.value = value; input.dispatchEvent(new w.Event("input", {bubbles: true})); };

// ---------------------------------------------------------------------------------------------------
// Funções puras
// ---------------------------------------------------------------------------------------------------

test("helpers: fillUrl, csrfFromCookie, initials, avatarClass and deadlineText", t => {
    const {w} = setup(t);
    const h = w.LPSInlineEdit.helpers;
    assert.equal(h.fillUrl("/demandas/999999999/inline/", 999999999, 42), "/demandas/42/inline/");
    assert.equal(h.csrfFromCookie("a=1; csrftoken=ab%20c; b=2"), "ab c");
    assert.equal(h.csrfFromCookie(""), "");
    assert.equal(h.initials("ana souza"), "AN");
    assert.equal(h.avatarClass(13), "avatar--1"); // pk % 6, como no servidor
    assert.equal(h.avatarClass("x"), "avatar--0");
    assert.equal(h.deadlineText("2026-10-14", "17:47"), "14/10/2026 17:47");
    assert.equal(h.deadlineText("2026-10-14", ""), "14/10/2026");
    assert.equal(h.deadlineText("", ""), "Sem prazo");
});

// ---------------------------------------------------------------------------------------------------
// Estrutura: a tela em repouso e quem pode editar
// ---------------------------------------------------------------------------------------------------

test("markers only where the row allows editing; locked rows and rows without permission stay as before", t => {
    const {$, $$, cell} = setup(t);
    for (const field of ["title", "owner", "requested_deadline"]) assert.ok(cell(101, field), field);
    assert.equal(cell(103, "title"), null);
    assert.equal(cell(103, "owner"), null);
    assert.equal($$('tr[data-activity-id="103"] [data-inline-field]').length, 0);
    // a linha travada mantém o título como link para o detalhe
    assert.ok($$('tr[data-activity-id="103"] .demand-board__title-cell > a > strong').length === 1);
    // editável: o título vira campo e o link fica no subtítulo
    assert.equal($$('tr[data-activity-id="101"] .demand-board__title-cell > a').length, 0);
    assert.ok($('tr[data-activity-id="101"] .demand-board__title-wrap > a span'));
});

test("nothing is added to the resting table: no chevron, no pencil, no extra buttons", t => {
    const {$$, $} = setup(t);
    const table = $("[data-activity-list]");
    assert.equal(table.querySelectorAll("button").length, 0);
    assert.equal(table.querySelectorAll("input, select, textarea").length, 0);
    assert.doesNotMatch(table.textContent, /[▼▲⌄⌃✎✏]/);
    assert.equal($$("[data-activity-list] svg use").filter(node => /chevron|pencil|edit/i.test(node.getAttribute("href") || "")).length, 0);
    assert.equal($(".activity-inline-popover"), null);
    assert.equal($$("[data-inline-field]").every(node => node.getAttribute("tabindex") === "0" && node.getAttribute("role") === "button" && node.getAttribute("aria-label")), true);
});

test("cliente / obra: a célula é link para a janela Editar demanda na etapa 2, só onde a linha permite", t => {
    const {w, $, $$, click, saves} = setup(t);
    const link = $('tr[data-activity-id="101"] .demand-board__context-cell a');
    assert.ok(link, "linha editável tem o link");
    assert.match(link.getAttribute("href"), /^\/demandas\/101\/editar\/\?passo=2&next=/);
    assert.ok(link.hasAttribute("data-activity-action"), "o activity-workspace.js abre a janela");
    assert.ok(!link.hasAttribute("data-activity-navigate"), "ao salvar, a lista recarrega em vez de ir ao detalhe");
    assert.equal(link.querySelector("strong").textContent, "Sem cliente", "o texto da célula é o de sempre");
    assert.equal($$('tr[data-activity-id="103"] .demand-board__context-cell a').length, 0, "linha travada não tem link");
    assert.equal($$('tr[data-activity-id="103"] .demand-board__context-cell strong').length, 1);
    // o editor inline não captura nem cancela esse clique: quem trata é o activity-workspace.js
    let prevented = null;
    w.document.addEventListener("click", event => { prevented = event.defaultPrevented; event.preventDefault(); });
    click(link);
    assert.equal(prevented, false);
    assert.equal($(".activity-inline-popover"), null);
    assert.equal(saves().length, 0);
});

// ---------------------------------------------------------------------------------------------------
// Título
// ---------------------------------------------------------------------------------------------------

test("title: click edits in the cell, Enter saves with CSRF and the optimistic text, no page change and no toast", async t => {
    const {w, $, click, key, cell, saves, toasts} = setup(t);
    const field = cell(101, "title");
    click(field);
    const input = field.querySelector("input");
    assert.equal(input.value, "Teste");
    assert.ok(field.classList.contains("is-editing"));
    input.value = "  Teste novo  ";
    key(input, "Enter");
    assert.equal(field.textContent, "Teste novo"); // otimista, antes da resposta
    assert.ok(field.classList.contains("is-saving"));
    assert.equal(field.getAttribute("aria-busy"), "true");
    await flush();
    assert.equal(saves().length, 1);
    const call = saves()[0];
    assert.equal(call.url, "/demandas/101/inline/");
    assert.equal(call.method, "POST");
    assert.equal(call.headers["X-CSRFToken"], "tok123");
    assert.equal(call.headers["X-Requested-With"], "XMLHttpRequest");
    assert.equal(call.body.get("field"), "title");
    assert.equal(call.body.get("value"), "Teste novo");
    assert.equal(field.textContent, "Teste novo");
    assert.equal(field.dataset.inlineValue, "Teste novo");
    assert.ok(!field.classList.contains("is-saving"));
    assert.ok(field.classList.contains("is-saved")); // sucesso é só um realce, sem aviso
    assert.equal(field.hasAttribute("aria-busy"), false);
    assert.deepEqual(toasts(), []);
    assert.equal($(".lps-toast"), null);
    assert.equal(w.location.pathname, "/demandas/");
});

test("title: Escape restores the text and sends nothing; an unchanged title sends nothing", async t => {
    const {click, key, cell, saves} = setup(t);
    const field = cell(101, "title");
    click(field);
    field.querySelector("input").value = "Outro";
    key(field.querySelector("input"), "Escape");
    assert.equal(field.textContent, "Teste");
    assert.equal(field.querySelector("input"), null);
    click(field);
    key(field.querySelector("input"), "Enter"); // não mudou
    await flush();
    assert.equal(saves().length, 0);
    assert.equal(field.textContent, "Teste");
});

test("title: blur saves a change; an empty title never saves (Enter keeps editing, blur reverts)", async t => {
    const {w, click, key, cell, saves} = setup(t);
    const field = cell(101, "title");
    click(field);
    field.querySelector("input").value = "Por blur";
    field.querySelector("input").dispatchEvent(new w.FocusEvent("blur"));
    await flush();
    assert.equal(saves().length, 1);
    assert.equal(field.textContent, "Por blur");

    click(field);
    const input = field.querySelector("input");
    input.value = "   ";
    key(input, "Enter");
    assert.equal(input.getAttribute("aria-invalid"), "true");
    assert.ok(field.querySelector("input")); // continua editando
    input.dispatchEvent(new w.FocusEvent("blur")); // sair do campo só desfaz
    await flush();
    assert.equal(saves().length, 1);
    assert.equal(field.textContent, "Por blur");
});

test("title: a refusal restores the confirmed text, marks the cell and shows a short error", async t => {
    const respond = call => call.body && call.body.get("field") === "title" ? jsonResponse({ok: false, error: "O título pode ter até 200 caracteres."}, 400) : null;
    const {click, key, cell, toasts, $} = setup(t, {respond});
    const field = cell(101, "title");
    click(field);
    field.querySelector("input").value = "x".repeat(10);
    key(field.querySelector("input"), "Enter");
    await flush();
    assert.equal(field.textContent, "Teste");
    assert.ok(field.classList.contains("is-error"));
    assert.deepEqual(toasts(), ["O título pode ter até 200 caracteres."]);
    assert.equal($(".lps-toast.is-error").getAttribute("role"), "alert");
});

test("title: a permission refusal (403) and a lost connection are reported without leaking details", async t => {
    let mode = "403";
    const respond = call => {
        if (!call.url.endsWith("/inline/")) return null;
        return mode === "403" ? jsonResponse({ok: false, error: "Você não tem permissão para fazer isso."}, 403) : Promise.reject(new Error("offline"));
    };
    const {click, key, cell, toasts} = setup(t, {respond});
    const field = cell(101, "title");
    click(field);
    field.querySelector("input").value = "A";
    key(field.querySelector("input"), "Enter");
    await flush();
    mode = "offline";
    click(field);
    field.querySelector("input").value = "B";
    key(field.querySelector("input"), "Enter");
    await flush();
    assert.deepEqual(toasts(), ["Você não tem permissão para fazer isso.", "Sem conexão com o servidor. Tente de novo."]);
    assert.equal(field.textContent, "Teste");
});

test("title: the server text is shown as text, never as markup", async t => {
    const payload = "<img src=x onerror=alert(1)><b>x</b>";
    const respond = call => call.body && call.body.get("field") === "title" ? jsonResponse({ok: true, field: "title", value: payload, display: {text: payload}}) : null;
    const {click, key, cell} = setup(t, {respond});
    const field = cell(101, "title");
    click(field);
    field.querySelector("input").value = "algo";
    key(field.querySelector("input"), "Enter");
    await flush();
    assert.equal(field.textContent, payload);
    assert.equal(field.querySelector("img, b"), null);
});

test("rollback goes back to the last CONFIRMED value, not to what was on screen at the start", async t => {
    let fail = false;
    const respond = call => {
        if (!call.url.endsWith("/inline/")) return null;
        return fail ? jsonResponse({ok: false, error: "não"}, 400) : jsonResponse({ok: true, field: "title", value: "Confirmado pelo servidor", display: {text: "Confirmado pelo servidor"}});
    };
    const {click, key, cell} = setup(t, {respond});
    const field = cell(101, "title");
    click(field);
    field.querySelector("input").value = "Primeiro";
    key(field.querySelector("input"), "Enter");
    await flush();
    assert.equal(field.textContent, "Confirmado pelo servidor");
    fail = true;
    click(field);
    field.querySelector("input").value = "Segundo";
    key(field.querySelector("input"), "Enter");
    await flush();
    assert.equal(field.textContent, "Confirmado pelo servidor"); // e não "Teste" (o HTML original)
});

test("only one request per cell at a time: while saving, a new edit of the same cell is ignored; other cells stay free", async t => {
    const pending = [];
    const respond = call => call.body && call.body.get("field") === "title" ? new Promise(resolve => pending.push(resolve)) : null;
    const {click, key, cell, saves} = setup(t, {respond});
    const field = cell(101, "title");
    click(field);
    field.querySelector("input").value = "Um";
    key(field.querySelector("input"), "Enter");
    assert.equal(saves().length, 1);
    click(field); // célula ocupada: nada abre
    assert.equal(field.querySelector("input"), null);
    assert.equal(saves().length, 1);
    click(cell(102, "title")); // outra célula continua livre
    assert.ok(cell(102, "title").querySelector("input"));
    pending[0]({ok: true, json: () => Promise.resolve({ok: true, field: "title", value: "Um", display: {text: "Um"}}), status: 200});
    await flush();
    assert.ok(!field.classList.contains("is-saving"));
    click(field); // livre de novo
    assert.ok(field.querySelector("input"));
});

// ---------------------------------------------------------------------------------------------------
// Responsável
// ---------------------------------------------------------------------------------------------------

test("owner: click opens a pop-over in the global layer with the first people; choosing saves and closes it", async t => {
    const {$, $$, click, cell, saves, calls} = setup(t);
    const field = cell(101, "owner");
    click(field);
    const pop = $("#activity-inline-overlay-root .activity-inline-popover");
    assert.ok(pop);
    assert.equal(field.getAttribute("aria-expanded"), "true");
    assert.ok(field.classList.contains("is-editing"));
    await flush();
    assert.equal(calls[0].url, "/api/pessoas/?q="); // abre já com as primeiras pessoas
    assert.deepEqual($$(".activity-inline-popover__option .activity-inline-popover__name").map(n => n.textContent), ["Ana Souza", "Bruno Lima", "Carla Dias"]);
    assert.equal($(".activity-inline-popover__option[aria-current=true] .activity-inline-popover__name").textContent, "Ana Souza");
    click($$(".activity-inline-popover__option")[1]);
    assert.equal($(".activity-inline-popover"), null);
    assert.equal(field.getAttribute("aria-expanded"), null);
    assert.match(field.textContent, /Bruno Lima/); // otimista
    await flush();
    assert.equal(saves().length, 1);
    assert.equal(saves()[0].url, "/demandas/101/inline/");
    assert.equal(saves()[0].body.get("field"), "owner");
    assert.equal(saves()[0].body.get("value"), "8");
    assert.equal(field.dataset.inlineValue, "8");
    assert.ok(field.querySelector(".avatar").className.includes("avatar--2")); // pk % 6, do servidor
    assert.equal(field.querySelector(".avatar").textContent, "BR");
});

test("owner: choosing the current person sends nothing; an empty owner shows 'Sem responsável' and can be filled", async t => {
    const {$$, click, cell, saves} = setup(t);
    click(cell(101, "owner"));
    await flush();
    click($$(".activity-inline-popover__option")[0]); // Ana, a atual
    await flush();
    assert.equal(saves().length, 0);
    const empty = cell(104, "owner");
    assert.equal(empty.textContent.trim(), "Sem responsável");
    click(empty);
    await flush();
    click($$(".activity-inline-popover__option")[2]);
    await flush();
    assert.match(empty.textContent, /Carla Dias/);
    assert.equal(saves()[0].body.get("value"), "9");
});

test("owner: a refusal puts the previous person back", async t => {
    const respond = call => call.body && call.body.get && call.body.get("field") === "owner" ? jsonResponse({ok: false, error: "Você não tem permissão para trocar o responsável."}, 403) : null;
    const {$$, click, cell, toasts} = setup(t, {respond});
    const field = cell(101, "owner");
    click(field);
    await flush();
    click($$(".activity-inline-popover__option")[1]);
    await flush();
    assert.match(field.textContent, /Ana Souza/);
    assert.equal(field.dataset.inlineValue, "7");
    assert.deepEqual(toasts(), ["Você não tem permissão para trocar o responsável."]);
});

test("owner: typing searches with debounce and a late answer to an old search is ignored", async t => {
    const waiting = {};
    const respond = call => {
        if (!call.url.startsWith("/api/pessoas/")) return null;
        const q = decodeURIComponent(call.url.split("q=")[1]);
        if (q === "") return jsonResponse({results: PEOPLE});
        return new Promise(resolve => { waiting[q] = resolve; });
    };
    const {w, $, $$, click, cell, calls, runTimers} = setup(t, {respond});
    click(cell(101, "owner"));
    await flush();
    const search = $(".activity-inline-popover__input");
    type(w, search, "br");
    type(w, search, "bru");
    assert.equal(calls.length, 1); // ainda dentro do debounce: nada pedido
    runTimers();
    assert.equal(calls.length, 2);
    assert.equal(decodeURIComponent(calls[1].url.split("q=")[1]), "bru");
    type(w, search, "car");
    runTimers();
    assert.equal(calls.length, 3);
    waiting["car"]({ok: true, json: () => Promise.resolve({results: [PEOPLE[2]]}), status: 200});
    await flush();
    waiting["bru"]({ok: true, json: () => Promise.resolve({results: [PEOPLE[1]]}), status: 200}); // resposta velha chega depois
    await flush();
    assert.deepEqual($$(".activity-inline-popover__name").map(n => n.textContent), ["Carla Dias"]);
});

// ---------------------------------------------------------------------------------------------------
// Prazo
// ---------------------------------------------------------------------------------------------------

test("deadline: the pop-over opens with the current date and time; Aplicar saves date and optional time", async t => {
    const {$, click, cell, saves} = setup(t);
    const field = cell(102, "requested_deadline");
    click(field);
    const date = $('.activity-inline-popover input[type="date"]');
    const time = $('.activity-inline-popover input[type="time"]');
    assert.equal(date.value, "2026-10-14");
    assert.equal(time.value, "17:47");
    date.value = "2026-10-20";
    time.value = "";
    click([...document_buttons($)].find(b => b.textContent === "Aplicar"));
    assert.equal(field.querySelector("span").textContent, "20/10/2026"); // otimista
    await flush();
    assert.equal(saves().length, 1);
    assert.equal(saves()[0].url, "/demandas/102/inline/");
    assert.equal(saves()[0].body.get("field"), "requested_deadline");
    assert.equal(saves()[0].body.get("date"), "2026-10-20");
    assert.equal(saves()[0].body.get("time"), "");
    assert.equal($(".activity-inline-popover"), null);
    assert.equal(field.dataset.inlineDate, "2026-10-20");
    assert.equal(field.dataset.inlineTime, "");
});

function document_buttons($) { return Array.from($(".activity-inline-popover").querySelectorAll("button")); }

test("deadline: empty cell gets a date and a time; Limpar removes the deadline; the late mark follows the server", async t => {
    const {$, click, cell} = setup(t);
    const field = cell(101, "requested_deadline");
    assert.equal(field.querySelector("span").textContent, "Sem prazo");
    click(field);
    $('.activity-inline-popover input[type="date"]').value = "2026-10-01";
    $('.activity-inline-popover input[type="time"]').value = "09:30";
    click(document_buttons($).find(b => b.textContent === "Aplicar"));
    await flush();
    assert.equal(field.querySelector("span").textContent, "01/10/2026 09:30");
    assert.ok(field.querySelector(".demand-board__deadline").classList.contains("is-late")); // is_late veio do servidor

    click(field);
    click(document_buttons($).find(b => b.textContent === "Limpar"));
    await flush();
    assert.equal(field.querySelector("span").textContent, "Sem prazo");
    assert.ok(!field.querySelector(".demand-board__deadline").classList.contains("is-late"));
    assert.equal(field.dataset.inlineDate, "");
});

test("deadline: Aplicar without a date shows a message in the pop-over and sends nothing; Cancelar closes", async t => {
    const {$, click, cell, saves} = setup(t);
    click(cell(101, "requested_deadline"));
    click(document_buttons($).find(b => b.textContent === "Aplicar"));
    assert.equal($(".activity-inline-popover__error").hidden, false);
    assert.match($(".activity-inline-popover__error").textContent, /Escolha a data/);
    assert.ok($(".activity-inline-popover")); // continua aberto
    click(document_buttons($).find(b => b.textContent === "Cancelar"));
    assert.equal($(".activity-inline-popover"), null);
    await flush();
    assert.equal(saves().length, 0);
});

test("deadline: a refusal restores the previous deadline text and flags", async t => {
    const respond = call => call.body && call.body.get && call.body.get("field") === "requested_deadline" ? jsonResponse({ok: false, error: "Não é possível editar uma demanda concluída ou cancelada."}, 400) : null;
    const {$, click, cell, toasts} = setup(t, {respond});
    const field = cell(102, "requested_deadline");
    click(field);
    $('.activity-inline-popover input[type="date"]').value = "2026-11-02";
    click(document_buttons($).find(b => b.textContent === "Aplicar"));
    await flush();
    assert.equal(field.querySelector("span").textContent, "14/10/2026 17:47");
    assert.equal(field.dataset.inlineDate, "2026-10-14");
    assert.deepEqual(toasts(), ["Não é possível editar uma demanda concluída ou cancelada."]);
});

// ---------------------------------------------------------------------------------------------------
// Pop-over: um só, fecha por clique fora e Esc, acompanha o scroll, teclado
// ---------------------------------------------------------------------------------------------------

test("only one pop-over at a time; clicking the same cell again closes it; outside click and Escape close it", async t => {
    const {w, $, $$, click, key, cell} = setup(t);
    click(cell(101, "owner"));
    click(cell(102, "requested_deadline"));
    assert.equal($$(".activity-inline-popover").length, 1);
    assert.ok($('.activity-inline-popover input[type="date"]'));
    assert.equal(cell(101, "owner").getAttribute("aria-expanded"), null);
    click(cell(102, "requested_deadline")); // de novo: fecha
    assert.equal($(".activity-inline-popover"), null);

    click(cell(101, "owner"));
    w.document.body.dispatchEvent(new w.MouseEvent("mousedown", {bubbles: true}));
    assert.equal($(".activity-inline-popover"), null);

    click(cell(101, "owner"));
    await flush();
    $(".activity-inline-popover__input").dispatchEvent(new w.KeyboardEvent("keydown", {key: "Escape", bubbles: true, cancelable: true}));
    assert.equal($(".activity-inline-popover"), null);
    assert.equal(w.document.activeElement, cell(101, "owner")); // o foco volta para a célula
});

test("mousedown inside the pop-over does not close it", async t => {
    const {w, $, click, cell} = setup(t);
    click(cell(101, "owner"));
    await flush();
    $(".activity-inline-popover").dispatchEvent(new w.MouseEvent("mousedown", {bubbles: true}));
    assert.ok($(".activity-inline-popover"));
});

test("the pop-over follows the cell on scroll and resize instead of closing", async t => {
    const {w, $, click, cell} = setup(t);
    const field = cell(101, "owner");
    let rect = {left: 100, right: 300, top: 150, bottom: 200, width: 200, height: 50};
    field.getBoundingClientRect = () => rect;
    click(field);
    const pop = $(".activity-inline-popover");
    assert.equal(pop.style.top, "204px");
    assert.equal(pop.style.left, "100px");
    rect = {left: 120, right: 320, top: 90, bottom: 140, width: 200, height: 50};
    w.dispatchEvent(new w.Event("scroll"));
    assert.equal(pop.style.top, "144px");
    assert.equal(pop.style.left, "120px");
    rect = {left: 130, right: 330, top: 60, bottom: 110, width: 200, height: 50};
    w.dispatchEvent(new w.Event("resize"));
    assert.equal(pop.style.top, "114px");
    assert.ok($(".activity-inline-popover"));
});

test("keyboard: Enter and Space on a focused cell open its editor", async t => {
    const {$, key, cell} = setup(t);
    key(cell(101, "owner"), "Enter");
    assert.ok($(".activity-inline-popover"));
    key(cell(101, "owner"), "Enter"); // de novo, fecha
    assert.equal($(".activity-inline-popover"), null);
    key(cell(102, "requested_deadline"), " ");
    assert.ok($('.activity-inline-popover input[type="date"]'));
    key(cell(101, "title"), "Enter");
    assert.ok(cell(101, "title").querySelector("input"));
    assert.equal($(".activity-inline-popover"), null); // abrir outra célula fecha o pop-over anterior
});


// ---------------------------------------------------------------------------------------------------
// Entrega 2: Setor (pop-over na tela, trocar e criar), Estágio e Status redesenhados pelo servidor
// ---------------------------------------------------------------------------------------------------

const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return {promise, resolve}; };

test("setor: o marcador fica no <td> só onde a linha permite e a tabela em repouso continua sem controles novos", t => {
    const {$$, sectorCell, stageCell, conditionCell} = setup(t);
    const td = sectorCell(101);
    assert.ok(td, "linha editável");
    assert.equal(td.getAttribute("role"), "button");
    assert.equal(td.getAttribute("tabindex"), "0");
    assert.match(td.getAttribute("aria-label"), /setor/i);
    assert.ok(td.querySelector(".sector-badge"), "o selo continua dentro da célula");
    assert.equal(sectorCell(103), null, "linha travada (concluída) não tem marcador");
    assert.equal($$('tr[data-activity-id="103"] td[data-inline-field]').length, 0);
    assert.ok(sectorCell(105), "demanda sem setor também pode ganhar um");
    assert.equal(sectorCell(105).textContent.trim(), "Sem setor");
    // Estágio e Status carregam a opção atual (`data-option-id`); só ficam editáveis quando a linha permite (Entrega 2C)
    assert.equal(stageCell(101).dataset.optionId, "31");
    assert.equal(conditionCell(101).dataset.optionId, "41");
    assert.equal($$("[data-activity-list] button, [data-activity-list] input").length, 0);
});

test("setor: clicar abre o pop-over com os setores coloridos, o atual marcado, e busca a lista da demanda", async t => {
    const {click, sectorCell, optionCalls, optionButtons, $} = setup(t);
    click(sectorCell(101));
    await flush();
    assert.equal(optionCalls().length, 1);
    assert.equal(optionCalls()[0].url, "/demandas/101/inline/opcoes/?campo=sector");
    assert.equal(optionCalls()[0].headers["X-Requested-With"], "XMLHttpRequest");
    const buttons = optionButtons();
    assert.deepEqual(buttons.map(b => b.querySelector(".activity-inline-color-option__name").textContent), ["Comercial", "Engenharia", "Qualidade"]);
    assert.match(buttons[1].getAttribute("style"), /--option-bg:#2563EB;--option-text:#FFFFFF/);
    assert.equal(buttons[0].getAttribute("aria-current"), "true");
    assert.equal(buttons[0].querySelector(".activity-inline-color-option__check").textContent, "✓");
    assert.equal(buttons[1].hasAttribute("aria-current"), false);
    assert.equal($("#activity-inline-overlay-root .activity-inline-popover").getAttribute("role"), "dialog");
    assert.equal(sectorCell(101).getAttribute("aria-expanded"), "true");
});

test("setor: escolher outro grava otimista; Estágio e Status ficam travados e são redesenhados com o que o servidor devolve", async t => {
    const gate = deferred();
    const {click, sectorCell, stageCell, conditionCell, saves, optionButtons, chip, toasts, $} = setup(t, {
        respond: call => call.url.endsWith("/inline/") ? gate.promise.then(() => defaultRespond(call)) : null,
    });
    click(sectorCell(101));
    await flush();
    click(optionButtons()[1]); // Engenharia
    assert.equal($(".activity-inline-popover"), null, "o pop-over fecha ao escolher");
    assert.equal(saves().length, 1);
    assert.equal(saves()[0].body.get("field"), "sector");
    assert.equal(saves()[0].body.get("value"), "2");
    assert.equal(saves()[0].headers["X-CSRFToken"], "tok123");
    // otimista: o selo já mostra o setor novo; as outras duas células aguardam o servidor
    assert.equal(sectorCell(101).querySelector(".sector-badge").textContent, "Engenharia");
    assert.match(sectorCell(101).querySelector(".sector-badge").getAttribute("style"), /--sector-color: #2563EB; --sector-text-color: #FFFFFF;/);
    for (const td of [sectorCell(101), stageCell(101), conditionCell(101)]) {
        assert.ok(td.classList.contains("is-saving"));
        assert.equal(td.getAttribute("aria-busy"), "true");
    }
    assert.equal(chip(stageCell(101)).textContent, "Orçamento", "ainda não mudou");
    gate.resolve();
    await flush();
    assert.equal(chip(stageCell(101)).textContent, "Projeto");
    assert.match(chip(stageCell(101)).getAttribute("style"), /--status-bg:#22C55E;--status-text:#1F2937;/);
    assert.equal(stageCell(101).dataset.optionId, "32");
    assert.equal(chip(conditionCell(101)).textContent, "Em análise");
    assert.equal(conditionCell(101).dataset.optionId, "42");
    for (const td of [sectorCell(101), stageCell(101), conditionCell(101)]) {
        assert.equal(td.classList.contains("is-saving"), false);
        assert.equal(td.hasAttribute("aria-busy"), false);
    }
    assert.equal(sectorCell(101).dataset.inlineField, "sector");
    assert.deepEqual(toasts(), [], "sucesso é silencioso");
    // as outras linhas não são tocadas
    assert.equal(chip(stageCell(102)).textContent, "Orçamento");
});

test("setor: escolher o setor atual não envia nada", async t => {
    const {click, sectorCell, saves, optionButtons, $} = setup(t);
    click(sectorCell(101));
    await flush();
    click(optionButtons()[0]);
    assert.equal(saves().length, 0);
    assert.equal($(".activity-inline-popover"), null);
});

test("setor: recusa do servidor volta ao último setor confirmado, não toca Estágio/Status e avisa", async t => {
    const {click, sectorCell, stageCell, conditionCell, optionButtons, chip, toasts} = setup(t, {
        respond: call => call.url.endsWith("/inline/") ? jsonResponse({ok: false, error: "Você não tem permissão para editar demandas no setor de destino."}, 403) : null,
    });
    click(sectorCell(101));
    await flush();
    click(optionButtons()[2]);
    await flush();
    assert.equal(sectorCell(101).querySelector(".sector-badge").textContent, "Comercial");
    assert.match(sectorCell(101).querySelector(".sector-badge").getAttribute("style"), /#F5B800/);
    assert.equal(chip(stageCell(101)).textContent, "Orçamento");
    assert.equal(chip(conditionCell(101)).textContent, "Normal");
    assert.deepEqual(toasts(), ["Você não tem permissão para editar demandas no setor de destino."]);
    for (const td of [sectorCell(101), stageCell(101), conditionCell(101)]) assert.equal(td.classList.contains("is-saving"), false);
    assert.ok(sectorCell(101).classList.contains("is-error"));
});

test("setor: enquanto grava, a linha não aceita outra gravação de setor (uma requisição por vez)", async t => {
    const gate = deferred();
    const {click, sectorCell, saves, optionButtons, w} = setup(t, {
        respond: call => call.url.endsWith("/inline/") ? gate.promise.then(() => defaultRespond(call)) : null,
    });
    click(sectorCell(101));
    await flush();
    click(optionButtons()[1]);
    click(sectorCell(101)); // ocupado: não abre
    await flush();
    assert.equal(w.document.querySelector(".activity-inline-popover"), null);
    assert.equal(saves().length, 1);
    gate.resolve();
    await flush();
    click(sectorCell(101)); // livre de novo
    await flush();
    assert.ok(w.document.querySelector(".activity-inline-popover"));
});

test("setor: o texto do servidor entra como texto (nunca como HTML) e cores inválidas viram a cor neutra", async t => {
    const evil = {id: 7, name: "<img src=x onerror=alert(1)>", color: "red;background:url(x)", text_color: "javascript:1"};
    const {click, sectorCell, optionButtons, $$} = setup(t, {
        respond: call => call.url.includes("/inline/opcoes/") ? sectorOptions({items: [...SECTORS, evil]}) : null,
    });
    click(sectorCell(101));
    await flush();
    const buttons = optionButtons();
    const last = buttons[buttons.length - 1];
    assert.equal(last.querySelector(".activity-inline-color-option__name").textContent, "<img src=x onerror=alert(1)>");
    assert.equal($$(".activity-inline-popover img").length, 0);
    assert.match(last.getAttribute("style"), /--option-bg:#94A3B8;--option-text:#FFFFFF/);
});

test("setor: com muitas opções aparece a busca, que filtra sem diferenciar acentos", async t => {
    const many = Array.from({length: 10}, (_, i) => ({id: 20 + i, name: `Setor ${i}`, color: "#3B82F6", text_color: "#FFFFFF"}));
    many.push({id: 40, name: "Manutenção", color: "#EF4444", text_color: "#FFFFFF"});
    const {click, sectorCell, optionButtons, w, $} = setup(t, {
        respond: call => call.url.includes("/inline/opcoes/") ? sectorOptions({items: many}) : null,
    });
    click(sectorCell(101));
    await flush();
    const search = $(".activity-inline-popover input[type=search]");
    assert.ok(search, "11 opções: busca disponível");
    assert.equal(w.document.activeElement, search);
    search.value = "manuten";
    search.dispatchEvent(new w.Event("input", {bubbles: true}));
    assert.deepEqual(optionButtons().map(b => b.textContent), ["Manutenção"]);
    search.value = "zzz";
    search.dispatchEvent(new w.Event("input", {bubbles: true}));
    assert.equal(optionButtons().length, 0);
    assert.match($(".activity-inline-popover").textContent, /Nenhum setor encontrado/);
});

test("setor: com poucas opções não há busca; as setas movem o foco e Esc fecha devolvendo o foco à célula", async t => {
    const {click, key, sectorCell, optionButtons, w, $} = setup(t);
    click(sectorCell(101));
    await flush();
    assert.equal($(".activity-inline-popover input[type=search]"), null);
    const buttons = optionButtons();
    assert.equal(w.document.activeElement, buttons[0], "o foco começa na opção atual");
    key(buttons[0], "ArrowDown");
    assert.equal(w.document.activeElement, buttons[1]);
    key(buttons[1], "ArrowUp");
    key(buttons[0], "ArrowUp");
    assert.equal(w.document.activeElement, buttons[2], "dá a volta");
    key(w.document.activeElement, "Escape");
    assert.equal($(".activity-inline-popover"), null);
    assert.equal(w.document.activeElement, sectorCell(101));
});

test("setor: se a lista chega depois de o pop-over ser fechado, nada é desenhado; falha na lista avisa e fecha", async t => {
    const gate = deferred();
    const slow = setup(t, {respond: call => call.url.includes("/inline/opcoes/") ? gate.promise.then(() => sectorOptions()) : null});
    slow.click(slow.sectorCell(101));
    slow.key(slow.w.document, "Escape");
    gate.resolve();
    await flush();
    assert.equal(slow.$(".activity-inline-popover"), null);

    const failing = setup(t, {respond: call => call.url.includes("/inline/opcoes/") ? jsonResponse({ok: false, error: "Você não tem permissão para fazer isso."}, 403) : null});
    failing.click(failing.sectorCell(101));
    await flush();
    assert.equal(failing.$(".activity-inline-popover"), null);
    assert.deepEqual(failing.toasts(), ["Você não tem permissão para fazer isso."]);
});

test("setor: '+ Novo setor' só aparece para quem pode criar", async t => {
    const withCreate = setup(t);
    withCreate.click(withCreate.sectorCell(101));
    await flush();
    assert.match(withCreate.$(".activity-inline-popover__more").textContent, /Novo setor/);

    const without = setup(t, {respond: call => call.url.includes("/inline/opcoes/") ? sectorOptions({can_create: false}) : null});
    without.click(without.sectorCell(101));
    await flush();
    assert.equal(without.$(".activity-inline-popover__more"), null);
});

test("setor: criar um setor novo no pop-over (nome + cor) grava e aplica numa única requisição, sem janela", async t => {
    const {click, sectorCell, stageCell, conditionCell, saves, chip, toasts, w, $, $$} = setup(t);
    click(sectorCell(101));
    await flush();
    click($(".activity-inline-popover__more"));
    const name = $(".activity-inline-popover input[type=text]");
    assert.ok(name, "o formulário abre no próprio pop-over");
    assert.equal(w.document.activeElement, name);
    assert.equal($$(".modal, .modal-backdrop").length, 0, "nenhuma janela");
    assert.equal($$(".activity-inline-swatch").length, 36, "as 36 cores da paleta oficial");
    assert.equal($(".activity-inline-swatch[aria-checked=true]").dataset.hex, "#3B82F6");
    name.value = "  Qualidade 2  ";
    name.dispatchEvent(new w.Event("input", {bubbles: true}));
    assert.equal($(".activity-inline-preview").textContent, "Qualidade 2");
    click($$(".activity-inline-swatch").find(s => s.dataset.hex === "#16A34A"));
    assert.equal($(".activity-inline-swatch[aria-checked=true]").dataset.hex, "#16A34A");
    assert.match($(".activity-inline-preview").getAttribute("style"), /background:#16A34A/);
    click($$(".activity-inline-popover button").find(b => /Criar e aplicar/.test(b.textContent)));
    assert.equal(saves().length, 1);
    assert.equal(saves()[0].body.get("field"), "sector");
    assert.equal(saves()[0].body.get("new_name"), "Qualidade 2");
    assert.equal(saves()[0].body.get("new_color"), "#16A34A");
    assert.equal(saves()[0].body.get("value"), null);
    await flush();
    assert.equal($(".activity-inline-popover"), null, "fecha ao concluir");
    assert.equal(sectorCell(101).querySelector(".sector-badge").textContent, "Qualidade 2");
    assert.equal(sectorCell(101).querySelector(".sector-badge").dataset.sectorId, "9");
    // setor novo nasce sem etapas e sem condições: as células mostram os rótulos neutros
    assert.equal(chip(stageCell(101)).textContent, "Sem estágio");
    assert.equal(chip(conditionCell(101)).textContent, "Sem condição");
    assert.match(chip(stageCell(101)).getAttribute("style"), /--status-bg:#94A3B8;--status-text:#FFFFFF;/);
    assert.equal(stageCell(101).dataset.optionId, "");
    assert.deepEqual(toasts(), []);
});

test("setor: criar com o nome vazio mostra o erro no pop-over e não envia; Voltar mostra a lista de novo", async t => {
    const {click, sectorCell, saves, optionButtons, w, $, $$} = setup(t);
    click(sectorCell(101));
    await flush();
    click($(".activity-inline-popover__more"));
    click($$(".activity-inline-popover button").find(b => /Criar e aplicar/.test(b.textContent)));
    assert.equal(saves().length, 0);
    assert.match($(".activity-inline-popover__error").textContent, /Informe o nome do setor/);
    assert.equal($(".activity-inline-popover__error").hidden, false);
    assert.equal(w.document.activeElement, $(".activity-inline-popover input[type=text]"));
    click($$(".activity-inline-popover button").find(b => b.textContent === "Voltar"));
    assert.equal(optionButtons().length, 3);
});

test("setor: erro ao criar (nome repetido, sem permissão) fica no pop-over, devolve o selo e libera o formulário", async t => {
    const {click, sectorCell, stageCell, saves, chip, toasts, w, $, $$} = setup(t, {
        respond: call => call.url.endsWith("/inline/") ? jsonResponse({ok: false, error: "Já existe um registro com o nome “Qualidade” nesta organização."}, 400) : null,
    });
    click(sectorCell(101));
    await flush();
    click($(".activity-inline-popover__more"));
    const name = $(".activity-inline-popover input[type=text]");
    name.value = "Qualidade";
    const create = $$(".activity-inline-popover button").find(b => /Criar e aplicar/.test(b.textContent));
    click(create);
    assert.equal(name.disabled, true, "formulário travado enquanto grava");
    await flush();
    assert.equal(saves().length, 1);
    assert.ok($(".activity-inline-popover"), "o pop-over continua aberto");
    assert.match($(".activity-inline-popover__error").textContent, /Já existe um registro/);
    assert.equal(name.disabled, false);
    assert.equal(create.disabled, false);
    assert.equal(w.document.activeElement, name);
    name.value = "Qualidade 2";
    name.dispatchEvent(new w.Event("input", {bubbles: true}));
    assert.equal($(".activity-inline-popover__error").hidden, true, "a mensagem some quando a pessoa corrige o nome");
    assert.equal(sectorCell(101).querySelector(".sector-badge").textContent, "Comercial", "voltou ao setor confirmado");
    assert.equal(chip(stageCell(101)).textContent, "Orçamento");
    assert.deepEqual(toasts(), [], "o erro foi mostrado no pop-over, sem aviso duplicado");
});

test("setor: Enter no nome cria; clicar fora com o formulário aberto fecha sem enviar", async t => {
    const {click, key, sectorCell, saves, w, $} = setup(t);
    click(sectorCell(101));
    await flush();
    click($(".activity-inline-popover__more"));
    $(".activity-inline-popover input[type=text]").value = "Novo";
    key($(".activity-inline-popover input[type=text]"), "Enter");
    assert.equal(saves().length, 1);
    await flush();

    click(sectorCell(105));
    await flush();
    click($(".activity-inline-popover__more"));
    w.document.body.dispatchEvent(new w.MouseEvent("mousedown", {bubbles: true}));
    assert.equal($(".activity-inline-popover"), null);
    assert.equal(saves().length, 1);
});

test("setor: demanda sem setor mostra 'Sem setor', abre a lista sem marcar nenhum e escolher define o setor", async t => {
    const {click, sectorCell, optionButtons, stageCell, chip, saves, $$} = setup(t, {
        respond: call => call.url.includes("/inline/opcoes/") ? sectorOptions({current_id: null}) : null,
    });
    click(sectorCell(105));
    await flush();
    assert.equal($$(".activity-inline-popover [aria-current]").length, 0);
    click(optionButtons()[1]);
    assert.equal(saves()[0].body.get("value"), "2");
    await flush();
    assert.equal(sectorCell(105).querySelector(".sector-badge").textContent, "Engenharia");
    assert.equal(chip(stageCell(105)).textContent, "Projeto");
});


// ---------------------------------------------------------------------------------------------------
// Entrega 2C: Estágio e Status (escolher, criar e editar opções) e a linha "Vencida há N dias"
// ---------------------------------------------------------------------------------------------------

const lateLine = (chipNode) => chipNode.querySelector(".demand-board__status-late");
const buttonByText = ($$, text) => $$(".activity-inline-popover button").find(b => b.textContent === text);

test("estágio e status: marcadores só onde a linha permite; em repouso a célula só ganha dados (nada visível)", t => {
    const {$, $$, stageCell, conditionCell} = setup(t);
    for (const td of [stageCell(101), conditionCell(101)]) {
        assert.equal(td.getAttribute("role"), "button");
        assert.equal(td.getAttribute("tabindex"), "0");
        assert.ok(td.hasAttribute("data-inline-field"));
        assert.match(td.getAttribute("aria-label"), /Alterar o (estágio|status)/);
    }
    assert.equal(stageCell(103).hasAttribute("data-inline-field"), false, "linha travada");
    assert.equal(conditionCell(103).hasAttribute("data-inline-field"), false);
    assert.equal($$("[data-activity-list] button, [data-activity-list] input").length, 0);
    assert.equal(lateLine(stageCell(101).querySelector(".demand-board__status")), null);
    assert.equal(conditionCell(101).querySelector(".demand-board__status").classList.contains("has-late"), false);
    assert.equal(conditionCell(101).querySelector(".demand-board__status-name").textContent, "Normal");
    assert.ok($("[data-options-url]"));
});

test("estágio: o pop-over lista os estágios do setor da demanda, com cor, o atual marcado e sem 'limpar'", async t => {
    const {click, stageCell, optionCalls, optionButtons} = setup(t);
    click(stageCell(101));
    await flush();
    assert.equal(optionCalls()[0].url, "/demandas/101/inline/opcoes/?campo=stage");
    const buttons = optionButtons();
    assert.deepEqual(buttons.map(b => b.querySelector(".activity-inline-color-option__name").textContent), ["Orçamento", "Projeto", "Execução"]);
    assert.match(buttons[1].getAttribute("style"), /--option-bg:#22C55E;--option-text:#1F2937/);
    assert.equal(buttons[0].getAttribute("aria-current"), "true");
    assert.equal(buttons.length, 3, "estágio não é limpável");
});

test("estágio: escolher grava (campo + id), mostra na hora e usa a cor e o texto que o servidor devolve; ninguém é travado à toa", async t => {
    const {click, stageCell, conditionCell, saves, optionButtons, chip, toasts} = setup(t);
    click(stageCell(101));
    await flush();
    click(optionButtons()[1]);
    assert.equal(saves()[0].body.get("field"), "stage");
    assert.equal(saves()[0].body.get("value"), "32");
    assert.equal(chip(stageCell(101)).textContent, "Projeto", "otimista");
    assert.ok(stageCell(101).classList.contains("is-saving"));
    assert.equal(conditionCell(101).classList.contains("is-saving"), false, "só a própria célula");
    await flush();
    assert.match(chip(stageCell(101)).getAttribute("style"), /--status-bg:#22C55E;--status-text:#1F2937;/);
    assert.equal(stageCell(101).dataset.optionId, "32");
    assert.equal(stageCell(101).classList.contains("is-saving"), false);
    assert.deepEqual(toasts(), []);
    assert.equal(chip(stageCell(102)).textContent, "Orçamento", "outras linhas intactas");
});

test("estágio: recusa do servidor volta ao estágio confirmado e avisa", async t => {
    const {click, stageCell, optionButtons, chip, toasts} = setup(t, {
        respond: call => call.url.endsWith("/inline/") ? jsonResponse({ok: false, error: "Não é possível alterar o estágio de uma demanda concluída ou cancelada."}, 400) : null,
    });
    click(stageCell(101));
    await flush();
    click(optionButtons()[2]);
    await flush();
    assert.equal(chip(stageCell(101)).textContent, "Orçamento");
    assert.equal(stageCell(101).dataset.optionId, "31");
    assert.deepEqual(toasts(), ["Não é possível alterar o estágio de uma demanda concluída ou cancelada."]);
    assert.ok(stageCell(101).classList.contains("is-error"));
});

test("status: a lista tem 'Sem condição' no topo (marcada quando não há valor), escolher grava e limpar manda vazio", async t => {
    const {click, conditionCell, optionButtons, saves, chip, toasts} = setup(t);
    click(conditionCell(101));
    await flush();
    const buttons = optionButtons();
    assert.deepEqual(buttons.map(b => b.querySelector(".activity-inline-color-option__name").textContent), ["Sem condição", "Normal", "Em análise"]);
    assert.equal(buttons[0].hasAttribute("aria-current"), false);
    assert.equal(buttons[1].getAttribute("aria-current"), "true");
    click(buttons[2]);
    await flush();
    assert.equal(saves()[0].body.get("field"), "condition");
    assert.equal(saves()[0].body.get("value"), "42");
    assert.equal(chip(conditionCell(101)).textContent, "Em análise");
    assert.match(chip(conditionCell(101)).getAttribute("style"), /--status-bg:#F59E0B;--status-text:#1F2937;/);

    click(conditionCell(101));
    await flush();
    click(optionButtons()[0]); // Sem condição
    assert.equal(saves()[1].body.get("value"), "");
    assert.equal(chip(conditionCell(101)).textContent, "Sem condição", "otimista");
    await flush();
    assert.equal(conditionCell(101).dataset.optionId, "");
    assert.match(chip(conditionCell(101)).getAttribute("style"), /--status-bg:#94A3B8;--status-text:#FFFFFF;/);
    click(conditionCell(101));
    await flush();
    assert.equal(optionButtons()[0].getAttribute("aria-current"), "true", "agora o 'Sem condição' é o atual");
    click(optionButtons()[0]);
    assert.equal(saves().length, 2, "escolher o que já está não envia");
    assert.deepEqual(toasts(), []);
});

test("estágio: '+ Novo estágio' cria a opção no setor da demanda e a aplica, em duas chamadas, sem janela", async t => {
    const {click, stageCell, calls, saves, chip, toasts, w, $, $$} = setup(t);
    click(stageCell(101));
    await flush();
    click($(".activity-inline-popover__more"));
    const name = $(".activity-inline-popover input[type=text]");
    assert.equal(w.document.activeElement, name);
    assert.equal($$(".modal, .modal-backdrop").length, 0);
    assert.equal($(".activity-inline-swatch[aria-checked=true]").dataset.hex, "#94A3B8", "cor neutra por padrão");
    name.value = "  Revisão final ";
    name.dispatchEvent(new w.Event("input", {bubbles: true}));
    click($$(".activity-inline-swatch").find(s => s.dataset.hex === "#9333EA"));
    click(buttonByText($$, "Criar e aplicar"));
    await flush();
    const optionPost = calls.find(call => call.method === "POST" && call.url.includes("/inline/opcoes/"));
    assert.ok(optionPost);
    assert.equal(optionPost.url, "/demandas/101/inline/opcoes/");
    assert.equal(optionPost.headers["X-CSRFToken"], "tok123");
    assert.deepEqual([...optionPost.body.entries()].sort(), [["acao", "criar"], ["campo", "stage"], ["color", "#9333EA"], ["name", "Revisão final"]]);
    assert.equal(saves().length, 1, "depois de criar, aplica pelo caminho normal");
    assert.equal(saves()[0].body.get("field"), "stage");
    assert.equal(saves()[0].body.get("value"), "50");
    assert.equal($(".activity-inline-popover"), null);
    assert.equal(chip(stageCell(101)).textContent, "Revisão final");
    assert.equal(stageCell(101).dataset.optionId, "50");
    assert.deepEqual(toasts(), []);
});

test("status: criar usa os textos de status e a opção nova entra na célula", async t => {
    const {click, conditionCell, chip, $, $$, w} = setup(t);
    click(conditionCell(101));
    await flush();
    assert.match($(".activity-inline-popover__more").textContent, /Novo status/);
    click($(".activity-inline-popover__more"));
    assert.equal($(".activity-inline-popover input[type=text]").getAttribute("placeholder"), "Nome do status");
    $(".activity-inline-popover input[type=text]").value = "Bloqueada";
    click(buttonByText($$, "Criar e aplicar"));
    await flush();
    assert.equal(chip(conditionCell(101)).textContent, "Bloqueada");
    assert.equal(conditionCell(101).dataset.optionId, "50");
});

test("criar opção: nome repetido (400) fica no pop-over, sem aplicar e sem aviso duplicado; vazio nem envia", async t => {
    const {click, stageCell, calls, saves, toasts, chip, w, $, $$} = setup(t, {
        respond: call => call.method === "POST" && call.url.includes("/inline/opcoes/") ? jsonResponse({ok: false, error: "Já existe uma opção com o nome “Projeto” neste setor."}, 400) : null,
    });
    click(stageCell(101));
    await flush();
    click($(".activity-inline-popover__more"));
    click(buttonByText($$, "Criar e aplicar"));
    assert.match($(".activity-inline-popover__error").textContent, /Informe o nome/);
    assert.equal(calls.filter(c => c.method === "POST").length, 0);
    const name = $(".activity-inline-popover input[type=text]");
    name.value = "Projeto";
    click(buttonByText($$, "Criar e aplicar"));
    assert.equal(name.disabled, true);
    await flush();
    assert.match($(".activity-inline-popover__error").textContent, /Já existe uma opção/);
    assert.equal(name.disabled, false);
    assert.equal(saves().length, 0);
    assert.equal(chip(stageCell(101)).textContent, "Orçamento");
    assert.deepEqual(toasts(), []);
});

test("criar opção: se a opção foi criada mas aplicá-la falha, a lista é recarregada (já com ela) e o erro aparece", async t => {
    const {click, stageCell, optionCalls, optionButtons, toasts, chip, $, $$} = setup(t, {
        respond: call => call.url.endsWith("/inline/") ? jsonResponse({ok: false, error: "Você não possui autorização para: definir etapa da demanda."}, 403) : null,
    });
    click(stageCell(101));
    await flush();
    click($(".activity-inline-popover__more"));
    $(".activity-inline-popover input[type=text]").value = "Nova";
    click(buttonByText($$, "Criar e aplicar"));
    await flush();
    assert.equal(optionCalls().filter(c => c.method === "GET").length, 2, "a lista foi pedida de novo");
    assert.ok($(".activity-inline-popover"), "continua aberto");
    assert.equal(optionButtons().length, 3);
    assert.deepEqual(toasts(), ["Você não possui autorização para: definir etapa da demanda."]);
    assert.equal(chip(stageCell(101)).textContent, "Orçamento");
});

test("opções: 'Editar estágios' e 'Gerenciar' só aparecem para quem gere; o link é só do próprio site", async t => {
    const manager = setup(t);
    manager.click(manager.stageCell(101));
    await flush();
    const labels = manager.$$(".activity-inline-popover__tail button").map(b => b.textContent);
    assert.deepEqual(labels, ["+ Novo estágio", "Editar estágios"]);
    const link = manager.$(".activity-inline-popover__tail a");
    assert.equal(link.getAttribute("href"), "/configuracoes/etapas-status/?domain=demandas&sector=1");

    const plain = setup(t, {respond: call => call.url.includes("/inline/opcoes/") ? optionOptions("stage", {can_create: false, can_manage: false, manage_url: ""}) : null});
    plain.click(plain.stageCell(101));
    await flush();
    assert.equal(plain.$(".activity-inline-popover__tail"), null);

    const hostile = setup(t, {respond: call => call.url.includes("/inline/opcoes/") ? optionOptions("stage", {manage_url: "javascript:alert(1)"}) : null});
    hostile.click(hostile.stageCell(101));
    await flush();
    assert.equal(hostile.$$(".activity-inline-popover__tail a").length, 0);
});

test("opções: editar nome e cor ali mesmo, com propagação para todas as linhas que mostram a mesma opção", async t => {
    const {click, stageCell, calls, chip, toasts, w, $, $$} = setup(t);
    click(stageCell(101));
    await flush();
    click(buttonByText($$, "Editar estágios"));
    const inputs = $$(".activity-inline-edit-row input[type=text]");
    assert.deepEqual(inputs.map(i => i.value), ["Orçamento", "Projeto", "Execução"]);
    const saveButtons = $$(".activity-inline-edit-row .btn");
    assert.equal(saveButtons.every(b => b.disabled), true, "nada a salvar sem mudança");
    inputs[0].value = "Orçamento v2";
    inputs[0].dispatchEvent(new w.Event("input", {bubbles: true}));
    assert.equal(saveButtons[0].disabled, false);
    click($$(".activity-inline-edit-dot")[0]);
    const grid = $$(".activity-inline-edit-row .activity-inline-swatches")[0];
    assert.equal(grid.hidden, false);
    click([...grid.querySelectorAll(".activity-inline-swatch")].find(s => s.dataset.hex === "#16A34A"));
    assert.match($$(".activity-inline-edit-dot")[0].getAttribute("style"), /background:#16A34A/);
    click(saveButtons[0]);
    await flush();
    const post = calls.find(call => call.method === "POST");
    assert.deepEqual([...post.body.entries()].sort(), [["acao", "editar"], ["campo", "stage"], ["color", "#16A34A"], ["name", "Orçamento v2"], ["option_id", "31"]]);
    assert.equal(saveButtons[0].textContent, "Salvo ✓");
    assert.equal(saveButtons[0].disabled, true);
    // a opção editada aparece nas DUAS linhas que a usam (101 e 102) e na 106, sem recarregar
    for (const id of [101, 102, 106]) {
        assert.equal(chip(stageCell(id)).textContent, "Orçamento v2", String(id));
        assert.match(chip(stageCell(id)).getAttribute("style"), /--status-bg:#16A34A;/, String(id));
    }
    assert.equal(stageCell(101).dataset.optionId, "31");
    assert.deepEqual(toasts(), []);
    // Concluir volta à lista já com o nome novo
    click(buttonByText($$, "Concluir"));
    assert.ok($$(".activity-inline-popover .activity-inline-color-option__name").some(n => n.textContent === "Orçamento v2"));
});

test("opções: editar com nome vazio ou recusado mostra o erro na linha e não troca nada na tela", async t => {
    const {click, stageCell, chip, toasts, w, $, $$} = setup(t, {
        respond: call => call.method === "POST" && call.url.includes("/inline/opcoes/") ? jsonResponse({ok: false, error: "Já existe uma opção com o nome “Projeto” neste setor."}, 400) : null,
    });
    click(stageCell(101));
    await flush();
    click(buttonByText($$, "Editar estágios"));
    const first = $$(".activity-inline-edit-row input[type=text]")[0];
    first.value = "   ";
    first.dispatchEvent(new w.Event("input", {bubbles: true}));
    click($$(".activity-inline-edit-row .btn")[0]);
    assert.match($(".activity-inline-edit-row .activity-inline-popover__error").textContent, /Informe o nome/);
    first.value = "Projeto";
    first.dispatchEvent(new w.Event("input", {bubbles: true}));
    click($$(".activity-inline-edit-row .btn")[0]);
    assert.equal(first.disabled, true);
    await flush();
    assert.match($(".activity-inline-edit-row .activity-inline-popover__error").textContent, /Já existe uma opção/);
    assert.equal(first.disabled, false);
    assert.equal(chip(stageCell(101)).textContent, "Orçamento");
    assert.deepEqual(toasts(), []);
});

test("atraso: a segunda linha 'Vencida há N dias' vem do servidor para todos e some quando a demanda não está vencida", t => {
    const {conditionCell, chip} = setup(t);
    const late = chip(conditionCell(106));
    assert.ok(late.classList.contains("has-late"));
    assert.equal(lateLine(late).textContent, "Vencida há 3 dias");
    assert.equal(late.querySelector(".demand-board__status-name").textContent, "Normal");
    assert.equal(late.getAttribute("title"), "Normal · Vencida há 3 dias");
    assert.equal(lateLine(chip(conditionCell(101))), null);
});

test("atraso: mudar o prazo ali mesmo liga, atualiza e desliga a segunda linha do Status (usa a resposta do servidor)", async t => {
    let answer = {is_late: true, days: 3};
    const {click, cell, conditionCell, chip, $, $$} = setup(t, {
        respond: call => call.url.endsWith("/inline/") && call.body.get("field") === "requested_deadline"
            ? jsonResponse({ok: true, field: "requested_deadline", value: {date: call.body.get("date"), time: ""}, display: {text: "x", is_late: answer.is_late}, derived: {overdue_days: answer.days}})
            : null,
    });
    const apply = async (id, date) => {
        click(cell(id, "requested_deadline"));
        $(".activity-inline-popover input[type=date]").value = date;
        click($$(".activity-inline-popover button").find(b => b.textContent === "Aplicar"));
        await flush();
    };
    await apply(101, "2026-10-01");
    assert.equal(lateLine(chip(conditionCell(101))).textContent, "Vencida há 3 dias");
    assert.ok(chip(conditionCell(101)).classList.contains("has-late"));
    answer = {is_late: true, days: 1};
    await apply(101, "2026-10-09");
    assert.equal(lateLine(chip(conditionCell(101))).textContent, "Vencida há 1 dia", "singular");
    assert.equal(chip(conditionCell(101)).querySelectorAll(".demand-board__status-late").length, 1, "uma só linha");
    answer = {is_late: false, days: 0};
    await apply(101, "2026-12-01");
    assert.equal(lateLine(chip(conditionCell(101))), null);
    assert.equal(chip(conditionCell(101)).classList.contains("has-late"), false);
    assert.equal(chip(conditionCell(101)).hasAttribute("title"), false);
    // a linha 106 (já vencida) deixa de estar vencida ao ganhar um prazo futuro
    await apply(106, "2026-12-01");
    assert.equal(lateLine(chip(conditionCell(106))), null);
});

test("atraso: trocar o status mantém a segunda linha e o título completo", async t => {
    const {click, conditionCell, optionButtons, chip} = setup(t);
    click(conditionCell(106));
    await flush();
    click(optionButtons()[2]); // Em análise
    await flush();
    const late = chip(conditionCell(106));
    assert.equal(late.querySelector(".demand-board__status-name").textContent, "Em análise");
    assert.equal(lateLine(late).textContent, "Vencida há 3 dias");
    assert.equal(late.getAttribute("title"), "Em análise · Vencida há 3 dias");
    assert.ok(late.classList.contains("has-late"));
});

test("setor: trocar de setor redesenha o Status preservando a linha de atraso", async t => {
    const {click, sectorCell, conditionCell, optionButtons, chip} = setup(t);
    click(sectorCell(106));
    await flush();
    click(optionButtons()[1]);
    await flush();
    const late = chip(conditionCell(106));
    assert.equal(late.querySelector(".demand-board__status-name").textContent, "Em análise");
    assert.equal(lateLine(late).textContent, "Vencida há 3 dias");
});

test("estágio e status: sem conflito entre as duas células: gravar uma não trava a outra e cada uma tem a sua revisão", async t => {
    const gate = deferred();
    const {click, stageCell, conditionCell, optionButtons, saves} = setup(t, {
        respond: call => call.url.endsWith("/inline/") && call.body.get("field") === "stage" ? gate.promise.then(() => defaultRespond(call)) : null,
    });
    click(stageCell(101));
    await flush();
    click(optionButtons()[1]);
    click(conditionCell(101)); // a outra célula continua livre
    await flush();
    click(optionButtons()[2]);
    await flush();
    assert.equal(saves().length, 2);
    gate.resolve();
    await flush();
    assert.equal(stageCell(101).classList.contains("is-saving"), false);
    assert.equal(conditionCell(101).classList.contains("is-saving"), false);
});
