/* Adaptador do Kanban de Demandas: liga o núcleo (kanban-core.js, o MESMO componente de Quadros) ao servidor de Demandas.
   - mover    = POST no endereço de gravação da célula do agrupamento (`data-move-url`, com `/itens/0/valor/`), `{value, updated_at}`;
   - renomear = o mesmo endereço para o campo Título (`data-rename-url`); o título é editado no lugar, como em Quadros;
   - o servidor valida tudo (permissão, setor da etapa, demanda concluída, versão) e a mensagem dele chega à tela;
   - raias    = GET da própria página com `fragmento=raias` (mesma autorização, mesmo recorte de busca e filtros);
   - mudar de setor pede confirmação: etapa e status voltam ao padrão do setor novo;
   - o ⋯ do cartão oferece "Abrir demanda" (a ficha) além de "Mover para…" e "Renomear";
   - o ⋮ da raia abre os itens que o servidor mandou (`data-lane-menu-items`: ir à tela de etapas/status do setor, só para quem a gere);
     o "+ Adicionar" da raia é um link para a janela "Nova demanda" já com os valores da raia, então não precisa de código aqui;
   - "Configurar cartões" = o diálogo de Quadros (`core.openConfig`) com os dados de `#kanban-config` (só vai para quem configura o quadro);
   - editar um campo no cartão (Responsável, Prazo, Setor, Etapa, Status, Prioridade) é o editor da Lista (activity-inline-edit.js, que
     reconhece o Kanban pela raiz `[data-kanban]`); aqui só se reage à gravação: guarda a versão do cartão e, quando o campo muda a
     raia dele, pede as raias de novo. */
(function () {
    "use strict";

    var core = window.LPSKanbanCore;
    var root = document.querySelector("[data-kanban]");
    if (!core || !root) return;

    var moveBase = root.getAttribute("data-move-url") || "";
    var renameBase = root.getAttribute("data-rename-url") || "";
    var NO_CONNECTION = "Sem conexão com o servidor. Tente de novo.";
    var SESSION = "Sua sessão expirou. Entre de novo para continuar.";

    // Mensagem de cada operação quando o servidor não dá a dele (400 usa a do servidor).
    var TEXT = {
        move: {
            generic: "Não foi possível mover a demanda. Tente de novo.",
            forbidden: "Você não pode mover esta demanda (sem permissão ou sessão expirada). Recarregue a página.",
            gone: "Esta demanda não está mais disponível."
        },
        rename: {
            generic: "Não foi possível renomear a demanda. Tente de novo.",
            forbidden: "Você não pode renomear esta demanda (sem permissão ou sessão expirada). Recarregue a página.",
            gone: "Esta demanda não está mais disponível."
        },
        config: {
            generic: "Não foi possível salvar a configuração dos cartões. Tente de novo.",
            forbidden: "Você não pode configurar os cartões (sem permissão ou sessão expirada). Recarregue a página.",
            gone: "Esta visualização não está mais disponível. Recarregue a página."
        }
    };

    function csrf() {
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        if (match) return decodeURIComponent(match[1]);
        var field = document.querySelector("input[name=csrfmiddlewaretoken]");
        return field ? field.value : "";
    }

    function itemUrl(base, itemId) {
        return base.replace("/itens/0/", "/itens/" + encodeURIComponent(itemId) + "/");
    }

    function failure(response, data, kind) {
        var text = TEXT[kind];
        var error = new Error(text.generic);
        if (response.redirected) {
            error.message = SESSION;
        } else if (response.status === 409) {
            error.message = data.message || "Esta demanda foi alterada por outra pessoa. As raias foram atualizadas.";
            error.refresh = true;  // a versão que a tela tinha é velha: o servidor manda de novo
        } else if (response.status === 400) {
            error.message = data.message || error.message;
        } else if (response.status === 403) {
            error.message = text.forbidden;
        } else if (response.status === 404) {
            error.message = text.gone;
            error.refresh = kind !== "config";
        }
        return error;
    }

    /** POST em JSON. Só `success: true` vale: uma página de login devolvida com 200 depois de uma sessão vencida não é sucesso. */
    function send(url, body, kind) {
        return window.fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrf()},
            body: JSON.stringify(body)
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (data) {
                if (response.ok && !response.redirected && data.success === true) return data;
                throw failure(response, data, kind);
            });
        }, function () {
            throw new Error(NO_CONNECTION);
        });
    }

    function move(ctx) {
        if (!moveBase) return Promise.reject(new Error("Esta tela não consegue gravar o agrupamento."));
        return send(itemUrl(moveBase, ctx.itemId), {value: ctx.laneKey === "empty" ? "" : ctx.laneKey, updated_at: ctx.updatedAt}, "move").then(function (data) {
            return {message: "Demanda movida para “" + ctx.laneLabel + "”.", updatedAt: data.updated_at};
        });
    }

    function rename(ctx) {
        var version = ctx.card.getAttribute("data-updated-at") || "";
        return send(itemUrl(renameBase, ctx.itemId), {value: ctx.title, updated_at: version}, "rename").then(function (data) {
            return {updatedAt: data.updated_at};
        });
    }

    function reload() {
        var params = new window.URLSearchParams(window.location.search);
        params.set("fragmento", "raias");
        return window.fetch(window.location.pathname + "?" + params.toString(), {
            credentials: "same-origin", headers: {"X-Requested-With": "XMLHttpRequest"}
        }).then(function (response) {
            if (!response.ok || response.redirected) throw new Error("Não foi possível atualizar as raias. Recarregue a página.");
            return response.text();
        }, function () {
            throw new Error(NO_CONNECTION);
        }).then(function (markup) {
            // Se o servidor devolver uma página inteira (por exemplo, a tela de login), não a injetamos nas raias.
            if (!/data-lane\b|kanban-state/.test(markup)) throw new Error("Não foi possível atualizar as raias. Recarregue a página.");
            return markup;
        });
    }

    function beforeMove(ctx) {
        if (root.getAttribute("data-group-by") !== "sector") return true;
        var title = ctx.card.querySelector("[data-card-title]");
        return core.confirm({
            title: "Mudar o setor da demanda",
            message: "“" + (title ? title.textContent.trim() : "Demanda") + "” vai para o setor " + ctx.laneLabel +
                ". A etapa e o status dela voltam ao padrão desse setor.",
            confirmLabel: "Mudar setor"
        });
    }

    function laneMenu(ctx) {
        var links = [];
        try { links = JSON.parse(ctx.anchor.getAttribute("data-lane-menu-items") || "[]"); } catch (error) { links = []; }
        return links.filter(function (link) { return link && link.href; }).map(function (link) {
            return {label: link.label, icon: link.icon, onClick: function () { window.location.assign(link.href); }};
        });
    }

    var controller = null;
    var adapter = {
        move: move,
        reload: reload,
        beforeMove: beforeMove,
        laneMenu: laneMenu,
        menuItems: function (ctx) {
            var items = [];
            var detail = ctx.card.getAttribute("data-detail-url");
            if (detail) items.push({label: "Abrir demanda", icon: "eye", onClick: function () { window.location.assign(detail); }});
            if (renameBase && ctx.card.querySelector("[data-card-title][role=textbox]")) {
                items.push({label: "Renomear", icon: "file-text", onClick: function () { controller.startRename(ctx.card); }});
            }
            return items;
        }
    };
    if (renameBase) adapter.rename = rename;
    controller = core.init(root, adapter);

    // -- Configurar cartões: o diálogo de Quadros com os dados desta visualização ---------------------------------------

    function openConfig() {
        var data = document.getElementById("kanban-config");
        if (!data || !controller) return;
        var config = JSON.parse(data.textContent);
        controller.openConfig({
            controls: [
                {type: "check", key: "show_empty", label: "Mostrar raias vazias", value: config.settings.show_empty},
                {type: "check", key: "show_field_names", label: "Mostrar o nome de cada campo no cartão", value: config.settings.show_field_names}
            ],
            fields: config.fields,
            selected: config.selected,
            save: function (change) {
                // a ordem dos campos vai para um endereço; as opções de exibição, para outro; as raias vêm do servidor de novo
                var sent = change.card_fields
                    ? send(config.fields_url, {field_ids: (config.always || []).concat(change.card_fields)}, "config")
                    : send(config.settings_url, change, "config");
                return sent.then(function () { return controller.reload(); });
            }
        });
    }

    // -- Editar um campo no cartão ----------------------------------------------------------------------------------------

    /** Quando editar o campo muda a RAIA do cartão (o agrupamento é esse campo; trocar o setor redefine etapa e status). */
    function movesTheCard(field) {
        var group = root.getAttribute("data-group-by");
        return field === group || (field === "sector" && (group === "stage" || group === "condition"));
    }

    if (window.LPSInlineEdit && window.LPSInlineEdit.use) {
        window.LPSInlineEdit.use(function (api) {
            if (api.surface !== "card") return;
            api.onSaved(function (field, data, cell) {
                var card = cell.closest("[data-card]");
                if (card && data.updated_at) card.setAttribute("data-updated-at", data.updated_at);  // a próxima gravação leva a versão em dia
                if (movesTheCard(field)) controller.reload();
            });
        });
    }

    document.addEventListener("click", function (event) {
        var button = event.target.closest && event.target.closest("[data-kanban-config]");
        if (!button) return;
        event.preventDefault();
        openConfig();
    });
})();
