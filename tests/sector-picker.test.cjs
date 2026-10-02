const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');

const script = readFileSync(path.join(__dirname, '../static/js/person-picker.js'), 'utf8');
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

function setup() {
    const dom = new JSDOM(`<!doctype html><body>
      <div data-person-picker data-picker-kind="sector" data-search-url="/sector-search/"
           data-placeholder="Buscar setor..." data-empty-label="Selecionar setor"
           data-selected-color="#3B82F6" data-selected-text-color="#FFFFFF">
        <input type="hidden" name="sector" value="">
        <button type="button" class="person-picker__trigger" aria-haspopup="listbox" aria-expanded="false">
          <span class="sector-picker__swatch" hidden></span>
          <span class="person-picker__label muted">Selecionar setor</span>
        </button>
      </div>
    </body>`, {url: 'http://localhost/demandas/', runScripts: 'dangerously'});
    dom.window.fetch = async () => ({json: async () => ({results: [
        {id: 7, name: 'Comercial', color: '#FACC15', text_color: '#1F2937'},
    ]})});
    const scriptElement = dom.window.document.createElement('script');
    scriptElement.textContent = script;
    dom.window.document.body.appendChild(scriptElement);
    return dom;
}

test('seletor de setor mostra a cor, atualiza o hidden e respeita teclado', async t => {
    const dom = setup();
    t.after(() => dom.window.close());
    const root = dom.window.document.querySelector('[data-person-picker]');
    const trigger = root.querySelector('.person-picker__trigger');

    trigger.click();
    assert.equal(trigger.getAttribute('aria-expanded'), 'true');
    const search = root.querySelector('.person-picker__search');
    search.value = 'com';
    search.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
    await wait(300);

    const option = root.querySelector('.person-picker__option');
    assert.ok(option.querySelector('.sector-picker__option-swatch'));
    option.click();

    assert.equal(root.querySelector('input[name=sector]').value, '7');
    assert.equal(root.querySelector('.person-picker__label').textContent, 'Comercial');
    assert.equal(root.querySelector('.sector-picker__swatch').style.backgroundColor, 'rgb(250, 204, 21)');
    assert.equal(trigger.getAttribute('aria-expanded'), 'false');

    trigger.click();
    root.querySelector('.person-picker__search').dispatchEvent(
        new dom.window.KeyboardEvent('keydown', {key: 'Escape', bubbles: true})
    );
    assert.equal(trigger.getAttribute('aria-expanded'), 'false');
});
