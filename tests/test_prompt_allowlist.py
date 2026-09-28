#!/usr/bin/env python3
"""The scheduled prompts (handover Appendix A, the Monday review, and Appendix E, the enquiry
assistant) run unattended: every script command they tell Claude to run must be allowed by
.claude/settings.json, or the run stops on a permission prompt. The owner-only and
approval-gated commands must stay OFF the allowlist. Stdlib only:
.venv/bin/python tests/test_prompt_allowlist.py (merges the prompt fixer's checks with the reviewer's)

Matching follows Claude Code's Bash rules conservatively: "Bash(cmd)" is an exact match,
"*" matches any characters, and a trailing " *" needs at least one argument (so it never
covers the bare command; list that separately, as settings.json already does).
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOVER = os.path.join(ROOT, "docs", "HANDOVER-2026-09-27-ads-analytics.md")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")
PY = ".venv/bin/python"

# Owner-only or approval-gated: the prompts name them, but Claude must never run them unattended.
NEVER = [
    f"{PY} scripts/bookings/singer_invoices.py confirm X",
    f"{PY} scripts/bookings/singer_invoices.py settled X 2026-09-28",
    f"{PY} scripts/ads/upload_bookings.py --apply",
    f"{PY} scripts/gsc/submit_sitemap.py --apply",
]
# Script mentions that are references or prohibitions, not commands to run.
NOT_RUN = re.compile(r"^(singer_invoices\.py (confirm|settled)|scripts/gsc/submit_sitemap\.py --apply)\b")


def appendix_blocks():
    """{"A": text, "E": text}: the ```text block under each appendix heading."""
    text = open(HANDOVER, encoding="utf-8").read()
    out = {}
    for letter in ("A", "E"):
        m = re.search(rf"^## Appendix {letter}:.*?^```text\n(.*?)^```", text, re.M | re.S)
        assert m, f"Appendix {letter} has no ```text block"
        out[letter] = m.group(1)
    return out


def script_paths():
    """Bare script name -> path from the repo root (pipeline.py -> scripts/bookings/pipeline.py)."""
    out = {}
    for d, _, files in os.walk(os.path.join(ROOT, "scripts")):
        for f in files:
            if f.endswith(".py"):
                out.setdefault(f, os.path.relpath(os.path.join(d, f), ROOT))
    return out


def normalise(cmd, scripts, last_script):
    """A prompt's command -> the full command line as Claude would run it, placeholders filled.
    Returns (command or None, script used)."""
    cmd = cmd.strip()
    if cmd.startswith(("…", "...", "--")):  # "… --note <ref> ..." continues the previous command
        if not last_script:
            return None, last_script
        cmd = f"{last_script} {cmd.lstrip('…. ')}"
    cmd = re.sub(r"^(?:\.venv/bin/)?python3?\s+", "", cmd)
    first = cmd.split()[0]
    if first in scripts:
        cmd = scripts[first] + cmd[len(first):]
        first = scripts[first]
    if not (first.startswith("scripts/") and first.endswith(".py")):
        return None, last_script
    cmd = re.sub(r"<[^<>]*>", "X", cmd)  # <threadId>, '<one-line JSON>' -> X, 'X'
    return f"{PY} {cmd}", f"{PY} {first}"


def commands(block, scripts):
    """Every script invocation in a prompt block: backticked spans and the indented command list."""
    spans = re.findall(r"`([^`\n]+)`", block)
    spans += [ln.strip() for ln in block.splitlines() if re.match(r"\s+\.venv/bin/python ", ln)]
    out, last = [], None
    for span in spans:
        span = re.sub(r"\s+\(fallback only.*$", "", span)
        if NOT_RUN.match(span) or ".py" not in span and not span.startswith(("…", "--")):
            continue
        cmd, last = normalise(span, scripts, last)
        if cmd and cmd.split()[1].endswith(".py") and len(cmd.split()) >= 2:
            out.append(cmd)
    return sorted(set(out))


def allow_patterns():
    rules = json.load(open(SETTINGS))["permissions"]["allow"]
    pats = []
    for r in rules:
        m = re.fullmatch(r"Bash\((.*)\)", r)
        if not m:
            continue
        body = m.group(1)
        if body.endswith(":*"):  # legacy prefix form
            pats.append((r, re.compile(re.escape(body[:-2]) + r"(?:\s.*)?", re.S)))
            continue
        parts = [re.escape(p) for p in body.split("*")]
        pats.append((r, re.compile(".*".join(parts), re.S)))
    return pats


def allowed(cmd, pats):
    if re.search(r"&&|\|\||;|\||`|\$\(", cmd.replace("'X'", "")):  # compound: every part needs a rule
        return False
    return any(p.fullmatch(cmd) for _, p in pats)


def test_prompts_name_commands():
    blocks, scripts = appendix_blocks(), script_paths()
    assert len(commands(blocks["A"], scripts)) >= 5
    assert len(commands(blocks["E"], scripts)) >= 20


def test_every_prompt_command_is_allowlisted():
    blocks, scripts, pats = appendix_blocks(), script_paths(), allow_patterns()
    missing = [(k, c) for k, b in blocks.items() for c in commands(b, scripts) if not allowed(c, pats)]
    assert not missing, "not in .claude/settings.json allow (the run would stop on a prompt):\n" + "\n".join(
        f"  Appendix {k}: {c}" for k, c in missing)


def test_prompt_scripts_exist():
    blocks, scripts = appendix_blocks(), script_paths()
    for k, b in blocks.items():
        for c in commands(b, scripts):
            path = c.split()[1]
            assert os.path.exists(os.path.join(ROOT, path)) or re.search(r"X", path), f"Appendix {k}: {path} missing"


def test_owner_only_commands_are_not_allowlisted():
    pats = allow_patterns()
    wrongly = [c for c in NEVER if allowed(c, pats)]
    assert not wrongly, "owner-only or approval-gated commands must prompt: " + ", ".join(wrongly)


def test_appendix_e_prose_uses_only_its_own_command_list():
    """Appendix E says "The only shell commands you run are these": prose steps may not add a script
    subcommand the list lacks."""
    e, scripts = appendix_blocks()["E"], script_paths()
    listed = [ln.strip() for ln in e.splitlines() if re.match(r"\s+\.venv/bin/python ", ln)]
    heads = {" ".join(normalise(ln, scripts, None)[0].split()[:3]) for ln in listed}
    extra = [c for c in commands(e, scripts) if " ".join(c.split()[:3]) not in heads]
    assert not extra, "Appendix E prose runs commands its TOOLS list lacks:\n" + "\n".join(extra)


def test_helper_commands_the_prompts_rely_on_are_covered():
    pats = allow_patterns()
    for cmd in (f"{PY} scripts/bookings/assistant_io.py daily-done",
                f"{PY} scripts/bookings/assistant_io.py prices",
                f"{PY} scripts/bookings/assistant_io.py next-ref 2026-11-21 --taken 2111,2111A",
                f"{PY} scripts/bookings/pipeline.py thread 2111",
                f"{PY} scripts/bookings/pipeline.py review-skipped 2111 planner",
                f"{PY} scripts/bookings/check_payments.py --json",
                f"{PY} scripts/bookings/check_payments.py --apply --json",
                f"{PY} scripts/bookings/check_payments.py --reminded 2111 --kind balance",
                f"{PY} scripts/bookings/invoice_text.py --fetch 6133510000000170001",
                f"{PY} scripts/bookings/singer_invoices.py withdrawn 1789828736363141700 not-ours"):
        assert allowed(cmd, pats), cmd


def test_extraction_handles_remarks_placeholders_and_continuations():
    scripts = script_paths()
    block = ("  .venv/bin/python scripts/bookings/singer_invoices.py scan <file> --message-id <id>   (fallback only)\n"
             "run `.venv/bin/python scripts/reports/dashboard.py`, then `check_payments.py --note <ref> \"x\"` "
             "and `… --note <ref> \"cancelled <YYYY-MM-DD>\"`.")
    assert commands(block, scripts) == [
        f"{PY} scripts/bookings/check_payments.py --note X \"cancelled X\"",
        f"{PY} scripts/bookings/check_payments.py --note X \"x\"",
        f"{PY} scripts/bookings/singer_invoices.py scan X --message-id X",
        f"{PY} scripts/reports/dashboard.py"], commands(block, scripts)


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"PASS {name}")
        except Exception as ex:  # an error is a failure too
            failures += 1
            print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
