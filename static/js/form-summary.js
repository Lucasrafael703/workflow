/* Resumo ao lado do formulário, atualizado enquanto a pessoa preenche.
   É só reflexo do que já está nos campos: sem JS o formulário continua
   funcionando igual, apenas sem a prévia. */
(function () {
    "use strict";

    var form = document.getElementById("activity-form");
    if (!form) return;

    var targets = {};
    Array.prototype.forEach.call(form.querySelectorAll("[data-summary]"), function (el) {
        targets[el.getAttribute("data-summary")] = {
            node: el,
            fallback: el.textContent
        };
    });

    function readable(field) {
        if (!field) return "";
        if (field.type === "radio") {
            var checked = form.querySelector("[name='" + field.name + "']:checked");
            if (!checked) return "";
            var radioLabel = checked.closest("label") || form.querySelector("label[for='" + checked.id + "']");
            return radioLabel ? radioLabel.textContent.trim() : checked.value;
        }
        if (field.tagName === "SELECT") {
            var option = field.options[field.selectedIndex];
            return option ? option.text.trim() : "";
        }
        var picker = field.closest(".person-picker");
        if (picker) {
            var label = picker.querySelector(".person-picker__label");
            return label && !label.classList.contains("muted") ? label.textContent.trim() : "";
        }
        if (field.type === "datetime-local" && field.value) {
            var parsed = new Date(field.value);
            if (!isNaN(parsed)) {
                return parsed.toLocaleString("pt-BR", {
                    day: "2-digit", month: "2-digit", year: "numeric",
                    hour: "2-digit", minute: "2-digit"
                });
            }
        }
        return field.value.trim();
    }

    function sync() {
        Object.keys(targets).forEach(function (name) {
            var field = form.querySelector("[name='" + name + "']");
            var target = targets[name];
            var value = readable(field);
            target.node.textContent = value || target.fallback;
            target.node.classList.toggle("muted", !value);
        });
    }

    form.addEventListener("input", sync);
    form.addEventListener("change", sync);
    sync();
})();
