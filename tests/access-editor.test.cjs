/* Telas de acesso (static/js/access-editor.js): escolher grupo, ajustes individuais, prévia do menu,
   equipes e primeiro acesso. Requires jsdom@26.1.0 in NODE_PATH (ou npm install nesta pasta).
   Run from workflow: node --test tests/access-editor.test.cjs
   Set PYTHON to the project's Python if it is not in .venv.

   As linhas de telas vêm do parcial Django real (core/_screen_levels.html) com as telas reais
   (acessos/screens.py), sem banco. */
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync, existsSync} = require("node:fs");
const {execFileSync} = require("node:child_process");
const path = require("node:path");
const {JSDOM} = require("jsdom");

const root = path.resolve(__dirname, "..");
const localPython = path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const python = process.env.PYTHON || (existsSync(localPython) ? localPython : "python");

const rendered = JSON.parse(execFileSync(python, ["-c", `
import os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
os.environ.setdefault('SECRET_KEY', 'test')
import django
django.setup()
from django.template.loader import render_to_string
from acessos import screens
from core.access_views import screen_sections

def levels(**over):
    base = {s.key: 'none' for s in screens.SCREENS}
    base.update(over)
    return base

colaborador = levels(inicio='ver', notificacoes='ver', tarefas='editar', demandas='editar')
gestor = levels(inicio='ver', notificacoes='ver', tarefas='editar', demandas='editar', visao_gestor='ver', quadros='ver')

def html(current, floor, locked=False):
    return render_to_string('core/_screen_levels.html', {
        'sections': screen_sections(current, floor=floor), 'locked': locked, 'show_individual': floor is not None,
    })

print(json.dumps({
    'userRows': html(colaborador, colaborador),
    'groupRows': html(colaborador, None),
    'lockedRows': html(colaborador, colaborador, True),
    'config': {
        'screens': screens.screens_payload(),
        'sections': [{'key': k, 'name': n} for k, n in screens.SECTIONS],
        'groups': {'1': {'name': 'Colaborador', 'levels': colaborador, 'scope': 'teams'},
                   '2': {'name': 'Gestor', 'levels': gestor, 'scope': 'org'}},
        'orgScope': 'org', 'mode': 'user',
    },
    'groupConfig': {
        'screens': screens.screens_payload(),
        'sections': [{'key': k, 'name': n} for k, n in screens.SECTIONS],
        'levels': colaborador, 'mode': 'group',
    },
}))
`], {cwd: root, encoding: "utf8"}).trim());

const script = readFileSync(path.join(root, "static/js/access-editor.js"), "utf8");

function userPage(t, {rows = rendered.userRows, selected = "1", scope = "teams", config = rendered.config} = {}) {
    const dom = new JSDOM(`<!doctype html><body>
      <form data-access-editor id="user-editor">
        <div data-first-access>
          <input type="radio" name="first_access" value="invite" checked>
          <input type="radio" name="first_access" value="password">
        </div>
        <div data-password-fields hidden></div>
        <input type="checkbox" name="teams" value="10" data-team>
        <input type="checkbox" name="teams" value="11" data-team checked>
        <div data-team-table>
          <div data-team-row="10" hidden><input type="radio" name="main_sector" value="10"></div>
          <div data-team-row="11"><input type="radio" name="main_sector" value="11" checked></div>
          <p data-team-empty hidden></p>
        </div>
        <div data-group-cards>
          <input type="radio" name="group" value="1" ${selected === "1" ? "checked" : ""}>
          <input type="radio" name="group" value="2" ${selected === "2" ? "checked" : ""}>
        </div>
        <select name="scope" data-scope>
          <option value="teams" ${scope === "teams" ? "selected" : ""}>equipes</option>
          <option value="managed">gerencia</option>
          <option value="org" ${scope === "org" ? "selected" : ""}>org</option>
        </select>
        <div data-scope-warning hidden><span data-scope-warning-text></span><button type="button" data-scope-use-org>org</button></div>
        <strong data-count="total"></strong><strong data-count="view"></strong><strong data-count="individual"></strong>
        <nav data-menu-preview></nav>
        ${rows}
      </form>
      <script type="application/json" id="access-config">${JSON.stringify(config)}</script>
    </body>`, {url: "http://localhost/usuarios/novo/", runScripts: "outside-only"});
    t.after(() => dom.window.close());
    dom.window.eval(script);
    const $ = selector => dom.window.document.querySelector(selector);
    const $$ = selector => Array.from(dom.window.document.querySelectorAll(selector));
    const row = key => $(`.access-row[data-screen="${key}"]`);
    const level = key => row(key).querySelector("input[type=radio]:checked").value;
    const choose = (key, value) => {
        const radio = row(key).querySelector(`input[value="${value}"]`);
        radio.checked = true;
        radio.dispatchEvent(new dom.window.Event("change", {bubbles: true}));
    };
    const change = (element, props = {}) => {
        Object.assign(element, props);
        element.dispatchEvent(new dom.window.Event("change", {bubbles: true}));
    };
    const count = name => $(`[data-count=${name}]`).textContent;
    const preview = () => $$(".menu-preview__item").map(item => item.textContent);
    return {dom, $, $$, row, level, choose, change, count, preview};
}

test("começa com as telas do grupo, sem ajustes e com a prévia do menu", t => {
    const page = userPage(t);
    assert.equal(page.level("tarefas"), "editar");
    assert.equal(page.level("usuarios"), "none");
    assert.equal(page.count("total"), "4");
    assert.equal(page.count("individual"), "0");
    assert.equal(page.count("view"), "0"); // Início e Notificações não têm "Editar": não contam como "só ver"
    const items = page.preview();
    assert.ok(items.some(text => text.startsWith("Tarefas")));
    assert.ok(!items.some(text => text.startsWith("Usuários")));
    assert.ok(page.$$(".menu-preview__title").some(title => title.textContent === "Dia a dia"));
    assert.ok(items.some(text => text.startsWith("Início") && text.includes("só ver") === false));
});

test("tela sem 'Editar' não ganha tag de só ver; tela com 'Editar' em 'Ver' ganha", t => {
    const page = userPage(t);
    page.choose("quadros", "ver");
    const quadros = page.preview().find(text => text.startsWith("Quadros"));
    assert.ok(quadros.includes("só ver") || quadros.includes("organização"));
    const inicio = page.preview().find(text => text.startsWith("Início"));
    assert.equal(inicio, "Início");
});

test("abaixo do grupo as opções ficam desabilitadas", t => {
    const page = userPage(t);
    assert.equal(page.row("tarefas").querySelector("input[value=none]").disabled, true);
    assert.equal(page.row("tarefas").querySelector("input[value=ver]").disabled, true);
    assert.equal(page.row("tarefas").querySelector("input[value=editar]").disabled, false);
    assert.equal(page.row("clientes").querySelector("input[value=none]").disabled, false);
});

test("subir uma tela vira ajuste individual, com selo, contagem e botão de voltar", t => {
    const page = userPage(t);
    page.choose("clientes", "editar");
    assert.equal(page.row("clientes").classList.contains("is-individual"), true);
    assert.equal(page.row("clientes").querySelector("[data-individual-badge]").hidden, false);
    assert.equal(page.row("clientes").querySelector("[data-reset]").hidden, false);
    assert.equal(page.count("individual"), "1");
    assert.equal(page.count("total"), "5");

    page.row("clientes").querySelector("[data-reset]").click();
    assert.equal(page.level("clientes"), "none");
    assert.equal(page.row("clientes").classList.contains("is-individual"), false);
    assert.equal(page.count("individual"), "0");
    assert.equal(page.row("clientes").querySelector("[data-reset]").hidden, true);
});

test("trocar de grupo marca as telas do novo grupo", t => {
    const page = userPage(t);
    page.change(page.$("input[name=group][value='2']"), {checked: true});
    assert.equal(page.level("visao_gestor"), "ver");
    assert.equal(page.level("quadros"), "ver");
    assert.equal(page.count("individual"), "0");
    // o piso agora é o do gestor
    assert.equal(page.row("visao_gestor").querySelector("input[value=none]").disabled, true);
    assert.equal(page.row("clientes").querySelector("input[value=none]").disabled, false);
});

test("um ajuste individual que continua acima do novo grupo é mantido", t => {
    const page = userPage(t);
    page.choose("quadros", "editar");
    page.choose("clientes", "editar");
    page.change(page.$("input[name=group][value='2']"), {checked: true});
    assert.equal(page.level("quadros"), "editar"); // acima do 'ver' do gestor
    assert.equal(page.level("clientes"), "editar");
    assert.equal(page.count("individual"), "2");
    page.change(page.$("input[name=group][value='1']"), {checked: true});
    assert.equal(page.level("visao_gestor"), "none"); // o que era do grupo anterior não acompanha
});

test("'Vale para' acompanha o grupo até a pessoa escolher à mão", t => {
    const page = userPage(t);
    page.change(page.$("input[name=group][value='2']"), {checked: true});
    assert.equal(page.$("[data-scope]").value, "org");
    page.change(page.$("[data-scope]"), {value: "managed"});
    page.change(page.$("input[name=group][value='1']"), {checked: true});
    assert.equal(page.$("[data-scope]").value, "managed");
});

test("avisa quando uma tela só funciona com a organização inteira", t => {
    const page = userPage(t);
    const warning = page.$("[data-scope-warning]");
    assert.equal(warning.hidden, true);
    page.change(page.$("input[name=group][value='2']"), {checked: true});
    page.change(page.$("[data-scope]"), {value: "teams"});
    assert.equal(warning.hidden, false);
    assert.ok(warning.textContent.includes("Quadros"));
    assert.ok(page.preview().some(text => text.startsWith("Quadros") && text.includes("organização inteira")));

    page.$("[data-scope-use-org]").click();
    assert.equal(page.$("[data-scope]").value, "org");
    assert.equal(warning.hidden, true);
    assert.ok(page.preview().every(text => !text.includes("organização inteira")));
});

test("'Todas: editar' sobe só o que existe e respeita o piso do grupo; 'Nenhuma' volta ao piso", t => {
    const page = userPage(t);
    const section = page.row("clientes").closest(".access-block");
    section.querySelector("[data-bulk=editar]").click();
    assert.equal(page.level("clientes"), "editar");
    assert.equal(page.level("empresas"), "editar");
    assert.equal(page.level("processos"), "editar");

    section.querySelector("[data-bulk=none]").click();
    assert.equal(page.level("clientes"), "none");

    const day = page.row("inicio").closest(".access-block");
    day.querySelector("[data-bulk=editar]").click();
    assert.equal(page.level("inicio"), "ver"); // Início não tem 'Editar'
    day.querySelector("[data-bulk=none]").click();
    assert.equal(page.level("tarefas"), "editar"); // piso do grupo
    assert.equal(page.level("inicio"), "ver");
});

test("equipes: marcar mostra a linha, desmarcar a esconde e a principal acompanha", t => {
    const page = userPage(t);
    const rowOf = id => page.$(`[data-team-row='${id}']`);
    assert.equal(rowOf(10).hidden, true);
    page.change(page.$("input[data-team][value='10']"), {checked: true});
    assert.equal(rowOf(10).hidden, false);

    page.change(page.$("input[data-team][value='11']"), {checked: false});
    assert.equal(rowOf(11).hidden, true);
    assert.equal(page.$("input[name=main_sector]:checked").value, "10"); // passou para a equipe que sobrou

    page.change(page.$("input[data-team][value='10']"), {checked: false});
    assert.equal(page.$("[data-team-empty]").hidden, false);
    assert.equal(page.$("input[name=main_sector]:checked"), null);
});

test("senha provisória só aparece quando escolhida", t => {
    const page = userPage(t);
    assert.equal(page.$("[data-password-fields]").hidden, true);
    page.change(page.$("input[name=first_access][value=password]"), {checked: true});
    assert.equal(page.$("[data-password-fields]").hidden, false);
    page.change(page.$("input[name=first_access][value=invite]"), {checked: true});
    assert.equal(page.$("[data-password-fields]").hidden, true);
});

test("somente leitura: nada de botões em massa e nenhuma opção habilitada", t => {
    const page = userPage(t, {rows: rendered.lockedRows});
    assert.equal(page.$$("[data-bulk]").length, 0);
    assert.ok(page.$$(".access-row input[type=radio]").every(radio => radio.disabled));
    assert.equal(page.count("total"), "4");
});

test("edição de grupo: contagem de telas liberadas e sem ajuste individual", t => {
    const page = userPage(t, {rows: rendered.groupRows, config: rendered.groupConfig});
    assert.equal(page.count("total"), "4");
    page.choose("clientes", "ver");
    assert.equal(page.count("total"), "5");
    assert.equal(page.count("individual"), "0");
    assert.equal(page.row("clientes").querySelector("[data-individual-badge]"), null);
    page.row("clientes").closest(".access-block").querySelector("[data-bulk=none]").click();
    assert.equal(page.level("clientes"), "none");
    assert.equal(page.count("total"), "4");
});

test("prévia vazia avisa que nenhuma tela foi liberada", t => {
    const page = userPage(t, {rows: rendered.groupRows, config: rendered.groupConfig});
    page.$$(".access-block [data-bulk=none]").forEach(button => button.click());
    assert.equal(page.count("total"), "0");
    assert.equal(page.$(".menu-preview__empty").textContent, "Nenhuma tela liberada.");
});
