// Cronômetro da sessão de trabalho em andamento.
// Conta localmente apenas para dar fluidez; o servidor continua sendo a
// referência de tempo (doc 09 §233) — o valor real vem de WorkSession.
(function () {
    "use strict";

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

    var elements = document.querySelectorAll("[data-started-at]");
    if (!elements.length) {
        return;
    }

    var clocks = [];
    elements.forEach(function (element) {
        var startedAt = Date.parse(element.dataset.startedAt);
        if (isNaN(startedAt)) {
            return;
        }
        clocks.push({ element: element, startedAt: startedAt });
        render(element, startedAt);
    });

    if (clocks.length) {
        setInterval(function () {
            clocks.forEach(function (clock) {
                render(clock.element, clock.startedAt);
            });
        }, 1000);
    }
})();
