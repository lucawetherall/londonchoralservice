#!/usr/bin/env python3
"""Tests for scripts/ads/negative_match.py (no network)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "ads"))
from negative_match import blocked, blocks  # noqa: E402

# exact: only the identical search, word order matters
assert blocks("funeral singers", "EXACT", "Funeral Singers")
assert not blocks("funeral singers london", "EXACT", "London Funeral Singers")
assert not blocks("funeral singers", "EXACT", "london funeral singers")
# phrase: the words together, in order, extra words allowed
assert blocks("carol event", "PHRASE", "christmas carol event london")
assert not blocks("carol event", "PHRASE", "carol singers for events")  # no plurals for negatives
assert not blocks("london funeral", "PHRASE", "funeral london")
# broad: every word, any order; no close variants
assert blocks("hymn", "BROAD", "funeral hymn singers")
assert not blocks("hymn", "BROAD", "hymns")
assert blocks("singers london", "BROAD", "london funeral singers")
assert not blocks("2025", "BROAD", "christmas carol singers london")
assert blocked([("pipers", "BROAD"), ("choir", "BROAD")], [("funeral choir", "EXACT"), ("london funeral singers", "PHRASE")]) \
    == [("choir", "BROAD", "funeral choir", "EXACT")]
try:
    blocks("x", "BROAD_MATCH", "x")
except ValueError:
    pass
else:
    raise AssertionError("unknown match type accepted")
print("negative_match: all tests passed")
