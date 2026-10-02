/* Editores "de opções" da lista de Demandas (/demandas/): as células coloridas Setor, Estágio e Status.

   Plugin de static/js/activity-inline-edit.js (que traz o estado por célula, a gravação otimista com revisão, o pop-over
   único e os avisos de erro). Aqui só ficam o desenho dessas células e os pop-overs de escolha:
   - lista de botões coloridos de largura total (a cor vem do servidor, com a cor do texto já calculada), a opção atual
     marcada com ✓ e anel, busca local quando há muitas opções, teclado (setas, Enter, Esc);
   - Setor: trocar de setor E criar um setor novo (nome + cor da paleta oficial) dentro do próprio pop-over, sem janela;
     "Criar e aplicar" é uma única gravação no servidor (uma transação: se a troca for recusada, o setor não é criado);
   - trocar o setor redefine Estágio e Status para os padrões do novo setor: as duas células ficam travadas até a resposta
     e são redesenhadas com o `derived` que o servidor devolve;
   - Estágio e Status: escolher, criar uma opção nova ("Criar e aplicar") e, para quem gere as opções do setor, editar
     nome e cor ali mesmo; a edição vale para todas as linhas da página que mostram a mesma opção. Status ainda pode ser
     limpo ("Sem status"). Inativar, ordenar e definir o padrão continuam na tela de configuração (link no rodapé);
   - a segunda linha "Vencida há N dias" do Status é derivada do prazo e acompanha o Prazo editado na própria tela.
   Todo texto de usuário entra por textContent; cores só entram se forem #RRGGBB. As opções vêm sempre do servidor, no
   contexto da demanda (o cliente nunca informa o setor das etapas). */
(function () {
    "use strict";

    var HEX = /^#[0-9A-Fa-f]{6}$/;
    var DEFAULT_BG = "#94A3B8";
    var DEFAULT_TEXT = "#FFFFFF";
    var DEFAULT_SECTOR = "#3B82F6";
    var SEARCH_FROM = 8; // a partir de quantas opções aparece a busca
    var FALLBACK_PALETTE = [
        "#22C55E", "#16A34A", "#14B8A6", "#FACC15", "#F97316", "#EF4444",
        "#EC4899", "#9333EA", "#4F46E5", "#3B82F6", "#38BDF8", "#64748B"
    ].map(function (hex) { return {hex: hex, name: hex}; });

    // Textos de cada campo. "Status" é a coluna da tela; no servidor é o status manual do setor.
    var KINDS = {
        sector: {
            title: "Escolher o setor", create: "+ Novo setor", nameLabel: "Nome do setor", namePlaceholder: "Nome do setor",
            preview: "Novo setor", search: "Pesquisar setor...", loading: "Carregando setores...", empty: "Nenhum setor ativo.",
            noMatch: "Nenhum setor encontrado.", defaultColor: DEFAULT_SECTOR
        },
        stage: {
            title: "Escolher o estágio", create: "+ Novo estágio", nameLabel: "Nome do estágio", namePlaceholder: "Nome do estágio",
            preview: "Novo estágio", search: "Pesquisar estágio...", loading: "Carregando estágios...",
            empty: "Este setor ainda não tem estágios.", noMatch: "Nenhum estágio encontrado.", defaultColor: DEFAULT_BG,
            edit: "Editar estágios", editTitle: "Editar estágios", placeholder: "Sem estágio"
        },
        condition: {
            title: "Escolher o status", create: "+ Novo status", nameLabel: "Nome do status", namePlaceholder: "Nome do status",
            preview: "Novo status", search: "Pesquisar status...", loading: "Carregando status...",
            empty: "Este setor ainda não tem status.", noMatch: "Nenhum status encontrado.", defaultColor: DEFAULT_BG,
            edit: "Editar status", editTitle: "Editar status", placeholder: "Sem status", clear: "Sem status"
        }
    };

    function safeColor(value, fallback) {
        return HEX.test(String(value || "")) ? String(value).toUpperCase() : fallback;
    }

    function fold(text) {
        return String(text || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    }

    function styleVar(node, name) {
        var match = new RegExp("--" + name + "\\s*:\\s*([^;]+)").exec(node.getAttribute("style") || "");
        return match ? match[1].trim() : "";
    }

    /** Item do servidor ({id, name, color, text_color}) -> modelo da célula; `null` = sem valor. */
    function optionModel(item) {
        if (!item || item.id === null || item.id === undefined) return null;
        return {
            id: String(item.id), name: String(item.name || ""),
            color: safeColor(item.color, DEFAULT_BG), textColor: safeColor(item.text_color, DEFAULT_TEXT)
        };
    }

    function toServerItem(model) {
        return {id: model.id, name: model.name, color: model.color, text_color: model.textColor};
    }

    /** Só aceita endereço do próprio site (nunca `javascript:` nem outro domínio). */
    function localPath(url) {
        return /^\/(?!\/)[^\s]*$/.test(String(url || "")) ? String(url) : "";
    }

    function plugin(api) {
        var el = api.el, win = api.win, doc = api.doc;

        function contrastText(hex) {
            var lib = win.LPSColors;
            return lib && lib.getContrastText ? safeColor(lib.getContrastText(hex), DEFAULT_TEXT) : DEFAULT_TEXT;
        }

        function palette() {
            var lib = win.LPSColors;
            return lib && lib.PALETTE && lib.PALETTE.length ? lib.PALETTE : FALLBACK_PALETTE;
        }

        // -- células -------------------------------------------------------------------------------------

        function readSector(cell) {
            var badge = cell.querySelector(".sector-badge");
            if (!badge) return null;
            return {
                id: badge.dataset.sectorId || "", name: badge.textContent,
                color: safeColor(styleVar(badge, "sector-color"), DEFAULT_SECTOR),
                textColor: safeColor(styleVar(badge, "sector-text-color"), DEFAULT_TEXT)
            };
        }

        function renderSector(cell, model) {
            cell.textContent = "";
            if (!model) {
                cell.appendChild(el("span", {class: "demand-board__muted", text: "Sem setor"}));
                return;
            }
            cell.appendChild(el("span", {
                class: "sector-badge sector-badge--table", title: model.name, text: model.name,
                "data-sector-id": model.id,
                style: "--sector-color: " + model.color + "; --sector-text-color: " + model.textColor + ";"
            }));
        }

        function chipOf(cell) { return cell.querySelector(".demand-board__status"); }
        function nameNode(chip) { return chip.querySelector(".demand-board__status-name") || chip; }

        /** O nome pode ficar cortado em 2 linhas quando há a linha de atraso: o texto completo vai no title. */
        function syncTitle(chip) {
            var late = chip.querySelector(".demand-board__status-late");
            if (late && chip.classList.contains("has-late")) chip.setAttribute("title", nameNode(chip).textContent + " · " + late.textContent);
            else chip.removeAttribute("title");
        }

        function readOption(cell) {
            var chip = chipOf(cell);
            var id = cell.dataset.optionId || "";
            if (!chip || !id) return null;
            return {
                id: id, name: nameNode(chip).textContent,
                color: safeColor(styleVar(chip, "status-bg"), DEFAULT_BG),
                textColor: safeColor(styleVar(chip, "status-text"), DEFAULT_TEXT)
            };
        }

        function optionRenderer(placeholder) {
            return function (cell, model) {
                var chip = chipOf(cell);
                if (!chip) return;
                chip.setAttribute("style", "--status-bg:" + (model ? model.color : DEFAULT_BG) + ";--status-text:" + (model ? model.textColor : DEFAULT_TEXT) + ";");
                nameNode(chip).textContent = model ? model.name : placeholder;
                cell.dataset.optionId = model ? model.id : "";
                syncTitle(chip);
            };
        }

        /** As células de Estágio e Status da mesma linha: o servidor as redefine quando o setor muda. */
        function linkedCells(cell) {
            var row = cell.closest("tr");
            var found = [];
            ["stage", "condition"].forEach(function (field) {
                var td = row && row.querySelector('td[data-column="' + field + '"]');
                if (td) found.push({cell: td, field: field});
            });
            return found;
        }

        /** Segunda linha do Status: "Vencida há N dias", derivada do prazo (o servidor diz se está vencida e há quantos dias). */
        function setLate(row, late, days) {
            var td = row && row.querySelector('td[data-column="condition"]');
            var chip = td && chipOf(td);
            if (!chip) return;
            var small = chip.querySelector(".demand-board__status-late");
            chip.classList.toggle("has-late", !!late);
            if (!late) {
                if (small) small.parentNode.removeChild(small);
                syncTitle(chip);
                return;
            }
            if (!small) {
                small = el("small", {class: "demand-board__status-late"});
                chip.appendChild(small);
            }
            var n = parseInt(days, 10) || 1;
            small.textContent = "Vencida há " + n + " dia" + (n === 1 ? "" : "s");
            syncTitle(chip);
        }

        // -- peças dos pop-overs ------------------------------------------------------------------------

        function hint(text) { return el("p", {class: "activity-inline-popover__hint", text: text}); }

        function colorButton(model, current, onChoose) {
            var button = el("button", {
                type: "button", class: "activity-inline-color-option", "aria-current": current ? "true" : null,
                style: "--option-bg:" + model.color + ";--option-text:" + model.textColor + ";"
            }, [el("span", {class: "activity-inline-color-option__name", text: model.name})]);
            if (current) button.appendChild(el("span", {class: "activity-inline-color-option__check", "aria-hidden": "true", text: "✓"}));
            button.addEventListener("click", function () { onChoose(model); });
            return button;
        }

        function wireArrows(box) {
            box.addEventListener("keydown", function (event) {
                if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
                var items = Array.prototype.slice.call(box.querySelectorAll(".activity-inline-color-option"))
                    .filter(function (button) { return !button.parentNode.hidden; });
                if (!items.length) return;
                event.preventDefault();
                var index = items.indexOf(doc.activeElement);
                var next = event.key === "ArrowDown"
                    ? (index < items.length - 1 ? index + 1 : 0)
                    : (index > 0 ? index - 1 : items.length - 1);
                items[next].focus();
            });
        }

        function swatchGrid(initial, onPick) {
            var grid = el("div", {class: "activity-inline-swatches", role: "radiogroup", "aria-label": "Cor"});
            var buttons = [];
            var chosen = safeColor(initial, DEFAULT_BG);
            function mark() {
                buttons.forEach(function (button) { button.setAttribute("aria-checked", button.dataset.hex === chosen ? "true" : "false"); });
            }
            palette().forEach(function (entry) {
                var hex = safeColor(entry.hex, null);
                if (!hex) return;
                var swatch = el("button", {
                    type: "button", class: "activity-inline-swatch", role: "radio", "aria-checked": "false", "data-hex": hex,
                    title: entry.name, "aria-label": entry.name, style: "background:" + hex + ";"
                });
                swatch.addEventListener("click", function () { chosen = hex; mark(); onPick(hex); });
                buttons.push(swatch);
                grid.appendChild(swatch);
            });
            mark();
            return {grid: grid, buttons: buttons, get: function () { return chosen; }};
        }

        // -- abrir um pop-over de opções (Setor, Estágio, Status) ----------------------------------------

        function openEditor(field) {
            return function (cell) {
                var kind = KINDS[field];
                var box = el("div", {class: "activity-inline-popover__body"}, [hint(kind.loading)]);
                var pop = api.openPopover(cell, box, kind.title);
                wireArrows(box);
                loadList(cell, box, pop, field, true);
            };
        }

        /** Busca as opções no servidor (no contexto da demanda) e mostra a lista. `focus`: foca a opção atual. */
        function loadList(cell, box, pop, field, focus) {
            api.getJSON(cell, "optionsUrl", "campo=" + field).then(function (data) {
                if (!api.isOpen(pop)) return;
                showList(cell, box, pop, field, data, focus);
            }, function (error) {
                if (api.isOpen(pop)) api.closePopover(true);
                api.showError(error.message);
            });
        }

        function currentId(cell) {
            var model = api.stateOf(cell).model;
            return String(model ? model.id : "");
        }

        function showList(cell, box, pop, field, data, focus) {
            var kind = KINDS[field];
            var current = currentId(cell);
            var items = (data.items || []).map(optionModel).filter(Boolean);
            box.textContent = "";
            var search = null;
            var list = el("ul", {class: "activity-inline-color-list"});

            function choose(model) {
                api.closePopover(true);
                if (model && model.id === current) return;
                if (!model && !current) return;
                var form = new win.FormData();
                form.append("value", model ? model.id : "");
                api.save(cell, field, form, model);
            }
            function paint(term) {
                var needle = fold(term);
                list.textContent = "";
                if (data.allow_clear && kind.clear && !needle) {
                    var clear = {id: "", name: kind.clear, color: "#E2E8F0", textColor: "#334155"};
                    list.appendChild(el("li", {}, [colorButton(clear, !current, function () { choose(null); })]));
                }
                var shown = items.filter(function (item) { return !needle || fold(item.name).indexOf(needle) !== -1; });
                shown.forEach(function (item) {
                    list.appendChild(el("li", {}, [colorButton(item, item.id === current, choose)]));
                });
                if (!shown.length) list.appendChild(el("li", {class: "activity-inline-popover__hint", text: items.length ? kind.noMatch : kind.empty}));
            }

            if (items.length > SEARCH_FROM) {
                search = el("input", {type: "search", class: "activity-inline-popover__input", placeholder: kind.search, "aria-label": kind.search, maxlength: "60"});
                search.addEventListener("input", function () { paint(search.value); api.reposition(); });
                box.appendChild(el("div", {class: "activity-inline-popover__search"}, [search]));
            }
            paint("");
            box.appendChild(list);

            var tail = [];
            if (data.can_create) {
                var add = el("button", {type: "button", class: "activity-inline-popover__more", text: kind.create});
                add.addEventListener("click", function () { showCreateForm(cell, box, pop, field, data); });
                tail.push(add);
            }
            if (data.can_manage && kind.edit && items.length) {
                var edit = el("button", {type: "button", class: "activity-inline-popover__more", text: kind.edit});
                edit.addEventListener("click", function () { showEditList(cell, box, pop, field, data, items); });
                tail.push(edit);
            }
            var manageUrl = localPath(data.manage_url);
            if (manageUrl) {
                tail.push(el("a", {class: "activity-inline-popover__link", href: manageUrl, text: "Gerenciar estágios e status"}));
            }
            if (tail.length) box.appendChild(el("div", {class: "activity-inline-popover__tail"}, tail));
            api.reposition();
            if (focus === false) return;
            var focusTarget = search || box.querySelector('[aria-current="true"]') || box.querySelector(".activity-inline-color-option");
            if (focusTarget) focusTarget.focus();
        }

        // -- criar (setor, estágio ou status) ---------------------------------------------------------------

        function showCreateForm(cell, box, pop, field, data) {
            var kind = KINDS[field];
            box.textContent = "";
            var name = el("input", {type: "text", class: "activity-inline-popover__input", maxlength: "150", placeholder: kind.namePlaceholder, "aria-label": kind.nameLabel});
            var preview = el("span", {class: "activity-inline-preview", text: kind.preview});
            var error = el("p", {class: "activity-inline-popover__error", role: "alert", hidden: true});
            var back = el("button", {type: "button", class: "btn btn--sm", text: "Voltar"});
            var create = el("button", {type: "button", class: "btn btn--primary btn--sm", text: "Criar e aplicar"});
            var grid = swatchGrid(kind.defaultColor, function () { paintPreview(); });

            function paintPreview() {
                error.hidden = true; // a mensagem era sobre o que estava escrito antes
                var hex = grid.get();
                preview.setAttribute("style", "background:" + hex + ";color:" + contrastText(hex) + ";");
                preview.textContent = name.value.trim() || kind.preview;
            }
            function setBusy(busy) {
                [name, back, create].concat(grid.buttons).forEach(function (node) { node.disabled = busy; });
            }
            function fail(message) {
                error.textContent = message;
                error.hidden = false;
                api.reposition();
            }
            // O erro fica no próprio pop-over (nome repetido, sem permissão...) e só vira aviso global se o pop-over já
            // tiver sido fechado.
            function onFailure(failure) {
                if (!api.isOpen(pop)) return false;
                setBusy(false);
                fail(failure.message);
                name.focus();
                return true;
            }
            function onBlocked() {
                setBusy(false);
                fail("Aguarde a gravação anterior terminar.");
            }
            function submit() {
                var value = name.value.trim();
                if (!value) { fail(field === "sector" ? "Informe o nome do setor." : "Informe o nome."); name.focus(); return; }
                error.hidden = true;
                var hex = grid.get();
                setBusy(true);
                if (field === "sector") createSector(cell, value, hex, onFailure, onBlocked);
                else createOption(cell, field, value, hex, box, pop, onFailure);
            }
            back.addEventListener("click", function () { showList(cell, box, pop, field, data); });
            create.addEventListener("click", submit);
            name.addEventListener("input", paintPreview);
            name.addEventListener("keydown", function (event) { if (event.key === "Enter") { event.preventDefault(); submit(); } });

            box.appendChild(el("div", {class: "activity-inline-popover__form"}, [
                el("label", {}, [el("span", {text: kind.nameLabel}), name]),
                el("div", {class: "activity-inline-popover__field"}, [el("span", {class: "activity-inline-popover__label", text: "Cor"}), grid.grid]),
                preview, error,
                el("div", {class: "activity-inline-popover__foot"}, [back, create])
            ]));
            paintPreview();
            api.reposition();
            name.focus();
        }

        /** Uma única gravação cria o setor e o aplica à demanda (uma transação no servidor). */
        function createSector(cell, name, hex, onFailure, onBlocked) {
            var form = new win.FormData();
            form.append("new_name", name);
            form.append("new_color", hex);
            api.save(cell, "sector", form, {id: "", name: name, color: hex, textColor: contrastText(hex)}, {
                onSuccess: function () { api.closePopover(true); },
                onError: onFailure,
                onBlocked: onBlocked
            });
        }

        /** Cria a etapa/status no setor da demanda e, em seguida, a aplica à demanda pelo caminho normal de gravação. */
        function createOption(cell, field, name, hex, box, pop, onFailure) {
            var form = new win.FormData();
            form.append("campo", field);
            form.append("acao", "criar");
            form.append("name", name);
            form.append("color", hex);
            api.postJSON(cell, "optionsUrl", form).then(function (created) {
                var model = optionModel(created.item);
                if (!model) throw new Error("Não foi possível criar agora. Tente de novo.");
                var apply = new win.FormData();
                apply.append("value", model.id);
                api.save(cell, field, apply, model, {
                    onSuccess: function () { api.closePopover(true); },
                    // A opção já existe: se aplicá-la falhar, a lista é recarregada (agora com ela) e o aviso aparece.
                    onError: function () { if (api.isOpen(pop)) loadList(cell, box, pop, field, false); return false; },
                    onBlocked: function () { if (api.isOpen(pop)) loadList(cell, box, pop, field, false); }
                });
            }, function (failure) {
                if (!onFailure(failure)) api.showError(failure.message);
            });
        }

        // -- editar nome e cor das opções (quem gere as opções do setor) -----------------------------------------

        /** Propaga a opção editada a todas as células da página que a mostram (mesmo id), sem recarregar. */
        function propagate(field, model) {
            var cells = api.table.querySelectorAll('td[data-column="' + field + '"][data-option-id="' + model.id + '"]');
            Array.prototype.forEach.call(cells, function (td) {
                if (api.stateOf(td).busy) return;
                api.setConfirmed(td, field, model);
            });
        }

        function showEditList(cell, box, pop, field, data, items) {
            var kind = KINDS[field];
            box.textContent = "";
            var rows = el("div", {class: "activity-inline-edit-list"});

            items.forEach(function (original, position) {
                var item = original;
                var chosen = item.color;
                var name = el("input", {type: "text", class: "activity-inline-popover__input", maxlength: "150", value: item.name, "aria-label": "Nome de " + item.name});
                var dot = el("button", {type: "button", class: "activity-inline-edit-dot", "aria-label": "Cor de " + item.name, "aria-expanded": "false", style: "background:" + item.color + ";"});
                var save = el("button", {type: "button", class: "btn btn--sm", text: "Salvar", disabled: true});
                var error = el("p", {class: "activity-inline-popover__error", role: "alert", hidden: true});
                var grid = swatchGrid(item.color, function (hex) { chosen = hex; dot.setAttribute("style", "background:" + hex + ";"); changed(); });
                grid.grid.hidden = true;

                function changed() {
                    error.hidden = true;
                    save.disabled = name.value.trim() === item.name && chosen === item.color;
                    save.textContent = "Salvar";
                }
                function commit() {
                    if (save.disabled) return;
                    var value = name.value.trim();
                    if (!value) { error.textContent = "Informe o nome."; error.hidden = false; name.focus(); api.reposition(); return; }
                    var form = new win.FormData();
                    form.append("campo", field);
                    form.append("acao", "editar");
                    form.append("option_id", item.id);
                    form.append("name", value);
                    form.append("color", chosen);
                    save.disabled = true;
                    name.disabled = true;
                    api.postJSON(cell, "optionsUrl", form).then(function (result) {
                        var model = optionModel(result.item);
                        if (!model) throw new Error("Não foi possível salvar agora. Tente de novo.");
                        items[position] = model;
                        item = model;
                        chosen = model.color;
                        name.disabled = false;
                        name.value = model.name;
                        propagate(field, model);
                        save.textContent = "Salvo ✓";
                        save.disabled = true;
                    }, function (failure) {
                        if (!api.isOpen(pop)) { api.showError(failure.message); return; }
                        name.disabled = false;
                        save.disabled = false;
                        error.textContent = failure.message;
                        error.hidden = false;
                        api.reposition();
                    });
                }
                dot.addEventListener("click", function () {
                    grid.grid.hidden = !grid.grid.hidden;
                    dot.setAttribute("aria-expanded", grid.grid.hidden ? "false" : "true");
                    api.reposition();
                });
                name.addEventListener("input", changed);
                name.addEventListener("keydown", function (event) { if (event.key === "Enter") { event.preventDefault(); commit(); } });
                save.addEventListener("click", commit);
                rows.appendChild(el("div", {class: "activity-inline-edit-row"}, [
                    el("div", {class: "activity-inline-edit-line"}, [dot, name, save]), grid.grid, error
                ]));
            });

            var done = el("button", {type: "button", class: "btn btn--primary btn--sm", text: "Concluir"});
            done.addEventListener("click", function () {
                showList(cell, box, pop, field, Object.assign({}, data, {items: items.map(toServerItem)}), false);
            });
            box.appendChild(el("div", {class: "activity-inline-popover__form"}, [
                el("span", {class: "activity-inline-popover__label", text: kind.editTitle}), rows,
                el("div", {class: "activity-inline-popover__foot"}, [done])
            ]));
            api.reposition();
            var first = box.querySelector("input");
            if (first) first.focus();
        }

        // -- registro -----------------------------------------------------------------------------------

        function optionEditor(field) {
            return {
                read: readOption, render: optionRenderer(KINDS[field].placeholder),
                fromResponse: function (data) { return optionModel(data.display); },
                open: openEditor(field)
            };
        }

        api.registerEditor("sector", {
            read: readSector,
            render: renderSector,
            fromResponse: function (data) { return optionModel(data.display); },
            derive: function (data) {
                var derived = data.derived || {};
                var out = {};
                if ("stage" in derived) out.stage = optionModel(derived.stage);
                if ("condition" in derived) out.condition = optionModel(derived.condition);
                return out;
            },
            linked: linkedCells,
            open: openEditor("sector")
        });
        api.registerEditor("stage", optionEditor("stage"));
        api.registerEditor("condition", optionEditor("condition"));

        // O prazo editado ali mesmo muda a segunda linha do Status (derivada do prazo, nunca marcada à mão).
        api.onSaved(function (field, data, cell) {
            if (field !== "requested_deadline") return;
            var display = data.display || {};
            setLate(cell.closest("tr"), !!display.is_late, data.derived && data.derived.overdue_days);
        });
    }

    if (window.LPSInlineEdit && window.LPSInlineEdit.use) window.LPSInlineEdit.use(plugin);
    window.LPSInlineOptions = {optionModel: optionModel, safeColor: safeColor, fold: fold, localPath: localPath};
})();
