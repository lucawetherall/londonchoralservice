#!/usr/bin/env python3
"""Ad attribution without cookies (specs docs/superpowers/specs/2026-10-14-cookieless-ad-attribution.md and
2026-10-23-cookieless-ad-source-design.md).

- The ad-visit slug partials/analytics.html writes (run under node) names a page and fits the pattern
  scripts/bookings/pipeline.py accepts, for every page the site serves.
- The ad-visit label adds the ad's campaign ("pricing (wedding-leads)"), travels to the next page only in
  same-site page links (lcs_av), and is read back only when the visitor came from one of our pages.
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
BOX_TEXT = "Let us tell Google if your booking came from its ads, using a scrambled copy of your email."


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


def js_fn(name):
    m = re.search(r"    function " + name + r"\(.*?\n    \}\n", PARTIAL, re.S)
    assert m, f"{name} not found in partials/analytics.html"
    return m.group(0)


ORIGIN = "https://londonchoralservice.com"


def js_run(setup, expr):
    """Run the partial's ad-visit functions under node with a fake page (location, document.referrer,
    localStorage) and return JSON.stringify(expr)."""
    keys = re.search(r"var LCS_ATTR_KEYS = [^;]+;", PARTIAL).group(0)
    code = ("var store = {}; var localStorage = {getItem: function (k) { return k in store ? store[k] : null; }};"
            "var saved = {}; var sessionStorage = {getItem: function (k) { return k in saved ? saved[k] : null; }};"
            + keys + setup + "\n" + js_fn("lcsAttribution") + js_fn("lcsAdVisitSlug") + js_fn("lcsAdVisitLabel")
            + js_fn("lcsAdVisit")
            + js_fn("lcsCarryAdVisit") + "var LCS_AD_VISIT = lcsAdVisitLabel();\n"
            + f"console.log(JSON.stringify({expr}));")
    return json.loads(subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout)


def page(path, search, referrer=""):
    return (f"var location = {{pathname: {json.dumps(path)}, search: {json.dumps(search)}, origin: {json.dumps(ORIGIN)}, "
            f"href: {json.dumps(ORIGIN + path + search)}}}; var document = {{referrer: {json.dumps(referrer)}}};")


def test_ad_visit_label_names_the_page_and_campaign_and_travels_only_between_our_pages():
    if not have_node():
        return
    here = ORIGIN + "/pricing.html"
    cases = [
        (("/pricing.html", "?gclid=Cj0KCQjw&utm_source=google&utm_medium=cpc&utm_campaign=wedding-leads"),
         "pricing (wedding-leads)"),
        (("/funerals.html", "?gbraid=0AAAAA&utm_campaign=funeral-expert"), "funerals (funeral-expert)"),
        (("/", "?wbraid=CkEKCQ&utm_campaign=christmas-carol-singers-2026"), "home (christmas-carol-singers-2026)"),
        (("/pricing.html", "?gclid=Cj0KCQjw"), "pricing"),
        (("/pricing.html", "?gclid=Cj0KCQjw&utm_campaign=Wedding%20Leads"), "pricing"),
        (("/pricing.html", "?gclid=Cj0KCQjw&utm_campaign=" + "a" * 41), "pricing"),
        (("/pricing.html", "?gclid=Cj0KCQjw&utm_campaign=x%3Cscript%3E"), "pricing"),
        (("/pricing.html", "?utm_campaign=wedding-leads"), ""),  # no click ID: not an ad visit
        (("/contact.html", "?lcs_av=pricing+%28wedding-leads%29", here), "pricing (wedding-leads)"),
        (("/contact.html", "?lcs_av=pricing%20(wedding-leads)", here), "pricing (wedding-leads)"),
        (("/contact.html", "?lcs_av=weddings", here), "weddings"),
        (("/contact.html", "?lcs_av=pricing+%28wedding-leads%29", ""), ""),  # typed, bookmarked or shared
        (("/contact.html", "?lcs_av=pricing+%28wedding-leads%29", "https://example.com/x"), ""),
        (("/contact.html", "?lcs_av=Ann+Smith", here), ""),
        (("/contact.html", "?lcs_av=pricing+%28wedding-leads%29%3Cb%3E", here), ""),
        (("/contact.html", "?lcs_av=pricing+%28Cj0KCQjw_A%29", here), ""),
        (("/contact.html", "?lcs_av=" + "a" * 81 + "+%28" + "b" * 40 + "%29", here), ""),
        (("/weddings.html", "?gclid=Cj0KCQjw&utm_campaign=wedding-leads&lcs_av=pricing", here),
         "weddings (wedding-leads)"),  # a new ad click starts a new visit
    ]
    for (path, search, *ref), want in cases:
        got = js_run(page(path, search, ref[0] if ref else ""), "LCS_AD_VISIT")
        assert got == want, (path, search, ref, got, want)
        assert "cj0kcqjw" not in got.lower()
        if got:
            assert pipeline.AD_VISIT_RE.fullmatch(got), got
    granted = "store['lcs-consent'] = 'granted';" + page("/pricing.html", "?gclid=X&utm_campaign=wedding-leads")
    assert js_run(granted, "[LCS_AD_VISIT, lcsAdVisit()]") == ["pricing (wedding-leads)", ""]
    # Allowed on a later page: no click ID is left (nothing was stored before consent), so the label stays
    later = "store['lcs-consent'] = 'granted';" + page("/contact.html", "?lcs_av=pricing+%28wedding-leads%29", here)
    assert js_run(later, "lcsAdVisit()") == "pricing (wedding-leads)"
    # ...unless a click ID was kept after consent: then the Ref takes over
    kept = later + "saved['lcs-attr'] = JSON.stringify({gclid: 'X'});"
    assert js_run(kept, "lcsAdVisit()") == ""


def test_only_same_site_page_links_carry_the_label():
    if not have_node():
        return
    links = ["/contact.html", "contact.html#enquiry", "/contact.html?occasion=funeral#enquiry", "/music-guides/",
             "https://londonchoralservice.com/weddings.html", "/", "#enquiry", "tel:+447356042468",
             "mailto:office@londonchoralservice.com", "https://wa.me/447356042468?text=Hello",
             "https://example.com/page.html", "/assets/brochure.pdf", "/css/style.css", "/funerals", "",
             "/contact.html?lcs_av=weddings"]
    anchors = ("var made = " + json.dumps(links) + ".map(function (h, i) { var at = {href: h};"
               " if (i === 0) at.download = ''; return {attrs: at, getAttribute: function (k) { return k in this.attrs ? this.attrs[k] : null; },"
               " setAttribute: function (k, v) { this.attrs[k] = v; }, hasAttribute: function (k) { return k in this.attrs; }}; });")
    setup = page("/pricing.html", "?gclid=Cj0KCQjw&utm_campaign=wedding-leads") + anchors
    got = js_run(setup, "(made.forEach(lcsCarryAdVisit), made.map(function (a) { return a.attrs.href; }))")
    tag = "lcs_av=pricing+%28wedding-leads%29"
    want = ["/contact.html",  # a download link is left alone
            f"/contact.html?{tag}#enquiry", f"/contact.html?occasion=funeral&{tag}#enquiry", f"/music-guides/?{tag}",
            f"/weddings.html?{tag}", f"/?{tag}", "#enquiry", "tel:+447356042468",
            "mailto:office@londonchoralservice.com", "https://wa.me/447356042468?text=Hello",
            "https://example.com/page.html", "/assets/brochure.pdf", "/css/style.css", "/funerals", "",
            f"/contact.html?{tag}"]
    assert got == want, list(zip(links, got))
    # After Allow, a link the page decorated loses the label as it is used; others are untouched.
    after = setup + "store['lcs-consent'] = 'granted'; made[1].attrs.href = '/contact.html?occasion=funeral&" + tag + "#enquiry';"
    got = js_run(after, "(made.forEach(lcsCarryAdVisit), [made[1].attrs.href, made[2].attrs.href])")
    assert got == ["/contact.html?occasion=funeral#enquiry", "/contact.html?occasion=funeral#enquiry"], got


def test_ad_visit_is_held_in_a_variable_and_never_stored():
    start = PARTIAL.index("function lcsAdVisitSlug")
    block = PARTIAL[start:PARTIAL.index("</script>", start)]
    for banned in ("setItem", "sessionStorage", "document.cookie", "fetch(", "sendBeacon", "gtag("):
        assert banned not in block, banned
    assert "var LCS_AD_VISIT = " in block and "if (a.gclid || a.gbraid || a.wbraid) return '';" in block
    # messages: the Ref with consent, else the page's name; never the click ID itself
    assert "var visit = ref ? '' : lcsAdVisit();" in PARTIAL
    assert "'Ad visit: ' + visit" in PARTIAL
    # the label rides in links only: written at run time, read back from the next page's own address
    assert "url.searchParams.set('lcs_av', visit)" in block and "q.get('lcs_av')" in block
    assert "document.referrer" in block


def form_pages():
    out = []
    for p in sorted(glob.glob("**/*.html", root_dir=ROOT, recursive=True)):
        if p.startswith(("partials/", ".")) or "/." in p:
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


def test_every_enquiry_form_asks_how_they_heard_with_the_google_answers_first():
    pages = form_pages()
    for p, s in pages:
        form = s[s.index("<form"):s.index("</form>")]
        # Optional since 24 Oct 2026 (owner): it must never block an enquiry.
        m = re.search(r'<label for="([^"]+)">How did you hear about us\? \(optional\)</label>\s*'
                      r'<select id="([^"]+)" name="hear">(.*?)</select>',
                      form, re.S)
        assert m, p
        label_for, select_id, options = m.group(1), m.group(2), re.findall(r"<option[^>]*>([^<]*)</option>", m.group(3))
        assert label_for == select_id and s.count(f'id="{select_id}"') == 1, (p, select_id)  # the label names it
        assert 'id="hear-error"' not in s, p
        assert options[:3] == ["Please choose", "A Google ad (marked Sponsored)", "A Google search result"], (p, options)
        assert options[-1] == "Prefer not to say" and len(options) == len(set(options)), (p, options)
        for old in ("Searching on Google", "A Google ad", "Search"):
            assert old not in options, (p, old)
        assert '<option value="" selected>Please choose</option>' in m.group(3), p
    assert len(pages) >= 39


def test_privacy_policy_explains_both():
    s = open(os.path.join(ROOT, "privacy.html")).read()
    assert 'id="ad-measurement"' in s and "Ad visit: pricing (wedding-leads)" in s and "lcs_av" in s


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
