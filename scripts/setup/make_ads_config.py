#!/usr/bin/env python3
"""Create ~/.config/lcs/google-ads.yaml for the google-ads Python library.

Runs the OAuth installed-app flow with the adwords scope using
~/.config/lcs/client_secret.json, then writes client_id, client_secret,
refresh_token and use_proto_plus to the yaml file (chmod 600). Prompts
(hidden input) for the developer token if the file doesn't have one yet.

Prints only "Saved google-ads.yaml" -- never the token or secret.

Run from the repo root with the venv active:
    source .venv/bin/activate
    python scripts/setup/make_ads_config.py
"""

import json
import os
from getpass import getpass
from pathlib import Path

import yaml
from google_auth_oauthlib.flow import InstalledAppFlow

CONFIG_DIR = Path.home() / ".config" / "lcs"
CLIENT_SECRET = CONFIG_DIR / "client_secret.json"
OUTPUT = CONFIG_DIR / "google-ads.yaml"
SCOPES = ["https://www.googleapis.com/auth/adwords"]


def main():
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), scopes=SCOPES)
    # prompt=consent forces Google to issue a refresh token even on re-runs.
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    if not creds.refresh_token:
        raise SystemExit("No refresh token returned; re-run and approve access.")

    client = json.loads(CLIENT_SECRET.read_text())
    client = client.get("installed") or client.get("web")

    config = {
        "client_id": client["client_id"],
        "client_secret": client["client_secret"],
        "refresh_token": creds.refresh_token,
        "use_proto_plus": True,
    }
    # Keep any keys added later (developer_token, login_customer_id).
    if OUTPUT.exists():
        existing = yaml.safe_load(OUTPUT.read_text()) or {}
        existing.update(config)
        config = existing

    # load_from_storage() refuses to load without a developer token.
    if not config.get("developer_token"):
        token = getpass("Google Ads developer token (hidden, Enter to skip): ").strip()
        if token:
            config["developer_token"] = token

    # Create with 600 from the start so the secret is never world-readable.
    fd = os.open(OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)
    os.chmod(OUTPUT, 0o600)

    print("Saved google-ads.yaml")


if __name__ == "__main__":
    main()
