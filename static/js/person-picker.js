/* Seletor de pessoa com busca (estilo "atribuir responsável" do Monday): abre
   um popup, filtra por nome enquanto digita, e permite criar um usuário sem
   sair do formulário atual quando a pessoa não existe ainda. */
(function () {
    "use strict";

    var DEBOUNCE_MS = 250;

    function init(root) {
        var hidden = root.querySelector("input[type=hidden]");
        var trigger = root.querySelector(".person-picker__trigger");
        var label = root.querySelector(".person-picker__label");
        var searchUrl = root.getAttribute("data-search-url");
        var createUrl = root.getAttribute("data-create-url");
        var createLabel = root.getAttribute("data-create-label") || "Criar novo usuário";

        var popup = null;
        var results = [];
        var activeIndex = -1;
        var debounceTimer = null;

        function closePopup() {
            if (!popup) return;
            popup.remove();
            popup = null;
            root.classList.remove("is-open");
            document.removeEventListener("click", onDocumentClick, true);
        }

        function onDocumentClick(event) {
            if (!root.contains(event.target)) closePopup();
        }

        function select(person) {
            hidden.value = person.id;
            label.textContent = person.name;
            label.classList.remove("muted");
            hidden.dispatchEvent(new Event("change", { bubbles: true }));
            closePopup();
            trigger.focus();
        }

        function renderResults(list) {
            results = list;
            activeIndex = -1;
            var resultsEl = popup.querySelector(".person-picker__results");
            resultsEl.innerHTML = "";

            if (list.length === 0) {
                var empty = document.createElement("div");
                empty.className = "person-picker__empty";
                empty.textContent = "Ninguém encontrado.";
                resultsEl.appendChild(empty);
                return;
            }

            list.forEach(function (person, index) {
                var option = document.createElement("button");
                option.type = "button";
                option.className = "person-picker__option";
                option.textContent = person.name;
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
            fetch(searchUrl + "?q=" + encodeURIComponent(term), {
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

            popup = document.createElement("div");
            popup.className = "person-picker__popup";
            popup.innerHTML =
                '<input type="text" class="person-picker__search" placeholder="Buscar pessoa...">' +
                '<div class="person-picker__results"></div>';

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
            search("");
            document.addEventListener("click", onDocumentClick, true);
        }

        trigger.addEventListener("click", function () {
            if (popup) closePopup();
            else openPopup();
        });
    }

    document.querySelectorAll("[data-person-picker]").forEach(init);
})();
