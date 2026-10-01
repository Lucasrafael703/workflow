const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');

const taskModal = readFileSync(path.join(__dirname, '../static/js/task-modal.js'), 'utf8');
const picker = readFileSync(path.join(__dirname, '../static/js/person-picker.js'), 'utf8');
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

const SUMMARY = {id: 7, title: 'Sincronização Cérebro', meta: 'Cliente interno • Setor: Operações • 3 tarefas'};

// O mesmo markup de _task_editor_fields.html + ActivityPickerWidget (nova tarefa fora de uma atividade).
const markup = `
<div class="modal-backdrop"><form>
  <div data-task-activity data-field="activity">
    <div data-task-activity-picker>
      <div class="person-picker" data-person-picker data-search-url="/demandas/busca/" data-placeholder="Buscar..." data-empty-label="Selecionar demanda">
        <input type="hidden" name="activity" id="id_activity">
        <button type="button" class="person-picker__trigger"><span class="person-picker__label muted">Selecionar demanda</span></button>
      </div>
    </div>
    <div class="task-selected-activity" data-task-activity-summary hidden>
      <div data-summary-title></div><div data-summary-meta></div>
      <button type="button" data-task-activity-change>Alterar</button>
    </div>
  </div>
</form></div>`;

function setup(t, {withPicker = false, html = markup} = {}) {
    const dom = new JSDOM(html, {url: 'http://localhost/tarefas/nova/', runScripts: 'outside-only', pretendToBeVisual: true});
    t.after(() => dom.window.close());
    const w = dom.window;
    if (withPicker) w.eval(picker);
    w.eval(taskModal);
    const $ = selector => w.document.querySelector(selector);
    const choose = item => $('#id_activity').dispatchEvent(new w.CustomEvent('change', {bubbles: true, detail: {item}}));
    return {w, $, choose};
}

test('choosing an activity swaps the picker for the activity card', t => {
    const {$, choose} = setup(t);
    $('#id_activity').value = '7';
    choose({id: 7, name: 'DEM-1 — Sincronização Cérebro', summary: SUMMARY});
    assert.equal($('[data-task-activity-summary]').hidden, false);
    assert.equal($('[data-summary-title]').textContent, SUMMARY.title);
    assert.equal($('[data-summary-meta]').textContent, SUMMARY.meta);
    assert.equal($('[data-task-activity-picker]').hidden, true);
});

test('"Alterar" brings the picker back and opens it', t => {
    const {w, $, choose} = setup(t);
    let opened = 0;
    $('.person-picker__trigger').addEventListener('click', () => opened++);
    $('#id_activity').value = '7';
    choose({id: 7, name: 'x', summary: SUMMARY});
    $('[data-task-activity-change]').dispatchEvent(new w.MouseEvent('click', {bubbles: true}));
    assert.equal($('[data-task-activity-summary]').hidden, true);
    assert.equal($('[data-task-activity-picker]').hidden, false);
    assert.equal(opened, 1);
});

test('clearing the selection (value emptied) shows the picker again', t => {
    const {w, $, choose} = setup(t);
    $('#id_activity').value = '7';
    choose({id: 7, name: 'x', summary: SUMMARY});
    $('#id_activity').value = '';
    $('#id_activity').dispatchEvent(new w.Event('change', {bubbles: true}));
    assert.equal($('[data-task-activity-picker]').hidden, false);
    assert.equal($('[data-task-activity-summary]').hidden, true);
});

test('a choice without a summary keeps what is on screen', t => {
    const {$, choose} = setup(t);
    $('#id_activity').value = '9';
    choose({id: 9, name: 'DEM-9 — Sem resumo'});
    assert.equal($('[data-task-activity-summary]').hidden, true);
    assert.equal($('[data-task-activity-picker]').hidden, false);
});

test('starting a block twice does not bind it twice', t => {
    const {w, $, choose} = setup(t);
    w.LPSWidgets.forEach(init => init(w.document));
    w.LPSWidgets.forEach(init => init(w.document));
    let opened = 0;
    $('.person-picker__trigger').addEventListener('click', () => opened++);
    $('#id_activity').value = '7';
    choose({id: 7, name: 'x', summary: SUMMARY});
    $('[data-task-activity-change]').dispatchEvent(new w.MouseEvent('click', {bubbles: true}));
    assert.equal(opened, 1);
});

test('a window injected later is started through LPSWidgets', t => {
    const {w, $} = setup(t, {html: '<div id="host"></div>'});
    $('#host').innerHTML = markup;
    w.LPSWidgets.forEach(init => init($('#host')));
    $('#id_activity').value = '7';
    $('#id_activity').dispatchEvent(new w.CustomEvent('change', {bubbles: true, detail: {item: {id: 7, summary: SUMMARY}}}));
    assert.equal($('[data-task-activity-summary]').hidden, false);
});

test('windows without an activity picker (inside an activity, edit) are left alone', t => {
    const html = '<div class="task-field"><div class="task-selected-activity" data-task-activity-summary><div data-summary-title>DEM</div></div></div>';
    const {$} = setup(t, {html});
    assert.equal($('[data-task-activity-summary]').hidden, false);
    assert.equal($('[data-summary-title]').textContent, 'DEM');
});

test('with the real picker: picking a search result carries its summary to the card', async t => {
    const {w, $} = setup(t, {withPicker: true});
    w.fetch = async url => ({
        json: async () => ({results: [{id: 7, name: 'DEM-1 — Sincronização Cérebro', summary: SUMMARY}]}),
        url,
    });
    $('.person-picker__trigger').dispatchEvent(new w.MouseEvent('click', {bubbles: true}));
    const input = $('.person-picker__search');
    input.value = 'Sinc';
    input.dispatchEvent(new w.Event('input', {bubbles: true}));
    await wait(350);
    $('.person-picker__option').dispatchEvent(new w.MouseEvent('click', {bubbles: true}));
    assert.equal($('#id_activity').value, '7');
    assert.equal($('[data-summary-title]').textContent, SUMMARY.title);
    assert.equal($('[data-summary-meta]').textContent, SUMMARY.meta);
    assert.equal($('[data-task-activity-picker]').hidden, true);
    assert.equal($('[data-task-activity-summary]').hidden, false);
});
