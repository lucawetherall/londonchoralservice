"""Readers for the Books cache and the per-event margins, for the pages to use once the UI is wired.

books.json is written by `scripts/reports/cc_sync.py books` (the scheduled assistant's daily pass); nothing here
calls Books. margins() is singer_invoices.margins over the ledger and the singer store, read at call time.
Both raise on a malformed file, so a page's Panel shows the error type and the rest renders.
"""

import os
import sys
from pathlib import Path

from . import auth, sources

REPO = Path(__file__).resolve().parent.parent


def books_path():
    return auth.config_dir() / "cache" / "books.json"


def books_cache():
    """{generated_at, invoices, bills, totals} from the cache, or None: Books isn't synced yet."""
    found = sources.read_json(books_path())
    if found is None:
        return None
    value, _ = found
    if not isinstance(value, dict) or not isinstance(value.get("invoices"), list) \
            or not isinstance(value.get("bills"), list) or not isinstance(value.get("totals"), dict) \
            or not isinstance(value.get("generated_at"), str):
        raise ValueError("books.json is not the expected shape")
    return value


def margins():
    """Per-booking margins (singer_invoices.margins) from the ledger and the singer store."""
    bookings = str(REPO / "scripts" / "bookings")
    if bookings not in sys.path:
        sys.path.insert(0, bookings)
    import lcs_money as lm
    import singer_invoices as si
    ledger = Path(os.environ.get("LCS_BOOKINGS_CSV") or auth.private_dir() / "bookings.csv")
    return si.margins(lm.read_csv(ledger), lm.read_csv(auth.private_dir() / "singer-invoices.csv"))
