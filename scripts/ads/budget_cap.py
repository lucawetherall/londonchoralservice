"""The daily budget cap, one place for every script that sets or proposes a budget.

£5/day for every campaign (CLAUDE.md), except where the owner has raised it for one campaign over set dates.
An exception names the campaign by id, never by name, so a renamed or new campaign can't inherit it.

    from budget_cap import cap_micros, cap_gbp
    cap_micros("24295921372", datetime.date(2026, 10, 1))   # 8_000_000
    cap_micros("111")                                        # 5_000_000

Stop rule for the Christmas exception (owner, 28 Sep 2026), checked by the Monday review: back to £5 if spend
above the £5/day level passes £60 by 2 Nov 2026 with no real enquiry, or if less than 90% of a week's spend
went on hiring searches.
"""

import datetime

BASE_CAP_MICROS = 5_000_000

# campaign id -> (cap in micros, first day, last day, why)
EXCEPTIONS = {
    "24295921372": (8_000_000, datetime.date(2026, 9, 28), datetime.date(2026, 12, 13),
                    "Christmas carol campaign: owner raised the cap to £8/day, 28 Sep to 13 Dec 2026"),
}


def cap_micros(campaign_id=None, day=None):
    day = day or datetime.date.today()
    exc = EXCEPTIONS.get(str(campaign_id or ""))
    if exc and exc[1] <= day <= exc[2]:
        return exc[0]
    return BASE_CAP_MICROS


def cap_gbp(campaign_id=None, day=None):
    return cap_micros(campaign_id, day) / 1_000_000


def max_cap_gbp():
    """The highest cap any exception allows, for checks that don't know the campaign yet."""
    return max([BASE_CAP_MICROS] + [e[0] for e in EXCEPTIONS.values()]) / 1_000_000
