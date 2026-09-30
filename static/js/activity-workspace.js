/* Identical short actions from the collection and from the activity workspace. */
(function () {
    "use strict";
    document.querySelectorAll("[data-activity-filters] [data-auto-submit]").forEach(function (field) {
        field.addEventListener("change", function () { field.form.requestSubmit(); });
    });
    document.addEventListener("click", function (event) {
        var link = event.target.closest("a[data-activity-action]");
        if (!link || !window.LPSModal || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        window.LPSModal.open(link.href, {
            onSuccess: function (result) {
                // Criar/editar atividade (data-activity-navigate) segue para a página que o servidor indicou;
                // as demais ações curtas só recarregam a tela em que estavam.
                if (link.hasAttribute("data-activity-navigate") && result && result.redirect_url) {
                    window.location.assign(result.redirect_url);
                } else {
                    window.location.reload();
                }
            }
        }).catch(function () {
            // The full-page form is also usable if loading the dialog fails.
            window.location.assign(link.href);
        });
    });

    document.addEventListener("submit", async function (event) {
        var form = event.target.closest("[data-editor-attachment-remove]");
        if (!form) return;
        event.preventDefault();
        if (form.dataset.busy || !window.confirm("Remover este anexo?")) return;
        var row = document.getElementById(form.dataset.attachmentRow);
        if (!row) return;
        form.dataset.busy = "true";
        var button = row.querySelector("button");
        button.disabled = true;
        var oldError = row.querySelector("[role=alert]");
        if (oldError) oldError.remove();
        try {
            var response = await fetch(form.action, {
                method: "POST", headers: {"X-Requested-With": "XMLHttpRequest"}, body: new FormData(form)
            });
            if (!(response.headers.get("content-type") || "").includes("application/json")) {
                throw new Error("Não foi possível remover o anexo. Verifique sua conexão ou sessão.");
            }
            var result = await response.json();
            if (!response.ok) throw new Error(result.error || "Não foi possível remover o anexo.");
            row.remove();
            form.remove();
        } catch (error) {
            var message = document.createElement("span");
            message.setAttribute("role", "alert");
            message.className = "errorlist";
            message.textContent = error.message;
            row.appendChild(message);
        } finally {
            delete form.dataset.busy;
            button.disabled = false;
        }
    });
})();
