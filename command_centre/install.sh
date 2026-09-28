#!/bin/bash
# Install (or re-install) the LCS Command Centre as a LaunchAgent on this Mac. Safe to run again.
#
#   bash command_centre/install.sh
#
# It:
#   1. makes ~/lcs-private/command-centre/{logs,cache} (mode 700);
#   2. writes ~/lcs-private/command-centre/config.json (mode 600) the first time only, asking for your
#      Tailscale login and this Mac's tailnet name; an existing config is never changed;
#   3. writes ~/Library/LaunchAgents/com.lcs.command-centre.plist (runs <repo>/.venv/bin/python -m command_centre
#      from the repo, at login, restarted if it stops, logs in ~/lcs-private/command-centre/logs/);
#   4. (re)loads it with launchctl and checks http://127.0.0.1:8765/healthz;
#   5. prints the one `tailscale serve` command to run yourself.
#
# It needs no secrets and stores none. The app listens on 127.0.0.1 only; `tailscale serve` is the only way in
# from your other devices, and it adds the Tailscale-User-Login / Tailscale-User-Name headers the app checks
# (and strips any a device tries to send itself). Never turn on Tailscale Funnel for this port.
set -euo pipefail

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
if ! "$PY" -c "import starlette, jinja2, uvicorn, webauthn" 2>/dev/null; then
  echo "Installing the Command Centre's packages into .venv ..."
  "$PY" -m pip install --quiet -r "$REPO/scripts/requirements.txt"
fi

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
    "EnvironmentVariables": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONUNBUFFERED": "1"},
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
launchctl bootstrap "$DOMAIN" "$PLIST"
launchctl enable "$DOMAIN/$LABEL" 2>/dev/null || true

printf "Waiting for the app"
for _ in $(seq 1 20); do
  if curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
    echo " ... running on 127.0.0.1:$PORT."
    break
  fi
  printf "."
  sleep 1
done
if ! curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
  echo
  echo "The app didn't answer. See $CC_DIR/logs/command-centre.err.log" >&2
  exit 1
fi

cat <<EOF

Last step (once; Tailscale remembers it across restarts). Run:

  tailscale serve --bg --https=443 http://127.0.0.1:$PORT

(If the tailscale command isn't found, use /Applications/Tailscale.app/Contents/MacOS/Tailscale in its place.)

Then open https://$(CC_CONFIG="$CONFIG" "$PY" -c 'import json,os; print(json.load(open(os.environ["CC_CONFIG"]))["rp_id"])')/passkeys
on your iPhone and register a passkey. The first time the app reads the bank, macOS may ask whether python
may use the "lcs-starling-read" Keychain item: choose Always Allow.
EOF
