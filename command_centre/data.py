"""Read models for the Command Centre's pages. Read-only: nothing here writes, sends or pays.

Everything comes from the existing scripts, imported rather than shelled out to, so the app, the static
dashboard and the Monday report agree: scripts/reports/dashboard.py's builders (payments, upcoming,
money_lines, hand_check, singers, bank_balance), which in turn use check_payments.collect/assess,
money_report.needs_hand_check/hand_check_label/summary_lines and singer_invoices.summary/payee_status.

- Private files come from ~/lcs-private (LCS_PRIVATE_DIR), through lcs_money's paths.
- Starling is read through lcs_money.StarlingReadOnly (GET only) with the Keychain token, and those reads
  (the payments feed and the balance) are cached for BANK_TTL seconds; the ledger and the singer store are
  read on every page load.
- Every source is a Panel: its value, or the failing exception's type name (never its message, which could
  carry private data), plus the last good value when there was one. A failing source never breaks a page.
- Client and singer first names only; bank accounts as ••••last4 only.
"""

import datetime
import os
import sys
import threading
import time
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "reports"))
import dashboard as dash  # noqa: E402  its builders are the read functions this reuses

cp, lm, mr, si = dash.cp, dash.lm, dash.mr, dash.si
LONDON = ZoneInfo("Europe/London")
BANK_TTL = 600  # seconds: the spec's 10-minute cache for the check_payments collect
STATES = dash.STATES
WEEK_DAYS = 6  # "this week" is today and the next six days


def default_client():
    """A GET-only Starling client when the Keychain token exists, else None (bank not checked).
    CC_NO_BANK=1 skips the Keychain and Starling altogether (local checks with fake data)."""
    if os.environ.get("CC_NO_BANK"):
        return None
    token = lm.keychain_token()
    return lm.StarlingReadOnly(token) if token else None


def stamp(when):
    return dash.stamp(when)


class Panel:
    """One source's result for a template: .value, or .error (a type name) with .stale (the last good value)."""

    def __init__(self, value=None, error=None, stale=None, as_of=None):
        self.value, self.error, self.stale, self.as_of = value, error, stale, as_of

    @property
    def ok(self):
        return self.error is None


class Data:
    def __init__(self, client_factory=default_client, now=None, clock=time.monotonic):
        self.client_factory = client_factory
        self.now = now or (lambda: datetime.datetime.now(LONDON))
        self.clock = clock
        self._bank = None  # (expires, key, value)
        self._last_good = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------ plumbing

    def panel(self, name, fn, *deps):
        """Run fn(*values of deps); any failure (a dep's or its own) becomes a Panel with the type name."""
        for d in deps:
            if not d.ok:
                return Panel(error=d.error, stale=self._last_good.get(name))
        try:
            value = fn(*(d.value for d in deps))
        except Exception as e:  # the type only: the message may hold private data
            return Panel(error=type(e).__name__, stale=self._last_good.get(name))
        self._last_good[name] = value
        return Panel(value=value)

    def _ledger_key(self):
        try:
            st = Path(cp.LEDGER).stat()
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def bank(self, rows, today):
        """The Starling-backed reads, cached BANK_TTL seconds (and redone when the ledger changes):
        {"assessments", "receipts", "bank_checked", "balance", "as_of"}."""
        key = (self._ledger_key(), today)
        with self._lock:
            cached = self._bank
            if cached and cached[0] > self.clock() and cached[1] == key:
                return cached[2]
        client = self.client_factory()
        assessments, receipts, checked = dash.payments(client, rows, today)
        balance = dash.bank_balance(client) if checked else None
        value = {"assessments": assessments, "receipts": receipts, "bank_checked": checked, "balance": balance,
                 "as_of": self.now().strftime("%H:%M") if checked else None}
        with self._lock:
            self._bank = (self.clock() + BANK_TTL, key, value)
        return value

    def _common(self):
        now = self.now()
        today = lm.today(now)
        ledger = self.panel("ledger", lambda: lm.read_csv(cp.LEDGER))
        bank = self.panel("bank", lambda rows: self.bank(rows, today), ledger)
        store = self.panel("singer_store", lambda: lm.read_csv(si.STORE))
        singers = self.panel("singers", dash.singers, store)
        hand = self.panel("hand_check", lambda b: dash.hand_check(b["assessments"], today), bank)
        return now, today, ledger, bank, store, singers, hand

    # ------------------------------------------------------------ pages

    def today_page(self):
        now, today, ledger, bank, store, singers, hand = self._common()
        warnings = self.panel("bank_warnings", lambda s: [x for x in s if x["ring_first"]], singers)
        upcoming = self.panel("upcoming", lambda rows, b: dash.upcoming(rows, b["assessments"], b["bank_checked"],
                                                                        today), ledger, bank)
        horizon = (today + datetime.timedelta(days=WEEK_DAYS)).isoformat()
        week = self.panel("week", lambda u: [x for x in u if x["date"] <= horizon], upcoming)
        later = self.panel("later", lambda u: [x for x in u if x["date"] > horizon], upcoming)
        count = sum(len(p.value) for p in (hand, singers) if p.ok)  # a bank warning is one of the singer invoices
        return {"stamp": stamp(now), "today": today, "warnings": warnings, "hand": hand, "singers": singers,
                "week": week, "later": later, "bank": bank, "attention": count}

    def money_page(self):
        now, today, ledger, bank, store, singers, hand = self._common()
        lines = self.panel("money_lines", lambda b, rows: dash.money_lines(b["assessments"], b["receipts"], rows,
                                                                           today), bank, store)
        balance = self.panel("balance", lambda b: b["balance"], bank)
        total = self.panel("singer_total", lambda s: round(sum(x["amount"] for x in s), 2), singers)
        return {"stamp": stamp(now), "today": today, "bank": bank, "balance": balance, "lines": lines, "hand": hand,
                "singers": singers, "singer_total": total}
