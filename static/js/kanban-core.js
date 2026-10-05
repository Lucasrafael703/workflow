/* Núcleo do Kanban (templates/kanban/*): o comportamento do Kanban de Quadros — arrastar com "Solte aqui para mover para…",
   menu "Mover para…" (a única forma em toque e no teclado), contagem e vazio da raia, desfazer quando o servidor recusa e
   redesenho que preserva rolagem e foco — sem saber nada do domínio. O servidor continua sendo a verdade: a tela antecipa
   o movimento e volta atrás com a mensagem dele.

   O que o núcleo lê da marcação (ver o cabeçalho de templates/kanban/_lanes.html):
     raia    [data-lane] [data-lane-key] [data-lane-label] [data-lane-scope] [data-lane-closed] [data-lane-body] [data-lane-empty] [data-lane-count]
     cartão  [data-card] [data-item-id] [data-card-scope] [data-updated-at] [draggable=true] [data-card-menu] [data-card-title]
   Uma raia recebe o cartão quando não é "fechada" e o escopo dela é vazio ou igual ao do cartão.

   Uso:  LPSKanbanCore.init(root, adapter)  →  {move, reload, redraw}
     root     elemento que rola na horizontal e contém `[data-kanban-lanes]`
     adapter  move(ctx)        → Promise<{message?, updatedAt?, refresh?}>; rejeita com Error(mensagem) (error.refresh = true: redesenhar)
              reload()         → Promise<string> o HTML das raias (opcional; sem ele a tela fica como o movimento otimista deixou)
              beforeMove(ctx)  → boolean | Promise<boolean> (opcional; false cancela, nada muda na tela)
     ctx      {card, from, to, itemId, laneKey, laneLabel, updatedAt}
   `LPSKanbanCore.confirm({title, message, confirmLabel})` → Promise<boolean>: a janela de confirmação do modelo (.board-dialog). */
(function () {
    "use strict";

    var doc = document;
    var ARROW = '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><use href="#i-arrow-right"></use></svg>';

    function q(selector, from) { return (from || doc).querySelector(selector); }
    function qa(selector, from) { return Array.prototype.slice.call((from || doc).querySelectorAll(selector)); }

    function node(tag, className, attrs) {
        var element = doc.createElement(tag);
        if (className) element.className = className;
        Object.keys(attrs || {}).forEach(function (name) { element.setAttribute(name, attrs[name]); });
        return element;
    }

    function toast(message, kind) {
        var area = q("[data-board-toasts]");
        if (!area || !message) return;
        var box = node("div", "board-toast" + (kind === "error" ? " is-error" : ""));
        box.textContent = message;
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

    // -- janela de confirmação (as classes são as de Quadros) ---------------------------------------

    function confirmDialog(options) {
        return new Promise(function (resolve) {
            var opener = doc.activeElement;
            var backdrop = node("div", "board-dialog-backdrop");
            var dialog = node("div", "board-dialog", {role: "alertdialog", "aria-modal": "true", "aria-label": options.title, "aria-describedby": "kanban-confirm-text"});
            var close = node("button", "board-dialog__close", {type: "button", "aria-label": "Fechar"});
            close.textContent = "×";
            var title = node("h2");
            title.textContent = options.title;
            var head = node("div", "board-dialog__head");
            head.appendChild(title);
            head.appendChild(close);
            var text = node("p", "", {id: "kanban-confirm-text"});
            text.textContent = options.message;
            var body = node("div", "board-dialog__body");
            body.appendChild(text);
            var cancel = node("button", "btn", {type: "button"});
            cancel.textContent = "Cancelar";
            var ok = node("button", "btn btn--primary", {type: "button"});
            ok.textContent = options.confirmLabel || "Confirmar";
            var foot = node("div", "board-dialog__foot");
            foot.appendChild(cancel);
            foot.appendChild(ok);
            dialog.appendChild(head);
            dialog.appendChild(body);
            dialog.appendChild(foot);
            backdrop.appendChild(dialog);

            var settled = false;
            function settle(answer) {
                if (settled) return;
                settled = true;
                doc.removeEventListener("keydown", onKey, true);
                if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
                if (opener && opener.focus && doc.contains(opener)) opener.focus();
                resolve(answer);
            }
            function onKey(event) {
                if (event.key === "Escape") { event.stopPropagation(); event.preventDefault(); settle(false); return; }
                if (event.key !== "Tab") return;
                var stops = [close, cancel, ok];
                var index = stops.indexOf(doc.activeElement);
                var next = event.shiftKey ? index - 1 : index + 1;
                event.preventDefault();
                stops[(next + stops.length) % stops.length].focus();
            }
            cancel.addEventListener("click", function () { settle(false); });
            close.addEventListener("click", function () { settle(false); });
            ok.addEventListener("click", function () { settle(true); });
            backdrop.addEventListener("mousedown", function (event) { if (event.target === backdrop) settle(false); });
            doc.addEventListener("keydown", onKey, true);
            doc.body.appendChild(backdrop);
            ok.focus();
        });
    }

    // -- o quadro ------------------------------------------------------------------------------------

    function init(root, adapter) {
        if (!root) return null;
        if (root.lpsKanbanCore) return root.lpsKanbanCore;
        var lanesRoot = q("[data-kanban-lanes]", root);
        if (!lanesRoot) return null;

        var drag = null;          // {card, lane} enquanto se arrasta
        var pending = 0;          // gravações em andamento
        var wantsReload = false;  // há redesenho esperando as gravações/arrasto terminarem
        var menu = null;          // {el, anchor} do menu "Mover para"

        function lanes() { return qa("[data-lane]", lanesRoot); }
        function bodyOf(lane) { return q("[data-lane-body]", lane); }

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
            return Promise.resolve(asked).then(function (go) { return go ? commit(ctx, options || {}) : false; });
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
                toast(result.message || ("Movido para “" + ctx.laneLabel + "”."));
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
                toast(error && error.message ? error.message : "Não foi possível mover. Tente de novo.", "error");
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
                toast(error && error.message ? error.message : "Não foi possível atualizar as raias. Recarregue a página.", "error");
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

        // -- menu "Mover para…" -----------------------------------------------------------------------

        function closeMenu(restoreFocus) {
            if (!menu) return;
            var current = menu;
            menu = null;
            if (current.el.parentNode) current.el.parentNode.removeChild(current.el);
            current.anchor.removeAttribute("aria-expanded");
            if (restoreFocus && doc.contains(current.anchor)) current.anchor.focus();
        }

        function openMenu(anchor, card) {
            closeMenu(false);
            var options = targets(card);
            if (!options.length) { toast("Não há outra raia que receba este cartão.", "error"); return; }
            var pop = node("div", "board-pop", {role: "menu", "aria-label": "Mover para"});
            var list = node("div", "board-menu");
            var heading = node("div", "board-menu__label", {role: "presentation"});
            heading.textContent = "Mover para";
            list.appendChild(heading);
            options.forEach(function (lane) {
                var item = node("button", "board-menu__item", {type: "button", role: "menuitem"});
                item.innerHTML = ARROW;
                var label = node("span");
                label.textContent = lane.getAttribute("aria-label") || lane.getAttribute("data-lane-label") || "";
                item.appendChild(label);
                item.addEventListener("click", function () {
                    closeMenu(false);
                    move(card, lane, {focusMenu: true});
                });
                list.appendChild(item);
            });
            pop.appendChild(list);
            pop.addEventListener("keydown", function (event) {
                var items = qa("button", pop);
                var index = items.indexOf(doc.activeElement);
                var next = null;
                if (event.key === "ArrowDown") next = (index + 1) % items.length;
                else if (event.key === "ArrowUp") next = (index - 1 + items.length) % items.length;
                else if (event.key === "Home") next = 0;
                else if (event.key === "End") next = items.length - 1;
                else if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); closeMenu(true); return; }
                else if (event.key === "Tab") { closeMenu(true); return; }  // volta ao ⋯ e deixa o Tab seguir dali
                if (next === null) return;
                event.preventDefault();
                items[next].focus();
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

        root.addEventListener("click", function (event) {
            var button = event.target.closest && event.target.closest("[data-card-menu]");
            if (!button) return;
            event.preventDefault();
            if (menu && menu.anchor === button) { closeMenu(true); return; }
            openMenu(button, button.closest("[data-card]"));
        });
        doc.addEventListener("mousedown", function (event) {
            if (menu && !menu.el.contains(event.target) && !menu.anchor.contains(event.target)) closeMenu(false);
        });
        // Girar a tela fecha o menu (a âncora mudou de lugar); a barra do navegador do celular aparecendo/sumindo não: só a altura muda.
        window.addEventListener("resize", function () { if (menu && menu.width !== window.innerWidth) closeMenu(false); });

        var controller = {move: move, reload: reload, redraw: redraw};
        root.lpsKanbanCore = controller;
        return controller;
    }

    window.LPSKanbanCore = {init: init, confirm: confirmDialog};
})();
