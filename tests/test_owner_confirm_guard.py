#!/usr/bin/env python3
"""Tests for .claude/hooks/owner_confirm_guard.py (PreToolUse on Bash). Stdlib only."""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, ".claude", "hooks", "owner_confirm_guard.py")


def decide(stdin):
    p = subprocess.run([sys.executable, GUARD], input=stdin, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else None


def bash(command):
    return decide(json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}))


def test_discard_and_every_way_round_the_plain_forms_ask_luca():
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


def test_the_automations_plain_forms_are_left_to_the_other_rules():
    for cmd in (".venv/bin/python scripts/bookings/imap_draft.py save '{\"key\": \"2111-confirmation\", \"html\": \"<p>a & b; $1</p>\"}'",
                ".venv/bin/python scripts/bookings/imap_draft.py attach '<a@b.com>' '{\"key\": \"2111-confirmation\"}'",
                ".venv/bin/python scripts/bookings/imap_draft.py sent 2111 client@example.com 2026-10-01", "ls"):
        assert bash(cmd) is None, cmd


def test_malformed_events_ask():
    assert decide("not json") == "ask"
    assert decide(json.dumps({"tool_name": "Bash", "tool_input": {}})) == "ask"


def test_settings_registers_the_guard_on_bash():
    with open(os.path.join(ROOT, ".claude", "settings.json")) as f:
        hooks = json.load(f)["hooks"]["PreToolUse"]
    cmds = [h["command"] for e in hooks if e["matcher"] == "Bash" for h in e["hooks"]]
    assert any("owner_confirm_guard.py" in c for c in cmds), cmds


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except Exception as e:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(e))
    print(f"\n{fails} failure(s)")
    sys.exit(1 if fails else 0)
