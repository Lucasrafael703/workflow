// Reordenação da fila por arrasto (doc 09 §93-96).
// O arrasto apenas preenche e envia o formulário que já existe em cada linha,
// então a tela continua funcionando sem JavaScript (campo "posição" + Mover).
(function () {
    "use strict";

    var list = document.getElementById("queue-list");
    if (!list) {
        return;
    }

    var dragged = null;

    list.addEventListener("dragstart", function (event) {
        var item = event.target.closest("li[data-entry-id]");
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
        var target = event.target.closest("li[data-entry-id]");
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

        var items = Array.prototype.slice.call(list.querySelectorAll("li[data-entry-id]"));
        var newPosition = items.indexOf(dragged) + 1;
        var form = dragged.querySelector("form.queue-move");
        if (!form || newPosition < 1) {
            return;
        }

        // O motivo é pedido depois do movimento, nunca antes (doc 09 §95).
        var reason = window.prompt(
            "Motivo da mudança de posição (opcional):",
            form.querySelector('input[name="reason"]').value || ""
        );
        if (reason === null) {
            window.location.reload();
            return;
        }

        form.querySelector('input[name="new_position"]').value = newPosition;
        form.querySelector('input[name="reason"]').value = reason;
        form.submit();
    });
})();
