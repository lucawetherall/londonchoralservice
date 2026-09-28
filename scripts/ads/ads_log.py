"""Where the Ads scripts log applied changes, and how they add a row.

The log is logs/ads-changes.md in the repo. The Command Centre runs proposal-aware scripts from a copy of a
commit on GitHub's main in a temp folder, where a path relative to __file__ would miss the real log, so it sets
LCS_ADS_LOG to the repo's log. Without it, the path is the usual one relative to this file.

Either way the log must be a repo's own logs/ads-changes.md (a folder holding .git and scripts/ads/ads_log.py),
a plain file reached through no symlink: anything else is refused before a change is made, so an applied change
can't be logged somewhere else or written through a link. The tests add their temp folders to TEST_LOG_ROOTS (a
module variable; nothing in the environment can).

    from ads_log import append_row
    append_row(f"| {now} | {resource} | field | old → new | reason | `scripts/ads/x.py` |")
"""

import os
import stat
from pathlib import Path

MARKER = "|---|---|---|---|---|---|\n"
TEST_LOG_ROOTS = []  # tests only: folders a log may sit in


def _refuse(path, why):
    raise SystemExit(f"the change log at {path} {why}; nothing applied")


def log_path():
    """The checked log path (SystemExit if it isn't a repo's own logs/ads-changes.md, or a symlink is involved)."""
    override = os.environ.get("LCS_ADS_LOG", "").strip()
    path = Path(override) if override else Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
    if not path.is_absolute():
        _refuse(path, "must be an absolute path")
    try:
        if stat.S_ISLNK(os.lstat(path).st_mode):
            _refuse(path, "is a symlink")
    except FileNotFoundError:
        pass
    try:
        if stat.S_ISLNK(os.lstat(path.parent).st_mode):
            _refuse(path, "sits in a symlinked folder")
    except FileNotFoundError:
        pass
    real = Path(os.path.realpath(path))
    if any(real.is_relative_to(Path(os.path.realpath(r))) for r in TEST_LOG_ROOTS):
        return path
    repo = real.parent.parent
    if not (real.name == "ads-changes.md" and real.parent.name == "logs" and (repo / ".git").exists()
            and (repo / "scripts" / "ads" / "ads_log.py").is_file()):
        _refuse(path, "isn't a repo's logs/ads-changes.md")
    return path


def _read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, encoding="utf-8") as f:
        return f.read()


def check_log():
    """Before applying anything: the log must be the repo's own, exist and carry the change table, so an applied
    change is never left unlogged."""
    path = log_path()
    try:
        text = _read(path)
    except OSError:
        raise SystemExit(f"can't read the change log at {path}; nothing applied") from None
    if MARKER not in text:
        raise SystemExit(f"{path.name} has no change table; nothing applied")
    return path


def append_row(row):
    """Insert one table row under the header (the log is newest first). Refuses a log without the table."""
    row = row.rstrip("\n") + "\n"
    path = log_path()
    text = _read(path)
    if MARKER not in text:
        raise SystemExit(f"{path.name} has no change table; the change was applied but not logged")
    fd = os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text.replace(MARKER, MARKER + row, 1))
    return path
