#!/usr/bin/env python3
"""Tests for scripts/bookings/lcs_owner.py: the owner barrier shared by the money scripts (the Command Centre's
one-time nonce, and the folder check that ties an --owner write to the files beside that nonce).
Stdlib only: .venv/bin/python tests/test_lcs_owner.py"""
import os, sys, tempfile

_HOME = tempfile.mkdtemp()  # never the real ~/lcs-private
os.environ["LCS_PRIVATE_DIR"] = _HOME
os.environ.pop("LCS_BOOKINGS_CSV", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import lcs_owner  # noqa: E402


def private(*parts):
    return os.path.join(_HOME, *parts)


def test_nonce_path_follows_the_private_dir_at_call_time():
    assert str(lcs_owner.owner_nonce_path()) == private("command-centre", "owner-nonce")
    other = tempfile.mkdtemp()
    os.environ["LCS_PRIVATE_DIR"] = other
    try:
        assert str(lcs_owner.owner_nonce_path()) == os.path.join(other, "command-centre", "owner-nonce")
    finally:
        os.environ["LCS_PRIVATE_DIR"] = _HOME


def test_files_directly_in_the_private_folder_pass():
    paths = [private("bookings.csv"), private("singer-invoices.csv"), private("events.jsonl")]
    assert lcs_owner.owner_folder_problem(paths, {}) is None


def test_lcs_bookings_csv_is_refused_even_naming_the_same_file():
    why = lcs_owner.owner_folder_problem([private("bookings.csv")], {"LCS_BOOKINGS_CSV": private("bookings.csv")})
    assert why and "LCS_BOOKINGS_CSV" in why


def test_a_store_or_log_outside_the_folder_is_refused():
    elsewhere = tempfile.mkdtemp()
    for bad in (os.path.join(elsewhere, "singer-invoices.csv"), os.path.join(elsewhere, "events.jsonl"),
                private("sub", "events.jsonl")):
        why = lcs_owner.owner_folder_problem([private("bookings.csv"), bad], {})
        assert why and "same private folder" in why, (bad, why)


def test_a_path_through_a_symlinked_folder_is_refused():
    """Even a link that leads back into the private folder: the path itself must sit directly in it."""
    elsewhere = tempfile.mkdtemp()
    out = private("out-link")
    os.symlink(elsewhere, out)
    back = os.path.join(tempfile.mkdtemp(), "back-link")
    os.symlink(_HOME, back)
    for bad in (os.path.join(out, "events.jsonl"), os.path.join(back, "events.jsonl")):
        why = lcs_owner.owner_folder_problem([bad], {})
        assert why and "same private folder" in why, (bad, why)


def test_a_file_that_is_a_symlink_out_of_the_folder_is_refused():
    elsewhere = tempfile.mkdtemp()
    target = os.path.join(elsewhere, "events.jsonl")
    open(target, "w").close()
    link = private("events-link.jsonl")
    os.symlink(target, link)
    why = lcs_owner.owner_folder_problem([link], {})
    assert why and "same private folder" in why, why


def test_owner_confirmed_is_false_without_a_pipe():
    """The full nonce cases run through check_payments.py --owner (tests/test_check_payments.py); here, the moved
    function still refuses a terminal or file on stdin."""
    with open(os.devnull) as f:
        assert lcs_owner.owner_confirmed(f.fileno()) is False


def test_check_payments_keeps_the_old_names():
    import check_payments as cp
    assert cp.OWNER_NONCE_TTL == lcs_owner.OWNER_NONCE_TTL
    assert cp.owner_nonce_path() == lcs_owner.owner_nonce_path()
    assert callable(cp.owner_confirmed) and callable(cp.owner_ledger_problem)


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
