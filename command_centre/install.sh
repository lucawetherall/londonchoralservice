#!/bin/bash
# Install (or re-install) the LCS Command Centre as a LaunchAgent on this Mac. Safe to run again.
#
#   bash command_centre/install.sh
#
# It:
#   1. makes ~/lcs-private/command-centre/{logs,cache} (mode 700);
#   2. writes ~/lcs-private/command-centre/config.json (mode 600) the first time only, asking for your
#      Tailscale login and this Mac's tailnet name; an existing config is never changed, except that
#   3. while no passkey is registered, it issues a one-time bootstrap code (only its sha256 and a 30-minute
#      expiry go in the config) and prints the code once: the first passkey registration needs it;
#   4. writes ~/Library/LaunchAgents/com.lcs.command-centre.plist (runs <repo>/.venv/bin/python -m command_centre
#      from the repo, at login, restarted if it stops, CC_DEV_LOGIN blanked, logs in
#      ~/lcs-private/command-centre/logs/, rotated by the app on start);
#   5. (re)loads it with launchctl (one retry) and checks /healthz on 127.0.0.1:8765 (with the tailnet Host);
#   6. prints the `tailscale serve` command to run yourself.
#
# It installs scripts/requirements.txt only (pinned versions; the test-only packages are in
# scripts/requirements-dev.txt). It needs no secrets and stores none. The app listens on 127.0.0.1 only; `tailscale serve` is the only way in
# from your other devices, and it adds the Tailscale-User-Login / Tailscale-User-Name headers the app checks
# (and strips any a device tries to send itself). Never turn on Tailscale Funnel for this port.
#
#   bash command_centre/install.sh --backup
#
# also writes and loads ~/Library/LaunchAgents/com.lcs.backup.plist: scripts/reports/cc_backup.py run, every
# night at 02:30 (refused until `.venv/bin/python scripts/reports/cc_backup.py init` has made the backup key).
set -euo pipefail

WITH_BACKUP=0
for arg in "$@"; do
  case "$arg" in
    --backup) WITH_BACKUP=1 ;;
    *) echo "Unknown option: $arg (the only option is --backup)" >&2; exit 2 ;;
  esac
done

LABEL="com.lcs.command-centre"
PORT=8765
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$REPO/.venv/bin/python"
PRIVATE="${LCS_PRIVATE_DIR:-$HOME/lcs-private}"
CC_DIR="$PRIVATE/command-centre"
CONFIG="$CC_DIR/config.json"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

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
echo "Installing the pinned packages from scripts/requirements.txt into .venv ..."
"$PY" -m pip install --quiet -r "$REPO/scripts/requirements.txt"

umask 077
mkdir -p "$CC_DIR/logs" "$CC_DIR/cache"
chmod 700 "$PRIVATE" "$CC_DIR" "$CC_DIR/logs" "$CC_DIR/cache"

# ---------------------------------------------------------------- config (first run only)
if [ -f "$CONFIG" ]; then
  echo "Config exists, left as it is: $CONFIG"
else
  DETECTED=""
  TS=""
  if command -v tailscale >/dev/null 2>&1; then
    TS="tailscale"
  elif [ -x "/Applications/Tailscale.app/Contents/MacOS/Tailscale" ]; then
    TS="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
  fi
  if [ -n "$TS" ]; then
    DETECTED="$("$TS" status --json 2>/dev/null | "$PY" -c 'import json,sys
try:
    print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))
except Exception:
    pass' || true)"
  fi

  LOGIN=""
  while [ -z "$LOGIN" ]; do
    read -r -p "Your Tailscale login (the email shown in the Tailscale app, e.g. owner@example.com): " LOGIN
  done
  HOSTNAME_TS=""
  while [ -z "$HOSTNAME_TS" ]; do
    if [ -n "$DETECTED" ]; then
      read -r -p "This Mac's tailnet name [$DETECTED]: " HOSTNAME_TS
      HOSTNAME_TS="${HOSTNAME_TS:-$DETECTED}"
    else
      read -r -p "This Mac's tailnet name (e.g. my-mac.tail1234.ts.net): " HOSTNAME_TS
    fi
  done

  CC_LOGIN="$LOGIN" CC_HOST="$HOSTNAME_TS" CC_CONFIG="$CONFIG" "$PY" - <<'PYEOF'
import json, os
host = os.environ["CC_HOST"].strip().rstrip(".").removeprefix("https://").split("/")[0]
cfg = {"allowed_logins": [os.environ["CC_LOGIN"].strip()], "origin": f"https://{host}", "rp_id": host,
       "passkeys": []}
path = os.environ["CC_CONFIG"]
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
print(f"Config written: {path}")
PYEOF
fi
chmod 600 "$CONFIG"
RP_ID="$(CC_CONFIG="$CONFIG" "$PY" -c 'import json,os; print(json.load(open(os.environ["CC_CONFIG"]))["rp_id"])')"

# ---------------------------------------------------------------- bootstrap code (until the first passkey)
BOOTSTRAP_MSG=""
if CC_CONFIG="$CONFIG" "$PY" -c 'import json,os,sys; sys.exit(1 if json.load(open(os.environ["CC_CONFIG"])).get("passkeys") else 0)'; then
  BOOTSTRAP_MSG="$(cd "$REPO" && "$PY" -m command_centre.bootstrap --new-bootstrap)"
else
  echo "A passkey is registered: no bootstrap code needed."
fi

# ---------------------------------------------------------------- LaunchAgent
mkdir -p "$HOME/Library/LaunchAgents"
CC_PLIST="$PLIST" CC_LABEL="$LABEL" CC_REPO="$REPO" CC_PY="$PY" CC_LOGS="$CC_DIR/logs" "$PY" - <<'PYEOF'
import os, plistlib
plist = {
    "Label": os.environ["CC_LABEL"],
    "ProgramArguments": [os.environ["CC_PY"], "-m", "command_centre"],
    "WorkingDirectory": os.environ["CC_REPO"],
    "RunAtLoad": True,
    "KeepAlive": True,
    "ThrottleInterval": 10,
    "ProcessType": "Interactive",
    "EnvironmentVariables": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONUNBUFFERED": "1", "CC_DEV_LOGIN": ""},
    "StandardOutPath": os.path.join(os.environ["CC_LOGS"], "command-centre.out.log"),
    "StandardErrorPath": os.path.join(os.environ["CC_LOGS"], "command-centre.err.log"),
}
path = os.environ["CC_PLIST"]
tmp = path + ".tmp"
with open(tmp, "wb") as f:
    plistlib.dump(plist, f)
os.chmod(tmp, 0o644)
os.replace(tmp, path)
print(f"LaunchAgent written: {path}")
PYEOF

DOMAIN="gui/$(id -u)"
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
if ! launchctl bootstrap "$DOMAIN" "$PLIST"; then
  echo "launchctl bootstrap failed; retrying once in 3 seconds ..." >&2
  sleep 3
  launchctl bootstrap "$DOMAIN" "$PLIST"
fi
launchctl enable "$DOMAIN/$LABEL" 2>/dev/null || true

printf "Waiting for the app"
for _ in $(seq 1 20); do
  if curl -fsS -H "Host: $RP_ID" "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
    echo " ... running on 127.0.0.1:$PORT."
    break
  fi
  printf "."
  sleep 1
done
if ! curl -fsS -H "Host: $RP_ID" "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
  echo
  echo "The app didn't answer. See $CC_DIR/logs/command-centre.err.log" >&2
  exit 1
fi

# ---------------------------------------------------------------- nightly backup (optional: --backup)
BACKUP_LABEL="com.lcs.backup"
BACKUP_PLIST="$HOME/Library/LaunchAgents/$BACKUP_LABEL.plist"
if [ "$WITH_BACKUP" = 1 ]; then
  if ! CC_CONFIG="$CONFIG" "$PY" -c 'import json,os,sys; b=json.load(open(os.environ["CC_CONFIG"])).get("backup") or {}; sys.exit(0 if b.get("recipient") else 1)'; then
    echo "No backup key yet. First run: cd $REPO && .venv/bin/python scripts/reports/cc_backup.py init" >&2
    echo "(store the key it prints in your password manager), then run this again with --backup." >&2
    exit 1
  fi
  CC_PLIST="$BACKUP_PLIST" CC_LABEL="$BACKUP_LABEL" CC_REPO="$REPO" CC_PY="$PY" CC_LOGS="$CC_DIR/logs" "$PY" - <<'PYEOF'
import os, plistlib
plist = {
    "Label": os.environ["CC_LABEL"],
    "ProgramArguments": [os.environ["CC_PY"], os.path.join(os.environ["CC_REPO"], "scripts", "reports", "cc_backup.py"), "run"],
    "WorkingDirectory": os.environ["CC_REPO"],
    "StartCalendarInterval": {"Hour": 2, "Minute": 30},
    "ProcessType": "Background",
    "EnvironmentVariables": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONUNBUFFERED": "1"},
    "StandardOutPath": os.path.join(os.environ["CC_LOGS"], "backup.out.log"),
    "StandardErrorPath": os.path.join(os.environ["CC_LOGS"], "backup.err.log"),
}
path = os.environ["CC_PLIST"]
tmp = path + ".tmp"
with open(tmp, "wb") as f:
    plistlib.dump(plist, f)
os.chmod(tmp, 0o644)
os.replace(tmp, path)
print(f"Backup LaunchAgent written: {path} (02:30 nightly)")
PYEOF
  launchctl bootout "$DOMAIN/$BACKUP_LABEL" 2>/dev/null || true
  launchctl bootstrap "$DOMAIN" "$BACKUP_PLIST"
  launchctl enable "$DOMAIN/$BACKUP_LABEL" 2>/dev/null || true
  echo "Nightly backup loaded. Tap Back up now on the Health page once to check it works."
fi

SOCK="$CC_DIR/run/cc.sock"
cat <<EOF

Last step (once; Tailscale remembers it across restarts). Run:

  tailscale serve --bg --https=443 http://127.0.0.1:$PORT

(If the tailscale command isn't found, use /Applications/Tailscale.app/Contents/MacOS/Tailscale in its place.)

Alternative, to be verified on this Mac first: serve the app on a Unix socket in a mode-700 directory, so
other local processes can't reach it over TCP. Change the LaunchAgent's ProgramArguments to end in
"-m command_centre --uds $SOCK", reload it, then run:

  tailscale serve --bg --https=443 unix:$SOCK

Check that https://$RP_ID/ loads before relying on it; if it doesn't, go back to the TCP command above.

Then open https://$RP_ID/passkeys on your iPhone and register a passkey with the bootstrap code below. The
first time the app reads the bank, macOS may ask whether python may use the "lcs-starling-read" Keychain
item: choose Always Allow.

The phone app (Tailscale only; the phone doesn't keep the VPN on):
  1. Tailscale admin console -> DNS: turn on MagicDNS and HTTPS certificates. The Home Screen app and Web
     Push need the real ts.net certificate.
  2. On the iPhone, with Tailscale connected, open https://$RP_ID/ in Safari: Share -> Add to Home Screen.
  3. Shortcuts app: a shortcut "LCS" with two actions, Tailscale -> Connect, then Open URL https://$RP_ID/.
     Add it to the Home Screen and open the app with it. Optional: a second shortcut, Tailscale -> Disconnect.
  4. In the app: More -> This device -> Enable notifications, then Approve this device (Face ID). macOS may
     ask once whether python may use the "lcs-command-centre-vapid" Keychain item: Always Allow.
     Notifications arrive with the VPN off, through Apple's push service (the Mac sends them over its normal
     internet connection). They show on the lock screen: turn off lock-screen previews for this app in
     iOS Settings if you prefer. With the VPN off the app shows the last Today and Money pages, marked
     "Couldn't reach the Mac (showing the copy from <time>)", for up to 7 days; actions need the VPN.
     This device -> Clear offline copies deletes them (so does turning notifications off).

Backups (once, in Terminal: init refuses to print the key anywhere else):
  .venv/bin/python scripts/reports/cc_backup.py init  (store the printed AGE-SECRET-KEY line in your password
  manager; it is shown once), then: bash command_centre/install.sh --backup
The next morning, check that Health shows the backup and that the file has reached iCloud Drive (macOS can
hold back a background job's writes there); if not, set backup.target in the config to a local folder.
EOF
if [ -n "$BOOTSTRAP_MSG" ]; then
  echo
  echo "$BOOTSTRAP_MSG"
  echo "If it expires first: cd $REPO && .venv/bin/python -m command_centre.bootstrap --new-bootstrap"
fi
