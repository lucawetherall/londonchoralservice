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
    assert "Offline, as of " in offline and "X-CC-Saved-At" in offline
    assert "Content-Security-Policy" in offline  # the saved copy keeps the page's policy
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
