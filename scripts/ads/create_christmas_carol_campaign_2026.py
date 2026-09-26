#!/usr/bin/env python3
"""Create the "Christmas carol singers – events 2026" Search campaign, PAUSED.

One atomic GoogleAdsService.mutate: budget, campaign, targeting, negatives,
four tightly themed ad groups (exact + phrase keywords only), one RSA per
ad group, and callout / structured snippet / sitelink / price assets.

Default run is validate_only. --apply only after approval; applied changes
are appended to logs/ads-changes.md. The campaign is created PAUSED and is
enabled separately, once christmas-pricing.html is live.

    source .venv/bin/activate
    python scripts/ads/create_christmas_carol_campaign_2026.py            # validate
    python scripts/ads/create_christmas_carol_campaign_2026.py --apply    # after approval
"""

import argparse
import datetime
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/create_christmas_carol_campaign_2026.py"

MAX_DAILY_BUDGET_MICROS = 5_000_000  # CLAUDE.md hard cap: £5/day
DAILY_BUDGET_MICROS = 5_000_000
CPC_CEILING_MICROS = 3_500_000       # Maximise clicks, never more than £3.50 a click
CAMPAIGN_NAME = "Christmas carol singers – events 2026"
END = "2026-12-20 23:59:59"          # last useful search date for December events
LANDING = "https://londonchoralservice.com/christmas-pricing.html"
SITE = "https://londonchoralservice.com/"
SUFFIX = "utm_source=google&utm_medium=cpc&utm_campaign=christmas-carol-singers-2026"
GREATER_LONDON = "geoTargetConstants/9041106"
ENGLISH = "languageConstants/1000"

NEGATIVES = [
    # jobs and taking part
    "job", "jobs", "vacancy", "vacancies", "audition", "auditions", "volunteer", "volunteering",
    "join", "wanted", "become", "rehearsal", "course", "lessons",
    # listening, lyrics, media
    "lyrics", "words", "sheet music", "chords", "karaoke", "youtube", "video", "mp3", "download",
    "spotify", "playlist", "songs", "song",
    # attending, not hiring
    "tickets", "near me tonight", "what's on", "concert tickets",
    # Dickens and the stage
    "dickens", "scrooge", "film", "movie", "musical", "theatre", "book", "novel",
    # objects that are also called "carol singers"
    "ornament", "ornaments", "figurine", "figurines", "decoration", "decorations", "costume",
    "costumes", "fancy dress", "card", "cards", "print", "painting", "clipart", "drawing",
    # not the buyer
    "free", "cheap", "school", "kids", "children", "nativity",
]
NEGATIVES = [n for n in NEGATIVES if n != "book"]  # "book carol singers" is a buying search

BASE_DESCRIPTIONS = [
    "Four professional carol singers for up to two hours, breaks included. £1,150, all in.",
    "Office parties, hotel lobbies and receptions across London. Quote within one working day.",
    "December costs the same as June. London travel, sheet music and rehearsals included.",
    "Carols planned with our Artistic Director, a University of Oxford music tutor.",
]
BASE_HEADLINES = [
    "4 Carol Singers from £1,150", "Two Hours of Carols Included", "Same Price in December",
    "No VAT, No Hidden Fees", "Hand-Picked Carol Singers", "4 to 12 Voices Available",
    "Quote in 1 Working Day", "London Travel Included", "Unaccompanied 4-Part Carols",
    "Book Your December Date", "The London Choral Service", "Professional Carol Singers",
]

AD_GROUPS = [
    {
        "name": "Hire carol singers",
        "pinned": ["Hire Carol Singers in London", "Carol Singers for Hire"],
        "extra": ["Carol Singers for Events"],
        "keywords": ["hire carol singers", "carol singers for hire", "carol singers hire", "book carol singers",
                     "professional carol singers", "carol singers london", "hire carol singers london",
                     "christmas carol singers for hire", "christmas carol singers london"],
    },
    {
        "name": "Carol singers for events",
        "pinned": ["Carol Singers for Events", "Office Party Carol Singers"],
        "extra": ["Corporate Carol Singers"],
        "keywords": ["carol singers for events", "carol singers for corporate events", "corporate carol singers",
                     "carol singers for office party", "carol singers for christmas party",
                     "christmas party carol singers", "carol singers for a party", "carol singers for company"],
    },
    {
        "name": "Venue and lobby carols",
        "pinned": ["Carol Singers for Hotels", "Lobby Carol Singers"],
        "extra": ["Carol Singers for Residents"],
        "keywords": ["carol singers for hotels", "hotel carol singers", "lobby carol singers",
                     "carol singers for residents", "carol singers for reception",
                     "carol singers for christmas reception"],
    },
    {
        "name": "Carol singer prices",
        "pinned": ["Carol Singer Prices", "Carol Singers: £1,150 All In"],
        "extra": ["See Our Christmas Prices"],
        "keywords": ["carol singers cost", "carol singers price", "carol singers prices",
                     "how much are carol singers", "how much do carol singers cost", "cost of carol singers",
                     "carol singers rates"],
    },
]

CALLOUTS = ["No VAT Added", "Two Hours Included", "London Travel Included", "Same Price in December",
            "Hand-Picked Singers"]
SNIPPET = ("Types", ["Office Parties", "Hotel Lobbies", "Carol Services", "Receptions", "Gala Dinners"])
SITELINKS = [
    ("Christmas Prices", "Every ensemble, two hours", "Breaks included, all in", LANDING),
    ("Hire Carol Singers", "Parties, lobbies, receptions", "Four to twelve voices", SITE + "carol-singers.html"),
    ("Carol Services", "Offices, halls and churches", "With an organist if needed", SITE + "christmas.html"),
    ("Hotels and Venues", "Lobby carols and switch-ons", "Sets across an evening", SITE + "for-hotels.html"),
]
PRICES = [  # (header ≤25, description ≤25, price £)
    ("Small Choir (4)", "Two hours, breaks incl.", 1150),
    ("Quintet (5)", "Two hours, breaks incl.", 1400),
    ("Sextet (6)", "Two hours, breaks incl.", 1600),
    ("Full Choir (8)", "Or a carol service", 2000),
    ("Chorus (12)", "Or a carol service", 3000),
]


def check_limits():
    assert DAILY_BUDGET_MICROS <= MAX_DAILY_BUDGET_MICROS, "Refusing: daily budget above the £5 cap"
    for g in AD_GROUPS:
        heads = g["pinned"] + g["extra"] + [h for h in BASE_HEADLINES if h not in g["pinned"] + g["extra"]]
        g["headlines"] = heads[:15]
        assert len(g["headlines"]) == 15 and len(set(g["headlines"])) == 15, g["name"]
        for h in g["headlines"]:
            assert len(h) <= 30, f"headline too long ({len(h)}): {h}"
    for d in BASE_DESCRIPTIONS:
        assert len(d) <= 90, f"description too long ({len(d)}): {d}"
    for c in CALLOUTS + SNIPPET[1]:
        assert len(c) <= 25, c
    for t, d1, d2, _ in SITELINKS:
        assert len(t) <= 25 and len(d1) <= 35 and len(d2) <= 35, t
    for h, d, _ in PRICES:
        assert len(h) <= 25 and len(d) <= 25, h


def build(client):
    ga = client.get_service("GoogleAdsService")
    E = client.enums
    ops, temp = [], iter(range(-1, -1000, -1))

    def op(kind):
        o = client.get_type("MutateOperation")
        ops.append(o)
        return getattr(o, kind).create

    budget_rn = ga.campaign_budget_path(CUSTOMER_ID, next(temp))
    b = op("campaign_budget_operation")
    b.resource_name = budget_rn
    b.name = CAMPAIGN_NAME + " budget"
    b.amount_micros = DAILY_BUDGET_MICROS
    b.delivery_method = E.BudgetDeliveryMethodEnum.STANDARD
    b.explicitly_shared = False

    camp_rn = ga.campaign_path(CUSTOMER_ID, next(temp))
    c = op("campaign_operation")
    c.resource_name = camp_rn
    c.name = CAMPAIGN_NAME
    c.status = E.CampaignStatusEnum.PAUSED
    c.advertising_channel_type = E.AdvertisingChannelTypeEnum.SEARCH
    c.campaign_budget = budget_rn
    c.target_spend.cpc_bid_ceiling_micros = CPC_CEILING_MICROS
    c.network_settings.target_google_search = True
    c.network_settings.target_search_network = False
    c.network_settings.target_content_network = False
    c.network_settings.target_partner_search_network = False
    c.geo_target_type_setting.positive_geo_target_type = E.PositiveGeoTargetTypeEnum.PRESENCE
    c.end_date_time = END
    c.final_url_suffix = SUFFIX
    c.contains_eu_political_advertising = E.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING

    cc = op("campaign_criterion_operation"); cc.campaign = camp_rn; cc.location.geo_target_constant = GREATER_LONDON
    cc = op("campaign_criterion_operation"); cc.campaign = camp_rn; cc.language.language_constant = ENGLISH
    for n in NEGATIVES:
        cc = op("campaign_criterion_operation")
        cc.campaign = camp_rn
        cc.negative = True
        cc.keyword.text = n
        cc.keyword.match_type = E.KeywordMatchTypeEnum.BROAD  # negative broad = block any query containing it

    for g in AD_GROUPS:
        ag_rn = ga.ad_group_path(CUSTOMER_ID, next(temp))
        ag = op("ad_group_operation")
        ag.resource_name = ag_rn
        ag.name = g["name"]
        ag.campaign = camp_rn
        ag.status = E.AdGroupStatusEnum.ENABLED
        ag.type_ = E.AdGroupTypeEnum.SEARCH_STANDARD
        for kw in g["keywords"]:
            for mt in (E.KeywordMatchTypeEnum.EXACT, E.KeywordMatchTypeEnum.PHRASE):
                k = op("ad_group_criterion_operation")
                k.ad_group = ag_rn
                k.status = E.AdGroupCriterionStatusEnum.ENABLED
                k.keyword.text = kw
                k.keyword.match_type = mt
        ad = op("ad_group_ad_operation")
        ad.ad_group = ag_rn
        ad.status = E.AdGroupAdStatusEnum.ENABLED
        ad.ad.final_urls.append(LANDING)
        rsa = ad.ad.responsive_search_ad
        rsa.path1 = "Christmas"
        rsa.path2 = "Prices"
        for i, h in enumerate(g["headlines"]):
            a = client.get_type("AdTextAsset")
            a.text = h
            if i < len(g["pinned"]):
                a.pinned_field = E.ServedAssetFieldTypeEnum.HEADLINE_1
            rsa.headlines.append(a)
        for d in BASE_DESCRIPTIONS:
            a = client.get_type("AdTextAsset")
            a.text = d
            rsa.descriptions.append(a)

    def link(asset_rn, field):
        ca = op("campaign_asset_operation")
        ca.campaign = camp_rn
        ca.asset = asset_rn
        ca.field_type = field

    for text in CALLOUTS:
        rn = ga.asset_path(CUSTOMER_ID, next(temp))
        a = op("asset_operation"); a.resource_name = rn; a.callout_asset.callout_text = text
        link(rn, E.AssetFieldTypeEnum.CALLOUT)

    rn = ga.asset_path(CUSTOMER_ID, next(temp))
    a = op("asset_operation"); a.resource_name = rn
    a.structured_snippet_asset.header = SNIPPET[0]
    a.structured_snippet_asset.values.extend(SNIPPET[1])
    link(rn, E.AssetFieldTypeEnum.STRUCTURED_SNIPPET)

    for text, d1, d2, url in SITELINKS:
        rn = ga.asset_path(CUSTOMER_ID, next(temp))
        a = op("asset_operation"); a.resource_name = rn
        a.final_urls.append(url)
        a.sitelink_asset.link_text = text
        a.sitelink_asset.description1 = d1
        a.sitelink_asset.description2 = d2
        link(rn, E.AssetFieldTypeEnum.SITELINK)

    rn = ga.asset_path(CUSTOMER_ID, next(temp))
    a = op("asset_operation"); a.resource_name = rn
    pa = a.price_asset
    pa.type_ = E.PriceExtensionTypeEnum.SERVICES
    pa.language_code = "en"
    for h, d, price in PRICES:
        o = client.get_type("PriceOffering")
        o.header = h
        o.description = d
        o.price.amount_micros = price * 1_000_000
        o.price.currency_code = "GBP"
        o.unit = E.PriceExtensionPriceUnitEnum.UNSPECIFIED
        o.final_url = LANDING
        pa.price_offerings.append(o)
    link(rn, E.AssetFieldTypeEnum.PRICE)
    return ops


def summary():
    kws = sum(len(g["keywords"]) for g in AD_GROUPS)
    print(f'Campaign "{CAMPAIGN_NAME}" (Search only, PAUSED, ends {END[:10]})')
    print(f"  budget: £{DAILY_BUDGET_MICROS/1e6:.2f}/day · bidding: maximise clicks, max CPC £{CPC_CEILING_MICROS/1e6:.2f}")
    print(f"  targeting: Greater London, people located there (presence), English, Google Search only")
    print(f"  tracking suffix: {SUFFIX}")
    print(f"  landing page: {LANDING}")
    print(f"  {len(AD_GROUPS)} ad groups · {kws} keywords × exact + phrase = {kws*2} · no broad match")
    print(f"  {len(NEGATIVES)} negative keywords · 1 RSA per ad group · {len(CALLOUTS)} callouts, 1 snippet, "
          f"{len(SITELINKS)} sitelinks, 1 price asset ({len(PRICES)} prices)")
    for g in AD_GROUPS:
        print(f'\n  ad group "{g["name"]}": {", ".join(g["keywords"])}')
        print(f'    headline 1 (pinned, rotates): {" | ".join(g["pinned"])}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    check_limits()
    client = GoogleAdsClient.load_from_storage()
    ops = build(client)
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operations\n")
    summary()
    req = client.get_type("MutateGoogleAdsRequest")
    req.customer_id = CUSTOMER_ID
    req.mutate_operations.extend(ops)
    req.validate_only = not args.apply
    try:
        resp = client.get_service("GoogleAdsService").mutate(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            loc = ".".join(f"{p.field_name}[{p.index}]" if p.index else p.field_name for p in err.location.field_path_elements)
            print("REJECTED:", err.error_code, err.message, "@", loc)
        raise SystemExit(1)
    if not args.apply:
        print("\nGoogle accepted every operation. Nothing was created.")
        return
    camp = next(r.campaign_result.resource_name for r in resp.mutate_operation_responses if r.campaign_result.resource_name)
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    row = (f"| {now} | campaign \"{CAMPAIGN_NAME}\" ({camp.rsplit('/', 1)[1]}) | (new) | does not exist → created PAUSED: "
           f"Search, £{DAILY_BUDGET_MICROS/1e6:.2f}/day, max CPC £{CPC_CEILING_MICROS/1e6:.2f}, Greater London, "
           f"{len(AD_GROUPS)} ad groups, exact+phrase only, ends {END[:10]} | Hyper-targeted Christmas carol singers "
           f"for events, landing on christmas-pricing.html | `{SCRIPT}` |\n")
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print("\nCreated:", camp, "(PAUSED). Logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
