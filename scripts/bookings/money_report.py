#!/usr/bin/env python3
"""Format the Monday report's money section. Totals and invoice numbers only, no names."""

import datetime

# Never in the balances line: settled, cancelled, uncertain or past bookings.
NOT_DUE = {"PAID_IN_FULL", "NOTED_PAID", "CANCELLED", "CHECK_PAYMENT", "CHECK_VALUE",
           "PAYMENT_ON_CANCELLED", "PAYMENT_AFTER_CLOSE"}
# NOTED_PAID stays here until the owner writes "paid in full YYYY-MM-DD" in the notes (the booking then closes).
HAND_CHECK = {"CHECK_PAYMENT": "possible payment", "CHECK_VALUE": "unreadable value or date",
              "PAST_UNMATCHED": "past, unpaid", "PAST_PART_PAID": "past, part paid",
              "NOTED_PAID": "noted paid, not in bank",
              "PAYMENT_ON_CANCELLED": "payment on a cancelled booking", "PAYMENT_AFTER_CLOSE": "payment after paid in full"}


def hand_check_label(a):
    received = a.get("received") or 0
    if a["state"] == "NOTED_PAID" and received:
        return f"noted paid, £{received:,.2f} in bank"
    if a["state"] == "CHECK_PAYMENT" and received:  # a deposit is in; the unconfirmed one may be the balance
        return "possible balance payment"
    return HAND_CHECK[a["state"]]
NO_DEPOSIT = {"DEPOSIT_OVERDUE", "AWAITING_DEPOSIT"}


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def summary_lines(assessments, receipts, singer, today):
    week_start = (today - datetime.timedelta(days=6)).isoformat()  # today and the six days before
    week = [r for r in receipts if r[1] >= week_start]
    lines = [f"received from clients, last 7 days: £{sum(a for _, _, a in week):,.2f} ({plural(len(week), 'payment')})"]
    overdue = [a["ref"] for a in assessments if a["state"] == "DEPOSIT_OVERDUE"]
    lines.append(f"deposits overdue: {len(overdue)}" + (f" ({', '.join(overdue)})" if overdue else ""))
    start, horizon = today.isoformat(), (today + datetime.timedelta(days=7)).isoformat()
    soon = [a for a in assessments if a.get("event_date") and start <= a["event_date"] <= horizon and a["balance"] > 0
            and a["state"] not in NOT_DUE and not a["state"].startswith("PAST_")]
    # An unpaid booking this week is listed here too (its whole fee is due); say so, so the total isn't read
    # as balances alone. The deposits line gives a count only, so no money is counted twice.
    bare = sum(a["state"] in NO_DEPOSIT for a in soon)
    lines.append(f"balances due in the next 7 days: {len(soon)}, £{sum(a['balance'] for a in soon):,.2f}"
                 + (f" ({', '.join(a['ref'] for a in soon)})" if soon else "")
                 + (f" (includes {bare} with no deposit)" if bare else ""))
    hand = [a for a in assessments if a["state"] in HAND_CHECK]
    lines.append(f"needs a hand check: {len(hand)}"
                 + (f" ({'; '.join(a['ref'] + ' ' + hand_check_label(a) for a in hand)})" if hand else ""))
    line = f"singer invoices unpaid: {singer['unpaid']}, £{singer['unpaid_total']:,.2f}"
    if singer["unpaid"]:
        line += f", oldest {plural(singer['oldest_days'], 'day')}"
    if singer["bank_changed"]:
        line += f" · BANK DETAILS CHANGED on {plural(singer['bank_changed'], 'invoice')}: ring before paying"
    lines.append(line)
    return lines
