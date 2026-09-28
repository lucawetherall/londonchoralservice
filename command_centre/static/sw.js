// LCS Command Centre service worker (served at /sw.js, scope /).
//
// - It never touches a write: any request that isn't a GET returns before anything else, so the browser sends
//   it straight to the server and nothing here sees, caches or replays it.
// - It caches the app shell (CSS, JS, icons) and the last copy of two pages, Today (/) and Money (/money), for
//   viewing with the VPN off. Those two are fetched with a 4-second timeout: when Tailscale is disconnected the
//   saved copy comes back quickly, with a banner "Offline, as of <time>". Every other page, /actions/, /auth/ and
//   the exports go to the network only, uncached.
// - Push: it shows the notification's title and body; a tap opens the payload's page (a same-origin path only).
"use strict";

var VERSION = "lcs-cc-v1";
var SHELL_CACHE = VERSION + "-shell";
var PAGE_CACHE = VERSION + "-pages";
var SHELL = [
  "/static/app.css", "/static/htmx.min.js", "/static/passkey.js", "/static/actions.js", "/static/handoffs.js",
  "/static/pwa.js", "/static/push.js", "/static/icons/icon-192.png", "/static/icons/icon-180.png"
];
var OFFLINE_PAGES = ["/", "/money"];
var TIMEOUT_MS = 4000;

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

// The saved page with a banner after <body>. The stamp is written here, never taken from the page.
async function offlineCopy(path) {
  var cache = await caches.open(PAGE_CACHE);
  var saved = await cache.match(path);
  if (!saved) {
    return new Response("<!doctype html><meta charset=utf-8><meta name=viewport content=\"width=device-width\">" +
      "<link rel=stylesheet href=\"/static/app.css\"><title>Offline</title><main class=main>" +
      "<p class=\"offline-banner\" role=status>Offline, and this page hasn't been saved yet. Connect Tailscale " +
      "and open it once.</p></main>", { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } });
  }
  var html = await saved.text();
  var banner = "<p class=\"offline-banner\" role=\"status\">Offline, as of " +
    stampText(saved.headers.get("X-CC-Saved-At")) + ". Connect Tailscale for live data; actions need it too.</p>";
  html = html.replace(/<body[^>]*>/i, function (tag) { return tag + banner; });
  var headers = { "Content-Type": "text/html; charset=utf-8" };
  var csp = saved.headers.get("Content-Security-Policy");
  if (csp) headers["Content-Security-Policy"] = csp;
  return new Response(html, { status: 200, headers: headers });
}

async function pageFirst(request, path) {
  try {
    var res = await withTimeout(fetch(request), TIMEOUT_MS);
    var type = res.headers.get("Content-Type") || "";
    if (res.ok && res.status === 200 && res.type === "basic" && type.indexOf("text/html") === 0) {
      var body = await res.clone().text();
      var headers = { "Content-Type": type, "X-CC-Saved-At": new Date().toISOString() };
      var csp = res.headers.get("Content-Security-Policy");
      if (csp) headers["Content-Security-Policy"] = csp;  // the offline copy keeps the page's own policy
      var copy = new Response(body, { headers: headers });
      (await caches.open(PAGE_CACHE)).put(path, copy);
    }
    return res;
  } catch (e) {
    return offlineCopy(path);
  }
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
