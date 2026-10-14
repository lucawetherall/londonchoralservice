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


def test_discard_always_asks_luca():
    for cmd in (".venv/bin/python scripts/bookings/imap_draft.py discard '<a@b.com>'",
                "cd x && python3 scripts/bookings/imap_draft.py  discard <a@b.com>",
                "echo hi; .venv/bin/python imap_draft.py discard x"):
        assert bash(cmd) == "ask", cmd


def test_other_commands_are_left_to_the_other_rules():
    for cmd in (".venv/bin/python scripts/bookings/imap_draft.py save '{}'",
                ".venv/bin/python scripts/bookings/imap_draft.py attach '<a@b.com>' '{}'", "ls"):
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
