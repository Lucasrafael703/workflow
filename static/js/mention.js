/* Autocomplete de @menção em qualquer campo de texto marcado com
   data-mention: textarea comum ou o contenteditable do RichTextWidget
   (rich-text.js). Digitar "@" abre um popup posicionado no cursor,
   buscando em PersonSearchView (mesmo endpoint do person-picker.js);
   escolher uma pessoa insere "@username" como texto puro — sem HTML
   especial, para o parser de menção do servidor (MENTION_PATTERN) casar
   sem precisar de nenhuma mudança no sanitizador. */
(function () {
    "use strict";

    var DEBOUNCE_MS = 250;
    var TRIGGER_PATTERN = /(?:^|\s)@([^\s@]*)$/;

    function init(field) {
        var searchUrl =
            field.getAttribute("data-mention-search-url") ||
            document.body.getAttribute("data-mention-search-url");
        if (!searchUrl) return;

        var isContentEditable = field.isContentEditable;
        var popup = null;
        var results = [];
        var activeIndex = -1;
        var debounceTimer = null;
        var triggerStart = null; // posição (textarea) onde o "@" do token atual começa
        var triggerEnd = null; // posição (textarea) onde o token atual termina

        var scrollAtOpen = { x: 0, y: 0 };

        function closePopup() {
            if (!popup) return;
            popup.remove();
            popup = null;
            triggerStart = null;
            document.removeEventListener("click", onDocumentClick, true);
            document.removeEventListener("scroll", onDocumentScroll, true);
        }

        function onDocumentClick(event) {
            if (popup && !popup.contains(event.target) && event.target !== field) closePopup();
        }

        function onDocumentScroll(event) {
            // Um reflow qualquer (texto novo no campo, popup abrindo/
            // reposicionando) pode gerar um scroll espúrio de 1px que não
            // é o usuário rolando a página de fato — só fecha acima de um
            // limiar real de movimento.
            var moved = Math.abs(window.scrollX - scrollAtOpen.x) > 4 || Math.abs(window.scrollY - scrollAtOpen.y) > 4;
            if (!moved) return;
            closePopup();
        }

        // --- Leitura do token "@algo" digitado ------------------------------

        function currentToken() {
            if (isContentEditable) {
                var selection = window.getSelection();
                if (!selection.rangeCount) return null;
                var range = selection.getRangeAt(0);
                if (!field.contains(range.startContainer)) return null;
                var textBefore = range.startContainer.textContent.slice(0, range.startOffset);
                var match = TRIGGER_PATTERN.exec(textBefore);
                return match ? { term: match[1], range: range } : null;
            }
            var caret = field.selectionStart;
            var textBefore = field.value.slice(0, caret);
            var match = TRIGGER_PATTERN.exec(textBefore);
            if (!match) return null;
            return { term: match[1], start: caret - match[1].length - 1, end: caret };
        }

        // --- Posicionamento do popup no cursor ------------------------------

        function caretRect() {
            if (isContentEditable) {
                var selection = window.getSelection();
                if (!selection.rangeCount) return field.getBoundingClientRect();
                var rect = selection.getRangeAt(0).getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) return field.getBoundingClientRect();
                return rect;
            }
            // Textarea não expõe a posição do caret nativamente: espelha o
            // texto até o cursor num <div> invisível com a mesma tipografia
            // e mede onde o último caractere (marcador) cai.
            var mirror = document.createElement("div");
            var style = window.getComputedStyle(field);
            ["fontFamily", "fontSize", "fontWeight", "lineHeight", "padding", "border", "boxSizing", "whiteSpace", "wordWrap"]
                .forEach(function (prop) { mirror.style[prop] = style[prop]; });
            mirror.style.position = "absolute";
            mirror.style.top = "0";
            mirror.style.left = "-9999px";
            mirror.style.visibility = "hidden";
            mirror.style.whiteSpace = "pre-wrap";
            mirror.style.width = field.clientWidth + "px";
            mirror.textContent = field.value.slice(0, field.selectionStart);
            var marker = document.createElement("span");
            marker.textContent = "​";
            mirror.appendChild(marker);
            document.body.appendChild(mirror);
            var fieldRect = field.getBoundingClientRect();
            var markerRect = marker.getBoundingClientRect();
            var mirrorRect = mirror.getBoundingClientRect();
            var rect = {
                left: fieldRect.left + (markerRect.left - mirrorRect.left) - field.scrollLeft,
                top: fieldRect.top + (markerRect.top - mirrorRect.top) - field.scrollTop,
                bottom: fieldRect.top + (markerRect.bottom - mirrorRect.top) - field.scrollTop,
            };
            document.body.removeChild(mirror);
            return rect;
        }

        // --- Inserção do resultado escolhido ---------------------------------

        function insertMention(person) {
            var mention = "@" + person.username + " ";
            if (isContentEditable) {
                var selection = window.getSelection();
                if (!selection.rangeCount) return;
                var range = selection.getRangeAt(0);
                var textNode = range.startContainer;
                var text = textNode.textContent;
                var match = TRIGGER_PATTERN.exec(text.slice(0, range.startOffset));
                if (!match) return;
                // match[0] é " @termo" (ou "@termo" no início do texto); o "@"
                // fica a match[1].length + 1 caracteres do fim do match.
                var tokenStart = range.startOffset - match[1].length - 1;
                textNode.textContent = text.slice(0, tokenStart) + mention + text.slice(range.startOffset);
                var newRange = document.createRange();
                newRange.setStart(textNode, tokenStart + mention.length);
                newRange.collapse(true);
                selection.removeAllRanges();
                selection.addRange(newRange);
                field.dispatchEvent(new Event("input", { bubbles: true }));
            } else {
                var value = field.value;
                field.value = value.slice(0, triggerStart) + mention + value.slice(triggerEnd);
                var cursor = triggerStart + mention.length;
                field.setSelectionRange(cursor, cursor);
                field.dispatchEvent(new Event("input", { bubbles: true }));
            }
            field.focus();
            closePopup();
        }

        // --- Popup: busca, resultados, navegação -----------------------------

        function renderResults(list) {
            results = list;
            activeIndex = list.length ? 0 : -1;
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
                option.className = "person-picker__option" + (index === 0 ? " is-active" : "");
                option.textContent = person.name;
                option.addEventListener("mousedown", function (event) { event.preventDefault(); });
                option.addEventListener("click", function () { insertMention(person); });
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
                .then(function (data) { if (popup) renderResults(data.results || []); })
                .catch(function () { if (popup) renderResults([]); });
        }

        function openPopup(rect) {
            if (!popup) {
                popup = document.createElement("div");
                popup.className = "person-picker__popup mention-popup";
                popup.innerHTML = '<div class="person-picker__results"></div>';
                document.body.appendChild(popup);
                scrollAtOpen = { x: window.scrollX, y: window.scrollY };
                document.addEventListener("click", onDocumentClick, true);
                document.addEventListener("scroll", onDocumentScroll, true);
            }
            popup.style.left = rect.left + window.scrollX + "px";
            popup.style.top = rect.bottom + window.scrollY + 4 + "px";
        }

        function handleTrigger() {
            var token = currentToken();
            if (!token) {
                closePopup();
                return;
            }
            if (!isContentEditable) {
                triggerStart = token.start;
                triggerEnd = token.end;
            }
            openPopup(caretRect());
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () { search(token.term); }, DEBOUNCE_MS);
        }

        field.addEventListener("input", handleTrigger);
        field.addEventListener("keydown", function (event) {
            if (!popup) return;
            if (event.key === "ArrowDown") {
                event.preventDefault();
                setActive(Math.min(activeIndex + 1, results.length - 1));
            } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setActive(Math.max(activeIndex - 1, 0));
            } else if (event.key === "Enter" || event.key === "Tab") {
                if (activeIndex >= 0 && results[activeIndex]) {
                    event.preventDefault();
                    insertMention(results[activeIndex]);
                }
            } else if (event.key === "Escape") {
                closePopup();
            }
        });
        field.addEventListener("blur", function () {
            // Sem isto o popup fecharia antes do mousedown da opção clicada
            // registrar a escolha — o mousedown com preventDefault acima já
            // evita que o blur aconteça antes do click, mas o setTimeout dá
            // uma folga extra para navegadores que divergem na ordem exata.
            setTimeout(closePopup, 150);
        });

        field.setAttribute("data-mention-ready", "1");
    }

    function initIn(root) {
        root.querySelectorAll("[data-mention]:not([data-mention-ready])").forEach(init);
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);

    initIn(document);
})();
