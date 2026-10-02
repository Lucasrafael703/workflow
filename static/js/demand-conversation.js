/* Interações progressivas da conversa. Publicar, reagir e responder seguem
   sendo formulários HTML normais; este arquivo só reduz atrito na escrita. */
(function () {
    "use strict";

    function fieldFor(control) {
        var form = control.closest("form");
        return form ? form.querySelector("textarea[data-conversation-textarea], textarea[name='body']") : null;
    }

    function insertAtCursor(field, text) {
        if (!field) return;
        var start = typeof field.selectionStart === "number" ? field.selectionStart : field.value.length;
        var end = typeof field.selectionEnd === "number" ? field.selectionEnd : field.value.length;
        field.value = field.value.slice(0, start) + text + field.value.slice(end);
        var cursor = start + text.length;
        field.focus();
        field.setSelectionRange(cursor, cursor);
        field.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function init() {
        document.querySelectorAll("[data-conversation-file]").forEach(function (input) {
            input.addEventListener("change", function () {
                var selector = input.getAttribute("data-file-label");
                var label = selector ? document.querySelector(selector) : null;
                if (label) label.textContent = input.files.length ? input.files[0].name : "";
            });
        });

        document.querySelectorAll("[data-conversation-mention]").forEach(function (button) {
            button.addEventListener("click", function () { insertAtCursor(fieldFor(button), "@"); });
        });
        document.querySelectorAll("[data-conversation-insert]").forEach(function (button) {
            button.addEventListener("click", function () {
                var details = button.closest("details");
                insertAtCursor(fieldFor(button), button.getAttribute("data-conversation-insert"));
                if (details) details.open = false;
            });
        });
        document.querySelectorAll("[data-conversation-link]").forEach(function (button) {
            button.addEventListener("click", function () {
                var value = window.prompt("Cole o link que deseja compartilhar:");
                if (!value) return;
                value = value.trim();
                if (value && !/^https?:\/\//i.test(value)) value = "https://" + value;
                insertAtCursor(fieldFor(button), value ? value + " " : "");
            });
        });

        document.querySelectorAll("[data-reply-toggle]").forEach(function (button) {
            button.setAttribute("aria-expanded", "false");
            button.addEventListener("click", function () {
                var form = document.getElementById(button.getAttribute("data-reply-toggle"));
                if (!form) return;
                form.hidden = !form.hidden;
                button.setAttribute("aria-expanded", String(!form.hidden));
                if (!form.hidden) {
                    var field = form.querySelector("textarea");
                    if (field) field.focus();
                }
            });
        });

        document.querySelectorAll(".conversation-composer textarea, .conversation-reply-form textarea").forEach(function (field) {
            field.addEventListener("keydown", function (event) {
                if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                    var form = field.closest("form");
                    if (form) form.requestSubmit();
                }
            });
        });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();
