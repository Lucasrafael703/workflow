/* Mostrar/ocultar a senha.
   O botão nasce oculto no HTML e só aparece aqui: sem JavaScript ele não
   existe, em vez de ficar visível sem funcionar. */
(function () {
    "use strict";

    var input = document.querySelector("[data-password]");
    var toggle = document.querySelector("[data-password-toggle]");
    if (!input || !toggle) return;

    var icon = toggle.querySelector("use");
    toggle.hidden = false;

    toggle.addEventListener("click", function () {
        var hidden = input.type === "password";
        input.type = hidden ? "text" : "password";
        toggle.setAttribute("aria-label", hidden ? "Ocultar senha" : "Mostrar senha");
        if (icon) icon.setAttribute("href", hidden ? "#i-eye-off" : "#i-eye");
        input.focus();
    });
})();
