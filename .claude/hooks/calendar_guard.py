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
delete_event (owner decisions, 14 and 31 Oct 2026) needs Luca's own click: on the
London Choral Service calendar, with only calendarId, eventId and notificationLevel
"NONE", the hook answers "ask", so Claude Code shows him the call and it runs only
when he clicks Allow (Remote Control relays the prompt to his phone). From a subagent
(the event carries an agent_id) it is denied, and a scheduled run has no one to click
Allow, so the scheduled tasks never delete events. Updating or responding to an
event, and any tool the connector adds later, are denied. It accepts only tools of this one connector (on a new
machine whose connector id differs, update SERVER here, the matcher and the
allowlist in .claude/settings.json together). It fails closed: any error, a
missing or malformed config, or a tool name of the wrong shape denies the call.
"""
import json
import os
import re
import sys

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
ASK = "ask:"
SUBAGENT = (f"{P}deleting an event runs only in Luca's own conversation, never in a subagent or a scheduled run. "
            "Hand it back to the main conversation, where he approves it.")


def check_delete(tool_input, agent_id=None):
    """ASK + the prompt's reason for a valid delete in Luca's own conversation, else a deny reason."""
    if agent_id:
        return SUBAGENT
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
    event_id = tool_input.get("eventId")
    if not isinstance(event_id, str) or not event_id.strip():
        return f"{P}eventId is required."
    if tool_input.get("notificationLevel", "NONE") != "NONE":
        return f"{P}notificationLevel must be NONE."
    return (f"{ASK}Delete London Choral Service calendar event {event_id}? Allow only if you asked for this in "
            "this chat; otherwise Deny.")


def decide(tool, tool_input=None, agent_id=None):
    parts = tool.split("__")
    if len(parts) != 3 or parts[0] != "mcp" or parts[1] != SERVER or not parts[2]:
        return f"{P}{tool!r} is not a tool of the Google Calendar connector this guard covers."
    if parts[2] in READ_TOOLS:
        return None  # allowed; normal permission rules apply
    if parts[2] == "create_event":
        return check_create(tool_input)
    if parts[2] == "delete_event":
        return check_delete(tool_input, agent_id)
    return (f"{P}{parts[2]} isn't allowed. Claude reads the diary and adds confirmed bookings to the "
            "London Choral Service calendar; it never changes or responds to an event, and deletes one "
            "only when Luca clicks Allow in his own chat.")


def main():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        event = json.load(sys.stdin)
        tool = event.get("tool_name")
        if not isinstance(tool, str) or not tool:
            raise ValueError("missing or invalid tool_name")
        reason = decide(tool, event.get("tool_input"), event.get("agent_id"))
    except Exception as e:  # fail closed
        reason = f"Calendar guard error ({type(e).__name__}); call blocked."
    if reason:
        ask = reason.startswith(ASK)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "ask" if ask else "deny",
                                                 "permissionDecisionReason": reason[len(ASK):] if ask else reason}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
