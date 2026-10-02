/* Ordenação discreta das configurações visuais por setor.
 * A interface só move a linha depois que o servidor confirma a nova ordem. */
(function () {
    "use strict";

    function csrfToken() {
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    function rowsFor(list, moving, target) {
        var rows = Array.prototype.slice.call(list.querySelectorAll(":scope > [data-item-id]"));
        rows = rows.filter(function (row) { return row !== moving; });
        var targetIndex = rows.indexOf(target);
        if (targetIndex < 0) rows.push(moving);
        else rows.splice(targetIndex, 0, moving);
        return rows;
    }

    document.querySelectorAll("[data-flow-reorder]").forEach(function (list) {
        var dragging = null;

        list.addEventListener("dragstart", function (event) {
            var row = event.target.closest("[data-item-id]");
            if (!row) return;
            dragging = row;
            row.classList.add("is-dragging");
            event.dataTransfer.effectAllowed = "move";
        });

        list.addEventListener("dragend", function () {
            if (dragging) dragging.classList.remove("is-dragging");
            dragging = null;
        });

        list.addEventListener("dragover", function (event) {
            if (dragging) event.preventDefault();
        });

        list.addEventListener("drop", function (event) {
            var target = event.target.closest("[data-item-id]");
            if (!dragging || !target || dragging === target) return;
            event.preventDefault();
            var proposedRows = rowsFor(list, dragging, target);
            var body = new FormData();
            proposedRows.forEach(function (row) { body.append("item_id", row.dataset.itemId); });

            fetch(list.dataset.reorderUrl, {
                method: "POST",
                body: body,
                headers: {"X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrfToken()}
            }).then(function (response) {
                return response.json().then(function (payload) {
                    if (!response.ok || !payload.success) throw new Error(payload.message || "Não foi possível salvar a ordem.");
                    list.insertBefore(dragging, target);
                    if (window.LPSAjax) window.LPSAjax.announce(payload.message);
                });
            }).catch(function (error) {
                if (window.LPSAjax) window.LPSAjax.announce(error.message || "Não foi possível salvar a ordem.");
            });
        });
    });
})();
