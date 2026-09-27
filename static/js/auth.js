/* Mostrar/ocultar senha em cada par campo+botão da página.
   O botão nasce oculto no HTML e só aparece aqui: sem JavaScript ele não
   existe, em vez de ficar visível sem funcionar. */
(function () {
    "use strict";

    var toggles = document.querySelectorAll("[data-password-toggle]");

    toggles.forEach(function (toggle) {
        var field = toggle.closest(".auth__field, .field");
        var input = field ? field.querySelector("[data-password]") : null;
        if (!input) return;

        var icon = toggle.querySelector("use");
        toggle.hidden = false;

        toggle.addEventListener("click", function () {
            var hidden = input.type === "password";
            input.type = hidden ? "text" : "password";
            toggle.setAttribute("aria-label", hidden ? "Ocultar senha" : "Mostrar senha");
            if (icon) icon.setAttribute("href", hidden ? "#i-eye-off" : "#i-eye");
            input.focus();
        });
    });
})();

/* Código de confirmação de e-mail: 6 campos que se comportam como um único
   valor — avança sozinho, aceita colar o código inteiro, Backspace volta. */
(function () {
    "use strict";

    var wrapper = document.querySelector("[data-code-input]");
    var hidden = document.querySelector("[data-code-value]");
    if (!wrapper || !hidden) return;

    var boxes = Array.prototype.slice.call(wrapper.querySelectorAll("input"));

    function sync() {
        hidden.value = boxes.map(function (box) { return box.value; }).join("");
    }

    function fill(digits, startIndex) {
        digits.split("").forEach(function (digit, offset) {
            var box = boxes[startIndex + offset];
            if (box) box.value = digit;
        });
        sync();
        var next = boxes[Math.min(startIndex + digits.length, boxes.length - 1)];
        if (next) next.focus();
    }

    boxes.forEach(function (box, index) {
        box.addEventListener("input", function () {
            box.value = box.value.replace(/\D/g, "").slice(-1);
            sync();
            if (box.value && index < boxes.length - 1) boxes[index + 1].focus();
        });

        box.addEventListener("keydown", function (event) {
            if (event.key === "Backspace" && !box.value && index > 0) {
                boxes[index - 1].focus();
            }
        });

        box.addEventListener("paste", function (event) {
            var text = (event.clipboardData || window.clipboardData).getData("text").replace(/\D/g, "");
            if (!text) return;
            event.preventDefault();
            fill(text.slice(0, boxes.length - index), index);
        });
    });

    if (boxes[0]) boxes[0].focus();
})();
