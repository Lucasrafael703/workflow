// Drag-and-drop do Kanban de atividades: mesmo padrão de static/js/task-kanban.js,
// adaptado para Activity. Ao soltar, só atualiza Activity.stage no servidor —
// nunca Activity.status.
(function () {
    "use strict";

    var board = document.querySelector(".activities-kanban-board");
    var config = document.getElementById("activity-kanban-config");
    if (!board || !config) {
        return;
    }

    var MOVE_URL_TEMPLATE = config.getAttribute("data-move-url");
    var SENTINEL = "999999999";

    function moveUrlFor(activityId) {
        return MOVE_URL_TEMPLATE.replace(SENTINEL, activityId);
    }

    function csrfToken() {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : "";
    }

    var dragged = null;

    board.addEventListener("dragstart", function (event) {
        var card = event.target.closest(".activities-kanban-card");
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
        var card = event.target.closest(".activities-kanban-card");
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

        var column = dragged.closest(".activities-kanban-column");
        var activityId = dragged.getAttribute("data-activity-id");
        var stageId = column ? column.getAttribute("data-stage-id") : "";

        var body = new FormData();
        body.append("stage_id", stageId || "");

        fetch(moveUrlFor(activityId), {
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
                document.querySelectorAll(".activities-kanban-column").forEach(function (col) {
                    var count = col.querySelectorAll(".activities-kanban-card").length;
                    var counter = col.querySelector(".activities-kanban-column__head > span:last-child");
                    if (counter) counter.textContent = count;
                });
            })
            .catch(function () {
                window.location.reload();
            });
    });
})();
