/* Identical short actions from the collection and from the activity workspace. */
(function () {
    "use strict";
    function targetElement(value) {
        if (!value) return null;
        if (value.charAt(0) === "#") return document.querySelector(value);
        return document.getElementById(value) || document.querySelector(value);
    }

    function applyResult(result) {
        if (!result) return false;
        var changed = false;
        if (result.remove) {
            var removable = targetElement(result.remove);
            if (removable) { removable.remove(); changed = true; }
        }
        if (result.html && result.target) {
            var target = targetElement(result.target);
            if (target) {
                var wrapper = document.createElement("template");
                wrapper.innerHTML = result.html.trim();
                var replacement = wrapper.content.firstElementChild;
                if (replacement) {
                    replacement.classList.add("lps-row-updated");
                    target.replaceWith(replacement);
                    window.setTimeout(function () { replacement.classList.remove("lps-row-updated"); }, 1900);
                    changed = true;
                }
            }
        }
        if (result.html && result.refresh_scope) {
            var scope = targetElement(result.refresh_scope);
            if (scope) { scope.innerHTML = result.html; changed = true; }
        }
        return changed;
    }

    function announce(message) {
        if (!message) return;
        var region = document.querySelector(".lps-toast-region");
        if (!region) {
            region = document.createElement("div");
            region.className = "lps-toast-region";
            region.setAttribute("role", "status");
            region.setAttribute("aria-live", "polite");
            document.body.appendChild(region);
        }
        var toast = document.createElement("div");
        toast.className = "lps-toast";
        toast.textContent = message;
        region.appendChild(toast);
        window.setTimeout(function () { toast.remove(); }, 4000);
    }

    window.LPSAjax = { applyResult: applyResult, announce: announce };

    function refreshSectorVisualOptions(sectorField) {
        var form = sectorField && sectorField.form;
        if (!form) return;
        var stage = form.querySelector("[name=stage]");
        var condition = form.querySelector("[name=condition]");
        if (!stage && !condition) return;
        var sectorId = sectorField.value;
        var domain = form.closest(".task-modal") ? "tarefa" : "demanda";
        function replaceOptions(select, data, placeholder) {
            if (!select) return;
            var current = select.value;
            select.innerHTML = "";
            var empty = document.createElement("option");
            empty.value = ""; empty.textContent = placeholder; select.appendChild(empty);
            (data.items || []).forEach(function (item) {
                var option = document.createElement("option");
                option.value = item.id; option.textContent = item.name;
                option.selected = String(item.id) === String(current);
                select.appendChild(option);
            });
            select.disabled = !sectorId;
        }
        if (!sectorId) {
            replaceOptions(stage, {items: []}, "Selecione o setor primeiro");
            replaceOptions(condition, {items: []}, "Selecione o setor primeiro");
            return;
        }
        [[stage, "etapas", "Sem etapa"], [condition, "condicoes", "Sem condição"]].forEach(function (entry) {
            if (!entry[0]) return;
            fetch("/api/setores/" + encodeURIComponent(sectorId) + "/" + entry[1] + "/?dominio=" + domain,
                {headers: {"X-Requested-With": "XMLHttpRequest"}})
                .then(function (response) { return response.ok ? response.json() : {items: []}; })
                .then(function (data) { replaceOptions(entry[0], data, entry[2]); })
                .catch(function () { replaceOptions(entry[0], {items: []}, entry[2]); });
        });
    }

    document.addEventListener("change", function (event) {
        var sectorField = event.target.closest && event.target.closest("[name=sector]");
        if (sectorField) refreshSectorVisualOptions(sectorField);
    });

    function submitFilterForm(form) {
        if (!form || form.dataset.filterSubmitting === "true") return;
        form.dataset.filterSubmitting = "true";
        if (typeof form.requestSubmit === "function") form.requestSubmit();
        else form.submit();
    }

    function setupActivityFilters(form) {
        if (!form || form.dataset.activityFiltersBound === "true") return;
        form.dataset.activityFiltersBound = "true";

        form.querySelectorAll("[data-auto-submit]").forEach(function (field) {
            field.addEventListener("change", function () { submitFilterForm(form); });
        });

    }

    document.querySelectorAll("[data-activity-filters]").forEach(setupActivityFilters);

    // As células de etapa/condição ficam dentro de tabelas com overflow-x:auto.
    // Um popup absoluto seria cortado pelo container da tabela; ao abrir,
    // posicionamos o menu em relação à janela para ele sobrepor cards, linhas
    // e demais containers sem alterar a rolagem horizontal da planilha.
    function workspaceMenuPopup(details) {
        return details && details.querySelector(".workspace-value-menu__options");
    }

    function clearWorkspaceMenuPosition(details) {
        var popup = workspaceMenuPopup(details);
        if (!popup) return;
        popup.classList.remove("is-fixed");
        popup.style.removeProperty("top");
        popup.style.removeProperty("left");
        popup.style.removeProperty("right");
        popup.style.removeProperty("width");
        var summary = details.querySelector(":scope > summary");
        if (summary) summary.setAttribute("aria-expanded", "false");
    }

    function positionWorkspaceMenu(details) {
        var popup = workspaceMenuPopup(details);
        var summary = details && details.querySelector(":scope > summary");
        if (!popup || !summary || !details.open) return;

        var rect = summary.getBoundingClientRect();
        var padding = 8;
        var width = Math.max(rect.width, 164);
        width = Math.min(width, 260, window.innerWidth - (padding * 2));

        popup.classList.add("is-fixed");
        popup.style.width = width + "px";
        popup.style.left = Math.max(
            padding,
            Math.min(rect.left, window.innerWidth - width - padding)
        ) + "px";
        popup.style.right = "auto";

        // O popup já está renderizado neste ponto, então podemos escolher o
        // lado com mais espaço e evitar que a lista fique fora da viewport.
        var popupHeight = popup.getBoundingClientRect().height;
        var below = window.innerHeight - rect.bottom - padding;
        var above = rect.top - padding;
        if (popupHeight > below && above > below) {
            popup.style.top = Math.max(padding, rect.top - popupHeight - 4) + "px";
        } else {
            popup.style.top = Math.max(
                padding,
                Math.min(window.innerHeight - popupHeight - padding, rect.bottom + 4)
            ) + "px";
        }
        summary.setAttribute("aria-expanded", "true");
    }

    function closeOtherWorkspaceMenus(current) {
        document.querySelectorAll(".workspace-value-menu[open]").forEach(function (details) {
            if (details !== current) {
                details.removeAttribute("open");
                clearWorkspaceMenuPosition(details);
            }
        });
    }

    document.addEventListener("toggle", function (event) {
        var details = event.target.closest && event.target.closest(".workspace-value-menu");
        if (!details) return;
        if (details.open) {
            closeOtherWorkspaceMenus(details);
            positionWorkspaceMenu(details);
        } else {
            clearWorkspaceMenuPosition(details);
        }
    }, true);

    function repositionWorkspaceMenus() {
        document.querySelectorAll(".workspace-value-menu[open]").forEach(positionWorkspaceMenu);
    }

    window.addEventListener("resize", repositionWorkspaceMenus);
    window.addEventListener("scroll", repositionWorkspaceMenus, true);

    document.addEventListener("click", function (event) {
        if (event.target.closest && event.target.closest(".workspace-value-menu")) return;
        document.querySelectorAll(".workspace-value-menu[open]").forEach(function (details) {
            details.removeAttribute("open");
            clearWorkspaceMenuPosition(details);
        });
    });

    document.addEventListener("click", function (event) {
        var link = event.target.closest("a[data-activity-action]");
        if (!link || !window.LPSModal || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        window.LPSModal.open(link.href, {
            onSuccess: function (result) {
                if (result && result.message) announce(result.message);
                if (applyResult(result)) return;
                // Criar/editar atividade (data-activity-navigate) segue para a página que o servidor indicou;
                // as demais ações curtas só recarregam a tela em que estavam.
                if (link.hasAttribute("data-activity-navigate") && result && result.redirect_url) {
                    window.location.assign(result.redirect_url);
                } else {
                    window.location.reload();
                }
            }
        }).catch(function () {
            // The full-page form is also usable if loading the dialog fails.
            window.location.assign(link.href);
        });
    });

    document.addEventListener("submit", async function (event) {
        var choiceForm = event.target.closest("[data-workspace-choice]");
        if (choiceForm) {
            event.preventDefault();
            if (choiceForm.dataset.busy) return;
            choiceForm.dataset.busy = "true";
            var choiceButton = choiceForm.querySelector("button[type=submit]");
            if (choiceButton) choiceButton.disabled = true;
            try {
                var choiceResponse = await fetch(choiceForm.action, {
                    method: "POST",
                    headers: {"X-Requested-With": "XMLHttpRequest"},
                    body: new FormData(choiceForm)
                });
                var choiceResult = await choiceResponse.json();
                if (!choiceResponse.ok || !choiceResult.success) {
                    throw new Error(choiceResult.message || "Não foi possível atualizar este valor.");
                }
                applyResult(choiceResult);
                announce(choiceResult.message);
            } catch (error) {
                announce(error.message || "Não foi possível atualizar este valor.");
                if (choiceButton) choiceButton.disabled = false;
                delete choiceForm.dataset.busy;
            }
            return;
        }
        var form = event.target.closest("[data-editor-attachment-remove]");
        if (!form) return;
        event.preventDefault();
        if (form.dataset.busy || !window.confirm("Remover este anexo?")) return;
        var row = document.getElementById(form.dataset.attachmentRow);
        if (!row) return;
        form.dataset.busy = "true";
        var button = row.querySelector("button");
        button.disabled = true;
        var oldError = row.querySelector("[role=alert]");
        if (oldError) oldError.remove();
        try {
            var response = await fetch(form.action, {
                method: "POST", headers: {"X-Requested-With": "XMLHttpRequest"}, body: new FormData(form)
            });
            if (!(response.headers.get("content-type") || "").includes("application/json")) {
                throw new Error("Não foi possível remover o anexo. Verifique sua conexão ou sessão.");
            }
            var result = await response.json();
            if (!response.ok) throw new Error(result.error || "Não foi possível remover o anexo.");
            row.remove();
            form.remove();
        } catch (error) {
            var message = document.createElement("span");
            message.setAttribute("role", "alert");
            message.className = "errorlist";
            message.textContent = error.message;
            row.appendChild(message);
        } finally {
            delete form.dataset.busy;
            button.disabled = false;
        }
    });
})();
