#!/usr/bin/env python3
"""Tests for .claude/hooks/calendar_guard.py (PreToolUse). Stdlib only."""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, ".claude", "hooks", "calendar_guard.py")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")
SERVER = "caefd5da-81a5-4eb0-993a-dfeaa5b9d7c1"
MATCHER = f"mcp__{SERVER}__.*"
READ = ("list_calendars", "list_events", "search_events", "get_event", "suggest_time")


def raw(stdin):
    """Run the guard on raw stdin; its decision ("allow" when it prints nothing)."""
    p = subprocess.run([sys.executable, GUARD], input=stdin, capture_output=True, text=True)
    assert p.returncode == 0, (p.returncode, p.stderr)
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else "allow"


def decide(tool, tool_input=None):
    return raw(json.dumps({"tool_name": tool, "tool_input": tool_input or {}}))


def hook_command():
    with open(SETTINGS) as f:
        cfg = json.load(f)
    cmds = [h["command"] for entry in cfg["hooks"]["PreToolUse"] if entry["matcher"] == MATCHER
            for h in entry["hooks"]]
    assert len(cmds) == 1, cmds
    return cmds[0]


def test_read_tools_are_allowed():
    for name in READ:
        assert decide(f"mcp__{SERVER}__{name}", {"calendarId": "primary"}) == "allow", name


def test_write_tools_are_denied():
    for name in ("create_event", "update_event", "delete_event", "respond_to_event", "unknown_tool",
                 "List_events", "list_events_and_delete", ""):
        assert decide(f"mcp__{SERVER}__{name}") == "deny", name


def test_other_servers_and_odd_names_are_denied():
    for tool in ("mcp__other-calendar__list_events", "mcp__zoho-books__list_events", "list_events",
                 f"mcp__{SERVER}__list_events__x", f"mcp__{SERVER}", f"xmcp__{SERVER}__list_events"):
        assert decide(tool) == "deny", tool


def test_malformed_events_fail_closed():
    assert raw("{not json") == "deny"
    assert raw("") == "deny"
    assert raw(json.dumps({"tool_input": {}})) == "deny"
    assert raw(json.dumps({"tool_name": 123})) == "deny"
    assert raw(json.dumps(["not", "an", "object"])) == "deny"


def test_settings_registers_the_guard_and_allows_only_read_tools():
    assert hook_command() == 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/calendar_guard.py" || exit 2'
    with open(SETTINGS) as f:
        cfg = json.load(f)
    allowed = sorted(a for a in cfg["permissions"]["allow"] if SERVER in a)
    assert allowed == sorted(f"mcp__{SERVER}__{n}" for n in
                             ("list_calendars", "list_events", "search_events", "get_event")), allowed
    assert f"mcp__{SERVER}" not in cfg["permissions"]["allow"]  # never the whole server


def test_settings_hook_blocks_when_the_guard_cannot_run():
    cmd = hook_command()
    event = json.dumps({"tool_name": f"mcp__{SERVER}__delete_event", "tool_input": {}})
    run = lambda c, project: subprocess.run(["sh", "-c", c], input=event, capture_output=True, text=True,
                                            env=dict(os.environ, CLAUDE_PROJECT_DIR=project))
    ok = run(cmd, ROOT)
    assert ok.returncode == 0 and json.loads(ok.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny", ok
    missing = cmd.replace("calendar_guard.py", "calendar_guard_missing.py")
    assert missing != cmd
    assert run(missing, ROOT).returncode == 2
    assert run(cmd, tempfile.mkdtemp()).returncode == 2


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
