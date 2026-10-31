#!/usr/bin/env python3
"""Is each scheduled routine still running? Read-only; for the routine watchdog task.

A run session left open (or stuck on a permission prompt) stops every later run of that task from starting
(27-29 Oct 2026: no mail was checked for 37 hours). A run that never starts can't raise its own alarm, so a
separate task runs this a few times a day and sends a push notification on any ALERT line.

Checks:
- The enquiry assistant (cron "7 6-22/2 * * *", Europe/London) wrote a "start" line in
  ~/lcs-private/assistant-runs.jsonl (scripts/bookings/assistant_io.py) at or after its last slot that is
  more than GRACE old. The last run's start with no "done" or "zoho_down" after it is reported as a note.
- The Monday review saved its report (~/lcs-private/reports/<that Monday>.txt) once the Monday is more
  than REPORT_GRACE past 09:00.

    .venv/bin/python scripts/reports/routine_health.py

Prints one line per check, "ok: …", "note: …" or "ALERT: …". Always exits 0; it prints no personal data.
"""

import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bookings"))
import lcs_money as lm  # noqa: E402  PRIVATE, LONDON

SLOT_HOURS = range(6, 23, 2)   # 06:07, 08:07 … 22:07 London
SLOT_MINUTE = 7
GRACE = datetime.timedelta(minutes=45)       # dispatch jitter (up to ~8 min) plus a slow start
REPORT_GRACE = datetime.timedelta(hours=2)   # the review starts at 09:03 plus jitter


def run_log_path():
    return lm.PRIVATE / "assistant-runs.jsonl"


def read_log(path):
    """[(kind, aware datetime)] for start, done and zoho_down lines, oldest first; None when there is no log."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    out = []
    for line in text.splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        for kind in ("start", "done", "zoho_down"):
            value = entry.get(kind) if isinstance(entry, dict) else None
            if isinstance(value, str):
                try:
                    t = datetime.datetime.fromisoformat(value)
                except ValueError:
                    break
                out.append((kind, t if t.tzinfo else t.replace(tzinfo=lm.LONDON)))
                break
    return sorted(out, key=lambda e: e[1])


def last_due_slot(now):
    """The latest assistant slot (London) that is more than GRACE before `now`, or None."""
    local = now.astimezone(lm.LONDON)
    for back in range(0, 3):
        day = local.date() - datetime.timedelta(days=back)
        for hour in reversed(SLOT_HOURS):
            slot = datetime.datetime.combine(day, datetime.time(hour, SLOT_MINUTE), lm.LONDON)
            if slot + GRACE <= local:
                return slot
    return None


def hm(t):
    return t.astimezone(lm.LONDON).strftime("%a %d %b %H:%M")


def assistant_lines(now, path=None):
    entries = read_log(path or run_log_path())
    if entries is None:
        return ["note: enquiry assistant: no run log yet (assistant_io.py writes it from its next run)"]
    starts = [t for k, t in entries if k == "start"]
    if not starts:
        return ["note: enquiry assistant: the run log has no run start yet"]
    last = starts[-1]
    slot = last_due_slot(now)
    lines = []
    if slot and last < slot - datetime.timedelta(minutes=10):
        lines.append(f"ALERT: enquiry assistant: no run has started since {hm(last)} (one was due {hm(slot)});"
                     " a run session may be stuck open. Open the Enquiry assistant's runs and close the stuck one.")
    else:
        lines.append(f"ok: enquiry assistant: last run started {hm(last)}")
    finished = any(k in ("done", "zoho_down") and t >= last for k, t in entries)
    if not finished and now - last > datetime.timedelta(hours=1):
        lines.append(f"note: enquiry assistant: the run started {hm(last)} never finished")
    return lines


def last_monday(now):
    local = now.astimezone(lm.LONDON)
    monday = local.date() - datetime.timedelta(days=local.weekday())
    due = datetime.datetime.combine(monday, datetime.time(9, 0), lm.LONDON) + REPORT_GRACE
    return monday if local >= due else monday - datetime.timedelta(days=7)


def review_lines(now, reports_dir=None):
    monday = last_monday(now)
    d = Path(reports_dir) if reports_dir else lm.PRIVATE / "reports"
    if (d / f"{monday}.txt").is_file():
        return [f"ok: Monday review: report saved for {monday}"]
    return [f"ALERT: Monday review: no report saved for {monday}. Open the Weekly marketing review's runs;"
            " if none ran, choose Run now."]


DEPLOY_CMD = ["gh", "run", "list", "--repo", "lucawetherall/londonchoralservice", "--workflow", "deploy-pages.yml",
              "--branch", "main", "--limit", "3", "--json", "status,conclusion,displayTitle,createdAt"]


def deploy_lines(runner=None):
    """The site deploy: an ALERT when the newest finished run on main failed and no newer run is under way (31 Oct
    2026: four deploys failed in a week and main stayed broken until a later merge happened to fix it). Read-only."""
    import subprocess
    try:
        p = (runner or subprocess.run)(DEPLOY_CMD, capture_output=True, text=True, timeout=30,
                                       stdin=subprocess.DEVNULL)
        runs = json.loads(p.stdout) if p.returncode == 0 else None
    except Exception:  # noqa: BLE001 - no gh, no network: say so, never alarm
        runs = None
    if not isinstance(runs, list) or not runs:
        return ["note: site deploy: couldn't read the deploy runs (gh)"]
    finished = next((r for r in runs if r.get("status") == "completed"), None)
    if finished is None:
        return ["ok: site deploy: a deploy is under way"]
    title = (finished.get("displayTitle") or "")[:70]
    if finished.get("conclusion") in ("success", "cancelled", "skipped"):
        return [f"ok: site deploy: last finished run {finished.get('conclusion')} ({title})"]
    if runs[0] is not finished:
        return [f"note: site deploy: the last finished run failed ({title}); a newer one is under way"]
    return [f"ALERT: site deploy failed on main ({title}): the live site is behind main. Open the Actions run,"
            " fix the failing check, and merge the fix."]


def main(now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    for line in assistant_lines(now) + review_lines(now) + deploy_lines():
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
