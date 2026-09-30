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
