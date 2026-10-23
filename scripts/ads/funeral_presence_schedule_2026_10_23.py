#!/usr/bin/env python3
"""23 Oct 2026 change set 2: funeral expert campaign (23735776277) after the review of 23 October.

a. Location targeting: presence or interest → presence (people in the targeted areas). wedding-leads was
   switched on 28 Sep (account_review_2026_09_28.py).
b. Ad schedule: none → every day 07:00–22:00 (seven entries, minutes on the hour). Refuses if the campaign
   already has any schedule entry.
c. Campaign negatives: exact [funeral singers], [funeral singers near me], [funeral singers london],
   [singers for funeral], [singers for funerals]; broad pipers, hymn. Existing negatives are skipped. The script
   refuses if any new one would block an enabled keyword in the campaign, or one of the two exact brand keywords
   change set 7 adds (funeral_brand_keywords_2026_10_23.py). Owner rule: choir searches only, never solo-singer
   searches; the "London Funeral Singers" competitor-brand keywords stay.

Budget and bids are untouched. Nothing is deleted. Every value is checked against the account before anything
is sent, and the whole set goes as one atomic request.

    source .venv/bin/activate
    python scripts/ads/funeral_presence_schedule_2026_10_23.py            # validate
    python scripts/ads/funeral_presence_schedule_2026_10_23.py --apply    # after approval
"""

import argparse
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ads_log  # noqa: E402
from negative_match import blocked  # noqa: E402

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
FUNERAL = 23735776277
CAMPAIGN = "funeral expert campaign"
START_HOUR, END_HOUR = 7, 22
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
SINGER_WHY = ("singer search, not a choir search (owner rule: choir bookings only); these five searches took "
              "5 clicks (£24.63) in 90 days, no conversions")
NEGATIVES = [
    ("funeral singers", "EXACT", SINGER_WHY),
    ("funeral singers near me", "EXACT", SINGER_WHY),
    ("funeral singers london", "EXACT", SINGER_WHY),
    ("singers for funeral", "EXACT", SINGER_WHY),
    ("singers for funerals", "EXACT", SINGER_WHY),
    ("pipers", "BROAD", "plural of the existing negative piper; negatives don't match plurals"),
    ("hymn", "BROAD", "singular of the existing negative hymns: searches for hymn choices, not singers to hire"),
]
# Added by change set 7 the same day: no negative here may block them either.
PLANNED = [("london funeral singers", "EXACT"), ("the london funeral singers", "EXACT")]
SCRIPT = "scripts/ads/funeral_presence_schedule_2026_10_23.py"


def shown(text, match):
    return f"[{text}]" if match == "EXACT" else (f'"{text}"' if match == "PHRASE" else text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))

    # --- check the account matches what was approved --------------------------
    camp = q("SELECT campaign.name, campaign.geo_target_type_setting.positive_geo_target_type FROM campaign "
             f"WHERE campaign.id = {FUNERAL}")
    if len(camp) != 1 or camp[0].campaign.name != CAMPAIGN:
        raise SystemExit(f'campaign {FUNERAL} is not "{CAMPAIGN}"; nothing sent')
    geo = camp[0].campaign.geo_target_type_setting.positive_geo_target_type.name
    if geo != "PRESENCE_OR_INTEREST":
        raise SystemExit(f"location targeting is {geo}, not PRESENCE_OR_INTEREST; nothing sent")

    sched = q("SELECT campaign_criterion.criterion_id FROM campaign_criterion "
              f"WHERE campaign.id = {FUNERAL} AND campaign_criterion.type = 'AD_SCHEDULE' "
              "AND campaign_criterion.status != 'REMOVED'")
    if sched:
        raise SystemExit(f"the campaign already has {len(sched)} ad schedule entr(ies); nothing sent")

    positives = [(r.ad_group_criterion.keyword.text, r.ad_group_criterion.keyword.match_type.name) for r in q(
        "SELECT ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type FROM ad_group_criterion "
        f"WHERE campaign.id = {FUNERAL} AND ad_group_criterion.type = 'KEYWORD' "
        "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status = 'ENABLED' "
        "AND ad_group.status = 'ENABLED'")]
    if not any("london funeral singers" in t.lower() for t, _ in positives):
        raise SystemExit('no enabled "London Funeral Singers" brand keyword found; the account differs; nothing sent')
    existing = {(r.campaign_criterion.keyword.text.lower(), r.campaign_criterion.keyword.match_type.name) for r in q(
        "SELECT campaign_criterion.keyword.text, campaign_criterion.keyword.match_type FROM campaign_criterion "
        f"WHERE campaign.id = {FUNERAL} AND campaign_criterion.negative = TRUE "
        "AND campaign_criterion.type = 'KEYWORD'")}
    new_negs = [(t, m, why) for t, m, why in NEGATIVES if (t.lower(), m) not in existing]
    hits = blocked([(t, m) for t, m, _ in new_negs], positives + PLANNED)
    if hits:
        for nt, nm, kt, km in hits:
            print(f"BLOCKS: negative {shown(nt, nm)} would block the keyword {shown(kt, km)}")
        raise SystemExit("a new negative would block an enabled or planned keyword; nothing sent")

    # --- build one atomic request ----------------------------------------------
    ops, changes = [], []  # changes: (resource, field, current → new, reason)

    op = c.get_type("MutateOperation")
    op.campaign_operation.update.resource_name = ga.campaign_path(CUSTOMER_ID, FUNERAL)
    op.campaign_operation.update.geo_target_type_setting.positive_geo_target_type = \
        E.PositiveGeoTargetTypeEnum.PRESENCE
    op.campaign_operation.update_mask.paths.append("geo_target_type_setting.positive_geo_target_type")
    ops.append(op)
    changes.append(("campaign", "location targeting", "presence or interest → presence",
                    "since 26 Sep £47.21 of £133.89 (35%) came from searchers outside every targeted area, "
                    "no leads; wedding-leads was switched on 28 Sep"))

    for d in DAYS:
        op = c.get_type("MutateOperation")
        cc = op.campaign_criterion_operation.create
        cc.campaign = ga.campaign_path(CUSTOMER_ID, FUNERAL)
        cc.ad_schedule.day_of_week = E.DayOfWeekEnum[d]
        cc.ad_schedule.start_hour, cc.ad_schedule.end_hour = START_HOUR, END_HOUR
        cc.ad_schedule.start_minute = E.MinuteOfHourEnum.ZERO
        cc.ad_schedule.end_minute = E.MinuteOfHourEnum.ZERO
        ops.append(op)
    changes.append(("campaign", "ad schedule", f"none → every day {START_HOUR:02d}:00–{END_HOUR:02d}:00 (7 entries)",
                    "20:00–07:00 took 33% of 90-day spend with no leads; evenings to 22:00 kept because "
                    "families plan then"))

    for t, m, why in new_negs:
        op = c.get_type("MutateOperation")
        cc = op.campaign_criterion_operation.create
        cc.campaign = ga.campaign_path(CUSTOMER_ID, FUNERAL)
        cc.negative = True
        cc.keyword.text = t
        cc.keyword.match_type = E.KeywordMatchTypeEnum[m]
        ops.append(op)
        changes.append((f"negative keyword {shown(t, m)} ({m.lower()})", "campaign negative", "none → added", why))

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operation(s), one atomic request\n")
    for res, field, what, why in changes:
        print(f"• {CAMPAIGN} · {res} · {field}: {what}\n    reason: {why}")
    for t, m, _ in NEGATIVES:
        if (t.lower(), m) in existing:
            print(f"  skipped: negative {shown(t, m)} already exists")
    brand = sorted(shown(t, m) for t, m in positives if "london funeral singers" in t.lower())
    print(f"  checked: no new negative blocks any of the {len(positives)} enabled keywords in the campaign "
          f"(brand: {', '.join(brand)}) or the planned exact {', '.join(shown(t, m) for t, m in PLANNED)}")
    if args.apply:
        ads_log.check_log()  # refuse before changing anything if the log can't be written
    try:
        req = c.get_type("MutateGoogleAdsRequest")
        req.customer_id = CUSTOMER_ID
        req.mutate_operations.extend(ops)
        req.validate_only = not args.apply
        ga.mutate(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("\nGoogle accepted every operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    for res, field, what, why in reversed(changes):
        ads_log.append_row(f'| {now} | campaign "{CAMPAIGN}" ({FUNERAL}) {res} | {field} | {what} | {why} | `{SCRIPT}` |')
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
