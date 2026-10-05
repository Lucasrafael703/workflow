const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');

const script = readFileSync(path.join(__dirname, '../static/js/person-picker.js'), 'utf8');
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const response = results => ({ok: true, json: async () => ({results})});

function setup({html, fetch} = {}) {
    const dom = new JSDOM(html || `<!doctype html><body>
      <input id="before" type="text">
      <div data-person-picker data-search-url="/pessoas/" data-create-url="/usuarios/novo/"
           data-placeholder="Buscar pessoa..." data-empty-label="Selecionar pessoa">
        <input type="hidden" name="owner" value="8">
        <button type="button" class="person-picker__trigger" aria-haspopup="listbox" aria-expanded="false">
          <span class="person-picker__label">Pessoa atual</span>
        </button>
      </div>
      <input id="after" type="text">
    </body>`, {url: 'http://localhost/demandas/', runScripts: 'dangerously'});
    dom.window.HTMLElement.prototype.scrollIntoView = function () {};
    dom.window.fetch = fetch || (async () => response([
        {id: 1, name: 'Alfa Engenharia'},
        {id: 2, name: 'Biasi Engenharia'},
        {id: 3, name: 'Construtora ABC'},
    ]));
    const scriptElement = dom.window.document.createElement('script');
    scriptElement.textContent = script;
    dom.window.document.body.appendChild(scriptElement);
    return dom;
}

test('abre por foco/Tab, busca q vazio e navega com setas e Enter', async t => {
    const calls = [];
    const dom = setup({fetch: async url => {
        calls.push(url);
        return response([
            {id: 1, name: 'Alfa Engenharia'},
            {id: 2, name: 'Biasi Engenharia'},
            {id: 3, name: 'Construtora ABC'},
        ]);
    }});
    t.after(() => dom.window.close());

    const root = dom.window.document.querySelector('[data-person-picker]');
    const trigger = root.querySelector('.person-picker__trigger');
    trigger.focus();
    await wait(10);

    assert.equal(trigger.getAttribute('aria-expanded'), 'true');
    assert.equal(new URL(calls[0], 'http://localhost').searchParams.get('q'), '');
    const search = root.querySelector('.person-picker__search');
    search.dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true, cancelable: true}));
    search.dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true, cancelable: true}));
    assert.equal(root.querySelectorAll('.person-picker__option')[1].getAttribute('aria-selected'), 'true');
    search.dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true}));

    assert.equal(root.querySelector('input[type=hidden]').value, '2');
    assert.equal(root.querySelector('.person-picker__label').textContent, 'Biasi Engenharia');
    assert.equal(trigger.getAttribute('aria-expanded'), 'false');
});

test('Tab e Shift+Tab fecham e seguem para o campo adjacente', async t => {
    const dom = setup();
    t.after(() => dom.window.close());
    const root = dom.window.document.querySelector('[data-person-picker]');
    const trigger = root.querySelector('.person-picker__trigger');
    const search = () => root.querySelector('.person-picker__search');

    trigger.focus();
    await wait(0);
    search().dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'Tab', bubbles: true, cancelable: true}));
    assert.equal(dom.window.document.activeElement.id, 'after');
    assert.equal(trigger.getAttribute('aria-expanded'), 'false');

    trigger.focus();
    await wait(0);
    search().dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'Tab', shiftKey: true, bubbles: true, cancelable: true}));
    assert.equal(dom.window.document.activeElement.id, 'before');
    assert.equal(trigger.getAttribute('aria-expanded'), 'false');
});

test('preserva seleção quando a pessoa pesquisa e sai sem escolher', async t => {
    const dom = setup({fetch: async () => response([])});
    t.after(() => dom.window.close());
    const root = dom.window.document.querySelector('[data-person-picker]');
    const trigger = root.querySelector('.person-picker__trigger');
    trigger.click();
    const search = root.querySelector('.person-picker__search');
    search.value = 'Zyx';
    search.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
    await wait(300);
    search.dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'Tab', bubbles: true, cancelable: true}));

    assert.equal(root.querySelector('input[type=hidden]').value, '8');
    assert.equal(root.querySelector('.person-picker__label').textContent, 'Pessoa atual');
});

test('diferencia erro de rede e envia initial_name ao cadastro', async t => {
    const modalCalls = [];
    const dom = setup({fetch: async () => { throw new Error('offline'); }});
    dom.window.LPSModal = {open: (url, options) => modalCalls.push({url, options})};
    t.after(() => dom.window.close());
    const root = dom.window.document.querySelector('[data-person-picker]');
    root.querySelector('.person-picker__trigger').click();
    const search = root.querySelector('.person-picker__search');
    search.value = 'Construtora ABC';
    search.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
    await wait(300);

    assert.match(root.querySelector('.person-picker__results').textContent, /N[aã]o foi poss[ií]vel carregar/);
    assert.equal(root.querySelector('.person-picker__create').hidden, true);

    // Reabre com uma resposta vazia para expor o CTA de criação.
    dom.window.fetch = async () => response([]);
    root.querySelector('.person-picker__trigger').click();
    root.querySelector('.person-picker__trigger').click();
    const secondSearch = root.querySelector('.person-picker__search');
    secondSearch.value = 'Construtora ABC';
    secondSearch.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
    await wait(300);
    root.querySelector('.person-picker__create').click();

    assert.equal(modalCalls.length, 1);
    assert.equal(new URL(modalCalls[0].url, 'http://localhost').searchParams.get('initial_name'), 'Construtora ABC');
    modalCalls[0].options.onSuccess({id: 11, name: 'Construtora ABC'});
    assert.equal(root.querySelector('input[type=hidden]').value, '11');
    assert.equal(root.querySelector('.person-picker__label').textContent, 'Construtora ABC');
});

test('resposta antiga não substitui uma pesquisa mais nova', async t => {
    const pending = [];
    const dom = setup({fetch: (url, options) => new Promise(resolve => {
        pending.push({url, options, resolve});
    })});
    t.after(() => dom.window.close());
    const root = dom.window.document.querySelector('[data-person-picker]');
    root.querySelector('.person-picker__trigger').click();
    await wait(0);
    const search = root.querySelector('.person-picker__search');
    search.value = 'R';
    search.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
    await wait(300);
    assert.equal(pending.length, 2);
    assert.equal(pending[0].options.signal.aborted, true);

    pending[1].resolve(response([{id: 2, name: 'Ribeiro'}]));
    await wait(0);
    pending[0].resolve(response([{id: 1, name: 'Alfa'}]));
    await wait(0);
    assert.equal(root.querySelector('.person-picker__option').textContent, 'Ribeiro');
});

test('mudança de Cliente invalida Obra e Centro de custo em cascata', async t => {
    const dom = new JSDOM(`<!doctype html><body>
      <div data-person-picker data-search-url="/clientes/"><input id="id_client" type="hidden" value="1"><button type="button" class="person-picker__trigger"><span class="person-picker__label">Cliente A</span></button></div>
      <div data-person-picker data-search-url="/obras/" data-filter-field="id_client" data-filter-param="client"><input id="id_site" type="hidden" value="2"><button type="button" class="person-picker__trigger"><span class="person-picker__label">Obra A1</span></button></div>
      <div data-person-picker data-search-url="/centros/" data-filter-field="id_site" data-filter-param="site"><input id="id_cost" type="hidden" value="3"><button type="button" class="person-picker__trigger"><span class="person-picker__label">Centro A</span></button></div>
      <input id="after" type="text">
    </body>`, {url: 'http://localhost/', runScripts: 'dangerously'});
    dom.window.HTMLElement.prototype.scrollIntoView = function () {};
    dom.window.fetch = async () => response([]);
    const scriptElement = dom.window.document.createElement('script');
    scriptElement.textContent = script;
    dom.window.document.body.appendChild(scriptElement);
    t.after(() => dom.window.close());

    const client = dom.window.document.querySelector('#id_client');
    client.value = '4';
    client.dispatchEvent(new dom.window.Event('change', {bubbles: true}));

    assert.equal(dom.window.document.querySelector('#id_site').value, '');
    assert.equal(dom.window.document.querySelector('#id_cost').value, '');
});
