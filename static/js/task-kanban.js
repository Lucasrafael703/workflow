// Drag-and-drop do Kanban de tarefas: mesmo padrão de static/js/queue.js,
// adaptado para múltiplos containers (uma coluna por estágio). Ao soltar,
// só atualiza Task.stage no servidor — nunca Task.status.
(function () {
    "use strict";

    var board = document.querySelector(".kanban-board");
    var config = document.getElementById("task-kanban-config");
    if (!board || !config) {
        return;
    }

    var MOVE_URL_TEMPLATE = config.getAttribute("data-move-url");
    var SENTINEL = "999999999";

    function moveUrlFor(taskId) {
        return MOVE_URL_TEMPLATE.replace(SENTINEL, taskId);
    }

    function csrfToken() {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : "";
    }

    var dragged = null;

    board.addEventListener("dragstart", function (event) {
        var card = event.target.closest(".kanban-card");
        if (!card) {
            return;
        }
        dragged = card;
        card.classList.add("is-dragging");
        event.dataTransfer.effectAllowed = "move";
    });

    board.addEventListener("dragend", function () {
        if (dragged) {
            dragged.classList.remove("is-dragging");
        }
        dragged = null;
    });

    board.addEventListener("dragover", function (event) {
        if (!dragged) {
            return;
        }
        var zone = event.target.closest("[data-drop-zone]");
        if (!zone) {
            return;
        }
        event.preventDefault();
        var card = event.target.closest(".kanban-card");
        if (card && card !== dragged && zone.contains(card)) {
            var bounds = card.getBoundingClientRect();
            var isAfter = event.clientY > bounds.top + bounds.height / 2;
            zone.insertBefore(dragged, isAfter ? card.nextSibling : card);
        } else if (!zone.contains(dragged)) {
            zone.appendChild(dragged);
        }
    });

    board.addEventListener("drop", function (event) {
        if (!dragged) {
            return;
        }
        event.preventDefault();

        var column = dragged.closest(".kanban-column");
        var taskId = dragged.getAttribute("data-task-id");
        var stageId = column ? column.getAttribute("data-stage-id") : "";

        var body = new FormData();
        body.append("stage_id", stageId || "");

        fetch(moveUrlFor(taskId), {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrfToken(),
            },
            body: body,
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("move failed");
                }
                return response.json();
            })
            .then(function () {
                document.querySelectorAll(".kanban-column").forEach(function (col) {
                    var count = col.querySelectorAll(".kanban-card").length;
                    var counter = col.querySelector(".kanban-column__count");
                    if (counter) counter.textContent = count;
                });
            })
            .catch(function () {
                window.location.reload();
            });
    });
})();
