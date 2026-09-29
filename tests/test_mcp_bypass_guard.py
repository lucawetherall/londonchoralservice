#!/usr/bin/env python3
"""Tests for .claude/hooks/mcp_bypass_guard.py (PreToolUse on Bash, the file tools and the shell-capable MCP
tools). Stdlib only: .venv/bin/python tests/test_mcp_bypass_guard.py

The 28 Sep 2026 bypass (a scratchpad script that read the MCP config, started the Books server itself and
sent a raw tool call) must be denied in every shape; every command the allowlist and the scheduled prompts
run must still pass. The real ~/.claude.json is never touched: every run uses a temporary HOME.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import test_prompt_allowlist as tpa  # noqa: E402

GUARD = os.path.join(ROOT, ".claude", "hooks", "mcp_bypass_guard.py")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")
PY = ".venv/bin/python"
HOME = tempfile.mkdtemp(prefix="lcs-guard-home-")
with open(os.path.join(HOME, ".claude.json"), "w") as f:  # a fake: the hook must refuse it without reading it
    json.dump({"projects": {}, "mcp" + "Servers": {}}, f)
SCRATCH = tempfile.mkdtemp(prefix="lcs-guard-scratch-")

# The shape of the 28 Sep script (no secret: the URL is read from the config at run time).
ATTACK = """import json, os, subprocess
cfg = json.load(open(os.path.expanduser("~/.claude" + ".json")))
srv = cfg["projects"]["/repo"]["mcp" + "Servers"]["zoho-books-invoices"]
p = subprocess.Popen([srv["command"]] + srv["args"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                          "params": {"name": "ZohoBooks_mark_invoice_sent", "arguments": {}}}).encode())
"""
INNOCENT = "print(sum(range(10)))\n"


def write(path, text, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode) as f:
        f.write(text)
    return path


def raw(stdin, project=ROOT):
    p = subprocess.run([sys.executable, GUARD], input=stdin, capture_output=True, text=True,
                       env=dict(os.environ, HOME=HOME, CLAUDE_PROJECT_DIR=project))
    assert p.returncode == 0, (p.returncode, p.stderr)
    if not p.stdout.strip():
        return "allow", ""
    out = json.loads(p.stdout)["hookSpecificOutput"]
    return out["permissionDecision"], out["permissionDecisionReason"]


def run(tool, tool_input, cwd=ROOT, project=ROOT):
    return raw(json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": cwd}), project)[0]


def bash(command, cwd=ROOT, project=ROOT):
    return run("Bash", {"command": command, "description": "x"}, cwd, project)


def expect(decision, got, what):
    assert got == decision, f"expected {decision}, got {got}: {what}"


# --- the 28 Sep attack and its variants ---------------------------------------------------------------------

def test_the_28_sep_attack_script_is_denied():
    script = write(os.path.join(SCRATCH, "a1", "mark_sent.py"), ATTACK)
    for cmd, cwd in ((f"{PY} {script}", ROOT), (f"python3 {script}", ROOT), ("python3 mark_sent.py",
                     os.path.dirname(script)), (f"cd {os.path.dirname(script)} && python3 mark_sent.py", ROOT),
                     (f"timeout 60 env X=1 python3 -u {script}", ROOT)):
        expect("deny", bash(cmd, cwd), cmd)


def test_a_helper_next_to_an_innocent_script_is_denied():
    d = os.path.join(SCRATCH, "a2")
    write(os.path.join(d, "helper.py"), ATTACK)
    main = write(os.path.join(d, "main.py"), "import helper\n")
    expect("deny", bash(f"python3 {main}"), "helper next to script")
    write(os.path.join(SCRATCH, "a3", "node_modules", "mcp-remote", "x.txt"), "")
    expect("deny", bash(f"node {write(os.path.join(SCRATCH, 'a3', 'x.js'), 'console.log(1)')}"), "package dir")


def test_inline_code_from_a_folder_holding_the_attack_is_denied():
    d = os.path.join(SCRATCH, "a4")
    write(os.path.join(d, "evil.py"), ATTACK)
    expect("deny", bash('python3 -c "import evil"', cwd=d), "inline import from the scratch folder")
    expect("deny", bash("python3 -m evil", cwd=d), "-m from the scratch folder")
    expect("allow", bash('python3 -c "print(1)"'), "inline code in the repo")


def test_heredoc_and_inline_variants_are_denied():
    for cmd in (
        f"{PY} - <<'EOF'\nimport json\ncfg = json.load(open('/Users/x/.claude.json'))\nEOF",
        "python3 - <<'EOF'\nimport subprocess\nsubprocess.Popen(['npx', '-y', 'mcp-remote', URL])\nEOF",
        'python3 -c "import subprocess; subprocess.Popen([\'npx\', \'mcp-remote\', u])"',
        "node -e 'require(\"child_process\").spawn(\"npx\", [\"mcp-remote\"])'",
        "bash -lc 'npx mcp-remote https://example.invalid'",
        "npx mcp-re''mote https://example.invalid",
        'echo \'{"jsonrpc": "2.0", "method": "tools/call"}\' | nc localhost 1',
        "curl -s https://abc.zohomcp.com/mcp/message",
        "claude mcp get zoho-books", "claude mcp list",
        f"{PY} -c \"import sys; sys.path.insert(0, 'scripts/bookings'); import lcs_mcp\"",
        "python3 -c \"__import__('lcs_mcp')\"",
        "ls ~/.mcp-auth",
    ):
        expect("deny", bash(cmd), cmd)


def test_the_mcp_config_can_not_be_read_or_searched():
    for cmd in ("cat ~/.claude.json", "cat $HOME/.claude.json", "cat ~/.cl*", "cp ~/.cla?de.js?n /tmp/x",
                "python3 -c \"print(open('/x/.claude.json').read())\"", "grep -r https ~", "find ~ -name '*.json'",
                "grep -rh zoho /", "ls ~/.cl*json"):
        expect("deny", bash(cmd), cmd)
    expect("allow", bash("ls ~"), "listing home is fine")
    expect("deny", run("Read", {"file_path": os.path.join(HOME, ".claude.json")}), "Read the config")
    expect("deny", run("Read", {"file_path": "~/.claude.json.backup"}), "Read a backup")
    expect("deny", run("Grep", {"pattern": "https", "path": HOME}), "Grep over home")
    expect("deny", run("Glob", {"pattern": "~/.claude*"}), "Glob for the config")


def test_a_heredoc_body_is_data_not_a_search_root():
    # 29 Sep: a PR description with "ok / stale / failed" fed through `cat <<'EOF'` was refused as a search of /
    body = "gh pr create --title t --body \"$(cat <<'EOF'\n- each chip is ok / stale / failed\n- see ~ for more\nEOF\n)\""
    expect("allow", bash(body), "a heredoc body naming / and ~")
    # the search-root rule still holds outside the body, and the body is still marker-scanned
    expect("deny", bash("cat <<'EOF' /\nhello\nEOF"), "cat of / beside a heredoc")
    expect("deny", bash("grep -r https ~ <<'EOF'\nx\nEOF"), "grep of ~ beside a heredoc")
    expect("deny", bash("cat <<'EOF'\nmcp-remote\nEOF"), "a marker inside the body")
    expect("deny", bash("cat <<'EOF'\n~/.claude.json\nEOF"), "the config named inside the body")
    # a quoted phrase is one argument: a commit message with " / " next to tail is fine; "/" on its own is not
    expect("allow", bash("git commit -qam \"fix: ok / stale / failed\" && git log -1 | tail -1"), "a quoted phrase")
    expect("deny", bash("cat \"/\""), "a quoted /")
    expect("deny", bash("grep -r https \"$HOME\" ~"), "~ unquoted beside a quoted variable")
    link = os.path.join(SCRATCH, "innocent-name")
    os.symlink(os.path.join(HOME, ".claude.json"), link)
    expect("deny", run("Read", {"file_path": link}), "Read through a symlink")
    expect("deny", bash(f"cat {link}"), "cat through a symlink")
    expect("allow", run("Read", {"file_path": os.path.join(ROOT, "scripts", "bookings", "lcs_mcp.py")}), "Read")
    expect("allow", run("Grep", {"pattern": "mcpServers", "path": os.path.join(ROOT, "scripts")}), "Grep repo")


def test_scripts_fed_on_stdin_are_vetted():
    script = write(os.path.join(SCRATCH, "a5", "notes.txt"), ATTACK)
    for cmd in (f"cat {script} | python3 -", f"python3 < {script}", f"{PY} - < {script}", f"cat {script} | sh",
                f"source {script}", f"bash {script}"):
        expect("deny", bash(cmd), cmd)
    pyc = write(os.path.join(SCRATCH, "a6", "x.pyc"), "\0\0compiled", "w")
    expect("deny", bash(f"python3 {pyc}"), "an untracked binary script")
    big = write(os.path.join(SCRATCH, "a7", "big.py"), "#" * ((1 << 20) + 10) + "\n")
    expect("deny", bash(f"python3 {big}"), "an untracked script over 1 MB")


def test_innocent_scratch_work_passes():
    script = write(os.path.join(SCRATCH, "ok", "sum.py"), INNOCENT)
    for cmd in (f"python3 {script}", f"cd {os.path.dirname(script)} && python3 sum.py", f"cat {script}",
                "python3 - <<'EOF'\nprint('hello, it\\'s fine')\nEOF"):
        expect("allow", bash(cmd), cmd)


def test_the_shell_capable_mcp_tools_are_checked_too():
    expect("deny", run("mcp__terminal__run_in_terminal", {"command": "npx mcp-remote https://x.invalid"}), "terminal")
    expect("deny", run("mcp__Control_your_Mac__osascript", {"script": 'do shell script "cat ~/.claude.json"'}), "osa")
    expect("allow", run("mcp__terminal__run_in_terminal", {"command": "git status"}), "terminal git status")


# --- file tools ----------------------------------------------------------------------------------------------

def test_writing_the_attack_is_denied_outside_the_allowlist():
    expect("deny", run("Write", {"file_path": os.path.join(SCRATCH, "w", "x.py"), "content": ATTACK}), "scratch")
    expect("deny", run("Write", {"file_path": "/tmp/x.py", "content": "import lcs_mcp\n"}), "lcs_mcp in /tmp")
    expect("allow", run("Write", {"file_path": os.path.join(SCRATCH, "w", "y.py"), "content": INNOCENT}), "ok")
    expect("deny", run("Write", {"file_path": os.path.join(ROOT, "scripts", "reports", "new.py"),
                                 "content": "METHOD = 'tools/call'\n"}), "a new repo script")
    expect("deny", run("Write", {"file_path": os.path.join(HOME, ".claude.json"), "content": "{}"}), "the config")
    expect("deny", run("NotebookEdit", {"notebook_path": os.path.join(SCRATCH, "n.ipynb"),
                                        "new_source": "!npx mcp-remote x"}), "notebook")


def test_edits_are_judged_on_the_resulting_file():
    f = write(os.path.join(SCRATCH, "w2", "part.py"), 'M = "tools/" + "XX"\n')
    expect("deny", run("Edit", {"file_path": f, "old_string": '" + "XX', "new_string": "call"}), "assembled")
    expect("deny", run("MultiEdit", {"file_path": f, "edits": [{"old_string": '" + "', "new_string": ""},
                                                               {"old_string": "XX", "new_string": "call"}]}), "multi")
    expect("allow", run("Edit", {"file_path": f, "old_string": "XX", "new_string": "YY"}), "harmless edit")


def test_the_allowlisted_files_and_prose_may_mention_mcp():
    for rel in ("scripts/bookings/lcs_mcp.py", "tests/test_lcs_mcp.py", ".claude/hooks/mcp_bypass_guard.py",
                "tests/test_mcp_bypass_guard.py", ".claude/settings.json", "CLAUDE.md", "logs/books-changes.md",
                "docs/superpowers/specs/2026-09-28-zoho-books-design.md", ".claude/agents/lcs-daily-pass.md",
                "MANUAL-ACTIONS-REQUIRED.md"):
        expect("allow", run("Edit", {"file_path": os.path.join(ROOT, rel), "old_string": "zzz-not-there",
                                     "new_string": "never read ~/.claude.json or start mcp-remote"}), rel)
    memory = os.path.join(HOME, ".claude", "projects", "-x", "memory", "note.md")
    expect("allow", run("Write", {"file_path": memory, "content": "Never read ~/.claude.json."}), "memory note")


# --- the legitimate commands --------------------------------------------------------------------------------

def allow_rule_commands():
    """Each Bash allow rule in .claude/settings.json as a concrete command (every * becomes X)."""
    rules = json.load(open(SETTINGS))["permissions"]["allow"]
    return [re.fullmatch(r"Bash\((.*)\)", r).group(1).replace("*", "X") for r in rules if r.startswith("Bash(")]


def prompt_commands():
    blocks, scripts = tpa.appendix_blocks(), tpa.script_paths()
    cmds = [c for b in blocks.values() for c in tpa.commands(b, scripts)]
    tasks = os.path.join(os.path.expanduser("~"), ".claude", "scheduled-tasks")  # the owner's machine only
    real_tasks = os.path.join(os.environ.get("HOME", ""), ".claude", "scheduled-tasks")
    for base in {tasks, real_tasks}:
        if os.path.isdir(base):
            for name in sorted(os.listdir(base)):
                path = os.path.join(base, name, "SKILL.md")
                if os.path.isfile(path):
                    cmds += tpa.commands(open(path, encoding="utf-8").read(), scripts)
    return sorted(set(cmds))


def test_every_allowlisted_and_prompt_command_passes():
    cmds = allow_rule_commands() + prompt_commands()
    assert len(cmds) >= 60, len(cmds)
    denied = [c for c in cmds if bash(c) != "allow"]
    assert not denied, "the bypass guard would stop these unattended commands:\n" + "\n".join(denied)


def test_everyday_repo_commands_pass():
    for cmd in (f"{PY} scripts/reports/cc_sync.py books", f"{PY} tests/test_lcs_mcp.py",
                f"{PY} tests/test_cc_pages2.py", f"{PY} tests/test_mcp_bypass_guard.py", "./build.sh",
                "python3 scripts/stage_site.py --list", f"{PY} validate_competitor_claims.py",
                "python3 validate_jsonld.py", "python3 -m http.server 8000", "git status",
                "git add scripts/bookings/lcs_mcp.py tests/test_lcs_mcp.py", "git diff --stat HEAD~1",
                "git log --oneline -5", f"{PY} scripts/bookings/check_payments.py --json 2>&1 | head -50",
                f"cd {ROOT} && {PY} scripts/bookings/assistant_io.py state",
                f"{PY} scripts/reports/cc_sync.py calendar-put '[{{\"start\": \"2026-10-01\", \"summary\": "
                f"\"Wedding (Barnes); rehearsal\", \"calendar\": \"London Choral Service\"}}]'",
                "grep -rn 'def main' scripts/bookings | head", "sed -n 1,40p docs/ROADMAP.md"):
        expect("allow", bash(cmd), cmd)


def test_tracked_files_with_markers_are_only_the_reviewed_ones():
    """Only CODE_OK and prose may mention MCP internals; anything else would be refused when run."""
    sys.path.insert(0, os.path.dirname(GUARD))
    import mcp_bypass_guard as g
    files = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], capture_output=True, check=True).stdout
    bad = []
    for rel in files.decode().split("\0"):
        path = os.path.join(ROOT, rel)
        if not rel or rel.startswith("graphify-out/") or rel in g.CODE_OK or g.prose(rel) or not os.path.isfile(path):
            continue
        data = open(path, "rb").read(1 << 20)
        if b"\0" not in data[:8192] and g.found(data.decode("utf-8", "replace")):
            bad.append(rel)
    assert not bad, bad


def test_a_tracked_script_with_markers_is_denied_unless_reviewed():
    repo = tempfile.mkdtemp(prefix="lcs-guard-repo-")
    git = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(git + ["init", "-q"], check=True)
    write(os.path.join(repo, "scripts", "evil.py"), ATTACK)
    write(os.path.join(repo, "scripts", "bookings", "lcs_mcp.py"), ATTACK)
    write(os.path.join(repo, "scripts", "fine.py"), INNOCENT)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-qm", "x"], check=True)
    expect("deny", bash("python3 scripts/evil.py", cwd=repo, project=repo), "tracked, not reviewed")
    expect("allow", bash("python3 scripts/bookings/lcs_mcp.py", cwd=repo, project=repo), "the reviewed client")
    expect("allow", bash("python3 scripts/fine.py", cwd=repo, project=repo), "tracked, no markers")
    expect("allow", bash("cat scripts/evil.py", cwd=repo, project=repo), "reading tracked code is fine")
    expect("deny", bash("cat scripts/evil.py | python3 -", cwd=repo, project=repo), "tracked code piped in")
    other = tempfile.mkdtemp(prefix="lcs-guard-other-")  # a second repo is not the project: untracked there
    subprocess.run(["git", "-C", other, "init", "-q"], check=True)
    fake = write(os.path.join(other, "scripts", "bookings", "lcs_mcp.py"), ATTACK)
    expect("deny", bash(f"python3 {fake}", cwd=ROOT), "an lcs_mcp.py lookalike in another repo")
    shutil.rmtree(repo)
    shutil.rmtree(other)


# --- plumbing -------------------------------------------------------------------------------------------------

def test_malformed_input_fails_closed():
    for stdin in ("not json", "[]", json.dumps({"tool_input": {"command": "ls"}}),
                  json.dumps({"tool_name": "Bash", "tool_input": ["ls"]}),
                  json.dumps({"tool_name": "Bash", "tool_input": {"command": 5}}),
                  json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/tmp/x"}}),
                  json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "/tmp/x", "old_string": "a"}}),
                  json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": 3})):
        expect("deny", raw(stdin)[0], stdin)
    decision, reason = raw(json.dumps({"tool_name": "Bash", "tool_input": {"command": "cat ~/.claude.json"}}))
    assert "stop and tell the owner" in reason and "guard" in reason, reason


def hook_commands(matcher):
    cfg = json.load(open(SETTINGS))
    return [h["command"] for e in cfg["hooks"]["PreToolUse"] if e["matcher"] == matcher for h in e["hooks"]]


def test_the_hook_is_wired_for_every_route():
    want = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/mcp_bypass_guard.py" || exit 2'
    for matcher in ("Bash", "Write|Edit|MultiEdit|NotebookEdit", "Read|Grep|Glob|NotebookRead"):
        assert hook_commands(matcher) == [want], (matcher, hook_commands(matcher))
    shells = [e["matcher"] for e in json.load(open(SETTINGS))["hooks"]["PreToolUse"]
              if "mcp__terminal__run_in_terminal" in e["matcher"]]
    assert len(shells) == 1 and hook_commands(shells[0]) == [want], shells
    sys.path.insert(0, os.path.dirname(GUARD))
    import mcp_bypass_guard as g
    assert set(shells[0].split("|")) == g.SHELL_TOOLS, shells


DENY = ["Read(~/.claude.json)", "Read(//Users/luca/.claude.json)", "Bash(*claude.json*)", "Bash(*mcp-remote*)",
        "Bash(python3 -)", "Bash(.venv/bin/python -)", "Bash(python3 - *)", "Bash(.venv/bin/python - *)"]


def test_the_deny_rules_exist_and_spare_the_legitimate_commands():
    deny, pats = tpa.deny_patterns()
    for rule in DENY:
        assert rule in deny, rule
    for cmd in ("cat ~/.claude.json", "npx -y mcp-remote x", "python3 -", f"{PY} -", "python3 - <<'EOF'",
                f"{PY} - < /tmp/x.py"):
        assert any(p.fullmatch(cmd) for _, p in pats), cmd
    caught = [c for c in allow_rule_commands() + prompt_commands() if any(p.fullmatch(c) for _, p in pats)]
    assert not caught, caught
    for cmd in ("python3 -c 'print(1)'", "python3 -m http.server 8000", f"{PY} -m pytest", "python3 scripts/x.py"):
        assert not any(p.fullmatch(cmd) for _, p in pats), cmd


if __name__ == "__main__":
    failures = 0
    try:
        for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as ex:  # an error is a failure too
                failures += 1
                print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    finally:
        shutil.rmtree(HOME, ignore_errors=True)
        shutil.rmtree(SCRATCH, ignore_errors=True)
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
