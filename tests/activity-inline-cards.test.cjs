/* Editar os campos no próprio cartão do Kanban de Demandas: activity-inline-edit.js e activity-inline-options.js (os MESMOS da Lista)
   reconhecem o Kanban pela raiz `[data-kanban]`; kanban-core.js e demand-kanban.js completam (versão do cartão, redesenho das raias).
   Requires jsdom@26.1.0 in NODE_PATH. Run from workflow: node --test tests/activity-inline-cards.test.cjs

   A marcação vem do construtor REAL (boards/demand_kanban.py) renderizado pelo kit REAL (templates/kanban/*), sem banco; o servidor é
   um `fetch` falso. O que se prova: o que o cartão oferece como editável, o que ele ENVIA, como se redesenha (otimista, depois o que o
   servidor confirma), o que acontece quando o servidor recusa e quando o campo muda a raia do cartão. */
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
from types import SimpleNamespace as NS
from django.template.loader import render_to_string
from boards.demand_kanban import build_demand_kanban

UTC = datetime.timezone.utc
PAULO = NS(pk=6, get_full_name=lambda: 'Paulo Souza', get_username=lambda: 'paulo')
COMERCIAL = NS(pk=1, name='Comercial', color='#FACC15', text_color='#1F2937')
PROPOSTA = NS(pk=10, name='Proposta', color='#3B82F6', text_color='#FFFFFF', sector_id=1)
NEGOCIACAO = NS(pk=11, name='Negociação', color='#F59E0B', text_color='#1F2937', sector_id=1)
NORMAL = NS(pk=30, name='Normal', color='#94A3B8', text_color='#FFFFFF')

def cell(key, label, **extra):
    base = {'field': NS(label=label), 'key': key, 'raw': '', 'text': ''}
    base.update(extra)
    return base

def item(pk, title, flags=True, stage=PROPOSTA, deadline=None, late=False, owner=PAULO):
    inline = {'title': flags, 'owner': flags, 'sector': flags, 'stage': flags, 'condition': flags, 'urgency': flags, 'requested_deadline': flags,
              'client': flags, 'locked': False, 'deadline_date': deadline.strftime('%Y-%m-%d') if deadline else '', 'deadline_time': ''}
    return NS(pk=pk, title=title, code='DEM-2026-%05d' % pk, sector_id=1, status='ABERTA', can_move_kanban=flags, inline=inline,
              is_overdue=late, updated_at=datetime.datetime(2026, 10, 3, 10, 0, tzinfo=UTC), work_cells=[
        cell('owner', 'Responsável', raw=owner.pk if owner else '', text='Paulo Souza' if owner else 'Sem responsável', person=owner),
        cell('sector', 'Setor', raw=1, text='Comercial', sector=COMERCIAL),
        cell('urgency', 'Prioridade', raw='MEDIA', text='Média', color='#F59E0B'),
        cell('requested_deadline', 'Prazo', raw='', text='', deadline=deadline),
        cell('stage', 'Status', raw=stage.pk, text=stage.name, choice=stage),
        cell('condition', 'Status', raw=30, text='Normal', choice=NORMAL),
    ])

def render(groups, group_by='stage'):
    kanban = build_demand_kanban(groups=groups, group_by=group_by, sectors_by_id={1: 'Comercial'}, show_field_names=False,
                                 can_create=True, create_url='/demandas/nova/', return_url='/demandas/kanban/', can_rename=True)
    return render_to_string('kanban/_lanes.html', {'kanban': kanban})

def group(key, label, items=(), **extra):
    return {'key': key, 'label': label, 'color': '#3B82F6', 'items': list(items), **extra}

from django.utils import timezone
LATE = timezone.make_aware(datetime.datetime(2026, 9, 20, 23, 59))  # 23:59 LOCAL = prazo só com data
stage = render([
    group('empty', 'Sem estágio'),
    group(10, 'Proposta', [item(1, 'Orçamento Aurora', deadline=LATE, late=True), item(2, 'Sem permissão', flags=False), item(3, 'Sem prazo nem dono', owner=None)], sector_id=1),
    group(11, 'Negociação', [], sector_id=1),
], 'stage')
print(json.dumps({'stage': stage}))
`], {cwd: root, encoding: "utf8"}).trim());

const scripts = ["kanban-core.js", "activity-inline-edit.js", "activity-inline-options.js", "demand-kanban.js"].map((name) => readFileSync(path.join(root, "static/js", name), "utf8"));

function response(status, body) {
    return Promise.resolve({
        ok: status >= 200 && status < 300, status, redirected: false,
        json: typeof body === "string" ? () => Promise.reject(new SyntaxError("não é JSON")) : () => Promise.resolve(body),
        text: () => Promise.resolve(typeof body === "string" ? body : JSON.stringify(body)),
    });
}

const URLS = {
    inline: "/demandas/999999999/inline/", options: "/demandas/999999999/inline/opcoes/", people: "/api/pessoas/",
};

function setup(t, {groupBy = "stage", handler, html = fixtures.stage} = {}) {
    const dom = new JSDOM(`<!doctype html><body><div class="kanban-scroll" data-kanban data-group-by="${groupBy}" data-move-url="/quadros/dominio/3/campos/9/itens/0/valor/" data-rename-url="/quadros/dominio/3/campos/7/itens/0/valor/" data-inline-url="${URLS.inline}" data-inline-sentinel="999999999" data-people-url="${URLS.people}" data-options-url="${URLS.options}"><div class="kanban-lanes" data-kanban-lanes>${html}</div></div><div id="activity-inline-overlay-root"></div><div data-board-toasts></div></body>`,
        {url: "http://localhost/demandas/kanban/?tab=todas", runScripts: "outside-only", pretendToBeVisual: true});
    t.after(() => dom.window.close());
    const {window} = dom;
    const {document} = window;
    document.cookie = "csrftoken=tok";
    const requests = [];
    window.fetch = (url, options = {}) => {
        const body = options.body;
        requests.push({
            url, method: options.method || "GET", headers: options.headers || {},
            form: body && typeof body.get === "function" ? Object.fromEntries([...body.entries()]) : null,
            json: typeof body === "string" ? JSON.parse(body) : null,
        });
        return Promise.resolve().then(() => handler(url, options, requests[requests.length - 1]));
    };
    scripts.forEach((script) => window.eval(script));
    if (!window.LPSInlineEdit.instance) window.LPSInlineEdit.boot();  // o módulo só se inicia sozinho enquanto o documento carrega
    const h = {
        window, document, requests,
        card: (id) => document.querySelector(`[data-card][data-item-id="${id}"]`),
        field: (id, name) => h.card(id).querySelector(`[data-inline-field="${name}"]`),
        model: (id, name) => JSON.parse(h.field(id, name).getAttribute("data-inline-model")),
        pop: () => document.querySelector(".activity-inline-popover"),
        lane: (key) => document.querySelector(`[data-lane][data-lane-key="${key}"]`),
        ids: (key) => [...h.lane(key).querySelectorAll("[data-card]")].map((n) => n.dataset.itemId),
        toasts: () => [...document.querySelectorAll(".lps-toast, .board-toast")].map((n) => n.textContent),
        key: (node, name) => node.dispatchEvent(new window.KeyboardEvent("keydown", {key: name, bubbles: true, cancelable: true})),
        tick: () => new Promise((resolve) => setTimeout(resolve, 8)),
    };
    return h;
}

const ok = (extra = {}) => response(200, {ok: true, ...extra});
const display = (id, name, color, text) => ({id, name, color, text_color: text});

// -- o que o cartão oferece ---------------------------------------------------------------------------------------------

test("os campos que a pessoa pode editar vêm como editáveis, com o gancho e o modelo; os outros não", (t) => {
    const h = setup(t, {handler: () => ok()});
    for (const name of ["owner", "sector", "urgency", "requested_deadline", "stage", "condition"]) {
        const field = h.field(1, name);
        assert.ok(field, name);
        assert.equal(field.classList.contains("is-editable"), true, name);
        assert.equal(field.getAttribute("tabindex"), "0", name);
    }
    assert.equal(h.card(2).querySelectorAll("[data-inline-field]").length, 0, "sem permissão: nenhum campo editável");
    assert.equal(h.card(2).querySelectorAll(".is-editable").length, 0);
    assert.deepEqual(h.model(1, "owner"), {value: "6", text: "Paulo Souza", initials: "", avatarClass: ""});
    assert.equal(h.model(1, "stage").name, "Proposta");
    assert.equal(h.field(1, "stage").dataset.optionId, "10");
    assert.deepEqual(h.model(1, "requested_deadline"), {date: "2026-09-20", time: "", text: "20/09/2026", isLate: true});
});

test("a edição inline reconhece o Kanban como superfície 'card' (e a Lista continua sendo 'table')", (t) => {
    const h = setup(t, {handler: () => ok()});
    assert.equal(h.window.LPSInlineEdit.instance.api.surface, "card");
    assert.ok(h.window.LPSInlineEdit.instance, "a instância existe: o boot achou [data-kanban][data-inline-url]");
});

// -- Responsável ---------------------------------------------------------------------------------------------------------

test("Responsável: abre a busca de pessoas, grava e redesenha o avatar no desenho do kit", async (t) => {
    const handler = (url, options, req) => {
        if (url.startsWith(URLS.people)) return ok({results: [{id: 7, name: "Maria Souza"}, {id: 6, name: "Paulo Souza"}]});
        return ok({field: "owner", value: 7, display: {text: "Maria Souza", initials: "MA", avatar_class: "avatar--1"}, updated_at: "2026-10-03T12:00:00+00:00"});
    };
    const h = setup(t, {handler});
    h.field(1, "owner").click();
    await h.tick();
    assert.ok(h.pop(), "o pop-over abre");
    const people = [...h.pop().querySelectorAll(".activity-inline-popover__option")];
    assert.deepEqual(people.map((n) => n.querySelector(".activity-inline-popover__name").textContent), ["Maria Souza", "Paulo Souza"]);
    people[0].click();
    await h.tick();
    const post = h.requests.find((r) => r.method === "POST");
    assert.equal(post.url, "/demandas/1/inline/");
    assert.deepEqual(post.form, {value: "7", field: "owner"});
    assert.equal(post.headers["X-CSRFToken"], "tok");
    const person = h.field(1, "owner").querySelector(".board-person");
    assert.equal(person.querySelector(".board-person__name").textContent, "Maria Souza");
    assert.equal(person.querySelector(".board-avatar").textContent, "MS", "as iniciais do kit: primeiro e último nome (não as 2 primeiras letras)");
    assert.equal(String(h.model(1, "owner").value), "7");
    assert.equal(h.card(1).getAttribute("data-updated-at"), "2026-10-03T12:00:00+00:00", "o cartão guarda a versão nova");
    assert.equal(h.requests.filter((r) => r.url.includes("fragmento")).length, 0, "agrupado por etapa: mudar o responsável não muda a raia");
});

test("Responsável: sem responsável mostra o avatar vazio com o texto para leitor de tela", async (t) => {
    const h = setup(t, {handler: (url) => (url.startsWith(URLS.people) ? ok({results: [{id: 7, name: "Maria Souza"}]}) : ok({field: "owner", value: "", display: {text: "Sem responsável", initials: "", avatar_class: ""}}))});
    assert.ok(h.field(3, "owner").querySelector(".board-person--empty"));
    assert.equal(h.field(3, "owner").querySelector(".sr-only").textContent, "Sem responsável");
});

// -- Prazo ------------------------------------------------------------------------------------------------------------

test("Prazo: grava data e hora e o atraso é um selo na data (nunca o fundo)", async (t) => {
    const h = setup(t, {handler: (url, options, req) => ok({field: "requested_deadline", value: {date: "2099-01-05", time: "17:30"}, display: {text: "05/01/2099 17:30", is_late: false}, derived: {overdue_days: 0}, updated_at: "2026-10-03T12:30:00+00:00"})});
    assert.ok(h.field(1, "requested_deadline").querySelector(".board-date.is-overdue .board-date__flag"), "hoje o prazo está vencido: selo");
    h.field(1, "requested_deadline").click();
    const [date, time] = h.pop().querySelectorAll("input");
    assert.equal(date.value, "2026-09-20", "o editor abre com o prazo atual");
    date.value = "2099-01-05";
    time.value = "17:30";
    h.pop().querySelector(".btn--primary").click();
    await h.tick();
    const post = h.requests.find((r) => r.method === "POST");
    assert.deepEqual(post.form, {date: "2099-01-05", time: "17:30", field: "requested_deadline"});
    const span = h.field(1, "requested_deadline").querySelector(".board-date");
    assert.equal(span.textContent.trim(), "05/01/2099 17:30");
    assert.equal(span.classList.contains("is-overdue"), false);
    assert.equal(h.field(1, "requested_deadline").querySelector(".board-date__flag"), null, "o selo some quando deixa de estar vencido");
    assert.equal(h.card(1).classList.contains("is-late"), false, "o cartão nunca ganha classe de atraso");
});

test("Prazo: limpar mostra o traço, e o servidor pode dizer que continua vencido", async (t) => {
    const h = setup(t, {handler: () => ok({field: "requested_deadline", value: {date: "", time: ""}, display: {text: "Sem prazo", is_late: false}, derived: {overdue_days: 0}})});
    h.field(1, "requested_deadline").click();
    [...h.pop().querySelectorAll("button")].find((n) => n.textContent === "Limpar").click();
    await h.tick();
    assert.equal(h.field(1, "requested_deadline").querySelector(".board-empty").textContent, "—");
    const late = setup(t, {handler: () => ok({field: "requested_deadline", value: {date: "2020-01-01", time: ""}, display: {text: "01/01/2020", is_late: true}, derived: {overdue_days: 2000}})});
    late.field(3, "requested_deadline").click();
    late.pop().querySelectorAll("input")[0].value = "2020-01-01";
    late.pop().querySelector(".btn--primary").click();
    await late.tick();
    assert.ok(late.field(3, "requested_deadline").querySelector(".board-date.is-overdue .board-date__flag"));
});

// -- Prioridade, Etapa, Status e Setor (as opções) ------------------------------------------------------------------------

test("Prioridade: lista as três, grava e redesenha a pílula com o contraste do kit", async (t) => {
    const items = [display("BAIXA", "Baixa", "#64748B", "#FFFFFF"), display("MEDIA", "Média", "#F59E0B", "#1F2937"), display("ALTA", "Alta", "#FACC15", "#1F2937")];
    const handler = (url) => (url.includes("opcoes")
        ? ok({field: "urgency", current_id: "MEDIA", allow_clear: false, can_create: false, can_manage: false, manage_url: "", items})
        : ok({field: "urgency", value: "ALTA", display: items[2], updated_at: "2026-10-03T12:10:00+00:00"}));
    const h = setup(t, {handler});
    h.field(1, "urgency").click();
    await h.tick();
    const options = [...h.pop().querySelectorAll(".activity-inline-color-option")];
    assert.deepEqual(options.map((n) => n.textContent.replace("✓", "")), ["Baixa", "Média", "Alta"]);
    assert.equal(h.requests[0].url, "/demandas/1/inline/opcoes/?campo=urgency");
    assert.equal(h.pop().querySelector(".activity-inline-popover__more"), null, "as prioridades são fixas: sem criar nem editar");
    options[2].click();
    await h.tick();
    assert.deepEqual(h.requests.find((r) => r.method === "POST").form, {value: "ALTA", field: "urgency"});
    const pill = h.field(1, "urgency").querySelector(".board-pill");
    assert.equal(pill.textContent, "Alta");
    assert.equal(pill.getAttribute("style"), "background:#FACC15;color:#1F2937", "amarelo: texto escuro (a fórmula do kit, a mesma do servidor)");
    assert.equal(h.field(1, "urgency").dataset.optionId, "ALTA");
});

test("Etapa agrupada por etapa: grava e pede as raias de novo (o cartão muda de raia)", async (t) => {
    const nego = display(11, "Negociação", "#F59E0B", "#1F2937");
    const moved = fixtures.stage.replace(/<article class="kanban-card"[^>]*data-item-id="1"[\s\S]*?<\/article>/, "");
    const handler = (url) => {
        if (url.includes("fragmento")) return response(200, moved);
        if (url.includes("opcoes")) return ok({field: "stage", current_id: 10, allow_clear: false, can_create: false, can_manage: false, items: [display(10, "Proposta", "#3B82F6", "#FFFFFF"), nego]});
        return ok({field: "stage", value: 11, display: nego, updated_at: "2026-10-03T12:20:00+00:00"});
    };
    const h = setup(t, {groupBy: "stage", handler});
    h.field(1, "stage").click();
    await h.tick();
    [...h.pop().querySelectorAll(".activity-inline-color-option")].find((n) => n.textContent.startsWith("Negociação")).click();
    await h.tick();
    await h.tick();
    assert.ok(h.requests.some((r) => r.url.includes("fragmento=raias")), "pediu as raias de novo");
    assert.equal(h.card(1), null, "o servidor redistribuiu: o cartão saiu desta lista");
});

test("Status agrupado por etapa: grava sem redesenhar (a raia não muda) e o selo atualiza no lugar", async (t) => {
    const aprov = display(31, "Aprovada", "#22C55E", "#FFFFFF");
    const handler = (url) => (url.includes("opcoes")
        ? ok({field: "condition", current_id: 30, allow_clear: true, can_create: false, can_manage: false, items: [display(30, "Normal", "#94A3B8", "#FFFFFF"), aprov]})
        : ok({field: "condition", value: 31, display: aprov}));
    const h = setup(t, {groupBy: "stage", handler});
    h.field(1, "condition").click();
    await h.tick();
    [...h.pop().querySelectorAll(".activity-inline-color-option")].find((n) => n.textContent.startsWith("Aprovada")).click();
    await h.tick();
    assert.equal(h.field(1, "condition").querySelector(".board-pill").textContent, "Aprovada");
    assert.equal(h.requests.some((r) => r.url.includes("fragmento")), false);
});

test("Status pode ser limpo: volta o traço", async (t) => {
    const handler = (url) => (url.includes("opcoes")
        ? ok({field: "condition", current_id: 30, allow_clear: true, can_create: false, can_manage: false, items: [display(30, "Normal", "#94A3B8", "#FFFFFF")]})
        : ok({field: "condition", value: "", display: null}));
    const h = setup(t, {handler});
    h.field(1, "condition").click();
    await h.tick();
    [...h.pop().querySelectorAll(".activity-inline-color-option")].find((n) => n.textContent.startsWith("Sem status")).click();
    await h.tick();
    assert.equal(h.field(1, "condition").querySelector(".board-empty").textContent, "—");
    assert.equal(h.field(1, "condition").dataset.optionId, "");
});

test("Setor: troca o selo, redefine Etapa e Status do mesmo cartão e (agrupado por etapa) pede as raias de novo", async (t) => {
    const fin = display(2, "Financeiro", "#16A34A", "#FFFFFF");
    const handler = (url) => {
        if (url.includes("fragmento")) return response(200, fixtures.stage);
        if (url.includes("opcoes")) return ok({field: "sector", current_id: 1, allow_clear: false, can_create: false, items: [display(1, "Comercial", "#FACC15", "#1F2937"), fin]});
        return ok({field: "sector", value: 2, display: fin, derived: {stage: display(20, "A fazer", "#64748B", "#FFFFFF"), condition: null}, updated_at: "2026-10-03T12:40:00+00:00"});
    };
    const h = setup(t, {groupBy: "stage", handler});
    h.field(1, "sector").click();
    await h.tick();
    [...h.pop().querySelectorAll(".activity-inline-color-option")].find((n) => n.textContent.startsWith("Financeiro")).click();
    await h.tick();
    await h.tick();
    assert.ok(h.requests.some((r) => r.url.includes("fragmento=raias")), "agrupado por etapa, trocar o setor muda a raia (as etapas são do setor)");
});

test("Setor sem redesenho (agrupado por responsável): o selo troca e Etapa e Status do MESMO cartão são redefinidos com o que o servidor devolve", async (t) => {
    const fin = display(2, "Financeiro", "#16A34A", "#FFFFFF");
    const handler = (url) => (url.includes("opcoes")
        ? ok({field: "sector", current_id: 1, allow_clear: false, can_create: false, items: [display(1, "Comercial", "#FACC15", "#1F2937"), fin]})
        : ok({field: "sector", value: 2, display: fin, derived: {stage: display(20, "A fazer", "#64748B", "#FFFFFF"), condition: null}, updated_at: "2026-10-03T12:40:00+00:00"}));
    const h = setup(t, {groupBy: "owner", handler});
    h.field(1, "sector").click();
    await h.tick();
    [...h.pop().querySelectorAll(".activity-inline-color-option")].find((n) => n.textContent.startsWith("Financeiro")).click();
    await h.tick();
    assert.equal(h.requests.some((r) => r.url.includes("fragmento")), false, "agrupado por responsável o cartão fica na mesma raia");
    const badge = h.field(1, "sector").querySelector(".sector-badge");
    assert.equal(badge.textContent, "Financeiro");
    assert.equal(badge.getAttribute("style"), "--sector-color: #16A34A; --sector-text-color: #FFFFFF;");
    assert.equal(badge.getAttribute("data-sector-id"), "2");
    assert.equal(h.field(1, "stage").querySelector(".board-pill").textContent, "A fazer", "a etapa passou para o padrão do setor novo");
    assert.equal(h.field(1, "condition").querySelector(".board-empty").textContent, "—", "o setor novo não tem status padrão");
    assert.equal(h.card(1).getAttribute("data-updated-at"), "2026-10-03T12:40:00+00:00");
});

test("Setor agrupado por setor: o campo editado É o agrupamento, então as raias vêm do servidor de novo", async (t) => {
    const fin = display(2, "Financeiro", "#16A34A", "#FFFFFF");
    const handler = (url) => (url.includes("fragmento") ? response(200, fixtures.stage)
        : url.includes("opcoes") ? ok({field: "sector", current_id: 1, items: [display(1, "Comercial", "#FACC15", "#1F2937"), fin]})
        : ok({field: "sector", value: 2, display: fin, derived: {stage: null, condition: null}}));
    const h = setup(t, {groupBy: "sector", handler});
    h.field(1, "sector").click();
    await h.tick();
    [...h.pop().querySelectorAll(".activity-inline-color-option")].find((n) => n.textContent.startsWith("Financeiro")).click();
    await h.tick();
    await h.tick();
    assert.ok(h.requests.some((r) => r.url.includes("fragmento=raias")));
});

// -- erros ----------------------------------------------------------------------------------------------------------------

test("o servidor recusa (400): o valor antigo volta e a mensagem dele aparece, sem redesenhar as raias", async (t) => {
    const h = setup(t, {handler: (url) => (url.startsWith(URLS.people) ? ok({results: [{id: 7, name: "Maria Souza"}]}) : response(400, {ok: false, error: "O responsável escolhido não pertence à organização ou está inativo."}))});
    h.field(1, "owner").click();
    await h.tick();
    h.pop().querySelector(".activity-inline-popover__option").click();
    await h.tick();
    assert.equal(h.field(1, "owner").querySelector(".board-person__name").textContent, "Paulo Souza", "voltou ao valor confirmado");
    assert.equal(h.model(1, "owner").value, "6");
    assert.deepEqual(h.toasts(), ["O responsável escolhido não pertence à organização ou está inativo."]);
    assert.equal(h.requests.some((r) => r.url.includes("fragmento")), false);
    assert.equal(h.card(1).getAttribute("data-updated-at"), "2026-10-03T10:00:00+00:00", "a versão do cartão não muda");
});

test("uma prioridade recusada devolve a pílula antiga", async (t) => {
    const items = [display("MEDIA", "Média", "#F59E0B", "#1F2937"), display("ALTA", "Alta", "#FACC15", "#1F2937")];
    const handler = (url) => (url.includes("opcoes") ? ok({field: "urgency", current_id: "MEDIA", items}) : response(403, {ok: false, error: "Você não possui autorização para alterar este campo."}));
    const h = setup(t, {handler});
    h.field(1, "urgency").click();
    await h.tick();
    [...h.pop().querySelectorAll(".activity-inline-color-option")].find((n) => n.textContent.startsWith("Alta")).click();
    await h.tick();
    assert.equal(h.field(1, "urgency").querySelector(".board-pill").textContent, "Média");
    assert.deepEqual(h.toasts(), ["Você não possui autorização para alterar este campo."]);
});

// -- teclado e convivência com o resto do cartão -------------------------------------------------------------------------------

test("Enter e Espaço no campo focado abrem o editor; Esc fecha e devolve o foco", async (t) => {
    const h = setup(t, {handler: (url) => (url.startsWith(URLS.people) ? ok({results: []}) : ok())});
    h.field(1, "owner").focus();
    h.key(h.field(1, "owner"), "Enter");
    await h.tick();
    assert.ok(h.pop());
    h.key(h.document, "Escape");
    assert.equal(h.pop(), null);
    assert.equal(h.document.activeElement, h.field(1, "owner"));
});

test("clicar no título renomeia (núcleo), não abre editor de campo; o ⋯ continua oferecendo as ações do cartão", (t) => {
    const h = setup(t, {handler: () => ok()});
    h.card(1).querySelector("[data-card-title]").click();
    assert.ok(h.card(1).querySelector(".board-inline-input"));
    assert.equal(h.pop(), null);
    h.card(3).querySelector("[data-card-menu]").click();
    assert.ok(h.document.querySelector(".board-pop"));
});

test("editar um campo não inicia arrasto nem mexe na contagem das raias", async (t) => {
    const h = setup(t, {handler: (url) => (url.startsWith(URLS.people) ? ok({results: [{id: 7, name: "Maria Souza"}]}) : ok({field: "owner", value: 7, display: {text: "Maria Souza", initials: "MS", avatar_class: ""}}))});
    const before = h.ids(10).join(",");
    h.field(1, "owner").click();
    await h.tick();
    h.pop().querySelector(".activity-inline-popover__option").click();
    await h.tick();
    assert.equal(h.ids(10).join(","), before);
    assert.equal(h.lane(10).querySelector("[data-lane-count]").textContent, "3");
});

test("a pré-visualização do Configurar cartões não é editável (sem gancho nem classe)", async (t) => {
    const h = setup(t, {handler: () => ok()});
    const controller = h.document.querySelector("[data-kanban]").lpsKanbanCore;
    controller.openConfig({controls: [], fields: [{id: 1, name: "Responsável"}], selected: [1], save: () => Promise.resolve()});
    const preview = h.document.querySelector(".kanban-config__preview .kanban-card");
    assert.equal(preview.querySelector("[data-inline-field]"), null);
    assert.equal(preview.querySelector(".is-editable"), null);
    assert.equal(preview.querySelector("[tabindex]"), null);
});
