"""Claude Code in the Command Centre (phase 4): one module, so it can be swapped out.

Each turn runs the Claude Agent SDK (claude-agent-sdk, which bundles and runs its own Claude Code CLI) in the repo the
app runs from, under the repo's own guards (spec: docs/superpowers/specs/2026-09-28-command-centre-design.md, binding
rule 6; plan: phase 4):

- **The same settings as a terminal session in the repo.** `setting_sources=["project"]` loads the checked-in
  `.claude/settings.json` (its allowlist, its deny rules and its PreToolUse hooks: the Zoho Mail, Zoho Books and
  calendar guards) and `CLAUDE.md`. `~/.claude/settings.json` and `.claude/settings.local.json` are not loaded, so an
  "always allow" clicked in a terminal doesn't carry over: here it becomes a card. `permission_mode` is always
  "default". check_options() refuses bypassPermissions, any other mode, a permission-prompt tool, allowed_tools and
  any extra CLI argument before every connect.
- **Approval cards.** A tool call the allowlist allows runs as it would in the terminal. One that would prompt reaches
  the SDK's `can_use_tool` callback, which opens a card: a server-built summary of the exact call (the tool name and
  a canonical JSON form of its input, truncated to fit but bound to all of it by its sha256). Approving needs a fresh
  passkey assertion over a challenge bound to auth.Action("chat-tool", that summary), made through the card's own
  routes; the approval is re-checked against the card's input as it is at that moment, and the callback then allows
  exactly that input, once (never `updated_permissions`, so no rule is added). Deny is one tap with no passkey.
  Ten minutes without an answer, a stop, a crash or the end of the turn all deny.
- **Streaming.** Every event is appended to the conversation (memory and ~/lcs-private/command-centre/chats/<id>.jsonl,
  mode 600) and sent to the browser as Server-Sent Events: one `data:` line of JSON, with <, > and & escaped, so no
  text can end an event or add a field; the page renders it with textContent. The stream is a GET with no side
  effects; messages, approvals and stop are same-origin POSTs.
- **Auth for the SDK.** The app has none of its own. The bundled CLI uses the owner's Claude Code login the way the
  terminal `claude` does (on macOS, the Keychain item that `claude` then `/login` creates), or ANTHROPIC_API_KEY if
  that is in the app's environment (the LaunchAgent sets no such variable).

Trust: sending a message needs the owner's Tailscale identity, the Host check and a same-origin POST (no passkey).
What a message can make Claude do without a card is what the allowlist already lets a terminal session do, and a
process on the Mac that could forge the headers could run `claude` in the repo itself (the accepted risk).
"""

import asyncio
import contextlib
import copy
import dataclasses
import datetime
import glob
import hashlib
import json
import logging
import os
import re
import secrets
import stat
import time
from pathlib import Path

from . import actions, auth, sources

try:  # the rest of the app works without the SDK; the chat page says it is missing
    import claude_agent_sdk as sdk
except ImportError:  # pragma: no cover
    sdk = None

log = logging.getLogger("command_centre.chat")

REPO = Path(__file__).resolve().parent.parent
SETTING_SOURCES = ("project",)
PERMISSION_MODE = "default"
ID_RE = re.compile(r"^[a-z]{16}$")  # letters only: no digit run for the pages' masking to eat
TASK_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)?$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
CARD_TIMEOUT = 600  # seconds a card waits for the owner; then it is a deny
STOP_GRACE = 10  # seconds after a stop before the turn is cancelled outright
MAX_RUNNING = 2  # turns running at once, across the app
DEFAULT_MAX_TURNS = 25
MAX_TURNS_CHOICES = (5, 10, 25, 50, 100)
TASK_MAX_TURNS = 100  # a scheduled task's prompt does a lot of steps
HANDOFF_MAX_TURNS = 50
TEXT_MAX = 8000  # characters of one message from the owner
STORED_TEXT_MAX = 20000  # characters of one reply block kept
RESULT_MAX = 1500  # characters of a tool result kept
TOOL_INPUT_SHOWN = 400  # characters of an allowed tool call's input shown in the log
TASK_PROMPT_MAX = 64 * 1024
LIST_MAX = 100
TOOL_ACTION = "chat-tool"
START_ACTION = "chat-start"
STOP_ACTION = "chat-stop"
AUDIT_NAMES = (START_ACTION, TOOL_ACTION, STOP_ACTION)
EVENT_TYPES = {"meta", "user", "text", "tool", "tool_result", "card", "card_done", "result", "error", "stopped",
               "session", "idle", "notice"}
APPEND_PROMPT = ("You are running inside the owner's private LCS Command Centre web app, usually read on a phone. "
                 "Keep replies short and in plain text (no tables). Any tool call outside the repo's allowlist is shown "
                 "to the owner as an approval card, which he approves with Face ID or Touch ID or denies.")
QUICK_PROMPTS = (
    ("What's owed this week?", "What's owed this week? List client money due or overdue and singer invoices to pay, "
                               "with dates and amounts, from the ledger, the payment check and the singer store."),
    ("Summarise today", "Summarise today: new enquiries, drafts waiting in Zoho, payments in, hand checks and anything "
                        "that needs me."),
    ("Draft a reply to…", "Draft a reply to "),
)
HAND_PROMPT = "Why is {ref} on the hand check? Look at the ledger notes and the payment check and explain."
TASK_NOTE = ("Manual run of the scheduled task \"{name}\", started from the Command Centre chat (not by the scheduler). "
             "Follow the task's prompt below as its scheduled run would. Anything outside the repo's allowlist comes "
             "to me as an approval card.\n\n")
TASK_DIFFERENCES = ("Runs the task's own prompt now, in this chat, under the repo's project settings only. Anything "
                    "outside the allowlist becomes a card for you. The scheduler's run history won't show it, and it "
                    "shouldn't overlap a scheduled run (the enquiry assistant runs at :07 past every other hour, "
                    "08:00 to 20:00).")
HANDOFFS = {"books-import-2026": "Books import"}


class ChatError(Exception):
    """A refused chat request. `reason` is a fixed phrase, safe to show and return as JSON."""

    def __init__(self, reason, status=400):
        super().__init__(reason)
        self.reason = reason
        self.status = status


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def new_id():
    """16 random lowercase letters (a conversation or a card): about 75 bits."""
    return "".join(secrets.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(16))


# ---------------------------------------------------------------- options


def chat_path():
    """The PATH for the CLI and the MCP servers it starts (pipx, npx, uvx): the app's own PATH (the LaunchAgent's is
    only the system folders) plus Homebrew, ~/.local/bin and the newest nvm Node, where they exist."""
    home = Path.home()
    extra = ["/opt/homebrew/bin", "/usr/local/bin", str(home / ".local" / "bin")]
    nvm = sorted(glob.glob(str(home / ".nvm" / "versions" / "node" / "*" / "bin")))
    if nvm:
        extra.append(nvm[-1])
    parts = [p for p in os.environ.get("PATH", "/usr/bin:/bin").split(":") if p]
    for p in extra:
        if p not in parts and os.path.isdir(p):
            parts.append(p)
    return ":".join(parts)


def chat_env():
    """Variables set for the CLI on top of the app's environment: the PATH above, and every CC_* variable blanked
    (the dev login, the port and the bank switch are the app's, not Claude's)."""
    env = {k: "" for k in os.environ if k.startswith("CC_")}
    env.update(PATH=chat_path(), CLAUDE_AGENT_SDK_CLIENT_APP="lcs-command-centre/4")
    return env


def _stderr(line):
    log.info("claude: %s", str(line)[:300])


def build_options(can_use_tool, max_turns=DEFAULT_MAX_TURNS, resume=None, cwd=None):
    """The only place the SDK's options are made. check_options() is run on the result before every connect."""
    if sdk is None:
        raise ChatError("the Claude Agent SDK is not installed", status=503)
    opts = sdk.ClaudeAgentOptions(
        cwd=str(cwd or REPO), setting_sources=list(SETTING_SOURCES), permission_mode=PERMISSION_MODE,
        can_use_tool=can_use_tool, max_turns=int(max_turns), resume=resume,
        system_prompt={"type": "preset", "preset": "claude_code", "append": APPEND_PROMPT},
        env=chat_env(), stderr=_stderr)
    check_options(opts)
    return opts


def check_options(opts):
    """Refuse anything that would loosen the repo's permissions. Raises ChatError."""
    if getattr(opts, "permission_mode", None) != PERMISSION_MODE:
        raise ChatError("the chat only runs in the default permission mode", status=500)
    if "project" not in (getattr(opts, "setting_sources", None) or []):
        raise ChatError("the chat must load the project settings", status=500)
    if getattr(opts, "can_use_tool", None) is None:
        raise ChatError("the chat needs its approval callback", status=500)
    if getattr(opts, "permission_prompt_tool_name", None) or getattr(opts, "allowed_tools", None):
        raise ChatError("the chat never adds allowed tools or a prompt tool", status=500)
    if getattr(opts, "extra_args", None) or getattr(opts, "settings", None) is not None:
        raise ChatError("the chat passes no extra CLI arguments or settings", status=500)
    return opts


# ---------------------------------------------------------------- cards


def canonical(tool, tool_input):
    """The exact call as one string: what the digest, and so the passkey, bind."""
    return json.dumps({"tool": tool, "input": tool_input}, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)


def digest_of(tool, tool_input):
    return hashlib.sha256(canonical(tool, tool_input).encode("utf-8")).hexdigest()


def tool_label(tool):
    text = str(tool)
    return text if re.fullmatch(r"[A-Za-z0-9_.:()-]{1,128}", text) else json.dumps(text)[:130]


def card_summary(cid, card_id, tool, tool_input):
    """(summary, digest). The summary is what the owner reads on the card and what the passkey challenge binds."""
    body = canonical(tool, tool_input)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    head = (f"Chat {cid}, request {card_id}\nAllow Claude to use: {tool_label(tool)}\n"
            f"Exact call ({len(body)} characters, sha256 {digest}):\n")
    tail = "\n… truncated: the sha256 above covers all of it"
    room = auth.MAX_SUMMARY - len(head)
    shown = body if len(body) <= room else body[:room - len(tail)] + tail
    return head + shown, digest


@dataclasses.dataclass
class Card:
    id: str
    tool: str
    input: dict
    digest: str
    summary: str
    login: str
    future: asyncio.Future
    created: float = dataclasses.field(default_factory=time.monotonic)
    status: str = "open"


# ---------------------------------------------------------------- SSE


def sse(event):
    """One Server-Sent Event: an id, a fixed event name and a single data line of JSON with <, > and & escaped."""
    etype = event.get("type") if event.get("type") in EVENT_TYPES else "notice"
    data = json.dumps(event, ensure_ascii=True, separators=(",", ":"), default=str)
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    n = int(event.get("n") or 0)
    return f"id: {n}\nevent: {etype}\ndata: {data}\n\n"


# ---------------------------------------------------------------- storage


def chats_dir():
    return auth.config_dir() / "chats"


def _private_dir(d):
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    return d


def _clip(text, most):
    text = str(text or "")
    return text if len(text) <= most else text[:most] + "…"


class Conversation:
    """One conversation: its events (in memory and in its .jsonl file) and, while a turn runs, its live state."""

    def __init__(self, cid, events=None):
        self.id = cid
        self.events = list(events or [])
        self.running = False
        self.pending = {}  # card id -> Card
        self.task = None
        self.stop_event = None
        self.stop_requested = False
        self._changed = asyncio.Event()

    @property
    def path(self):
        return chats_dir() / f"{self.id}.jsonl"

    @property
    def meta(self):
        return next((e for e in self.events if e.get("type") == "meta"), {})

    @property
    def session_id(self):
        for e in reversed(self.events):
            if e.get("type") in ("session", "result") and isinstance(e.get("session_id"), str) and e["session_id"]:
                return e["session_id"]
        return None

    def totals(self):
        cost, tokens_in, tokens_out = 0.0, 0, 0
        for e in self.events:
            if e.get("type") == "result":
                cost += float(e.get("cost_usd") or 0)
                u = e.get("usage") or {}
                tokens_in += sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens",
                                                              "cache_creation_input_tokens"))
                tokens_out += int(u.get("output_tokens") or 0)
        return {"cost_usd": round(cost, 4), "input_tokens": tokens_in, "output_tokens": tokens_out}

    def append(self, event):
        event = dict(event)
        event["n"] = (self.events[-1]["n"] + 1) if self.events else 1
        event.setdefault("at", _now())
        self.events.append(event)
        _private_dir(chats_dir())
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        self.notify()
        return event

    def notify(self):
        self._changed.set()
        self._changed = asyncio.Event()

    def after(self, n):
        return [e for e in self.events if int(e.get("n") or 0) > n]

    @classmethod
    def load(cls, cid):
        path = chats_dir() / f"{cid}.jsonl"
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except (FileNotFoundError, OSError):
            return None
        events = []
        with os.fdopen(fd, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if isinstance(e, dict) and isinstance(e.get("n"), int) and e.get("type") in EVENT_TYPES:
                    events.append(e)
        conv = cls(cid, events)
        closed = {e.get("card") for e in events if e.get("type") == "card_done"}
        for e in events:  # a card left open when the app stopped: its turn is gone, so it reads as expired
            if e.get("type") == "card" and e.get("card") not in closed:
                e["expired"] = True
        return conv


def list_conversations(limit=LIST_MAX):
    d = chats_dir()
    if not d.is_dir():
        return []
    items = []
    for path in d.glob("*.jsonl"):
        if not ID_RE.fullmatch(path.stem) or path.is_symlink():
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                meta = json.loads(f.readline() or "{}")
            mtime = path.stat().st_mtime
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict):
            continue
        items.append({"id": path.stem, "title": str(meta.get("title") or "Chat")[:80], "kind": meta.get("kind", "blank"),
                      "created": meta.get("at", ""),
                      "updated": datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc)})
    items.sort(key=lambda i: i["updated"], reverse=True)
    return items[:limit]


# ---------------------------------------------------------------- tasks and handoffs


def task_names():
    return [t["dir"] for t in scheduled_tasks()]


def scheduled_tasks():
    """The scheduled tasks the chat can run now: [{"dir", "name", "description"}]."""
    d = sources.tasks_dir()
    out = []
    if not d.is_dir():
        return out
    for task in sorted(d.iterdir()):
        if not TASK_RE.fullmatch(task.name) or task.is_symlink() or not task.is_dir():
            continue
        skill = task / "SKILL.md"
        if skill.is_symlink() or not skill.is_file():
            continue
        try:
            meta = sources.frontmatter(skill)
        except OSError:
            continue
        out.append({"dir": task.name, "name": meta.get("name") or task.name, "description": meta.get("description", "")})
    return out


def task_prompt(name):
    """The first message for "run <task> now": a line saying it is a manual run, then the SKILL.md body (after its
    frontmatter). The file must be a regular file owned by this user, not a symlink, at most 64 KB."""
    if not isinstance(name, str) or not TASK_RE.fullmatch(name) or name not in task_names():
        raise ChatError("unknown task", status=404)
    path = sources.tasks_dir() / name / "SKILL.md"
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        raise ChatError("couldn't read the task's prompt") from None
    with os.fdopen(fd, "rb") as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid():
            raise ChatError("the task's prompt isn't a regular file of yours")
        if st.st_size > TASK_PROMPT_MAX:
            raise ChatError("the task's prompt is too long")
        text = f.read(TASK_PROMPT_MAX + 1).decode("utf-8", errors="replace")
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is not None:
            lines = lines[end + 1:]
    body = "\n".join(lines).strip()
    if not body:
        raise ChatError("the task's prompt is empty")
    return TASK_NOTE.format(name=name) + body


def handoffs_dir():
    return auth.config_dir() / "handoffs"


def handoff_started(item):
    try:
        with open(handoffs_dir() / f"{item}.json", encoding="utf-8") as f:
            rec = json.load(f)
        cid = rec.get("conversation")
        return cid if isinstance(cid, str) and ID_RE.fullmatch(cid) else "unknown"
    except FileNotFoundError:
        return None
    except (OSError, ValueError, AttributeError):
        return "unknown"


def books_handoff():
    """The Books import approval, if it can be handed to the chat: the approval record exists and its dry-run hash
    still matches the dry run on disk. {"item", "label", "approved_at", "sha256", "started"} or None."""
    rec_path = actions.books_approval_path()
    dry = actions.books_dry_run()
    if rec_path.is_symlink() or not rec_path.is_file() or dry.is_symlink() or not dry.is_file():
        return None
    try:
        with open(rec_path, encoding="utf-8") as f:
            rec = json.load(f)
        current = hashlib.sha256(dry.read_bytes()).hexdigest()
    except (OSError, ValueError):
        return None
    if not isinstance(rec, dict) or rec.get("status") != "approved":
        return None
    sha, when = rec.get("dry_run_sha256"), rec.get("approved_at")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha) or sha != current:
        return None
    if not isinstance(when, str) or not ISO_RE.fullmatch(when):
        return None
    item = f"books-import-{actions.BOOKS_YEAR}"
    return {"item": item, "label": HANDOFFS[item], "approved_at": when, "sha256": sha, "started": handoff_started(item)}


def handoff_prompt(h):
    """The fixed first message for an approved handoff: built here from validated values, never text from a file."""
    return (f"Run the approved Books import. The owner approved it in the Command Centre ({h['approved_at']}) with a "
            f"passkey.\nFirst check that the sha256 of ~/lcs-private/books-import-{actions.BOOKS_YEAR}.json is "
            f"{h['sha256']}. If it isn't, stop and tell me, and create nothing.\n"
            f"Then: {actions.BOOKS_INSTRUCTION}\n"
            "Use only the Zoho Books tools the Books guard allows (.claude/hooks/zoho_books_guard.py): draft invoices "
            "only; never send, void, delete or record a payment. Finish with one line per invoice created.")


def handoffs():
    h = books_handoff()
    return [h] if h else []


# ---------------------------------------------------------------- the manager


def _default_factory(options):
    if sdk is None:
        raise ChatError("the Claude Agent SDK is not installed", status=503)
    return sdk.ClaudeSDKClient(options)


def _blocks(msg):
    content = getattr(msg, "content", None)
    return content if isinstance(content, list) else []


def _result_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(c.get("text", "")) for c in content if isinstance(c, dict) and c.get("type") == "text")
    return ""


class ChatManager:
    """The app's conversations. Everything here runs on the server's event loop; passkey checks go to a thread."""

    def __init__(self, passkeys, client_factory=None, cwd=None):
        self.passkeys = passkeys
        self.factory = client_factory or _default_factory
        self.cwd = cwd
        self.convs = {}

    # -- conversations

    def get(self, cid):
        if not isinstance(cid, str) or not ID_RE.fullmatch(cid):
            return None
        conv = self.convs.get(cid)
        if conv is None:
            conv = Conversation.load(cid)
            if conv is not None:
                self.convs[cid] = conv
        return conv

    def require(self, cid):
        conv = self.get(cid)
        if conv is None:
            raise ChatError("unknown chat", status=404)
        return conv

    def create(self, user, kind="blank", title="New chat", first=None, cid=None):
        cid = cid or new_id()
        if not ID_RE.fullmatch(cid) or self.get(cid) is not None:
            raise ChatError("malformed request")
        conv = Conversation(cid)
        self.convs[cid] = conv
        conv.append({"type": "meta", "title": _clip(title, 80), "kind": kind, "login": (user or {}).get("login", "")})
        digest = hashlib.sha256((first or "").encode("utf-8")).hexdigest() if first else None
        actions.write_audit(START_ACTION, f"chat {cid}: {kind}: {_clip(title, 80)}", user, "started",
                            chat=cid, kind=kind, **({"first_sha256": digest} if digest else {}))
        return conv

    def running_count(self):
        return sum(1 for c in self.convs.values() if c.running)

    # -- turns

    def send(self, conv, text, user, max_turns=DEFAULT_MAX_TURNS):
        """Start a turn (returns at once; the turn runs as a task on the loop)."""
        if not isinstance(text, str) or not text.strip():
            raise ChatError("write a message first")
        if len(text) > TEXT_MAX:
            raise ChatError("that message is too long")
        try:
            max_turns = int(max_turns)
        except (TypeError, ValueError):
            raise ChatError("max turns must be a number") from None
        if max_turns not in MAX_TURNS_CHOICES:
            raise ChatError("max turns must be one of " + ", ".join(map(str, MAX_TURNS_CHOICES)))
        if conv.running:
            raise ChatError("Claude is still working on the last message; stop it or wait", status=409)
        if self.running_count() >= MAX_RUNNING:
            raise ChatError("two chats are already running; wait for one to finish", status=409)
        if len([e for e in conv.events if e.get("type") == "meta"]) == 0:
            raise ChatError("unknown chat", status=404)
        if len(conv.events) == 1 and conv.meta.get("title") == "New chat":
            conv.meta["title"] = _clip(text.strip().splitlines()[0], 80)
            _rewrite_meta(conv)
        conv.append({"type": "user", "text": text, "login": (user or {}).get("login", ""), "max_turns": max_turns})
        conv.running = True
        conv.stop_requested = False
        conv.stop_event = asyncio.Event()
        conv.task = asyncio.get_running_loop().create_task(self._turn(conv, text, max_turns, dict(user or {})))
        return conv

    async def _turn(self, conv, text, max_turns, user):
        client = watcher = None
        try:
            options = build_options(self._callback(conv, user), max_turns, resume=conv.session_id, cwd=self.cwd)
            client = self.factory(options)
            await client.connect()
            await client.query(text)

            async def watch():
                await conv.stop_event.wait()
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(client.interrupt(), 5)

            watcher = asyncio.get_running_loop().create_task(watch())
            async for msg in client.receive_response():
                self._on_message(conv, msg)
        except asyncio.CancelledError:
            if not conv.stop_requested:
                conv.append({"type": "stopped", "reason": "cancelled"})
        except ChatError as e:
            conv.append({"type": "error", "error": e.reason})
        except Exception as e:  # the chat never takes the app down; the type only reaches the page
            log.warning("chat turn failed: %s", type(e).__name__)
            conv.append({"type": "error", "error": f"Claude stopped with an error ({type(e).__name__})"})
        finally:
            if watcher is not None:
                watcher.cancel()
            self._close_cards(conv, "expired", user)
            if client is not None:
                with contextlib.suppress(BaseException):
                    await asyncio.wait_for(client.disconnect(), 10)
            conv.running = False
            conv.task = None
            conv.notify()

    def _on_message(self, conv, msg):
        name = type(msg).__name__
        if name == "AssistantMessage":
            sub = bool(getattr(msg, "parent_tool_use_id", None))
            for b in _blocks(msg):
                bname = type(b).__name__
                if bname == "TextBlock" and str(b.text).strip():
                    conv.append({"type": "text", "text": _clip(b.text, STORED_TEXT_MAX), "sub": sub})
                elif bname == "ToolUseBlock":
                    conv.append({"type": "tool", "tool": tool_label(b.name), "sub": sub,
                                 "input": _clip(json.dumps(b.input, ensure_ascii=False, sort_keys=True, default=str),
                                                TOOL_INPUT_SHOWN)})
        elif name == "UserMessage":
            for b in _blocks(msg):
                if type(b).__name__ == "ToolResultBlock":
                    conv.append({"type": "tool_result", "error": bool(b.is_error),
                                 "text": _clip(_result_text(b.content), RESULT_MAX)})
        elif name == "SystemMessage":
            sid = (getattr(msg, "data", None) or {}).get("session_id")
            if getattr(msg, "subtype", "") == "init" and isinstance(sid, str) and sid != conv.session_id:
                conv.append({"type": "session", "session_id": sid})
        elif name == "ResultMessage":
            usage = msg.usage if isinstance(getattr(msg, "usage", None), dict) else {}
            keep = {k: usage.get(k) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                              "cache_creation_input_tokens") if isinstance(usage.get(k), int)}
            conv.append({"type": "result", "subtype": str(msg.subtype), "error": bool(msg.is_error),
                         "turns": msg.num_turns, "cost_usd": msg.total_cost_usd, "usage": keep,
                         "session_id": msg.session_id, "duration_ms": msg.duration_ms})

    # -- cards

    def _callback(self, conv, user):
        async def can_use_tool(tool_name, tool_input, context):
            if conv.stop_requested:
                return sdk.PermissionResultDeny(message="The owner stopped this chat.", interrupt=True)
            card = self._open_card(conv, tool_name, tool_input, user)
            try:
                decision = await asyncio.wait_for(asyncio.shield(card.future), CARD_TIMEOUT)
            except asyncio.TimeoutError:
                self._finish(conv, card, "timed out", user)
                return sdk.PermissionResultDeny(message="No answer from the owner within 10 minutes, so this was denied.")
            except asyncio.CancelledError:
                self._finish(conv, card, "expired", user)
                raise
            if decision == "approved" and digest_of(card.tool, card.input) == card.digest:
                return sdk.PermissionResultAllow(updated_input=copy.deepcopy(card.input))
            if decision == "stopped":
                return sdk.PermissionResultDeny(message="The owner stopped this chat.", interrupt=True)
            return sdk.PermissionResultDeny(message="The owner denied this in the Command Centre.")
        return can_use_tool

    def _open_card(self, conv, tool_name, tool_input, user):
        card_id = new_id()
        tool_input = copy.deepcopy(tool_input) if isinstance(tool_input, dict) else {"value": tool_input}
        summary, digest = card_summary(conv.id, card_id, tool_name, tool_input)
        card = Card(card_id, str(tool_name), tool_input, digest, summary, (user or {}).get("login", ""),
                    asyncio.get_running_loop().create_future())
        conv.pending[card_id] = card
        conv.append({"type": "card", "card": card_id, "tool": tool_label(tool_name), "summary": summary,
                     "digest": digest, "timeout": CARD_TIMEOUT})
        return card

    def _finish(self, conv, card, decision, user, passkey=None, audit=True):
        """Close a card once: set its answer, record it in the conversation and the audit log."""
        if card.status != "open":
            return False
        card.status = decision
        conv.pending.pop(card.id, None)
        if not card.future.done():
            card.future.set_result(decision)
        conv.append({"type": "card_done", "card": card.id, "decision": decision})
        if audit:
            result = {"approved": "ok"}.get(decision, decision)
            actions.write_audit(TOOL_ACTION, card.summary[:600], user, result, chat=conv.id, card=card.id,
                                input_sha256=card.digest, tool=tool_label(card.tool), passkey=passkey)
        return True

    def _close_cards(self, conv, decision, user):
        for card in list(conv.pending.values()):
            self._finish(conv, card, decision, user)

    def _card(self, conv, card_id, digest):
        card = conv.pending.get(card_id) if isinstance(card_id, str) else None
        if card is None or card.status != "open":
            raise ChatError("that request is no longer open", status=409)
        if not isinstance(digest, str) or digest != card.digest:
            raise ChatError("this isn't the request you were shown", status=409)
        summary, now = card_summary(conv.id, card.id, card.tool, card.input)
        if now != card.digest:
            raise ChatError("the request changed after it was shown; deny it", status=409)
        return card, auth.Action(TOOL_ACTION, summary)

    def card_options(self, conv, card_id, digest):
        card, action = self._card(conv, card_id, digest)
        return self.passkeys.assertion_options(action)

    def card_check(self, conv, card_id, digest, user):
        """The card and its server-built action, for an approval; a refusal here is audited."""
        try:
            return self._card(conv, card_id, digest)
        except ChatError as e:
            actions.write_audit(TOOL_ACTION, f"chat {conv.id}, request {str(card_id)[:16]}", user,
                                f"refused: {e.reason}", chat=conv.id)
            raise

    def approve_verified(self, conv, card, action, passkey_id, user):
        """After require_fresh_assertion() passed for `action`: check nothing moved in the meantime, then allow."""
        summary, now = card_summary(conv.id, card.id, card.tool, card.input)
        if card.status != "open" or now != card.digest or summary != action.summary:
            actions.write_audit(TOOL_ACTION, action.summary[:600], user, "refused: changed or closed after the passkey",
                                chat=conv.id, card=card.id, passkey=passkey_id)
            raise ChatError("the request changed or closed; nothing was approved", status=409)
        self._finish(conv, card, "approved", user, passkey=passkey_id)

    def refuse_passkey(self, conv, card, action, reason, user):
        actions.write_audit(TOOL_ACTION, action.summary[:600], user, f"refused: {reason}", chat=conv.id, card=card.id,
                            input_sha256=card.digest)

    def deny(self, conv, card_id, user):
        card = conv.pending.get(card_id) if isinstance(card_id, str) else None
        if card is None:
            raise ChatError("that request is no longer open", status=409)
        self._finish(conv, card, "denied", user)

    # -- stop

    def stop(self, conv, user):
        if not conv.running:
            raise ChatError("nothing is running", status=409)
        if conv.stop_requested:
            return
        conv.stop_requested = True
        for card in list(conv.pending.values()):
            self._finish(conv, card, "stopped", user)
        conv.append({"type": "stopped", "reason": "owner"})
        actions.write_audit(STOP_ACTION, f"chat {conv.id}: stop", user, "ok", chat=conv.id)
        if conv.stop_event is not None:
            conv.stop_event.set()
        task = conv.task

        def cancel():
            if task is not None and not task.done():
                task.cancel()
        asyncio.get_running_loop().call_later(STOP_GRACE, cancel)

    # -- streaming

    async def stream(self, conv, after=0, keepalive=15.0):
        """SSE strings: the stored events after `after`, then live ones; `idle` and the end when no turn runs."""
        n = after
        yield "retry: 3000\n\n"
        while True:
            waiter = conv._changed
            for e in conv.after(n):
                yield sse(e)
                n = e["n"]
            if not conv.running:
                yield sse({"type": "idle", "n": n, "totals": conv.totals()})
                return
            try:
                await asyncio.wait_for(waiter.wait(), keepalive)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"


def _rewrite_meta(conv):
    """Rewrite the file with the updated title (the first line is the meta)."""
    path = conv.path
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for e in conv.events:
            f.write(json.dumps(e, ensure_ascii=False, default=str) + "\n")
    os.replace(tmp, path)


def record_handoff(item, cid, user):
    """Once only per item: refused (ChatError 409) if it was already started."""
    _private_dir(handoffs_dir())
    try:
        actions.write_private(handoffs_dir() / f"{item}.json",
                              {"conversation": cid, "started_at": _now(), "login": (user or {}).get("login", "")},
                              exclusive=True)
    except actions.ActionError:
        raise ChatError("already started", status=409) from None
