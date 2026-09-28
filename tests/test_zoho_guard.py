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


# --- Cc, recipients and bank details in drafts -----------------------------------------------------

def office(**kw):
    return dict(draft("office@londonchoralservice.com"), **kw)


def test_cc_is_denied():
    assert decide("sendReplyEmail", office(ccAddress="other@example.com")) == "deny"
    assert decide("sendReplyEmail", office(ccAddress="")) == "allow"
    assert decide("sendReplyEmail", office(ccAddress=["x@example.com"])) == "deny"


def test_one_recipient_only():
    assert decide("sendReplyEmail", office(toAddress="a@example.com,b@example.com")) == "deny"
    assert decide("sendReplyEmail", office(toAddress="a@example.com; b@example.com")) == "deny"
    assert decide("sendReplyEmail", office(toAddress="Ann Smith <ann@example.com>")) == "allow"


QUOTE = ("<p>Dear Ann,</p><p>Thank you so much for getting in touch about your wedding on Saturday 21 November 2026 "
         "at St Mary&rsquo;s, Barnes (ceremony 14:00&ndash;15:00, 2pm). I&rsquo;d recommend:</p>"
         "<p>Small Choir (4 singers) &mdash; &pound;1,150<br>Small Choir with an organist &mdash; £1,400<br>"
         "Full Choir (8 singers) — £2,000.00</p><p>We&rsquo;re not VAT-registered, so no VAT is added. "
         "A deposit of £575.00 secures the date, with the balance of £575.00 due on 20/11/2026 or 2026-11-20. "
         "Invoice 2111 will follow.</p><p>Do give me a ring on 07356 042468, +44 7356 042468, +44 (0)7356 042468 "
         "or WhatsApp https://wa.me/447356042468.</p>"
         "<p style=\"color:#123456\">Best wishes,<br>Luca</p>")


def test_an_ordinary_quote_passes():
    assert decide("sendReplyEmail", office(subject="Re: Wedding 21/11/2026", content=QUOTE)) == "allow"


def test_bank_details_in_a_draft_are_denied():
    for text in ("Please pay to sort code 04-00-04, account 12345678.",
                 "Our bank: 04-00-04 12345678",
                 "Account number: 12345678",
                 "IBAN GB33 BUKB 2020 1555 5555 55",
                 "the balance to GB33BUKB20201555555555 please",
                 "SWIFT/BIC: BUKBGB22",
                 "s/c 040004 a/c 12345678",
                 "the bank details are 04 00 04 / 1234 5678"):
        assert decide("sendReplyEmail", office(content=f"<p>{text}</p>")) == "deny", text
    assert decide("sendReplyEmail", office(subject="sort code 04-00-04", content="<p>Hello</p>")) == "deny"
    # the house wording, with no numbers, is fine
    assert decide("sendReplyEmail", office(content="<p>The bank details are on your invoice.</p>")) == "allow"


def test_bank_scan_fails_closed_on_a_non_text_content():
    assert decide("sendReplyEmail", office(content={"html": "x"})) == "deny"


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
