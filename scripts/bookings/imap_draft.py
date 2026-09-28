#!/usr/bin/env python3
"""Save a client reply, with the invoice PDF and booking confirmation attached, into Zoho Mail Drafts.

The Zoho Mail MCP can't attach files to a draft, so this script builds the whole email itself and
puts it in the Drafts folder of office@londonchoralservice.com over IMAP (APPEND). It never sends:
there is no SMTP code here, and the only IMAP writes are APPEND to Drafts. Luca opens the draft in
Zoho, checks it and presses Send.

    .venv/bin/python scripts/bookings/imap_draft.py save '<one-line JSON spec>'
    .venv/bin/python scripts/bookings/imap_draft.py check     (log in, count the drafts; writes nothing)
    .venv/bin/python scripts/bookings/imap_draft.py test      (one test draft to luca@almaconsort.com; delete it)

spec: {"key": "2111-confirmation", "to": "<the client's address>", "subject": "Re: …",
       "in_reply_to": "<Message-Id of the client's email>", "references": "<id> <id> …",
       "html": "<p>…</p>", "attachments": ["<full path of the invoice PDF>", "<… the .docx>"]}
  key          [0-9A-Za-z-], at most 40: a rerun with the same key finds the draft already in Drafts
               and saves nothing (the X-LCS-Draft-Key header carries it).
  to           one address only. There is no Cc or Bcc, and any other spec key is refused.
  in_reply_to, references   optional; from ZohoMail_getMessageHeader (Message-Id and References),
               so Zoho threads the draft with the client's email.
  attachments  optional, at most 4: .pdf or .docx files inside iCloud Drive/LCS-invoices (where
               make_booking_docs.py writes), each at most 10 MB.
The subject and text are scanned for bank details with the Zoho Mail guard's scanner
(.claude/hooks/zoho_guard.py): a draft's text never carries them; the invoice PDF does, as it
always has.

Sign-in: a Zoho app password (Zoho Mail → Settings → Security → App Passwords), kept by the owner in
the macOS Keychain, service "lcs-zoho-imap", account office@londonchoralservice.com. The script reads
it itself and never prints it. IMAP access must be on for the mailbox (Zoho Mail → Settings →
Mail Accounts → IMAP Access).
"""

import email.policy
import imaplib
import json
import mimetypes
import os
import re
import ssl
import subprocess
import sys
import time
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))

FROM_ADDRESS = "office@londonchoralservice.com"
FROM_HEADER = f"Luca Wetherall <{FROM_ADDRESS}>"  # as Luca's own sent replies show it
KEYCHAIN_SERVICE = "lcs-zoho-imap"
DEFAULT_HOST = "imappro.zoho.com"  # Zoho's IMAP server for organisation mailboxes
HOST_OK = re.compile(r"imap(?:pro)?\.zoho\.(?:com|eu|in|com\.au|jp|com\.cn|ca|sa)")
DRAFTS = "Drafts"
KEY_HEADER = "X-LCS-Draft-Key"
INVOICES_ROOT = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "LCS-invoices"  # = lcs_money.ICLOUD_INVOICES

SPEC_KEYS = {"key", "to", "subject", "in_reply_to", "references", "html", "attachments"}
KEY = re.compile(r"[0-9A-Za-z-]{1,40}")
ADDRESS = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
                     r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+")
MSG_ID = re.compile(r"<[^<>\s@]+@[^<>\s@]+>")
EXTS = {".pdf": ("application", "pdf"),
        ".docx": ("application", "vnd.openxmlformats-officedocument.wordprocessingml.document")}
MAX_ATTACHMENTS, MAX_BYTES = 4, 10 * 1024 * 1024
TAG = re.compile(r"<[^>]*>")


class Refused(Exception):
    pass


def fail(msg):
    raise Refused(msg)


def one_line(value, what, limit):
    if not isinstance(value, str) or not value.strip():
        fail(f"{what} is missing")
    if any(c in value for c in "\r\n\x00") or len(value) > limit:
        fail(f"{what} must be one line of at most {limit} characters")
    return value.strip()


def attachment_path(value, root=None):
    """The real path of one attachment, which must be a .pdf or .docx file inside the invoices folder."""
    root = Path(root or INVOICES_ROOT).expanduser().resolve()
    if not isinstance(value, str) or not value.startswith(("/", "~/")) or "\x00" in value or ".." in value:
        fail("attachments must be full paths inside iCloud Drive/LCS-invoices")
    real = Path(value).expanduser().resolve()
    if root not in real.parents:
        fail(f"{real.name} is not inside iCloud Drive/LCS-invoices")
    if real.suffix not in EXTS:
        fail(f"{real.name}: only .pdf and .docx files can be attached")
    if not real.is_file():
        icloud_stub = real.with_name(f".{real.name}.icloud")
        if icloud_stub.exists():
            fail(f"{real.name} is in iCloud only: open the folder in Finder to download it, then rerun")
        fail(f"{real.name} does not exist")
    if real.stat().st_size > MAX_BYTES:
        fail(f"{real.name} is larger than 10 MB")
    return real


def validate(spec, root=None):
    """The checked spec. Refused for anything outside the rules in the module docstring."""
    if not isinstance(spec, dict):
        fail("the spec must be a JSON object")
    extra = set(spec) - SPEC_KEYS
    if extra:
        fail(f"spec keys not allowed: {', '.join(sorted(extra))} (no Cc, Bcc or From: one recipient only)")
    key = spec.get("key")
    if not (isinstance(key, str) and KEY.fullmatch(key)):
        fail("key must be letters, digits and '-', at most 40 (e.g. 2111-confirmation)")
    to = one_line(spec.get("to"), "to", 254)
    if not ADDRESS.fullmatch(to):
        fail("to must be exactly one email address")
    if to.lower() == FROM_ADDRESS:
        fail("to is our own address; address the draft to the client who wrote")
    subject = one_line(spec.get("subject"), "subject", 200)
    html = spec.get("html")
    if not isinstance(html, str) or not html.strip() or len(html) > 50000:
        fail("html is missing or longer than 50,000 characters")
    irt = spec.get("in_reply_to")
    if irt is not None and not (isinstance(irt, str) and MSG_ID.fullmatch(irt.strip())):
        fail("in_reply_to must be one Message-Id like <abc@example.com>")
    refs = spec.get("references")
    if refs is not None:
        if not isinstance(refs, str) or any(c in refs for c in "\r\n") or len(refs) > 4000:
            fail("references must be one line of Message-Ids")
        if not all(MSG_ID.fullmatch(r) for r in refs.split()):
            fail("references must be Message-Ids like <abc@example.com>, separated by spaces")
    files = spec.get("attachments") or []
    if not isinstance(files, list) or len(files) > MAX_ATTACHMENTS:
        fail(f"attachments must be a list of at most {MAX_ATTACHMENTS} paths")
    paths = [attachment_path(f, root) for f in files]
    if len({p.name for p in paths}) != len(paths):
        fail("two attachments have the same file name")
    from zoho_guard import has_bank_details  # the Zoho Mail guard's own scanner
    if has_bank_details({"subject": subject, "content": html}):
        fail("the draft looks like it carries bank details (sort code, account number, IBAN); "
             "say they are on the invoice instead")
    return {"key": key, "to": to, "subject": subject, "html": html,
            "in_reply_to": irt.strip() if irt else None, "references": refs.strip() if refs else None,
            "attachments": paths}


def plain_text(html):
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", html)
    text = unescape(TAG.sub("", text))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line.strip() for line in text.splitlines())).strip() + "\n"


def build_message(spec):
    """The email (an EmailMessage) for a validated spec."""
    msg = EmailMessage(policy=email.policy.SMTP)
    msg["From"] = FROM_HEADER
    msg["To"] = spec["to"]
    msg["Subject"] = spec["subject"]
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="londonchoralservice.com")
    if spec.get("in_reply_to"):
        msg["In-Reply-To"] = spec["in_reply_to"]
        msg["References"] = spec.get("references") or spec["in_reply_to"]
    msg[KEY_HEADER] = spec["key"]
    msg.set_content(plain_text(spec["html"]))
    msg.add_alternative(spec["html"], subtype="html")
    for path in spec["attachments"]:
        maintype, subtype = EXTS[path.suffix]
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
    return msg


def keychain_password():
    r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", FROM_ADDRESS, "-w"],
                       capture_output=True, text=True)
    pw = r.stdout.strip() if r.returncode == 0 else ""
    if not pw:
        fail(f'no Zoho app password in the Keychain (service "{KEYCHAIN_SERVICE}"): the owner adds it once '
             "(see docs/HANDOVER-2026-09-27-ads-analytics.md, section 4)")
    return pw


def connect(password=None, factory=None):
    host = os.environ.get("LCS_IMAP_HOST", DEFAULT_HOST)
    if not HOST_OK.fullmatch(host):
        fail(f"LCS_IMAP_HOST {host!r} is not a Zoho IMAP server")
    if factory is None:
        conn = imaplib.IMAP4_SSL(host, 993, ssl_context=ssl.create_default_context(), timeout=60)
    else:
        conn = factory(host)
    try:
        conn.login(FROM_ADDRESS, password if password is not None else keychain_password())
    except imaplib.IMAP4.error:
        fail("Zoho refused the sign-in: check the app password in the Keychain and that IMAP access is on")
    return conn


def draft_keys(conn):
    """The X-LCS-Draft-Key values already in Drafts, and the number of drafts."""
    typ, data = conn.select(DRAFTS, readonly=True)
    if typ != "OK":
        fail("couldn't open the Drafts folder over IMAP")
    count = int((data[0] or b"0").decode() or 0)
    keys = set()
    if count:
        typ, rows = conn.fetch("1:*", f"(BODY.PEEK[HEADER.FIELDS ({KEY_HEADER.upper()})])")
        if typ != "OK":
            fail("couldn't read the Drafts folder over IMAP")
        for row in rows:
            if isinstance(row, tuple) and len(row) > 1:
                m = re.search(rb"(?im)^" + KEY_HEADER.encode() + rb":\s*(\S+)", row[1] or b"")
                if m:
                    keys.add(m.group(1).decode("ascii", "replace"))
    conn.close()
    return keys, count


def save(spec, conn):
    """APPEND the draft to Drafts unless one with the same key is there. Returns what happened."""
    keys, _ = draft_keys(conn)
    if spec["key"] in keys:
        return f"already in Drafts ({spec['key']})"
    msg = build_message(spec)
    typ, _ = conn.append(DRAFTS, r"(\Draft \Seen)", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
    if typ != "OK":
        fail("Zoho did not accept the draft")
    n = len(spec["attachments"])
    return f"draft saved in Zoho Drafts ({spec['key']}, {n} attachment{'s' * (n != 1)})"


def main(argv=None, factory=None, password=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv[:1] == ["save"] and len(argv) == 2:
            arg = argv[1].strip()
            spec = validate(json.loads(arg if arg.startswith("{") else Path(arg).read_text()))
            conn = connect(password, factory)
            try:
                print(save(spec, conn))
            finally:
                conn.logout()
        elif argv == ["check"]:
            conn = connect(password, factory)
            try:
                _, count = draft_keys(conn)
            finally:
                conn.logout()
            print(f"IMAP ok: signed in as {FROM_ADDRESS}; {count} message(s) in Drafts")
        elif argv == ["test"]:
            spec = {"key": f"test-{int(time.time())}", "to": "luca@almaconsort.com",
                    "subject": "LCS test draft (delete me)",
                    "html": "<p>A test draft saved by imap_draft.py. Delete it; don't send it.</p>",
                    "in_reply_to": None, "references": None, "attachments": []}
            conn = connect(password, factory)
            try:
                print(save(spec, conn))
            finally:
                conn.logout()
        else:
            print(__doc__.split("\n\n")[1])
            return 2
    except (Refused, json.JSONDecodeError) as e:
        print(f"STOP: {e}")
        return 1
    except (OSError, imaplib.IMAP4.error) as e:
        print(f"STOP: IMAP failed ({type(e).__name__})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
