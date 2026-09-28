#!/usr/bin/env python3
"""Format the Monday report's money section. Totals and invoice numbers only, no names."""

import datetime


def summary_lines(assessments, receipts, singer, today):
    week_start = (today - datetime.timedelta(days=7)).isoformat()
    week = [r for r in receipts if r[1] >= week_start]
    n = len(week)
    lines = [f"received from clients, last 7 days: £{sum(a for _, _, a in week):,.2f} ({n} payment{'' if n == 1 else 's'})"]
    overdue = [a["ref"] for a in assessments if a["state"] == "DEPOSIT_OVERDUE"]
    lines.append(f"deposits overdue: {len(overdue)}" + (f" ({', '.join(overdue)})" if overdue else ""))
    horizon = (today + datetime.timedelta(days=7)).isoformat()
    soon = [a for a in assessments if a["state"] in ("BALANCE_DUE", "DEPOSIT_SEEN") and a["balance"] > 0
            and a["event_date"] and a["event_date"] <= horizon]
    lines.append(f"balances due in the next 7 days: {len(soon)}, £{sum(a['balance'] for a in soon):,.2f}"
                 + (f" ({', '.join(a['ref'] for a in soon)})" if soon else ""))
    lines.append(f"singer invoices unpaid: {singer['unpaid']}, £{singer['unpaid_total']:,.2f}, oldest {singer['oldest_days']} days"
                 + (f" · BANK DETAILS CHANGED on {singer['bank_changed']}: ring before paying" if singer["bank_changed"] else ""))
    return lines
