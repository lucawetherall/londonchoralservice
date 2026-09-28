#!/usr/bin/env python3
"""Shared, READ-ONLY money helpers for the bookings scripts.

- StarlingReadOnly: the only way these scripts talk to Starling. It sends GET
  requests and nothing else; no method here can move money, add payees or
  write to the bank (tests/test_lcs_money.py enforces the method list).
- The token lives in the owner's macOS Keychain (service lcs-starling-read)
  and is read at run time, never printed.
- Private files live in ~/lcs-private/ (override with LCS_PRIVATE_DIR), mode 600.
- Bank details are reduced to a fingerprint plus the last four digits.
"""

import csv
import datetime
import hashlib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

API = "https://api.starlingbank.com"
KEYCHAIN_SERVICE = "lcs-starling-read"
PRIVATE = Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private"))
LEDGER = Path(os.environ.get("LCS_BOOKINGS_CSV", PRIVATE / "bookings.csv"))


def keychain_token():
    r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


class StarlingError(Exception):
    pass


class StarlingReadOnly:
    """GET-only Starling client. Add no other public methods."""

    def __init__(self, token, opener=urllib.request.urlopen):
        self._token = token
        self._open = opener
        self._account = None

    def get(self, path):
        req = urllib.request.Request(API + path, method="GET", headers={"Accept": "application/json"})
        req.add_unredirected_header("Authorization", f"Bearer {self._token}")  # never follows a redirect
        with self._open(req, timeout=30) as resp:
            return json.load(resp)

    def account(self):
        if self._account is None:
            want = os.environ.get("LCS_STARLING_ACCOUNT_UID")
            for a in self.get("/api/v2/accounts").get("accounts", []):
                if not want or a.get("accountUid") == want:
                    self._account = a
                    break
            else:
                raise StarlingError("No matching Starling account (set LCS_STARLING_ACCOUNT_UID if there are several).")
        return self._account

    def feed(self, since, until, direction):
        """Settled-or-pending feed items between two dates, one direction ("IN" or "OUT")."""
        a = self.account()
        path = (f"/api/v2/feed/account/{a['accountUid']}/category/{a['defaultCategory']}/transactions-between"
                f"?minTransactionTimestamp={since.isoformat()}T00:00:00.000Z"
                f"&maxTransactionTimestamp={until.isoformat()}T00:00:00.000Z")
        items = self.get(path).get("feedItems", [])
        return [i for i in items if i.get("direction") == direction
                and i.get("status") not in ("DECLINED", "REVERSED", "REFUNDED")]

    def payees(self):
        return self.get("/api/v2/payees").get("payees", [])


def money(value):
    try:
        return float(str(value if value is not None else "0").replace("£", "").replace(",", "") or 0)
    except ValueError:
        return 0.0


def local_date(ts):
    """ISO timestamp (UTC unless it says otherwise) -> Europe/London date string."""
    if not ts:
        return ""
    try:
        t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return ts[:10]
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    return t.astimezone(ZoneInfo("Europe/London")).date().isoformat()


def bank_fingerprint(sort_code, account_number):
    """16-hex fingerprint of a UK bank account, or None if the details aren't a sort code + account."""
    sc = re.sub(r"\D", "", sort_code or "")
    acc = re.sub(r"\D", "", account_number or "")
    if len(sc) != 6 or not 6 <= len(acc) <= 8:
        return None
    return hashlib.sha256(f"{sc}:{acc.zfill(8)}".encode()).hexdigest()[:16]


def last4(account_number):
    digits = re.sub(r"\D", "", account_number or "")
    return digits[-4:]


def payee_fingerprints(payees):
    """fingerprint -> payee name, for every UK account on every Starling payee."""
    out = {}
    for p in payees:
        for a in p.get("accounts", []):
            fp = bank_fingerprint(a.get("bankIdentifier"), a.get("accountIdentifier"))
            if fp:
                out[fp] = p.get("payeeName", "")
    return out


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, columns):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
