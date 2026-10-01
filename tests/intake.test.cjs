const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require('jsdom');

// intake.js usa o LPSAjax real (activity-workspace.js) e uma janela de mentira: o contrato testado é
// "o que o servidor responde" -> "o que acontece na tela".
const workspace = readFileSync(path.join(__dirname, '../static/js/activity-workspace.js'), 'utf8');
const intake = readFileSync(path.join(__dirname, '../static/js/intake.js'), 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));

const LIST = `
<ul data-intake-list>
  <li class="intake-item" id="intake-item-1">
    <a id="criar" href="/entrada/#criar-1" data-intake-action>Criar demanda</a>
    <a id="editar" href="/entrada/#editar-1" data-intake-action>Editar</a>
    <a id="ignorar" href="/entrada/#ignorar-1" data-intake-action>Ignorar</a>
    <form id="restaurar" method="post" action="/entrada/1/restaurar/" data-intake-restore>
      <input type="hidden" name="csrfmiddlewaretoken" value="token-123">
      <button type="submit">Restaurar</button>
    </form>
  </li>
  <li class="intake-item" id="intake-item-2"><a id="outro" href="/entrada/#editar-2" data-intake-action>Editar</a></li>
</ul>`;

function setup(t, {modal = true, html = LIST} = {}) {
    const reloads = [];
    const virtualConsole = new VirtualConsole();
    // jsdom não navega: avisa "Not implemented: navigation". É assim que se enxerga um reload.
    virtualConsole.on('jsdomError', error => { if (/navigation/.test(error.message)) reloads.push(error.message); });
    const dom = new JSDOM(html, {url: 'http://localhost/entrada/', runScripts: 'outside-only', virtualConsole});
    t.after(() => dom.window.close());
    const w = dom.window;
    const opened = [];
    const state = {rejectOpen: false, onSuccess: null};
    w.eval(workspace);
    if (modal) {
        w.LPSModal = {
            open(url, options) {
                opened.push({url, options});
                state.onSuccess = options.onSuccess;
                return state.rejectOpen ? Promise.reject(new Error('indisponível')) : Promise.resolve();
            },
        };
    }
    w.eval(intake);
    const $ = selector => w.document.querySelector(selector);
    const click = (element, init = {}) => {
        const event = new w.MouseEvent('click', {bubbles: true, cancelable: true, button: 0, ...init});
        element.dispatchEvent(event);
        return event;
    };
    return {w, $, click, opened, reloads, state};
}

test('clicking an action opens it in the modal instead of navigating', t => {
    const {$, click, opened} = setup(t);
    const event = click($('#criar'));
    assert.equal(event.defaultPrevented, true);
    assert.equal(opened.length, 1);
    assert.equal(opened[0].url, 'http://localhost/entrada/#criar-1');
    assert.equal(typeof opened[0].options.onSuccess, 'function');
});

test('modifier keys and other buttons keep the normal link behavior', t => {
    const {$, click, opened} = setup(t);
    for (const init of [{ctrlKey: true}, {metaKey: true}, {shiftKey: true}, {altKey: true}, {button: 1}]) {
        assert.equal(click($('#criar'), init).defaultPrevented, false, JSON.stringify(init));
    }
    assert.equal(opened.length, 0);
});

test('without the modal the link just opens the full page', t => {
    const {$, click} = setup(t, {modal: false});
    assert.equal(click($('#criar')).defaultPrevented, false);
});

test('a modal that fails to open falls back to the full page', async t => {
    const {w, $, click, state} = setup(t);
    state.rejectOpen = true;
    click($('#editar'));
    await tick();
    assert.equal(w.location.hash, '#editar-1');
});

test('ignoring removes only that card, announces and does not reload while others remain', t => {
    const {w, $, click, reloads, state} = setup(t);
    click($('#ignorar'));
    state.onSuccess({message: 'Solicitação ignorada.', remove: '#intake-item-1'});
    assert.equal($('#intake-item-1'), null);
    assert.ok($('#intake-item-2'));
    assert.equal($('[role=status]').textContent, 'Solicitação ignorada.');
    assert.equal(reloads.length, 0);
});

test('removing the last card reloads to show the empty state', t => {
    const {$, click, reloads, state} = setup(t);
    $('#intake-item-2').remove();
    click($('#ignorar'));
    state.onSuccess({message: 'Solicitação ignorada.', remove: '#intake-item-1'});
    assert.equal(reloads.length, 1);
});

test('editing replaces the card with the one the server rendered', t => {
    const {$, click, reloads, state} = setup(t);
    click($('#editar'));
    state.onSuccess({message: 'Sugestões atualizadas.', target: '#intake-item-1',
        html: '<li class="intake-item" id="intake-item-1">Cliente novo</li>'});
    assert.equal($('#intake-item-1').textContent, 'Cliente novo');
    assert.equal($('#intake-item-2').tagName, 'LI');
    assert.equal(reloads.length, 0);
});

test('creating the demand follows the redirect the server gave', t => {
    const {w, $, click, reloads, state} = setup(t);
    click($('#criar'));
    state.onSuccess({message: 'Demanda DEM-2026-00001 criada.', redirect_url: '/entrada/#demanda'});
    assert.equal(w.location.hash, '#demanda');
    assert.equal($('[role=status]').textContent, 'Demanda DEM-2026-00001 criada.');
    assert.equal(reloads.length, 0);
});

test('a result with nothing to apply reloads the page', t => {
    const {$, click, reloads, state} = setup(t);
    click($('#editar'));
    state.onSuccess({message: 'Sugestões atualizadas.', target: '#nao-existe', html: '<li id="nao-existe"></li>'});
    assert.equal(reloads.length, 1);
});

test('restore posts with the CSRF field, locks against double submit and applies the result', async t => {
    const {w, $, reloads} = setup(t);
    const calls = [];
    let release;
    w.fetch = (url, options) => {
        calls.push({url, options});
        return new Promise(resolve => {
            release = () => resolve({ok: true, headers: {get: () => 'application/json'},
                json: async () => ({message: 'Solicitação restaurada.', remove: '#intake-item-1'})});
        });
    };
    const form = $('#restaurar');
    form.dispatchEvent(new w.Event('submit', {bubbles: true, cancelable: true}));
    form.dispatchEvent(new w.Event('submit', {bubbles: true, cancelable: true}));
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, 'http://localhost/entrada/1/restaurar/');
    assert.equal(calls[0].options.method, 'POST');
    assert.equal(calls[0].options.headers['X-Requested-With'], 'XMLHttpRequest');
    assert.equal(calls[0].options.body.get('csrfmiddlewaretoken'), 'token-123');
    assert.equal($('#restaurar button').disabled, true);
    release();
    await tick(); await tick();
    assert.equal($('#intake-item-1'), null);
    assert.equal($('[role=status]').textContent, 'Solicitação restaurada.');
    assert.equal(reloads.length, 0);
});

test('a failed restore shows the error and lets the user try again', async t => {
    const {w, $} = setup(t);
    w.fetch = async () => ({ok: false, headers: {get: () => 'application/json'},
        json: async () => ({error: 'Só uma solicitação ignorada pode ser restaurada.'})});
    $('#restaurar').dispatchEvent(new w.Event('submit', {bubbles: true, cancelable: true}));
    await tick(); await tick();
    assert.match($('#restaurar [role=alert]').textContent, /ignorada pode ser restaurada/);
    assert.equal($('#restaurar button').disabled, false);
    assert.ok($('#intake-item-1'));
    assert.equal($('#restaurar').dataset.busy, undefined);
});

test('a non-JSON answer (expired session) is reported instead of failing silently', async t => {
    const {w, $} = setup(t);
    w.fetch = async () => ({ok: true, headers: {get: () => 'text/html'}, json: async () => { throw new Error('x'); }});
    $('#restaurar').dispatchEvent(new w.Event('submit', {bubbles: true, cancelable: true}));
    await tick(); await tick();
    assert.match($('#restaurar [role=alert]').textContent, /Verifique sua conexão ou sessão/);
});
