#!/usr/bin/env python3
"""PreToolUse guard for the Zoho Mail MCP server (matcher mcp__zoho-mail__.*).

Claude may READ mail and may SAVE DRAFTS from office@londonchoralservice.com or luca@almaconsort.com.
It may never send, schedule, delete, move, label, mark or change settings: the
owner reviews every draft in Zoho and presses Send. A draft has one recipient
(no Cc, no Bcc, no "," or ";" in toAddress) and never carries bank details in its
subject or content: the scanner is zoho_books_guard.bank_details_in, run on the
text with HTML tags and entities removed. This holds whatever tools the Zoho MCP
console exposes, and it fails closed: any error denies the call.
"""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

READ_TOOLS = {
    "ZohoMail_SearchEmails", "ZohoMail_listEmails", "ZohoMail_getMessageContent",
    "ZohoMail_getMessageDetails", "ZohoMail_getMessageHeader", "ZohoMail_getMessageAttachmentInfo",
    "ZohoMail_getOriginalMessage", "ZohoMail_getAllFolders", "ZohoMail_getFolder",
    "ZohoMail_getMailAccounts", "ZohoMail_getAccountDetails", "ZohoMail_getAllLabelDetails",
    "ZohoMail_getSpecificLabelDetails",
}
DRAFT_TOOLS = {"ZohoMail_sendEmail", "ZohoMail_sendReplyEmail"}
DRAFT_FROM = {"office@londonchoralservice.com", "luca@almaconsort.com"}
SCANNED = ("subject", "content")
TAG = re.compile(r"<[^>]*>")
# our own WhatsApp link and the "(0)" in "+44 (0)7356 042468" are not bank numbers
OWN_LINKS = re.compile(r"wa\.me/\+?[0-9]+|tel:\+?[0-9]+", re.I)


def plain_text(value):
    if not isinstance(value, str):
        raise TypeError("draft text must be a string")
    text = TAG.sub(" ", OWN_LINKS.sub(" ", value))
    text = html.unescape(text).replace("(0)", "0")
    return OWN_LINKS.sub(" ", text)


def has_bank_details(body):
    from zoho_books_guard import bank_details_in  # imported here so an import error fails closed in main()
    return any(bank_details_in(plain_text(body[k])) for k in SCANNED if body.get(k) is not None)


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
        if body.get("ccAddress"):
            return "Zoho guard: no Cc on drafts; address the draft only to the person who wrote."
        if body.get("attachments"):
            return "Zoho guard: attachments are added by the owner in Zoho."
        to = body.get("toAddress") or ""
        if not isinstance(to, str) or not to.strip():
            return "Zoho guard: a draft needs the client's address in toAddress."
        if "," in to or ";" in to:
            return "Zoho guard: one recipient only; address the draft only to the person who wrote."
        if has_bank_details(body):
            return ("Zoho guard: the draft looks like it carries bank details (sort code, account number, IBAN). "
                    "Never write bank details in a draft: say they are on the invoice.")
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
