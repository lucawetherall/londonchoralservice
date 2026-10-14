#!/usr/bin/env python3
"""PreToolUse guard (matcher Bash): commands only Luca may approve, one run at a time.

`imap_draft.py discard <Message-ID>` moves one draft from office@londonchoralservice.com in Zoho Drafts to Trash
(owner decision, 14 Oct 2026). Claude may run it only with Luca's explicit approval, so this hook answers "ask"
for any command that mentions it: Claude Code then shows Luca the command and waits for him, whatever the
permission mode or allowlist. It never allows anything itself, and it fails closed (an unreadable event asks too).
The scheduled tasks and their agents never run discard.
"""
import json
import re
import sys

ASK = re.compile(r"imap_draft\.py\W+discard\b")


def decide(command):
    """"ask" with a reason, or None (no opinion: the other hooks and rules decide)."""
    if not isinstance(command, str):
        return "Owner confirm guard: unreadable command; Luca must approve it."
    if ASK.search(command):
        return ("Moves one London Choral Service draft from Zoho Drafts to Trash (recoverable there). "
                "Only Luca can approve this.")
    return None


def main():
    try:
        event = json.load(sys.stdin)
        reason = decide((event.get("tool_input") or {}).get("command"))
    except Exception as e:  # fail closed: ask
        reason = f"Owner confirm guard error ({type(e).__name__}); Luca must approve this command."
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "ask",
                                                 "permissionDecisionReason": reason}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
