"""Where the Ads scripts log applied changes, and how they add a row.

The log is logs/ads-changes.md in the repo. The Command Centre runs proposal-aware scripts from an archived copy
of an origin/main commit in a temp folder, where a path relative to __file__ would miss the real log, so it sets
LCS_ADS_LOG to the repo's log. Without it, the path is the usual one relative to this file.

    from ads_log import append_row
    append_row(f"| {now} | {resource} | field | old → new | reason | `scripts/ads/x.py` |")
"""

import os
from pathlib import Path

MARKER = "|---|---|---|---|---|---|\n"


def log_path():
    override = os.environ.get("LCS_ADS_LOG", "").strip()
    return Path(override) if override else Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"


def check_log():
    """Before applying anything: the log must exist and carry the change table, so an applied change is never
    left unlogged."""
    path = log_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise SystemExit(f"can't read the change log at {path}; nothing applied") from None
    if MARKER not in text:
        raise SystemExit(f"{path.name} has no change table; nothing applied")
    return path


def append_row(row):
    """Insert one table row under the header (the log is newest first). Refuses a log without the table."""
    row = row.rstrip("\n") + "\n"
    path = log_path()
    text = path.read_text(encoding="utf-8")
    if MARKER not in text:
        raise SystemExit(f"{path.name} has no change table; the change was applied but not logged")
    path.write_text(text.replace(MARKER, MARKER + row, 1), encoding="utf-8")
    return path
