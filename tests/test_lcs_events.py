#!/usr/bin/env python3
"""Tests for scripts/bookings/lcs_events.py: the state log's schema, appends, reads and index (structured-state
design, 29 Sep 2026). Every test uses a temp LCS_PRIVATE_DIR, never ~/lcs-private.
Stdlib only: .venv/bin/python tests/test_lcs_events.py"""
import contextlib, copy, datetime, json, os, subprocess, sys, tempfile

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
    """Refused as a new line (validate for writing: the fee cap applies too)."""
    try:
        ev.validate(obj, write=True)
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


def test_the_fee_cap_applies_only_when_writing():
    """Lowering FEE_CAP later must never reopen a booking closed by a fee that was within the cap when written."""
    over = line(kind="fees-accepted", fields={"amount": f"{lm.FEE_CAP + 5:.2f}"}, by="owner")
    assert ev.validate(copy.deepcopy(over)) == over
    try:
        ev.validate(copy.deepcopy(over), write=True)
        assert False, "an over-cap fee was accepted for writing"
    except ValueError:
        pass
    path = fresh_dir()
    with open(os.open(path, os.O_WRONLY | os.O_CREAT, 0o600), "w") as f:
        f.write(ev.dumps(over) + "\n")
    assert [e["fields"]["amount"] for e in ev.read()[0]] == [over["fields"]["amount"]]
    assert ev.booking_facts("2111", T).closed_on == T


def test_an_at_more_than_a_day_ahead_is_refused():
    now = datetime.datetime.now(datetime.timezone.utc)
    soon = (now + datetime.timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ")
    later = (now + datetime.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert not refused(line(at=soon))
    assert refused(line(at=later))
    try:
        ev.validate(line(at=later))
        assert False, "read accepted a stamp two days ahead"
    except ValueError:
        pass


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


# --- Task 3: append, read, index --------------------------------------------------------------------------------

def fresh_dir():
    """A new private dir for one test, set as LCS_PRIVATE_DIR (read at call time); returns the log's path."""
    d = tempfile.mkdtemp()
    os.chmod(d, 0o700)
    os.environ["LCS_PRIVATE_DIR"] = d
    ev.clear_cache()
    return os.path.join(d, "events.jsonl")


def sha16(raw):
    import hashlib
    return hashlib.sha256(raw).hexdigest()[:16]


def test_log_path_follows_the_private_dir_at_call_time():
    path = fresh_dir()
    assert str(ev.log_path()) == path


def test_note_hash_is_twelve_hex_of_the_clause():
    import hashlib
    clause = "paid in full 2026-09-28 (owner)"
    assert ev.note_hash(clause) == hashlib.sha256(clause.encode("utf-8")).hexdigest()[:12]
    assert ev.note_hash(" " + clause) != ev.note_hash(clause)


def test_a_missing_log_reads_as_empty():
    fresh_dir()
    events, stats = ev.read()
    assert events == [] and stats["lines"] == 0 and stats["chain_ok"] and not stats.get("unreadable")


def test_round_trip_and_chain():
    path = fresh_dir()
    e1 = ev.append("booking", "2111", "deposit-seen", {}, "script", on="2026-09-20")
    e2 = ev.append("booking", "2111", "reminder-drafted", {"what": "balance"}, "script", note=ev.note_hash("x"))
    e3 = ev.append("singer_invoice", "1759123", "bank-warning", {"fp8": "0123abcd", "codes": ["new"]}, "script")
    assert oct(os.stat(path).st_mode & 0o777) == "0o600"
    raw = open(path, "rb").read()
    lines = raw.split(b"\n")[:-1]
    assert len(lines) == 3 and raw.endswith(b"\n")
    objs = [json.loads(x) for x in lines]
    assert [o["eid"] for o in objs] == [e1, e2, e3]
    assert objs[0]["prev"] == "" and objs[1]["prev"] == sha16(lines[0] + b"\n") and objs[2]["prev"] == sha16(lines[1] + b"\n")
    assert objs[0]["on"] == "2026-09-20" and objs[1]["on"] == lm.today().isoformat()
    assert objs[1]["note"] == ev.note_hash("x") and objs[0]["src"] == "live"
    events, stats = ev.read()
    assert [e["eid"] for e in events] == [e1, e2, e3]
    assert stats["lines"] == 3 and stats["skipped"] == 0 and stats["chain_ok"] and stats["broken_at"] is None
    assert stats["last_at"] == objs[2]["at"]


def test_append_refuses_a_bad_line_or_a_reserved_kind_and_writes_nothing():
    path = fresh_dir()
    for args in (("booking", "2111", "cancelled", {}, "robot"), ("booking", "a@b", "cancelled", {}, "script"),
                 ("booking", "2111", "fees-accepted", {"amount": "12.40"}, "script"),
                 ("booking", "2111", "discount-agreed", {"amount": "50.00"}, "owner")):
        try:
            ev.append(*args)
            assert False, args
        except ValueError:
            pass
    for on in ("2999-01-01", "not a date"):
        try:
            ev.append("booking", "2111", "cancelled", {}, "script", on=on)
            assert False, on
        except ValueError:
            pass
    assert not os.path.exists(path)


def test_the_cache_follows_the_file():
    fresh_dir()
    ev.append("booking", "2111", "cancelled", {}, "script")
    first, _ = ev.read()
    again, _ = ev.read()
    assert first == again and len(first) == 1
    ev.append("booking", "2111", "deposit-seen", {}, "script")
    assert len(ev.read()[0]) == 2


def test_a_partial_last_line_is_ignored_and_the_next_append_starts_a_new_line():
    path = fresh_dir()
    ev.append("booking", "2111", "cancelled", {}, "script")
    with open(path, "ab") as f:
        f.write(b'{"at":"2026-09-28T12:0')  # a write in progress
    events, stats = ev.read()
    assert len(events) == 1 and stats["skipped"] == 1 and stats["chain_ok"]
    eid = ev.append("booking", "2111", "deposit-seen", {}, "script")
    events, stats = ev.read()
    assert [e["kind"] for e in events] == ["cancelled", "deposit-seen"] and events[1]["eid"] == eid
    assert stats["lines"] == 3 and stats["skipped"] == 1 and stats["chain_ok"], stats
    lines = open(path, "rb").read().split(b"\n")
    assert json.loads(lines[2])["prev"] == sha16(lines[1] + b"\n")


def test_bad_long_and_duplicate_lines_are_skipped_and_counted():
    path = fresh_dir()
    ev.append("booking", "2111", "cancelled", {}, "script")
    good = open(path, "rb").read()
    obj = json.loads(good)
    with open(path, "ab") as f:
        f.write(b"not json\n")
        f.write(b'{"v":1}\n')
        f.write(json.dumps(dict(obj, id="Ann Smith")).encode() + b"\n")
        f.write(b'{"pad":"' + b"x" * 1100 + b'"}\n')
        f.write(good)  # the same eid again
    events, stats = ev.read()
    assert len(events) == 1 and stats["lines"] == 6 and stats["skipped"] == 5, stats


def test_an_edited_or_deleted_line_breaks_the_chain():
    path = fresh_dir()
    for kind in ("deposit-seen", "cancelled", "review-drafted"):
        ev.append("booking", "2111", kind, {}, "script")
    lines = open(path, "rb").read().split(b"\n")[:-1]
    with open(path, "wb") as f:
        f.write(lines[0] + b"\n" + lines[2] + b"\n")  # the middle line deleted
    events, stats = ev.read()
    assert len(events) == 2 and not stats["chain_ok"] and stats["broken_at"] == 2, stats


def test_a_symlinked_or_group_readable_log_is_refused_on_write_and_read():
    path = fresh_dir()
    real = os.path.join(tempfile.mkdtemp(), "elsewhere.jsonl")
    ev.append("booking", "2111", "cancelled", {}, "script")
    os.rename(path, real)
    os.symlink(real, path)
    size = os.path.getsize(real)
    try:
        ev.append("booking", "2111", "deposit-seen", {}, "script")
        assert False, "appended through a symlink"
    except OSError:
        pass
    assert os.path.getsize(real) == size
    events, stats = ev.read()
    assert events == [] and stats.get("unreadable"), stats
    os.remove(path)
    os.rename(real, path)
    os.chmod(path, 0o640)
    ev.clear_cache()
    try:
        ev.append("booking", "2111", "deposit-seen", {}, "script")
        assert False, "appended to a group-readable log"
    except OSError:
        pass
    assert os.path.getsize(path) == size
    events, stats = ev.read()
    assert events == [] and stats.get("unreadable"), stats
    os.chmod(path, 0o600)
    assert len(ev.read()[0]) == 1


def test_two_processes_appending_at_once_keep_every_line_and_the_chain():
    path = fresh_dir()
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import lcs_events as ev\n"
            "for i in range(200):\n"
            "    ev.append('booking', sys.argv[2], 'reminder-drafted', {'what': 'deposit'}, 'script')\n")
    env = dict(os.environ)
    procs = [subprocess.Popen([PY, "-c", code, os.path.join(ROOT, "scripts", "bookings"), ref], env=env)
             for ref in ("2111", "2112")]
    assert [p.wait(timeout=120) for p in procs] == [0, 0]
    events, stats = ev.read()
    assert len(events) == 400 and stats["skipped"] == 0 and stats["chain_ok"], stats
    assert sum(1 for e in events if e["id"] == "2111") == 200


def test_index_groups_by_subject_and_marks_retracted():
    fresh_dir()
    a = ev.append("booking", "2111", "cancelled", {}, "script", on="2026-09-20")
    ev.append("booking", "2112", "cancelled", {}, "script", on="2026-09-20")
    with as_owner():
        ev.append("booking", "2111", "retract", {"target": a, "why": "mistake"}, "owner", on="2026-09-21")
        ev.append("booking", "2112", "retract", {"target": a, "why": "mistake"}, "owner", on="2026-09-21")  # another id
    events, _ = ev.read()
    idx = ev.index(events, T)
    one, two = idx[("booking", "2111")], idx[("booking", "2112")]
    assert [e["kind"] for e in one] == ["cancelled", "retract"] and one[0]["retracted"] and not one[1]["retracted"]
    assert not two[0]["retracted"], "a retract never reaches another booking's fact"


def test_a_retract_cannot_be_retracted():
    fresh_dir()
    a = ev.append("booking", "2111", "cancelled", {}, "script", on="2026-09-20")
    with as_owner():
        r = ev.append("booking", "2111", "retract", {"target": a, "why": "mistake"}, "owner", on="2026-09-21")
        ev.append("booking", "2111", "retract", {"target": r, "why": "mistake"}, "owner", on="2026-09-22")
    one = ev.index(ev.read()[0], T)[("booking", "2111")]
    assert one[0]["retracted"] and not one[1]["retracted"]


def test_append_refuses_an_owner_fact_without_the_owner_check():
    """by: owner only after lcs_owner's nonce check passed in this process, with the log in the nonce's folder."""
    path = fresh_dir()
    for bad in ({}, {"LCS_BOOKINGS_CSV": os.path.join(os.path.dirname(path), "bookings.csv")}):
        import lcs_owner
        saved_env = {k: os.environ.get(k) for k in ("LCS_BOOKINGS_CSV",)}
        os.environ.pop("LCS_BOOKINGS_CSV", None)
        os.environ.update(bad)
        saved, lcs_owner._PROVEN = lcs_owner._PROVEN, bool(bad)  # the second case: proven, but the CSV override set
        try:
            ev.append("booking", "2111", "reinstated", {}, "owner")
            assert False, ("an owner fact was written", bad)
        except ev.OwnerRefused:
            pass
        finally:
            lcs_owner._PROVEN = saved
            for k, v in saved_env.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    assert not os.path.exists(path)
    ev.append("booking", "2111", "cancelled", {}, "script")  # a script fact needs no proof
    with as_owner():
        ev.append("booking", "2111", "reinstated", {}, "owner")
    assert [e["by"] for e in ev.read()[0]] == ["script", "owner"]


def test_a_short_or_failed_write_leaves_the_log_as_it_was():
    """A write that loses only the final newline would otherwise revive the event once the next append ends the
    line: append truncates back to the old size and raises."""
    path = fresh_dir()
    ev.append("booking", "2111", "cancelled", {}, "script")
    before = open(path, "rb").read()

    def short(fd, data):
        return os.write(fd, data[:-1])

    def fails(fd, data):
        os.write(fd, data[:-1])
        raise OSError("disk full")

    saved = ev._write
    for fake in (short, fails):
        ev._write = fake
        try:
            ev.append("booking", "2111", "deposit-seen", {}, "script")
            assert False, "a short write was accepted"
        except OSError:
            pass
        finally:
            ev._write = saved
        assert open(path, "rb").read() == before, fake.__name__
    ev.append("booking", "2111", "review-drafted", {}, "script")
    assert [e["kind"] for e in ev.read()[0]] == ["cancelled", "review-drafted"]


def test_the_log_lock_is_never_followed_through_a_symlink():
    path = fresh_dir()
    elsewhere = os.path.join(tempfile.mkdtemp(), "victim")
    open(elsewhere, "w").close()
    os.symlink(elsewhere, path + ".lock")
    try:
        ev.append("booking", "2111", "cancelled", {}, "script")
        assert False, "locked through a symlink"
    except OSError:
        pass
    assert not os.path.exists(path)
    try:
        with lm.ledger_lock(path):
            assert False, "ledger_lock followed a symlinked lock file"
    except OSError:
        pass


def test_log_problem_names_an_unreadable_broken_or_skipping_log():
    """Readers treat an unreadable log as absent; log_problem says so, for the Health page and verify."""
    path = fresh_dir()
    assert ev.log_problem() is None  # no log yet is not a problem
    ev.append("booking", "2111", "cancelled", {}, "script")
    ev.append("booking", "2111", "deposit-seen", {}, "script")
    assert ev.log_problem() is None
    os.chmod(path, 0o640)
    assert "can't be read" in ev.log_problem()
    os.chmod(path, 0o600)
    real = path + ".real"
    os.rename(path, real)
    os.symlink(real, path)
    assert "can't be read" in ev.log_problem()
    os.remove(path)
    lines = open(real, "rb").read().split(b"\n")
    with open(os.open(path, os.O_WRONLY | os.O_CREAT, 0o600), "wb") as f:
        f.write(lines[1] + b"\n")
    assert ev.log_problem() == "the state log's chain is broken at line 1"
    with open(path, "ab") as f:
        f.write(b"not json\n")
    assert ev.log_problem() == "the state log's chain is broken at line 1; 1 line skipped"


def test_owner_confirmed_marks_the_process_proven():
    import hashlib, lcs_owner, time
    d = os.path.dirname(fresh_dir())
    os.makedirs(os.path.join(d, "command-centre"), mode=0o700)
    nonce = "ab" * 32
    nf = os.path.join(d, "command-centre", "owner-nonce")
    fd = os.open(nf, os.O_WRONLY | os.O_CREAT, 0o600)
    os.write(fd, hashlib.sha256(nonce.encode()).hexdigest().encode())
    os.close(fd)
    r, w = os.pipe()
    os.write(w, (nonce + "\n").encode())
    saved, lcs_owner._PROVEN = lcs_owner._PROVEN, False
    try:
        assert not lcs_owner.owner_proven()
        assert lcs_owner.owner_confirmed(r) and lcs_owner.owner_proven()
    finally:
        lcs_owner._PROVEN = saved
        os.close(r)
        os.close(w)


@contextlib.contextmanager
def as_owner():
    """This process as the Command Centre's owner run: the nonce check passed (lcs_owner), no LCS_BOOKINGS_CSV."""
    import lcs_owner
    saved, csv_env = lcs_owner._PROVEN, os.environ.pop("LCS_BOOKINGS_CSV", None)
    lcs_owner._PROVEN = True
    try:
        yield
    finally:
        lcs_owner._PROVEN = saved
        if csv_env is not None:
            os.environ["LCS_BOOKINGS_CSV"] = csv_env


def retract_line(target, why, by, at, eid, subject="booking", id_="2111"):
    return ev.validate(line(subject, "retract", {"target": target["eid"], "why": why}, by, at=at, on=at[:10], eid=eid,
                            id=id_))


def test_a_write_failed_retract_drops_its_target_and_its_claim():
    """The writer's own retract in the same run: the fact never happened, so it counts for nothing (not even for
    'the family has facts') and no longer claims its note: a note that did land is read from the notes."""
    target = ev.validate(line(kind="cancelled", at="2026-09-10T10:00:00Z", on="2026-09-10", note=ev.note_hash("x")))
    undo = retract_line(target, "write-failed", "script", "2026-09-10T10:00:01Z", "b1b2c3d4e5f60718")
    one = ev.index([target, undo], T)[("booking", "2111")]
    assert one[0]["retracted"] == "write-failed", one
    f = ev.booking_facts("2111", T, events=[target, undo])
    assert not f.has("cancellation") and ev.note_hash("x") not in f.claims and not f.cancelled


def test_a_mistake_retract_keeps_its_target_as_history():
    target = ev.validate(line(kind="cancelled", at="2026-09-10T10:00:00Z", on="2026-09-10", note=ev.note_hash("x")))
    undo = retract_line(target, "mistake", "owner", "2026-09-11T10:00:00Z", "b1b2c3d4e5f60718")
    f = ev.booking_facts("2111", T, events=[target, undo])
    assert f.has("cancellation") and ev.note_hash("x") in f.claims and not f.cancelled


def test_a_write_failed_retract_needs_the_same_writer_and_the_same_run():
    owner_fee = ev.validate(line(kind="fees-accepted", fields={"amount": "12.40"}, by="owner",
                                 at="2026-09-10T10:00:00Z", on="2026-09-10"))
    by_script = retract_line(owner_fee, "write-failed", "script", "2026-09-10T10:00:01Z", "b1b2c3d4e5f60718")
    f = ev.booking_facts("2111", T, events=[owner_fee, by_script])
    assert f.closed_on == datetime.date(2026, 9, 10), "a script can't undo an owner fact"
    cancel = ev.validate(line(kind="cancelled", at="2026-09-10T10:00:00Z", on="2026-09-10"))
    later = retract_line(cancel, "write-failed", "script", "2026-09-10T10:05:00Z", "c1b2c3d4e5f60718")
    assert ev.booking_facts("2111", T, events=[cancel, later]).cancelled, "not the same run: ignored"
    owner_undo = retract_line(owner_fee, "write-failed", "owner", "2026-09-10T10:00:02Z", "d1b2c3d4e5f60718")
    assert ev.booking_facts("2111", T, events=[owner_fee, owner_undo]).closed_on is None


def test_a_future_on_is_ignored_until_that_day():
    fresh_dir()
    events = [ev.validate(line(on="2026-09-29", at="2026-09-29T09:00:00Z"))]
    assert ev.index(events, T) == {}
    assert len(ev.index(events, T + datetime.timedelta(days=1))[("booking", "2111")]) == 1


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
