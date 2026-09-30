const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const path = require("node:path");
const {JSDOM} = require("jsdom");
const script = readFileSync(path.join(__dirname, "../static/js/modal.js"), "utf8");
const html = `<div class="modal-backdrop"><div class="modal"><h2>Ação da atividade</h2><button class="modal__close">Fechar</button><form><div class="modal__body"><details><summary>Contexto</summary><div class="form-row"><input name="title" value="Trabalho em andamento"></div></details></div><div class="modal__foot"><a class="btn" href="/atividades/">Voltar</a><button type="submit" name="acao" value="publicar">Salvar</button></div></form></div></div>`;
function setup(fetch) {
    const dom = new JSDOM('<button id="opener">Abrir</button>', {url:'http://localhost/', runScripts:'outside-only'});
    dom.window.fetch = fetch;
    dom.window.eval(script);
    dom.window.document.getElementById('opener').focus();
    return dom;
}
function getResponse() { return {ok:true,redirected:false,text:async()=>html}; }
function jsonResponse(ok, data) { return {ok,headers:{get:()=> 'application/json'},json:async()=>data}; }
const tick = () => new Promise(resolve => setImmediate(resolve));
function submit(window) {
    const form = window.document.querySelector('.js-modal-backdrop:not([hidden]) form');
    form.dispatchEvent(new window.SubmitEvent('submit', {bubbles:true,cancelable:true,submitter:form.querySelector('button[type=submit]')}));
}

test('validation keeps user input, expands erroneous section, and allows retry', async () => {
    const dom = setup(async (url, options) => options.method ? jsonResponse(false,{errors:{title:['Revise o nome']}}) : getResponse());
    const w = dom.window;
    await w.LPSModal.open('/action/');
    submit(w); await tick();
    assert.equal(w.document.querySelector('input').value, 'Trabalho em andamento');
    assert.equal(w.document.querySelector('details').open, true);
    assert.match(w.document.querySelector('.errorlist').textContent,/Revise/);
    assert.equal(w.document.querySelector('[type=submit]').disabled,false);
    dom.window.close();
});

test('duplicate submits produce one request and preserve the clicked action', async () => {
    let finish, calls=0, sent;
    const dom = setup(async (url, options) => {
        if (!options.method) return getResponse();
        calls++; sent=options.body.get('acao');
        return new Promise(resolve=> {finish=resolve;});
    });
    const w=dom.window; let saved=0;
    await w.LPSModal.open('/action/',{onSuccess:()=>saved++});
    submit(w); submit(w);
    assert.equal(calls,1); assert.equal(sent,'publicar');
    w.LPSModal.close();
    assert.ok(w.document.querySelector('.modal'));
    finish(jsonResponse(true,{id:1})); await tick();
    assert.equal(saved,1); assert.equal(w.document.querySelector('.modal'),null);
    assert.equal(w.document.activeElement.id,'opener');
    dom.window.close();
});

test('nested picker returns to the existing form without losing its values', async () => {
    const dom=setup(async()=>getResponse()); const w=dom.window;
    await w.LPSModal.open('/parent/');
    const parent=w.document.querySelector('.modal-backdrop');
    parent.querySelector('input').value='Não perder';
    await w.LPSModal.open('/child/');
    assert.equal(parent.hidden,true);
    w.LPSModal.close();
    assert.equal(parent.hidden,false);
    assert.equal(parent.querySelector('input').value,'Não perder');
    assert.equal(w.document.querySelectorAll('.modal-backdrop').length,1);
    dom.window.close();
});

test('failed network submission remains open with visible feedback', async () => {
    const dom=setup(async(url,options)=> {
        if (options.method) throw new Error('Conexão interrompida');
        return getResponse();
    });
    await dom.window.LPSModal.open('/action/');
    submit(dom.window); await tick();
    assert.match(dom.window.document.querySelector('.errorlist').textContent,/Conexão/);
    assert.ok(dom.window.document.querySelector('.modal'));
    dom.window.close();
});

test('an expired login page is not treated as a successfully loaded dialog', async () => {
    const dom=setup(async()=>({ok:true,redirected:true}));
    await assert.rejects(dom.window.LPSModal.open('/action/'),/indisponível/);
    assert.equal(dom.window.document.querySelector('.modal'),null);
    dom.window.close();
});
