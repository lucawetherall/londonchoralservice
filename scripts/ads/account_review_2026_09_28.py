#!/usr/bin/env python3
"""Account review of 28 September 2026 (owner approved every item): pay for the searches that convert.

1. wedding-leads: location targeting "presence or interest" → "presence" (Greater London only). Searchers
   outside London took 62 clicks (£273) in 90 days and converted nothing.
2. funeral expert campaign: Maximise clicks (£5 cap) → manual CPC. Choir keywords £5.00 (they convert),
   "London Funeral Singers" brand keywords £2.00 (kept, paid less), the rest £3.50.
3. wedding-leads: Maximise clicks (£5 cap) → manual CPC. Exact choir keywords £4.50, phrase £3.00,
   "choir for wedding ceremony" £2.50 (quality score 4, 13 clicks, nothing).
4. wedding-leads: ad schedule 07:00–23:15 → 07:00–20:00 every day. Evening clicks converted nothing.
   A schedule can't be edited in place: the seven old entries are replaced by seven new ones.
5. Christmas: [christmas carol singers london] exact and phrase, [carol singers london] exact £2.50 → £3.50,
   above their first-page estimates (£2.77 and £3.33).
6. wedding-leads sitelink "Wedding Music Guide": weddings.html (the landing page) → the wedding choir guide.

The funeral budget (£4 → £5) goes through scripts/ads/set_budget.py, which checks the cap.
Validate-only by default; --apply after approval, logged to logs/ads-changes.md. Nothing is removed
except the schedule entries being replaced.

    source .venv/bin/activate
    python scripts/ads/account_review_2026_09_28.py            # validate
    python scripts/ads/account_review_2026_09_28.py --apply    # after approval
"""

import argparse
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ads_log  # noqa: E402

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
FUNERAL, WEDDING, CHRISTMAS = 23735776277, 23739971001, 24295921372
SCRIPT = "scripts/ads/account_review_2026_09_28.py"
GUIDE_SITELINK = "customers/8733881378/assets/348796933583"
GUIDE_URL = "https://londonchoralservice.com/music-guides/wedding-choir-guide.html"
CHRISTMAS_RAISE = {("christmas carol singers london", "EXACT"), ("christmas carol singers london", "PHRASE"),
                   ("carol singers london", "EXACT")}
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


def gbp(m):
    return f"£{m / 1e6:.2f}"


def funeral_bid(text):
    t = text.lower()
    if "choir" in t:
        return 5_000_000, "funeral choir search: these convert"
    if "funeral singers" in t or "londonfuneralsingers" in t:
        return 2_000_000, "competitor-brand search: kept, but 13 clicks (£58) brought nothing"
    return 3_500_000, "other funeral music search"


def wedding_bid(text, mt):
    t = text.lower()
    if t == "choir for wedding ceremony":
        return 2_500_000, "quality score 4, 13 clicks and nothing"
    if mt == "EXACT":
        return 4_500_000, "exact wedding choir search"
    return 3_000_000, "phrase wedding choir search"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.apply:
        ads_log.check_log()
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    ops, changes = [], []

    def change(res, field, cur, new, why):
        changes.append((res, field, cur, new, why))

    names = {}
    for r in ga.search(customer_id=CUSTOMER_ID, query=(
            "SELECT campaign.id, campaign.name, campaign.resource_name, campaign.bidding_strategy_type, "
            "campaign.target_spend.cpc_bid_ceiling_micros, campaign.geo_target_type_setting.positive_geo_target_type "
            f"FROM campaign WHERE campaign.id IN ({FUNERAL}, {WEDDING}, {CHRISTMAS})")):
        k = r.campaign
        names[k.id] = f'campaign "{k.name}" ({k.id})'
        o = c.get_type("MutateOperation")  # one operation per campaign: Google refuses two on the same resource
        u = o.campaign_operation.update
        u.resource_name = k.resource_name
        if k.id == WEDDING and k.geo_target_type_setting.positive_geo_target_type.name != "PRESENCE":
            u.geo_target_type_setting.positive_geo_target_type = E.PositiveGeoTargetTypeEnum.PRESENCE
            o.campaign_operation.update_mask.paths.append("geo_target_type_setting.positive_geo_target_type")
            change(names[k.id], "location targeting", "presence or interest", "presence (in Greater London)",
                   "62 clicks (£273) from searchers outside London in 90 days, no conversions of any kind")
        if k.id in (FUNERAL, WEDDING) and k.bidding_strategy_type.name != "MANUAL_CPC":
            manual = c.get_type("ManualCpc")
            manual.enhanced_cpc_enabled = False
            c.copy_from(u.manual_cpc, manual)
            o.campaign_operation.update_mask.paths.append("manual_cpc.enhanced_cpc_enabled")
            change(names[k.id], "bidding", f"Maximise clicks (max {gbp(k.target_spend.cpc_bid_ceiling_micros)} a click)",
                   "manual CPC, no enhanced CPC",
                   "About one click a day gives Maximise clicks nothing to learn from; it pays near the cap on every "
                   "click. Manual bids pay by what the search is worth")
        if o.campaign_operation.update_mask.paths:
            ops.append(o)
    if len(names) != 3:
        raise SystemExit("not all three campaigns found; nothing changed")

    for r in ga.search(customer_id=CUSTOMER_ID, query=(
            "SELECT campaign.id, ad_group_criterion.resource_name, ad_group_criterion.keyword.text, "
            "ad_group_criterion.keyword.match_type, ad_group_criterion.cpc_bid_micros FROM ad_group_criterion "
            f"WHERE campaign.id IN ({FUNERAL}, {WEDDING}, {CHRISTMAS}) AND ad_group_criterion.type = 'KEYWORD' "
            "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status = 'ENABLED'")):
        k = r.ad_group_criterion
        text, mt = k.keyword.text, k.keyword.match_type.name
        if r.campaign.id == FUNERAL:
            bid, why = funeral_bid(text)
        elif r.campaign.id == WEDDING:
            bid, why = wedding_bid(text, mt)
        elif (text.lower(), mt) in CHRISTMAS_RAISE:
            bid, why = 3_500_000, "first-page bid estimate (£2.77–£3.33) is above the £2.50 default"
        else:
            continue
        if k.cpc_bid_micros == bid:
            continue
        o = c.get_type("MutateOperation")
        u = o.ad_group_criterion_operation.update
        u.resource_name = k.resource_name
        u.cpc_bid_micros = bid
        o.ad_group_criterion_operation.update_mask.paths.append("cpc_bid_micros")
        ops.append(o)
        shown = f"[{text}]" if mt == "EXACT" else (f'"{text}"' if mt == "PHRASE" else text)
        change(f"{names[r.campaign.id]} keyword {shown}", "max CPC",
               "ad group default" if not k.cpc_bid_micros else gbp(k.cpc_bid_micros), gbp(bid), why)

    old = [r.campaign_criterion for r in ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT campaign.id, campaign_criterion.resource_name, campaign_criterion.ad_schedule.day_of_week, "
        "campaign_criterion.ad_schedule.start_hour, campaign_criterion.ad_schedule.end_hour, "
        "campaign_criterion.ad_schedule.end_minute FROM campaign_criterion "
        f"WHERE campaign.id = {WEDDING} AND campaign_criterion.type = 'AD_SCHEDULE'"))]
    already = {(s.ad_schedule.day_of_week.name, s.ad_schedule.start_hour, s.ad_schedule.end_hour, s.ad_schedule.end_minute.name)
               for s in old} == {(d, 7, 20, "ZERO") for d in DAYS}
    if not already:
        for s in old:
            o = c.get_type("MutateOperation")
            o.campaign_criterion_operation.remove = s.resource_name
            ops.append(o)
        for d in DAYS:
            o = c.get_type("MutateOperation")
            cc = o.campaign_criterion_operation.create
            cc.campaign = ga.campaign_path(CUSTOMER_ID, WEDDING)
            cc.ad_schedule.day_of_week = E.DayOfWeekEnum[d]
            cc.ad_schedule.start_hour, cc.ad_schedule.end_hour = 7, 20
            cc.ad_schedule.start_minute = E.MinuteOfHourEnum.ZERO
            cc.ad_schedule.end_minute = E.MinuteOfHourEnum.ZERO
            ops.append(o)
        shown = ", ".join(f"{s.ad_schedule.day_of_week.name[:3].title()} {s.ad_schedule.start_hour:02d}:00–"
                          f"{s.ad_schedule.end_hour:02d}:{'15' if s.ad_schedule.end_minute.name == 'FIFTEEN' else '00'}"
                          for s in old) or "none"
        change(names[WEDDING], "ad schedule", shown, "every day 07:00–20:00",
               "20:00–23:00 took 45 clicks (£197) across both campaigns since July with no conversions of any kind; "
               "form leads all arrived 07:00–18:00 (the old entries are replaced, not edited)")

    for r in ga.search(customer_id=CUSTOMER_ID, query=(
            "SELECT asset.resource_name, asset.sitelink_asset.link_text, asset.final_urls FROM asset "
            f"WHERE asset.resource_name = '{GUIDE_SITELINK}'")):
        if list(r.asset.final_urls) != [GUIDE_URL]:
            o = c.get_type("MutateOperation")
            u = o.asset_operation.update
            u.resource_name = GUIDE_SITELINK
            u.final_urls.append(GUIDE_URL)
            o.asset_operation.update_mask.paths.append("final_urls")
            ops.append(o)
            change(f'{names[WEDDING]} sitelink "{r.asset.sitelink_asset.link_text}"', "link",
                   "/" + list(r.asset.final_urls)[0].split("/")[-1], "/music-guides/wedding-choir-guide.html",
                   "It pointed at the ad's own landing page, so Google rarely shows it")

    if not ops:
        print("Nothing to change.")
        return
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operations\n")
    for res, field, cur, new, why in changes:
        print(f"{res}\n   {field}: {cur} → {new}\n   reason: {why}\n")
    req = c.get_type("MutateGoogleAdsRequest")
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
    for res, field, cur, new, why in reversed(changes):
        ads_log.append_row(f"| {now} | {res} | {field} | {cur} → {new} | {why} | `{SCRIPT}` |")
    print("Applied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
