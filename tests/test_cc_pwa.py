#!/usr/bin/env python3
"""Tests for the Command Centre's installable app (phase 5): the manifest, the service worker, the icons, the CSP and
the base template's links. Stdlib runner, Starlette's TestClient, a temp LCS_PRIVATE_DIR.
"""
import json, os, re, struct, sys, tempfile, zlib
from pathlib import Path

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
os.environ["CC_VAPID_STORE"] = "file"
os.environ.pop("CC_DEV_LOGIN", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from starlette.testclient import TestClient  # noqa: E402

from command_centre import auth, pwa  # noqa: E402
from command_centre.app import create_app  # noqa: E402

LOGIN = "owner@example.org"
HOST = "mac.example-tailnet.ts.net"
ORIGIN = f"https://{HOST}"
HEADERS = {"Tailscale-User-Login": LOGIN, "Tailscale-User-Name": "Owner"}
SW = Path(ROOT) / "command_centre" / "static" / "sw.js"


def client():
    auth.save_config({"allowed_logins": [LOGIN], "origin": ORIGIN, "rp_id": HOST, "passkeys": []})
    app = create_app(client_factory=lambda: None, checkout=lambda: "main")
    return TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000), follow_redirects=False)


def test_manifest_is_served_with_its_type_and_fields():
    c = client()
    r = c.get("/manifest.webmanifest", headers=HEADERS)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/manifest+json")
    m = r.json()
    assert m["name"] == "LCS Command Centre" and m["short_name"] == "LCS"
    assert m["display"] == "standalone" and m["start_url"] == "/" and m["scope"] == "/"
    assert m["theme_color"] == "#8B3A3A" and m["background_color"] == "#F7F3EE"
    for icon in m["icons"]:
        assert icon["src"].startswith("/static/icons/") and icon["type"] == "image/png"
        assert c.get(icon["src"], headers=HEADERS).status_code == 200
    assert any(i.get("purpose") == "maskable" for i in m["icons"])
    assert not re.search(r"https?://", json.dumps(m))  # nothing from another origin
    # like every page, it needs the owner's identity
    assert c.get("/manifest.webmanifest").status_code == 403


def test_service_worker_is_served_from_the_root_with_its_headers():
    c = client()
    r = c.get("/sw.js", headers=HEADERS)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/javascript")
    assert r.headers["service-worker-allowed"] == "/"
    assert r.headers["cache-control"] == "no-store"
    assert r.content == SW.read_bytes()
    assert c.get("/sw.js").status_code == 403


def test_csp_allows_the_worker_and_manifest_from_self_only():
    c = client()
    csp = c.get("/sw.js", headers=HEADERS).headers["content-security-policy"]
    assert "worker-src 'self'" in csp and "manifest-src 'self'" in csp
    assert "script-src 'self'" in csp and "unsafe" not in csp


def js_body(fn, text):
    """The source of `function <fn>(...) {...}` or `"<event>", function (event) {...}` (brace-matched)."""
    start = text.index(fn)
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        if depth == 0:
            return text[i:j + 1]
    raise AssertionError(fn)


def test_the_worker_never_touches_a_post_and_caches_only_the_shell_and_two_pages():
    text = SW.read_text()
    fetch = js_body('addEventListener("fetch"', text)
    first = fetch.strip("{} \n").splitlines()[0:2]
    # the method check comes before anything else, and returns (the browser handles the request itself)
    assert 'if (request.method !== "GET") return;' in first[1], first
    assert fetch.index('request.method !== "GET"') < fetch.index("respondWith")
    # cache.put only in the GET-only helpers; nothing writes to a cache for any other method
    assert text.count("cache.put(") + text.count(".put(") >= 2
    assert re.search(r'OFFLINE_PAGES = \["/", "/money"\]', text)
    code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//"))
    for never in ("/actions", "/auth", "/exports", "/todo/tick"):
        assert f"\"{never}" not in code, never  # no path starting with these in the code
    # the two pages only when navigated to exactly, with no query
    assert 'request.mode === "navigate" && url.search === ""' in fetch
    # same origin only
    assert "url.origin !== self.location.origin" in fetch


def test_the_worker_falls_back_fast_with_an_offline_stamp():
    text = SW.read_text()
    assert "var TIMEOUT_MS = 4000;" in text
    page = js_body("async function pageFirst", text)
    assert "withTimeout(fetch(request), TIMEOUT_MS)" in page and "offlineCopy(path)" in page
    offline = js_body("async function offlineCopy", text)
    assert "Couldn't reach the Mac (showing the copy from " in offline and "Offline, as of" not in text
    assert "savedAge(saved)" in offline and "age > MAX_AGE_MS" in offline and "cache.delete(path)" in offline
    assert "var MAX_AGE_MS = 7 * 24 * 3600 * 1000;" in text and "X-CC-Saved-At" in js_body("function savedAge", text)
    assert "Content-Security-Policy" in offline  # the saved copy keeps the page's policy
    # a 401 or 403 for either page deletes the saved pages
    assert "res.status === 401 || res.status === 403" in page and "await clearPages()" in page
    assert "caches.delete(PAGE_CACHE)" in js_body("function clearPages", text)
    # the clear message: only {type: "clear-offline"}, only from a window of this origin
    msg = js_body('addEventListener("message"', text)
    assert 'd.type !== "clear-offline"' in msg and "self.location.origin" in msg and "clearPages()" in msg
    # a notification tap only opens a same-origin path
    assert "safePath" in js_body('addEventListener("notificationclick"', text)


def read_png(body):
    assert body[:8] == b"\x89PNG\r\n\x1a\n"
    pos, chunks = 8, {}
    while pos < len(body):
        n = struct.unpack(">I", body[pos:pos + 4])[0]
        kind = body[pos + 4:pos + 8]
        data = body[pos + 8:pos + 8 + n]
        assert struct.unpack(">I", body[pos + 8 + n:pos + 12 + n])[0] == zlib.crc32(kind + data) & 0xFFFFFFFF
        chunks[kind] = data
        pos += 12 + n
    w, h = struct.unpack(">II", chunks[b"IHDR"][:8])
    zlib.decompress(chunks[b"IDAT"])
    return w, h


def test_icons_are_valid_pngs_in_step_with_the_drawing_code():
    drawn = pwa.icon_bytes()
    for name, size, _, _ in pwa.SIZES:
        path = Path(ROOT) / "command_centre" / "static" / "icons" / name
        body = path.read_bytes()
        assert read_png(body) == (size, size), name
        assert body == drawn[name], f"{name} differs from pwa.py: run python -m command_centre.pwa"


def test_base_template_links_the_manifest_worker_and_install_hint():
    c = client()
    page = c.get("/", headers=HEADERS).text
    assert '<link rel="manifest" href="/manifest.webmanifest">' in page
    assert '<link rel="apple-touch-icon" href="/static/icons/icon-180.png">' in page
    assert '<script src="/static/pwa.js" defer></script>' in page
    assert 'id="cc-install-hint" hidden' in page
    assert 'href="/device"' in page
    pwa_js = (Path(ROOT) / "command_centre" / "static" / "pwa.js").read_text()
    assert 'register("/sw.js", { scope: "/" })' in pwa_js


NODE_HARNESS = r'''
// Runs sw.js in a vm context with fake caches, fetch and clients; prints one JSON line of results.
const vm = require("vm"), fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const ORIGIN = "https://mac.example-tailnet.ts.net";
const stores = new Map();
function store(name) {
  if (!stores.has(name)) stores.set(name, new Map());
  const m = stores.get(name);
  return {
    match: async (k) => { const r = m.get(k); return r ? r.clone() : undefined; },
    put: async (k, r) => { m.set(k, r); },
    delete: async (k) => m.delete(k),
  };
}
const caches = {
  open: async (n) => store(n), delete: async (n) => stores.delete(n), keys: async () => [...stores.keys()],
};
let next = null;  // what the fake network does next: a function returning a Response, or throwing
async function fakeFetch(req) { return next(req); }
function page(status, body) {
  const r = new Response(body || "<html><body class=x><h1>Today</h1></body></html>",
    { status, headers: { "Content-Type": "text/html; charset=utf-8", "Content-Security-Policy": "default-src 'self'" } });
  Object.defineProperty(r, "type", { value: "basic" });
  return r;
}
const handlers = {};
const self = {
  location: { origin: ORIGIN }, addEventListener: (t, f) => { handlers[t] = f; },
  registration: {}, clients: {}, skipWaiting: () => {},
};
let now = Date.parse("2026-09-28T12:00:00Z");
class FakeDate extends Date {
  constructor(...a) { if (a.length === 0) { super(now); } else { super(...a); } }
  static now() { return now; }
}
const ctx = { self, caches, fetch: fakeFetch, Response, URL, setTimeout, clearTimeout, Promise, Date: FakeDate, console };
vm.createContext(ctx);
vm.runInContext(src, ctx);
const PAGES = "lcs-cc-v2-pages";

async function nav(path) {
  let out;
  handlers.fetch({ request: { method: "GET", url: ORIGIN + path, mode: "navigate" }, respondWith: (p) => { out = p; } });
  const res = await out;
  return { status: res.status, text: await res.text() };
}
function has(path) { return stores.has(PAGES) && stores.get(PAGES).has(path); }
async function message(data, url) {
  let waited; const got = [];
  handlers.message({ data, source: { url }, ports: [{ postMessage: (m) => got.push(m) }], waitUntil: (p) => { waited = p; } });
  if (waited) await waited;
  return got.length;
}

(async () => {
  const r = {};
  next = () => page(200);
  r.live = await nav("/");
  r.savedAfterLive = has("/");
  await nav("/money");
  next = () => { throw new TypeError("offline"); };
  now += 3600 * 1000;
  r.offline = await nav("/");
  r.offlineMoney = await nav("/money");
  next = () => page(401, "no");
  r.unauth = await nav("/money");
  r.savedAfter401 = has("/") || has("/money");
  next = () => page(200); await nav("/");
  next = () => page(403, "no"); await nav("/");
  r.savedAfter403 = has("/");
  next = () => page(200); await nav("/");
  now += 8 * 24 * 3600 * 1000;
  next = () => { throw new TypeError("offline"); };
  r.stale = await nav("/");
  r.savedAfterStale = has("/");
  now -= 8 * 24 * 3600 * 1000;
  next = () => page(200); await nav("/"); await nav("/money");
  r.foreignClear = await message({ type: "clear-offline" }, "https://evil.example/");
  r.savedAfterForeign = has("/");
  r.otherMessage = await message({ type: "something" }, ORIGIN + "/device");
  r.clear = await message({ type: "clear-offline" }, ORIGIN + "/device");
  r.savedAfterClear = has("/") || has("/money");
  console.log(JSON.stringify(r));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
'''


def test_the_worker_logic_runs_in_node():
    """sw.js itself, in node's vm with fake caches and network: the copy, its banner, the 401/403 wipe, the 7-day
    expiry and the clear message. Skipped (the static checks above still run) when node isn't installed."""
    import shutil, subprocess
    node = shutil.which("node")
    if not node:
        print("SKIP test_the_worker_logic_runs_in_node: node not found")
        return
    harness = Path(tempfile.mkdtemp()) / "sw_harness.js"
    harness.write_text(NODE_HARNESS)
    r = subprocess.run([node, str(harness), str(SW)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout.strip().splitlines()[-1])
    assert got["live"]["status"] == 200 and got["savedAfterLive"] is True
    assert got["offline"]["status"] == 200
    assert "Couldn't reach the Mac (showing the copy from " in got["offline"]["text"]
    assert "<h1>Today</h1>" in got["offline"]["text"] and got["offlineMoney"]["status"] == 200
    assert got["unauth"]["status"] == 401 and got["savedAfter401"] is False
    assert got["savedAfter403"] is False
    assert got["stale"]["status"] == 503 and "no copy of this page from the last 7 days" in got["stale"]["text"]
    assert got["savedAfterStale"] is False
    assert got["foreignClear"] == 0 and got["savedAfterForeign"] is True and got["otherMessage"] == 0
    assert got["clear"] == 1 and got["savedAfterClear"] is False


def test_device_page_has_the_clear_button_and_turning_off_clears():
    c = client()
    page = c.get("/device", headers=HEADERS).text
    assert 'id="offline-clear"' in page and "Clear offline copies" in page
    assert "lock-screen previews" in page
    js = (Path(ROOT) / "command_centre" / "static" / "push.js").read_text()
    assert 'postMessage({ type: "clear-offline" }' in js
    off = js[js.index('off.addEventListener("click"'):]
    assert "await clearOffline()" in off


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"PASS {name}")
        except Exception as ex:
            failures += 1
            import traceback
            traceback.print_exc()
            print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
