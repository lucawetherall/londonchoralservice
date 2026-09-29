"""File readers for the phase-2 pages: caches, archived reports, scheduled-task metadata and health checks.

Read-only. Paths are worked out at call time from auth.private_dir() (LCS_PRIVATE_DIR moves them) and HOME,
so the tests point them at temp folders. Nothing here opens a credential: the Google ADC file and the
Starling token are checked for existence only (the token not at all: the Starling check goes through the
GET-only client), and the MCP config is parsed only for its server names, whose values are dropped.
"""

import datetime
import json
import os
import re
import shutil
import stat
import threading
from pathlib import Path
from zoneinfo import ZoneInfo

from . import auth

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()
LONDON = ZoneInfo("Europe/London")
REPORT_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.txt$")
REPORT_MAX = 2 * 1024 * 1024
FRONTMATTER_LINES = 40
MCP_NAMES = ("zoho-mail", "zoho-books")
DISK_LOW_GB = 5
ASSISTANT_STALE = datetime.timedelta(hours=3)
WEEKLY_STALE = datetime.timedelta(days=8)
BOOKS_STALE = datetime.timedelta(hours=24)  # the refresh job writes it every 30 minutes, 07:00-22:00
CACHE_STALE = datetime.timedelta(hours=36)  # the daily pass writes the diary and syncs the drafts once a day
DASHBOARD_STALE = datetime.timedelta(hours=36)  # the refresh job rewrites it every 30 minutes, and the daily pass
#                                             (the refresh job also writes the marketing cache daily)


def private():
    return auth.private_dir()


def mtime(path):
    """The file's modification time (London), or None when it doesn't exist."""
    try:
        return datetime.datetime.fromtimestamp(Path(path).stat().st_mtime, LONDON)
    except FileNotFoundError:
        return None


def read_json(path):
    """(value, mtime), or None when the file doesn't exist. Other errors propagate (the panel shows the type)."""
    try:
        with open(path, encoding="utf-8") as f:
            value = json.load(f)
    except FileNotFoundError:
        return None
    return value, mtime(path)


# ---------------------------------------------------------------- caches


def ads_summary():
    found = read_json(private() / "ads-summary.json")
    if found is None:
        return None
    value, _ = found
    if not isinstance(value, dict):
        raise ValueError("ads-summary.json is not an object")
    return value


def gclid_cache():
    found = read_json(private() / "gclid-campaigns.json")
    return found[0] if found and isinstance(found[0], dict) else {}


def calendar_path():
    return auth.config_dir() / "cache" / "calendar.json"


def calendar_cache():
    """(entries, synced at) from the calendar cache, or None: the diary isn't synced yet."""
    found = read_json(calendar_path())
    if found is None:
        return None
    entries, when = found
    if not isinstance(entries, list):
        raise ValueError("calendar.json is not a list")
    return entries, when


def marketing_path():
    return auth.config_dir() / "cache" / "marketing.json"


def marketing_cache():
    """The marketing cache (cc_sync.py marketing, once a day from the refresh job), or None: not synced yet."""
    found = read_json(marketing_path())
    if found is None:
        return None
    value, _ = found
    if not isinstance(value, dict):
        raise ValueError("marketing.json is not an object")
    return value


# ---------------------------------------------------------------- reports


def reports_dir():
    return private() / "reports"


def report_list():
    """[{name, date, size, modified}] for the archived Monday reports, newest first."""
    d = reports_dir()
    if not d.is_dir():
        return []
    out = []
    for p in d.iterdir():
        if not REPORT_NAME.fullmatch(p.name):
            continue
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if not stat.S_ISREG(st.st_mode):
            continue
        out.append({"name": p.name, "date": p.name[:10], "size": st.st_size,
                    "modified": datetime.datetime.fromtimestamp(st.st_mtime, LONDON)})
    return sorted(out, key=lambda r: r["name"], reverse=True)


def report_text(name):
    """One report's text, or None when the name isn't YYYY-MM-DD.txt, the file is missing, a symlink, not a
    regular file, outside the reports folder or over 2 MB."""
    if not isinstance(name, str) or not REPORT_NAME.fullmatch(name):
        return None
    d = reports_dir()
    path = d / name
    try:
        st = os.lstat(path)
        if not stat.S_ISREG(st.st_mode) or st.st_size > REPORT_MAX:
            return None
        if path.resolve().parent != d.resolve():
            return None
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return None
    with os.fdopen(fd, "rb") as f:
        return f.read(REPORT_MAX).decode("utf-8", errors="replace")


# ---------------------------------------------------------------- runs


def tasks_dir():
    return Path(os.environ.get("CC_SCHEDULED_TASKS_DIR") or HOME / ".claude" / "scheduled-tasks")


def frontmatter(path):
    """The name and description from a SKILL.md's frontmatter; the prompt body is never read."""
    meta = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        if f.readline().strip() != "---":
            return meta
        for _ in range(FRONTMATTER_LINES):
            line = f.readline()
            if not line or line.strip() == "---":
                break
            key, sep, value = line.partition(":")
            if sep and key.strip() in ("name", "description"):
                meta[key.strip()] = value.strip()[:200]
    return meta


def scheduled_tasks():
    d = tasks_dir()
    if not d.is_dir():
        return []
    out = []
    for task in sorted(d.iterdir()):
        skill = task / "SKILL.md"
        if task.is_dir() and skill.is_file():
            meta = frontmatter(skill)
            out.append({"name": meta.get("name") or task.name, "description": meta.get("description", ""),
                        "changed": mtime(skill)})
    return out


def run_proxies(now):
    """The last-modified times of the files the scheduled runs write: the nearest thing to a run history."""
    p = private()
    reports = report_list()
    newest = reports_dir() / reports[0]["name"] if reports else None
    daytime = 9 <= now.hour <= 21
    rows = [
        ("Enquiry assistant state", p / "assistant-state.json", ASSISTANT_STALE if daytime else None),
        ("Ads summary (Monday review)", p / "ads-summary.json", WEEKLY_STALE),
        ("Newest Monday report", newest, WEEKLY_STALE),
        ("Static dashboard", p / "dashboard.html", DASHBOARD_STALE),
        ("Bookings ledger", Path(os.environ.get("LCS_BOOKINGS_CSV") or p / "bookings.csv"), None),
        ("Singer invoices", p / "singer-invoices.csv", None),
        ("Enquiry pipeline", p / "enquiries.csv", None),
        ("Books cache (cc_sync.py books)", auth.config_dir() / "cache" / "books.json", BOOKS_STALE),
        ("Diary cache (the daily pass)", calendar_path(), CACHE_STALE),
        ("Drafts cache (the assistant)", auth.config_dir() / "cache" / "drafts.json", CACHE_STALE),
        ("Marketing cache (cc_sync.py marketing, daily)", marketing_path(), CACHE_STALE),
    ]
    out = []
    for label, path, limit in rows:
        when = mtime(path) if path else None
        age = None
        if when is not None and now >= when:
            age = "under an hour ago" if now - when < datetime.timedelta(hours=1) else age_words(now - when)
        out.append({"label": label, "when": when, "age": age,
                    "stale": bool(limit and (when is None or now - when > limit))})
    state = read_json(p / "assistant-state.json")
    checked = state[0].get("last_checked") if state and isinstance(state[0], dict) else None
    try:
        checked = datetime.datetime.fromisoformat(str(checked).replace("Z", "+00:00")) if checked else None
    except ValueError:
        checked = str(checked)[:25]
    return out, checked


# ---------------------------------------------------------------- checks


def check(name, ok, detail):
    return {"name": name, "ok": ok, "detail": detail}


def adc_check():
    """The Google Application Default Credentials file exists (never opened)."""
    path = HOME / ".config" / "gcloud" / "application_default_credentials.json"
    present = path.exists()
    return check("Google sign-in", present, "Google credentials file present" if present
                 else "No Google credentials file: the owner re-runs the gcloud sign-in")


def mcp_names():
    """MCP server names configured for this repo (~/.claude.json's project entry, the top level, and the
    repo's .mcp.json). Only the names are kept."""
    names = set()
    try:
        with open(HOME / ".claude.json", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {}
    if isinstance(cfg, dict):
        for block in (cfg.get("mcpServers"), ((cfg.get("projects") or {}).get(str(REPO)) or {}).get("mcpServers")):
            if isinstance(block, dict):
                names.update(str(k) for k in block)
    try:
        with open(REPO / ".mcp.json", encoding="utf-8") as f:
            repo_cfg = json.load(f)
        if isinstance(repo_cfg, dict) and isinstance(repo_cfg.get("mcpServers"), dict):
            names.update(str(k) for k in repo_cfg["mcpServers"])
    except (OSError, ValueError):
        pass
    del cfg
    return names


def mcp_checks():
    names = mcp_names()
    return [check(f"MCP {n}", n in names, "configured" if n in names else "not configured") for n in MCP_NAMES]


BACKUP_STALE = datetime.timedelta(hours=36)


def backup_status(now):
    """The last backup, from <private>/command-centre/backup-state.json (written by scripts/reports/cc_backup.py):
    {"at", "age", "name", "size", "stale", "configured"}. The backup folder itself isn't listed (iCloud may hold
    it offline). Only the public recipient's presence is checked; nothing secret is read."""
    try:
        cfg = auth.load_config()
    except (OSError, ValueError):
        cfg = {}
    block = cfg.get("backup") if isinstance(cfg.get("backup"), dict) else {}
    found = read_json(auth.config_dir() / "backup-state.json")
    state = found[0] if found and isinstance(found[0], dict) else {}
    try:
        at = datetime.datetime.fromisoformat(str(state.get("at"))).astimezone(LONDON) if state.get("at") else None
    except ValueError:
        at = None
    age = now - at if at else None
    return {"at": at, "age": age, "name": str(state.get("name") or "")[:80], "size": state.get("size"),
            "stale": age is None or age > BACKUP_STALE, "configured": bool(block.get("recipient"))}


def age_words(age):
    hours = int(age.total_seconds() // 3600)
    return f"{hours} hours ago" if hours < 48 else f"{hours // 24} days ago"


def backup_check(now):
    b = backup_status(now)
    if not b["configured"]:
        return check("Backup", False, "no backup key yet: run scripts/reports/cc_backup.py init on the Mac")
    if b["at"] is None:
        return check("Backup", False, "no backup yet: tap Back up now, then install the nightly LaunchAgent")
    detail = f"last {age_words(b['age'])}" + (" (over 36 hours: check the nightly LaunchAgent)" if b["stale"] else "")
    return check("Backup", not b["stale"], detail)


def fingerprint_check(now=None):
    present = (private() / "fingerprint.key").exists()
    if not present:
        return check("Fingerprint key", False, "fingerprint.key not found")
    b = backup_status(now or datetime.datetime.now(LONDON))
    if b["at"] is None:
        return check("Fingerprint key", None, "present; not in a backup yet")
    return check("Fingerprint key", not b["stale"], f"present; in the encrypted backup of {age_words(b['age'])}")


def disk_check():
    usage = shutil.disk_usage(private() if private().exists() else HOME)
    free = usage.free / 1e9
    return check("Disk", free >= DISK_LOW_GB, f"{free:,.1f} GB free of {usage.total / 1e9:,.0f} GB")


def state_log_check():
    """The state log (~/lcs-private/events.jsonl, lcs_events) for the Health page: lines, when it was last written,
    whether the chain is whole, and events.py verify's problems as counts only (lcs_events.log_problem: unreadable,
    a broken chain, skipped lines; events.note_problems: facts whose note clause is missing, notes-checked hashes no
    clause matches). Never an id, a note or a name. "note" (ok None) while there is no log yet."""
    import sys
    bookings = str(REPO / "scripts" / "bookings")
    if bookings not in sys.path:
        sys.path.insert(0, bookings)
    import events as state_events
    import lcs_events
    events, stats = lcs_events.read()
    problem = lcs_events.log_problem(stats)
    if stats.get("unreadable"):
        return check("State log", False, f"{problem}; run events.py verify")
    if not stats["lines"] and not stats["skipped"]:
        return check("State log", None, "no state log yet: the facts are read from the notes until the events "
                                        "migration is applied")
    when = "never"
    if stats["last_at"]:
        at = datetime.datetime.strptime(stats["last_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        when = f"{at.astimezone(LONDON):%-d %b %Y %H:%M}"
    chain = "chain whole" if stats["chain_ok"] else f"chain broken at line {stats['broken_at']}"
    detail = f"{stats['lines']} line{'' if stats['lines'] == 1 else 's'}, {chain}, last written {when}"
    notes = state_events.note_problems(events)
    missing = sum(1 for n in notes if n.startswith("fact without its note"))
    stale = len(notes) - missing
    extra = [x for x in (
        f"{stats['skipped']} line{'' if stats['skipped'] == 1 else 's'} skipped" if stats["skipped"] else "",
        f"{missing} fact{'' if missing == 1 else 's'} without {'its' if missing == 1 else 'their'} note" if missing else "",
        f"{stale} notes-checked hash{'' if stale == 1 else 'es'} no clause matches" if stale else "") if x]
    if extra:
        return check("State log", False, f"{detail}; {', '.join(extra)}: run events.py verify")
    return check("State log", not problem, detail)


def branch_check(branch):
    return check("Git branch", branch == "main", f"serving checkout on {branch or 'a detached HEAD'}")


# ---------------------------------------------------------------- the sync strip (every page)


_OUTCOMES = {}  # sync name -> {"ok": bool, "at": aware datetime}: the latest attempt in this process
_OUTCOMES_LOCK = threading.Lock()


def record_outcome(name, ok, at=None):
    """The refresh job and the sync-now action note each attempt at a sync (books, marketing, dashboard), so the
    strip can say "failed" when the latest attempt failed after the last good one. In memory only: a restart
    forgets it, and the file times still say how old the data is."""
    with _OUTCOMES_LOCK:
        _OUTCOMES[name] = {"ok": bool(ok), "at": at or datetime.datetime.now(LONDON)}


def outcomes():
    with _OUTCOMES_LOCK:
        return {k: dict(v) for k, v in _OUTCOMES.items()}


def forget_outcomes():
    """Tests only."""
    with _OUTCOMES_LOCK:
        _OUTCOMES.clear()


def books_cache_path():
    return auth.config_dir() / "cache" / "books.json"


def drafts_cache_path():
    return auth.config_dir() / "cache" / "drafts.json"


def dashboard_path():
    return private() / "dashboard.html"


# (key, label, the file whose time is the last good sync, stale after, what a stale or failed chip does: a sync-now
# source the app can run, or None when only a scheduled run writes it and the chip links to Health instead)
SYNCS = (
    ("books", "Books", books_cache_path, BOOKS_STALE, "books"),
    ("drafts", "Drafts", drafts_cache_path, CACHE_STALE, None),
    ("diary", "Diary", calendar_path, CACHE_STALE, None),
    ("ads", "Ads", lambda: private() / "ads-summary.json", WEEKLY_STALE, None),
    ("marketing", "Marketing", marketing_path, CACHE_STALE, "marketing"),
)
SYNC_WHY = {  # the chip's title: where the data comes from
    "bank": "Starling, read-only, on the pages that show the bank (ten-minute cache)",
    "books": "cc_sync.py books, every 30 minutes from 07:00 to 22:00",
    "drafts": "the enquiry assistant's daily pass reads Zoho Drafts; the app can't read Mail",
    "diary": "the enquiry assistant's daily pass reads Google Calendar; the app can't read the calendar",
    "ads": "the Monday review writes the Ads summary",
    "marketing": "cc_sync.py marketing, once a day from 07:00",
}


def short_time(when, now):
    """"07:30" today, "Sat 07:30" within the last week, else "12 Sep"."""
    when = when.astimezone(LONDON)
    now = now.astimezone(LONDON) if now.tzinfo else now.replace(tzinfo=LONDON)
    if when.date() == now.date():
        return f"{when:%H:%M}"
    if now - when < datetime.timedelta(days=6):
        return f"{when:%a %H:%M}"
    return f"{when.day} {when:%b}"


def sync_chips(now, bank):
    """The strip's chips, in order: Bank, Books, Drafts, Diary, Ads, Marketing. Each {"key", "label", "shown" (the
    last good time, short), "tone" ("ok", "stale", "failed" or "off"), "sync" (a sync-now source, or None), "why"}.

    `bank` is data.Data.bank_status(): {"good" (a datetime or None), "failed" (a datetime or None, only when the
    latest read failed), "connected"}. The bank is "failed" while its latest read failed (Bank unreachable), "off"
    with no Starling token or before any page has read it, else "ok"; it is never "stale" (the pages read it when
    they need it). A cache is "failed" when this process's latest attempt at it failed after its last good write,
    "stale" past its limit (sources' BOOKS_STALE, CACHE_STALE, WEEKLY_STALE) or when it was never written, else "ok"."""
    now = now if now.tzinfo else now.replace(tzinfo=LONDON)
    chips = []
    good, failed = bank.get("good"), bank.get("failed")
    if failed is not None:
        tone = "failed"
    elif good is not None:
        tone = "ok"
    else:
        tone = "off"
    shown = short_time(good, now) if good else ("not connected" if bank.get("connected") is False else "not read yet")
    chips.append({"key": "bank", "label": "Bank", "shown": shown, "tone": tone,
                  "sync": "bank" if tone == "failed" else None, "why": SYNC_WHY["bank"]})
    tried = outcomes()
    for key, label, path, limit, sync in SYNCS:
        when = mtime(path())
        last = tried.get(key)
        if last is not None and not last["ok"] and (when is None or last["at"] > when):
            tone = "failed"
        elif when is None or now - when > limit:
            tone = "stale"
        else:
            tone = "ok"
        chips.append({"key": key, "label": label, "shown": short_time(when, now) if when else "never", "tone": tone,
                      "sync": sync if tone != "ok" else None, "why": SYNC_WHY[key]})
    return chips
