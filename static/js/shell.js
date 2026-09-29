/* Comportamentos da casca: menu no celular e janelas de ação.
   Tudo aqui é conforto — sem JS o menu continua acessível e as janelas
   continuam sendo páginas normais com links reais de fechar. */
(function () {
    "use strict";

    // Menu recolhível (desktop): estado persiste entre páginas via
    // localStorage. O <script> no <head> já aplicou a classe antes do
    // primeiro paint — aqui só liga o clique e mantém o texto/aria em dia.
    var collapseButton = document.querySelector("[data-sidebar-collapse]");
    if (collapseButton) {
        var STORAGE_KEY = "lps-sidebar-collapsed";

        function syncCollapseButton(collapsed) {
            var label = collapsed ? "Expandir menu" : "Recolher menu";
            collapseButton.setAttribute("title", label);
            collapseButton.setAttribute("aria-label", label);
            collapseButton.setAttribute("aria-pressed", String(collapsed));
        }

        syncCollapseButton(document.documentElement.classList.contains("sidebar--collapsed"));

        collapseButton.addEventListener("click", function () {
            var collapsed = document.documentElement.classList.toggle("sidebar--collapsed");
            localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
            syncCollapseButton(collapsed);
        });
    }

    // Tooltip de texto dos itens simples (Início, Fila, Notificações...)
    // quando o menu está recolhido: mesmo motivo do flyout abaixo — a
    // sidebar tem overflow-y:auto, que corta o ::after se ele for
    // position:absolute. Aqui basta calcular a posição real do ícone e
    // escrever nas custom properties que o CSS já lê (--tooltip-left/-top);
    // o ::after em si continua sendo position:fixed puro, sem precisar
    // mover nenhum elemento do DOM.
    document.querySelectorAll(".nav-item[data-tooltip]").forEach(function (item) {
        function updatePosition() {
            var rect = item.getBoundingClientRect();
            item.style.setProperty("--tooltip-left", (rect.right + 10) + "px");
            item.style.setProperty("--tooltip-top", (rect.top + rect.height / 2 - 15) + "px");
        }
        item.addEventListener("mouseenter", updatePosition);
        item.addEventListener("focus", updatePosition);
    });

    // Flyout dos grupos (Atividades, Tarefas, Cadastros...) quando o menu
    // está recolhido: a sidebar tem overflow-y:auto, que corta qualquer
    // position:absolute além da sua largura — por isso o flyout é movido
    // para o <body> (portal) enquanto aberto, posicionado por coordenadas
    // reais do ícone, e devolvido ao lugar original ao fechar.
    document.querySelectorAll(".nav-group").forEach(function (group) {
        var flyout = group.querySelector(".nav-group__flyout");
        if (!flyout) return;

        var placeholder = document.createComment("nav-group__flyout-anchor");
        var closeTimer = null;

        function isCollapsed() {
            return document.documentElement.classList.contains("sidebar--collapsed");
        }

        function open() {
            if (!isCollapsed()) return;
            clearTimeout(closeTimer);
            if (!flyout.parentElement || flyout.parentElement !== document.body) {
                flyout.parentNode.insertBefore(placeholder, flyout);
                document.body.appendChild(flyout);
            }
            var rect = group.getBoundingClientRect();
            flyout.style.left = (rect.right + 10) + "px";
            flyout.style.top = rect.top + "px";
            flyout.classList.add("is-open");
        }

        function scheduleClose() {
            clearTimeout(closeTimer);
            closeTimer = setTimeout(close, 120);
        }

        function close() {
            flyout.classList.remove("is-open");
            if (placeholder.parentNode) {
                placeholder.parentNode.insertBefore(flyout, placeholder);
                placeholder.remove();
            }
        }

        group.addEventListener("mouseenter", open);
        group.addEventListener("mouseleave", scheduleClose);
        flyout.addEventListener("mouseenter", function () { clearTimeout(closeTimer); });
        flyout.addEventListener("mouseleave", scheduleClose);
        group.addEventListener("focusin", open);
        group.addEventListener("focusout", function (event) {
            if (!group.contains(event.relatedTarget) && !flyout.contains(event.relatedTarget)) {
                close();
            }
        });
    });

    // Recolher o menu fecha qualquer flyout aberto e some com o portal.
    var collapseObserver = new MutationObserver(function () {
        if (!document.documentElement.classList.contains("sidebar--collapsed")) {
            document.querySelectorAll(".nav-group__flyout.is-open").forEach(function (flyout) {
                flyout.classList.remove("is-open");
            });
        }
    });
    collapseObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

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

    // Popup de tarefas em execução na topbar: mesmo padrão do menu de
    // notificações acima (toggle, fecha ao clicar fora ou Esc). Pausar/
    // Concluir reaproveitam os endpoints ajax já usados pelo menu "⋮" das
    // listas de tarefa — sucesso recarrega a página, que já traz o popup
    // atualizado via o context processor global.
    var timerToggle = document.querySelector("[data-timer-menu-toggle]");
    if (timerToggle) {
        var timerMenu = document.querySelector("[data-timer-menu]");

        function closeTimerMenu() {
            timerMenu.hidden = true;
            timerToggle.setAttribute("aria-expanded", "false");
        }

        timerToggle.addEventListener("click", function (event) {
            event.stopPropagation();
            var abrindo = timerMenu.hidden;
            timerMenu.hidden = !abrindo;
            timerToggle.setAttribute("aria-expanded", String(abrindo));
        });
        document.addEventListener("click", function (event) {
            if (!timerToggle.contains(event.target) && !timerMenu.contains(event.target)) closeTimerMenu();
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") closeTimerMenu();
        });

        function csrfToken() {
            var match = document.cookie.match(/csrftoken=([^;]+)/);
            return match ? match[1] : "";
        }

        timerMenu.querySelectorAll(".js-timer-ajax").forEach(function (button) {
            button.addEventListener("click", function (event) {
                event.stopPropagation();
                button.disabled = true;
                fetch(button.dataset.url, {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRFToken": csrfToken(),
                    },
                })
                    .then(function (response) { return response.json().then(function (data) { return { ok: response.ok, data: data }; }); })
                    .then(function (result) {
                        if (!result.ok) {
                            alert(result.data.error || "Não foi possível concluir a ação.");
                            button.disabled = false;
                            return;
                        }
                        window.location.reload();
                    })
                    .catch(function () { button.disabled = false; });
            });
        });
    }

    // Popover "+N participantes" nas listas/cards de tarefa: um por linha,
    // só um aberto por vez, mesmo padrão do menu de notificações acima.
    var participantsToggles = document.querySelectorAll(".participants-popover__trigger");
    if (participantsToggles.length) {
        function fecharTodosParticipantes(exceto) {
            document.querySelectorAll(".participants-popover__menu").forEach(function (menu) {
                if (menu !== exceto) menu.hidden = true;
            });
        }

        participantsToggles.forEach(function (btn) {
            var menu = btn.nextElementSibling;
            btn.addEventListener("click", function (event) {
                event.stopPropagation();
                var abrindo = menu.hidden;
                fecharTodosParticipantes(abrindo ? menu : null);
                menu.hidden = !abrindo;
            });
        });

        document.addEventListener("click", function () { fecharTodosParticipantes(null); });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") fecharTodosParticipantes(null);
        });
    }
})();
