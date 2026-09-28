// Action buttons: preview (the server's summary and exact command), then Face ID or Touch ID, then the result.
// Same-origin fetches only; no inline code. The page never sends summary text: the server builds it from the
// form's fields, and the passkey challenge it returns is bound to that summary.
(function () {
  "use strict";

  var dialog = document.getElementById("cc-dialog");
  if (!dialog || !window.LCSPasskey) return;
  var el = {
    title: document.getElementById("cc-title"),
    summary: document.getElementById("cc-summary"),
    command: document.getElementById("cc-command"),
    code: document.getElementById("cc-code"),
    codeHead: document.getElementById("cc-code-head"),
    codeLink: document.getElementById("cc-code-link"),
    diff: document.getElementById("cc-diff"),
    status: document.getElementById("cc-status"),
    output: document.getElementById("cc-output"),
    approve: document.getElementById("cc-approve"),
    next: document.getElementById("cc-next"),
    close: document.getElementById("cc-close")
  };
  var current = null;   // {name, input, preview}
  var pendingNext = null;
  var changed = false;  // reload the page on close after something ran

  function say(text) { el.status.textContent = text; }

  function formInput(form) {
    var input = {};
    new FormData(form).forEach(function (value, key) { input[key] = String(value); });
    return input;
  }

  function reset() {
    el.summary.textContent = "";
    el.command.textContent = "";
    if (el.code) {
      el.code.hidden = true;
      el.diff.textContent = "";
      el.codeHead.textContent = "";
      el.codeLink.removeAttribute("href");
    }
    el.output.textContent = "";
    el.output.hidden = true;
    el.next.hidden = true;
    el.approve.hidden = false;
    el.approve.disabled = true;
    pendingNext = null;
    say("");
  }

  async function preview(name, input) {
    reset();
    el.title.textContent = "Check before you approve";
    if (!dialog.open) dialog.showModal();
    say("Asking the server what this will do…");
    try {
      var p = await window.LCSPasskey.post("/actions/" + encodeURIComponent(name) + "/preview", { input: input });
      current = { name: name, input: input, preview: p };
      el.title.textContent = p.title || "Check before you approve";
      // the signed summary ends with "Runs: <command>"; the command has its own box below
      var tail = p.command ? "\nRuns: " + p.command : "";
      el.summary.textContent = tail && p.summary.slice(-tail.length) === tail ? p.summary.slice(0, -tail.length) : p.summary;
      el.command.textContent = p.command || "(no script: a record in the app's own folder)";
      if (p.code && el.code) {
        // the server's diff and link (the summary carries the diff's sha256, so the tap binds this code)
        el.codeHead.textContent = p.code.head || "";
        el.diff.textContent = p.code.diff || "(no change in this file)";
        if (typeof p.code.link === "string") el.codeLink.setAttribute("href", p.code.link);  // built by the server
        el.code.hidden = false;
      }
      el.approve.textContent = p.passkey ? "Approve with Face ID or Touch ID" : "Run it";
      el.approve.disabled = false;
      say(p.passkey ? "Nothing has run yet. Approving asks for your passkey, for this exact action, within 60 seconds."
                    : "Nothing has run yet.");
    } catch (e) {
      current = null;
      el.approve.hidden = true;
      say("Refused: " + (e && e.message ? e.message : "no answer"));
    }
  }

  async function approve() {
    if (!current) return;
    var name = current.name, body = { input: current.input };
    el.approve.disabled = true;
    try {
      if (current.preview.passkey) {
        say("Waiting for Face ID or Touch ID…");
        body.credential = await window.LCSPasskey.assertWith(current.preview.options);
      }
      say("Running…");
      var r = await window.LCSPasskey.post("/actions/" + encodeURIComponent(current.name) + "/run", body);
      changed = true;
      el.approve.hidden = true;
      say(r.ok ? "Done." : (r.exit_code === null ? "Stopped: it took too long." : "It failed (exit " + r.exit_code + ")."));
      if (r.output) { el.output.textContent = r.output; el.output.hidden = false; }
      if (r.next && r.next.action) {
        pendingNext = r.next;
        el.next.textContent = r.next.label || "Next";
        el.next.hidden = false;
      }
    } catch (e) {
      // the challenge is single use: another try starts from a fresh preview
      say("Not run: " + (e && e.message ? e.message : "cancelled"));
      current = null;
      el.approve.hidden = true;
      pendingNext = { action: name, input: body.input };
      el.next.textContent = "Check again";
      el.next.hidden = false;
    }
  }

  el.approve.addEventListener("click", approve);
  el.next.addEventListener("click", function () {
    if (pendingNext) preview(pendingNext.action, pendingNext.input || {});
  });
  el.close.addEventListener("click", function () { dialog.close(); });
  dialog.addEventListener("close", function () {
    current = null;
    if (changed) window.location.reload();
  });

  document.addEventListener("submit", function (ev) {
    var form = ev.target;
    if (!(form instanceof HTMLFormElement) || !form.classList.contains("cc-action")) return;
    ev.preventDefault();
    if (!form.reportValidity()) return;
    preview(form.dataset.action, formInput(form));
  });
})();
