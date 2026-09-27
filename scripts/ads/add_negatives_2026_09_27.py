#!/usr/bin/env python3
"""Add campaign-level negative keywords from the first search terms seen after
the 26 September 2026 changes (Christmas concert-goers, funeral music research).

Default run is validate_only. --apply only after approval; applied changes
are appended to logs/ads-changes.md. Existing negatives are skipped.

    source .venv/bin/activate
    python scripts/ads/add_negatives_2026_09_27.py            # validate
    python scripts/ads/add_negatives_2026_09_27.py --apply    # after approval
"""

import argparse
import datetime
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/add_negatives_2026_09_27.py"

# (text, match type). BROAD negatives block any search containing every word;
# PHRASE negatives block searches containing the exact phrase.
PLAN = {
    24295921372: {  # Christmas carol singers – events 2026
        "reason": "First-day search terms were people looking for carol concerts and services to attend "
                  "(Royal Albert Hall, Westminster Abbey, 'christmas carols in london'), matched as 'same meaning' "
                  "by the 'carol singers london' keywords: 109 impressions, 0 clicks",
        "negatives": [
            ("concert", "BROAD"), ("concerts", "BROAD"), ("carols", "BROAD"), ("singalong", "BROAD"),
            ("albert hall", "PHRASE"), ("westminster abbey", "PHRASE"), ("sing along", "PHRASE"),
            ("carol service", "PHRASE"), ("carol services", "PHRASE"), ("carol singing", "PHRASE"),
        ],
    },
    23735776277: {  # funeral expert campaign
        "reason": "Paid click on 'best choral music for funerals': music research, not hiring a choir",
        "negatives": [("choral music", "PHRASE")],
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    client = GoogleAdsClient.load_from_storage()
    ga = client.get_service("GoogleAdsService")
    E = client.enums

    ops, changes = [], []
    for cid, plan in PLAN.items():
        name = next(iter(ga.search(customer_id=CUSTOMER_ID,
                                   query=f"SELECT campaign.name FROM campaign WHERE campaign.id = {cid}"))).campaign.name
        existing = {(r.campaign_criterion.keyword.text.lower(), r.campaign_criterion.keyword.match_type.name)
                    for r in ga.search(customer_id=CUSTOMER_ID, query=(
                        "SELECT campaign_criterion.keyword.text, campaign_criterion.keyword.match_type "
                        f"FROM campaign_criterion WHERE campaign.id = {cid} AND campaign_criterion.negative = TRUE "
                        "AND campaign_criterion.type = 'KEYWORD'"))}
        new = [(t, m) for t, m in plan["negatives"] if (t, m) not in existing]
        for t, m in new:
            o = client.get_type("MutateOperation")
            cc = o.campaign_criterion_operation.create
            cc.campaign = ga.campaign_path(CUSTOMER_ID, cid)
            cc.negative = True
            cc.keyword.text = t
            cc.keyword.match_type = E.KeywordMatchTypeEnum[m]
            ops.append(o)
        if new:
            listed = ", ".join(f'"{t}"' if m == "PHRASE" else t for t, m in new)
            changes.append((f'campaign "{name}" ({cid})', "negative keywords",
                            f"{len(existing)} negatives", f"+{len(new)}: {listed}", plan["reason"]))

    if not ops:
        print("Nothing to change: every negative already exists.")
        return
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} negatives\n")
    for res, field, cur, new, why in changes:
        print(f"{res}\n   {field}: {cur} → {new}\n   reason: {why}\n   (\"quoted\" = phrase match, others broad)\n")
    req = client.get_type("MutateGoogleAdsRequest")
    req.customer_id = CUSTOMER_ID
    req.mutate_operations.extend(ops)
    req.validate_only = not args.apply
    try:
        ga.mutate(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("Google accepted every operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    rows = "".join(f"| {now} | {r} | {f} | {c} → {n} | {w} | `{SCRIPT}` |\n" for r, f, c, n, w in changes)
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + rows, 1))
    print("Applied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
