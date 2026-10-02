/* Edição inline delegada e confirmada pelo servidor para quadros de domínio. */
(function () {
    "use strict";
    function csrf() { var m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : ""; }
    function toast(board, message, error) { var node = board.querySelector("[data-work-board-toast]"); if (!node) return; node.textContent = message; node.className = "work-board__toast is-visible" + (error ? " is-error" : ""); setTimeout(function () { node.className = "work-board__toast"; }, 3500); }
    function post(url, body) { return fetch(url, {method:"POST", headers:{"Content-Type":"application/json","Accept":"application/json","X-Requested-With":"XMLHttpRequest","X-CSRFToken":csrf()}, body:JSON.stringify(body)}).then(function (response) { return response.json().then(function (data) { return {ok:response.ok, data:data}; }); }); }
    function url(board, cell) { return "/quadros/dominio/" + board.dataset.boardId + "/campos/" + cell.dataset.fieldId + "/itens/" + cell.dataset.itemId + "/valor/"; }
    function editor(cell) {
        var choices = cell.querySelector("template[data-work-options]");
        var input = document.createElement(choices || cell.className.indexOf("priority") >= 0 ? "select" : "input");
        if (choices) { input.innerHTML = choices.innerHTML; }
        if (!choices && input.tagName === "SELECT") { ["BAIXA", "MEDIA", "ALTA"].forEach(function (v) { input.add(new Option(v.charAt(0) + v.slice(1).toLowerCase(), v, false, v === cell.dataset.value)); }); }
        else { input.type = cell.className.indexOf("datetime") >= 0 ? "datetime-local" : "text"; input.value = cell.className.indexOf("datetime") >= 0 ? (cell.dataset.value || "").slice(0,16) : (cell.dataset.value || ""); }
        input.className = "work-cell__editor"; input.setAttribute("aria-label", cell.getAttribute("aria-label")); return input;
    }
    function edit(board, cell) {
        if (cell.dataset.saving || cell.querySelector(".work-cell__editor")) return;
        var original = cell.innerHTML, input = editor(cell), row = cell.closest("[data-work-item]");
        function restore() { cell.innerHTML = original; }
        function save() { if (cell.dataset.saving) return; cell.dataset.saving="1"; input.disabled=true; post(url(board,cell), {value:input.value,updated_at:row ? row.dataset.workUpdatedAt : ""}).then(function (result) { if (!result.ok || !result.data.success) { restore(); toast(board,result.data.message || "Não foi possível salvar.",true); return; } var old=document.getElementById(result.data.target); if (old) { var holder=old.ownerDocument.createElement("tbody"); holder.innerHTML="<tr>"+result.data.html+"</tr>"; var replacement=holder.querySelector("td"); if (replacement) old.replaceWith(replacement); } if (row && result.data.updated_at) { row.dataset.workUpdatedAt=result.data.updated_at; row.classList.add("is-saved"); setTimeout(function(){row.classList.remove("is-saved");},1300); } toast(board,result.data.message || "Salvo."); }).catch(function(){restore();toast(board,"Não foi possível salvar.",true);}).finally(function(){delete cell.dataset.saving;}); }
        cell.innerHTML="";cell.appendChild(input);input.focus();if(input.select)input.select();input.addEventListener("keydown",function(e){if(e.key==="Escape"){e.preventDefault();restore();}if(e.key==="Enter"){e.preventDefault();save();}});input.addEventListener("blur",save,{once:true});
    }
    function initDrag(board) {
        var card, origin; board.addEventListener("dragstart",function(e){card=e.target.closest("[data-work-card]");if(!card)return;origin=card.parentElement;e.dataTransfer.setData("text/plain",card.dataset.itemId);}); board.addEventListener("dragover",function(e){if(e.target.closest("[data-work-card-list]"))e.preventDefault();}); board.addEventListener("drop",function(e){var list=e.target.closest("[data-work-card-list]"), field=board.querySelector("[data-work-group-field]");if(!list||!card||list===origin)return;e.preventDefault();if(!field){toast(board,"Esta visualização não possui agrupamento editável.",true);return;}list.appendChild(card);var lane=list.closest("[data-work-lane]");post("/quadros/dominio/"+board.dataset.boardId+"/campos/"+field.dataset.workGroupField+"/itens/"+card.dataset.itemId+"/valor/",{value:lane.dataset.groupKey==="empty"?"":lane.dataset.groupKey,updated_at:card.dataset.workUpdatedAt||""}).then(function(r){if(!r.ok||!r.data.success){origin.appendChild(card);toast(board,r.data.message||"Movimento não permitido.",true);}else toast(board,"Movimento salvo.");}).catch(function(){origin.appendChild(card);toast(board,"Não foi possível mover o cartão.",true);});});
    }
    document.addEventListener("DOMContentLoaded",function(){
        document.querySelectorAll("[data-work-board]").forEach(function(board){board.addEventListener("click",function(e){var cell=e.target.closest("[data-work-cell]");if(cell&&!e.target.closest("a,button,input,select"))edit(board,cell);var hide=e.target.closest("[data-work-hide-field]");if(hide)post("/quadros/dominio/visoes/"+board.dataset.viewId+"/campos/"+hide.dataset.workHideField+"/layout/",{is_visible:false}).then(function(r){if(r.ok)location.reload();});});board.addEventListener("keydown",function(e){var cell=e.target.closest("[data-work-cell]");if(cell&&(e.key==="Enter"||e.key===" ")){e.preventDefault();edit(board,cell);}});initDrag(board);});
        document.querySelectorAll("[data-work-card-settings]").forEach(function(b){b.addEventListener("click",function(){var p=document.querySelector("[data-work-card-settings-panel]");if(p){p.hidden=false;b.setAttribute("aria-expanded","true");}});});
        document.querySelectorAll("[data-work-add-field]").forEach(function(b){b.addEventListener("click",function(){var p=document.querySelector("[data-work-add-field-panel]");if(p){p.hidden=false;p.querySelector("input").focus();}});});
        document.querySelectorAll("[data-work-card-settings-close],[data-work-add-field-close]").forEach(function(b){b.addEventListener("click",function(){b.closest(".work-card-settings").hidden=true;});});
        document.querySelectorAll("[data-work-card-settings-form]").forEach(function(f){f.addEventListener("submit",function(e){e.preventDefault();var ids=[].map.call(f.querySelectorAll("input:checked"),function(i){return i.value;});post(f.dataset.url,{field_ids:ids}).then(function(r){if(r.ok)location.reload();});});});
        document.querySelectorAll("[data-work-add-field-form]").forEach(function(f){f.addEventListener("submit",function(e){e.preventDefault();post(f.dataset.url,{label:f.elements.label.value,type:f.elements.type.value}).then(function(r){if(r.ok)location.reload();});});});
        document.querySelectorAll("[data-work-group-by]").forEach(function(select){select.addEventListener("change",function(){post(select.dataset.url,{group_by:select.value}).then(function(r){if(r.ok)location.reload();});});});
        document.addEventListener("keydown",function(e){if(e.key==="Escape")document.querySelectorAll("[data-work-card-settings-panel],[data-work-add-field-panel]").forEach(function(p){p.hidden=true;});});
    });
})();
