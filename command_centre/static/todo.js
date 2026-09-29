// To-do "Mark done" and "Reopen" forms. They are posted with fetch(), not as a plain form submit: the app sends
// Referrer-Policy: no-referrer, under which a browser's form POST carries "Origin: null", which the same-origin
// check refuses. fetch() sends the real Origin. One listener on the document (delegated), so the forms still work
// after the Refresh link re-renders the page.
(function () {
  "use strict";

  document.addEventListener("submit", async function (ev) {
    var f = ev.target;
    if (!(f instanceof HTMLFormElement) || !f.classList.contains("todo-tick")) return;
    ev.preventDefault();
    var btn = f.querySelector("button");
    if (btn) btn.disabled = true;
    try {
      var res = await fetch(f.action, {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json" },
        body: new URLSearchParams(new FormData(f)).toString()
      });
      var data = {};
      try { data = await res.json(); } catch (e) { /* not JSON */ }
      if (!res.ok || data.url !== "/todo") {
        throw new Error(data.error || ("refused (" + res.status + ")"));
      }
      window.location.assign(data.url);
    } catch (err) {
      if (btn) btn.disabled = false;
      var note = f.querySelector(".status") || f.appendChild(document.createElement("p"));
      note.className = "status";
      note.setAttribute("role", "status");
      note.textContent = "Not saved: " + (err && err.message ? err.message : "error");
    }
  });
})();
