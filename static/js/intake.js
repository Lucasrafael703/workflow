/* Caixa de Entrada: abre as ações em janela e aplica a resposta do servidor.
   Depende só de LPSModal.open(url, {onSuccess}) e de LPSAjax.{applyResult, announce};
   sem eles (ou se a janela não abrir) cai na página completa, que também funciona. */
(function () {
    "use strict";

    function announce(message) {
        if (message && window.LPSAjax) window.LPSAjax.announce(message);
    }

    // Depois de remover um cartão, se a lista esvaziou recarrega: mostra o estado vazio e as contagens das abas.
    function finish(result) {
        if (window.LPSAjax && window.LPSAjax.applyResult(result)) {
            var list = document.querySelector("[data-intake-list]");
            if (result.remove && list && !list.querySelector(".intake-item")) window.location.reload();
            return;
        }
        if (result && result.redirect_url) {
            window.location.assign(result.redirect_url);
        } else {
            window.location.reload();
        }
    }

    function handle(result) {
        if (result && result.message) announce(result.message);
        finish(result || {});
    }

    document.addEventListener("click", function (event) {
        var link = event.target.closest("a[data-intake-action]");
        if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        if (!window.LPSModal) return; // sem janela: o link abre a página completa
        event.preventDefault();
        window.LPSModal.open(link.href, {onSuccess: handle}).catch(function () {
            window.location.assign(link.href);
        });
    });

    document.addEventListener("submit", function (event) {
        var form = event.target.closest("form[data-intake-restore]");
        if (!form) return;
        event.preventDefault();
        if (form.dataset.busy) return;
        form.dataset.busy = "true";
        var button = form.querySelector("button[type=submit]");
        if (button) button.disabled = true;
        var previous = form.querySelector("[role=alert]");
        if (previous) previous.remove();

        function fail(message) {
            var alert = document.createElement("span");
            alert.setAttribute("role", "alert");
            alert.className = "errorlist";
            alert.textContent = message;
            form.appendChild(alert);
        }

        fetch(form.action, {method: "POST", headers: {"X-Requested-With": "XMLHttpRequest"}, body: new FormData(form)})
            .then(function (response) {
                if (!(response.headers.get("content-type") || "").includes("application/json")) {
                    throw new Error("Não foi possível confirmar a operação. Verifique sua conexão ou sessão e tente novamente.");
                }
                return response.json().then(function (result) {
                    if (!response.ok) throw new Error(result.error || "Não foi possível restaurar a solicitação.");
                    return result;
                });
            })
            .then(handle)
            .catch(function (error) { fail(error.message); })
            .then(function () {
                delete form.dataset.busy;
                if (button) button.disabled = false;
            });
    });
})();
