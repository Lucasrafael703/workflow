/* Quadros dinâmicos: a tela do quadro (tabela editável), o modo Kanban e o modo Calendário.

   O servidor desenha tudo (cabeçalho, linha, célula) e este arquivo só liga o comportamento: abrir o
   seletor de tipo, criar coluna e item sem recarregar, renomear no lugar, redimensionar, arrastar,
   ordenar, editar célula por tipo e gerir etiquetas. Cada gravação é otimista: a tela muda na hora e volta
   ao valor anterior, com aviso, se o servidor recusar. O servidor é quem valida e quem manda o HTML final
   (`cell_html`, `header_html`, `row_html`), então nenhuma regra de tipo é duplicada aqui além do necessário
   para a pré-visualização.

   Os endereços vêm do `json_script` #board-meta, com um id fictício que `fillUrl` troca pelo real. */
(function () {
    "use strict";

    // ---------------------------------------------------------------------------------------------
    // Funções puras (testadas à parte)
    // ---------------------------------------------------------------------------------------------

    function fillUrl(template, ids, sentinels) {
        var url = String(template);
        if (ids && ids.column != null) url = url.replace(String(sentinels.column), String(ids.column));
        if (ids && ids.id != null) url = url.replace(String(sentinels.id), String(ids.id));
        return url;
    }

    function clamp(value, minimum, maximum) {
        return Math.max(minimum, Math.min(maximum, value));
    }

    /** Vizinhos de `movedId` depois de colocá-lo junto de `targetId` (lado "before" ou "after"). */
    function neighbours(ids, movedId, targetId, side) {
        var rest = ids.filter(function (id) { return id !== movedId; });
        var index = rest.indexOf(targetId);
        if (index < 0) return {before_id: null, after_id: null};
        var insertAt = side === "after" ? index + 1 : index;
        return {
            before_id: insertAt > 0 ? rest[insertAt - 1] : null,
            after_id: insertAt < rest.length ? rest[insertAt] : null
        };
    }

    function contrastColor(hex) {
        var value = String(hex || "").replace("#", "");
        if (value.length !== 6) return "#1F2937";
        var red = parseInt(value.slice(0, 2), 16), green = parseInt(value.slice(2, 4), 16), blue = parseInt(value.slice(4, 6), 16);
        if (isNaN(red) || isNaN(green) || isNaN(blue)) return "#1F2937";
        return (0.299 * red + 0.587 * green + 0.114 * blue) / 255 > 0.62 ? "#1F2937" : "#FFFFFF";
    }

    function initials(name) {
        var parts = String(name || "").trim().split(/\s+/).filter(Boolean);
        if (!parts.length) return "?";
        return (parts[0].charAt(0) + (parts.length > 1 ? parts[parts.length - 1].charAt(0) : "")).toUpperCase();
    }

    function formatIsoDate(iso) {
        var match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
        return match ? match[3] + "/" + match[2] + "/" + match[1] : "";
    }

    /** "2026-10-15T14:00" -> {date: "2026-10-15", time: "14:00"}. Data pura vem com `time` vazio. */
    function splitDateValue(raw) {
        var match = /^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}))?/.exec(String(raw || ""));
        return match ? {date: match[1], time: match[2] || ""} : {date: "", time: ""};
    }

    /** Junta a data e a hora opcional como o servidor entende. Sem hora vai só a data: nunca se inventa 00:00. */
    function composeDateValue(date, time) {
        return date && time ? date + "T" + time : (date || "");
    }

    /** "14:30", "9:05", "1430", "14h", "14h30", "9" -> "HH:MM"; qualquer outra coisa (ou hora impossível) -> null. */
    function parseTimeInput(text) {
        var value = String(text || "").trim().toLowerCase().replace(/\s+/g, "").replace(/h(\d{2})$/, ":$1").replace(/h$/, "");
        var match = /^(\d{1,2}):(\d{2})$/.exec(value) || /^(\d{2})(\d{2})$/.exec(value) || /^(\d{1,2})()$/.exec(value);
        if (!match) return null;
        var hours = parseInt(match[1], 10), minutes = match[2] ? parseInt(match[2], 10) : 0;
        if (hours > 23 || minutes > 59) return null;
        return (hours < 10 ? "0" : "") + hours + ":" + (minutes < 10 ? "0" : "") + minutes;
    }

    var helpers = {
        fillUrl: fillUrl, clamp: clamp, neighbours: neighbours, contrastColor: contrastColor,
        initials: initials, formatIsoDate: formatIsoDate, splitDateValue: splitDateValue,
        composeDateValue: composeDateValue, parseTimeInput: parseTimeInput
    };

    // ---------------------------------------------------------------------------------------------
    // Tela
    // ---------------------------------------------------------------------------------------------

    function init(page, meta) {
        var doc = page.ownerDocument;
        var win = doc.defaultView;
        var table = page.querySelector("[data-board-table]");
        var scroller = page.querySelector("[data-board-scroll]");
        var toastArea = doc.querySelector("[data-board-toasts]");
        var statusEl = page.querySelector("[data-board-status]");
        var perms = meta.permissions || {};
        var NAME_WIDTH = 280, ADD_WIDTH = 64;
        var pending = 0, statusTimer = null;
        var drag = null, popover = null, lastTrigger = null;

        // -- utilidades de DOM ------------------------------------------------------------------

        function el(tag, attrs, children) {
            var node = doc.createElement(tag);
            Object.keys(attrs || {}).forEach(function (key) {
                var value = attrs[key];
                if (value === null || value === undefined || value === false) return;
                if (key === "class") node.className = value;
                else if (key === "text") node.textContent = value;
                else if (key === "html") node.innerHTML = value;
                else node.setAttribute(key, value === true ? "" : value);
            });
            (children || []).forEach(function (child) { if (child) node.appendChild(child); });
            return node;
        }

        function icon(name) {
            var holder = doc.createElement("span");
            holder.innerHTML = '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><use href="#i-' + name + '"></use></svg>';
            return holder.firstChild;
        }

        function parse(html, tag) {
            var template = doc.createElement("template");
            template.innerHTML = String(html || "").trim();
            return template.content.querySelector(tag) || template.content.firstElementChild;
        }

        function q(selector, root) { return (root || table || page).querySelector(selector); }
        function qa(selector, root) { return Array.prototype.slice.call((root || table || page).querySelectorAll(selector)); }

        function url(key, ids) {
            return fillUrl(meta.urls[key], ids, meta.sentinels);
        }

        function columnMeta(id) {
            for (var i = 0; i < meta.columns.length; i += 1) if (meta.columns[i].id === Number(id)) return meta.columns[i];
            return null;
        }

        // cada grupo tem a sua linha de títulos: `th` é o primeiro (ou o do grupo `scope`), `thAll` são todos
        function th(columnId, scope) { return q('th[data-column-th][data-column-id="' + columnId + '"]', scope); }
        function thAll(columnId) { return qa('th[data-column-th][data-column-id="' + columnId + '"]'); }
        function colEl(columnId) { return q('col[data-col-id="' + columnId + '"]'); }
        function rowEl(itemId) { return q('tr[data-item-row][data-item-id="' + itemId + '"]'); }
        function groupEl(groupId) { return q('tbody[data-group][data-group-id="' + groupId + '"]'); }
        function cellEl(itemId, columnId) {
            return q('td[data-cell][data-item-id="' + itemId + '"][data-column-id="' + columnId + '"]');
        }
        function orderedColumnIds() {
            return qa("colgroup col[data-col-id]").map(function (col) { return Number(col.dataset.colId); });
        }
        function groupRows(group) { return qa("tr[data-item-row]", group); }

        function syncTableWidth() {
            if (!table) return;
            var total = NAME_WIDTH + ADD_WIDTH;
            qa("colgroup col[data-col-id]").forEach(function (col) { total += parseInt(col.style.width, 10) || 160; });
            table.style.width = total + "px";
        }

        function updateGroupCount(group) {
            var count = groupRows(group).length;
            var label = group.querySelector("[data-group-count]");
            if (label) label.textContent = count + " ite" + (count === 1 ? "m" : "ns");
        }

        // -- avisos e estado de gravação --------------------------------------------------------

        function setStatus(text, kind) {
            if (!statusEl) return;
            statusEl.textContent = text || "";
            statusEl.classList.toggle("is-error", kind === "error");
        }

        function toast(message, kind) {
            if (!toastArea) return;
            var node = el("div", {class: "board-toast" + (kind === "error" ? " is-error" : ""), text: message});
            toastArea.appendChild(node);
            win.setTimeout(function () { if (node.parentNode) node.parentNode.removeChild(node); }, kind === "error" ? 6000 : 3000);
        }

        function csrfToken() {
            var match = /(?:^|;\s*)csrftoken=([^;]+)/.exec(doc.cookie || "");
            if (match) return decodeURIComponent(match[1]);
            var field = doc.querySelector("input[name=csrfmiddlewaretoken]");
            return field ? field.value : "";
        }

        function request(endpoint, body, options) {
            var quiet = !!(options && options.quiet); // navegar e abrir a gaveta não são "salvar": o indicador não muda
            if (!quiet) {
                pending += 1;
                win.clearTimeout(statusTimer);
                setStatus("Salvando…");
            }
            return win.fetch(endpoint, {
                method: "POST",
                credentials: "same-origin",
                headers: {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrfToken()},
                body: JSON.stringify(body || {})
            }).then(function (response) {
                return response.json().catch(function () { return {}; }).then(function (data) {
                    if (!response.ok || data.ok === false) {
                        var error = new Error(data.error || "Não foi possível salvar. Tente de novo.");
                        error.status = response.status;
                        error.data = data;
                        throw error;
                    }
                    return data;
                });
            }, function () {
                throw new Error("Sem conexão com o servidor. Tente de novo.");
            }).then(function (data) {
                if (!quiet) finishRequest(true);
                return data;
            }, function (error) {
                if (!quiet) finishRequest(false);
                throw error;
            });
        }

        function finishRequest(ok) {
            pending = Math.max(0, pending - 1);
            if (!ok) { setStatus("Erro ao salvar", "error"); return; }
            if (pending === 0) {
                setStatus("Salvo");
                statusTimer = win.setTimeout(function () { setStatus(""); }, 2500);
            }
        }

        function fail(error) {
            toast(error && error.message ? error.message : "Não foi possível salvar.", "error");
        }

        function cancellationPayload() {
            if (!meta.board || meta.board.kind !== "DEMAND") return {};
            var reason = win.prompt("Informe o motivo do cancelamento da tarefa:", "");
            reason = String(reason || "").trim();
            return reason ? {reason: reason} : null;
        }

        // -- pop-overs, menus e janelas ---------------------------------------------------------

        function closePopover(restoreFocus) {
            if (!popover) return;
            var current = popover;
            popover = null;
            if (current.el.parentNode) current.el.parentNode.removeChild(current.el);
            if (current.anchor) current.anchor.removeAttribute("aria-expanded");
            if (current.onClose) current.onClose();
            if (restoreFocus && current.anchor && current.anchor.focus && doc.contains(current.anchor)) current.anchor.focus();
        }

        function placePopover(pop, anchor) {
            var rect = anchor.getBoundingClientRect();
            var width = pop.offsetWidth, height = pop.offsetHeight;
            var left = rect.left, top = rect.bottom + 4;
            if (left + width > win.innerWidth - 8) left = Math.max(8, win.innerWidth - width - 8);
            if (top + height > win.innerHeight - 8) {
                var above = rect.top - height - 4;
                top = above >= 8 ? above : Math.max(8, win.innerHeight - height - 8);
            }
            pop.style.left = left + "px";
            pop.style.top = top + "px";
        }

        function focusFirst(root) {
            var target = root.querySelector("input:not([type=hidden]), select, textarea, button:not([disabled]), [tabindex='0']");
            if (target) target.focus();
        }

        function openPopover(anchor, content, options) {
            options = options || {};
            closePopover(false);
            var pop = el("div", {class: "board-pop" + (options.wide ? " board-pop--wide" : ""), role: options.role || "dialog"}, [content]);
            if (options.label) pop.setAttribute("aria-label", options.label);
            // medir de um canto conhecido: sem isso a largura fica espremida pelo espaço à direita do botão
            pop.style.left = "0px";
            pop.style.top = "0px";
            doc.body.appendChild(pop);
            placePopover(pop, anchor);
            if (anchor) anchor.setAttribute("aria-expanded", "true");
            popover = {el: pop, anchor: anchor, onClose: options.onClose};
            focusFirst(pop);
            return pop;
        }

        function buildMenu(items) {
            var menu = el("div", {class: "board-menu", role: "menu"});
            items.forEach(function (item) {
                if (item.separator) { menu.appendChild(el("div", {class: "board-menu__sep", role: "separator"})); return; }
                if (item.heading) { menu.appendChild(el("div", {class: "board-menu__label", text: item.heading})); return; }
                var button = el("button", {
                    type: "button", role: "menuitem", class: "board-menu__item" + (item.danger ? " is-danger" : ""),
                    disabled: item.disabled ? true : null
                }, [item.icon ? icon(item.icon) : null, el("span", {text: item.label})]);
                button.addEventListener("click", function () {
                    closePopover(false);
                    if (item.onClick) item.onClick();
                });
                menu.appendChild(button);
            });
            menu.addEventListener("keydown", function (event) {
                if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
                var buttons = qa("button:not([disabled])", menu);
                var index = buttons.indexOf(doc.activeElement);
                var next = event.key === "ArrowDown" ? index + 1 : index - 1;
                if (buttons.length) buttons[(next + buttons.length) % buttons.length].focus();
                event.preventDefault();
            });
            return menu;
        }

        function openMenu(anchor, items, label) {
            openPopover(anchor, buildMenu(items), {role: "menu", label: label});
        }

        function openDialog(title, body, buttons) {
            var opener = doc.activeElement;
            var errorBox = el("p", {class: "board-dialog__error", role: "alert", hidden: true});
            var backdrop = el("div", {class: "board-dialog-backdrop"});
            var closeButton = el("button", {type: "button", class: "board-dialog__close", "aria-label": "Fechar", text: "×"});
            var head = el("div", {class: "board-dialog__head"}, [el("h2", {text: title}), closeButton]);
            var foot = el("div", {class: "board-dialog__foot"});
            var dialog = el("div", {class: "board-dialog", role: "dialog", "aria-modal": "true", "aria-label": title},
                [head, el("div", {class: "board-dialog__body"}, [body, errorBox]), foot]);
            backdrop.appendChild(dialog);
            var api = {
                root: dialog,
                error: function (message) { errorBox.textContent = message || ""; errorBox.hidden = !message; },
                close: function () {
                    if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
                    doc.removeEventListener("keydown", onKey, true);
                    if (api.onClose) api.onClose();
                    if (opener && opener.focus && doc.contains(opener)) opener.focus();
                }
            };
            function onKey(event) {
                // com um pop-over aberto (ex.: a paleta de cores) o primeiro Escape fecha só ele; o listener do documento cuida disso
                if (event.key === "Escape") { if (popover) return; event.stopPropagation(); api.close(); return; }
                if (event.key !== "Tab") return;
                var focusable = qa("button:not([disabled]), input:not([type=hidden]), select, textarea, [tabindex='0']", dialog);
                if (!focusable.length) return;
                var first = focusable[0], last = focusable[focusable.length - 1];
                if (event.shiftKey && doc.activeElement === first) { event.preventDefault(); last.focus(); }
                else if (!event.shiftKey && doc.activeElement === last) { event.preventDefault(); first.focus(); }
            }
            (buttons || []).forEach(function (spec) {
                var button = el("button", {
                    type: "button", class: "btn" + (spec.kind === "primary" ? " btn--primary" : spec.kind === "danger" ? " btn--danger" : ""),
                    text: spec.label
                });
                button.addEventListener("click", function () { if (spec.onClick) spec.onClick(api, button); else api.close(); });
                foot.appendChild(button);
            });
            closeButton.addEventListener("click", function () { api.close(); });
            backdrop.addEventListener("mousedown", function (event) { if (event.target === backdrop) api.close(); });
            doc.addEventListener("keydown", onKey, true);
            doc.body.appendChild(backdrop);
            closePopover(false);
            win.setTimeout(function () { focusFirst(dialog.querySelector(".board-dialog__body")); }, 0);
            return api;
        }

        function confirmDialog(options) {
            return new Promise(function (resolve) {
                var settled = false;
                function settle(value, dialog) { if (settled) return; settled = true; if (dialog) dialog.close(); resolve(value); }
                var dialog = openDialog(options.title, el("p", {text: options.message}), [
                    {label: "Cancelar", onClick: function (d) { settle(false, d); }},
                    {label: options.confirmLabel || "Confirmar", kind: options.danger ? "danger" : "primary", onClick: function (d) { settle(true, d); }}
                ]);
                dialog.onClose = function () { settle(false); };
            });
        }

        function paletteNode(current, onPick) {
            var palette = el("div", {class: "board-palette", role: "listbox", "aria-label": "Cores"});
            (meta.palette || []).forEach(function (color) {
                var swatch = el("button", {
                    type: "button", class: "board-swatch" + (String(current).toUpperCase() === color ? " is-current" : ""),
                    style: "background:" + color, "aria-label": "Cor " + color, role: "option"
                });
                swatch.addEventListener("click", function () { onPick(color); });
                palette.appendChild(swatch);
            });
            return palette;
        }

        // -- edição de texto no lugar -----------------------------------------------------------

        function inlineEdit(target, options) {
            var input = el("input", {type: "text", class: "board-inline-input", maxlength: options.maxlength || 255});
            var finished = false;
            input.value = options.value || "";
            target.style.display = "none";
            target.parentNode.insertBefore(input, target.nextSibling);
            input.focus();
            input.select();
            function cleanup() {
                finished = true;
                if (input.parentNode) input.parentNode.removeChild(input);
                target.style.display = "";
            }
            function commit() {
                if (finished) return;
                var value = input.value.trim();
                cleanup();
                if (value === (options.value || "").trim()) { if (options.onCancel) options.onCancel(); return; }
                options.onCommit(value);
            }
            input.addEventListener("keydown", function (event) {
                if (event.key === "Enter") { event.preventDefault(); commit(); }
                else if (event.key === "Escape") {
                    event.preventDefault(); event.stopPropagation(); cleanup();
                    if (options.onCancel) options.onCancel();
                }
            });
            input.addEventListener("blur", commit);
            return input;
        }

        // -- colunas ----------------------------------------------------------------------------

        function applyColumnFragment(payload) {
            var column = payload.column;
            if (payload.header_html) {
                var fresh = parse(payload.header_html, "th");
                thAll(column.id).forEach(function (current, index) {
                    current.parentNode.replaceChild(index === 0 ? fresh : fresh.cloneNode(true), current);
                });
            }
            for (var i = 0; i < meta.columns.length; i += 1) if (meta.columns[i].id === column.id) meta.columns[i] = column;
            var col = colEl(column.id);
            if (col) col.style.width = column.width + "px";
            if (payload.cells) {
                Object.keys(payload.cells).forEach(function (itemId) {
                    var old = cellEl(itemId, column.id);
                    var td = parse(payload.cells[itemId], "td");
                    if (old && td) old.parentNode.replaceChild(td, old);
                });
            }
            syncTableWidth();
            markDraggable();
        }

        function insertColumn(payload) {
            var column = payload.column;
            var refId = payload.after_column_id;
            var refCol = refId ? colEl(refId) : null;
            var col = el("col", {"data-col-id": column.id, style: "width:" + column.width + "px"});
            var addCol = q("col[data-col-add]");
            if (refCol) refCol.parentNode.insertBefore(col, refCol.nextSibling); else addCol.parentNode.insertBefore(col, addCol);
            var header = parse(payload.header_html, "th");
            qa("tr[data-cols-row]").forEach(function (colsRow, index) {
                var copy = index === 0 ? header : header.cloneNode(true);
                var refTh = refId ? th(refId, colsRow) : null;
                if (refTh) refTh.parentNode.insertBefore(copy, refTh.nextSibling);
                else colsRow.insertBefore(copy, colsRow.querySelector("th[data-add-column-th]"));
            });
            qa("tr[data-item-row]").forEach(function (row) {
                var td = parse((payload.cells || {})[row.dataset.itemId], "td");
                if (!td) return;
                var refTd = refId ? row.querySelector('td[data-cell][data-column-id="' + refId + '"]') : null;
                if (refTd) refTd.parentNode.insertBefore(td, refTd.nextSibling);
                else row.insertBefore(td, row.querySelector(".board-td--filler"));
            });
            var index = refId ? meta.columns.findIndex(function (c) { return c.id === refId; }) + 1 : meta.columns.length;
            meta.columns.splice(index, 0, column);
            qa("td[colspan]").forEach(function (cell) { cell.setAttribute("colspan", String(meta.columns.length + 2)); });
            syncTableWidth();
            markDraggable();
        }

        function removeColumnDom(columnId) {
            [colEl(columnId)].concat(thAll(columnId)).forEach(function (node) { if (node && node.parentNode) node.parentNode.removeChild(node); });
            qa('td[data-cell][data-column-id="' + columnId + '"]').forEach(function (td) { td.parentNode.removeChild(td); });
            meta.columns = meta.columns.filter(function (c) { return c.id !== Number(columnId); });
            qa("td[colspan]").forEach(function (cell) { cell.setAttribute("colspan", String(meta.columns.length + 2)); });
            syncTableWidth();
        }

        // `scope`: o grupo de onde se clicou, para o campo de renomear abrir na linha de títulos que a pessoa está vendo
        function addColumn(type, afterColumnId, scope) {
            return request(url("column_create"), {type: type, after_column_id: afterColumnId || null})
                .then(function (payload) {
                    insertColumn(payload);
                    startColumnRename(payload.column.id, scope);
                }, fail);
        }

        function openTypePicker(anchor, afterColumnId) {
            var grid = el("div", {class: "board-types"});
            var scope = anchor && anchor.closest ? anchor.closest("[data-group]") : null;
            (meta.types || []).forEach(function (type) {
                var button = el("button", {type: "button", class: "board-type"}, [
                    icon(type.icon), el("div", {}, [el("strong", {text: type.label}), el("span", {text: type.description})])
                ]);
                button.addEventListener("click", function () { closePopover(false); addColumn(type.value, afterColumnId, scope); });
                grid.appendChild(button);
            });
            var wrapper = el("div", {}, [el("p", {class: "board-pop__title", text: "Escolha o tipo da coluna"}), grid]);
            openPopover(anchor, wrapper, {label: "Tipos de coluna", wide: true});
        }

        function startColumnRename(columnId, scope) {
            var header = th(columnId, scope) || th(columnId);
            if (!header || !perms.manage_columns) return;
            var nameEl = header.querySelector("[data-column-name]");
            var previous = nameEl.textContent;
            inlineEdit(nameEl, {
                value: previous, maxlength: 120,
                onCommit: function (value) {
                    nameEl.textContent = value || previous;
                    request(url("column_rename", {id: columnId}), {name: value}).then(applyColumnFragment, function (error) {
                        nameEl.textContent = previous;
                        fail(error);
                    });
                }
            });
        }

        function sortUrl(columnId, direction) {
            var params = new win.URLSearchParams(win.location.search);
            params.delete("page");
            if (columnId) { params.set("sort", columnId); params.set("dir", direction); }
            else { params.delete("sort"); params.delete("dir"); }
            var query = params.toString();
            return win.location.pathname + (query ? "?" + query : "");
        }

        function navigate(target) { win.location.assign(target); }

        function openColumnMenu(anchor, columnId) {
            var column = columnMeta(columnId);
            if (!column) return;
            var manage = !!perms.manage_columns;
            var sorted = meta.sort && meta.sort.column === column.id;
            var items = [];
            if (manage) items.push({label: "Configurações da coluna", icon: "settings", onClick: function () { openSettings(column.id); }});
            if (manage && (column.type === "STATUS" || column.type === "DROPDOWN")) {
                items.push({label: "Editar etiquetas", icon: "list-ul", onClick: function () { openLabels(column.id); }});
            }
            if (items.length) items.push({separator: true});
            items.push({label: "Ordenar ascendente", icon: "arrow-right", onClick: function () { navigate(sortUrl(column.id, "asc")); }});
            items.push({label: "Ordenar descendente", icon: "arrow-right", onClick: function () { navigate(sortUrl(column.id, "desc")); }});
            if (sorted) items.push({label: "Remover ordenação", icon: "back", onClick: function () { navigate(sortUrl(null)); }});
            if (manage) {
                items.push({separator: true});
                items.push({label: "Duplicar coluna", icon: "archive", onClick: function () { duplicateColumn(column.id); }});
                items.push({label: "Adicionar coluna à direita", icon: "plus", onClick: function () { openTypePicker(anchor.closest("th") || th(column.id), column.id); }});
                items.push({label: "Alterar tipo", icon: "swap", onClick: function () { openTypeChange(column.id); }});
                items.push({label: "Renomear", icon: "file-text", onClick: function () { startColumnRename(column.id, anchor.closest("[data-group]")); }});
                items.push({label: "Ocultar coluna", icon: "eye-off", onClick: function () { hideColumn(column.id); }});
                items.push({separator: true});
                items.push({label: "Excluir coluna", icon: "trash", danger: true, onClick: function () { deleteColumn(column.id); }});
            }
            openMenu(anchor, items, "Opções da coluna " + column.name);
        }

        function duplicateColumn(columnId) {
            request(url("column_duplicate", {id: columnId}), {}).then(insertColumn, fail);
        }

        function hideColumn(columnId) {
            request(url("column_hide", {id: columnId}), {visible: false}).then(function () { win.location.reload(); }, fail);
        }

        function deleteColumn(columnId) {
            var column = columnMeta(columnId);
            confirmDialog({
                title: "Excluir coluna", danger: true, confirmLabel: "Excluir coluna",
                message: "Excluir a coluna “" + column.name + "”? Os valores dela deixam de aparecer no quadro."
            }).then(function (yes) {
                if (!yes) return;
                request(url("column_delete", {id: columnId}), {}).then(function () { removeColumnDom(columnId); }, fail);
            });
        }

        function openTypeChange(columnId) {
            var column = columnMeta(columnId);
            var holder = el("div", {class: "board-field"});
            var select = el("select", {"aria-label": "Novo tipo"});
            (meta.types || []).forEach(function (type) {
                if (type.value !== column.type) select.appendChild(el("option", {value: type.value, text: type.label}));
            });
            holder.appendChild(el("span", {text: "Tipo atual: " + column.type_label + ". Escolha o novo tipo:"}));
            holder.appendChild(select);
            holder.appendChild(el("span", {class: "board-field__hint", text: "Se algum valor não puder ser convertido, a LPS avisa quantos serão apagados antes de mudar."}));
            openDialog("Alterar tipo da coluna", holder, [
                {label: "Cancelar"},
                {label: "Continuar", kind: "primary", onClick: function (dialog) {
                    var newType = select.value;
                    request(url("column_type", {id: columnId}), {type: newType, preview: true}).then(function (preview) {
                        var plan = preview.plan;
                        if (plan.mode === "safe") return applyTypeChange(dialog, columnId, newType, false);
                        dialog.close();
                        return confirmDialog({
                            title: "Converter e apagar valores", danger: true, confirmLabel: "Converter",
                            message: plan.lost + " de " + plan.filled + " valor(es) desta coluna não pode(m) ser convertido(s) e será(ão) apagado(s). Deseja continuar?"
                        }).then(function (yes) { if (yes) applyTypeChange(null, columnId, newType, true); });
                    }, function (error) { dialog.error(error.message); });
                }}
            ]);
        }

        function applyTypeChange(dialog, columnId, newType, confirm) {
            return request(url("column_type", {id: columnId}), {type: newType, confirm: confirm}).then(function (payload) {
                if (dialog) dialog.close();
                applyColumnFragment(payload);
                toast("Tipo da coluna alterado.");
            }, function (error) { if (dialog) dialog.error(error.message); else fail(error); });
        }

        function openSettings(columnId) {
            var column = columnMeta(columnId);
            var s = column.settings || {};
            var form = el("div", {});
            var fields = {};
            function field(label, control, hint) {
                var wrapper = el("label", {class: "board-field"}, [el("span", {text: label}), control]);
                if (hint) wrapper.appendChild(el("span", {class: "board-field__hint", text: hint}));
                form.appendChild(wrapper);
                return control;
            }
            function check(key, label, value) {
                var input = el("input", {type: "checkbox"});
                input.checked = !!value;
                var wrapper = el("label", {class: "board-field board-field--check"}, [input, el("span", {text: label})]);
                form.appendChild(wrapper);
                fields[key] = input;
            }
            var description = el("textarea", {rows: "2", maxlength: "500"});
            description.value = column.description || "";
            field("Descrição da coluna (aparece ao passar o mouse)", description);
            check("is_required", "Valor obrigatório", column.is_required);

            if (column.type === "DATE") {
                check("show_time", "Mostrar horário", s.show_time);
                check("allow_weekends", "Permitir sábado e domingo", s.allow_weekends !== false);
                check("is_deadline", "Tratar como prazo (destaca quando vencido)", s.is_deadline);
            }
            if (column.type === "NUMBER" || column.type === "CURRENCY") {
                if (column.type === "CURRENCY") {
                    var currency = el("select", {}, [
                        el("option", {value: "BRL", text: "Real (R$)"}), el("option", {value: "USD", text: "Dólar (US$)"}), el("option", {value: "EUR", text: "Euro (€)"})
                    ]);
                    currency.value = s.currency || "BRL";
                    fields.currency = field("Moeda", currency);
                }
                var places = el("input", {type: "number", min: "0", max: "6", step: "1"});
                places.value = s.decimal_places == null ? 2 : s.decimal_places;
                fields.decimal_places = field("Casas decimais", places);
                if (column.type === "NUMBER") {
                    var unit = el("input", {type: "text", maxlength: "12", placeholder: "Ex.: %, m², kg"});
                    unit.value = s.unit || "";
                    fields.unit = field("Unidade", unit);
                }
                var range = el("div", {class: "board-field-row"});
                var minimum = el("input", {type: "text", inputmode: "decimal", placeholder: "Sem mínimo"});
                var maximum = el("input", {type: "text", inputmode: "decimal", placeholder: "Sem máximo"});
                minimum.value = s.minimum == null ? "" : String(s.minimum).replace(".", ",");
                maximum.value = s.maximum == null ? "" : String(s.maximum).replace(".", ",");
                range.appendChild(el("label", {class: "board-field"}, [el("span", {text: "Valor mínimo"}), minimum]));
                range.appendChild(el("label", {class: "board-field"}, [el("span", {text: "Valor máximo"}), maximum]));
                form.appendChild(range);
                fields.minimum = minimum; fields.maximum = maximum;
            }
            if (column.type === "STATUS" || column.type === "DROPDOWN") {
                var labelsButton = el("button", {type: "button", class: "btn", text: "Editar etiquetas"});
                labelsButton.addEventListener("click", function () { dialog.close(); openLabels(columnId); });
                form.appendChild(labelsButton);
            }
            var dialog = openDialog("Configurações · " + column.name, form, [
                {label: "Cancelar"},
                {label: "Salvar", kind: "primary", onClick: function (d) {
                    var settings = {};
                    ["show_time", "allow_weekends", "is_deadline"].forEach(function (key) { if (fields[key]) settings[key] = fields[key].checked; });
                    ["currency", "unit", "decimal_places", "minimum", "maximum"].forEach(function (key) { if (fields[key]) settings[key] = fields[key].value; });
                    request(url("column_settings", {id: columnId}), {
                        description: description.value, is_required: fields.is_required.checked, settings: settings
                    }).then(function (payload) { d.close(); applyColumnFragment(payload); }, function (error) { d.error(error.message); });
                }}
            ]);
        }

        // -- etiquetas --------------------------------------------------------------------------

        function openLabels(columnId) {
            var column = columnMeta(columnId);
            var changed = false;
            var list = el("div", {class: "board-labels"});
            var addInput = el("input", {type: "text", maxlength: "120", placeholder: "Nova etiqueta", "aria-label": "Nome da nova etiqueta"});
            var addButton = el("button", {type: "button", class: "btn", text: "Adicionar"});
            var dialog;

            function swap(option, direction) {
                var options = column.options;
                var ids = options.map(function (o) { return o.id; });
                var index = ids.indexOf(option.id);
                var target = ids[index + direction];
                if (target == null) return;
                var pos = neighbours(ids, option.id, target, direction > 0 ? "after" : "before");
                request(url("option_reorder", {id: option.id}), pos).then(function () {
                    options.splice(index, 1);
                    options.splice(index + direction, 0, option);
                    changed = true;
                    render();
                }, function (error) { dialog.error(error.message); });
            }

            function row(option) {
                var swatch = el("button", {type: "button", class: "board-swatch", style: "background:" + option.color,
                    "aria-label": "Mudar a cor de " + option.label, "data-option-id": option.id});
                swatch.addEventListener("click", function () {
                    openPopover(swatch, paletteNode(option.color, function (color) {
                        closePopover(false);
                        request(url("option_update", {id: option.id}), {color: color}).then(function () {
                            option.color = color; changed = true; render();
                            // a lista foi redesenhada: o foco volta ao botão da cor da mesma etiqueta (teclado não se perde)
                            var again = list.querySelector('.board-swatch[data-option-id="' + option.id + '"]');
                            if (again) again.focus();
                        }, function (error) { dialog.error(error.message); });
                    }), {label: "Cores"});
                });
                var input = el("input", {type: "text", maxlength: "120", "aria-label": "Nome da etiqueta"});
                input.value = option.label;
                input.addEventListener("change", function () {
                    request(url("option_update", {id: option.id}), {label: input.value}).then(function () {
                        option.label = input.value.trim(); changed = true; dialog.error("");
                    }, function (error) { input.value = option.label; dialog.error(error.message); });
                });
                var up = el("button", {type: "button", class: "btn btn--ghost btn--sm", "aria-label": "Subir etiqueta", text: "↑"});
                var down = el("button", {type: "button", class: "btn btn--ghost btn--sm", "aria-label": "Descer etiqueta", text: "↓"});
                up.addEventListener("click", function () { swap(option, -1); });
                down.addEventListener("click", function () { swap(option, 1); });
                var remove = el("button", {type: "button", class: "board-label-remove", "aria-label": "Excluir a etiqueta " + option.label}, [icon("trash")]);
                remove.addEventListener("click", function () {
                    confirmDialog({
                        title: "Excluir etiqueta", danger: true, confirmLabel: "Excluir",
                        message: "Excluir a etiqueta “" + option.label + "”? As células que a usam ficarão vazias."
                    }).then(function (yes) {
                        if (!yes) return;
                        request(url("option_delete", {id: option.id}), {}).then(function () {
                            column.options = column.options.filter(function (o) { return o.id !== option.id; });
                            changed = true; render();
                        }, function (error) { dialog.error(error.message); });
                    });
                });
                var isDefault = el("input", {type: "radio", name: "label-default", "aria-label": "Etiqueta padrão"});
                isDefault.checked = !!option.is_default;
                isDefault.addEventListener("change", function () {
                    request(url("option_update", {id: option.id}), {is_default: true}).then(function () {
                        column.options.forEach(function (o) { o.is_default = o.id === option.id; }); changed = true;
                    }, function (error) { dialog.error(error.message); });
                });
                var isDone = el("input", {type: "checkbox", "aria-label": "Representa conclusão"});
                isDone.checked = !!option.is_done;
                isDone.addEventListener("change", function () {
                    request(url("option_update", {id: option.id}), {is_done: isDone.checked}).then(function () {
                        option.is_done = isDone.checked; changed = true;
                    }, function (error) { isDone.checked = !isDone.checked; dialog.error(error.message); });
                });
                return el("div", {class: "board-label-row"}, [
                    swatch, input, el("span", {}, [up, down]), remove,
                    el("div", {class: "board-label-flags"}, [
                        el("label", {}, [isDefault, el("span", {text: "Padrão para novos itens"})]),
                        el("label", {}, [isDone, el("span", {text: "Conta como concluído"})])
                    ])
                ]);
            }

            function render() {
                list.textContent = "";
                column.options.forEach(function (option) { list.appendChild(row(option)); });
                if (!column.options.length) list.appendChild(el("p", {class: "board-field__hint", text: "Nenhuma etiqueta ainda. Adicione a primeira abaixo."}));
            }

            function addLabel() {
                var label = addInput.value.trim();
                if (!label) return;
                request(url("option_create", {id: columnId}), {label: label}).then(function (payload) {
                    column.options.push(payload.option);
                    addInput.value = "";
                    changed = true; dialog.error(""); render(); addInput.focus();
                }, function (error) { dialog.error(error.message); });
            }
            addButton.addEventListener("click", addLabel);
            addInput.addEventListener("keydown", function (event) { if (event.key === "Enter") { event.preventDefault(); addLabel(); } });

            var body = el("div", {}, [list, el("div", {class: "board-label-add"}, [addInput, addButton])]);
            dialog = openDialog("Etiquetas · " + column.name, body, [{label: "Concluir", kind: "primary"}]);
            dialog.onClose = function () {
                if (!changed) return;
                if (kanban) { refreshKanban(); return; }
                request(url("column_fragment", {id: columnId}), {sort: meta.sort.column, dir: meta.sort.dir}).then(applyColumnFragment, fail);
            };
            render();
        }

        // -- redimensionar e reordenar colunas --------------------------------------------------

        function setColumnWidth(columnId, width) {
            var col = colEl(columnId);
            if (col) col.style.width = width + "px";
            syncTableWidth();
        }

        function saveWidth(columnId, width, previous) {
            request(url("column_resize", {id: columnId}), {width: width}).then(function (payload) {
                var column = columnMeta(columnId);
                if (column) column.width = payload.width;
                setColumnWidth(columnId, payload.width);
            }, function (error) { setColumnWidth(columnId, previous); fail(error); });
        }

        var keyboardResize = {timer: null, base: null};

        function startResize(event, handle) {
            if (event.button !== undefined && event.button !== 0) return;
            event.preventDefault();
            var header = handle.closest("th");
            var columnId = Number(header.dataset.columnId);
            var startX = event.clientX, startWidth = header.getBoundingClientRect().width || parseInt(colEl(columnId).style.width, 10);
            var limits = meta.limits;
            var width = startWidth;
            doc.body.classList.add("board-resizing");
            header.classList.add("is-resizing");
            function move(e) {
                width = Math.round(clamp(startWidth + (e.clientX - startX), limits.min_width, limits.max_width));
                setColumnWidth(columnId, width);
            }
            function stop() {
                doc.removeEventListener("pointermove", move);
                doc.removeEventListener("pointerup", stop);
                doc.removeEventListener("pointercancel", stop);
                doc.body.classList.remove("board-resizing");
                header.classList.remove("is-resizing");
                if (width !== Math.round(startWidth)) saveWidth(columnId, width, Math.round(startWidth));
            }
            doc.addEventListener("pointermove", move);
            doc.addEventListener("pointerup", stop);
            doc.addEventListener("pointercancel", stop);
        }

        function resizeByKey(event, handle) {
            var step = event.shiftKey ? 48 : 16;
            var delta = event.key === "ArrowRight" ? step : event.key === "ArrowLeft" ? -step : 0;
            if (!delta) return;
            event.preventDefault();
            var columnId = Number(handle.closest("th").dataset.columnId);
            var current = parseInt(colEl(columnId).style.width, 10) || 160;
            if (keyboardResize.base === null) keyboardResize.base = current;
            var width = Math.round(clamp(current + delta, meta.limits.min_width, meta.limits.max_width));
            setColumnWidth(columnId, width);
            win.clearTimeout(keyboardResize.timer);
            keyboardResize.timer = win.setTimeout(function () {
                var base = keyboardResize.base;
                keyboardResize.base = null;
                saveWidth(columnId, width, base);
            }, 450);
        }

        function markDraggable() {
            if (!perms.manage_columns) return;
            qa("th[data-column-th]").forEach(function (header) { header.setAttribute("draggable", "true"); });
        }

        function moveColumnDom(columnId, beforeId, afterId) {
            // insere à direita do vizinho da esquerda; sem ele, antes do vizinho da direita
            var anchorId = beforeId || afterId;
            var toRight = !!beforeId;
            var colNode = colEl(columnId), colRef = colEl(anchorId);
            if (colNode && colRef) colRef.parentNode.insertBefore(colNode, toRight ? colRef.nextSibling : colRef);
            qa("tr[data-cols-row]").forEach(function (colsRow) {
                var node = th(columnId, colsRow), ref = th(anchorId, colsRow);
                if (node && ref) ref.parentNode.insertBefore(node, toRight ? ref.nextSibling : ref);
            });
            qa("tr[data-item-row]").forEach(function (row) {
                var td = row.querySelector('td[data-cell][data-column-id="' + columnId + '"]');
                var ref = row.querySelector('td[data-cell][data-column-id="' + anchorId + '"]');
                if (td && ref) ref.parentNode.insertBefore(td, toRight ? ref.nextSibling : ref);
            });
            var order = orderedColumnIds();
            meta.columns.sort(function (a, b) { return order.indexOf(a.id) - order.indexOf(b.id); });
        }

        function clearDropMarks() {
            qa(".is-drop-before, .is-drop-after, .is-drop-target").forEach(function (node) {
                node.classList.remove("is-drop-before", "is-drop-after", "is-drop-target");
            });
        }

        // -- itens e grupos ---------------------------------------------------------------------

        function addItem(group) {
            return request(url("item_create", {id: meta.board.id}), {group_id: Number(group.dataset.groupId)}).then(function (payload) {
                var row = parse(payload.row_html, "tr");
                var addRow = group.querySelector("[data-add-row]");
                group.insertBefore(row, addRow);
                updateGroupCount(group);
                startItemRename(row);
            }, fail);
        }

        function startItemRename(row) {
            if (!perms.edit_item) return;
            if (row.matches("[data-card]")) { if (kanbanCore) kanbanCore.startRename(row); return; }  // o título do cartão é do núcleo
            var nameEl = row.querySelector("[data-item-name]");
            if (!nameEl) return;
            var wasEmpty = nameEl.classList.contains("is-empty");
            var previous = wasEmpty ? "" : nameEl.textContent;
            inlineEdit(nameEl, {
                value: previous, maxlength: 255,
                onCommit: function (value) {
                    nameEl.textContent = value || "Sem título";
                    nameEl.classList.toggle("is-empty", !value);
                    request(url("item_rename", {id: row.dataset.itemId}), {name: value}).then(null, function (error) {
                        nameEl.textContent = previous || "Sem título";
                        nameEl.classList.toggle("is-empty", !previous);
                        fail(error);
                    });
                }
            });
        }

        function deleteItem(row) {
            var group = row.closest("[data-group]");
            confirmDialog({
                title: "Excluir item", danger: true, confirmLabel: "Excluir",
                message: "Excluir “" + (row.querySelector("[data-item-name]").textContent.trim()) + "”? Ele deixa de aparecer no quadro."
            }).then(function (yes) {
                if (!yes) return;
                var payload = cancellationPayload();
                if (payload === null) return;
                request(url("item_delete", {id: row.dataset.itemId}), payload).then(function () {
                    row.parentNode.removeChild(row);
                    updateGroupCount(group);
                }, fail);
            });
        }

        function moveItemTo(row, group, beforeRow) {
            // `beforeRow` é a linha que passa a ficar logo ABAIXO do item; sem ela, vai para o fim do grupo
            var rows = groupRows(group).filter(function (r) { return r !== row; });
            var below = beforeRow && beforeRow !== row ? beforeRow : null;
            var index = below ? rows.indexOf(below) : rows.length;
            var above = index > 0 ? rows[index - 1] : null;
            var previousGroup = row.closest("[data-group]");
            var previousNext = row.nextElementSibling;
            var body = {
                group_id: Number(group.dataset.groupId),
                before_id: above ? Number(above.dataset.itemId) : null,
                after_id: below ? Number(below.dataset.itemId) : null
            };
            group.insertBefore(row, below || group.querySelector("[data-add-row]"));
            row.dataset.groupId = group.dataset.groupId;
            updateGroupCount(previousGroup);
            updateGroupCount(group);
            return request(url("item_move", {id: row.dataset.itemId}), body).then(null, function (error) {
                previousGroup.insertBefore(row, previousNext);
                row.dataset.groupId = previousGroup.dataset.groupId;
                updateGroupCount(previousGroup);
                updateGroupCount(group);
                fail(error);
            });
        }

        function openItemMenu(anchor, row) {
            var current = row.closest("[data-group]");
            var items = [];
            if (perms.edit_item) {
                var others = qa("tbody[data-group]").filter(function (g) { return g !== current; });
                if (others.length) items.push({heading: "Mover para o grupo"});
                others.forEach(function (g) {
                    items.push({label: g.dataset.groupName, icon: "arrow-right", onClick: function () { moveItemTo(row, g, null); }});
                });
                if (others.length) items.push({separator: true});
                items.push({label: "Renomear", icon: "file-text", onClick: function () { startItemRename(row); }});
            }
            if (perms.delete_item) items.push({label: "Excluir item", icon: "trash", danger: true, onClick: function () { deleteItem(row); }});
            openMenu(anchor, items, "Opções do item");
        }

        function startGroupRename(group) {
            var titleEl = group.querySelector("[data-group-title]");
            if (!perms.edit || !titleEl) return;
            var previous = titleEl.textContent;
            inlineEdit(titleEl, {
                value: previous, maxlength: 120,
                onCommit: function (value) {
                    titleEl.textContent = value || previous;
                    request(url("group_update", {id: group.dataset.groupId}), {name: value}).then(function (payload) {
                        group.dataset.groupName = payload.group.name;
                        titleEl.textContent = payload.group.name;
                    }, function (error) { titleEl.textContent = previous; fail(error); });
                }
            });
        }

        function moveGroup(group, direction) {
            var groups = qa("tbody[data-group]");
            var ids = groups.map(function (g) { return Number(g.dataset.groupId); });
            var index = groups.indexOf(group);
            var target = groups[index + direction];
            if (!target) return;
            var pos = neighbours(ids, Number(group.dataset.groupId), Number(target.dataset.groupId), direction > 0 ? "after" : "before");
            request(url("group_reorder", {id: group.dataset.groupId}), pos).then(function () {
                table.insertBefore(group, direction > 0 ? target.nextSibling : target);
            }, fail);
        }

        function openGroupMenu(anchor, group) {
            var groups = qa("tbody[data-group]");
            var index = groups.indexOf(group);
            openMenu(anchor, [
                {label: "Renomear grupo", icon: "file-text", onClick: function () { startGroupRename(group); }},
                {label: "Mudar a cor", icon: "sliders", onClick: function () { openGroupColor(anchor, group); }},
                {label: "Mover para cima", icon: "back", disabled: index === 0, onClick: function () { moveGroup(group, -1); }},
                {label: "Mover para baixo", icon: "arrow-right", disabled: index === groups.length - 1, onClick: function () { moveGroup(group, 1); }},
                {separator: true},
                {label: "Excluir grupo", icon: "trash", danger: true, onClick: function () { deleteGroup(group); }}
            ], "Opções do grupo");
        }

        function openGroupColor(anchor, group) {
            openPopover(anchor, paletteNode(group.dataset.groupColor, function (color) {
                closePopover(false);
                var previous = group.dataset.groupColor;
                group.style.setProperty("--group-color", color);
                group.dataset.groupColor = color;
                request(url("group_update", {id: group.dataset.groupId}), {color: color}).then(null, function (error) {
                    group.style.setProperty("--group-color", previous);
                    group.dataset.groupColor = previous;
                    fail(error);
                });
            }), {label: "Cores do grupo"});
        }

        function deleteGroup(group) {
            confirmDialog({
                title: "Excluir grupo", danger: true, confirmLabel: "Excluir grupo",
                message: "Excluir o grupo “" + group.dataset.groupName + "”? Só é possível se ele estiver sem itens."
            }).then(function (yes) {
                if (!yes) return;
                request(url("group_delete", {id: group.dataset.groupId}), {}).then(function () {
                    group.parentNode.removeChild(group);
                }, fail);
            });
        }

        function addGroup() {
            request(url("group_create", {id: meta.board.id}), {name: "Novo grupo"}).then(function (payload) {
                var group = parse(payload.group_html, "tbody");
                table.appendChild(group);
                startGroupRename(group);
            }, fail);
        }

        // -- células ----------------------------------------------------------------------------

        function pillNode(option) {
            return el("span", {class: "board-pill", text: option.label, style: "background:" + option.color + ";color:" + contrastColor(option.color)});
        }

        function optimisticCell(td, column, raw, extra) {
            td.textContent = "";
            td.dataset.value = raw == null ? "" : String(raw);
            var type = column.type;
            if (type === "STATUS" || type === "DROPDOWN") {
                if (extra && extra.option) td.appendChild(pillNode(extra.option));
                else td.appendChild(el("span", {class: "board-empty", text: type === "STATUS" ? "—" : " "}));
            } else if (type === "PERSON") {
                if (extra && extra.person) {
                    td.appendChild(el("span", {class: "board-person"}, [
                        el("span", {class: "board-avatar", text: initials(extra.person.name)}),
                        el("span", {class: "board-person__name", text: extra.person.name})
                    ]));
                }
            } else if (type === "DATE") {
                if (raw) {
                    var when = splitDateValue(raw);
                    td.appendChild(el("span", {class: "board-date", text: formatIsoDate(when.date) + (when.time ? " " + when.time : "")}));
                }
            } else if (type === "CHECKBOX") {
                var on = String(raw) === "1";
                var box = el("span", {class: "board-check" + (on ? " is-on" : "")});
                if (on) box.appendChild(icon("check"));
                td.appendChild(box);
            } else if (raw !== "" && raw != null) {
                td.appendChild(el("span", {class: type === "NUMBER" || type === "CURRENCY" ? "board-number" : "board-text", text: String(raw)}));
            }
        }

        function saveCell(td, raw, extra) {
            var column = columnMeta(td.dataset.columnId);
            var itemId = td.dataset.itemId;
            var snapshot = td.cloneNode(true);
            var hadFocus = doc.activeElement === td;
            var inDrawer = !!(td.closest && td.closest("[data-drawer]"));
            optimisticCell(td, column, raw, extra);
            td.classList.add("is-saving");
            return request(url("cell_update", {id: itemId, column: column.id}), {value: raw}).then(function (payload) {
                var fresh = payload.cell_html ? parse(payload.cell_html, "td") : null;
                if (fresh && td.parentNode && td.tagName === "TD") {
                    td.parentNode.replaceChild(fresh, td);
                    if (hadFocus) fresh.focus();
                } else if (fresh && td.parentNode) {
                    // campo de cartão (não é <td>): fica o mesmo elemento, com o conteúdo que o servidor desenhou
                    td.innerHTML = fresh.innerHTML;
                    td.dataset.value = fresh.dataset.value;
                    td.classList.remove("is-saving");
                } else {
                    td.classList.remove("is-saving"); // sem HTML novo: vale o que a tela já mostra
                }
                // mudou o que decide as raias (a etiqueta agrupadora), a soma ou a ordem: o servidor redistribui
                if (kanban && (column.id === kanban.group_column_id || column.id === kanban.sum_column_id ||
                    (kanban.settings.sort && kanban.settings.sort.by === column.id))) refreshKanban();
                // o calendário reposiciona o cartão (data), recolore (etiqueta) e atualiza o que o cartão mostra
                if (cal) {
                    refreshCalendar();
                    if (inDrawer) refreshDrawer(column.id);
                }
            }, function (error) {
                if (td.parentNode) td.parentNode.replaceChild(snapshot, td);
                snapshot.classList.add("has-error");
                win.setTimeout(function () { snapshot.classList.remove("has-error"); }, 2500);
                if (hadFocus) snapshot.focus();
                fail(error);
            });
        }

        function openCellEditor(td) {
            if (!perms.edit_item || td.querySelector(".board-inline-input")) return;
            var column = columnMeta(td.dataset.columnId);
            if (!column) return;
            var type = column.type;
            var current = td.dataset.value || "";
            if (type === "CHECKBOX") { saveCell(td, current === "1" ? "0" : "1"); return; }
            if (type === "TEXT" || type === "NUMBER" || type === "CURRENCY") return editCellInline(td, column, current);
            if (type === "DATE") return editDate(td, column, current);
            if (type === "STATUS" || type === "DROPDOWN") return editOption(td, column, current);
            if (type === "PERSON") return editPerson(td, column, current);
        }

        function editCellInline(td, column, current) {
            var input = el("input", {
                type: "text", class: "board-inline-input", maxlength: column.type === "TEXT" ? "5000" : "40",
                inputmode: column.type === "TEXT" ? null : "decimal", "aria-label": column.name
            });
            var done = false;
            input.value = current;
            var content = Array.prototype.slice.call(td.childNodes);
            content.forEach(function (node) { if (node.style) node.style.display = "none"; });
            td.appendChild(input);
            input.focus();
            input.select();
            function cleanup() {
                done = true;
                if (input.parentNode) input.parentNode.removeChild(input);
                content.forEach(function (node) { if (node.style) node.style.display = ""; });
            }
            function commit() {
                if (done) return;
                var value = input.value.trim();
                cleanup();
                if (value === current.trim()) { td.focus(); return; }
                saveCell(td, value);
            }
            input.addEventListener("keydown", function (event) {
                if (event.key === "Enter") { event.preventDefault(); commit(); }
                else if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); cleanup(); td.focus(); }
                else if (event.key === "Tab") { commit(); }
            });
            input.addEventListener("blur", commit);
        }

        function editDate(td, column, current) {
            if (cal) return editDateWithTime(td, column, current);
            var withTime = !!(column.settings && column.settings.show_time);
            var input = el("input", {type: withTime ? "datetime-local" : "date", "aria-label": column.name});
            input.value = current;
            var foot = el("div", {class: "board-pop__foot"});
            var today = el("button", {type: "button", class: "btn btn--sm", text: "Hoje"});
            today.addEventListener("click", function () {
                var now = new Date();
                var pad = function (n) { return (n < 10 ? "0" : "") + n; };
                var day = now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate());
                closePopover(false);
                saveCell(td, withTime ? day + "T" + pad(now.getHours()) + ":" + pad(now.getMinutes()) : day);
            });
            foot.appendChild(today);
            if (current && !column.is_required) {
                var clear = el("button", {type: "button", class: "btn btn--sm", text: "Limpar"});
                clear.addEventListener("click", function () { closePopover(false); saveCell(td, ""); });
                foot.appendChild(clear);
            }
            input.addEventListener("change", function () {
                if (!input.value) return;
                closePopover(true);
                saveCell(td, input.value);
            });
            openPopover(td, el("div", {}, [input, foot]), {label: column.name});
        }

        function editOption(td, column, current) {
            var list = el("div", {class: "board-options", role: "listbox", "aria-label": column.name});
            column.options.forEach(function (option) {
                var button = el("button", {
                    type: "button", class: "board-option", role: "option", text: option.label,
                    style: "background:" + option.color + ";color:" + contrastColor(option.color)
                });
                if (String(option.id) === String(current)) button.setAttribute("aria-selected", "true");
                button.addEventListener("click", function () { closePopover(true); saveCell(td, option.id, {option: option}); });
                list.appendChild(button);
            });
            var foot = el("div", {class: "board-pop__foot"});
            if (current && !column.is_required) {
                var clear = el("button", {type: "button", class: "btn btn--sm", text: "Limpar"});
                clear.addEventListener("click", function () { closePopover(true); saveCell(td, ""); });
                foot.appendChild(clear);
            }
            if (perms.manage_columns) {
                var edit = el("button", {type: "button", class: "btn btn--sm", text: "Editar etiquetas"});
                edit.addEventListener("click", function () { closePopover(false); openLabels(column.id); });
                foot.appendChild(edit);
            }
            if (!column.options.length) list.appendChild(el("p", {class: "board-people__hint", text: "Esta coluna ainda não tem etiquetas."}));
            openPopover(td, el("div", {}, [list, foot.childNodes.length ? foot : null]), {label: column.name});
        }

        // Busca de pessoas (a mesma do editor de célula e da janela de criar no calendário): digitar filtra no servidor.
        function personSearchNode(onPick) {
            var search = el("input", {type: "search", class: "board-people__search", placeholder: "Buscar pessoa…", "aria-label": "Buscar pessoa", maxlength: "60"});
            var list = el("ul", {class: "board-people__list"});
            var timer = null, serial = 0;
            function render(results) {
                list.textContent = "";
                if (!results.length) list.appendChild(el("li", {class: "board-people__hint", text: "Ninguém encontrado."}));
                results.forEach(function (person) {
                    var button = el("button", {type: "button", class: "board-people__item"}, [
                        el("span", {class: "board-avatar", text: initials(person.name)}), el("span", {text: person.name})
                    ]);
                    button.addEventListener("click", function () { onPick(person); });
                    list.appendChild(el("li", {}, [button]));
                });
            }
            function load(term) {
                var mine = (serial += 1);
                win.fetch(meta.urls.person_search + "?q=" + encodeURIComponent(term), {credentials: "same-origin", headers: {"X-Requested-With": "XMLHttpRequest"}})
                    .then(function (response) { return response.json(); })
                    .then(function (data) { if (mine === serial) render(data.results || []); })
                    .catch(function () { if (mine === serial) { list.textContent = ""; list.appendChild(el("li", {class: "board-people__hint", text: "Não foi possível buscar agora."})); } });
            }
            search.addEventListener("input", function () { win.clearTimeout(timer); timer = win.setTimeout(function () { load(search.value.trim()); }, 200); });
            return {search: search, list: list, load: load};
        }

        function editPerson(td, column, current) {
            var finder = personSearchNode(function (person) { closePopover(true); saveCell(td, person.id, {person: person}); });
            var foot = el("div", {class: "board-pop__foot"});
            if (current && !column.is_required) {
                var clear = el("button", {type: "button", class: "btn btn--sm", text: "Remover pessoa"});
                clear.addEventListener("click", function () { closePopover(true); saveCell(td, ""); });
                foot.appendChild(clear);
            }
            openPopover(td, el("div", {}, [finder.search, finder.list, foot.childNodes.length ? foot : null]), {label: column.name});
            finder.load("");
        }

        function moveFocus(td, dRow, dCol) {
            if (td.tagName !== "TD") return; // as setas só andam pela tabela
            var rows = qa("tbody[data-group]:not(.is-collapsed) tr[data-item-row]");
            var row = td.closest("tr");
            var cells = qa("td[data-cell]", row);
            var rowIndex = rows.indexOf(row), colIndex = cells.indexOf(td);
            var targetRow = rows[rowIndex + dRow];
            if (!targetRow) return;
            var targetCells = qa("td[data-cell]", targetRow);
            var target = targetCells[clamp(colIndex + dCol, 0, targetCells.length - 1)];
            if (target) target.focus();
        }

        // -- visualizações do quadro (abas) -----------------------------------------------------

        // Cria uma coluna de Data (o Calendário precisa de uma) sem sair da tela. Na tabela a coluna entra na hora.
        function createDateColumn() {
            return request(url("column_create"), {type: "DATE"}).then(function (payload) {
                if (table) insertColumn(payload); else meta.columns.push(payload.column);
                return payload.column;
            }, function (error) { fail(error); return null; });
        }

        function hasDateColumn() {
            return meta.columns.some(function (column) { return column.type === "DATE"; });
        }

        function openViewDialog() {
            var kinds = [
                {key: "TABLE", label: "Tabela", text: "Já existe: é o Quadro principal."},
                {key: "KANBAN", label: "Kanban", text: "Os mesmos itens em raias, por Status ou Lista suspensa.", name: "Kanban"},
                {key: "CALENDAR", label: "Calendário", text: "Os mesmos itens nos dias de uma coluna de Data.", name: "Calendário"},
                {key: "TIMELINE", label: "Linha do tempo", text: "Em breve."},
                {key: "DASHBOARD", label: "Dashboard", text: "Em breve."}
            ];
            var selected = "KANBAN";
            var touched = false;
            var name = el("input", {type: "text", maxlength: "80", "aria-label": "Nome da visualização"});
            name.value = "Kanban";
            name.addEventListener("input", function () { touched = true; });
            var notice = el("div", {class: "board-field__hint", role: "status", hidden: true});
            var types = el("div", {class: "board-view-types", role: "radiogroup", "aria-label": "Tipo de visualização"});
            var options = {};
            var createButton = null;

            function updateNotice() {
                var missing = selected === "CALENDAR" && !hasDateColumn();
                notice.hidden = !missing;
                notice.textContent = "";
                if (createButton) createButton.disabled = missing;
                if (!missing) return;
                notice.appendChild(el("p", {text: "Para usar o Calendário, escolha ou crie uma coluna de Data."}));
                if (perms.manage_columns) {
                    var make = el("button", {type: "button", class: "btn btn--sm", text: "+ Criar coluna de Data"});
                    make.addEventListener("click", function () {
                        make.disabled = true;
                        createDateColumn().then(function (column) { if (column) updateNotice(); else make.disabled = false; });
                    });
                    notice.appendChild(make);
                }
            }
            function choose(kind) {
                selected = kind.key;
                Object.keys(options).forEach(function (key) {
                    options[key].classList.toggle("is-selected", key === selected);
                    options[key].setAttribute("aria-checked", key === selected ? "true" : "false");
                });
                if (!touched) name.value = kind.name;
                updateNotice();
            }
            kinds.forEach(function (kind) {
                var available = !!kind.name;
                var option = el("button", {
                    type: "button", role: "radio", "aria-checked": kind.key === selected ? "true" : "false",
                    class: "board-view-type" + (kind.key === selected ? " is-selected" : "") + (available ? "" : " is-disabled"),
                    "aria-disabled": available ? null : "true", disabled: available ? null : true
                }, [el("strong", {text: kind.label}), el("span", {text: kind.text})]);
                if (available) option.addEventListener("click", function () { choose(kind); });
                options[kind.key] = option;
                types.appendChild(option);
            });
            var field = el("label", {class: "board-field"}, [el("span", {text: "Nome da visualização"}), name]);
            var dialog = openDialog("Adicionar visualização", el("div", {}, [types, notice, field]), [
                {label: "Cancelar"},
                {label: "Criar visualização", kind: "primary", onClick: function (d) {
                    if (selected === "CALENDAR" && !hasDateColumn()) { d.error("Para usar o Calendário, escolha ou crie uma coluna de Data."); return; }
                    request(url("view_create"), {name: name.value, type: selected}).then(function (payload) {
                        d.close();
                        navigate(payload.redirect_url);
                    }, function (error) { d.error(error.message); });
                }}
            ]);
            createButton = dialog.root.querySelector(".btn--primary");
            return dialog;
        }

        function renameViewDialog(viewId, currentName) {
            var name = el("input", {type: "text", maxlength: "80", "aria-label": "Nome da visualização"});
            name.value = currentName;
            openDialog("Renomear visualização", el("label", {class: "board-field"}, [el("span", {text: "Nome"}), name]), [
                {label: "Cancelar"},
                {label: "Salvar", kind: "primary", onClick: function (d) {
                    request(url("view_update", {id: viewId}), {name: name.value}).then(function (payload) {
                        d.close();
                        qa('a.board-tab[data-view-id="' + viewId + '"]', page).forEach(function (link) {
                            link.dataset.viewName = payload.view.name;
                            var label = link.querySelector("span");
                            if (label) label.textContent = payload.view.name;
                        });
                    }, function (error) { d.error(error.message); });
                }}
            ]);
        }

        function openViewMenu(anchor, viewId) {
            var link = q('a.board-tab[data-view-id="' + viewId + '"]', page);
            var current = link ? (link.dataset.viewName || link.textContent.trim()) : "";
            openMenu(anchor, [
                {label: "Renomear", icon: "file-text", onClick: function () { renameViewDialog(viewId, current); }},
                {separator: true},
                {label: "Excluir visualização", icon: "trash", danger: true, onClick: function () {
                    confirmDialog({
                        title: "Excluir visualização", danger: true, confirmLabel: "Excluir visualização",
                        message: "Excluir a visualização “" + current + "”? Os itens do quadro não são afetados."
                    }).then(function (yes) {
                        if (!yes) return;
                        request(url("view_delete", {id: viewId}), {}).then(function (payload) { navigate(payload.redirect_url); }, fail);
                    });
                }}
            ], "Opções da visualização " + current);
        }

        // -- Kanban -----------------------------------------------------------------------------
        // O Kanban é o componente ÚNICO do sistema (static/js/kanban-core.js + templates/kanban/*, o mesmo de Demandas):
        // arrastar, menu "Mover para…", renomear o título no lugar, contagem, desfazer, redesenho e "Configurar cartões"
        // são dele. Aqui ficam só as ligações de Quadros: como gravar (a célula agrupadora, o nome do item), as etiquetas
        // da raia, excluir e criar. Tudo que muda a distribuição (agrupar por, etiquetas, configuração do cartão) pede
        // as raias de novo (o servidor é quem sabe distribuir os itens).

        var lanesRoot = page.querySelector("[data-kanban-lanes]");
        var kanban = lanesRoot ? meta.kanban : null;
        var kanbanCore = null;

        function queryState() {
            var params = new win.URLSearchParams(win.location.search);
            return {q: params.get("q") || "", pessoa: params.get("pessoa") || ""};
        }

        function syncKanbanControls() {
            if (!kanban) return;
            var groupSelect = page.querySelector("[data-kanban-group-by]");
            if (groupSelect && kanban.group_column_id) groupSelect.value = String(kanban.group_column_id);
            var sortSelect = page.querySelector("[data-kanban-sort]");
            if (sortSelect) {
                var sort = kanban.settings.sort || {by: "manual", dir: "asc"};
                sortSelect.value = sort.by + "|" + sort.dir;
            }
        }

        function applyLanes(payload) {
            // o HTML das raias quem troca é o núcleo (preservando rolagem e foco); aqui só o que o servidor diz sobre o quadro
            meta.columns = payload.columns;
            kanban.settings = payload.settings;
            kanban.group_column_id = payload.group_column_id;
            kanban.sum_column_id = payload.sum_column_id;
            kanban.card_column_ids = payload.card_column_ids;
            syncKanbanControls();
        }

        function refreshKanban() { return kanbanCore.reload(); }

        function updateView(settings) {
            return request(url("view_update", {id: kanban.view.id}), {settings: settings}).then(function (payload) {
                kanban.settings = payload.settings;
                return refreshKanban();
            }, function (error) {
                fail(error);
                syncKanbanControls();
            });
        }

        function addCard(lane) {
            if (!kanban.default_group_id) { toast("Crie um grupo no Quadro principal antes de adicionar itens.", "error"); return null; }
            var body = {group_id: kanban.default_group_id, name: ""};
            if (kanban.group_column_id) body.initial = {column_id: kanban.group_column_id, value: lane.dataset.optionId ? Number(lane.dataset.optionId) : ""};
            return request(url("item_create", {id: meta.board.id}), body).then(function (payload) {
                return refreshKanban().then(function () {
                    var card = q('[data-card][data-item-id="' + payload.item.id + '"]', lanesRoot);
                    if (card) startItemRename(card);
                });
            }, fail);
        }

        function deleteCard(card) {
            var lane = card.closest("[data-lane]");
            confirmDialog({
                title: "Excluir item", danger: true, confirmLabel: "Excluir",
                message: "Excluir “" + card.querySelector("[data-card-title]").textContent.trim() + "”? Ele deixa de aparecer no quadro."
            }).then(function (yes) {
                if (!yes) return;
                var payload = cancellationPayload();
                if (payload === null) return;
                request(url("item_delete", {id: card.dataset.itemId}), payload).then(function () {
                    card.parentNode.removeChild(card);
                    kanbanCore.updateCount(lane);
                    return refreshKanban();
                }, fail);
            });
        }

        function renameLane(lane) {
            var titleEl = lane.querySelector("[data-lane-title]");
            if (!perms.manage_columns || !lane.dataset.optionId || !titleEl) return;
            var previous = lane.dataset.laneLabel;
            inlineEdit(titleEl, {
                value: previous, maxlength: 120,
                onCommit: function (value) {
                    titleEl.textContent = value || previous;
                    request(url("option_update", {id: lane.dataset.optionId}), {label: value}).then(refreshKanban, function (error) {
                        titleEl.textContent = previous;
                        fail(error);
                    });
                }
            });
        }

        function recolorLane(anchor, lane) {
            openPopover(anchor, paletteNode(lane.style.getPropertyValue("--lane-color"), function (color) {
                closePopover(false);
                request(url("option_update", {id: lane.dataset.optionId}), {color: color}).then(refreshKanban, fail);
            }), {label: "Cores da raia"});
        }

        function laneMenuItems(ctx) {
            return [
                {label: "Renomear etiqueta", icon: "file-text", onClick: function () { renameLane(ctx.lane); }},
                {label: "Mudar a cor", icon: "sliders", onClick: function () { recolorLane(ctx.anchor, ctx.lane); }},
                {label: "Editar etiquetas", icon: "list-ul", onClick: function () { openLabels(kanban.group_column_id); }}
            ];
        }

        function openKanbanConfig() {
            var settings = kanban.settings;
            var summable = meta.columns.filter(function (column) { return kanban.summable_ids.indexOf(column.id) >= 0; });
            kanbanCore.openConfig({
                controls: [
                    {type: "check", key: "show_empty", label: "Mostrar raias vazias", value: settings.show_empty},
                    {type: "select", key: "blank_lane", label: "Raia “Em branco” (itens sem etiqueta)", value: settings.blank_lane,
                        choices: [["auto", "Só quando houver itens"], ["always", "Sempre"], ["never", "Nunca"]]},
                    {type: "select", key: "sum_column", label: "Somar valor no cabeçalho da raia",
                        choices: [["", "Não somar"]].concat(summable.map(function (column) { return [String(column.id), column.name]; })),
                        value: kanban.sum_column_id ? String(kanban.sum_column_id) : "", parse: function (value) { return value ? Number(value) : null; }},
                    {type: "check", key: "show_field_names", label: "Mostrar o nome de cada campo no cartão", value: settings.show_field_names}
                ],
                fields: meta.columns.map(function (column) { return {id: column.id, name: column.name}; }),
                selected: kanban.card_column_ids,
                save: updateView
            });
        }

        if (kanban) {
            if (!win.LPSKanbanCore) throw new Error("static/js/kanban-core.js precisa ser carregado antes de boards.js");
            kanbanCore = win.LPSKanbanCore.init(lanesRoot.closest(".kanban-scroll") || lanesRoot.parentNode, {
                // arrastar um cartão grava a etiqueta da coluna agrupadora pelo mesmo endpoint da célula (mesma permissão e auditoria)
                move: function (ctx) {
                    var value = ctx.to.dataset.optionId ? Number(ctx.to.dataset.optionId) : "";
                    return request(url("cell_update", {id: ctx.itemId, column: kanban.group_column_id}), {value: value}).then(function () {
                        return {silent: true}; // Quadros nunca avisou sucesso ao mover: as raias redesenhadas são o aviso
                    });
                },
                reload: function () {
                    return request(url("view_lanes", {id: kanban.view.id}), queryState()).then(function (payload) {
                        if (!payload || typeof payload.lanes_html !== "string") return null;
                        applyLanes(payload);
                        return payload.lanes_html;
                    });
                },
                rename: function (ctx) { return request(url("item_rename", {id: ctx.itemId}), {name: ctx.title}); },
                laneMenu: laneMenuItems,
                addCard: function (ctx) { addCard(ctx.lane); },
                menuItems: function (ctx) {
                    var items = [];
                    if (perms.edit_item) items.push({label: "Renomear", icon: "file-text", onClick: function () { kanbanCore.startRename(ctx.card); }});
                    if (perms.delete_item) items.push({label: "Excluir item", icon: "trash", danger: true, onClick: function () { deleteCard(ctx.card); }});
                    return items;
                }
            });
        }
        if (kanban) {
            var groupSelect = page.querySelector("[data-kanban-group-by]");
            if (groupSelect) groupSelect.addEventListener("change", function () { updateView({group_by: groupSelect.value ? Number(groupSelect.value) : null}); });
            var sortSelect = page.querySelector("[data-kanban-sort]");
            if (sortSelect) sortSelect.addEventListener("change", function () {
                var parts = sortSelect.value.split("|");
                var by = /^\d+$/.test(parts[0]) ? Number(parts[0]) : parts[0];
                updateView({sort: {by: by, dir: parts[1] || "asc"}});
            });
        }

        // -- Calendário -------------------------------------------------------------------------
        // O Calendário lê os mesmos itens do quadro; o servidor posiciona os cartões nos dias. Aqui só se liga o
        // comportamento: arrastar o cartão para outro dia grava a MESMA célula de data (pelo endpoint da célula, então
        // com a mesma permissão e auditoria da tabela), criar no dia já manda a data preenchida, e tudo que muda o que
        // aparece (mês, configuração, edição de um campo) pede o corpo do calendário de novo.

        var calRoot = page.querySelector("[data-cal-body]");
        var cal = calRoot ? meta.calendar : null;
        var drawerRoot = page.querySelector("[data-cal-drawer]");
        var calConfigState = null;

        function calDay(iso) { return calRoot ? q('[data-cal-day][data-date="' + iso + '"]', calRoot) : null; }
        function calCardEl(itemId) { return calRoot ? q('[data-cal-card][data-item-id="' + itemId + '"]', calRoot) : null; }
        function dateColumn() { return cal && cal.date_column_id ? columnMeta(cal.date_column_id) : null; }
        function dateShowsTime() {
            var column = dateColumn();
            return !!(column && column.settings && column.settings.show_time);
        }

        function isoToday() {
            var now = new Date();
            var pad = function (n) { return (n < 10 ? "0" : "") + n; };
            return now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate());
        }

        function calHref(month) {
            var params = new win.URLSearchParams(win.location.search);
            params.set("mes", month);
            return win.location.pathname + "?" + params.toString();
        }

        function setNav(selector, month) {
            var link = page.querySelector(selector);
            if (!link) return;
            link.dataset.month = month;
            link.setAttribute("href", calHref(month));
        }

        function applyCalendar(payload) {
            if (!payload || typeof payload.body_html !== "string") return;
            calRoot.innerHTML = payload.body_html;
            meta.columns = payload.columns;
            cal.settings = payload.settings;
            cal.date_column_id = payload.date_column_id;
            cal.color_kind = payload.color_kind;
            cal.color_column_id = payload.color_column_id;
            cal.card_column_ids = payload.card_column_ids;
            if (payload.dateable_ids) cal.dateable_ids = payload.dateable_ids; // criar uma coluna de Data muda as opções da configuração
            if (payload.colorable_ids) cal.colorable_ids = payload.colorable_ids;
            cal.month = payload.month;
            var title = page.querySelector("[data-cal-title]");
            if (title) title.textContent = payload.title;
            setNav("[data-cal-prev]", payload.prev);
            setNav("[data-cal-next]", payload.next);
            setNav("[data-cal-today]", payload.today);
            var monthInput = page.querySelector("[data-cal-month-input]");
            if (monthInput) monthInput.value = payload.month;
            if (calConfigState) calConfigState.updatePreview();
        }

        // Devolve o que o servidor mandou, ou null se falhou (o aviso já foi mostrado). `options.quiet`: navegar não é gravar.
        function refreshCalendar(month, options) {
            return request(url("view_calendar", {id: cal.view.id}), {mes: month || cal.month, q: queryState().q, pessoa: queryState().pessoa}, options)
                .then(function (payload) { applyCalendar(payload); return payload; }, function (error) { fail(error); return null; });
        }

        function goToMonth(month) {
            return refreshCalendar(month, {quiet: true}).then(function (payload) {
                if (!payload) return;
                try { win.history.replaceState(null, "", calHref(payload.month)); } catch (e) { /* sem histórico: só não atualiza o endereço */ }
            });
        }

        function updateCalView(settings) {
            return request(url("view_update", {id: cal.view.id}), {settings: settings}).then(function (payload) {
                cal.settings = payload.settings;
                return refreshCalendar();
            }, function (error) { fail(error); return null; });
        }

        // um dia com mais cartões que o limite mostra os primeiros e "+ N mais" (o resto continua no DOM, escondido)
        function layoutDay(day) {
            var cards = qa("[data-cal-card]", day);
            cards.forEach(function (card, index) { card.classList.toggle("is-overflow", index >= cal.max_visible); });
            var extra = Math.max(0, cards.length - cal.max_visible);
            var more = day.querySelector("[data-cal-more]");
            if (extra && !more) {
                more = el("button", {type: "button", class: "cal-day__more", "data-cal-more": true});
                day.appendChild(more);
            }
            if (!more) return;
            if (extra) more.textContent = "+ " + extra + " mais";
            else if (more.parentNode) more.parentNode.removeChild(more);
        }

        // Arrastar para outro dia muda SÓ a data (e mantém a hora do cartão): status, pessoa e o resto não se mexem.
        // Otimista: o cartão muda de dia na hora e volta, com aviso, se o servidor recusar.
        function moveCalCard(card, targetDay) {
            var column = dateColumn();
            var fromDay = card.closest("[data-cal-day]");
            if (!cal || !column || !fromDay || !targetDay || fromDay === targetDay || targetDay.classList.contains("is-blocked")) return null;
            var oldDate = card.dataset.date, time = card.dataset.time || "";
            var iso = targetDay.dataset.date;
            var next = card.nextElementSibling;
            var targetItems = targetDay.querySelector("[data-cal-items]");
            targetItems.insertBefore(card, targetItems.firstChild);
            card.dataset.date = iso;
            layoutDay(fromDay);
            layoutDay(targetDay);
            return request(url("cell_update", {id: card.dataset.itemId, column: column.id}), {value: composeDateValue(iso, dateShowsTime() ? time : "")}).then(
                function () { return refreshCalendar(); },
                function (error) {
                    var back = fromDay.querySelector("[data-cal-items]");
                    back.insertBefore(card, next && next.parentNode === back ? next : null);
                    card.dataset.date = oldDate;
                    layoutDay(fromDay);
                    layoutDay(targetDay);
                    var reason = error && error.status && error.status < 500 && error.message ? " " + error.message : "";
                    toast("Não foi possível alterar a data. O item voltou para " + formatIsoDate(oldDate) + "." + reason, "error");
                }
            );
        }

        // -- gaveta do item: os campos editáveis no lugar, sem sair do calendário

        function drawerPanel() { return drawerRoot ? drawerRoot.querySelector("[data-drawer]") : null; }

        function closeDrawer(restoreFocus) {
            if (!drawerRoot || drawerRoot.hidden) return;
            var panel = drawerPanel();
            var itemId = panel ? panel.dataset.itemId : null;
            drawerRoot.hidden = true;
            drawerRoot.innerHTML = "";
            if (restoreFocus && itemId) {
                var card = calCardEl(itemId);
                if (card) card.focus();
            }
        }

        function openDrawer(itemId) {
            if (!drawerRoot) return null;
            return request(url("item_detail", {id: itemId}), {}, {quiet: true}).then(function (payload) {
                drawerRoot.innerHTML = payload.drawer_html;
                drawerRoot.hidden = false;
                var panel = drawerPanel();
                if (panel) panel.focus();
            }, fail);
        }

        // atualiza a gaveta aberta (campos e últimas mudanças) depois de uma gravação, devolvendo o foco ao campo editado
        function refreshDrawer(columnId) {
            var panel = drawerPanel();
            if (!panel) return null;
            var itemId = panel.dataset.itemId;
            return request(url("item_detail", {id: itemId}), {}, {quiet: true}).then(function (payload) {
                var current = drawerPanel();
                if (!current || current.dataset.itemId !== String(itemId)) return;
                drawerRoot.innerHTML = payload.drawer_html;
                if (columnId) {
                    var cell = drawerRoot.querySelector('[data-cell][data-column-id="' + columnId + '"]');
                    if (cell) cell.focus();
                }
            }, fail);
        }

        function startDrawerRename() {
            var panel = drawerPanel();
            var titleEl = panel ? panel.querySelector("[data-drawer-title]") : null;
            if (!perms.edit_item || !titleEl) return;
            var wasEmpty = titleEl.classList.contains("is-empty");
            var previous = wasEmpty ? "" : titleEl.textContent;
            var itemId = panel.dataset.itemId;
            inlineEdit(titleEl, {
                value: previous, maxlength: 255,
                onCommit: function (value) {
                    titleEl.textContent = value || "Sem título";
                    titleEl.classList.toggle("is-empty", !value);
                    request(url("item_rename", {id: itemId}), {name: value}).then(function () { refreshCalendar(); refreshDrawer(); }, function (error) {
                        titleEl.textContent = previous || "Sem título";
                        titleEl.classList.toggle("is-empty", !previous);
                        fail(error);
                    });
                }
            });
        }

        function deleteDrawerItem() {
            var panel = drawerPanel();
            if (!panel) return;
            var itemId = panel.dataset.itemId;
            var titleEl = panel.querySelector("[data-drawer-title]");
            var name = titleEl.classList.contains("is-empty") ? "Sem título" : titleEl.textContent.trim();
            confirmDialog({
                title: "Excluir item", danger: true, confirmLabel: "Excluir",
                message: "Excluir “" + name + "”? Ele deixa de aparecer no quadro."
            }).then(function (yes) {
                if (!yes) return;
                var payload = cancellationPayload();
                if (payload === null) return;
                request(url("item_delete", {id: itemId}), payload).then(function () { closeDrawer(false); refreshCalendar(); }, fail);
            });
        }

        // -- listas em pop-over: "+ N mais" de um dia, "Sem data" e "Atrasados"

        function openDayPopover(anchor, day) {
            var label = day.getAttribute("aria-label") || day.dataset.date;
            var holder = el("div", {class: "cal-pop-day"}, [el("p", {class: "board-pop__title", text: label})]);
            qa("[data-cal-card]", day).forEach(function (card) {
                var copy = card.cloneNode(true);
                copy.removeAttribute("draggable");
                copy.classList.remove("is-overflow");
                qa("[data-cell]", copy).forEach(function (node) {
                    node.removeAttribute("data-cell");
                    node.removeAttribute("tabindex");
                    node.classList.remove("is-editable");
                });
                copy.addEventListener("click", function () { closePopover(false); openDrawer(card.dataset.itemId); });
                copy.addEventListener("keydown", function (event) {
                    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); closePopover(false); openDrawer(card.dataset.itemId); }
                });
                holder.appendChild(copy);
            });
            openPopover(anchor, holder, {label: "Itens de " + label, wide: true});
        }

        function openPanel(anchor, key) {
            var source = calRoot.querySelector('[data-cal-panel="' + key + '"]');
            if (!source) return;
            var copy = source.cloneNode(true);
            copy.removeAttribute("data-cal-panel");
            copy.addEventListener("click", function (event) {
                var row = event.target.closest("[data-cal-open]");
                if (!row) return;
                closePopover(false);
                openDrawer(row.dataset.itemId);
            });
            openPopover(anchor, copy, {label: key === "overdue" ? "Itens atrasados" : "Itens sem data"});
        }

        // -- data com hora opcional (no calendário a data se edita neste pop-over; a hora só existe se a coluna a exibe)

        function editDateWithTime(td, column, current) {
            var withTime = !!(column.settings && column.settings.show_time);
            var parts = splitDateValue(current);
            var dateInput = el("input", {type: "date", "aria-label": column.name});
            dateInput.value = parts.date;
            var root = el("div", {class: "cal-datepop"}, [dateInput]);
            var finished = false;

            function commit(date, time) {
                if (finished) return;
                finished = true;
                closePopover(true);
                saveCell(td, composeDateValue(date, withTime ? time : ""));
            }
            dateInput.addEventListener("change", function () { if (dateInput.value) commit(dateInput.value, parts.time); });

            if (withTime) {
                var block = el("div", {class: "cal-datepop__time"});
                var timeInput = el("input", {type: "text", inputmode: "numeric", placeholder: "HH:MM", maxlength: "5", "aria-label": "Horário (opcional)"});
                timeInput.value = parts.time;
                var error = el("p", {class: "cal-datepop__error", role: "alert", hidden: true});
                var applyTime = function (text) {
                    var time = parseTimeInput(text);
                    if (!time) { error.textContent = "Use o formato HH:MM, por exemplo 14:30."; error.hidden = false; return; }
                    commit(dateInput.value || isoToday(), time);
                };
                var quick = el("div", {class: "cal-datepop__times"});
                ["08:00", "09:00", "10:00", "14:00", "15:00", "16:00"].forEach(function (time) {
                    var button = el("button", {type: "button", class: "btn btn--sm", text: time});
                    button.addEventListener("click", function () { applyTime(time); });
                    quick.appendChild(button);
                });
                timeInput.addEventListener("keydown", function (event) {
                    if (event.key === "Enter") { event.preventDefault(); applyTime(timeInput.value); }
                });
                timeInput.addEventListener("change", function () { if (timeInput.value.trim()) applyTime(timeInput.value); });
                block.appendChild(el("label", {text: "Horário (opcional)"}));
                block.appendChild(quick);
                block.appendChild(timeInput);
                block.appendChild(error);
                root.appendChild(block);
            } else if (perms.manage_columns) {
                var enable = el("button", {type: "button", class: "btn btn--sm", text: "Ativar horário nesta coluna"});
                enable.addEventListener("click", function () {
                    request(url("column_settings", {id: column.id}), {settings: {show_time: true}}).then(function (payload) {
                        for (var i = 0; i < meta.columns.length; i += 1) if (meta.columns[i].id === payload.column.id) meta.columns[i] = payload.column;
                        closePopover(false);
                        if (doc.contains(td)) editDateWithTime(td, payload.column, current);
                    }, fail);
                });
                root.appendChild(el("p", {class: "cal-datepop__hint", text: "Esta coluna guarda só o dia. O horário é opcional e pode ser ativado."}));
                root.appendChild(enable);
            }

            var foot = el("div", {class: "board-pop__foot"});
            var today = el("button", {type: "button", class: "btn btn--sm", text: "Hoje"});
            today.addEventListener("click", function () { commit(isoToday(), parts.time); });
            foot.appendChild(today);
            if (withTime && parts.time) {
                var clearTime = el("button", {type: "button", class: "btn btn--sm", text: "Limpar horário"});
                clearTime.addEventListener("click", function () { commit(parts.date, ""); });
                foot.appendChild(clearTime);
            }
            if (parts.date && !column.is_required) {
                var clearDate = el("button", {type: "button", class: "btn btn--sm", text: "Limpar data"});
                clearDate.addEventListener("click", function () {
                    if (finished) return;
                    finished = true;
                    closePopover(true);
                    saveCell(td, "");
                });
                foot.appendChild(clearDate);
            }
            root.appendChild(foot);
            openPopover(td, root, {label: column.name});
        }

        // -- criar no dia: a janela abre por cima do calendário, com a data já preenchida

        function createControl(column) {
            var type = column.type;
            if (type === "STATUS" || type === "DROPDOWN") {
                var select = el("select", {"aria-label": column.name}, [el("option", {value: "", text: "—"})]);
                column.options.forEach(function (option) { select.appendChild(el("option", {value: String(option.id), text: option.label})); });
                column.options.forEach(function (option) { if (option.is_default) select.value = String(option.id); });
                return {node: el("label", {class: "board-field"}, [el("span", {text: column.name}), select]), value: function () { return select.value ? Number(select.value) : ""; }};
            }
            if (type === "PERSON") {
                var chosen = null;
                var chip = el("div", {class: "cal-form__chosen", hidden: true});
                var holder = el("div", {class: "cal-form__person"});
                var finder = personSearchNode(function (person) {
                    chosen = person;
                    chip.hidden = false;
                    chip.textContent = "";
                    var remove = el("button", {type: "button", "aria-label": "Remover " + person.name, text: "×"});
                    remove.addEventListener("click", function () { chosen = null; chip.hidden = true; });
                    chip.appendChild(el("span", {text: person.name}));
                    chip.appendChild(remove);
                });
                finder.list.className = "board-people__list cal-form__person-list";
                holder.appendChild(chip);
                holder.appendChild(finder.search);
                holder.appendChild(finder.list);
                finder.load("");
                return {node: el("div", {class: "board-field"}, [el("span", {text: column.name}), holder]), value: function () { return chosen ? chosen.id : ""; }};
            }
            if (type === "CHECKBOX") {
                var box = el("input", {type: "checkbox"});
                return {node: el("label", {class: "board-field board-field--check"}, [box, el("span", {text: column.name})]), value: function () { return box.checked ? "1" : ""; }};
            }
            if (type === "DATE") {
                var withTime = !!(column.settings && column.settings.show_time);
                var date = el("input", {type: withTime ? "datetime-local" : "date", "aria-label": column.name});
                return {node: el("label", {class: "board-field"}, [el("span", {text: column.name}), date]), value: function () { return date.value; }};
            }
            if (type === "TEXT" || type === "NUMBER" || type === "CURRENCY") {
                var text = el("input", {type: "text", maxlength: type === "TEXT" ? "5000" : "40", inputmode: type === "TEXT" ? null : "decimal", "aria-label": column.name});
                return {node: el("label", {class: "board-field"}, [el("span", {text: column.name}), text]), value: function () { return text.value.trim(); }};
            }
            return null;
        }

        function openCreateDialog(iso) {
            var column = dateColumn();
            if (!column || !perms.create_item) return null;
            if (!cal.default_group_id) { toast("Crie um grupo no Quadro principal antes de adicionar itens.", "error"); return null; }
            var withTime = dateShowsTime();
            var label = String(meta.board.item_label || "item").toLowerCase();
            var form = el("form", {class: "cal-form", novalidate: true});
            var title = el("input", {type: "text", maxlength: "255", "aria-label": "Título"});
            form.appendChild(el("label", {class: "board-field"}, [el("span", {text: "Título"}), title]));

            var groupSelect = null;
            if ((meta.groups || []).length > 1) {
                groupSelect = el("select", {"aria-label": "Grupo"});
                meta.groups.forEach(function (group) { groupSelect.appendChild(el("option", {value: String(group.id), text: group.name})); });
                groupSelect.value = String(cal.default_group_id);
                form.appendChild(el("label", {class: "board-field"}, [el("span", {text: "Grupo"}), groupSelect]));
            }

            var dateInput = el("input", {type: "date", "aria-label": column.name});
            dateInput.value = iso;
            var timeInput = withTime ? el("input", {type: "text", inputmode: "numeric", placeholder: "HH:MM", maxlength: "5", "aria-label": "Horário (opcional)"}) : null;
            var dateRow = el("div", {class: "cal-form__row"}, [
                el("label", {class: "board-field"}, [el("span", {text: column.name}), dateInput]),
                timeInput ? el("label", {class: "board-field"}, [el("span", {text: "Horário (opcional)"}), timeInput]) : null
            ]);
            form.appendChild(dateRow);

            var controls = [];
            (cal.card_column_ids || []).forEach(function (id) {
                var meta_column = columnMeta(id);
                if (!meta_column || meta_column.id === column.id) return;
                var control = createControl(meta_column);
                if (!control) return;
                controls.push({column: meta_column, control: control});
                form.appendChild(control.node);
            });

            var dialog;
            function submit(button) {
                var name = title.value.trim();
                if (!name) { dialog.error("Informe o título."); title.focus(); return; }
                if (!dateInput.value) { dialog.error("Informe a data."); dateInput.focus(); return; }
                var time = "";
                if (timeInput && timeInput.value.trim()) {
                    time = parseTimeInput(timeInput.value);
                    if (!time) { dialog.error("Use o formato HH:MM para o horário, por exemplo 14:30."); timeInput.focus(); return; }
                }
                var initial = [{column_id: column.id, value: composeDateValue(dateInput.value, time)}];
                controls.forEach(function (entry) {
                    var value = entry.control.value();
                    if (value !== "" && value != null) initial.push({column_id: entry.column.id, value: value});
                });
                button.disabled = true;
                var body = {group_id: Number(groupSelect ? groupSelect.value : cal.default_group_id), name: name, initial: initial};
                request(url("item_create", {id: meta.board.id}), body).then(function (payload) {
                    dialog.close();
                    return refreshCalendar().then(function () {
                        if (!calCardEl(payload.item.id)) toast("“" + name + "” foi criado para " + formatIsoDate(dateInput.value) + ".");
                    });
                }, function (error) { button.disabled = false; dialog.error(error.message); });
            }
            dialog = openDialog("Criar " + label, form, [
                {label: "Cancelar"},
                {label: "Criar " + label, kind: "primary", onClick: function (d, button) { submit(button); }}
            ]);
            form.addEventListener("submit", function (event) {
                event.preventDefault();
                submit(dialog.root.querySelector(".btn--primary"));
            });
            title.addEventListener("keydown", function (event) {
                if (event.key === "Enter") { event.preventDefault(); submit(dialog.root.querySelector(".btn--primary")); }
            });
            return dialog;
        }

        // -- configurar a visualização (salva sozinha a cada mudança)

        function createDateColumnForCalendar() {
            return createDateColumn().then(function (column) {
                if (!column) return null;
                var saved = perms.edit
                    ? request(url("view_update", {id: cal.view.id}), {settings: {date_field: column.id}}).then(null, function () { return null; })
                    : Promise.resolve(null);
                return saved.then(function () { return refreshCalendar(); });
            });
        }

        function openCalendarConfig() {
            var settings = function () { return cal.settings; };
            var root = el("div", {class: "kanban-config"});
            var controls = el("div", {class: "kanban-config__controls"});
            var preview = el("div", {class: "kanban-config__preview", "aria-label": "Pré-visualização do cartão"});
            var timer = null;

            function check(label, key) {
                var input = el("input", {type: "checkbox"});
                input.checked = !!settings()[key];
                input.addEventListener("change", function () {
                    var change = {};
                    change[key] = input.checked;
                    updateCalView(change).then(function (payload) { if (!payload) input.checked = !!settings()[key]; });
                });
                controls.appendChild(el("label", {class: "board-field board-field--check"}, [input, el("span", {text: label})]));
            }
            function select(label, key, choices, current, transform) {
                var control = el("select", {"aria-label": label});
                choices.forEach(function (choice) { control.appendChild(el("option", {value: choice[0], text: choice[1], disabled: choice[2] ? true : null})); });
                control.value = current;
                var previous = current;
                control.addEventListener("change", function () {
                    var change = {};
                    change[key] = transform ? transform(control.value) : control.value;
                    updateCalView(change).then(function (payload) {
                        if (payload) previous = control.value; else control.value = previous;
                    });
                });
                controls.appendChild(el("label", {class: "board-field"}, [el("span", {text: label}), control]));
            }
            var number = function (value) { return /^\d+$/.test(value) ? Number(value) : value; };

            var dates = meta.columns.filter(function (column) { return cal.dateable_ids.indexOf(column.id) >= 0; });
            select("Data utilizada", "date_field", dates.map(function (column) { return [String(column.id), column.name]; }),
                cal.date_column_id ? String(cal.date_column_id) : "", function (value) { return value ? Number(value) : null; });
            var colorable = meta.columns.filter(function (column) { return cal.colorable_ids.indexOf(column.id) >= 0; });
            select("Colorir por", "color_by",
                colorable.map(function (column) { return [String(column.id), column.name]; }).concat([["group", "Grupo do item"], ["none", "Sem cor"]]),
                cal.color_kind === "column" && cal.color_column_id ? String(cal.color_column_id) : cal.color_kind, number);
            select("Escala", "period", [["month", "Mês"], ["week", "Semana (em breve)", true], ["day", "Dia (em breve)", true], ["agenda", "Agenda (em breve)", true]], settings().period || "month");
            check("Mostrar finais de semana", "show_weekends");
            check("Mostrar concluídos (itens cujo Status representa conclusão)", "show_completed");

            // campos do cartão: marcados primeiro, na ordem do cartão; os demais depois, na ordem do quadro
            var candidates = meta.columns.filter(function (column) { return column.id !== cal.date_column_id; });
            var chosen = cal.card_column_ids.slice();
            var rest = candidates.map(function (column) { return column.id; }).filter(function (id) { return chosen.indexOf(id) < 0; });
            var order = chosen.concat(rest);
            var checked = {};
            chosen.forEach(function (id) { checked[id] = true; });
            var fields = el("div", {class: "kanban-config__fields", role: "list"});

            function saveFields() {
                win.clearTimeout(timer);
                timer = win.setTimeout(function () {
                    updateCalView({card_fields: order.filter(function (id) { return checked[id]; })});
                }, 250);
            }
            function renderFields() {
                fields.textContent = "";
                order.forEach(function (id, index) {
                    var column = columnMeta(id);
                    if (!column) return;
                    var box = el("input", {type: "checkbox", "aria-label": "Mostrar " + column.name + " no cartão"});
                    box.checked = !!checked[id];
                    box.addEventListener("change", function () {
                        if (box.checked && order.filter(function (other) { return checked[other]; }).length >= cal.max_card_fields) {
                            box.checked = false;
                            toast("O cartão do calendário aceita até " + cal.max_card_fields + " campos.", "error");
                            return;
                        }
                        checked[id] = box.checked;
                        saveFields();
                    });
                    var up = el("button", {type: "button", class: "btn btn--ghost btn--sm", "aria-label": "Subir " + column.name, text: "↑"});
                    var down = el("button", {type: "button", class: "btn btn--ghost btn--sm", "aria-label": "Descer " + column.name, text: "↓"});
                    up.disabled = index === 0;
                    down.disabled = index === order.length - 1;
                    up.addEventListener("click", function () { order.splice(index - 1, 0, order.splice(index, 1)[0]); renderFields(); saveFields(); });
                    down.addEventListener("click", function () { order.splice(index + 1, 0, order.splice(index, 1)[0]); renderFields(); saveFields(); });
                    fields.appendChild(el("div", {class: "kanban-config__field", role: "listitem"}, [
                        el("label", {}, [box, el("span", {text: column.name})]), el("span", {class: "kanban-config__move"}, [up, down])
                    ]));
                });
            }
            renderFields();
            controls.appendChild(el("p", {class: "board-pop__title", text: "Campos do cartão"}));
            controls.appendChild(el("p", {class: "board-field__hint", text: "O cartão do mês é compacto: o recomendado é até " + cal.recommended_card_fields + " campos (o limite é " + cal.max_card_fields + ")."}));
            controls.appendChild(fields);

            function updatePreview() {
                preview.textContent = "";
                preview.appendChild(el("p", {class: "board-pop__title", text: "Pré-visualização"}));
                var first = calRoot.querySelector("[data-cal-card]");
                if (!first) { preview.appendChild(el("p", {class: "board-field__hint", text: "Ainda não há cartões neste mês para mostrar."})); return; }
                var copy = first.cloneNode(true);
                copy.removeAttribute("draggable");
                copy.classList.add("is-preview");
                copy.classList.remove("is-overflow");
                qa("[tabindex]", copy).forEach(function (node) { node.removeAttribute("tabindex"); });
                qa("[data-cell]", copy).forEach(function (node) { node.removeAttribute("data-cell"); });
                preview.appendChild(copy);
            }
            calConfigState = {updatePreview: updatePreview};
            updatePreview();

            root.appendChild(controls);
            root.appendChild(preview);
            var dialog = openDialog("Configurar calendário", root, [{label: "Concluir", kind: "primary"}]);
            dialog.root.classList.add("board-dialog--wide");
            dialog.onClose = function () { win.clearTimeout(timer); calConfigState = null; };
        }

        // -- ligação dos eventos ----------------------------------------------------------------

        page.addEventListener("click", function (event) {
            var target = event.target;
            var node;
            if ((node = target.closest("[data-view-add]"))) {
                if (popover && popover.anchor === node) { closePopover(true); return; }
                openViewDialog();
                return;
            }
            if ((node = target.closest("[data-view-menu]"))) {
                if (popover && popover.anchor === node) { closePopover(true); return; }
                openViewMenu(node, Number(node.dataset.viewId));
                return;
            }
            if (kanban) {
                if ((node = target.closest("[data-kanban-config]"))) { openKanbanConfig(); return; }
                if ((node = target.closest("[data-lane-title]"))) {
                    if (event.detail >= 2) renameLane(node.closest("[data-lane]"));
                    return;
                }
            }
            if (cal) {
                if ((node = target.closest("[data-cal-nav]"))) {
                    if (event.ctrlKey || event.metaKey || event.shiftKey || event.button) return; // abrir em outra aba continua valendo
                    event.preventDefault();
                    goToMonth(node.dataset.month);
                    return;
                }
                if ((node = target.closest("[data-cal-add]"))) { openCreateDialog(node.closest("[data-cal-day]").dataset.date); return; }
                if ((node = target.closest("[data-cal-more]"))) {
                    if (popover && popover.anchor === node) { closePopover(true); return; }
                    openDayPopover(node, node.closest("[data-cal-day]"));
                    return;
                }
                if ((node = target.closest("[data-cal-panel-open]"))) {
                    if (popover && popover.anchor === node) { closePopover(true); return; }
                    openPanel(node, node.dataset.calPanelOpen);
                    return;
                }
                if ((node = target.closest("[data-cal-config]"))) { openCalendarConfig(); return; }
                if ((node = target.closest("[data-cal-show-weekends]"))) { updateCalView({show_weekends: true}); return; }
                if ((node = target.closest("[data-cal-create-date]"))) { createDateColumnForCalendar(); return; }
                if ((node = target.closest("[data-drawer-close]"))) { closeDrawer(true); return; }
                if ((node = target.closest("[data-drawer-delete]"))) { deleteDrawerItem(); return; }
                if ((node = target.closest("[data-drawer-title]"))) { startDrawerRename(); return; }
                if ((node = target.closest("[data-cal-card]"))) {
                    var field = target.closest("[data-cell]");
                    if (field) openCellEditor(field); else openDrawer(node.dataset.itemId);
                    return;
                }
            }
            if ((node = target.closest("[data-column-menu]"))) {
                event.stopPropagation();
                if (popover && popover.anchor === node) { closePopover(true); return; }
                openColumnMenu(node, Number(node.closest("th").dataset.columnId));
                return;
            }
            if ((node = target.closest("[data-column-add]"))) {
                if (popover && popover.anchor === node) { closePopover(true); return; }
                openTypePicker(node, null);
                return;
            }
            if ((node = target.closest("[data-item-add]"))) { addItem(node.closest("[data-group]")); return; }
            if ((node = target.closest("[data-group-add]"))) { addGroup(); return; }
            if ((node = target.closest("[data-item-menu]"))) {
                if (popover && popover.anchor === node) { closePopover(true); return; }
                openItemMenu(node, node.closest("tr")); return;
            }
            if ((node = target.closest("[data-group-menu]"))) {
                if (popover && popover.anchor === node) { closePopover(true); return; }
                openGroupMenu(node, node.closest("[data-group]")); return;
            }
            if ((node = target.closest("[data-group-toggle]"))) { toggleGroup(node.closest("[data-group]")); return; }
            if ((node = target.closest("[data-group-title]"))) { startGroupRename(node.closest("[data-group]")); return; }
            if ((node = target.closest("[data-item-name]"))) { startItemRename(node.closest("tr")); return; }
            if ((node = target.closest("[data-column-name]"))) {
                if (event.detail >= 2) startColumnRename(Number(node.closest("th").dataset.columnId), node.closest("[data-group]"));
                return;
            }
            if ((node = target.closest("[data-column-show]"))) {
                request(url("column_hide", {id: node.dataset.columnId}), {visible: true}).then(function () { win.location.reload(); }, fail);
                return;
            }
            if ((node = target.closest("[data-board-delete]"))) { deleteBoard(); return; }
            if ((node = target.closest("[data-cell]"))) { openCellEditor(node); return; }
        });

        page.addEventListener("keydown", function (event) {
            var node = event.target;
            if (node.matches && node.matches("[data-column-resize]")) { resizeByKey(event, node); return; }
            if (cal && node.matches && node.matches("[data-cal-card]") && (event.key === "Enter" || event.key === " ")) {
                event.preventDefault();
                openDrawer(node.dataset.itemId);
                return;
            }
            if (cal && node.matches && node.matches("[data-drawer-title]") && event.key === "Enter") { event.preventDefault(); startDrawerRename(); return; }
            if (node.matches && node.matches("[data-cell]")) {
                if (event.key === "Enter" || event.key === "F2" || (event.key === " " && node.dataset.type === "CHECKBOX")) {
                    event.preventDefault(); openCellEditor(node);
                } else if ((event.key === "Delete" || event.key === "Backspace") && perms.edit_item && node.dataset.type !== "CHECKBOX") {
                    var column = columnMeta(node.dataset.columnId);
                    if (node.dataset.value && !(column && column.is_required)) { event.preventDefault(); saveCell(node, ""); }
                } else if (event.key === "ArrowDown") { event.preventDefault(); moveFocus(node, 1, 0); }
                else if (event.key === "ArrowUp") { event.preventDefault(); moveFocus(node, -1, 0); }
                else if (event.key === "ArrowRight") { event.preventDefault(); moveFocus(node, 0, 1); }
                else if (event.key === "ArrowLeft") { event.preventDefault(); moveFocus(node, 0, -1); }
                return;
            }
            if (node.matches && node.matches("[data-item-name]") && event.key === "Enter") { event.preventDefault(); startItemRename(node.closest("tr")); return; }
            if (node.matches && node.matches("[data-group-title]") && event.key === "Enter") { event.preventDefault(); startGroupRename(node.closest("[data-group]")); }
        });

        page.addEventListener("mousedown", function (event) {
            var handle = event.target.closest("[data-column-resize]");
            if (handle) event.preventDefault();
        });
        page.addEventListener("pointerdown", function (event) {
            var handle = event.target.closest("[data-column-resize]");
            if (handle) startResize(event, handle);
        });

        // arrastar colunas e itens
        page.addEventListener("dragstart", function (event) {
            var calCard = event.target.closest && event.target.closest("[data-cal-card]");
            if (calCard && cal && perms.edit_item) {
                drag = {kind: "calcard", id: Number(calCard.dataset.itemId), el: calCard, day: calCard.closest("[data-cal-day]")};
                calCard.classList.add("is-dragging");
                if (event.dataTransfer) {
                    event.dataTransfer.effectAllowed = "move";
                    event.dataTransfer.setData("text/plain", "calcard:" + calCard.dataset.itemId);
                }
                return;
            }
            var grip = event.target.closest && event.target.closest("[data-item-grip]");
            var header = event.target.closest && event.target.closest("th[data-column-th]");
            if (grip) {
                var row = grip.closest("tr");
                drag = {kind: "item", id: Number(row.dataset.itemId), row: row};
                row.classList.add("is-dragging");
                if (event.dataTransfer) {
                    event.dataTransfer.effectAllowed = "move";
                    event.dataTransfer.setData("text/plain", "item:" + row.dataset.itemId);
                    if (event.dataTransfer.setDragImage) event.dataTransfer.setDragImage(row, 24, 20);
                }
            } else if (header && perms.manage_columns && !event.target.closest("[data-column-resize]")) {
                drag = {kind: "column", id: Number(header.dataset.columnId), header: header};
                header.classList.add("is-dragging");
                if (event.dataTransfer) { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", "column:" + header.dataset.columnId); }
            } else if (event.target.closest && event.target.closest("[data-column-resize]")) {
                event.preventDefault();
            }
        });

        page.addEventListener("dragover", function (event) {
            if (!drag) return;
            if (drag.kind === "calcard") {
                var overDay = event.target.closest("[data-cal-day]");
                if (!overDay || overDay.classList.contains("is-blocked")) return; // dia que a coluna recusa: sem "soltar aqui"
                event.preventDefault();
                clearDropMarks();
                if (overDay !== drag.day) overDay.classList.add("is-drop-target");
                return;
            }
            if (drag.kind === "column") {
                var header = event.target.closest("th[data-column-th]");
                if (!header || Number(header.dataset.columnId) === drag.id) return;
                event.preventDefault();
                clearDropMarks();
                var rect = header.getBoundingClientRect();
                header.classList.add(event.clientX < rect.left + rect.width / 2 ? "is-drop-before" : "is-drop-after");
            } else if (drag.kind === "item") {
                var row = event.target.closest("tr[data-item-row]");
                var group = event.target.closest("tbody[data-group]");
                if (!group) return;
                event.preventDefault();
                clearDropMarks();
                if (row && row !== drag.row) {
                    var box = row.getBoundingClientRect();
                    row.classList.add(event.clientY < box.top + box.height / 2 ? "is-drop-before" : "is-drop-after");
                } else if (!row) {
                    group.classList.add("is-drop-target");
                }
            }
        });

        page.addEventListener("drop", function (event) {
            if (!drag) return;
            var current = drag;
            event.preventDefault();
            if (current.kind === "calcard") {
                var dropDay = event.target.closest("[data-cal-day]");
                endDrag();
                if (dropDay) moveCalCard(current.el, dropDay);
                return;
            }
            var side;
            if (current.kind === "column") {
                var header = event.target.closest("th[data-column-th]");
                if (!header || Number(header.dataset.columnId) === current.id) { endDrag(); return; }
                side = header.classList.contains("is-drop-after") ? "after" : "before";
                var targetId = Number(header.dataset.columnId);
                var pos = neighbours(orderedColumnIds(), current.id, targetId, side);
                endDrag();
                var previousOrder = orderedColumnIds();
                moveColumnDom(current.id, pos.before_id, pos.after_id);
                request(url("column_reorder", {id: current.id}), pos).then(null, function (error) {
                    var prevIndex = previousOrder.indexOf(current.id);
                    moveColumnDom(current.id, previousOrder[prevIndex - 1] || null, previousOrder[prevIndex + 1] || null);
                    fail(error);
                });
            } else {
                var row = event.target.closest("tr[data-item-row]");
                var group = event.target.closest("tbody[data-group]");
                side = row && row.classList.contains("is-drop-after") ? "after" : "before";
                endDrag();
                if (!group) return;
                var reference = null;
                if (row) reference = side === "after" ? nextRow(row, group) : row;
                if (reference === current.row) reference = nextRow(reference, group);
                moveItemTo(current.row, group, reference);
            }
        });

        function nextRow(row, group) {
            var rows = groupRows(group);
            return rows[rows.indexOf(row) + 1] || null;
        }

        function endDrag() {
            clearDropMarks();
            if (drag) {
                if (drag.row) drag.row.classList.remove("is-dragging");
                if (drag.header) drag.header.classList.remove("is-dragging");
                if (drag.el) drag.el.classList.remove("is-dragging");
            }
            drag = null;
        }
        page.addEventListener("dragend", endDrag);

        // grupos recolhidos (só neste navegador)
        var collapsedKey = "lps-board-" + meta.board.id + "-collapsed";
        function readCollapsed() {
            try { return JSON.parse(win.localStorage.getItem(collapsedKey) || "[]"); } catch (e) { return []; }
        }
        function writeCollapsed(ids) {
            try { win.localStorage.setItem(collapsedKey, JSON.stringify(ids)); } catch (e) { /* sem armazenamento: só não lembra */ }
        }
        function toggleGroup(group) {
            var collapsed = group.classList.toggle("is-collapsed");
            var button = group.querySelector("[data-group-toggle]");
            if (button) button.setAttribute("aria-expanded", collapsed ? "false" : "true");
            var ids = readCollapsed().filter(function (id) { return id !== Number(group.dataset.groupId); });
            if (collapsed) ids.push(Number(group.dataset.groupId));
            writeCollapsed(ids);
        }
        readCollapsed().forEach(function (id) {
            var group = groupEl(id);
            if (group) { group.classList.add("is-collapsed"); var b = group.querySelector("[data-group-toggle]"); if (b) b.setAttribute("aria-expanded", "false"); }
        });

        // título do quadro e exclusão
        var titleInput = page.querySelector("[data-board-title]");
        if (titleInput && perms.edit) {
            var savedTitle = titleInput.value;
            titleInput.addEventListener("keydown", function (event) {
                if (event.key === "Enter") { event.preventDefault(); titleInput.blur(); }
                else if (event.key === "Escape") { titleInput.value = savedTitle; titleInput.blur(); }
            });
            titleInput.addEventListener("blur", function () {
                var value = titleInput.value.trim();
                if (!value) { titleInput.value = savedTitle; return; }
                if (value === savedTitle) return;
                request(url("board_rename", {id: meta.board.id}), {name: value}).then(function (payload) {
                    savedTitle = payload.name; titleInput.value = payload.name; doc.title = payload.name + " — Quadros — LPS";
                }, function (error) { titleInput.value = savedTitle; fail(error); });
            });
        }

        function deleteBoard() {
            confirmDialog({
                title: "Excluir quadro", danger: true, confirmLabel: "Excluir quadro",
                message: "Excluir o quadro “" + meta.board.name + "” com todos os itens? Esta ação tira o quadro da lista."
            }).then(function (yes) {
                if (!yes) return;
                request(url("board_delete", {id: meta.board.id}), {}).then(function (payload) { navigate(payload.redirect_url); }, fail);
            });
        }

        // filtro por pessoa envia o formulário na hora
        var personFilter = page.querySelector("[data-board-person-filter]");
        if (personFilter) personFilter.addEventListener("change", function () {
            if (personFilter.form) personFilter.form.submit();
        });

        // fechar pop-over ao clicar fora, ao rolar ou ao apertar Escape
        doc.addEventListener("mousedown", function (event) {
            if (!popover) return;
            if (popover.el.contains(event.target) || (popover.anchor && popover.anchor.contains(event.target))) return;
            closePopover(false);
        });
        doc.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && popover) { event.stopPropagation(); closePopover(true); return; }
            if (event.key === "Escape" && cal && drawerRoot && !drawerRoot.hidden) closeDrawer(true);
        });
        // rolar a tabela ou redimensionar a janela: o pop-over acompanha o botão que o abriu (e não fecha, porque o
        // navegador também dispara "scroll" quando só rola o botão para dentro da tela antes do clique)
        function keepPopoverAnchored() {
            if (popover && popover.anchor && doc.contains(popover.anchor)) placePopover(popover.el, popover.anchor);
        }
        if (scroller) scroller.addEventListener("scroll", keepPopoverAnchored);
        win.addEventListener("resize", keepPopoverAnchored);

        markDraggable();
        syncTableWidth();

        return {
            request: request, openColumnMenu: openColumnMenu, openTypePicker: openTypePicker, addColumn: addColumn,
            saveCell: saveCell, columnMeta: columnMeta, toast: toast, refreshKanban: refreshKanban, moveCard: function (card, lane) { return kanbanCore.move(card, lane); },
            refreshCalendar: refreshCalendar, openDrawer: openDrawer, moveCalCard: moveCalCard
        };
    }

    function boot() {
        var page = document.querySelector("[data-board-page]");
        var metaNode = document.getElementById("board-meta");
        if (!page || !metaNode || window.LPSBoards.instance) return;
        window.LPSBoards.instance = init(page, JSON.parse(metaNode.textContent));
    }

    window.LPSBoards = {helpers: helpers, init: init, boot: boot};
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();
})();
