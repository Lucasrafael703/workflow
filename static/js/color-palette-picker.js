/* ColorPalettePicker: popover de 36 cores fixas para customizar a cor de um
   status/etapa/prioridade/marcador por organização. Sem <input type="color">.
   Segue o mesmo padrão de popup do tag-picker.js/person-picker.js
   (window.LPSWidgets.push), mas com grid de cores + navegação 2D por setas.

   Dois modos, pelo mesmo seletor [data-color-swatch]:
   - Com `data-save-url`: clique salva IMEDIATAMENTE via POST (tela de
     configuração e listagens de Cadastros).
   - Sem `data-save-url`: clique só grava o hex no <input hidden> irmão,
     deixando o submit do form tradicional levar o valor (ColorPaletteWidget,
     usado na criação de um novo marcador). */
(function () {
    "use strict";

    var COLS = 6; // largura do grid — usada para navegação por ↑/↓

    function getCookie(name) {
        var match = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
        return match ? decodeURIComponent(match.pop()) : "";
    }

    function init(swatch) {
        var PALETTE = (window.LPSColors && window.LPSColors.PALETTE) || [];
        var getContrastText = (window.LPSColors && window.LPSColors.getContrastText) || function () {
            return "#FFFFFF";
        };

        var saveUrl = swatch.getAttribute("data-save-url");
        var code = swatch.getAttribute("data-code");
        var hiddenInput = saveUrl ? null : swatch.previousElementSibling;

        var popover = null;
        var scrim = null;
        var focusedIndex = -1;
        var originalHex = null;

        function currentHex() {
            return swatch.getAttribute("data-current-color") || null;
        }

        function applySwatch(hex) {
            swatch.style.setProperty("--swatch-color", hex);
            swatch.setAttribute("data-current-color", hex);
            swatch.setAttribute("aria-label", "Cor atual: " + hex + ". Clique para mudar.");
        }

        function isMobile() {
            return window.matchMedia("(max-width: 720px)").matches;
        }

        function positionPopover() {
            if (isMobile()) return;
            var rect = swatch.getBoundingClientRect();
            var popRect = popover.getBoundingClientRect();
            if (rect.left + popRect.width > window.innerWidth - 12) {
                popover.setAttribute("data-align", "right");
            }
        }

        function optionsList() {
            return Array.prototype.slice.call(popover.querySelectorAll(".color-palette-cell"));
        }

        function focusOption(index) {
            var opts = optionsList();
            if (index < 0 || index >= opts.length) return;
            focusedIndex = index;
            opts.forEach(function (opt) { opt.setAttribute("tabindex", "-1"); });
            opts[index].setAttribute("tabindex", "0");
            opts[index].focus();
        }

        function moveFocus(deltaRow, deltaCol) {
            if (deltaCol !== 0) {
                var next = focusedIndex + deltaCol;
                next = Math.max(0, Math.min(PALETTE.length - 1, next));
                focusOption(next);
                return;
            }
            var row = Math.floor(focusedIndex / COLS);
            var col = focusedIndex % COLS;
            var maxRow = Math.floor((PALETTE.length - 1) / COLS);
            var newRow = Math.max(0, Math.min(maxRow, row + deltaRow));
            var newIndex = Math.min(newRow * COLS + col, PALETTE.length - 1);
            focusOption(newIndex);
        }

        function trapTab(event) {
            var opts = optionsList();
            var first = opts[0];
            var last = opts[opts.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }

        function buildCell(color, index) {
            var selected = currentHex() && currentHex().toUpperCase() === color.hex.toUpperCase();
            var cell = document.createElement("button");
            cell.type = "button";
            cell.className = "color-palette-cell" + (selected ? " is-selected" : "");
            cell.setAttribute("role", "option");
            cell.setAttribute("aria-selected", selected ? "true" : "false");
            cell.setAttribute("data-hex", color.hex);
            cell.title = color.name;
            cell.setAttribute("aria-label", color.name);
            cell.setAttribute("tabindex", selected ? "0" : "-1");
            cell.style.setProperty("--cell-color", color.hex);
            if (selected) {
                focusedIndex = index;
                cell.style.setProperty(
                    "--check-color",
                    getContrastText(color.hex)
                );
            }
            cell.addEventListener("click", function () { choose(color); });
            return cell;
        }

        function buildPopover() {
            var el = document.createElement("div");
            el.className = "color-palette-popover";
            el.setAttribute("role", "listbox");
            el.setAttribute("aria-label", "Escolha uma cor");
            el.tabIndex = -1;

            var grid = document.createElement("div");
            grid.className = "color-palette-grid";
            PALETTE.forEach(function (color, index) {
                grid.appendChild(buildCell(color, index));
            });
            el.appendChild(grid);
            el.addEventListener("keydown", onPopoverKeydown);
            return el;
        }

        function onPopoverKeydown(event) {
            switch (event.key) {
                case "ArrowLeft": event.preventDefault(); moveFocus(0, -1); break;
                case "ArrowRight": event.preventDefault(); moveFocus(0, 1); break;
                case "ArrowUp": event.preventDefault(); moveFocus(-1, 0); break;
                case "ArrowDown": event.preventDefault(); moveFocus(1, 0); break;
                case "Escape": event.preventDefault(); close(true); break;
                case "Tab": trapTab(event); break;
                case "Enter":
                case " ": {
                    event.preventDefault();
                    var opts = optionsList();
                    var hex = opts[focusedIndex] && opts[focusedIndex].getAttribute("data-hex");
                    var picked = PALETTE.filter(function (c) { return c.hex === hex; })[0];
                    if (picked) choose(picked);
                    break;
                }
                default: break;
            }
        }

        function onDocumentClick(event) {
            if (popover && !popover.contains(event.target) && event.target !== swatch) {
                close(false);
            }
        }

        function open() {
            if (popover) return;
            originalHex = currentHex();
            popover = buildPopover();
            swatch.parentElement.style.position = "relative";
            swatch.parentElement.appendChild(popover);

            if (isMobile()) {
                scrim = document.createElement("div");
                scrim.className = "color-palette-scrim";
                scrim.addEventListener("click", function () { close(false); });
                document.body.appendChild(scrim);
            }

            positionPopover();
            swatch.setAttribute("aria-expanded", "true");
            focusOption(focusedIndex >= 0 ? focusedIndex : 0);
            document.addEventListener("click", onDocumentClick, true);
        }

        function close(returnFocus) {
            if (!popover) return;
            popover.remove();
            popover = null;
            if (scrim) { scrim.remove(); scrim = null; }
            swatch.setAttribute("aria-expanded", "false");
            document.removeEventListener("click", onDocumentClick, true);
            if (returnFocus) swatch.focus();
        }

        function choose(color) {
            applySwatch(color.hex);
            close(true);

            if (!saveUrl) {
                if (hiddenInput) hiddenInput.value = color.hex;
                return;
            }

            var body = new URLSearchParams();
            body.set("code", code);
            body.set("color", color.hex);

            fetch(saveUrl, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: body,
            })
                .then(function (response) {
                    if (!response.ok) throw new Error("save failed");
                    return response.json();
                })
                .catch(function () {
                    if (originalHex) applySwatch(originalHex);
                    window.alert("Não foi possível salvar a cor. Tente novamente.");
                });
        }

        swatch.addEventListener("click", function () {
            if (popover) close(true); else open();
        });
        swatch.setAttribute("data-color-swatch-ready", "1");
    }

    function initIn(root) {
        root.querySelectorAll("[data-color-swatch]:not([data-color-swatch-ready])").forEach(init);
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);

    initIn(document);
})();
