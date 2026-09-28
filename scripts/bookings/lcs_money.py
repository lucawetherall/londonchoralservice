#!/usr/bin/env python3
"""Shared, READ-ONLY money helpers for the bookings scripts.

- StarlingReadOnly: the only way these scripts talk to Starling. It sends GET
  requests and nothing else; no method here can move money, add payees or
  write to the bank (tests/test_lcs_money.py enforces the method list).
- The token lives in the owner's macOS Keychain (service lcs-starling-read)
  and is read at run time, never printed.
- Private files live in ~/lcs-private/ (override with LCS_PRIVATE_DIR), mode 600.
- One helper each, used by every bookings and report script: locked_rows (the locked
  read-modify-write of a private CSV), parse_gbp (money) and today (the Europe/London date).
- Bank details are reduced to a fingerprint plus the last four digits. The
  fingerprint is an HMAC-SHA256 keyed with fingerprint.key (32 random bytes,
  mode 600, made on first use in the private dir), so the stored fingerprint and
  last four digits can't be brute-forced back to an account number. Never commit,
  copy or share the key; if it's lost, restore it from a backup rather than letting
  one be recreated — a new key would make every fingerprint already on record
  unmatchable, so lcs_money refuses to create one while singer-invoices.csv still
  holds fingerprints made with the old one.
"""

import contextlib
import csv
import datetime
import fcntl
import hashlib
import hmac
import json
import math
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

API = "https://api.starlingbank.com"
KEYCHAIN_SERVICE = "lcs-starling-read"
PRIVATE = Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private"))
LONDON = ZoneInfo("Europe/London")
# Invoices and booking confirmations (make_booking_docs.py), in iCloud Drive so they are on every device.
# LCS_INVOICES_DIR overrides it for tests only; make_booking_docs.py, imap_draft.py and the Books guard
# use the fixed path.
ICLOUD_INVOICES = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "LCS-invoices"
_KEYS = {}
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


def parse_gbp(value):
    """An amount in pounds ("£1,150.00", "575.5", 325) -> float, or None for anything unreadable, blank,
    nan or inf. The one money parser for the bookings and report scripts: callers decide what a negative
    or zero amount means."""
    if value is None:
        return None
    text = str(value).replace("£", "").replace(",", "").strip()
    try:
        v = float(text)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def money(value):
    """parse_gbp, with 0.0 for anything unreadable (nan and inf included)."""
    v = parse_gbp(value)
    return 0.0 if v is None else v


def today(now=None):
    """Today's date in Europe/London (`now`: an aware datetime, default the current time). Use this, never
    date.today(): the scheduled tasks and the ledger's dates are London dates, whatever the machine's zone."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return now.astimezone(LONDON).date()


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
    return t.astimezone(LONDON).date().isoformat()


def _fingerprint_key():
    """The 32-byte key in <private dir>/fingerprint.key (LCS_PRIVATE_DIR read at call time), made once, mode 600.
    Refuses to make a new one when singer-invoices.csv already carries fingerprints made with an old key: recreating
    it here would make every one of those fingerprints unmatchable, so the old key must be restored instead."""
    home = Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private"))
    path = home / "fingerprint.key"
    if path not in _KEYS:
        if not path.exists():
            csv_path = home / "singer-invoices.csv"
            if csv_path.exists():
                with open(csv_path, newline="") as f:
                    if any((row.get("bank_fp") or "").strip() for row in csv.DictReader(f)):
                        raise ValueError(
                            "fingerprint.key is missing but singer-invoices.csv has fingerprints made with it: "
                            "restore the key from a backup (creating a new one would break every stored fingerprint)")
            home.mkdir(mode=0o700, parents=True, exist_ok=True)
            tmp = home / f".fingerprint.key.{os.getpid()}.{os.urandom(4).hex()}.tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(os.urandom(32))
                os.link(tmp, path)  # atomic: another process may have won the race, which is fine
            except FileExistsError:
                pass
            finally:
                tmp.unlink(missing_ok=True)
        key = path.read_bytes()
        if len(key) != 32:
            raise ValueError(f"{path} is damaged (not 32 bytes): restore it from a backup")
        _KEYS[path] = key
    return _KEYS[path]


def bank_fingerprint(sort_code, account_number):
    """16-hex keyed fingerprint of a UK bank account, or None if the details aren't a sort code + account.
    Inputs are coerced with str() (None -> ""), so a numeric field straight out of JSON can't crash this."""
    sc = re.sub(r"\D", "", str(sort_code) if sort_code is not None else "")
    acc = re.sub(r"\D", "", str(account_number) if account_number is not None else "")
    if len(sc) != 6 or not 6 <= len(acc) <= 8:
        return None
    return hmac.new(_fingerprint_key(), f"{sc}:{acc.zfill(8)}".encode(), hashlib.sha256).hexdigest()[:16]


def feed_item_fingerprint(item):
    """Fingerprint of the recipient's bank details on a Starling feed item (payments to a payee), or None."""
    return bank_fingerprint(item.get("counterPartySubEntityIdentifier"), item.get("counterPartySubEntitySubIdentifier"))


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


@contextlib.contextmanager
def ledger_lock(path):
    """Exclusive lock for a read-modify-write of a private CSV: flock on "<path>.lock" (mode 600)."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(f"{path}.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)  # closing releases the lock


class LockedTable:
    """What locked_rows yields: .rows (list of dicts, edit or append in place) and .columns (the header)."""

    def __init__(self, rows, columns):
        self.rows, self.columns = rows, columns


@contextlib.contextmanager
def locked_rows(path, columns=None):
    """The one read-modify-write for a private CSV. Takes ledger_lock, reads the rows with the file's own
    header (plus any of `columns` it lacks, appended), and refuses (SystemExit, nothing written) a row with
    more fields than the header, since a rewrite would drop them. On a clean exit, if the rows changed, it
    writes them back atomically at mode 600 (write_csv); after an exception, SystemExit included, it writes
    nothing. ledger_lock is not re-entrant: never nest this, or call another writer of the file inside it."""
    path = Path(path)
    with ledger_lock(path):
        header, rows = [], []
        if path.exists():
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                header = list(reader.fieldnames or [])
                rows = list(reader)
        if any(None in r for r in rows):
            raise SystemExit(f"{path.name} has a row with more fields than its header; nothing written")
        cols = header + [c for c in (columns or []) if c not in header]
        before = [dict(r) for r in rows]
        table = LockedTable(rows, cols)
        yield table
        if table.rows != before:
            write_csv(path, table.rows, table.columns)
