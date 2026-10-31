#!/usr/bin/env python3
"""The cookie-free visit counter (js/counter.js, switched by LCS_COUNTER in partials/analytics.html).

- While LCS_COUNTER is empty the partial adds no script, and no built page names the counter's host.
- Once on, counter.js (run under node with a fake browser) counts the live site only, sends the page path
  without its query string (never an ad click ID or _gl), another site's referrer as its origin only and
  our own pages' referrer not at all, and only the four fixed enquiry-sent-* events.
- It skips Global Privacy Control, Do Not Track, automated browsers, the owner's lcs-internal devices and
  ?lcs_count=off, and writes nothing but that opt-out flag (no cookie, no sessionStorage).
- lcsLead (the generate_lead conversion) fires enquiry-sent-form; privacy.html describes the counter.

Stdlib only (node for the behaviour checks; skipped without node outside CI): python3 tests/test_visit_counter.py
"""
import glob, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTIAL = open(os.path.join(ROOT, "partials", "analytics.html")).read()
COUNTER = open(os.path.join(ROOT, "js", "counter.js")).read()
HOSTS = ("goatcounter.com", "gc.zgo.at")


def have_node():
    if shutil.which("node"):
        return True
    assert not os.environ.get("CI"), "node is needed in CI"
    print("skip: node not installed")
    return False


def loader():
    m = re.search(r"  <script>\n    var LCS_COUNTER = '[a-z0-9-]*';\n.*?  </script>", PARTIAL, re.S)
    assert m, "the LCS_COUNTER loader is missing from partials/analytics.html"
    return m.group(0).replace("<script>", "").replace("</script>", "")


def test_loader_adds_nothing_while_the_code_is_empty():
    assert PARTIAL.count("var LCS_COUNTER = ") == 1
    if not have_node():
        return
    for code, want in (("", []), ("lcs-test", ["/js/counter.js"])):
        js = re.sub(r"var LCS_COUNTER = '[a-z0-9-]*';", f"var LCS_COUNTER = '{code}';", loader())
        harness = ("var added = []; var document = { createElement: function () { return {}; },"
                   " head: { appendChild: function (s) { added.push(s.src); } } };"
                   + js + "console.log(JSON.stringify(added));")
        out = subprocess.run(["node", "-e", harness], capture_output=True, text=True, check=True).stdout
        assert json.loads(out) == want, (code, out)


def test_no_built_page_names_the_counter_host():
    pages = [p for p in glob.glob("**/*.html", root_dir=ROOT, recursive=True)
             if not p.startswith(("partials/", "graphify-out/", ".")) and "/." not in p]
    assert len(pages) > 150, len(pages)
    for p in pages:
        s = open(os.path.join(ROOT, p), encoding="utf-8").read()
        for host in HOSTS:
            assert host not in s, (p, host)
        if "@include-start partials/analytics.html" in s:
            assert "var LCS_COUNTER = " in s, p


HARNESS = r"""
var sc = JSON.parse(process.argv[1]);
var sent = [], store = Object.assign({}, sc.store || {}), handlers = {}, cookieTouched = false;
var win = { LCS_COUNTER: sc.code };
var loc = { hostname: sc.host, pathname: sc.path, search: sc.search, origin: 'https://' + sc.host };
var doc = { referrer: sc.referrer, readyState: 'complete', visibilityState: 'visible', title: 'Page title',
  addEventListener: function (t, f) { handlers[t] = f; } };
Object.defineProperty(doc, 'cookie', { get: function () { cookieTouched = true; return ''; },
  set: function () { cookieTouched = true; } });
var nav = { sendBeacon: function (u) { sent.push(u); return true; }, webdriver: !!sc.webdriver,
  globalPrivacyControl: sc.gpc, doNotTrack: sc.dnt };
var ls = { getItem: function (k) { return k in store ? store[k] : null; },
  setItem: function (k, v) { store[k] = String(v); }, removeItem: function (k) { delete store[k]; } };
(function (window, location, document, navigator, localStorage, sessionStorage) {
  SOURCE
})(win, loc, doc, nav, ls, undefined);
(sc.events || []).forEach(function (e) { if (win.lcsCount) win.lcsCount(e); });
function link(href) { return { closest: function () { return { getAttribute: function () { return href; } }; } }; }
(sc.taps || []).forEach(function (href) {
  if (handlers.click) handlers.click({ type: 'click', target: link(href) });
});
(sc.auxtaps || []).forEach(function (t) {
  if (handlers.auxclick) handlers.auxclick({ type: 'auxclick', button: t[1], target: link(t[0]) });
});
console.log(JSON.stringify({ sent: sent, store: store, cookie: cookieTouched }));
"""


def run(**sc):
    base = {"code": "lcs-test", "host": "londonchoralservice.com", "path": "/contact.html", "search": "",
            "referrer": "", "gpc": None, "dnt": None}
    base.update(sc)
    code = HARNESS.replace("SOURCE", COUNTER)
    out = subprocess.run(["node", "-e", code, json.dumps(base)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def params(url):
    from urllib.parse import urlsplit, parse_qs
    u = urlsplit(url)
    assert u.scheme == "https" and u.netloc == "lcs-test.goatcounter.com" and u.path == "/count", url
    return {k: v[0] for k, v in parse_qs(u.query).items()}


def test_page_view_sends_the_path_and_never_the_query_string():
    if not have_node():
        return
    r = run(search="?_gl=1*1sorl1z*_up*MQ..&gclid=SECRETCLICK&utm_source=google&occasion=wedding",
            referrer="https://londonchoralservice.com/weddings.html?gclid=SECRETCLICK")
    assert len(r["sent"]) == 1, r
    url = r["sent"][0]
    for leak in ("SECRETCLICK", "gclid", "_gl", "utm_", "occasion"):
        assert leak not in url, (leak, url)
    p = params(url)
    assert p["p"] == "/contact.html" and p["t"] == "Page title" and "r" not in p and "e" not in p, p
    assert not r["cookie"] and r["store"] == {}, r


def test_other_sites_referrer_is_sent_as_its_origin_only():
    if not have_node():
        return
    r = run(path="/index.html", referrer="https://www.google.com/search?q=wedding+choir+london")
    p = params(r["sent"][0])
    assert p["p"] == "/" and p["r"] == "https://www.google.com", p


def test_only_the_four_enquiry_events_are_sent():
    if not have_node():
        return
    r = run(search="?gclid=SECRETCLICK", events=["enquiry-sent-form", "someone@example.com", "toString"],
            taps=["tel:+442071234567", "mailto:office@londonchoralservice.com?subject=Hi",
                  "https://wa.me/447356042468?text=Hello"])
    hits = [params(u) for u in r["sent"]]
    assert [h["p"] for h in hits] == ["/contact.html", "enquiry-sent-form", "enquiry-sent-call",
                                      "enquiry-sent-email", "enquiry-sent-whatsapp"], hits
    for h in hits[1:]:
        assert h["e"] == "true" and h["r"] == "https://londonchoralservice.com/contact.html", h
    assert not any("SECRETCLICK" in u or "example.com" in u or "7356042468" in u for u in r["sent"]), r["sent"]


def test_middle_click_counts_and_right_click_does_not():
    if not have_node():
        return
    r = run(auxtaps=[["https://wa.me/447356042468", 2], ["mailto:office@londonchoralservice.com", 1]])
    assert [params(u)["p"] for u in r["sent"]] == ["/contact.html", "enquiry-sent-email"], r["sent"]


def test_nothing_is_counted_off_the_live_site_or_without_a_code():
    if not have_node():
        return
    assert run(host="localhost")["sent"] == []
    assert run(host="lucawetherall.github.io")["sent"] == []
    assert run(code="")["sent"] == []
    assert run(code="bad code/../x")["sent"] == []


def test_opt_outs_are_honoured():
    if not have_node():
        return
    assert run(gpc=True)["sent"] == []
    assert run(dnt="1")["sent"] == []
    assert run(webdriver=True)["sent"] == []
    assert run(store={"lcs-internal": "1"})["sent"] == []
    off = run(search="?lcs_count=off", events=["enquiry-sent-form"])
    assert off["sent"] == [] and off["store"] == {"lcs-count-off": "1"}, off
    assert run(store={"lcs-count-off": "1"})["sent"] == []
    on = run(search="?lcs_count=on", store={"lcs-count-off": "1"})
    assert len(on["sent"]) == 1 and on["store"] == {}, on


def test_counter_never_touches_cookies_or_session_storage():
    for banned in ("document.cookie", "sessionStorage", "location.href", "location.search +", "fetch("):
        assert banned not in COUNTER, banned
    assert re.findall(r"setItem\('([^']+)'", COUNTER) == ["lcs-count-off"]


def test_lead_fires_the_form_event_and_privacy_explains_it():
    start = PARTIAL.index("function lcsLead(")
    body = PARTIAL[start:PARTIAL.index("\n    }\n", start)]
    assert "window.lcsCount('enquiry-sent-form')" in body
    s = open(os.path.join(ROOT, "privacy.html")).read()
    assert 'id="visit-counter"' in s and 'href="/privacy.html?lcs_count=off#visit-counter"' in s


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:  # an error is a failure too
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
