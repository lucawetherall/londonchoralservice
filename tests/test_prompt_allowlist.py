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
    f"{PY} scripts/bookings/singer_invoices.py confirm 1789828736363141700",
    f"{PY} scripts/bookings/singer_invoices.py settled X 2026-09-28",
    f"{PY} scripts/ads/upload_bookings.py --apply",
    f"{PY} scripts/gsc/submit_sitemap.py --apply",
    # Ads change sets: the Command Centre applies them after two passkey taps (validate, then apply)
    f"{PY} scripts/ads/add_negatives_2026_09_28.py --apply",
    f"{PY} scripts/ads/set_campaign_status.py 24295921372 enabled --reason X --apply",
    f"{PY} scripts/ads/generated_proposal_2026_10_05.py --apply",
    f"{PY} scripts/ads/generated_proposal_2026_10_05.py",  # even the validate-only run goes through the app
    f"{PY} scripts/ads/set_budget.py 24295921372 4.50 --apply",
    f"{PY} scripts/ads/set_budget.py 24295921372 4.50 --validate-only",
    f"{PY} scripts/bookings/singer_invoices.py confirm X --expect-fp a1b2c3d4e5f60718",
    # the state log's owner commands: the Command Centre runs them after a passkey tap (structured-state design)
    f"{PY} scripts/bookings/events.py migrate --apply --expect {'a' * 64} --owner",
    f"{PY} scripts/bookings/events.py migrate --apply",
    f"{PY} scripts/bookings/events.py retract a1b2c3d4e5f60718 --owner",
    f"{PY} scripts/bookings/events.py notes-checked booking 2111 a1b2c3d4e5f6 --owner",
    # imap_draft.py: the assistant only saves drafts; the sign-in check and the test draft are the owner's
    f"{PY} scripts/bookings/imap_draft.py check",
    f"{PY} scripts/bookings/imap_draft.py test",
]
# Owner-only forms the allowlist can't exclude (a glob can't forbid a flag): `--note *` and `--reminded *` match
# them, so check_payments.py itself refuses --owner without the Command Centre's one-time nonce on a pipe
# (tests/test_check_payments.py, test_owner_note_is_refused_without_the_nonce and the tests after it).
SCRIPT_GUARDED = [
    f"{PY} scripts/bookings/check_payments.py --note X \"paid in full 2026-09-28\" --owner",
    f"{PY} scripts/bookings/check_payments.py --reminded X --note X \"refunded 2026-09-28\" --owner",
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
    # The enquiry assistant (Appendix E) dispatches to sub-agents in .claude/agents/; their prompts run
    # unattended under the same allowlist, so they are checked too (key "agent:<name>").
    agents = os.path.join(ROOT, ".claude", "agents")
    if os.path.isdir(agents):
        for f in sorted(os.listdir(agents)):
            if f.endswith(".md"):
                body = open(os.path.join(agents, f), encoding="utf-8").read()
                out[f"agent:{f[:-3]}"] = body.split("---", 2)[2] if body.startswith("---") else body
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
    return patterns_of(json.load(open(SETTINGS))["permissions"]["allow"])


def patterns_of(rules):
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


MONDAY_AGENTS = ("lcs-review-ads", "lcs-review-web", "lcs-review-bookings")


def test_prompts_name_commands():
    blocks, scripts = appendix_blocks(), script_paths()
    # The Monday review (Appendix A) is a dispatcher: its own commands plus its three sub-agents'.
    monday = commands(blocks["A"], scripts) + [c for n in MONDAY_AGENTS for c in commands(blocks[f"agent:{n}"], scripts)]
    assert len(commands(blocks["A"], scripts)) >= 2 and len(monday) >= 10, monday
    assistant = [c for k, b in blocks.items() if k == "E" or k.startswith("agent:") for c in commands(b, scripts)]
    assert len(assistant) >= 20, len(assistant)


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


def test_script_guarded_forms_are_documented_and_guarded():
    """These ARE matched by the allowlist, which is why check_payments.py must refuse them itself: if one ever
    stops matching (the allowlist narrowed), it can move to NEVER."""
    pats = allow_patterns()
    for cmd in SCRIPT_GUARDED:
        assert allowed(cmd, pats), f"{cmd} no longer matches the allowlist: move it to NEVER"
        assert cmd.rstrip().endswith("--owner")
    src = open(os.path.join(ROOT, "scripts", "bookings", "check_payments.py"), encoding="utf-8").read()
    assert "def owner_confirmed(" in src and "if not owner_confirmed():" in src


def test_claude_file_tools_cant_write_the_command_centre_folder():
    """The owner nonce, proposals, approvals and audit log live in ~/lcs-private/command-centre/: Claude's Write
    and Edit tools are denied there (the nonce file is the --owner barrier; a pipe alone is not)."""
    with open(SETTINGS, encoding="utf-8") as f:
        deny = json.load(f)["permissions"]["deny"]
    for tool in ("Write", "Edit"):
        assert f"{tool}(~/lcs-private/command-centre/**)" in deny, tool


GIT_DENY = ["Bash(git update-ref *)", "Bash(git remote set-url *)", "Bash(git config *)", "Edit(.git/**)"]


def deny_patterns():
    with open(SETTINGS, encoding="utf-8") as f:
        deny = json.load(f)["permissions"]["deny"]
    return deny, patterns_of([r for r in deny if r.startswith("Bash(")])


def test_git_ref_and_config_changes_are_denied():
    """Belt and braces for the Ads mirror (it never trusts the working repo, but Claude shouldn't be moving refs,
    remotes or git config by hand): the deny rules exist, they don't catch any command the scheduled prompts run,
    and the prompts never ask for git config, update-ref or remote set-url."""
    deny, pats = deny_patterns()
    for rule in GIT_DENY:
        assert rule in deny, rule
    for cmd in ("git update-ref refs/remotes/origin/main HEAD", "git remote set-url origin https://example.org/x",
                "git config filter.x.smudge cat", "git config --local --list"):
        assert any(p.fullmatch(cmd) for _, p in pats), cmd
    blocks, scripts = appendix_blocks(), script_paths()
    for k, b in blocks.items():
        for c in commands(b, scripts):
            assert not any(p.fullmatch(c) for _, p in pats), f"Appendix {k}: {c} is denied"
        for bad in ("git config", "update-ref", "remote set-url"):
            assert bad not in b, f"Appendix {k} mentions {bad}"
    for everyday in ("git status", "git fetch -q origin", "git add -A", "git commit -m x", "git push origin x"):
        assert not any(p.fullmatch(everyday) for _, p in pats), everyday


def test_no_allowlist_rule_covers_every_script():
    """A rule like Bash(.venv/bin/python *) or Bash(.venv/bin/python scripts/ads/*) would let any owner-only
    command through."""
    for rule, _ in allow_patterns():
        fixed = rule[len("Bash("):-1].split("*", 1)[0]  # everything before the first wildcard
        assert re.fullmatch(rf"{re.escape(PY)} scripts/[a-z]+/[a-z_]+\.py( .*)?", fixed.rstrip()), rule


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
                f"{PY} scripts/bookings/singer_invoices.py withdrawn 1789828736363141700 not-ours",
                f"{PY} scripts/bookings/singer_invoices.py link 1789828736363141700 2111",
                f"{PY} scripts/bookings/singer_invoices.py margins",
                f"{PY} scripts/reports/cc_sync.py books",
                f"{PY} scripts/reports/cc_sync.py calendar-put 'X'",
                f"{PY} scripts/reports/weekly_review.py --save-report --write-proposals"):
        assert allowed(cmd, pats), cmd


def test_the_command_centre_caches_and_proposals_are_in_the_prompts():
    """The daily pass writes the Books and diary caches with plain allowlisted commands (never a pipe or heredoc,
    which the allowlist can't vouch for), and the Monday review writes its budget proposals for the app."""
    blocks, scripts = appendix_blocks(), script_paths()
    a = commands(blocks["A"], scripts)
    agents = {name: commands(blocks[f"agent:{name}"], scripts) for name in ("lcs-daily-pass", "lcs-singer-clerk")}
    assert f"{PY} scripts/reports/cc_sync.py books" in agents["lcs-daily-pass"], agents
    assert f"{PY} scripts/reports/cc_sync.py calendar-put 'X'" in agents["lcs-daily-pass"], agents
    assert f"{PY} scripts/bookings/singer_invoices.py link X X" in agents["lcs-singer-clerk"], agents
    assert f"{PY} scripts/reports/weekly_review.py --save-report --quiet --write-proposals" in a, a
    assert "Budget proposals are waiting in the command centre" in blocks["agent:lcs-review-bookings"]
    for name in MONDAY_AGENTS:  # each Monday sub-agent reads its own slice of the saved report
        assert any(c.startswith(f"{PY} scripts/reports/report_sections.py ") for c in
                   commands(blocks[f"agent:{name}"], scripts)), name
    assert not allowed(f"{PY} scripts/reports/cc_sync.py calendar-put < /tmp/x | cat", allow_patterns())


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
