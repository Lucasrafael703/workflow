const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');

const script = readFileSync(path.join(__dirname, '../static/js/person-multi-picker.js'), 'utf8');
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const response = results => ({ok: true, json: async () => ({results})});

function setup(fetch) {
    const dom = new JSDOM(`<!doctype html><body>
      <input id="before" type="text">
      <div data-person-multi-picker data-search-url="/pessoas/" data-create-url="/usuarios/novo/">
        <select multiple hidden name="participantes">
          <option value="1" selected>Alfa</option>
        </select>
        <div class="person-multi-picker__chips">
          <span class="person-multi-picker__chip" data-person-id="1">Alfa<button type="button" class="person-multi-picker__remove">×</button></span>
          <button type="button" class="person-multi-picker__add">Adicionar participante</button>
        </div>
      </div>
      <input id="after" type="text">
    </body>`, {url: 'http://localhost/tarefas/', runScripts: 'dangerously'});
    dom.window.HTMLElement.prototype.scrollIntoView = function () {};
    dom.window.fetch = fetch || (async () => response([
        {id: 1, name: 'Alfa'},
        {id: 2, name: 'Biasi'},
        {id: 3, name: 'Carlos'},
    ]));
    const scriptElement = dom.window.document.createElement('script');
    scriptElement.textContent = script;
    dom.window.document.body.appendChild(scriptElement);
    return dom;
}

test('lista inicial, busca de uma letra e exclusão dos já selecionados', async t => {
    const calls = [];
    const dom = setup(async url => {
        calls.push(url);
        return response([
            {id: 1, name: 'Alfa'},
            {id: 2, name: 'Biasi'},
            {id: 3, name: 'Carlos'},
        ]);
    });
    t.after(() => dom.window.close());
    const root = dom.window.document.querySelector('[data-person-multi-picker]');
    const add = root.querySelector('.person-multi-picker__add');
    add.click();
    await wait(10);

    assert.equal(new URL(calls[0], 'http://localhost').searchParams.get('q'), '');
    assert.deepEqual(Array.from(root.querySelectorAll('.person-picker__option')).map(o => o.textContent), ['Biasi', 'Carlos']);

    const search = root.querySelector('.person-picker__search');
    search.value = 'R';
    search.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
    await wait(300);
    assert.equal(new URL(calls[1], 'http://localhost').searchParams.get('q'), 'R');
    assert.equal(root.querySelector('.person-picker__results').getAttribute('role'), 'listbox');
});

test('Enter adiciona a opção ativa e mantém a fonte de verdade no select', async t => {
    const dom = setup();
    t.after(() => dom.window.close());
    const root = dom.window.document.querySelector('[data-person-multi-picker]');
    root.querySelector('.person-multi-picker__add').click();
    await wait(10);
    const search = root.querySelector('.person-picker__search');
    search.dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true, cancelable: true}));
    search.dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true}));

    assert.equal(root.querySelector('select option[value="2"]').selected, true);
    assert.equal(root.querySelectorAll('.person-multi-picker__chip').length, 2);
    assert.equal(root.querySelector('.person-picker__popup'), null);
});

test('criação de pessoa usa o texto pesquisado e adiciona o retorno ao múltiplo', async t => {
    const calls = [];
    const dom = setup(async () => response([]));
    dom.window.LPSModal = {open: (url, options) => calls.push({url, options})};
    t.after(() => dom.window.close());
    const root = dom.window.document.querySelector('[data-person-multi-picker]');
    root.querySelector('.person-multi-picker__add').click();
    const search = root.querySelector('.person-picker__search');
    search.value = 'Nova Pessoa';
    search.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
    await wait(300);
    root.querySelector('.person-picker__create').click();

    assert.equal(new URL(calls[0].url, 'http://localhost').searchParams.get('initial_name'), 'Nova Pessoa');
    calls[0].options.onSuccess({id: 9, name: 'Nova Pessoa'});
    assert.equal(root.querySelector('select option[value="9"]').selected, true);
    assert.match(root.querySelector('[data-person-id="9"]').textContent, /Nova Pessoa/);
});

test('Tab no múltiplo fecha e avança', async t => {
    const dom = setup();
    t.after(() => dom.window.close());
    const root = dom.window.document.querySelector('[data-person-multi-picker]');
    root.querySelector('.person-multi-picker__add').focus();
    await wait(0);
    root.querySelector('.person-picker__search').dispatchEvent(
        new dom.window.KeyboardEvent('keydown', {key: 'Tab', bubbles: true, cancelable: true})
    );
    assert.equal(dom.window.document.activeElement.id, 'after');
    assert.equal(root.querySelector('.person-picker__popup'), null);
});
