/* Editor de descrição com formatação básica: contenteditable nativo do
   navegador + document.execCommand para os 5 comandos da toolbar. O
   <textarea> escondido continua sendo o que o form realmente submete —
   este script só mantém os dois sincronizados, então a tela funciona
   normalmente mesmo se JS falhar (só perde a formatação visual ao vivo). */
(function () {
    "use strict";

    function init(root) {
        var body = root.querySelector(".rich-text__body");
        var textarea = root.querySelector("textarea");
        if (!body || !textarea) return;

        function syncToTextarea() {
            textarea.value = body.innerHTML;
        }

        body.addEventListener("input", syncToTextarea);
        body.addEventListener("blur", syncToTextarea);

        var form = root.closest("form");
        if (form) {
            form.addEventListener("submit", syncToTextarea);
        }

        root.querySelectorAll(".rich-text__btn").forEach(function (button) {
            // preventDefault no mousedown (antes do click) impede que o
            // botão roube o foco do contenteditable — sem isso, o cursor
            // "esquece" onde estava e o comando aplica sempre no início do
            // texto (um body.focus() sozinho no click não recupera a
            // posição perdida).
            button.addEventListener("mousedown", function (event) {
                event.preventDefault();
            });
            button.addEventListener("click", function () {
                var command = button.getAttribute("data-command");
                if (command === "createLink") {
                    var url = window.prompt("Endereço do link:", "https://");
                    if (!url) return;
                    document.execCommand("createLink", false, url);
                } else {
                    document.execCommand(command, false, null);
                }
                // insertUnorderedList não preserva a posição do cursor: o
                // Chrome deixa a seleção no início do texto convertido em
                // vez de manter o fim, então digitar em seguida entra antes
                // do que já existia. Move explicitamente para o fim.
                if (command === "insertUnorderedList") {
                    var range = document.createRange();
                    range.selectNodeContents(body);
                    range.collapse(false);
                    var selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                }
                syncToTextarea();
            });
        });
        root.setAttribute("data-rich-text-ready", "1");
    }

    // Ver o mesmo comentário em person-picker.js: um editor rico aberto
    // dentro de um modal injetado via LPSModal.open() só ganha vida se
    // reinicializado depois da inserção — modal.js chama initIn de novo.
    function initIn(root) {
        root.querySelectorAll("[data-rich-text]:not([data-rich-text-ready])").forEach(init);
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);

    initIn(document);
})();
