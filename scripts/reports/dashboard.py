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
import singer_invoices as si  # noqa: E402

LONDON = ZoneInfo("Europe/London")
# URLError and HTTPError are OSErrors too; a non-JSON 200 body (an outage page) is a JSONDecodeError
BANK_DOWN = (lm.StarlingError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
             json.JSONDecodeError)
SEASON_START_MONTH = 9  # the pipeline season runs from 1 September
STATUS_ORDER = ["new", "quoted", "confirmed", "deposit paid", "done", "lost"]
CONFIRMED = {"confirmed", "deposit paid", "done"}
STATES = {  # payment state -> (words, tone)
    "PAID_IN_FULL": ("paid in full", "ok"), "CLOSED": ("paid in full (closed)", "ok"),
    "DEPOSIT_SEEN": ("deposit in", "ok"), "AWAITING_DEPOSIT": ("awaiting deposit", ""),
    "BALANCE_DUE": ("balance due", "warn"), "DEPOSIT_OVERDUE": ("deposit overdue", "bad"),
    "NOTED_PAID": ("noted paid", "warn"), "CHECK_PAYMENT": ("possible payment: check", "warn"),
    "CHECK_VALUE": ("unreadable value or date", "warn"), "PAST_UNMATCHED": ("past, unpaid", "bad"),
    "PAST_PART_PAID": ("past, part paid", "bad"), "PAYMENT_ON_CANCELLED": ("payment on a cancelled booking", "bad"),
    "PAYMENT_AFTER_CLOSE": ("payment after paid in full", "bad"),
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


def hand_check(assessments):
    return [{"ref": a["ref"], "state": a["state"], "label": mr.hand_check_label(a), "value": a.get("value") or 0.0,
             "received": a.get("received") or 0.0} for a in assessments if a["state"] in mr.HAND_CHECK]


def digits4(value):
    return re.sub(r"\D", "", str(value or ""))[-4:]


def payee_status(payee):
    """Whether Starling already knows the singer, without the payee's full name."""
    for prefix, label in (("existing: ", "existing payee"),
                          ("name matches payee ", "matches an existing payee, different bank details"),
                          ("probably existing: ", "probably an existing payee (no bank details on the invoice)")):
        if payee.startswith(prefix):
            return label
    return payee


def singers(rows):
    return [{"received": r.get("received", ""), "first_name": first_name(r.get("singer_name")),
             "amount": lm.money(r.get("amount_gbp")), "payee": payee_status(r.get("payee", "")),
             "bank_changed": r.get("bank_changed") == "yes", "ring_first": si.ring_first(r),
             "last4": digits4(r.get("bank_last4"))}
            for r in sorted(rows, key=lambda r: r.get("received") or "") if not r.get("paid_on")]


def enquiries():
    path = private_dir() / "enquiries.csv"
    return lm.read_csv(path) if path.exists() else None


def season_start(today):
    year = today.year if today.month >= SEASON_START_MONTH else today.year - 1
    return datetime.date(year, SEASON_START_MONTH, 1)


def status_of(r):
    return (r.get("status") or "").strip().lower() or "(none)"


def window(rows, label, since):
    picked = [r for r in rows if (r.get("first_seen") or "")[:10] >= since.isoformat()]
    counts = {}
    for r in picked:
        counts[status_of(r)] = counts.get(status_of(r), 0) + 1
    confirmed = sum(status_of(r) in CONFIRMED for r in picked)
    quoted = sum(status_of(r) in CONFIRMED or status_of(r) == "quoted" or lm.money(r.get("quoted_gbp")) > 0
                 for r in picked)
    return {"label": label, "counts": counts, "total": len(picked), "quoted": quoted, "confirmed": confirmed}


def pipeline(enq, today):
    if enq is None:
        return None
    start = season_start(today)
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
        data["hand_check"] = section(hand_check, assessments)
    data["singers"] = section(lambda: singers(lm.read_csv(si.STORE)))
    enq = section(enquiries)
    enq_ok = not (isinstance(enq, dict) and "failed" in enq)
    data["pipeline"] = section(pipeline, enq, today) if enq_ok else enq
    data["ads"] = section(ads, enq if enq_ok else None)
    data["bank"] = section(bank_balance, client)
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
        rate = f" ({round(100 * w['confirmed'] / w['quoted'])}%)" if w["quoted"] else ""
        out.append(f"<h3>{e(w['label'])}</h3><p>{e(str(w['total']))} enquiries: {status}</p>"
                   f"<p>Conversion: {e(str(w['confirmed']))} confirmed of {e(str(w['quoted']))} quoted{e(rate)}</p>")
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


SECTIONS = [("Upcoming events", "upcoming", r_upcoming), ("Money", "money", r_money),
            ("Needs a hand check", "hand_check", r_hand), ("Singer invoices unpaid", "singers", r_singers),
            ("Pipeline", "pipeline", r_pipeline), ("Ads", "ads", r_ads), ("Bank balance", "bank", r_bank)]


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
    today = datetime.datetime.now(LONDON).date()
    client = None
    if not args.no_bank:
        tok = lm.keychain_token()
        client = lm.StarlingReadOnly(tok) if tok else None
    path = write(render(gather(client, today)))
    print(f"dashboard written: {path}")


if __name__ == "__main__":
    main()
