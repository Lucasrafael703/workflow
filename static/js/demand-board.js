/* Criação rápida exclusiva do Quadro de Demanda. O restante do workspace é o
   motor genérico de Quadros; aqui só há os campos obrigatórios do domínio. */
(function () {
    "use strict";

    function csrfToken(doc) {
        var match = /(?:^|;\s*)csrftoken=([^;]+)/.exec(doc.cookie || "");
        if (match) return decodeURIComponent(match[1]);
        var field = doc.querySelector("input[name=csrfmiddlewaretoken]");
        return field ? field.value : "";
    }

    function readMeta(doc) {
        var node = doc.getElementById("board-meta");
        try { return node ? JSON.parse(node.textContent) : null; } catch (_) { return null; }
    }

    function composerFor(node) {
        var addRow = node.closest("[data-add-row]");
        return addRow ? addRow.querySelector("[data-demand-task-composer]") : null;
    }

    function setError(form, message) {
        var error = form.querySelector("[data-demand-task-error]");
        if (!error) return;
        error.textContent = message || "";
        error.hidden = !message;
    }

    document.addEventListener("click", function (event) {
        var open = event.target.closest("[data-demand-task-open]");
        if (open) {
            var composer = composerFor(open);
            if (!composer) return;
            open.hidden = true;
            composer.hidden = false;
            var input = composer.querySelector("input[name=title]");
            if (input) input.focus();
            return;
        }

        var cancel = event.target.closest("[data-demand-task-cancel]");
        if (!cancel) return;
        var form = cancel.closest("[data-demand-task-add]");
        var taskComposer = form ? composerFor(cancel) : null;
        if (!form || !taskComposer) return;
        form.reset();
        setError(form, "");
        taskComposer.hidden = true;
        var trigger = taskComposer.closest("[data-add-row]").querySelector("[data-demand-task-open]");
        if (trigger) trigger.hidden = false;
    });

    document.addEventListener("submit", function (event) {
        var form = event.target.closest("[data-demand-task-add]");
        if (!form) return;
        event.preventDefault();
        var doc = form.ownerDocument, meta = readMeta(doc);
        if (!meta || !meta.urls || !meta.urls.item_create) return;
        var title = form.elements.title.value.trim();
        var responsavel = form.elements.responsavel_id.value;
        setError(form, "");
        if (!title || !responsavel) {
            form.reportValidity();
            return;
        }
        var submit = form.querySelector("button[type=submit]");
        if (submit) submit.disabled = true;
        window.fetch(meta.urls.item_create, {
            method: "POST", credentials: "same-origin",
            headers: {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrfToken(doc)},
            body: JSON.stringify({
                group_id: Number(form.dataset.groupId), name: title,
                responsavel_id: Number(responsavel),
                sector_id: form.elements.sector_id.value ? Number(form.elements.sector_id.value) : null
            })
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (body) {
                if (!response.ok || body.ok === false) throw new Error(body.error || "Não foi possível criar a tarefa.");
                window.location.reload();
            });
        }).catch(function (error) {
            setError(form, error.message || "Não foi possível criar a tarefa.");
        }).finally(function () {
            if (submit) submit.disabled = false;
        });
    });
}());
