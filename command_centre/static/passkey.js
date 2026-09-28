// Passkey registration and assertion for the Command Centre. Same-origin fetches only; no inline code.
(function () {
  "use strict";

  function b64urlToBuf(s) {
    s = s.replace(/-/g, "+").replace(/_/g, "/");
    while (s.length % 4) s += "=";
    var bin = atob(s), out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out.buffer;
  }

  function bufToB64url(buf) {
    var bytes = new Uint8Array(buf), bin = "";
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function creationOptions(o) {
    if (window.PublicKeyCredential && PublicKeyCredential.parseCreationOptionsFromJSON) {
      return PublicKeyCredential.parseCreationOptionsFromJSON(o);
    }
    var p = Object.assign({}, o);
    p.challenge = b64urlToBuf(o.challenge);
    p.user = Object.assign({}, o.user, { id: b64urlToBuf(o.user.id) });
    p.excludeCredentials = (o.excludeCredentials || []).map(function (c) {
      return Object.assign({}, c, { id: b64urlToBuf(c.id) });
    });
    return p;
  }

  function requestOptions(o) {
    if (window.PublicKeyCredential && PublicKeyCredential.parseRequestOptionsFromJSON) {
      return PublicKeyCredential.parseRequestOptionsFromJSON(o);
    }
    var p = Object.assign({}, o);
    p.challenge = b64urlToBuf(o.challenge);
    p.allowCredentials = (o.allowCredentials || []).map(function (c) {
      return Object.assign({}, c, { id: b64urlToBuf(c.id) });
    });
    return p;
  }

  function credentialJSON(cred) {
    if (typeof cred.toJSON === "function") return cred.toJSON();
    var r = cred.response, out = { id: cred.id, rawId: bufToB64url(cred.rawId), type: cred.type, response: {} };
    out.response.clientDataJSON = bufToB64url(r.clientDataJSON);
    if (r.attestationObject) {
      out.response.attestationObject = bufToB64url(r.attestationObject);
      if (r.getTransports) out.response.transports = r.getTransports();
    }
    if (r.authenticatorData) out.response.authenticatorData = bufToB64url(r.authenticatorData);
    if (r.signature) out.response.signature = bufToB64url(r.signature);
    if (r.userHandle) out.response.userHandle = bufToB64url(r.userHandle);
    out.clientExtensionResults = cred.getClientExtensionResults ? cred.getClientExtensionResults() : {};
    return out;
  }

  async function post(path, body) {
    var res = await fetch(path, {
      method: "POST", credentials: "same-origin", cache: "no-store",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {})
    });
    var data = {};
    try { data = await res.json(); } catch (e) { /* not JSON */ }
    if (!res.ok) throw new Error(data.error || ("refused (" + res.status + ")"));
    return data;
  }

  // A fresh assertion bound to `action`: the server's challenge embeds a hash of it and lasts 60 seconds.
  async function assertFor(action) {
    var opts = await post("/auth/passkey/assert/options", { action: action });
    var cred = await navigator.credentials.get({ publicKey: requestOptions(opts) });
    return credentialJSON(cred);
  }

  var box = document.getElementById("passkeys");
  if (!box) return;
  var status = document.getElementById("pk-status");
  function say(text) { status.textContent = text; }

  var reg = document.getElementById("pk-register");
  if (reg) reg.addEventListener("click", async function () {
    try {
      var body = {};
      if (box.dataset.hasKeys === "yes") {
        say("First, confirm with a passkey you already have.");
        body.assertion = await assertFor(box.dataset.registerSummary);
      }
      var opts = await post("/auth/passkey/register/options", body);
      say("Now create the passkey on this device.");
      var cred = await navigator.credentials.create({ publicKey: creationOptions(opts) });
      await post("/auth/passkey/register", { credential: credentialJSON(cred) });
      say("Passkey registered. Reloading.");
      window.location.reload();
    } catch (e) {
      say("Not registered: " + (e && e.message ? e.message : "cancelled"));
    }
  });

  var test = document.getElementById("pk-test");
  if (test) test.addEventListener("click", async function () {
    try {
      var action = "check passkey";
      var cred = await assertFor(action);
      await post("/auth/passkey/assert", { action: action, credential: cred });
      say("Passkey accepted.");
    } catch (e) {
      say("Not accepted: " + (e && e.message ? e.message : "cancelled"));
    }
  });
})();
