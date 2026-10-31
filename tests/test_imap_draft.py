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
    capabilities = ("IMAP4REV1", "MOVE", "UIDPLUS")

    def __init__(self, drafts=(), sent=()):
        self.boxes = {"Drafts": list(drafts), "Sent": list(sent), "Trash": []}
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
                names = re.search(r"HEADER\.FIELDS \(([^)]*)\)", what).group(1).split()
                msg = email.message_from_bytes(raw)
                head = "".join(f"{n}: {msg.get(n)}\r\n" for n in names if msg.get(n))
                rows.append((f"{i} (BODY[HEADER.FIELDS])".encode(), (head + "\r\n").encode()))
            else:
                rows.append((f"{i} (BODY[])".encode(), raw))
            rows.append(b")")
        return "OK", rows

    def uid(self, command, *args):
        self.calls.append(("uid", self.box, command) + args)
        msgs = self.boxes[self.box]
        if command == "FETCH":
            rows = []
            for i, raw in enumerate(msgs, 1):
                names = re.search(r"HEADER\.FIELDS \(([^)]*)\)", args[1]).group(1).split()
                msg = email.message_from_bytes(raw)
                head = "".join(f"{n}: {msg.get(n)}\r\n" for n in names if msg.get(n))
                rows += [(f"{i} (UID {100 + i} BODY[HEADER.FIELDS])".encode(), (head + "\r\n").encode()), b")"]
            return "OK", rows
        if command == "MOVE":
            uid, box = args
            self.boxes[box].append(msgs.pop(int(uid) - 101))
            return "OK", [None]
        raise AssertionError(f"unexpected UID {command}")

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
        assert refused(spec(to=bad, key="2111-reply", attachments=[])), bad
    for key in ("cc", "bcc", "from", "fromAddress", "ccAddress", "send", "mode"):
        assert "not allowed" in (refused(spec(**{key: "x@example.com"})) or ""), key
    assert refused(spec(to="office@londonchoralservice.com", key="2111-reply", attachments=[])), "our own address"


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
    assert d.validate(spec(key="2111-reply", attachments=[]))["attachments"] == []  # a plain draft takes none


def test_a_long_references_list_is_trimmed_not_refused():
    ids = " ".join(f"<m{i}@example.com>" for i in range(40))
    got = d.validate(spec(references=ids))
    kept = got["references"].split()
    assert len(kept) == d.KEEP_REFS and kept[0] == "<m0@example.com>" and kept[-1] == "<m39@example.com>", kept


# --- attachments belong to this booking and this client ----------------------------------------

def test_a_confirmation_carries_both_files_and_nothing_else_carries_any():
    for files in ([], [str(PDF)], [str(DOCX)]):
        assert "both files" in (refused(spec(attachments=files)) or ""), files
    assert "only a confirmation" in refused(spec(key="2111-reply"))
    assert "only a confirmation" in refused(spec(key="2111-followup", attachments=[str(PDF)]))
    got = d.validate(spec(attachments=[str(DOCX), str(PDF)]))
    assert [a[0] for a in got["attachments"]] == [PDF.name, DOCX.name], "the invoice first"


def test_a_business_confirmation_may_be_a_pdf():
    conf = FOLDER / "Booking Confirmation - A Client - 21 Nov 2026.pdf"
    conf.write_bytes(b"%PDF-1.4 fake confirmation")
    got = d.validate(spec(attachments=[str(conf), str(PDF)]))
    assert [a[0] for a in got["attachments"]] == [PDF.name, conf.name], "the invoice first"
    two_invoices = FOLDER / "Invoice 2111 - A Client copy.pdf"
    two_invoices.write_bytes(b"%PDF-1.4 fake invoice")
    assert "one invoice PDF" in (refused(spec(attachments=[str(PDF), str(two_invoices)])) or "")
    two_invoices.unlink()
    conf.unlink()


def test_a_reissue_key_takes_the_same_files_under_the_same_rules():
    got = d.validate(spec(key="2111-confirmation-r2"))
    assert [a[0] for a in got["attachments"]] == [PDF.name, DOCX.name]
    assert d.validate(spec(key="2111-confirmation-r9"))["attachments"]
    for bad in ("2111-confirmation-r1", "2111-confirmation-r10", "2111-confirmation-2", "2111-reissue"):
        assert "only a confirmation" in (refused(spec(key=bad)) or ""), bad
    assert "not the client on booking 2111" in refused(spec(key="2111-confirmation-r2", to="other@example.com"))
    d.record_saved("2111-confirmation")
    assert not d.saved_before("2111-confirmation-r2"), "a reissue is its own key"
    d.forget_saved("2111-confirmation")


def test_attachments_must_be_this_bookings_files_for_this_client():
    assert "not in booking 2111's folder" in refused(spec(attachments=[str(OTHER_PDF), str(DOCX)]))
    assert "not the client on booking 2111" in refused(spec(to="other@example.com"))
    assert "no client email in the ledger" in refused(spec(key="3112-confirmation"))
    wrong = FOLDER / "Invoice 0512 - A Client.pdf"
    wrong.write_bytes(b"%PDF-1.4")
    notes = FOLDER / "Notes.pdf"
    notes.write_bytes(b"%PDF-1.4")
    for bad in (wrong, notes):
        assert "only booking 2111's invoice PDF" in refused(spec(attachments=[str(bad), str(DOCX)])), bad
    assert refused(spec(attachments=[str(PDF), str(PDF)])), "the same invoice twice"
    assert refused(spec(attachments=[str(DOCX), str(DOCX)])), "the same confirmation twice"
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
    assert refused(spec(attachments=[str(sym), str(DOCX)])), "symlink"
    assert "ordinary file" in refused(spec(attachments=[str(hard), str(DOCX)])), "hard link"
    assert "doesn't look like a .pdf" in refused(spec(attachments=[str(fake), str(DOCX)]))
    for bad in (str(FOLDER / "Invoice 2111 - Missing.pdf"), str(FOLDER / ".." / "0512 - Someone Else" / OTHER_PDF.name),
                "relative/Invoice 2111 - A.pdf", "https://evil.test/Invoice 2111 - A.pdf", str(INV),
                str(FOLDER / "Invoice 2111 - A .pdf")):
        assert refused(spec(attachments=[bad, str(DOCX)])), bad
    assert refused(spec(attachments=str(PDF))), "not a list"


def test_an_icloud_only_file_says_how_to_fix_it():
    (FOLDER / ".Invoice 2111 - Evicted.pdf.icloud").write_bytes(b"")
    assert "iCloud only" in refused(spec(attachments=[str(FOLDER / "Invoice 2111 - Evicted.pdf"), str(DOCX)]))


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
    docs = [("Invoice 0101 - Test Client.pdf", "application", "pdf", b"%PDF-1.7 real enough"),
            ("Booking Confirmation - Test Client - 1 Jan 2027.docx", *d.FILES[".docx"][:2], b"PK\x03\x04 docx")]
    real = d.sample_documents
    d.sample_documents = lambda: docs
    try:
        imap = FakeIMAP()
        rc, out = run_main(["test"], imap)
        assert rc == 0 and "draft saved" in out and "header kept by Zoho: yes; attachments intact: yes" in out, out
        parsed = email.message_from_bytes(imap.boxes["Drafts"][0], policy=email.policy.default)
        assert parsed["To"] == "luca@almaconsort.com"
        assert [p.get_filename() for p in parsed.iter_attachments()] == [n for n, *_ in docs]

        class Mangling(FakeIMAP):  # a server that alters an attachment on the way in
            def append(self, box, flags, when, data):
                return super().append(box, flags, when, data.replace(b"JVBERi0xLjcgcmVhbCBlbm91Z2g=", b"QlJPS0VO"))  # the PDF's bytes, base64
        rc, out = run_main(["test"], Mangling())
        assert rc == 0 and "attachments intact: NO" in out, out
    finally:
        d.sample_documents = real


def test_the_sample_documents_stop_cleanly_without_the_templates():
    import make_booking_docs as mbd
    real = mbd.make_docs
    def missing(spec, root):
        raise SystemExit("STOP: /x/invoice.html is missing")
    mbd.make_docs = missing
    try:
        rc, out = run_main(["test"], FakeIMAP())
        assert rc == 1 and out.startswith("STOP: the sample documents couldn't be made (/x/invoice.html is missing)"), out
    finally:
        mbd.make_docs = real


# --- attach: a copy of Luca's own draft with the two files -------------------------------------

LUCA_ID = "<luca-draft-1@londonchoralservice.com>"


def luca_draft(to="client@example.com", msg_id=LUCA_ID, cc=None, key=None, attach=False,
               html="<p>Dear Sam,</p><p>Lovely to speak. I've attached the invoice and booking confirmation.</p>"
                    '<p>Luca<br><img src="cid:sig1"></p>'):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = d.FROM_HEADER, to, "Re: Wedding enquiry"
    m["Message-ID"], m["In-Reply-To"], m["References"] = msg_id, "<abc123@mail.example.com>", "<abc123@mail.example.com>"
    if cc:
        m["Cc"] = cc
    if key:
        m[d.KEY_HEADER] = key
    m.set_content("Dear Sam, lovely to speak.")
    m.add_alternative(html, subtype="html")
    m.get_payload()[1].add_related(b"GIF89a-signature", maintype="image", subtype="gif", cid="<sig1>")
    if attach:
        m.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf", filename="Old.pdf")
    return m.as_bytes()


def attach_spec(**kw):
    s = {"key": "2111-confirmation", "attachments": [str(PDF), str(DOCX)]}
    s.update(kw)
    return json.dumps(s)


def test_attach_saves_a_copy_of_lucas_draft_with_both_files_and_leaves_the_original():
    clear_saved()
    original = luca_draft()
    imap = FakeIMAP(drafts=[original])
    rc, out = run_main(["attach", LUCA_ID, attach_spec()], imap)
    assert rc == 0, out
    moves = [c for c in imap.calls if c[0] == "uid" and c[2] == "MOVE"]
    assert moves == [("uid", "Drafts", "MOVE", "101", "Trash")], moves
    assert imap.boxes["Trash"] == [original] and len(imap.boxes["Drafts"]) == 1, "original moved to Trash, not deleted"
    assert "draft updated" in out and "the earlier version is in Trash" in out, out
    old = email.message_from_bytes(original, policy=email.policy.default)
    new = email.message_from_bytes(imap.boxes["Drafts"][0], policy=email.policy.default)
    for h in ("From", "To", "Subject", "In-Reply-To", "References"):
        assert new[h] == old[h], h
    assert new["Message-ID"] != old["Message-ID"] and new[d.KEY_HEADER] == "2111-confirmation"
    assert [p.get_filename() for p in new.iter_attachments()] == [PDF.name, DOCX.name]
    html = lambda m: m.get_body(("html",)).get_content().replace("\r\n", "\n")
    assert html(new) == html(old), (html(new), html(old))
    assert any(p.get("Content-ID") == "<sig1>" for p in new.walk()), "the signature image is kept"
    assert new["Cc"] is None and new["Bcc"] is None
    rc, out = run_main(["attach", LUCA_ID, attach_spec()], FakeIMAP(drafts=[original]))
    assert rc == 0 and "already saved earlier" in out, out


def test_the_original_stays_unless_the_copy_checks_out_and_can_be_moved():
    class NoMove(FakeIMAP):
        capabilities = ("IMAP4REV1",)

    class Mangling(FakeIMAP):  # the server alters the saved copy's attachment
        def append(self, box, flags, when, data):
            return super().append(box, flags, when, data.replace(b"JVBERi0xLjQgZmFrZSBpbnZvaWNl", b"QlJPS0VO"))
    for server, why in ((NoMove, "couldn't be moved to Trash"), (Mangling, "couldn't be checked")):
        clear_saved()
        original = luca_draft()
        imap = server(drafts=[original])
        rc, out = run_main(["attach", LUCA_ID, attach_spec()], imap)
        assert rc == 0 and why in out and "deletes his draft" in out, (why, out)
        assert imap.boxes["Drafts"][0] == original and imap.boxes["Trash"] == [], why
        assert not [c for c in imap.calls if c[0] == "uid" and c[2] == "MOVE"], why
    clear_saved()  # two drafts with the same Message-ID: touch neither
    imap = FakeIMAP(drafts=[luca_draft(), luca_draft()])
    rc, out = run_main(["attach", LUCA_ID, attach_spec()], imap)
    assert rc == 0 and imap.boxes["Trash"] == [] and len(imap.boxes["Drafts"]) == 3, out


def test_attach_refuses_anything_but_a_plain_draft_to_that_client():
    cases = [
        (luca_draft(cc="planner@example.com"), "Cc or Bcc"),
        (luca_draft(to="other@example.com"), "not the client on booking 2111"),
        (luca_draft(attach=True), "already has attachments"),
        (luca_draft(key="2111-reply"), "saved by the assistant"),
        (luca_draft(html="<p>Sort code 04-00-04, account 12345678.</p>"), "bank details"),
        (luca_draft(msg_id="<someone-else@londonchoralservice.com>"), "isn't in Drafts"),
    ]
    for raw, why in cases:
        clear_saved()
        imap = FakeIMAP(drafts=[raw])
        rc, out = run_main(["attach", LUCA_ID, attach_spec()], imap)
        assert rc == 1 and why in out, (why, out)
        assert len(imap.boxes["Drafts"]) == 1, why
    for args in ([LUCA_ID, attach_spec(key="2111-reply")], [LUCA_ID, attach_spec(attachments=[str(PDF)])],
                 ["not-an-id", attach_spec()], [LUCA_ID, json.dumps({"key": "2111-confirmation"})],
                 [LUCA_ID, attach_spec(to="x@example.com")]):
        clear_saved()
        rc, out = run_main(["attach", *args], FakeIMAP(drafts=[luca_draft()]))
        assert rc == 1 and out.startswith("STOP:"), (args, out)


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
                 ["2111", "client@example.com", "29/09/2026"], ["21112", "client@example.com", "2026-09-29"],
                 ["2111267", "client@example.com", "2026-09-29"]):
        rc, out = run_main(["sent", *args], FakeIMAP())
        assert rc == 1 and out.startswith("STOP:"), (args, out)


APPROVALS = TMP / "private" / "owner-approvals"
NONCE_FILE = APPROVALS / "unset"


def owner_run(argv, imap, nonce_ok=True, piped=True):
    """run_main with Luca's one-time approval as owner_confirm_guard writes it once he clicks Allow:
    <private>/owner-approvals/owner-nonce.chat-<the nonce's sha256> (mode 600) holding this process's argv (the
    script reads sys.argv), the nonce itself on a pipe (nonce_ok=False pipes a different one; piped=False gives
    /dev/null instead)."""
    import hashlib, json, secrets
    global NONCE_FILE
    d.lcs_owner._PROVEN = False
    nonce = secrets.token_hex(32)
    APPROVALS.mkdir(mode=0o700, exist_ok=True)
    NONCE_FILE = APPROVALS / ("owner-nonce.chat-" + hashlib.sha256(nonce.encode()).hexdigest())
    fd = os.open(NONCE_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.write(fd, json.dumps({"argv": list(sys.argv)}).encode())
    os.close(fd)
    r, w = os.pipe()
    os.write(w, ((nonce if nonce_ok else secrets.token_hex(32)) + "\n").encode())
    os.close(w)
    out = io.StringIO()
    try:
        with redirect_stdout(out), open(os.devnull) as null:
            rc = d.main(argv, factory=lambda host: imap, password="right", stdin_fd=r if piped else null.fileno())
    finally:
        os.close(r)
        d.lcs_owner._PROVEN = False
        if NONCE_FILE.exists():
            NONCE_FILE.unlink()
    return rc, out.getvalue()


def test_sent_takes_ddmmyy_refs_and_never_confuses_them_with_ddmm():
    # owner decision, 14 Oct 2026: new refs are DDMMYY; older DDMM refs keep working
    imap = FakeIMAP(sent=[sent_message("client@example.com", "Invoice 2111 - A Client.pdf"),
                          sent_message("other@example.com", "Invoice 211126A - B Client.pdf")])
    for ref, to, want in (("211126", "client@example.com", "no"), ("2111", "client@example.com", "yes 2026-09-29"),
                          ("211126A", "other@example.com", "yes 2026-09-29"), ("211126", "other@example.com", "no")):
        rc, out = run_main(["sent", ref, to, "2026-09-29"], FakeIMAP(sent=imap.boxes["Sent"]))
        assert rc == 0 and out.strip() == f"sent: {want}", (ref, out)
    for key in ("211126-confirmation", "211126A-confirmation", "2111-confirmation", "2111A-confirmation"):
        assert d.CONFIRMATION_KEY.fullmatch(key), key
    for key in ("21112-confirmation", "2111267-confirmation", "211126AB-confirmation"):
        assert not d.CONFIRMATION_KEY.fullmatch(key), key


def test_a_ddmmyy_ref_in_the_text_is_not_read_as_bank_details():
    assert refused(spec(subject="Invoice 211126: booking confirmation",
                        html="<p>Please use 211126 as the payment reference.</p>")) is None
    assert refused(spec(html="<p>Sort code 21-11-26</p>"))


def test_discard_moves_one_office_draft_to_trash_and_forgets_its_key():
    clear_saved()
    keyed = luca_draft(key="2111-confirmation")
    d.record_saved("2111-confirmation")
    imap = FakeIMAP(drafts=[luca_draft(msg_id="<other@londonchoralservice.com>"), keyed])
    rc, out = owner_run(["discard", LUCA_ID, "--owner"], imap)
    assert rc == 0 and "moved to Trash" in out and "can be saved again" in out, out
    assert imap.boxes["Trash"] == [keyed] and len(imap.boxes["Drafts"]) == 1, "only that draft, and only to Trash"
    assert not d.saved_before("2111-confirmation")
    plain = luca_draft()
    imap = FakeIMAP(drafts=[plain])
    rc, out = owner_run(["discard", LUCA_ID, "--owner"], imap)
    assert rc == 0 and imap.boxes["Trash"] == [plain] and "can be saved again" not in out, out


def test_the_nonce_is_burnt_by_a_discard():
    burnt = []
    real = d.lcs_owner.owner_confirmed

    def watch(fd=0):
        ok = real(fd)
        burnt.append(ok and not NONCE_FILE.exists())
        return ok
    d.lcs_owner.owner_confirmed = watch
    try:
        rc, out = owner_run(["discard", LUCA_ID, "--owner"], FakeIMAP(drafts=[luca_draft()]))
    finally:
        d.lcs_owner.owner_confirmed = real
    assert rc == 0 and burnt == [True], (burnt, out)


def test_discard_needs_the_owner_flag_and_lucas_approval():
    for argv, kw in ((["discard", LUCA_ID], {}), (["discard", LUCA_ID, "--force"], {}),
                     (["discard", LUCA_ID, "--owner", "x"], {}),
                     (["discard", LUCA_ID, "--owner"], {"nonce_ok": False}),
                     (["discard", LUCA_ID, "--owner"], {"piped": False})):
        imap = FakeIMAP(drafts=[luca_draft()])
        rc, out = owner_run(argv, imap, **kw)
        assert rc == 1 and out.startswith("STOP:") and "Allow" in out and out.count("\n") == 1, (argv, kw, out)
        assert "passkey" not in out and "Command Centre" not in out, out
        assert imap.boxes["Trash"] == [] and not [c for c in imap.calls if c[0] == "login"], (argv, kw)
    rc, out = run_main(["discard", LUCA_ID, "--owner"], FakeIMAP(drafts=[luca_draft()]))  # no approval at all
    assert rc == 1 and "Allow" in out, out


def test_the_trash_helper_refuses_other_callers_but_attachs_retire_still_runs():
    d.lcs_owner._PROVEN = False
    imap = FakeIMAP(drafts=[luca_draft(key="2111-reply")])
    try:
        d.trash_draft(imap, LUCA_ID, own_only=False)
        raise AssertionError("trash_draft(own_only=False) ran without the owner's nonce")
    except d.Refused as e:
        assert "Allow" in str(e)
    assert imap.boxes["Trash"] == [] and not [c for c in imap.calls if c[0] == "uid"]
    plain = luca_draft()
    imap = FakeIMAP(drafts=[plain])
    assert d.retire_original(imap, LUCA_ID) is True and imap.boxes["Trash"] == [plain], "unattended, as before"


def test_the_trash_helper_takes_replace_only_for_a_pair_that_passes_the_replace_rules():
    """replace runs without Luca's Allow (owner decision, 14 Oct 2026), but replaced_by isn't a general way round it:
    trash_draft checks the replace rules for that exact pair itself."""
    d.lcs_owner._PROVEN = False
    other_thread = luca_draft(msg_id=NEW_ID).replace(b"In-Reply-To: <abc123@mail.example.com>",
                                                     b"In-Reply-To: <zzz@mail.example.com>")
    for drafts, new_id in (([luca_draft(key="2111-reply")], NEW_ID),             # no replacement saved
                           ([luca_draft(key="2111-reply")], LUCA_ID),            # itself
                           ([luca_draft(key="2111-reply"), luca_draft(msg_id=NEW_ID, to="someone@example.com")], NEW_ID),
                           ([luca_draft(key="2111-reply"), other_thread], NEW_ID)):
        imap = FakeIMAP(drafts=drafts)
        try:
            d.trash_draft(imap, LUCA_ID, own_only=False, replaced_by=new_id)
            raise AssertionError(f"trash_draft moved a draft for a pair the replace rules refuse ({new_id})")
        except d.Refused:
            pass
        assert imap.boxes["Trash"] == [] and not [c for c in imap.calls if c[0] == "uid"]
    old, new = luca_draft(key="2111-reply"), luca_draft(msg_id=NEW_ID)
    imap = FakeIMAP(drafts=[old, new])
    assert d.trash_draft(imap, LUCA_ID, own_only=False, replaced_by=NEW_ID) == "2111-reply"
    assert imap.boxes["Trash"] == [old] and imap.boxes["Drafts"] == [new]


def test_replace_runs_unattended_without_the_owners_nonce():
    d.lcs_owner._PROVEN = False
    old, new = luca_draft(), luca_draft(msg_id=NEW_ID)
    imap = FakeIMAP(drafts=[old, new])
    rc, out = run_main(["replace", LUCA_ID, NEW_ID], imap)
    assert rc == 0 and "moved to Trash" in out and imap.boxes["Trash"] == [old], out
    assert not d.lcs_owner.owner_proven()


def test_discard_refuses_other_senders_missing_or_duplicate_drafts():
    other = luca_draft().replace(d.FROM_HEADER.encode(), b"Luca <luca@almaconsort.com>")
    for drafts, why in (([other], "only a draft from office@"), ([], "isn't in Drafts"),
                        ([luca_draft(), luca_draft()], "couldn't move")):
        imap = FakeIMAP(drafts=drafts)
        rc, out = owner_run(["discard", LUCA_ID, "--owner"], imap)
        assert rc == 1 and why in out and imap.boxes["Trash"] == [], (why, out)
    rc, out = owner_run(["discard", "not-an-id", "--owner"], FakeIMAP())
    assert rc == 1 and "Message-ID" in out, out


NEW_ID = "<new@londonchoralservice.com>"


def test_replace_moves_the_old_draft_once_its_replacement_is_saved():
    clear_saved()
    old, new = luca_draft(key="2111-confirmation"), luca_draft(msg_id=NEW_ID)
    d.record_saved("2111-confirmation")
    imap = FakeIMAP(drafts=[old, new])
    rc, out = run_main(["replace", LUCA_ID, NEW_ID], imap)
    assert rc == 0 and "moved to Trash" in out, out
    assert imap.boxes["Trash"] == [old] and imap.boxes["Drafts"] == [new], "only the old draft, and only to Trash"
    assert not d.saved_before("2111-confirmation")


def test_replace_refuses_unless_the_new_draft_matches():
    other_sender = luca_draft(msg_id=NEW_ID).replace(d.FROM_HEADER.encode(), b"Luca <luca@almaconsort.com>")
    for drafts, why in (([luca_draft()], "replacement draft isn't in Drafts"),
                        ([luca_draft(msg_id=NEW_ID)], "old draft isn't in Drafts"),
                        ([luca_draft(), luca_draft(msg_id=NEW_ID, to="someone@example.com")], "same one address"),
                        ([luca_draft(), other_sender], "only drafts from office@")):
        imap = FakeIMAP(drafts=drafts)
        rc, out = run_main(["replace", LUCA_ID, NEW_ID], imap)
        assert rc == 1 and why in out and imap.boxes["Trash"] == [], (why, out)
    other_thread = luca_draft(msg_id=NEW_ID).replace(b"In-Reply-To: <abc123@mail.example.com>",
                                                     b"In-Reply-To: <zzz@mail.example.com>")
    imap = FakeIMAP(drafts=[luca_draft(), other_thread])
    rc, out = run_main(["replace", LUCA_ID, NEW_ID], imap)
    assert rc == 1 and "same conversation" in out and imap.boxes["Trash"] == [], out
    for args in (["replace", LUCA_ID, LUCA_ID], ["replace", "x", NEW_ID]):
        rc, out = run_main(args, FakeIMAP(drafts=[luca_draft()]))
        assert rc == 1 and out.startswith("STOP:"), (args, out)


def test_the_script_has_no_sending_code():
    src = (ROOT / "scripts" / "bookings" / "imap_draft.py").read_text()
    for word in ("smtplib", "SMTP(", "sendmail", "send_message", ".store(", ".copy(", ".move(", "expunge",
                 "EXPUNGE", "STORE", "COPY", ".delete(", ".create(", "Deleted"):
        assert word not in src, word
    # UID commands only in trash_draft: a FETCH of headers and one MOVE, to Trash
    trash = src[src.index("def trash_draft"):src.index("def retire_original")]
    rest = src.replace(trash, "")
    assert ".uid(" not in rest and "conn.select(DRAFTS)" not in rest.replace("conn.select(DRAFTS, readonly=True)", "")
    assert re.findall(r'\.uid\("(\w+)"', trash) == ["FETCH", "MOVE"], re.findall(r'\.uid\("(\w+)"', trash)
    assert 'conn.uid("MOVE", uid, TRASH)' in trash and "len(hits) != 1" in trash
    assert "conn.close()" not in trash, "CLOSE on a writable folder would expunge"
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
