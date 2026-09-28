#!/usr/bin/env python3
"""Tests for scripts/bookings/imap_draft.py (a fake IMAP server; no network, no Keychain, no real private files).
.venv/bin/python tests/test_imap_draft.py"""
import csv
import email
import email.policy
import io
import json
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout
from email.message import EmailMessage
from pathlib import Path

TMP = Path(tempfile.mkdtemp())
os.environ["LCS_PRIVATE_DIR"] = str(TMP / "private")  # never the real ~/lcs-private
os.environ["LCS_BOOKINGS_CSV"] = str(TMP / "private" / "bookings.csv")
(TMP / "private").mkdir()
with open(TMP / "private" / "bookings.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["booking_ref", "client_email"])
    w.writeheader()
    w.writerow({"booking_ref": "2111", "client_email": "Client@Example.com"})
    w.writerow({"booking_ref": "0512", "client_email": "other@example.com"})

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "bookings"))
import imap_draft as d  # noqa: E402

INV = TMP / "LCS-invoices"
FOLDER = INV / "2111 - A Client"
OTHER = INV / "0512 - Someone Else"
for f in (FOLDER, OTHER):
    f.mkdir(parents=True)
PDF = FOLDER / "Invoice 2111 - A Client.pdf"
DOCX = FOLDER / "Booking Confirmation - A Client - 21 Nov 2026.docx"
PDF.write_bytes(b"%PDF-1.4 fake invoice")
DOCX.write_bytes(b"PK\x03\x04 fake docx")
OTHER_PDF = OTHER / "Invoice 0512 - Someone Else.pdf"
OTHER_PDF.write_bytes(b"%PDF-1.4 someone else's invoice")
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


def clear_saved():
    if d.SAVED.exists():
        d.SAVED.unlink()


def sent_message(to, filename, date="Tue, 29 Sep 2026 10:00:00 +0100"):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"], m["Date"] = d.FROM_HEADER, to, "Re: Wedding", date
    m.set_content("Attached.")
    m.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf", filename=filename)
    return m.as_bytes()


class FakeIMAP:
    def __init__(self, drafts=(), sent=()):
        self.boxes = {"Drafts": list(drafts), "Sent": list(sent)}
        self.calls, self.box = [], None

    def login(self, user, pw):
        self.calls.append(("login", user))
        if pw != "right":
            raise d.imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    def select(self, box, readonly=False):
        self.calls.append(("select", box, readonly))
        if box not in self.boxes:
            return "NO", [b"no such folder"]
        self.box = box
        return "OK", [str(len(self.boxes[box])).encode()]

    def search(self, charset, *criteria):
        self.calls.append(("search", self.box) + criteria)
        to = criteria[1].strip('"').lower()
        hits = [str(i).encode() for i, raw in enumerate(self.boxes[self.box], 1)
                if to in (email.message_from_bytes(raw)["To"] or "").lower()]
        return "OK", [b" ".join(hits)]

    def fetch(self, rng, what):
        self.calls.append(("fetch", self.box, rng, what))
        msgs = self.boxes[self.box]
        picked = list(enumerate(msgs, 1)) if rng == "1:*" else [(int(rng), msgs[int(rng) - 1])]
        rows = []
        for i, raw in picked:
            if "HEADER.FIELDS" in what:
                key = email.message_from_bytes(raw).get(d.KEY_HEADER)
                rows.append((f"{i} (BODY[HEADER.FIELDS])".encode(),
                             (f"{d.KEY_HEADER}: {key}\r\n\r\n" if key else "\r\n").encode()))
            else:
                rows.append((f"{i} (BODY[])".encode(), raw))
            rows.append(b")")
        return "OK", rows

    def close(self):
        self.calls.append(("close",))

    def append(self, box, flags, when, data):
        self.calls.append(("append", box, flags))
        self.boxes[box].append(data)
        return "OK", [b"APPEND completed"]

    def logout(self):
        self.calls.append(("logout",))


def run_main(argv, imap, password="right"):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = d.main(argv, factory=lambda host: imap, password=password)
    return rc, out.getvalue()


# --- the spec ---------------------------------------------------------------------------------

def test_a_good_spec_passes_and_reads_each_file_once():
    got = d.validate(spec())
    assert got["to"] == "client@example.com", got
    assert [a[0] for a in got["attachments"]] == [PDF.name, DOCX.name]
    assert got["attachments"][0][3] == PDF.read_bytes() and isinstance(got["message"], bytes)


def test_only_one_recipient_and_no_cc_bcc_or_from():
    for bad in ("a@example.com, b@example.com", "a@example.com; b@example.com", "a@example.com b@example.com",
                "Sam <a@example.com>", "not-an-address", "a@example.com\r\nBcc: x@example.com", ""):
        assert refused(spec(to=bad, attachments=[])), bad
    for key in ("cc", "bcc", "from", "fromAddress", "ccAddress", "send", "mode"):
        assert "not allowed" in (refused(spec(**{key: "x@example.com"})) or ""), key
    assert refused(spec(to="office@londonchoralservice.com", attachments=[])), "our own address"


def test_header_injection_and_control_characters_are_refused():
    for bad in ("Re: hi\r\nBcc: x@example.com", "Re: hi\x0bBcc", "Re: hi\x0c", "Re: hi\x1c", "Re: hi\x85",
                "Re: hi Bcc: x", "Re: hi ", "Re:\x00hi", "Re: hi\tthere"):
        assert refused(spec(subject=bad)), repr(bad)
    for bad in ("<a@b>\r\nBcc: x@example.com", "not a message id", "<a\x00b@c.com>", "<a b@c.com>", "<a@b\x7f.com>"):
        assert refused(spec(in_reply_to=bad)), repr(bad)
    for bad in ("<a@b.com>\nBcc: x@example.com", "<a@b.com> junk", "<a@b.com> <c@d.com>"):
        assert refused(spec(references=bad)), repr(bad)
    for key in ("", "a b", "x" * 41, "../x", "k\n"):
        assert refused(spec(key=key, attachments=[])), key


def test_a_long_references_list_is_trimmed_not_refused():
    ids = " ".join(f"<m{i}@example.com>" for i in range(40))
    got = d.validate(spec(references=ids))
    kept = got["references"].split()
    assert len(kept) == d.KEEP_REFS and kept[0] == "<m0@example.com>" and kept[-1] == "<m39@example.com>", kept


# --- attachments belong to this booking and this client ----------------------------------------

def test_attachments_must_be_this_bookings_files_for_this_client():
    assert "not in booking 2111's folder" in refused(spec(attachments=[str(OTHER_PDF)]))
    assert "not the client on booking 2111" in refused(spec(to="other@example.com"))
    assert "no client email in the ledger" in refused(spec(key="3112-confirmation"))
    assert "needs the key <ref>-confirmation" in refused(spec(key="2111-reply"))
    wrong = FOLDER / "Invoice 0512 - A Client.pdf"
    wrong.write_bytes(b"%PDF-1.4")
    notes = FOLDER / "Notes.pdf"
    notes.write_bytes(b"%PDF-1.4")
    for bad in (wrong, notes):
        assert "only booking 2111's invoice PDF" in refused(spec(attachments=[str(bad)])), bad
    assert refused(spec(attachments=[str(PDF), str(PDF)])), "the same invoice twice"
    assert refused(spec(attachments=[str(PDF), str(DOCX), str(PDF)])), "three files"


def test_links_paths_and_contents_are_checked():
    outside = TMP / "secret.txt"
    outside.write_text("private")
    sym = FOLDER / "Invoice 2111 - Sym.pdf"
    hard = FOLDER / "Invoice 2111 - Hard.pdf"
    fake = FOLDER / "Invoice 2111 - Fake.pdf"
    if not sym.exists():
        os.symlink(outside, sym)
    if not hard.exists():
        os.link(outside, hard)
    fake.write_bytes(b"not a pdf")
    assert refused(spec(attachments=[str(sym)])), "symlink"
    assert "ordinary file" in refused(spec(attachments=[str(hard)])), "hard link"
    assert "doesn't look like a .pdf" in refused(spec(attachments=[str(fake)]))
    for bad in (str(FOLDER / "Invoice 2111 - Missing.pdf"), str(FOLDER / ".." / "0512 - Someone Else" / OTHER_PDF.name),
                "relative/Invoice 2111 - A.pdf", "https://evil.test/Invoice 2111 - A.pdf", str(INV),
                str(FOLDER / "Invoice 2111 - A .pdf")):
        assert refused(spec(attachments=[bad])), bad
    assert refused(spec(attachments=str(PDF))), "not a list"


def test_an_icloud_only_file_says_how_to_fix_it():
    (FOLDER / ".Invoice 2111 - Evicted.pdf.icloud").write_bytes(b"")
    assert "iCloud only" in refused(spec(attachments=[str(FOLDER / "Invoice 2111 - Evicted.pdf")]))


def test_bank_details_in_the_text_are_refused():
    for html in ("<p>Sort code 04-00-04, account 12345678.</p>", "<p>IBAN GB33BUKB20201555555555</p>"):
        assert "bank details" in (refused(spec(html=html)) or ""), html
    assert refused(spec(subject="Re: sort code 040004 acc 12345678"))
    assert refused(spec(html="<p>Your event is on 21/11/2026 at 3.00pm; call +44 (0)7356 042468.</p>")) is None


# --- the message ------------------------------------------------------------------------------

def test_the_message_is_a_threaded_draft_with_both_files():
    raw = d.validate(spec())["message"]
    parsed = email.message_from_bytes(raw, policy=email.policy.default)
    assert parsed["From"] == "Luca Wetherall <office@londonchoralservice.com>"
    assert parsed["To"] == "client@example.com" and parsed["Cc"] is None and parsed["Bcc"] is None
    assert parsed["In-Reply-To"] == "<abc123@mail.example.com>"
    assert parsed["References"] == "<x1@example.com> <abc123@mail.example.com>"
    assert parsed[d.KEY_HEADER] == "2111-confirmation"
    names = [p.get_filename() for p in parsed.iter_attachments()]
    assert names == [PDF.name, DOCX.name], names
    body = parsed.get_body(("plain",)).get_content()
    assert "Invoice 2111" in body and "<p>" not in body, body
    assert parsed.get_body(("html",)).get_content().strip().startswith("<p>Dear Sam")


# --- saving -----------------------------------------------------------------------------------

def test_save_appends_to_drafts_once_and_remembers_it():
    clear_saved()
    imap = FakeIMAP()
    rc, out = run_main(["save", json.dumps(spec())], imap)
    assert rc == 0 and "draft saved in Zoho Drafts (2111-confirmation, 2 attachments)" in out, out
    assert [c for c in imap.calls if c[0] == "append"] == [("append", "Drafts", r"(\Draft \Seen)")]
    assert {c[1] for c in imap.calls if c[0] in ("select", "append")} == {"Drafts"}
    assert ("select", "Drafts", True) in imap.calls and imap.calls[-1] == ("logout",)
    # after Luca sends it the draft leaves Drafts; the local record still stops a second one
    again = FakeIMAP()
    rc, out = run_main(["save", json.dumps(spec())], again)
    assert rc == 0 and "already saved earlier" in out and again.calls == [], (out, again.calls)
    assert "2111-confirmation" in d.SAVED.read_text() and oct(d.SAVED.stat().st_mode & 0o777) == "0o600"


def test_a_draft_already_in_drafts_is_not_saved_twice():
    clear_saved()
    s = d.validate(spec())
    imap = FakeIMAP(drafts=[s["message"]])
    assert d.save(s, imap) == "already in Drafts (2111-confirmation)"
    assert not [c for c in imap.calls if c[0] == "append"] and d.saved_before("2111-confirmation")


def test_a_bad_password_stops_without_saving():
    clear_saved()
    imap = FakeIMAP()
    rc, out = run_main(["save", json.dumps(spec())], imap, password="wrong")
    assert rc == 1 and out.startswith("STOP: Zoho refused the sign-in"), out
    assert not [c for c in imap.calls if c[0] == "append"] and "wrong" not in out
    assert not d.saved_before("2111-confirmation")


def test_a_refused_spec_never_signs_in():
    imap = FakeIMAP()
    rc, out = run_main(["save", json.dumps(spec(to="other@example.com"))], imap)
    assert rc == 1 and out.startswith("STOP:") and imap.calls == [], (out, imap.calls)
    rc, out = run_main(["save", "not json"], imap)
    assert rc == 1 and "one JSON object" in out, out
    rc, out = run_main(["save", "/etc/passwd"], imap)
    assert rc == 1 and "one JSON object" in out and "root" not in out, out


def test_any_unexpected_error_is_one_stop_line():
    class Broken(FakeIMAP):
        def select(self, box, readonly=False):
            raise KeyError("client@example.com")
    clear_saved()
    rc, out = run_main(["save", json.dumps(spec())], Broken())
    assert rc == 1 and out.strip() == "STOP: KeyError", out
    rc, out = run_main(["frobnicate"], FakeIMAP())
    assert rc == 1 and out.startswith("STOP: usage"), out


def test_the_host_must_be_zoho():
    os.environ["LCS_IMAP_HOST"] = "imap.evil.test"
    try:
        rc, out = run_main(["check"], FakeIMAP())
        assert rc == 1 and "not a Zoho IMAP server" in out, out
    finally:
        del os.environ["LCS_IMAP_HOST"]


def test_check_and_test_for_the_owner():
    rc, out = run_main(["check"], FakeIMAP(drafts=[b"x"]))
    assert rc == 0 and out.startswith("IMAP ok") and "1 draft(s), 0 sent" in out and "writable" in out, out
    imap = FakeIMAP()
    rc, out = run_main(["test"], imap)
    assert rc == 0 and "draft saved" in out and "header kept by Zoho: yes" in out, out
    parsed = email.message_from_bytes(imap.boxes["Drafts"][0], policy=email.policy.default)
    assert parsed["To"] == "luca@almaconsort.com" and [p.get_filename() for p in parsed.iter_attachments()] == ["LCS test.pdf"]


# --- sent: the evidence for marking a Books invoice sent ---------------------------------------

def test_sent_matches_the_exact_invoice_to_the_client():
    imap = FakeIMAP(sent=[sent_message("other@example.com", "Invoice 2111 - A Client.pdf"),
                          sent_message("client@example.com", "Invoice 2111B - A Client.pdf"),
                          sent_message("client@example.com", "Invoice 2111 - A Client.pdf")])
    rc, out = run_main(["sent", "2111", "client@example.com", "2026-09-29"], imap)
    assert rc == 0 and out.strip() == "sent: yes 2026-09-29", out
    assert not [c for c in imap.calls if c[0] == "append"]
    assert {c[1] for c in imap.calls if c[0] == "select"} == {"Sent"} and all(c[2] for c in imap.calls if c[0] == "select")
    for args in (["2111C", "client@example.com", "2026-09-29"], ["2111", "other2@example.com", "2026-09-29"],
                 ["2111", "client@example.com", "2026-09-30"]):
        rc, out = run_main(["sent", *args], FakeIMAP(sent=imap.boxes["Sent"]))
        assert rc == 0 and out.strip() == "sent: no", (args, out)
    for args in (["21x1", "client@example.com", "2026-09-29"], ["2111", "a@b.com, c@d.com", "2026-09-29"],
                 ["2111", "client@example.com", "29/09/2026"]):
        rc, out = run_main(["sent", *args], FakeIMAP())
        assert rc == 1 and out.startswith("STOP:"), (args, out)


def test_the_script_has_no_sending_code():
    src = (ROOT / "scripts" / "bookings" / "imap_draft.py").read_text()
    for word in ("smtplib", "SMTP(", "sendmail", "send_message", ".store(", ".copy(", ".move(", "expunge",
                 ".uid(", ".delete(", ".create("):
        assert word not in src, word
    assert len(re.findall(r"\.append\(DRAFTS", src)) == 1
    assert len(re.findall(r"conn\.append\(", src)) == 1


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
