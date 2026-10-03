/* Interações das visualizações de domínio (Demandas e Tarefas).
   O servidor continua sendo a fonte de verdade: a UI apenas antecipa o
   movimento e restaura o cartão quando a alteração não for autorizada. */
(function () {
    "use strict";

    function csrf() {
        var match = document.cookie.match(/(?:^|;\\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    function toast(board, message, error) {
        var node = board.querySelector("[data-work-board-toast]") || document.querySelector("[data-work-board-toast]");
        if (!node) return;
        node.textContent = message;
        node.className = "work-board__toast is-visible" + (error ? " is-error" : "");
        window.setTimeout(function () { node.className = "work-board__toast"; }, 3500);
    }

    function post(url, body) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrf()
            },
            body: JSON.stringify(body || {})
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (data) {
                return {ok: response.ok && data.success !== false, data: data};
            });
        });
    }

    function valueUrl(board, fieldId, itemId) {
        return "/quadros/dominio/" + board.dataset.boardId + "/campos/" + fieldId + "/itens/" + itemId + "/valor/";
    }

    function openPanel(selector, trigger) {
        var panel = document.querySelector(selector);
        if (!panel) return;
        panel.hidden = false;
        if (trigger) trigger.setAttribute("aria-expanded", "true");
        var focus = panel.querySelector("input, select, button");
        if (focus) focus.focus();
    }

    function closePanel(button) {
        var panel = button.closest(".work-card-settings");
        if (panel) panel.hidden = true;
        document.querySelectorAll("[data-work-card-settings][aria-expanded=true]").forEach(function (trigger) {
            trigger.setAttribute("aria-expanded", "false");
        });
    }

    function editor(cell) {
        var choices = cell.querySelector("template[data-work-options]");
        var input = document.createElement(choices ? "select" : "input");
        if (choices) {
            input.innerHTML = choices.innerHTML;
        } else {
            input.type = cell.className.indexOf("datetime") >= 0 ? "datetime-local" : "text";
            input.value = cell.className.indexOf("datetime") >= 0 ? (cell.dataset.value || "").slice(0, 16) : (cell.dataset.value || "");
        }
        input.className = "work-cell__editor";
        input.setAttribute("aria-label", cell.getAttribute("aria-label") || "Editar valor");
        return input;
    }

    function replaceCell(result) {
        var old = document.getElementById(result.data.target);
        if (!old || !result.data.html) return;
        var holder = old.ownerDocument.createElement("tbody");
        holder.innerHTML = "<tr>" + result.data.html + "</tr>";
        var replacement = holder.querySelector("td");
        if (replacement) old.replaceWith(replacement);
    }

    function edit(board, cell) {
        if (cell.dataset.saving || cell.querySelector(".work-cell__editor")) return;
        var original = cell.innerHTML;
        var input = editor(cell);
        var row = cell.closest("[data-work-item]");
        var restored = false;

        function restore() {
            if (restored) return;
            restored = true;
            cell.innerHTML = original;
        }

        function save() {
            if (cell.dataset.saving || restored) return;
            cell.dataset.saving = "1";
            input.disabled = true;
            post(valueUrl(board, cell.dataset.fieldId, cell.dataset.itemId), {
                value: input.value,
                updated_at: row ? row.dataset.workUpdatedAt : ""
            }).then(function (result) {
                if (!result.ok) {
                    restore();
                    toast(board, result.data.message || "Não foi possível salvar.", true);
                    return;
                }
                replaceCell(result);
                if (row && result.data.updated_at) {
                    row.dataset.workUpdatedAt = result.data.updated_at;
                    row.classList.add("is-saved");
                    window.setTimeout(function () { row.classList.remove("is-saved"); }, 1300);
                }
                toast(board, result.data.message || "Salvo.");
            }).catch(function () {
                restore();
                toast(board, "Não foi possível salvar.", true);
            }).finally(function () {
                delete cell.dataset.saving;
            });
        }

        cell.innerHTML = "";
        cell.appendChild(input);
        input.focus();
        if (input.select) input.select();
        input.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                event.preventDefault();
                restore();
            } else if (event.key === "Enter") {
                event.preventDefault();
                save();
            }
        });
        input.addEventListener("blur", save, {once: true});
    }

    function updateLane(lane, board) {
        if (!lane) return;
        var list = lane.querySelector("[data-work-card-list]");
        var count = list ? list.querySelectorAll("[data-work-card]").length : 0;
        var countNode = lane.querySelector("header span");
        if (countNode) countNode.textContent = count;
        if (!list) return;
        var empty = list.querySelector(".work-kanban__empty");
        if (!count && !empty) {
            empty = document.createElement("p");
            empty.className = "work-kanban__empty";
            empty.textContent = board && board.dataset.domain === "task" ? "Nenhuma tarefa" : "Nenhuma demanda";
            list.appendChild(empty);
        } else if (count && empty) {
            empty.remove();
        }
    }

    function clearDropTargets(board) {
        board.querySelectorAll(".work-kanban__cards.is-drop-target").forEach(function (list) {
            list.classList.remove("is-drop-target");
        });
    }

    function initDrag(board) {
        var card = null;
        var origin = null;

        board.addEventListener("dragstart", function (event) {
            var candidate = event.target.closest("[data-work-card]");
            if (!candidate) return;
            card = candidate;
            origin = {list: card.parentElement, next: card.nextElementSibling};
            card.classList.add("is-dragging");
            if (event.dataTransfer) {
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", card.dataset.itemId);
            }
        });

        board.addEventListener("dragover", function (event) {
            if (!card) return;
            var list = event.target.closest("[data-work-card-list]");
            if (!list) return;
            event.preventDefault();
            clearDropTargets(board);
            list.classList.add("is-drop-target");
            var over = event.target.closest("[data-work-card]");
            if (over && over !== card && list.contains(over)) {
                var bounds = over.getBoundingClientRect();
                list.insertBefore(card, event.clientY > bounds.top + bounds.height / 2 ? over.nextSibling : over);
            } else if (!list.contains(card)) {
                list.appendChild(card);
            }
        });

        board.addEventListener("drop", function (event) {
            if (!card) return;
            var target = event.target.closest("[data-work-card-list]");
            if (!target) return;
            event.preventDefault();
            clearDropTargets(board);
            var moving = card;
            var previous = origin;
            var fromLane = previous.list.closest("[data-work-lane]");
            var toLane = target.closest("[data-work-lane]");
            var field = board.querySelector("[data-work-group-field]");

            if (!field || !fromLane || !toLane || fromLane === toLane) {
                updateLane(fromLane, board);
                card = origin = null;
                return;
            }

            moving.classList.add("is-saving");
            updateLane(fromLane, board);
            updateLane(toLane, board);
            post(valueUrl(board, field.dataset.workGroupField, moving.dataset.itemId), {
                value: toLane.dataset.groupKey === "empty" ? "" : toLane.dataset.groupKey,
                updated_at: moving.dataset.workUpdatedAt || ""
            }).then(function (result) {
                if (!result.ok) {
                    previous.list.insertBefore(moving, previous.next && previous.next.parentElement === previous.list ? previous.next : null);
                    toast(board, result.data.message || "Movimento não permitido.", true);
                } else {
                    if (result.data.updated_at) moving.dataset.workUpdatedAt = result.data.updated_at;
                    toast(board, result.data.message || "Movimento salvo.");
                }
            }).catch(function () {
                previous.list.insertBefore(moving, previous.next && previous.next.parentElement === previous.list ? previous.next : null);
                toast(board, "Não foi possível mover o cartão.", true);
            }).finally(function () {
                moving.classList.remove("is-saving", "is-dragging");
                updateLane(fromLane, board);
                updateLane(toLane, board);
                if (card === moving) card = origin = null;
            });
        });

        board.addEventListener("dragend", function () {
            if (card) card.classList.remove("is-dragging");
            clearDropTargets(board);
        });
    }

    function moveConfiguredField(button) {
        var row = button.closest("[data-work-card-field]");
        var list = row && row.parentElement;
        if (!row || !list) return;
        if (button.dataset.workCardFieldMove === "up" && row.previousElementSibling) {
            list.insertBefore(row, row.previousElementSibling);
        } else if (button.dataset.workCardFieldMove === "down" && row.nextElementSibling) {
            list.insertBefore(row.nextElementSibling, row);
        }
    }

    function submitCardSettings(board, form) {
        var ids = Array.prototype.map.call(form.querySelectorAll("input[name=field_ids]:checked"), function (input) {
            return input.value;
        });
        if (!form.dataset.settingsUrl) {
            post(form.dataset.url, {field_ids: ids}).then(function (result) {
                if (result.ok) window.location.reload();
                else toast(board, result.data.message || "Não foi possível salvar a configuração.", true);
            }).catch(function () {
                toast(board, "Não foi possível salvar a configuração.", true);
            });
            return;
        }
        var settings = {
            show_empty: !!form.querySelector("[name=show_empty]").checked,
            show_field_names: !!form.querySelector("[name=show_field_names]").checked
        };
        var save = form.querySelector("button[type=submit]");
        if (save) save.disabled = true;
        Promise.all([
            post(form.dataset.url, {field_ids: ids}),
            post(form.dataset.settingsUrl, settings)
        ]).then(function (results) {
            var failed = results.find(function (result) { return !result.ok; });
            if (failed) {
                toast(board, failed.data.message || "Não foi possível salvar a configuração.", true);
                return;
            }
            window.location.reload();
        }).catch(function () {
            toast(board, "Não foi possível salvar a configuração.", true);
        }).finally(function () {
            if (save) save.disabled = false;
        });
    }

    function bindBoard(board) {
        board.addEventListener("click", function (event) {
            var cell = event.target.closest("[data-work-cell]");
            if (cell && !event.target.closest("a, button, input, select")) edit(board, cell);

            var hide = event.target.closest("[data-work-hide-field]");
            if (hide) {
                post("/quadros/dominio/visoes/" + board.dataset.viewId + "/campos/" + hide.dataset.workHideField + "/layout/", {is_visible: false})
                    .then(function (result) { if (result.ok) window.location.reload(); });
            }
        });
        board.addEventListener("keydown", function (event) {
            var cell = event.target.closest("[data-work-cell]");
            if (cell && (event.key === "Enter" || event.key === " ")) {
                event.preventDefault();
                edit(board, cell);
            }
        });
        initDrag(board);
    }

    function bindGlobalControls() {
        document.querySelectorAll("[data-work-card-settings]").forEach(function (button) {
            button.addEventListener("click", function () { openPanel("[data-work-card-settings-panel]", button); });
        });
        document.querySelectorAll("[data-work-add-field]").forEach(function (button) {
            button.addEventListener("click", function () { openPanel("[data-work-add-field-panel]", button); });
        });
        document.querySelectorAll("[data-work-card-settings-close], [data-work-add-field-close]").forEach(function (button) {
            button.addEventListener("click", function () { closePanel(button); });
        });
        document.querySelectorAll("[data-work-card-field-move]").forEach(function (button) {
            button.addEventListener("click", function () { moveConfiguredField(button); });
        });
        document.querySelectorAll("[data-work-card-settings-form]").forEach(function (form) {
            form.addEventListener("submit", function (event) {
                event.preventDefault();
                var board = document.querySelector("[data-work-board]");
                if (board) submitCardSettings(board, form);
            });
        });
        document.querySelectorAll("[data-work-add-field-form]").forEach(function (form) {
            form.addEventListener("submit", function (event) {
                event.preventDefault();
                var board = document.querySelector("[data-work-board]");
                var button = form.querySelector("button[type=submit]");
                if (button) button.disabled = true;
                post(form.dataset.url, {label: form.elements.label.value, type: form.elements.type.value})
                    .then(function (result) {
                        if (result.ok) window.location.reload();
                        else if (board) toast(board, result.data.message || "Não foi possível adicionar o campo.", true);
                    })
                    .catch(function () { if (board) toast(board, "Não foi possível adicionar o campo.", true); })
                    .finally(function () { if (button) button.disabled = false; });
            });
        });
        document.querySelectorAll("[data-work-group-by]").forEach(function (select) {
            select.addEventListener("change", function () {
                post(select.dataset.url, {group_by: select.value}).then(function (result) {
                    if (result.ok) window.location.reload();
                    else {
                        var board = document.querySelector("[data-work-board]");
                        if (board) toast(board, result.data.message || "Não foi possível alterar o agrupamento.", true);
                    }
                });
            });
        });
        document.addEventListener("keydown", function (event) {
            if (event.key !== "Escape") return;
            document.querySelectorAll("[data-work-card-settings-panel], [data-work-add-field-panel]").forEach(function (panel) {
                panel.hidden = true;
            });
        });
    }

    function init() {
        document.querySelectorAll("[data-work-board]").forEach(bindBoard);
        bindGlobalControls();
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
}());
