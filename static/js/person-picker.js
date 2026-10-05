/* Seletor de pessoa com busca (estilo "atribuir responsável" do Monday): abre
   um popup, filtra por nome enquanto digita, e permite criar um usuário sem
   sair do formulário atual quando a pessoa não existe ainda. */
(function () {
    "use strict";

    var DEBOUNCE_MS = 250;
    var pickerSequence = 0;

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
        var activeRequest = null;
        var requestSequence = 0;
        var searchInput = null;
        var createButton = null;
        var suppressFocusOpen = false;
        var pointerDown = false;
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
                    if (hidden.value) {
                        hidden.value = "";
                        label.textContent = emptyLabel;
                        label.classList.add("muted");
                    }
                    // Mesmo sem seleção direta, propaga a mudança para o
                    // próximo campo (Cliente -> Obra -> Centro de custo).
                    hidden.dispatchEvent(new Event("change", { bubbles: true }));
                });
            }
        }

        function closePopup() {
            if (!popup) return;
            clearTimeout(debounceTimer);
            if (activeRequest && activeRequest.abort) activeRequest.abort();
            activeRequest = null;
            requestSequence += 1;
            popup.remove();
            popup = null;
            searchInput = null;
            root.classList.remove("is-open");
            trigger.setAttribute("aria-expanded", "false");
            trigger.removeAttribute("aria-controls");
            document.removeEventListener("click", onDocumentClick, true);
        }

        function onDocumentClick(event) {
            if (!root.contains(event.target)) closePopup();
        }

        function focusAdjacent(reverse) {
            var candidates = Array.prototype.filter.call(
                document.querySelectorAll(
                    "a[href], button:not([disabled]), input:not([disabled]):not([type=hidden]), " +
                    "select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])"
                ),
                function (element) {
                    return !element.closest(".person-picker__popup") && !element.hidden;
                }
            );
            var triggerIndex = candidates.indexOf(trigger);
            var target = triggerIndex === -1
                ? null
                : candidates[triggerIndex + (reverse ? -1 : 1)];
            closePopup();
            if (target) target.focus();
            else trigger.blur();
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
            suppressFocusOpen = true;
            trigger.focus();
            setTimeout(function () { suppressFocusOpen = false; }, 0);
        }

        function renderMessage(text) {
            results = [];
            activeIndex = -1;
            var resultsEl = popup.querySelector(".person-picker__results");
            resultsEl.innerHTML = "";
            resultsEl.setAttribute("aria-busy", text === "Buscando..." ? "true" : "false");
            var empty = document.createElement("div");
            empty.className = "person-picker__empty";
            empty.textContent = text;
            resultsEl.appendChild(empty);
            if (createButton) createButton.hidden = text !== "Nenhum resultado encontrado";
        }

        function renderResults(list) {
            var visibleList = list.filter(function (person) {
                return !isSectorPicker || !allowedSectorIds.length || allowedSectorIds.indexOf(String(person.id)) !== -1;
            });
            results = visibleList;
            activeIndex = -1;
            var resultsEl = popup.querySelector(".person-picker__results");
            resultsEl.innerHTML = "";
            resultsEl.setAttribute("aria-busy", "false");

            if (visibleList.length === 0) {
                renderMessage("Nenhum resultado encontrado");
                return;
            }
            if (createButton) createButton.hidden = true;

            visibleList.forEach(function (person, index) {
                var option = document.createElement("button");
                option.type = "button";
                option.className = "person-picker__option";
                option.id = resultsEl.id + "-option-" + index;
                option.setAttribute("role", "option");
                option.setAttribute("aria-selected", "false");
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
            options.forEach(function (el) {
                el.classList.remove("is-active");
                el.setAttribute("aria-selected", "false");
            });
            if (index >= 0 && index < options.length) {
                options[index].classList.add("is-active");
                options[index].setAttribute("aria-selected", "true");
                options[index].scrollIntoView({ block: "nearest" });
                if (searchInput) searchInput.setAttribute("aria-activedescendant", options[index].id);
            } else if (searchInput) {
                searchInput.removeAttribute("aria-activedescendant");
            }
            activeIndex = index;
        }

        function search(term) {
            if (!popup) return;
            if (activeRequest && activeRequest.abort) activeRequest.abort();
            var sequence = ++requestSequence;
            var controller = window.AbortController ? new AbortController() : null;
            activeRequest = controller;
            var params = new URLSearchParams({ q: term });
            if (sectorFieldId) {
                var sectorField = document.getElementById(sectorFieldId);
                params.set("sector", sectorField ? sectorField.value : "");
            }
            if (filterFieldId && filterParam) {
                var dependsOn = document.getElementById(filterFieldId);
                if (dependsOn && dependsOn.value) params.set(filterParam, dependsOn.value);
            }
            renderMessage("Buscando...");
            var requestOptions = {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            };
            if (controller) requestOptions.signal = controller.signal;
            fetch(searchUrl + "?" + params.toString(), requestOptions)
                .then(function (response) {
                    if (response && response.ok === false) throw new Error("search_failed");
                    return response.json();
                })
                .then(function (data) {
                    if (!popup || sequence !== requestSequence) return;
                    activeRequest = null;
                    renderResults(data.results || []);
                })
                .catch(function (error) {
                    if (error && error.name === "AbortError") return;
                    if (!popup || sequence !== requestSequence) return;
                    activeRequest = null;
                    renderMessage("Não foi possível carregar as opções. Tente novamente.");
                });
        }

        function openCreateModal(initialName) {
            if (!createUrl || !window.LPSModal) return;
            var targetUrl = createUrl;
            if (initialName) {
                try {
                    var parsedUrl = new URL(createUrl, window.location.href);
                    parsedUrl.searchParams.set("initial_name", initialName);
                    targetUrl = parsedUrl.toString();
                } catch (error) {
                    targetUrl = createUrl;
                }
            }
            window.LPSModal.open(targetUrl, {
                onSuccess: function (person) { select(person); },
            });
        }

        function openPopup() {
            if (popup) return;
            root.classList.add("is-open");
            trigger.setAttribute("aria-expanded", "true");

            popup = document.createElement("div");
            popup.className = "person-picker__popup";
            createButton = null;
            var resultsId = "person-picker-results-" + (++pickerSequence);
            popup.innerHTML =
                '<input type="text" class="person-picker__search" role="combobox" aria-expanded="true" aria-haspopup="listbox" aria-autocomplete="list" autocomplete="off">' +
                '<div class="person-picker__results" role="listbox"></div>';
            searchInput = popup.querySelector(".person-picker__search");
            searchInput.placeholder = placeholder;
            searchInput.setAttribute("aria-controls", resultsId);
            popup.querySelector(".person-picker__results").id = resultsId;
            trigger.setAttribute("aria-controls", resultsId);

            if (createUrl) {
                createButton = document.createElement("button");
                createButton.type = "button";
                createButton.className = "person-picker__create";
                createButton.hidden = true;
                createButton.innerHTML =
                    '<svg width="15" height="15" viewBox="0 0 20 20" aria-hidden="true"><use href="#i-plus"></use></svg>' +
                    "<span>" + createLabel + "</span>";
                createButton.addEventListener("click", function () {
                    var initialName = searchInput ? searchInput.value.trim() : "";
                    closePopup();
                    openCreateModal(initialName);
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
                    suppressFocusOpen = true;
                    trigger.focus();
                    setTimeout(function () { suppressFocusOpen = false; }, 0);
                } else if (event.key === "Tab") {
                    event.preventDefault();
                    focusAdjacent(event.shiftKey);
                }
            });

            searchInput.focus();
            document.addEventListener("click", onDocumentClick, true);
            search("");
        }

        trigger.addEventListener("pointerdown", function () {
            pointerDown = true;
            setTimeout(function () { pointerDown = false; }, 0);
        });
        trigger.addEventListener("focus", function () {
            if (!pointerDown && !suppressFocusOpen && !popup) openPopup();
        });
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
