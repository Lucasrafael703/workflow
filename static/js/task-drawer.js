/* Painel lateral de uma tarefa: abre por cima da ficha da atividade sem
   navegar para fora dela — ao contrário do modal, nunca fecha sozinho ao
   concluir uma ação interna (checklist, timer, comentário); só por X, Esc
   ou clique fora. window.LPSDrawer.open(url) recarrega o fragmento inteiro
   após qualquer ação bem-sucedida, em vez de manipular o DOM peça por peça. */
(function () {
    "use strict";

    var current = null;
    var currentUrl = null;

    function csrfToken() {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : "";
    }

    function close() {
        if (!current) return;
        current.remove();
        current = null;
        currentUrl = null;
        document.removeEventListener("keydown", onKeydown);
    }

    function onKeydown(event) {
        if (event.key === "Escape") close();
    }

    function extractDrawer(html) {
        var wrapper = document.createElement("div");
        wrapper.innerHTML = html;
        return wrapper.querySelector(".drawer-backdrop");
    }

    function reload() {
        if (currentUrl) open(currentUrl, { keepScroll: true });
    }

    function bindAjaxButtons(backdrop) {
        backdrop.querySelectorAll(".js-task-ajax").forEach(function (button) {
            button.addEventListener("click", function () {
                button.disabled = true;
                fetch(button.dataset.url, {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRFToken": csrfToken(),
                    },
                })
                    .then(function () { reload(); })
                    .catch(function () { button.disabled = false; });
            });
        });
    }

    function bindMessageForm(backdrop) {
        var form = backdrop.querySelector(".js-drawer-message");
        if (!form) return;
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            var submitButton = form.querySelector("[type=submit]");
            if (submitButton) submitButton.disabled = true;
            fetch(form.dataset.url, {
                method: "POST",
                headers: { "X-Requested-With": "XMLHttpRequest" },
                body: new FormData(form),
            })
                .then(function () { reload(); })
                .catch(function () {
                    if (submitButton) submitButton.disabled = false;
                });
        });
    }

    function open(url, options) {
        options = options || {};
        return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (response) { return response.text(); })
            .then(function (html) {
                var backdrop = extractDrawer(html);
                if (!backdrop) return;

                var scrollTop = options.keepScroll && current
                    ? current.querySelector(".drawer__body").scrollTop
                    : 0;

                backdrop.addEventListener("click", function (event) {
                    if (event.target === backdrop) close();
                });
                var closeButton = backdrop.querySelector(".js-drawer-close");
                if (closeButton) {
                    closeButton.addEventListener("click", function () { close(); });
                }

                bindAjaxButtons(backdrop);
                bindMessageForm(backdrop);

                if (current) current.remove();
                document.body.appendChild(backdrop);
                current = backdrop;
                currentUrl = url;
                document.addEventListener("keydown", onKeydown);

                (window.LPSWidgets || []).forEach(function (initIn) { initIn(backdrop); });

                var body = backdrop.querySelector(".drawer__body");
                if (body) body.scrollTop = scrollTop;
            });
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(".js-open-drawer").forEach(function (link) {
            link.addEventListener("click", function (event) {
                event.preventDefault();
                open(link.dataset.drawerUrl);
            });
        });
    });

    window.LPSDrawer = {
        open: open,
        close: close,
        reload: reload,
        isOpen: function (element) { return !!(current && current.contains(element)); },
    };
})();
