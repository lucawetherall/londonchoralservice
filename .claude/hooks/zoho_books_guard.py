#!/usr/bin/env python3
"""PreToolUse guard for the Zoho Books MCP servers (matcher mcp__zoho-books.*).

There are two servers: `zoho-books` (general accounting) and
`zoho-books-invoices` (invoices), so tool names look like
`mcp__zoho-books__<Tool>` or `mcp__zoho-books-invoices__<Tool>`. Both OAuth
connections are new and the exact tool names each server exposes aren't
known yet, so this guard can't work from an exact allow-list the way the
Zoho Mail guard does. Instead it allows a call only when the tool name,
after stripping the MCP and vendor prefixes, looks like a plain read (starts
with list/get/search/fetch/read/retrieve) and contains none of the words
that make a call a write, a send, or a destructive action. Everything else
is denied, deny-by-default. Claude never sends, deletes or voids an invoice
through these servers: that stays the owner's job in Zoho Books until they
approve specific write tools by name below. This holds whatever tools the
Zoho Books MCP console exposes, and it fails closed: any error denies the
call.
"""
import json
import re
import sys

READ_PREFIXES = ("list", "get", "search", "fetch", "read", "retrieve")
DENY_SUBSTRINGS = (
    "send", "email", "mail", "remind", "delete", "void", "writeoff",
    "write_off", "refund", "share", "portal",
)
# A vendor prefix such as "ZohoBooks_" or "ZohoBooksInvoices_" in front of
# the actual tool name.
VENDOR_PREFIX = re.compile(r"^Zoho\w*?_")

# Add exact tool names here only after the owner approves them (see
# docs/superpowers/specs/*zoho-books*).
WRITE_ALLOW = set()


def decide(tool, tool_input):
    name = tool.split("__")[-1]
    core = VENDOR_PREFIX.sub("", name)
    if name in WRITE_ALLOW or core in WRITE_ALLOW:
        return None  # allowed; normal permission rules apply
    lower = core.lower()
    if lower.startswith(READ_PREFIXES) and not any(s in lower for s in DENY_SUBSTRINGS):
        return None  # allowed; normal permission rules apply
    return (f"Zoho Books guard: {name} isn't allowed. Claude has read-only access to "
            "Zoho Books until the owner approves specific write tools.")


def main():
    try:
        event = json.load(sys.stdin)
        tool = event.get("tool_name")
        if not isinstance(tool, str) or not tool:
            raise ValueError("missing or invalid tool_name")
        reason = decide(tool, event.get("tool_input"))
    except Exception as e:  # fail closed
        reason = f"Zoho Books guard error ({type(e).__name__}); call blocked."
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
