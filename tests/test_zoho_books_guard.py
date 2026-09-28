#!/usr/bin/env python3
"""Tests for .claude/hooks/zoho_books_guard.py (PreToolUse). Stdlib only."""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, ".claude", "hooks", "zoho_books_guard.py")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")

SERVERS = ("zoho-books", "zoho-books-invoices")


def raw(stdin):
    """Run the guard on raw stdin; its decision ("allow" when it prints nothing)."""
    p = subprocess.run([sys.executable, GUARD], input=stdin, capture_output=True, text=True)
    assert p.returncode == 0, (p.returncode, p.stderr)
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else "allow"


def decide(server, tool, tool_input=None):
    return raw(json.dumps({"tool_name": f"mcp__{server}__{tool}", "tool_input": tool_input or {}}))


def hook_command():
    """The zoho-books guard command exactly as .claude/settings.json runs it."""
    with open(SETTINGS) as f:
        cfg = json.load(f)
    cmds = [h["command"] for entry in cfg["hooks"]["PreToolUse"] if entry["matcher"] == "mcp__zoho-books.*"
            for h in entry["hooks"]]
    assert len(cmds) == 1, cmds
    return cmds[0]


def test_read_only_tools_are_allowed_on_both_servers():
    for server in SERVERS:
        assert decide(server, "ZohoBooks_listInvoices") == "allow"
        assert decide(server, "getInvoice") == "allow"
        assert decide(server, "searchContacts") == "allow"
        assert decide(server, "ZohoBooksInvoices_fetchContact") == "allow"
        assert decide(server, "retrieveItems") == "allow"


def test_send_and_destructive_tools_are_denied():
    for server in SERVERS:
        assert decide(server, "ZohoBooks_emailInvoice") == "deny"
        assert decide(server, "sendInvoice") == "deny"
        assert decide(server, "getInvoiceEmailContent") == "deny"
        assert decide(server, "createInvoice") == "deny"
        assert decide(server, "updateInvoice") == "deny"
        assert decide(server, "deleteInvoice") == "deny"
        assert decide(server, "voidInvoice") == "deny"
        assert decide(server, "markInvoiceAsSent") == "deny"
        assert decide(server, "recordPayment") == "deny"
        assert decide(server, "ZohoBooks_someUnknownTool") == "deny"


def test_malformed_events_fail_closed():
    assert raw("{not json") == "deny"
    assert raw("") == "deny"
    assert raw(json.dumps({"tool_input": {}})) == "deny"  # missing tool_name
    assert raw(json.dumps({"tool_name": 123, "tool_input": {}})) == "deny"  # not a string
    assert raw(json.dumps(["not", "an", "object"])) == "deny"


def test_settings_hook_blocks_when_the_guard_cannot_run():
    cmd = hook_command()
    assert cmd.endswith("|| exit 2"), cmd
    event = json.dumps({"tool_name": "mcp__zoho-books__ZohoBooks_deleteInvoice", "tool_input": {}})
    run = lambda c, project: subprocess.run(["sh", "-c", c], input=event, capture_output=True, text=True,
                                            env=dict(os.environ, CLAUDE_PROJECT_DIR=project))
    # the real command, from the worktree: the guard runs and denies with exit 0
    ok = run(cmd, ROOT)
    assert ok.returncode == 0 and json.loads(ok.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny", ok
    # the same command against a guard path that does not exist: exit 2, which blocks a PreToolUse call
    missing = cmd.replace("zoho_books_guard.py", "zoho_books_guard_missing.py")
    assert missing != cmd
    assert run(missing, ROOT).returncode == 2
    assert run(cmd, tempfile.mkdtemp()).returncode == 2


def test_settings_json_is_valid_and_registers_the_guard():
    with open(SETTINGS) as f:
        cfg = json.load(f)
    assert hook_command() == 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/zoho_books_guard.py" || exit 2'
    matchers = [entry["matcher"] for entry in cfg["hooks"]["PreToolUse"]]
    assert "mcp__zoho-mail__.*" in matchers
    assert "mcp__zoho-books.*" in matchers


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
