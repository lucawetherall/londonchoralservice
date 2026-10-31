#!/usr/bin/env python3
"""Have Google validate one budget or pause proposal from the Monday review. Validate-only, always.

The unattended Monday run quotes what this prints, so the owner approves exactly what Google accepted
(owner decision D2, 31 Oct 2026). It has no --apply flag: argparse refuses one as an unknown argument, and the
code below calls set_budget.change() and set_campaign_status.change() with apply=False and nothing else, so it
can never change the account. Applying an approved change is still set_budget.py / set_campaign_status.py
--apply, in a live chat, after the owner's approval.

    .venv/bin/python scripts/ads/validate_proposal.py budget <campaign id> <£ daily> --reason "<reason>"
    .venv/bin/python scripts/ads/validate_proposal.py status <campaign id> paused --reason "<reason>"

budget: set_budget.py's own checks, the cap from budget_cap.py first (a budget above the campaign's cap is
refused before anything talks to Google), then Google's validate_only. status: only "paused"; enabling a
campaign is never a Monday proposal this script validates. Each prints the same "current → new" lines as the
script it reuses. Exit 0 when Google accepted it (or there is nothing to change), non-zero otherwise.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import set_budget  # noqa: E402
import set_campaign_status  # noqa: E402


def parse(argv=None):
    p = argparse.ArgumentParser(description="Validate one budget or pause proposal (never applies it).")
    sub = p.add_subparsers(dest="kind", required=True)
    b = sub.add_parser("budget", help="a new daily budget for one campaign")
    b.add_argument("campaign", help="the campaign's numeric id")
    b.add_argument("daily", help="the proposed daily budget in pounds, e.g. 4.50")
    b.add_argument("--reason", required=True)
    s = sub.add_parser("status", help="pause one campaign")
    s.add_argument("campaign", help="the campaign's numeric id")
    s.add_argument("status", choices=["paused"])
    s.add_argument("--reason", required=True)
    args = p.parse_args(argv)
    if not args.campaign.isdigit():
        p.error("the campaign must be its numeric id")
    if not set_budget.reason_ok(args.reason):
        p.error("the reason must be one line of at most 300 characters, without '|'")
    return args


def main(argv=None, client=None, now=None):
    args = parse(argv)
    if args.kind == "budget":
        return set_budget.change(args.campaign, args.daily, args.reason, apply=False, client=client, now=now) or 0
    set_campaign_status.change(int(args.campaign), "paused", args.reason, apply=False, client=client)
    return 0


if __name__ == "__main__":
    sys.exit(main())
