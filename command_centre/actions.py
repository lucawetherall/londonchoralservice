"""The action registry. Every write the app makes is an action here: a name, a strict validator for its input, a
preview that builds the summary on the server (auth.Action), and either a fixed argv (ScriptAction) or a local
write (LocalAction). Each run is logged, append-only, in ~/lcs-private/command-centre/audit.jsonl (mode 600).

Binding rules (docs/superpowers/specs/2026-09-28-command-centre-design.md, and the plan's phase 3):
- Every action except `todo-tick` and `refresh-data` needs a fresh passkey assertion over a challenge bound to the
  summary that preview() writes from the validated input. The summary ends with the exact command ("Runs: …"), so
  the owner's Face ID or Touch ID approves that command and nothing else. run_action() rebuilds the summary from
  the data as it is at run time: if anything it depends on changed since the preview, the assertion no longer
  matches and nothing runs.
- A ScriptAction runs `subprocess.run(argv, shell=False)` with a fixed script path under the repo and validated
  arguments (none may start with "-" unless it is a fixed flag), cwd the repo, the environment minus every CC_*
  variable with LCS_PRIVATE_DIR set explicitly (and LCS_BOOKINGS_CSV removed), stdin /dev/null (or the owner
  nonce), a timeout, one action at a time, and no retries. run_action() takes the action lock before it validates,
  so every check (an .applied record, a validate record) is re-read under the lock; refresh-data has its own lock.
- Output is scrubbed (lcs_mcp's approach: URLs, token-like values; plus any run of six or more digits) and trimmed
  before it reaches the page; the audit keeps only its sha256. Ads output is not masked: its first and last 3,000
  characters are shown, secrets still redacted.
- The owner-only hand-check phrases go through `check_payments.py --note … --owner`, which refuses unless it gets
  the one-time owner nonce written here (owner_nonce(): the file holds sha256(nonce), the nonce goes over the pipe),
  and unless the ledger sits beside that nonce (LCS_BOOKINGS_CSV unset).
- Ads change sets come from ~/lcs-private/command-centre/proposals/<id>.json (mode 600). A proposal pins a commit,
  the script's blob at that commit and its arguments (simple tokens). The app keeps its own bare mirror,
  ~/lcs-private/command-centre/mirror.git (mode 700, its config rewritten to a fixed one each time), and fetches
  GitHub's main into it from a hard-coded URL (GITHUB_URL) at the preview and again at the run; a failed fetch
  refuses. The commit must be an ancestor of that fetched main. Every git call runs in the mirror with no global
  or system config, none of the caller's GIT_* variables, no replace refs, fsmonitor and hooks off; the fetch
  allows https only. The working repo (its refs, its config, its remote URL, its files) is never read. The run
  folder is written from `git ls-tree -r` and `git cat-file --batch` in the mirror (no checkout, no archive, so
  no filters or attributes), each file checked against its blob id, regular files only, in an app-owned mode-700
  folder, and the script runs with `python -E -s -B`, an allowlisted environment and no bytecode from anywhere
  else. Validate passes --validate-only, which only proposal-aware scripts accept; apply passes --apply, runs
  from the same commit, and is bound to the validate run's output hash. The preview shows the script's last
  change on main as a diff (bound to the summary by its sha256) and links to the file on GitHub. A blob and
  arguments once applied are refused again under any proposal id.
- What stays trusted (accepted residual risk, in the spec's threat model): the Python interpreter the app runs
  (sys.executable, the repo's .venv) and that venv's site-packages, including any .pth file, which Python runs at
  start-up even with -E -s; the git binary; and the mirror and the private folder on disk. All of these belong to
  the same macOS user as the app, and a process running as that user could alter them. The mirror and run
  folder stop the working tree and its git state from changing what runs, not that user.
- The audit log is hash-chained: each line carries the sha256 of the line before it (verify_audit()).
"""

import contextlib
import dataclasses
import datetime
import fcntl
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import ast
from pathlib import Path
from typing import Callable, Optional

from . import auth, data, models, todo

REPO = Path(__file__).resolve().parent.parent  # read at call time (the ads tests point it at a temp git repo)
PY_SHOWN = ".venv/bin/python"
CHECK_PAYMENTS = "scripts/bookings/check_payments.py"
SINGER_INVOICES = "scripts/bookings/singer_invoices.py"
DASHBOARD = "scripts/reports/dashboard.py"
OUTPUT_MAX = 6000  # characters of scrubbed output shown (the tail)
ADS_HEAD = ADS_TAIL = 3000  # Ads output: its first and last characters, unmasked
RUN_WAIT = 5  # seconds to wait for another action to finish before refusing
VALIDATION_TTL = 15 * 60  # seconds an ads validate run stays good for its apply
RUNNER = subprocess.run  # the tests replace this with a recorder
FIXED_FLAGS = {"--note", "--owner", "--apply", "--validate-only", "--expect-fp"}  # the only arguments that may start with "-"; the rest are validated values
lm, cp, si = data.lm, data.cp, data.si


class ActionError(Exception):
    """Refused input. `reason` is a fixed phrase, safe to show."""

    def __init__(self, reason, status=400):
        super().__init__(reason)
        self.reason = reason
        self.status = status


@dataclasses.dataclass(frozen=True)
class Result:
    ok: bool
    exit_code: Optional[int]
    output: str
    summary: str
    next: Optional[dict] = None

    def as_json(self):
        return {"ok": self.ok, "exit_code": self.exit_code, "output": self.output, "summary": self.summary,
                "next": self.next}


# ---------------------------------------------------------------- the two kinds of action


@dataclasses.dataclass(frozen=True)
class LocalAction:
    """A write to the app's own files (no subprocess). `run(cleaned, who) -> str` returns a line for the result;
    `who` is {"login", "passkey"} (the approving login and passkey id, or None)."""
    name: str
    validate: Callable  # raw input (a dict of strings) -> cleaned input, or ActionError
    preview: Callable   # cleaned input -> the summary, written by the server
    run: Callable       # (cleaned input, who) -> None or a short message
    passkey: bool = True
    title: str = ""
    lock: str = "action"

    def build(self, raw):
        """The server-built auth.Action for this input (what a passkey, when needed, binds)."""
        return auth.Action(self.name, self.preview(self.validate(raw)))

    def command(self, cleaned):
        return None

    def perform(self, cleaned, action, user, passkey_id=None):
        who = {"login": (user or {}).get("login", ""), "passkey": passkey_id}
        try:
            message = self.run(cleaned, who)
        except ActionError as e:
            audit(action, user, f"refused: {e.reason}", input=public(cleaned), passkey=passkey_id)
            raise
        except Exception as e:
            audit(action, user, f"failed: {type(e).__name__}", input=public(cleaned), passkey=passkey_id)
            raise
        warning = audit_after_run(action, user, "ok", input=public(cleaned), passkey=passkey_id)
        return Result(True, None, join_warning(warning, message or "done"), action.summary)

    def execute(self, raw, user):
        """Validate, run and log an action that needs no passkey (the to-do tick's form route)."""
        if self.passkey:
            raise ActionError("this action needs a passkey", status=403)
        cleaned = self.validate(raw)
        action = auth.Action(self.name, self.preview(cleaned))
        self.perform(cleaned, action, user)
        return action


def check_args(args):
    """Belt and braces: the validators already refuse these."""
    for a in args:
        if not isinstance(a, str) or "\x00" in a or (a.startswith("-") and a not in FIXED_FLAGS):
            raise ActionError("bad argument")


@dataclasses.dataclass(frozen=True)
class ScriptAction:
    """A fixed script run. `script` is repo-relative and fixed; `args(cleaned)` returns the validated arguments."""
    name: str
    script: str
    validate: Callable
    describe: Callable  # cleaned -> plain English (the summary's first part)
    args: Callable      # cleaned -> list[str]
    passkey: bool = True
    timeout: int = 60
    owner_nonce: bool = False
    clears_cache: bool = False
    after: Optional[Callable] = None  # (cleaned, exit_code, raw_output) -> the result's `next`, or None
    title: str = ""
    lock: str = "action"

    def argv(self, cleaned):
        return [sys.executable, str(Path(REPO) / self.script), *self.args(cleaned)]

    def shown(self, cleaned):
        return [PY_SHOWN, self.script, *self.args(cleaned)]

    def command(self, cleaned):
        return shlex.join(self.shown(cleaned))

    def preview(self, cleaned):
        return f"{self.describe(cleaned)}\nRuns: {self.command(cleaned)}"

    def build(self, raw):
        return auth.Action(self.name, self.preview(self.validate(raw)))

    def claim(self, cleaned):
        """Anything the run must take for itself, atomically, just before it starts (ActionError refuses)."""

    def execute_script(self, cleaned):
        """(exit code or None, raw stdout+stderr)."""
        argv = self.argv(cleaned)
        env = clean_env(drop=("LCS_BOOKINGS_CSV",) if self.owner_nonce else ())
        if self.owner_nonce:
            with owner_nonce() as nonce:
                return run_argv(argv, self.timeout, stdin_text=nonce + "\n", env=env)
        return run_argv(argv, self.timeout, env=env)

    def show(self, raw):
        return scrub(raw.decode("utf-8", "replace"))

    def perform(self, cleaned, action, user, passkey_id=None):
        check_args(self.args(cleaned))
        try:
            self.claim(cleaned)
        except ActionError as e:
            audit(action, user, f"refused: {e.reason}", input=public(cleaned), passkey=passkey_id)
            raise
        audit(action, user, "started", input=public(cleaned), passkey=passkey_id)
        code, raw = self.execute_script(cleaned)
        digest = hashlib.sha256(raw).hexdigest()
        ok = code == 0
        warning = audit_after_run(action, user, "ok" if ok else ("timed out" if code is None else "failed"),
                                  input=public(cleaned), exit_code=code, output_sha256=digest, passkey=passkey_id)
        nxt = self.after(cleaned, code, raw, {"login": (user or {}).get("login", ""), "passkey": passkey_id}) \
            if self.after else None
        if isinstance(nxt, str):  # a warning from `after` (the ads apply's record couldn't be saved)
            warning, nxt = join_warning(nxt, warning), None
        return Result(ok, code, join_warning(warning, self.show(raw)), action.summary, nxt)


def public(cleaned):
    """The input fields as the request gave them (validated), for the audit log."""
    value = cleaned.get("input") if isinstance(cleaned, dict) else None
    return dict(value) if isinstance(value, dict) else None


def join_warning(warning, text):
    return f"{warning}\n{text}" if warning else text


# ---------------------------------------------------------------- running


_RUN_LOCK = threading.Lock()
_LOCKS = {"action": _RUN_LOCK, "refresh": threading.Lock()}  # refresh-data never waits on (or blocks) a write


def clean_env(drop=()):
    """The app's environment minus every CC_* variable (the dev login, the port, the bank switch) and `drop`, with
    LCS_PRIVATE_DIR set explicitly to the folder the app itself reads (so a script and its nonce agree)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("CC_") and k not in drop}
    env["LCS_PRIVATE_DIR"] = str(auth.private_dir())
    return env


def run_argv(argv, timeout, stdin_text=None, cwd=None, env=None):
    """(exit code or None on a timeout, stdout+stderr bytes). An argv list, never a shell."""
    if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
        raise ActionError("bad command")
    kw = {"cwd": str(cwd or REPO), "env": clean_env() if env is None else env, "capture_output": True,
          "timeout": timeout, "shell": False}
    if stdin_text is None:
        kw["stdin"] = subprocess.DEVNULL
    else:
        kw["input"] = stdin_text.encode("ascii")
    try:
        proc = RUNNER(argv, **kw)
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"") + (e.stderr or b"")
        return None, out + f"\n(stopped: no answer after {timeout} seconds)".encode()
    except OSError as e:
        return None, f"could not start the script ({type(e).__name__})".encode()
    return proc.returncode, (proc.stdout or b"") + (proc.stderr or b"")


@contextlib.contextmanager
def owner_nonce():
    """A one-time nonce for check_payments.py --owner: sha256(nonce) in <config dir>/owner-nonce (mode 600, created
    exclusively, never through a symlink), the nonce itself for the child's stdin. The file goes afterwards."""
    d = auth.config_dir()
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    path = d / "owner-nonce"
    with contextlib.suppress(FileNotFoundError):
        os.unlink(path)  # a stale one from a crash; actions run one at a time
    nonce = secrets.token_hex(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as f:
            f.write(hashlib.sha256(nonce.encode("ascii")).hexdigest())
        yield nonce
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(path)


URL_RE = re.compile(r"(?i)\b(?:https?|wss?|ftp)://\S+")
BEARER_RE = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
SECRET_KV_RE = re.compile(r"(?i)\b([a-z_]*(?:token|secret|password|passwd|api_?key|client_?id|authorization)[a-z_]*)"
                          r"([\"']?\s*[:=]\s*[\"']?)([^\s\"',;]+)")
TOKENISH_RE = re.compile(r"(?<![A-Za-z0-9+/=_.-])(?=[A-Za-z0-9+/=_.-]*[A-Z])(?=[A-Za-z0-9+/=_.-]*[a-z])"
                         r"(?=[A-Za-z0-9+/=_.-]*\d)[A-Za-z0-9+/=_.-]{32,}")
DIGITS_RE = re.compile(r"\d{6,}")


def redact(text, extra_secrets=()):
    """URLs (lcs_mcp's rule), bearer and key=value secrets, long mixed-case token-shaped strings, the given
    secrets. Digits are left alone."""
    text = URL_RE.sub("<url>", str(text))
    for s in extra_secrets:
        if s and len(s) >= 6:
            text = text.replace(s, "<redacted>")
    text = BEARER_RE.sub(lambda m: f"{m.group(1)} <redacted>", text)
    text = SECRET_KV_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}<redacted>", text)
    return TOKENISH_RE.sub("<redacted>", text)


def scrub(text, extra_secrets=()):
    """Output safe to show: redact(), and any run of six or more digits (account numbers, message ids) masked;
    then trimmed to its last OUTPUT_MAX characters."""
    text = DIGITS_RE.sub("••••••", redact(text, extra_secrets)).strip()
    if len(text) > OUTPUT_MAX:
        text = "…\n" + text[-OUTPUT_MAX:]
    return text


def head_and_tail(text, head=ADS_HEAD, tail=ADS_TAIL):
    """Ads output as the owner needs it (campaign ids and amounts unmasked, secrets still redacted): the first
    `head` and last `tail` characters, with a marker for what was left out."""
    text = redact(text).strip()
    if len(text) <= head + tail:
        return text
    return f"{text[:head]}\n… ({len(text) - head - tail:,} characters left out) …\n{text[-tail:]}"


def input_sha256(raw):
    try:
        text = json.dumps(raw, sort_keys=True, ensure_ascii=True, default=str)
    except (TypeError, ValueError):
        text = repr(raw)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def refuse_early(defn, raw, user, reason):
    """A refusal at the run step before a summary exists (bad input, busy): logged with the action's name and a
    hash of the input, never the input itself."""
    write_audit(defn.name, "(refused before a summary was built)", user, f"refused: {reason}",
                input_sha256=input_sha256(raw))


def run_action(defn, raw, user, credential=None, passkeys=None):
    """Take the action's lock, then validate (so every check is made under the lock), check the passkey when the
    action needs one, and perform. Raises ActionError or auth.PasskeyError; every refusal is logged."""
    lock = _LOCKS[getattr(defn, "lock", "action")]
    if not lock.acquire(timeout=RUN_WAIT):
        refuse_early(defn, raw, user, "another action is running")
        raise ActionError("another action is running; try again in a moment", status=409)
    try:
        try:
            cleaned = defn.validate(raw)
            action = auth.Action(defn.name, defn.preview(cleaned))
        except (ActionError, auth.PasskeyError) as e:
            refuse_early(defn, raw, user, e.reason)
            raise
        passkey_id = None
        if defn.passkey:
            if credential is None or passkeys is None:
                audit(action, user, "refused: no passkey", input=public(cleaned))
                raise ActionError("this action needs a passkey", status=403)
            try:
                passkey_id = passkeys.require_fresh_assertion(credential, action)
            except auth.PasskeyError as e:
                audit(action, user, f"refused: {e.reason}", input=public(cleaned))
                raise
        return defn.perform(cleaned, action, user, passkey_id)
    finally:
        lock.release()


# ---------------------------------------------------------------- audit


GENESIS = "0" * 64  # the "prev" of the first line
_AUDIT_TAIL = 256 * 1024


def audit_path():
    return auth.config_dir() / "audit.jsonl"


def audit(action, user, result, **extra):
    write_audit(action.name, action.summary, user, result, **extra)


def audit_after_run(action, user, result, **extra):
    """The audit line written after something ran: a failure to write it never hides that the action ran. Returns
    None, or the warning to put in front of the output."""
    try:
        audit(action, user, result, **extra)
    except OSError as e:
        return f"ran, but the audit write failed ({type(e).__name__}): this run is not in the activity log"
    return None


def _last_line(fd, size):
    """The last non-empty line's bytes (no newline), or None; and whether the file ends with a newline."""
    if size == 0:
        return None, True
    start = max(0, size - _AUDIT_TAIL)
    data = os.pread(fd, size - start, start)
    while start > 0 and b"\n" not in data.rstrip(b"\n"):  # a very long last line: read further back
        start = max(0, start - _AUDIT_TAIL)
        data = os.pread(fd, size - start, start)
    body = data.rstrip(b"\n")
    last = body.rsplit(b"\n", 1)[-1] if body else None
    return (last or None), data.endswith(b"\n")


def write_audit(name, summary, user, result, **extra):
    """Append one JSON line under an exclusive flock. Each line carries "prev": the sha256 of the line before it
    (GENESIS for the first), so an edited, removed or inserted line breaks the chain (verify_audit())."""
    entry = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             "action": name, "summary": summary, "login": (user or {}).get("login", ""), "result": result}
    for k, v in extra.items():
        if v is not None:
            entry[k] = v[:8] if k == "passkey" and isinstance(v, str) else v
    d = auth.config_dir()
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(audit_path(), os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        size = os.fstat(fd).st_size
        last, ends = _last_line(fd, size)
        entry["prev"] = hashlib.sha256(last).hexdigest() if last else GENESIS
        line = json.dumps(entry, ensure_ascii=False).encode("utf-8") + b"\n"
        if not ends:
            line = b"\n" + line
        view = memoryview(line)
        while view:
            view = view[os.write(fd, view):]
    finally:
        os.close(fd)


def verify_audit(path=None):
    """The 1-based numbers of the non-empty lines that break the hash chain (not JSON, no "prev", or a "prev" that
    isn't the sha256 of the line before). An empty list means the log is whole."""
    try:
        data = Path(path or audit_path()).read_bytes()
    except FileNotFoundError:
        return []
    bad, prev = [], None
    for n, line in enumerate(data.split(b"\n"), 1):
        if not line:
            continue
        want = hashlib.sha256(prev).hexdigest() if prev is not None else GENESIS
        try:
            e = json.loads(line)
            good = isinstance(e, dict) and e.get("prev") == want
        except ValueError:
            good = False
        if not good:
            bad.append(n)
        prev = line
    return bad


def audit_status(path=None):
    """{"ok", "bad" (verify_audit()), "lines" (non-empty lines), "last" (sha256 of the last line, or None)} for
    the Activity page and the .applied records."""
    try:
        data_ = Path(path or audit_path()).read_bytes()
    except FileNotFoundError:
        data_ = b""
    lines = [ln for ln in data_.split(b"\n") if ln]
    bad = verify_audit(path)
    return {"ok": not bad, "bad": bad, "lines": len(lines),
            "last": hashlib.sha256(lines[-1]).hexdigest() if lines else None}


def read_audit(limit=1000):
    """The last `limit` audit entries, newest first; malformed lines are skipped."""
    try:
        with open(audit_path(), encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-limit:]
    except FileNotFoundError:
        return []
    out = []
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict) and isinstance(e.get("action"), str):
            out.append(e)
    return out


# ---------------------------------------------------------------- input helpers


REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,19}$")  # never a leading "-": no argument can pass for a flag
MESSAGE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,199}$")
INVOICE_KEY_RE = re.compile(r"^[a-z]{12}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def fields(raw, allowed, required=None):
    """A dict of short strings with only `allowed` keys (all of `required`, default all)."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ActionError("malformed request")
    unknown = set(raw) - set(allowed)
    if unknown:
        raise ActionError("unexpected field")
    for k, v in raw.items():
        if not isinstance(v, str) or len(v) > 200:
            raise ActionError(f"bad {k}")
    for k in (allowed if required is None else required):
        if not raw.get(k, "").strip():
            raise ActionError(f"{k} is required")
    return {k: v.strip() for k, v in raw.items()}


def iso_date(value, today, back_days, what="date"):
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        raise ActionError(f"the {what} must be YYYY-MM-DD")
    try:
        d = datetime.date.fromisoformat(value)
    except ValueError:
        raise ActionError(f"the {what} is not a real date") from None
    if d > today:
        raise ActionError(f"the {what} is after today")
    if d < today - datetime.timedelta(days=back_days):
        raise ActionError(f"the {what} is too far back")
    return d.isoformat()


def today():
    return lm.today()


# ---------------------------------------------------------------- resolve a hand check


HAND_CHOICES = {  # choice -> (the owner's words in the preview, the ledger phrase; {d} is the date)
    "paid-in-full": ("paid in full", "paid in full {d}"),
    "deposit-kept": ("deposit kept on a cancelled booking", "deposit kept {d}"),
    "refunded": ("refunded", "refunded {d}"),
    "reinstated": ("reinstated: the booking is back on", "reinstated {d}"),
    "cancelled": ("cancelled", "cancelled {d}"),
    "payment-checked": ("payment checked by hand", "payment checked {d}"),
    "arranged-cash": ("balance arranged in cash on the day", "balance payable in cash on the day (arranged {d})"),
    "arranged-cheque": ("balance arranged by cheque on the day", "balance payable by cheque on the day (arranged {d})"),
}
HAND_BACK_DAYS = 730


def _hand_validate(raw):
    f = fields(raw, ("ref", "choice", "date"))
    if not REF_RE.fullmatch(f["ref"]):
        raise ActionError("unknown booking")
    if f["choice"] not in HAND_CHOICES:
        raise ActionError("unknown choice")
    day = iso_date(f["date"], today(), HAND_BACK_DAYS)
    # check_payments.py --owner writes only to <private dir>/bookings.csv (it refuses LCS_BOOKINGS_CSV): the
    # ledger this preview reads must be that same file
    if Path(cp.LEDGER).resolve() != (auth.private_dir() / "bookings.csv").resolve():
        raise ActionError("the ledger isn't the one in the private folder (LCS_BOOKINGS_CSV moves it)")
    rows = lm.read_csv(cp.LEDGER)
    row = next((r for r in rows if (r.get("booking_ref") or "").strip() == f["ref"]), None)
    if row is None:
        raise ActionError("unknown booking")
    words, phrase = HAND_CHOICES[f["choice"]]
    return {"input": {"ref": f["ref"], "choice": f["choice"], "date": day}, "ref": f["ref"],
            "words": words, "phrase": phrase.format(d=day), "first_name": data.dash.first_name(row.get("client_name"))}


def _hand_describe(c):
    return (f"Resolve the hand check on booking {c['ref']} ({c['first_name']}): {c['words']}. "
            f"Adds \"{c['phrase']} (owner)\" to its ledger notes.")


RESOLVE_HAND_CHECK = ScriptAction(
    "resolve-hand-check", CHECK_PAYMENTS, _hand_validate, _hand_describe,
    lambda c: ["--note", c["ref"], c["phrase"], "--owner"], owner_nonce=True, timeout=30,
    title="Resolve a hand check")


# ---------------------------------------------------------------- singer invoices


def invoice_key(message_id):
    return models.invoice_key(message_id)


def _singer_row(key):
    if not isinstance(key, str) or not INVOICE_KEY_RE.fullmatch(key):
        raise ActionError("unknown invoice")
    rows = [r for r in lm.read_csv(si.STORE) if invoice_key(r.get("message_id")) == key]
    if len(rows) != 1:
        raise ActionError("unknown invoice")
    r = rows[0]
    if not MESSAGE_ID_RE.fullmatch(r.get("message_id") or ""):
        raise ActionError("that invoice's id can't be passed safely")
    return r


def _singer_facts(r):
    return {"message_id": r["message_id"], "first_name": si.first_name(r.get("singer_name")),
            "amount": lm.money(r.get("amount_gbp")),
            "received": si.received_date(r).isoformat() if si.received_date(r) else "?",
            "last4": data.dash.digits4(r.get("bank_last4"))}


FP_PREFIX = 16  # characters of bank_fp shown in the summary and passed as --expect-fp: all of it
FP_RE = re.compile(r"^[0-9a-f]{16}$")


def _confirm_validate(raw):
    f = fields(raw, ("invoice",))
    r = _singer_row(f["invoice"])
    if not r.get("bank_fp"):
        raise ActionError("no bank details recorded on that invoice")
    if not FP_RE.fullmatch(r["bank_fp"]):
        raise ActionError("that invoice's bank fingerprint isn't in the expected form")
    if r.get("bank_confirmed") == "yes":
        raise ActionError("already confirmed")
    if si.is_withdrawn(r):
        raise ActionError("that invoice was withdrawn")
    return dict(_singer_facts(r), fp=r["bank_fp"][:FP_PREFIX], input={"invoice": f["invoice"]})


def _confirm_describe(c):
    return (f"Confirm the bank details on {c['first_name']}'s invoice of £{c['amount']:,.2f} received {c['received']} "
            f"(account ••••{c['last4']}, fingerprint {c['fp']}). Only after ringing {c['first_name']} on a number "
            f"you already hold: this account is trusted for them from now on. If the details change before this "
            f"runs, it refuses.")


def _settled_validate(raw):
    f = fields(raw, ("invoice", "date"))
    r = _singer_row(f["invoice"])
    if r.get("paid_on"):
        raise ActionError("already paid")
    if si.is_withdrawn(r):
        raise ActionError("that invoice was withdrawn")
    day = iso_date(f["date"], today(), 366)
    return dict(_singer_facts(r), date=day, input={"invoice": f["invoice"], "date": day})


def _settled_describe(c):
    return (f"Mark {c['first_name']}'s invoice of £{c['amount']:,.2f} (received {c['received']}) as paid by you on "
            f"{c['date']}, outside the bank feed. Its bank details stay unverified.")


def _withdrawn_validate(raw):
    f = fields(raw, ("invoice", "reason"))
    r = _singer_row(f["invoice"])
    if not si.REASON_RE.fullmatch(f["reason"]):
        raise ActionError("the reason must be one lower-case word, such as not-ours")
    if r.get("paid_on"):
        raise ActionError("already paid")
    if si.is_withdrawn(r):
        raise ActionError("already withdrawn")
    return dict(_singer_facts(r), reason=f["reason"], input={"invoice": f["invoice"], "reason": f["reason"]})


def _withdrawn_describe(c):
    return (f"Withdraw {c['first_name']}'s invoice of £{c['amount']:,.2f} (received {c['received']}) as sent to us "
            f"by mistake ({c['reason']}): it leaves the unpaid list, the money line and the bills.")


SINGER_CONFIRM = ScriptAction("singer-confirm", SINGER_INVOICES, _confirm_validate, _confirm_describe,
                              lambda c: ["confirm", c["message_id"], "--expect-fp", c["fp"]],
                              title="Confirm bank details")
SINGER_SETTLED = ScriptAction("singer-settled", SINGER_INVOICES, _settled_validate, _settled_describe,
                              lambda c: ["settled", c["message_id"], c["date"]], title="Mark a singer invoice paid")
SINGER_WITHDRAWN = ScriptAction("singer-withdrawn", SINGER_INVOICES, _withdrawn_validate, _withdrawn_describe,
                                lambda c: ["withdrawn", c["message_id"], c["reason"]],
                                title="Withdraw a singer invoice")


# ---------------------------------------------------------------- refresh


def _refresh_validate(raw):
    fields(raw, ())
    return {"input": {}}


REFRESH = ScriptAction(
    "refresh-data", DASHBOARD, _refresh_validate,
    lambda c: "Refresh the data now: rebuild the static dashboard (read-only) and clear the app's ten-minute bank cache.",
    lambda c: [], passkey=False, timeout=180, clears_cache=True, title="Refresh data now", lock="refresh")


# ---------------------------------------------------------------- Google Ads change sets


PROPOSAL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ADS_SCRIPT_RE = re.compile(r"^scripts/ads/[a-z0-9_]+\.py$")
BLOB_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
COMMIT_RE = BLOB_RE
TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._]{0,63}$")  # a proposal's argument: never a flag, a path or a space
MAX_ARGS = 12
GITHUB_URL = "https://github.com/lucawetherall/londonchoralservice.git"  # the only place Ads code comes from
GITHUB_BLOB = "https://github.com/lucawetherall/londonchoralservice/blob"  # for the preview's link to the file
TEST_UPSTREAM = None  # tests only: a local bare repo standing in for GitHub (a module variable, never read from the environment)
MAIN = "refs/heads/main"
DIFF_MAX = 6000  # characters of the script's last change shown in the preview
RUN_FOLDER_MAX = 20 * 1024 * 1024  # bytes of scripts/ written into a run folder
ADS_ENV_KEYS = ("HOME", "PATH", "LANG", "TZ", "GOOGLE_ADS_CONFIGURATION_FILE_PATH")
GIT_ENV_KEYS = ("HOME", "PATH", "LANG", "TZ", "https_proxy", "HTTPS_PROXY", "no_proxy", "NO_PROXY")
GIT_SAFE = ["-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "core.attributesFile=/dev/null",
            "--no-replace-objects"]
MIRROR_CONFIG = "[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = true\n"
GIT_RUNNER = subprocess.run  # the tests wrap this to see every git call
_VALIDATIONS = {}  # proposal id -> {"commit", "blob", "args", "sha256", "at" (monotonic)}
_VALIDATIONS_LOCK = threading.Lock()
_UNRECORDED = {"ids": set(), "runs": []}  # applies whose .applied record couldn't be written: refused until restart
clock = time.monotonic


class NotFetched(ActionError):
    """The mirror has never been fetched (a GET page doesn't fetch)."""


def proposals_dir():
    return auth.config_dir() / "proposals"


def mirror_dir():
    """The app's own bare mirror of GitHub's main: ~/lcs-private/command-centre/mirror.git (mode 700)."""
    return auth.config_dir() / "mirror.git"


def git_env():
    """A fixed environment for git: none of the caller's GIT_* (GIT_DIR, GIT_CONFIG_*, GIT_EXEC_PATH…) and no
    global or system config, replace refs off, prompts off. Only HOME, PATH, LANG, TZ and proxy settings pass."""
    env = {k: os.environ[k] for k in GIT_ENV_KEYS if k in os.environ}
    env.update(GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
               GIT_NO_REPLACE_OBJECTS="1")
    return env


def git_binary():
    return "/usr/bin/git" if os.path.exists("/usr/bin/git") else (shutil.which("git") or "git")


def _git(*args, timeout=15, text=True, input=None):
    """git in the mirror (--git-dir, never the working repo), hardened; ActionError if it doesn't answer."""
    argv = [git_binary(), f"--git-dir={mirror_dir()}", *GIT_SAFE, *args]
    kw = {"capture_output": True, "text": text, "timeout": timeout, "env": git_env(), "shell": False,
          "cwd": str(mirror_dir())}
    if input is None:
        kw["stdin"] = subprocess.DEVNULL
    else:
        kw["input"] = input
    try:
        return GIT_RUNNER(argv, **kw)
    except (OSError, subprocess.TimeoutExpired):
        raise ActionError("git didn't answer") from None


def ensure_mirror():
    """Create the mirror if it's missing; either way make it mode 700, this user's, a real folder (never a
    symlink), and put back its fixed config, dropping anything that could change what git reads: alternates,
    grafts, a shallow file, info/attributes."""
    d = mirror_dir()
    d.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(d.parent, 0o700)
    try:
        st = os.lstat(d)
    except FileNotFoundError:
        st = None
    if st is not None and (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()):
        raise ActionError("the app's git mirror isn't a folder of its own; nothing runs")
    if st is None or not (d / "objects").is_dir():
        env = git_env()
        try:
            p = GIT_RUNNER([git_binary(), f"--git-dir={d}", *GIT_SAFE, "init", "--quiet", "--bare"],
                           capture_output=True, timeout=15, env=env, shell=False, stdin=subprocess.DEVNULL,
                           cwd=str(d.parent))
        except (OSError, subprocess.TimeoutExpired):
            p = None
        if p is None or p.returncode != 0:
            raise ActionError("couldn't set up the app's git mirror; nothing runs")
    os.chmod(d, 0o700)
    cfg = d / "config"
    with contextlib.suppress(FileNotFoundError):
        if cfg.is_symlink() or not cfg.is_file():
            os.unlink(cfg)
    tmp = d / f".config.{secrets.token_hex(4)}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as f:
        f.write(MIRROR_CONFIG)
    os.replace(tmp, cfg)
    for rel in ("objects/info/alternates", "objects/info/http-alternates", "info/grafts", "info/attributes",
                "shallow"):
        with contextlib.suppress(FileNotFoundError, IsADirectoryError):
            os.unlink(d / rel)
    return d


def fetch_args():
    """The fetch: GitHub's main (the hard-coded URL) into the mirror's main, forced, with only https allowed (the
    file protocol off); in the tests only, from TEST_UPSTREAM with only the file protocol allowed."""
    if TEST_UPSTREAM is None:
        url, protocols = GITHUB_URL, ["-c", "protocol.https.allow=always", "-c", "protocol.file.allow=never"]
    else:
        url, protocols = str(TEST_UPSTREAM), ["-c", "protocol.file.allow=always"]
    return ["-c", "protocol.allow=never", *protocols, "-c", "http.followRedirects=false",
            "-c", "credential.helper=", "-c", "core.askPass=",
            "fetch", "--quiet", "--no-tags", "--no-write-fetch-head", "--no-recurse-submodules", "--no-auto-gc",
            url, f"+{MAIN}:{MAIN}"]


def fetch_mirror():
    """Fetch GitHub's main into the mirror, every time (the preview and the run each fetch: no stale ref is
    trusted). A failure refuses."""
    ensure_mirror()
    first = _git("rev-parse", "--verify", "--quiet", MAIN).returncode != 0
    try:
        p = _git(*fetch_args(), timeout=300 if first else 60)
    except ActionError:
        p = None
    if p is None or p.returncode != 0 or _git("rev-parse", "--verify", "--quiet", MAIN).returncode != 0:
        raise ActionError("couldn't verify against GitHub; nothing runs")


def git_blob_id(content, like):
    """Git's id for a blob with this content, in the hash the repo uses (like's length)."""
    header = f"blob {len(content)}\0".encode()
    return (hashlib.sha1 if len(like) == 40 else hashlib.sha256)(header + content).hexdigest()


def _empty_tree(like):
    """Git's empty tree, in the hash the repo uses."""
    header = b"tree 0\0"
    return (hashlib.sha1 if len(like) == 40 else hashlib.sha256)(header).hexdigest()


def script_change(changed_in, rel):
    """The script's last change on main, as git shows it: `git diff <changed_in>^ <changed_in> -- <rel>` (the
    empty tree for a first commit), no external diff or textconv, capped at DIFF_MAX characters."""
    parents = _git("log", "-1", "--format=%P", changed_in)
    if parents.returncode != 0:
        raise ActionError("git couldn't describe the script")
    base = (parents.stdout.split() or [_empty_tree(changed_in)])[0]
    diff = _git("diff", "--no-ext-diff", "--no-textconv", "--no-color", base, changed_in, "--", rel, timeout=30)
    if diff.returncode != 0:
        raise ActionError("git couldn't show the script's change")
    text = diff.stdout
    if len(text) > DIFF_MAX:
        text = f"{text[:DIFF_MAX]}\n… ({len(text) - DIFF_MAX:,} characters more: open it on GitHub)"
    return text


def commit_facts(commit, rel, blob, fetch=True):
    """What the server reads from the mirror about the script to run, or ActionError: the commit is on GitHub's
    main (as just fetched), holds `rel` as a regular file whose blob is `blob`; who last changed the script, when
    and in which commit, that change's diff and the script's docstring. `fetch` False (the Marketing page, a GET)
    uses the mirror as last fetched."""
    if not COMMIT_RE.fullmatch(commit or ""):
        raise ActionError("the proposal's commit isn't a full commit id")
    if fetch:
        fetch_mirror()
    else:
        if not (mirror_dir() / "objects").is_dir():
            raise NotFetched("not checked against GitHub yet")
        ensure_mirror()
        if _git("rev-parse", "--verify", "--quiet", MAIN).returncode != 0:
            raise NotFetched("not checked against GitHub yet")
    if _git("cat-file", "-e", f"{commit}^{{commit}}").returncode != 0 or \
            _git("merge-base", "--is-ancestor", commit, MAIN).returncode != 0:
        raise ActionError("the proposal's commit isn't on main at GitHub")
    tree = _git("ls-tree", commit, "--", rel)
    parts = tree.stdout.split()
    if tree.returncode != 0 or len(parts) < 4:
        raise ActionError("the script isn't in that commit")
    mode, kind, found = parts[0], parts[1], parts[2]
    if kind != "blob" or mode not in ("100644", "100755"):
        raise ActionError("the script must be a file in scripts/ads/")
    if found != blob:
        raise ActionError("the script at that commit isn't the blob the proposal names")
    log = _git("log", "-1", "--format=%H%x1f%an%x1f%as%x1f%s", commit, "--", rel)
    bits = log.stdout.strip().split("\x1f")
    if log.returncode != 0 or len(bits) != 4 or not COMMIT_RE.fullmatch(bits[0]):
        raise ActionError("git couldn't describe the script")
    src = _git("cat-file", "blob", blob, text=False)
    if src.returncode != 0 or len(src.stdout) > 512 * 1024 or git_blob_id(src.stdout, blob) != blob:
        raise ActionError("git couldn't read the script")
    try:
        doc = ast.get_docstring(ast.parse(src.stdout)) or ""
    except (SyntaxError, ValueError):
        raise ActionError("the script at that commit isn't valid Python") from None
    diff = script_change(bits[0], rel)
    return {"changed_in": bits[0][:12], "changed_in_full": bits[0], "author": _one_line(bits[1], 60),
            "date": bits[2], "subject": _one_line(bits[3], 80), "doc": _one_line(doc, 400) or "(no docstring)",
            "on_main": True, "diff": diff, "diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
            "link": f"{GITHUB_BLOB}/{commit}/{rel}"}


def applied_path(pid):
    return proposals_dir() / f"{pid}.applied"


def applied_records():
    """Every *.applied record (a dict; an unreadable one counts as {"unreadable": True})."""
    try:
        paths = sorted(p for p in proposals_dir().iterdir() if p.name.endswith(".applied"))
    except FileNotFoundError:
        return []
    out = []
    for p in paths:
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            out.append(rec if isinstance(rec, dict) else {"unreadable": True})
        except (OSError, ValueError):
            out.append({"unreadable": True})
    return out


def already_applied(blob, args):
    """True when this script blob with these arguments has been applied, under any proposal id (an .applied
    record, or an apply whose record couldn't be written since the app started)."""
    if (blob, list(args)) in _UNRECORDED["runs"]:
        return True
    return any(r.get("blob") == blob and list(r.get("args") or []) == list(args) for r in applied_records())


def is_applied(pid):
    return pid in _UNRECORDED["ids"] or applied_path(pid).exists()


def forget_unrecorded_applies():
    """Tests only (a restart does the same): drop the in-memory markers."""
    _UNRECORDED["ids"].clear()
    _UNRECORDED["runs"].clear()


def load_proposal(pid):
    """A checked proposal dict, or ActionError: <id>.json in proposals/, a regular file (never a symlink), this
    user's, mode exactly 600, with id matching its name, kind "ads", a script_path in scripts/ads/, the script's
    blob and the commit to run it from, and `args` (optional) a short list of simple tokens."""
    if not isinstance(pid, str) or not PROPOSAL_ID_RE.fullmatch(pid):
        raise ActionError("unknown proposal")
    path = proposals_dir() / f"{pid}.json"
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        raise ActionError("unknown proposal") from None
    except OSError:
        raise ActionError("the proposal file must be a plain file") from None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid():
            raise ActionError("the proposal file must be a plain file")
        if stat.S_IMODE(st.st_mode) != 0o600:
            raise ActionError("the proposal file must be mode 600")
        if st.st_size > 65536:
            raise ActionError("the proposal file is too big")
        raw = os.read(fd, 65537)
    finally:
        os.close(fd)
    try:
        p = json.loads(raw.decode("utf-8"))
    except ValueError:
        raise ActionError("the proposal file isn't valid JSON") from None
    if not isinstance(p, dict) or p.get("id") != pid:
        raise ActionError("the proposal's id doesn't match its file name")
    if p.get("kind") != "ads":
        raise ActionError("not an Ads proposal")
    unknown = set(p) - {"id", "kind", "title", "summary", "script_path", "created", "script_blob", "commit", "args"}
    if unknown:
        raise ActionError("the proposal has an unexpected field")
    for k, most in (("title", 120), ("summary", 1000), ("script_path", 100), ("created", 40)):
        if not isinstance(p.get(k), str) or not p[k].strip() or len(p[k]) > most:
            raise ActionError(f"the proposal's {k} is missing or too long")
    if not ADS_SCRIPT_RE.fullmatch(p["script_path"]):
        raise ActionError("the script must be a file in scripts/ads/")
    if not isinstance(p.get("script_blob"), str) or not BLOB_RE.fullmatch(p["script_blob"]):
        raise ActionError("the proposal must pin the script's blob (script_blob)")
    if not isinstance(p.get("commit"), str) or not COMMIT_RE.fullmatch(p["commit"]):
        raise ActionError("the proposal must pin a full commit id (commit)")
    args = p.get("args", [])
    if not isinstance(args, list) or len(args) > MAX_ARGS or not all(
            isinstance(a, str) and TOKEN_RE.fullmatch(a) for a in args):
        raise ActionError("the proposal's args must be a short list of simple words or numbers")
    out = {k: p[k].strip() for k in ("id", "title", "summary", "script_path", "created")}
    return dict(out, blob=p["script_blob"], commit=p["commit"], args=list(args))


def list_proposals():
    """Every proposals/*.json, each with its problem (a refusal reason) or None, applied and validated flags."""
    try:
        names = sorted(p.name for p in proposals_dir().iterdir() if p.name.endswith(".json"))
    except FileNotFoundError:
        return []
    out = []
    for name in names:
        pid = name[:-len(".json")]
        good_id = bool(PROPOSAL_ID_RE.fullmatch(pid))
        entry = {"id": pid if good_id else "", "title": pid if good_id else "(unreadable name)", "summary": "",
                 "created": "", "script_path": "", "problem": None,
                 "applied": good_id and is_applied(pid), "validated": False}
        try:
            p = load_proposal(pid)
            entry.update({k: p[k] for k in ("id", "title", "summary", "script_path", "created")})
            if not entry["applied"] and already_applied(p["blob"], p["args"]):
                raise ActionError("this script with these arguments was already applied")
            with contextlib.suppress(NotFetched):  # checked against GitHub when the owner opens it
                commit_facts(p["commit"], p["script_path"], p["blob"], fetch=False)
        except ActionError as e:
            entry["problem"] = e.reason
        with _VALIDATIONS_LOCK:
            v = _VALIDATIONS.get(pid)
        entry["validated"] = bool(v and clock() - v["at"] < VALIDATION_TTL)
        out.append(entry)
    return out


def _ads_common(raw):
    f = fields(raw, ("proposal",))
    p = load_proposal(f["proposal"])
    if is_applied(p["id"]):
        raise ActionError("already applied")
    if already_applied(p["blob"], p["args"]):
        raise ActionError("this script with these arguments was already applied")
    facts = commit_facts(p["commit"], p["script_path"], p["blob"])
    return dict(p, facts=facts, input={"proposal": p["id"]})


def _one_line(text, most):
    text = " ".join(str(text).split())
    return text if len(text) <= most else text[:most - 1] + "…"


def _facts_text(c):
    f = c["facts"]
    return (f"Script: {c['script_path']} at commit {c['commit'][:12]} (on main at GitHub: "
            f"{'yes' if f['on_main'] else 'no'}, fetched just now), last changed by {f['author']} on {f['date']} in "
            f"{f['changed_in']} (\"{f['subject']}\"); blob {c['blob'][:12]}.\n"
            f"Its code change is shown below (diff sha256 {f['diff_sha256'][:16]}, {len(f['diff']):,} characters); "
            f"the file on GitHub: {f['link']}\n"
            f"What the script says it does: {f['doc']}\n"
            f"Claude's description: \"{_one_line(c['title'], 80)}\": {_one_line(c['summary'], 300)}")


def _validate_validate(raw):
    return _ads_common(raw)


def _validate_describe(c):
    return (f"Check this Ads change set with Google, validate only (nothing changes).\n{_facts_text(c)}\n"
            f"It runs from that commit's scripts/, written out of the app's own mirror of GitHub.")


def _validate_after(c, code, raw, who):
    if code != 0:
        with _VALIDATIONS_LOCK:
            _VALIDATIONS.pop(c["id"], None)
        return None
    with _VALIDATIONS_LOCK:
        _VALIDATIONS[c["id"]] = {"commit": c["commit"], "blob": c["blob"], "args": list(c["args"]),
                                 "sha256": hashlib.sha256(raw).hexdigest(), "at": clock()}
    return {"action": "ads-apply", "input": {"proposal": c["id"]}, "label": "Apply this change set"}


def _apply_validate(raw):
    c = _ads_common(raw)
    with _VALIDATIONS_LOCK:
        v = _VALIDATIONS.get(c["id"])
        v = dict(v) if v else None
    if not v or clock() - v["at"] >= VALIDATION_TTL:
        raise ActionError("validate this change set first (a validate run lasts 15 minutes)", status=409)
    if (v["commit"], v["blob"], v["args"]) != (c["commit"], c["blob"], c["args"]):
        raise ActionError("the script changed since it was validated; validate again", status=409)
    return dict(c, validated_sha=v["sha256"], validated_at=v["at"])


def _apply_describe(c):
    return (f"Apply this Ads change set for real. It is the run you validated: the same commit, blob and arguments "
            f"(the validate output's sha256 began {c['validated_sha'][:16]}).\n{_facts_text(c)}\n"
            f"The script keeps its £5 daily cap and logs the change in logs/ads-changes.md.")


def _apply_claim(c):
    """Take the validate record for this apply, atomically: it must still be the one the summary was built from.
    A second apply (or one racing this) finds nothing and is refused."""
    with _VALIDATIONS_LOCK:
        v = _VALIDATIONS.pop(c["id"], None)
    if not v or (v["commit"], v["blob"], v["args"], v["sha256"], v["at"]) != (
            c["commit"], c["blob"], c["args"], c["validated_sha"], c["validated_at"]):
        raise ActionError("validate this change set again", status=409)


UNRECORDED_WARNING = ("applied, but the record couldn't be saved: DO NOT re-apply. Check Google Ads and "
                      "logs/ads-changes.md; the app refuses this change set again until it restarts.")


def _apply_after(c, code, raw, who):
    """After a successful apply: the .applied record, with the audit chain's head at that moment. If the record
    can't be written, a warning (a string: ScriptAction.perform puts it in front of the output) and an in-memory
    marker that refuses the same proposal, or the same blob and arguments, until the app restarts."""
    if code != 0:
        return None
    try:
        head = audit_status()["last"]
    except OSError:
        head = None
    try:
        write_private(applied_path(c["id"]), {
            "applied_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "proposal": c["id"], "commit": c["commit"], "blob": c["blob"], "args": list(c["args"]),
            "validated_sha256": c["validated_sha"], "output_sha256": hashlib.sha256(raw).hexdigest(),
            "audit_sha256": head, "login": who.get("login", ""), "passkey": who.get("passkey")})
    except Exception:  # noqa: BLE001 (anything: the change is live at Google either way)
        _UNRECORDED["ids"].add(c["id"])
        _UNRECORDED["runs"].append((c["blob"], list(c["args"])))
        return UNRECORDED_WARNING
    return None


def ads_env(root):
    """Only what an Ads script needs: HOME, PATH, LANG, TZ, the Ads config path, the private dir, the change log
    (the repo's logs/ads-changes.md: the run folder has no logs/), and Python told to ignore user site-packages,
    write no bytecode and look for none outside an empty folder."""
    env = {k: os.environ[k] for k in ADS_ENV_KEYS if k in os.environ}
    env["LCS_PRIVATE_DIR"] = str(auth.private_dir())
    env["LCS_ADS_LOG"] = str(Path(REPO) / "logs" / "ads-changes.md")
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(root) / "pycache")
    return env


def runs_dir():
    return auth.config_dir() / "runs"


def _tree_files(commit):
    """[(mode, blob id, path)] for the regular files under scripts/ at `commit`, from `git ls-tree -r -z` in the
    mirror. Symlinks (120000) and submodules (160000) are left out; an odd path refuses."""
    ls = _git("ls-tree", "-r", "-z", commit, "--", "scripts/", text=False, timeout=30)
    if ls.returncode != 0:
        raise ActionError("git couldn't list that commit's scripts")
    out = []
    for rec in ls.stdout.split(b"\0"):
        if not rec:
            continue
        meta, _, raw_path = rec.partition(b"\t")
        bits = meta.split()
        if len(bits) != 3:
            raise ActionError("git's listing of that commit didn't parse")
        mode, kind, oid = (b.decode("ascii", "replace") for b in bits)
        if kind != "blob" or mode not in ("100644", "100755"):
            continue
        try:
            path = raw_path.decode("utf-8")
        except UnicodeDecodeError:
            raise ActionError("a file name in scripts/ isn't UTF-8") from None
        parts = path.split("/")
        if parts[0] != "scripts" or any(x in ("", ".", "..") or "\\" in x for x in parts) or not BLOB_RE.fullmatch(oid):
            raise ActionError("a file name in scripts/ isn't safe to write")
        out.append((mode, oid, path))
    return out


def _read_blobs(ids):
    """{id: bytes} through one `git cat-file --batch` (no filters, no textconv), each checked against its id."""
    if not ids:
        return {}
    p = _git("cat-file", "--batch", text=False, input=("\n".join(ids) + "\n").encode("ascii"), timeout=60)
    if p.returncode != 0:
        raise ActionError("git couldn't read that commit's scripts")
    data_, pos, out = p.stdout, 0, {}
    for oid in ids:
        nl = data_.find(b"\n", pos)
        head = data_[pos:nl].decode("ascii", "replace").split() if nl >= 0 else []
        if len(head) != 3 or head[0] != oid or head[1] != "blob" or not head[2].isdigit():
            raise ActionError("git's copy of that commit didn't parse")
        size = int(head[2])
        body = data_[nl + 1:nl + 1 + size]
        if len(body) != size or data_[nl + 1 + size:nl + 2 + size] != b"\n" or git_blob_id(body, oid) != oid:
            raise ActionError("a file in that commit isn't the blob git named")
        out[oid] = body
        pos = nl + 2 + size
    return out


@contextlib.contextmanager
def run_folder(commit, rel, blob):
    """That commit's scripts/, written out of the mirror into a fresh mode-700 folder under the app's config dir:
    `git ls-tree -r` for the list, `git cat-file --batch` for the bytes (no checkout, no archive, so no filters or
    attributes), each file's bytes checked against its blob id, regular files only (no symlinks, no submodules),
    created exclusively and never through a symlink. The script must be the pinned blob. Removed afterwards."""
    files = _tree_files(commit)
    script = next((f for f in files if f[2] == rel), None)
    if script is None:
        raise ActionError("the script isn't in that commit")
    if script[1] != blob:
        raise ActionError("the script at that commit isn't the pinned blob")
    blobs = _read_blobs(sorted({oid for _, oid, _ in files}))
    if sum(len(b) for b in blobs.values()) > RUN_FOLDER_MAX:
        raise ActionError("that commit's scripts/ is too big to run")
    base = runs_dir()
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(base, 0o700)
    root = Path(tempfile.mkdtemp(prefix="ads-", dir=base))
    try:
        (root / "pycache").mkdir(mode=0o700)
        for mode, oid, path in files:
            target = root / path
            d = root
            for part in path.split("/")[:-1]:
                d = d / part
                with contextlib.suppress(FileExistsError):
                    d.mkdir(mode=0o700)
                if d.is_symlink() or not d.is_dir():
                    raise ActionError("a folder in scripts/ isn't safe to write")
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o700 if mode == "100755" else 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(blobs[oid])
        if git_blob_id((root / rel).read_bytes(), blob) != blob:
            raise ActionError("the script at that commit isn't the pinned blob")
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


archived = run_folder  # the name the earlier review's proofs of concept call


@dataclasses.dataclass(frozen=True)
class ProposalScriptAction(ScriptAction):
    """Runs the proposal's own script from its pinned commit on GitHub's main, written out of the app's mirror
    (commit_facts and run_folder()), never from the working tree. Its `args` are the proposal's own, then one
    fixed flag: --validate-only (which only proposal-aware scripts accept) or --apply."""
    claim_fn: Optional[Callable] = None

    def argv(self, cleaned, root=None):
        base = Path(root) if root else Path("<run folder>")
        return [sys.executable, "-E", "-s", "-B", "-X", f"pycache_prefix={base / 'pycache'}",
                str(base / cleaned["script_path"]), *self.args(cleaned)]

    def shown(self, cleaned):
        return [PY_SHOWN, "-E", "-s", "-B", cleaned["script_path"], *self.args(cleaned)]

    def claim(self, cleaned):
        if self.claim_fn:
            self.claim_fn(cleaned)

    def execute_script(self, cleaned):
        with run_folder(cleaned["commit"], cleaned["script_path"], cleaned["blob"]) as root:
            return run_argv(self.argv(cleaned, root), self.timeout, cwd=root, env=ads_env(root))

    def code(self, cleaned):
        """For the preview: the script's last change on main (bound to the summary by its sha256) and its link."""
        f = cleaned["facts"]
        return {"head": f"{f['changed_in']} by {f['author']} on {f['date']}: {f['subject']}", "diff": f["diff"],
                "link": f["link"]}

    def show(self, raw):
        return head_and_tail(raw.decode("utf-8", "replace"))


ADS_VALIDATE = ProposalScriptAction("ads-validate", "scripts/ads/", _validate_validate, _validate_describe,
                                    lambda c: [*c["args"], "--validate-only"], timeout=180, after=_validate_after,
                                    title="Check an Ads change set")
ADS_APPLY = ProposalScriptAction("ads-apply", "scripts/ads/", _apply_validate, _apply_describe,
                                 lambda c: [*c["args"], "--apply"], timeout=180, after=_apply_after,
                                 title="Apply an Ads change set", claim_fn=_apply_claim)


def reset_validations():
    with _VALIDATIONS_LOCK:
        _VALIDATIONS.clear()


# ---------------------------------------------------------------- the 2026 Books import approval


BOOKS_YEAR = 2026
BOOKS_INSTRUCTION = ("Create one draft invoice per booking in Zoho Books from the dry run at "
                     "~/lcs-private/books-import-2026.json, dated at each booking's own invoice date, as "
                     "MANUAL-ACTIONS-REQUIRED.md section 20 describes. Only while the dry run's sha256 still matches "
                     "this record; never send, void or record a payment.")


def books_dry_run():
    return auth.private_dir() / f"books-import-{BOOKS_YEAR}.json"


def books_approval_path():
    return auth.config_dir() / "approvals" / f"books-import-{BOOKS_YEAR}.json"


def books_status():
    """{"dry_run": bool, "approved_at": str or None} for Today."""
    approved = None
    try:
        with open(books_approval_path(), encoding="utf-8") as f:
            approved = str(json.load(f).get("approved_at") or "") or None
    except (OSError, ValueError, AttributeError):
        approved = None
    path = books_dry_run()
    return {"dry_run": path.is_file() and not path.is_symlink(), "approved_at": approved}


def _books_validate(raw):
    fields(raw, ())
    path = books_dry_run()
    if path.is_symlink() or not path.is_file():
        raise ActionError("no dry run at ~/lcs-private/books-import-2026.json")
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ActionError("the dry run is too big")
    blob = path.read_bytes()
    try:
        parsed = json.loads(blob.decode("utf-8"))
    except ValueError:
        raise ActionError("the dry run isn't valid JSON") from None
    if isinstance(parsed, list):
        items = parsed
    elif isinstance(parsed, dict):
        lists = [v for v in parsed.values() if isinstance(v, list)]
        items = lists[0] if lists else []
    else:
        items = []
    if books_approval_path().exists():
        raise ActionError("already approved")
    refs = [_books_ref(i) for i in items]
    amounts = [_books_amount(i) for i in items]
    total = sum(amounts) if items and all(a is not None for a in amounts) else None
    return {"input": {}, "sha256": hashlib.sha256(blob).hexdigest(), "entries": len(items), "total": total,
            "first_ref": refs[0] if refs else None, "last_ref": refs[-1] if refs else None}


BOOKS_REF_KEYS = ("booking_ref", "ref", "reference", "invoice_number")
BOOKS_AMOUNT_KEYS = ("total", "total_gbp", "amount", "amount_gbp", "value_gbp")


def _books_ref(item):
    if isinstance(item, dict):
        for k in BOOKS_REF_KEYS:
            v = item.get(k)
            if isinstance(v, (str, int)) and REF_RE.fullmatch(str(v).strip()):
                return str(v).strip()
    return "?"


def _books_amount(item):
    if isinstance(item, dict):
        for k in BOOKS_AMOUNT_KEYS:
            v = item.get(k)
            if isinstance(v, bool):
                continue
            try:
                return float(str(v).replace("£", "").replace(",", "")) if v not in (None, "") else None
            except ValueError:
                return None
    return None


def _books_preview(c):
    total = f"£{c['total']:,.2f} in total" if c["total"] is not None else "no total (some entries carry no amount)"
    span = f"first {c['first_ref']}, last {c['last_ref']}" if c["entries"] else "no entries"
    return (f"Approve the {BOOKS_YEAR} Books import: the dry run at ~/lcs-private/books-import-{BOOKS_YEAR}.json "
            f"({c['entries']} entries, {total}; {span}; sha256 {c['sha256'][:16]}). This writes an approval record only; the chat "
            f"(phase 4) or a session you start creates the draft invoices in Books, and only while the dry run is "
            f"unchanged. The app never calls Books.\n"
            f"Writes: ~/lcs-private/command-centre/approvals/books-import-{BOOKS_YEAR}.json")


def write_private(path, payload, exclusive=False):
    """JSON, mode 600, in a mode-700 directory; atomic (or refused if it exists, when `exclusive`)."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    target = path if exclusive else path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    try:
        fd = os.open(target, flags, 0o600)
    except FileExistsError:
        raise ActionError("already recorded") from None
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    if not exclusive:
        os.replace(target, path)


def _books_run(c, who):
    write_private(books_approval_path(), {
        "approved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "approved_by": who.get("login", ""), "passkey": who.get("passkey"),
        "dry_run": f"~/lcs-private/books-import-{BOOKS_YEAR}.json", "dry_run_sha256": c["sha256"],
        "entries": c["entries"], "total_gbp": c["total"], "first_ref": c["first_ref"], "last_ref": c["last_ref"],
        "instruction": BOOKS_INSTRUCTION, "status": "approved"}, exclusive=True)
    return "approval recorded"


BOOKS_IMPORT = LocalAction("approve-books-import", _books_validate, _books_preview, _books_run,
                           title="Approve the Books import")


# ---------------------------------------------------------------- todo-tick (phase 2, no passkey)


def _todo_validate(raw):
    if not isinstance(raw, dict):
        raise ActionError("malformed request")
    key, done = raw.get("key"), raw.get("done")
    if not isinstance(key, str) or not todo.KEY_RE.fullmatch(key):
        raise ActionError("unknown to-do item")
    if done not in ("yes", "no"):
        raise ActionError("done must be yes or no")
    item = next((i for i in todo.read_items() if i["key"] == key), None)
    if item is None:
        raise ActionError("unknown to-do item")
    return {"key": key, "done": done == "yes", "item": item, "input": {"key": key, "done": done}}


def _todo_preview(c):
    verb = "tick" if c["done"] else "untick"
    return f"{verb} to-do {c['item']['number']}: {c['item']['title']}"[:auth.MAX_SUMMARY]


def _todo_run(c, who=None):
    todo.set_tick(c["key"], c["done"])


TODO_TICK = LocalAction("todo-tick", _todo_validate, _todo_preview, _todo_run, passkey=False, title="Tick a to-do")
REGISTRY = {a.name: a for a in (TODO_TICK, RESOLVE_HAND_CHECK, SINGER_CONFIRM, SINGER_SETTLED, SINGER_WITHDRAWN,
                                REFRESH, ADS_VALIDATE, ADS_APPLY, BOOKS_IMPORT)}
ROUTED = {n for n in REGISTRY if n != "todo-tick"}  # the JSON routes; the tick keeps its own form route
