/* Comportamentos da casca: menu no celular e janelas de ação.
   Tudo aqui é conforto — sem JS o menu continua acessível e as janelas
   continuam sendo páginas normais com links reais de fechar. */
(function () {
    "use strict";

    var toggle = document.getElementById("nav-toggle");

    // Ao navegar no celular, o menu não deve continuar aberto por cima.
    if (toggle) {
        var sidebar = document.querySelector(".sidebar");
        if (sidebar) {
            sidebar.addEventListener("click", function (event) {
                if (event.target.closest("a")) toggle.checked = false;
            });
        }
    }

    // Esc fecha a janela de ação indo para o mesmo destino do botão Cancelar.
    var backdrop = document.querySelector(".modal-backdrop");
    if (backdrop) {
        var closer = backdrop.querySelector(".modal__close");

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && closer && closer.href) {
                window.location.href = closer.href;
            }
        });

        // Clique fora da janela equivale a fechar.
        backdrop.addEventListener("mousedown", function (event) {
            if (event.target === backdrop && closer && closer.href) {
                window.location.href = closer.href;
            }
        });

        // O foco começa no primeiro campo, para já poder digitar.
        var first = backdrop.querySelector(
            ".modal__body input:not([type=hidden]), .modal__body select, .modal__body textarea"
        );
        if (first) first.focus();
    }

    // Menu "mais opções" das notificações: um por linha, só um aberto por vez.
    // Sem JS o menu simplesmente não aparece — a ação principal ao lado
    // continua sendo um botão normal.
    var toggles = document.querySelectorAll("[data-notif-menu-toggle]");
    if (toggles.length) {
        function fecharTodos(exceto) {
            document.querySelectorAll("[data-notif-menu]").forEach(function (menu) {
                if (menu !== exceto) menu.hidden = true;
            });
            document.querySelectorAll("[data-notif-menu-toggle]").forEach(function (btn) {
                if (btn.getAttribute("aria-expanded") === "true" && btn.nextElementSibling !== exceto) {
                    btn.setAttribute("aria-expanded", "false");
                }
            });
        }

        toggles.forEach(function (btn) {
            var menu = btn.nextElementSibling;
            btn.addEventListener("click", function (event) {
                event.stopPropagation();
                var abrindo = menu.hidden;
                fecharTodos(abrindo ? menu : null);
                menu.hidden = !abrindo;
                btn.setAttribute("aria-expanded", String(abrindo));
            });
        });

        document.addEventListener("click", function () { fecharTodos(null); });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") fecharTodos(null);
        });
    }
})();
