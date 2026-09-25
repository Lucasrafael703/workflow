// Cronômetro da sessão de trabalho em andamento.
// Conta localmente apenas para dar fluidez; o servidor continua sendo a
// referência de tempo (doc 09 §233) — o valor real vem de WorkSession.
// Registrado em LPSWidgets (mesmo padrão de person-picker.js): um relógio
// dentro do painel lateral só existe depois de um fetch dinâmico, então
// precisa de initIn(root) chamado de novo a cada injeção, não só no load.
(function () {
    "use strict";

    var clocks = [];
    var intervalStarted = false;

    function pad(value) {
        return String(value).padStart(2, "0");
    }

    function render(element, startedAt) {
        var elapsed = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
        var hours = Math.floor(elapsed / 3600);
        var minutes = Math.floor((elapsed % 3600) / 60);
        var seconds = elapsed % 60;
        element.textContent = pad(hours) + ":" + pad(minutes) + ":" + pad(seconds);
    }

    function ensureInterval() {
        if (intervalStarted) return;
        intervalStarted = true;
        setInterval(function () {
            clocks = clocks.filter(function (clock) { return clock.element.isConnected; });
            clocks.forEach(function (clock) { render(clock.element, clock.startedAt); });
        }, 1000);
    }

    function initIn(root) {
        root.querySelectorAll("[data-started-at]:not([data-timer-ready])").forEach(function (element) {
            var startedAt = Date.parse(element.dataset.startedAt);
            if (isNaN(startedAt)) return;
            element.setAttribute("data-timer-ready", "1");
            clocks.push({ element: element, startedAt: startedAt });
            render(element, startedAt);
        });
        if (clocks.length) ensureInterval();
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);

    initIn(document);
})();
