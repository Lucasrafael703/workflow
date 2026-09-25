/* Seletor de marcadores M2M com busca e chips removíveis — variante de
   múltipla escolha do person-picker.js: clicar um resultado ADICIONA um
   chip (não fecha/substitui como os pickers de valor único), e cada chip
   tem um "×" para remover. O <select multiple hidden> continua sendo a
   fonte de verdade submetida pelo form; este JS só sincroniza suas
   <option selected> com os chips exibidos. */
(function () {
    "use strict";

    var DEBOUNCE_MS = 250;

    function init(root) {
        var select = root.querySelector("select");
        var chipsContainer = root.querySelector(".tag-picker__chips");
        var addButton = root.querySelector(".tag-picker__add");
        var searchUrl = root.getAttribute("data-search-url");

        var popup = null;
        var results = [];
        var activeIndex = -1;
        var debounceTimer = null;

        function selectedIds() {
            return Array.prototype.map.call(select.selectedOptions, function (opt) {
                return opt.value;
            });
        }

        function isSelected(id) {
            return selectedIds().indexOf(String(id)) !== -1;
        }

        function ensureOption(tag) {
            var existing = select.querySelector('option[value="' + tag.id + '"]');
            if (existing) {
                existing.selected = true;
                return;
            }
            var option = document.createElement("option");
            option.value = tag.id;
            option.textContent = tag.name;
            option.selected = true;
            select.appendChild(option);
        }

        function renderChip(tag) {
            var chip = document.createElement("span");
            chip.className = "tag-picker__chip tag-chip tag-chip--" + (tag.color || 0);
            chip.setAttribute("data-tag-id", tag.id);
            chip.textContent = tag.name;

            var remove = document.createElement("button");
            remove.type = "button";
            remove.className = "tag-picker__remove";
            remove.setAttribute("aria-label", "Remover");
            remove.textContent = "×";
            remove.addEventListener("click", function () {
                var option = select.querySelector('option[value="' + tag.id + '"]');
                if (option) option.selected = false;
                chip.remove();
                select.dispatchEvent(new Event("change", { bubbles: true }));
            });
            chip.appendChild(remove);
            chipsContainer.insertBefore(chip, addButton);
        }

        function add(tag) {
            if (isSelected(tag.id)) return;
            ensureOption(tag);
            renderChip(tag);
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

        function renderResults(list) {
            results = list;
            activeIndex = -1;
            var resultsEl = popup.querySelector(".tag-picker__results");
            resultsEl.innerHTML = "";

            var available = list.filter(function (tag) { return !isSelected(tag.id); });
            if (available.length === 0) {
                var empty = document.createElement("div");
                empty.className = "tag-picker__empty";
                empty.textContent = "Nenhum marcador encontrado.";
                resultsEl.appendChild(empty);
                return;
            }

            available.forEach(function (tag, index) {
                var option = document.createElement("button");
                option.type = "button";
                option.className = "tag-picker__option";
                var swatch = document.createElement("span");
                swatch.className = "tag-chip tag-chip--" + (tag.color || 0);
                swatch.textContent = tag.name;
                option.appendChild(swatch);
                option.addEventListener("click", function () {
                    add(tag);
                    closePopup();
                });
                option.addEventListener("mouseenter", function () { setActive(index); });
                resultsEl.appendChild(option);
            });
        }

        function setActive(index) {
            var options = popup.querySelectorAll(".tag-picker__option");
            options.forEach(function (el) { el.classList.remove("is-active"); });
            if (index >= 0 && index < options.length) {
                options[index].classList.add("is-active");
                activeIndex = index;
            }
        }

        function search(term) {
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
            popup.className = "tag-picker__popup person-picker__popup";
            popup.innerHTML =
                '<input type="text" class="person-picker__search" placeholder="Buscar marcador...">' +
                '<div class="tag-picker__results person-picker__results"></div>';
            root.appendChild(popup);

            var searchInput = popup.querySelector(".person-picker__search");
            searchInput.addEventListener("input", function () {
                clearTimeout(debounceTimer);
                var term = searchInput.value;
                debounceTimer = setTimeout(function () { search(term); }, DEBOUNCE_MS);
            });
            searchInput.addEventListener("keydown", function (event) {
                if (event.key === "Enter") {
                    event.preventDefault();
                    var available = results.filter(function (tag) { return !isSelected(tag.id); });
                    if (activeIndex >= 0 && available[activeIndex]) {
                        add(available[activeIndex]);
                        closePopup();
                    }
                } else if (event.key === "Escape") {
                    closePopup();
                }
            });

            searchInput.focus();
            search("");
            document.addEventListener("click", onDocumentClick, true);
        }

        addButton.addEventListener("click", function () {
            if (popup) closePopup();
            else openPopup();
        });
        root.setAttribute("data-tag-picker-ready", "1");
    }

    // Ver o mesmo comentário em person-picker.js: um seletor de tags aberto
    // dentro de um modal injetado via LPSModal.open() só ganha vida se
    // reinicializado depois da inserção — modal.js chama initIn de novo.
    function initIn(root) {
        root.querySelectorAll("[data-tag-picker]:not([data-tag-picker-ready])").forEach(init);
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);

    initIn(document);
})();
