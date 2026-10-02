const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');

const script = readFileSync(path.join(__dirname, '../static/js/workspace-filters.js'), 'utf8');

function setup() {
    const dom = new JSDOM(`<!doctype html><body>
      <form data-workspace-filters>
        <input name="q" id="q">
        <select name="setor" data-workspace-sector><option value="">Todos</option><option value="4">Comercial</option></select>
        <details data-workspace-popover><summary class="workspace-filter-button" aria-expanded="false">Pessoa</summary><div>conteúdo</div></details>
        <button type="submit" class="activities-search__submit">Buscar</button>
      </form>
    </body>`, {url: 'http://localhost/demandas/', runScripts: 'dangerously'});
    const scriptElement = dom.window.document.createElement('script');
    scriptElement.textContent = script;
    dom.window.document.body.appendChild(scriptElement);
    return dom;
}

test('typing does not submit the shared filter form', t => {
    const dom = setup();
    t.after(() => dom.window.close());
    const form = dom.window.document.querySelector('form');
    const input = form.querySelector('[name=q]');
    let submits = 0;
    form.addEventListener('submit', event => { submits++; event.preventDefault(); });
    input.value = 'demanda longa';
    input.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
    assert.equal(submits, 0);
});

test('manual submit is accepted once and prevents duplicates', t => {
    const dom = setup();
    t.after(() => dom.window.close());
    const form = dom.window.document.querySelector('form');
    const button = form.querySelector('button[type=submit]');
    form.addEventListener('submit', event => event.preventDefault());
    const first = form.dispatchEvent(new dom.window.SubmitEvent('submit', {bubbles: true, cancelable: true, submitter: button}));
    const second = form.dispatchEvent(new dom.window.SubmitEvent('submit', {bubbles: true, cancelable: true, submitter: button}));
    assert.equal(first, false, 'o listener do teste cancela o envio, mas o script processa apenas uma tentativa');
    assert.equal(second, false);
    assert.equal(form.dataset.submitting, 'true');
    assert.equal(button.disabled, true);
});

test('changing the highlighted sector submits the form once', t => {
    const dom = setup();
    t.after(() => dom.window.close());
    const form = dom.window.document.querySelector('form');
    const sector = form.querySelector('[data-workspace-sector]');
    let requests = 0;
    form.requestSubmit = () => { requests++; };
    sector.value = '4';
    sector.dispatchEvent(new dom.window.Event('change', {bubbles: true}));
    assert.equal(requests, 1);
});

test('popover exposes expanded state and closes with Escape', t => {
    const dom = setup();
    t.after(() => dom.window.close());
    const popover = dom.window.document.querySelector('[data-workspace-popover]');
    const summary = popover.querySelector('summary');
    popover.open = true;
    popover.dispatchEvent(new dom.window.Event('toggle'));
    assert.equal(summary.getAttribute('aria-expanded'), 'true');
    dom.window.document.dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
    assert.equal(popover.open, false);
    assert.equal(summary.getAttribute('aria-expanded'), 'false');
});
