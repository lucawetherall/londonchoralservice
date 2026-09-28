"""Pure builders for the phase-2 pages: plain data in, plain data out, no file or network access.

The rules stay in the scripts: payment states come from check_payments (collect, assess, deposit_due_date,
is_cancelled, closed_on), the pipeline's from pipeline (followups_due, reviews_due, summary_dict, STATUS_ORDER),
the singers' from singer_invoices (normalise_name, first_name, payee_status, is_open, ring_first_in, trust_label, live_warnings,
bill_number). What is here only arranges their answers for a page.

Privacy, as on the phase-1 pages: client and singer first names only, emails never, bank accounts as
••••last4 only, and any run of six or more digits in free text is masked to its last four.
"""

import datetime
import hashlib
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


def invoice_key(message_id):
    """A singer invoice's handle for the action forms: 12 lower-case letters from sha256 of its message id, so a
    page never carries the id (a long digit run) and the server looks the invoice up again from the store."""
    digest = hashlib.sha256(("lcs-cc-invoice:" + str(message_id or "")).encode("utf-8")).digest()
    return "".join(chr(97 + b % 26) for b in digest[:12])


def singer_actions(r):
    """Which singer-invoice actions a store row allows (the validators in actions.py check again)."""
    open_ = si.is_open(r)
    return {"key": invoice_key(r.get("message_id")),
            "can_confirm": bool(r.get("bank_fp")) and r.get("bank_confirmed") != "yes" and not si.is_withdrawn(r),
            "can_settle": open_, "can_withdraw": open_}


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


def linked_singer_rows(ref, event_date, singer_rows):
    """The singer invoices linked to a booking: the store's booking_ref (singer_invoices.py link, or the automatic
    link at scan), or an event_date column when a store has one. Withdrawn invoices are left out."""
    out = []
    for r in singer_rows:
        if si.is_withdrawn(r):
            continue
        by_ref = bool(ref) and (r.get("booking_ref") or "").strip() == ref
        by_date = bool(event_date) and to_date(r.get("event_date")) == event_date
        if by_ref or by_date:
            out.append(r)
    return out


def booking_singers(event_date, singer_rows, ref=None):
    """The timeline items for the singer invoices linked to a booking (linked_singer_rows)."""
    out = []
    for r in linked_singer_rows(ref, event_date, singer_rows):
        paid = f", paid {r['paid_on']}" if r.get("paid_on") else ", unpaid"
        out.append(item(si.received_date(r), "singer",
                        f"Singer invoice from {si.first_name(r.get('singer_name'))}: "
                        f"£{lm.money(r.get('amount_gbp')):,.2f}{paid}"))
    return out


def booking_singer_list(ref, event_date, singer_rows):
    """[{first_name, amount, paid_on}] for the booking's linked singers, first names only."""
    return [{"first_name": si.first_name(r.get("singer_name")), "amount": lm.money(r.get("amount_gbp")),
             "paid_on": (r.get("paid_on") or "").strip()}
            for r in sorted(linked_singer_rows(ref, event_date, singer_rows), key=lambda r: r.get("received") or "")]


# ---------------------------------------------------------------- Books (R17) and margins (R18)


BOOKS_UNPAID = {"sent", "viewed", "unpaid", "overdue"}
STARLING_MATCHED = {"DEPOSIT_SEEN", "PAID_IN_FULL"}
DRAFT_DAYS = 2  # Appendix A step 6g: a Books draft more than 2 days old
LEDGER_SETTLED = {"PAID_IN_FULL", "CLOSED", "CANCELLED", "PAYMENT_ON_CANCELLED"}  # not "open" for the ledger rule


BOOKS_STALE = datetime.timedelta(hours=24)  # Today warns when books.json is older than this


def books_synced(cache, now):
    """{generated_at (an aware datetime, or None when unreadable), stale} for the "as of" line on Today."""
    try:
        when = datetime.datetime.fromisoformat(str(cache.get("generated_at")))
    except ValueError:
        when = None
    if when is not None and when.tzinfo is None:
        when = when.replace(tzinfo=dash.LONDON)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dash.LONDON)
    return {"generated_at": when, "stale": when is None or now - when > BOOKS_STALE}


def ledger_href(number, ledger_rows):
    """/bookings/<ref> for the ledger booking whose ref is this Books number (check_payments.norm_ref on both), or
    None when there is no such booking."""
    key = cp.norm_ref(str(number or ""))
    for r in ledger_rows or []:
        ref = (r.get("booking_ref") or "").strip()
        if key and cp.norm_ref(ref) == key and REF_RE.fullmatch(ref):
            return f"/bookings/{ref}"
    return None


def books_summary(cache, ledger_rows=None):
    """The Money page's Books panel from books.json: totals, draft and overdue invoices ({number, href}: the ledger
    booking's page, or None when the ledger has no such booking), and when it was synced (an aware datetime, or
    None when the stamp is unreadable)."""
    try:
        when = datetime.datetime.fromisoformat(str(cache.get("generated_at")))
    except ValueError:
        when = None
    invoices = [i for i in cache.get("invoices") or [] if isinstance(i, dict)]

    def listed(keep):
        numbers = sorted(str(i.get("number", "")) for i in invoices if keep(i))
        return [{"number": n, "href": ledger_href(n, ledger_rows)} for n in numbers]
    return {"totals": cache.get("totals") or {}, "generated_at": when,
            "drafts": listed(lambda i: i.get("status") == "draft"),
            "overdue": listed(lambda i: i.get("status") == "overdue" and float(i.get("balance") or 0) > 0)}


def books_invoice(ref, invoices):
    """The Books invoice whose number is this booking ref (check_payments.norm_ref on both), or None."""
    key = cp.norm_ref(ref)
    return next((i for i in invoices or [] if isinstance(i, dict) and key and cp.norm_ref(str(i.get("number"))) == key),
                None)


def books_timeline(ref, invoices):
    """The booking's Books invoice as a timeline item (status, total and balance), or [] when it isn't in Books."""
    i = books_invoice(ref, invoices)
    if i is None:
        return []
    status = str(i.get("status") or "?")
    tone = "bad" if status == "overdue" else "warn" if status == "draft" else "ok" if status == "paid" else ""
    return [item(to_date(i.get("date")), "books",
                 f"Books invoice {i.get('number')}: {status}, £{float(i.get('total') or 0):,.2f}"
                 f" (balance £{float(i.get('balance') or 0):,.2f})", tone=tone)]


def books_flags(invoices, ledger_rows, bookings, today, bank_checked):
    """The Appendix A step 6g disagreements, for Today: [{ref, text, tone}].

    - a Books draft more than 2 days old: "Books draft not sent (>2 days)";
    - Books paid, but Starling hasn't matched the full fee (the state isn't PAID_IN_FULL and the notes have no
      "paid in full" date): "Books paid, Starling not matched";
    - Starling matched a payment (DEPOSIT_SEEN, PAID_IN_FULL, or a "paid in full" note) but Books shows the invoice
      unpaid or overdue with nothing paid: "Starling matched, Books unpaid"; or part-paid when Starling says paid in
      full: "Starling paid in full, Books part-paid".
    The two Starling comparisons are skipped when the bank wasn't checked, as 6g skips them.

    And the ledger against Books (the caller passes a cache, so these never run while Books isn't synced):
    - an open ledger booking (not cancelled, not closed, not paid in full) invoiced at least 2 days ago with no
      Books invoice of its ref (a void one doesn't count): "in the ledger, not in Books";
    - a Books invoice, not a draft or void, whose number is no ledger ref: "in Books, not in the ledger".
    Each flag carries `href`: the ledger booking's page, or None when the ledger has no such booking."""
    rows = {cp.norm_ref(r.get("booking_ref")): r for r in ledger_rows if (r.get("booking_ref") or "").strip()}
    states = {cp.norm_ref(b.get("ref")): b.get("state") for b in bookings}
    out = []

    def flag(number, text, tone):
        row = rows.get(cp.norm_ref(number))
        ref = (row.get("booking_ref") or "").strip() if row else ""
        out.append({"ref": number, "text": text, "tone": tone,
                    "href": f"/bookings/{ref}" if ref and REF_RE.fullmatch(ref) else None})

    in_books = set()
    for i in invoices or []:
        if not isinstance(i, dict):
            continue
        number = str(i.get("number") or "")
        key = cp.norm_ref(number)
        status = str(i.get("status") or "")
        made = to_date(i.get("date"))
        if key and status != "void":
            in_books.add(key)
        if key and status not in ("draft", "void") and key not in rows:
            flag(number, "in Books, not in the ledger", "warn")
        if status == "draft":
            if made and (today - made).days > DRAFT_DAYS:
                flag(number, "Books draft not sent (>2 days)", "warn")
            continue
        if not bank_checked or key not in rows:
            continue
        state = states.get(key)
        full = state == "PAID_IN_FULL" or bool(cp.closed_on(rows[key]))
        matched = full or state in STARLING_MATCHED
        total, balance = float(i.get("total") or 0), float(i.get("balance") or 0)
        if status == "paid" and not full:
            flag(number, "Books paid, Starling not matched", "bad")
        elif status in BOOKS_UNPAID and matched and total > 0 and balance >= total - 0.005:
            flag(number, "Starling matched, Books unpaid", "warn")
        elif status == "partially_paid" and full:
            flag(number, "Starling paid in full, Books part-paid", "warn")
    for key, r in rows.items():
        invoiced = to_date(r.get("invoice_date"))
        if key in in_books or cp.is_cancelled(r) or cp.closed_on(r) or invoiced is None \
                or states.get(key) in LEDGER_SETTLED:
            continue
        if (today - invoiced).days >= DRAFT_DAYS:
            flag(r["booking_ref"].strip(), "in the ledger, not in Books", "warn")
    return sorted(out, key=lambda f: (f["ref"], f["text"]))


def _bill_first(r):
    return si.first_name(r.get("singer_name"))


def singer_bill_flags(store_rows, bills):
    """The singer store against the Books bills, for Today's Books and Starling card: [{ref, text, tone, href}].

    - a singer invoice paid with paid_verified "yes" whose Books bill (singer_invoices.books_bill) is still open
      with a balance: "paid in Starling, bill open in Books";
    - a Books bill marked paid whose invoice is still open here (not paid, not withdrawn): "bill paid in Books,
      invoice open here".
    `ref` is the bill number and the first name ("SI-12345 Jane"); `href` is the Singers page."""
    out = []
    for r in store_rows or []:
        if si.is_withdrawn(r):
            continue
        bill = si.books_bill(r, bills)
        if bill is None:
            continue
        number = si.bill_number(r.get("invoice_ref"), r.get("message_id"))
        label = f"{mask_digits(number)} {_bill_first(r)}".strip()
        status = str(bill.get("status") or "")
        balance = float(bill.get("balance") or 0)
        if r.get("paid_on") and r.get("paid_verified") == "yes" and status not in ("paid", "void") and balance > 0:
            out.append({"ref": label, "text": "paid in Starling, bill open in Books", "tone": "warn", "href": "/singers"})
        elif status == "paid" and si.is_open(r):
            out.append({"ref": label, "text": "bill paid in Books, invoice open here", "tone": "warn",
                        "href": "/singers"})
    return sorted(out, key=lambda f: (f["ref"], f["text"]))


def margin_map(margins):
    """singer_invoices.margins() keyed by booking ref."""
    return {m["ref"]: m for m in margins}


def season_margin(margins, start):
    """The season's totals from `start` (a date): bookings with an event date on or after it, cancelled ones left
    out. {fee, costs, margin, margin_pct, count, start}."""
    rows = [m for m in margins if not m["cancelled"] and to_date(m.get("event_date")) and
            to_date(m["event_date"]) >= start]
    fee = round(sum(m["fee"] for m in rows), 2)
    costs = round(sum(m["costs"] for m in rows), 2)
    margin = round(fee - costs, 2)
    return {"fee": fee, "costs": costs, "margin": margin, "margin_pct": round(100 * margin / fee, 1) if fee else None,
            "count": len(rows), "start": start}


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


def _warnings(rows, r):
    """si.live_warnings (no bank alarm once the account is trusted anywhere in rows), long digit runs masked."""
    return [mask_digits(n) for n in si.live_warnings(rows, r)]


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
        if any(si.ring_first_in(rows, r) for r in live if si.is_open(r)):
            warnings.append("Bank details changed: ring on a number you already have before paying")
        for r in live:
            if si.is_open(r):
                warnings += [w for w in _warnings(rows, r) if w not in warnings]
        if not latest.get("bank_fp"):
            check = "no bank details on file"
        else:  # the account, not just this row: confirmed or paid to verifiably on any invoice with the same details
            check = si.trust_label(rows, latest) or "not yet verified"
        invoices = [{"received": si.received_date(r), "bill_number": si.bill_number(r.get("invoice_ref"), r.get("message_id")),
                     "amount": lm.money(r.get("amount_gbp")), "paid_on": to_date(r.get("paid_on")),
                     "paid_amount": lm.parse_gbp(r.get("paid_amount")), "open": si.is_open(r),
                     "ring_first": si.ring_first_in(rows, r), "last4": dash.digits4(r.get("bank_last4")),
                     **singer_actions(r)} for r in live]
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


# ---------------------------------------------------------------- handoff prompts (Claude Code Remote Control)
#
# There is no in-app chat and the app never runs Claude Code itself (see docs/superpowers/specs/
# 2026-09-28-command-centre-design.md, binding rule 6). These build the fixed text a "Copy prompt for Remote
# Control" button puts on the clipboard: plain templates plus a ref/thread id already on the page, never free
# text typed into the app. Copying needs no passkey, because nothing runs until the owner pastes the prompt
# into Claude Code Remote Control on his phone.

BOOKS_IMPORT_PROMPT = (
    "Run the owner-approved Zoho Books 2026 import: read ~/lcs-private/books-import-2026.json and "
    "~/lcs-private/command-centre/approvals/books-import-2026.json{approval}, check the approval's dry-run "
    "sha256 still matches the dry run, first list the invoices already in Books and skip any invoice number "
    "that already exists, then create each remaining invoice as a draft in Zoho Books under the guard "
    "(see docs/superpowers/specs/2026-09-28-zoho-books-design.md) — never send, void or record a payment — "
    "then report. I mark the import done on the Command Centre's Today page afterwards."
)


def books_import_handoff(approval):
    """The fixed Books-import handoff prompt, or None unless the import is approved, matches the dry run and isn't
    done yet (state "approved"). `approval` is actions.books_status()'s dict. The prompt never carries any
    record's own text (client names, amounts, refs): only the file paths, the guard doc, and the approval's own
    sha256 prefix, which is a fingerprint of the record, not its content, and is already shown on the page."""
    if not approval or approval.get("state") != "approved" or not approval.get("approved_at"):
        return None
    sha = approval.get("dry_run_sha256")
    detail = f" (approval hash {sha[:16]}…)" if sha else ""
    return BOOKS_IMPORT_PROMPT.format(approval=detail)


def whats_owed_prompt():
    return (
        "What's owed this week? Read the ledger and the Starling balance the way "
        "scripts/reports/dashboard.py and scripts/bookings/money_report.py do, and scripts/bookings/"
        "check_payments.py for anything on the hand check. Summarise what's due this week, what's overdue, "
        "and what's outstanding from singers (scripts/bookings/singer_invoices.py). Read only; don't change "
        "anything."
    )


def summarise_today_prompt():
    return (
        "Summarise today's business: today's and this week's events from the ledger "
        "(scripts/reports/dashboard.py), anything on the hand check (scripts/bookings/check_payments.py), "
        "enquiries needing a follow-up (scripts/bookings/pipeline.py) and anything flagged on the Command "
        "Centre's Runs and health page. A few lines, read only."
    )


def hand_check_prompt(ref, label=""):
    """`ref` must already be a value the hand-check panel produced (REF_RE); the caller only offers refs
    currently on the hand check, so this never becomes a way to name an arbitrary ledger row from free text."""
    if not isinstance(ref, str) or not REF_RE.fullmatch(ref):
        return None
    why = f" (currently: {label})" if label else ""
    return (
        f"Why is {ref} on the hand check{why}? Read scripts/bookings/check_payments.py's assessment for {ref} "
        f"against the ledger (scripts/bookings/money_report.py) and, if the Starling token is available, the "
        f"bank transactions, and explain what would resolve it. Read only; don't change anything."
    )


def draft_reply_prompt(thread_id):
    """`thread_id` must be an enquiry id the caller already has (pl.ID_RE) — an enquiry the pipeline knows
    about, not a value typed into the app."""
    if not isinstance(thread_id, str) or not pl.ID_RE.fullmatch(thread_id):
        return None
    return (
        f"Draft a reply to {thread_id}: read the Zoho thread for enquiry {thread_id} "
        f"(scripts/bookings/pipeline.py), Luca's quote style (~/lcs-private/email-style.md) and his most "
        f"recent sent replies for the same kind of booking, checked against the stop-slop skill. Prices from "
        f"pricing.html/christmas-pricing.html. Save the reply as a Zoho draft only — never send it."
    )
