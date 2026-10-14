#!/usr/bin/env python3
"""Ad attribution without cookies (spec docs/superpowers/specs/2026-10-14-cookieless-ad-attribution.md).

- The ad-visit slug partials/analytics.html writes (run under node) names a page and fits the pattern
  scripts/bookings/pipeline.py accepts, for every page the site serves.
- The ad-visit code never stores anything (no localStorage/sessionStorage write, no cookie).
- Every enquiry form carries the optional, unticked ad-measurement box, inside the form and before the
  captcha, and keeps its honeypot and captcha.
- Both form scripts send ad_visit, and the URL's click IDs only with the box ticked.

Stdlib only (node for the slug check; skipped without node outside CI): python3 tests/test_ad_attribution.py
"""
import glob, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import pipeline  # noqa: E402

PARTIAL = open(os.path.join(ROOT, "partials", "analytics.html")).read()
BOX_TEXT = ("Let us tell Google if your booking came from one of its ads. Google receives a scrambled (hashed) "
            "copy of your email address, never the address itself.")


def slug_fn():
    m = re.search(r"    function lcsAdVisitSlug\(path\) \{.*?\n    \}\n", PARTIAL, re.S)
    assert m, "lcsAdVisitSlug not found in partials/analytics.html"
    return m.group(0)


def js_slugs(paths):
    code = slug_fn() + f"console.log(JSON.stringify({json.dumps(paths)}.map(lcsAdVisitSlug)));"
    return json.loads(subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout)


def have_node():
    if shutil.which("node"):
        return True
    assert not os.environ.get("CI"), "node is needed in CI"
    print("skip: node not installed")
    return False


def test_slugs():
    if not have_node():
        return
    cases = {"/weddings.html": "weddings", "/": "home", "/index.html": "home", "/funerals": "funerals",
             "/areas/london/camden.html": "areas/london/camden", "/destinations/": "destinations",
             "/destinations/index.html": "destinations", "/Carol-Singers.HTML": "carol-singers",
             "/a%20b.html": "other", "/x.html?gclid=1": "other", "": "home"}
    assert js_slugs(list(cases)) == list(cases.values()), dict(zip(cases, js_slugs(list(cases))))


def test_every_served_page_gives_a_slug_the_pipeline_accepts():
    if not have_node():
        return
    listed = subprocess.run([sys.executable, "scripts/stage_site.py", "--list"], cwd=ROOT, capture_output=True,
                            text=True, check=True).stdout.split()
    pages = ["/" + p for p in listed if p.endswith(".html")]
    assert len(pages) > 150, len(pages)
    for page, slug in zip(pages, js_slugs(pages)):
        assert slug != "other" and pipeline.AD_VISIT_RE.fullmatch(slug), (page, slug)


def test_ad_visit_is_held_in_a_variable_and_never_stored():
    start = PARTIAL.index("function lcsAdVisitSlug")
    block = PARTIAL[start:PARTIAL.index("</script>", start)]
    for banned in ("setItem", "sessionStorage", "document.cookie", "fetch(", "sendBeacon", "gtag("):
        assert banned not in block, banned
    assert "var LCS_AD_VISIT = " in block and "'granted') return ''" in block
    # messages: the Ref with consent, else the page's name; never the click ID itself
    assert "var visit = ref ? '' : lcsAdVisit();" in PARTIAL
    assert "'Ad visit: ' + visit" in PARTIAL


def form_pages():
    out = []
    for p in sorted(glob.glob("**/*.html", root_dir=ROOT, recursive=True)):
        if p.startswith(("partials/", "command_centre/", ".")) or "/." in p:
            continue
        s = open(os.path.join(ROOT, p)).read()
        if 'class="contact-form"' in s or 'id="pe-enquiry"' in s:
            out.append((p, s))
    return out


def test_every_enquiry_form_has_the_unticked_box_before_the_captcha():
    pages = form_pages()
    assert len(pages) >= 39, [p for p, _ in pages]  # 14 main-site forms, private-events, planners, 23 destinations
    for p, s in pages:
        start, end = s.index("<form"), s.index("</form>")
        boxes = re.findall(r'<input[^>]*name="ad_measurement"[^>]*>', s)
        assert len(boxes) == 1, (p, boxes)
        box = boxes[0]
        assert 'type="checkbox"' in box and 'value="yes"' in box and "checked" not in box, (p, box)
        assert "required" not in box, (p, box)
        i = s.index(box)
        assert start < i < s.index('class="h-captcha"') < end, p
        assert BOX_TEXT in s[i:i + 600], p
        assert 'href="/privacy.html#ad-measurement"' in s[i:i + 900], p
        assert 'name="botcheck"' in s[start:end] and 'class="h-captcha"' in s[start:end], p


def test_privacy_policy_explains_both():
    s = open(os.path.join(ROOT, "privacy.html")).read()
    assert 'id="ad-measurement"' in s and "Ad visit: weddings" in s


def test_form_scripts_send_ad_visit_and_click_ids_only_with_the_box():
    for name in ("form.js", "private-events.js"):
        s = open(os.path.join(ROOT, "js", name)).read()
        assert "data.ad_visit = visit" in s, name
        assert "data.ad_measurement === 'yes' && typeof window.lcsClickIds === 'function'" in s, name
        assert "setItem" not in s and "document.cookie" not in s, name
        # the honeypot and captcha guards stay
        assert "h-captcha-response" in s and "api.web3forms.com/submit" in s, name


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
