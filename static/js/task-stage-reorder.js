// Reordenação dos estágios de tarefa por arrasto (Cadastros > Estágios de tarefa).
// Mesmo padrão de static/js/queue.js: ao soltar, envia a lista completa de
// IDs na nova ordem para o servidor renumerar — sem "posição" digitada.
(function () {
    "use strict";

    var list = document.getElementById("taskstage-list");
    var form = document.getElementById("taskstage-reorder-form");
    if (!list || !form) {
        return;
    }

    var dragged = null;

    list.addEventListener("dragstart", function (event) {
        var item = event.target.closest("li[data-stage-id]");
        if (!item) {
            return;
        }
        dragged = item;
        item.classList.add("is-dragging");
        event.dataTransfer.effectAllowed = "move";
    });

    list.addEventListener("dragend", function () {
        if (dragged) {
            dragged.classList.remove("is-dragging");
        }
        dragged = null;
    });

    list.addEventListener("dragover", function (event) {
        if (!dragged) {
            return;
        }
        event.preventDefault();
        var target = event.target.closest("li[data-stage-id]");
        if (!target || target === dragged) {
            return;
        }
        var bounds = target.getBoundingClientRect();
        var isAfter = event.clientY > bounds.top + bounds.height / 2;
        list.insertBefore(dragged, isAfter ? target.nextSibling : target);
    });

    list.addEventListener("drop", function (event) {
        if (!dragged) {
            return;
        }
        event.preventDefault();

        var items = Array.prototype.slice.call(list.querySelectorAll("li[data-stage-id]"));
        form.querySelectorAll('input[name="stage_id"]').forEach(function (input) {
            input.remove();
        });
        items.forEach(function (item) {
            var input = document.createElement("input");
            input.type = "hidden";
            input.name = "stage_id";
            input.value = item.getAttribute("data-stage-id");
            form.appendChild(input);
        });

        fetch(form.action, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" },
            body: new FormData(form),
        }).catch(function () {
            window.location.reload();
        });
    });
})();
