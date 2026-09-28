#!/usr/bin/env python3
"""Tests for scripts/bookings/imap_draft.py (a fake IMAP server; no network, no Keychain).
.venv/bin/python tests/test_imap_draft.py"""
import email
import email.policy
import io
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "bookings"))
import imap_draft as d  # noqa: E402

TMP = Path(tempfile.mkdtemp())
INV = TMP / "LCS-invoices"
FOLDER = INV / "2111 - A Client"
FOLDER.mkdir(parents=True)
PDF = FOLDER / "Invoice 2111 - A Client.pdf"
DOCX = FOLDER / "Booking Confirmation - A Client - 21 Nov 2026.docx"
PDF.write_bytes(b"%PDF-1.4 fake invoice")
DOCX.write_bytes(b"PK fake docx")
d.INVOICES_ROOT = INV


def spec(**kw):
    s = {"key": "2111-confirmation", "to": "client@example.com", "subject": "Re: Wedding enquiry",
         "in_reply_to": "<abc123@mail.example.com>", "references": "<x1@example.com> <abc123@mail.example.com>",
         "html": "<p>Dear Sam,</p><p>Thank you. Invoice 2111 and the booking confirmation are attached.</p>",
         "attachments": [str(PDF), str(DOCX)]}
    s.update(kw)
    return s


def refused(s):
    try:
        d.validate(s)
    except d.Refused as e:
        return str(e)
    return None


class FakeIMAP:
    def __init__(self, drafts=()):
        self.drafts = list(drafts)  # raw message bytes
        self.calls = []

    def login(self, user, pw):
        self.calls.append(("login", user))
        if pw != "right":
            raise d.imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    def select(self, box, readonly=False):
        self.calls.append(("select", box, readonly))
        return "OK", [str(len(self.drafts)).encode()]

    def fetch(self, rng, what):
        self.calls.append(("fetch", rng, what))
        rows = []
        for i, raw in enumerate(self.drafts, 1):
            msg = email.message_from_bytes(raw)
            key = msg.get(d.KEY_HEADER)
            rows.append((f"{i} (BODY[HEADER.FIELDS])".encode(),
                         (f"{d.KEY_HEADER}: {key}\r\n\r\n" if key else "\r\n").encode()))
            rows.append(b")")
        return "OK", rows

    def close(self):
        self.calls.append(("close",))

    def append(self, box, flags, when, data):
        self.calls.append(("append", box, flags))
        self.drafts.append(data)
        return "OK", [b"APPEND completed"]

    def logout(self):
        self.calls.append(("logout",))


def test_a_good_spec_passes():
    got = d.validate(spec())
    assert got["to"] == "client@example.com" and got["attachments"] == [PDF.resolve(), DOCX.resolve()], got


def test_only_one_recipient_and_no_cc_bcc_or_from():
    for bad in ("a@example.com, b@example.com", "a@example.com; b@example.com", "a@example.com b@example.com",
                "Sam <a@example.com>", "not-an-address", "a@example.com\r\nBcc: x@example.com", ""):
        assert refused(spec(to=bad)), bad
    for key in ("cc", "bcc", "from", "fromAddress", "ccAddress", "send", "mode"):
        assert "not allowed" in (refused(spec(**{key: "x@example.com"})) or ""), key
    assert refused(spec(to="office@londonchoralservice.com")), "our own address"


def test_header_injection_is_refused():
    assert refused(spec(subject="Re: hi\r\nBcc: x@example.com"))
    assert refused(spec(in_reply_to="<a@b>\r\nBcc: x@example.com"))
    assert refused(spec(references="<a@b.com>\nBcc: x@example.com"))
    assert refused(spec(in_reply_to="not a message id"))
    assert refused(spec(references="<a@b.com> junk"))
    for key in ("", "a b", "x" * 41, "../x", "k\n"):
        assert refused(spec(key=key)), key


def test_attachments_must_be_invoice_files():
    outside = TMP / "elsewhere.pdf"
    outside.write_bytes(b"%PDF")
    link = FOLDER / "link.pdf"
    if not link.exists():
        os.symlink(outside, link)
    txt = FOLDER / "notes.txt"
    txt.write_text("x")
    for bad in (str(outside), str(link), str(txt), str(FOLDER / "missing.pdf"), str(FOLDER / ".." / ".." / "x.pdf"),
                "relative/Invoice.pdf", "https://evil.test/a.pdf", str(INV)):
        assert refused(spec(attachments=[bad])), bad
    assert refused(spec(attachments=[str(PDF)] * 5)), "too many"
    assert refused(spec(attachments=[str(PDF), str(PDF)])), "same name twice"
    assert refused(spec(attachments=str(PDF))), "not a list"


def test_an_icloud_only_file_says_how_to_fix_it():
    (FOLDER / ".Evicted.pdf.icloud").write_bytes(b"")
    assert "iCloud only" in refused(spec(attachments=[str(FOLDER / "Evicted.pdf")]))


def test_bank_details_in_the_text_are_refused():
    for html in ("<p>Sort code 04-00-04, account 12345678.</p>", "<p>IBAN GB33BUKB20201555555555</p>"):
        assert "bank details" in (refused(spec(html=html)) or ""), html
    assert refused(spec(subject="Re: sort code 040004 acc 12345678"))
    assert refused(spec(html="<p>Your event is on 21/11/2026 at 3.00pm; call +44 (0)7356 042468.</p>")) is None


def test_the_message_is_a_threaded_draft_with_both_files():
    msg = d.build_message(d.validate(spec()))
    assert msg["From"] == "Luca Wetherall <office@londonchoralservice.com>"
    assert msg["To"] == "client@example.com" and msg["Cc"] is None and msg["Bcc"] is None
    assert msg["In-Reply-To"] == "<abc123@mail.example.com>"
    assert msg["References"] == "<x1@example.com> <abc123@mail.example.com>"
    assert msg[d.KEY_HEADER] == "2111-confirmation"
    parsed = email.message_from_bytes(msg.as_bytes(), policy=email.policy.default)
    names = [p.get_filename() for p in parsed.iter_attachments()]
    assert names == [PDF.name, DOCX.name], names
    body = parsed.get_body(("plain",)).get_content()
    assert "Invoice 2111" in body and "<p>" not in body, body
    assert parsed.get_body(("html",)).get_content().strip().startswith("<p>Dear Sam")


def test_save_appends_to_drafts_once():
    imap = FakeIMAP()
    s = d.validate(spec())
    assert d.save(s, imap).startswith("draft saved in Zoho Drafts (2111-confirmation, 2 attachments)")
    assert d.save(s, imap) == "already in Drafts (2111-confirmation)"
    appends = [c for c in imap.calls if c[0] == "append"]
    assert appends == [("append", "Drafts", r"(\Draft \Seen)")], appends
    assert ("select", "Drafts", True) in imap.calls


def test_main_never_touches_any_folder_but_drafts():
    imap = FakeIMAP()
    out = io.StringIO()
    with redirect_stdout(out):
        rc = d.main(["save", __import__("json").dumps(spec())], factory=lambda host: imap, password="right")
    assert rc == 0 and "draft saved" in out.getvalue(), out.getvalue()
    boxes = {c[1] for c in imap.calls if c[0] in ("select", "append")}
    assert boxes == {"Drafts"}, boxes
    assert imap.calls[-1] == ("logout",)


def test_a_bad_password_stops_without_saving():
    imap = FakeIMAP()
    out = io.StringIO()
    with redirect_stdout(out):
        rc = d.main(["save", __import__("json").dumps(spec())], factory=lambda host: imap, password="wrong")
    assert rc == 1 and "refused the sign-in" in out.getvalue(), out.getvalue()
    assert not [c for c in imap.calls if c[0] == "append"]
    assert "wrong" not in out.getvalue()


def test_the_host_must_be_zoho():
    os.environ["LCS_IMAP_HOST"] = "imap.evil.test"
    try:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = d.main(["check"], factory=lambda host: FakeIMAP(), password="right")
        assert rc == 1 and "not a Zoho IMAP server" in out.getvalue(), out.getvalue()
    finally:
        del os.environ["LCS_IMAP_HOST"]


def test_the_script_has_no_sending_code():
    src = (ROOT / "scripts" / "bookings" / "imap_draft.py").read_text()
    for word in ("smtplib", "SMTP(", "sendmail", "send_message", ".store(", ".copy(", ".move(", "expunge",
                 ".uid(", ".delete(", "create("):
        assert word not in src, word
    assert len(re.findall(r"\.append\(", src)) == 1


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except Exception as e:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(e))
    print(f"\n{fails} failure(s)")
    sys.exit(1 if fails else 0)
