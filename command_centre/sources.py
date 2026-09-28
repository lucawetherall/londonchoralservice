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
        ("Static dashboard", p / "dashboard.html", None),
        ("Bookings ledger", Path(os.environ.get("LCS_BOOKINGS_CSV") or p / "bookings.csv"), None),
        ("Singer invoices", p / "singer-invoices.csv", None),
        ("Enquiry pipeline", p / "enquiries.csv", None),
        ("Books cache (cc_sync.py books)", auth.config_dir() / "cache" / "books.json", BOOKS_STALE),
        ("Diary cache (the daily pass)", calendar_path(), CACHE_STALE),
        ("Drafts cache (the assistant)", auth.config_dir() / "cache" / "drafts.json", CACHE_STALE),
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


def branch_check(branch):
    return check("Git branch", branch == "main", f"serving checkout on {branch or 'a detached HEAD'}")
