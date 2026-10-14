#!/usr/bin/env python3
"""PreToolUse guard (matcher Bash): an extra "ask" around Zoho Drafts beyond the automation's plain commands.

The boundary is not this hook. Moving an office@ draft to Trash (owner decision, 14 Oct 2026) happens only through
`imap_draft.py discard <Message-ID> --owner`, which refuses unless the Command Centre ran it after Luca's passkey
and piped its one-time nonce (lcs_owner.owner_confirmed), and imap_draft.trash_draft refuses any draft but Luca's
own original in a process that hasn't passed that check. This hook is a harmless second layer on top: it answers
"ask" for any command that touches imap_draft except the plain forms the automation uses (save, attach, sent,
check, test, run as `.venv/bin/python scripts/bookings/imap_draft.py <command> …` with nothing chained after it),
and for any command naming its Trash helpers, so an odd command is shown to Luca as well as failing. It is a check
on Bash text, not a sandbox; it never allows anything itself, and it fails closed (an unreadable event asks too).
"""
import json
import re
import sys

HELPERS = re.compile(r"trash_draft|forget_saved|retire_original")
PLAIN = re.compile(r"\s*(?:\.venv/bin/python|python3) scripts/bookings/imap_draft\.py (?:save|attach|sent|check|test)\b"
                   r"[^;&|`$<>(){}\n\\]*")
REASON = ("Touches Zoho Drafts beyond the automation's plain save/attach/sent. Moving a draft to Trash runs only from "
          "the Command Centre after Luca's passkey (Drafts, Move to Trash); from here it would refuse anyway.")


def decide(command):
    """"ask" with a reason, or None (no opinion: the other hooks and rules decide)."""
    if not isinstance(command, str):
        return "Owner confirm guard: unreadable command; Luca must approve it."
    if HELPERS.search(command):
        return REASON
    if "imap_draft" in command:
        bare = re.sub(r"'[^']*'", "''", command)  # single-quoted JSON specs are data, not shell
        if "'" in bare.replace("''", "") or not PLAIN.fullmatch(bare):
            return REASON
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
