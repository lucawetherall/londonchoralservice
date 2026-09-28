#!/usr/bin/env python3
"""Tests for .claude/hooks/zoho_guard.py (PreToolUse). Stdlib only."""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, ".claude", "hooks", "zoho_guard.py")


SETTINGS = os.path.join(ROOT, ".claude", "settings.json")


def raw(stdin):
    """Run the guard on raw stdin; its decision ("allow" when it prints nothing)."""
    p = subprocess.run([sys.executable, GUARD], input=stdin, capture_output=True, text=True)
    assert p.returncode == 0, (p.returncode, p.stderr)
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else "allow"


def decide(tool, body=None):
    return raw(json.dumps({"tool_name": f"mcp__zoho-mail__ZohoMail_{tool}", "tool_input": {"body": body or {}}}))


def hook_command():
    """The zoho guard command exactly as .claude/settings.json runs it."""
    with open(SETTINGS) as f:
        cfg = json.load(f)
    cmds = [h["command"] for entry in cfg["hooks"]["PreToolUse"] if entry["matcher"] == "mcp__zoho-mail__.*"
            for h in entry["hooks"]]
    assert len(cmds) == 1, cmds
    return cmds[0]


def draft(frm):
    return {"mode": "draft", "fromAddress": frm, "toAddress": "someone@example.com"}


def test_reads_are_allowed():
    assert decide("SearchEmails") == "allow"


def test_drafts_from_office_and_luca_are_allowed():
    assert decide("sendReplyEmail", draft("office@londonchoralservice.com")) == "allow"
    assert decide("sendReplyEmail", draft("luca@almaconsort.com")) == "allow"


def test_other_senders_and_real_sends_are_denied():
    assert decide("sendEmail", draft("izzy@almaconsort.com")) == "deny"
    assert decide("sendReplyEmail", {"fromAddress": "luca@almaconsort.com", "toAddress": "a@b.com"}) == "deny"
    assert decide("sendEmail", dict(draft("luca@almaconsort.com"), isSchedule=True)) == "deny"
    assert decide("emptyFolder") == "deny"


def test_malformed_events_fail_closed():
    draft_ok = draft("office@londonchoralservice.com")
    assert raw("{not json") == "deny"
    assert raw("") == "deny"
    assert raw(json.dumps({"tool_name": "mcp__zoho-mail__ZohoMail_sendEmail", "tool_input": {"body": json.dumps(draft_ok)}})) == "deny"
    assert raw(json.dumps({"tool_name": "mcp__zoho-mail__ZohoMail_sendEmail", "tool_input": draft_ok})) == "deny"
    assert raw(json.dumps({"tool_input": {"body": draft_ok}})) == "deny"
    assert raw(json.dumps({"tool_name": "mcp__zoho-mail__ZohoMail_sendEmail", "tool_input": "x"})) == "deny"
    assert raw(json.dumps(["not", "an", "object"])) == "deny"


def test_settings_hook_blocks_when_the_guard_cannot_run():
    cmd = hook_command()
    assert cmd.endswith("|| exit 2"), cmd
    event = json.dumps({"tool_name": "mcp__zoho-mail__ZohoMail_sendEmail", "tool_input": {"body": draft("izzy@almaconsort.com")}})
    run = lambda c, project: subprocess.run(["sh", "-c", c], input=event, capture_output=True, text=True,
                                            env=dict(os.environ, CLAUDE_PROJECT_DIR=project))
    # the real command, from the worktree: the guard runs and denies with exit 0
    ok = run(cmd, ROOT)
    assert ok.returncode == 0 and json.loads(ok.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny", ok
    # the same command against a guard path that does not exist: exit 2, which blocks a PreToolUse call
    missing = cmd.replace("zoho_guard.py", "zoho_guard_missing.py")
    assert missing != cmd
    assert run(missing, ROOT).returncode == 2
    assert run(cmd, tempfile.mkdtemp()).returncode == 2


def test_settings_json_is_valid_and_keeps_the_guard_matcher():
    with open(SETTINGS) as f:
        cfg = json.load(f)
    assert "Bash(security find-generic-password *)" in cfg["permissions"]["deny"]
    assert hook_command() == 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/zoho_guard.py" || exit 2'


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
