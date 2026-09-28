// This device's notifications (/device). Enable: ask permission and subscribe (one tap), then approve the new
// device with Face ID or Touch ID (a second tap: the server's summary, bound to a passkey challenge). Turn off:
// unsubscribe here and remove the device on the server (no passkey: it only narrows who is told), and clear the
// saved offline pages. "Clear offline copies" asks the service worker to delete the saved Today and Money pages.
(function () {
  "use strict";

  // Ask the service worker to delete the saved pages; resolves true once it confirms.
  function clearOffline() {
    if (!("serviceWorker" in navigator)) return Promise.resolve(false);
    return navigator.serviceWorker.ready.then(function (reg) {
      var worker = navigator.serviceWorker.controller || reg.active;
      if (!worker) return false;
      return new Promise(function (resolve) {
        var channel = new MessageChannel();
        var timer = setTimeout(function () { resolve(false); }, 3000);
        channel.port1.onmessage = function () { clearTimeout(timer); resolve(true); };
        worker.postMessage({ type: "clear-offline" }, [channel.port2]);
      });
    });
  }
  window.LCSClearOffline = clearOffline;

  var clearButton = document.getElementById("offline-clear");
  var clearStatus = document.getElementById("offline-status");
  if (clearButton) {
    clearButton.addEventListener("click", function () {
      clearButton.disabled = true;
      clearOffline().then(function (ok) {
        clearStatus.textContent = ok ? "Offline copies cleared on this device." : "Nothing to clear on this device.";
      }, function () {
        clearStatus.textContent = "Couldn't clear the offline copies.";
      }).then(function () { clearButton.disabled = false; });
    });
  }

  var box = document.getElementById("push-box");
  if (!box || !window.LCSPasskey) return;
  var status = document.getElementById("push-status");
  var summary = document.getElementById("push-summary");
  var enable = document.getElementById("push-enable");
  var approve = document.getElementById("push-approve");
  var off = document.getElementById("push-off");
  var known = (box.dataset.ids || "").split(",").filter(Boolean);
  var pending = null;  // {input, options} between the two taps

  function say(text) { status.textContent = text; }
  function show(el, on) { if (el) el.hidden = !on; }

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
    var reg = await navigator.serviceWorker.ready;
    return reg.pushManager.getSubscription();
  }

  async function refresh() {
    show(approve, false);
    if (!supported()) {
      say("Notifications work once the app is on the Home Screen (iOS 16.4 or later). Add it first, then open it from there.");
      show(enable, false); show(off, false);
      return;
    }
    if (!box.dataset.key) {
      say("The server has no notification key yet (see Health).");
      show(enable, false); show(off, false);
      return;
    }
    var sub = await current();
    var on = sub && known.indexOf(await deviceId(sub.endpoint)) !== -1 && Notification.permission === "granted";
    say(on ? "Notifications are on for this device." :
        Notification.permission === "denied" ? "Notifications are blocked for this app in the phone's Settings." :
        "Notifications are off for this device.");
    show(enable, !on && Notification.permission !== "denied");
    show(off, !!on);
  }

  enable.addEventListener("click", async function () {
    enable.disabled = true;
    try {
      var perm = await Notification.requestPermission();
      if (perm !== "granted") { say("Notifications weren't allowed."); return; }
      var reg = await navigator.serviceWorker.ready;
      var sub = await reg.pushManager.getSubscription() ||
        await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(box.dataset.key) });
      var j = sub.toJSON();
      var input = { endpoint: j.endpoint, p256dh: j.keys.p256dh, auth: j.keys.auth };
      var p = await window.LCSPasskey.post("/actions/push-subscribe/preview", { input: input });
      pending = { input: input, options: p.options };
      summary.textContent = p.summary;
      summary.hidden = false;
      show(enable, false);
      show(approve, true);
      say("One more tap: approve this device with Face ID or Touch ID (within 60 seconds).");
    } catch (e) {
      say("Not turned on: " + (e && e.message ? e.message : "no answer"));
    } finally {
      enable.disabled = false;
    }
  });

  approve.addEventListener("click", async function () {
    if (!pending) return;
    approve.disabled = true;
    try {
      var cred = await window.LCSPasskey.assertWith(pending.options);
      await window.LCSPasskey.post("/actions/push-subscribe/run", { input: pending.input, credential: cred });
      window.location.reload();
    } catch (e) {
      say("Not approved: " + (e && e.message ? e.message : "cancelled") + ". Tap Enable notifications to try again.");
      pending = null;
      show(approve, false);
      show(enable, true);
    } finally {
      approve.disabled = false;
    }
  });

  off.addEventListener("click", async function () {
    off.disabled = true;
    try {
      var sub = await current();
      if (sub) {
        var input = { id: await deviceId(sub.endpoint) };
        if (known.indexOf(input.id) !== -1) {
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
      off.disabled = false;
    }
  });

  refresh().catch(function () { say("Couldn't read this device's notification state."); });
})();
