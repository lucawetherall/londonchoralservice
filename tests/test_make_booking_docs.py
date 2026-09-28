#!/usr/bin/env python3
"""Tests for scripts/bookings/make_booking_docs.py's file naming (no Chrome, node or templates needed).
.venv/bin/python tests/test_make_booking_docs.py"""
import os, sys, tempfile

os.environ["LCS_PRIVATE_DIR"] = tempfile.mkdtemp()  # never the real ~/lcs-private
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import make_booking_docs as mbd  # noqa: E402


def test_safe_name_keeps_a_normal_name():
    assert mbd.safe_name("Rowan Ashby & Sam Fenwick-Hale") == "Rowan Ashby & Sam Fenwick-Hale"
    assert mbd.safe_name("  O’Brien  ") == "O’Brien"


def test_safe_name_can_never_leave_the_folder():
    for raw in ("../../etc/passwd", "a/b", "a\\b", ".hidden", "x\x00y", "tab\tnew\nline", "C:..\\x"):
        got = mbd.safe_name(raw)
        assert "/" not in got and "\\" not in got and ".." not in got and not got.startswith("."), (raw, got)
        assert all(c.isprintable() for c in got), (raw, got)


def test_safe_name_refuses_a_name_with_nothing_left():
    for raw in ("", "   ", "..", "/", "..//.."):
        try:
            mbd.safe_name(raw)
            raise AssertionError(f"{raw!r} accepted")
        except SystemExit as e:
            assert "STOP" in str(e), e


def test_out_folder_is_private_and_inside_the_root():
    root = os.path.join(tempfile.mkdtemp(), "lcs-private", "invoices")
    folder = mbd.out_folder("2111", "../../Rowan Ashby", root)
    assert os.path.dirname(folder) == root and os.path.basename(folder) == "2111 - Rowan Ashby", folder
    for path in (folder, root):
        assert oct(os.stat(path).st_mode & 0o777) == "0o700", (path, oct(os.stat(path).st_mode))


def test_pounds_refuses_the_unreadable():
    assert mbd.pounds("£1,150", "rate") == 1150.0 and mbd.pounds(2, "qty") == 2.0
    for bad in ("nan", "inf", "-5", "abc", None):
        try:
            mbd.pounds(bad, "rate")
            raise AssertionError(f"{bad!r} accepted")
        except SystemExit as e:
            assert "STOP" in str(e), e


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except (Exception, SystemExit) as e:
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
