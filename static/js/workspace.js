/* Workspace de Demandas (templates/workspace/*): comportamento da barra.

   Uma regra de interação, em uma frase: controles simples aplicam ao escolher; o painel "Filtros" é um RASCUNHO com um
   único "Aplicar filtros"; a busca aplica com Enter. Aqui:
   - [data-ws-nav] (Agrupar/Ordenar): ao escolher, vai para a URL da opção (o servidor guarda o estado na querystring);
   - [data-ws-panel]: o painel acumula as escolhas SEM recarregar; "Aplicar filtros" é o envio único. Fechar sem aplicar
     (Esc ou clicar fora) DESCARTA o rascunho: o painel volta ao que está de fato aplicado;
   - Setor → Etapa e Status: o painel só oferece as do setor escolhido (e limpa a escolha que deixou de valer);
   - busca: nada automático; só Enter/lupa (o formulário nativo);
   - foco e carregando: o foco volta ao controle usado depois de aplicar; `html.ws-loading` mostra a barra de progresso.
   O estado da tela é a URL; este script não guarda nada além do rascunho. */
(function () {
    "use strict";

    var FOCUS_KEY = "lps-ws-focus";
    var api = {
        // Trocar de página fica atrás de uma função só: o servidor guarda o estado na URL e o teste a substitui.
        navigate: function (url) { window.location.assign(url); }
    };

    function loading() {
        document.documentElement.classList.add("ws-loading");
    }

    // Lembra qual controle foi usado para devolver o foco depois da recarga.
    function rememberFocus(id) {
        try { window.sessionStorage.setItem(FOCUS_KEY, id); } catch (error) { /* sem storage: sem foco restaurado */ }
    }

    function restoreFocus(root) {
        var id = null;
        try { id = window.sessionStorage.getItem(FOCUS_KEY); window.sessionStorage.removeItem(FOCUS_KEY); } catch (error) { return; }
        if (!id) return;
        var target = root.querySelector("[data-ws-focus-id=\"" + id + "\"]");
        if (target && target.focus) target.focus();
    }

    // -- Agrupar / Ordenar: escolheu, aplicou ---------------------------------------------------

    function bindNav(root) {
        root.querySelectorAll("select[data-ws-nav]").forEach(function (select, index) {
            var id = "nav-" + index;
            select.setAttribute("data-ws-focus-id", id);
            select.addEventListener("change", function () {
                if (!select.value) return;
                rememberFocus(id);
                loading();
                api.navigate(select.value);
            });
        });
    }

    // -- Painel de filtros (rascunho) --------------------------------------------------------

    function filterBySector(select, sectorId) {
        // Reconstrói as opções com só os grupos do setor escolhido (ocultar <optgroup> não funciona em todo navegador).
        if (!select._wsAll) select._wsAll = Array.prototype.slice.call(select.children);
        var current = select.value;
        while (select.firstChild) select.removeChild(select.firstChild);
        select._wsAll.forEach(function (node) {
            if (node.tagName === "OPTGROUP" && sectorId && node.getAttribute("data-sector-id") !== String(sectorId)) return;
            select.appendChild(node);
        });
        var stillThere = Array.prototype.some.call(select.options, function (option) { return option.value === current; });
        select.value = stillThere ? current : "";
    }

    function bindSectorDependents(panel) {
        var sector = panel.querySelector("[data-ws-sector]");
        var dependents = panel.querySelectorAll("select[data-ws-dependent]");
        if (!sector || !dependents.length) return;
        function sync() {
            dependents.forEach(function (select) { filterBySector(select, sector.value); });
        }
        sector.addEventListener("change", sync);
        sync();
    }

    function bindPanel(root) {
        var panel = root.querySelector("[data-ws-panel]");
        var toggle = root.querySelector("[data-ws-panel-toggle]");
        if (!panel || !toggle) return;
        var body = panel.querySelector("[data-ws-panel-body]");
        var pristine = body.innerHTML; // o que está de fato aplicado: é para onde "descartar" volta

        function open() {
            panel.hidden = false;
            toggle.setAttribute("aria-expanded", "true");
        }
        function reinit() {
            bindSectorDependents(panel);
            // Seletores de Cliente/Obra (person-picker.js) precisam ser religados no conteúdo restaurado.
            (window.LPSWidgets || []).forEach(function (init) { try { init(panel); } catch (error) { /* widget opcional */ } });
        }
        function discard() {
            body.innerHTML = pristine;
            reinit();
        }
        function close(options) {
            if (panel.hidden) return;
            panel.hidden = true;
            toggle.setAttribute("aria-expanded", "false");
            if (!options || options.discard !== false) discard();
            if (options && options.focus) toggle.focus();
        }

        toggle.addEventListener("click", function () {
            if (panel.hidden) open(); else close({focus: true});
        });
        // Esc fecha (e descarta) de onde o foco estiver; com um seletor de Cliente/Obra aberto, o Esc é só dele.
        document.addEventListener("keydown", function (event) {
            if (event.key !== "Escape" || panel.hidden) return;
            if (panel.querySelector(".person-picker.is-open")) return;
            close({focus: true});
        });
        document.addEventListener("click", function (event) {
            if (panel.hidden) return;
            if (panel.contains(event.target) || toggle.contains(event.target)) return;
            // Clicar dentro de um popup de seletor (renderizado dentro do painel) não conta como "fora".
            if (event.target.closest && event.target.closest(".person-picker__popup")) return;
            close();
        });
        panel.addEventListener("submit", function () {
            rememberFocus("panel-toggle");
            loading();
        });
        toggle.setAttribute("data-ws-focus-id", "panel-toggle");
        bindSectorDependents(panel);
        // No celular o painel é uma folha inferior que cobre a tela: nunca abre sozinho, só pelo botão Filtros.
        if (!panel.hidden && window.matchMedia && window.matchMedia("(max-width: 760px)").matches) {
            panel.hidden = true;
            toggle.setAttribute("aria-expanded", "false");
        }
    }

    // -- Voltar da ficha sem perder o lugar (P1) ------------------------------------------------
    // O recorte já volta pela URL (o link da ficha leva `next=` com o endereço completo). Aqui só a posição de rolagem:
    // guardada por endereço antes de abrir uma demanda e restaurada uma vez quando a mesma lista volta.
    var SCROLL_PREFIX = "lps-ws-scroll:";

    function scrollKey() { return SCROLL_PREFIX + window.location.pathname + window.location.search; }

    function rememberScroll(root) {
        root.addEventListener("click", function (event) {
            var link = event.target.closest && event.target.closest("a[href]");
            if (!link || event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.button) return;
            if (!/\/demandas\/\d+\//.test(link.getAttribute("href") || "")) return; // só quem abre uma demanda
            try { window.sessionStorage.setItem(scrollKey(), String(window.scrollY || 0)); } catch (error) { /* sem storage */ }
        });
    }

    function restoreScroll() {
        var saved = null;
        try { saved = window.sessionStorage.getItem(scrollKey()); window.sessionStorage.removeItem(scrollKey()); } catch (error) { return; }
        var top = parseInt(saved, 10);
        if (!isNaN(top) && top > 0) window.scrollTo(0, top);
    }

    // -- Busca e links: só o estado de "carregando" ---------------------------------------------

    function bindLoading(root) {
        var search = root.querySelector("[data-ws-search]");
        if (search) search.addEventListener("submit", function () { rememberFocus("search"); loading(); });
        var input = root.querySelector("[data-ws-search] input[type=search]");
        if (input) input.setAttribute("data-ws-focus-id", "search");
        root.querySelectorAll(".ws-segment a, .ws__tab, .ws-chip a, .ws-chips__clear").forEach(function (link) {
            link.addEventListener("click", function (event) {
                if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.button) return;
                loading();
            });
        });
    }

    function init(root) {
        if (!root || root.getAttribute("data-ws-ready")) return null;
        root.setAttribute("data-ws-ready", "1");
        var bar = root.querySelector("[data-ws-bar]");
        if (bar) {
            bindNav(bar);
            bindPanel(bar);
        }
        bindLoading(root);
        rememberScroll(root);
        restoreFocus(root);
        restoreScroll();
        return root;
    }

    api.init = init;
    api.filterBySector = filterBySector;
    window.LPSWorkspace = api;
    document.querySelectorAll("[data-ws]").forEach(init);
    // Voltar pelo botão do navegador (bfcache) não pode deixar a barra de progresso ligada.
    window.addEventListener("pageshow", function () { document.documentElement.classList.remove("ws-loading"); });
})();
