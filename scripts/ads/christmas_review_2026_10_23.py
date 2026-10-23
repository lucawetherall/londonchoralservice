#!/usr/bin/env python3
"""23 Oct 2026 change set 1: Christmas campaign (24295921372) after the review of 23 October.

a. Ad schedule: none → every day 07:00–24:00 (seven entries, minutes on the hour). Refuses if the campaign
   already has any schedule entry.
b. Keyword "christmas carol singers london" phrase (1894700369719, "Hire carol singers"): enabled → paused.
   The exact version stays enabled; the script refuses if it isn't.
c. Campaign negatives: exact [london christmas carol], phrase "carol event", broad 2025. Existing negatives
   are skipped, and the script refuses if any new one would block an enabled keyword in the campaign.
d. Ad 825999587211 display path: Christmas/Prices → Carol-Singers/London, edited in place (the update mask
   names path1 and path2 only; headlines, descriptions and the final URL are untouched).

Budget and bids are untouched. Nothing is deleted. Every value is checked against the account before anything
is sent, and the whole set goes as one atomic request.

    source .venv/bin/activate
    python scripts/ads/christmas_review_2026_10_23.py            # validate
    python scripts/ads/christmas_review_2026_10_23.py --apply    # after approval
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
CHRISTMAS = 24295921372
CAMPAIGN = "Christmas carol singers – events 2026"
AD_GROUP = "Hire carol singers"
PHRASE_KW, KW_TEXT = 1894700369719, "christmas carol singers london"
AD_ID = 825999587211
OLD_PATHS, NEW_PATHS = ("Christmas", "Prices"), ("Carol-Singers", "London")
START_HOUR, END_HOUR = 7, 24
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
NEGATIVES = [
    ("london christmas carol", "EXACT",
     "event-goer search 'london christmas carol': 8 impressions and 1 click (£3.44) since 26 Sep, no lead"),
    ("carol event", "PHRASE",
     "event-goer search 'christmas carol event london' (4 impressions since 26 Sep); the plural \"carol events\" "
     "is already a negative and negatives don't match plurals"),
    ("2025", "BROAD", "last year's dated search 'christmas choir london 2025' (2 impressions since 26 Sep)"),
]
SCRIPT = "scripts/ads/christmas_review_2026_10_23.py"


def shown(text, match):
    return f"[{text}]" if match == "EXACT" else (f'"{text}"' if match == "PHRASE" else text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    for p in NEW_PATHS:
        if len(p) > 15:
            raise SystemExit(f'display path "{p}" is over 15 characters; nothing sent')
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))

    # --- check the account matches what was approved --------------------------
    camp = q(f"SELECT campaign.name FROM campaign WHERE campaign.id = {CHRISTMAS}")
    if len(camp) != 1 or camp[0].campaign.name != CAMPAIGN:
        raise SystemExit(f'campaign {CHRISTMAS} is not "{CAMPAIGN}"; nothing sent')

    sched = q("SELECT campaign_criterion.criterion_id FROM campaign_criterion "
              f"WHERE campaign.id = {CHRISTMAS} AND campaign_criterion.type = 'AD_SCHEDULE' "
              "AND campaign_criterion.status != 'REMOVED'")
    if sched:
        raise SystemExit(f"the campaign already has {len(sched)} ad schedule entr(ies); nothing sent")

    kws = q("SELECT ad_group.name, ad_group_criterion.criterion_id, ad_group_criterion.resource_name, "
            "ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type, ad_group_criterion.status, "
            "ad_group_criterion.cpc_bid_micros FROM ad_group_criterion "
            f"WHERE campaign.id = {CHRISTMAS} AND ad_group_criterion.type = 'KEYWORD' "
            "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status != 'REMOVED'")
    target = [r for r in kws if r.ad_group_criterion.criterion_id == PHRASE_KW]
    if len(target) != 1:
        raise SystemExit(f"keyword {PHRASE_KW} not found in the campaign; nothing sent")
    k = target[0]
    if (k.ad_group.name, k.ad_group_criterion.keyword.text, k.ad_group_criterion.keyword.match_type.name,
            k.ad_group_criterion.status.name) != (AD_GROUP, KW_TEXT, "PHRASE", "ENABLED"):
        raise SystemExit(f"keyword {PHRASE_KW} is {k.ad_group_criterion.keyword.text!r} "
                         f"{k.ad_group_criterion.keyword.match_type.name} {k.ad_group_criterion.status.name} in "
                         f'"{k.ad_group.name}", not "{KW_TEXT}" PHRASE ENABLED in "{AD_GROUP}"; nothing sent')
    exact = [r for r in kws if r.ad_group.name == AD_GROUP and r.ad_group_criterion.keyword.text.lower() == KW_TEXT
             and r.ad_group_criterion.keyword.match_type.name == "EXACT"
             and r.ad_group_criterion.status.name == "ENABLED"]
    if len(exact) != 1:
        raise SystemExit(f"the exact [{KW_TEXT}] is not enabled in \"{AD_GROUP}\"; pausing the phrase would drop "
                         "the search entirely; nothing sent")

    positives = [(r.ad_group_criterion.keyword.text, r.ad_group_criterion.keyword.match_type.name) for r in q(
        "SELECT ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type FROM ad_group_criterion "
        f"WHERE campaign.id = {CHRISTMAS} AND ad_group_criterion.type = 'KEYWORD' "
        "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status = 'ENABLED' "
        "AND ad_group.status = 'ENABLED'")]
    existing = {(r.campaign_criterion.keyword.text.lower(), r.campaign_criterion.keyword.match_type.name) for r in q(
        "SELECT campaign_criterion.keyword.text, campaign_criterion.keyword.match_type FROM campaign_criterion "
        f"WHERE campaign.id = {CHRISTMAS} AND campaign_criterion.negative = TRUE "
        "AND campaign_criterion.type = 'KEYWORD'")}
    new_negs = [(t, m, why) for t, m, why in NEGATIVES if (t.lower(), m) not in existing]
    hits = blocked([(t, m) for t, m, _ in new_negs], positives)
    if hits:
        for nt, nm, kt, km in hits:
            print(f"BLOCKS: negative {shown(nt, nm)} would block the keyword {shown(kt, km)}")
        raise SystemExit("a new negative would block an enabled keyword; nothing sent")

    ads = q("SELECT ad_group.name, ad_group_ad.status, ad_group_ad.ad.resource_name, "
            "ad_group_ad.ad.responsive_search_ad.path1, ad_group_ad.ad.responsive_search_ad.path2 FROM ad_group_ad "
            f"WHERE campaign.id = {CHRISTMAS} AND ad_group_ad.ad.id = {AD_ID}")
    if len(ads) != 1:
        raise SystemExit(f"ad {AD_ID} not found in the campaign; nothing sent")
    ad = ads[0]
    rsa = ad.ad_group_ad.ad.responsive_search_ad
    if (rsa.path1, rsa.path2) != OLD_PATHS:
        raise SystemExit(f"ad {AD_ID} paths are {rsa.path1!r}/{rsa.path2!r}, not "
                         f"{OLD_PATHS[0]!r}/{OLD_PATHS[1]!r}; nothing sent")

    # --- build one atomic request ----------------------------------------------
    ops, changes = [], []  # changes: (resource, field, current → new, reason)

    for d in DAYS:
        op = c.get_type("MutateOperation")
        cc = op.campaign_criterion_operation.create
        cc.campaign = ga.campaign_path(CUSTOMER_ID, CHRISTMAS)
        cc.ad_schedule.day_of_week = E.DayOfWeekEnum[d]
        cc.ad_schedule.start_hour, cc.ad_schedule.end_hour = START_HOUR, END_HOUR
        cc.ad_schedule.start_minute = E.MinuteOfHourEnum.ZERO
        cc.ad_schedule.end_minute = E.MinuteOfHourEnum.ZERO
        ops.append(op)
    changes.append(("campaign", "ad schedule", f"none → every day {START_HOUR:02d}:00–{END_HOUR:02d}:00 (7 entries)",
                    "00:00–07:00 took 5 of 33 clicks (£15.90 of £109.59) in the last 90 days, no leads; "
                    "the evening up to midnight is kept"))

    op = c.get_type("MutateOperation")
    op.ad_group_criterion_operation.update.resource_name = k.ad_group_criterion.resource_name
    op.ad_group_criterion_operation.update.status = E.AdGroupCriterionStatusEnum.PAUSED
    op.ad_group_criterion_operation.update_mask.paths.append("status")
    ops.append(op)
    changes.append((f'ad group "{AD_GROUP}" keyword "{KW_TEXT}" (phrase, {PHRASE_KW})', "status", "enabled → paused",
                    "£23.04 since 26 Sep; every visible matched search was someone looking for a carol event to "
                    f"attend; the exact [{KW_TEXT}] stays enabled"))

    for t, m, why in new_negs:
        op = c.get_type("MutateOperation")
        cc = op.campaign_criterion_operation.create
        cc.campaign = ga.campaign_path(CUSTOMER_ID, CHRISTMAS)
        cc.negative = True
        cc.keyword.text = t
        cc.keyword.match_type = E.KeywordMatchTypeEnum[m]
        ops.append(op)
        changes.append((f"negative keyword {shown(t, m)} ({m.lower()})", "campaign negative", "none → added", why))

    op = c.get_type("MutateOperation")
    op.ad_operation.update.resource_name = ad.ad_group_ad.ad.resource_name
    op.ad_operation.update.responsive_search_ad.path1 = NEW_PATHS[0]
    op.ad_operation.update.responsive_search_ad.path2 = NEW_PATHS[1]
    op.ad_operation.update_mask.paths.extend(["responsive_search_ad.path1", "responsive_search_ad.path2"])
    ops.append(op)
    changes.append((f'ad {AD_ID} in "{ad.ad_group.name}"', "display path",
                    f"{OLD_PATHS[0]}/{OLD_PATHS[1]} → {NEW_PATHS[0]}/{NEW_PATHS[1]}",
                    "the ad lands on christmas.html, the carol singers page, not the prices page; the path now "
                    "says what the searcher asked for"))

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operation(s), one atomic request\n")
    for res, field, what, why in changes:
        print(f"• {CAMPAIGN} · {res} · {field}: {what}\n    reason: {why}")
    for t, m, _ in NEGATIVES:
        if (t.lower(), m) in existing:
            print(f"  skipped: negative {shown(t, m)} already exists")
    print(f"  checked: no new negative blocks any of the {len(positives)} enabled keywords in the campaign")
    print(f"  unchanged: exact [{KW_TEXT}] stays enabled at £{exact[0].ad_group_criterion.cpc_bid_micros / 1e6:.2f}")
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
        ads_log.append_row(f'| {now} | campaign "{CAMPAIGN}" {res} | {field} | {what} | {why} | `{SCRIPT}` |')
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
