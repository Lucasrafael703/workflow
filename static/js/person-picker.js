/* Seletor de pessoa com busca (estilo "atribuir responsável" do Monday): abre
   um popup, filtra por nome enquanto digita, e permite criar um usuário sem
   sair do formulário atual quando a pessoa não existe ainda. */
(function () {
    "use strict";

    var DEBOUNCE_MS = 250;
    var MIN_CHARS = 3;

    function init(root) {
        var hidden = root.querySelector("input[type=hidden]");
        var trigger = root.querySelector(".person-picker__trigger");
        var label = root.querySelector(".person-picker__label");
        var searchUrl = root.getAttribute("data-search-url");
        var sectorFieldId = root.getAttribute("data-sector-field");
        // Seletor que depende de outro campo (obra ← cliente, centro de custo ← obra):
        // ao mudar o outro campo a escolha é zerada e o valor dele segue na busca.
        var filterFieldId = root.getAttribute("data-filter-field");
        var filterParam = root.getAttribute("data-filter-param");
        var placeholder = root.getAttribute("data-placeholder") || "Buscar pessoa...";
        var emptyLabel = root.getAttribute("data-empty-label") || "Selecionar pessoa";
        var createUrl = root.getAttribute("data-create-url");
        var createLabel = root.getAttribute("data-create-label") || "Criar novo usuário";
        var pickerKind = root.getAttribute("data-picker-kind") || "";
        var isSectorPicker = pickerKind === "sector";
        var allowedSectorIds = (root.getAttribute("data-allowed-sector-ids") || "")
            .split(",").filter(Boolean);

        var popup = null;
        var results = [];
        var activeIndex = -1;
        var debounceTimer = null;
        var sectorSwatch = null;

        function setSectorVisual(item) {
            if (!isSectorPicker) return;
            var color = item && item.color || "";
            var textColor = item && item.text_color || "";
            if (color) root.style.setProperty("--picker-color", color);
            else root.style.removeProperty("--picker-color");
            if (textColor) root.style.setProperty("--picker-text-color", textColor);
            else root.style.removeProperty("--picker-text-color");
            if (sectorSwatch) {
                sectorSwatch.hidden = !color;
                if (color) sectorSwatch.style.backgroundColor = color;
            }
        }

        if (isSectorPicker) {
            sectorSwatch = trigger.querySelector(".sector-picker__swatch");
            if (!sectorSwatch) {
                sectorSwatch = document.createElement("span");
                sectorSwatch.className = "sector-picker__swatch";
                sectorSwatch.setAttribute("aria-hidden", "true");
                trigger.insertBefore(sectorSwatch, label);
            }
            setSectorVisual({
                color: root.getAttribute("data-selected-color") || "",
                text_color: root.getAttribute("data-selected-text-color") || "",
            });
        }

        if (sectorFieldId) {
            var sectorField = document.getElementById(sectorFieldId);
            if (sectorField) {
                sectorField.addEventListener("change", function () {
                    hidden.value = "";
                    label.textContent = emptyLabel;
                    label.classList.add("muted");
                    hidden.dispatchEvent(new Event("change", { bubbles: true }));
                });
            }
        }

        if (filterFieldId && filterParam) {
            var filterField = document.getElementById(filterFieldId);
            if (filterField) {
                filterField.addEventListener("change", function () {
                    if (!hidden.value) return;
                    hidden.value = "";
                    label.textContent = emptyLabel;
                    label.classList.add("muted");
                    hidden.dispatchEvent(new Event("change", { bubbles: true }));
                });
            }
        }

        function closePopup() {
            if (!popup) return;
            popup.remove();
            popup = null;
            root.classList.remove("is-open");
            trigger.setAttribute("aria-expanded", "false");
            document.removeEventListener("click", onDocumentClick, true);
        }

        function onDocumentClick(event) {
            if (!root.contains(event.target)) closePopup();
        }

        function select(person) {
            hidden.value = person.id;
            label.textContent = person.name;
            label.classList.remove("muted");
            if (!person.id) label.classList.add("muted");
            setSectorVisual(person);
            // `detail.item` é a opção escolhida, com o que mais a busca devolveu (ex.: o resumo da atividade).
            hidden.dispatchEvent(new CustomEvent("change", { bubbles: true, detail: { item: person } }));
            closePopup();
            trigger.focus();
        }

        function renderMessage(text) {
            results = [];
            activeIndex = -1;
            var resultsEl = popup.querySelector(".person-picker__results");
            resultsEl.innerHTML = "";
            var empty = document.createElement("div");
            empty.className = "person-picker__empty";
            empty.textContent = text;
            resultsEl.appendChild(empty);
        }

        function renderResults(list) {
            var visibleList = list.filter(function (person) {
                return !isSectorPicker || !allowedSectorIds.length || allowedSectorIds.indexOf(String(person.id)) !== -1;
            });
            results = visibleList;
            activeIndex = -1;
            var resultsEl = popup.querySelector(".person-picker__results");
            resultsEl.innerHTML = "";

            if (visibleList.length === 0) {
                renderMessage("Nada encontrado.");
                return;
            }

            visibleList.forEach(function (person, index) {
                var option = document.createElement("button");
                option.type = "button";
                option.className = "person-picker__option";
                if (isSectorPicker && person.color) {
                    var swatch = document.createElement("span");
                    swatch.className = "sector-picker__option-swatch";
                    swatch.style.backgroundColor = person.color;
                    swatch.setAttribute("aria-hidden", "true");
                    option.appendChild(swatch);
                }
                var optionLabel = document.createElement("span");
                optionLabel.textContent = person.name;
                option.appendChild(optionLabel);
                option.addEventListener("click", function () { select(person); });
                option.addEventListener("mouseenter", function () { setActive(index); });
                resultsEl.appendChild(option);
            });
        }

        function setActive(index) {
            var options = popup.querySelectorAll(".person-picker__option");
            options.forEach(function (el) { el.classList.remove("is-active"); });
            if (index >= 0 && index < options.length) {
                options[index].classList.add("is-active");
                options[index].scrollIntoView({ block: "nearest" });
            }
            activeIndex = index;
        }

        function search(term) {
            if (term.trim().length < MIN_CHARS) {
                renderMessage("Digite ao menos " + MIN_CHARS + " letras para buscar.");
                return;
            }
            var params = new URLSearchParams({ q: term });
            if (sectorFieldId) {
                var sectorField = document.getElementById(sectorFieldId);
                params.set("sector", sectorField ? sectorField.value : "");
            }
            if (filterFieldId && filterParam) {
                var dependsOn = document.getElementById(filterFieldId);
                if (dependsOn && dependsOn.value) params.set(filterParam, dependsOn.value);
            }
            fetch(searchUrl + "?" + params.toString(), {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            })
                .then(function (response) { return response.json(); })
                .then(function (data) { renderResults(data.results || []); })
                .catch(function () { renderResults([]); });
        }

        function openCreateModal() {
            if (!createUrl || !window.LPSModal) return;
            window.LPSModal.open(createUrl, {
                onSuccess: function (person) { select(person); },
            });
        }

        function openPopup() {
            if (popup) return;
            root.classList.add("is-open");
            trigger.setAttribute("aria-expanded", "true");

            popup = document.createElement("div");
            popup.className = "person-picker__popup";
            popup.innerHTML =
                '<input type="text" class="person-picker__search">' +
                '<div class="person-picker__results"></div>';
            popup.querySelector(".person-picker__search").placeholder = placeholder;

            if (createUrl) {
                var createButton = document.createElement("button");
                createButton.type = "button";
                createButton.className = "person-picker__create";
                createButton.innerHTML =
                    '<svg width="15" height="15" viewBox="0 0 20 20" aria-hidden="true"><use href="#i-plus"></use></svg>' +
                    "<span>" + createLabel + "</span>";
                createButton.addEventListener("click", function () {
                    closePopup();
                    openCreateModal();
                });
                popup.appendChild(createButton);
            }

            // "Todos os ..." para limpar a escolha: setor (como sempre) e qualquer outro seletor que peça `data-allow-empty`
            // (ex.: Cliente e Obra no painel de filtros do Workspace).
            if (root.getAttribute("data-allow-empty") === "true") {
                var clearButton = document.createElement("button");
                clearButton.type = "button";
                clearButton.className = "person-picker__option sector-picker__clear";
                clearButton.textContent = emptyLabel;
                clearButton.addEventListener("click", function () {
                    select({ id: "", name: emptyLabel });
                });
                popup.appendChild(clearButton);
            }

            root.appendChild(popup);

            var searchInput = popup.querySelector(".person-picker__search");
            searchInput.addEventListener("input", function () {
                clearTimeout(debounceTimer);
                var term = searchInput.value;
                debounceTimer = setTimeout(function () { search(term); }, DEBOUNCE_MS);
            });
            searchInput.addEventListener("keydown", function (event) {
                if (event.key === "ArrowDown") {
                    event.preventDefault();
                    setActive(Math.min(activeIndex + 1, results.length - 1));
                } else if (event.key === "ArrowUp") {
                    event.preventDefault();
                    setActive(Math.max(activeIndex - 1, 0));
                } else if (event.key === "Enter") {
                    event.preventDefault();
                    if (activeIndex >= 0 && results[activeIndex]) select(results[activeIndex]);
                } else if (event.key === "Escape") {
                    closePopup();
                    trigger.focus();
                }
            });

            searchInput.focus();
            renderMessage("Digite ao menos " + MIN_CHARS + " letras para buscar.");
            document.addEventListener("click", onDocumentClick, true);
        }

        trigger.addEventListener("click", function () {
            if (popup) closePopup();
            else openPopup();
        });
        root.setAttribute("data-person-picker-ready", "1");
    }

    // `initIn(root)` também é chamado por modal.js depois de injetar um
    // formulário via LPSModal.open(): o forEach abaixo só cobre o DOM que
    // já existia quando este script rodou, então um picker dentro de um
    // modal aninhado (ex.: "Atividade" em "+ Nova tarefa") precisa ser
    // inicializado de novo manualmente após ser inserido na página.
    function initIn(root) {
        root.querySelectorAll("[data-person-picker]:not([data-person-picker-ready])").forEach(init);
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);

    initIn(document);
})();
