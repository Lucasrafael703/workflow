/* Tela Tarefas (/tarefas/): "+ Adicionar" no fim da Lista e de cada coluna do Kanban.

   Abre um formulário pequeno no próprio lugar do botão: nome da tarefa + Demanda (só as Demandas em que a pessoa pode criar
   item, vindas do servidor em #task-center-add). Cria o item pelo endpoint do quadro (`board-item-create`, JSON): a
   regra, a autorização e a auditoria continuam no ItemService.create. A pessoa vira a responsável e o Status segue a coluna
   (A fazer = a etiqueta padrão, que o quadro já preenche; Em andamento / Concluídas = a etiqueta correspondente, se o quadro
   tiver). Erro (403/400) aparece no próprio formulário; sucesso recarrega a tela mantendo os filtros.
   Exporta window.LPSTaskCenter ({buildBody, init}) para os testes. */
(function () {
    "use strict";

    function csrfFromCookie(cookie) {
        var match = /(?:^|;\s*)csrftoken=([^;]+)/.exec(cookie || "");
        return match ? decodeURIComponent(match[1]) : "";
    }

    /** O corpo JSON do `board-item-create`: grupo, nome e valores iniciais (responsável e Status). */
    function buildBody(entry, name, state, me) {
        var initial = [];
        if (entry.person_column_id) initial.push({column_id: entry.person_column_id, value: me});
        var option = entry.status_options ? entry.status_options[state] : null;
        if (state !== "todo" && entry.status_column_id && option) initial.push({column_id: entry.status_column_id, value: option});
        return {group_id: entry.group_id, name: name, initial: initial};
    }

    function el(doc, tag, attrs, text) {
        var node = doc.createElement(tag);
        Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); });
        if (text) node.textContent = text;
        return node;
    }

    function init(doc, win) {
        var data = doc.getElementById("task-center-add");
        if (!data) return null;
        var payload;
        try { payload = JSON.parse(data.textContent); } catch (error) { return null; }
        var boards = payload.boards || [];

        function open(button) {
            var state = button.getAttribute("data-state") || "todo";
            var holder = button.parentNode;
            var form = el(doc, "form", {"class": "task-center__add-form", "data-task-add-form": ""});
            var name = el(doc, "input", {type: "text", maxlength: "200", placeholder: "Nome da tarefa", "aria-label": "Nome da tarefa", "class": "task-center__add-input"});
            var select = el(doc, "select", {"aria-label": "Demanda", "class": "task-center__add-select"});
            boards.forEach(function (entry) {
                var option = el(doc, "option", {value: String(entry.board_id)}, entry.label);
                select.appendChild(option);
            });
            var error = el(doc, "p", {role: "alert", "class": "task-center__add-error"});
            error.hidden = true;
            var save = el(doc, "button", {type: "submit", "class": "btn btn--primary btn--sm"}, "Adicionar");
            var cancel = el(doc, "button", {type: "button", "class": "btn btn--sm"}, "Cancelar");
            form.appendChild(name);
            form.appendChild(select);
            var actions = el(doc, "div", {"class": "task-center__add-actions"});
            actions.appendChild(save);
            actions.appendChild(cancel);
            form.appendChild(actions);
            form.appendChild(error);
            button.hidden = true;
            holder.appendChild(form);
            name.focus();

            function close() {
                if (form.parentNode) form.parentNode.removeChild(form);
                button.hidden = false;
                button.focus();
            }
            function fail(message) {
                error.textContent = message;
                error.hidden = false;
                save.disabled = false;
                cancel.disabled = false;
            }
            cancel.addEventListener("click", close);
            form.addEventListener("keydown", function (event) {
                if (event.key === "Escape") { event.stopPropagation(); close(); }
            });
            form.addEventListener("submit", function (event) {
                event.preventDefault();
                var value = name.value.trim();
                if (!value) { fail("Informe o nome da tarefa."); name.focus(); return; }
                var entry = boards.filter(function (item) { return String(item.board_id) === select.value; })[0];
                if (!entry) { fail("Escolha a demanda."); return; }
                error.hidden = true;
                save.disabled = true;
                cancel.disabled = true;
                var url = String(payload.url).replace(/\/0\//, "/" + entry.board_id + "/");
                win.fetch(url, {
                    method: "POST", credentials: "same-origin",
                    headers: {"Content-Type": "application/json", "X-CSRFToken": csrfFromCookie(doc.cookie), "X-Requested-With": "XMLHttpRequest"},
                    body: JSON.stringify(buildBody(entry, value, state, payload.me))
                }).then(function (response) {
                    return response.json().catch(function () { return {}; }).then(function (body) {
                        if (!response.ok || body.ok === false) throw new Error(body.error || "Não foi possível adicionar a tarefa.");
                        win.location.reload();
                    });
                }).catch(function (failure) {
                    fail(failure && failure.message ? failure.message : "Sem conexão com o servidor. Tente de novo.");
                });
            });
        }

        doc.addEventListener("click", function (event) {
            var button = event.target.closest && event.target.closest("[data-task-add]");
            if (!button || button.hidden) return;
            event.preventDefault();
            open(button);
        });
        return {open: open};
    }

    window.LPSTaskCenter = {buildBody: buildBody, init: init};
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { init(document, window); });
    else init(document, window);
})();
