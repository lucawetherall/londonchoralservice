#!/usr/bin/env python3
"""PreToolUse guard for the Zoho Mail MCP server (matcher mcp__zoho-mail__.*).

Claude may READ mail and may SAVE DRAFTS from office@londonchoralservice.com or luca@almaconsort.com.
It may never send, schedule, delete, move, label, mark or change settings: the
owner reviews every draft in Zoho and presses Send. This holds whatever tools
the Zoho MCP console exposes, and it fails closed: any error denies the call.
"""
import json
import sys

READ_TOOLS = {
    "ZohoMail_SearchEmails", "ZohoMail_listEmails", "ZohoMail_getMessageContent",
    "ZohoMail_getMessageDetails", "ZohoMail_getMessageHeader", "ZohoMail_getMessageAttachmentInfo",
    "ZohoMail_getOriginalMessage", "ZohoMail_getAllFolders", "ZohoMail_getFolder",
    "ZohoMail_getMailAccounts", "ZohoMail_getAccountDetails", "ZohoMail_getAllLabelDetails",
    "ZohoMail_getSpecificLabelDetails",
}
DRAFT_TOOLS = {"ZohoMail_sendEmail", "ZohoMail_sendReplyEmail"}
DRAFT_FROM = {"office@londonchoralservice.com", "luca@almaconsort.com"}


def decide(tool, tool_input):
    name = tool.split("__")[-1]
    if name in READ_TOOLS:
        return None  # allowed; normal permission rules apply
    if name in DRAFT_TOOLS:
        body = (tool_input or {}).get("body") or {}
        if body.get("mode") != "draft":
            return "Zoho guard: Claude may only save drafts (body.mode = \"draft\"); the owner sends from Zoho."
        if body.get("isSchedule") or body.get("scheduleType") or body.get("scheduleTime"):
            return "Zoho guard: scheduled sending is a send; save a plain draft instead."
        if (body.get("fromAddress") or "").strip().lower() not in DRAFT_FROM:
            return "Zoho guard: drafts must come from office@londonchoralservice.com (clients) or luca@almaconsort.com (singers)."
        if body.get("bccAddress"):
            return "Zoho guard: no Bcc on drafts."
        if body.get("attachments"):
            return "Zoho guard: attachments are added by the owner in Zoho."
        if not (body.get("toAddress") or "").strip():
            return "Zoho guard: a draft needs the client's address in toAddress."
        return None
    return f"Zoho guard: {name} is not allowed. Claude has read access plus drafts from office@ or luca@almaconsort.com only."


def main():
    try:
        event = json.load(sys.stdin)
        reason = decide(event.get("tool_name", ""), event.get("tool_input"))
    except Exception as e:  # fail closed
        reason = f"Zoho guard error ({type(e).__name__}); call blocked."
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
