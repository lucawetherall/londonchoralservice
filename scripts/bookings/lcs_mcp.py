#!/usr/bin/env python3
"""A tiny, READ-ONLY MCP stdio client for the bookings scripts.

It reads a server's command and args from ~/.claude.json (the project entry for
this repo, falling back to the main checkout's entry, then the user-level
mcpServers), spawns it, runs initialize -> notifications/initialized ->
tools/call, returns the text content and kills the process.

- Only the (server, tool) pairs in ALLOWED can be called, plus the Zoho Books
  servers (zoho-books, zoho-books-invoices) with a tool named in the Books guard
  hook's READ_ALLOW (.claude/hooks/zoho_books_guard.py, loaded by path, so the
  hook's read list is the only list). Anything else, every Books write tool
  included, is refused before a process is started. If the hook can't be
  loaded, no Books tool is allowed (fail closed).
- The server command and args hold a secret URL. They are never printed, and
  no exception raised here carries them: errors name the server only, and any
  text passed on from the server is scrubbed of URLs and of the args.
- The server's stderr is discarded (mcp-remote logs the URL there).
- A bare command (the config's `npx`) not on the child's PATH is looked for in /opt/homebrew/bin, /usr/local/bin
  and nvm's folders (launchd gives the Command Centre a bare PATH); none found raises CommandNotFound, an
  McpError that names the server only.
- The server runs in its own session and process group; close() kills the whole group (npx's children
  too), and never waits on a pipe a stray grandchild might still hold open. A single reply is capped at
  MAX_REPLY characters.
"""

import json
import os
import queue
import re
import shutil
import signal
import subprocess
import threading
import time
import importlib.util
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAIN_CHECKOUT = Path("/Users/luca/Documents/GitHub/londonchoralservice")
CLAUDE_JSON = Path(os.environ.get("LCS_CLAUDE_JSON", Path.home() / ".claude.json"))
TIMEOUT = 90  # seconds, for the whole exchange
MAX_REPLY = 60 << 20  # characters in one reply line (a raw email with its attachments, base64)
ALLOWED = {("zoho-mail", "ZohoMail_getOriginalMessage")}
BOOKS_SERVERS = frozenset({"zoho-books", "zoho-books-invoices"})
BOOKS_GUARD = REPO / ".claude" / "hooks" / "zoho_books_guard.py"
ZOHO_ACCOUNT = "6133510000000008002"
PROTOCOL = "2025-06-18"


class McpError(Exception):
    """Raised with the server name only: never the command, args or URL."""


class CommandNotFound(McpError):
    """The server's command is a bare name found neither on PATH nor in the usual Node folders (NODE_DIRS)."""


NODE_DIRS = ("/opt/homebrew/bin", "/usr/local/bin")  # Homebrew on Apple silicon, then Intel (and the Node installer)
NVM_GLOB = ".nvm/versions/node/*/bin"  # under HOME: each nvm-installed Node, newest version first


def _version_key(path):
    """Sort key for an nvm folder ("…/node/v20.11.1/bin"): the version as numbers, unreadable ones last."""
    name = Path(path).parent.name.lstrip("v")
    try:
        return tuple(int(x) for x in name.split("."))
    except ValueError:
        return ()


def fallback_dirs(home=None):
    """The folders searched for a bare command that isn't on PATH: NODE_DIRS, then nvm's, newest first."""
    home = Path(home) if home is not None else Path.home()
    nvm = sorted((str(p) for p in home.glob(NVM_GLOB) if p.is_dir()), key=_version_key, reverse=True)
    return [*NODE_DIRS, *nvm]


def resolve_command(name, command, env_path, dirs=None, which=shutil.which):
    """(the command to run, the folder to put first on the child's PATH or None). A command with a "/" is used
    as it is; a bare name is looked up on `env_path` (the PATH the child gets), then in `dirs` (fallback_dirs()).
    When found in a fallback folder, that folder goes first on the child's PATH too, so a `#!/usr/bin/env node`
    script such as npx finds node beside it. Raises CommandNotFound naming the server only (launchd's bare PATH
    has no Node: command_centre/install.sh adds its folders)."""
    if "/" in command:
        return command, None
    if which(command, path=env_path):
        return command, None
    for d in (fallback_dirs() if dirs is None else dirs):
        found = which(command, path=d)
        if found:
            return found, d
    raise CommandNotFound(f"{name}: the MCP server's command isn't on PATH or in the usual Node folders "
                          f"(re-run command_centre/install.sh, or check the MCP config)")


def books_read_allow(path=BOOKS_GUARD):
    """The Books guard's READ_ALLOW, imported from the hook file by path, minus any name that is also one of its
    write tools; an empty set when the hook can't be loaded (fail closed)."""
    try:
        spec = importlib.util.spec_from_file_location("_lcs_zoho_books_guard", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        names = set(mod.READ_ALLOW)
        if not all(isinstance(n, str) and n for n in names):
            return frozenset()
        return frozenset(names - set(getattr(mod, "WRITE_TOOLS", None) or {}))
    except Exception:
        return frozenset()


BOOKS_READ = books_read_allow()


def is_allowed(server, tool):
    """True for a Mail pair in ALLOWED, and for a Books server with a tool on the Books guard's read list."""
    return (server, tool) in ALLOWED or (server in BOOKS_SERVERS and tool in BOOKS_READ)


_TOO_LARGE = object()  # queued by the reader when one reply line exceeds MAX_REPLY


def _main_checkout(repo):
    """The main checkout for a worktree path (…/<repo>/.claude/worktrees/<name>), else the path itself."""
    parts = repo.parts
    for i in range(len(parts) - 2):
        if parts[i] == ".claude" and parts[i + 1] == "worktrees":
            return Path(*parts[:i])
    return repo


def server_config(name, config_path=None, repo=None):
    """(command, args, env) for a stdio server named in ~/.claude.json. Raises McpError(name) if absent."""
    path = Path(config_path or CLAUDE_JSON)
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        raise McpError(f"{name}: could not read the MCP settings") from None
    projects = data.get("projects") or {}
    repo = Path(repo or REPO)
    entry = None
    for key in (str(repo), str(_main_checkout(repo)), str(MAIN_CHECKOUT)):
        entry = ((projects.get(key) or {}).get("mcpServers") or {}).get(name)
        if entry:
            break
    entry = entry or (data.get("mcpServers") or {}).get(name)
    if not entry:
        raise McpError(f"{name}: no such MCP server configured")
    if entry.get("type") not in (None, "stdio") or not entry.get("command"):
        raise McpError(f"{name}: not a stdio MCP server")
    return entry["command"], [str(a) for a in entry.get("args") or []], dict(entry.get("env") or {})


def _secret_forms(secret):
    """The secret, and for a URL every piece of it that could turn up on its own in an error: host, path,
    path segments and query values of 8+ characters, and the percent-encoded URL."""
    s = str(secret)
    forms = {s}
    try:
        u = urllib.parse.urlsplit(s)
    except ValueError:
        return forms
    if u.scheme and u.netloc:
        forms |= {u.netloc, u.hostname or "", u.path, u.netloc + u.path, urllib.parse.quote(s, safe="")}
        forms |= {seg for seg in u.path.split("/") if len(seg) >= 8}
        forms |= {v for _, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True) if len(v) >= 8}
    return forms


def _scrub(text, secrets):
    text = re.sub(r"(?i)\b(?:https?|wss?)://\S+", "<url>", str(text))
    forms = set()
    for s in secrets:
        if s is not None and s != "":
            forms |= _secret_forms(s)
    for f in sorted(forms, key=len, reverse=True):  # longest first, so a URL goes before its host
        if len(f) >= 6:
            text = text.replace(f, "<redacted>")
    return text[:300]


class _Session:
    def __init__(self, name, command, args, env, timeout, popen):
        self.name, self._secrets = name, [str(x) for x in (command, *args, *env.values())]
        self._deadline = None
        self._timeout = timeout
        full_env = {**os.environ, **{k: str(v) for k, v in env.items()}}
        command, first = resolve_command(name, command, full_env.get("PATH", os.defpath))
        if first:
            full_env["PATH"] = os.pathsep.join(p for p in (first, full_env.get("PATH", "")) if p)
        try:
            # its own session: close() can kill the whole process group, npx's children included
            self.proc = popen([command, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, env=full_env, text=True, bufsize=1,
                              encoding="utf-8", errors="replace", start_new_session=True)
        except OSError:
            raise McpError(f"{name}: could not start the MCP server") from None
        self._lines = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()
        self._next_id = 0

    def _pump(self):
        """Reads reply lines on its own thread, and alone closes stdout: a grandchild that escaped the kill
        may hold the pipe open, and closing it from close() would block on this thread's read."""
        out = self.proc.stdout
        try:
            while True:
                line = out.readline(MAX_REPLY + 1)
                if not line:
                    break
                if len(line) > MAX_REPLY:
                    self._lines.put(_TOO_LARGE)
                    return
                self._lines.put(line)
        except (OSError, ValueError):
            pass
        finally:
            try:
                out.close()
            except Exception:
                pass
        self._lines.put(None)

    def _send(self, msg):
        try:
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
        except (OSError, ValueError):
            raise McpError(f"{self.name}: the MCP server closed the connection") from None

    def request(self, method, params, deadline):
        self._next_id += 1
        rid = self._next_id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise McpError(f"{self.name}: timed out after {self._timeout}s")
            try:
                line = self._lines.get(timeout=left)
            except queue.Empty:
                raise McpError(f"{self.name}: timed out after {self._timeout}s") from None
            if line is None:
                raise McpError(f"{self.name}: the MCP server exited before answering")
            if line is _TOO_LARGE:
                raise McpError(f"{self.name}: the MCP server's reply was too large")
            try:
                msg = json.loads(line)
            except ValueError:
                continue  # a stray log line on stdout
            if not isinstance(msg, dict):
                continue
            if "method" in msg and "id" in msg:  # a request from the server (ping, roots/list …)
                if msg["method"] == "ping":
                    self._send({"jsonrpc": "2.0", "id": msg["id"], "result": {}})
                else:
                    self._send({"jsonrpc": "2.0", "id": msg["id"],
                                "error": {"code": -32601, "message": "method not found"}})
                continue
            if msg.get("id") != rid:
                continue  # a notification or a stale answer
            if "error" in msg:
                err = msg["error"] or {}
                raise McpError(f"{self.name}: {method} failed ({err.get('code')}: "
                               f"{_scrub(err.get('message', ''), self._secrets)})")
            return msg.get("result") or {}

    def notify(self, method):
        self._send({"jsonrpc": "2.0", "method": method})

    def close(self):
        try:
            os.killpg(self.proc.pid, signal.SIGKILL)  # the whole group: npx and the server it started
        except ProcessLookupError:
            pass
        except OSError:  # a popen that ignored start_new_session (EPERM): at least the process itself
            try:
                self.proc.kill()
            except OSError:
                pass
        try:
            self.proc.wait(timeout=5)
        except Exception:
            pass
        try:
            self.proc.stdin and self.proc.stdin.close()
        except Exception:
            pass


def _session(server, config_path, timeout, popen, fn):
    command, args, env = server_config(server, config_path)
    deadline = time.monotonic() + timeout
    s = _Session(server, command, args, env, timeout, popen)
    try:
        s.request("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                                 "clientInfo": {"name": "lcs-bookings", "version": "1"}}, deadline)
        s.notify("notifications/initialized")
        return fn(s, deadline)
    finally:
        s.close()


def call_tool(server, tool, arguments, config_path=None, timeout=TIMEOUT, popen=subprocess.Popen):
    """Text content of one allowed, read-only tool call. Raises McpError (server name only) on any failure."""
    if not is_allowed(server, tool):
        raise McpError(f"{server}: tool {tool} is not allowed")

    def run(s, deadline):
        result = s.request("tools/call", {"name": tool, "arguments": arguments}, deadline)
        text = "".join(c.get("text", "") for c in result.get("content") or [] if c.get("type") == "text")
        if result.get("isError"):
            raise McpError(f"{server}: {tool} returned an error: {_scrub(text, s._secrets)}")
        return text

    return _session(server, config_path, timeout, popen, run)


def list_tools(server, config_path=None, timeout=TIMEOUT, popen=subprocess.Popen):
    """[{name, inputSchema…}] from tools/list: metadata only, for checking a tool's schema. Only for a server
    named in ALLOWED."""
    if server not in {srv for srv, _ in ALLOWED}:
        raise McpError(f"{server}: not an allowed server")

    def run(s, deadline):
        tools, cursor = [], None
        while True:
            result = s.request("tools/list", {"cursor": cursor} if cursor else {}, deadline)
            tools += result.get("tools") or []
            cursor = result.get("nextCursor")
            if not cursor:
                return tools

    return _session(server, config_path, timeout, popen, run)


def zoho_original_message(message_id, **kw):
    """The tool's text for ZohoMail_getOriginalMessage (JSON wrapping the raw MIME)."""
    if not re.fullmatch(r"[0-9]{6,25}", str(message_id)):  # ASCII digits only
        raise McpError(f"zoho-mail: not a message id: {message_id!r}")
    return call_tool("zoho-mail", "ZohoMail_getOriginalMessage",
                     {"path_variables": {"accountId": ZOHO_ACCOUNT, "messageId": str(message_id)}}, **kw)
