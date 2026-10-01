/* Identical short actions from the collection and from the activity workspace. */
(function () {
    "use strict";
    function targetElement(value) {
        if (!value) return null;
        if (value.charAt(0) === "#") return document.querySelector(value);
        return document.getElementById(value) || document.querySelector(value);
    }

    function applyResult(result) {
        if (!result) return false;
        var changed = false;
        if (result.remove) {
            var removable = targetElement(result.remove);
            if (removable) { removable.remove(); changed = true; }
        }
        if (result.html && result.target) {
            var target = targetElement(result.target);
            if (target) {
                var wrapper = document.createElement("template");
                wrapper.innerHTML = result.html.trim();
                var replacement = wrapper.content.firstElementChild;
                if (replacement) {
                    replacement.classList.add("lps-row-updated");
                    target.replaceWith(replacement);
                    window.setTimeout(function () { replacement.classList.remove("lps-row-updated"); }, 1900);
                    changed = true;
                }
            }
        }
        if (result.html && result.refresh_scope) {
            var scope = targetElement(result.refresh_scope);
            if (scope) { scope.innerHTML = result.html; changed = true; }
        }
        return changed;
    }

    function announce(message) {
        if (!message) return;
        var region = document.querySelector(".lps-toast-region");
        if (!region) {
            region = document.createElement("div");
            region.className = "lps-toast-region";
            region.setAttribute("role", "status");
            region.setAttribute("aria-live", "polite");
            document.body.appendChild(region);
        }
        var toast = document.createElement("div");
        toast.className = "lps-toast";
        toast.textContent = message;
        region.appendChild(toast);
        window.setTimeout(function () { toast.remove(); }, 4000);
    }

    window.LPSAjax = { applyResult: applyResult, announce: announce };

    function submitFilterForm(form) {
        if (!form || form.dataset.filterSubmitting === "true") return;
        form.dataset.filterSubmitting = "true";
        if (typeof form.requestSubmit === "function") form.requestSubmit();
        else form.submit();
    }

    function setupActivityFilters(form) {
        if (!form || form.dataset.activityFiltersBound === "true") return;
        form.dataset.activityFiltersBound = "true";

        form.querySelectorAll("[data-auto-submit]").forEach(function (field) {
            field.addEventListener("change", function () { submitFilterForm(form); });
        });

    }

    document.querySelectorAll("[data-activity-filters]").forEach(setupActivityFilters);
    document.addEventListener("click", function (event) {
        var link = event.target.closest("a[data-activity-action]");
        if (!link || !window.LPSModal || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        window.LPSModal.open(link.href, {
            onSuccess: function (result) {
                if (result && result.message) announce(result.message);
                if (applyResult(result)) return;
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
