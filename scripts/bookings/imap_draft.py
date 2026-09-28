#!/usr/bin/env python3
"""Save a client's confirmation email, with the invoice PDF and booking confirmation attached, in Zoho Drafts.

The Zoho Mail MCP can't attach files to a draft, so this script builds the whole email itself and
puts it in the Drafts folder of office@londonchoralservice.com over IMAP (APPEND). It never sends:
there is no SMTP code here, and the only IMAP write is APPEND to Drafts. Luca opens the draft in
Zoho, checks it and presses Send.

    .venv/bin/python scripts/bookings/imap_draft.py save '<one-line JSON spec>'
    .venv/bin/python scripts/bookings/imap_draft.py sent <invoice ref> <client email> <YYYY-MM-DD>
    .venv/bin/python scripts/bookings/imap_draft.py check     (owner: sign in, count the folders; writes nothing)
    .venv/bin/python scripts/bookings/imap_draft.py test      (owner: one test draft to luca@almaconsort.com; delete it)

save's spec: {"key": "2111-confirmation", "to": "<the client's address>", "subject": "Re: …",
       "in_reply_to": "<Message-Id of the client's email>", "references": "<id> <id> …",
       "html": "<p>…</p>", "attachments": ["<full path of the invoice PDF>", "<… the .docx>"]}
  key          [0-9A-Za-z-], at most 40. A key saved before (~/lcs-private/imap-drafts.csv) or already on a
               draft in Drafts (the X-LCS-Draft-Key header) is not saved again.
  to           one address only. There is no Cc or Bcc, and any other spec key is refused.
  in_reply_to, references   optional; from ZohoMail_getMessageHeader (Message-Id and References), so Zoho
               threads the draft with the client's email. A long References list keeps its first and last ids.
  attachments  optional. With attachments the key must be "<ref>-confirmation", `to` must be the client_email
               of booking <ref> in the ledger, and the files must be the ones make_booking_docs.py wrote for
               that ref: "Invoice <ref> - <client>.pdf" and/or "Booking Confirmation - <client> - <date>.docx",
               in iCloud Drive/LCS-invoices/<ref> - <client>/, each an ordinary file (no links), at most 10 MB,
               that starts like a PDF or a .docx. Each file is read once, before signing in.
The subject and text are scanned for bank details with the Zoho Mail guard's scanner
(.claude/hooks/zoho_guard.py): a draft's text never carries them; the invoice PDF does, as it always has.

sent reads the Sent folder (read-only) for a message to <client email> since <date> with an attachment named
exactly "Invoice <ref> - <…>.pdf", and prints "sent: yes <YYYY-MM-DD>" or "sent: no". The daily pass marks the
Books invoice sent only on "sent: yes".

Sign-in: a Zoho app password (accounts.zoho.com → Security → App Passwords), kept by the owner in the macOS
Keychain, service "lcs-zoho-imap", account office@londonchoralservice.com. The script reads it itself and never
prints it. IMAP access must be on for the mailbox (Zoho Mail → Settings → Mail Accounts → IMAP Access).
Every failure prints one "STOP: …" line and exits 1, so the caller can fall back to a plain draft.
"""

import datetime
import email
import email.policy
import imaplib
import json
import os
import re
import ssl
import stat
import subprocess
import sys
import time
import unicodedata
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parsedate_to_datetime
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402  LEDGER, PRIVATE, LONDON, ICLOUD_INVOICES, read_csv, locked_rows

FROM_ADDRESS = "office@londonchoralservice.com"
FROM_HEADER = f"Luca Wetherall <{FROM_ADDRESS}>"  # as Luca's own sent replies show it
TEST_TO = "luca@almaconsort.com"
KEYCHAIN_SERVICE = "lcs-zoho-imap"
DEFAULT_HOST = "imappro.zoho.com"  # Zoho's IMAP server for organisation mailboxes
HOST_OK = re.compile(r"imap(?:pro)?\.zoho\.(?:com|eu|in|com\.au|jp|com\.cn|ca|sa)")
DRAFTS, SENT = "Drafts", "Sent"
KEY_HEADER = "X-LCS-Draft-Key"
INVOICES_ROOT = lm.ICLOUD_INVOICES  # where make_booking_docs.py writes
SAVED = lm.PRIVATE / "imap-drafts.csv"  # keys of drafts saved before
SAVED_COLUMNS = ["key", "saved_at"]

SPEC_KEYS = {"key", "to", "subject", "in_reply_to", "references", "html", "attachments"}
KEY = re.compile(r"[0-9A-Za-z-]{1,40}")
REF = re.compile(r"[0-9]{4}[A-Z]?")
CONFIRMATION_KEY = re.compile(r"([0-9]{4}[A-Z]?)-confirmation")
ADDRESS = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
                     r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+")
ID_CHARS = r"[!-;=?A-~]+"  # printable ASCII except space, "<", ">" and "@"
MSG_ID = re.compile(f"<{ID_CHARS}@{ID_CHARS}>")
KEEP_REFS = 10  # the first id and the last nine
FILES = {".pdf": ("application", "pdf", b"%PDF-"),
         ".docx": ("application", "vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04")}
MAX_BYTES = 10 * 1024 * 1024
TAG = re.compile(r"<[^>]*>")
BAD_CHARS = ("Cc", "Zl", "Zp")


class Refused(Exception):
    pass


def fail(msg):
    raise Refused(msg)


def one_line(value, what, limit):
    if not isinstance(value, str) or not value.strip():
        fail(f"{what} is missing")
    if len(value) > limit or len(value.splitlines()) > 1 or any(unicodedata.category(c) in BAD_CHARS for c in value):
        fail(f"{what} must be one line of at most {limit} characters, with no control characters")
    return value.strip()


def ledger_email(ref):
    """The client_email of booking `ref` in the ledger (lower case), or None."""
    for row in lm.read_csv(lm.LEDGER):
        if (row.get("booking_ref") or "").strip() == ref:
            return (row.get("client_email") or "").strip().lower() or None
    return None


def read_attachment(value, ref, root=None):
    """(file name, maintype, subtype, bytes) for one attachment of booking `ref`, read once, safely."""
    root = Path(root or INVOICES_ROOT).expanduser().resolve()
    if not isinstance(value, str) or not value.startswith(("/", "~/")) or ".." in value or any(
            unicodedata.category(c) in BAD_CHARS for c in value):
        fail("attachments must be full paths inside iCloud Drive/LCS-invoices")
    real = Path(value).expanduser().resolve()
    if real.parent.parent != root or not real.parent.name.startswith(f"{ref} - "):
        fail(f"{real.name} is not in booking {ref}'s folder in iCloud Drive/LCS-invoices")
    name = real.name
    if real.suffix == ".pdf":
        ok = re.fullmatch(rf"Invoice {re.escape(ref)} - .+\.pdf", name)
    elif real.suffix == ".docx":
        ok = re.fullmatch(r"Booking Confirmation - .+\.docx", name)
    else:
        ok = None
    if not ok:
        fail(f"{name}: only booking {ref}'s invoice PDF and booking confirmation can be attached")
    if not real.exists() and real.with_name(f".{name}.icloud").exists():
        fail(f"{name} is in iCloud only: open the folder in Finder to download it, then rerun")
    try:
        fd = os.open(real, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as e:
        fail(f"{name} can't be opened ({type(e).__name__})")
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            fail(f"{name} must be an ordinary file (not a link)")
        if st.st_size > MAX_BYTES:
            fail(f"{name} is larger than 10 MB")
        with os.fdopen(os.dup(fd), "rb") as f:
            data = f.read(MAX_BYTES + 1)
    except OSError as e:
        fail(f"{name} can't be read ({type(e).__name__}); if it is in iCloud only, open it in Finder, then rerun")
    finally:
        os.close(fd)
    maintype, subtype, magic = FILES[real.suffix]
    if len(data) > MAX_BYTES or not data.startswith(magic):
        fail(f"{name} doesn't look like a {real.suffix} file")
    return name, maintype, subtype, data


def trim_references(refs):
    ids = refs.split()
    return " ".join(ids if len(ids) <= KEEP_REFS else ids[:1] + ids[-(KEEP_REFS - 1):])


def validate(spec, root=None):
    """The checked spec, attachments read into memory and the message built. Refused outside the rules above."""
    if not isinstance(spec, dict):
        fail("the spec must be a JSON object")
    extra = set(spec) - SPEC_KEYS
    if extra:
        fail(f"spec keys not allowed: {', '.join(sorted(map(str, extra)))} (no Cc, Bcc or From: one recipient only)")
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
    if not isinstance(html, str) or not html.strip() or len(html) > 50000 or "\x00" in html:
        fail("html is missing or longer than 50,000 characters")
    irt = spec.get("in_reply_to")
    if irt is not None:
        irt = one_line(irt, "in_reply_to", 998)
        if not MSG_ID.fullmatch(irt):
            fail("in_reply_to must be one Message-Id like <abc@example.com>")
    refs = spec.get("references")
    if refs is not None:
        refs = one_line(refs, "references", 20000)
        if not all(MSG_ID.fullmatch(r) for r in refs.split()):
            fail("references must be Message-Ids like <abc@example.com>, separated by spaces")
        refs = trim_references(refs)
    files = spec.get("attachments") or []
    if not isinstance(files, list) or len(files) > 2:
        fail("attachments must be a list of at most 2 paths (the invoice PDF and the booking confirmation)")
    attachments = []
    if files:
        m = CONFIRMATION_KEY.fullmatch(key)
        if not m:
            fail("a draft with attachments needs the key <ref>-confirmation (e.g. 2111-confirmation)")
        ref = m.group(1)
        client = ledger_email(ref)
        if client is None:
            fail(f"booking {ref} has no client email in the ledger: run ledger-add first")
        if to.lower() != client:
            fail(f"to is not the client on booking {ref} in the ledger")
        attachments = [read_attachment(f, ref, root) for f in files]
        if len({a[0].rsplit(".", 1)[1] for a in attachments}) != len(attachments):
            fail("attach one invoice PDF and one booking confirmation at most")
    from zoho_guard import has_bank_details  # the Zoho Mail guard's own scanner
    if has_bank_details({"subject": subject, "content": html}):
        fail("the draft looks like it carries bank details (sort code, account number, IBAN); "
             "say they are on the invoice instead")
    checked = {"key": key, "to": to, "subject": subject, "html": html, "in_reply_to": irt, "references": refs,
               "attachments": attachments}
    try:
        checked["message"] = build_message(checked).as_bytes()  # before signing in: a bad header stops here
    except (ValueError, TypeError) as e:
        fail(f"the email couldn't be built ({type(e).__name__})")
    return checked


def plain_text(html):
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", html)
    text = unescape(TAG.sub("", text))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line.strip() for line in text.splitlines())).strip() + "\n"


def build_message(spec):
    """The email (an EmailMessage) for a validated spec; attachments are (name, maintype, subtype, bytes)."""
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
    for name, maintype, subtype, data in spec["attachments"]:
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)
    return msg


def keychain_password():
    r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", FROM_ADDRESS, "-w"],
                       capture_output=True, text=True)
    pw = r.stdout.strip() if r.returncode == 0 else ""
    if not pw:
        fail(f'no Zoho app password in the Keychain (service "{KEYCHAIN_SERVICE}"): the owner adds it once '
             "(MANUAL-ACTIONS-REQUIRED.md, section 28)")
    return pw


def connect(password=None, factory=None):
    host = os.environ.get("LCS_IMAP_HOST", DEFAULT_HOST)
    if not HOST_OK.fullmatch(host):
        fail(f"LCS_IMAP_HOST {host!r} is not a Zoho IMAP server")
    pw = password if password is not None else keychain_password()
    if factory is None:
        conn = imaplib.IMAP4_SSL(host, 993, ssl_context=ssl.create_default_context(), timeout=60)
    else:
        conn = factory(host)
    try:
        conn.login(FROM_ADDRESS, pw)
    except imaplib.IMAP4.error:
        fail("Zoho refused the sign-in: check the app password in the Keychain and that IMAP access is on")
    return conn


def open_folder(conn, box):
    """Select `box` read-only; its message count."""
    typ, data = conn.select(box, readonly=True)
    if typ != "OK":
        fail(f"couldn't open the {box} folder over IMAP")
    try:
        return int((data[0] or b"0").decode())
    except (ValueError, AttributeError, IndexError):
        fail(f"the {box} folder's message count couldn't be read")


def draft_keys(conn):
    """The X-LCS-Draft-Key values on the drafts in Drafts, and the number of drafts."""
    count = open_folder(conn, DRAFTS)
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


def saved_before(key):
    return any(r.get("key") == key for r in lm.read_csv(SAVED))


def record_saved(key):
    with lm.locked_rows(SAVED, SAVED_COLUMNS) as t:
        if not any(r.get("key") == key for r in t.rows):
            t.rows.append({"key": key, "saved_at": datetime.datetime.now(lm.LONDON).isoformat(timespec="seconds")})


def save(spec, conn, record=True):
    """APPEND the draft to Drafts unless its key was saved before or is on a draft there. Returns what happened."""
    if record and saved_before(spec["key"]):
        return f"already saved earlier ({spec['key']}): nothing added"
    keys, _ = draft_keys(conn)
    if spec["key"] in keys:
        if record:
            record_saved(spec["key"])
        return f"already in Drafts ({spec['key']})"
    typ, _ = conn.append(DRAFTS, r"(\Draft \Seen)", imaplib.Time2Internaldate(time.time()), spec["message"])
    if typ != "OK":
        fail("Zoho did not accept the draft")
    if record:
        record_saved(spec["key"])
    n = len(spec["attachments"])
    return f"draft saved in Zoho Drafts ({spec['key']}, {n} attachment{'s' * (n != 1)})"


def invoice_sent(conn, ref, to, since):
    """"sent: yes <date>" if Sent holds a message to `to` since `since` with "Invoice <ref> - ….pdf" attached."""
    name = re.compile(rf"Invoice {re.escape(ref)} - .+\.pdf")
    if open_folder(conn, SENT) == 0:
        conn.close()
        return "sent: no"
    typ, data = conn.search(None, "TO", f'"{to}"', "SINCE", since.strftime("%d-%b-%Y"))
    if typ != "OK":
        fail("couldn't search the Sent folder over IMAP")
    found = None
    for num in (data[0] or b"").split()[-50:]:
        typ, rows = conn.fetch(num.decode(), "(BODY.PEEK[])")
        raw = next((r[1] for r in rows or [] if isinstance(r, tuple) and len(r) > 1), None) if typ == "OK" else None
        if not raw:
            continue
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        if to.lower() not in {a.addr_spec.lower() for h in msg.get_all("To", []) for a in h.addresses}:
            continue
        if not any(name.fullmatch(p.get_filename() or "") for p in msg.iter_attachments()):
            continue
        try:
            when = parsedate_to_datetime(msg["Date"]).astimezone(lm.LONDON).date()
        except (TypeError, ValueError):
            continue
        if when >= since:
            found = max(found or when, when)
    conn.close()
    return f"sent: yes {found.isoformat()}" if found else "sent: no"


def run(argv, factory=None, password=None):
    if argv[:1] == ["save"] and len(argv) == 2:
        try:
            spec = validate(json.loads(argv[1]))
        except json.JSONDecodeError:
            fail("the spec must be one JSON object, as a single-quoted argument")
        if saved_before(spec["key"]):
            return f"already saved earlier ({spec['key']}): nothing added"
        conn = connect(password, factory)
        try:
            return save(spec, conn)
        finally:
            conn.logout()
    if argv[:1] == ["sent"] and len(argv) == 4:
        ref, to, since = argv[1], argv[2].strip(), argv[3]
        if not REF.fullmatch(ref):
            fail("the ref must be a DDMM booking ref, e.g. 2111 or 2111B")
        if not ADDRESS.fullmatch(to):
            fail("the client email must be one address")
        try:
            since = datetime.date.fromisoformat(since)
        except ValueError:
            fail("the date must be YYYY-MM-DD (the invoice date)")
        conn = connect(password, factory)
        try:
            return invoice_sent(conn, ref, to, since)
        finally:
            conn.logout()
    if argv == ["check"]:
        root = Path(INVOICES_ROOT)
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        writable = os.access(root, os.W_OK)
        conn = connect(password, factory)
        try:
            _, count = draft_keys(conn)
            sent = open_folder(conn, SENT)
            conn.close()
        finally:
            conn.logout()
        return (f"IMAP ok: signed in as {FROM_ADDRESS}; {count} draft(s), {sent} sent message(s); "
                f"iCloud Drive/LCS-invoices {'writable' if writable else 'NOT writable'}")
    if argv == ["test"]:
        key = f"test-{int(time.time())}"
        spec = {"key": key, "to": TEST_TO, "subject": "LCS test draft (delete me)",
                "html": "<p>A test draft saved by imap_draft.py, with a small test PDF attached. "
                        "Open it to check the attachment shows and the draft can be edited, then delete it; "
                        "don't send it.</p>",
                "in_reply_to": None, "references": None,
                "attachments": [("LCS test.pdf", "application", "pdf", b"%PDF-1.4\n% LCS test\n%%EOF\n")]}
        spec["message"] = build_message(spec).as_bytes()
        conn = connect(password, factory)
        try:
            result = save(spec, conn, record=False)
            keys, _ = draft_keys(conn)
        finally:
            conn.logout()
        kept = "yes" if key in keys else "NO (reruns rely on ~/lcs-private/imap-drafts.csv only)"
        return f"{result}; draft key header kept by Zoho: {kept}"
    fail("usage: imap_draft.py save '<JSON>' | sent <ref> <client email> <YYYY-MM-DD> | check | test")


def main(argv=None, factory=None, password=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        print(run(argv, factory, password))
    except Refused as e:
        print(f"STOP: {e}")
        return 1
    except (OSError, imaplib.IMAP4.error) as e:
        print(f"STOP: IMAP failed ({type(e).__name__}); check Zoho Drafts before saving a fallback draft")
        return 1
    except Exception as e:  # noqa: BLE001  one STOP line, never a traceback (it could carry client details)
        print(f"STOP: {type(e).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
