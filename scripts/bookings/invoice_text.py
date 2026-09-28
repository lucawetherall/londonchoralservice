#!/usr/bin/env python3
"""Read London Choral Service invoice PDFs out of a raw email, for the private
bookings ledger.

The Zoho Mail MCP cannot download attachments, but ZohoMail_getOriginalMessage
returns the whole message (MIME, with the PDFs inside). Claude Code saves a
large result like that to a file; pass that file (or a plain .eml) here, or let
the script fetch the message itself (read-only, through scripts/bookings/lcs_mcp.py):

    .venv/bin/python scripts/bookings/invoice_text.py <saved-result-file> [...]
    .venv/bin/python scripts/bookings/invoice_text.py --fetch <message id> [--fetch <message id> ...]

For every attachment named "Invoice*.pdf" it prints the invoice number, issue
date, who it is billed to, the line items and the total. PDFs are unpacked into
a private temporary folder (mode 700, outside the repo) and deleted before the
script exits. Output stays in the session: never paste client names into the
repo, commits, PRs or logs/.
"""

import argparse
import email
import json
import re
import sys
import tempfile
from email import policy
from pathlib import Path

from pypdf import PdfReader


def raw_message_text(text):
    """Raw MIME from a ZohoMail_getOriginalMessage result (JSON, as saved or as returned inline) or from MIME itself."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text  # already MIME (.eml)
    if not isinstance(data, dict):
        return str(data)
    node = data.get("data", data)
    node = node.get("data", node) if isinstance(node, dict) else node
    return node.get("content", "") if isinstance(node, dict) else str(node)


def raw_message(path):
    return raw_message_text(Path(path).read_text(errors="replace"))


def fetch_message(message_id, **kw):
    """Raw MIME of a Zoho message, fetched read-only with ZohoMail_getOriginalMessage (no saved file needed)."""
    import lcs_mcp
    return raw_message_text(lcs_mcp.zoho_original_message(message_id, **kw))


def summarise(pdf_text):
    lines = [re.sub(r"\s+", " ", l).strip() for l in pdf_text.splitlines()]
    lines = [l for l in lines if l]
    joined = "\n".join(lines)
    number = re.search(r"№\s*(\S+)", joined)
    issued = re.search(r"Issued\s+(\d{1,2} \w+ \d{4})", joined)
    total = re.search(r"Total due\s*£\s*([\d,]+\.\d{2})", joined)
    billed = None
    for i, l in enumerate(lines):
        if re.sub(r"\s", "", l).upper().startswith("BILLEDTO") and i + 1 < len(lines):
            billed = lines[i + 1: i + 4]
            break
    items = [l for l in lines if "£" in l and not re.search(r"Subtotal|Total due|instalment|Payment in full", l)]
    brand = "London Choral Service" if re.search(r"L\s*O\s*N\s*D\s*O\s*N\s+C\s*H\s*O\s*R\s*A\s*L", joined) else "OTHER BRAND"
    return {"number": number and number.group(1), "issued": issued and issued.group(1),
            "total_gbp": total and total.group(1).replace(",", ""), "billed_to": billed,
            "items": items, "brand": brand,
            "schedule": [l for l in lines if re.search(r"instalment|Payment in full", l)]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--fetch", action="append", default=[], metavar="MESSAGE_ID",
                    help="fetch this Zoho message read-only instead of reading a saved file")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args()
    if not args.files and not args.fetch:
        ap.error("give a saved file or --fetch <message id>")
    sources = [(Path(f).name, lambda f=f: raw_message(f)) for f in args.files]
    sources += [(f"message {m}", lambda m=m: fetch_message(m)) for m in args.fetch]
    out = []
    with tempfile.TemporaryDirectory(prefix="lcs-inv-") as tmp:
        Path(tmp).chmod(0o700)
        for source, load in sources:
            msg = email.message_from_string(load(), policy=policy.default)
            found = False
            for part in msg.walk():
                name = part.get_filename() or ""
                if not re.match(r"(?i)invoice.*\.pdf$", name):
                    continue
                found = True
                pdf = Path(tmp) / re.sub(r"[^\w.\- ()]", "_", name)
                pdf.write_bytes(part.get_payload(decode=True))
                text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
                out.append({"file": name, "email_date": msg.get("Date"), **summarise(text)})
            if not found:
                out.append({"file": None, "source": source, "note": "no Invoice*.pdf attachment"})
    if args.json:
        json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
        print()
        return
    for r in out:
        if not r.get("file"):
            print(f"== {r['source']}: {r['note']}")
            continue
        print(f"== {r['file']} ({r['brand']})")
        print(f"   invoice {r['number']} · issued {r['issued']} · total £{r['total_gbp']} · email sent {r['email_date']}")
        print(f"   billed to: {' / '.join(r['billed_to'] or [])}")
        for i in r["items"]:
            print(f"   item: {i}")
        for sch in r["schedule"]:
            print(f"   terms: {sch}")


if __name__ == "__main__":
    main()
