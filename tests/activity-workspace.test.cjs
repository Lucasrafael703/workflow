const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
const code=readFileSync(path.join(__dirname,'../static/js/activity-workspace.js'),'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const markup=`<form id="editor"><input value="Alteração ainda não salva"></form><ul><li id="attachment-1"><button form="remove">Remover</button></li></ul><form hidden id="remove" method="post" action="/delete/" data-editor-attachment-remove data-attachment-row="attachment-1"></form>`;

test('removing an attachment preserves the unsaved editor',async()=>{
 const dom=new JSDOM(markup,{url:'http://localhost/',runScripts:'outside-only'});
 const w=dom.window;w.confirm=()=>true;
 w.fetch=async()=>({ok:true,headers:{get:()=> 'application/json'},json:async()=>({removed:1})});
 w.eval(code);
 w.document.getElementById('remove').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
 await tick();
 assert.equal(w.document.getElementById('attachment-1'),null);
 assert.equal(w.document.querySelector('#editor input').value,'Alteração ainda não salva');
 dom.window.close();
});

test('rejected attachment removal keeps the item and offers retry',async()=>{
 const dom=new JSDOM(markup,{url:'http://localhost/',runScripts:'outside-only'});
 const w=dom.window;w.confirm=()=>true;
 w.fetch=async()=>({ok:false,headers:{get:()=> 'application/json'},json:async()=>({error:'Sem permissão'})});
 w.eval(code);
 w.document.getElementById('remove').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
 await tick();
 assert.match(w.document.querySelector('[role=alert]').textContent,/Sem permissão/);
 assert.equal(w.document.querySelector('li button').disabled,false);
 assert.ok(w.document.getElementById('attachment-1'));
 dom.window.close();
});

test('every collection uses the same filter submission behavior',()=>{
 const dom=new JSDOM('<form data-activity-filters><select data-auto-submit><option>Aberta</option></select></form>',{runScripts:'outside-only'});
 const w=dom.window;let submitted=0;
 w.document.querySelector('form').requestSubmit=()=>submitted++;
 w.eval(code);
 w.document.querySelector('select').dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.equal(submitted,1);
 dom.window.close();
});

test('activity search submits after debounce and Enter submits immediately',async()=>{
 const dom=new JSDOM('<form data-activity-filters><input data-activity-search value=""></form>',{runScripts:'outside-only'});
 const w=dom.window; let submitted=0;
 const form=w.document.querySelector('form');
 form.requestSubmit=()=>submitted++;
 w.eval(code);
 const search=w.document.querySelector('[data-activity-search]');
 search.value='Material';
 search.dispatchEvent(new w.Event('input',{bubbles:true}));
 assert.equal(submitted,0);
 await new Promise(resolve=>w.setTimeout(resolve,380));
 assert.equal(submitted,1);
 search.value='Cliente';
 search.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
 assert.equal(submitted,2);
 dom.window.close();
});

test('activity filter setup is idempotent and binds every view form once',()=>{
 const dom=new JSDOM('<form data-activity-filters><select data-auto-submit><option>Lista</option></select></form><form data-activity-filters><select data-auto-submit><option>Kanban</option></select></form>',{runScripts:'outside-only'});
 const w=dom.window; let submitted=0;
 w.document.querySelectorAll('form').forEach(form=>{form.requestSubmit=()=>submitted++});
 w.eval(code);
 w.eval(code);
 w.document.querySelectorAll('select').forEach(select=>select.dispatchEvent(new w.Event('change',{bubbles:true})));
 assert.equal(submitted,2);
 dom.window.close();
});

test('standard ajax result replaces only the requested target and announces feedback',()=>{
 const dom=new JSDOM('<div id="task-1">Antigo</div>',{url:'http://localhost/',runScripts:'outside-only'});
 const w=dom.window;w.eval(code);
 const changed=w.LPSAjax.applyResult({success:true,target:'task-1',html:'<div id="task-1">Novo</div>'});
 w.LPSAjax.announce('Responsável alterado.');
 assert.equal(changed,true);
 assert.equal(w.document.getElementById('task-1').textContent,'Novo');
 assert.ok(w.document.getElementById('task-1').classList.contains('lps-row-updated'));
 assert.equal(w.document.querySelector('[role="status"]').textContent,'Responsável alterado.');
 dom.window.close();
});

test('standard ajax result removes only the requested target',()=>{
 const dom=new JSDOM('<div id="task-1">A</div><div id="task-2">B</div>',{runScripts:'outside-only'});
 const w=dom.window;w.eval(code);
 assert.equal(w.LPSAjax.applyResult({success:true,remove:'task-1'}),true);
 assert.equal(w.document.getElementById('task-1'),null);
 assert.equal(w.document.getElementById('task-2').textContent,'B');
 dom.window.close();
});
