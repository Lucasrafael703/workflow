/* Nova / Editar demanda em quatro etapas (templates/activities/activity_form.html) — a MESMA janela nos dois casos.

   As etapas são painéis do MESMO formulário: aqui só se mostra um por vez,
   se marca o progresso e se valida a primeira etapa antes de avançar. Nenhum dado
   sai do DOM ao avançar ou voltar (os painéis só ficam `hidden`) e nada é enviado
   antes do botão final — o servidor continua sendo quem valida e grava.
   Editar: trocar o quadro de tarefas (etapa 3) exclui as tarefas do quadro atual, então o envio final abre um
   diálogo de confirmação; só ao confirmar a caixa `confirm_board_replace` é marcada e o formulário é reenviado.
   Sem este script as etapas aparecem empilhadas e o formulário funciona igual (a caixa de confirmação fica visível). */
(function () {
    "use strict";

    // Campos obrigatórios da etapa 1 (o servidor exige os mesmos em ActivityEditorForm.clean).
    var REQUIRED_MESSAGES = {
        title: "Informe o nome da demanda.",
        owner: "Escolha quem fica com a demanda.",
        sector: "Escolha o setor responsável.",
        board_template: "Escolha o modelo de quadro."
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

        // Quadro de tarefas: o campo "Modelo de quadro" só existe (e só é obrigatório) em "Usar quadro existente".
        var templateBox = root.querySelector("[data-board-template-field]");
        function syncTemplate() {
            if (!templateBox) return;
            var checked = root.querySelector("input[name=board_setup_mode]:checked");
            var useTemplate = !!checked && checked.value === "TEMPLATE";
            templateBox.hidden = !useTemplate;
            var group = templateBox.querySelector("[data-field=board_template]");
            if (group) {
                if (useTemplate) group.setAttribute("data-required", "");
                else { group.removeAttribute("data-required"); group.classList.remove("has-error"); var old = group.querySelector(".activity-error"); if (old) old.remove(); }
            }
        }
        root.addEventListener("change", function (event) {
            if (event.target && event.target.name === "board_setup_mode") syncTemplate();
        });
        syncTemplate();

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

        // ---- Editar: trocar o quadro pede confirmação (as tarefas do quadro atual são excluídas) ----
        var boardExists = root.getAttribute("data-board-exists") === "1";
        var boardTemplate = root.getAttribute("data-board-template") || "";
        var boardItems = parseInt(root.getAttribute("data-board-items"), 10) || 0;
        var confirmBox = root.querySelector("[data-board-confirm]");
        var confirmFlag = form.querySelector("input[name=confirm_board_replace]");
        var confirmFallback = root.querySelector("[data-board-confirm-fallback]");
        var changeWarning = root.querySelector("[data-board-change-warning]");
        if (!confirmBox || !confirmFlag) boardExists = false;
        if (boardExists && confirmFallback) confirmFallback.hidden = true; // com JavaScript quem confirma é o diálogo

        // A escolha do passo 3 difere do quadro que a demanda tem hoje? (mesmo critério do servidor)
        function boardChanged() {
            if (!boardExists) return false;
            var checked = root.querySelector("input[name=board_setup_mode]:checked");
            var mode = checked ? checked.value : "BLANK";
            if (mode !== "TEMPLATE") return boardTemplate !== "";
            var select = root.querySelector("[name=board_template]");
            return !!select && select.value !== "" && select.value !== boardTemplate;
        }

        function syncBoardChange() {
            if (changeWarning) changeWarning.hidden = !boardChanged();
        }
        syncBoardChange();
        // Mudou a escolha: a confirmação anterior não vale mais.
        root.addEventListener("change", function (event) {
            if (!event.target || (event.target.name !== "board_setup_mode" && event.target.name !== "board_template")) return;
            if (confirmFlag) confirmFlag.checked = false;
            syncBoardChange();
        });

        function confirmText() {
            if (boardItems === 1) return "A tarefa do quadro atual será excluída definitivamente. Esta ação não pode ser desfeita.";
            if (boardItems > 1) return "As " + boardItems + " tarefas do quadro atual serão excluídas definitivamente. Esta ação não pode ser desfeita.";
            return "O quadro atual será substituído por um novo. Esta ação não pode ser desfeita.";
        }

        function targetText() {
            var checked = root.querySelector("input[name=board_setup_mode]:checked");
            if (checked && checked.value === "TEMPLATE") {
                var select = root.querySelector("[name=board_template]");
                var option = select && select.options && select.options[select.selectedIndex];
                return "Novo quadro: a partir do modelo " + (option ? option.textContent.trim() : "");
            }
            return "Novo quadro: em branco";
        }

        function setInert(on) {
            Array.prototype.slice.call(root.children).forEach(function (child) {
                if (child === confirmBox) return;
                if (on) child.setAttribute("inert", ""); else child.removeAttribute("inert");
            });
        }

        function openConfirm() {
            root.querySelector("[data-board-confirm-message]").textContent = confirmText();
            root.querySelector("[data-board-confirm-target]").textContent = targetText();
            setInert(true);
            confirmBox.hidden = false;
            var cancel = confirmBox.querySelector("[data-board-confirm-cancel]");
            if (cancel) cancel.focus(); // o botão seguro é o padrão
        }

        function closeConfirm() {
            confirmBox.hidden = true;
            setInert(false);
        }

        if (boardExists) {
            confirmBox.querySelector("[data-board-confirm-cancel]").addEventListener("click", function () {
                closeConfirm();
                confirmFlag.checked = false;
                show(3, { focus: false }); // volta ao passo do quadro; nada foi enviado
                var radio = root.querySelector("input[name=board_setup_mode]:checked");
                if (radio && radio.focus) radio.focus();
            });
            confirmBox.querySelector("[data-board-confirm-accept]").addEventListener("click", function () {
                closeConfirm();
                confirmFlag.checked = true;
                if (form.requestSubmit) form.requestSubmit(submit);
                else form.submit();
            });
            // Clicar fora do cartão não confirma: só cancela.
            confirmBox.addEventListener("click", function (event) {
                if (event.target === confirmBox) confirmBox.querySelector("[data-board-confirm-cancel]").click();
            });
        }

        // Com o diálogo aberto, Esc fecha só o diálogo (não a janela inteira) e Tab fica preso nele.
        root.addEventListener("keydown", function (event) {
            if (!boardExists || confirmBox.hidden) return;
            if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                confirmBox.querySelector("[data-board-confirm-cancel]").click();
            } else if (event.key === "Tab") {
                var buttons = Array.prototype.slice.call(confirmBox.querySelectorAll("button"));
                var index = buttons.indexOf(document.activeElement);
                event.preventDefault();
                event.stopPropagation();
                if (event.shiftKey) index = index <= 0 ? buttons.length - 1 : index - 1;
                else index = index < 0 || index === buttons.length - 1 ? 0 : index + 1;
                buttons[index].focus();
            }
        }, true);

        // Captura: roda antes do envio do LPSModal. Nas primeiras etapas o envio vira "continuar"; ao enviar de verdade,
        // confere todas as etapas e, se o quadro foi trocado e ainda não houve confirmação, abre o diálogo.
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
            if (boardChanged() && !confirmFlag.checked) {
                event.preventDefault();
                event.stopPropagation();
                openConfirm();
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
                // O servidor recusou o envio: a confirmação dada não vale para a próxima tentativa.
                if (boardExists && form.querySelector(".errorlist")) confirmFlag.checked = false;
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
