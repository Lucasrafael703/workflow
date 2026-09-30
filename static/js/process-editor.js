/* Editor de processo: no formulário "Adicionar etapa", o responsável padrão
   sugere primeiro quem participa do setor escolhido. Quem é de outros setores
   continua disponível — o responsável de uma tarefa não precisa ser do setor
   dela —, só fica escondido até a pessoa marcar "Mostrar pessoas de outros
   setores". Sem JavaScript o seletor mostra todo mundo. */
(function () {
    "use strict";

    function init(form) {
        var sector = form.querySelector("[data-step-sector]");
        var person = form.querySelector("[data-step-responsavel]");
        var showAll = form.querySelector("[data-step-show-all]");
        if (!sector || !person) return;

        function refresh() {
            var sectorId = sector.value;
            var everyone = showAll && showAll.checked;
            Array.prototype.forEach.call(person.options, function (option) {
                if (!option.value) return;
                var sectors = (option.getAttribute("data-sectors") || "").split(",");
                var visible = everyone || !sectorId || sectors.indexOf(sectorId) !== -1;
                option.hidden = !visible;
                option.disabled = !visible;
            });
            var selected = person.options[person.selectedIndex];
            if (selected && selected.value && selected.disabled) person.value = "";
        }

        sector.addEventListener("change", refresh);
        if (showAll) showAll.addEventListener("change", refresh);
        refresh();
    }

    document.querySelectorAll("[data-step-form]").forEach(init);
})();
