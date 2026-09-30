/* Reuse server-rendered forms as dialogs, preserving the calling page. */
(function () {
    "use strict";
    var stack = [];
    var loading = 0;
    var originalOverflow = "";
    function current() { return stack[stack.length - 1]; }
    function focusable(element) {
        return Array.from(element.querySelectorAll("a[href], button:not([disabled]), input:not([disabled]):not([type=hidden]), select:not([disabled]), textarea:not([disabled]), [tabindex='0']"))
            .filter(function (node) { return node.getClientRects().length && !node.closest("[hidden]"); });
    }
    function close() {
        var item = current();
        if (!item || item.busy) return;
        loading += 1;
        stack.pop();
        item.element.remove();
        if (current()) current().element.hidden = false;
        else {
            document.body.style.overflow = originalOverflow;
            document.removeEventListener("keydown", onKeydown);
        }
        if (item.opener && item.opener.isConnected) item.opener.focus();
    }
    function onKeydown(event) {
        var item = current();
        if (!item) return;
        if (event.key === "Escape") { event.preventDefault(); close(); }
        if (event.key !== "Tab") return;
        var nodes = focusable(item.element);
        if (!nodes.length) { event.preventDefault(); return; }
        var first = nodes[0], last = nodes[nodes.length - 1];
        if (event.shiftKey && (document.activeElement === first || !item.element.contains(document.activeElement))) {
            event.preventDefault(); last.focus();
        } else if (!event.shiftKey && (document.activeElement === last || !item.element.contains(document.activeElement))) {
            event.preventDefault(); first.focus();
        }
    }
    function extractModal(html) {
        return new DOMParser().parseFromString(html, "text/html").querySelector(".modal-backdrop");
    }
    function renderErrors(form, errors) {
        form.querySelectorAll(".errorlist, .modal-error").forEach(function (el) { el.remove(); });
        var firstTarget = null;
        Object.keys(errors).forEach(function (name) {
            var field = form.elements.namedItem(name) || form.elements.namedItem(name + "_0");
            if (field && !field.closest) field = field[0];
            var row = field && field.closest(".form-row");
            var target = row || form.querySelector(".modal__body") || form;
            var list = document.createElement("ul");
            list.className = "errorlist";
            list.setAttribute("role", "alert");
            errors[name].forEach(function (error) {
                var li = document.createElement("li");
                li.textContent = typeof error === "string" ? error : error.message;
                list.appendChild(li);
            });
            target.appendChild(list);
            var details = target.closest("details");
            if (details) details.open = true;
            if (field && !firstTarget) firstTarget = field;
        });
        if (firstTarget) firstTarget.focus();
    }
    function setBusy(item, busy) {
        item.busy = busy;
        item.element.setAttribute("aria-busy", String(busy));
        item.element.querySelectorAll("button[type=submit], input[type=submit]").forEach(function (button) { button.disabled = busy; });
    }
    function initialize(item) {
        var element = item.element;
        var dialog = element.querySelector(".modal");
        dialog.setAttribute("role", "dialog");
        dialog.setAttribute("aria-modal", "true");
        var title = dialog.querySelector("h1, h2");
        if (title) dialog.setAttribute("aria-label", title.textContent.trim());
        element.classList.add("js-modal-backdrop");
        element.addEventListener("click", function (event) {
            if (event.target === element) close();
        });
        element.querySelectorAll(".modal__close, .modal__foot a.btn").forEach(function (button) {
            button.addEventListener("click", function (event) { event.preventDefault(); close(); });
        });
        var form = element.querySelector("form");
        if (form) form.addEventListener("submit", async function (event) {
            event.preventDefault();
            if (item.busy) return;
            var data = new FormData(form);
            if (event.submitter && event.submitter.name) data.append(event.submitter.name, event.submitter.value);
            setBusy(item, true);
            try {
                var response = await fetch(form.getAttribute("action") || item.url, {
                    method: "POST", headers: {"X-Requested-With": "XMLHttpRequest"}, body: data
                });
                if (!(response.headers.get("content-type") || "").includes("application/json")) {
                    throw new Error("Não foi possível confirmar a operação. Verifique sua conexão ou sessão e tente novamente.");
                }
                var result = await response.json();
                if (!response.ok) {
                    renderErrors(form, result.errors || {__all__: ["Não foi possível salvar. Tente novamente."]});
                    return;
                }
                setBusy(item, false);
                close();
                if (typeof item.onSuccess === "function") item.onSuccess(result);
            } catch (error) {
                renderErrors(form, {__all__: [error.message || "Não foi possível salvar. Tente novamente."]});
            } finally { setBusy(item, false); }
        });
        (window.LPSWidgets || []).forEach(function (init) { init(element); });
        var first = element.querySelector("[autofocus]") || focusable(element)[0];
        if (first) first.focus();
    }
    async function open(url, options) {
        options = options || {};
        var token = ++loading;
        var opener = document.activeElement;
        var response = await fetch(url, {headers: {"X-Requested-With": "XMLHttpRequest"}});
        if (!response.ok || response.redirected) throw new Error("Formulário indisponível.");
        var element = extractModal(await response.text());
        if (!element) throw new Error("Formulário indisponível.");
        if (token !== loading) return;
        if (current()) current().element.hidden = true;
        else {
            originalOverflow = document.body.style.overflow;
            document.body.style.overflow = "hidden";
            document.addEventListener("keydown", onKeydown);
        }
        var item = {element: element, url: url, opener: opener, onSuccess: options.onSuccess, busy: false};
        stack.push(item);
        document.body.appendChild(element);
        initialize(item);
    }
    window.LPSModal = {open: open, close: close};
})();
