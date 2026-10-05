/* Núcleo do Kanban (templates/kanban/*) — o comportamento ÚNICO do Kanban do sistema (Quadros e Demandas): arrastar com
   "Solte aqui para mover para…", menu ⋯ com "Mover para…" (a única forma em toque e no teclado) e as ações do anfitrião,
   contagem e vazio da raia, desfazer quando o servidor recusa, renomear o título no lugar, redesenho que preserva rolagem
   e foco e o diálogo "Configurar cartões". Não sabe nada do domínio: o servidor continua sendo a verdade; a tela antecipa
   o movimento e volta atrás com a mensagem dele.

   O que o núcleo lê da marcação (ver o cabeçalho de templates/kanban/_lanes.html):
     raia    [data-lane] [data-lane-key] [data-lane-label] [data-lane-scope] [data-lane-closed] [data-lane-body] [data-lane-empty] [data-lane-count]
     cartão  [data-card] [data-item-id] [data-card-scope] [data-updated-at] [draggable=true] [data-card-menu] [data-card-title][role=textbox]
   Uma raia recebe o cartão quando não é "fechada" e o escopo dela é vazio ou igual ao do cartão.

   Uso:  LPSKanbanCore.init(root, adapter)  →  {move, reload, redraw, startRename, openConfig, openMenu, updateCount}
     root     elemento que rola na horizontal e contém `[data-kanban-lanes]`
     adapter  move(ctx)        → Promise<{message?, silent?, updatedAt?, refresh?}>; rejeita com Error(mensagem) (error.refresh = true: redesenhar)
              reload()         → Promise<string> o HTML das raias (opcional; sem ele a tela fica como o movimento otimista deixou)
              beforeMove(ctx)  → boolean | Promise<boolean> (opcional; false cancela, nada muda na tela; `true` move no mesmo instante)
              rename(ctx)      → Promise<{title?, updatedAt?}> grava o título novo (opcional; sem ele o título não é editável pelo núcleo)
              menuItems(ctx)   → [{label, icon, danger, onClick} | {separator: true} | {heading}] ações do anfitrião no ⋯ do cartão (opcional)
     ctx      {card, from, to, itemId, laneKey, laneLabel, updatedAt} no move; {card, itemId, title, previous} no rename
   Editar o valor de um campo, "+ Adicionar" e o menu da raia continuam sendo do anfitrião (ele liga o clique na própria raiz);
   para não reimplementar menus, janelas e edição de texto, o anfitrião usa as primitivas em `LPSKanbanCore.ui`.
   `LPSKanbanCore.confirm({title, message, confirmLabel, danger})` → Promise<boolean>: a janela de confirmação do modelo (.board-dialog). */
(function () {
    "use strict";

    var doc = document;
    var ICONS = {};
    function icon(name) {
        if (!ICONS[name]) ICONS[name] = '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><use href="#i-' + name + '"></use></svg>';
        return ICONS[name];
    }

    function q(selector, from) { return (from || doc).querySelector(selector); }
    function qa(selector, from) { return Array.prototype.slice.call((from || doc).querySelectorAll(selector)); }

    function el(tag, attrs, children) {
        var element = doc.createElement(tag);
        Object.keys(attrs || {}).forEach(function (key) {
            var value = attrs[key];
            if (value === null || value === undefined || value === false) return;
            if (key === "class") element.className = value;
            else if (key === "text") element.textContent = value;
            else element.setAttribute(key, value === true ? "" : value);
        });
        (children || []).forEach(function (child) { if (child) element.appendChild(child); });
        return element;
    }

    function toast(message, kind) {
        var area = q("[data-board-toasts]");
        if (!area || !message) return;
        var box = el("div", {class: "board-toast" + (kind === "error" ? " is-error" : ""), text: message});
        area.appendChild(box);
        window.setTimeout(function () { if (box.parentNode) box.parentNode.removeChild(box); }, kind === "error" ? 6000 : 3000);
    }

    function placePopover(pop, anchor) {
        var rect = anchor.getBoundingClientRect();
        var width = pop.offsetWidth, height = pop.offsetHeight;
        var left = rect.left, top = rect.bottom + 4;
        if (left + width > window.innerWidth - 8) left = Math.max(8, window.innerWidth - width - 8);
        if (top + height > window.innerHeight - 8) {
            var above = rect.top - height - 4;
            top = above >= 8 ? above : Math.max(8, window.innerHeight - height - 8);
        }
        pop.style.left = left + "px";
        pop.style.top = top + "px";
    }

    function focusFirst(container) {
        var target = container && container.querySelector("input:not([type=hidden]), select, textarea, button:not([disabled]), [tabindex='0']");
        if (target) target.focus();
    }

    // -- edição de texto no lugar (a mesma de Quadros) -----------------------------------------------

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

    // -- janelas (as classes são as de Quadros) -------------------------------------------------------

    /** `buttons`: [{label, kind: "primary"|"danger", onClick(api, button)}]. `options`: {role, describedBy, focus(api) -> elemento}. */
    function openDialog(title, body, buttons, options) {
        options = options || {};
        var opener = doc.activeElement;
        var errorBox = el("p", {class: "board-dialog__error", role: "alert", hidden: true});
        var backdrop = el("div", {class: "board-dialog-backdrop"});
        var closeButton = el("button", {type: "button", class: "board-dialog__close", "aria-label": "Fechar", text: "×"});
        var head = el("div", {class: "board-dialog__head"}, [el("h2", {text: title}), closeButton]);
        var foot = el("div", {class: "board-dialog__foot"});
        var dialog = el("div", {
            class: "board-dialog", role: options.role || "dialog", "aria-modal": "true", "aria-label": title, "aria-describedby": options.describedBy
        }, [head, el("div", {class: "board-dialog__body"}, [body, errorBox]), foot]);
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
            if (event.key === "Escape") { event.stopPropagation(); event.preventDefault(); api.close(); return; }
            if (event.key !== "Tab") return;
            var focusable = qa("button:not([disabled]), input:not([type=hidden]), select, textarea, [tabindex='0']", dialog);
            if (!focusable.length) return;
            var first = focusable[0], last = focusable[focusable.length - 1];
            if (event.shiftKey && doc.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && doc.activeElement === last) { event.preventDefault(); first.focus(); }
            else if (focusable.indexOf(doc.activeElement) < 0) { event.preventDefault(); first.focus(); }
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
        if (options.focus) {
            var target = options.focus(api);
            if (target) target.focus();
        } else {
            window.setTimeout(function () { focusFirst(dialog.querySelector(".board-dialog__body")); }, 0);
        }
        return api;
    }

    function confirmDialog(options) {
        return new Promise(function (resolve) {
            var settled = false;
            function settle(answer, dialog) {
                if (settled) return;
                settled = true;
                if (dialog) dialog.close();
                resolve(answer);
            }
            var dialog = openDialog(options.title, el("p", {id: "kanban-confirm-text", text: options.message}), [
                {label: "Cancelar", onClick: function (d) { settle(false, d); }},
                {label: options.confirmLabel || "Confirmar", kind: options.danger ? "danger" : "primary", onClick: function (d) { settle(true, d); }}
            ], {
                role: "alertdialog", describedBy: "kanban-confirm-text",
                focus: function (d) { return d.root.querySelector(".btn--primary, .btn--danger"); }
            });
            dialog.onClose = function () { settle(false); };
        });
    }

    // -- o quadro ------------------------------------------------------------------------------------

    function init(root, adapter) {
        if (!root) return null;
        if (root.lpsKanbanCore) return root.lpsKanbanCore;
        var lanesRoot = q("[data-kanban-lanes]", root);
        if (!lanesRoot) return null;
        adapter = adapter || {};

        var drag = null;          // {card, lane} enquanto se arrasta
        var pending = 0;          // gravações em andamento
        var wantsReload = false;  // há redesenho esperando as gravações/arrasto terminarem
        var menu = null;          // {el, anchor, width} do menu aberto
        var config = null;        // {updatePreview} enquanto o diálogo "Configurar cartões" está aberto

        function lanes() { return qa("[data-lane]", lanesRoot); }
        function bodyOf(lane) { return q("[data-lane-body]", lane); }
        function laneName(lane) { return lane.getAttribute("aria-label") || lane.getAttribute("data-lane-label") || ""; }
        function failureMessage(error, fallback) { return error && error.message ? error.message : fallback; }

        function accepts(card, lane) {
            if (lane.hasAttribute("data-lane-closed")) return false;
            var scope = lane.getAttribute("data-lane-scope") || "";
            return scope === "" || scope === (card.getAttribute("data-card-scope") || "");
        }

        function targets(card) {
            var own = card.closest("[data-lane]");
            return lanes().filter(function (lane) { return lane !== own && accepts(card, lane); });
        }

        function updateCount(lane) {
            var count = qa("[data-card]", bodyOf(lane)).length;
            var counter = q("[data-lane-count]", lane);
            if (counter) counter.textContent = String(count);
            var empty = q("[data-lane-empty]", lane);
            if (empty) empty.hidden = count > 0;
        }

        function relocate(card, body, before) {
            var active = doc.activeElement;
            var hadFocus = active && card.contains(active);
            body.insertBefore(card, before);
            if (hadFocus && doc.activeElement !== active) active.focus();  // mover o nó tira o foco dele
        }

        // -- movimento --------------------------------------------------------------------------------

        function move(card, target, options) {
            var from = card.closest("[data-lane]");
            if (!from || !target || from === target || !accepts(card, target)) return Promise.resolve(false);
            var ctx = {
                card: card, from: from, to: target, itemId: card.getAttribute("data-item-id"),
                laneKey: target.getAttribute("data-lane-key"), laneLabel: target.getAttribute("data-lane-label") || "",
                updatedAt: card.getAttribute("data-updated-at") || ""
            };
            var asked = adapter.beforeMove ? adapter.beforeMove(ctx) : true;
            if (asked === true || asked === undefined) return commit(ctx, options || {});  // sem confirmação: o cartão se mexe no mesmo instante
            if (asked && typeof asked.then === "function") {
                return asked.then(function (go) { return go ? commit(ctx, options || {}) : false; });
            }
            return asked ? commit(ctx, options || {}) : Promise.resolve(false);
        }

        function commit(ctx, options) {
            var card = ctx.card;
            var fromBody = bodyOf(ctx.from);
            var next = card.nextElementSibling;
            relocate(card, bodyOf(ctx.to), q("[data-lane-empty]", ctx.to));
            updateCount(ctx.from);
            updateCount(ctx.to);
            card.classList.add("is-saving");
            if (options.focusMenu) { var button = q("[data-card-menu]", card); if (button) button.focus(); }
            pending += 1;
            var sent;
            try { sent = Promise.resolve(adapter.move(ctx)); } catch (error) { sent = Promise.reject(error); }
            return sent.then(function (result) {
                pending -= 1;
                card.classList.remove("is-saving");
                result = result || {};
                if (result.updatedAt) card.setAttribute("data-updated-at", result.updatedAt);
                if (!result.silent) toast(result.message || ("Movido para “" + ctx.laneLabel + "”."));
                settle(result.refresh !== false);
                return true;
            }, function (error) {
                pending -= 1;
                card.classList.remove("is-saving");
                if (doc.contains(fromBody)) {  // se as raias já foram redesenhadas, o servidor é quem manda
                    relocate(card, fromBody, next && next.parentNode === fromBody ? next : q("[data-lane-empty]", ctx.from));
                    updateCount(ctx.from);
                    updateCount(ctx.to);
                }
                toast(failureMessage(error, "Não foi possível mover. Tente de novo."), "error");
                settle(!!(error && error.refresh));
                return false;
            });
        }

        // Redesenha só quando nada está em andamento: uma gravação lenta não pode ter o cartão trocado debaixo dela.
        function settle(refresh) {
            if (refresh && adapter.reload) wantsReload = true;
            if (wantsReload && pending === 0 && !drag) {
                wantsReload = false;
                reload();
            }
        }

        function reload() {
            if (!adapter.reload) return Promise.resolve();
            var asked;
            try { asked = Promise.resolve(adapter.reload()); } catch (error) { asked = Promise.reject(error); }
            return asked.then(redraw, function (error) {
                toast(failureMessage(error, "Não foi possível atualizar as raias. Recarregue a página."), "error");
            });
        }

        function redraw(markup) {
            if (typeof markup !== "string") return;
            closeMenu(false);
            var active = doc.activeElement;
            var focus = null;
            if (active && root.contains(active) && active !== root) {
                var owner = active.closest("[data-card]");
                var lane = active.closest("[data-lane]");
                focus = {
                    itemId: owner ? owner.getAttribute("data-item-id") : "",
                    part: active.matches("[data-card-menu]") ? "menu" : (active.matches("[data-card-title]") ? "title" : ""),
                    laneKey: lane ? lane.getAttribute("data-lane-key") : ""
                };
            }
            var scrolls = {};
            lanes().forEach(function (lane) {
                var body = bodyOf(lane);
                if (body && body.scrollTop) scrolls[lane.getAttribute("data-lane-key")] = body.scrollTop;
            });
            var left = root.scrollLeft;
            var page = window.pageYOffset;

            lanesRoot.innerHTML = markup;

            root.scrollLeft = left;
            lanes().forEach(function (lane) {
                var top = scrolls[lane.getAttribute("data-lane-key")];
                if (top && bodyOf(lane)) bodyOf(lane).scrollTop = top;
            });
            if (Math.abs(window.pageYOffset - page) > 1) window.scrollTo(window.pageXOffset, page);
            if (focus) restoreFocus(focus);
            if (config) config.updatePreview();
        }

        function restoreFocus(focus) {
            var target = null;
            if (focus.itemId) {
                var card = q('[data-card][data-item-id="' + focus.itemId + '"]', lanesRoot);
                if (card) target = (focus.part === "menu" && q("[data-card-menu]", card)) || q("[data-card-title]", card) || q("[data-card-menu]", card);
            }
            if (!target && focus.laneKey) {  // o filtro tirou o cartão da tela: o foco vai para a raia dele
                var lane = lanes().filter(function (candidate) { return candidate.getAttribute("data-lane-key") === focus.laneKey; })[0];
                target = lane && q("[data-lane-title]", lane);
                if (target) target.setAttribute("tabindex", "-1");
            }
            if (target && target.focus) target.focus();
        }

        // -- renomear o título no lugar -----------------------------------------------------------------

        function startRename(card) {
            var titleEl = q("[data-card-title]", card);
            if (!titleEl || !adapter.rename) return;
            var wasEmpty = titleEl.classList.contains("is-empty");
            var previous = wasEmpty ? "" : titleEl.textContent;
            inlineEdit(titleEl, {
                value: previous, maxlength: 255,
                onCommit: function (value) {
                    titleEl.textContent = value || "Sem título";
                    titleEl.classList.toggle("is-empty", !value);
                    var sent;
                    try { sent = Promise.resolve(adapter.rename({card: card, itemId: card.getAttribute("data-item-id"), title: value, previous: previous})); }
                    catch (error) { sent = Promise.reject(error); }
                    sent.then(function (result) {
                        result = result || {};
                        if (result.title !== undefined && result.title !== null) {
                            titleEl.textContent = result.title || "Sem título";
                            titleEl.classList.toggle("is-empty", !result.title);
                        }
                        if (result.updatedAt) card.setAttribute("data-updated-at", result.updatedAt);
                    }, function (error) {
                        titleEl.textContent = previous || "Sem título";
                        titleEl.classList.toggle("is-empty", !previous);
                        toast(failureMessage(error, "Não foi possível renomear. Tente de novo."), "error");
                        settle(!!(error && error.refresh));  // versão velha (409): as raias vêm do servidor
                    });
                }
            });
        }

        // -- arrastar ---------------------------------------------------------------------------------

        function clearMarks(except) {
            qa(".is-drop-target", lanesRoot).forEach(function (lane) { if (lane !== except) lane.classList.remove("is-drop-target"); });
        }

        function endDrag() {
            clearMarks(null);
            if (drag) drag.card.classList.remove("is-dragging");
            drag = null;
            settle(false);
        }

        root.addEventListener("dragstart", function (event) {
            var card = event.target.closest && event.target.closest("[data-card]");
            if (!card || card.getAttribute("draggable") !== "true") return;
            closeMenu(false);
            drag = {card: card, lane: card.closest("[data-lane]")};
            card.classList.add("is-dragging");
            if (event.dataTransfer) {
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", "card:" + card.getAttribute("data-item-id"));
            }
        });

        root.addEventListener("dragover", function (event) {
            if (!drag) return;
            var lane = event.target.closest && event.target.closest("[data-lane]");
            if (!lane) return;
            if (!accepts(drag.card, lane)) { clearMarks(null); return; }  // sem preventDefault: o cursor mostra "não pode"
            event.preventDefault();
            if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
            var mark = lane !== drag.lane ? lane : null;
            clearMarks(mark);
            if (mark) mark.classList.add("is-drop-target");
        });

        root.addEventListener("drop", function (event) {
            if (!drag) return;
            var current = drag;
            var lane = event.target.closest && event.target.closest("[data-lane]");
            event.preventDefault();
            endDrag();
            if (lane) move(current.card, lane);
        });

        root.addEventListener("dragend", endDrag);

        // -- menus ------------------------------------------------------------------------------------

        function closeMenu(restoreFocus) {
            if (!menu) return;
            var current = menu;
            menu = null;
            if (current.el.parentNode) current.el.parentNode.removeChild(current.el);
            current.anchor.removeAttribute("aria-expanded");
            if (restoreFocus && doc.contains(current.anchor)) current.anchor.focus();
        }

        /** `items`: [{heading} | {separator: true} | {label, icon, danger, onClick}]. O mesmo desenho do menu de Quadros. */
        function openMenu(anchor, items, label) {
            closeMenu(false);
            var pop = el("div", {class: "board-pop", role: "menu", "aria-label": label || "Opções"});
            var list = el("div", {class: "board-menu"});
            items.forEach(function (item) {
                if (item.separator) { list.appendChild(el("div", {class: "board-menu__sep", role: "separator"})); return; }
                if (item.heading) { list.appendChild(el("div", {class: "board-menu__label", role: "presentation", text: item.heading})); return; }
                var button = el("button", {type: "button", role: "menuitem", class: "board-menu__item" + (item.danger ? " is-danger" : "")});
                if (item.icon) button.innerHTML = icon(item.icon);
                button.appendChild(el("span", {text: item.label}));
                button.addEventListener("click", function () {
                    closeMenu(false);
                    if (item.onClick) item.onClick();
                });
                list.appendChild(button);
            });
            pop.appendChild(list);
            pop.addEventListener("keydown", function (event) {
                var buttons = qa("button", pop);
                var index = buttons.indexOf(doc.activeElement);
                var next = null;
                if (event.key === "ArrowDown") next = (index + 1) % buttons.length;
                else if (event.key === "ArrowUp") next = (index - 1 + buttons.length) % buttons.length;
                else if (event.key === "Home") next = 0;
                else if (event.key === "End") next = buttons.length - 1;
                else if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); closeMenu(true); return; }
                else if (event.key === "Tab") { closeMenu(true); return; }  // volta ao ⋯ e deixa o Tab seguir dali
                if (next === null) return;
                event.preventDefault();
                buttons[next].focus();
            });
            pop.style.left = "0px";
            pop.style.top = "0px";
            doc.body.appendChild(pop);
            placePopover(pop, anchor);
            anchor.setAttribute("aria-expanded", "true");
            menu = {el: pop, anchor: anchor, width: window.innerWidth};
            var first = q("button", pop);
            if (first) first.focus();
        }

        function openCardMenu(anchor, card) {
            var items = [];
            var destinations = card.getAttribute("draggable") === "true" ? targets(card) : [];
            if (destinations.length) {
                items.push({heading: "Mover para"});
                destinations.forEach(function (lane) {
                    items.push({label: laneName(lane), icon: "arrow-right", onClick: function () { move(card, lane, {focusMenu: true}); }});
                });
            }
            var extras = adapter.menuItems ? adapter.menuItems({card: card, itemId: card.getAttribute("data-item-id")}) || [] : [];
            if (extras.length) {
                if (items.length) items.push({separator: true});
                items = items.concat(extras);
            }
            if (!items.length) { toast("Não há ações disponíveis para este cartão.", "error"); return; }
            openMenu(anchor, items, "Opções do cartão");
        }

        root.addEventListener("click", function (event) {
            // ⋮ da raia: o anfitrião diz o que cabe no menu (`adapter.laneMenu`); sem itens, o botão não faz nada
            var laneButton = adapter.laneMenu && event.target.closest && event.target.closest("[data-lane-menu]");
            if (laneButton) {
                event.preventDefault();
                if (menu && menu.anchor === laneButton) { closeMenu(true); return; }
                var lane = laneButton.closest("[data-lane]");
                var laneItems = adapter.laneMenu({lane: lane, anchor: laneButton, laneKey: lane.getAttribute("data-lane-key")}) || [];
                if (laneItems.length) openMenu(laneButton, laneItems, "Opções da raia " + (lane.getAttribute("data-lane-label") || ""));
                return;
            }
            // "+ Adicionar": com `adapter.addCard` o anfitrião cria; sem ele o botão é um link e segue o endereço dele
            var addButton = adapter.addCard && event.target.closest && event.target.closest("[data-kanban-add]");
            if (addButton) {
                event.preventDefault();
                adapter.addCard({lane: addButton.closest("[data-lane]"), anchor: addButton});
                return;
            }
            var button = event.target.closest && event.target.closest("[data-card-menu]");
            if (button) {
                event.preventDefault();
                if (menu && menu.anchor === button) { closeMenu(true); return; }
                openCardMenu(button, button.closest("[data-card]"));
                return;
            }
            var title = event.target.closest && event.target.closest("[data-card-title]");
            if (title && title.getAttribute("role") === "textbox") {  // só o título editável (a marcação decide quem pode)
                event.preventDefault();
                startRename(title.closest("[data-card]"));
            }
        });
        root.addEventListener("keydown", function (event) {
            var title = event.target;
            if (event.key === "Enter" && title.matches && title.matches("[data-card-title][role=textbox]")) {
                event.preventDefault();
                startRename(title.closest("[data-card]"));
            }
        });
        doc.addEventListener("mousedown", function (event) {
            if (menu && !menu.el.contains(event.target) && !menu.anchor.contains(event.target)) closeMenu(false);
        });
        // Girar a tela fecha o menu (a âncora mudou de lugar); a barra do navegador do celular aparecendo/sumindo não: só a altura muda.
        window.addEventListener("resize", function () { if (menu && menu.width !== window.innerWidth) closeMenu(false); });

        // -- "Configurar cartões" ---------------------------------------------------------------------

        /** spec: {title?, controls: [{type: "check"|"select", key, label, value, choices?: [[valor, rótulo]], parse?}],
                   fieldsTitle?, fields: [{id, name}] (todos os campos possíveis), selected: [id] (os do cartão, na ordem),
                   save(change) -> Promise}. `change` = {chave: valor} ou {card_fields: [ids]} (esta, depois de uma pausa). */
        function openConfig(spec) {
            var timer = null;
            var body = el("div", {class: "kanban-config"});
            var controls = el("div", {class: "kanban-config__controls"});
            var preview = el("div", {class: "kanban-config__preview", "aria-label": "Pré-visualização do cartão"});

            function save(change) {
                var sent;
                try { sent = Promise.resolve(spec.save(change)); } catch (error) { sent = Promise.reject(error); }
                sent.then(null, function (error) { toast(failureMessage(error, "Não foi possível salvar."), "error"); });
            }
            (spec.controls || []).forEach(function (control) {
                if (control.type === "select") {
                    var select = el("select", {"aria-label": control.label});
                    control.choices.forEach(function (choice) { select.appendChild(el("option", {value: choice[0], text: choice[1]})); });
                    select.value = control.value;
                    select.addEventListener("change", function () {
                        var change = {};
                        change[control.key] = control.parse ? control.parse(select.value) : select.value;
                        save(change);
                    });
                    controls.appendChild(el("label", {class: "board-field"}, [el("span", {text: control.label}), select]));
                } else {
                    var input = el("input", {type: "checkbox"});
                    input.checked = !!control.value;
                    input.addEventListener("change", function () { var change = {}; change[control.key] = input.checked; save(change); });
                    controls.appendChild(el("label", {class: "board-field board-field--check"}, [input, el("span", {text: control.label})]));
                }
            });

            // campos do cartão: marcados primeiro, na ordem do cartão; os demais depois, na ordem em que o anfitrião os deu
            var byId = {};
            (spec.fields || []).forEach(function (field) { byId[field.id] = field; });
            var chosen = (spec.selected || []).slice();
            var rest = (spec.fields || []).map(function (field) { return field.id; }).filter(function (id) { return chosen.indexOf(id) < 0; });
            var order = chosen.concat(rest);
            var checked = {};
            chosen.forEach(function (id) { checked[id] = true; });
            var list = el("div", {class: "kanban-config__fields", role: "list"});

            function saveFields() {
                window.clearTimeout(timer);
                timer = window.setTimeout(function () { save({card_fields: order.filter(function (id) { return checked[id]; })}); }, 250);
            }
            function renderFields() {
                list.textContent = "";
                order.forEach(function (id, index) {
                    var field = byId[id];
                    if (!field) return;
                    var box = el("input", {type: "checkbox", "aria-label": "Mostrar " + field.name + " no cartão"});
                    box.checked = !!checked[id];
                    box.addEventListener("change", function () { checked[id] = box.checked; saveFields(); });
                    var up = el("button", {type: "button", class: "btn btn--ghost btn--sm", "aria-label": "Subir " + field.name, text: "↑"});
                    var down = el("button", {type: "button", class: "btn btn--ghost btn--sm", "aria-label": "Descer " + field.name, text: "↓"});
                    up.disabled = index === 0;
                    down.disabled = index === order.length - 1;
                    up.addEventListener("click", function () { order.splice(index - 1, 0, order.splice(index, 1)[0]); renderFields(); saveFields(); });
                    down.addEventListener("click", function () { order.splice(index + 1, 0, order.splice(index, 1)[0]); renderFields(); saveFields(); });
                    list.appendChild(el("div", {class: "kanban-config__field", role: "listitem"}, [
                        el("label", {}, [box, el("span", {text: field.name})]), el("span", {class: "kanban-config__move"}, [up, down])
                    ]));
                });
            }
            renderFields();
            controls.appendChild(el("p", {class: "board-pop__title", text: spec.fieldsTitle || "Campos do cartão"}));
            controls.appendChild(list);

            function updatePreview() {
                preview.textContent = "";
                preview.appendChild(el("p", {class: "board-pop__title", text: "Pré-visualização"}));
                var first = q("[data-card]", lanesRoot);
                if (!first) { preview.appendChild(el("p", {class: "board-field__hint", text: "Ainda não há cartões para mostrar."})); return; }
                var copy = first.cloneNode(true);
                copy.removeAttribute("draggable");
                copy.classList.add("is-preview");
                qa("[tabindex]", copy).forEach(function (node) { node.removeAttribute("tabindex"); });
                qa("[role=textbox]", copy).forEach(function (node) { node.removeAttribute("role"); });  // o título da prévia não é um campo
                // a pré-visualização não é editável: sai tudo o que o anfitrião usa para ligar a edição
                qa("[data-cell], [data-inline-field]", copy).forEach(function (node) {
                    node.removeAttribute("data-cell");
                    node.removeAttribute("data-inline-field");
                    node.classList.remove("is-editable");
                });
                preview.appendChild(copy);
            }
            config = {updatePreview: updatePreview};
            updatePreview();

            body.appendChild(controls);
            body.appendChild(preview);
            var dialog = openDialog(spec.title || "Configurar cartões", body, [{label: "Concluir", kind: "primary"}]);
            dialog.root.classList.add("board-dialog--wide");
            dialog.onClose = function () { window.clearTimeout(timer); config = null; };
            return dialog;
        }

        var controller = {
            move: move, reload: reload, redraw: redraw, startRename: startRename, openConfig: openConfig, openMenu: openMenu,
            updateCount: updateCount
        };
        root.lpsKanbanCore = controller;
        return controller;
    }

    window.LPSKanbanCore = {
        init: init, confirm: confirmDialog,
        ui: {el: el, toast: toast, icon: icon, openDialog: openDialog, confirm: confirmDialog, inlineEdit: inlineEdit}
    };
})();
