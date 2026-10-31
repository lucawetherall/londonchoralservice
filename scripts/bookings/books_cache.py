"""Readers for the local Books cache and the per-event margins, for the private dashboard.

books-cache.json (~/lcs-private) is written by `scripts/bookings/books_sync.py` (the scheduled assistant's daily
pass); nothing here calls Books. margins() is singer_invoices.margins over the ledger and the singer store. Paths
are read at call time (LCS_PRIVATE_DIR, LCS_BOOKINGS_CSV), so the tests never touch ~/lcs-private. Both raise on
a malformed file, so the dashboard's Books section shows the error type and the rest renders.
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def private_dir():
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private"))


def books_path():
    return private_dir() / "books-cache.json"


def books_cache():
    """{generated_at, invoices, bills, totals} from the cache, or None: Books isn't synced yet."""
    try:
        with open(books_path(), encoding="utf-8") as f:
            value = json.load(f)
    except FileNotFoundError:
        return None
    if not isinstance(value, dict) or not isinstance(value.get("invoices"), list) \
            or not isinstance(value.get("bills"), list) or not isinstance(value.get("totals"), dict) \
            or not isinstance(value.get("generated_at"), str):
        raise ValueError("books-cache.json is not the expected shape")
    return value


def margins():
    """Per-booking margins (singer_invoices.margins) from the ledger and the singer store."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import lcs_money as lm
    import singer_invoices as si
    ledger = Path(os.environ.get("LCS_BOOKINGS_CSV") or private_dir() / "bookings.csv")
    return si.margins(lm.read_csv(ledger), lm.read_csv(private_dir() / "singer-invoices.csv"))
