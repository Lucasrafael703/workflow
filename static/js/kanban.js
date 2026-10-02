/* Quadro Kanban de Demandas e de Tarefas (por setor). JavaScript progressivo: sem ele os filtros (details +
   "Aplicar") e os links continuam funcionando; com ele o quadro fica leve.

   O que este script faz: filtros que se aplicam ao escolher, menus e popovers, arrastar cartão entre etapas
   (grava SÓ a etapa), criar demanda na própria coluna, limite de coluna, abrir a gaveta ao clicar no cartão e
   manter cartões e contadores em dia depois de cada ação. Quem valida e grava é sempre o servidor. */
(function () {
    "use strict";

    var SENTINEL = "999999999";
    var config = document.getElementById("kanban-config");
    var board = document.querySelector("[data-kanban-board]");
    var toolbar = document.querySelector("[data-kanban-toolbar]");

    function csrfToken() {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        if (match) return match[1];
        var field = document.querySelector("input[name=csrfmiddlewaretoken]");
        return field ? field.value : "";
    }

    function announce(message) {
        if (message && window.LPSAjax && typeof window.LPSAjax.announce === "function") window.LPSAjax.announce(message);
    }

    function request(url, options) {
        options = options || {};
        options.headers = Object.assign({"X-Requested-With": "XMLHttpRequest"}, options.headers || {});
        return fetch(url, options).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (data) {
                if (!response.ok || data.success === false) {
                    var error = new Error(data.message || "Não foi possível concluir a ação.");
                    error.data = data;
                    throw error;
                }
                return data;
            });
        });
    }

    function post(url, fields) {
        var body = new FormData();
        Object.keys(fields || {}).forEach(function (key) { body.append(key, fields[key]); });
        return request(url, {method: "POST", headers: {"X-CSRFToken": csrfToken()}, body: body});
    }

    function urlFor(template, id) { return template.replace(SENTINEL, id); }

    /* -- Barra de filtros e menus ------------------------------------------------ */

    function closeAll(selector, except) {
        document.querySelectorAll(selector + "[open]").forEach(function (node) {
            if (node !== except && !(except && node.contains(except))) node.removeAttribute("open");
        });
    }

    function submitToolbar() {
        if (!toolbar) return;
        if (typeof toolbar.requestSubmit === "function") toolbar.requestSubmit(); else toolbar.submit();
    }

    function initToolbar() {
        if (!toolbar) return;
        toolbar.addEventListener("change", function (event) {
            if (event.target.matches("[data-kanban-sector]")) { submitToolbar(); return; }
            var pop = event.target.closest("[data-kanban-pop][data-autosubmit]");
            if (pop) submitToolbar();
        });
        document.querySelectorAll("[data-kanban-pop]").forEach(function (pop) {
            pop.addEventListener("toggle", function () {
                if (pop.open) closeAll("[data-kanban-pop]", pop);
            });
        });
    }

    document.addEventListener("click", function (event) {
        // Clicou fora de um popover da barra ou de um menu "•••": fecha.
        if (!event.target.closest("[data-kanban-pop]")) closeAll("[data-kanban-pop]");
        var menu = event.target.closest("[data-kanban-menu]");
        closeAll("[data-kanban-menu]", menu);
    });
    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") return;
        closeAll("[data-kanban-pop]");
        closeAll("[data-kanban-menu]");
    });

    if (!config || !board) { initToolbar(); return; }
    initToolbar();

    var domain = config.dataset.domain;
    var noun = config.dataset.noun || "item";
    var sectorId = config.dataset.sectorId;

    /* -- Colunas e contadores ------------------------------------------------------ */

    function columnOf(node) { return node && node.closest("[data-kanban-column]"); }
    function cardsIn(column) { return column.querySelectorAll("[data-kanban-card]"); }

    function refreshColumn(column, keep) {
        if (!column || !column.isConnected) return;
        var count = cardsIn(column).length;
        var limit = parseInt(column.dataset.limit || "", 10);
        var counter = column.querySelector("[data-column-count]");
        if (counter) {
            counter.dataset.count = count;
            counter.textContent = limit ? count + " de " + limit : String(count);
            counter.classList.toggle("is-over", !!limit && count > limit);
            if (limit) counter.title = "Limite da coluna: " + limit; else counter.removeAttribute("title");
        }
        var empty = column.querySelector("[data-column-empty]");
        if (empty) empty.hidden = count > 0;
        // "Sem etapa" não é uma etapa: some quando não sobra ninguém para classificar.
        if (!keep && column.hasAttribute("data-unassigned") && count === 0) column.remove();
    }

    function columnForStage(stageId) {
        return board.querySelector('[data-kanban-column][data-stage-id="' + stageId + '"]');
    }

    function htmlToCard(html) {
        var holder = document.createElement("div");
        holder.innerHTML = html.trim();
        return holder.querySelector("[data-kanban-card]");
    }

    function findCard(itemId) {
        return board.querySelector('[data-kanban-card][data-item-id="' + itemId + '"]');
    }

    /* Troca o cartão pelo HTML novo e, se a etapa mudou, leva para a coluna certa. */
    function applyCard(itemId, html, stageId) {
        var fresh = htmlToCard(html);
        if (!fresh) return;
        var old = findCard(itemId);
        var fromColumn = old ? columnOf(old) : null;
        var target = stageId ? columnForStage(stageId) : null;
        fresh.classList.add("is-updated");
        if (old && (!target || target === fromColumn)) {
            old.replaceWith(fresh);
        } else if (target) {
            if (old) old.remove();
            target.querySelector("[data-dropzone]").insertBefore(fresh, target.querySelector("[data-column-empty]"));
        } else if (old) {
            old.replaceWith(fresh);
        }
        refreshColumn(fromColumn);
        refreshColumn(columnOf(fresh));
    }

    function removeCard(itemId) {
        var card = findCard(itemId);
        if (!card) return;
        var column = columnOf(card);
        card.remove();
        refreshColumn(column);
    }

    /* Depois de uma ação feita fora do quadro (gaveta, menu): pergunta ao servidor como o cartão está agora. */
    function refreshCard(itemId) {
        return request(urlFor(config.dataset.cardUrl, itemId) + window.location.search)
            .then(function (data) {
                if (!data.visible) removeCard(itemId);
                else applyCard(itemId, data.card_html, data.stage_id);
            })
            .catch(function () { /* o quadro fica como está; a próxima carga corrige */ });
    }

    document.addEventListener("lps:workflow-changed", function (event) {
        var detail = event.detail || {};
        if (detail.domain !== domain || !detail.response || !detail.response.card_html) return;
        applyCard(detail.itemId, detail.response.card_html, detail.response.stage_id);
    });

    /* -- Arrastar entre etapas ------------------------------------------------------ */

    var dragged = null;
    var origin = null;

    function clearDropHighlight() {
        board.querySelectorAll(".kanban-dropzone--active").forEach(function (zone) { zone.classList.remove("kanban-dropzone--active"); });
    }

    board.addEventListener("dragstart", function (event) {
        var card = event.target.closest && event.target.closest("[data-kanban-card]");
        if (!card || card.getAttribute("draggable") !== "true") return;
        dragged = card;
        origin = {parent: card.parentNode, next: card.nextSibling, column: columnOf(card)};
        card.classList.add("is-dragging");
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = "move";
            try { event.dataTransfer.setData("text/plain", card.dataset.itemId); } catch (error) { /* navegadores antigos */ }
        }
    });

    board.addEventListener("dragend", function () {
        if (dragged) dragged.classList.remove("is-dragging");
        clearDropHighlight();
        if (!dragged || !dragged.dataset.saving) { dragged = null; origin = null; }
    });

    board.addEventListener("dragover", function (event) {
        if (!dragged) return;
        var column = columnOf(event.target);
        // "Sem etapa" só recebe de volta o que não pode ser classificado: nunca é destino.
        if (!column || column.hasAttribute("data-unassigned")) return;
        event.preventDefault();
        if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
        clearDropHighlight();
        var zone = column.querySelector("[data-dropzone]");
        zone.classList.add("kanban-dropzone--active");
        var over = event.target.closest && event.target.closest("[data-kanban-card]");
        if (over && over !== dragged && zone.contains(over)) {
            var bounds = over.getBoundingClientRect();
            zone.insertBefore(dragged, event.clientY > bounds.top + bounds.height / 2 ? over.nextSibling : over);
        } else if (!zone.contains(dragged)) {
            zone.insertBefore(dragged, zone.querySelector("[data-column-empty]"));
        }
    });

    board.addEventListener("drop", function (event) {
        if (!dragged) return;
        var column = columnOf(event.target);
        if (!column || column.hasAttribute("data-unassigned")) return;
        event.preventDefault();
        clearDropHighlight();
        var card = dragged;
        var back = origin;
        var targetStage = column.dataset.stageId;
        if (back.column === column) { refreshColumn(column); dragged = null; origin = null; return; }
        card.dataset.saving = "1";
        card.classList.add("is-saving");
        refreshColumn(back.column, true);
        refreshColumn(column, true);
        post(urlFor(config.dataset.setStageUrl, card.dataset.itemId), {stage_id: targetStage})
            .then(function (data) {
                announce(data.message);
                var fresh = htmlToCard(data.card_html);
                if (fresh) { fresh.classList.add("is-updated"); card.replaceWith(fresh); }
            })
            .catch(function (error) {
                announce(error.message);
                // Volta para onde estava: o servidor recusou.
                back.parent.insertBefore(card, back.next && back.next.parentNode === back.parent ? back.next : null);
                card.classList.remove("is-saving");
            })
            .then(function () {
                delete card.dataset.saving;
                refreshColumn(back.column);
                refreshColumn(column);
                if (dragged === card) { dragged = null; origin = null; }
            });
    });

    /* -- Gaveta ao clicar no cartão ------------------------------------------------- */

    var drawerItemId = null;
    var drawerSeen = false;

    function openDrawer(itemId) {
        if (!window.LPSDrawer) return false;
        drawerItemId = itemId;
        drawerSeen = false;
        window.LPSDrawer.open(urlFor(config.dataset.drawerUrl, itemId));
        return true;
    }

    // Quando a gaveta fecha, o cartão pode ter mudado (condição, etapa, conclusão): relê só ele.
    new MutationObserver(function () {
        if (!drawerItemId) return;
        if (document.querySelector(".drawer-backdrop")) { drawerSeen = true; return; }
        if (!drawerSeen) return;
        var id = drawerItemId;
        drawerItemId = null;
        drawerSeen = false;
        refreshCard(id);
    }).observe(document.body, {childList: true});

    board.addEventListener("click", function (event) {
        var opener = event.target.closest("[data-open-drawer]");
        if (opener) {
            if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            var card = opener.closest("[data-kanban-card]");
            closeAll("[data-kanban-menu]");
            if (card && openDrawer(card.dataset.itemId)) event.preventDefault();
            return;
        }
        // Clique no corpo do cartão (fora de botões, links e menus) também abre a gaveta.
        var body = event.target.closest("[data-kanban-card]");
        if (body && !event.target.closest("a, button, summary, details, input, select, textarea, label")) {
            openDrawer(body.dataset.itemId);
        }
    });

    /* -- Ações dos menus ------------------------------------------------------------ */

    function copyText(text) {
        function fallback() {
            var area = document.createElement("textarea");
            area.value = text;
            area.style.position = "fixed";
            area.style.opacity = "0";
            document.body.appendChild(area);
            area.select();
            try { document.execCommand("copy"); } catch (error) { /* sem permissão */ }
            area.remove();
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text).catch(fallback);
        }
        fallback();
        return Promise.resolve();
    }

    board.addEventListener("click", function (event) {
        var copy = event.target.closest("[data-copy-text]");
        if (copy) {
            copyText(copy.dataset.copyText).then(function () { announce("Copiado."); });
            closeAll("[data-kanban-menu]");
            return;
        }
        var action = event.target.closest("[data-kanban-post]");
        if (action) {
            var card = action.closest("[data-kanban-card]");
            closeAll("[data-kanban-menu]");
            action.disabled = true;
            request(action.dataset.url, {method: "POST", headers: {"X-CSRFToken": csrfToken()}})
                .then(function (data) { announce(data.message || "Pronto."); })
                .catch(function (error) { announce(error.message); })
                .then(function () { if (card) refreshCard(card.dataset.itemId); });
        }
    });

    // Ações com janela (cancelar, bloquear, mover de setor...): ao concluir, o quadro recarrega no mesmo lugar.
    board.addEventListener("click", function (event) {
        var link = event.target.closest("a[data-activity-action], a[data-new-item]");
        if (!link || !window.LPSModal) return;
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        event.stopPropagation();
        closeAll("[data-kanban-menu]");
        window.LPSModal.open(link.getAttribute("href"), {onSuccess: function () { window.location.reload(); }});
    }, true);

    // O botão "Nova tarefa" do cabeçalho também abre em janela e recarrega o quadro.
    document.querySelectorAll("a.js-new-task").forEach(function (link) {
        link.addEventListener("click", function (event) {
            if (!window.LPSModal) return;
            event.preventDefault();
            window.LPSModal.open(link.getAttribute("href"), {onSuccess: function () { window.location.reload(); }});
        });
    });

    /* -- Criar demanda na coluna ---------------------------------------------------- */

    function openInlineCreate(column) {
        var zone = column.querySelector("[data-dropzone]");
        var existing = zone.querySelector(".kanban-inline-create");
        if (existing) { existing.querySelector("input").focus(); return; }
        var box = document.createElement("div");
        box.className = "kanban-inline-create";
        var input = document.createElement("input");
        input.type = "text";
        input.maxLength = 200;
        input.placeholder = "Nome da " + noun;
        input.setAttribute("aria-label", "Nome da " + noun);
        var hint = document.createElement("p");
        hint.className = "kanban-inline-create__hint";
        hint.textContent = "Enter para criar · Esc para cancelar";
        box.appendChild(input);
        box.appendChild(hint);
        zone.insertBefore(box, zone.firstChild);
        input.focus();

        function cancel() { box.remove(); }
        input.addEventListener("keydown", function (event) {
            if (event.key === "Escape") { cancel(); return; }
            if (event.key !== "Enter") return;
            event.preventDefault();
            var title = input.value.trim();
            if (!title) { cancel(); return; }
            box.classList.add("is-saving");
            input.disabled = true;
            post(config.dataset.createUrl, {title: title, stage_id: column.dataset.stageId, sector_id: sectorId})
                .then(function (data) {
                    announce(data.message);
                    box.remove();
                    var fresh = htmlToCard(data.card_html);
                    var target = (data.stage_id && columnForStage(data.stage_id)) || column;
                    if (fresh) {
                        fresh.classList.add("is-updated");
                        var targetZone = target.querySelector("[data-dropzone]");
                        targetZone.insertBefore(fresh, targetZone.firstChild);
                    }
                    refreshColumn(target);
                })
                .catch(function (error) {
                    announce(error.message);
                    box.classList.remove("is-saving");
                    input.disabled = false;
                    input.focus();
                });
        });
        input.addEventListener("blur", function () {
            if (!input.disabled && !input.value.trim()) setTimeout(cancel, 120);
        });
    }

    board.addEventListener("click", function (event) {
        var trigger = event.target.closest("[data-inline-create]");
        if (!trigger) return;
        event.preventDefault();
        closeAll("[data-kanban-menu]");
        openInlineCreate(columnOf(trigger));
    });

    /* -- Limite da coluna ----------------------------------------------------------- */

    function openLimitForm(column) {
        document.querySelectorAll(".kanban-limit-pop").forEach(function (old) { old.remove(); });
        var pop = document.createElement("div");
        pop.className = "workflow-pop kanban-limit-pop";
        var form = document.createElement("form");
        form.className = "kanban-limit-form";
        var label = document.createElement("label");
        label.textContent = "Máximo de itens nesta etapa";
        var input = document.createElement("input");
        input.type = "number";
        input.min = "1";
        input.max = "999";
        input.value = column.dataset.limit || "";
        input.placeholder = "Sem limite";
        label.appendChild(input);
        var note = document.createElement("p");
        note.className = "kanban-inline-create__hint";
        note.textContent = "O limite só avisa: o contador fica vermelho quando passa. Nada é bloqueado.";
        var actions = document.createElement("div");
        actions.className = "kanban-limit-form__actions";
        var remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn btn--sm";
        remove.textContent = "Remover limite";
        var save = document.createElement("button");
        save.type = "submit";
        save.className = "btn btn--primary btn--sm";
        save.textContent = "Salvar";
        actions.appendChild(remove);
        actions.appendChild(save);
        form.appendChild(label);
        form.appendChild(note);
        form.appendChild(actions);
        pop.appendChild(form);
        document.body.appendChild(pop);
        var rect = (column.querySelector(".kanban-column__header") || column).getBoundingClientRect();
        pop.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - 300) + window.scrollX) + "px";
        pop.style.top = (rect.bottom + window.scrollY + 4) + "px";
        input.focus();

        function dismiss() {
            pop.remove();
            document.removeEventListener("mousedown", outside, true);
            document.removeEventListener("keydown", escape, true);
        }
        function outside(event) { if (!pop.contains(event.target)) dismiss(); }
        function escape(event) { if (event.key === "Escape") dismiss(); }
        document.addEventListener("mousedown", outside, true);
        document.addEventListener("keydown", escape, true);

        function send(value) {
            save.disabled = remove.disabled = true;
            post(config.dataset.limitUrl, {stage_id: column.dataset.stageId, limit: value})
                .then(function (data) {
                    column.dataset.limit = data.limit ? String(data.limit) : "";
                    refreshColumn(column);
                    announce(data.message);
                    dismiss();
                })
                .catch(function (error) {
                    announce(error.message);
                    save.disabled = remove.disabled = false;
                });
        }
        form.addEventListener("submit", function (event) { event.preventDefault(); send(input.value); });
        remove.addEventListener("click", function () { send(""); });
    }

    board.addEventListener("click", function (event) {
        var trigger = event.target.closest("[data-set-limit]");
        if (!trigger) return;
        closeAll("[data-kanban-menu]");
        openLimitForm(columnOf(trigger));
    });

    window.LPSKanban = {refreshCard: refreshCard, refreshColumn: refreshColumn, applyCard: applyCard};
})();
