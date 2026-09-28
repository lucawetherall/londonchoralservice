"""The quote calculator: packages, the organist add-on and the soloist-with-organist price from pricing.html and
christmas-pricing.html, parsed by assistant_io.PriceParser (the parser the reply drafter's `prices` command uses).

Every figure comes from the pages; nothing here holds a price. Travel is never priced (it is "confirmed with the
quote"), and the Christmas Eve and Christmas Day premium is the page's own percentage, stated but never added to
the total. The wording follows the house rules: UK English, "No VAT is added." as the only VAT wording (Alma Consort
Ltd is not VAT-registered), no roster size.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "bookings"))
import assistant_io  # noqa: E402

LISTS = {"standard": "pricing.html", "christmas": "christmas-pricing.html"}
LIST_LABELS = {"standard": "Weddings, funerals, events", "christmas": "Christmas carol singers"}
POUNDS = re.compile(r"£\s?([\d,]+)")
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
                10: "ten", 11: "eleven", 12: "twelve", 16: "sixteen", 20: "twenty"}
COMBO = re.compile(r"^soloist with an organist or pianist:\s*£\s?([\d,]+)", re.I)
PERCENT = re.compile(r"around (\d{1,2})%", re.I)


def pounds(text):
    m = POUNDS.search(text or "")
    return int(m.group(1).replace(",", "")) if m else None


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def price_list(page, root=REPO):
    """{"page", "heading", "packages": [{key, name, singers, price, label}], "organist", "organist_name",
    "soloist_organist", "premium_pct"} from one pricing page. The packages are the first pricing table's rows
    with a £ figure; the organist is the first row anywhere naming an organist."""
    p = assistant_io.PriceParser()
    p.feed((Path(root) / page).read_text(encoding="utf-8"))
    packages, organist, organist_name = [], None, ""
    for r in p.rows:
        price = pounds(r["price"])
        if price is None:
            continue
        if re.search(r"organist", r["name"], re.I):
            if organist is None:
                organist, organist_name = price, r["name"]
            continue
        if r["table"] != 0:
            continue
        m = re.search(r"(\d+)\s+singers?", r["sub"] or "")
        singers = int(m.group(1)) if m else (1 if re.fullmatch(r"soloist", r["name"].strip(), re.I) else None)
        if singers is None:
            continue
        label = r["name"] + (f" ({r['sub']})" if r["sub"] else "")
        packages.append({"key": slug(r["name"]), "name": r["name"], "singers": singers, "price": price,
                         "label": label})
    combo = next((int(m.group(1).replace(",", "")) for x in p.extras for m in [COMBO.match(x)] if m), None)
    pct = next((int(m.group(1)) for x in p.notes if "Christmas Eve" in x for m in [PERCENT.search(x)] if m), None)
    return {"page": page, "heading": p.blocks[0][0] if p.blocks else "", "packages": packages,
            "organist": organist, "organist_name": organist_name, "soloist_organist": combo, "premium_pct": pct}


def load_lists(root=REPO):
    return {key: price_list(page, root) for key, page in LISTS.items()}


def money(n):
    return f"£{n:,}"


def calculate(lists, list_key, package_key, organist=False, travel=False, premium_day=False):
    """{"total", "lines": [(label, amount)], "wording", "package"}; ValueError for an unknown list or package, or an
    organist the page has no price for."""
    lst = lists.get(list_key) if isinstance(lists, dict) else None
    if not lst:
        raise ValueError("unknown price list")
    pkg = next((p for p in lst["packages"] if p["key"] == package_key), None)
    if pkg is None:
        raise ValueError("unknown package")
    if organist and lst["organist"] is None:
        raise ValueError("no organist price on that page")
    solo = pkg["singers"] == 1
    if solo:
        who = "a soloist"
    else:
        who = f"a {pkg['name']} of {NUMBER_WORDS.get(pkg['singers'], str(pkg['singers']))} singers"
    if organist and solo and lst["soloist_organist"]:
        total = lst["soloist_organist"]
        lines = [("Soloist with an organist or pianist", total)]
        first = f"{who} with an organist or pianist is {money(total)}."
    elif organist:
        total = pkg["price"] + lst["organist"]
        lines = [(pkg["label"], pkg["price"]), (lst["organist_name"] or "Organist", lst["organist"])]
        first = (f"{who} with an organist is {money(total)}: {money(pkg['price'])} for the "
                 f"{'soloist' if solo else 'singers'} and {money(lst['organist'])} for the organist.")
    else:
        total = pkg["price"]
        lines = [(pkg["label"], total)]
        first = f"{who} is {money(total)}."
    if list_key == "christmas":
        sentences = [f"For a two-hour booking, {first}"]
    else:
        sentences = [first[0].upper() + first[1:]]
    sentences.append("No VAT is added.")
    if travel:
        sentences.append("Travel beyond Greater London is extra, and we'll confirm it with the quote.")
    if premium_day and lst["premium_pct"]:
        sentences.append(f"Christmas Eve and Christmas Day carry a premium of around {lst['premium_pct']}%, which we "
                         f"confirm in the written quote.")
    return {"total": total, "lines": lines, "wording": " ".join(sentences), "package": pkg}
