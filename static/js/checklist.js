/* Shared by the task page and drawer; mutations never reload either surface. */
(function () {
    "use strict";

    function initIn(root) {
        root.querySelectorAll(".js-task-checklist:not([data-checklist-ready])").forEach(function (widget) {
            widget.dataset.checklistReady = "1";
            var list = widget.querySelector(".js-checklist");
            var error = widget.querySelector(".js-checklist-error");
            var form = widget.querySelector(".js-checklist-add");

            function showError(message) {
                error.textContent = message || "";
                error.hidden = !message;
            }

            function updateCount() {
                var items = list.querySelectorAll("[data-item-id]");
                var done = list.querySelectorAll(".checklist__item--done").length;
                widget.querySelector(".js-checklist-count").textContent = done + " de " + items.length + " concluídos";
                widget.querySelector(".js-checklist-empty").hidden = items.length > 0;
            }

            async function request(url, values) {
                var response;
                try {
                    response = await fetch(url, {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "X-Requested-With": "XMLHttpRequest",
                            "X-CSRFToken": widget.querySelector("[name=csrfmiddlewaretoken]").value,
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                        body: new URLSearchParams(values).toString(),
                    });
                } catch (_) {
                    throw new Error("Não foi possível confirmar o salvamento. Verifique sua conexão e confira os itens antes de tentar novamente.");
                }
                if (response.redirected || response.status === 401) {
                    throw new Error("Sua sessão expirou. Entre novamente antes de alterar o checklist.");
                }
                var data;
                try { data = await response.json(); } catch (_) {
                    throw new Error(response.status === 403
                        ? "Não foi possível autorizar a operação. Atualize a página antes de tentar novamente."
                        : "O servidor não confirmou a alteração. Confira os itens antes de tentar novamente.");
                }
                if (!response.ok || !data || data.error) {
                    throw new Error(data && data.error || "Não foi possível salvar a alteração.");
                }
                return data;
            }

            function busy(item, value) {
                item.dataset.busy = value ? "1" : "0";
                item.setAttribute("aria-busy", String(value));
                item.querySelectorAll("input, button").forEach(function (control) {
                    control.disabled = value || (control.matches(".js-checklist-toggle") && widget.dataset.canToggle !== "1");
                });
            }

            function makeItem(data) {
                var item = document.createElement("li");
                item.className = "checklist__item";
                item.dataset.itemId = data.id;
                item.dataset.toggleUrl = data.toggle_url;
                item.dataset.removeUrl = data.remove_url;
                var label = document.createElement("label");
                var checkbox = document.createElement("input");
                checkbox.type = "checkbox";
                checkbox.className = "js-checklist-toggle";
                checkbox.disabled = widget.dataset.canToggle !== "1";
                var text = document.createElement("span");
                text.textContent = data.text;
                label.append(checkbox, text);
                item.append(label);
                if (widget.dataset.canManage === "1") {
                    var remove = document.createElement("button");
                    remove.type = "button";
                    remove.className = "link-button js-checklist-remove";
                    remove.textContent = "Remover";
                    remove.setAttribute("aria-label", "Remover item: " + data.text);
                    item.append(remove);
                }
                return item;
            }

            list.addEventListener("change", async function (event) {
                var checkbox = event.target.closest(".js-checklist-toggle");
                if (!checkbox || widget.dataset.canToggle !== "1") return;
                var item = checkbox.closest("[data-item-id]");
                if (item.dataset.busy === "1") return;
                var previous = item.classList.contains("checklist__item--done");
                var requested = checkbox.checked;
                busy(item, true);
                showError("");
                try {
                    var data = await request(item.dataset.toggleUrl, { is_done: requested ? "1" : "0" });
                    if (String(data.id) !== item.dataset.itemId || data.is_done !== requested) throw new Error("O servidor não confirmou a marcação do item.");
                    checkbox.checked = data.is_done;
                    item.classList.toggle("checklist__item--done", data.is_done);
                    updateCount();
                } catch (failure) {
                    checkbox.checked = previous;
                    showError(failure.message);
                } finally { busy(item, false); }
            });

            list.addEventListener("click", async function (event) {
                var button = event.target.closest(".js-checklist-remove");
                if (!button || widget.dataset.canManage !== "1") return;
                var item = button.closest("[data-item-id]");
                if (item.dataset.busy === "1") return;
                busy(item, true);
                showError("");
                try {
                    var data = await request(item.dataset.removeUrl, {});
                    if (data.ok !== true) throw new Error("O servidor não confirmou a remoção do item.");
                    var next = item.nextElementSibling || item.previousElementSibling;
                    item.remove();
                    updateCount();
                    var focus = next ? next.querySelector(".js-checklist-remove") : form && form.querySelector("input[name=text]");
                    if (focus) focus.focus({ preventScroll: true });
                } catch (failure) { showError(failure.message); }
                finally { busy(item, false); }
            });

            if (form) form.addEventListener("submit", async function (event) {
                event.preventDefault();
                if (form.dataset.busy === "1") return;
                var input = form.querySelector("input[name=text]");
                var text = input.value.trim();
                if (!text || Array.from(text).length > 255) {
                    showError(!text ? "Escreva o texto do item." : "O item deve ter no máximo 255 caracteres.");
                    input.focus({ preventScroll: true });
                    return;
                }
                busy(form, true);
                showError("");
                var saved = false;
                try {
                    var data = await request(form.action, { text: text });
                    if (!Number.isInteger(data.id) || typeof data.text !== "string" || data.is_done !== false || !data.toggle_url || !data.remove_url) throw new Error("O servidor não confirmou a inclusão do item.");
                    list.append(makeItem(data));
                    input.value = "";
                    updateCount();
                    saved = true;
                } catch (failure) { showError(failure.message); }
                finally {
                    busy(form, false);
                    if (saved) input.focus({ preventScroll: true });
                }
            });
        });
    }

    window.LPSWidgets = window.LPSWidgets || [];
    window.LPSWidgets.push(initIn);
    initIn(document);
})();
