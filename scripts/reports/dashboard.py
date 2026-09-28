#!/usr/bin/env python3
"""The owner's private dashboard: one self-contained HTML page at ~/lcs-private/dashboard.html (mode 600).

    .venv/bin/python scripts/reports/dashboard.py            # reads Starling (GET only) when a Keychain token exists
    .venv/bin/python scripts/reports/dashboard.py --no-bank  # ledger notes only, no Starling calls

It prints one line, "dashboard written: <path>", and never any data. The page is a local file only: never
publish, commit, attach or copy it anywhere (spec: docs/superpowers/specs/2026-09-28-business-automation-design.md,
Phase 5). It makes no network requests of its own: inline CSS, no scripts, fonts, images or links, and a
Content-Security-Policy that blocks everything else.

gather(client, today) reads the private files (and Starling, when a client is given) into a plain dict;
render(data) turns that dict into HTML and nothing else, so tests drive it with fake data. Each section is
built and rendered on its own: one that fails shows "couldn't load (<TypeName>)" and the rest still render.
Only client and singer first names appear, and never more of a bank account than ••••last4.

The Books section (R21) reuses command_centre/books_cache.py, read-only, for the cache the daily pass writes
(cc_sync.py books): totals, draft and overdue invoice numbers, the season margin (books_cache.margins(), the
same figures the Command Centre's Money page shows) and unlinked singer invoices (singer_invoices.unlinked_
invoices). "Books not synced yet." when the cache doesn't exist.
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import urllib.error
from pathlib import Path
from zoneinfo import ZoneInfo

BOOKINGS = Path(__file__).resolve().parent.parent / "bookings"
sys.path.insert(0, str(BOOKINGS))
import check_payments as cp  # noqa: E402
import lcs_money as lm  # noqa: E402
import money_report as mr  # noqa: E402
import pipeline as pl  # noqa: E402  summary_dict: the Monday report's pipeline figures
import singer_invoices as si  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import economics as ec  # noqa: E402  load_windows: the season start

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from command_centre import books_cache as bc  # noqa: E402  R21: the Books panel and season margin reuse this reader
BUDGET_WINDOWS = REPO / "data" / "budget-windows.yml"  # season_start, as the Monday report's section 11 reads it

LONDON = ZoneInfo("Europe/London")
# URLError and HTTPError are OSErrors too; a non-JSON 200 body (an outage page) is a JSONDecodeError
BANK_DOWN = (lm.StarlingError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
             json.JSONDecodeError)
STATUS_ORDER = pl.STATUS_ORDER
STATES = {  # payment state -> (words, tone)
    "PAID_IN_FULL": ("paid in full", "ok"), "CLOSED": ("paid in full (closed)", "ok"),
    "DEPOSIT_SEEN": ("deposit in", "ok"), "AWAITING_DEPOSIT": ("awaiting deposit", ""),
    "BALANCE_DUE": ("balance due", "warn"), "DEPOSIT_OVERDUE": ("deposit overdue", "bad"),
    "NOTED_PAID": ("noted paid", "warn"), "CHECK_PAYMENT": ("possible payment: check", "warn"),
    "CHECK_VALUE": ("unreadable value or date", "warn"), "PAST_UNMATCHED": ("past, unpaid", "bad"),
    "PAST_PART_PAID": ("past, part paid", "bad"), "PAYMENT_ON_CANCELLED": ("payment on a cancelled booking", "bad"),
    "PAYMENT_AFTER_CLOSE": ("payment after paid in full", "bad"),
    "ARRANGED": ("balance arranged (cash/cheque)", "warn"),
}


def private_dir():
    return Path(lm.PRIVATE)


def out_path():
    return private_dir() / "dashboard.html"


# ---------------------------------------------------------------- gather


def section(fn, *args):
    """Run one section's builder; a failure becomes {"failed": TypeName} (never the message: it may hold data)."""
    try:
        return fn(*args)
    except Exception as e:
        return {"failed": type(e).__name__}


def first_name(name):
    return si.first_name(name) if (name or "").strip() else "?"


def payments(client, rows, today):
    """(assessments, receipts or None, bank_checked). Without a working bank: each open row's notes-only state."""
    if client is not None:
        try:
            assessments = [a for _, _, a in cp.collect(client, rows, today)]
            receipts = cp.received_since(client, rows, today - datetime.timedelta(days=6), today)
            return assessments, receipts, True
        except BANK_DOWN:
            pass
    return [cp.assess(r, [], today) for r in cp.open_rows(rows)], None, False


def upcoming(rows, assessments, bank_checked, today):
    by_ref = {a["ref"]: a for a in assessments}
    out = []
    for r in rows:
        day = cp.date_or_none(r.get("event_date"))
        if not day or day < today or cp.is_cancelled(r):
            continue
        a = by_ref.get(r.get("booking_ref"))
        state = a["state"] if a else ("CLOSED" if cp.closed_on(r) else cp.assess(r, [], today)["state"])
        out.append({"date": day.isoformat(), "ref": r.get("booking_ref", ""), "first_name": first_name(r.get("client_name")),
                    "occasion": r.get("occasion", ""), "ensemble": r.get("ensemble", ""), "value": cp.money(r),
                    "state": state, "bank_checked": bank_checked})
    return sorted(out, key=lambda u: (u["date"], u["ref"]))


def money_lines(assessments, receipts, singer_rows, today):
    lines = mr.summary_lines(assessments, receipts or [], si.summary(singer_rows, today), today)
    if receipts is None:
        lines[0] = "received from clients, last 7 days: bank not checked"
    return lines


def hand_check(assessments, today):
    """The Monday money line's "needs a hand check" list (money_report.needs_hand_check), one row each."""
    return [{"ref": a["ref"], "state": a["state"], "label": mr.hand_check_label(a), "value": a.get("value") or 0.0,
             "received": a.get("received") or 0.0} for a in assessments if mr.needs_hand_check(a, today)]


def digits4(value):
    return re.sub(r"\D", "", str(value or ""))[-4:]


payee_status = si.payee_status  # whether Starling already knows the singer, never the payee's name


def singers(rows):
    return [{"received": r.get("received", ""), "first_name": first_name(r.get("singer_name")),
             "amount": lm.money(r.get("amount_gbp")), "payee": payee_status(r.get("payee", "")),
             "bank_changed": r.get("bank_changed") == "yes", "ring_first": si.ring_first(r),
             "last4": digits4(r.get("bank_last4"))}
            for r in sorted(rows, key=lambda r: r.get("received") or "") if si.is_open(r)]


def enquiries():
    path = private_dir() / "enquiries.csv"
    return lm.read_csv(path) if path.exists() else None


def season_start():
    """season_start from data/budget-windows.yml, the date the Monday report's section 11 counts from."""
    start = ec.load_windows(BUDGET_WINDOWS)["season_start"]
    if start is None:
        raise ValueError("season_start")
    return start


def window(rows, label, since):
    """One window's figures, straight from pipeline.summary_dict, so they match the Monday report."""
    s = pl.summary_dict(rows, since)
    return {"label": label, "counts": {k: n for k, n in s["by_status"].items() if n}, "total": s["enquiries"],
            "quoted": s["quoted"], "confirmed": s["confirmed"], "rate": s["conversion_rate"]}


def pipeline(enq, today):
    if enq is None:
        return None
    start = season_start()
    return {"season_start": start.isoformat(),
            "windows": [window(enq, "Season", start), window(enq, "Last 30 days", today - datetime.timedelta(days=30))]}


def ads(enq):
    path = private_dir() / "ads-summary.json"
    if not path.exists():
        return None
    with open(path) as f:
        summary = json.load(f)
    weeks = sorted(summary.get("weeks") or [], key=lambda w: w["week_start"], reverse=True)[:4]
    out = []
    for w in weeks:
        start = datetime.date.fromisoformat(w["week_start"][:10])
        row = {"week_start": start.isoformat(), "spend": float(w.get("spend_gbp") or 0),
               "clicks": int(w.get("clicks") or 0), "enquiries": None, "cpe": None}
        if enq is not None:
            end = (start + datetime.timedelta(days=7)).isoformat()
            n = sum(start.isoformat() <= (r.get("first_seen") or "")[:10] < end for r in enq)
            row["enquiries"], row["cpe"] = n, (round(row["spend"] / n, 2) if n else None)
        out.append(row)
    return {"generated": str(summary.get("generated") or ""), "weeks": out}


def season_totals(margins, start):
    """The season's margin totals from `start` (a date), cancelled bookings left out: {fee, costs, margin,
    margin_pct, count, start}. A small local copy of command_centre.models.season_margin: importing that module
    here would import dashboard right back (it does `import dashboard as dash`), so this stays self-contained."""
    rows = [m for m in margins if not m["cancelled"] and cp.date_or_none(m.get("event_date")) and
            cp.date_or_none(m["event_date"]) >= start]
    fee = round(sum(m["fee"] for m in rows), 2)
    costs = round(sum(m["costs"] for m in rows), 2)
    margin = round(fee - costs, 2)
    return {"fee": fee, "costs": costs, "margin": margin, "margin_pct": round(100 * margin / fee, 1) if fee else None,
            "count": len(rows), "start": start}


def books_section():
    """The Books panel: totals, draft and overdue invoice numbers (command_centre.books_cache.books_cache(),
    written by the daily pass's `cc_sync.py books`), the season margin (books_cache.margins(), the same reader
    the Command Centre's Money page uses) and unlinked singer invoices. None when Books isn't synced yet."""
    cache = bc.books_cache()
    if cache is None:
        return None
    invoices = [i for i in cache.get("invoices") or [] if isinstance(i, dict)]
    drafts = sorted(str(i.get("number", "")) for i in invoices if i.get("status") == "draft")
    overdue = sorted(str(i.get("number", "")) for i in invoices
                      if i.get("status") == "overdue" and float(i.get("balance") or 0) > 0)
    try:
        when = datetime.datetime.fromisoformat(str(cache.get("generated_at")))
    except ValueError:
        when = None
    season = season_totals(bc.margins(), season_start())
    unlinked = si.unlinked_invoices(lm.read_csv(si.STORE))
    return {"totals": cache.get("totals") or {}, "drafts": drafts, "overdue": overdue,
            "bills_read": cache.get("bills_read") is not False,
            "generated_at": when.isoformat() if when else None, "season": season, "unlinked": unlinked}


def bank_balance(client):
    if client is None:
        return None
    try:
        uid = client.account()["accountUid"]
        b = client.get(f"/api/v2/accounts/{uid}/balance")
    except BANK_DOWN:
        return None
    return {"cleared": b["clearedBalance"]["minorUnits"] / 100, "effective": b["effectiveBalance"]["minorUnits"] / 100}


def stamp(now):
    return f"{now:%A} {now.day} {now:%B %Y, %H:%M}"


def gather(client, today):
    """Everything the page shows, as plain data. client is a StarlingReadOnly (GET only) or None: no bank."""
    data = {"generated": stamp(datetime.datetime.now(LONDON)), "bank_checked": False}
    try:
        rows = lm.read_csv(cp.LEDGER)
        assessments, receipts, data["bank_checked"] = payments(client, rows, today)
    except Exception as e:
        failed = {"failed": type(e).__name__}
        data.update(upcoming=failed, money=failed, hand_check=failed)
    else:
        data["upcoming"] = section(upcoming, rows, assessments, data["bank_checked"], today)
        data["money"] = section(lambda: money_lines(assessments, receipts, lm.read_csv(si.STORE), today))
        data["hand_check"] = section(hand_check, assessments, today)
    data["singers"] = section(lambda: singers(lm.read_csv(si.STORE)))
    enq = section(enquiries)
    enq_ok = not (isinstance(enq, dict) and "failed" in enq)
    data["pipeline"] = section(pipeline, enq, today) if enq_ok else enq
    data["ads"] = section(ads, enq if enq_ok else None)
    data["bank"] = section(bank_balance, client)
    data["books"] = section(books_section)
    return data


# ---------------------------------------------------------------- render

e = html.escape

CSS = """
:root{--bg:#faf8f4;--fg:#1d1b18;--muted:#6b665e;--card:#fff;--line:#e3ddd2;--ok:#1f6f43;--okbg:#e3f2e8;
--warn:#8a5a00;--warnbg:#fbf0d9;--bad:#a4262c;--badbg:#fbe4e4;--accent:#5b3a29}
@media (prefers-color-scheme: dark){:root{--bg:#161412;--fg:#ece7df;--muted:#a59e93;--card:#201d1a;--line:#36312b;
--ok:#7fd4a0;--okbg:#18321f;--warn:#f0c46a;--warnbg:#3a2d10;--bad:#f19a9a;--badbg:#3d1a1a;--accent:#e0b99c}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",
Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%}
main{max-width:960px;margin:0 auto;padding:16px}
header{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:4px 16px;margin:8px 0 16px}
h1{font-size:1.5rem;margin:0;color:var(--accent)}
.gen{color:var(--muted);font-size:.9rem}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:0 0 14px}
h2{font-size:1.1rem;margin:0 0 8px}
h3{font-size:.95rem;margin:12px 0 4px;color:var(--muted)}
p{margin:4px 0}
ul{margin:0;padding-left:1.2em}
.muted{color:var(--muted)}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
table{width:100%;border-collapse:collapse;font-size:.95rem}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{font-weight:600;color:var(--muted);font-size:.85rem}
tr:last-child td{border-bottom:0}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:.85rem;background:var(--line)}
.ok{background:var(--okbg);color:var(--ok)}.warn{background:var(--warnbg);color:var(--warn)}
.bad{background:var(--badbg);color:var(--bad)}
.fail{color:var(--bad)}
.big{font-size:1.4rem;font-weight:600;font-variant-numeric:tabular-nums}
.pair{display:flex;flex-wrap:wrap;gap:8px 32px}
@media (max-width:640px){
table,thead,tbody,tr,th,td{display:block}thead{display:none}
tr{border-bottom:1px solid var(--line);padding:6px 0}tr:last-child{border-bottom:0}
td{border:0;padding:2px 0;text-align:left}
td::before{content:attr(data-label);display:inline-block;min-width:7.5em;color:var(--muted);font-size:.85rem}
.num{text-align:left}}
"""


def gbp(x):
    return e(f"£{float(x):,.2f}")


def day(iso):
    try:
        d = datetime.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return e(str(iso))
    return e(f"{d:%a} {d.day} {d:%b %Y}")


def badge(text, tone=""):
    return f'<span class="badge {e(tone)}">{e(str(text))}</span>'


def table(columns, rows):
    """columns: [(label, is_number)]; rows: lists of already-escaped cell HTML."""
    def cls(num):
        return ' class="num"' if num else ""
    head = "".join(f"<th{cls(num)}>{e(label)}</th>" for label, num in columns)
    body = "".join("<tr>" + "".join(f'<td data-label="{e(label)}"{cls(num)}>{cell}</td>'
                                    for (label, num), cell in zip(columns, row)) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def failed(value):
    return isinstance(value, dict) and "failed" in value


def fail(name):
    return '<p class="fail">' + e("couldn't load (" + str(name) + ")") + "</p>"


def state_html(u):
    words, tone = STATES.get(u["state"], (u["state"], ""))
    if not u.get("bank_checked"):
        return badge("bank not checked") + " " + badge(f"notes: {words}", "")
    return badge(words, tone)


def r_upcoming(items, data):
    if not items:
        return '<p class="muted">No upcoming events in the ledger.</p>'
    note = "" if data.get("bank_checked") else \
        '<p class="muted">Bank not checked: payment states come from the ledger notes only.</p>'
    return note + table([("Date", False), ("Ref", False), ("Client", False), ("Occasion", False), ("Ensemble", False),
                         ("Value", True), ("Payment", False)],
                        [[day(u["date"]), e(str(u["ref"])), e(str(u["first_name"])), e(str(u["occasion"])),
                          e(str(u["ensemble"])), gbp(u["value"]), state_html(u)] for u in items])


def r_money(lines, data):
    return "<ul>" + "".join(f"<li>{e(str(x))}</li>" for x in lines) + "</ul>"


def r_hand(items, data):
    if not items:
        return '<p class="muted">Nothing needs a hand check.</p>'
    return table([("Ref", False), ("State", False), ("Value", True), ("Received", True)],
                 [[e(str(h["ref"])), badge(h["label"], STATES.get(h["state"], ("", "warn"))[1] or "warn"),
                   gbp(h["value"]), gbp(h["received"]) if data.get("bank_checked") else e("not checked")]
                  for h in items])


def masked(last4):
    d = digits4(last4)
    return e(f"••••{d}") if d else e("-")


def r_singers(items, data):
    if not items:
        return '<p class="muted">No unpaid singer invoices.</p>'
    rows = []
    for s in items:
        warn = (badge("BANK DETAILS CHANGED: ring before paying", "bad") if s.get("ring_first")
                else badge("changed, confirmed by phone", "warn") if s.get("bank_changed") else "")
        rows.append([day(s["received"]), e(str(s["first_name"])), gbp(s["amount"]), e(str(s["payee"])),
                     masked(s.get("last4")) + (" " + warn if warn else "")])
    total = sum(float(s["amount"]) for s in items)
    return (f'<p>{e(str(len(items)))} unpaid, {gbp(total)}</p>'
            + table([("Received", False), ("Singer", False), ("Amount", True), ("Payee", False), ("Bank", False)], rows))


def ordered(counts):
    known = [s for s in STATUS_ORDER if s in counts]
    return known + sorted(s for s in counts if s not in STATUS_ORDER)


def r_pipeline(p, data):
    if p is None:
        return '<p class="muted">pipeline sheet not set up yet</p>'
    out = [f'<p class="muted">Season from {day(p["season_start"])}.</p>']
    for w in p["windows"]:
        counts = w["counts"]
        status = " · ".join(f"{e(s)} {e(str(counts[s]))}" for s in ordered(counts)) or "none"
        rate = f" ({round(100 * w['rate'])}%)" if w.get("rate") is not None else ""
        out.append(f"<h3>{e(w['label'])}</h3><p>{e(str(w['total']))} enquiries: {status}</p>"
                   f"<p>{e(str(w['total']))} enquiries, {e(str(w['quoted']))} quoted, "
                   f"{e(str(w['confirmed']))} booked{e(rate)}</p>")
    return "".join(out)


def r_ads(a, data):
    if a is None:
        return '<p class="muted">run the Monday review to fill this</p>'
    weeks = a["weeks"]
    with_enq = any(w.get("enquiries") is not None for w in weeks)
    cols = [("Week from", False), ("Spend", True), ("Clicks", True)]
    if with_enq:
        cols += [("Enquiries", True), ("Cost per enquiry", True)]
    rows = []
    for w in weeks:
        row = [day(w["week_start"]), gbp(w["spend"]), e(str(w["clicks"]))]
        if with_enq:
            row += [e(str(w["enquiries"])), gbp(w["cpe"]) if w.get("cpe") is not None else e("no enquiries")]
        rows.append(row)
    gen = f'<p class="muted">Ads summary from {e(a["generated"])}.</p>' if a.get("generated") else ""
    return gen + (table(cols, rows) if rows else '<p class="muted">No weeks in the Ads summary yet.</p>')


def r_bank(b, data):
    if b is None:
        return '<p class="muted">not checked</p>'
    return (f'<div class="pair"><div><div class="muted">Cleared</div><div class="big">{gbp(b["cleared"])}</div></div>'
            f'<div><div class="muted">Effective</div><div class="big">{gbp(b["effective"])}</div></div></div>')


def r_books(v, data):
    if v is None:
        return '<p class="muted">Books not synced yet.</p>'
    t = v["totals"]
    out = [f'<div class="pair"><div><div class="muted">Receivables</div><div class="big">{gbp(t.get("receivables", 0))}</div></div>'
           f'<div><div class="muted">Overdue</div><div class="big">{gbp(t.get("overdue", 0))}</div></div>'
           + (f'<div><div class="muted">Unpaid bills</div><div class="big">{gbp(t.get("unpaid_bills", 0))}</div></div>'
              if v.get("bills_read", True) is not False else "")
           + '</div>']
    if v["drafts"]:
        out.append(f'<p>Drafts not yet sent: {", ".join(e(n) for n in v["drafts"])}</p>')
    if v["overdue"]:
        out.append(f'<p>Overdue: {", ".join(e(n) for n in v["overdue"])}</p>')
    s = v["season"]
    pct = f"{s['margin_pct']:.1f}%" if s["margin_pct"] is not None else "–"
    out.append(f'<p>Season margin from {day(s["start"].isoformat())}: fee {gbp(s["fee"])}, singer costs {gbp(s["costs"])}, '
               f'margin {gbp(s["margin"])} ({e(pct)}), {e(str(s["count"]))} booking{"" if s["count"] == 1 else "s"}.</p>')
    u = v["unlinked"]
    if u["count"]:
        out.append(f'<p>Unlinked singer invoices: {e(str(u["count"]))}, {gbp(u["total"])}.</p>')
    return "".join(out)


SECTIONS = [("Upcoming events", "upcoming", r_upcoming), ("Money", "money", r_money),
            ("Needs a hand check", "hand_check", r_hand), ("Singer invoices unpaid", "singers", r_singers),
            ("Pipeline", "pipeline", r_pipeline), ("Ads", "ads", r_ads), ("Bank balance", "bank", r_bank),
            ("Books", "books", r_books)]


def render(data):
    """The whole page from gather()'s dict. Pure: no files, no network."""
    parts = []
    for title, key, fn in SECTIONS:
        value = data.get(key)
        try:
            body = fail(value["failed"]) if failed(value) else fn(value, data)
        except Exception as ex:  # type name only: the message could carry private data
            body = fail(type(ex).__name__)
        parts.append(f'<section><h2>{e(title)}</h2>{body}</section>')
    return ("<!doctype html>\n<html lang=\"en-GB\"><head><meta charset=\"utf-8\">"
            "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            "<meta name=\"referrer\" content=\"no-referrer\"><meta name=\"robots\" content=\"noindex, nofollow\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<meta name=\"color-scheme\" content=\"light dark\">"
            f"<title>LCS dashboard</title><style>{CSS}</style></head><body><main>"
            f"<header><h1>LCS dashboard</h1><span class=\"gen\">Generated {e(str(data.get('generated', '')))} "
            "(Europe/London)</span></header>" + "".join(parts) + "</main></body></html>\n")


# ---------------------------------------------------------------- write


def write(page):
    """Atomically replace the dashboard: a mode-600 temp file in the same directory, then os.replace."""
    path = out_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(page)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write the owner's private dashboard to ~/lcs-private/dashboard.html.")
    ap.add_argument("--no-bank", action="store_true", help="don't read the Keychain token or call Starling")
    args = ap.parse_args(argv)
    today = lm.today()
    client = None
    if not args.no_bank:
        tok = lm.keychain_token()
        client = lm.StarlingReadOnly(tok) if tok else None
    path = write(render(gather(client, today)))
    print(f"dashboard written: {path}")


if __name__ == "__main__":
    main()
