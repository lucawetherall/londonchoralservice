#!/usr/bin/env python3
"""Print chosen sections of a saved Monday report, so each Monday sub-agent reads only its own part.

The report is the one `weekly_review.py --save-report` archived: ~/lcs-private/reports/<date>.txt (today,
Europe/London, unless --date). Sections are named as the report heads them ("== 4b. Google's …" is 4b).
Read-only; prints nothing but the report's own text, which carries no names or emails.

    .venv/bin/python scripts/reports/report_sections.py 1 2 4 4b      # today's report
    .venv/bin/python scripts/reports/report_sections.py --date 2026-10-05 6 7 13
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bookings"))
import lcs_money as lm  # noqa: E402  PRIVATE, today

HEAD = re.compile(r"^== (\w+)\.", re.M)


def split(text):
    """{section id: its text, heading included}, in report order."""
    marks = [(m.group(1), m.start()) for m in HEAD.finditer(text)]
    return {sid: text[start:(marks[i + 1][1] if i + 1 < len(marks) else len(text))].rstrip() + "\n"
            for i, (sid, start) in enumerate(marks)}


def main(argv=None):
    p = argparse.ArgumentParser(description="Print sections of a saved Monday report.")
    p.add_argument("sections", nargs="+", help="section ids as the report heads them: 1 2 4b 12 …")
    p.add_argument("--date", type=datetime.date.fromisoformat, help="the report's date (default: today)")
    args = p.parse_args(argv)
    path = lm.PRIVATE / "reports" / f"{args.date or lm.today()}.txt"
    if not path.is_file():
        print(f"no saved report at {path}: run weekly_review.py --save-report first", file=sys.stderr)
        return 2
    parts = split(path.read_text(encoding="utf-8"))
    missing = [s for s in args.sections if s not in parts]
    for s in args.sections:
        if s in parts:
            sys.stdout.write(parts[s] + "\n")
    if missing:
        print(f"not in this report: {' '.join(missing)} (it has {' '.join(parts) or 'nothing'})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
