# Competitive Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a sourced, family-facing comparison against The London Funeral Singers, backed by a build-gated claims-integrity check so quoted competitor figures cannot go stale silently.

**Architecture:** Competitor figures live in one YAML file with verbatim source quotes and a checked date. A new `validate_competitor_claims.py`, run by `build.sh`, hard-fails if a price appears on a `compare/` page without a matching source in that file. The comparison page itself is a cloned music-guide (same directory depth, same `Article` + `FAQPage` schema shape, same subject matter). Existing cost guides are upgraded rather than duplicated, to avoid cannibalising pages that already rank.

**Tech Stack:** Static HTML, `build.sh` (bash + awk), Python 3 with PyYAML for the validator, no framework and no CI.

**Spec:** [docs/superpowers/specs/2026-08-18-competitive-capture-design.md](../specs/2026-08-18-competitive-capture-design.md)

---

## Read this before starting

**Testing convention.** This repo has no test framework, no `package.json`, and no CI. Task 3 introduces the repo's first test, for the validator, because a build-gating script that passes vacuously is worse than no script. It uses plain `assert` and the standard library, so it runs anywhere `python3` does. Every other task is content, and its "test" is the grep/build verification command given in that task. This matches the convention already used throughout `docs/ROADMAP.md`.

**Copy gate — applies to Tasks 5, 6, 8, 9, 10, 11.** Before drafting any visible text, load **both** the `writing-site-copy` skill and the `stop-slop` skill. After drafting, re-read the text against the stop-slop quick checks and score it before committing. Where the two conflict, the project rule wins: generic stop-slop says remove em dashes, but parenthetical `&thinsp;&mdash;&thinsp;` is established house typography here and stays.

**Claim discipline.** Every statement about The London Funeral Singers must be a verbatim quote from their published pricing page, sourced in the YAML. Make no claim about their musicians, their staff, or their quality. Price, VAT treatment, and published package inclusions only.

**Audience.** This page addresses families arranging a funeral. Do not link to `compare/` from any `for-*.html` page, and do not reuse its figures there.

---

## File structure

| Path | Status | Responsibility |
|---|---|---|
| `data/competitor-pricing.yml` | Create | Sole source of truth for competitor figures, with verbatim quotes and checked date |
| `validate_competitor_claims.py` | Create | Build gate: no unsourced figure on a `compare/` page; warn on stale data |
| `tests/test_competitor_claims.py` | Create | Proves the validator actually catches an unsourced figure |
| `compare/london-funeral-singers.html` | Create | The comparison page |
| `build.sh` | Modify | Run the new validator alongside `validate_jsonld.py` |
| `sitemap.xml`, `llms.txt` | Modify | Wiring |
| `partials/footer.html` | Modify | Footer link (partial edit → rebuild mandatory) |
| `funerals.html`, `pricing.html` | Modify | Inbound links; inclusions block; ensemble argument |
| `music-guides/funeral-music-costs.html` | Modify | Market-comparison section; `£215` → `£250` |
| `music-guides/best-funeral-singers-london.html` | Modify | Correct the understated market table |
| `MANUAL-ACTIONS-REQUIRED.md` | Modify | Google Ads work (dashboard-only, never attempted by an agent) |
| `CLAUDE.md`, `docs/ROADMAP.md` | Modify | Record the new convention and close out the programme |

---

## Task 1: Confirm prerequisites and finish the £215 sweep

The comparison page quotes £250 for a soloist. If the pricing branch has not merged, the site would state two different soloist prices at once. **This task gates everything else.**

**Files:**
- Modify: `music-guides/funeral-music-costs.html`, `funerals.html`, `llms.txt` (confirm by grep, do not trust this list)

- [ ] **Step 1: Confirm the pricing branch has merged**

```bash
grep -c 'From &pound;250' pricing.html
```

Expected: `3` (soloist, organist, instrumentalists rows).

If this returns `0`, **stop**. `site-audit-improvements-47d735` has not merged. Do not continue; report the blocker.

- [ ] **Step 2: Find every surviving £215**

```bash
grep -rn '£215\|&pound;215\|"215"' --include='*.html' --include='*.txt' .
```

Expected: hits in `music-guides/funeral-music-costs.html` (×4, one inside a `FAQPage` answer), `funerals.html` (×1), `llms.txt` (×1). Treat the grep output as authoritative, not this list.

- [ ] **Step 3: Replace them**

Every `215` becomes `250`. The `FAQPage` answer and its visible counterpart must stay identical — Google requires parity between marked-up and visible FAQ text.

```bash
python3 - <<'PYEOF'
import glob
files = glob.glob("*.html") + glob.glob("areas/*.html") + glob.glob("areas/**/*.html") \
      + glob.glob("music-guides/*.html") + ["llms.txt"]
pairs = [("&pound;215", "&pound;250"), ("£215", "£250"), ('"215"', '"250"'), ('"minPrice": "215"', '"minPrice": "250"')]
total = 0
for path in sorted(set(files)):
    src = open(path, encoding="utf-8").read()
    out = src
    for old, new in pairs:
        out = out.replace(old, new)
    if out != src:
        open(path, "w", encoding="utf-8").write(out)
        n = sum(src.count(o) for o, _ in pairs)
        print(f"{path}: {n}")
        total += n
print("TOTAL:", total)
PYEOF
```

- [ ] **Step 4: Verify nothing survives and the build is green**

```bash
grep -rn '£215\|&pound;215\|"215"' --include='*.html' --include='*.txt' . ; ./build.sh
```

Expected: no grep output, then `build.sh` prints its four counts and ends with `JSON-LD valid in 132 files checked.` and `Done.`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix(pricing): sweep residual £215 references to £250

The pricing branch raised the single-musician rate but did not reach the
cost guide, the funerals page, or llms.txt. FAQPage answers updated in
step with their visible counterparts to preserve schema parity."
```

---

## Task 2: Add the competitor data file

**Files:**
- Create: `data/competitor-pricing.yml`

- [ ] **Step 1: Write the file**

Figures are quoted from `https://www.londonfuneralsingers.co.uk/pricing`, retrieved 2026-08-18. `source_quote` holds the exact published string. If a figure cannot be quoted, it does not belong here and must not appear on the page.

```yaml
# Competitor pricing — source of truth for anything published under compare/
#
# Every figure carries the verbatim string it was taken from. validate_competitor_claims.py
# hard-fails the build if a price appears on a compare/ page without a match here, and warns
# when checked_date is more than 120 days old.
#
# Re-check quarterly. See MANUAL-ACTIONS-REQUIRED.md. Update checked_date and the page in the
# same commit — a figure and its date must never disagree.
#
# vat_rate is the UK standard rate used to derive inc-VAT figures for family-facing copy.
# Families cannot reclaim VAT, so the inc-VAT column is what they actually pay.

vat_rate: 0.20

providers:
  london-funeral-singers:
    name: "The London Funeral Singers"
    url: "https://www.londonfuneralsingers.co.uk/"
    pricing_url: "https://www.londonfuneralsingers.co.uk/pricing"
    checked_date: "2026-08-18"
    vat_treatment: "quoted excluding VAT"
    travel: "Travel charges apply outside of London"
    packages:
      soloist:
        price_ex_vat: 275
        source_quote: "Soloist: From £275 + VAT"
        includes: "One solo performance piece; Congregation leading - up to three hymns"
      organist:
        price_ex_vat: 275
        source_quote: "Organist: £275 + VAT"
        includes: "Professional accompaniment for hymns with rehearsal"
      instrumentalists:
        price_ex_vat: 275
        source_quote: "Instrumentalists: Starting at £275 + VAT"
        includes: "Pianists, string quartets, harpists, bugle players"
      small_choir:
        price_ex_vat: 1400
        source_quote: "Small Choir: £1,400 + VAT"
        includes: "Four singers; One performance piece; Leading the congregation - up to three hymns"
      full_choir:
        price_ex_vat: 2400
        source_quote: "Full Choir: £2,400 + VAT"
        includes: "Eight singers; One performance piece; Leading the congregation - up to three hymns"
      chorus:
        price_ex_vat: 4000
        source_quote: "Chorus: £4,000 + VAT"
        includes: "Twelve singers; Two performance pieces; Leading the congregation - up to four hymns; organist-conductor"

# LCS figures are mirrored here only so the validator can whitelist them on comparison pages.
# pricing.html remains the source of truth for LCS prices; these must match it.
lcs_prices:
  soloist: 250
  organist_standalone: 250
  organist_added_to_choir: 225
  soloist_with_organist: 450
  small_choir: 1150
  quintet: 1400
  sextet: 1600
  full_choir: 2000
  chorus: 3000

# Every combination total and saving the comparison page is allowed to print.
# The validator accepts NOTHING beyond the figures above plus this list, so a new
# number on the page means adding it here with a note explaining the arithmetic.
# Deliberately explicit: deriving these by summing and subtracting the base prices
# would admit thousands of values and let a wrong figure through by coincidence.
derived_figures:
  550:  "LFS soloist + organist, ex VAT (275 + 275)"
  660:  "LFS soloist + organist, inc VAT (330 + 330)"
  1675: "LFS small choir + organist, ex VAT (1400 + 275)"
  2010: "LFS small choir + organist, inc VAT (1680 + 330)"
  1375: "LCS small choir + organist (1150 + 225)"
  80:   "Saving on a soloist (330 - 250)"
  210:  "Saving on soloist with organist (660 - 450)"
  530:  "Saving on a small choir (1680 - 1150)"
  635:  "Saving on small choir with organist (2010 - 1375)"
  880:  "Saving on a full choir (2880 - 2000)"
  1800: "Saving on a chorus (4800 - 3000)"
```

- [ ] **Step 2: Verify it parses**

```bash
python3 -c "import yaml; d=yaml.safe_load(open('data/competitor-pricing.yml')); print(sorted(d['providers']['london-funeral-singers']['packages']))"
```

Expected: `['chorus', 'full_choir', 'instrumentalists', 'organist', 'small_choir', 'soloist']`

- [ ] **Step 3: Confirm LCS figures match pricing.html**

```bash
python3 - <<'PYEOF'
import yaml, re
d = yaml.safe_load(open('data/competitor-pricing.yml'))
page = open('pricing.html', encoding='utf-8').read()
for key, val in d['lcs_prices'].items():
    token = f"&pound;{val:,}"
    print(f"{'OK ' if token in page else 'MISSING'}  {key}: {token}")
PYEOF
```

Expected: `OK` for soloist (250), small_choir (1,150), quintet (1,400), sextet (1,600), full_choir (2,000), chorus (3,000), organist_added_to_choir (225), soloist_with_organist (450). Any `MISSING` means the YAML disagrees with `pricing.html`; fix the YAML, never the other way round.

- [ ] **Step 4: Commit**

```bash
git add data/competitor-pricing.yml
git commit -m "data: add competitor pricing source of truth

Verbatim published figures for The London Funeral Singers with retrieval
date, plus LCS prices mirrored from pricing.html so the validator can
tell sourced figures from invented ones."
```

---

## Task 3: Test-drive the claims validator

**Files:**
- Create: `tests/test_competitor_claims.py`
- Create: `validate_competitor_claims.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_competitor_claims.py`:

```python
#!/usr/bin/env python3
"""Tests for validate_competitor_claims.py. Stdlib only — run with: python3 tests/test_competitor_claims.py"""
import os, subprocess, sys, tempfile, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

YAML = """
vat_rate: 0.20
providers:
  test-provider:
    name: "Test Provider"
    pricing_url: "https://example.com/pricing"
    checked_date: "{date}"
    packages:
      soloist:
        price_ex_vat: 275
        source_quote: "Soloist: From £275 + VAT"
lcs_prices:
  soloist: 250
"""

def run_in_sandbox(yaml_text, page_html):
    """Copy the validator into a temp repo, run it, return (exit_code, output)."""
    tmp = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmp, "data"))
        os.makedirs(os.path.join(tmp, "compare"))
        with open(os.path.join(tmp, "data", "competitor-pricing.yml"), "w") as f:
            f.write(yaml_text)
        with open(os.path.join(tmp, "compare", "x.html"), "w") as f:
            f.write(page_html)
        shutil.copy(os.path.join(ROOT, "validate_competitor_claims.py"), tmp)
        p = subprocess.run([sys.executable, "validate_competitor_claims.py"],
                           cwd=tmp, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr
    finally:
        shutil.rmtree(tmp)

def test_sourced_figures_pass():
    code, out = run_in_sandbox(
        YAML.format(date="2026-08-18"),
        "<p>They charge &pound;275 plus VAT, or &pound;330. We charge &pound;250.</p>")
    assert code == 0, f"expected pass, got {code}: {out}"

def test_unsourced_figure_fails():
    code, out = run_in_sandbox(
        YAML.format(date="2026-08-18"),
        "<p>They charge &pound;999 plus VAT.</p>")
    assert code == 1, f"expected failure for unsourced £999, got {code}: {out}"
    assert "999" in out, f"error should name the offending figure: {out}"

def test_undeclared_sum_fails():
    """£550 is 275+275, but arithmetic alone must not make a figure acceptable."""
    code, out = run_in_sandbox(
        YAML.format(date="2026-08-18"),
        "<p>A soloist with an organist is &pound;550 plus VAT.</p>")
    assert code == 1, f"undeclared sum £550 must fail, got {code}: {out}"

def test_declared_derived_figure_passes():
    yaml_text = YAML.format(date="2026-08-18") + "derived_figures:\n  550: \"soloist + organist\"\n"
    code, out = run_in_sandbox(yaml_text, "<p>&pound;550 plus VAT.</p>")
    assert code == 0, f"declared derived figure should pass: {out}"

def test_stale_data_warns_but_passes():
    code, out = run_in_sandbox(
        YAML.format(date="2020-01-01"),
        "<p>They charge &pound;275 plus VAT.</p>")
    assert code == 0, f"stale data must warn, not fail: {out}"
    assert "STALE" in out, f"expected a staleness warning: {out}"

def test_no_compare_pages_is_fine():
    tmp = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmp, "data"))
        with open(os.path.join(tmp, "data", "competitor-pricing.yml"), "w") as f:
            f.write(YAML.format(date="2026-08-18"))
        shutil.copy(os.path.join(ROOT, "validate_competitor_claims.py"), tmp)
        p = subprocess.run([sys.executable, "validate_competitor_claims.py"],
                           cwd=tmp, capture_output=True, text=True)
        assert p.returncode == 0, f"no compare/ pages should pass: {p.stdout}{p.stderr}"
    finally:
        shutil.rmtree(tmp)

if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
```

- [ ] **Step 2: Run it to verify it fails**

```bash
python3 tests/test_competitor_claims.py
```

Expected: all four tests fail, because `validate_competitor_claims.py` does not exist yet. The `shutil.copy` raises `FileNotFoundError`, which surfaces as an error rather than a clean `FAIL` line — that is the correct failing state for step 2.

- [ ] **Step 3: Write the validator**

Create `validate_competitor_claims.py`:

```python
#!/usr/bin/env python3
"""Guards competitor claims published under compare/.

Hard-fails if a money figure appears on a compare/ page that is not derivable from
data/competitor-pricing.yml. Warns when the data is more than 120 days old.
"""
import datetime, glob, os, re, sys

try:
    import yaml
except ImportError:
    print("ERROR: validate_competitor_claims.py needs PyYAML. Install it with: pip3 install pyyaml")
    sys.exit(1)

DATA = os.path.join("data", "competitor-pricing.yml")
STALE_AFTER_DAYS = 120
MONEY = re.compile(r'(?:&pound;|£)\s*([\d,]+)')

def allowed_figures(cfg):
    """Every figure a compare/ page may legitimately print.

    Explicit only. Deriving combination totals and savings by summing and
    subtracting the base prices would admit thousands of values and let a wrong
    figure pass by coincidence, which would defeat the point of the check. Any
    computed figure on the page must be declared in derived_figures.
    """
    allowed, vat = set(), cfg.get("vat_rate", 0.20)
    for provider in cfg.get("providers", {}).values():
        for pkg in provider.get("packages", {}).values():
            ex = pkg["price_ex_vat"]
            allowed.add(ex)
            allowed.add(round(ex * (1 + vat)))
    allowed.update(cfg.get("lcs_prices", {}).values())
    allowed.update(int(k) for k in cfg.get("derived_figures", {}))
    return allowed

def main():
    pages = sorted(glob.glob(os.path.join("compare", "*.html")))
    if not pages:
        print("No compare/ pages; competitor claim check skipped.")
        return 0
    if not os.path.exists(DATA):
        print(f"ERROR: {pages[0]} exists but {DATA} does not. Competitor figures must be sourced.")
        return 1

    cfg = yaml.safe_load(open(DATA, encoding="utf-8"))
    allowed = allowed_figures(cfg)

    today = datetime.date.today()
    for key, provider in cfg.get("providers", {}).items():
        checked = datetime.date.fromisoformat(str(provider["checked_date"]))
        age = (today - checked).days
        if age > STALE_AFTER_DAYS:
            print(f"STALE: {key} last checked {checked} ({age} days ago). "
                  f"Re-check {provider['pricing_url']} and update checked_date.")
        else:
            print(f"OK: {key} checked {checked} ({age} days ago).")

    errors = 0
    for page in pages:
        content = open(page, encoding="utf-8").read()
        for match in MONEY.finditer(content):
            value = int(match.group(1).replace(",", ""))
            if value not in allowed:
                print(f"UNSOURCED FIGURE in {page}: £{value:,} is not declared in {DATA}")
                errors += 1

    if errors:
        print(f"\n{errors} unsourced figure(s). Every price on a compare/ page must trace to {DATA} "
              f"— either a published competitor price, an LCS price, or an entry in derived_figures.")
        return 1
    print(f"Competitor claims valid across {len(pages)} compare/ page(s).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python3 tests/test_competitor_claims.py
```

Expected:
```
PASS test_declared_derived_figure_passes
PASS test_no_compare_pages_is_fine
PASS test_sourced_figures_pass
PASS test_stale_data_warns_but_passes
PASS test_undeclared_sum_fails
PASS test_unsourced_figure_fails

0 failure(s)
```

- [ ] **Step 5: Run it against the real repo**

```bash
python3 validate_competitor_claims.py
```

Expected: `No compare/ pages; competitor claim check skipped.` and exit 0. The page does not exist yet.

- [ ] **Step 6: Commit**

```bash
git add tests/test_competitor_claims.py validate_competitor_claims.py
git commit -m "feat: add competitor claim validator with tests

Hard-fails the build if a price on a compare/ page is not derivable from
data/competitor-pricing.yml, so a competitor figure cannot be hand-edited
into the page without a source. Warns at 120 days rather than failing, so
stale competitor data never blocks unrelated work.

First test in the repo — plain asserts, stdlib only, no test framework
needed: python3 tests/test_competitor_claims.py"
```

---

## Task 4: Wire the validator into build.sh

**Files:**
- Modify: `build.sh` (the final validation block)

- [ ] **Step 1: Add the call after the JSON-LD check**

Replace the last three lines of `build.sh`:

```bash
echo "Validating JSON-LD..."
python3 validate_jsonld.py

echo "Done."
```

with:

```bash
echo "Validating JSON-LD..."
python3 validate_jsonld.py

echo "Validating competitor claims..."
python3 validate_competitor_claims.py

echo "Done."
```

`build.sh` runs under `set -euo pipefail`, so a non-zero exit from the validator fails the build without further wiring.

- [ ] **Step 2: Verify the build still passes**

```bash
./build.sh
```

Expected, after the JSON-LD line:
```
Validating competitor claims...
No compare/ pages; competitor claim check skipped.
Done.
```

- [ ] **Step 3: Prove the gate actually bites**

```bash
mkdir -p compare && printf '<p>&pound;9999</p>' > compare/_gate-test.html
./build.sh; echo "exit=$?"
rm compare/_gate-test.html
```

Expected: `UNSOURCED FIGURE in compare/_gate-test.html: £9,999 is not derivable from data/competitor-pricing.yml`, then `exit=1`.

Confirm the build recovers:

```bash
./build.sh && echo "recovered"
```

- [ ] **Step 4: Commit**

```bash
git add build.sh
git commit -m "build: gate competitor claims in build.sh

Verified the gate bites: a compare/ page carrying an unsourced figure
fails the build."
```

---

## Task 5: Create the comparison page shell

Head block and JSON-LD only. Body copy is Task 6.

**Files:**
- Create: `compare/london-funeral-singers.html` (cloned from `music-guides/best-funeral-singers-london.html`)

- [ ] **Step 1: Clone the exemplar**

`music-guides/best-funeral-singers-london.html` is the right exemplar: same subject, same `Article` + `LocalBusiness` stub + `BreadcrumbList` + `FAQPage` schema shape, and the same directory depth, so every `../` path resolves identically in `compare/`.

```bash
mkdir -p compare
cp music-guides/best-funeral-singers-london.html compare/london-funeral-singers.html
```

- [ ] **Step 2: Replace the six title/description fields**

All six must change together — `<title>`, `meta description`, `og:title`, `og:description`, `twitter:title`, `twitter:description`. Leaving the exemplar's text in any one of them is the most common mistake on this site.

- Title: `London Funeral Singers vs The London Choral Service`
- Description (146 chars, verified): `Comparing quotes for funeral singers in London? See what The London Funeral Singers charge, what we charge, and what each price actually includes.`

```bash
python3 - <<'PYEOF'
p = "compare/london-funeral-singers.html"
s = open(p, encoding="utf-8").read()
TITLE = "London Funeral Singers vs The London Choral Service"
DESC = ("Comparing quotes for funeral singers in London? See what The London Funeral Singers "
        "charge, what we charge, and what each price actually includes.")
assert 141 <= len(DESC) <= 161, len(DESC)
old_title = "Best funeral singers in London &mdash; what to look for"
import re
s = re.sub(r'<title>[^<]*</title>', f'<title>{TITLE}</title>', s, count=1)
for prop in ['name="description"', 'property="og:description"', 'name="twitter:description"']:
    s = re.sub(rf'({re.escape(prop)} content=")[^"]*(")', rf'\g<1>{DESC}\g<2>', s, count=1)
for prop in ['property="og:title"', 'name="twitter:title"']:
    s = re.sub(rf'({re.escape(prop)} content=")[^"]*(")', rf'\g<1>{TITLE}\g<2>', s, count=1)
open(p, "w", encoding="utf-8").write(s)
print("title/description fields updated")
PYEOF
```

- [ ] **Step 3: Repoint canonical, hreflang, and og:url**

```bash
python3 - <<'PYEOF'
p = "compare/london-funeral-singers.html"
s = open(p, encoding="utf-8").read()
old = "https://londonchoralservice.com/music-guides/best-funeral-singers-london.html"
new = "https://londonchoralservice.com/compare/london-funeral-singers.html"
n = s.count(old)
open(p, "w", encoding="utf-8").write(s.replace(old, new))
print(f"{n} URL references repointed")
PYEOF
grep -c 'compare/london-funeral-singers.html' compare/london-funeral-singers.html
```

Expected: at least 4 (canonical, both hreflang, og:url), plus any occurrences inside JSON-LD.

- [ ] **Step 4: Set og:type**

Comparison pages are articles, same as guides. Confirm it is already `article` from the clone:

```bash
grep -o 'og:type" content="[^"]*"' compare/london-funeral-singers.html
```

Expected: `og:type" content="article"`. If it says `website`, change it to `article`.

- [ ] **Step 5: Rewrite the JSON-LD graph**

Replace the `Article` `headline`/`description` and the `BreadcrumbList` to match the new page. The graph keeps `Article`, the `LocalBusiness` stub (`@id` `https://londonchoralservice.com/#organization` — reuse, never redefine), `BreadcrumbList`, and `FAQPage`.

Breadcrumb is three levels, and the final item carries `name` but no `item` URL:

```json
{
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://londonchoralservice.com/" },
    { "@type": "ListItem", "position": 2, "name": "Compare", "item": "https://londonchoralservice.com/compare/london-funeral-singers.html" },
    { "@type": "ListItem", "position": 3, "name": "London Funeral Singers vs The London Choral Service" }
  ]
}
```

Set the `Article` fields:

```json
"headline": "London Funeral Singers vs The London Choral Service",
"description": "Comparing quotes for funeral singers in London? See what The London Funeral Singers charge, what we charge, and what each price actually includes.",
"datePublished": "2026-08-18",
"author": { "@type": "Person", "name": "Luca Wetherall" }
```

Leave the `FAQPage` node in place for now; Task 6 replaces its questions to match the new visible FAQ.

**Do not add `Product`, `Offer`, or `AggregateOffer` containing competitor prices.** Offer markup asserts that the marked-up entity sells at that price, which would misrepresent the relationship. **Do not add `AggregateRating` or `Review`** — prohibited site-wide.

- [ ] **Step 6: Verify the head block and schema**

```bash
python3 -c "
import re
s = open('compare/london-funeral-singers.html', encoding='utf-8').read()
d = re.search(r'name=\"description\" content=\"([^\"]*)\"', s).group(1)
print('desc length:', len(d), 141 <= len(d) <= 161)
print('exemplar text left over:', 'Best funeral singers in London' in s)
"
grep -c 'AggregateRating\|"@type": "Review"\|"@type": "Offer"' compare/london-funeral-singers.html
python3 validate_jsonld.py
```

Expected: length in range and `True`; `exemplar text left over: False`; grep count `0`; JSON-LD valid.

- [ ] **Step 7: Commit**

```bash
git add compare/london-funeral-singers.html
git commit -m "feat(compare): scaffold the London Funeral Singers comparison page

Head block, canonical, and JSON-LD graph. Body copy follows."
```

---

## Task 6: Write the comparison page body

**Files:**
- Modify: `compare/london-funeral-singers.html` (body between the nav and footer include markers)

- [ ] **Step 1: Load both copy skills**

Load `writing-site-copy` and `stop-slop` before drafting a single sentence. Funeral copy is restrained and practical. The reader is bereaved and comparing quotes because they have to, so the page must never read as a price war.

- [ ] **Step 2: Replace the body with these sections**

Keep the breadcrumb `<nav>`, the `<h1>`, and the existing section/prose class structure from the clone. Replace everything between them.

**H1:** `London Funeral Singers vs The London Choral Service`

**Opening:**

> If you are comparing quotes for funeral singers in London, you are doing it in a week with a great deal else to arrange. This page sets out what The London Funeral Singers charge, what we charge, and what each price covers.
>
> They quote before VAT. We quote with everything in, so the figure you see is the figure on the invoice.

**Section: The gap is wider than it looks**

> The London Funeral Singers list a soloist at £275 + VAT. On the invoice that is £330. We are not VAT-registered, so our £250 stays £250.
>
> The same holds at every size. Their small choir of four is £1,400 + VAT, which comes to £1,680. Ours is £1,150, with travel inside Greater London already in the figure.

Then the price table. Every figure must trace to `data/competitor-pricing.yml` or the validator will fail the build.

| Configuration | The London Funeral Singers | On the invoice | The London Choral Service | Difference |
|---|---|---|---|---|
| Soloist | £275 + VAT | £330 | £250 | £80 |
| Organist | £275 + VAT | £330 | £250 | £80 |
| Soloist with organist | £550 + VAT | £660 | £450 | £210 |
| Small choir, four singers | £1,400 + VAT | £1,680 | £1,150 | £530 |
| Small choir with organist | £1,675 + VAT | £2,010 | £1,375 | £635 |
| Full choir, eight singers | £2,400 + VAT | £2,880 | £2,000 | £880 |
| Chorus, twelve singers | £4,000 + VAT | £4,800 | £3,000 | £1,800 |

Directly beneath the table, in `text-sm text-mid`:

> Their prices as published at <a href="https://www.londonfuneralsingers.co.uk/pricing" rel="nofollow noopener" target="_blank">londonfuneralsingers.co.uk/pricing</a>, checked 18 August 2026. VAT shown at the standard 20% rate. Our prices are on our <a href="../pricing.html">pricing page</a>.

**Section: How much singing you get**

> Price is half the comparison. The other half is how much music the price buys.
>
> Their small choir of four includes one performance piece and up to three hymns. Their full choir of eight includes the same. Ours include up to three performance pieces and every hymn in the service.
>
> At quartet level that works out at three times the sung music for about two-thirds of the price.

| | The London Funeral Singers | The London Choral Service |
|---|---|---|
| Four singers | One performance piece, up to three hymns | Up to three performance pieces, all hymns |
| Eight singers | One performance piece, up to three hymns | Up to three performance pieces, all hymns |
| Twelve singers | Two performance pieces, up to four hymns | Up to four performance pieces, all hymns |

> We also offer five and six singers, at £1,400 and £1,600. If you want six voices, you can book six.

**Section: Who sings**

> We keep the team small on purpose. Luca Wetherall, our Artistic Director and a Tutor in Music at the University of Oxford, auditions every singer himself and picks the ensemble for your service.
>
> Our quartets and sextets rehearse and sing together rather than coming together for a single booking. That is what lets four voices fill a parish church without straining.
>
> You do not have to take this on trust. The recordings below are our own singers.

Make no claim here about their musicians, their staff, or their quality.

**Section: Listen** — embed the two existing YouTube videos, matching the embed markup already used on `listen.html`:

- `G9-R6k5n7Io` — Abide With Me (Eventide)
- `ZVSQ2Ts4GZE` — Anima Christi (Marco Frisina)

IDs, durations, and upload dates are in `data/seo-fix-discovered-urls.yml`. Do not add `VideoObject` schema here; it is already emitted on `listen.html` and duplicating it across pages splits the signal.

**Section: What each price covers** — two lists side by side. Ours:

> Rehearsal and preparation. Sheet music. A music director. Coordination with your funeral director and the venue. Travel within Greater London. No VAT, and no fee added afterwards.

Theirs, quoted from their published inclusions and nothing beyond them:

> Coordination with funeral directors and venues, musician selection, sheet music, rehearsal, and personal support. Their site states that travel charges apply outside London, and that prices are quoted plus VAT.

**Section: Already have a quote?**

> Send it to us and we will tell you what the same service costs here, itemised, with no obligation. If your existing quote suits you better, we will say so.

CTA to `../contact.html?occasion=quote-check`, using the existing `?occasion=` pre-fill in `js/contact.js`. Follow the button markup from the exemplar.

- [ ] **Step 3: Write the FAQ, visible and in schema**

Five questions. The `FAQPage` answers must match the visible text word for word.

1. **Why are your prices lower?** — We are not VAT-registered, so nothing is added at the end. We keep a small team rather than a large agency book. Travel within Greater London, sheet music, and rehearsal are already in the quoted figure.
2. **Do you charge VAT?** — No. Alma Consort Ltd is not VAT-registered, so the price we quote is the price on the invoice.
3. **What is included in the price?** — Rehearsal and preparation, sheet music, a music director, coordination with your funeral director and the venue, and travel within Greater London.
4. **How many pieces will the choir sing?** — Up to three performance pieces plus every hymn in the service, for any ensemble from four singers to eight. A twelve-voice chorus covers up to four pieces.
5. **Can you arrange singers at short notice?** — Yes. We hold diary space for short-notice work. A 48-hour turnaround is normal and shorter is often possible.

- [ ] **Step 4: Run the copy through stop-slop**

Re-read every paragraph against the stop-slop quick checks: adverbs, passive voice, inanimate subjects doing human verbs, Wh- openers, "here's what" throat-clearing, "not X but Y" contrasts, three consecutive sentences of matching length, punchy one-liner paragraph endings, vague declaratives. Score the page on the five dimensions; revise anything below 35/50.

House exception: parenthetical `&thinsp;&mdash;&thinsp;` stays.

- [ ] **Step 5: Verify**

```bash
./build.sh
python3 -c "
s = open('compare/london-funeral-singers.html', encoding='utf-8').read()
print('h1 count:', s.count('<h1'))
print('checked date present:', 'checked 18 August 2026' in s)
print('source link present:', 'londonfuneralsingers.co.uk/pricing' in s)
"
```

Expected: build green, ending `Competitor claims valid across 1 compare/ page(s).`; `h1 count: 1`; both `True`.

If the build reports an unsourced figure, the page contains a price that is not in the YAML. Fix the page or add the sourced figure to the YAML — never loosen the validator.

- [ ] **Step 6: Commit**

```bash
git add compare/london-funeral-singers.html
git commit -m "copy(compare): write the comparison page body

Sourced price and repertoire tables, the hand-picked positioning, two
recordings, and a five-question FAQ matched to its schema. Every figure
traces to data/competitor-pricing.yml; no claim about their musicians."
```

---

## Task 7: Wire the page in

A page nobody links to is invisible.

**Files:**
- Modify: `sitemap.xml`, `llms.txt`, `partials/footer.html`, `funerals.html`, `pricing.html`, `music-guides/funeral-music-costs.html`, `music-guides/best-funeral-singers-london.html`

- [ ] **Step 1: Add the sitemap entry**

Insert after the `pricing.html` entry, keeping the file's existing ordering (core pages, then areas, then guides):

```xml
  <url>
    <loc>https://londonchoralservice.com/compare/london-funeral-singers.html</loc>
    <lastmod>2026-08-18</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
```

- [ ] **Step 2: Add the llms.txt entry**

Under `## Main Pages`:

```
- [London Funeral Singers Comparison](https://londonchoralservice.com/compare/london-funeral-singers.html): How our funeral singer prices and repertoire compare with The London Funeral Singers — sourced figures, VAT treatment, and what each package includes
```

- [ ] **Step 3: Add the footer link**

Edit `partials/footer.html`, not the expanded copies. Put it alongside the existing footer links, not in a new prominent block.

**This is a partial edit, so `./build.sh` is mandatory** and will rewrite ~132 files.

- [ ] **Step 4: Add body links from four pages**

Do **not** add it to the nav. A "Compare" tab is the first thing a bereaved visitor would see, and it reads as combative.

- `funerals.html` — near the pricing paragraph: `<a href="compare/london-funeral-singers.html">how our prices compare</a>`
- `pricing.html` — beneath the price table
- `music-guides/funeral-music-costs.html` — in the related links block: `<a href="../compare/london-funeral-singers.html">…</a>`
- `music-guides/best-funeral-singers-london.html` — in the related links block

Mind the depth: root pages use `compare/…`, `music-guides/` pages use `../compare/…`.

- [ ] **Step 5: Verify wiring and diff shape**

```bash
./build.sh
grep -rl 'compare/london-funeral-singers' --include='*.html' . | grep -v '^./compare/'
python3 -c "import xml.dom.minidom; xml.dom.minidom.parse('sitemap.xml'); print('sitemap parses')"
grep -c '<loc>' sitemap.xml
```

Expected: at least four hub pages listed; sitemap parses; `<loc>` count is the previous count plus one.

Because Step 3 touched a partial, `git diff --stat` will show ~132 files. Spot-check that those changes are confined to the footer marker region:

```bash
git diff -- index.html areas/london/camden.html music-guides/index.html | grep -c '^[+-]'
```

Every changed line should sit inside the `partials/footer.html` marker region. If anything changed outside it, stop and investigate.

- [ ] **Step 6: Preview**

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000/compare/london-funeral-singers.html`. Confirm nav and footer render, no raw `@include` markers are visible, the tables do not overflow at a 375px viewport, and the CTA reaches the contact form with the occasion pre-filled.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(compare): wire the comparison page into the site

Sitemap, llms.txt, footer partial, and body links from funerals, pricing,
and both funeral guides. Deliberately not in the main nav."
```

---

## Task 8: Add the market comparison to the cost guide

Upgrade the page that already ranks rather than building a rival to it.

**Files:**
- Modify: `music-guides/funeral-music-costs.html`

- [ ] **Step 1: Load both copy skills**

`writing-site-copy` and `stop-slop`.

- [ ] **Step 2: Add a section after "What funeral musicians cost"**

The page already says *"These are our prices — other providers may differ, but this gives you an honest benchmark."* That sentence has been writing a cheque the page never cashed. Cash it.

Heading: **What other London providers charge**

> The London Funeral Singers publish their prices too, which makes a like-for-like comparison possible. They list a soloist at £275 + VAT and a small choir of four at £1,400 + VAT. Add the VAT and those become £330 and £1,680.
>
> Their small choir includes one performance piece and up to three hymns. Ours includes up to three pieces and all the hymns. We set the two side by side on our <a href="../compare/london-funeral-singers.html">comparison page</a>.
>
> Figures taken from their published price list on 18 August 2026.

Use only the same single competitor as the comparison page. This is not a multi-provider market survey.

- [ ] **Step 3: Run the new copy through stop-slop**

- [ ] **Step 4: Verify**

```bash
./build.sh
grep -c 'compare/london-funeral-singers' music-guides/funeral-music-costs.html
```

Expected: build green, count `1`.

Note that this page is under `music-guides/`, not `compare/`, so the validator does not check it. The figures still have to match `data/competitor-pricing.yml`; check by eye against Task 2.

- [ ] **Step 5: Commit**

```bash
git add music-guides/funeral-music-costs.html
git commit -m "copy(guides): add a sourced market comparison to the cost guide

The page promised an honest benchmark against other providers and never
gave one. Now it does, with published figures and a retrieval date."
```

---

## Task 9: Correct the understated market table

**Files:**
- Modify: `music-guides/best-funeral-singers-london.html`

- [ ] **Step 1: Find the table**

```bash
grep -n 'Price ranges across the market' music-guides/best-funeral-singers-london.html
```

It currently gives a soloist range of £200–£300 and a small choir range of £900–£1,400. The one published London price list puts a quartet at £1,680 including VAT, so the table understates the market and, with it, the site's own advantage.

- [ ] **Step 2: Correct the ranges**

| Ensemble | Corrected range |
|---|---|
| Soloist | £250–£350 |
| Small choir, four singers | £1,150–£1,700 |
| Sextet | £1,600–£2,400 |
| Full choir | £2,000–£3,500 |

Keep the existing paragraph about VAT varying between providers. It is accurate, and it now has published evidence behind it. Add one sentence:

> One London provider, The London Funeral Singers, publishes a price list showing £1,400 + VAT for four singers, which is £1,680 once VAT is added.

- [ ] **Step 3: Run the new copy through stop-slop**

- [ ] **Step 4: Verify**

```bash
./build.sh
grep -n '£900\|&pound;900' music-guides/best-funeral-singers-london.html
```

Expected: build green, no `£900` remaining.

- [ ] **Step 5: Commit**

```bash
git add music-guides/best-funeral-singers-london.html
git commit -m "copy(guides): correct the understated market price table

The quoted quartet range topped out below what the one published London
price list actually charges, which understated the market and our own
position in it."
```

---

## Task 10: Add the inclusions block to pricing.html

**Files:**
- Modify: `pricing.html`

- [ ] **Step 1: Load both copy skills**

- [ ] **Step 2: Add the block after the accompaniment table**

Heading: **What you are not charged for**

> Travel within Greater London. Sheet music. Rehearsal and preparation. The music director. Coordination with your funeral director and the venue. VAT, which we are not registered for and do not add.
>
> Your written quote is the whole cost. Nothing arrives afterwards.

The page already carries a "no hidden fees" FAQ answer. Do not restate it; this block names the specific items instead of asserting the general claim.

- [ ] **Step 3: Run the new copy through stop-slop**

- [ ] **Step 4: Verify**

```bash
./build.sh
python3 validate_jsonld.py
```

Expected: both green.

- [ ] **Step 5: Commit**

```bash
git add pricing.html
git commit -m "copy(pricing): name the items included in the quoted price

Replaces an assertion about hidden fees with the specific list."
```

---

## Task 11: Surface the ensemble argument and service standards

**Files:**
- Modify: `funerals.html`

- [ ] **Step 1: Load both copy skills**

- [ ] **Step 2: Add a section on how the ensemble is put together**

The strongest version of this argument already exists in `music-guides/best-funeral-singers-london.html`. Adapt it for the service page; do not copy it verbatim, or the two pages compete for the same query.

> A quartet who rehearse together sounds different from four singers meeting for the first time on the morning. We keep the team small so the same voices sing together, and Luca Wetherall auditions every one of them.

- [ ] **Step 3: Add the service standards**

Specifics read as competence where adjectives do not.

> Our singers arrive 45 to 60 minutes early and check in with the funeral director. They wear plain dark dress unless you ask for something else, stand at the back rather than the front, and post nothing about the service.

- [ ] **Step 4: Run the new copy through stop-slop**

- [ ] **Step 5: Verify**

```bash
./build.sh
grep -c '<h1' funerals.html
```

Expected: build green, `h1` count `1`.

- [ ] **Step 6: Commit**

```bash
git add funerals.html
git commit -m "copy(funerals): add the ensemble argument and service standards

Promotes the fixed-ensemble point from the guide to the service page, and
states the on-the-day standards as specifics rather than adjectives."
```

---

## Task 12: Document the Google Ads work

Ads live in a dashboard. **An agent must never attempt these** — `MANUAL-ACTIONS-REQUIRED.md` is human-only, per CLAUDE.md.

**Files:**
- Modify: `MANUAL-ACTIONS-REQUIRED.md`

- [ ] **Step 1: Append a new numbered section**

Follow the existing heading style (`## N. Title`). The file currently runs to section 10.

```markdown
## 11. Google Ads campaigns for the competitive capture programme

Spec: `docs/superpowers/specs/2026-08-18-competitive-capture-design.md` §6.

**Do first, before any spend:** confirm phone-click and WhatsApp-click conversion
actions exist and fire. `AW-17988388404` is on every page and wired for form
submissions; call conversions are unverified. A call-only campaign without a call
conversion action spends blind.

1. **Generic funeral, price-led.** "funeral singer london", "funeral choir hire
   london", "singer for funeral service", "funeral choir cost". RSA headlines led
   on "From £250, nothing added" and "Three sung pieces included, not one".
   Landing: `funerals.html`, with `compare/london-funeral-singers.html` as an A/B
   alternative. This is where the budget goes.
2. **Call-only, short notice.** Evening and weekend scheduling. Keywords around
   "short notice", "this week", "urgent".
3. **Brand defence.** LCS brand terms, exact match, capped budget.
4. **Conquest.** Competitor brand terms as keywords, landing on
   `compare/london-funeral-singers.html`. **Their trademark must not appear in ad
   text** — Google permits the mark as a keyword but restricts it in creative, and
   the owner can complain. Negative-match trade terms ("funeral director", "trade",
   "supplier") so the campaign stays on the family audience the landing page
   addresses. Expect low volume and a poor quality score; keep it a small line item.
5. **Borough and crematorium geo.** Hold until those landing pages exist.

Site-wide negatives: jobs, wanted, free, karaoke, courses, "become a".

Note that conversion modelling is degraded until Consent Mode v2 exists
(ROADMAP R4). Read the figures accordingly.

### Quarterly: re-check competitor pricing

`data/competitor-pricing.yml` carries a `checked_date`. `build.sh` prints a STALE
warning once it passes 120 days. Every quarter, open
https://www.londonfuneralsingers.co.uk/pricing, compare each `source_quote` against
what is published, and update the figures, the `checked_date`, and
`compare/london-funeral-singers.html` **in the same commit** — a figure and its date
must never disagree. If their prices moved, the `derived_figures` totals and savings
need recomputing too, and the build will fail until they are.
```

- [ ] **Step 2: Commit**

```bash
git add MANUAL-ACTIONS-REQUIRED.md
git commit -m "docs: record the Google Ads work as a manual action

Dashboard work an agent must not attempt. Includes the trademark
constraint on conquest ad copy and the call-conversion prerequisite."
```

---

## Task 13: Record the conventions and close the programme out

**Files:**
- Modify: `CLAUDE.md`, `docs/ROADMAP.md`

- [ ] **Step 1: Extend the CLAUDE.md conventions**

The Conventions section already says *"Prices quoted anywhere must match `pricing.html`."* Add directly beneath it:

```markdown
- Competitor figures must match `data/competitor-pricing.yml`, quote the source verbatim, and carry a visible checked date. `build.sh` fails if a price on a `compare/` page is not derivable from that file. Re-check quarterly (see `MANUAL-ACTIONS-REQUIRED.md` §11).
- `compare/` addresses families. Never link to it from a `for-*.html` page or reuse its inc-VAT figures there — a VAT-registered business buyer reclaims VAT, so those figures do not describe their position.
- **Alma Consort Ltd is not VAT-registered.** Never state or imply otherwise.
```

Also add `validate_competitor_claims.py` to the Commands section:

```markdown
- Competitor claim check alone: `python3 validate_competitor_claims.py`
- Validator tests: `python3 tests/test_competitor_claims.py`
```

- [ ] **Step 2: Add the roadmap entry**

Append a completed item to `docs/ROADMAP.md` following the existing format, marked `[done 2026-08-18]`, describing the programme and linking the spec and this plan.

- [ ] **Step 3: Verify**

```bash
./build.sh
python3 tests/test_competitor_claims.py
grep -c 'competitor-pricing.yml' CLAUDE.md
```

Expected: build green; `0 failure(s)`; count at least `1`.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/ROADMAP.md
git commit -m "docs: record competitor-claim conventions and close out the programme"
```

---

## Done when

- `./build.sh` exits 0 and ends with `Competitor claims valid across 1 compare/ page(s).`
- `python3 tests/test_competitor_claims.py` reports `0 failure(s)`.
- A hand-edited unsourced figure on the comparison page fails the build (verified in Task 4 step 3).
- `grep -rn '£215' --include='*.html' --include='*.txt' .` is empty.
- `grep -rn 'VAT' --include='for-*.html' .` is empty.
- The comparison page is reachable from at least four hub pages and absent from the main nav.
- No `for-*.html` page links to `compare/`.
