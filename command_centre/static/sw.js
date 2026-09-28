// LCS Command Centre service worker (served at /sw.js, scope /).
//
// - It never touches a write: any request that isn't a GET returns before anything else, so the browser sends
//   it straight to the server and nothing here sees, caches or replays it.
// - It caches the app shell (CSS, JS, icons) and the last copy of two pages, Today (/) and Money (/money), for
//   viewing with the VPN off. Those two are fetched with a 4-second timeout: when Tailscale is disconnected the
//   saved copy comes back quickly, with a banner "Couldn't reach the Mac (showing the copy from <time>)". Every
//   other page, /actions/, /auth/ and the exports go to the network only, uncached.
// - The saved copies expire: one older than 7 days (its X-CC-Saved-At stamp) is deleted, not shown; a 401 or 403
//   answer for either page deletes both (signed out or refused: nothing stays on the phone); and a
//   {type: "clear-offline"} message from a page of this origin deletes them (the /device page's "Clear offline
//   copies" button, and turning notifications off).
// - Push: it shows the notification's title and body; a tap opens the payload's page (a same-origin path only).
"use strict";

var VERSION = "lcs-cc-v2";
var SHELL_CACHE = VERSION + "-shell";
var PAGE_CACHE = VERSION + "-pages";
var SHELL = [
  "/static/app.css", "/static/htmx.min.js", "/static/passkey.js", "/static/actions.js", "/static/handoffs.js",
  "/static/pwa.js", "/static/push.js", "/static/icons/icon-192.png", "/static/icons/icon-180.png"
];
var OFFLINE_PAGES = ["/", "/money"];
var TIMEOUT_MS = 4000;
var MAX_AGE_MS = 7 * 24 * 3600 * 1000;  // an offline copy older than this is deleted, never shown
var SKEW_MS = 5 * 60 * 1000;

self.addEventListener("install", function (event) {
  event.waitUntil(caches.open(SHELL_CACHE).then(function (cache) {
    return Promise.all(SHELL.map(function (path) {
      return fetch(path, { cache: "no-store" }).then(function (res) {
        if (res.ok) return cache.put(path, res);
      }).catch(function () { /* offline at install: filled on the next visit */ });
    }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (event) {
  event.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k.indexOf(VERSION) !== 0; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function withTimeout(promise, ms) {
  return new Promise(function (resolve, reject) {
    var timer = setTimeout(function () { reject(new Error("timeout")); }, ms);
    promise.then(function (v) { clearTimeout(timer); resolve(v); },
                 function (e) { clearTimeout(timer); reject(e); });
  });
}

function stampText(iso) {
  var d = new Date(iso);
  if (isNaN(d.getTime())) return "an unknown time";
  return d.toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit",
                                     minute: "2-digit", timeZone: "Europe/London" });
}

function clearPages() {
  return caches.delete(PAGE_CACHE);
}

// A saved copy's age from its stamp, or null when the stamp is missing, unreadable or in the future.
function savedAge(res) {
  var at = Date.parse(res.headers.get("X-CC-Saved-At") || "");
  if (isNaN(at)) return null;
  var age = Date.now() - at;
  return age < -SKEW_MS ? null : age;
}

function noCopy() {
  return new Response("<!doctype html><meta charset=utf-8><meta name=viewport content=\"width=device-width\">" +
    "<link rel=stylesheet href=\"/static/app.css\"><title>Couldn't reach the Mac</title><main class=main>" +
    "<p class=\"offline-banner\" role=status>Couldn't reach the Mac, and there's no copy of this page from the " +
    "last 7 days. Connect Tailscale and open it once.</p></main>",
    { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } });
}

// The saved page with a banner after <body>. The stamp is written here, never taken from the page. A copy older
// than MAX_AGE_MS (or with no readable stamp) is deleted instead.
async function offlineCopy(path) {
  var cache = await caches.open(PAGE_CACHE);
  var saved = await cache.match(path);
  if (!saved) return noCopy();
  var age = savedAge(saved);
  if (age === null || age > MAX_AGE_MS) {
    await cache.delete(path);
    return noCopy();
  }
  var html = await saved.text();
  var banner = "<p class=\"offline-banner\" role=\"status\">Couldn't reach the Mac (showing the copy from " +
    stampText(saved.headers.get("X-CC-Saved-At")) + "). Connect Tailscale for live data; actions need it too.</p>";
  html = html.replace(/<body[^>]*>/i, function (tag) { return tag + banner; });
  var headers = { "Content-Type": "text/html; charset=utf-8" };
  var csp = saved.headers.get("Content-Security-Policy");
  if (csp) headers["Content-Security-Policy"] = csp;
  return new Response(html, { status: 200, headers: headers });
}

async function pageFirst(request, path) {
  var res;
  try {
    res = await withTimeout(fetch(request), TIMEOUT_MS);
  } catch (e) {
    return offlineCopy(path);
  }
  if (res.status === 401 || res.status === 403) {
    await clearPages();  // signed out or refused: no saved page stays on the phone
    return res;
  }
  var type = res.headers.get("Content-Type") || "";
  if (res.ok && res.status === 200 && res.type === "basic" && type.indexOf("text/html") === 0) {
    try {
      var body = await res.clone().text();
      var headers = { "Content-Type": type, "X-CC-Saved-At": new Date().toISOString() };
      var csp = res.headers.get("Content-Security-Policy");
      if (csp) headers["Content-Security-Policy"] = csp;  // the offline copy keeps the page's own policy
      await (await caches.open(PAGE_CACHE)).put(path, new Response(body, { headers: headers }));
    } catch (e) { /* no copy this time; the live page is still shown */ }
  }
  return res;
}

async function shellFirst(request, path) {
  try {
    var res = await withTimeout(fetch(request), TIMEOUT_MS);
    if (res.ok && res.type === "basic") (await caches.open(SHELL_CACHE)).put(path, res.clone());
    return res;
  } catch (e) {
    var hit = await (await caches.open(SHELL_CACHE)).match(path);
    if (hit) return hit;
    throw e;
  }
}

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET") return;  // writes (POST and the rest) are never touched, cached or replayed
  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  var path = url.pathname;
  if (request.mode === "navigate" && url.search === "" && OFFLINE_PAGES.indexOf(path) !== -1) {
    event.respondWith(pageFirst(request, path));
  } else if (SHELL.indexOf(path) !== -1 && url.search === "") {
    event.respondWith(shellFirst(request, path));
  }
  // anything else: the network, uncached
});

// "Clear offline copies" (/device) and turning notifications off: only from a window of this origin.
self.addEventListener("message", function (event) {
  var d = event.data;
  if (!d || d.type !== "clear-offline") return;
  var src = event.source;
  if (!src || typeof src.url !== "string" || new URL(src.url).origin !== self.location.origin) return;
  event.waitUntil(clearPages().then(function () {
    if (event.ports && event.ports[0]) event.ports[0].postMessage({ cleared: true });
  }));
});

function safePath(value) {
  return typeof value === "string" && /^\/(?!\/)[A-Za-z0-9\/_-]{0,64}$/.test(value) ? value : "/";
}

self.addEventListener("push", function (event) {
  var d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = {}; }
  var title = typeof d.title === "string" && d.title ? d.title.slice(0, 60) : "LCS Command Centre";
  var body = typeof d.body === "string" ? d.body.slice(0, 120) : "";
  event.waitUntil(self.registration.showNotification(title, {
    body: body, icon: "/static/icons/icon-192.png", badge: "/static/icons/icon-192.png",
    data: { url: safePath(d.url) }
  }));
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  var path = safePath(event.notification.data && event.notification.data.url);
  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (list) {
    for (var i = 0; i < list.length; i++) {
      var c = list[i];
      if (new URL(c.url).origin === self.location.origin && "focus" in c) {
        return c.focus().then(function (w) { return w && "navigate" in w ? w.navigate(path) : w; });
      }
    }
    return self.clients.openWindow(path);
  }));
});
