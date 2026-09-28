"""Pure builders for the phase-2 pages: plain data in, plain data out, no file or network access.

The rules stay in the scripts: payment states come from check_payments (collect, assess, deposit_due_date,
is_cancelled, closed_on), the pipeline's from pipeline (followups_due, reviews_due, summary_dict, STATUS_ORDER),
the singers' from singer_invoices (normalise_name, first_name, payee_status, is_open, ring_first, is_trusted,
bill_number). What is here only arranges their answers for a page.

Privacy, as on the phase-1 pages: client and singer first names only, emails never, bank accounts as
••••last4 only, and any run of six or more digits in free text is masked to its last four.
"""

import datetime
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "reports"))
import dashboard as dash  # noqa: E402

cp, lm, pl, si = dash.cp, dash.lm, dash.pl, dash.si

BALANCE_DAYS = 3  # check_payments' BALANCE_DUE: the balance falls due three days before the event
DEPOSIT_STATES = {"AWAITING_DEPOSIT", "DEPOSIT_OVERDUE"}
NO_BALANCE = {"PAID_IN_FULL", "CLOSED", "CANCELLED", "PAYMENT_ON_CANCELLED", "PAYMENT_AFTER_CLOSE", "CHECK_VALUE"}
REF_RE = re.compile(r"^[A-Za-z0-9-]{1,20}$")
ISO_DAY = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
LONG_DIGITS = re.compile(r"\d(?:[ -]?\d){5,}")
SEARCH_MIN, SEARCH_MAX, SEARCH_LIMIT = 2, 80, 50
FOLLOWUP_GAP = {0: pl.FIRST_AFTER, 1: pl.SECOND_AFTER, 2: pl.LOST_AFTER}


# ---------------------------------------------------------------- small helpers


def to_date(value):
    return pl.to_date(value) if value else None


def first_name(name):
    return dash.first_name(name)


def mask_digits(text):
    """Any run of six or more digits (spaces or dashes allowed between them) -> ••••last4."""
    return LONG_DIGITS.sub(lambda m: "••••" + re.sub(r"\D", "", m.group())[-4:], str(text or ""))


def mask_note(text, full_name=""):
    """A ledger note clause for the page: emails dropped, the client's other name words masked, long digit
    runs masked. The first name stays, as everywhere else."""
    out = EMAIL.sub("[email]", str(text or ""))
    words = [w for w in re.findall(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", full_name or "") if len(w) > 1]
    for w in words[1:]:
        if words and w.casefold() == words[0].casefold():
            continue
        out = re.sub(rf"(?<!\w){re.escape(w)}(?!\w)", "…", out, flags=re.I)
    return mask_digits(out)


def item(day, kind, text, href=None, tone=""):
    """One timeline or calendar entry. `day` is a date or None (undated)."""
    return {"date": day, "kind": kind, "text": text, "href": href, "tone": tone}


def sort_items(items):
    return sorted(items, key=lambda i: (i["date"] is None, i["date"] or datetime.date.min))


# ---------------------------------------------------------------- bookings


def booking_rows(ledger, assessments, bank_checked, today):
    """One dict per ledger row with its payment state: the bank cache's assessment when it has one (open rows,
    and cancelled or closed rows with a payment to check), else CANCELLED, CLOSED, or the notes-only
    check_payments.assess state, as dashboard.upcoming decides."""
    by_ref = {a["ref"]: a for a in assessments}
    out = []
    for r in ledger:
        ref = (r.get("booking_ref") or "").strip()
        a = by_ref.get(ref)
        if a is None:
            if cp.is_cancelled(r):
                state = "CANCELLED"
            elif cp.closed_on(r):
                state = "CLOSED"
            else:
                a = cp.assess(r, [], today)
        state = a["state"] if a else state
        event = to_date(r.get("event_date"))
        value = cp.money(r)
        out.append({
            "ref": ref, "event_date": event, "invoice_date": to_date(r.get("invoice_date")),
            "first_name": first_name(r.get("client_name")), "occasion": r.get("occasion", ""),
            "ensemble": r.get("ensemble", ""), "value": value, "state": state,
            "received": (a or {}).get("received", value if state == "CLOSED" else 0.0) or 0.0,
            "balance": (a or {}).get("balance", 0.0 if state in ("CLOSED", "CANCELLED") else value),
            "deposit_due": to_date((a or {}).get("deposit_due")), "assessment": a,
            "bank_checked": bool(bank_checked and ref in by_ref),
            "upcoming": event is None or event >= today, "cancelled": state in ("CANCELLED", "PAYMENT_ON_CANCELLED"),
        })
    return sorted(out, key=lambda b: (b["event_date"] or datetime.date.max, b["ref"]))


WHEN = ("upcoming", "past", "all")


def filter_bookings(rows, when, state):
    when = when if when in WHEN else "upcoming"
    if when == "upcoming":
        rows = [b for b in rows if b["upcoming"]]
        rows = [b for b in rows if not b["cancelled"]] if not state else rows
    elif when == "past":
        rows = sorted([b for b in rows if not b["upcoming"]], key=lambda b: b["event_date"], reverse=True)
    if state:
        rows = [b for b in rows if b["state"] == state]
    return rows


def ledger_timeline(row, booking, today):
    """The ledger's part of a booking's timeline: invoice, deposit due, payments, notes, event."""
    a = booking["assessment"] or {}
    out = []
    if booking["invoice_date"]:
        out.append(item(booking["invoice_date"], "invoice", f"Invoice {booking['ref']} issued, £{booking['value']:,.2f}"))
    if booking["deposit_due"]:
        tone = "bad" if booking["state"] == "DEPOSIT_OVERDUE" else ""
        out.append(item(booking["deposit_due"], "money", "Deposit due", tone=tone))
    if a.get("first"):
        out.append(item(to_date(a["first"]), "money", f"First payment seen in Starling (matched by {a.get('how') or '?'}); "
                        f"£{a.get('received', 0):,.2f} received in all", tone="ok"))
    for key, words in (("unconfirmed", "Possible payment, unconfirmed"),
                       ("hand_check_payments", "Payment to check by hand")):
        for d, amount in a.get(key) or []:
            out.append(item(to_date(d), "money", f"{words}: £{amount:,.2f}", tone="warn"))
    for clause in [c.strip() for c in (row.get("notes") or "").split(";") if c.strip()]:
        m = ISO_DAY.search(clause)
        kind = "review" if cp.REVIEW_NOTE.search(clause) else "note"
        out.append(item(to_date(m.group(1)) if m else None, kind, mask_note(clause, row.get("client_name"))))
    if booking["event_date"]:
        out.append(item(booking["event_date"], "event", f"Event: {booking['occasion'] or 'booking'}"
                        + (f", {booking['ensemble']}" if booking["ensemble"] else "")))
    if booking["ref"] in {x["booking_ref"] for x in pl.reviews_due([row], today)}:
        out.append(item(today, "review", "Review request due", tone="warn"))
    return out


def enquiry_items(r, cache, today, prefix=""):
    """An enquiry's timeline items (pipeline row): first seen, quotes, follow-ups, next follow-up, event."""
    eid = r.get("enquiry_id", "")
    href = f"/enquiries/{eid}"
    out = [item(to_date(r.get("first_seen")), "enquiry",
                f"{prefix}Enquiry {eid} by {r.get('source') or 'unknown source'}"
                + (f", {r.get('occasion')}" if r.get("occasion") else ""), href)]
    quotes = sorted({d for d in (to_date(x) for x in pl.QUOTED_NOTE.findall(r.get("notes") or "")) if d})
    for i, d in enumerate(quotes):
        last = i == len(quotes) - 1
        what = (f" {r.get('package')}" if last and r.get("package") else "")
        amount = lm.parse_gbp(r.get("quoted_gbp")) if last else None
        out.append(item(d, "quote", f"Quoted{what}" + (f", £{amount:,.2f}" if amount else "")))
    n = pl.followups_of(r) or 0
    if n:
        out.append(item(to_date(r.get("last_contact")), "followup",
                        f"Follow-up {n} sent" + (" (the latest)" if n > 1 else "")))
    elif to_date(r.get("last_contact")) not in (set(quotes) | {to_date(r.get("first_seen")), None}):
        out.append(item(to_date(r.get("last_contact")), "enquiry", "Client replied"))
    nxt = next_followup(r, today)
    if nxt:
        words = "Mark lost" if nxt[1] == "mark_lost" else f"Next follow-up ({nxt[1]})"
        out.append(item(nxt[0], "followup", f"{words} due", tone="warn" if nxt[0] <= today else ""))
    return out


def enquiry_timeline(r, cache, today):
    out = enquiry_items(r, cache, today)
    event = to_date(r.get("event_date"))
    if event:
        out.append(item(event, "event", "Event date"))
    return sort_items(out)


def booking_enquiries(ref, enquiries, cache, today):
    return [x for r in enquiries if (r.get("booking_ref") or "").strip() == ref
            for x in enquiry_items(r, cache, today)]


def booking_singers(event_date, singer_rows):
    """Singer invoices linked to a booking by the store's event_date field, when the store has one."""
    if not event_date:
        return []
    out = []
    for r in singer_rows:
        if to_date(r.get("event_date")) == event_date and not si.is_withdrawn(r):
            paid = f", paid {r['paid_on']}" if r.get("paid_on") else ", unpaid"
            out.append(item(si.received_date(r), "singer",
                            f"Singer invoice from {si.first_name(r.get('singer_name'))}: "
                            f"£{lm.money(r.get('amount_gbp')):,.2f}{paid}"))
    return out


def campaign_for(r, cache):
    gclid = (r.get("gclid") or "").strip()
    if not gclid or "@" in gclid or not isinstance(cache, dict):
        return None
    value = cache.get(gclid)
    return value if isinstance(value, str) and value else None


# ---------------------------------------------------------------- enquiries


def next_followup(r, today):
    """(date, kind) of the next follow-up or mark-lost for a pipeline row, or None. The rules are
    pipeline.followups_due's: this only asks it about the day each rule could fire."""
    if pl.status_of(r) != "quoted" or (r.get("booking_ref") or "").strip():
        return None
    n = pl.followups_of(r)
    last = to_date(r.get("last_contact")) or to_date(r.get("first_seen"))
    event = to_date(r.get("event_date"))
    days = []
    if n is not None and last is not None:
        days.append(max(last + datetime.timedelta(days=FOLLOWUP_GAP[n]), today))
    if event:
        days.append(max(event, today))
    for day in sorted(set(days)):
        due = pl.followups_due([r], day)
        if due:
            return day, due[0]["kind"]
    return None


def enquiry_board(rows):
    columns = {s: [] for s in pl.STATUS_ORDER}
    for r in rows:
        columns.setdefault(pl.status_of(r) or "blank", []).append(r)
    for cards in columns.values():
        cards.sort(key=lambda r: r.get("first_seen") or "", reverse=True)
    return [(status, cards) for status, cards in columns.items()]


def rate(value):
    return None if value is None else f"{value * 100:.0f}%"


# ---------------------------------------------------------------- singers


def _warnings(r):
    return [mask_digits(n) for n in (r.get("notes") or "").split("; ") if n and not n.startswith(si.KEEP_NOTES)]


def singer_directory(rows, today):
    """One entry per singer (singer_invoices.normalise_name), warnings first, then by name."""
    groups = {}
    for r in rows:
        key = si.normalise_name(r.get("singer_name")) or (r.get("singer_email") or "").strip().lower() or "?"
        groups.setdefault(key, []).append(r)
    out = []
    for key, group in groups.items():
        group = sorted(group, key=lambda r: r.get("received") or "", reverse=True)
        live = [r for r in group if not si.is_withdrawn(r)]
        latest = live[0] if live else group[0]
        paid = [r for r in live if r.get("paid_on")]
        warnings = []
        if any(si.ring_first(r) for r in live if si.is_open(r)):
            warnings.append("Bank details changed: ring on a number you already have before paying")
        for r in live:
            if si.is_open(r):
                warnings += [w for w in _warnings(r) if w not in warnings]
        if not latest.get("bank_fp"):
            check = "no bank details on file"
        elif latest.get("bank_confirmed") == "yes":
            check = "confirmed by phone"
        elif latest.get("paid_verified") == "yes":
            check = "paid to verifiably"
        else:
            check = "not yet verified"
        invoices = [{"received": si.received_date(r), "bill_number": si.bill_number(r.get("invoice_ref"), r.get("message_id")),
                     "amount": lm.money(r.get("amount_gbp")), "paid_on": to_date(r.get("paid_on")),
                     "paid_amount": lm.parse_gbp(r.get("paid_amount")), "open": si.is_open(r),
                     "ring_first": si.ring_first(r), "last4": dash.digits4(r.get("bank_last4"))} for r in live]
        withdrawn = [{"received": si.received_date(r), "bill_number": si.bill_number(r.get("invoice_ref"), r.get("message_id")),
                      "amount": lm.money(r.get("amount_gbp")), "on": to_date(r.get("withdrawn"))}
                     for r in group if si.is_withdrawn(r)]
        out.append({
            "key": key, "first_name": si.first_name(latest.get("singer_name")), "invoices": invoices,
            "withdrawn": withdrawn, "count": len(live),
            "total_paid": round(sum(lm.parse_gbp(r.get("paid_amount")) or lm.money(r.get("amount_gbp")) for r in paid), 2),
            "unpaid_total": round(sum(lm.money(r.get("amount_gbp")) for r in live if si.is_open(r)), 2),
            "unpaid": sum(1 for r in live if si.is_open(r)),
            "last_invoice": si.received_date(latest), "payee": si.payee_status(latest.get("payee")) or "new payee",
            "last4": dash.digits4(latest.get("bank_last4")), "bank_check": check, "warnings": warnings,
        })
    return sorted(out, key=lambda g: (not g["warnings"], g["first_name"].lower(), g["key"]))


# ---------------------------------------------------------------- marketing


def _num(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def season_table(summary):
    """The season per campaign from ads-summary.json (economics.cost_table's shape), numbers checked."""
    season = summary.get("season") or {}
    keys = ("spend_gbp", "clicks", "enquiries", "bookings", "booked_gbp", "cost_per_enquiry", "cost_per_booking")

    def clean(r):
        return {"campaign": str(r.get("campaign") or "?")[:80], **{k: _num(r.get(k)) for k in keys}}
    return {"start": to_date(season.get("start")), "campaigns": [clean(r) for r in season.get("campaigns") or []],
            "unattributed": {k: _num((season.get("unattributed") or {}).get(k)) for k in ("enquiries", "bookings", "booked_gbp")},
            "total": clean(dict(season.get("total") or {}, campaign="Total"))}


def weekly_chart(weeks, width=480, height=210):
    """Geometry for an inline SVG: bars of weekly spend and a line of clicks, oldest week first."""
    pts = []
    for w in weeks or []:
        day = to_date(str(w.get("week_start") or "")[:10])
        spend, clicks = _num(w.get("spend_gbp")), _num(w.get("clicks"))
        if day and spend is not None:
            pts.append((day, spend, clicks or 0))
    pts.sort()
    if not pts:
        return None
    left, right, top, bottom = 62, 12, 14, 30
    plot_w, plot_h = width - left - right, height - top - bottom
    top_spend = max(p[1] for p in pts) or 1.0
    top_clicks = max(p[2] for p in pts) or 1.0
    slot = plot_w / len(pts)
    bars, line = [], []
    for i, (day, spend, clicks) in enumerate(pts):
        h = plot_h * spend / top_spend
        x = left + i * slot
        bars.append({"x": round(x + slot * 0.15, 1), "y": round(top + plot_h - h, 1), "w": round(slot * 0.7, 1),
                     "h": round(h, 1), "label": f"{day.day} {day:%b}", "lx": round(x + slot / 2, 1),
                     "title": f"week of {day.day} {day:%b}: £{spend:,.2f}, {int(clicks)} clicks"})
        line.append(f"{round(x + slot / 2, 1)},{round(top + plot_h - plot_h * clicks / top_clicks, 1)}")
    return {"width": width, "height": height, "bars": bars, "line": " ".join(line), "top": top,
            "base": top + plot_h, "left": left, "right": width - right, "max_spend": top_spend,
            "max_clicks": int(top_clicks), "label_y": height - 10}


def gclid_counts(cache):
    """{campaign: click ids traced to it} from gclid-campaigns.json; misses (gclid@date/days) are skipped."""
    counts = {}
    for k, v in (cache or {}).items() if isinstance(cache, dict) else []:
        if "@" in str(k) or not isinstance(v, str) or not v:
            continue
        counts[v[:80]] = counts.get(v[:80], 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))


# ---------------------------------------------------------------- calendar


def booking_dates(bookings):
    out = []
    for b in bookings:
        if b["cancelled"]:
            continue
        href = f"/bookings/{b['ref']}"
        who = f"{b['ref']} {b['first_name']}"
        if b["event_date"]:
            out.append(item(b["event_date"], "event", f"{who}, {b['occasion'] or 'booking'}", href))
        if b["deposit_due"] and b["state"] in DEPOSIT_STATES:
            out.append(item(b["deposit_due"], "deposit", f"Deposit due {who}", href,
                            "bad" if b["state"] == "DEPOSIT_OVERDUE" else "warn"))
        if b["event_date"] and b["state"] not in NO_BALANCE and (b["balance"] or 0) > 0:
            out.append(item(b["event_date"] - datetime.timedelta(days=BALANCE_DAYS), "balance",
                            f"Balance due {who}, £{b['balance']:,.2f}", href, "warn"))
    return out


def enquiry_dates(enquiries, today):
    out = []
    for r in enquiries:
        eid = r.get("enquiry_id", "")
        href = f"/enquiries/{eid}"
        nxt = next_followup(r, today)
        if nxt:
            words = "Mark lost" if nxt[1] == "mark_lost" else f"Follow-up ({nxt[1]})"
            out.append(item(nxt[0], "followup", f"{words} {eid}", href, "warn"))
        event = to_date(r.get("event_date"))
        if event and pl.status_of(r) in ("new", "quoted") and not (r.get("booking_ref") or "").strip():
            out.append(item(event, "enquiry", f"Enquiry {eid}: {r.get('occasion') or 'event'} (not booked)", href))
    return out


def _when(value):
    """An ISO date (all-day) or an aware ISO datetime -> (London date, "HH:MM" or None), else None."""
    text = str(value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        d = to_date(text)
        return (d, None) if d else None
    try:
        dt = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    dt = dt.astimezone(dash.LONDON)
    return dt.date(), f"{dt:%H:%M}"


def diary_items(entries):
    """Calendar cache entries [{start, end, summary, calendar}] -> items; invalid entries are skipped."""
    out = []
    for e in entries if isinstance(entries, list) else []:
        if not isinstance(e, dict) or not isinstance(e.get("summary", ""), str):
            continue
        start = _when(e.get("start"))
        if not start:
            continue
        summary = (e.get("summary") or "(no title)").strip()[:120]
        cal = str(e.get("calendar") or "").strip()[:40]
        end = _when(e.get("end"))
        last = start[0]
        if end and start[1] is None and end[1] is None and end[0] > start[0]:
            last = min(end[0] - datetime.timedelta(days=1), start[0] + datetime.timedelta(days=30))
        day = start[0]
        while day <= last:
            text = (f"{start[1]} " if start[1] and day == start[0] else "") + summary + (f" · {cal}" if cal else "")
            out.append(item(day, "diary", text))
            day += datetime.timedelta(days=1)
    return out


KIND_ORDER = {"event": 0, "diary": 1, "deposit": 2, "balance": 3, "followup": 4, "enquiry": 5}


def calendar_items(view, anchor, today, *lists):
    """The month or week grid around `anchor`: {view, title, weeks: [[{date, items, in_range, today}]], prev,
    next}. `lists` are item lists (bookings, enquiries, diary)."""
    by_day = {}
    for lst in lists:
        for i in lst or []:
            if i["date"]:
                by_day.setdefault(i["date"], []).append(i)
    for v in by_day.values():
        v.sort(key=lambda i: (KIND_ORDER.get(i["kind"], 9), i["text"]))
    if view == "week":
        start = anchor - datetime.timedelta(days=anchor.weekday())
        end = start + datetime.timedelta(days=6)
        prev, nxt = start - datetime.timedelta(days=7), start + datetime.timedelta(days=7)
        title = f"Week of {start.day} {start:%B %Y}"
        in_range = (start, end)
    else:
        first = anchor.replace(day=1)
        last = (first.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        start = first - datetime.timedelta(days=first.weekday())
        end = last + datetime.timedelta(days=6 - last.weekday())
        prev = (first - datetime.timedelta(days=1)).replace(day=1)
        nxt = last + datetime.timedelta(days=1)
        title = f"{first:%B %Y}"
        in_range = (first, last)
    weeks, day = [], start
    while day <= end:
        week = []
        for _ in range(7):
            week.append({"date": day, "entries": by_day.get(day, []), "in_range": in_range[0] <= day <= in_range[1],
                         "today": day == today})
            day += datetime.timedelta(days=1)
        weeks.append(week)
    return {"view": view, "title": title, "weeks": weeks, "prev": prev, "next": nxt, "anchor": anchor}


# ---------------------------------------------------------------- search


def clean_query(q):
    return re.sub(r"\s+", " ", str(q or "")).strip()[:SEARCH_MAX]


def _ref_query(q):
    return re.sub(r"^(inv|invoice|lcs)[\s#:-]*", "", q.casefold())


def search(q, kind, rows):
    """Matches of `q` (casefolded substring) in one source's rows, as [{kind, label, detail, href}]."""
    q = clean_query(q).casefold()
    if len(q) < SEARCH_MIN:
        return []
    out = []
    if kind == "bookings":
        rq = _ref_query(q)
        for r in rows:
            ref = (r.get("booking_ref") or "").strip()
            if (rq and rq in ref.casefold()) or q in (r.get("client_name") or "").casefold():
                out.append({"kind": "Booking", "label": f"{ref} {first_name(r.get('client_name'))}",
                            "detail": f"{r.get('occasion') or ''} {r.get('event_date') or ''}".strip(),
                            "href": f"/bookings/{ref}" if REF_RE.fullmatch(ref) else None})
    elif kind == "enquiries":
        for r in rows:
            fields = [r.get("enquiry_id"), r.get("occasion"), r.get("booking_ref"), r.get("package")]
            if any(q in (f or "").casefold() for f in fields):
                eid = r.get("enquiry_id", "")
                out.append({"kind": "Enquiry", "label": eid,
                            "detail": f"{r.get('occasion') or ''} · {pl.status_of(r) or 'no status'}",
                            "href": f"/enquiries/{eid}" if pl.ID_RE.fullmatch(eid) else None})
    elif kind == "singers":
        rq = _ref_query(q)
        for r in rows:
            bill = si.bill_number(r.get("invoice_ref"), r.get("message_id"))
            ref = (r.get("invoice_ref") or "").casefold()
            if (q in (r.get("singer_name") or "").casefold() or (rq and (rq in ref or rq in bill.casefold()))):
                state = "withdrawn" if si.is_withdrawn(r) else ("paid" if r.get("paid_on") else "unpaid")
                out.append({"kind": "Singer invoice", "label": f"{si.first_name(r.get('singer_name'))} · {bill}",
                            "detail": f"£{lm.money(r.get('amount_gbp')):,.2f} · received {r.get('received') or '?'} · {state}",
                            "href": "/singers"})
    return out[:SEARCH_LIMIT]


# ---------------------------------------------------------------- CSV exports


def csv_safe(value):
    """A CSV cell a spreadsheet won't run as a formula."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def _iso(d):
    return d.isoformat() if d else ""


def export_bookings(bookings):
    head = ["booking_ref", "invoice_date", "event_date", "first_name", "occasion", "ensemble", "value_gbp", "state",
            "received_gbp", "balance_gbp"]
    rows = [[b["ref"], _iso(b["invoice_date"]), _iso(b["event_date"]), b["first_name"], b["occasion"], b["ensemble"],
             f"{b['value']:.2f}", b["state"], f"{b['received'] or 0:.2f}", f"{b['balance'] or 0:.2f}"] for b in bookings]
    return head, rows


def export_singers(store):
    head = ["received", "first_name", "bill_number", "amount_gbp", "payee", "bank", "bank_changed", "bank_confirmed",
            "paid_on", "paid_amount_gbp", "paid_verified", "withdrawn"]
    rows = []
    for r in sorted(store, key=lambda r: r.get("received") or ""):
        last4 = dash.digits4(r.get("bank_last4"))
        rows.append([r.get("received", ""), si.first_name(r.get("singer_name")),
                     si.bill_number(r.get("invoice_ref"), r.get("message_id")), f"{lm.money(r.get('amount_gbp')):.2f}",
                     si.payee_status(r.get("payee")) or "new payee", f"••••{last4}" if last4 else "",
                     r.get("bank_changed", ""), r.get("bank_confirmed", ""), r.get("paid_on", ""),
                     r.get("paid_amount", ""), r.get("paid_verified", ""), r.get("withdrawn", "")])
    return head, rows


def export_pipeline(enquiries, cache):
    cols = [c for c in pl.COLUMNS if c not in ("notes", "gclid")]
    rows = [[r.get(c, "") for c in cols] + [campaign_for(r, cache) or ""] for r in enquiries]
    return cols + ["campaign"], rows
