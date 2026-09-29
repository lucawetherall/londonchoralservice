"""The background refresh job: every 30 minutes from 07:00 to 22:00 London time, inside the app process.

Each pass runs, in order, as subprocesses: `scripts/bookings/singer_invoices.py paid --apply` (matches the Starling
feed, read-only, against the unpaid singer invoices and records a match's paid_on, paid_amount, paid_ref and
paid_verified in the singer store under its lock: a verified payment shows within 30 minutes even when the enquiry
assistant hasn't run; it never creates a payee, a payment or a Books record, which the singer clerk still does from
`paid --books-due`), `scripts/reports/dashboard.py` (the static dashboard, read-only) and `scripts/reports/cc_sync.py
books` (the Books cache, through lcs_mcp's read-only client; it exits 1 when Books couldn't be read). Once a day, in
the day's first pass (the 07:00 slot, or the first one after it when the service started later or that slot was
skipped as busy), it also runs `scripts/reports/cc_sync.py marketing` (flagged search terms, the Search Console
shortlist and GA4 leads, through weekly_review's read-only functions): a script whose SCRIPTS entry has daily=True.
A daily script that fails is logged and not retried until the next day. Each is an
argv list, never a shell, with the actions' clean environment (no CC_* variable, LCS_PRIVATE_DIR set explicitly),
stdin /dev/null and a timeout. Then it puts the Ads mirror's fixed config back (actions.tidy_mirror: only an existing
mirror, and only when no action is running; the pages read the proposals without writing), and clears the app's bank
cache, so the next page load reads Starling afresh.

- It has its own lock, and it takes the manual refresh's lock (actions._LOCKS["refresh"]) without waiting, so a pass
  never overlaps a "Refresh data now" or another pass: a slot that finds either busy is skipped. While it holds that
  lock it sets actions.BACKGROUND_REFRESH, so a manual refresh waits up to 20 seconds and then says a background
  refresh is running, rather than "another action is running".
- A clean pass writes nothing to the audit log. A failure (a timeout, a non-zero exit, a script that won't start,
  a failing cache clear) is logged as "refresh-job" with its exception's type name only, never the output or the
  message, which could hold private data. One failing script never stops the other.
- Each script's outcome is noted in memory (sources.record_outcome), so the sync strip's Books and Marketing chips
  say "failed" when the latest attempt failed after the cache's last good write.
- create_app starts it only for the service (watch=True: the LaunchAgent on port 8765 or the socket), never on a
  dev port or in the tests, and never when CC_NO_REFRESH_JOB is set.
"""

import asyncio
import contextlib
import datetime
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from zoneinfo import ZoneInfo

from . import actions, sources

REPO = Path(__file__).resolve().parent.parent
LONDON = ZoneInfo("Europe/London")
FIRST, LAST = datetime.time(7, 0), datetime.time(22, 0)  # the first and last slot of the day
STEP = 30  # minutes
POLL = 60  # seconds between looks at the clock
# (name, argv after the interpreter, timeout in seconds, daily): a daily script runs in the day's first pass only
SCRIPTS = (("singer-paid", ["scripts/bookings/singer_invoices.py", "paid", "--apply"], 180, False),
           ("dashboard", ["scripts/reports/dashboard.py"], 180, False),
           ("books", ["scripts/reports/cc_sync.py", "books"], 300, False),
           ("marketing", ["scripts/reports/cc_sync.py", "marketing"], 300, True))
SYSTEM_USER = {"login": "refresh-job"}
log = logging.getLogger("command_centre")


class NonZeroExit(Exception):
    """A script exited with a non-zero code (its output is never logged)."""


def disabled():
    return bool(os.environ.get("CC_NO_REFRESH_JOB"))


def slot(now):
    """The start of the 30-minute slot `now` (any zone) falls in, in London time."""
    local = now.astimezone(LONDON)
    return local.replace(minute=local.minute - local.minute % STEP, second=0, microsecond=0)


class RefreshJob:
    def __init__(self, clear, runner=subprocess.run, python=sys.executable, tidy=None):
        self.clear = clear
        self.runner = runner
        self.python = python
        self.tidy = tidy or actions.tidy_mirror
        self.last_slot = None
        self.last_daily = None  # the London date the daily scripts last ran
        self._lock = threading.Lock()

    def due(self, now):
        s = slot(now)
        return FIRST <= s.time() <= LAST and s != self.last_slot

    def tick(self, now):
        """Run a pass when `now` is in a slot that hasn't had one. True when a pass ran (or was skipped as busy)."""
        if not self.due(now):
            return False
        self.last_slot = slot(now)
        self.run_once(now)
        return True

    def _fail(self, what, exc):
        try:
            actions.write_audit("refresh-job", f"Background refresh: {what}", SYSTEM_USER,
                                f"failed: {type(exc).__name__}")
        except OSError as e:
            log.warning("refresh job: the audit write failed (%s)", type(e).__name__)
        log.warning("refresh job: %s failed (%s)", what, type(exc).__name__)

    def run_script(self, args, timeout):
        argv = [self.python, str(REPO / args[0]), *args[1:]]
        proc = self.runner(argv, cwd=str(REPO), env=actions.clean_env(), stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=timeout, shell=False)
        if proc.returncode != 0:
            raise NonZeroExit()

    def run_once(self, now=None):
        """One pass: "ok", "failed" (logged) or "skipped" (another pass or a manual refresh is running). With `now`,
        the daily scripts run too when they haven't run on that London date; without it they never do."""
        if not self._lock.acquire(blocking=False):
            return "skipped"
        try:
            refresh = actions._LOCKS["refresh"]
            if not refresh.acquire(blocking=False):
                return "skipped"
            actions.BACKGROUND_REFRESH.set()  # a manual "Refresh data now" waits, then says a pass is running
            try:
                ok = True
                day = now.astimezone(LONDON).date() if now is not None else None
                daily_due = day is not None and day != self.last_daily
                if daily_due:
                    self.last_daily = day  # once a day, whatever the outcome: a failure waits for tomorrow
                for what, args, timeout, daily in SCRIPTS:
                    if daily and not daily_due:
                        continue
                    try:
                        self.run_script(args, timeout)
                        sources.record_outcome(what, True)
                    except Exception as e:  # the type only
                        ok = False
                        sources.record_outcome(what, False)  # the strip's chip says "failed" until a good sync
                        self._fail(what, e)
                try:
                    self.tidy()
                except Exception as e:
                    ok = False
                    self._fail("tidy the Ads mirror", e)
                try:
                    self.clear()
                except Exception as e:
                    ok = False
                    self._fail("clear the bank cache", e)
                return "ok" if ok else "failed"
            finally:
                actions.BACKGROUND_REFRESH.clear()
                refresh.release()
        finally:
            self._lock.release()


async def loop(job, stop_event, poll=POLL, now=None):
    """The service's refresh loop (the app's lifespan). A failing look at the clock is logged by type only."""
    from starlette.concurrency import run_in_threadpool
    now = now or (lambda: datetime.datetime.now(LONDON))
    while not stop_event.is_set():
        try:
            await run_in_threadpool(job.tick, now())
        except Exception as e:
            log.warning("refresh job: %s", type(e).__name__)
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=poll)
