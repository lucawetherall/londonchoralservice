#!/usr/bin/env python3
"""PreToolUse guard against reaching Zoho Books or Zoho Mail around the MCP guard hooks.

On 28 Sep 2026 a session that zoho_books_guard.py had refused wrote a script in its scratchpad that read
the server command and secret URL from ~/.claude.json, started the Books MCP server itself and sent a raw
JSON-RPC tool call over stdin. The other guards match only mcp__zoho-* tool calls, so that route was
unguarded. This hook closes it. Wired in .claude/settings.json for:

- Bash (and the shell-capable MCP tools in SHELL_TOOLS: every string in their input is treated as a
  command). Denied when:
  - the command text holds a marker (MARKERS: the MCP config files, mcp-remote, the MCP protocol, the Zoho
    MCP host names, `claude mcp`, the MCP token cache), also after quotes and backslashes are dropped
    (`mcp-re''mote`), or imports lcs_mcp (the read client) from inline code;
  - any file the command names (paths, globs, `NAME=path`, `< file`) is MCP configuration, or is an
    untracked text file holding a marker;
  - a script it runs (the first existing file after an interpreter, a file run directly, `source`, a file
    fed to an interpreter on stdin) is untracked and binary, over 1 MB or holds a marker, or has an
    untracked neighbour in its folder that holds one; or is tracked, holds a marker and is not in
    CODE_OK (lcs_mcp.py, the one legitimate MCP client, its tests and this guard's own files);
  - an interpreter runs inline code, a module or stdin in a folder outside the repo whose files hold a
    marker;
  - a search or copy (grep, find, cp, tar…) is rooted at a folder that holds MCP configuration (/, the
    home folder, ~/Library…).
  Tracked files are reviewed code: `git ls-files` in the project repo (or one of its worktrees) decides.
- Write, Edit, MultiEdit and NotebookEdit: denied when the file would end up holding a marker, unless it
  is in CODE_OK or is prose (docs/**.md, CLAUDE.md, MANUAL-ACTIONS-REQUIRED.md, logs/*.md,
  .claude/agents/*.md, Claude's own memory notes). Outside the repo (scratchpad, /tmp) naming lcs_mcp
  counts as a marker too. MCP configuration itself is never written.
- Read, Grep and Glob: denied on MCP configuration (~/.claude.json and its backups, .mcp.json,
  claude_desktop_config.json, ~/.mcp-auth) and on a search rooted at a folder that holds it.

It fails closed: malformed input or any internal error denies the call. It can't see through deliberate
obfuscation (strings assembled at run time, encoded payloads); the rule in CLAUDE.md covers intent.
"""
import glob
import itertools
import json
import os
import re
import shlex
import stat
import subprocess
import sys

P = "MCP bypass guard: "
TAIL = (" Zoho Books and Zoho Mail are reached only through their MCP tools under the guard hooks (and "
        "lcs_mcp.py's read-only client), never by starting a server, reading the MCP config or sending "
        "protocol messages yourself. If a guard refuses a call, stop and tell the owner what you were trying "
        "to do. (To read code that mentions these words, use the Read or Grep tool.)")

# Case-insensitive. Generic on purpose: the Zoho MCP URLs are secrets and are never written down here.
MARKERS = [
    (r"claude\.json", "the Claude Code config file (~/.claude.json)"),
    (r"\.claude[*?\[]|claude\.js[a-z]*[*?\[]", "a wildcard for the Claude Code config file"),
    (r"claude_desktop_config", "the Claude Desktop MCP config"),
    (r"(?<![a-z0-9_])\.mcp\.json", "an MCP config file (.mcp.json)"),
    (r"\.mcp-auth", "the MCP token cache (~/.mcp-auth)"),
    (r"\bclaude\s+mcp\b", "the `claude mcp` command"),
    (r"mcp-remote", "the MCP proxy (mcp-remote)"),
    (r"mcpservers", "an MCP server list (mcpServers)"),
    (r"modelcontextprotocol", "the MCP SDK"),
    (r"jsonrpc", "JSON-RPC"),
    (r"tools/call", "an MCP tool call"),
    (r"zohomcp", "a Zoho MCP host"),
    (r"(?<![a-z0-9_])mcp\.zoho", "a Zoho MCP host"),
]
MARKERS = [(re.compile(rx, re.I), label) for rx, label in MARKERS]
# lcs_mcp.py, the read client, may be named in a command (git add, a test run); importing it from inline
# code, or naming it at all in an untracked file, counts as a marker.
CLIENT = {
    "cmd": (re.compile(r"\b(import|from)\s+lcs_mcp\b|lcs_mcp['\"]|['\"]lcs_mcp", re.I), "the lcs_mcp client"),
    "file": (re.compile(r"(?<![a-z0-9_])lcs_mcp(?![a-z0-9_])", re.I), "the lcs_mcp client"),
}

# Tracked files that may hold markers (and may be written with them).
CODE_OK = {
    "scripts/bookings/lcs_mcp.py",          # the one legitimate MCP client (read-only allowlist)
    "tests/test_lcs_mcp.py",
    ".claude/hooks/mcp_bypass_guard.py",
    "tests/test_mcp_bypass_guard.py",
    "command_centre/sources.py",            # reads MCP server *names* for a health check
    "tests/test_cc_pages2.py",              # its test (a fake config in a temporary HOME)
    "tests/test_cc_sync.py",                # points lcs_mcp at a missing config
    ".claude/settings.json",                # the deny rules name these files
}
PROTECTED = re.compile(r"^(\.claude\.json.*|claude_desktop_config\.json|\.mcp\.json|\.mcp-auth)$", re.I)
PROTECTED_TEXT = re.compile(r"claude\.json|claude_desktop_config|(?<![a-z0-9_])\.mcp\.json|\.mcp-auth|"
                            r"\.claude[*?\[]|claude\.js[a-z]*[*?\[]", re.I)

INTERP = re.compile(r"^((python|pypy)[0-9.]*w?|ipython[0-9]*|node(js)?|deno|bunx?|tsx|ts-node|npx|uvx?|pipx|"
                    r"pytest|bash|sh|zsh|dash|ksh|fish|t?csh|ruby|perl[0-9.]*|php[0-9.]*|osascript|"
                    r"lua(jit)?|rscript|swift|julia|tclsh[0-9.]*|expect|pwsh)$", re.I)
SHELLS = re.compile(r"^(bash|sh|zsh|dash|ksh|fish|t?csh)$", re.I)
WRAPPERS = {"env", "sudo", "nohup", "nice", "time", "timeout", "gtimeout", "caffeinate", "exec", "command",
            "stdbuf", "arch", "xargs", "builtin", "doas"}
INLINE = re.compile(r"^(-[a-z]*[ce]|--eval|--print|--command|-r)$", re.I)
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SEPARATORS = {"|", "||", "&&", ";", "&", "(", ")", ";;", "|&", ";&"}
# A search or copy rooted at a folder that holds MCP configuration is refused.
SEARCHERS = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "find", "fd", "tar", "zip", "rsync", "cp", "ditto",
             "strings", "xxd", "od", "hexdump", "awk", "sed", "jq", "cat", "head", "tail", "less", "more"}
CODE_EXT = {".py", ".pyw", ".pth", ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".sh", ".bash", ".zsh", ".rb",
            ".pl", ".php", ".json", ".applescript", ".command", ".lua", ".r", ".swift", ".toml", ".cfg", ".ini",
            ".txt", ".md", ""}
SHELL_TOOLS = {"mcp__terminal__run_in_terminal", "mcp__Control_your_Mac__osascript",
               "mcp__plugin_playwright_playwright__browser_run_code_unsafe"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read", "Grep", "Glob", "NotebookRead"}
CAP = 1 << 20            # bytes read from any one file
DIR_FILES = 300          # neighbour files vetted around an untracked script
DIR_BYTES = 32 << 20
GLOB_MAX = 50


class Deny(Exception):
    pass


def found(text, client=None):
    """The label of the first marker in `text` (also with quotes and backslashes dropped), else None.
    `client` ("cmd" or "file") adds the lcs_mcp check for command text or for an untracked file."""
    if not text:
        return None
    for t in (text, re.sub(r"[\"'\\`]", "", text)):
        for rx, label in MARKERS + ([CLIENT[client]] if client else []):
            if rx.search(t):
                return label
    return None


# --- files and the repo ------------------------------------------------------------------------------------

def _git(args, cwd):
    p = subprocess.run(["git", "-C", cwd] + args, capture_output=True, timeout=5)
    return p.stdout.decode("utf-8", "surrogateescape") if p.returncode == 0 else None


class Repo:
    """The project repo: its main checkout and worktrees share one git common dir."""

    def __init__(self, project):
        self.common = self._common(project)
        self._roots, self._tracked = {}, {}

    @staticmethod
    def _common(d):
        out = _git(["rev-parse", "--path-format=absolute", "--git-common-dir"], d) if os.path.isdir(d) else None
        return os.path.realpath(out.strip()) if out and out.strip() else None

    def locate(self, path):
        """(root, rel) when `path` is inside the project repo or one of its worktrees, else None."""
        if not self.common:
            return None
        d = path if os.path.isdir(path) else os.path.dirname(path)
        while d and not os.path.exists(d):
            d = os.path.dirname(d)
        while d:
            if os.path.exists(os.path.join(d, ".git")):
                if d not in self._roots:
                    self._roots[d] = self._common(d) == self.common
                if not self._roots[d]:
                    return None
                rel = os.path.relpath(path, d)
                return None if rel.startswith("..") else (d, rel.replace(os.sep, "/"))
            parent = os.path.dirname(d)
            if parent == d:
                return None
            d = parent
        return None

    def tracked(self, loc):
        root, rel = loc
        if root not in self._tracked:
            out = _git(["ls-files", "-z"], root)
            self._tracked[root] = set(out.split("\0")) if out else set()
        return rel in self._tracked[root]


def read_head(path, n=CAP):
    with open(path, "rb") as f:
        return f.read(n)


def binary(data):
    return b"\0" in data[:8192]


def regular(path):
    try:
        return stat.S_ISREG(os.stat(path).st_mode)
    except OSError:
        return False


def resolve(word, cwds):
    """Existing paths a command word may name (expanded, globbed, relative to each cwd), as real paths."""
    w = os.path.expandvars(os.path.expanduser(word))
    bases = [w] if os.path.isabs(w) else [os.path.join(c, w) for c in cwds]
    out = []
    for b in bases:
        hits = list(itertools.islice(glob.iglob(b), GLOB_MAX)) if re.search(r"[*?\[]", b) else [b]
        out += [os.path.realpath(h) for h in hits if os.path.lexists(h)]
    return list(dict.fromkeys(out))


def config_roots():
    """Folders that hold MCP configuration, directly or a level or two down."""
    home = os.path.realpath(os.path.expanduser("~"))
    return {"/", os.path.dirname(home), home, os.path.join(home, "Library"),
            os.path.join(home, "Library", "Application Support"),
            os.path.join(home, "Library", "Application Support", "Claude"), os.path.join(home, ".claude")}


def protected(path):
    if PROTECTED.match(os.path.basename(path)):
        raise Deny(f"{P}{os.path.basename(path)} is MCP configuration and is off limits.")


# --- commands ----------------------------------------------------------------------------------------------

def strip_heredocs(cmd):
    """The command without heredoc bodies (the whole text is marker-scanned separately)."""
    lines, out, i = cmd.split("\n"), [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        for m in re.finditer(r"(?<!<)<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", line):
            while i < len(lines) and lines[i].strip() != m.group(2):
                i += 1
            i += 1
    return "\n".join(out)


def crude(body):
    return re.findall(r"\|\||&&|[|;&()]|[0-9]*[<>]+&?|[^\s'\"|;&()<>]+", body)


def token_lists(cmd):
    """The command's tokens twice: shell-parsed without heredoc bodies, and crudely split with them (so a
    fake heredoc marker can't hide the lines after it)."""
    out = []
    for body, parse in ((strip_heredocs(cmd), True), (cmd, False)):
        body = re.sub(r"\n", " ; ", re.sub(r"\\\n", " ", body))
        if parse:
            try:
                lex = shlex.shlex(body, posix=True, punctuation_chars=True)
                lex.whitespace_split = True
                lex.commenters = ""
                out.append(list(lex))
                continue
            except ValueError:
                pass
        out.append(crude(body))
    return out


def segments(toks):
    segs, cur = [], []
    for t in toks:
        if t in SEPARATORS or (t and set(t) <= set("|&;()")):
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs


def words(text):
    """Every path-like piece of `text`, for the file checks (crude on purpose: quoting can't hide a path)."""
    out = []
    for w in re.findall(r"[^\s'\"`<>|;&(){}]+", text):
        out.append(w)
        out += [p for p in re.split(r"[=:,]", w) if p and p != w]
    return list(dict.fromkeys(out))


class Command:
    def __init__(self, repo, cwd):
        self.repo, self.cwds = repo, [cwd]
        self.scripts, self.inline_cwds = [], []
        self.stdin_interp = False
        self.dirs_vetted, self.heads = set(), set()

    def analyse(self, cmd, depth=0):
        label = found(cmd, client="cmd")
        if label:
            raise Deny(f"{P}the command mentions {label}.")
        if depth > 3:
            return
        for toks in token_lists(cmd):
            for seg in segments(toks):
                self.segment(seg, depth)

    def segment(self, seg, depth):
        i = 0
        while i < len(seg):
            t, base = seg[i], os.path.basename(seg[i]).lower()
            if ASSIGN.match(t):
                i += 1
            elif base in WRAPPERS:
                i += 1
                while i < len(seg) and (seg[i].startswith("-") or ASSIGN.match(seg[i])
                                        or re.fullmatch(r"[0-9.]+[smhd]?", seg[i])):
                    i += 1
            else:
                break
        if i >= len(seg):
            return
        head, rest = seg[i], seg[i + 1:]
        base = os.path.basename(head).lower()
        self.heads.add(base)
        redirect = [("<" in t or ">" in t) for t in rest]
        stdin_files = [rest[j + 1] for j, t in enumerate(rest[:-1]) if "<" in t and "<<" not in t]
        args = [t for j, t in enumerate(rest) if not redirect[j] and not (j and redirect[j - 1])]
        if base == "cd" and args:
            self.cwds += [p for p in resolve(args[0], self.cwds[:1]) if os.path.isdir(p)]
            return
        if base == "eval":
            self.analyse(" ".join(args), depth + 1)
            return
        if base in ("source", "."):
            self.scripts += [p for w in args[:1] for p in resolve(w, self.cwds) if regular(p)]
            return
        if INTERP.match(base):
            script, inline = None, False
            for j, w in enumerate(args):
                if INLINE.match(w) and j + 1 < len(args):
                    inline, code = True, args[j + 1]
                    if SHELLS.match(base):
                        self.analyse(code, depth + 1)
                    hits = [p for p in resolve(code, self.cwds) if regular(p)]  # `-E x.py`: a flag, then a file
                    script = hits[0] if hits else None
                    break
                if w == "-m":
                    inline = True
                    break
                cand = w.split("=", 1)[1] if w.startswith("-") and "=" in w else (None if w.startswith("-") else w)
                hits = [p for p in resolve(cand, self.cwds) if regular(p)] if cand else []
                if hits:
                    script = hits[0]
                    break
            if script:
                self.scripts.append(script)
            elif inline:
                self.inline_cwds += self.cwds
            else:  # reads its program from stdin
                self.stdin_interp = True
                self.inline_cwds += self.cwds
                self.scripts += [p for w in stdin_files for p in resolve(w, self.cwds) if regular(p)]
            return
        if "/" in head:
            self.scripts += [p for p in resolve(head, self.cwds) if regular(p)]


def vet_script(path, repo, cmd):
    protected(path)
    loc = repo.locate(path)
    if loc and repo.tracked(loc):
        if loc[1] in CODE_OK:
            return
        label = found(read_head(path).decode("utf-8", "replace"))
        if label:
            raise Deny(f"{P}{loc[1]} mentions {label}; only lcs_mcp.py (and its tests) may talk to MCP servers.")
        return
    shown = loc[1] if loc else path
    data = read_head(path, CAP + 1)
    if len(data) > CAP:
        raise Deny(f"{P}{shown} is untracked and too large to vet.")
    if binary(data):
        raise Deny(f"{P}{shown} is an untracked binary or compiled file, which can't be vetted.")
    label = found(data.decode("utf-8", "replace"), client="file")
    if label:
        raise Deny(f"{P}{shown} mentions {label}.")
    if not loc:
        vet_dir(os.path.dirname(path), repo, cmd)


def vet_dir(d, repo, cmd):
    """Untracked code in the folder a script or inline code runs from (a helper it imports or runs), two
    levels deep."""
    if d in cmd.dirs_vetted or repo.locate(d):
        return
    cmd.dirs_vetted.add(d)
    files, budget = 0, DIR_BYTES
    for root, dirs, names in os.walk(d):
        rel = os.path.relpath(root, d)
        if rel != "." and rel.count(os.sep) >= 1:
            dirs[:] = []
        for name in dirs + names:
            label = found(name)
            if label:
                raise Deny(f"{P}{os.path.join(root, name)}, in the folder the code runs from, is named after "
                           f"{label}.")
        for name in names:
            path = os.path.join(root, name)
            if os.path.splitext(name)[1].lower() not in CODE_EXT or not regular(path):
                continue
            files += 1
            if files > DIR_FILES or budget <= 0:
                raise Deny(f"{P}the folder {d} has too many files to vet; run the script from its own small "
                           "folder in the scratchpad.")
            data = read_head(path)
            budget -= len(data)
            if not binary(data):
                label = found(data.decode("utf-8", "replace"), client="file")
                if label:
                    raise Deny(f"{P}{path}, in the folder the code runs from, mentions {label}.")


def check_command(text, repo, cwd):
    cmd = Command(repo, cwd)
    cmd.analyse(text)
    scripts = list(cmd.scripts)
    seen, roots = set(), config_roots()
    searching = bool(cmd.heads & SEARCHERS)
    # A heredoc body is data a command reads on stdin, not paths it opens: "ok / stale" in a PR description fed
    # through `cat <<'EOF'` is not a search of "/". The body is still marker-scanned (analyse) and every word in
    # it still goes through protected() and the file checks below; only the search-root rule skips it.
    outside = set(words(strip_heredocs(text)))
    for w in words(text):
        if INTERP.match(os.path.basename(w)):
            continue
        for p in resolve(w, cmd.cwds):
            protected(p)
            if searching and p in roots and w in outside:
                raise Deny(f"{P}searching or copying {p} would take in MCP configuration; name a project "
                           "folder instead.")
            if p in seen or not regular(p):
                continue
            seen.add(p)
            if cmd.stdin_interp:  # anything named may be the program an interpreter reads on stdin
                scripts.append(p)
                continue
            loc = repo.locate(p)
            if loc and repo.tracked(loc):
                continue
            data = read_head(p)
            if not binary(data):
                label = found(data.decode("utf-8", "replace"), client="file")
                if label:
                    raise Deny(f"{P}{loc[1] if loc else p} mentions {label}.")
    for p in dict.fromkeys(scripts):
        vet_script(p, repo, cmd)
    for d in dict.fromkeys(cmd.inline_cwds):
        vet_dir(d, repo, cmd)


# --- file tools --------------------------------------------------------------------------------------------

def prose(rel):
    return (rel in ("CLAUDE.md", "MANUAL-ACTIONS-REQUIRED.md")
            or (rel.startswith("docs/") and rel.endswith(".md"))
            or re.fullmatch(r"logs/[^/]+\.md", rel) is not None
            or re.fullmatch(r"\.claude/agents/[^/]+\.md", rel) is not None)


def memory_note(path):
    """Claude's own memory notes (~/.claude/projects/<project>/memory/*.md): prose, never run."""
    base = os.path.join(os.path.realpath(os.path.expanduser("~")), ".claude", "projects")
    return re.fullmatch(r"[^/]+/memory/[^/]+\.md", os.path.relpath(path, base)) is not None


def _str(ti, key, required=True):
    v = ti.get(key)
    if v is None and not required:
        return ""
    if not isinstance(v, str):
        raise ValueError(f"{key} must be a string")
    return v


def _abs(path, cwd):
    path = os.path.expanduser(path)
    return os.path.realpath(path if os.path.isabs(path) else os.path.join(cwd, path))


def _apply(text, e):
    old, new = _str(e, "old_string"), _str(e, "new_string")
    return new, (text.replace(old, new) if e.get("replace_all") is True else text.replace(old, new, 1))


def check_write(tool, ti, repo, cwd):
    path = _abs(_str(ti, "notebook_path" if tool == "NotebookEdit" else "file_path"), cwd)
    protected(path)
    current = ""
    if tool in ("Edit", "MultiEdit") and regular(path) and os.path.getsize(path) <= 8 * CAP:
        with open(path, encoding="utf-8", errors="replace") as f:
            current = f.read()
    if tool == "Write":
        texts = [_str(ti, "content")]
    elif tool == "Edit":
        texts = list(_apply(current, ti))
    elif tool == "MultiEdit":
        edits = ti.get("edits")
        if not isinstance(edits, list):
            raise ValueError("edits must be a list")
        texts = []
        for e in edits:
            if not isinstance(e, dict):
                raise ValueError("each edit must be an object")
            new, current = _apply(current, e)
            texts.append(new)
        texts.append(current)
    else:
        texts = [_str(ti, "new_source", required=False)]
    loc = repo.locate(path)
    if loc and (loc[1] in CODE_OK or prose(loc[1])):
        return
    if not loc and memory_note(path):
        return
    for t in texts:
        label = found(t, client=None if loc else "file")
        if label:
            raise Deny(f"{P}writing {label} into {loc[1] if loc else path} isn't allowed.")


def check_read(tool, ti, cwd):
    keys = ("file_path", "notebook_path", "path", "glob") + (("pattern",) if tool == "Glob" else ())
    for key in keys:
        v = ti.get(key)
        if isinstance(v, str) and PROTECTED_TEXT.search(v):
            raise Deny(f"{P}that names MCP configuration, which is off limits.")
    roots = config_roots()
    for key in ("file_path", "notebook_path", "path"):
        v = ti.get(key)
        if isinstance(v, str) and v:
            p = _abs(v, cwd)
            protected(p)
            if key == "path" and p in roots:
                raise Deny(f"{P}searching {p} would take in MCP configuration; search a project folder instead.")


# --- entry point -------------------------------------------------------------------------------------------

def decide(event):
    """None to let the call through (normal permission rules apply), else the reason it is denied. Raises on
    malformed input (main() turns that into a deny)."""
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    tool, ti = event.get("tool_name"), event.get("tool_input")
    if not isinstance(tool, str) or not tool:
        raise ValueError("missing or invalid tool_name")
    if not isinstance(ti, dict):
        raise ValueError("tool_input must be an object")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    cwd = event.get("cwd") or project
    if not isinstance(cwd, str):
        raise ValueError("cwd must be a string")
    repo = Repo(project)
    try:
        if tool == "Bash":
            check_command(_str(ti, "command"), repo, cwd)
        elif tool in SHELL_TOOLS:
            stack = [ti]
            while stack:
                v = stack.pop()
                if isinstance(v, dict):
                    stack += list(v.values())
                elif isinstance(v, list):
                    stack += v
                elif isinstance(v, str):
                    check_command(v, repo, cwd)
        elif tool in WRITE_TOOLS:
            check_write(tool, ti, repo, cwd)
        elif tool in READ_TOOLS:
            check_read(tool, ti, cwd)
    except Deny as e:
        return str(e) + TAIL
    return None


def main():
    try:
        reason = decide(json.load(sys.stdin))
    except Exception as e:  # fail closed
        reason = f"{P}error ({type(e).__name__}); call blocked." + TAIL
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
