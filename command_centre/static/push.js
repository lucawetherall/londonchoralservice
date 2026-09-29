// This device's notifications (/device). Enable: ask permission and subscribe (one tap), then approve the new
// device with Face ID or Touch ID (a second tap: the server's summary, bound to a passkey challenge). Turn off:
// unsubscribe here and remove the device on the server (no passkey: it only narrows who is told), and clear the
// saved offline pages. "Clear offline copies" asks the service worker to delete the saved Today and Money pages.
//
// One click listener on the document (delegated), with the page's elements looked up when they are used, and the
// state read again after the Refresh link re-renders the page (htmx:load), so the buttons keep working.
(function () {
  "use strict";

  var READY_WAIT = 3000;  // ms: navigator.serviceWorker.ready never settles when no service worker is active

  // The active service worker's registration, or null when none is active within READY_WAIT (a browser tab that
  // never installed the app, or a private window): never waits forever.
  function ready() {
    if (!("serviceWorker" in navigator)) return Promise.resolve(null);
    return Promise.race([
      navigator.serviceWorker.ready,
      new Promise(function (resolve) { setTimeout(function () { resolve(null); }, READY_WAIT); })
    ]);
  }

  // Ask the service worker to delete the saved pages; resolves true once it confirms, null when there is no
  // service worker to ask (so nothing was saved here), false when it didn't answer.
  function clearOffline() {
    return ready().then(function (reg) {
      if (!reg) return null;
      var worker = navigator.serviceWorker.controller || reg.active;
      if (!worker) return null;
      return new Promise(function (resolve) {
        var channel = new MessageChannel();
        var timer = setTimeout(function () { resolve(false); }, 3000);
        channel.port1.onmessage = function () { clearTimeout(timer); resolve(true); };
        worker.postMessage({ type: "clear-offline" }, [channel.port2]);
      });
    });
  }
  window.LCSClearOffline = clearOffline;

  var pending = null;  // {input, options} between the two taps

  function el(id) { return document.getElementById(id); }
  function say(text) { var s = el("push-status"); if (s) s.textContent = text; }
  function show(e, on) { if (e) e.hidden = !on; }
  function known() {
    var box = el("push-box");
    return ((box && box.dataset.ids) || "").split(",").filter(Boolean);
  }

  function keyBytes(s) {
    s = s.replace(/-/g, "+").replace(/_/g, "/");
    var bin = atob(s + "===".slice((s.length + 3) % 4));
    var out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  async function deviceId(endpoint) {
    var digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(endpoint));
    return Array.from(new Uint8Array(digest)).map(function (b) { return b.toString(16).padStart(2, "0"); })
      .join("").slice(0, 16);
  }

  function supported() {
    return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  }

  async function current() {
    var reg = await ready();
    return reg ? reg.pushManager.getSubscription() : null;
  }

  // Show this device's state (the page's buttons start hidden).
  async function refresh() {
    var box = el("push-box");
    if (!box) return;
    pending = null;
    show(el("push-approve"), false);
    if (!supported()) {
      say("Notifications work once the app is on the Home Screen (iOS 16.4 or later). Add it first, then open it from there.");
      show(el("push-enable"), false); show(el("push-off"), false);
      return;
    }
    if (!box.dataset.key) {
      say("Notifications aren't set up yet: the service makes its key when it starts.");
      show(el("push-enable"), false); show(el("push-off"), false);
      return;
    }
    var sub = await current();
    var on = sub && known().indexOf(await deviceId(sub.endpoint)) !== -1 && Notification.permission === "granted";
    say(on ? "Notifications are on for this device." :
        Notification.permission === "denied" ? "Notifications are blocked for this app in the phone's Settings." :
        "Notifications are off for this device.");
    show(el("push-enable"), !on && Notification.permission !== "denied");
    show(el("push-off"), !!on);
  }

  function start() {
    refresh().catch(function () { say("Couldn't read this device's notification state."); });
  }

  function clearCopies(button) {
    var status = el("offline-status");
    button.disabled = true;
    if (status) status.textContent = "Clearing…";
    clearOffline().then(function (ok) {
      if (!status) return;
      status.textContent = ok ? "Offline copies cleared on this device." :
        ok === null ? "Nothing to clear: this browser keeps no offline copies (the app isn't installed here, or its offline helper isn't running)." :
        "The offline helper didn't answer. Close the app, open it again and retry.";
    }, function () {
      if (status) status.textContent = "Couldn't clear the offline copies.";
    }).then(function () { button.disabled = false; });
  }

  async function enable(button) {
    var box = el("push-box");
    if (!box || !window.LCSPasskey) return;
    button.disabled = true;
    try {
      var perm = await Notification.requestPermission();
      if (perm !== "granted") { say("Notifications weren't allowed."); return; }
      var reg = await ready();
      if (!reg) { say("The app's offline helper isn't running here: open the app from the Home Screen and try again."); return; }
      var sub = await reg.pushManager.getSubscription() ||
        await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(box.dataset.key) });
      var j = sub.toJSON();
      var input = { endpoint: j.endpoint, p256dh: j.keys.p256dh, auth: j.keys.auth };
      var p = await window.LCSPasskey.post("/actions/push-subscribe/preview", { input: input });
      pending = { input: input, options: p.options };
      var summary = el("push-summary");
      if (summary) { summary.textContent = p.summary; summary.hidden = false; }
      show(button, false);
      show(el("push-approve"), true);
      say("One more tap: approve this device with Face ID or Touch ID (within 60 seconds).");
    } catch (e) {
      say("Not turned on: " + (e && e.message ? e.message : "no answer"));
    } finally {
      button.disabled = false;
    }
  }

  async function approve(button) {
    if (!pending || !window.LCSPasskey) return;
    button.disabled = true;
    try {
      var cred = await window.LCSPasskey.assertWith(pending.options);
      await window.LCSPasskey.post("/actions/push-subscribe/run", { input: pending.input, credential: cred });
      window.location.reload();
    } catch (e) {
      say("Not approved: " + (e && e.message ? e.message : "cancelled") + ". Tap Enable notifications to try again.");
      pending = null;
      show(button, false);
      show(el("push-enable"), true);
    } finally {
      button.disabled = false;
    }
  }

  async function turnOff(button) {
    if (!window.LCSPasskey) return;
    button.disabled = true;
    try {
      var sub = await current();
      if (sub) {
        var input = { id: await deviceId(sub.endpoint) };
        if (known().indexOf(input.id) !== -1) {
          await window.LCSPasskey.post("/actions/push-unsubscribe/preview", { input: input });
          await window.LCSPasskey.post("/actions/push-unsubscribe/run", { input: input });
        }
        await sub.unsubscribe();
      }
      await clearOffline().catch(function () { return false; });  // turning off also clears the saved pages
      window.location.reload();
    } catch (e) {
      say("Not turned off: " + (e && e.message ? e.message : "no answer"));
    } finally {
      button.disabled = false;
    }
  }

  var HANDLERS = { "offline-clear": clearCopies, "push-enable": enable, "push-approve": approve, "push-off": turnOff };

  document.addEventListener("click", function (ev) {
    var button = ev.target && ev.target.closest ? ev.target.closest("#offline-clear, #push-enable, #push-approve, #push-off") : null;
    if (button && HANDLERS[button.id]) HANDLERS[button.id](button);
  });

  // after the Refresh link swaps in a new #main, read this device's state again for the new buttons
  document.addEventListener("htmx:load", function (ev) {
    var t = ev.target;
    if (t && t.querySelector && (t.id === "push-box" || t.querySelector("#push-box"))) start();
  });

  start();
})();
