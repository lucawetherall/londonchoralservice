#!/usr/bin/env python3
"""Tests for scripts/bookings/lcs_events.py: the state log's schema, appends, reads and index (structured-state
design, 29 Sep 2026). Every test uses a temp LCS_PRIVATE_DIR, never ~/lcs-private.
Stdlib only: .venv/bin/python tests/test_lcs_events.py"""
import copy, datetime, json, os, subprocess, sys, tempfile

_HOME = tempfile.mkdtemp()  # never the real ~/lcs-private
os.environ["LCS_PRIVATE_DIR"] = _HOME
os.environ.pop("LCS_BOOKINGS_CSV", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import lcs_events as ev  # noqa: E402
import lcs_money as lm  # noqa: E402

PY = sys.executable
T = datetime.date(2026, 9, 28)
AT = "2026-09-28T12:00:00Z"

# one valid (subject, kind, fields, by) per kind
GOOD = [
    ("booking", "paid-in-full", {"basis": "bank"}, "script"),
    ("booking", "paid-in-full", {"basis": "owner"}, "owner"),
    ("booking", "fees-accepted", {"amount": "12.40"}, "owner"),
    ("booking", "noted-paid", {"scope": "part"}, "script"),
    ("booking", "noted-paid", {"scope": "full"}, "owner"),
    ("booking", "arranged", {"method": "cash"}, "script"),
    ("booking", "arranged", {"method": "third-party"}, "owner"),
    ("booking", "cancelled", {}, "script"),
    ("booking", "reinstated", {}, "owner"),
    ("booking", "deposit-kept", {}, "owner"),
    ("booking", "refunded", {}, "owner"),
    ("booking", "payment-checked", {}, "owner"),
    ("booking", "deposit-seen", {}, "script"),
    ("booking", "reminder-drafted", {"what": "balance"}, "script"),
    ("booking", "review-drafted", {}, "script"),
    ("booking", "review-skipped", {"reason": "planner"}, "script"),
    ("booking", "retract", {"target": "0123456789abcdef", "why": "mistake"}, "owner"),
    ("booking", "retract", {"target": "0123456789abcdef", "why": "write-failed"}, "script"),
    ("booking", "notes-checked", {"clauses": ["0123456789ab"]}, "owner"),
    ("singer_invoice", "bank-warning", {"fp8": "0123abcd", "codes": ["changed", "not-yet-verified"]}, "script"),
    ("singer_invoice", "bank-warning", {"fp8": "", "codes": []}, "script"),
    ("singer_invoice", "bank-confirmed", {"fp8": "0123abcd"}, "owner"),
    ("singer_invoice", "settled", {"amount": "250.00"}, "owner"),
    ("singer_invoice", "withdrawn", {"reason": "not-ours"}, "script"),
    ("singer_invoice", "paid-reply-drafted", {}, "script"),
    ("singer_invoice", "retract", {"target": "0123456789abcdef", "why": "mistake"}, "owner"),
    ("singer_invoice", "notes-checked", {"clauses": ["0123456789ab", "ba9876543210"]}, "owner"),
]

# (subject, kind, bad fields, by, why) for each kind: at least two refusals apiece
BAD = [
    ("booking", "paid-in-full", {"basis": "bank"}, "owner", "bank basis is the script's"),
    ("booking", "paid-in-full", {"basis": "owner"}, "script", "a script never writes the owner's basis"),
    ("booking", "paid-in-full", {}, "owner", "missing field"),
    ("booking", "fees-accepted", {"amount": "12.4"}, "owner", "one decimal"),
    ("booking", "fees-accepted", {"amount": "0.00"}, "owner", "zero"),
    ("booking", "fees-accepted", {"amount": f"{lm.FEE_CAP + 0.01:.2f}"}, "owner", "over the cap"),
    ("booking", "fees-accepted", {"amount": "12.40"}, "script", "owner only"),
    ("booking", "fees-accepted", {"amount": 12.4}, "owner", "a number, not a string"),
    ("booking", "noted-paid", {"scope": "half"}, "script", "unknown word"),
    ("booking", "noted-paid", {"scope": "part", "by": "x"}, "script", "unknown field"),
    ("booking", "arranged", {"method": "card"}, "script", "unknown method"),
    ("booking", "arranged", {}, "script", "missing method"),
    ("booking", "cancelled", {"reason": "client"}, "script", "no fields allowed"),
    ("booking", "cancelled", {}, "robot", "unknown by"),
    ("booking", "reinstated", {}, "script", "owner only"),
    ("booking", "reinstated", {"x": "y"}, "owner", "no fields"),
    ("booking", "deposit-kept", {}, "script", "owner only"),
    ("booking", "deposit-kept", {"amount": "100.00"}, "owner", "no fields"),
    ("booking", "refunded", {}, "script", "owner only"),
    ("booking", "refunded", {"amount": "100.00"}, "owner", "no fields"),
    ("booking", "payment-checked", {}, "script", "owner only"),
    ("booking", "payment-checked", {"on": "2026-09-01"}, "owner", "no fields"),
    ("booking", "cancelled", {}, "Luca", "a name as the writer"),
    ("booking", "deposit-seen", {}, "owner", "script only"),
    ("booking", "deposit-seen", {"on": "2026-09-01"}, "script", "no fields"),
    ("booking", "reminder-drafted", {"what": "final"}, "script", "unknown word"),
    ("booking", "reminder-drafted", {"what": "balance"}, "owner", "script only"),
    ("booking", "review-drafted", {}, "owner", "script only"),
    ("booking", "review-drafted", {"what": "x"}, "script", "no fields"),
    ("booking", "review-skipped", {"reason": "other"}, "script", "reason not on the list"),
    ("booking", "review-skipped", {"reason": "planner2"}, "script", "digit run in a word field"),
    ("booking", "retract", {"target": "0123456789abcdef", "why": "mistake"}, "script", "a mistake is the owner's"),
    ("booking", "retract", {"target": "0123456789ABCDEF", "why": "mistake"}, "owner", "upper-case eid"),
    ("booking", "retract", {"target": "0123456789abcde", "why": "mistake"}, "owner", "short eid"),
    ("booking", "notes-checked", {"clauses": []}, "owner", "no clauses"),
    ("booking", "notes-checked", {"clauses": ["0123456789ab"] * 21}, "owner", "too many clauses"),
    ("booking", "notes-checked", {"clauses": "0123456789ab"}, "owner", "a string where a list goes"),
    ("booking", "notes-checked", {"clauses": ["0123456789ab"]}, "script", "owner only"),
    ("booking", "bank-warning", {"fp8": "", "codes": []}, "script", "a singer kind on a booking"),
    ("booking", "payment-confirmed", {"item": "x", "amount": "1.00"}, "owner", "reserved, bad item"),
    ("singer_invoice", "bank-warning", {"fp8": "0123ABCD", "codes": []}, "script", "upper-case fp8"),
    ("singer_invoice", "bank-warning", {"fp8": "0123abcd", "codes": ["moved"]}, "script", "unknown code"),
    ("singer_invoice", "bank-warning", {"fp8": "0123abcd", "codes": "changed"}, "script", "a string where a list goes"),
    ("singer_invoice", "bank-warning", {"fp8": "0123abcd", "codes": ["changed", "changed"]}, "script", "repeated code"),
    ("singer_invoice", "bank-warning", {"fp8": "0123abcd", "codes": []}, "owner", "script only"),
    ("singer_invoice", "bank-confirmed", {"fp8": ""}, "owner", "nothing to confirm"),
    ("singer_invoice", "bank-confirmed", {"fp8": "0123abcd"}, "script", "owner only"),
    ("singer_invoice", "bank-confirmed", {"fp8": "0123abcd0123abcd"}, "owner", "the whole fingerprint"),
    ("singer_invoice", "settled", {"amount": "250"}, "owner", "no pence"),
    ("singer_invoice", "settled", {"amount": "250.00"}, "script", "owner only"),
    ("singer_invoice", "settled", {"amount": "123456.00"}, "owner", "six digits"),
    ("singer_invoice", "withdrawn", {"reason": "mistake"}, "script", "reason not on the list"),
    ("singer_invoice", "withdrawn", {}, "script", "missing reason"),
    ("singer_invoice", "paid-reply-drafted", {}, "owner", "script only"),
    ("singer_invoice", "paid-reply-drafted", {"x": "1"}, "script", "no fields"),
    ("singer_invoice", "cancelled", {}, "script", "a booking kind on a singer invoice"),
    ("singer_invoice", "notes-checked", {"clauses": ["0123456789a"]}, "owner", "short hash"),
]

# a name, an email, a sort code, an account number with pence, an IBAN, a pound sign (an 8-digit string alone is a
# legal fp8, which is hex: the fingerprint's first 8 characters, never a bank number)
NAMEY = ["Ann Smith", "ann@example.com", "12-34-56", "12345678.00", "GB29NWBK60161331926819", "£250"]


def line(subject="booking", kind="cancelled", fields=None, by="script", **over):
    obj = {"v": 1, "eid": "a1b2c3d4e5f60718", "prev": "", "at": AT, "on": "2026-09-28", "subject": subject,
           "id": "2111" if subject == "booking" else "1759123456789012345", "kind": kind,
           "fields": {} if fields is None else fields, "by": by, "src": "live"}
    obj.update(over)
    return obj


def refused(obj):
    try:
        ev.validate(obj)
    except ValueError:
        return True
    return False


# --- Task 2: the schema ---------------------------------------------------------------------------------------

def test_every_kind_has_a_passing_line():
    for subject, kind, fields, by in GOOD:
        obj = line(subject, kind, fields, by)
        assert ev.validate(copy.deepcopy(obj)) == obj, (subject, kind, fields, by)


def test_every_kind_is_in_the_schema_and_refused_at_least_twice():
    kinds = {(s, k) for s, k in ev.KINDS}
    assert kinds == {(s, k) for s, k, _, _ in GOOD} | {("booking", k) for k in ev.RESERVED}, kinds
    counts = {}
    for subject, kind, fields, by, why in BAD:
        assert refused(line(subject, kind, fields, by)), (subject, kind, why)
        counts[(subject, kind)] = counts.get((subject, kind), 0) + 1
    for s, k, _, _ in GOOD:
        assert counts.get((s, k), 0) >= 2 or k in ("retract", "notes-checked"), (s, k, counts.get((s, k)))


def test_reserved_kinds_validate_but_are_listed():
    assert ev.RESERVED == {"payment-confirmed", "discount-agreed", "goodwill-reduction", "overpayment-refunded"}
    ok = line("booking", "payment-confirmed", {"item": "0a1b2c3d-0a1b-4c3d-8e9f-0a1b2c3d4e5f", "amount": "575.00"}, "owner")
    assert ev.validate(ok) == ok
    assert refused(line("booking", "discount-agreed", {"amount": "50.00"}, "script"))


def test_unknown_or_missing_top_level_keys_are_refused():
    assert refused(dict(line(), extra="x"))
    for key in ("v", "eid", "prev", "at", "on", "subject", "id", "kind", "fields", "by", "src"):
        obj = line()
        del obj[key]
        assert refused(obj), key
    assert not refused(line(note="0123456789ab"))  # note is the one optional key
    for bad in ("", "0123456789AB", "0123456789a", 12):
        assert refused(line(note=bad)), bad


def test_top_level_forms():
    for key, bad in (("v", 2), ("v", True), ("v", "1"), ("eid", "0123"), ("eid", "g123456789abcdef"),
                     ("prev", "0123"), ("at", "2026-09-28 12:00:00"), ("at", "2026-09-28T12:00:00+01:00"),
                     ("at", "2026-02-30T12:00:00Z"), ("on", "2026-02-30"), ("on", "28/09/2026"),
                     ("subject", "enquiry"), ("by", "Luca"), ("src", "import"), ("kind", "Cancelled"),
                     ("fields", []), ("id", "")):
        assert refused(line(**{key: bad})), (key, bad)
    assert not refused(line(prev="0123456789abcdef"))


def test_on_is_never_after_the_london_date_of_at():
    # 23:30 UTC on 28 Sep is 00:30 on 29 Sep in London (BST)
    assert not refused(line(at="2026-09-28T23:30:00Z", on="2026-09-29"))
    assert refused(line(at="2026-09-28T22:30:00Z", on="2026-09-29"))
    assert not refused(line(on="2024-01-01"))


def test_ids_by_subject():
    for good in ("2111", "1212A", "INV-2111"):
        assert not refused(line(id=good)), good
    for bad in ("-2111", "a" * 21, "2111 A", "2111@x", "ann@example.com", "Ann Smith", "2111;x"):
        assert refused(line(id=bad)), bad
    for good in ("1759123456789012345", "a.b_c-d", "x" * 200):
        assert not refused(line("singer_invoice", "paid-reply-drafted", {}, id=good)), good
    for bad in ("x" * 201, "abc@mail.zoho.com", "<abc@x>", "Ann Smith", ".abc"):
        assert refused(line("singer_invoice", "paid-reply-drafted", {}, id=bad)), bad


def test_name_or_email_shaped_values_are_refused_in_every_string_field():
    for subject, kind, fields, by in GOOD:
        for key, value in fields.items():
            if not isinstance(value, str):
                continue
            for bad in NAMEY:
                assert refused(line(subject, kind, dict(fields, **{key: bad}), by)), (kind, key, bad)
    for key in ("eid", "prev", "at", "on", "subject", "kind", "by", "src", "note"):
        for bad in NAMEY:
            assert refused(line(**{key: bad})), (key, bad)
    for bad in NAMEY:
        assert refused(line("booking", "notes-checked", {"clauses": [bad]}, "owner"))
        assert refused(line("singer_invoice", "bank-warning", {"fp8": "", "codes": [bad]}, "script"))


def test_dumps_is_one_sorted_compact_line():
    obj = line(note="0123456789ab")
    text = ev.dumps(obj)
    assert "\n" not in text and " " not in text
    assert list(json.loads(text)) == sorted(obj) and json.loads(text) == obj
    assert text.startswith('{"at":')


def test_dumps_refuses_an_over_long_line():
    saved = ev.LINE_MAX
    try:
        ev.LINE_MAX = 100
        try:
            ev.dumps(line())
            assert False, "an over-long line was accepted"
        except ValueError:
            pass
    finally:
        ev.LINE_MAX = saved
    assert len(ev.dumps(line("singer_invoice", "notes-checked", {"clauses": ["0123456789ab"] * 20}, "owner",
                             id="x" * 200)).encode()) < ev.LINE_MAX


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
