#!/usr/bin/env python3
"""Dismiss Google's open recommendations that the Monday review of 26 October 2026 declined.

Google's DismissRecommendation call has no validate_only flag, so the default run is a dry run: it lists every
open recommendation of the declined types (campaign, type, resource) and changes nothing. --apply dismisses
exactly those, only after the owner approves the list; applied changes are appended to logs/ads-changes.md.
A dismissal changes no setting, bid, budget or ad; Google may raise the same recommendation again later.

    source .venv/bin/activate
    python scripts/ads/dismiss_recommendations_2026_10_26.py            # dry run
    python scripts/ads/dismiss_recommendations_2026_10_26.py --apply    # after approval
"""
import os
import argparse
import datetime
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/dismiss_recommendations_2026_10_26.py"

DECLINED = {
    "CAMPAIGN_BUDGET": "a higher budget breaks the owner's caps (£5/day; Christmas £8 to 13 Dec 2026)",
    "SEARCH_PARTNERS_OPT_IN": "owner rule: no search partners",
    "MAXIMIZE_CONVERSIONS_OPT_IN": "owner rule: manual CPC; too few conversions for smart bidding",
    "LEAD_FORM_ASSET": "a Google lead form skips the site form's hCaptcha and consent check",
    "DYNAMIC_IMAGE_EXTENSION_OPT_IN": "would let Google pick images from the site unchecked",
    "RESPONSIVE_SEARCH_AD": "stale: wedding-leads already has a second ad (829372414723, EXCELLENT) since 23 Oct",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    client = GoogleAdsClient.load_from_storage(os.environ.get("GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = client.get_service("GoogleAdsService")

    names = {str(r.campaign.id): r.campaign.name
             for r in ga.search(customer_id=CUSTOMER_ID, query="SELECT campaign.id, campaign.name FROM campaign")}
    found = []
    for r in ga.search(customer_id=CUSTOMER_ID, query=(
            "SELECT recommendation.resource_name, recommendation.type, recommendation.campaign, "
            "recommendation.dismissed FROM recommendation")):
        rec = r.recommendation
        kind = rec.type_.name
        if rec.dismissed or kind not in DECLINED:
            continue
        camp = rec.campaign.split("/")[-1] if rec.campaign else ""
        found.append((names.get(camp, "account") if camp else "account", kind, rec.resource_name))
    found.sort()

    if not found:
        print("Nothing to dismiss: no open recommendation of the declined types.")
        return
    print(("APPLYING" if args.apply else "DRY RUN (nothing is changed)") + f" — {len(found)} recommendations\n")
    for camp, kind, res in found:
        print(f"{camp}: {kind}\n   status: open → dismissed\n   reason: {DECLINED[kind]}\n   {res}\n")
    if not args.apply:
        print("Run with --apply after approval to dismiss exactly these.")
        return

    # One request per recommendation type: Google refuses a request mixing types (DIFFERENT_TYPES_NOT_SUPPORTED).
    svc = client.get_service("RecommendationService")
    done, failed = [], False
    for kind in sorted({k for _, k, _ in found}):
        batch = [f for f in found if f[1] == kind]
        req = client.get_type("DismissRecommendationRequest")
        req.customer_id = CUSTOMER_ID
        for _, _, res in batch:
            op = client.get_type("DismissRecommendationRequest").DismissRecommendationOperation()
            op.resource_name = res
            req.operations.append(op)
        try:
            svc.dismiss_recommendation(request=req)
            done.extend(batch)
        except GoogleAdsException as e:
            failed = True
            for err in e.failure.errors:
                print(f"REJECTED ({kind}):", err.error_code, err.message)
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    rows = "".join(f"| {now} | {'account' if c == 'account' else f'campaign \"{c}\"'} recommendation {k} | status | "
                   f"open → dismissed | {DECLINED[k]} | `{SCRIPT}` |\n" for c, k, _ in done)
    marker = "|---|---|---|---|---|---|\n"
    if done:
        LOG.write_text(LOG.read_text().replace(marker, marker + rows, 1))
    print(f"Dismissed {len(done)} of {len(found)} and logged them to logs/ads-changes.md")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
