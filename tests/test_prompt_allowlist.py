#!/usr/bin/env python3
"""Every `.venv/bin/python scripts/…` command in the two unattended prompts (handover Appendix A,
the Monday review, and Appendix E, the enquiry assistant) must match a Bash allow entry in
.claude/settings.json, so a scheduled run never stops on a permission prompt. The one command
that must NOT be allowed is `singer_invoices.py confirm`: the owner runs it himself after
ringing the singer. Stdlib only: .venv/bin/python tests/test_prompt_allowlist.py"""
import fnmatch, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOVER = os.path.join(ROOT, "docs", "HANDOVER-2026-09-27-ads-analytics.md")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")
PREFIX = ".venv/bin/python scripts/"
COMMAND = re.compile(r"\.venv/bin/python scripts/[^`\n]*")
CONFIRM = ".venv/bin/python scripts/bookings/singer_invoices.py confirm"


def text_block(appendix):
    """The ```text block under '## Appendix <letter>'."""
    with open(HANDOVER, encoding="utf-8") as f:
        doc = f.read()
    start = doc.index(f"## Appendix {appendix}:")
    end = doc.find("\n## ", start + 1)
    section = doc[start:end if end != -1 else len(doc)]
    m = re.search(r"```text\n(.*?)\n```", section, re.S)
    assert m, f"no ```text block in Appendix {appendix}"
    return m.group(1)


def commands(block):
    """Each command as written, with a trailing '(…)' remark and trailing punctuation removed."""
    out = []
    for m in COMMAND.finditer(block):
        cmd = re.sub(r"\s{2,}\(.*$", "", m.group(0))  # "   (fallback only, …)"
        cmd = cmd.rstrip(" .,;:)")
        out.append(cmd)
    return out


def allow_patterns():
    with open(SETTINGS) as f:
        allow = json.load(f)["permissions"]["allow"]
    return [a[len("Bash("):-1] for a in allow if a.startswith("Bash(") and a.endswith(")")]


def allowed(cmd, patterns):
    return any(fnmatch.fnmatchcase(cmd, p) for p in patterns)


def test_both_prompts_name_commands():
    assert len(commands(text_block("A"))) >= 5
    assert len(commands(text_block("E"))) >= 25


def test_every_prompt_command_is_allowlisted():
    patterns = allow_patterns()
    missing = []
    for appendix in ("A", "E"):
        for cmd in commands(text_block(appendix)):
            if cmd.startswith(CONFIRM):
                continue  # checked below: must not be allowed
            if not allowed(cmd, patterns):
                missing.append(f"Appendix {appendix}: {cmd}")
    assert not missing, "not in .claude/settings.json allow:\n  " + "\n  ".join(missing)


def test_singer_confirm_is_never_allowed():
    patterns = allow_patterns()
    for cmd in [CONFIRM + " 6133510000000170001", CONFIRM] + [
            c for a in ("A", "E") for c in commands(text_block(a)) if c.startswith(CONFIRM)]:
        assert not allowed(cmd, patterns), f"{cmd} must not be allowlisted"


def test_new_helper_commands_are_covered():
    patterns = allow_patterns()
    for cmd in (".venv/bin/python scripts/bookings/assistant_io.py daily-done",
                ".venv/bin/python scripts/bookings/assistant_io.py prices",
                ".venv/bin/python scripts/bookings/assistant_io.py next-ref 2026-11-21 --taken 2111,2111A",
                ".venv/bin/python scripts/bookings/pipeline.py thread 2111",
                ".venv/bin/python scripts/bookings/pipeline.py review-skipped 2111 planner",
                ".venv/bin/python scripts/bookings/check_payments.py --json",
                ".venv/bin/python scripts/bookings/check_payments.py --apply --json"):
        assert allowed(cmd, patterns), cmd


def test_extraction_handles_remarks_and_placeholders():
    block = ("  .venv/bin/python scripts/bookings/singer_invoices.py scan <file> --message-id <id>   (fallback only)\n"
             "run `.venv/bin/python scripts/reports/dashboard.py`.")
    assert commands(block) == [".venv/bin/python scripts/bookings/singer_invoices.py scan <file> --message-id <id>",
                               ".venv/bin/python scripts/reports/dashboard.py"]


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
