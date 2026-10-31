#!/bin/bash
# Install (or re-install) the nightly encrypted backup of ~/lcs-private as a LaunchAgent on this Mac. Safe to run
# again.
#
#   bash scripts/reports/install_backup.sh
#
# It writes ~/Library/LaunchAgents/com.lcs.backup.plist, which runs
# <repo>/.venv/bin/python <repo>/scripts/reports/backup.py run every night at 02:30 (logs in ~/lcs-private/logs/,
# mode 700), and (re)loads it with launchctl. It refuses until `.venv/bin/python scripts/reports/backup.py init`
# has made the backup key (run that once yourself, in Terminal: it prints the key once, for your password manager).
# Run it from the main checkout, not a worktree: the LaunchAgent runs the code where this script sits. It needs no
# secrets and stores none.
set -euo pipefail

if [ "$#" -gt 0 ]; then
  echo "Unknown option: $1 (this script takes none)" >&2
  exit 2
fi

LABEL="com.lcs.backup"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$REPO/.venv/bin/python"
PRIVATE="${LCS_PRIVATE_DIR:-$HOME/lcs-private}"
LOGS="$PRIVATE/logs"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

case "$REPO" in
  */.claude/worktrees/*)
    echo "Run this from the main checkout, not a worktree: $REPO" >&2
    exit 1 ;;
esac

if [ ! -x "$PY" ]; then
  echo "No virtualenv at $REPO/.venv. Create it first:" >&2
  echo "  python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt" >&2
  exit 1
fi

if ! LCS_PRIVATE_DIR="$PRIVATE" "$PY" -c 'import json,os,sys
try:
    b = json.load(open(os.path.join(os.environ["LCS_PRIVATE_DIR"], "backup.json")))
except (OSError, ValueError):
    sys.exit(1)
sys.exit(0 if isinstance(b, dict) and b.get("recipient") else 1)'; then
  echo "No backup key yet. First run, in Terminal: cd $REPO && .venv/bin/python scripts/reports/backup.py init" >&2
  echo "(store the key it prints in your password manager), then run this again." >&2
  exit 1
fi

umask 077
mkdir -p "$LOGS" "$HOME/Library/LaunchAgents"
chmod 700 "$PRIVATE" "$LOGS"

# launchd starts an agent with a bare PATH; the backup needs nothing beyond the system folders (osascript for a
# failure notification).
B_PLIST="$PLIST" B_LABEL="$LABEL" B_REPO="$REPO" B_PY="$PY" B_LOGS="$LOGS" "$PY" - <<'PYEOF'
import os, plistlib
plist = {
    "Label": os.environ["B_LABEL"],
    "ProgramArguments": [os.environ["B_PY"], os.path.join(os.environ["B_REPO"], "scripts", "reports", "backup.py"), "run"],
    "WorkingDirectory": os.environ["B_REPO"],
    "StartCalendarInterval": {"Hour": 2, "Minute": 30},
    "ProcessType": "Background",
    "EnvironmentVariables": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONUNBUFFERED": "1"},
    "StandardOutPath": os.path.join(os.environ["B_LOGS"], "backup.out.log"),
    "StandardErrorPath": os.path.join(os.environ["B_LOGS"], "backup.err.log"),
}
path = os.environ["B_PLIST"]
tmp = path + ".tmp"
with open(tmp, "wb") as f:
    plistlib.dump(plist, f)
os.chmod(tmp, 0o644)
os.replace(tmp, path)
print(f"Backup LaunchAgent written: {path} (02:30 nightly)")
PYEOF

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST"
launchctl enable "$DOMAIN/$LABEL" 2>/dev/null || true

cat <<EOF
Nightly backup loaded. Check it once now:
  cd $REPO && .venv/bin/python scripts/reports/backup.py run
The next morning, check that ~/lcs-private/backup-state.json names last night's backup and that the file has
reached iCloud Drive (macOS can hold back a background job's writes there); if not, set "target" in
~/lcs-private/backup.json to a local folder.
EOF
