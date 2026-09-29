/* The back/forward cache can restore an old unread badge and list snapshot. */
(function () {
    "use strict";
    window.addEventListener("pageshow", function (event) {
        if (event.persisted) window.location.reload();
    });
})();
