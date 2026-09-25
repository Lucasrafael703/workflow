/* Modal via JS: busca um formulário existente (fetch) e o injeta por cima da
   tela atual, sem navegar. Reaproveita o HTML de ".modal-backdrop" que as
   telas de cadastro já renderizam — aqui ele só ganha vida sem redirect.
   window.LPSModal.open(url, {onSuccess}) devolve o JSON de sucesso da view. */
(function () {
    "use strict";

    var current = null;

    function close() {
        if (!current) return;
        current.remove();
        current = null;
        document.removeEventListener("keydown", onKeydown);
    }

    function onKeydown(event) {
        if (event.key === "Escape") close();
    }

    function extractModal(html) {
        var wrapper = document.createElement("div");
        wrapper.innerHTML = html;
        return wrapper.querySelector(".modal-backdrop");
    }

    function bindForm(backdrop, onSuccess, sourceUrl) {
        var form = backdrop.querySelector("form");
        if (!form) return;

        form.addEventListener("submit", function (event) {
            event.preventDefault();
            var submitButton = form.querySelector("[type=submit]");
            if (submitButton) submitButton.disabled = true;

            fetch(sourceUrl, {
                method: "POST",
                headers: { "X-Requested-With": "XMLHttpRequest" },
                body: new FormData(form),
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        return { ok: response.ok, data: data };
                    });
                })
                .then(function (result) {
                    if (!result.ok) {
                        renderErrors(form, result.data.errors || {});
                        if (submitButton) submitButton.disabled = false;
                        return;
                    }
                    close();
                    if (typeof onSuccess === "function") onSuccess(result.data);
                })
                .catch(function () {
                    if (submitButton) submitButton.disabled = false;
                });
        });
    }

    function renderErrors(form, errors) {
        form.querySelectorAll(".errorlist").forEach(function (el) { el.remove(); });
        Object.keys(errors).forEach(function (fieldName) {
            var field = form.querySelector("[name='" + fieldName + "']");
            var row = field ? field.closest(".form-row") : null;
            var target = row || form;
            var list = document.createElement("ul");
            list.className = "errorlist";
            errors[fieldName].forEach(function (message) {
                var item = document.createElement("li");
                item.textContent = typeof message === "string" ? message : message.message;
                list.appendChild(item);
            });
            target.appendChild(list);
        });
    }

    function open(url, options) {
        options = options || {};
        return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (response) { return response.text(); })
            .then(function (html) {
                var backdrop = extractModal(html);
                if (!backdrop) return;

                backdrop.classList.add("js-modal-backdrop");
                backdrop.addEventListener("click", function (event) {
                    if (event.target === backdrop) close();
                });
                var closeButton = backdrop.querySelector(".modal__close");
                if (closeButton) {
                    closeButton.setAttribute("type", "button");
                    closeButton.removeAttribute("href");
                    closeButton.addEventListener("click", function (event) {
                        event.preventDefault();
                        close();
                    });
                }
                var cancelLink = backdrop.querySelector(".modal__foot a.btn");
                if (cancelLink) {
                    cancelLink.addEventListener("click", function (event) {
                        event.preventDefault();
                        close();
                    });
                }

                bindForm(backdrop, options.onSuccess, url);

                close();
                document.body.appendChild(backdrop);
                current = backdrop;
                document.addEventListener("keydown", onKeydown);

                // Widgets como PersonPickerWidget/TagPickerWidget/RichTextWidget
                // só ligam seus listeners uma vez, no carregamento da página —
                // um formulário injetado agora precisa que cada um se
                // reinicialize dentro deste backdrop específico.
                (window.LPSWidgets || []).forEach(function (initIn) { initIn(backdrop); });

                var firstField = backdrop.querySelector(".modal__body input, .modal__body select, .modal__body textarea");
                if (firstField) firstField.focus();
            });
    }

    window.LPSModal = { open: open, close: close };
})();
