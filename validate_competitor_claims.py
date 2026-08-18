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
