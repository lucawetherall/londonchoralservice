#!/usr/bin/env python3
"""Lint the Monday review's reply before it goes to the owner (plan 2026-10-31, task 5). Read-only.

    .venv/bin/python scripts/reports/review_lint.py <review file>

Prints "lint: clean" and exits 0, or one line per finding, "line N: <check>: <short reason>", and exits 1 (2 for a
usage error or an unreadable file). A finding names the line and the check, never a client's name, email or phone.

The checks:
  contact        an email address or a UK phone number, except the business's own (07356 042468,
                 office@londonchoralservice.com, luca@almaconsort.com)
  client name    a ledger client_name (whole name, case-insensitive, word-bounded; names under 5 characters skipped)
  price          under a Decisions, Ad copy, GBP posts or Landing page heading (any level, or a bold label such as
                 "**Ad copy**"), a figure from £250 to £10,000 that the visible text of pricing.html and
                 christmas-pricing.html never shows (CLAUDE.md's £550 and £1,400 combinations allowed), or that sits
                 next to one item (soloist, small choir, organist…) whose price on those pages is different
  house rule     the roster-size and London cathedral-choir patterns of validate_house_claims.py
  proposal form  a numbered item under "## Decisions" without " → "
  targeting      a Decisions item adding a keyword (not a negative) with singer, soloist, solo or vocalist
  length         more than 900 words before the last line ending with "?"
"""

import html.parser
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts" / "bookings"))
import validate_house_claims as vhc  # noqa: E402
import lcs_money as lm  # noqa: E402
from assistant_io import PriceParser  # noqa: E402  the assistant's own reading of the price tables

PRICE_PAGES = ("pricing.html", "christmas-pricing.html")
EXTRA_PRICES = {550, 1400}  # CLAUDE.md: soloist + organist £550; Small Choir + organist £1,400
PRICE_MIN, PRICE_MAX = 250, 10000
MAX_WORDS = 900
MIN_NAME = 5
OWN_PHONES = {"07356042468"}
OWN_EMAILS = {"office@londonchoralservice.com", "luca@almaconsort.com"}

# The house rules, taken from the build's own validator so the two never drift.
_HOUSE_LABELS = ("roster-scale claim", "London cathedral-choir supplement claim")
HOUSE_RULES = [(b[0], b[1], b[3] if len(b) > 3 else None) for b in vhc.BANNED if b[1] in _HOUSE_LABELS]
if len(HOUSE_RULES) != len(_HOUSE_LABELS):
    raise SystemExit("review_lint: validate_house_claims.py no longer has the roster and London cathedral rules")

CHECKED_SECTION = re.compile(r"\b(?:decisions|ad copy|gbp posts?|landing pages?)\b", re.I)
DECISIONS = re.compile(r"\bdecisions\b", re.I)
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
BOLD_LABEL = re.compile(r"^\s*\*\*([^*]+?)\*\*")
NUMBERED = re.compile(r"^\d+\. ")
GBP = re.compile(r"£\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?(?![\d,]*\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<![\w+])(?:\+44\s?(?:\(0\)\s?)?|0)\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}(?!\d)")
ADD_KEYWORD = re.compile(r"\badd\w*\b.*\bkeywords?\b|\bkeywords?\b.*\badd\w*\b", re.I)
NEGATIVE = re.compile(r"\bnegatives?\b", re.I)
SOLO_WORDS = re.compile(r"\b(?:singer|soloist|solo|vocalist)\b", re.I)
# An item named next to a price, and the pricing-table rows it is priced by.
ITEMS = {
    "soloist": (re.compile(r"\bsoloists?\b|\bsolo singers?\b", re.I), lambda n: n.startswith("soloist")),
    "small choir": (re.compile(r"\bsmall choir\b|\bquartet\b|\bchoir of four\b", re.I),
                    lambda n: n.startswith("small choir")),
    "quintet": (re.compile(r"\bquintet\b", re.I), lambda n: n.startswith("quintet")),
    "sextet": (re.compile(r"\bsextet\b", re.I), lambda n: n.startswith("sextet")),
    "full choir": (re.compile(r"\bfull choir\b|\bchoir of eight\b", re.I), lambda n: n.startswith("full choir")),
    "organist": (re.compile(r"\borganists?\b|\bpianists?\b", re.I), lambda n: n.startswith("organist")),
}
CHECK_ORDER = ["proposal form", "targeting", "client name", "contact", "price", "house rule", "length"]


class VisibleText(html.parser.HTMLParser):
    """The page's text as a reader sees it: no tags, scripts (JSON-LD included) or styles."""

    SKIP = {"script", "style", "noscript", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skipping = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skipping += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skipping:
            self.skipping -= 1

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(data)


def visible_text(page_html):
    p = VisibleText()
    p.feed(page_html)
    return " ".join(p.parts)


def figures(text):
    """[(match, pounds as int)] for each £ figure in `text`."""
    return [(m, int(m.group(1).replace(",", ""))) for m in GBP.finditer(text)]


def site_prices(repo=REPO):
    """(every £ figure the pricing pages show, {item: its table prices}), plus CLAUDE.md's combinations."""
    allowed, items = set(EXTRA_PRICES), {k: set() for k in ITEMS}
    for page in PRICE_PAGES:
        source = (repo / page).read_text(encoding="utf-8")
        allowed |= {v for _, v in figures(visible_text(source))}
        parser = PriceParser()
        parser.feed(source)
        for row in parser.rows:
            name = row["name"].lower()
            for key, (_, is_row) in ITEMS.items():
                if is_row(name):
                    items[key] |= {v for _, v in figures(row["price"])}
    return allowed, items


def item_next_to(line, m, previous_end):
    """The one item named in the same clause as the figure `m`, or None (none, or more than one)."""
    before = line[max(previous_end, m.start() - 50):m.start()]
    before = re.split(r"[;.|(]", before)[-1]
    after = re.split(r"[;.,|)£]", line[m.end():m.end() + 30])[0]
    named = {key for key, (rx, _) in ITEMS.items() if rx.search(before) or rx.search(after)}
    return named.pop() if len(named) == 1 else None


def price_findings(line, allowed, items):
    out, previous_end = [], 0
    for m, value in figures(line):
        if PRICE_MIN <= value <= PRICE_MAX:
            item = item_next_to(line, m, previous_end)
            if value not in allowed:
                out.append(f"£{value:,} is on neither pricing page")
            elif item and items.get(item) and value not in items[item]:
                want = " or ".join(f"£{v:,}" for v in sorted(items[item]))
                out.append(f"£{value:,} for a {item}; the pricing pages have {want}")
        previous_end = m.end()
    return out


def name_patterns(names):
    out = []
    for name in {(n or "").strip() for n in names}:
        if len(name) >= MIN_NAME:
            words = [re.escape(w) for w in name.split()]
            out.append(re.compile(r"(?<!\w)" + r"\s+".join(words) + r"(?!\w)", re.I))
    return out


def phone_digits(text):
    digits = re.sub(r"\D", "", text)
    return "0" + digits[2:] if text.startswith("+") else digits


def lint(text, names=(), prices=None):
    """[(line number, check, reason)] for the review `text`, in line order. `names`: the ledger's client names;
    `prices`: site_prices() (read from the pages when None)."""
    allowed, items = prices or site_prices()
    names_rx = name_patterns(names)
    lines = text.splitlines()
    found = []
    heading = label = ""
    for n, line in enumerate(lines, 1):
        h = HEADING.match(line)
        if h:
            heading, label = h.group(1), ""
        else:
            b = BOLD_LABEL.match(line)
            if b:
                label = b.group(1)
        in_decisions = bool(DECISIONS.search(heading))
        if in_decisions and not h and NUMBERED.match(line):
            if " → " not in line:
                found.append((n, "proposal form", "a numbered decision without \" → \""))
            proposal = line.split(" — ")[0]
            if ADD_KEYWORD.search(proposal) and not NEGATIVE.search(proposal) and SOLO_WORDS.search(proposal):
                found.append((n, "targeting", "a proposed keyword with singer, soloist, solo or vocalist"))
        if any(rx.search(line) for rx in names_rx):
            found.append((n, "client name", "a client name from the ledger"))
        if any(e.group(0).lower() not in OWN_EMAILS for e in EMAIL.finditer(line)):
            found.append((n, "contact", "an email address"))
        phones = [phone_digits(p.group(0)) for p in PHONE.finditer(line)]
        if any(len(d) in (10, 11) and d not in OWN_PHONES for d in phones):
            found.append((n, "contact", "a phone number"))
        if CHECKED_SECTION.search(heading) or CHECKED_SECTION.search(label):
            found += [(n, "price", reason) for reason in price_findings(line, allowed, items)]
    for pattern, rule, scope in HOUSE_RULES:
        for m in pattern.finditer(text):
            if vhc.in_scope(scope, "", text, m):
                found.append((text.count("\n", 0, m.start()) + 1, "house rule", rule))
    asks = [i for i, line in enumerate(lines) if line.rstrip().rstrip("*_ ").endswith("?")]
    end = asks[-1] if asks else len(lines)
    words = sum(len(line.split()) for line in lines[:end])
    if words > MAX_WORDS:
        found.append((end + 1 if asks else max(len(lines), 1), "length",
                      f"{words} words before the final question (at most {MAX_WORDS})"))
    return sorted(dict.fromkeys(found), key=lambda f: (f[0], CHECK_ORDER.index(f[1])))


def ledger_names():
    """The ledger's client names, or None when there is no ledger."""
    if not Path(lm.LEDGER).exists():
        return None
    return [r.get("client_name") or "" for r in lm.read_csv(lm.LEDGER)]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: review_lint.py <review file>", file=sys.stderr)
        return 2
    try:
        text = Path(argv[0]).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"review_lint: cannot read the review file ({type(e).__name__})", file=sys.stderr)
        return 2
    names = ledger_names()
    if names is None:
        print("review_lint: no ledger found; client names not checked", file=sys.stderr)
    findings = lint(text, names or [])
    if not findings:
        print("lint: clean")
        return 0
    for n, check, reason in findings:
        print(f"line {n}: {check}: {reason}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
