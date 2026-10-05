/* Edição inline de Demandas: clicar no dado e editá-lo ali mesmo. Vale para a LISTA (`[data-activity-list]`, uma linha por
   demanda) e para o KANBAN (`[data-kanban]`, os campos do cartão): a "superfície" decide só como LER o valor de um campo e como
   DESENHÁ-LO; pop-overs, gravação otimista, revisão por célula e erros são os mesmos. Na tabela o valor é lido do desenho; no
   cartão ele mora em `data-inline-model` (JSON) e o desenho é o do kit (templates/kanban/_fields.html).

   O servidor decide tudo (autorização, validação, auditoria, notificação): este arquivo só liga o comportamento.
   Cada gravação é otimista (a célula muda na hora) e volta ao valor confirmado, com aviso, se o servidor recusar.
   Regras de robustez:
   - cada célula tem UM modelo estruturado ({value, texto...}) e é redesenhada a partir dele, nunca por cópia de
     innerHTML; todo texto de usuário entra por textContent;
   - UMA requisição por vez em cada célula (novo clique espera) e um número de revisão: só a última operação pode
     atualizar ou reverter a célula;
   - sucesso é silencioso (só um realce curto); erro mostra um aviso curto (role="alert");
   - um único pop-over aberto, ancorado com position:fixed na camada global, que acompanha scroll e resize e fecha
     por clique fora ou Esc.
   Os endereços vêm de data-* da raiz (`data-activity-list` ou `data-kanban`), com um id fictício que `fillUrl` troca pelo real.
   Editores de campo mais ricos (Setor, Estágio e Status: static/js/activity-inline-options.js) entram por
   `LPSInlineEdit.use(plugin)`: o plugin recebe a mesma infraestrutura (estado, gravação otimista, pop-over) e registra
   o seu editor (`api.registerEditor` na tabela; `api.registerCardField` no cartão). Exporta window.LPSInlineEdit ({helpers, init, boot, use}) para os testes. */
(function () {
    "use strict";

    // ---------------------------------------------------------------------------------------------
    // Funções puras (testadas à parte)
    // ---------------------------------------------------------------------------------------------

    function fillUrl(template, sentinel, id) {
        return String(template).replace(String(sentinel), String(id));
    }

    function csrfFromCookie(cookie) {
        var match = /(?:^|;\s*)csrftoken=([^;]+)/.exec(cookie || "");
        return match ? decodeURIComponent(match[1]) : "";
    }

    function initials(name) {
        return String(name || "").trim().slice(0, 2).toUpperCase();
    }

    /** Mesma paleta do servidor (`avatar_color`: pk % 6). */
    function avatarClass(personId) {
        var n = parseInt(personId, 10);
        return "avatar--" + (isNaN(n) ? 0 : n % 6);
    }

    /** "2026-10-14" + "17:47" -> "14/10/2026 17:47" (a hora só aparece quando existe). Serve só ao otimista: o servidor devolve o texto final. */
    function deadlineText(date, time) {
        var match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(date || ""));
        if (!match) return "Sem prazo";
        return match[3] + "/" + match[2] + "/" + match[1] + (time ? " " + time : "");
    }

    var helpers = {
        fillUrl: fillUrl, csrfFromCookie: csrfFromCookie, initials: initials, avatarClass: avatarClass,
        deadlineText: deadlineText
    };
    var plugins = [];

    // ---------------------------------------------------------------------------------------------
    // Tela
    // ---------------------------------------------------------------------------------------------

    function init(table, overlay, doc, win) {
        var peopleUrl = table.dataset.peopleUrl || "";
        var active = null; // {anchor, pop}
        var states = new win.WeakMap();
        var peopleSerial = 0;
        // Editores registrados por plugins: {read(cell), render(cell, model), fromResponse(data), open(cell),
        // linked(cell) -> [{cell, field}], derive(data) -> {field: model}}
        var editors = {};
        var listeners = []; // fn(field, data, cell): depois de uma gravação aplicada (ex.: o prazo muda a linha de atraso)
        // Superfície: a tabela da Lista ou o Kanban. No cartão cada campo tem o seu editor em `cardFields` (mesmo contrato).
        var surface = table.hasAttribute("data-kanban") ? "card" : "table";
        var cardFields = {};

        function editorFor(field) {
            return surface === "card" ? (cardFields[field] || null) : (editors[field] || null);
        }

        // -- DOM ----------------------------------------------------------------------------------

        function el(tag, attrs, children) {
            var node = doc.createElement(tag);
            Object.keys(attrs || {}).forEach(function (key) {
                var value = attrs[key];
                if (value === null || value === undefined || value === false) return;
                if (key === "class") node.className = value;
                else if (key === "text") node.textContent = value;
                else node.setAttribute(key, value === true ? "" : value);
            });
            (children || []).forEach(function (child) { if (child) node.appendChild(child); });
            return node;
        }

        function stateOf(cell) {
            var state = states.get(cell);
            if (!state) {
                // células só de exibição (ex.: Estágio ao trocar o setor) têm `data-column` em vez de `data-inline-field`
                state = {busy: false, rev: 0, model: readModel(cell, cell.dataset.inlineField || cell.dataset.column)};
                states.set(cell, state);
            }
            return state;
        }

        // -- modelo de cada campo (o que a célula mostra) --------------------------------------------

        function readModel(cell, field) {
            var editor = editorFor(field);
            if (editor) return editor.read(cell);
            if (field === "title") {
                return {value: cell.dataset.inlineValue != null ? cell.dataset.inlineValue : cell.textContent};
            }
            if (field === "owner") {
                var avatar = cell.querySelector(".avatar");
                var name = cell.querySelector(".demand-board__owner > span:last-child");
                var color = avatar ? /avatar--\d+/.exec(avatar.className) : null;
                return {
                    value: cell.dataset.inlineValue || "", text: name ? name.textContent : "",
                    initials: avatar ? avatar.textContent : "", avatarClass: color ? color[0] : ""
                };
            }
            var line = cell.querySelector(".demand-board__deadline");
            var span = line ? line.querySelector("span") : null;
            return {
                date: cell.dataset.inlineDate || "", time: cell.dataset.inlineTime || "",
                text: span ? span.textContent : "", isLate: !!(line && line.classList.contains("is-late"))
            };
        }

        function render(cell, field, model) {
            var editor = editorFor(field);
            if (editor) { editor.render(cell, model); return; }
            if (field === "title") {
                cell.textContent = model.value;
                cell.dataset.inlineValue = model.value;
                cell.setAttribute("aria-label", "Editar o título da demanda " + model.value);
            } else if (field === "owner") {
                cell.textContent = "";
                if (model.value) {
                    cell.appendChild(el("span", {class: "demand-board__owner"}, [
                        el("span", {class: "avatar " + model.avatarClass, text: model.initials}),
                        el("span", {text: model.text})
                    ]));
                } else {
                    cell.appendChild(el("span", {class: "demand-board__muted", text: "Sem responsável"}));
                }
                cell.dataset.inlineValue = model.value || "";
            } else {
                var line = cell.querySelector(".demand-board__deadline");
                var span = line ? line.querySelector("span") : null;
                if (line) line.classList.toggle("is-late", !!model.isLate);
                if (span) span.textContent = model.text;
                cell.dataset.inlineDate = model.date || "";
                cell.dataset.inlineTime = model.time || "";
            }
        }

        function modelFromResponse(field, data) {
            var editor = editorFor(field);
            if (editor && editor.fromResponse) return editor.fromResponse(data);
            var display = data.display || {};
            if (field === "title") return {value: display.text != null ? display.text : data.value};
            if (field === "owner") {
                return {value: data.value || "", text: display.text, initials: display.initials, avatarClass: display.avatar_class};
            }
            var value = data.value || {};
            return {date: value.date || "", time: value.time || "", text: display.text, isLate: !!display.is_late};
        }

        // -- rede e avisos ---------------------------------------------------------------------------

        /** A linha (ou o cartão) da demanda de uma célula. */
        function rowOf(cell) { return cell.closest("[data-activity-id]"); }

        /** Endereço de uma rota da linha: o `data-*` da raiz tem um id fictício que é trocado pelo id da demanda. */
        function rowUrl(cell, attr) {
            return fillUrl(table.dataset[attr], table.dataset.inlineSentinel, rowOf(cell).dataset.activityId);
        }

        function request(cell, formData) {
            return send(rowUrl(cell, "inlineUrl"), {
                method: "POST", credentials: "same-origin",
                headers: {"X-CSRFToken": csrfFromCookie(doc.cookie), "X-Requested-With": "XMLHttpRequest"},
                body: formData
            });
        }

        /** POST de dados da linha que não é gravação de campo (ex.: criar ou editar uma opção). */
        function postJSON(cell, attr, formData) {
            return send(rowUrl(cell, attr), {
                method: "POST", credentials: "same-origin",
                headers: {"X-CSRFToken": csrfFromCookie(doc.cookie), "X-Requested-With": "XMLHttpRequest"},
                body: formData
            });
        }

        /** GET de dados da linha (ex.: opções de um pop-over). */
        function getJSON(cell, attr, query) {
            return send(rowUrl(cell, attr) + (query ? "?" + query : ""), {
                credentials: "same-origin", headers: {"X-Requested-With": "XMLHttpRequest"}
            });
        }

        function send(url, init) {
            return win.fetch(url, init).then(function (response) {
                return response.json().catch(function () { return {}; }).then(function (data) {
                    if (!response.ok || data.ok === false) {
                        var error = new Error(data.error || "Não foi possível salvar. Tente de novo.");
                        error.status = response.status;
                        throw error;
                    }
                    return data;
                });
            }, function () {
                throw new Error("Sem conexão com o servidor. Tente de novo.");
            });
        }

        function showError(message) {
            var region = doc.querySelector(".lps-toast-region");
            if (!region) {
                region = el("div", {class: "lps-toast-region", "aria-live": "polite"});
                doc.body.appendChild(region);
            }
            var toast = el("div", {class: "lps-toast is-error", role: "alert", text: message || "Não foi possível salvar."});
            region.appendChild(toast);
            win.setTimeout(function () { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 6000);
        }

        /** Grava um campo. Otimista: `optimistic` já vai para a tela; só a última revisão atualiza ou reverte.
            Campos que mexem em outras células da linha (Setor -> Estágio e Status) travam essas células até a resposta
            e as redesenham com o que o servidor devolve em `derived`. `hooks.onError(error)` devolvendo true significa
            "já avisei a pessoa" (sem aviso global); `hooks.onSuccess(data)` roda depois de aplicar a resposta;
            `hooks.onBlocked()` roda quando já há uma gravação em andamento nessas células (nada é enviado). */
        function save(cell, field, formData, optimistic, hooks) {
            hooks = hooks || {};
            var state = stateOf(cell);
            var editor = editorFor(field);
            var linked = editor && editor.linked ? editor.linked(cell) : [];
            var blocked = state.busy || linked.some(function (item) { return stateOf(item.cell).busy; });
            if (blocked) {
                if (hooks.onBlocked) hooks.onBlocked();
                return Promise.resolve(null);
            }
            var locked = [cell].concat(linked.map(function (item) { return item.cell; }));
            linked.forEach(function (item) { stateOf(item.cell).busy = true; });
            state.busy = true;
            state.rev += 1;
            var rev = state.rev;
            var confirmed = state.model;
            locked.forEach(function (node) { node.classList.add("is-saving"); node.setAttribute("aria-busy", "true"); });
            render(cell, field, optimistic);
            formData.append("field", field);
            return request(cell, formData).then(function (data) {
                if (state.rev === rev) {
                    state.model = modelFromResponse(field, data);
                    render(cell, field, state.model);
                    var derived = editor && editor.derive ? editor.derive(data) : {};
                    linked.forEach(function (item) {
                        if (derived[item.field] === undefined) return;
                        stateOf(item.cell).model = derived[item.field];
                        render(item.cell, item.field, derived[item.field]);
                    });
                    cell.classList.add("is-saved");
                    win.setTimeout(function () { cell.classList.remove("is-saved"); }, 1200);
                    listeners.forEach(function (listener) { listener(field, data, cell); });
                    if (hooks.onSuccess) hooks.onSuccess(data);
                }
                return data;
            }, function (error) {
                if (state.rev === rev) {
                    render(cell, field, confirmed);
                    cell.classList.add("is-error");
                    win.setTimeout(function () { cell.classList.remove("is-error"); }, 2500);
                }
                if (!(hooks.onError && hooks.onError(error))) showError(error.message);
                return null;
            }).then(function (result) {
                if (state.rev === rev) {
                    linked.forEach(function (item) { stateOf(item.cell).busy = false; });
                    state.busy = false;
                    locked.forEach(function (node) { node.classList.remove("is-saving"); node.removeAttribute("aria-busy"); });
                }
                return result;
            });
        }

        // -- pop-over único ---------------------------------------------------------------------------

        function place(anchor, pop) {
            var rect = anchor.getBoundingClientRect();
            // medir sempre de um canto conhecido: perto da borda direita o espaço restante espremeria a largura
            // (o pop-over é `position: fixed` e encolhe para caber), e ele ficaria com a margem errada ao ser recolocado
            pop.style.left = "0px";
            pop.style.top = "0px";
            var width = pop.offsetWidth, height = pop.offsetHeight;
            var margin = 8;
            var left = rect.left, top = rect.bottom + 4;
            if (left + width > win.innerWidth - margin) left = win.innerWidth - width - margin;
            if (top + height > win.innerHeight - margin) {
                var above = rect.top - height - 4;
                top = above >= margin ? above : Math.max(margin, win.innerHeight - height - margin);
            }
            pop.style.left = Math.max(margin, left) + "px";
            pop.style.top = Math.max(margin, top) + "px";
        }

        function closePopover(restoreFocus) {
            if (!active) return;
            var current = active;
            active = null;
            if (current.pop.parentNode) current.pop.parentNode.removeChild(current.pop);
            current.anchor.removeAttribute("aria-expanded");
            current.anchor.classList.remove("is-editing");
            if (restoreFocus && doc.contains(current.anchor)) current.anchor.focus();
        }

        function openPopover(anchor, content, label) {
            closePopover(false);
            var pop = el("div", {class: "activity-inline-popover", role: "dialog", "aria-label": label}, [content]);
            // medir de um canto conhecido: a largura não pode ser espremida pelo espaço à direita da célula
            pop.style.left = "0px";
            pop.style.top = "0px";
            overlay.appendChild(pop);
            place(anchor, pop);
            anchor.setAttribute("aria-expanded", "true");
            anchor.classList.add("is-editing");
            active = {anchor: anchor, pop: pop};
            var first = pop.querySelector("input, button");
            if (first) first.focus();
            return pop;
        }

        function reposition() {
            if (!active) return;
            if (!doc.contains(active.anchor)) { closePopover(false); return; }
            place(active.anchor, active.pop);
        }

        // -- editor de título (na própria célula) -----------------------------------------------------

        function openTitleEditor(cell) {
            var state = stateOf(cell);
            var original = state.model.value;
            var input = el("input", {type: "text", class: "activity-inline-text-input", maxlength: "200", "aria-label": "Título da demanda"});
            input.value = original;
            cell.textContent = "";
            cell.classList.add("is-editing");
            cell.appendChild(input);
            input.focus();
            input.select();
            var finished = false;

            function finish(commit, fromBlur) {
                if (finished) return;
                var value = input.value.trim();
                if (commit && !value) {
                    // título vazio nunca salva: no Enter continua editando (avisando); sair do campo só desfaz
                    if (!fromBlur) { input.setAttribute("aria-invalid", "true"); input.focus(); return; }
                    commit = false;
                }
                finished = true;
                cell.classList.remove("is-editing");
                if (!commit || value === original) { render(cell, "title", state.model); cell.focus(); return; }
                var data = new win.FormData();
                data.append("value", value);
                save(cell, "title", data, {value: value}).then(function () { cell.focus(); });
            }
            input.addEventListener("keydown", function (event) {
                if (event.key === "Enter") { event.preventDefault(); finish(true); }
                else if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); finish(false); }
            });
            input.addEventListener("blur", function () { finish(true, true); });
        }

        // -- editor de responsável ----------------------------------------------------------------------

        function openOwnerEditor(cell) {
            var state = stateOf(cell);
            var search = el("input", {type: "search", class: "activity-inline-popover__input", placeholder: "Pesquisar pessoa...", "aria-label": "Pesquisar pessoa", maxlength: "60"});
            var list = el("ul", {class: "activity-inline-popover__list"});
            var timer = null;

            function renderPeople(results) {
                list.textContent = "";
                if (!results.length) list.appendChild(el("li", {class: "activity-inline-popover__hint", text: "Ninguém encontrado."}));
                results.forEach(function (person) {
                    var current = String(person.id) === String(state.model.value);
                    var button = el("button", {type: "button", class: "activity-inline-popover__option", "aria-current": current ? "true" : null}, [
                        el("span", {class: "avatar " + avatarClass(person.id), text: initials(person.name)}),
                        el("span", {class: "activity-inline-popover__name", text: person.name}),
                        current ? el("span", {class: "activity-inline-popover__check", "aria-hidden": "true", text: "✓"}) : null
                    ]);
                    button.addEventListener("click", function () {
                        closePopover(true);
                        if (current) return;
                        var data = new win.FormData();
                        data.append("value", person.id);
                        save(cell, "owner", data, {
                            value: String(person.id), text: person.name, initials: initials(person.name), avatarClass: avatarClass(person.id)
                        });
                    });
                    list.appendChild(el("li", {}, [button]));
                });
            }
            function load(term) {
                peopleSerial += 1;
                var mine = peopleSerial;
                win.fetch(peopleUrl + "?q=" + encodeURIComponent(term), {credentials: "same-origin", headers: {"X-Requested-With": "XMLHttpRequest"}})
                    .then(function (response) { return response.json(); })
                    .then(function (data) { if (mine === peopleSerial && active) renderPeople(data.results || []); })
                    .catch(function () {
                        if (mine !== peopleSerial || !active) return;
                        list.textContent = "";
                        list.appendChild(el("li", {class: "activity-inline-popover__hint", text: "Não foi possível buscar agora."}));
                    });
            }
            search.addEventListener("input", function () {
                win.clearTimeout(timer);
                timer = win.setTimeout(function () { load(search.value.trim()); }, 250);
            });
            var box = el("div", {}, [el("div", {class: "activity-inline-popover__search"}, [search]), list]);
            openPopover(cell, box, "Escolher o responsável");
            load("");
        }

        // -- editor de prazo ---------------------------------------------------------------------------

        function openDeadlineEditor(cell) {
            var state = stateOf(cell);
            var model = state.model;
            var date = el("input", {type: "date", "aria-label": "Data do prazo"});
            var time = el("input", {type: "time", "aria-label": "Hora do prazo (opcional)"});
            date.value = model.date;
            time.value = model.time;
            var error = el("p", {class: "activity-inline-popover__error", role: "alert", hidden: true});
            var apply = el("button", {type: "button", class: "btn btn--primary btn--sm", text: "Aplicar"});
            var clear = el("button", {type: "button", class: "btn btn--sm", text: "Limpar"});
            var cancel = el("button", {type: "button", class: "btn btn--sm", text: "Cancelar"});

            function commit(newDate, newTime) {
                var data = new win.FormData();
                data.append("date", newDate);
                data.append("time", newTime);
                closePopover(true);
                var late = newDate ? new Date(newDate + "T" + (newTime || "23:59") + ":00") < new Date() : false;
                save(cell, "requested_deadline", data, {date: newDate, time: newTime, text: newDate ? deadlineText(newDate, newTime) : "Sem prazo", isLate: late});
            }
            function submit() {
                if (!date.value) {
                    error.textContent = time.value ? "Escolha a data do prazo." : "Escolha a data ou use Limpar.";
                    error.hidden = false;
                    date.focus();
                    return;
                }
                commit(date.value, time.value);
            }
            apply.addEventListener("click", submit);
            clear.addEventListener("click", function () { commit("", ""); });
            cancel.addEventListener("click", function () { closePopover(true); });
            [date, time].forEach(function (input) {
                input.addEventListener("keydown", function (event) { if (event.key === "Enter") { event.preventDefault(); submit(); } });
            });
            var foot = el("div", {class: "activity-inline-popover__foot"}, [model.date ? clear : null, cancel, apply]);
            var form = el("div", {class: "activity-inline-popover__form"}, [
                el("label", {}, [el("span", {text: "Data"}), date]),
                el("label", {}, [el("span", {text: "Hora (opcional)"}), time]),
                error, foot
            ]);
            openPopover(cell, form, "Editar o prazo");
        }

        // -- campos do cartão do Kanban ---------------------------------------------------------------------------------
        // O servidor desenha o cartão (templates/kanban/_fields.html) com o modelo de cada campo editável em `data-inline-model`.
        // Aqui só o desenho otimista de Responsável e Prazo; Setor, Etapa, Status e Prioridade ficam em activity-inline-options.js.
        // Depois de uma gravação o servidor ainda redesenha as raias quando o campo muda a raia do cartão (demand-kanban.js).

        function cardModel(cell) {
            try { return JSON.parse(cell.getAttribute("data-inline-model") || "null"); } catch (error) { return null; }
        }

        function keepCardModel(cell, model) {
            cell.setAttribute("data-inline-model", JSON.stringify(model));
        }

        /** As iniciais do kit (`lps_board.initials`): a inicial do primeiro e do último nome. */
        function kitInitials(name) {
            var words = String(name || "").trim().split(/\s+/).filter(Boolean);
            if (!words.length) return "?";
            return (words[0].charAt(0) + (words.length > 1 ? words[words.length - 1].charAt(0) : "")).toUpperCase();
        }

        function renderCardOwner(cell, model) {
            cell.textContent = "";
            if (model && model.value) {
                cell.appendChild(el("span", {class: "board-person"}, [
                    el("span", {class: "board-avatar", "aria-hidden": "true", text: kitInitials(model.text)}),
                    el("span", {class: "board-person__name", text: model.text})
                ]));
            } else {
                var avatar = el("span", {class: "board-avatar board-avatar--empty", "aria-hidden": "true"});
                avatar.innerHTML = '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><use href="#i-user"></use></svg>';
                cell.appendChild(el("span", {class: "board-person board-person--empty"}, [avatar, el("span", {class: "sr-only", text: "Sem responsável"})]));
            }
            keepCardModel(cell, model);
        }

        function renderCardDeadline(cell, model) {
            cell.textContent = "";
            if (!model || !model.text || model.text === "Sem prazo") {
                cell.appendChild(el("span", {class: "board-empty", text: "—"}));
            } else {
                var date = el("span", {class: "board-date" + (model.isLate ? " is-overdue" : ""), text: model.text});
                if (model.isLate) {
                    date.appendChild(doc.createTextNode(" "));
                    date.appendChild(el("span", {class: "board-date__flag", text: "vencido"}));  // atraso é selo, nunca fundo
                }
                cell.appendChild(date);
            }
            keepCardModel(cell, model);
        }

        cardFields.owner = {read: cardModel, render: renderCardOwner};
        cardFields.requested_deadline = {read: cardModel, render: renderCardDeadline};

        // -- eventos ------------------------------------------------------------------------------------

        function openEditor(cell) {
            var field = cell.dataset.inlineField;
            if (stateOf(cell).busy) return;
            if (active && active.anchor === cell) { closePopover(true); return; }
            closePopover(false);
            if (field === "title") openTitleEditor(cell);
            else if (field === "owner") openOwnerEditor(cell);
            else if (field === "requested_deadline") openDeadlineEditor(cell);
            else if (editorFor(field) && editorFor(field).open) editorFor(field).open(cell);
        }

        table.addEventListener("click", function (event) {
            var cell = event.target.closest("[data-inline-field]");
            if (!cell || !table.contains(cell)) return;
            if (cell.classList.contains("is-editing") && event.target.closest("input")) return; // clique dentro do campo de texto
            event.preventDefault();
            openEditor(cell);
        });
        table.addEventListener("keydown", function (event) {
            var cell = event.target;
            if (!cell.matches || !cell.matches("[data-inline-field]")) return;
            if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openEditor(cell); }
        });
        doc.addEventListener("mousedown", function (event) {
            if (!active) return;
            if (active.pop.contains(event.target) || active.anchor.contains(event.target)) return;
            closePopover(false);
        }, true);
        doc.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && active) { event.preventDefault(); closePopover(true); }
        });
        win.addEventListener("resize", reposition);
        win.addEventListener("scroll", reposition, true);

        var api = {
            table: table, overlay: overlay, doc: doc, win: win, el: el, helpers: helpers, surface: surface, rowOf: rowOf,
            stateOf: stateOf, save: save, getJSON: getJSON, postJSON: postJSON, showError: showError,
            /** Dá a uma célula um valor já confirmado pelo servidor (ex.: a opção que outra linha acabou de editar). */
            setConfirmed: function (cell, field, model) { stateOf(cell).model = model; render(cell, field, model); },
            onSaved: function (listener) { listeners.push(listener); },
            openPopover: openPopover, closePopover: closePopover, reposition: reposition,
            isOpen: function (pop) { return !!active && active.pop === pop; },
            registerEditor: function (field, editor) { editors[field] = editor; },
            /** Editor de um campo do CARTÃO (mesmo contrato de `registerEditor`; só vale na superfície do Kanban). */
            registerCardField: function (field, editor) { cardFields[field] = editor; },
            /** As células da página que mostram a mesma opção (por exemplo, a etapa que acabou de ser renomeada). */
            optionCells: function (field, id) {
                var selector = surface === "card" ? '[data-inline-field="' + field + '"]' : 'td[data-column="' + field + '"]';
                return Array.prototype.filter.call(table.querySelectorAll(selector), function (node) { return node.dataset.optionId === String(id); });
            },
            /** As células de Etapa e Status da mesma demanda: o servidor as redefine quando o setor muda. */
            linkedCells: function (cell) {
                var row = rowOf(cell);
                var found = [];
                ["stage", "condition"].forEach(function (field) {
                    var node = row && row.querySelector(surface === "card" ? '[data-inline-field="' + field + '"]' : 'td[data-column="' + field + '"]');
                    if (node) found.push({cell: node, field: field});
                });
                return found;
            }
        };
        plugins.forEach(function (plugin) { plugin(api); });
        return {closePopover: closePopover, openEditor: openEditor, stateOf: stateOf, api: api};
    }

    /** Plugins de editores (ex.: activity-inline-options.js). Vale em qualquer ordem de carregamento. */
    function use(plugin) {
        plugins.push(plugin);
        if (window.LPSInlineEdit && window.LPSInlineEdit.instance) plugin(window.LPSInlineEdit.instance.api);
    }

    function boot() {
        var table = document.querySelector("[data-activity-list], [data-kanban][data-inline-url]");
        var overlay = document.getElementById("activity-inline-overlay-root");
        if (!table || !overlay || window.LPSInlineEdit.instance) return;
        window.LPSInlineEdit.instance = init(table, overlay, document, window);
    }

    window.LPSInlineEdit = {helpers: helpers, init: init, boot: boot, use: use};
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();
})();
