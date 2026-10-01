/* Janela de tarefa (Nova / Editar): cartão da atividade escolhida e botão "Alterar".
   Nova tarefa fora de uma atividade tem um seletor; ao escolher, o seletor dá lugar a um
   cartão (título e "Cliente • Setor • N tarefas") e "Alterar" volta ao seletor, já aberto.
   Nenhuma regra mora aqui: o servidor valida a atividade e devolve o resumo na busca. */
(function () {
    "use strict";

    function init(root) {
        root.querySelectorAll("[data-task-activity]:not([data-task-activity-ready])").forEach(function (block) {
            var picker = block.querySelector("[data-task-activity-picker]");
            var summary = block.querySelector("[data-task-activity-summary]");
            var hidden = block.querySelector("input[name=activity]");
            var change = block.querySelector("[data-task-activity-change]");
            if (!picker || !summary || !hidden) return;
            block.setAttribute("data-task-activity-ready", "1");

            function showPicker() {
                summary.hidden = true;
                picker.hidden = false;
            }

            function showSummary(info) {
                summary.querySelector("[data-summary-title]").textContent = info.title;
                summary.querySelector("[data-summary-meta]").textContent = info.meta || "";
                summary.hidden = false;
                picker.hidden = true;
            }

            hidden.addEventListener("change", function (event) {
                var item = event.detail && event.detail.item;
                if (item && item.summary) showSummary(item.summary);
                else if (!hidden.value) showPicker();
            });

            if (change) {
                change.addEventListener("click", function () {
                    showPicker();
                    var trigger = picker.querySelector(".person-picker__trigger");
                    if (trigger) trigger.click();
                });
            }
        });
    }

    // Mesmo padrão dos outros widgets: modal.js chama cada init depois de injetar a janela.
    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(init);
    init(document);
})();
