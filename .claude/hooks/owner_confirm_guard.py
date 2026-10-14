#!/usr/bin/env python3
"""PreToolUse guard (matcher Bash): commands only Luca may approve, one run at a time.

`imap_draft.py discard <Message-ID>` moves one draft from office@londonchoralservice.com in Zoho Drafts to Trash
(owner decision, 14 Oct 2026). Claude may run it only with Luca's explicit approval, so this hook answers "ask"
for any command that touches imap_draft except the plain forms the automation uses (save, attach, sent, check,
test, run as `.venv/bin/python scripts/bookings/imap_draft.py <command> …` with nothing chained after it), and for
any command naming its Trash helpers. Claude Code then shows Luca the command and waits for him. It is a
best-effort gate on Bash text, not a sandbox: code written to a file and run from there isn't seen here. It never
allows anything itself, and it fails closed (an unreadable event asks too). The scheduled tasks never run discard.
"""
import json
import re
import sys

HELPERS = re.compile(r"trash_draft|forget_saved|retire_original")
PLAIN = re.compile(r"\s*(?:\.venv/bin/python|python3) scripts/bookings/imap_draft\.py (?:save|attach|sent|check|test)\b"
                   r"[^;&|`$<>(){}\n\\]*")
REASON = ("Touches Zoho Drafts beyond the automation's plain save/attach/sent (for example discard, which moves one "
          "London Choral Service draft to Trash). Only Luca can approve this.")


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
