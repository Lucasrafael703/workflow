/* Seletor de múltiplas pessoas (participantes) com busca e chips
   removíveis — mesma estrutura de tag-picker.js, mas buscando pessoas
   (person-search, mesmo endpoint do person-picker.js) e exigindo 3+
   caracteres antes de buscar (mesma regra do person-picker.js). Clicar um
   resultado ADICIONA um chip; cada chip tem um "×" para remover. O
   <select multiple hidden> continua sendo a fonte de verdade submetida
   pelo form. */
(function () {
    "use strict";

    var DEBOUNCE_MS = 250;
    var MIN_CHARS = 3;
    var AVATAR_COLOR_COUNT = 6;

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

        var popup = null;
        var results = [];
        var activeIndex = -1;
        var debounceTimer = null;

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
            popup.remove();
            popup = null;
            document.removeEventListener("click", onDocumentClick, true);
        }

        function onDocumentClick(event) {
            if (!root.contains(event.target)) closePopup();
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
            var exclude = excludedId();
            var available = list.filter(function (person) {
                return !isSelected(person.id) && (!exclude || String(person.id) !== String(exclude));
            });
            results = available;
            activeIndex = -1;
            var resultsEl = popup.querySelector(".person-picker__results");
            resultsEl.innerHTML = "";

            if (available.length === 0) {
                renderMessage("Nada encontrado.");
                return;
            }

            available.forEach(function (person, index) {
                var option = document.createElement("button");
                option.type = "button";
                option.className = "person-picker__option";
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
            fetch(searchUrl + "?q=" + encodeURIComponent(term), {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            })
                .then(function (response) { return response.json(); })
                .then(function (data) { renderResults(data.results || []); })
                .catch(function () { renderResults([]); });
        }

        function openPopup() {
            if (popup) return;

            popup = document.createElement("div");
            popup.className = "person-picker__popup";
            popup.innerHTML =
                '<input type="text" class="person-picker__search" placeholder="Buscar participante...">' +
                '<div class="person-picker__results"></div>';
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
                    if (activeIndex >= 0 && results[activeIndex]) {
                        add(results[activeIndex]);
                        closePopup();
                    }
                } else if (event.key === "Escape") {
                    closePopup();
                }
            });

            searchInput.focus();
            renderMessage("Digite ao menos " + MIN_CHARS + " letras para buscar.");
            document.addEventListener("click", onDocumentClick, true);
        }

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
