#!/usr/bin/env python3
"""Tests for scripts/bookings/lcs_owner.py: the owner barrier shared by the money scripts (the Command Centre's
one-time nonce, the chat approval owner_confirm_guard writes once Luca clicks Allow, and the folder check that ties an
--owner write to the files beside the nonce).
Stdlib only: .venv/bin/python tests/test_lcs_owner.py"""
import hashlib, json, os, secrets, sys, tempfile, time

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


ARGV = ["scripts/bookings/check_payments.py", "--fact", "2108A", "paid-in-full", "--on", "2026-10-19", "--owner"]


def chat_approval(argv, mode=0o600, age=0, body=None, home=None):
    """An approval as owner_confirm_guard writes it: owner-nonce.chat-<sha256 of the secret> in the command-centre
    folder, holding the argv. Returns (secret, path)."""
    secret = secrets.token_hex(32)
    cc = os.path.join(home or _HOME, "command-centre")
    os.makedirs(cc, mode=0o700, exist_ok=True)
    path = os.path.join(cc, "owner-nonce.chat-" + hashlib.sha256(secret.encode()).hexdigest())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.write(fd, (json.dumps({"argv": argv, "created": "2026-10-19T12:00:00+00:00", "session": "s"})
                  if body is None else body).encode())
    os.close(fd)
    os.chmod(path, mode)
    if age:
        os.utime(path, (time.time() - age, time.time() - age))
    return secret, path


def confirm(line, argv=None):
    """owner_confirmed with `line` on a pipe; _PROVEN reset first and restored after."""
    r, w = os.pipe()
    os.write(w, (line + "\n").encode())
    os.close(w)
    saved, lcs_owner._PROVEN = lcs_owner._PROVEN, False
    try:
        ok = lcs_owner.owner_confirmed(r) if argv is None else lcs_owner.owner_confirmed(r, argv)
        return ok, lcs_owner.owner_proven()
    finally:
        lcs_owner._PROVEN = saved
        os.close(r)


def test_a_chat_approval_is_taken_once_for_its_own_argv():
    secret, path = chat_approval(ARGV)
    assert confirm(secret, list(ARGV)) == (True, True)
    assert not os.path.exists(path), "single use: the approval file is deleted"
    assert confirm(secret, list(ARGV)) == (False, False), "burnt"


def test_a_chat_approval_reads_this_processs_argv_by_default():
    secret, path = chat_approval(list(sys.argv))
    assert confirm(secret) == (True, True) and not os.path.exists(path)
    secret, path = chat_approval(ARGV)
    assert confirm(secret) == (False, False) and os.path.exists(path), "sys.argv is not that command"
    os.unlink(path)


def test_a_chat_approval_is_refused_when_anything_is_off():
    other = tempfile.NamedTemporaryFile("w", delete=False)
    other.write(json.dumps({"argv": ARGV}))
    other.close()
    cases = [("another argv", chat_approval(ARGV), ARGV[:-1] + ["--note", "--owner"]),
             ("a shorter argv", chat_approval(ARGV), ARGV[:-1]),
             ("expired", chat_approval(ARGV, age=lcs_owner.OWNER_CHAT_TTL + 5), ARGV),
             ("from the future", chat_approval(ARGV, age=-60), ARGV),
             ("group bits", chat_approval(ARGV, mode=0o640), ARGV),
             ("other bits", chat_approval(ARGV, mode=0o604), ARGV),
             ("not JSON", chat_approval(ARGV, body="not json"), ARGV),
             ("argv not a list", chat_approval(ARGV, body=json.dumps({"argv": " ".join(ARGV)})), ARGV),
             ("argv not strings", chat_approval(ARGV, body=json.dumps({"argv": [1, 2]})), [1, 2]),
             ("no argv", chat_approval(ARGV, body=json.dumps({"created": "x"})), ARGV),
             ("over 4096 bytes", chat_approval(ARGV, body=json.dumps({"argv": ARGV, "pad": "x" * 4100})), ARGV)]
    for why, (secret, path), argv in cases:
        assert confirm(secret, argv) == (False, False), why
        os.unlink(path)
    secret = secrets.token_hex(32)  # a symlink in the approval's place
    link = os.path.join(_HOME, "command-centre", "owner-nonce.chat-" + hashlib.sha256(secret.encode()).hexdigest())
    os.symlink(other.name, link)
    assert confirm(secret, ARGV) == (False, False), "a symlink"
    os.unlink(link)
    secret, path = chat_approval(ARGV)
    assert confirm(secrets.token_hex(32), ARGV) == (False, False), "another code on the pipe"
    assert confirm(secret.upper(), ARGV) == (False, False), "not lower-case hex"
    assert confirm(secret[:-1], ARGV) == (False, False), "63 characters"
    with open(other.name, "w") as f:  # stdin a redirected file, not a pipe
        f.write(secret + "\n")
    with open(other.name) as f:
        saved, lcs_owner._PROVEN = lcs_owner._PROVEN, False
        assert lcs_owner.owner_confirmed(f.fileno(), ARGV) is False and not lcs_owner.owner_proven()
        lcs_owner._PROVEN = saved
    assert os.path.exists(path), "every refusal leaves the approval alone"
    assert confirm(secret, ARGV) == (True, True), "and the right code still works"
    os.unlink(other.name)


def test_a_chat_approval_counts_until_its_ttl():
    secret, path = chat_approval(ARGV, age=lcs_owner.OWNER_CHAT_TTL - 30)
    assert lcs_owner.OWNER_CHAT_TTL == 900 and confirm(secret, ARGV) == (True, True)


def test_a_chat_approval_in_a_linked_folder_is_refused():
    """The approval must sit in a real command-centre folder, as the hook only writes one there."""
    real = tempfile.mkdtemp()
    linked = tempfile.mkdtemp()
    os.symlink(os.path.join(real, "command-centre"), os.path.join(linked, "command-centre"))
    secret, path = chat_approval(ARGV, home=real)
    os.environ["LCS_PRIVATE_DIR"] = linked
    try:
        assert confirm(secret, ARGV) == (False, False)
    finally:
        os.environ["LCS_PRIVATE_DIR"] = _HOME
    assert os.path.exists(path)


def test_the_command_centres_nonce_still_passes():
    nonce = secrets.token_hex(32)
    nf = private("command-centre", "owner-nonce")
    os.makedirs(os.path.dirname(nf), mode=0o700, exist_ok=True)
    fd = os.open(nf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.write(fd, hashlib.sha256(nonce.encode()).hexdigest().encode())
    os.close(fd)
    chat, chat_path = chat_approval(ARGV)  # a chat approval beside it is left alone
    assert confirm(nonce, ["anything"]) == (True, True) and not os.path.exists(nf)
    assert confirm(nonce, ["anything"]) == (False, False), "burnt"
    assert os.path.exists(chat_path)
    os.unlink(chat_path)
    fd = os.open(nf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.write(fd, hashlib.sha256(nonce.encode()).hexdigest().encode())
    os.close(fd)
    os.utime(nf, (time.time() - lcs_owner.OWNER_NONCE_TTL - 5,) * 2)
    assert confirm(nonce, ["anything"]) == (False, False), "the Command Centre's nonce keeps its 60 seconds"
    os.unlink(nf)


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
