/* Seletor de Etapa e de Condição de uma Demanda/Tarefa (cartão do quadro, menu "Mover para etapa" e gaveta).
   Um botão com `data-workflow-picker` abre uma lista ancorada nele com as opções DO SETOR do item
   (GET em `data-options-url`); escolher uma opção grava só ela (POST em `data-set-url`). Quem gere o catálogo
   também vê "+ Nova etapa/condição" (cria sem sair da tela) e "Gerenciar". O servidor decide tudo de novo:
   aqui só se mostra o que ele devolve.

   Depois de gravar, dispara `lps:workflow-changed` no document com {domain, itemId, kind, response}; o quadro
   troca o cartão pelo `response.card_html`. Na gaveta o próprio botão passa a mostrar a opção escolhida. */
(function () {
    "use strict";

    // Cores da paleta oficial (core/colors.py); o servidor valida de novo.
    var SWATCHES = ["#94A3B8", "#22C55E", "#10B981", "#14B8A6", "#FACC15", "#F59E0B", "#F97316",
                    "#EF4444", "#EC4899", "#A855F7", "#7C3AED", "#3B82F6"];
    var current = null; // {pop, button}

    function csrfToken() {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        if (match) return match[1];
        var field = document.querySelector("input[name=csrfmiddlewaretoken]");
        return field ? field.value : "";
    }

    function announce(message) {
        if (message && window.LPSAjax && typeof window.LPSAjax.announce === "function") window.LPSAjax.announce(message);
    }

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function dot(color) {
        var node = el("span", "option-dot");
        node.style.setProperty("--option-color", color || "#94A3B8");
        return node;
    }

    function close() {
        if (!current) return;
        current.button.setAttribute("aria-expanded", "false");
        current.pop.remove();
        current = null;
        document.removeEventListener("keydown", onKeydown, true);
        document.removeEventListener("mousedown", onOutside, true);
        window.removeEventListener("resize", close);
    }

    function onKeydown(event) {
        if (!current) return;
        if (event.key === "Escape") {
            var button = current.button;
            close();
            button.focus();
            return;
        }
        if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
        var options = Array.prototype.slice.call(current.pop.querySelectorAll(".workflow-pop__option"));
        if (!options.length) return;
        event.preventDefault();
        var index = options.indexOf(document.activeElement);
        index = event.key === "ArrowDown" ? (index + 1) % options.length : (index - 1 + options.length) % options.length;
        options[index].focus();
    }

    function onOutside(event) {
        if (!current) return;
        if (current.pop.contains(event.target) || current.button.contains(event.target)) return;
        close();
    }

    function place(pop, button) {
        var rect = button.getBoundingClientRect();
        var width = pop.offsetWidth || 240;
        var left = Math.min(rect.left, window.innerWidth - width - 8);
        pop.style.left = Math.max(8, left + window.scrollX) + "px";
        pop.style.top = (rect.bottom + window.scrollY + 4) + "px";
    }

    function request(url, options) {
        options = options || {};
        options.headers = Object.assign({"X-Requested-With": "XMLHttpRequest"}, options.headers || {});
        return fetch(url, options).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (data) {
                if (!response.ok || data.success === false) {
                    var error = new Error(data.message || (data.detail) || "Não foi possível concluir.");
                    error.data = data;
                    throw error;
                }
                return data;
            });
        });
    }

    function noun(button) {
        return button.dataset.kind === "stage" ? "etapa" : "condição";
    }

    function renderOptions(state, items) {
        var button = state.button;
        var pop = state.pop;
        var currentId = button.dataset.currentId || "";
        pop.innerHTML = "";
        if (button.dataset.allowClear === "1" && currentId) {
            var clear = el("button", "workflow-pop__option", "Sem " + noun(button));
            clear.type = "button";
            clear.setAttribute("role", "option");
            clear.addEventListener("click", function () { choose(button, ""); });
            pop.appendChild(clear);
        }
        if (!items.length) {
            pop.appendChild(el("div", "workflow-pop__empty", "Este setor ainda não tem " + noun(button) + "s."));
        }
        items.forEach(function (item) {
            var option = el("button", "workflow-pop__option" + (String(item.id) === currentId ? " is-current" : ""));
            option.type = "button";
            option.setAttribute("role", "option");
            option.dataset.optionId = item.id;
            option.appendChild(dot(item.color));
            option.appendChild(el("span", "", item.name));
            if (String(item.id) === currentId) {
                var check = el("span", "workflow-pop__check", "✓");
                option.appendChild(check);
                option.setAttribute("aria-selected", "true");
            }
            option.addEventListener("click", function () { choose(button, item.id); });
            pop.appendChild(option);
        });
        if (button.dataset.canCreate === "1" || button.dataset.manageUrl) {
            pop.appendChild(el("div", "workflow-pop__sep"));
        }
        if (button.dataset.canCreate === "1") {
            var add = el("button", "workflow-pop__option", "+ Nova " + noun(button));
            add.type = "button";
            add.addEventListener("click", function () { showCreateForm(state); });
            pop.appendChild(add);
        }
        if (button.dataset.manageUrl && button.dataset.canCreate === "1") {
            var manage = el("a", "workflow-pop__link", "Gerenciar " + noun(button) + "s");
            manage.href = button.dataset.manageUrl;
            pop.appendChild(manage);
        }
        place(pop, button);
        var focus = pop.querySelector(".is-current") || pop.querySelector(".workflow-pop__option");
        if (focus) focus.focus();
    }

    function loadOptions(state) {
        return request(state.button.dataset.optionsUrl)
            .then(function (data) { renderOptions(state, data.items || []); })
            .catch(function (error) {
                state.pop.innerHTML = "";
                state.pop.appendChild(el("div", "workflow-pop__empty", error.message));
            });
    }

    function showCreateForm(state) {
        var button = state.button;
        var pop = state.pop;
        var form = el("form", "workflow-pop__form");
        var input = el("input");
        input.type = "text";
        input.placeholder = "Nome da " + noun(button);
        input.maxLength = 150;
        input.setAttribute("aria-label", "Nome da " + noun(button));
        var swatches = el("div", "workflow-pop__swatches");
        var color = SWATCHES[0];
        SWATCHES.forEach(function (hex, index) {
            var swatch = el("button", "workflow-pop__swatch" + (index === 0 ? " is-selected" : ""));
            swatch.type = "button";
            swatch.style.setProperty("--swatch", hex);
            swatch.setAttribute("aria-label", "Cor " + hex);
            swatch.addEventListener("click", function () {
                color = hex;
                swatches.querySelectorAll(".workflow-pop__swatch").forEach(function (other) { other.classList.remove("is-selected"); });
                swatch.classList.add("is-selected");
            });
            swatches.appendChild(swatch);
        });
        var error = el("p", "workflow-pop__error");
        error.hidden = true;
        var save = el("button", "btn btn--primary btn--sm", "Salvar " + noun(button));
        save.type = "submit";
        form.appendChild(input);
        form.appendChild(swatches);
        form.appendChild(error);
        form.appendChild(save);
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            save.disabled = true;
            var body = new FormData();
            body.append("kind", button.dataset.kind);
            body.append("name", input.value);
            body.append("color", color);
            body.append("sector_id", button.dataset.sectorId);
            request(button.dataset.createUrl, {method: "POST", headers: {"X-CSRFToken": csrfToken()}, body: body})
                .then(function (data) {
                    announce(data.message);
                    pop.innerHTML = "";
                    pop.appendChild(el("div", "workflow-pop__empty", "Carregando…"));
                    loadOptions(state);
                })
                .catch(function (failure) {
                    error.textContent = failure.message;
                    error.hidden = false;
                    save.disabled = false;
                    input.focus();
                });
        });
        pop.innerHTML = "";
        pop.appendChild(form);
        place(pop, button);
        input.focus();
    }

    function choose(button, optionId) {
        var body = new FormData();
        body.append(button.dataset.kind === "stage" ? "stage_id" : "condition_id", optionId);
        close();
        button.disabled = true;
        request(button.dataset.setUrl, {method: "POST", headers: {"X-CSRFToken": csrfToken()}, body: body})
            .then(function (data) {
                announce(data.message);
                applyToButton(button, data, optionId);
                document.dispatchEvent(new CustomEvent("lps:workflow-changed", {
                    detail: {domain: button.dataset.domain, itemId: button.dataset.itemId, kind: button.dataset.kind, response: data},
                }));
            })
            .catch(function (error) { announce(error.message); })
            .then(function () { if (document.body.contains(button)) button.disabled = false; });
    }

    // Na gaveta o botão fica mostrando a opção escolhida; no cartão a troca do HTML cuida disso.
    function applyToButton(button, data, optionId) {
        button.dataset.currentId = optionId === "" ? "" : String(optionId);
        var label = button.querySelector("[data-workflow-label]");
        if (!label) return;
        var name = button.dataset.kind === "stage" ? data.stage_name : data.condition_name;
        label.textContent = name || ("Sem " + noun(button));
    }

    function open(button) {
        if (current && current.button === button) { close(); return; }
        close();
        var pop = el("div", "workflow-pop");
        pop.setAttribute("role", "listbox");
        pop.appendChild(el("div", "workflow-pop__empty", "Carregando…"));
        document.body.appendChild(pop);
        current = {pop: pop, button: button};
        button.setAttribute("aria-expanded", "true");
        place(pop, button);
        document.addEventListener("keydown", onKeydown, true);
        document.addEventListener("mousedown", onOutside, true);
        window.addEventListener("resize", close);
        loadOptions(current);
    }

    document.addEventListener("click", function (event) {
        var button = event.target.closest && event.target.closest("[data-workflow-picker]");
        if (!button || button.disabled) return;
        event.preventDefault();
        event.stopPropagation();
        open(button);
    });

    window.LPSWorkflowPicker = {open: open, close: close};
})();
