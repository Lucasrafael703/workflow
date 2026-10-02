/* Barra de filtros compartilhada por Lista, Por demanda, Kanban e Calendário. */
(function () {
    "use strict";
    var doc = window.document;

    function closeOtherPopovers(current) {
        doc.querySelectorAll("[data-workspace-popover][open]").forEach(function (popover) {
            if (popover !== current) {
                popover.removeAttribute("open");
                var summary = popover.querySelector(":scope > summary");
                if (summary) summary.setAttribute("aria-expanded", "false");
            }
        });
    }

    doc.addEventListener("toggle", function (event) {
        var popover = event.target.closest && event.target.closest("[data-workspace-popover]");
        if (!popover) return;
        var summary = popover.querySelector(":scope > summary");
        if (summary) summary.setAttribute("aria-expanded", popover.open ? "true" : "false");
        if (popover.open) closeOtherPopovers(popover);
    }, true);

    doc.addEventListener("click", function (event) {
        if (!event.target.closest("[data-workspace-popover]")) closeOtherPopovers(null);
    });

    doc.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") return;
        closeOtherPopovers(null);
    });

    doc.addEventListener("change", function (event) {
        var field = event.target.closest && event.target.closest("[data-workspace-sector]");
        if (!field || !field.form || field.form.dataset.submitting === "true") return;
        if (typeof field.form.requestSubmit === "function") field.form.requestSubmit();
        else field.form.submit();
    });

    doc.addEventListener("submit", function (event) {
        var form = event.target.closest && event.target.closest("[data-workspace-filters]");
        if (!form) return;
        if (form.dataset.submitting === "true") {
            event.preventDefault();
            return;
        }
        form.dataset.submitting = "true";
        form.querySelectorAll("button[type=submit]").forEach(function (button) { button.disabled = true; });
    });
})();
