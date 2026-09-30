/* Popup "Aplicar processo": quatro passos num único formulário.
   1 Processo → 2 Responsáveis → 3 Entradas → 4 Confirmar.

   O HTML já traz os campos de todas as versões elegíveis; aqui só se mostra
   e se habilita o bloco da versão escolhida (campo desabilitado não é enviado,
   então o servidor só vê a versão certa). Nenhuma regra de negócio mora aqui:
   o servidor valida tudo de novo em ProcessApplicationService. */
(function () {
    "use strict";

    var LAST = 4;

    function setup(box) {
        if (box.getAttribute("data-apply-ready")) return;
        var form = box.querySelector("form");
        if (!form) return;
        var radios = Array.prototype.slice.call(form.querySelectorAll("input[name=process_version]"));
        if (!radios.length) return;
        box.setAttribute("data-apply-ready", "1");

        var panes = Array.prototype.slice.call(form.querySelectorAll("[data-pane]"));
        var tabs = Array.prototype.slice.call(form.querySelectorAll("[data-step-tab]"));
        var back = form.querySelector("[data-apply-back]");
        var next = form.querySelector("[data-apply-next]");
        var submit = form.querySelector("[data-apply-submit]");
        var errorBox = form.querySelector("[data-form-errors]");
        var current = 1;

        function selectedRadio() {
            for (var i = 0; i < radios.length; i++) if (radios[i].checked) return radios[i];
            return null;
        }

        function showMessage(text) {
            if (!errorBox) return;
            errorBox.innerHTML = "";
            if (!text) return;
            var list = document.createElement("ul");
            list.className = "errorlist";
            var item = document.createElement("li");
            item.textContent = text;
            list.appendChild(item);
            errorBox.appendChild(list);
        }

        // Só os campos da versão escolhida ficam visíveis e habilitados.
        function syncVersion() {
            var chosen = selectedRadio();
            var chosenId = chosen ? chosen.value : null;
            form.querySelectorAll(".apply-version").forEach(function (block) {
                var active = block.getAttribute("data-version") === chosenId;
                block.hidden = !active;
                block.querySelectorAll("input, select").forEach(function (field) {
                    field.disabled = !active;
                });
            });
        }

        function activeBlock(step) {
            var pane = form.querySelector("[data-pane='" + step + "']");
            return pane ? pane.querySelector(".apply-version:not([hidden])") : null;
        }

        function validate(step) {
            if (step === 1) {
                if (!selectedRadio()) {
                    showMessage("Escolha o processo que será aplicado.");
                    return false;
                }
            }
            if (step === 2) {
                var block = activeBlock(2);
                var selects = block ? block.querySelectorAll("select") : [];
                for (var i = 0; i < selects.length; i++) {
                    if (!selects[i].value) {
                        showMessage("Escolha o responsável de “" + selects[i].getAttribute("data-step-name") + "”.");
                        selects[i].focus();
                        return false;
                    }
                }
            }
            showMessage("");
            return true;
        }

        function text(el) {
            return (el && el.textContent || "").replace(/\s+/g, " ").trim();
        }

        function buildSummary() {
            var box2 = form.querySelector("[data-apply-summary]");
            if (!box2) return;
            var chosen = selectedRadio();
            var stepsBlock = activeBlock(2);
            var inputsBlock = activeBlock(3);
            var html = document.createElement("div");

            function line(strong, rest) {
                var p = document.createElement("p");
                var s = document.createElement("strong");
                s.textContent = strong;
                p.appendChild(s);
                if (rest) p.appendChild(document.createTextNode(" " + rest));
                return p;
            }

            html.appendChild(line("Processo:", chosen.getAttribute("data-name") + " — versão " + chosen.getAttribute("data-number")));

            var stepsTitle = document.createElement("p");
            stepsTitle.innerHTML = "<strong>Etapas:</strong>";
            html.appendChild(stepsTitle);
            var list = document.createElement("ol");
            list.className = "apply-summary__steps";
            (stepsBlock ? stepsBlock.querySelectorAll("select") : []).forEach(function (select) {
                var li = document.createElement("li");
                var chosenOption = select.options[select.selectedIndex];
                li.textContent = select.getAttribute("data-step-name") + " — " + select.getAttribute("data-step-sector") +
                    " — " + (chosenOption ? text(chosenOption) : "");
                list.appendChild(li);
            });
            html.appendChild(list);

            var informed = 0, waiting = 0, missingRequired = [];
            (inputsBlock ? inputsBlock.querySelectorAll(".apply-input") : []).forEach(function (row) {
                // Arquivo/seleção só contam com "Já recebi" marcado (a observação
                // é livre); os demais tipos, com valor preenchido — como no servidor.
                var check = row.querySelector("[data-input-received]");
                var filled = false;
                if (check) {
                    filled = check.checked;
                } else {
                    row.querySelectorAll("input[type=text], input[type=date], input[type=url]").forEach(function (f) {
                        if (f.value.trim()) filled = true;
                    });
                }
                if (filled) {
                    informed++;
                } else {
                    waiting++;
                    if (row.getAttribute("data-input-required") === "1") {
                        missingRequired.push(text(row.querySelector("label")).split(" Obrigat")[0]);
                    }
                }
            });
            html.appendChild(line("Entradas:", informed + " informada" + (informed === 1 ? "" : "s") + " · " + waiting + " aguardando"));
            if (missingRequired.length) {
                var warn = document.createElement("p");
                warn.className = "muted small";
                warn.textContent = "Faltam entradas obrigatórias (" + missingRequired.join("; ") +
                    "). Dá para aplicar assim, mas as tarefas só começam depois que elas forem recebidas.";
                html.appendChild(warn);
            }
            html.appendChild(line("Critérios de aceite:", chosen.getAttribute("data-criteria") + " serão criados"));

            box2.innerHTML = "";
            box2.appendChild(html);
        }

        function show(step) {
            current = step;
            panes.forEach(function (pane) { pane.hidden = pane.getAttribute("data-pane") !== String(step); });
            tabs.forEach(function (tab) {
                var n = parseInt(tab.getAttribute("data-step-tab"), 10);
                tab.classList.toggle("is-active", n === step);
                tab.classList.toggle("is-done", n < step);
            });
            if (back) back.hidden = step === 1;
            if (next) next.hidden = step === LAST;
            if (submit) submit.hidden = step !== LAST;
            if (step === LAST) buildSummary();
        }

        radios.forEach(function (radio) { radio.addEventListener("change", syncVersion); });
        if (next) next.addEventListener("click", function () {
            syncVersion();
            if (validate(current)) show(Math.min(current + 1, LAST));
        });
        if (back) back.addEventListener("click", function () { showMessage(""); show(Math.max(current - 1, 1)); });

        // Enter num campo não pode enviar o formulário antes do último passo.
        form.addEventListener("keydown", function (event) {
            if (event.key !== "Enter") return;
            var tag = event.target && event.target.tagName;
            if (tag === "TEXTAREA" || tag === "BUTTON") return;
            event.preventDefault();
            if (current < LAST && next) next.click();
        });

        // Depois de um erro do servidor: o erro do formulário como um todo (que
        // o popup anexa ao fim do corpo) sobe para o espaço reservado no topo, e
        // o passo volta para o do primeiro campo com erro.
        if (window.MutationObserver) {
            new MutationObserver(function () {
                if (errorBox) {
                    form.querySelectorAll(".modal__body > .errorlist").forEach(function (list) {
                        errorBox.appendChild(list);
                    });
                }
                var firstError = form.querySelector(".apply-pane .errorlist");
                if (!firstError) return;
                var pane = firstError.closest("[data-pane]");
                if (pane && String(current) !== pane.getAttribute("data-pane")) {
                    show(parseInt(pane.getAttribute("data-pane"), 10));
                }
            }).observe(form, { childList: true, subtree: true });
        }

        syncVersion();
        show(1);
    }

    function initIn(root) {
        (root || document).querySelectorAll("[data-process-apply]").forEach(setup);
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);
    initIn(document);
})();
