#!/usr/bin/env python3
"""Tests for .claude/hooks/calendar_guard.py (PreToolUse). Stdlib only."""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, ".claude", "hooks", "calendar_guard.py")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")
SERVER = "caefd5da-81a5-4eb0-993a-dfeaa5b9d7c1"
MATCHER = f"mcp__{SERVER}__.*"
READ = ("list_calendars", "list_events", "search_events", "get_event", "suggest_time")


LCS_CAL = "abc123@group.calendar.google.com"


def home_with(config):
    """A temporary HOME whose ~/lcs-private/calendar.json holds `config` (None: no file)."""
    home = tempfile.mkdtemp()
    os.makedirs(os.path.join(home, "lcs-private"))
    if config is not None:
        with open(os.path.join(home, "lcs-private", "calendar.json"), "w") as f:
            f.write(config if isinstance(config, str) else json.dumps(config))
    return home


HOME = home_with({"lcs_calendar_id": LCS_CAL})


def raw(stdin, home=None):
    """Run the guard on raw stdin; its decision ("allow" when it prints nothing)."""
    p = subprocess.run([sys.executable, GUARD], input=stdin, capture_output=True, text=True,
                       env=dict(os.environ, HOME=home or HOME))
    assert p.returncode == 0, (p.returncode, p.stderr)
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else "allow"


def decide(tool, tool_input=None, home=None):
    return raw(json.dumps({"tool_name": tool, "tool_input": tool_input or {}}), home)


CREATE = f"mcp__{SERVER}__create_event"


def booking(**changes):
    event = {"calendarId": LCS_CAL, "summary": "LCS 2108 Wedding, Sam", "startTime": "2027-08-21T14:00:00+01:00",
             "endTime": "2027-08-21T16:00:00+01:00", "timeZone": "Europe/London", "location": "St Mary's, Barnes",
             "description": "Small Choir (4 singers), £1,150. Invoice 2108.", "notificationLevel": "NONE",
             "availability": "AVAILABILITY_FREE"}
    event.update(changes)
    return {k: v for k, v in event.items() if v is not None}


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
    for name in ("update_event", "delete_event", "respond_to_event", "unknown_tool",
                 "List_events", "list_events_and_delete", ""):
        assert decide(f"mcp__{SERVER}__{name}") == "deny", name


DELETE = f"mcp__{SERVER}__delete_event"


def approvals(home):
    folder = os.path.join(home, "lcs-private", "command-centre", "approvals")
    os.makedirs(folder, mode=0o700, exist_ok=True)
    for d in (folder, os.path.dirname(folder)):
        os.chmod(d, 0o700)
    return folder


def approve(home, event_id="e1abc", cal=LCS_CAL, age=0, ttl=600, mode=0o600, name=None, **changes):
    """An approval as the Command Centre's calendar-delete action writes it (command_centre/actions.py _cal_run)."""
    import hashlib, secrets, time
    nonce_sha = hashlib.sha256(secrets.token_hex(32).encode()).hexdigest()
    at = int(time.time()) - age
    rec = {"kind": "calendar-delete", "calendar_id": cal, "event_id": event_id, "nonce_sha256": nonce_sha,
           "binding": hashlib.sha256(f"lcs-calendar-delete\n{nonce_sha}\n{cal}\n{event_id}".encode()).hexdigest(),
           "approved_at": at, "expires_at": at + ttl, "approved_by": "luca", "passkey": "pk1"}
    rec.update(changes)
    path = os.path.join(approvals(home), name or f"calendar-delete-{nonce_sha[:32]}.json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(rec, f)
    os.chmod(path, mode)
    return path


def test_delete_without_an_approval_is_denied_never_asked():
    home = home_with({"lcs_calendar_id": LCS_CAL})
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=home) == "deny"
    for bad in ({"eventId": "e1abc"}, {"calendarId": "primary", "eventId": "e1abc"},
                {"calendarId": LCS_CAL, "eventId": ""}, {"calendarId": LCS_CAL, "eventId": "e1abc", "notificationLevel": "ALL"},
                {"calendarId": LCS_CAL, "eventId": "e1abc", "sendUpdates": "all"}):
        assert decide(DELETE, bad, home=home) == "deny", bad
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=home_with(None)) == "deny"


def test_a_valid_approval_allows_exactly_that_delete_once():
    home = home_with({"lcs_calendar_id": LCS_CAL})
    path = approve(home)
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc", "notificationLevel": "NONE"}, home=home) == "allow"
    assert not os.path.exists(path), "the approval is burnt as the call is allowed"
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=home) == "deny", "reused"


def test_an_approval_never_covers_another_event_calendar_or_shape():
    home = home_with({"lcs_calendar_id": LCS_CAL})
    path = approve(home)
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e2abc"}, home=home) == "deny", "wrong event"
    assert decide(DELETE, {"calendarId": "primary", "eventId": "e1abc"}, home=home) == "deny", "wrong calendar"
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc", "notificationLevel": "ALL"}, home=home) == "deny"
    assert os.path.exists(path), "a refused call leaves the approval for the right one"
    other = home_with({"lcs_calendar_id": LCS_CAL})
    approve(other, cal="primary")  # approved for another calendar: never matches the LCS one
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=other) == "deny"


def test_expired_future_long_or_tampered_approvals_are_denied():
    for kw in ({"age": 601}, {"age": 700, "ttl": 600}, {"age": -60}, {"ttl": 3600},
               {"binding": "0" * 64}, {"kind": "books-import"}, {"name": "calendar-delete-" + "a" * 32 + ".json"},
               {"approved_at": "now"}, {"event_id": "E1ABC"}):
        home = home_with({"lcs_calendar_id": LCS_CAL})
        approve(home, **kw)
        assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=home) == "deny", kw


def test_symlinked_wrong_mode_or_linked_approvals_are_denied():
    home = home_with({"lcs_calendar_id": LCS_CAL})
    approve(home, mode=0o644)
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=home) == "deny", "mode 644"
    home = home_with({"lcs_calendar_id": LCS_CAL})  # a symlink to a good approval elsewhere
    real = approve(home_with({"lcs_calendar_id": LCS_CAL}))
    os.symlink(real, os.path.join(approvals(home), os.path.basename(real)))
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=home) == "deny", "symlinked file"
    assert os.path.exists(real)
    home = home_with({"lcs_calendar_id": LCS_CAL})  # a hard link: two names for one approval
    path = approve(home)
    os.link(path, os.path.join(tempfile.mkdtemp(), "copy.json"))
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=home) == "deny", "hard link"
    home = home_with({"lcs_calendar_id": LCS_CAL})  # the approvals folder is a symlink to a folder of good ones
    elsewhere = home_with({"lcs_calendar_id": LCS_CAL})
    approve(elsewhere)
    os.makedirs(os.path.join(home, "lcs-private", "command-centre"), mode=0o700)
    os.symlink(approvals(elsewhere), os.path.join(home, "lcs-private", "command-centre", "approvals"))
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=home) == "deny", "symlinked folder"
    home = home_with({"lcs_calendar_id": LCS_CAL})  # a folder others can write to
    approve(home)
    os.chmod(approvals(home), 0o777)
    os.chmod(os.path.join(home, "lcs-private", "command-centre", "approvals"), 0o777)
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=home) == "deny", "folder mode 777"


def test_the_command_centre_writes_approvals_the_guard_accepts():
    """The app's own writer (command_centre/actions.py calendar-delete) and this guard agree on the format."""
    home = home_with({"lcs_calendar_id": LCS_CAL})
    code = ("import sys; sys.path.insert(0, sys.argv[1]); from command_centre import actions; "
            "c = actions._cal_validate({'event_id': 'e1abc'}); "
            "print(actions._cal_run(c, {'login': 'luca', 'passkey': 'pk1'}))")
    p = subprocess.run([sys.executable, "-c", code, ROOT], capture_output=True, text=True,
                       env=dict(os.environ, LCS_PRIVATE_DIR=os.path.join(home, "lcs-private"), HOME=home))
    assert p.returncode == 0 and "approved" in p.stdout, (p.stdout, p.stderr)
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e2abc"}, home=home) == "deny"
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=home) == "allow"
    assert decide(DELETE, {"calendarId": LCS_CAL, "eventId": "e1abc"}, home=home) == "deny"


def test_booking_on_the_lcs_calendar_is_allowed():
    assert decide(CREATE, booking()) == "allow"
    assert decide(CREATE, booking(allDay=True, startTime="2027-08-21", endTime="2027-08-22",
                                  location=None, notificationLevel=None)) == "allow"


def test_create_event_elsewhere_or_with_extras_is_denied():
    for changes in ({"calendarId": "primary"}, {"calendarId": "lucwetho@gmail.com"}, {"calendarId": None},
                    {"calendarId": LCS_CAL + " "}, {"attendees": [{"email": "a@b.com"}]},
                    {"attendeeEmails": ["a@b.com"]}, {"addGoogleMeetUrl": True}, {"recurrenceData": ["RRULE:FREQ=DAILY"]},
                    {"attachments": [{"fileUrl": "https://x"}]}, {"notificationLevel": "ALL"},
                    {"summary": "Wedding, Sam"}, {"summary": "LCS " + "x" * 120}, {"summary": None},
                    {"startTime": None}, {"endTime": ""}, {"description": "Client sam@example.com"},
                    {"location": "call sam@example.com"}, {"description": "Sort code 12-34-56, account 12345678"},
                    {"description": 5}, {"description": "x" * 1001}):
        assert decide(CREATE, booking(**changes)) == "deny", changes
    assert decide(CREATE, "not an object") == "deny"


def test_create_event_without_a_good_config_is_denied():
    for config in (None, "{not json", [], {}, {"lcs_calendar_id": ""}, {"lcs_calendar_id": 5}):
        assert decide(CREATE, booking(), home_with(config)) == "deny", config


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


def test_settings_registers_the_guard_and_allows_reads_and_create_event():
    assert hook_command() == 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/calendar_guard.py" || exit 2'
    with open(SETTINGS) as f:
        cfg = json.load(f)
    allowed = sorted(a for a in cfg["permissions"]["allow"] if SERVER in a)
    assert allowed == sorted(f"mcp__{SERVER}__{n}" for n in
                             ("list_calendars", "list_events", "search_events", "get_event", "create_event")), allowed
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
