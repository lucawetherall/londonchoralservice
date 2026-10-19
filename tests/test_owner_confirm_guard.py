#!/usr/bin/env python3
"""Tests for .claude/hooks/owner_confirm_guard.py (PreToolUse on Bash). Stdlib only.

Every run gets a temporary private folder (LCS_PRIVATE_DIR): the real ~/lcs-private is never touched."""
import glob, hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, ".claude", "hooks", "owner_confirm_guard.py")
PRIVATE = tempfile.mkdtemp(prefix="lcs-owner-guard-")
CC = os.path.join(PRIVATE, "command-centre")
os.makedirs(CC, mode=0o700)
PY = ".venv/bin/python"
FACT = f"{PY} scripts/bookings/check_payments.py --fact 2108A paid-in-full --on 2026-10-19 --owner"


def hook(stdin, private=PRIVATE):
    """The hook's hookSpecificOutput ({} when it has no opinion)."""
    env = dict(os.environ, LCS_PRIVATE_DIR=private)
    p = subprocess.run([sys.executable, GUARD], input=stdin, capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)["hookSpecificOutput"] if p.stdout.strip() else {}


def decide(stdin, private=PRIVATE):
    return hook(stdin, private).get("permissionDecision")


def event(command, **extra):
    return json.dumps(dict({"tool_name": "Bash", "session_id": "s1",
                            "tool_input": {"command": command, "description": "x"}}, **extra))


def bash(command, **extra):
    return decide(event(command, **extra))


def approvals():
    return sorted(glob.glob(os.path.join(CC, "owner-nonce.chat-*")))


def clear():
    for p in approvals():
        os.unlink(p)


def test_discard_and_every_way_round_the_plain_forms_ask_luca():
    """A second layer only: discard refuses without Luca's approval (tests/test_imap_draft.py). Without --owner,
    an odd imap_draft command asks; with it, only the plain form asks (the approval prompt) and the rest are denied."""
    for cmd in (".venv/bin/python scripts/bookings/imap_draft.py discard '<a@b.com>'",
                "cd x && python3 scripts/bookings/imap_draft.py  discard '<a@b.com>'",
                "python3 -m imap_draft discard x",
                "python3 -c \"import imap_draft as d; d.main([chr(100)+'iscard','x'])\"",
                "X=discard; .venv/bin/python scripts/bookings/imap_draft.py $X x",
                ".venv/bin/python scripts/bookings/imap_draft.py save '{}'; .venv/bin/python scripts/bookings/imap_draft.py discard x",
                ".venv/bin/python scripts/bookings/imap_draft.py save \"$(cat spec)\"",
                ".venv/bin/python other.py  # calls trash_draft",
                ".venv/bin/python -c 'import x; x.forget_saved(1)'"):
        assert bash(cmd) == "ask", cmd
    assert bash(".venv/bin/python scripts/bookings/imap_draft.py discard '<a@b.com>' --owner") == "ask"
    assert bash("echo x | .venv/bin/python scripts/bookings/imap_draft.py discard '<a@b.com>' --owner") == "deny"
    clear()


def test_the_automations_plain_forms_are_left_to_the_other_rules():
    for cmd in (".venv/bin/python scripts/bookings/imap_draft.py save '{\"key\": \"2111-confirmation\", \"html\": \"<p>a & b; $1</p>\"}'",
                ".venv/bin/python scripts/bookings/imap_draft.py attach '<a@b.com>' '{\"key\": \"2111-confirmation\"}'",
                ".venv/bin/python scripts/bookings/imap_draft.py sent 2111 client@example.com 2026-10-01",
                ".venv/bin/python scripts/bookings/imap_draft.py replace '<old@x.com>' '<new@x.com>'", "ls",
                f"{PY} scripts/bookings/check_payments.py --fact 2111 cancelled --on 2026-10-01"):
        assert bash(cmd) is None, cmd


def test_replace_chained_or_disguised_still_asks():
    for cmd in (".venv/bin/python scripts/bookings/imap_draft.py replace '<a@b.com>' '<c@d.com>'; rm x",
                ".venv/bin/python scripts/bookings/imap_draft.py replace $(cat ids)"):
        assert bash(cmd) == "ask", cmd


def test_malformed_events_ask():
    assert decide("not json") == "ask"
    assert decide(json.dumps({"tool_name": "Bash", "tool_input": {}})) == "ask"
    assert decide("not json --owner") == "deny"  # may be an owner action: refused, not asked


def test_an_owner_command_asks_with_the_one_time_code_piped_in():
    clear()
    ti = {"command": FACT, "description": "Record the payment", "timeout": 60000, "run_in_background": False}
    out = hook(json.dumps({"tool_name": "Bash", "session_id": "s1", "tool_input": ti}))
    assert out["permissionDecision"] == "ask", out
    new = out["updatedInput"]
    m = re.fullmatch(r"printf '%s\\n' ([0-9a-f]{64}) \| (.*)", new["command"], re.S)
    assert m and m.group(2) == FACT, new["command"]
    assert {k: v for k, v in new.items() if k != "command"} == {k: v for k, v in ti.items() if k != "command"}, new
    reason = out["permissionDecisionReason"]
    assert reason.startswith("Owner approval: check_payments.py --fact 2108A paid-in-full --on 2026-10-19. "), reason
    assert "Allow only if you asked Claude for this in this chat; otherwise Deny" in reason and m.group(1) not in reason
    files = approvals()
    assert files == [os.path.join(CC, "owner-nonce.chat-" + hashlib.sha256(m.group(1).encode()).hexdigest())], files
    st = os.lstat(files[0])
    assert stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o600, oct(st.st_mode)
    record = json.load(open(files[0]))
    assert record["argv"] == ["scripts/bookings/check_payments.py", "--fact", "2108A", "paid-in-full", "--on",
                              "2026-10-19", "--owner"], record
    assert record["created"].endswith("+00:00") and record["session"] == "s1", record
    clear()


def test_quoted_arguments_are_recorded_as_the_shell_reads_them():
    clear()
    cmd = f"{PY} scripts/bookings/check_payments.py --note 2111 \"paid in full 2026-09-28, by card\" --owner"
    out = hook(event(cmd))
    assert out["permissionDecision"] == "ask", out
    assert json.load(open(approvals()[0]))["argv"][3] == "paid in full 2026-09-28, by card"
    out = hook(event(f"{PY} scripts/bookings/imap_draft.py discard '<a@b.com>' --owner"))
    assert out["permissionDecision"] == "ask", out
    assert json.load(open(approvals()[0]))["argv"] == ["scripts/bookings/imap_draft.py", "discard", "<a@b.com>",
                                                        "--owner"]
    clear()


def test_a_second_owner_command_replaces_the_first_approval():
    clear()
    hook(event(FACT))
    first = approvals()
    hook(event(f"{PY} scripts/bookings/events.py retract a1b2c3d4e5f60718 --owner"))
    second = approvals()
    assert len(first) == len(second) == 1 and first != second, (first, second)
    clear()


def test_a_subagent_is_denied():
    clear()
    out = hook(event(FACT, agent_id="agent-123"))
    assert out["permissionDecision"] == "deny" and "never in a subagent" in out["permissionDecisionReason"], out
    assert approvals() == []


def test_compound_and_odd_forms_are_denied():
    clear()
    for cmd in (FACT + "; ls", FACT + " && ls", "ls; " + FACT, FACT + " | cat", "cat x | " + FACT,
                FACT.replace("2108A", "$X"), FACT.replace("2108A", "\"$X\""), "X=1 " + FACT,
                "LCS_PRIVATE_DIR=/tmp/x " + FACT, FACT.replace("2108A", "`id`"), FACT.replace(PY, "python3"),
                FACT.replace("check_payments", "assistant_io"), f"{PY} scripts/other.py --owner",
                FACT + " > /tmp/out", FACT + " < /tmp/in", FACT + "\nls", FACT.replace("2108A", "21*"),
                FACT.replace("2108A", "~/x"), FACT.replace("2108A", "'a'\"b\""), f"(cd . && {FACT})",
                f"{PY} -c 'import sys' scripts/bookings/check_payments.py --owner", f"bash -c '{FACT}'",
                FACT.replace("--on 2026-10-19", "--on '2026\n10'")):
        out = hook(event(cmd))
        assert out.get("permissionDecision") == "deny", (cmd, out)
        assert "one plain command" in out["permissionDecisionReason"], (cmd, out)
    assert approvals() == []


def test_owner_hidden_by_quotes_is_still_an_owner_command():
    clear()
    for cmd in (FACT.replace("--owner", "--own''er") + " | cat", FACT.replace("--owner", "--own\\er") + "; ls",
                FACT.replace("--owner", "'--owner'") + " && ls"):
        assert bash(cmd) == "deny", cmd
    out = hook(event(FACT.replace("--owner", "--own''er")))
    assert out["permissionDecision"] == "deny", out  # not plain ('' glued to a word), so refused, not approved
    assert approvals() == []


def test_a_missing_or_linked_private_folder_is_denied():
    clear()
    empty = tempfile.mkdtemp(prefix="lcs-owner-guard-empty-")
    out = hook(event(FACT), private=empty)
    assert out["permissionDecision"] == "deny" and "isn't set up" in out["permissionDecisionReason"], out
    linked = tempfile.mkdtemp(prefix="lcs-owner-guard-link-")
    os.symlink(CC, os.path.join(linked, "command-centre"))
    out = hook(event(FACT), private=linked)
    assert out["permissionDecision"] == "deny" and "isn't set up" in out["permissionDecisionReason"], out
    assert approvals() == []
    shutil.rmtree(empty)
    shutil.rmtree(linked)


def test_a_later_command_in_the_same_session_retires_an_unused_approval():
    """A prompt Luca denied leaves its approval file: the session's next command deletes it before it runs; another
    session's approval and the Command Centre's own nonce file are left alone."""
    clear()
    hook(event(FACT, session_id="other"))
    theirs = approvals()
    cc_nonce = os.path.join(CC, "owner-nonce")
    open(os.open(cc_nonce, os.O_WRONLY | os.O_CREAT, 0o600), "w").close()
    assert bash("git status", session_id="s1") is None and approvals() == theirs
    hook(event(FACT, session_id="s1"))  # replaces every outstanding approval, as minting always does
    assert len(approvals()) == 1 and approvals() != theirs
    assert bash("git status", session_id="s1") is None and approvals() == []
    assert os.path.exists(cc_nonce)
    os.unlink(cc_nonce)


def test_a_command_naming_an_outstanding_code_is_denied():
    clear()
    out = hook(event(FACT, session_id="other"))
    secret = re.search(r"[0-9a-f]{64}", out["updatedInput"]["command"]).group(0)
    for cmd in (f"printf '%s\\n' {secret} | {PY} scripts/bookings/check_payments.py --fact 2108A paid-in-full",
                f"echo x{secret}y > /tmp/x"):
        out = hook(event(cmd, session_id="s2"))
        assert out.get("permissionDecision") == "deny" and "one-time approval code" in out["permissionDecisionReason"], out
    assert bash("echo " + "ab" * 32, session_id="other") is None  # any other 64 hex is fine
    clear()


def test_settings_registers_the_guard_on_bash_and_asks_for_owner_commands():
    with open(os.path.join(ROOT, ".claude", "settings.json")) as f:
        settings = json.load(f)
    cmds = [h["command"] for e in settings["hooks"]["PreToolUse"] if e["matcher"] == "Bash" for h in e["hooks"]]
    assert any("owner_confirm_guard.py" in c for c in cmds), cmds
    assert "Bash(*--owner*)" in settings["permissions"]["ask"], settings["permissions"].get("ask")


if __name__ == "__main__":
    fails = 0
    try:
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                try:
                    fn()
                    print("ok  ", name)
                except Exception as e:  # noqa: BLE001
                    fails += 1
                    print("FAIL", name, repr(e))
    finally:
        shutil.rmtree(PRIVATE, ignore_errors=True)
    print(f"\n{fails} failure(s)")
    sys.exit(1 if fails else 0)
