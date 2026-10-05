/* Telas de acesso: usuário numa página só e edição de grupos.
 *
 * O servidor é quem decide (a página funciona sem este script, só sem as ajudas): aqui ficam as
 * ajudas de tela — escolher um grupo marca as telas, a prévia do menu muda na hora, o que for
 * diferente do grupo ganha "Ajuste individual" e dá para voltar ao padrão.
 */
(function () {
    "use strict";

    var root = document.querySelector("[data-access-editor]");
    var configEl = document.getElementById("access-config");
    if (!root) return;

    var config = {screens: [], sections: [], groups: {}, orgScope: "org", mode: "group"};
    if (configEl) {
        try { config = JSON.parse(configEl.textContent); } catch (error) { /* usa o padrão */ }
    }

    var RANK = {none: 0, ver: 1, editar: 2};
    var screensByKey = {};
    config.screens.forEach(function (screen) { screensByKey[screen.key] = screen; });

    var isUser = config.mode === "user";
    var locked = !root.querySelector("[data-bulk]");
    var rows = Array.prototype.slice.call(root.querySelectorAll(".access-row"));
    var scopeSelect = root.querySelector("[data-scope]");
    var scopeTouched = false;

    function rank(level) { return RANK[level] || 0; }

    function rowLevel(row) {
        var checked = row.querySelector("input[type=radio]:checked");
        return checked ? checked.value : "none";
    }

    function rowFloor(row) { return row.getAttribute("data-floor") || "none"; }

    function setLevel(row, level) {
        var screen = screensByKey[row.getAttribute("data-screen")];
        if (level === "editar" && screen && !screen.canEdit) level = "ver";
        if (rank(level) < rank(rowFloor(row))) level = rowFloor(row);
        var radio = row.querySelector("input[type=radio][value=" + level + "]");
        if (radio) radio.checked = true;
    }

    function applyFloor(row, floor) {
        row.setAttribute("data-floor", floor);
        Array.prototype.forEach.call(row.querySelectorAll("input[type=radio]"), function (radio) {
            var disabled = locked || rank(radio.value) < rank(floor);
            radio.disabled = disabled;
            var label = radio.closest(".seg__opt");
            if (label) label.classList.toggle("is-disabled", disabled);
        });
    }

    function currentScope() { return scopeSelect ? scopeSelect.value : config.orgScope; }

    /* --- Recalcula tudo o que depende dos níveis ------------------------------------------- */

    function refresh() {
        var total = 0, viewOnly = 0, individual = 0;
        var limited = [];
        var levels = {};

        rows.forEach(function (row) {
            var key = row.getAttribute("data-screen");
            var level = rowLevel(row);
            var screen = screensByKey[key] || {};
            levels[key] = level;
            if (level !== "none") total += 1;
            if (level === "ver" && screen.canEdit) viewOnly += 1;

            var isIndividual = isUser && rank(level) > rank(rowFloor(row));
            if (isIndividual) individual += 1;
            row.classList.toggle("is-individual", isIndividual);
            var badge = row.querySelector("[data-individual-badge]");
            if (badge) badge.hidden = !isIndividual;
            var reset = row.querySelector("[data-reset]");
            if (reset) reset.hidden = !isIndividual;

            if (isUser && level !== "none" && screen.needsOrg && screen.needsOrg[level] && currentScope() !== config.orgScope) {
                limited.push(key);
            }
        });

        setCount("total", total);
        setCount("view", viewOnly);
        setCount("individual", individual);
        renderPreview(levels, limited);
        renderScopeWarning(limited);
    }

    function setCount(name, value) {
        Array.prototype.forEach.call(root.querySelectorAll("[data-count=" + name + "]"), function (el) {
            el.textContent = value;
        });
    }

    function renderPreview(levels, limited) {
        var box = root.querySelector("[data-menu-preview]");
        if (!box) return;
        box.textContent = "";
        var any = false;
        config.sections.forEach(function (section) {
            var items = config.screens.filter(function (screen) {
                return screen.section === section.key && levels[screen.key] && levels[screen.key] !== "none";
            });
            if (!items.length) return;
            any = true;
            var title = document.createElement("div");
            title.className = "menu-preview__title";
            title.textContent = section.name;
            box.appendChild(title);
            items.forEach(function (screen) {
                var item = document.createElement("div");
                item.className = "menu-preview__item";
                var name = document.createElement("span");
                name.textContent = screen.name;
                item.appendChild(name);
                var tag = null;
                if (limited.indexOf(screen.key) !== -1) {
                    item.classList.add("is-limited");
                    tag = "só com a organização inteira";
                } else if (levels[screen.key] === "ver" && screen.canEdit) {
                    tag = "só ver";
                }
                if (tag) {
                    var badge = document.createElement("span");
                    badge.className = "menu-preview__tag";
                    badge.textContent = tag;
                    item.appendChild(badge);
                }
                box.appendChild(item);
            });
        });
        if (!any) {
            var empty = document.createElement("p");
            empty.className = "menu-preview__empty";
            empty.textContent = "Nenhuma tela liberada.";
            box.appendChild(empty);
        }
    }

    function renderScopeWarning(limited) {
        var box = root.querySelector("[data-scope-warning]");
        if (!box) return;
        if (!limited.length) { box.hidden = true; return; }
        var names = limited.map(function (key) { return screensByKey[key].name; });
        box.querySelector("[data-scope-warning-text]").textContent =
            "Estas telas só funcionam quando o acesso vale para a organização inteira: " + names.join(", ") + ".";
        box.hidden = false;
    }

    /* --- Eventos das telas ------------------------------------------------------------------ */

    root.addEventListener("change", function (event) {
        var target = event.target;
        if (!target || !target.name) return;

        if (target.name === "group") {
            chooseGroup(target.value);
        } else if (target.name === "scope") {
            scopeTouched = true;
            refresh();
        } else if (target.name.indexOf("screen_") === 0) {
            refresh();
        }
        if (target.hasAttribute("data-team")) syncTeams();
        if (target.name === "first_access") syncFirstAccess();
        root.setAttribute("data-dirty", "1");
    });

    root.addEventListener("click", function (event) {
        var bulk = event.target.closest("[data-bulk]");
        if (bulk) {
            event.preventDefault();
            var block = bulk.closest(".access-block");
            Array.prototype.forEach.call(block.querySelectorAll(".access-row"), function (row) {
                setLevel(row, bulk.getAttribute("data-bulk"));
            });
            refresh();
            root.setAttribute("data-dirty", "1");
            return;
        }
        var reset = event.target.closest("[data-reset]");
        if (reset) {
            event.preventDefault();
            var row = reset.closest(".access-row");
            setLevel(row, rowFloor(row));
            refresh();
            return;
        }
        if (event.target.closest("[data-scope-use-org]")) {
            event.preventDefault();
            if (scopeSelect) { scopeSelect.value = config.orgScope; scopeTouched = true; }
            refresh();
        }
    });

    function chooseGroup(groupId) {
        var group = config.groups[groupId];
        if (!group) return;
        rows.forEach(function (row) {
            var key = row.getAttribute("data-screen");
            var wasIndividual = rank(rowLevel(row)) > rank(rowFloor(row));
            var kept = wasIndividual ? rowLevel(row) : "none";
            applyFloor(row, group.levels[key] || "none");
            // Um ajuste individual que continua acima do novo grupo é mantido; o resto acompanha o grupo.
            setLevel(row, rank(kept) > rank(group.levels[key]) ? kept : group.levels[key]);
        });
        if (scopeSelect && !scopeTouched && !scopeSelect.disabled && scopeSelect.querySelector("option[value=" + group.scope + "]")) {
            scopeSelect.value = group.scope;
        }
        refresh();
    }

    /* --- Equipes e primeiro acesso ---------------------------------------------------------- */

    function syncTeams() {
        var table = root.querySelector("[data-team-table]");
        if (!table) return;
        var selected = [];
        Array.prototype.forEach.call(root.querySelectorAll("input[data-team]"), function (box) {
            var row = table.querySelector("[data-team-row='" + box.value + "']");
            if (row) row.hidden = !box.checked;
            if (box.checked) selected.push(box.value);
        });
        var empty = table.querySelector("[data-team-empty]");
        if (empty) empty.hidden = selected.length > 0;

        var main = table.querySelector("input[name=main_sector]:checked");
        if (!main || selected.indexOf(main.value) === -1) {
            var next = selected.length ? table.querySelector("input[name=main_sector][value='" + selected[0] + "']") : null;
            if (next) next.checked = true;
            else if (main) main.checked = false;
        }
    }

    function syncFirstAccess() {
        var fields = root.querySelector("[data-password-fields]");
        if (!fields) return;
        var chosen = root.querySelector("input[name=first_access]:checked");
        fields.hidden = !(chosen && chosen.value === "password");
    }

    /* --- Início ------------------------------------------------------------------------------ */

    if (isUser) {
        var selectedGroup = root.querySelector("input[name=group]:checked");
        var startGroup = selectedGroup && config.groups[selectedGroup.value];
        rows.forEach(function (row) {
            var key = row.getAttribute("data-screen");
            applyFloor(row, startGroup ? (startGroup.levels[key] || "none") : "none");
        });
        // Quem é novo começa com as telas do grupo; quem já existe mantém o que tem (inclusive ajustes).
        syncTeams();
        syncFirstAccess();
    }
    refresh();

    /* Aviso ao sair com alterações não salvas (edição de grupo). */
    if (root.hasAttribute("data-dirty-guard")) {
        var submitting = false;
        root.addEventListener("submit", function () { submitting = true; });
        var saveButton = document.querySelector("button[form='" + root.id + "']");
        if (saveButton) saveButton.addEventListener("click", function () { submitting = true; });
        window.addEventListener("beforeunload", function (event) {
            if (root.getAttribute("data-dirty") === "1" && !submitting) {
                event.preventDefault();
                event.returnValue = "";
            }
        });
    }
})();
