"""Read models for the Command Centre's pages. Read-only: nothing here writes, sends or pays.

Everything comes from the existing scripts, imported rather than shelled out to, so the app, the static
dashboard and the Monday report agree: scripts/reports/dashboard.py's builders (payments, upcoming,
money_lines, hand_check, singers, bank_balance), which in turn use check_payments.collect/assess,
money_report.needs_hand_check/hand_check_label/summary_lines and singer_invoices.summary/payee_status.

- Private files come from ~/lcs-private (LCS_PRIVATE_DIR), through lcs_money's paths.
- Starling is read through lcs_money.StarlingReadOnly (GET only) with the Keychain token, and those reads
  (the payments feed and the balance) are cached for BANK_TTL seconds, a failed read for BANK_FAIL_TTL only (a
  blip is retried a minute later, and Today says "Bank unreachable at HH:MM (retrying)"); the ledger and the
  singer store are read on every page load.
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

from . import books_cache, drafts, models, quote, sources, todo  # noqa: E402  the builders and readers

cp, lm, mr, si, pl = dash.cp, dash.lm, dash.mr, dash.si, dash.pl
LONDON = ZoneInfo("Europe/London")
BANK_TTL = 600  # seconds: the spec's 10-minute cache for the check_payments collect (and the health check)
BANK_FAIL_TTL = 60  # seconds a failed Starling read is kept before the next page load tries again
STATES = dict(dash.STATES, CANCELLED=("cancelled", ""))
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


def open_singers(rows):
    """dash.singers (the unpaid invoices, oldest first) with each row's action handle and allowed actions, and what
    the pay list needs (models.singer_trust): whether the account is trusted, how, the Books bill number, and why
    an untrusted one waits."""
    out = []
    for r in sorted(rows, key=lambda r: r.get("received") or ""):
        for s in dash.singers([r], rows):  # the whole store: an account trusted on one invoice is on all
            out.append(dict(s, **models.singer_actions(r), **models.singer_trust(rows, r)))
    return out


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
        self._bank_seen = {"good": None, "failed": None, "connected": None}  # the strip's Bank chip; never cleared
        self._starling = None  # (expires, value): the health page's account check
        self._last_good = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------ plumbing

    def panel(self, name, fn, *deps, keep=True):
        """Run fn(*values of deps); any failure (a dep's or its own) becomes a Panel with the type name.
        keep=False: no last good value (a search's results, or one booking's timeline, are only good for
        their own request)."""
        for d in deps:
            if not d.ok:
                return Panel(error=d.error, stale=self._last_good.get(name) if keep else None)
        try:
            value = fn(*(d.value for d in deps))
        except Exception as e:  # the type only: the message may hold private data
            return Panel(error=type(e).__name__, stale=self._last_good.get(name) if keep else None)
        if keep:
            self._last_good[name] = value
        return Panel(value=value)

    def _ledger_key(self):
        try:
            st = Path(cp.LEDGER).stat()
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def bank(self, rows, today):
        """The Starling-backed reads, cached BANK_TTL seconds (a failed read BANK_FAIL_TTL seconds), and redone when
        the ledger changes: {"assessments", "receipts", "bank_checked", "balance", "as_of", "unreachable"}.
        `unreachable` is the HH:MM of a failed read (there is a client, but Starling didn't answer, so
        dashboard.payments fell back to the ledger notes); None when the read worked or there is no client at all
        (no Keychain token, or CC_NO_BANK)."""
        key = (self._ledger_key(), today)
        with self._lock:
            cached = self._bank
            if cached and cached[0] > self.clock() and cached[1] == key:
                return cached[2]
        client = self.client_factory()
        assessments, receipts, checked = dash.payments(client, rows, today)
        balance = dash.bank_balance(client) if checked else None
        at = self.now().strftime("%H:%M")
        failed = client is not None and not checked
        value = {"assessments": assessments, "receipts": receipts, "bank_checked": checked, "balance": balance,
                 "as_of": at if checked else None, "unreachable": at if failed else None}
        with self._lock:
            self._bank = (self.clock() + (BANK_FAIL_TTL if failed else BANK_TTL), key, value)
            seen = self._bank_seen
            seen["connected"] = client is not None
            if checked:
                seen["good"], seen["failed"] = self.now(), None
            elif failed:
                seen["failed"] = self.now()
        return value

    def bank_status(self):
        """The Bank chip's facts, from the reads the pages made (the strip never reads Starling itself): the time
        of the last good read, the time of the latest read when it failed, and whether there is a client."""
        with self._lock:
            return dict(self._bank_seen)

    def sync_strip(self):
        """The chips under the header on every page (sources.sync_chips)."""
        return sources.sync_chips(self.now(), self.bank_status())

    def books_flags_now(self):
        """For the push watcher's books-disagree alert: (models.books_flags as Today shows them, complete), or None
        when Books isn't synced. `complete` is False while the bank isn't checked (the Starling comparisons are then
        left out, so a flag missing from the list may still be there). Failures propagate (the watcher logs the type)."""
        now = self.now()
        today = lm.today(now)
        cache = books_cache.books_cache()
        if cache is None:
            return None
        rows = lm.read_csv(cp.LEDGER)
        b = self.bank(rows, today)
        bookings = models.booking_rows(rows, b["assessments"], b["bank_checked"], today)
        return models.books_flags(cache["invoices"], rows, bookings, today, b["bank_checked"]), bool(b["bank_checked"])

    def _common(self):
        now = self.now()
        today = lm.today(now)
        ledger = self.panel("ledger", lambda: lm.read_csv(cp.LEDGER))
        bank = self.panel("bank", lambda rows: self.bank(rows, today), ledger)
        store = self.panel("singer_store", lambda: lm.read_csv(si.STORE))
        singers = self.panel("singers", open_singers, store)
        hand = self.panel("hand_check", lambda b: dash.hand_check(b["assessments"], today), bank)
        return now, today, ledger, bank, store, singers, hand

    def clear_caches(self):
        """"Refresh data now": the next page load reads the bank (and the health page's Starling check) afresh."""
        with self._lock:
            self._bank = None
            self._starling = None

    # ------------------------------------------------------------ pages

    def today_page(self, proposals=None, books_import=None):
        """Today. `proposals` (actions.list_proposals) and `books_import` (actions.books_status) are Panels the app
        passes in (this module doesn't import actions). "Needs you" is models.needs_you over every source it names:
        `attention` is its count, `missing` the sources that didn't load (the count is then a floor)."""
        now, today, ledger, bank, store, singers, hand = self._common()
        upcoming = self.panel("upcoming", lambda rows, b: dash.upcoming(rows, b["assessments"], b["bank_checked"],
                                                                        today), ledger, bank)
        horizon = (today + datetime.timedelta(days=WEEK_DAYS)).isoformat()
        week = self.panel("week", lambda u: [x for x in u if x["date"] <= horizon], upcoming)
        later = self.panel("later", lambda u: [x for x in u if x["date"] > horizon], upcoming)
        books = self.books()
        flags = self.panel("books_flags", lambda c, rows, b: None if c is None else models.books_flags(
            c["invoices"], rows, models.booking_rows(rows, b["assessments"], b["bank_checked"], today), today,
            b["bank_checked"]), books, ledger, bank)
        bill_flags = self.panel("singer_bill_flags", lambda c, s: None if c is None else models.singer_bill_flags(
            s, c["bills"]), books, store)
        synced = self.panel("books_synced", lambda c: None if c is None else models.books_synced(c, now), books)
        enq = self._enquiries()
        due = self.panel("followups_due", lambda rows: pl.followups_due(rows, today), enq)
        found = self.panel("drafts", drafts.read_drafts)
        inbox = self.panel("drafts_inbox", drafts.inbox, found, self.panel("draft_marks", drafts.load_marks))
        waiting = self.panel("enquiries_waiting", lambda rows, d: models.enquiries_waiting(rows, d, now), enq, found)
        runs = self.panel("proxies", lambda: sources.run_proxies(now))
        backup = self.panel("backup", lambda: sources.backup_status(now))
        panels = {"ledger": ledger, "singer_store": store, "books": books, "enquiries": enq, "singers": singers,
                  "hand": hand, "bank": bank, "drafts": inbox, "books_flags": flags, "bill_flags": bill_flags,
                  "followups": due, "waiting": waiting, "runs": runs, "backup": backup}
        if proposals is not None:
            panels["proposals"] = proposals
        if books_import is not None:
            panels["books_import"] = books_import
        unreachable = bool(bank.ok and bank.value.get("unreachable"))
        needs, missing = models.needs_you(panels, bank_unreachable=unreachable)
        return {"stamp": stamp(now), "today": today, "hand": hand, "singers": singers, "week": week, "later": later,
                "bank": bank, "needs": needs, "missing": missing, "attention": sum(r["count"] for r in needs),
                "books_flags": flags, "singer_bill_flags": bill_flags, "books_synced": synced}

    def money_page(self):
        now, today, ledger, bank, store, singers, hand = self._common()
        lines = self.panel("money_lines", lambda b, rows: dash.money_lines(b["assessments"], b["receipts"], rows,
                                                                           today), bank, store)
        balance = self.panel("balance", lambda b: b["balance"], bank)
        total = self.panel("singer_total", lambda s: round(sum(x["amount"] for x in s), 2), singers)
        books = self.books()
        summary = self.panel("books_summary", lambda c: models.books_summary(
            c, ledger.value if ledger.ok else None) if c else None, books)
        margins = self.margins(ledger, store)
        season = self.panel("season_margin", lambda m: models.season_margin(m, dash.season_start()), margins)
        unlinked = self.panel("unlinked_singer_invoices", si.unlinked_invoices, store)
        # the pay list: the same split Today's Needs you makes (models.singer_pay_list), so its count and total
        # are the "Pay N singer invoices" row's; a Books cache that won't load only drops the "paid in Books" check
        bill_flags = self.panel("singer_bill_flags", lambda c, s: None if c is None else models.singer_bill_flags(
            s, c["bills"]), books, store)
        pay = self.panel("singer_pay_list", lambda s: models.singer_pay_list(
            s, bill_flags.value if bill_flags.ok else None), singers)
        return {"stamp": stamp(now), "today": today, "bank": bank, "balance": balance, "lines": lines, "hand": hand,
                "singers": singers, "singer_total": total, "books": summary, "season": season, "unlinked": unlinked,
                "pay": pay, "pay_books_checked": bill_flags.ok and bill_flags.value is not None}

    # ------------------------------------------------------------ phase 6: Books, margins, drafts, quotes

    def books(self):
        """books.json (cc_sync.py books), or a Panel with None when Books isn't synced yet."""
        return self.panel("books", books_cache.books_cache)

    def margins(self, ledger, store):
        """singer_invoices.margins() over the ledger and the singer store the pages read."""
        return self.panel("margins", lambda rows, s: si.margins(rows, s), ledger, store)

    def drafts_page(self):
        now = self.now()
        found = self.panel("drafts", drafts.read_drafts)
        marks = self.panel("draft_marks", drafts.load_marks)
        box = self.panel("drafts_inbox", drafts.inbox, found, marks)
        return {"stamp": stamp(now), "drafts": found, "inbox": box, "zoho_url": drafts.ZOHO_DRAFTS_URL}

    def quote_page(self, list_key, package, organist, travel, premium_day):
        now = self.now()
        lists = self.panel("price_lists", quote.load_lists)
        list_key = list_key if list_key in quote.LISTS else "standard"
        result = None
        if lists.ok and package:
            try:
                result = quote.calculate(lists.value, list_key, package, organist=organist, travel=travel,
                                         premium_day=premium_day)
            except ValueError:
                result = None
        return {"stamp": stamp(now), "lists": lists, "list_key": list_key, "labels": quote.LIST_LABELS,
                "package": package if result else "", "organist": organist, "travel": travel,
                "premium_day": premium_day, "result": result}

    # ------------------------------------------------------------ phase 2

    def _bookings(self, today):
        ledger = self.panel("ledger", lambda: lm.read_csv(cp.LEDGER))
        bank = self.panel("bank", lambda rows: self.bank(rows, today), ledger)
        bookings = self.panel("bookings", lambda rows, b: models.booking_rows(rows, b["assessments"],
                                                                               b["bank_checked"], today), ledger, bank)
        return ledger, bank, bookings

    def _enquiries(self):
        return self.panel("enquiries", lambda: lm.read_csv(pl.ENQUIRIES) if pl.ENQUIRIES.exists() else [])

    def _gclids(self):
        return self.panel("gclid_cache", sources.gclid_cache)

    def bookings_page(self, when="upcoming", state=""):
        now = self.now()
        today = lm.today(now)
        when = when if when in models.WHEN else "upcoming"
        state = state if state in STATES else ""
        ledger, bank, bookings = self._bookings(today)
        shown = self.panel("bookings_shown", lambda b: models.filter_bookings(b, when, state), bookings, keep=False)
        store = self.panel("singer_store", lambda: lm.read_csv(si.STORE))
        margins = self.panel("margins_by_ref", models.margin_map, self.margins(ledger, store))
        return {"stamp": stamp(now), "bank": bank, "bookings": shown, "when": when, "state": state,
                "states": sorted(STATES.items(), key=lambda kv: kv[1][0]), "margins": margins}

    def booking_page(self, ref):
        """None when the ref is malformed or not in the (readable) ledger: the route answers 404."""
        if not isinstance(ref, str) or not models.REF_RE.fullmatch(ref):
            return None
        now = self.now()
        today = lm.today(now)
        ledger, bank, bookings = self._bookings(today)
        row = None
        if ledger.ok:
            row = next((r for r in ledger.value if (r.get("booking_ref") or "").strip() == ref), None)
            if row is None:
                return None
        booking = self.panel("booking", lambda b: next(x for x in b if x["ref"] == ref), bookings, keep=False)
        store = self.panel("singer_store", lambda: lm.read_csv(si.STORE))
        parts = {
            "ledger": self.panel("tl_ledger", lambda b: models.ledger_timeline(row, b, today), booking, keep=False),
            "enquiries": self.panel("tl_enquiries", lambda rows: models.booking_enquiries(ref, rows, today),
                                    self._enquiries(), keep=False),
            "singers": self.panel("tl_singers", lambda b, rows: models.booking_singers(b["event_date"], rows, ref),
                                  booking, store, keep=False),
        }
        books = self.books()
        parts["books"] = self.panel("tl_books", lambda c: models.books_timeline(ref, c["invoices"]) if c else [],
                                    books, keep=False)
        items = models.sort_items([i for p in parts.values() if p.ok for i in p.value])
        singer_list = self.panel("booking_singer_list", lambda b, rows: models.booking_singer_list(
            ref, b["event_date"], rows), booking, store, keep=False)
        margin = self.panel("booking_margin", lambda m: next((x for x in m if x["ref"] == ref), None),
                            self.margins(ledger, store), keep=False)
        return {"stamp": stamp(now), "ref": ref, "booking": booking, "bank": bank, "parts": parts, "timeline": items,
                "ledger": ledger, "books": books, "singer_list": singer_list, "margin": margin}

    def enquiries_page(self):
        now = self.now()
        today = lm.today(now)
        enq = self._enquiries()
        board = self.panel("board", models.enquiry_board, enq)
        due = self.panel("followups_due", lambda rows: pl.followups_due(rows, today), enq)
        windows = self.panel("conversion", lambda rows: [
            dash.window(rows, "Season", dash.season_start()),
            dash.window(rows, "Last 30 days", today - datetime.timedelta(days=30)),
            dash.window(rows, "All time", None)], enq)
        mix = self.panel("sources", lambda rows: sorted(pl.summary_dict(rows)["by_source"].items(),
                                                        key=lambda kv: (-kv[1], kv[0])), enq)
        return {"stamp": stamp(now), "enquiries": enq, "board": board, "due": due, "windows": windows, "sources": mix}

    def enquiry_page(self, eid):
        """None when the id is malformed or not in the (readable) pipeline: the route answers 404."""
        if not isinstance(eid, str) or not pl.ID_RE.fullmatch(eid):
            return None
        now = self.now()
        today = lm.today(now)
        enq = self._enquiries()
        row = None
        if enq.ok:
            row = next((r for r in enq.value if r.get("enquiry_id") == eid), None)
            if row is None:
                return None
        timeline = self.panel("enquiry_timeline", lambda rows: models.enquiry_timeline(row, today), enq,
                              keep=False)
        campaign = self.panel("campaign", lambda c: models.campaign_for(row or {}, c), self._gclids(), keep=False)
        return {"stamp": stamp(now), "eid": eid, "row": row, "enquiries": enq, "timeline": timeline,
                "campaign": campaign, "status": pl.status_of(row) if row else "",
                "next": models.next_followup(row, today) if row else None}

    def singers_page(self):
        now = self.now()
        today = lm.today(now)
        store = self.panel("singer_store", lambda: lm.read_csv(si.STORE))
        directory = self.panel("singer_directory", lambda rows: models.singer_directory(rows, today), store)
        return {"stamp": stamp(now), "directory": directory}

    def marketing_page(self):
        now = self.now()
        summary = self.panel("ads_summary", sources.ads_summary)
        weeks = self.panel("ads_weeks", lambda s, e: dash.ads(e) if s else None, summary, self._enquiries())
        chart = self.panel("ads_chart", lambda s: models.weekly_chart((s or {}).get("weeks")), summary)
        season = self.panel("ads_season", lambda s: models.season_table(s) if s else None, summary)
        traced = self.panel("gclid_counts", models.gclid_counts, self._gclids())
        generated = None
        if summary.ok and summary.value:
            try:
                generated = datetime.datetime.fromisoformat(str(summary.value.get("generated")))
            except ValueError:
                generated = None
        cache = self.panel("marketing_cache", sources.marketing_cache)
        market = self.panel("marketing_view", lambda c: models.marketing_view(c, now) if c else None, cache)
        return {"stamp": stamp(now), "summary": summary, "weeks": weeks, "chart": chart, "season": season,
                "traced": traced, "generated": generated, "market": market}

    def calendar_page(self, view="month", date=None):
        now = self.now()
        today = lm.today(now)
        view = view if view in ("month", "week") else "month"
        anchor = (models.to_date(date) if isinstance(date, str) else None) or today
        ledger, bank, bookings = self._bookings(today)
        diary = self.panel("diary", sources.calendar_cache)
        lists = [self.panel("cal_bookings", models.booking_dates, bookings),
                 self.panel("cal_enquiries", lambda rows: models.enquiry_dates(rows, today), self._enquiries()),
                 self.panel("cal_diary", lambda c: models.diary_items(c[0]) if c else [], diary)]
        grid = self.panel("calendar", lambda: models.calendar_items(view, anchor, today,
                                                                   *(p.value for p in lists if p.ok)), keep=False)
        return {"stamp": stamp(now), "view": view, "grid": grid, "lists": lists, "diary": diary, "today": today,
                "anchor": anchor}

    def search_page(self, q):
        now = self.now()
        q = models.clean_query(q)
        results = []
        if len(q) >= models.SEARCH_MIN:
            for label, kind, read in (
                    ("Bookings", "bookings", lambda: lm.read_csv(cp.LEDGER)),
                    ("Enquiries", "enquiries", lambda: lm.read_csv(pl.ENQUIRIES) if pl.ENQUIRIES.exists() else []),
                    ("Singers and their invoices", "singers", lambda: lm.read_csv(si.STORE))):
                rows = self.panel(f"search_rows_{kind}", read, keep=False)
                results.append((label, self.panel(f"search_{kind}", lambda r, k=kind: models.search(q, k, r), rows,
                                                  keep=False)))
        return {"stamp": stamp(now), "q": q, "results": results, "min": models.SEARCH_MIN}

    def reports_page(self):
        return {"stamp": stamp(self.now()), "reports": self.panel("reports", sources.report_list)}

    def report_page(self, name):
        """None for a bad or missing name: the route answers 404."""
        text = sources.report_text(name)
        if text is None:
            return None
        return {"stamp": stamp(self.now()), "report_name": name, "text": text}

    def starling_check(self):
        """The Starling account read (GET only), cached BANK_TTL seconds. The token never reaches the page."""
        with self._lock:
            cached = self._starling
            if cached and cached[0] > self.clock():
                return cached[1]
        client = self.client_factory()
        if client is None:
            value = sources.check("Starling", None, "not checked: no Keychain token, or CC_NO_BANK is set")
        else:
            try:
                client.account()
                value = sources.check("Starling", True, f"account readable (read-only), checked at {self.now():%H:%M}")
            except Exception as e:  # the type only
                value = sources.check("Starling", False, f"account read failed ({type(e).__name__}) at "
                                                         f"{self.now():%H:%M}; retrying")
        with self._lock:
            self._starling = (self.clock() + (BANK_FAIL_TTL if value["ok"] is False else BANK_TTL), value)
        return value

    def health_page(self, branch):
        now = self.now()
        tasks = self.panel("tasks", sources.scheduled_tasks)
        proxies = self.panel("proxies", lambda: sources.run_proxies(now))
        checks = [self.panel("check_starling", self.starling_check),
                  self.panel("check_adc", sources.adc_check),
                  self.panel("check_mcp", sources.mcp_checks),
                  self.panel("check_fingerprint", lambda: sources.fingerprint_check(now)),
                  self.panel("check_backup", lambda: sources.backup_check(now)),
                  self.panel("check_disk", sources.disk_check),
                  self.panel("check_branch", lambda: sources.branch_check(branch))]
        backup = self.panel("backup", lambda: sources.backup_status(now))
        return {"stamp": stamp(now), "tasks": tasks, "proxies": proxies, "checks": checks, "backup": backup}

    def todo_page(self):
        items = self.panel("todo", lambda: todo.todo_items(todo.read_items(), todo.load_ticks()))
        return {"stamp": stamp(self.now()), "items_panel": items}

    EXPORTS = ("bookings", "singer-invoices", "pipeline")

    def export(self, name):
        """(filename, header, rows) for one CSV export, or None for an unknown name. RuntimeError(<TypeName>)
        when a source fails (the route answers 503)."""
        if name not in self.EXPORTS:
            return None
        today = lm.today(self.now())
        if name == "bookings":
            panel = self.panel("export_bookings", models.export_bookings, self._bookings(today)[2], keep=False)
        elif name == "singer-invoices":
            panel = self.panel("export_singers", lambda: models.export_singers(lm.read_csv(si.STORE)), keep=False)
        else:
            panel = self.panel("export_pipeline", models.export_pipeline, self._enquiries(), self._gclids(),
                               keep=False)
        if not panel.ok:
            raise RuntimeError(panel.error)
        head, rows = panel.value
        return f"lcs-{name}-{today.isoformat()}.csv", head, rows
