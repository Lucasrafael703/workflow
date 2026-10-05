/* Adaptador do Kanban de Demandas (Workspace): liga o núcleo (kanban-core.js) ao servidor de Demandas.
   - mover  = POST no endereço de gravação da célula (`data-move-url`, com `/itens/0/valor/`), `{value, updated_at}`;
              o servidor valida tudo (permissão, setor da etapa, demanda concluída, versão) e a mensagem dele chega à tela;
   - raias  = GET da própria página com `fragmento=raias` (mesma autorização, mesmo recorte de busca e filtros);
   - mudar de setor pede confirmação: etapa e status voltam ao padrão do setor novo. */
(function () {
    "use strict";

    var core = window.LPSKanbanCore;
    var root = document.querySelector("[data-kanban][data-move-url]");
    if (!core || !root) return;

    var NO_CONNECTION = "Sem conexão com o servidor. Tente de novo.";
    var SESSION = "Sua sessão expirou. Entre de novo para continuar.";

    function csrf() {
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        if (match) return decodeURIComponent(match[1]);
        var field = document.querySelector("input[name=csrfmiddlewaretoken]");
        return field ? field.value : "";
    }

    function moveUrl(itemId) {
        return root.getAttribute("data-move-url").replace("/itens/0/", "/itens/" + encodeURIComponent(itemId) + "/");
    }

    function failure(response, data) {
        var error = new Error("Não foi possível mover a demanda. Tente de novo.");
        if (response.redirected) {
            error.message = SESSION;
        } else if (response.status === 409) {
            error.message = data.message || "Esta demanda foi alterada por outra pessoa. As raias foram atualizadas.";
            error.refresh = true;  // a versão que a tela tinha é velha: o servidor manda de novo
        } else if (response.status === 400) {
            error.message = data.message || error.message;
        } else if (response.status === 403) {
            error.message = "Você não pode mover esta demanda (sem permissão ou sessão expirada). Recarregue a página.";
        } else if (response.status === 404) {
            error.message = "Esta demanda não está mais disponível.";
            error.refresh = true;
        }
        return error;
    }

    function move(ctx) {
        return window.fetch(moveUrl(ctx.itemId), {
            method: "POST",
            credentials: "same-origin",
            headers: {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrf()},
            body: JSON.stringify({value: ctx.laneKey === "empty" ? "" : ctx.laneKey, updated_at: ctx.updatedAt})
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (data) {
                // Só `success: true` vale: uma página de login devolvida com 200 depois de uma sessão vencida não é sucesso.
                if (response.ok && !response.redirected && data.success === true) {
                    return {message: "Demanda movida para “" + ctx.laneLabel + "”.", updatedAt: data.updated_at};
                }
                throw failure(response, data);
            });
        }, function () {
            throw new Error(NO_CONNECTION);
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

    core.init(root, {move: move, reload: reload, beforeMove: beforeMove});
})();
