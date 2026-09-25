/* Checklist de subtarefas de uma Task: mesmo bloco em task_detail.html (página
   completa) e no painel lateral (fragmento injetado) — por isso é um widget
   registrado em LPSWidgets (padrão de person-picker.js), não uma função presa
   a um dos dois contextos. Dentro do drawer aberto, recarrega só o fragmento;
   na página completa, recarrega a página inteira. */
(function () {
    "use strict";

    function csrfToken() {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : "";
    }

    function reloadAfter(anchorElement) {
        if (window.LPSDrawer && window.LPSDrawer.isOpen(anchorElement)) {
            window.LPSDrawer.reload();
        } else {
            window.location.reload();
        }
    }

    function initIn(root) {
        root.querySelectorAll(".js-checklist:not([data-checklist-ready])").forEach(function (list) {
            list.setAttribute("data-checklist-ready", "1");

            list.querySelectorAll(".js-checklist-toggle").forEach(function (checkbox) {
                checkbox.addEventListener("change", function () {
                    var item = checkbox.closest("[data-item-id]");
                    fetch(item.dataset.toggleUrl, {
                        method: "POST",
                        headers: {
                            "X-Requested-With": "XMLHttpRequest",
                            "X-CSRFToken": csrfToken(),
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                        body: "is_done=" + (checkbox.checked ? "1" : "0"),
                    })
                        .then(function () { reloadAfter(item); })
                        .catch(function () { checkbox.checked = !checkbox.checked; });
                });
            });

            list.querySelectorAll(".js-checklist-remove").forEach(function (button) {
                button.addEventListener("click", function () {
                    var item = button.closest("[data-item-id]");
                    fetch(item.dataset.removeUrl, {
                        method: "POST",
                        headers: {
                            "X-Requested-With": "XMLHttpRequest",
                            "X-CSRFToken": csrfToken(),
                        },
                    }).then(function () { reloadAfter(item); });
                });
            });
        });

        root.querySelectorAll(".js-checklist-add:not([data-checklist-ready])").forEach(function (addForm) {
            addForm.setAttribute("data-checklist-ready", "1");
            addForm.addEventListener("submit", function (event) {
                event.preventDefault();
                var input = addForm.querySelector("input[name=text]");
                if (!input.value.trim()) return;
                fetch(addForm.dataset.url, {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRFToken": csrfToken(),
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    body: "text=" + encodeURIComponent(input.value.trim()),
                }).then(function () { reloadAfter(addForm); });
            });
        });
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);

    initIn(document);
})();
