# Automation Phase 1 (Money) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track money in and out automatically:
- a state for every client booking, with balance chasing and "payment received" drafts;
- a tracker for invoices from singers and organists, with payee checks and a changed-bank-details warning;
- a money line in the Monday report.

**Architecture:** One shared, read-only Starling client and the private-file helpers go in `scripts/bookings/lcs_money.py`. `check_payments.py` is refactored onto it and gains pure `assess()` states and `--json` output. A new `singer_invoices.py` handles money going out, and `money_report.py` formats the Monday section. The enquiry assistant (handover Appendix E) and the Monday review (Appendix A) call these scripts. Every email is a draft; the Zoho guard now also allows drafts from luca@almaconsort.com, for singer replies only.

**Tech Stack:**
- Python 3 (stdlib plus `pypdf`) in the repo's `.venv`.
- Starling API v2, GET only.
- Zoho Mail MCP, read tools plus drafts.
- Tests are stdlib-only scripts in the repo's style: `.venv/bin/python tests/test_x.py`.

**Spec:** [docs/superpowers/specs/2026-09-28-business-automation-design.md](../specs/2026-09-28-business-automation-design.md), Phase 1, features 1–5.

---

## Read this before starting

- **Never add a write call to Starling.** `StarlingReadOnly` exposes exactly `get`, `account`, `feed` and `payees`, and Task 1's test fails if anything else appears. Claude must not create payees or payments, whatever the token allows.
- **Never print a full sort code or account number.** Store a fingerprint plus the last four digits, and print only `••••1234`.
- **Private files only.** Everything personal goes in `~/lcs-private/` (mode 600), via `lcs_money.write_csv`. Tests point `LCS_PRIVATE_DIR` and `LCS_BOOKINGS_CSV` at a temp directory, and must never touch the real ledger.
- **Keep callers working.** The live scheduled tasks call `check_payments.py --apply`, `--reminded REF` and `--selftest`. All three must behave as today until Task 7 updates the prompts.
- **Branch and worktree.** Work in a worktree on a new branch from `origin/main`, e.g. `claude/automation-phase-1`. Run everything with the main checkout's venv: `PY=~/Documents/GitHub/londonchoralservice/.venv/bin/python`.

## File structure

| File | Responsibility |
|---|---|
| Create `scripts/bookings/lcs_money.py` | Starling read-only client, Keychain token, private CSV read/write, money parsing, bank fingerprints |
| Modify `scripts/bookings/check_payments.py` | Client payments: matching, `assess()` states, `--json`, `--kind` reminder marks, `collect()` and `received_since()` for the report |
| Create `scripts/bookings/singer_invoices.py` | Money out: read singer invoices, check payees, warn on bank changes, match paid, status and summary |
| Create `scripts/bookings/money_report.py` | Pure formatting of the Monday money lines |
| Modify `scripts/reports/weekly_review.py` | Section 10, Money |
| Modify `.claude/hooks/zoho_guard.py` | Allow drafts from luca@almaconsort.com as well as office@ |
| Modify `.claude/settings.json` | Allowlist the new commands |
| Modify `docs/HANDOVER-2026-09-27-ads-analytics.md` | Appendix E (assistant) and Appendix A (Monday review) steps |
| Modify `CLAUDE.md` | "Email and invoices" section |
| Create `tests/test_lcs_money.py`, `tests/test_check_payments.py`, `tests/test_singer_invoices.py`, `tests/test_money_report.py`, `tests/test_zoho_guard.py` | Tests |

Every test file ends with the repo's standard runner:

```python
if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
```

---

### Task 1: Shared read-only money module

**Files:**
- Create: `scripts/bookings/lcs_money.py`
- Test: `tests/test_lcs_money.py`

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for scripts/bookings/lcs_money.py. Stdlib only: .venv/bin/python tests/test_lcs_money.py"""
import datetime, io, json, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import lcs_money as m


class FakeOpener:
    """Stands in for urllib.request.urlopen and records every request."""
    def __init__(self, payload):
        self.payload, self.requests = payload, []

    def __call__(self, req, timeout=30):
        self.requests.append(req)
        body = self.payload(req.full_url) if callable(self.payload) else self.payload
        return io.BytesIO(json.dumps(body).encode())


ACCOUNTS = {"accounts": [{"accountUid": "a1", "defaultCategory": "c1"}]}


def test_fingerprint_ignores_formatting():
    a = m.bank_fingerprint("60-83-71", "24972792")
    assert a == m.bank_fingerprint("608371", "2497 2792")
    assert len(a) == 16


def test_fingerprint_pads_seven_digit_accounts():
    assert m.bank_fingerprint("60-83-71", "1234567") == m.bank_fingerprint("608371", "01234567")


def test_fingerprint_rejects_bad_input():
    assert m.bank_fingerprint("6083", "24972792") is None
    assert m.bank_fingerprint("60-83-71", "12") is None
    assert m.bank_fingerprint("", "") is None


def test_last4():
    assert m.last4("2497 2792") == "2792"
    assert m.last4("") == ""


def test_money_parses_pounds():
    assert m.money("£1,150.00") == 1150.0
    assert m.money("") == 0.0
    assert m.money(None) == 0.0
    assert m.money("n/a") == 0.0


def test_client_only_sends_get_with_bearer():
    fake = FakeOpener(ACCOUNTS)
    m.StarlingReadOnly("tok", opener=fake).account()
    assert fake.requests and all(r.get_method() == "GET" for r in fake.requests)
    assert fake.requests[0].headers["Authorization"] == "Bearer tok"


def test_client_has_no_write_methods():
    public = {n for n in dir(m.StarlingReadOnly) if not n.startswith("_")}
    assert public == {"get", "account", "feed", "payees"}, public


def test_feed_filters_direction_and_status():
    items = [{"direction": "IN", "status": "SETTLED"}, {"direction": "OUT", "status": "SETTLED"},
             {"direction": "IN", "status": "DECLINED"}]
    fake = FakeOpener(lambda url: ACCOUNTS if url.endswith("/accounts") else {"feedItems": items})
    got = m.StarlingReadOnly("tok", opener=fake).feed(datetime.date(2026, 9, 1), datetime.date(2026, 9, 2), "IN")
    assert got == [items[0]]
    assert "minTransactionTimestamp=2026-09-01T00:00:00.000Z" in fake.requests[-1].full_url


def test_payee_fingerprints():
    payees = [{"payeeName": "Laura T", "accounts": [{"bankIdentifier": "608371", "accountIdentifier": "24972792"}]},
              {"payeeName": "No UK account", "accounts": [{"bankIdentifier": "", "accountIdentifier": "GB00XX"}]}]
    fps = m.payee_fingerprints(payees)
    assert fps == {m.bank_fingerprint("60-83-71", "24972792"): "Laura T"}


def test_csv_round_trip_is_private():
    path = os.path.join(tempfile.mkdtemp(), "sub", "f.csv")
    m.write_csv(path, [{"a": "1", "b": "x"}], ["a", "b"])
    assert oct(os.stat(path).st_mode)[-3:] == "600"
    assert m.read_csv(path) == [{"a": "1", "b": "x"}]
    assert m.read_csv(path + ".missing") == []
```

Add the standard runner at the end of the file.

- [ ] **Step 2: Run the test to verify it fails**

Run: `$PY tests/test_lcs_money.py`
Expected: `ModuleNotFoundError: No module named 'lcs_money'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Shared, READ-ONLY money helpers for the bookings scripts.

- StarlingReadOnly: the only way these scripts talk to Starling. It sends GET
  requests and nothing else; no method here can move money, add payees or
  write to the bank (tests/test_lcs_money.py enforces the method list).
- The token lives in the owner's macOS Keychain (service lcs-starling-read)
  and is read at run time, never printed.
- Private files live in ~/lcs-private/ (override with LCS_PRIVATE_DIR), mode 600.
- Bank details are reduced to a fingerprint plus the last four digits.
"""

import csv
import hashlib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

API = "https://api.starlingbank.com"
KEYCHAIN_SERVICE = "lcs-starling-read"
PRIVATE = Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private"))
LEDGER = Path(os.environ.get("LCS_BOOKINGS_CSV", PRIVATE / "bookings.csv"))


def keychain_token():
    r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


class StarlingReadOnly:
    """GET-only Starling client. Add no other public methods."""

    def __init__(self, token, opener=urllib.request.urlopen):
        self._token = token
        self._open = opener

    def get(self, path):
        req = urllib.request.Request(API + path, method="GET",
                                     headers={"Authorization": f"Bearer {self._token}",
                                              "Accept": "application/json"})
        with self._open(req, timeout=30) as resp:
            return json.load(resp)

    def account(self):
        accounts = self.get("/api/v2/accounts").get("accounts", [])
        want = os.environ.get("LCS_STARLING_ACCOUNT_UID")
        for a in accounts:
            if not want or a.get("accountUid") == want:
                return a
        raise SystemExit("No matching Starling account (set LCS_STARLING_ACCOUNT_UID if there are several).")

    def feed(self, since, until, direction):
        """Settled-or-pending feed items between two dates, one direction ("IN" or "OUT")."""
        a = self.account()
        path = (f"/api/v2/feed/account/{a['accountUid']}/category/{a['defaultCategory']}/transactions-between"
                f"?minTransactionTimestamp={since.isoformat()}T00:00:00.000Z"
                f"&maxTransactionTimestamp={until.isoformat()}T00:00:00.000Z")
        items = self.get(path).get("feedItems", [])
        return [i for i in items if i.get("direction") == direction
                and i.get("status") not in ("DECLINED", "REVERSED", "REFUNDED")]

    def payees(self):
        return self.get("/api/v2/payees").get("payees", [])


def money(value):
    try:
        return float(str(value if value is not None else "0").replace("£", "").replace(",", "") or 0)
    except ValueError:
        return 0.0


def bank_fingerprint(sort_code, account_number):
    """16-hex fingerprint of a UK bank account, or None if the details aren't a sort code + account."""
    sc = re.sub(r"\D", "", sort_code or "")
    acc = re.sub(r"\D", "", account_number or "")
    if len(sc) != 6 or not 6 <= len(acc) <= 8:
        return None
    return hashlib.sha256(f"{sc}:{acc.zfill(8)}".encode()).hexdigest()[:16]


def last4(account_number):
    digits = re.sub(r"\D", "", account_number or "")
    return digits[-4:]


def payee_fingerprints(payees):
    """fingerprint -> payee name, for every UK account on every Starling payee."""
    out = {}
    for p in payees:
        for a in p.get("accounts", []):
            fp = bank_fingerprint(a.get("bankIdentifier"), a.get("accountIdentifier"))
            if fp:
                out[fp] = p.get("payeeName", "")
    return out


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, columns):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.chmod(path, 0o600)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `$PY tests/test_lcs_money.py`
Expected: every line `PASS …`, then `0 failure(s)`.

- [ ] **Step 5: Commit**

```bash
git add scripts/bookings/lcs_money.py tests/test_lcs_money.py
git commit -m "feat(bookings): shared read-only Starling client and private-file helpers"
```

---

### Task 2: Client payment states in `check_payments.py`

**Files:**
- Modify: `scripts/bookings/check_payments.py` (full rewrite below; behaviour is kept, and states and JSON are added)
- Test: `tests/test_check_payments.py`

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for scripts/bookings/check_payments.py. Stdlib only."""
import datetime, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import check_payments as cp

T = datetime.date(2026, 9, 28)


def row(ref, value, invoice, event, notes="", name="Ann Smith"):
    return {"booking_ref": ref, "value_gbp": str(value), "invoice_date": invoice, "event_date": event,
            "notes": notes, "client_name": name}


def pay(amount, when, ref="", who="Someone"):
    return {"direction": "IN", "amount": {"minorUnits": int(round(amount * 100))},
            "transactionTime": when + "T10:00:00Z", "reference": ref, "counterPartyName": who}


def test_match_by_reference():
    found = cp.match([row("2111", 650, "2026-08-22", "2026-11-21")], [pay(325, "2026-08-26", "INV 2111")], T)
    assert found["2111"] == [("2026-08-26", 325.0, "reference")]


def test_match_by_surname_and_deposit():
    found = cp.match([row("0810", 375, "2026-09-22", "2026-10-08")], [pay(187.5, "2026-09-24", "deposit", "MRS A SMITH")], T)
    assert found["0810"][0][2] == "name and amount"


def test_amount_only_needs_a_unique_amount():
    one = [row("A", 1150, "2026-09-01", "2026-10-10", name="X Y")]
    two = one + [row("B", 1150, "2026-09-02", "2026-10-11", name="P Q")]
    payment = [pay(1150, "2026-09-05", "wedding")]
    assert cp.match(one, payment, T)["A"][0][2] == "amount only"
    assert cp.match(two, payment, T) == {"A": [], "B": []}


def test_past_event_is_never_overdue():
    assert cp.assess(row("2509", 3225, "2026-09-12", "2026-09-21"), [], T)["state"] == "PAST_UNMATCHED"


def test_noted_paid_is_not_chased():
    assert cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "paid 14 Sep"), [], T)["state"] == "NOTED_PAID"


def test_deposit_overdue_for_future_event():
    a = cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced"), [], T)
    assert a["state"] == "DEPOSIT_OVERDUE" and a["deposit_due"] == "2026-09-08"


def test_awaiting_deposit_inside_seven_days():
    assert cp.assess(row("X", 500, "2026-09-25", "2026-10-30", "PENDING: invoiced"), [], T)["state"] == "AWAITING_DEPOSIT"


def test_balance_due_from_three_days_before():
    paid = [("2026-08-26", 325.0, "reference")]
    assert cp.assess(row("2111", 650, "2026-08-22", "2026-10-01"), paid, T)["state"] == "BALANCE_DUE"
    assert cp.assess(row("2111", 650, "2026-08-22", "2026-11-21"), paid, T)["state"] == "DEPOSIT_SEEN"


def test_paid_in_full():
    paid = [("2026-08-26", 325.0, "reference"), ("2026-09-20", 325.0, "reference")]
    a = cp.assess(row("2111", 650, "2026-08-22", "2026-11-21"), paid, T)
    assert a["state"] == "PAID_IN_FULL" and a["balance"] == 0


def test_just_received_only_from_pending():
    paid = [("2026-09-27", 325.0, "reference")]
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "PENDING: invoiced"), paid, T)["just_received"] is True
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "deposit seen 2026-09-27 (Starling)"), paid, T)["just_received"] is False


def test_reminder_marks_are_distinct():
    a = cp.assess(row("X", 650, "2026-08-22", "2026-10-01", "deposit seen x; balance reminder drafted 2026-09-28"),
                  [("2026-08-26", 325.0, "reference")], T)
    assert a["reminded"] == {"deposit": False, "balance": True, "receipt": False}
    b = cp.assess(row("X", 650, "2026-09-01", "2026-10-30", "PENDING: x; reminder drafted 2026-09-20"), [], T)
    assert b["reminded"]["deposit"] is True and b["reminded"]["balance"] is False


def test_updated_notes_clears_pending_and_marks_full():
    paid = [("2026-08-26", 325.0, "reference"), ("2026-09-20", 325.0, "reference")]
    r = row("X", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced; from quote")
    a = cp.assess(r, paid, T)
    assert cp.updated_notes(r["notes"], a, paid) == "deposit seen 2026-08-26 (Starling); from quote; paid in full 2026-09-20"


def test_describe_never_names_the_client():
    a = cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced", name="Secret Person"), [], T)
    assert "Secret" not in cp.describe(a) and "DEPOSIT OVERDUE since 2026-09-08" in cp.describe(a)
```

Add the standard runner.

- [ ] **Step 2: Run the test to verify it fails**

Run: `$PY tests/test_check_payments.py`
Expected: `AttributeError: module 'check_payments' has no attribute 'assess'`, or a `TypeError` from `match()` taking 2 arguments.

- [ ] **Step 3: Replace `scripts/bookings/check_payments.py` with this implementation**

```python
#!/usr/bin/env python3
"""Confirm deposits and balances for London Choral Service bookings against the
Alma Consort Starling account, READ-ONLY (see lcs_money.StarlingReadOnly).

    .venv/bin/python scripts/bookings/check_payments.py                  # report
    .venv/bin/python scripts/bookings/check_payments.py --apply          # also update ledger notes
    .venv/bin/python scripts/bookings/check_payments.py --apply --json   # machine-readable, for the assistant
    .venv/bin/python scripts/bookings/check_payments.py --reminded 2111 [--kind deposit|balance|receipt]
    .venv/bin/python scripts/bookings/check_payments.py --selftest       # token, account and permissions

Matching: an incoming payment belongs to a booking when its reference contains
the invoice number; failing that, when its amount is the deposit or full fee and
the payer's name contains the client's surname; failing that, when its amount is
exactly the deposit or fee of one open booking and of no other, inside that
booking's invoice-to-event window.

States (assess): PAID_IN_FULL, DEPOSIT_SEEN, BALANCE_DUE (from 3 days before the
event), AWAITING_DEPOSIT (first 7 days), DEPOSIT_OVERDUE (future events only),
NOTED_PAID (ledger notes say paid), PAST_UNMATCHED / PAST_PART_PAID (past
events: reported, never chased). Output shows invoice numbers and amounts only.
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402

LEDGER = lm.LEDGER
MARK_TEXT = {"deposit": "reminder drafted", "balance": "balance reminder drafted", "receipt": "receipt drafted"}


def money(row):
    return lm.money(row.get("value_gbp"))


def window(r, today):
    start = datetime.date.fromisoformat(r["invoice_date"][:10]) - datetime.timedelta(days=3)
    end = (datetime.date.fromisoformat(r["event_date"][:10]) if r.get("event_date") else today) + datetime.timedelta(days=14)
    return start, end


def match(rows, items, today):
    """booking_ref -> list of (date, amount, how)."""
    found = {r["booking_ref"]: [] for r in rows}
    for it in items:
        amount = (it.get("amount") or {}).get("minorUnits", 0) / 100
        when = (it.get("transactionTime") or "")[:10]
        ref_text = re.sub(r"[^A-Z0-9]", " ", (it.get("reference") or "").upper())
        payer = (it.get("counterPartyName") or "").lower()
        hit = None
        for r in rows:
            ref = r["booking_ref"].upper()
            if re.search(rf"(?:^|\s)(?:INV\s*)?{re.escape(ref)}(?:\s|$)", ref_text) or f"INV{ref}" in ref_text.replace(" ", ""):
                hit = (r["booking_ref"], "reference")
                break
        if not hit:
            for r in rows:
                surname = (r.get("client_name") or "").strip().split(" ")[-1].lower()
                v = money(r)
                if surname and len(surname) > 2 and surname in payer and any(abs(amount - x) < 0.01 for x in (v, v / 2)):
                    hit = (r["booking_ref"], "name and amount")
                    break
        if not hit and when:
            day = datetime.date.fromisoformat(when)
            fits = [r for r in rows if any(abs(amount - x) < 0.01 for x in (money(r), money(r) / 2))
                    and window(r, today)[0] <= day <= window(r, today)[1]]
            same_value = [r for r in rows if abs(money(r) - money(fits[0])) < 0.01] if len(fits) == 1 else []
            if len(fits) == 1 and len(same_value) == 1:
                hit = (fits[0]["booking_ref"], "amount only")
        if hit:
            found[hit[0]].append((when, amount, hit[1]))
    return found


def assess(r, paid, today):
    value, notes = money(r), r.get("notes") or ""
    total = round(sum(a for _, a, _ in paid), 2)
    first = min((d for d, _, _ in paid), default=None)
    deposit_due = datetime.date.fromisoformat(r["invoice_date"][:10]) + datetime.timedelta(days=7)
    event = datetime.date.fromisoformat(r["event_date"][:10]) if r.get("event_date") else None
    pending = notes.upper().startswith("PENDING")
    manual = bool(re.search(r"\b(paid|deposit seen)\b", notes, re.I)) and not pending
    upcoming = event is None or event >= today
    if value > 0 and total + 0.01 >= value:
        state = "PAID_IN_FULL"
    elif not upcoming:
        state = "PAST_PART_PAID" if paid else ("NOTED_PAID" if manual else "PAST_UNMATCHED")
    elif not paid:
        state = ("NOTED_PAID" if manual else "DEPOSIT_OVERDUE") if today > deposit_due else "AWAITING_DEPOSIT"
    elif event and today >= event - datetime.timedelta(days=3):
        state = "BALANCE_DUE"
    else:
        state = "DEPOSIT_SEEN"
    return {
        "ref": r["booking_ref"], "state": state, "received": total, "value": value,
        "balance": round(max(value - total, 0), 2), "first": first, "how": paid[0][2] if paid else "",
        "event_date": event.isoformat() if event else None, "deposit_due": deposit_due.isoformat(),
        "reminded": {"deposit": bool(re.search(r"(?<!balance )reminder drafted", notes)),
                     "balance": "balance reminder drafted" in notes,
                     "receipt": "receipt drafted" in notes},
        "just_received": bool(paid) and pending,
    }


def describe(a):
    line = f"{a['ref']}: £{a['received']:,.2f} of £{a['value']:,.2f} received"
    if a["first"]:
        line += f" (first {a['first']}, matched by {a['how']})"
    return line + {
        "PAID_IN_FULL": " · PAID IN FULL",
        "DEPOSIT_SEEN": "",
        "AWAITING_DEPOSIT": " · awaiting deposit (not yet due)",
        "BALANCE_DUE": f" · BALANCE £{a['balance']:,.2f} DUE" + (" (reminder already drafted)" if a["reminded"]["balance"] else ""),
        "DEPOSIT_OVERDUE": f" · DEPOSIT OVERDUE since {a['deposit_due']}" + (" (reminder already drafted)" if a["reminded"]["deposit"] else ""),
        "NOTED_PAID": " · no matching payment in the bank feed, but the ledger notes say it was paid (check by hand)",
        "PAST_UNMATCHED": " · event has passed; no matching payment in the bank feed (check by hand; never chase automatically)",
        "PAST_PART_PAID": " · event has passed; part paid (check by hand; never chase automatically)",
    }[a["state"]]


def updated_notes(notes, a, paid):
    new = notes
    if paid and new.upper().startswith("PENDING"):
        rest = new.split(";", 1)[1].strip() if ";" in new else ""
        new = f"deposit seen {a['first']} (Starling)" + (f"; {rest}" if rest else "")
    if a["state"] == "PAID_IN_FULL" and not re.search(r"paid in full \d{4}-\d{2}-\d{2}", new):
        new += f"; paid in full {max(d for d, _, _ in paid)}"
    return new


def open_rows(rows):
    return [r for r in rows if not (r.get("notes") or "").upper().startswith("CANCELLED")
            and not re.search(r"paid in full \d{4}-\d{2}-\d{2}", r.get("notes") or "")]


def collect(client, rows, today):
    """[(row, paid, assessment)] for every open booking."""
    rows = open_rows(rows)
    if not rows:
        return []
    since = min(datetime.date.fromisoformat(r["invoice_date"][:10]) for r in rows) - datetime.timedelta(days=3)
    found = match(rows, client.feed(since, today + datetime.timedelta(days=1), "IN"), today)
    return [(r, found[r["booking_ref"]], assess(r, found[r["booking_ref"]], today)) for r in rows]


def received_since(client, rows, since, today):
    """[(booking_ref, date, amount)] for client payments since a date (any non-cancelled booking)."""
    live = [r for r in rows if not (r.get("notes") or "").upper().startswith("CANCELLED")]
    if not live:
        return []
    found = match(live, client.feed(since, today + datetime.timedelta(days=1), "IN"), today)
    return [(ref, d, a) for ref, hits in found.items() for d, a, _ in hits if d >= since.isoformat()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--reminded", metavar="REF")
    ap.add_argument("--kind", choices=sorted(MARK_TEXT), default="deposit")
    args = ap.parse_args()
    today = datetime.date.today()
    rows = lm.read_csv(LEDGER)
    cols = list(rows[0].keys()) if rows else []

    if args.reminded:
        for r in rows:
            if r["booking_ref"] == args.reminded:
                r["notes"] = (r.get("notes") or "") + f"; {MARK_TEXT[args.kind]} {today}"
                break
        else:
            raise SystemExit(f"no booking {args.reminded}")
        lm.write_csv(LEDGER, rows, cols)
        print(f"{args.reminded}: {MARK_TEXT[args.kind]} noted")
        return

    tok = lm.keychain_token()
    if not tok:
        print(f"No Starling token in the Keychain (service {lm.KEYCHAIN_SERVICE}); payment check skipped.")
        return
    client = lm.StarlingReadOnly(tok)
    if args.selftest:
        try:
            scopes = sorted(client.get("/api/v2/identity/token").get("scopes", []))
        except Exception as e:  # identity endpoint unavailable: still test the account call
            scopes = [f"(could not read scopes: {type(e).__name__})"]
        acct = client.account()
        print("Starling token works; account found (uid ends …" + acct["accountUid"][-4:] + ").")
        print("Token permissions: " + ", ".join(scopes))
        risky = [x for x in scopes if not x.startswith("(") and not x.endswith(":read")]
        if risky:
            print("WARNING: this token can do more than read: " + ", ".join(risky)
                  + ". Revoke it in the Starling developer portal and create one with only account-list:read and transaction:read.")
        return

    results = collect(client, rows, today)
    if not results:
        print("[]" if args.json else "No open bookings to check.")
        return
    changed = False
    for r, paid, a in results:
        if not args.json:
            print(describe(a))
        if args.apply:
            new = updated_notes(r.get("notes") or "", a, paid)
            if new != (r.get("notes") or ""):
                r["notes"], changed = new, True
    if args.json:
        print(json.dumps([a for _, _, a in results]))
    if args.apply and changed:
        lm.write_csv(LEDGER, rows, cols)
        if not args.json:
            print("Ledger notes updated.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY tests/test_check_payments.py && $PY tests/test_lcs_money.py`
Expected: every line PASS in both, and `0 failure(s)` twice.

- [ ] **Step 5: Check it against the live ledger (read-only report)**

Run: `cd ~/Documents/GitHub/londonchoralservice && $PY <worktree>/scripts/bookings/check_payments.py`
Expected: the same bookings as before the refactor. 2408 now ends "· event has passed; part paid (check by hand…)" (or the NOTED_PAID line if its payments fall outside the feed window), and 2111 shows a deposit seen with no flag. No names appear.

- [ ] **Step 6: Commit**

```bash
git add scripts/bookings/check_payments.py tests/test_check_payments.py
git commit -m "feat(bookings): payment states, --json and reminder kinds on the shared client"
```

---

### Task 3: Singer invoice extraction (pure functions)

**Files:**
- Create: `scripts/bookings/singer_invoices.py` (this task: constants, `extract`, `surname`, `assess_new`, `match_paid`, `summary`)
- Test: `tests/test_singer_invoices.py`

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for scripts/bookings/singer_invoices.py. Stdlib only. Uses a temp private dir."""
import datetime, os, sys, tempfile

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import lcs_money as lm
import singer_invoices as si

LABELLED = """INVOICE
Invoice No: 1020
Date: 25/09/2026
To: Alma Consort Ltd
Funeral 21 September   £100.00
Total due £100.00
Account name: B Fenwick
Sort code: 12-34-56
Account number: 12345678
"""
TERSE = """Invoice INV-0107
Wedding 19 Sep     £150
Travel             £50
Subtotal £200.00
TOTAL £200.00
Sort Code 123456 Acc No 8765 4321
"""
NO_BANK = """Invoice 20260309-001
Balance due: £1,129.15
Thanks!"""


def test_extract_labelled_invoice():
    assert si.extract(LABELLED) == {"amount": 100.0, "invoice_ref": "1020", "sort_code": "123456", "account_number": "12345678"}


def test_extract_terse_invoice():
    e = si.extract(TERSE)
    assert (e["amount"], e["invoice_ref"], e["sort_code"], e["account_number"]) == (200.0, "INV-0107", "123456", "87654321")


def test_extract_without_bank_details():
    e = si.extract(NO_BANK)
    assert (e["amount"], e["invoice_ref"], e["sort_code"], e["account_number"]) == (1129.15, "20260309-001", "", "")


def test_extract_falls_back_to_largest_pound_figure():
    assert si.extract("Fee £80\nTravel £20\nPlease pay £100")["amount"] == 100.0


def inv(sort="123456", acc="12345678", amount=100.0):
    return {"amount": amount, "invoice_ref": "1", "sort_code": sort, "account_number": acc}


def test_new_singer_needs_a_payee():
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], {}, [])
    assert a["payee"] == "NEW: add as a payee in the Starling app" and a["bank_changed"] == "no"
    assert a["bank_last4"] == "5678" and "12345678" not in str(a)


def test_existing_payee_by_fingerprint():
    fps = {lm.bank_fingerprint("123456", "12345678"): "Ben W"}
    assert si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], fps, ["Ben W"])["payee"] == "existing: Ben W"


def test_changed_bank_details_warn():
    history = [{"singer_email": "b@x.com", "bank_fp": lm.bank_fingerprint("123456", "11112222"), "bank_last4": "2222"}]
    a = si.assess_new(inv(), "B@X.com", "Ben Fenwick", history, {}, [])
    assert a["bank_changed"] == "yes" and any("BANK DETAILS CHANGED" in w and "••••2222" in w for w in a["warnings"])


def test_payee_name_with_different_details_warns():
    fps = {lm.bank_fingerprint("123456", "99990000"): "Ben Fenwick"}
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], fps, ["Ben Fenwick"])
    assert a["bank_changed"] == "yes" and "different bank details" in a["payee"]


def test_no_bank_details_and_no_token():
    a = si.assess_new(inv("", ""), "b@x.com", "Ben Fenwick", [], None, [])
    assert a["payee"] == "unknown (no Starling token)" and "no bank details found on the invoice" in a["warnings"]


def out(amount, when, who):
    return {"direction": "OUT", "amount": {"minorUnits": int(round(amount * 100))},
            "transactionTime": when + "T10:00:00Z", "counterPartyName": who}


def unpaid(mid, name, amount, received, payee="NEW: add as a payee in the Starling app"):
    return {"message_id": mid, "singer_name": name, "amount_gbp": f"{amount:.2f}", "received": received,
            "payee": payee, "paid_on": "", "bank_changed": "no"}


def test_match_paid_by_amount_and_surname():
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-19")]
    assert si.match_paid(rows, [out(200, "2026-09-19", "LAURA PENHALLOW")]) == {"m1": ("2026-09-19", 200.0)}


def test_match_paid_uses_payee_name():
    rows = [unpaid("m1", "Maddy Kessell", 160, "2026-09-01", payee="existing: M M Kessell")]
    assert si.match_paid(rows, [out(160, "2026-09-02", "M M KESSELL")]) == {"m1": ("2026-09-02", 160.0)}


def test_match_paid_rejects_wrong_amount_early_date_and_double_use():
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-19"), unpaid("m2", "Laura Penhallow", 200, "2026-09-20")]
    assert si.match_paid(rows, [out(150, "2026-09-21", "LAURA PENHALLOW")]) == {}
    assert si.match_paid(rows[:1], [out(200, "2026-09-10", "LAURA PENHALLOW")]) == {}
    assert si.match_paid(rows, [out(200, "2026-09-21", "LAURA PENHALLOW")]) == {"m1": ("2026-09-21", 200.0)}


def test_summary_counts():
    rows = [dict(unpaid("m1", "A B", 100, "2026-09-20"), bank_changed="yes"),
            dict(unpaid("m2", "C D", 50, "2026-09-26")),
            dict(unpaid("m3", "E F", 70, "2026-09-01"), paid_on="2026-09-02")]
    assert si.summary(rows, datetime.date(2026, 9, 28)) == {"unpaid": 2, "unpaid_total": 150.0, "oldest_days": 8, "bank_changed": 1}
```

Add the standard runner.

- [ ] **Step 2: Run the test to verify it fails**

Run: `$PY tests/test_singer_invoices.py`
Expected: `ModuleNotFoundError: No module named 'singer_invoices'`

- [ ] **Step 3: Write the pure functions** (the top of the new file; Task 4 adds the commands)

```python
#!/usr/bin/env python3
"""Track invoices from singers and organists (money OUT), READ-ONLY against
Starling. Records live in ~/lcs-private/singer-invoices.csv (mode 600).

    singer_invoices.py scan <saved message> --message-id ID --received YYYY-MM-DD --sender-email E --sender-name 'N'
    singer_invoices.py paid [--apply]      # match OUT payments; prints NEWLY PAID <message id>
    singer_invoices.py status              # unpaid invoices and totals
    singer_invoices.py thanked <message id>  # note that the "Paid!" reply was drafted

Bank details are stored as a fingerprint plus the last four digits, and only
"••••1234" is ever printed. This script never creates payees or payments: a new
singer is flagged for the owner to add in the Starling app, where Confirmation
of Payee runs. Changed bank details raise a warning to ring before paying.
"""

import argparse
import datetime
import email
import io
import re
import sys
from email import policy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402

STORE = lm.PRIVATE / "singer-invoices.csv"
COLUMNS = ["message_id", "received", "singer_name", "singer_email", "invoice_ref", "amount_gbp",
           "bank_fp", "bank_last4", "payee", "bank_changed", "paid_on", "paid_amount", "notes"]
NEW_PAYEE = "NEW: add as a payee in the Starling app"

AMOUNT = r"(\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+(?:\.\d{2})?)"
SORT = re.compile(r"sort[\s\-]*code\W{0,5}(\d{2})\W?(\d{2})\W?(\d{2})(?!\d)", re.I)
ACCOUNT = re.compile(r"(?:account|acc|a/c)[\s\.]*(?:no|number|num|#)?\.?\W{0,5}(\d(?:\s?\d){7})(?!\d)", re.I)
TOTAL = re.compile(r"(?<![A-Za-z])(?:total\s+due|amount\s+due|balance\s+due|total\s+amount|grand\s+total|total)\b"
                   r"[^£\d\n]{0,15}£?\s*" + AMOUNT, re.I)
POUNDS = re.compile(r"£\s*" + AMOUNT)
REF = re.compile(r"(?:invoice|inv)\s*(?:no\.?|number|#|ref(?:erence)?)?\s*[:#\-]?\s*([A-Z]{0,5}[-/]?\d[\w\-/]{0,15})", re.I)


def extract(text):
    sort, acc, ref = SORT.search(text), ACCOUNT.search(text), REF.search(text)
    totals = TOTAL.findall(text)
    amount = lm.money(totals[-1]) if totals else max((lm.money(x) for x in POUNDS.findall(text)), default=0.0)
    return {"amount": round(amount, 2), "invoice_ref": ref.group(1) if ref else "",
            "sort_code": "".join(sort.groups()) if sort else "",
            "account_number": re.sub(r"\s", "", acc.group(1)) if acc else ""}


def surname(name):
    parts = re.findall(r"[a-z]+", (name or "").lower())
    return parts[-1] if parts else ""


def assess_new(inv, sender_email, sender_name, history, payee_fps, payee_names):
    """Payee status and warnings for a new invoice. payee_fps None = no Starling token."""
    fp = lm.bank_fingerprint(inv["sort_code"], inv["account_number"])
    previous = [r for r in history if r.get("singer_email", "").lower() == sender_email.lower() and r.get("bank_fp")]
    warnings, changed = [], False
    if fp and previous and previous[-1]["bank_fp"] != fp:
        changed = True
        warnings.append(f"BANK DETAILS CHANGED since their last invoice (was ••••{previous[-1]['bank_last4']}, "
                        f"now ••••{lm.last4(inv['account_number'])}): ring them before paying")
    if payee_fps is None:
        payee = "unknown (no Starling token)"
    elif fp and fp in payee_fps:
        payee = f"existing: {payee_fps[fp]}"
    else:
        sn = surname(sender_name)
        by_name = [n for n in payee_names if sn and sn in n.lower()]
        if by_name and fp:
            payee = f"name matches payee {by_name[0]} but with different bank details"
            changed = True
            warnings.append(f"Starling payee '{by_name[0]}' has different bank details from this invoice: ring them before paying")
        elif by_name:
            payee = f"probably existing: {by_name[0]} (no bank details on the invoice)"
        else:
            payee = NEW_PAYEE
    if not fp:
        warnings.append("no bank details found on the invoice")
    return {"bank_fp": fp or "", "bank_last4": lm.last4(inv["account_number"]) if fp else "",
            "payee": payee, "bank_changed": "yes" if changed else "no", "warnings": warnings}


def match_paid(unpaid, out_items):
    """{message_id: (date, amount)} for OUT payments that settle an unpaid invoice (each payment used once)."""
    hits, used = {}, set()
    for r in sorted(unpaid, key=lambda r: r["received"]):
        amount = lm.money(r["amount_gbp"])
        names = {surname(r["singer_name"])}
        if r["payee"].startswith("existing: "):
            names.add(surname(r["payee"][len("existing: "):]))
        names.discard("")
        for i, it in enumerate(out_items):
            if i in used:
                continue
            paid = (it.get("amount") or {}).get("minorUnits", 0) / 100
            when = (it.get("transactionTime") or "")[:10]
            who = (it.get("counterPartyName") or "").lower()
            if abs(paid - amount) < 0.01 and when >= r["received"][:10] and any(n in who for n in names):
                hits[r["message_id"]] = (when, paid)
                used.add(i)
                break
    return hits


def summary(rows, today):
    unpaid = [r for r in rows if not r.get("paid_on")]
    ages = [(today - datetime.date.fromisoformat(r["received"][:10])).days for r in unpaid]
    return {"unpaid": len(unpaid), "unpaid_total": round(sum(lm.money(r["amount_gbp"]) for r in unpaid), 2),
            "oldest_days": max(ages, default=0), "bank_changed": sum(1 for r in unpaid if r.get("bank_changed") == "yes")}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `$PY tests/test_singer_invoices.py`
Expected: every line PASS, then `0 failure(s)`. If an `extract` case fails, fix the regex, not the test: the three samples mirror the real invoice formats seen in the inbox.

- [ ] **Step 5: Commit**

```bash
git add scripts/bookings/singer_invoices.py tests/test_singer_invoices.py
git commit -m "feat(bookings): read singer invoices, payee check and changed-bank-details warning"
```

---

### Task 4: Singer invoice commands (scan, paid, status, thanked)

**Files:**
- Modify: `scripts/bookings/singer_invoices.py` (append the code below)
- Test: `tests/test_singer_invoices.py` (append)

- [ ] **Step 1: Append failing tests**

```python
class FakeClient:
    def __init__(self, payees=(), out=()):
        self._payees, self._out = list(payees), list(out)

    def payees(self):
        return self._payees

    def feed(self, since, until, direction):
        assert direction == "OUT"
        return self._out


def eml(body, sender="Ben Fenwick <ben@example.com>"):
    path = os.path.join(TMP, "msg.eml")
    with open(path, "w") as f:
        f.write(f"From: {sender}\nSubject: Invoice\nContent-Type: text/plain; charset=utf-8\n\n{body}")
    return path


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_store_lifecycle():
    """scan -> repeat scan -> paid --apply -> thanked, in order (one test: the runner sorts by name)."""
    if si.STORE.exists():
        si.STORE.unlink()
    a = Args(file=eml(LABELLED), message_id="m1", received="2026-09-25", sender_email="ben@example.com", sender_name="Ben Fenwick")
    si.cmd_scan(a, FakeClient())
    rows = lm.read_csv(si.STORE)
    assert len(rows) == 1 and rows[0]["amount_gbp"] == "100.00" and rows[0]["payee"] == si.NEW_PAYEE
    assert "12345678" not in si.STORE.read_text() and rows[0]["bank_last4"] == "5678"
    assert oct(si.STORE.stat().st_mode)[-3:] == "600"
    si.cmd_scan(a, FakeClient())
    assert len(lm.read_csv(si.STORE)) == 1

    si.cmd_paid(Args(apply=True), FakeClient(out=[{"direction": "OUT", "amount": {"minorUnits": 10000},
                                                   "transactionTime": "2026-09-26T09:00:00Z", "counterPartyName": "BEN FENWICK"}]))
    row = lm.read_csv(si.STORE)[0]
    assert (row["paid_on"], row["paid_amount"]) == ("2026-09-26", "100.00")

    si.cmd_thanked(Args(message_id="m1"))
    assert "paid reply drafted" in lm.read_csv(si.STORE)[0]["notes"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `$PY tests/test_singer_invoices.py`
Expected: `FAIL test_store_lifecycle` with `module 'singer_invoices' has no attribute 'cmd_scan'` (raised as AttributeError; the runner only catches AssertionError, so it shows as a traceback).

- [ ] **Step 3: Append the implementation to `singer_invoices.py`**

```python
def message_texts(path):
    """[(label, text)] for every PDF attachment in a saved message, then its body."""
    from invoice_text import raw_message
    from pypdf import PdfReader
    msg = email.message_from_string(raw_message(path), policy=policy.default)
    out = []
    for part in msg.walk():
        name = part.get_filename() or ""
        if name.lower().endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(part.get_payload(decode=True) or b""))
                out.append((name, "\n".join(p.extract_text() or "" for p in reader.pages)))
            except Exception:
                out.append((name, ""))
    body = msg.get_body(preferencelist=("plain", "html"))
    if body is not None:
        out.append(("email body", re.sub(r"<[^>]+>", " ", body.get_content())))
    return out


def read_invoice(path):
    found = {"amount": 0.0, "invoice_ref": "", "sort_code": "", "account_number": ""}
    for _, text in message_texts(path):
        e = extract(text)
        if not found["amount"] and e["amount"]:
            found.update(amount=e["amount"], invoice_ref=e["invoice_ref"])
        if not found["sort_code"] and e["sort_code"] and e["account_number"]:
            found.update(sort_code=e["sort_code"], account_number=e["account_number"])
    return found


def first_name(name):
    return (name or "?").split()[0]


def cmd_scan(args, client):
    rows = lm.read_csv(STORE)
    if any(r["message_id"] == args.message_id for r in rows):
        print(f"already recorded: {args.message_id}")
        return
    inv = read_invoice(args.file)
    payees = client.payees() if client else None
    fps = lm.payee_fingerprints(payees) if payees is not None else None
    names = [p.get("payeeName", "") for p in payees] if payees is not None else []
    a = assess_new(inv, args.sender_email, args.sender_name, rows, fps, names)
    rows.append({"message_id": args.message_id, "received": args.received, "singer_name": args.sender_name,
                 "singer_email": args.sender_email.lower(), "invoice_ref": inv["invoice_ref"],
                 "amount_gbp": f"{inv['amount']:.2f}", "bank_fp": a["bank_fp"], "bank_last4": a["bank_last4"],
                 "payee": a["payee"], "bank_changed": a["bank_changed"], "paid_on": "", "paid_amount": "",
                 "notes": "; ".join(a["warnings"])})
    lm.write_csv(STORE, rows, COLUMNS)
    print(f"{first_name(args.sender_name)}: £{inv['amount']:,.2f} (ref {inv['invoice_ref'] or '?'}) · payee {a['payee']}"
          + (f" · bank ••••{a['bank_last4']}" if a["bank_last4"] else ""))
    for w in a["warnings"]:
        print(f"   ! {w}")


def cmd_paid(args, client):
    rows = lm.read_csv(STORE)
    unpaid = [r for r in rows if not r["paid_on"]]
    if not unpaid:
        print("No unpaid singer invoices.")
        return
    if not client:
        print("No Starling token; paid check skipped.")
        return
    today = datetime.date.today()
    since = min(datetime.date.fromisoformat(r["received"][:10]) for r in unpaid) - datetime.timedelta(days=1)
    hits = match_paid(unpaid, client.feed(since, today + datetime.timedelta(days=1), "OUT"))
    for r in rows:
        if r["message_id"] in hits:
            when, amount = hits[r["message_id"]]
            print(f"NEWLY PAID {r['message_id']}: {first_name(r['singer_name'])} £{amount:,.2f} on {when}")
            if args.apply:
                r["paid_on"], r["paid_amount"] = when, f"{amount:.2f}"
    if not hits:
        print("No new payments to singers matched.")
    elif args.apply:
        lm.write_csv(STORE, rows, COLUMNS)
        print("Singer invoice store updated.")


def cmd_status(args, client=None):
    rows = lm.read_csv(STORE)
    today = datetime.date.today()
    for r in rows:
        if not r["paid_on"]:
            print(f"{r['received']} {first_name(r['singer_name'])} £{lm.money(r['amount_gbp']):,.2f} "
                  f"(ref {r['invoice_ref'] or '?'}) · payee {r['payee']}"
                  + (" · BANK DETAILS CHANGED: ring before paying" if r["bank_changed"] == "yes" else ""))
    s = summary(rows, today)
    print(f"{s['unpaid']} unpaid, £{s['unpaid_total']:,.2f}, oldest {s['oldest_days']} days"
          + (f", {s['bank_changed']} with changed bank details" if s["bank_changed"] else ""))


def cmd_thanked(args, client=None):
    rows = lm.read_csv(STORE)
    for r in rows:
        if r["message_id"] == args.message_id:
            r["notes"] = (r["notes"] + "; " if r["notes"] else "") + f"paid reply drafted {datetime.date.today()}"
            lm.write_csv(STORE, rows, COLUMNS)
            print(f"{args.message_id}: paid reply noted")
            return
    raise SystemExit(f"no invoice {args.message_id}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("file")
    s.add_argument("--message-id", required=True)
    s.add_argument("--received", required=True)
    s.add_argument("--sender-email", required=True)
    s.add_argument("--sender-name", required=True)
    p = sub.add_parser("paid")
    p.add_argument("--apply", action="store_true")
    sub.add_parser("status")
    t = sub.add_parser("thanked")
    t.add_argument("message_id")
    args = ap.parse_args()
    tok = lm.keychain_token() if args.cmd in ("scan", "paid") else None
    client = lm.StarlingReadOnly(tok) if tok else None
    {"scan": cmd_scan, "paid": cmd_paid, "status": cmd_status, "thanked": cmd_thanked}[args.cmd](args, client)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY tests/test_singer_invoices.py`
Expected: every line PASS, then `0 failure(s)`.

- [ ] **Step 5: Commit**

```bash
git add scripts/bookings/singer_invoices.py tests/test_singer_invoices.py
git commit -m "feat(bookings): singer invoice scan, paid, status and thanked commands"
```

---

### Task 5: Zoho guard allows drafts from luca@almaconsort.com

**Files:**
- Modify: `.claude/hooks/zoho_guard.py`
- Test: `tests/test_zoho_guard.py`

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for .claude/hooks/zoho_guard.py (PreToolUse). Stdlib only."""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, ".claude", "hooks", "zoho_guard.py")


def decide(tool, body=None):
    event = {"tool_name": f"mcp__zoho-mail__ZohoMail_{tool}", "tool_input": {"body": body or {}}}
    out = subprocess.run([sys.executable, GUARD], input=json.dumps(event), capture_output=True, text=True).stdout
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else "allow"


def draft(frm):
    return {"mode": "draft", "fromAddress": frm, "toAddress": "someone@example.com"}


def test_reads_are_allowed():
    assert decide("SearchEmails") == "allow"


def test_drafts_from_office_and_luca_are_allowed():
    assert decide("sendReplyEmail", draft("office@londonchoralservice.com")) == "allow"
    assert decide("sendReplyEmail", draft("luca@almaconsort.com")) == "allow"


def test_other_senders_and_real_sends_are_denied():
    assert decide("sendEmail", draft("izzy@almaconsort.com")) == "deny"
    assert decide("sendReplyEmail", {"fromAddress": "luca@almaconsort.com", "toAddress": "a@b.com"}) == "deny"
    assert decide("sendEmail", dict(draft("luca@almaconsort.com"), isSchedule=True)) == "deny"
    assert decide("emptyFolder") == "deny"
```

Add the standard runner.

- [ ] **Step 2: Run to verify it fails**

Run: `$PY tests/test_zoho_guard.py`
Expected: `FAIL test_drafts_from_office_and_luca_are_allowed` (luca@ is denied today).

- [ ] **Step 3: Implement.** In `.claude/hooks/zoho_guard.py`:
  - replace `DRAFT_FROM = "office@londonchoralservice.com"` with:
    ```python
    DRAFT_FROM = {"office@londonchoralservice.com", "luca@almaconsort.com"}
    ```
  - replace the sender check with:
    ```python
    if (body.get("fromAddress") or "").strip().lower() not in DRAFT_FROM:
        return "Zoho guard: drafts must come from office@londonchoralservice.com (clients) or luca@almaconsort.com (singers)."
    ```
  - in the final deny message, replace `drafts from {DRAFT_FROM} only` with `drafts from office@ or luca@almaconsort.com only`.
  - update the module docstring's second sentence to say "…may SAVE DRAFTS from office@londonchoralservice.com or luca@almaconsort.com."

- [ ] **Step 4: Run to verify it passes**

Run: `$PY tests/test_zoho_guard.py`
Expected: every line PASS, then `0 failure(s)`.

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/zoho_guard.py tests/test_zoho_guard.py
git commit -m "feat(guard): allow drafts from luca@almaconsort.com for singer replies"
```

---

### Task 6: The Monday money line

**Files:**
- Create: `scripts/bookings/money_report.py`
- Modify: `scripts/reports/weekly_review.py` (add `import sys`, `money_section()`, and a call in `main()`)
- Test: `tests/test_money_report.py`

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for scripts/bookings/money_report.py. Stdlib only."""
import datetime, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import money_report as mr

T = datetime.date(2026, 9, 28)


def test_summary_lines():
    assessments = [
        {"ref": "A", "state": "DEPOSIT_OVERDUE", "balance": 500.0, "event_date": "2026-10-30"},
        {"ref": "B", "state": "BALANCE_DUE", "balance": 325.0, "event_date": "2026-10-01"},
        {"ref": "C", "state": "DEPOSIT_SEEN", "balance": 575.0, "event_date": "2026-12-12"},
    ]
    receipts = [("B", "2026-09-25", 325.0), ("C", "2026-09-01", 575.0)]
    singer = {"unpaid": 2, "unpaid_total": 150.0, "oldest_days": 8, "bank_changed": 1}
    assert mr.summary_lines(assessments, receipts, singer, T) == [
        "received from clients, last 7 days: £325.00 (1 payment)",
        "deposits overdue: 1 (A)",
        "balances due in the next 7 days: 1, £325.00 (B)",
        "singer invoices unpaid: 2, £150.00, oldest 8 days · BANK DETAILS CHANGED on 1: ring before paying",
    ]


def test_quiet_week():
    singer = {"unpaid": 0, "unpaid_total": 0.0, "oldest_days": 0, "bank_changed": 0}
    assert mr.summary_lines([], [], singer, T) == [
        "received from clients, last 7 days: £0.00 (0 payments)",
        "deposits overdue: 0",
        "balances due in the next 7 days: 0, £0.00",
        "singer invoices unpaid: 0, £0.00, oldest 0 days",
    ]
```

Add the standard runner.

- [ ] **Step 2: Run to verify it fails**

Run: `$PY tests/test_money_report.py`
Expected: `ModuleNotFoundError: No module named 'money_report'`

- [ ] **Step 3: Write `scripts/bookings/money_report.py`**

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `$PY tests/test_money_report.py`
Expected: PASS ×2, `0 failure(s)`.

- [ ] **Step 5: Wire it into `scripts/reports/weekly_review.py`**
  - Add `import sys` to the imports, alphabetically after `re`.
  - Add `  10. Money: client receipts, deposits overdue, balances due, singer invoices (totals only)` to the docstring's section list.
  - Add this function above `def main():`

```python
def money_section():
    print("\n== 10. Money (totals and invoice numbers only)")
    sys.path.insert(0, str(REPO / "scripts" / "bookings"))
    import check_payments
    import lcs_money
    import money_report
    import singer_invoices
    today = datetime.date.today()
    tok = lcs_money.keychain_token()
    if not tok:
        print("   no Starling token in the Keychain: money check skipped")
        return
    client = lcs_money.StarlingReadOnly(tok)
    rows = lcs_money.read_csv(check_payments.LEDGER)
    assessments = [a for _, _, a in check_payments.collect(client, rows, today)]
    receipts = check_payments.received_since(client, rows, today - datetime.timedelta(days=7), today)
    singer = singer_invoices.summary(lcs_money.read_csv(singer_invoices.STORE), today)
    for line in money_report.summary_lines(assessments, receipts, singer, today):
        print("   " + line)
```

  - In `main()`, add `money_section()` after `ledger_section()`.

- [ ] **Step 6: Run the report section live**

Run: `cd ~/Documents/GitHub/londonchoralservice && $PY <worktree>/scripts/reports/weekly_review.py 2>&1 | awk '/== 10/,0'`
Expected: four lines. 2111's balance appears only if the event is within 7 days (it isn't on 28 Sep). The singer line reads 0 unpaid until Task 8's first scan. No names appear.

- [ ] **Step 7: Commit**

```bash
git add scripts/bookings/money_report.py scripts/reports/weekly_review.py tests/test_money_report.py
git commit -m "feat(reports): Monday money line (receipts, deposits, balances, singer invoices)"
```

---

### Task 7: Wire the scheduled tasks, allowlist and docs

**Files:**
- Modify: `.claude/settings.json`
- Modify: `docs/HANDOVER-2026-09-27-ads-analytics.md` (Appendix E and Appendix A)
- Modify: `CLAUDE.md`
- Update: scheduled tasks `enquiry-assistant` and `christmas-carol-campaign-review` (via the scheduled-tasks tool, text copied from the appendices)

- [ ] **Step 1: Allowlist.** Add to `permissions.allow` in `.claude/settings.json`, keeping the existing entries and the `deny` list:

```json
"Bash(.venv/bin/python scripts/bookings/check_payments.py --apply --json)",
"Bash(.venv/bin/python scripts/bookings/singer_invoices.py *)"
```

(`check_payments.py --reminded *` is already allowed and covers `--kind`.)

- [ ] **Step 2: Appendix E, TOOLS list.** Replace these two lines:

```text
  .venv/bin/python scripts/bookings/check_payments.py --apply
  .venv/bin/python scripts/bookings/check_payments.py --reminded <invoice ref>
```

with:

```text
  .venv/bin/python scripts/bookings/check_payments.py --apply --json
  .venv/bin/python scripts/bookings/check_payments.py --reminded <invoice ref> --kind <deposit|balance|receipt>
  .venv/bin/python scripts/bookings/singer_invoices.py scan <saved result file> --message-id <id> --received <YYYY-MM-DD> --sender-email <address> --sender-name '<name>'
  .venv/bin/python scripts/bookings/singer_invoices.py paid --apply
  .venv/bin/python scripts/bookings/singer_invoices.py status
  .venv/bin/python scripts/bookings/singer_invoices.py thanked <message id>
```

- [ ] **Step 3: Appendix E, SAFETY.**
  - Replace the draft sentence `body.fromAddress = "office@londonchoralservice.com"` with `body.fromAddress = "office@londonchoralservice.com" (or "luca@almaconsort.com", only for the "Paid!" replies to singers in step 6b)`.
  - Replace the Alma Consort bullet with:

```text
- Alma Consort work is out of scope for enquiries: skip anything sent to luca@almaconsort.com or izzy@almaconsort.com, subjects "New message from almaconsort.com", and recording projects. The one exception is step 5: invoices from singers, organists and other musicians sent to luca@almaconsort.com.
```

- [ ] **Step 4: Appendix E, steps.** Replace the current step 5 (Payments) with the two steps below, and renumber the later steps. "Run `assistant_io.py done`" becomes 7 (its ids now include the singer invoice messages from step 5) and "PushNotification" becomes 8.

```text
5. Singer invoices, every run: find new Inbox messages since last_checked sent to luca@almaconsort.com with an attachment, where the subject or attachment name mentions "invoice" (or "inv"), from a musician rather than a client or a software supplier. Invoices sent through QuickBooks, Xero or similar come from a notification address: use the musician's name from the subject and their Reply-To address. For each one: ZohoMail_getOriginalMessage (Claude Code saves the large result to a file), then `singer_invoices.py scan <that file> --message-id <id> --received <YYYY-MM-DD> --sender-email <address> --sender-name '<name>'`, then delete the saved file. Put every "!" line at the very top of your summary. If one says BANK DETAILS CHANGED or "different bank details", send a PushNotification at once: "Singer bank details changed: <first name>. Ring them before paying." Never add a payee or payment yourself.
6. Money, on the first run of each day only (when `state` shows the time now before 09:30 UTC):
   a. Run `check_payments.py --apply --json` and act only on these cases:
      - just_received true and reminded.receipt false: reply in the client's thread thanking them for the payment and confirming their date is secured, in Luca's style. Then run `check_payments.py --reminded <ref> --kind receipt`.
      - state DEPOSIT_OVERDUE and reminded.deposit false: read the thread first. If the client says they've paid or Luca acknowledged a payment, draft nothing and list it for Luca. Otherwise draft a short, friendly reminder (the invoice number, the first instalment, that it secures the date, "do let me know if you've already sent it"). Then run `--reminded <ref> --kind deposit`.
      - state BALANCE_DUE and reminded.balance false: the same thread check, then a short balance reminder (the amount, due the day before the event, bank details on the invoice). Then run `--reminded <ref> --kind balance`.
      Never draft for any other state, and never about a past event.
   b. Run `singer_invoices.py paid --apply`. For each "NEWLY PAID <message id>", save a draft reply to that invoice email from luca@almaconsort.com in Luca's one-line style ("Paid! Thanks so much, <first name>." Vary it naturally and keep it short). Then run `singer_invoices.py thanked <message id>`.
   If check_payments says no token is stored, skip 6a and 6b.
```

- [ ] **Step 5: Appendix E, notification and summary.**
  - Replace the PushNotification step's message with: `"<n> drafts in Zoho to review and send"` plus `", <m> invoices ready in ~/lcs-private/invoices"` when you made any, plus `", <k> singer invoices to pay (<j> new payees to add in Starling)"` when step 5 found any.
  - Add this line at the top of FINAL SUMMARY: `- Warnings first: any changed singer bank details, then new payees to add.` and after "Invoices made": `- Singer invoices: first name, £, payee status (no bank numbers beyond ••••1234).`

- [ ] **Step 6: Appendix A (Monday).**
  - Append to step 6: `   f. Money line: include report section 10's four lines as they are.`
  - In REPLY FORMAT, change the bookings bullet to: `- A bookings line: new bookings recorded (count, total £), uploads ready (count), anything skipped and why, then section 10's money line. No client or singer names.`

- [ ] **Step 7: CLAUDE.md.** In "Email and invoices (Zoho Mail)", add after the Payments bullet:

```text
- **Singer invoices:** `scripts/bookings/singer_invoices.py` records invoices from musicians (luca@almaconsort.com) in `~/lcs-private/singer-invoices.csv`. It checks Starling payees read-only, warns when bank details change, and marks invoices paid from the OUT feed. Claude never creates payees or payments: a new singer is flagged for the owner to add in the Starling app. The guard allows drafts from luca@almaconsort.com only for the "Paid!" replies to singers.
```

Also change the guard bullet's "drafts from office@londonchoralservice.com" wording to "drafts from office@londonchoralservice.com (clients) or luca@almaconsort.com (singer replies)".

- [ ] **Step 8: Update the scheduled tasks.** Print each appendix's text block and paste it verbatim into `update_scheduled_task` (`enquiry-assistant` ← Appendix E, `christmas-carol-campaign-review` ← Appendix A). Then verify:

```bash
cd ~/Documents/GitHub/londonchoralservice && python3 - <<'EOF'
from pathlib import Path
h = Path("docs/HANDOVER-2026-09-27-ads-analytics.md").read_text()
def block(t):
    a = h[h.index(t):]; a = a[a.index("```text\n") + 8:]; return a[:a.index("\n```")].strip()
for t, task in [("## Appendix A", "christmas-carol-campaign-review"), ("## Appendix E", "enquiry-assistant")]:
    s = (Path.home() / f".claude/scheduled-tasks/{task}/SKILL.md").read_text().split("---", 2)[2].strip()
    print(t, block(t) == s)
EOF
```

Expected: `## Appendix A True` and `## Appendix E True` (run it after the PR is merged and the main checkout pulled).

- [ ] **Step 9: Commit**

```bash
git add .claude/settings.json docs/HANDOVER-2026-09-27-ads-analytics.md CLAUDE.md
git commit -m "docs(automation): wire singer invoices, balance and receipt drafts into the assistant and Monday review"
```

---

### Task 8: Live verification, PR and merge

- [ ] **Step 1: Run every test**

```bash
for t in tests/test_lcs_money.py tests/test_check_payments.py tests/test_singer_invoices.py tests/test_money_report.py tests/test_zoho_guard.py tests/test_competitor_claims.py tests/test_register_generators.py; do $PY "$t" | tail -1; done
```

Expected: `0 failure(s)` for the first five, `0 failure(s)` for the competitor tests, and `0 of 24 register pages drift` for the register test.

- [ ] **Step 2: Confirm the live payees call works.** Take the most recent singer invoice in Zoho (Inbox, to luca@almaconsort.com). Fetch it with `ZohoMail_getOriginalMessage`, then run:

```bash
cd ~/Documents/GitHub/londonchoralservice && $PY <worktree>/scripts/bookings/singer_invoices.py scan <saved file> --message-id <id> --received <date> --sender-email <from> --sender-name '<name>'
```

Expected: one line with the first name, £ amount, ref, and a payee status that isn't "unknown". A singer the owner has paid before should read `existing: …`. If every singer comes back NEW, print `sorted(client.payees()[0].keys())` and the first account's keys, not their values. Then correct `payee_fingerprints` to Starling's real field names and add a test with the corrected shape. Delete the saved file afterwards.

- [ ] **Step 3: Backfill the last 30 days of singer invoices.** Repeat Step 2 for each invoice in the last 30 days (the inbox listing on 28 Sep shows about 20). Then run `singer_invoices.py paid --apply`. Most should be marked paid, since the owner replies "Paid!" the same day. Finally run `singer_invoices.py status`. The expected unpaid list is short, and every entry should be genuinely outstanding.

- [ ] **Step 4: Check the client side**

Run `check_payments.py --json`. Expected: valid JSON, with a state for each open booking (2111 DEPOSIT_SEEN; 2408 PAST_PART_PAID), and every `just_received` false because the ledger was already updated.

- [ ] **Step 5: Push, PR, merge, pull**

```bash
git push -u origin claude/automation-phase-1
gh pr create --title "Automation Phase 1: money in and out" --body "<summary of tasks 1–7, verification from task 8, then the attribution line>"
gh pr merge --merge
git -C ~/Documents/GitHub/londonchoralservice pull --ff-only origin main
```

Then do Task 7 Step 8 (paste the appendices into the two scheduled tasks and verify both print True).

- [ ] **Step 6: Watch one real run.** Run the enquiry assistant once (`run_scheduled_task enquiry-assistant`) and read its transcript. Expected:
  - no permission prompts;
  - singer invoices since last_checked scanned;
  - no draft for any past event;
  - a summary with warnings first.

---

## Self-review (done while writing)

- **Spec coverage:**
  - features 1 and 2: Tasks 3, 4, 7 (step 5), 8;
  - features 3 and 4: Tasks 2 and 7 (step 6a);
  - feature 5: Task 6;
  - guard change for singer replies: Task 5.
- **Consistency:**
  - `StarlingReadOnly.feed(since, until, direction)` is used identically in `check_payments.collect`/`received_since` and `singer_invoices.cmd_paid`.
  - `assess()` keys (`state`, `balance`, `event_date`, `reminded`, `just_received`, `deposit_due`) match `describe()`, `money_report.summary_lines()` and Appendix E.
  - `singer_invoices.summary()` keys match `money_report`.
- **Known risk:** the Starling payee field names (`bankIdentifier`, `accountIdentifier`) are checked live in Task 8, Step 2 before anything depends on them.
