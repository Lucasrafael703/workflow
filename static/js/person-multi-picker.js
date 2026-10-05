/* Seletor de múltiplas pessoas (participantes) com busca e chips
   removíveis — mesma estrutura de tag-picker.js, mas buscando pessoas
   (person-search, mesmo endpoint do person-picker.js). A lista inicial abre
   sem texto e a busca começa na primeira letra. Clicar um
   resultado ADICIONA um chip; cada chip tem um "×" para remover. O
   <select multiple hidden> continua sendo a fonte de verdade submetida
   pelo form. */
(function () {
    "use strict";

    var DEBOUNCE_MS = 250;
    var AVATAR_COLOR_COUNT = 6;
    var pickerSequence = 0;

    function initials(name) {
        return (name || "").slice(0, 2).toUpperCase();
    }

    function avatarColorIndex(id) {
        var n = Number(id);
        return Number.isFinite(n) ? n % AVATAR_COLOR_COUNT : 0;
    }

    function init(root) {
        var select = root.querySelector("select");
        var chipsContainer = root.querySelector(".person-multi-picker__chips");
        var addButton = root.querySelector(".person-multi-picker__add");
        var searchUrl = root.getAttribute("data-search-url");
        var excludeFieldId = root.getAttribute("data-exclude-field");
        var createUrl = root.getAttribute("data-create-url");
        var createLabel = root.getAttribute("data-create-label") || "Cadastrar novo usuário";

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

        function selectedIds() {
            return Array.prototype.map.call(select.selectedOptions, function (opt) {
                return opt.value;
            });
        }

        function excludedId() {
            if (!excludeFieldId) return null;
            var field = document.getElementById(excludeFieldId);
            return field ? field.value : null;
        }

        function isSelected(id) {
            return selectedIds().indexOf(String(id)) !== -1;
        }

        function ensureOption(person) {
            var existing = select.querySelector('option[value="' + person.id + '"]');
            if (existing) {
                existing.selected = true;
                return;
            }
            var option = document.createElement("option");
            option.value = person.id;
            option.textContent = person.name;
            option.selected = true;
            select.appendChild(option);
        }

        function renderChip(person) {
            var chip = document.createElement("span");
            chip.className = "person-multi-picker__chip";
            chip.setAttribute("data-person-id", person.id);

            var avatar = document.createElement("span");
            avatar.className = "avatar avatar--" + avatarColorIndex(person.id);
            avatar.textContent = initials(person.name);
            chip.appendChild(avatar);
            chip.appendChild(document.createTextNode(person.name));

            var remove = document.createElement("button");
            remove.type = "button";
            remove.className = "person-multi-picker__remove";
            remove.setAttribute("aria-label", "Remover");
            remove.textContent = "×";
            remove.addEventListener("click", function () {
                var option = select.querySelector('option[value="' + person.id + '"]');
                if (option) option.selected = false;
                chip.remove();
                select.dispatchEvent(new Event("change", { bubbles: true }));
            });
            chip.appendChild(remove);
            chipsContainer.insertBefore(chip, addButton);
        }

        function add(person) {
            if (isSelected(person.id)) return;
            ensureOption(person);
            renderChip(person);
            select.dispatchEvent(new Event("change", { bubbles: true }));
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
            createButton = null;
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
            var addIndex = candidates.indexOf(addButton);
            var target = addIndex === -1
                ? null
                : candidates[addIndex + (reverse ? -1 : 1)];
            closePopup();
            if (target) target.focus();
            else addButton.blur();
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
            var exclude = excludedId();
            var available = list.filter(function (person) {
                return !isSelected(person.id) && (!exclude || String(person.id) !== String(exclude));
            });
            results = available;
            activeIndex = -1;
            var resultsEl = popup.querySelector(".person-picker__results");
            resultsEl.innerHTML = "";
            resultsEl.setAttribute("aria-busy", "false");

            if (available.length === 0) {
                renderMessage("Nenhum resultado encontrado");
                return;
            }

            available.forEach(function (person, index) {
                var option = document.createElement("button");
                option.type = "button";
                option.className = "person-picker__option";
                option.id = resultsEl.id + "-option-" + index;
                option.setAttribute("role", "option");
                option.setAttribute("aria-selected", "false");
                option.textContent = person.name;
                option.addEventListener("click", function () {
                    add(person);
                    closePopup();
                });
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
            renderMessage("Buscando...");
            var requestOptions = {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            };
            if (controller) requestOptions.signal = controller.signal;
            fetch(searchUrl + "?q=" + encodeURIComponent(term), requestOptions)
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
                onSuccess: function (person) { add(person); },
            });
        }

        function openPopup() {
            if (popup) return;

            popup = document.createElement("div");
            popup.className = "person-picker__popup";
            var resultsId = "person-multi-picker-results-" + (++pickerSequence);
            popup.innerHTML =
                '<input type="text" class="person-picker__search" placeholder="Buscar participante..." role="combobox" aria-expanded="true" aria-haspopup="listbox" aria-autocomplete="list" autocomplete="off">' +
                '<div class="person-picker__results" role="listbox"></div>';
            root.appendChild(popup);

            searchInput = popup.querySelector(".person-picker__search");
            searchInput.setAttribute("aria-controls", resultsId);
            popup.querySelector(".person-picker__results").id = resultsId;
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
                    if (activeIndex >= 0 && results[activeIndex]) {
                        add(results[activeIndex]);
                        closePopup();
                    }
                } else if (event.key === "Escape") {
                    closePopup();
                    suppressFocusOpen = true;
                    addButton.focus();
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

        addButton.addEventListener("pointerdown", function () {
            pointerDown = true;
            setTimeout(function () { pointerDown = false; }, 0);
        });
        addButton.addEventListener("focus", function () {
            if (!pointerDown && !suppressFocusOpen && !popup) openPopup();
        });
        addButton.addEventListener("click", function () {
            if (popup) closePopup();
            else openPopup();
        });
        root.setAttribute("data-person-multi-picker-ready", "1");
    }

    // Mesmo motivo de tag-picker.js: um picker aberto dentro de um modal
    // injetado via LPSModal.open() só ganha vida se reinicializado depois
    // da inserção.
    function initIn(root) {
        root.querySelectorAll("[data-person-multi-picker]:not([data-person-multi-picker-ready])").forEach(init);
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);

    initIn(document);
})();
