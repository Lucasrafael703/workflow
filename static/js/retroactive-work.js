/* Janela "Já realizei este trabalho": só ajuda a preencher.
   - avisa quando a data é de um dia anterior (fica destacado no histórico);
   - mostra o comentário só quando ele é necessário: motivo "Outro", ou trabalho
     de mais de N dias atrás (justificativa).
   Nenhuma regra mora aqui: o servidor valida tudo em
   TaskService.register_completed_work. Sem JavaScript o comentário fica sempre
   visível e o formulário funciona do mesmo jeito. */
(function () {
    "use strict";

    function setup(box) {
        if (box.getAttribute("data-retro-ready")) return;
        var form = box.querySelector("form");
        var dateInput = form && form.querySelector("[name=date]");
        var noteRow = form && form.querySelector("[data-note-row]");
        if (!dateInput || !noteRow) return;
        box.setAttribute("data-retro-ready", "1");

        var justifyDays = parseInt(box.getAttribute("data-justify-days"), 10) || 7;
        var today = box.getAttribute("data-today") || "";
        var reasons = form.querySelectorAll("[name=reason]");
        var required = form.querySelector("[data-note-required]");
        var warning = form.querySelector("[data-past-day-warning]");

        // Dias inteiros entre a data escolhida e hoje (a data de hoje vem do servidor,
        // no fuso da organização — não do relógio do navegador).
        function daysBefore(iso) {
            if (!iso || !today) return 0;
            var a = Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
            var b = Date.UTC(+today.slice(0, 4), +today.slice(5, 7) - 1, +today.slice(8, 10));
            return Math.round((b - a) / 86400000);
        }

        function selectedReason() {
            for (var i = 0; i < reasons.length; i++) if (reasons[i].checked) return reasons[i].value;
            return "";
        }

        function refresh() {
            var days = daysBefore(dateInput.value);
            var needsNote = selectedReason() === "OUTRO" || days > justifyDays;
            if (warning) warning.hidden = !(days > 0);
            noteRow.hidden = !needsNote;
            if (required) required.hidden = !needsNote;
        }

        dateInput.addEventListener("input", refresh);
        dateInput.addEventListener("change", refresh);
        reasons.forEach(function (radio) { radio.addEventListener("change", refresh); });
        refresh();
    }

    function initIn(root) {
        (root || document).querySelectorAll("[data-retroactive-form]").forEach(setup);
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);
    initIn(document);
})();
