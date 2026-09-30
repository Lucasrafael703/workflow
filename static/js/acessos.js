/* Telas de acesso: matriz de telas (Sem acesso / Ver / Editar), cartões de
   grupo, prévia do menu e equipes. Funciona sem JS também: o formulário é
   HTML comum; o script só deixa a experiência imediata. */
(function () {
    "use strict";

    var dataEl = document.getElementById("access-data");
    var data = dataEl ? JSON.parse(dataEl.textContent) : { sections: [], groups: {} };
    var rows = Array.prototype.slice.call(document.querySelectorAll(".screen-row[data-screen]"));
    if (!rows.length && !document.querySelector("[data-team-row]") && !document.querySelector("[data-first-access]")) {
        return;
    }

    var groupRadios = Array.prototype.slice.call(document.querySelectorAll("input[data-group]"));
    var withGroups = groupRadios.length > 0;

    function currentGroupLevels() {
        if (!withGroups) return {};
        var picked = groupRadios.filter(function (r) { return r.checked; })[0];
        if (!picked || !picked.value) return {};
        return data.groups[picked.value] || {};
    }

    function rowInputs(row) {
        return Array.prototype.slice.call(row.querySelectorAll('input[type="radio"]'));
    }

    function rowLevel(row) {
        var checked = rowInputs(row).filter(function (i) { return i.checked; })[0];
        return checked ? parseInt(checked.value, 10) : 0;
    }

    function setRowLevel(row, level) {
        var inputs = rowInputs(row);
        var values = inputs.map(function (i) { return parseInt(i.value, 10); });
        // Telas sem "Ver" (cadastros): Ver vira o nível mais alto disponível.
        if (values.indexOf(level) === -1) {
            level = level > 0 ? Math.max.apply(null, values) : 0;
        }
        inputs.forEach(function (i) { i.checked = parseInt(i.value, 10) === level; });
    }

    // Na tela de usuário, o grupo é o piso: dá para acrescentar, não tirar.
    function applyFloor() {
        if (!withGroups) return;
        var base = currentGroupLevels();
        rows.forEach(function (row) {
            var floor = base[row.dataset.screen] || 0;
            rowInputs(row).forEach(function (i) {
                var v = parseInt(i.value, 10);
                i.disabled = v < floor;
                i.parentNode.title = v < floor ? "O grupo já libera esta tela. Para tirar, escolha um grupo mais restrito." : "";
            });
            if (rowLevel(row) < floor) setRowLevel(row, floor);
            row.dataset.override = rowLevel(row) > floor ? "1" : "0";
        });
    }

    function refreshPreview() {
        var preview = document.querySelector("[data-menu-preview]");
        var on = 0, view = 0, own = 0;
        var levels = {};
        rows.forEach(function (row) {
            var l = rowLevel(row);
            levels[row.dataset.screen] = l;
            if (l > 0) on++;
            if (l === 1) view++;
            if (row.dataset.override === "1") own++;
        });
        var set = function (sel, v) { var el = document.querySelector(sel); if (el) el.textContent = v; };
        set("[data-count-on]", on);
        set("[data-count-view]", view);
        set("[data-count-own]", own);
        set("[data-count-screens]", on);
        if (!preview) return;

        preview.textContent = "";
        var any = false;
        data.sections.forEach(function (section) {
            var visible = section.screens.filter(function (s) { return levels[s.key] > 0; });
            if (!visible.length) return;
            any = true;
            var title = document.createElement("div");
            title.className = "menu-preview__section";
            title.textContent = section.name;
            preview.appendChild(title);
            visible.forEach(function (s) {
                var item = document.createElement("div");
                item.className = "menu-preview__item";
                var name = document.createElement("span");
                name.textContent = s.name;
                item.appendChild(name);
                if (levels[s.key] === 1) {
                    var tag = document.createElement("span");
                    tag.className = "menu-preview__tag";
                    tag.textContent = "só ver";
                    item.appendChild(tag);
                }
                preview.appendChild(item);
            });
        });
        if (!any) {
            var empty = document.createElement("div");
            empty.className = "menu-preview__empty";
            empty.textContent = "Nenhuma tela liberada. A pessoa verá só Início e Notificações.";
            preview.appendChild(empty);
        }
    }

    function refresh() {
        applyFloor();
        refreshPreview();
    }

    // Trocar de grupo: telas vão para o nível do grupo, mantendo o que era
    // ajuste individual acima dele.
    var lastBase = currentGroupLevels();
    groupRadios.forEach(function (radio) {
        radio.addEventListener("change", function () {
            var next = currentGroupLevels();
            rows.forEach(function (row) {
                var key = row.dataset.screen;
                var wasOverride = rowLevel(row) > (lastBase[key] || 0);
                var target = next[key] || 0;
                if (wasOverride) target = Math.max(target, rowLevel(row));
                // Destrava antes de marcar, senão o radio desabilitado não aceita.
                rowInputs(row).forEach(function (i) { i.disabled = false; });
                setRowLevel(row, target);
            });
            lastBase = next;
            refresh();
        });
    });

    rows.forEach(function (row) {
        rowInputs(row).forEach(function (i) { i.addEventListener("change", refresh); });
        var reset = row.querySelector("[data-reset]");
        if (reset) {
            reset.addEventListener("click", function () {
                setRowLevel(row, currentGroupLevels()[row.dataset.screen] || 0);
                refresh();
            });
        }
    });

    Array.prototype.slice.call(document.querySelectorAll("[data-section]")).forEach(function (block) {
        Array.prototype.slice.call(block.querySelectorAll("[data-set-all]")).forEach(function (btn) {
            btn.addEventListener("click", function () {
                var level = parseInt(btn.getAttribute("data-set-all"), 10);
                var base = currentGroupLevels();
                Array.prototype.slice.call(block.querySelectorAll(".screen-row[data-screen]")).forEach(function (row) {
                    setRowLevel(row, Math.max(level, base[row.dataset.screen] || 0));
                });
                refresh();
            });
        });
    });

    // Equipes: gestor/principal só fazem sentido para quem é da equipe.
    var teamRows = Array.prototype.slice.call(document.querySelectorAll("[data-team-row]"));
    function refreshTeams() {
        var anyMain = false, firstMember = null;
        teamRows.forEach(function (row) {
            var member = row.querySelector("[data-team-member]");
            var extras = row.querySelectorAll(".team-row__extra input");
            row.classList.toggle("is-off", !member.checked);
            Array.prototype.forEach.call(extras, function (input) {
                if (!member.checked) input.checked = false;
            });
            if (member.checked && !firstMember) firstMember = row;
            var main = row.querySelector('input[name="main_sector"]');
            if (main && main.checked) anyMain = true;
        });
        if (!anyMain && firstMember) {
            var main = firstMember.querySelector('input[name="main_sector"]');
            if (main) main.checked = true;
        }
    }
    teamRows.forEach(function (row) {
        row.querySelector("[data-team-member]").addEventListener("change", refreshTeams);
    });

    // Primeiro acesso: senha só aparece quando é para definir agora.
    var firstAccess = Array.prototype.slice.call(document.querySelectorAll("[data-first-access]"));
    var passwordBox = document.querySelector("[data-password-fields]");
    var saveButton = document.querySelector("[data-save-label]");
    function refreshFirstAccess() {
        var invite = firstAccess.some(function (r) { return r.checked && r.value === "convite"; });
        if (passwordBox) passwordBox.hidden = invite;
        if (saveButton && firstAccess.length) saveButton.textContent = invite ? "Salvar e enviar convite" : "Salvar usuário";
    }
    firstAccess.forEach(function (r) { r.addEventListener("change", refreshFirstAccess); });

    refreshTeams();
    refreshFirstAccess();
    refresh();
})();
