// Registers the service worker (/sw.js, scope /) and shows the install hint on a phone that hasn't added the app
// to its Home Screen yet. Same-origin only; no inline code.
(function () {
  "use strict";

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () { /* the pages work without it */ });
  }

  var hint = document.getElementById("cc-install-hint");
  if (!hint) return;
  var standalone = window.navigator.standalone === true ||
    (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches);
  var phone = /iPhone|iPad|iPod|Android/.test(navigator.userAgent || "");
  var dismissed = false;
  try { dismissed = window.localStorage.getItem("cc-install-hint") === "no"; } catch (e) { /* private mode */ }
  if (standalone || !phone || dismissed) return;
  hint.hidden = false;
  var close = document.getElementById("cc-install-close");
  if (close) close.addEventListener("click", function () {
    hint.hidden = true;
    try { window.localStorage.setItem("cc-install-hint", "no"); } catch (e) { /* private mode */ }
  });
})();
