#!/usr/bin/env python3
"""Make the invoice PDF and the booking confirmation (.docx) for one booking.

Uses the owner's own templates, kept PRIVATE in ~/lcs-private/tools/ (they hold
the bank details, so they never go in this public repo):
  invoice.html + fill-template.js      from the lcs-invoice-generator skill
  generate-agreement.js (+ npm docx)   from the lcs-booking-agreement-generator skill
The invoice is rendered with headless Google Chrome and must fit on one page.

    .venv/bin/python scripts/bookings/make_booking_docs.py spec.json

spec.json (all money in pounds; the fee must be the one the client accepted):
  {"ref": "2111", "client_name": "…", "service_type": "Wedding ceremony",
   "service_date": "2026-11-21", "service_time": "3.00pm", "venue": "Chelsea Town Hall",
   "provision": "Solo singer & harpist", "issue_date": "2026-08-21",
   "items": [{"name": "Wedding solo singer", "detail": "…", "qty": 1, "rate": 325}, …],
   "instalment_1_due": "2026-08-28", "instalment_2_due": "2026-11-20"}
Instalments are 50/50 unless "instalment_1" / "instalment_2" amounts are given.
Output goes to ~/lcs-private/invoices/<ref> - <client>/ (mode 700). Nothing is
sent anywhere: the owner attaches the files to the reply draft in Zoho.
"""

import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader

TOOLS = Path.home() / "lcs-private" / "tools"
OUT_ROOT = Path.home() / "lcs-private" / "invoices"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def long_date(iso, weekday=False):
    d = datetime.date.fromisoformat(iso)
    return d.strftime(("%A, " if weekday else "") + "%-d %B %Y")


def money(x):
    return f"£{x:,.2f}"


def fail(msg):
    raise SystemExit(f"STOP: {msg}")


def main():
    if len(sys.argv) != 2:
        fail("usage: make_booking_docs.py spec.json")
    spec = json.loads(Path(sys.argv[1]).read_text())
    for f in ("ref", "client_name", "service_type", "service_date", "provision", "items",
              "instalment_1_due", "instalment_2_due"):
        if not spec.get(f):
            fail(f"spec is missing {f}")
    for need in ("invoice.html", "fill-template.js", "generate-agreement.js", "node_modules/docx"):
        if not (TOOLS / need).exists():
            fail(f"{TOOLS / need} is missing (see the handover doc, section 4)")
    if re.search(r"\bVAT\b", json.dumps(spec), re.I):
        fail("the spec mentions VAT; Alma Consort Ltd is not VAT-registered, so no VAT line")
    total = round(sum(float(i["rate"]) * float(i.get("qty", 1)) for i in spec["items"]), 2)
    i1 = round(float(spec.get("instalment_1", total / 2)), 2)
    i2 = round(float(spec.get("instalment_2", total - i1)), 2)
    if abs(i1 + i2 - total) > 0.005:
        fail(f"instalments {i1} + {i2} do not add up to the total {total}")
    issue = spec.get("issue_date") or datetime.date.today().isoformat()
    when = long_date(spec["service_date"], weekday=True)
    if spec.get("service_time"):
        when += f" at {spec['service_time']}"
    service = spec["service_type"] + (f" — {spec['venue']}" if spec.get("venue") else "")
    client, ref = spec["client_name"].strip(), str(spec["ref"]).strip()

    folder = OUT_ROOT / f"{ref} - {client}"
    folder.mkdir(parents=True, exist_ok=True)
    os.chmod(folder, 0o700)
    pdf = folder / f"Invoice {ref} - {client}.pdf"
    short = datetime.date.fromisoformat(spec["service_date"]).strftime("%-d %b %Y")
    docx = folder / f"Booking Confirmation - {client} - {short}.docx"

    inv_spec = {
        "INVOICE_REF": ref, "ISSUE_DATE": long_date(issue), "CLIENT_NAME": client,
        "SERVICE_TYPE": service, "SERVICE_DATE": when,
        "items": [{"name": i["name"], "detail": i.get("detail", ""), "qty": i.get("qty", 1), "rate": i["rate"]}
                  for i in spec["items"]],
        "INSTALMENT_1_AMOUNT": money(i1),
        "INSTALMENT_1_DATE": f"Due by {long_date(spec['instalment_1_due'])} to confirm the booking",
        "INSTALMENT_2_AMOUNT": money(i2),
        "INSTALMENT_2_DATE": f"Due by {long_date(spec['instalment_2_due'])} (at least 24 hours before the service)",
        "PAYMENT_REF": f"INV {ref}",
    }
    agr_spec = {
        "client_name": client, "service_type": service, "service_date": when,
        "provision": spec["provision"], "total_fee": money(total),
        "instalment_1_amount": money(i1), "instalment_1_due": long_date(spec["instalment_1_due"]),
        "instalment_2_amount": money(i2), "instalment_2_due": long_date(spec["instalment_2_due"]),
        "payment_ref": f"INV {ref}", "issue_date": long_date(issue),
    }
    with tempfile.TemporaryDirectory(prefix="lcs-docs-") as tmp:
        tmp = Path(tmp)
        (tmp / "inv.json").write_text(json.dumps(inv_spec))
        (tmp / "agr.json").write_text(json.dumps(agr_spec))
        html = tmp / "invoice.html"
        subprocess.run(["node", str(TOOLS / "fill-template.js"), str(tmp / "inv.json"), str(TOOLS / "invoice.html"), str(html)],
                       check=True, capture_output=True, text=True)
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={tmp / 'chrome'}", f"--print-to-pdf={pdf}", html.as_uri()],
                       check=True, capture_output=True, text=True, timeout=120)
        subprocess.run(["node", str(TOOLS / "generate-agreement.js"), str(tmp / "agr.json"), str(docx)],
                       check=True, capture_output=True, text=True, cwd=TOOLS)
    pages = len(PdfReader(pdf).pages)
    for f in (pdf, docx):
        os.chmod(f, 0o600)
    print(f"invoice {ref}: total {money(total)} · instalments {money(i1)} + {money(i2)} · {pages} page(s)")
    print(f"   {pdf}")
    print(f"   {docx}")
    if pages != 1:
        fail("the invoice runs to more than one page; tighten the template before sending")


if __name__ == "__main__":
    main()
