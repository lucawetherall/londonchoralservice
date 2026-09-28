#!/usr/bin/env python3
"""Tests for .claude/hooks/zoho_guard.py (PreToolUse). Stdlib only."""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, ".claude", "hooks", "zoho_guard.py")


def decide(tool, body=None):
    event = {"tool_name": f"mcp__zoho-mail__ZohoMail_{tool}", "tool_input": {"body": body or {}}}
    out = subprocess.run([sys.executable, GUARD], input=json.dumps(event), capture_output=True, text=True).stdout
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else "allow"


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
