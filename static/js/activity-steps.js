/* Nova / Editar atividade em três etapas (templates/activities/activity_form.html).

   As três etapas são painéis do MESMO formulário: aqui só se mostra um por vez,
   se marca o progresso e se valida a primeira etapa antes de avançar. Nenhum dado
   sai do DOM ao avançar ou voltar (os painéis só ficam `hidden`) e nada é enviado
   antes do botão final — o servidor continua sendo quem valida e grava.
   Sem este script as três etapas aparecem empilhadas e o formulário funciona igual. */
(function () {
    "use strict";

    // Campos obrigatórios da etapa 1 (o servidor exige os mesmos em ActivityEditorForm.clean).
    var REQUIRED_MESSAGES = {
        title: "Informe o nome da atividade.",
        owner: "Escolha quem fica com a atividade.",
        sector: "Escolha o setor responsável."
    };

    function setup(root) {
        if (root.getAttribute("data-steps-ready")) return;
        var form = root.querySelector("form");
        var panels = Array.prototype.slice.call(root.querySelectorAll("[data-step-panel]"));
        var indicators = Array.prototype.slice.call(root.querySelectorAll("[data-step-indicator]"));
        var stepper = root.querySelector("[data-stepper]");
        var prev = root.querySelector("[data-step-prev]");
        var next = root.querySelector("[data-step-next]");
        var submit = root.querySelector("[data-step-submit]");
        var body = root.querySelector(".activity-modal-body");
        var errorBox = root.querySelector("[data-form-errors]");
        if (!form || !panels.length || !prev || !next || !submit) return;
        root.setAttribute("data-steps-ready", "1");

        var total = panels.length;
        var current = 1;

        function groupsIn(panel) {
            return Array.prototype.slice.call(panel.querySelectorAll("[data-required]"));
        }

        function valueOf(group) {
            var input = group.querySelector("input:not([type=radio]):not([type=checkbox]), textarea, select");
            return input ? String(input.value || "").trim() : "";
        }

        function clearError(group) {
            group.classList.remove("has-error");
            var old = group.querySelector(".activity-error");
            if (old) old.remove();
        }

        function showError(group) {
            clearError(group);
            group.classList.add("has-error");
            var message = document.createElement("p");
            message.className = "activity-error";
            message.setAttribute("role", "alert");
            message.textContent = REQUIRED_MESSAGES[group.getAttribute("data-field")] || "Preencha este campo.";
            group.appendChild(message);
        }

        function focusField(group) {
            var target = group.querySelector("input:not([type=hidden]), textarea, select, .person-picker__trigger");
            if (target && target.focus) target.focus();
        }

        // Valida os campos obrigatórios de uma etapa; devolve true se está tudo preenchido.
        function validate(step) {
            var firstInvalid = null;
            groupsIn(panels[step - 1]).forEach(function (group) {
                if (valueOf(group)) {
                    clearError(group);
                } else {
                    showError(group);
                    if (!firstInvalid) firstInvalid = group;
                }
            });
            if (firstInvalid) focusField(firstInvalid);
            return !firstInvalid;
        }

        function show(step, options) {
            current = Math.max(1, Math.min(total, step));
            panels.forEach(function (panel, index) { panel.hidden = index + 1 !== current; });
            indicators.forEach(function (indicator, index) {
                var number = index + 1;
                var label = indicator.querySelector(".activity-step-number");
                indicator.classList.toggle("is-complete", number < current);
                indicator.classList.toggle("is-active", number === current);
                indicator.removeAttribute("aria-current");
                if (number === current) indicator.setAttribute("aria-current", "step");
                if (label) label.textContent = number < current ? "✓" : String(number);
            });
            prev.hidden = false;
            prev.disabled = current === 1;
            next.hidden = current === total;
            submit.hidden = current !== total;
            if (body) body.scrollTop = 0;
            if (options && options.focus) {
                var first = panels[current - 1].querySelector("input:not([type=hidden]):not([type=radio]), textarea, .person-picker__trigger, [contenteditable]");
                if (first && first.focus) first.focus();
            }
        }

        function goNext() {
            if (current < total && validate(current)) show(current + 1, { focus: true });
        }

        next.addEventListener("click", goNext);
        prev.addEventListener("click", function () { show(current - 1, { focus: true }); });

        // Enter num campo de texto nas primeiras etapas avança em vez de enviar o formulário.
        form.addEventListener("keydown", function (event) {
            if (event.key !== "Enter" || event.defaultPrevented || event.shiftKey) return;
            var target = event.target;
            if (!target || target.tagName !== "INPUT" || target.type === "submit" || target.type === "button") return;
            if (current < total) {
                event.preventDefault();
                goNext();
            }
        });

        // Captura: roda antes do envio do LPSModal. Nas primeiras etapas o envio vira "continuar";
        // na última, confere a etapa 1 de novo (Enter ou clique) antes de deixar seguir.
        root.addEventListener("submit", function (event) {
            if (current < total) {
                event.preventDefault();
                event.stopPropagation();
                goNext();
                return;
            }
            for (var step = 1; step <= total; step += 1) {
                if (!validate(step)) {
                    event.preventDefault();
                    event.stopPropagation();
                    show(step, { focus: false });
                    validate(step);
                    return;
                }
            }
        }, true);

        // Quem já tem valor deixa de ser "erro" assim que a pessoa escolhe ou digita.
        function revalidate(event) {
            var group = event.target.closest && event.target.closest("[data-required]");
            if (group && valueOf(group)) clearError(group);
        }
        form.addEventListener("input", revalidate);
        form.addEventListener("change", revalidate);

        // Erros devolvidos pelo servidor (LPSModal insere `.errorlist` no formulário): abre a
        // etapa do primeiro erro e puxa o erro geral para o topo da área de rolagem.
        if (window.MutationObserver) {
            new MutationObserver(function () {
                Array.prototype.slice.call(form.children).forEach(function (child) {
                    if (child.classList && child.classList.contains("errorlist") && errorBox) errorBox.appendChild(child);
                });
                var lists = panels.map(function (panel) { return panel.querySelector(".errorlist"); });
                for (var index = 0; index < lists.length; index += 1) {
                    if (lists[index]) {
                        if (index + 1 !== current) show(index + 1, { focus: false });
                        var field = lists[index].closest("[data-field]");
                        if (field) focusField(field);
                        break;
                    }
                }
            }).observe(form, { childList: true, subtree: true });
        }

        if (stepper) stepper.hidden = false;
        var start = parseInt(root.getAttribute("data-initial-step"), 10) || 1;
        // Página devolvida com erro de servidor: abre na primeira etapa que tem erro.
        for (var index = 0; index < panels.length; index += 1) {
            if (panels[index].querySelector(".errorlist")) { start = index + 1; break; }
        }
        show(start);
    }

    function initIn(container) {
        (container || document).querySelectorAll("[data-activity-stepper]").forEach(setup);
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);
    initIn(document);
})();
