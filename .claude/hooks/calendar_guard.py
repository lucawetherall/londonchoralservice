#!/usr/bin/env python3
"""PreToolUse guard for the Google Calendar connector
(matcher mcp__caefd5da-81a5-4eb0-993a-dfeaa5b9d7c1__.*).

The enquiry assistant reads Luca's diary before drafting a reply. This hook
allows the connector's read tools (list_calendars, list_events, search_events,
get_event, suggest_time) and one write: create_event on the "London Choral
Service" calendar, for a confirmed booking (owner decision, 28 Sep 2026).

That calendar's id lives in ~/lcs-private/calendar.json as {"lcs_calendar_id": "…"}
(outside the public repo). create_event is allowed only when:
  - calendarId is exactly that id (never the primary or any other calendar);
  - it uses only the keys in CREATE_KEYS: no attendees, invitations, Meet links,
    attachments, recurrence or colours;
  - summary starts with "LCS " and is at most 120 characters;
  - notificationLevel, if given, is "NONE";
  - no text field holds an email address or bank details.
delete_event (owner decision, 14 Oct 2026) is allowed only with Luca's passkey:
he approves "delete LCS calendar event <id>" in the Command Centre, which writes
a one-time approval, ~/lcs-private/command-centre/approvals/calendar-delete-
<32 hex>.json. The call must be on the London Choral Service calendar, with only
calendarId, eventId and notificationLevel "NONE", and an approval must name
exactly that calendarId and eventId, be unexpired (at most APPROVAL_TTL seconds
from its approval), and be a regular file of this user's, mode 600, with one
link, in a mode-700 folder that is not a symlink (nor is its parent). The guard
deletes the approval as it allows the call, so it works once; if it can't, it
denies. Without one, delete_event is denied: there is no "ask" (auto mode could
settle one without Luca). Claude never writes approvals (settings deny writes
there, and mcp_bypass_guard.py refuses shell commands naming the folder). The
scheduled tasks never delete events. Updating or responding to an
event, and any tool the connector adds later, are denied. It accepts only tools of this one connector (on a new
machine whose connector id differs, update SERVER here, the matcher and the
allowlist in .claude/settings.json together). It fails closed: any error, a
missing or malformed config, or a tool name of the wrong shape denies the call.
"""
import hashlib
import hmac
import json
import os
import re
import stat
import sys
import time

SERVER = "caefd5da-81a5-4eb0-993a-dfeaa5b9d7c1"
READ_TOOLS = {"list_calendars", "list_events", "search_events", "get_event", "suggest_time"}
CONFIG = os.path.join("~", "lcs-private", "calendar.json")
CREATE_KEYS = {"calendarId", "summary", "startTime", "endTime", "timeZone", "allDay", "location",
               "description", "availability", "notificationLevel", "useDefaultReminders"}
TEXT_MAX = {"summary": 120, "location": 300, "description": 1000}
EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
P = "Calendar guard: "


def lcs_calendar_id():
    with open(os.path.expanduser(CONFIG)) as f:
        cfg = json.load(f)
    cal = cfg.get("lcs_calendar_id") if isinstance(cfg, dict) else None
    if not isinstance(cal, str) or not cal.strip():
        raise ValueError("no lcs_calendar_id")
    return cal


def check_create(tool_input):
    from zoho_books_guard import bank_details_in  # imported here so an import error fails closed in main()
    if not isinstance(tool_input, dict):
        return f"{P}create_event input must be an object."
    extra = sorted(set(tool_input) - CREATE_KEYS)
    if extra:
        return f"{P}create_event may not set {', '.join(extra)} (no guests, invitations, Meet links or recurrence)."
    try:
        cal = lcs_calendar_id()
    except Exception:
        return f"{P}{CONFIG} is missing or has no lcs_calendar_id; events can't be created until it's set."
    if tool_input.get("calendarId") != cal:
        return f"{P}events may be created only on the London Choral Service calendar."
    summary = tool_input.get("summary")
    if not isinstance(summary, str) or not summary.startswith("LCS "):
        return f"{P}the event title must start with \"LCS \"."
    for key in ("startTime", "endTime"):
        if not isinstance(tool_input.get(key), str) or not tool_input[key]:
            return f"{P}{key} is required."
    if tool_input.get("notificationLevel", "NONE") != "NONE":
        return f"{P}notificationLevel must be NONE."
    for key, limit in TEXT_MAX.items():
        value = tool_input.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or len(value) > limit:
            return f"{P}{key} must be text of at most {limit} characters."
        if EMAIL.search(value):
            return f"{P}{key} may not hold an email address."
        if bank_details_in(value):
            return f"{P}{key} looks like bank details."
    return None


DELETE_KEYS = {"calendarId", "eventId", "notificationLevel"}
ALLOW = "allow:"
APPROVALS = os.path.join("~", "lcs-private", "command-centre", "approvals")
APPROVAL_NAME = re.compile(r"calendar-delete-[0-9a-f]{32}\.json")
APPROVAL_TTL = 600  # seconds; the Command Centre's CAL_APPROVAL_TTL
APPROVAL_MAX_BYTES = 4096
NO_APPROVAL = (f"{P}deleting an event needs Luca's passkey: he approves \"delete LCS calendar event <eventId>\" in "
               "the Command Centre (Calendar), then Claude may make exactly that call once within 10 minutes.")


def private_folder_ok(path):
    """True when `path` is a real folder (not a symlink) of this user's with no group or other access."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid() and not st.st_mode & 0o077


def read_approval(folder, name):
    """The approval record in folder/name, opened without following a symlink, or None if it isn't a regular file
    of this user's, mode 600 (no group or other bits), with one link and at most APPROVAL_MAX_BYTES."""
    try:
        fd = os.open(os.path.join(folder, name), os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        return None
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077 or st.st_nlink != 1
                or st.st_size > APPROVAL_MAX_BYTES):
            return None
        data = os.read(fd, APPROVAL_MAX_BYTES + 1)
    finally:
        os.close(fd)
    try:
        rec = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    return rec if isinstance(rec, dict) else None


def approval_matches(rec, name, cal, event_id, now):
    """True when the record approves deleting exactly `event_id` on `cal`, now."""
    nonce_sha = rec.get("nonce_sha256")
    if (rec.get("kind") != "calendar-delete" or not isinstance(nonce_sha, str)
            or not re.fullmatch(r"[0-9a-f]{64}", nonce_sha) or name != f"calendar-delete-{nonce_sha[:32]}.json"):
        return False
    if rec.get("calendar_id") != cal or rec.get("event_id") != event_id:
        return False
    binding = hashlib.sha256(f"lcs-calendar-delete\n{nonce_sha}\n{cal}\n{event_id}".encode("utf-8")).hexdigest()
    if not isinstance(rec.get("binding"), str) or not hmac.compare_digest(rec["binding"], binding):
        return False
    at, until = rec.get("approved_at"), rec.get("expires_at")
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (at, until)):
        return False
    return at - 5 <= now < until and until - at <= APPROVAL_TTL


def burn_approval(cal, event_id, now=None):
    """Find an approval for exactly this delete and remove it; True when one was found and removed (so it works
    once). Unlink is atomic: of two calls racing for one approval, only one removes it."""
    now = time.time() if now is None else now
    folder = os.path.expanduser(APPROVALS)
    if not (private_folder_ok(os.path.dirname(folder)) and private_folder_ok(folder)):
        return False
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return False
    for name in names:
        if not APPROVAL_NAME.fullmatch(name):
            continue
        rec = read_approval(folder, name)
        if rec is None or not approval_matches(rec, name, cal, event_id, now):
            continue
        try:
            os.unlink(os.path.join(folder, name))
        except OSError:
            continue  # taken by another call, or can't be burnt: not usable
        return True
    return False


def check_delete(tool_input):
    """ALLOW + reason when an approval for exactly this delete was found and burnt, else a deny reason."""
    if not isinstance(tool_input, dict):
        return f"{P}delete_event input must be an object."
    extra = sorted(set(tool_input) - DELETE_KEYS)
    if extra:
        return f"{P}delete_event may not set {', '.join(extra)}."
    try:
        cal = lcs_calendar_id()
    except Exception:
        return f"{P}{CONFIG} is missing or has no lcs_calendar_id; no event can be deleted."
    if tool_input.get("calendarId") != cal:
        return f"{P}events may be deleted only from the London Choral Service calendar."
    if not isinstance(tool_input.get("eventId"), str) or not tool_input["eventId"].strip():
        return f"{P}eventId is required."
    if tool_input.get("notificationLevel", "NONE") != "NONE":
        return f"{P}notificationLevel must be NONE."
    if not burn_approval(cal, tool_input["eventId"]):
        return NO_APPROVAL
    return f"{ALLOW}Luca approved deleting this one London Choral Service event with his passkey (approval used)."


def decide(tool, tool_input=None):
    parts = tool.split("__")
    if len(parts) != 3 or parts[0] != "mcp" or parts[1] != SERVER or not parts[2]:
        return f"{P}{tool!r} is not a tool of the Google Calendar connector this guard covers."
    if parts[2] in READ_TOOLS:
        return None  # allowed; normal permission rules apply
    if parts[2] == "create_event":
        return check_create(tool_input)
    if parts[2] == "delete_event":
        return check_delete(tool_input)
    return (f"{P}{parts[2]} isn't allowed. Claude reads the diary and adds confirmed bookings to the "
            "London Choral Service calendar; it never changes or responds to an event, and deletes one "
            "only after Luca's passkey approval in the Command Centre.")


def main():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        event = json.load(sys.stdin)
        tool = event.get("tool_name")
        if not isinstance(tool, str) or not tool:
            raise ValueError("missing or invalid tool_name")
        reason = decide(tool, event.get("tool_input"))
    except Exception as e:  # fail closed
        reason = f"Calendar guard error ({type(e).__name__}); call blocked."
    if reason:
        allow = reason.startswith(ALLOW)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "allow" if allow else "deny",
                                                 "permissionDecisionReason": reason[len(ALLOW):] if allow else reason}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
