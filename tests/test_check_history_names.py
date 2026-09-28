#!/usr/bin/env python3
"""Tests for scripts/check_history_names.py. Uses invented phrases, never the real names."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import check_history_names as chn  # noqa: E402

FAKE = {chn.fingerprint("zanzibar quoll"), chn.fingerprint("brindlewick")}


def test_phrases_cover_one_to_three_words_case_insensitively():
    got = set(chn.phrases("Hello Zanzibar-QUOLL there"))
    assert {"hello", "zanzibar quoll", "hello zanzibar quoll"} <= got


def test_has_banned_matches_split_and_joined_forms():
    assert chn.has_banned("sender_name='Zanzibar Quoll'", FAKE)
    assert chn.has_banned("payee BRINDLEWICK, T", FAKE)
    assert not chn.has_banned("Zanzibar and a quoll", FAKE)
    assert not chn.has_banned("nothing to see", FAKE)


def test_stored_list_holds_fingerprints_only():
    assert all(len(h) == 24 and all(c in "0123456789abcdef" for c in h) for h in chn.BANNED)
    src = open(os.path.join(ROOT, "scripts", "check_history_names.py"), encoding="utf-8").read()
    assert "BANNED = {" in src


def test_main_refuses_a_commit_that_adds_a_banned_phrase():
    d = tempfile.mkdtemp()
    run = lambda *a: subprocess.run(["git", *a], cwd=d, check=True, capture_output=True, text=True).stdout.strip()
    run("init", "-q"); run("config", "user.email", "t@example.com"); run("config", "user.name", "T")
    open(os.path.join(d, "a.txt"), "w").write("clean\n"); run("add", "."); run("commit", "-qm", "base")
    base = run("rev-parse", "HEAD")
    open(os.path.join(d, "a.txt"), "a").write("hello Zanzibar Quoll\n"); run("commit", "-qam", "adds a name")
    head = run("rev-parse", "HEAD")
    old = os.getcwd(); saved = chn.BANNED
    try:
        os.chdir(d); chn.BANNED = FAKE
        assert chn.main(["x", base, head]) == 1
        open(os.path.join(d, "a.txt"), "w").write("clean again\n"); run("commit", "-qam", "tidy")
        assert chn.main(["x", head, run("rev-parse", "HEAD")]) == 0
    finally:
        os.chdir(old); chn.BANNED = saved


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
