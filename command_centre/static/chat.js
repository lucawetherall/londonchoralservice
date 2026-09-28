// The Command Centre chat: the stream (Server-Sent Events), the composer, quick prompts, stop, and approval cards.
// No inline code; every value from the server is rendered with textContent, never as HTML.
(function () {
  "use strict";

  // "New chat", "Run now" and "Run approved" forms. They are posted with fetch(), not as a plain form submit: the
  // app sends Referrer-Policy: no-referrer, under which a browser's form POST carries "Origin: null", which the
  // same-origin check refuses. fetch() sends the real Origin.
  Array.prototype.forEach.call(document.querySelectorAll("form.chat-new"), function (f) {
    f.addEventListener("submit", async function (ev) {
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
        if (!res.ok || typeof data.url !== "string" || data.url.indexOf("/chat/") !== 0) {
          throw new Error(data.error || ("refused (" + res.status + ")"));
        }
        window.location.assign(data.url);
      } catch (err) {
        if (btn) btn.disabled = false;
        var note = f.querySelector(".status") || f.appendChild(document.createElement("p"));
        note.className = "status";
        note.textContent = "Not started: " + (err && err.message ? err.message : "error");
      }
    });
  });

  var root = document.getElementById("chat");
  if (!root) return;
  var id = root.dataset.chat;
  var log = document.getElementById("chat-log");
  var form = document.getElementById("chat-form");
  var text = document.getElementById("chat-text");
  var turns = document.getElementById("chat-turns");
  var send = document.getElementById("chat-send");
  var stopBtn = document.getElementById("chat-stop");
  var status = document.getElementById("chat-status");
  var state = document.getElementById("chat-state");
  var totals = document.getElementById("chat-totals");
  var last = 0, source = null, running = false, cards = {};

  function el(tag, cls, content) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (content !== undefined && content !== null) e.textContent = String(content);
    return e;
  }

  function say(t) { status.textContent = t || ""; }

  function setRunning(on) {
    running = on;
    stopBtn.hidden = !on;
    send.disabled = on;
    state.textContent = on ? "Claude is working…" : "Ready";
  }

  function item(cls, label, body) {
    var li = el("li", "chat-item " + cls);
    if (label) li.appendChild(el("p", "chat-label", label));
    if (body !== undefined && body !== null && body !== "") li.appendChild(el("div", "chat-text", body));
    log.appendChild(li);
    li.scrollIntoView({ block: "nearest" });
    return li;
  }

  function money(v) { return "$" + (Number(v) || 0).toFixed(4); }

  function showTotals(t) {
    if (!t) return;
    totals.textContent = money(t.cost_usd) + " · " + (t.input_tokens || 0) + " in / " + (t.output_tokens || 0) + " out tokens";
  }

  function decisionWords(d) {
    return ({ approved: "Approved with your passkey", denied: "Denied", "timed out": "Denied: no answer in 10 minutes",
              expired: "Closed: the turn ended", stopped: "Denied: chat stopped" })[d] || d;
  }

  function renderCard(e) {
    var li = el("li", "chat-item chat-card");
    li.appendChild(el("p", "chat-label", "Claude asks to use " + e.tool));
    li.appendChild(el("pre", "command", e.summary));
    var st = el("p", "status");
    var row = el("div", "actions");
    var ok = el("button", "button", "Approve with Face ID or Touch ID");
    var no = el("button", "button quiet", "Deny");
    ok.type = no.type = "button";
    row.appendChild(ok); row.appendChild(no);
    li.appendChild(row); li.appendChild(st);
    log.appendChild(li);
    li.scrollIntoView({ block: "nearest" });
    var base = "/chat/" + id + "/cards/" + e.card;
    ok.addEventListener("click", async function () {
      ok.disabled = no.disabled = true;
      try {
        st.textContent = "Waiting for Face ID or Touch ID…";
        var opts = await window.LCSPasskey.post(base + "/options", { digest: e.digest });
        var cred = await window.LCSPasskey.assertWith(opts);
        await window.LCSPasskey.post(base + "/approve", { digest: e.digest, credential: cred });
        st.textContent = "Approved.";
      } catch (err) {
        st.textContent = "Not approved: " + (err && err.message ? err.message : "cancelled");
        ok.disabled = no.disabled = false;
      }
    });
    no.addEventListener("click", async function () {
      ok.disabled = no.disabled = true;
      try { await window.LCSPasskey.post(base + "/deny", {}); st.textContent = "Denied."; }
      catch (err) { st.textContent = "Couldn't deny: " + (err && err.message ? err.message : "error"); ok.disabled = no.disabled = false; }
    });
    cards[e.card] = { li: li, row: row, st: st };
    if (e.expired) closeCard(e.card, "expired");
  }

  function closeCard(card, decision) {
    var c = cards[card];
    if (!c) return;
    c.row.hidden = true;
    c.st.textContent = decisionWords(decision);
    c.li.classList.add(decision === "approved" ? "card-ok" : "card-closed");
  }

  function render(e) {
    switch (e.type) {
      case "meta": break;
      case "session": break;
      case "user": item("chat-user", "You", e.text); break;
      case "text": item("chat-claude" + (e.sub ? " chat-sub" : ""), e.sub ? "Claude (sub-agent)" : "Claude", e.text); break;
      case "tool": item("chat-tool", "Tool: " + e.tool, e.input); break;
      case "tool_result": item("chat-result" + (e.error ? " chat-error" : ""), e.error ? "Tool error" : "Tool result", e.text); break;
      case "card": renderCard(e); break;
      case "card_done": closeCard(e.card, e.decision); break;
      case "result":
        var u = e.usage || {};
        item("chat-cost", null, (e.error ? "Stopped (" + e.subtype + ") · " : "") + (e.turns || 0) + " turns · " +
             money(e.cost_usd) + " · " + (u.input_tokens || 0) + " in / " + (u.output_tokens || 0) + " out tokens");
        break;
      case "error": item("chat-error", "Error", e.error); break;
      case "stopped": item("chat-note", null, e.reason === "owner" ? "You stopped this chat." : "The turn was cancelled."); break;
      default: break;
    }
  }

  function connect() {
    if (source) source.close();
    source = new EventSource("/chat/" + id + "/stream?after=" + last);
    ["meta", "user", "text", "tool", "tool_result", "card", "card_done", "result", "error", "stopped", "session", "notice"]
      .forEach(function (name) {
        source.addEventListener(name, function (m) {
          var e;
          try { e = JSON.parse(m.data); } catch (err) { return; }
          if (typeof e.n === "number" && e.n <= last) return;
          if (typeof e.n === "number") last = e.n;
          if (!running && e.type !== "meta") setRunning(true);
          render(e);
        });
      });
    source.addEventListener("idle", function (m) {
      try { showTotals(JSON.parse(m.data).totals); } catch (err) { /* ignore */ }
      setRunning(false);
      source.close();
      source = null;
    });
    source.onerror = function () { state.textContent = "Reconnecting…"; };
  }

  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    var t = text.value.trim();
    if (!t) return;
    say("Sending…");
    try {
      await window.LCSPasskey.post("/chat/" + id + "/message", { text: t, max_turns: Number(turns.value) });
      text.value = "";
      say("");
      setRunning(true);
      connect();
    } catch (err) { say("Not sent: " + (err && err.message ? err.message : "error")); }
  });

  stopBtn.addEventListener("click", async function () {
    try { await window.LCSPasskey.post("/chat/" + id + "/stop", {}); say("Stopping…"); }
    catch (err) { say("Couldn't stop: " + (err && err.message ? err.message : "error")); }
  });

  Array.prototype.forEach.call(document.querySelectorAll("[data-prefill]"), function (b) {
    b.addEventListener("click", function () { text.value = b.dataset.prefill; text.focus(); });
  });
  var hand = document.getElementById("chat-hand"), ref = document.getElementById("chat-ref");
  if (hand && ref) hand.addEventListener("click", function () {
    if (!ref.value) return;
    text.value = hand.dataset.template.replace("{ref}", ref.value);
    text.focus();
  });

  setRunning(false);
  state.textContent = "Loading…";
  connect();
})();
