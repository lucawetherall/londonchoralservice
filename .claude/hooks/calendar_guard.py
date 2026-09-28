#!/usr/bin/env python3
"""PreToolUse guard for the Google Calendar connector
(matcher mcp__caefd5da-81a5-4eb0-993a-dfeaa5b9d7c1__.*).

The enquiry assistant reads Luca's diary before drafting a reply, and never
changes it. This hook allows only the connector's read tools (list_calendars,
list_events, search_events, get_event, suggest_time) and denies everything
else: creating, updating, deleting or responding to an event, and any tool the
connector adds later. It accepts only tools of this one connector (on a new
machine whose connector id differs, update SERVER here, the matcher and the
allowlist in .claude/settings.json together). It fails closed: any error, or a
tool name of the wrong shape, denies the call.
"""
import json
import sys

SERVER = "caefd5da-81a5-4eb0-993a-dfeaa5b9d7c1"
READ_TOOLS = {"list_calendars", "list_events", "search_events", "get_event", "suggest_time"}
P = "Calendar guard: "


def decide(tool):
    parts = tool.split("__")
    if len(parts) != 3 or parts[0] != "mcp" or parts[1] != SERVER or not parts[2]:
        return f"{P}{tool!r} is not a tool of the Google Calendar connector this guard covers."
    if parts[2] in READ_TOOLS:
        return None  # allowed; normal permission rules apply
    return (f"{P}{parts[2]} isn't allowed. Claude reads the diary only; it never creates, changes, "
            "deletes or responds to an event.")


def main():
    try:
        event = json.load(sys.stdin)
        tool = event.get("tool_name")
        if not isinstance(tool, str) or not tool:
            raise ValueError("missing or invalid tool_name")
        reason = decide(tool)
    except Exception as e:  # fail closed
        reason = f"Calendar guard error ({type(e).__name__}); call blocked."
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
