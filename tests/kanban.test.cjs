const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require('jsdom');

// kanban.js e workflow-picker.js rodam numa janela de mentira com um fetch de mentira: o contrato testado é
// "o que o servidor responde" -> "o que acontece no quadro". O HTML do fixture espelha os atributos dos templates
// (activities/_kanban_*.html); os testes de Django conferem esses mesmos atributos no HTML real.
const kanban = readFileSync(path.join(__dirname, '../static/js/kanban.js'), 'utf8');
const picker = readFileSync(path.join(__dirname, '../static/js/workflow-picker.js'), 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));
const settle = async () => { for (let i = 0; i < 6; i++) await tick(); };

function card(id, stage, {move = true, title = `Item ${id}`} = {}) {
    return `<article class="kanban-card" data-kanban-card data-item-id="${id}" data-stage-id="${stage}" data-can-move="${move ? 1 : ''}" draggable="${move}">
  <a class="kanban-card__title" href="/demandas/${id}/" data-open-drawer data-drawer-url="/demandas/${id}/gaveta/">${title}</a>
  <details class="kanban-menu" data-kanban-menu><summary>•••</summary><div class="kanban-menu__panel">
    <button type="button" data-open-drawer data-drawer-url="/demandas/${id}/gaveta/">Abrir</button>
    <button type="button" data-copy-text="Item ${id}">Copiar nome</button>
    <button type="button" data-kanban-post data-url="/tarefas/${id}/concluir/ajax/">Concluir</button>
    <a id="cancelar-${id}" href="/demandas/${id}/cancelar/" data-activity-action>Cancelar</a>
    <button type="button" id="mover-${id}" data-workflow-picker data-kind="stage">Mover</button>
  </div></details>
  <span class="meta">texto</span>
</article>`;
}

function column(stage, name, cards, {limit = '', unassigned = false} = {}) {
    const attrs = unassigned ? 'data-unassigned' : `data-stage-id="${stage}" data-stage-name="${name}" data-limit="${limit}"`;
    return `<section class="kanban-column" data-kanban-column ${attrs}>
  <header class="kanban-column__header"><strong>${name}</strong><span data-column-count data-count="${cards.length}">${limit ? `${cards.length} de ${limit}` : cards.length}</span>
    ${unassigned ? '' : `<button type="button" data-inline-create>+</button>
    <details class="kanban-menu" data-kanban-menu><summary>•••</summary><div class="kanban-menu__panel"><button type="button" data-set-limit>Definir limite</button></div></details>`}
  </header>
  <div class="kanban-column__body" data-dropzone>${cards.join('')}<div data-column-empty${cards.length ? ' hidden' : ''}>Nenhum item</div></div>
</section>`;
}

const PAGE = `
<form data-kanban-toolbar method="get">
  <select name="setor" data-kanban-sector><option value="1" selected>Orçamento</option><option value="2">Financeiro</option></select>
  <details class="kanban-pop" data-kanban-pop data-autosubmit><summary>Pessoa</summary><label><input type="radio" name="pessoa" value="eu" id="pessoa-eu"> Eu</label></details>
  <details class="kanban-pop" data-kanban-pop><summary>Filtro</summary><label><input type="checkbox" name="bloqueio" value="1" id="bloqueio"> Bloqueio</label></details>
</form>
<a class="js-new-task" id="nova-tarefa" href="/tarefas/nova-rapida/">Nova tarefa</a>
<div class="kanban-scroll"><section data-kanban-board>
  ${column(null, 'Sem etapa', [card(9, '')], {unassigned: true})}
  ${column(10, 'A fazer', [card(1, 10), card(2, 10, {move: false})])}
  ${column(11, 'Levantamento', [card(3, 11)], {limit: 1})}
  ${column(12, 'Pronto', [])}
</section></div>
<div id="kanban-config" hidden data-domain="demandas" data-noun="demanda" data-sector-id="1"
  data-set-stage-url="/kanban/demandas/999999999/etapa/" data-card-url="/kanban/demandas/999999999/cartao/"
  data-create-url="/kanban/demandas/criar/" data-limit-url="/kanban/demandas/limite/" data-drawer-url="/demandas/999999999/gaveta/"></div>`;

function setup(t, {html = PAGE, modal = true, drawer = true, search = ''} = {}) {
    const virtualConsole = new VirtualConsole();
    const navigations = [];
    const errors = [];
    virtualConsole.on('jsdomError', error => {
        if (/navigation/i.test(error.message)) navigations.push(error.message);
        else errors.push(error.detail && error.detail.stack ? error.detail.stack.split('\n').slice(0, 3).join(' | ') : error.message);
    });
    const dom = new JSDOM(`<!doctype html><body>${html}</body>`, {url: `http://localhost/demandas/kanban/${search}`, runScripts: 'outside-only', virtualConsole, pretendToBeVisual: true});
    t.after(() => {
        dom.window.close();
        assert.deepEqual(errors, [], 'exceção não tratada dentro da página');
    });
    const w = dom.window;
    const calls = [];
    const toasts = [];
    const routes = [];
    const modals = [];
    const drawers = [];
    // route(matcher, responder): o primeiro que casar responde; responder devolve {status, body}.
    const route = (matcher, responder) => routes.push({matcher, responder});
    w.fetch = (url, options = {}) => {
        const entry = {url, method: options.method || 'GET', body: options.body, headers: options.headers || {}};
        calls.push(entry);
        const found = routes.find(r => (typeof r.matcher === 'string' ? url.startsWith(r.matcher) : r.matcher.test(url)));
        const reply = found ? found.responder(entry) : {status: 404, body: {success: false, message: 'sem rota'}};
        return Promise.resolve({ok: reply.status >= 200 && reply.status < 300, status: reply.status, json: async () => reply.body});
    };
    w.LPSAjax = {announce: message => toasts.push(message)};
    if (modal) w.LPSModal = {open: (url, options) => { modals.push({url, options}); return Promise.resolve(); }};
    if (drawer) w.LPSDrawer = {open: url => { drawers.push(url); return Promise.resolve(); }};
    w.eval(picker);
    w.eval(kanban);
    const $ = selector => w.document.querySelector(selector);
    const $$ = selector => Array.from(w.document.querySelectorAll(selector));
    const click = (element, init = {}) => {
        const event = new w.MouseEvent('click', {bubbles: true, cancelable: true, button: 0, ...init});
        element.dispatchEvent(event);
        return event;
    };
    const drag = (type, target, init = {}) => {
        const event = new w.Event(type, {bubbles: true, cancelable: true});
        Object.defineProperty(event, 'dataTransfer', {value: {setData() {}, effectAllowed: '', dropEffect: ''}});
        Object.assign(event, init);
        target.dispatchEvent(event);
        return event;
    };
    const col = stage => $(`[data-kanban-column][data-stage-id="${stage}"]`);
    const countOf = stage => col(stage).querySelector('[data-column-count]').textContent;
    const ids = stage => Array.from(col(stage).querySelectorAll('[data-kanban-card]')).map(c => c.dataset.itemId);
    const body = call => Object.fromEntries(call.body.entries());
    return {w, $, $$, click, drag, col, countOf, ids, body, calls, toasts, route, modals, drawers, navigations};
}

const movedCard = (id, stage) => card(id, stage).replace('class="kanban-card"', 'class="kanban-card" data-fresh="1"');

// -- arrastar -----------------------------------------------------------------------------------------

test('dropping a card on another column saves only the stage and keeps the card there', async t => {
    const k = setup(t);
    k.route('/kanban/demandas/1/etapa/', () => ({status: 200, body: {success: true, message: 'Etapa alterada para Pronto.', stage_id: 12, card_html: movedCard(1, 12)}}));
    const cardEl = k.$('[data-item-id="1"]');
    k.drag('dragstart', cardEl);
    assert.equal(k.drag('dragover', k.col(12).querySelector('[data-dropzone]')).defaultPrevented, true);
    assert.deepEqual(k.ids(12), ['1']);
    k.drag('drop', k.col(12).querySelector('[data-dropzone]'));
    await settle();
    assert.equal(k.calls.length, 1);
    assert.equal(k.calls[0].method, 'POST');
    assert.equal(k.calls[0].url, '/kanban/demandas/1/etapa/');
    assert.deepEqual(k.body(k.calls[0]), {stage_id: '12'});
    assert.equal(k.calls[0].headers['X-Requested-With'], 'XMLHttpRequest');
    assert.deepEqual(k.ids(12), ['1']);
    assert.equal(k.$('[data-item-id="1"]').dataset.fresh, '1', 'o cartão foi trocado pelo HTML do servidor');
    assert.equal(k.countOf(12), '1');
    assert.equal(k.countOf(10), '1');
    assert.deepEqual(k.toasts, ['Etapa alterada para Pronto.']);
});

test('when the server refuses, the card goes back where it was and the reason is shown', async t => {
    const k = setup(t);
    k.route('/kanban/demandas/1/etapa/', () => ({status: 403, body: {success: false, message: 'A etapa escolhida não pertence ao setor atual.'}}));
    k.drag('dragstart', k.$('[data-item-id="1"]'));
    k.drag('dragover', k.col(12).querySelector('[data-dropzone]'));
    k.drag('drop', k.col(12).querySelector('[data-dropzone]'));
    await settle();
    assert.deepEqual(k.ids(10), ['1', '2'], 'voltou para a mesma posição');
    assert.deepEqual(k.ids(12), []);
    assert.equal(k.countOf(10), '2');
    assert.equal(k.countOf(12), '0');
    assert.deepEqual(k.toasts, ['A etapa escolhida não pertence ao setor atual.']);
});

test('dropping on the same column does not call the server', async t => {
    const k = setup(t);
    k.drag('dragstart', k.$('[data-item-id="1"]'));
    k.drag('dragover', k.col(10).querySelector('[data-dropzone]'));
    k.drag('drop', k.col(10).querySelector('[data-dropzone]'));
    await settle();
    assert.equal(k.calls.length, 0);
});

test('"Sem etapa" is never a destination', async t => {
    const k = setup(t);
    k.drag('dragstart', k.$('[data-item-id="1"]'));
    const zone = k.$('[data-unassigned] [data-dropzone]');
    assert.equal(k.drag('dragover', zone).defaultPrevented, false);
    k.drag('drop', zone);
    await settle();
    assert.equal(k.calls.length, 0);
    assert.deepEqual(k.ids(10), ['1', '2']);
});

test('a card the person cannot move does not start a drag', async t => {
    const k = setup(t);
    k.drag('dragstart', k.$('[data-item-id="2"]'));
    k.drag('dragover', k.col(12).querySelector('[data-dropzone]'));
    k.drag('drop', k.col(12).querySelector('[data-dropzone]'));
    await settle();
    assert.equal(k.calls.length, 0);
    assert.deepEqual(k.ids(10), ['1', '2']);
});

// -- contadores ------------------------------------------------------------------------------------------

test('the counter shows the limit and turns red above it; the empty note follows the column', async t => {
    const k = setup(t);
    k.route('/kanban/demandas/1/etapa/', () => ({status: 200, body: {success: true, message: 'ok', stage_id: 11, card_html: card(1, 11)}}));
    assert.equal(k.countOf(11), '1 de 1');
    k.drag('dragstart', k.$('[data-item-id="1"]'));
    k.drag('dragover', k.col(11).querySelector('[data-dropzone]'));
    k.drag('drop', k.col(11).querySelector('[data-dropzone]'));
    await settle();
    assert.equal(k.countOf(11), '2 de 1');
    assert.equal(k.col(11).querySelector('[data-column-count]').classList.contains('is-over'), true);
    assert.equal(k.col(12).querySelector('[data-column-empty]').hidden, false);
    assert.equal(k.col(11).querySelector('[data-column-empty]').hidden, true);
});

test('"Sem etapa" disappears once nothing is left to classify', async t => {
    const k = setup(t);
    k.route('/kanban/demandas/9/etapa/', () => ({status: 200, body: {success: true, message: 'ok', stage_id: 12, card_html: card(9, 12)}}));
    k.drag('dragstart', k.$('[data-item-id="9"]'));
    k.drag('dragover', k.col(12).querySelector('[data-dropzone]'));
    k.drag('drop', k.col(12).querySelector('[data-dropzone]'));
    await settle();
    assert.equal(k.$('[data-unassigned]'), null);
    assert.deepEqual(k.ids(12), ['9']);
});

test('"Sem etapa" stays while a refused move still needs to put the card back', async t => {
    const k = setup(t);
    k.route('/kanban/demandas/9/etapa/', () => ({status: 403, body: {success: false, message: 'Sem permissão.'}}));
    k.drag('dragstart', k.$('[data-item-id="9"]'));
    k.drag('dragover', k.col(12).querySelector('[data-dropzone]'));
    k.drag('drop', k.col(12).querySelector('[data-dropzone]'));
    await settle();
    assert.notEqual(k.$('[data-unassigned]'), null);
    assert.deepEqual(Array.from(k.$('[data-unassigned]').querySelectorAll('[data-kanban-card]')).map(c => c.dataset.itemId), ['9']);
});

// -- criar na coluna -----------------------------------------------------------------------------------------

test('"+" opens a name field; Enter creates the demand in that column and puts the card on top', async t => {
    const k = setup(t);
    k.route('/kanban/demandas/criar/', () => ({status: 201, body: {success: true, message: 'Demanda criada.', id: 20, stage_id: 12, card_html: card(20, 12, {title: 'Nova'})}}));
    k.click(k.col(12).querySelector('[data-inline-create]'));
    const input = k.col(12).querySelector('.kanban-inline-create input');
    assert.ok(input, 'campo de nome aberto');
    input.value = '  Nova  ';
    input.dispatchEvent(new k.w.KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true}));
    await settle();
    assert.deepEqual(k.body(k.calls[0]), {title: 'Nova', stage_id: '12', sector_id: '1'});
    assert.equal(k.col(12).querySelector('.kanban-inline-create'), null);
    assert.deepEqual(k.ids(12), ['20']);
    assert.equal(k.countOf(12), '1');
    assert.deepEqual(k.toasts, ['Demanda criada.']);
});

test('Escape and an empty name cancel without calling the server', async t => {
    const k = setup(t);
    k.click(k.col(12).querySelector('[data-inline-create]'));
    let input = k.col(12).querySelector('.kanban-inline-create input');
    input.dispatchEvent(new k.w.KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
    assert.equal(k.col(12).querySelector('.kanban-inline-create'), null);
    k.click(k.col(12).querySelector('[data-inline-create]'));
    input = k.col(12).querySelector('.kanban-inline-create input');
    input.value = '   ';
    input.dispatchEvent(new k.w.KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true}));
    assert.equal(k.col(12).querySelector('.kanban-inline-create'), null);
    assert.equal(k.calls.length, 0);
});

test('a failed creation keeps what was typed and shows the reason', async t => {
    const k = setup(t);
    k.route('/kanban/demandas/criar/', () => ({status: 403, body: {success: false, message: 'Você não pode criar demandas neste setor.'}}));
    k.click(k.col(12).querySelector('[data-inline-create]'));
    const input = k.col(12).querySelector('.kanban-inline-create input');
    input.value = 'Minha demanda';
    input.dispatchEvent(new k.w.KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true}));
    await settle();
    assert.equal(k.col(12).querySelector('.kanban-inline-create input').value, 'Minha demanda');
    assert.equal(k.col(12).querySelector('.kanban-inline-create input').disabled, false);
    assert.deepEqual(k.toasts, ['Você não pode criar demandas neste setor.']);
    assert.deepEqual(k.ids(12), []);
});

test('clicking "+" twice does not open two fields', t => {
    const k = setup(t);
    const trigger = k.col(12).querySelector('[data-inline-create]');
    k.click(trigger);
    k.click(trigger);
    assert.equal(k.col(12).querySelectorAll('.kanban-inline-create').length, 1);
});

// -- limite -----------------------------------------------------------------------------------------------

test('setting the limit posts it and refreshes the counter', async t => {
    const k = setup(t);
    k.route('/kanban/demandas/limite/', () => ({status: 200, body: {success: true, limit: 3, message: 'Limite da coluna definido em 3.'}}));
    k.click(k.col(10).querySelector('[data-set-limit]'));
    const form = k.$('.kanban-limit-pop form');
    assert.ok(form);
    form.querySelector('input').value = '3';
    form.dispatchEvent(new k.w.Event('submit', {bubbles: true, cancelable: true}));
    await settle();
    assert.deepEqual(k.body(k.calls[0]), {stage_id: '10', limit: '3'});
    assert.equal(k.col(10).dataset.limit, '3');
    assert.equal(k.countOf(10), '2 de 3');
    assert.equal(k.$('.kanban-limit-pop'), null);
});

test('removing the limit sends it empty and goes back to the plain count', async t => {
    const k = setup(t);
    k.route('/kanban/demandas/limite/', () => ({status: 200, body: {success: true, limit: null, message: 'Limite da coluna removido.'}}));
    k.click(k.col(11).querySelector('[data-set-limit]'));
    k.click(Array.from(k.$$('.kanban-limit-pop button')).find(b => /Remover/.test(b.textContent)));
    await settle();
    assert.deepEqual(k.body(k.calls[0]), {stage_id: '11', limit: ''});
    assert.equal(k.countOf(11), '1');
});

test('a refused limit shows the reason and keeps the form', async t => {
    const k = setup(t);
    k.route('/kanban/demandas/limite/', () => ({status: 403, body: {success: false, message: 'Você não pode gerir as etapas deste setor.'}}));
    k.click(k.col(10).querySelector('[data-set-limit]'));
    const form = k.$('.kanban-limit-pop form');
    form.querySelector('input').value = '2';
    form.dispatchEvent(new k.w.Event('submit', {bubbles: true, cancelable: true}));
    await settle();
    assert.ok(k.$('.kanban-limit-pop'));
    assert.deepEqual(k.toasts, ['Você não pode gerir as etapas deste setor.']);
});

// -- gaveta ------------------------------------------------------------------------------------------------

test('clicking the title opens the drawer instead of navigating', t => {
    const k = setup(t);
    const event = k.click(k.$('[data-item-id="1"] .kanban-card__title'));
    assert.equal(event.defaultPrevented, true);
    assert.deepEqual(k.drawers, ['/demandas/1/gaveta/']);
});

test('modifier keys keep the normal link; without the drawer the link works', t => {
    const k = setup(t);
    for (const init of [{ctrlKey: true}, {metaKey: true}, {shiftKey: true}, {altKey: true}, {button: 1}]) {
        assert.equal(k.click(k.$('[data-item-id="1"] .kanban-card__title'), init).defaultPrevented, false, JSON.stringify(init));
    }
    assert.equal(k.drawers.length, 0);
    const bare = setup(t, {drawer: false});
    assert.equal(bare.click(bare.$('[data-item-id="1"] .kanban-card__title')).defaultPrevented, false);
});

test('clicking the card body opens the drawer, clicking its controls does not', async t => {
    const k = setup(t);
    k.click(k.$('[data-item-id="3"] .meta'));
    assert.deepEqual(k.drawers, ['/demandas/3/gaveta/']);
    k.click(k.$('[data-item-id="3"] summary'));
    k.click(k.$('#mover-3'));
    assert.equal(k.drawers.length, 1);
    await settle();
});

test('when the drawer closes the card is read again with the same filters', async t => {
    const k = setup(t, {search: '?setor=1&q=aurora'});
    k.route(/^\/kanban\/demandas\/1\/cartao\//, () => ({status: 200, body: {success: true, visible: true, stage_id: 10, card_html: movedCard(1, 10)}}));
    k.click(k.$('[data-item-id="1"] .kanban-card__title'));
    const backdrop = k.w.document.createElement('div');
    backdrop.className = 'drawer-backdrop';
    k.w.document.body.appendChild(backdrop);
    await settle();
    assert.equal(k.calls.length, 0, 'aberta: nada a reler ainda');
    backdrop.remove();
    await settle();
    assert.equal(k.calls.length, 1);
    assert.equal(k.calls[0].url, '/kanban/demandas/1/cartao/?setor=1&q=aurora');
    assert.equal(k.$('[data-item-id="1"]').dataset.fresh, '1');
});

test('a card that left the board when the drawer closes is removed and the count follows', async t => {
    const k = setup(t);
    k.route(/^\/kanban\/demandas\/3\/cartao\//, () => ({status: 200, body: {success: true, visible: false}}));
    k.click(k.$('[data-item-id="3"] .kanban-card__title'));
    const backdrop = k.w.document.createElement('div');
    backdrop.className = 'drawer-backdrop';
    k.w.document.body.appendChild(backdrop);
    await settle();
    backdrop.remove();
    await settle();
    assert.equal(k.$('[data-item-id="3"]'), null);
    assert.equal(k.countOf(11), '0 de 1');
});

// -- menus e ações -----------------------------------------------------------------------------------------

test('copy name writes to the clipboard and says so', async t => {
    const k = setup(t);
    const copied = [];
    Object.defineProperty(k.w.navigator, 'clipboard', {value: {writeText: text => { copied.push(text); return Promise.resolve(); }}, configurable: true});
    k.$('[data-item-id="1"] details').setAttribute('open', '');
    k.click(k.$('[data-item-id="1"] [data-copy-text]'));
    await settle();
    assert.deepEqual(copied, ['Item 1']);
    assert.deepEqual(k.toasts, ['Copiado.']);
    assert.equal(k.$('[data-item-id="1"] details').hasAttribute('open'), false);
});

test('an action posts to the server and then re-reads the card', async t => {
    const k = setup(t);
    k.route('/tarefas/1/concluir/ajax/', () => ({status: 200, body: {success: true, message: 'Tarefa concluída.'}}));
    k.route(/^\/kanban\/demandas\/1\/cartao\//, () => ({status: 200, body: {success: true, visible: false}}));
    k.click(k.$('[data-item-id="1"] [data-kanban-post]'));
    await settle();
    assert.equal(k.calls[0].method, 'POST');
    assert.equal(k.calls[0].url, '/tarefas/1/concluir/ajax/');
    assert.equal(k.calls[1].method, 'GET');
    assert.equal(k.$('[data-item-id="1"]'), null);
    assert.deepEqual(k.toasts, ['Tarefa concluída.']);
});

test('an action the server refuses shows its message', async t => {
    const k = setup(t);
    k.route('/tarefas/1/concluir/ajax/', () => ({status: 400, body: {success: false, message: 'Esta tarefa não pode ser concluída no status atual.'}}));
    k.route(/^\/kanban\/demandas\/1\/cartao\//, () => ({status: 200, body: {success: true, visible: true, stage_id: 10, card_html: card(1, 10)}}));
    k.click(k.$('[data-item-id="1"] [data-kanban-post]'));
    await settle();
    assert.deepEqual(k.toasts, ['Esta tarefa não pode ser concluída no status atual.']);
});

test('actions with a window open it and reload the board when done, ahead of the generic handler', t => {
    const k = setup(t);
    let reached = false;
    k.w.document.addEventListener('click', () => { reached = true; });
    const event = k.click(k.$('#cancelar-1'));
    assert.equal(event.defaultPrevented, true);
    assert.equal(reached, false, 'não segue para os outros tratadores de clique');
    assert.equal(k.modals.length, 1);
    assert.equal(k.modals[0].url, '/demandas/1/cancelar/');
    k.modals[0].options.onSuccess({redirect_url: '/qualquer/'});
    assert.equal(k.navigations.length, 1, 'recarregou o quadro');
});

test('the header "Nova tarefa" button opens in a window and reloads', t => {
    const k = setup(t);
    assert.equal(k.click(k.$('#nova-tarefa')).defaultPrevented, true);
    assert.equal(k.modals[0].url, '/tarefas/nova-rapida/');
});

test('clicking outside closes an open card menu; Escape closes menus and popovers', t => {
    const k = setup(t);
    const menu = k.$('[data-item-id="1"] details');
    menu.setAttribute('open', '');
    k.click(k.$('.meta'));
    assert.equal(menu.hasAttribute('open'), false);
    menu.setAttribute('open', '');
    const pop = k.$('[data-kanban-pop]');
    pop.setAttribute('open', '');
    k.w.document.dispatchEvent(new k.w.KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
    assert.equal(menu.hasAttribute('open'), false);
    assert.equal(pop.hasAttribute('open'), false);
});

test('only one toolbar popover is open at a time', async t => {
    const k = setup(t);
    const [first, second] = k.$$('[data-kanban-pop]');
    first.open = true;
    first.dispatchEvent(new k.w.Event('toggle'));
    second.open = true;
    second.dispatchEvent(new k.w.Event('toggle'));
    await settle();
    assert.equal(first.hasAttribute('open'), false);
    assert.equal(second.hasAttribute('open'), true);
});

// -- barra ---------------------------------------------------------------------------------------------------

test('changing the sector or an auto-apply popover submits the filters; other popovers wait for "Aplicar"', t => {
    const k = setup(t);
    const form = k.$('[data-kanban-toolbar]');
    let submits = 0;
    form.requestSubmit = () => { submits += 1; };
    k.$('[data-kanban-sector]').dispatchEvent(new k.w.Event('change', {bubbles: true}));
    assert.equal(submits, 1);
    k.$('#pessoa-eu').dispatchEvent(new k.w.Event('change', {bubbles: true}));
    assert.equal(submits, 2);
    k.$('#bloqueio').dispatchEvent(new k.w.Event('change', {bubbles: true}));
    assert.equal(submits, 2);
});

// -- seletor de etapa/status ---------------------------------------------------------------------------------

const PICKER_PAGE = `${PAGE}
<div class="drawer-backdrop"><button type="button" id="etapa" class="workflow-value" data-workflow-picker data-kind="stage" data-domain="demandas"
  data-item-id="1" data-sector-id="1" data-options-url="/api/setores/1/etapas/?dominio=demanda" data-set-url="/kanban/demandas/1/etapa/"
  data-current-id="10" data-create-url="/kanban/demandas/opcoes/" data-manage-url="/configuracoes/etapas-e-status/?domain=demandas&sector=1" data-can-create="1">
  <span data-workflow-label>A fazer</span></button>
  <button type="button" id="condicao" class="workflow-value" data-workflow-picker data-kind="condition" data-domain="demandas"
  data-item-id="1" data-sector-id="1" data-options-url="/api/setores/1/condicoes/?dominio=demanda" data-set-url="/kanban/demandas/1/condicao/"
  data-current-id="5" data-allow-clear="1" data-create-url="/kanban/demandas/opcoes/"><span data-workflow-label>Normal</span></button>
  <button type="button" id="travado" disabled data-workflow-picker data-kind="stage" data-options-url="/x"></button></div>`;

const STAGES = {items: [{id: 10, name: 'A fazer', color: '#94A3B8'}, {id: 11, name: 'Levantamento', color: '#3B82F6'}, {id: 12, name: 'Pronto', color: '#22C55E'}]};
const CONDITIONS = {items: [{id: 5, name: 'Normal', color: '#3B82F6'}, {id: 6, name: 'Aguardando cliente', color: '#F59E0B'}]};

function pickerSetup(t) {
    const k = setup(t, {html: PICKER_PAGE});
    k.stageList = STAGES;
    k.route('/api/setores/1/etapas/', () => ({status: 200, body: k.stageList}));
    k.route('/api/setores/1/condicoes/', () => ({status: 200, body: CONDITIONS}));
    return k;
}

test('the picker lists the options of the sector and marks the current one', async t => {
    const k = pickerSetup(t);
    k.click(k.$('#etapa'));
    await settle();
    const options = k.$$('.workflow-pop__option');
    assert.deepEqual(options.slice(0, 3).map(o => o.textContent.replace('✓', '').trim()), ['A fazer', 'Levantamento', 'Pronto']);
    assert.equal(options[0].classList.contains('is-current'), true);
    assert.equal(k.calls[0].url, '/api/setores/1/etapas/?dominio=demanda');
    assert.equal(k.$('#etapa').getAttribute('aria-expanded'), 'true');
});

test('choosing an option saves it, updates the button and tells the board', async t => {
    const k = pickerSetup(t);
    k.route('/kanban/demandas/1/etapa/', () => ({status: 200, body: {success: true, message: 'Etapa alterada para Pronto.', stage_id: 12, stage_name: 'Pronto', card_html: movedCard(1, 12)}}));
    const heard = [];
    k.w.document.addEventListener('lps:workflow-changed', event => heard.push(event.detail));
    k.click(k.$('#etapa'));
    await settle();
    k.click(k.$$('.workflow-pop__option')[2]);
    await settle();
    const post = k.calls.find(c => c.method === 'POST');
    assert.deepEqual(k.body(post), {stage_id: '12'});
    assert.equal(k.$('#etapa [data-workflow-label]').textContent, 'Pronto');
    assert.equal(k.$('#etapa').dataset.currentId, '12');
    assert.equal(k.$('.workflow-pop'), null, 'o seletor fechou');
    assert.equal(heard.length, 1);
    assert.equal(heard[0].domain, 'demandas');
    assert.equal(heard[0].kind, 'stage');
    assert.deepEqual(k.ids(12), ['1'], 'o quadro levou o cartão para a coluna nova');
    assert.deepEqual(k.toasts, ['Etapa alterada para Pronto.']);
});

test('a refused choice shows the reason and leaves the button as it was', async t => {
    const k = pickerSetup(t);
    k.route('/kanban/demandas/1/etapa/', () => ({status: 403, body: {success: false, message: 'Você não pode mudar a etapa.'}}));
    k.click(k.$('#etapa'));
    await settle();
    k.click(k.$$('.workflow-pop__option')[1]);
    await settle();
    assert.equal(k.$('#etapa [data-workflow-label]').textContent, 'A fazer');
    assert.equal(k.$('#etapa').dataset.currentId, '10');
    assert.equal(k.$('#etapa').disabled, false);
    assert.deepEqual(k.toasts, ['Você não pode mudar a etapa.']);
});

test('a condition can be cleared', async t => {
    const k = pickerSetup(t);
    k.route('/kanban/demandas/1/condicao/', () => ({status: 200, body: {success: true, message: 'Status removida.', condition_name: '', card_html: card(1, 10)}}));
    k.click(k.$('#condicao'));
    await settle();
    const clear = k.$$('.workflow-pop__option').find(o => /Sem status/.test(o.textContent));
    assert.ok(clear, 'oferece "Sem status"');
    k.click(clear);
    await settle();
    assert.deepEqual(k.body(k.calls.find(c => c.method === 'POST')), {condition_id: ''});
    assert.equal(k.$('#condicao [data-workflow-label]').textContent, 'Sem status');
});

test('a stage cannot be cleared: there is no empty option', async t => {
    const k = pickerSetup(t);
    k.click(k.$('#etapa'));
    await settle();
    assert.equal(k.$$('.workflow-pop__option').some(o => /Sem etapa/.test(o.textContent)), false);
});

test('who manages the catalog sees "+ Nova etapa" and "Gerenciar"; others do not', async t => {
    const k = pickerSetup(t);
    k.click(k.$('#etapa'));
    await settle();
    assert.ok(k.$$('.workflow-pop__option').some(o => /\+ Nova etapa/.test(o.textContent)));
    assert.equal(k.$('.workflow-pop__link').getAttribute('href'), '/configuracoes/etapas-e-status/?domain=demandas&sector=1');
    k.w.LPSWorkflowPicker.close();
    k.click(k.$('#condicao'));
    await settle();
    assert.equal(k.$$('.workflow-pop__option').some(o => /Nova status/.test(o.textContent)), false);
    assert.equal(k.$('.workflow-pop__link'), null);
});

test('creating a stage in place posts the name and color, then lists it', async t => {
    const k = pickerSetup(t);
    const created = {items: [...STAGES.items, {id: 13, name: 'Revisão', color: '#22C55E'}]};
    k.route('/kanban/demandas/opcoes/', () => ({status: 201, body: {success: true, message: 'Etapa criada.', item: {id: 13, name: 'Revisão', color: '#22C55E'}}}));
    k.click(k.$('#etapa'));
    await settle();
    k.click(k.$$('.workflow-pop__option').find(o => /\+ Nova etapa/.test(o.textContent)));
    const form = k.$('.workflow-pop form');
    assert.ok(form);
    form.querySelector('input[type=text]').value = 'Revisão';
    form.querySelectorAll('.workflow-pop__swatch')[1].click();
    k.stageList = created;
    form.dispatchEvent(new k.w.Event('submit', {bubbles: true, cancelable: true}));
    await settle();
    const post = k.calls.find(c => c.url === '/kanban/demandas/opcoes/');
    assert.deepEqual(k.body(post), {kind: 'stage', name: 'Revisão', color: '#22C55E', sector_id: '1'});
    assert.ok(k.$$('.workflow-pop__option').some(o => /Revisão/.test(o.textContent)), 'a opção nova aparece na lista');
    assert.deepEqual(k.toasts, ['Etapa criada.']);
});

test('a refused creation shows the reason inside the form', async t => {
    const k = pickerSetup(t);
    k.route('/kanban/demandas/opcoes/', () => ({status: 400, body: {success: false, message: 'Já existe uma opção com o nome “Pronto” neste setor.'}}));
    k.click(k.$('#etapa'));
    await settle();
    k.click(k.$$('.workflow-pop__option').find(o => /\+ Nova etapa/.test(o.textContent)));
    const form = k.$('.workflow-pop form');
    form.querySelector('input[type=text]').value = 'Pronto';
    form.dispatchEvent(new k.w.Event('submit', {bubbles: true, cancelable: true}));
    await settle();
    const error = k.$('.workflow-pop__error');
    assert.equal(error.hidden, false);
    assert.match(error.textContent, /Já existe/);
    assert.equal(form.querySelector('button[type=submit]').disabled, false);
});

test('Escape and an outside click close the picker; clicking the button again toggles it', async t => {
    const k = pickerSetup(t);
    k.click(k.$('#etapa'));
    await settle();
    k.w.document.dispatchEvent(new k.w.KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true}));
    assert.equal(k.$('.workflow-pop'), null);
    k.click(k.$('#etapa'));
    await settle();
    k.w.document.body.dispatchEvent(new k.w.MouseEvent('mousedown', {bubbles: true}));
    assert.equal(k.$('.workflow-pop'), null);
    k.click(k.$('#etapa'));
    k.click(k.$('#etapa'));
    assert.equal(k.$('.workflow-pop'), null);
});

test('a disabled picker button does nothing', async t => {
    const k = pickerSetup(t);
    k.click(k.$('#travado'));
    await settle();
    assert.equal(k.$('.workflow-pop'), null);
    assert.equal(k.calls.length, 0);
});

test('if the options cannot be loaded the picker says so', async t => {
    const k = setup(t, {html: PICKER_PAGE});
    k.route('/api/setores/1/etapas/', () => ({status: 404, body: {detail: 'Setor não encontrado.'}}));
    k.click(k.$('#etapa'));
    await settle();
    assert.match(k.$('.workflow-pop').textContent, /Setor não encontrado/);
});

test('the card condition chip opens the same picker from inside the board', async t => {
    const chip = `<button type="button" class="condition-chip" id="chip" data-workflow-picker data-kind="condition" data-domain="demandas" data-item-id="1" data-sector-id="1"
        data-options-url="/api/setores/1/condicoes/?dominio=demanda" data-set-url="/kanban/demandas/1/condicao/" data-current-id="5">Normal</button>`;
    const html = PAGE.replace(card(1, 10), card(1, 10).replace('<span class="meta">texto</span>', `<span class="meta">texto</span>${chip}`));
    const k = setup(t, {html});
    k.route('/api/setores/1/condicoes/', () => ({status: 200, body: CONDITIONS}));
    k.route('/kanban/demandas/1/condicao/', () => ({status: 200, body: {success: true, message: 'Status alterada para Aguardando cliente.', condition_name: 'Aguardando cliente', card_html: movedCard(1, 10)}}));
    k.click(k.$('#chip'));
    await settle();
    assert.equal(k.drawers.length, 0, 'o clique no chip não abre a gaveta');
    k.click(k.$$('.workflow-pop__option')[1]);
    await settle();
    assert.equal(k.$('[data-kanban-card][data-item-id="1"]').dataset.fresh, '1', 'o cartão foi trocado pelo HTML novo');
    assert.equal(k.$$('[data-kanban-card][data-item-id="1"]').length, 1, 'sem cartão duplicado');
});

test('the picker works on pages that have no board (drawer on the demand sheet)', async t => {
    const k = setup(t, {html: PICKER_PAGE.replace(/<section data-kanban-board>[\s\S]*<\/section>/, '').replace(/<div id="kanban-config"[\s\S]*?<\/div>/, '')});
    k.route('/api/setores/1/etapas/', () => ({status: 200, body: STAGES}));
    k.click(k.$('#etapa'));
    await settle();
    assert.equal(k.$$('.workflow-pop__option').length > 0, true);
});
