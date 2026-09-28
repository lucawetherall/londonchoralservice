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
  variable, stdin /dev/null (or the owner nonce), a timeout, one action at a time, and no retries.
- Output is scrubbed (lcs_mcp's approach: URLs, token-like values; plus any run of six or more digits) and trimmed
  before it reaches the page; the audit keeps only its sha256.
- The owner-only hand-check phrases go through `check_payments.py --note … --owner`, which refuses unless it gets
  the one-time owner nonce written here (owner_nonce(): the file holds sha256(nonce), the nonce goes over the pipe).
- Ads change sets come from ~/lcs-private/command-centre/proposals/<id>.json (mode 600) and run only a script that
  is inside scripts/ads/, tracked by git and unmodified. The apply step is bound to the validate run's output hash.
"""

import contextlib
import dataclasses
import datetime
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
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from . import auth, data, models, todo

REPO = Path(__file__).resolve().parent.parent  # read at call time (the ads tests point it at a temp git repo)
PY_SHOWN = ".venv/bin/python"
CHECK_PAYMENTS = "scripts/bookings/check_payments.py"
SINGER_INVOICES = "scripts/bookings/singer_invoices.py"
DASHBOARD = "scripts/reports/dashboard.py"
OUTPUT_MAX = 6000  # characters of scrubbed output shown (the tail)
RUN_WAIT = 5  # seconds to wait for another action to finish before refusing
VALIDATION_TTL = 15 * 60  # seconds an ads validate run stays good for its apply
RUNNER = subprocess.run  # the tests replace this with a recorder
FIXED_FLAGS = {"--note", "--owner", "--apply"}  # the only arguments that may start with "-"; the rest are validated values
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
    """A write to the app's own files (no subprocess). `run(cleaned) -> str` returns a line for the result."""
    name: str
    validate: Callable  # raw input (a dict of strings) -> cleaned input, or ActionError
    preview: Callable   # cleaned input -> the summary, written by the server
    run: Callable       # cleaned input -> None or a short message
    passkey: bool = True
    title: str = ""

    def build(self, raw):
        """The server-built auth.Action for this input (what a passkey, when needed, binds)."""
        return auth.Action(self.name, self.preview(self.validate(raw)))

    def command(self, cleaned):
        return None

    def perform(self, cleaned, action, user, passkey_id=None):
        try:
            message = self.run(cleaned)
        except ActionError as e:
            audit(action, user, f"refused: {e.reason}", input=public(cleaned), passkey=passkey_id)
            raise
        except Exception as e:
            audit(action, user, f"failed: {type(e).__name__}", input=public(cleaned), passkey=passkey_id)
            raise
        audit(action, user, "ok", input=public(cleaned), passkey=passkey_id)
        return Result(True, None, message or "done", action.summary)

    def execute(self, raw, user):
        """Validate, run and log an action that needs no passkey (the to-do tick's form route)."""
        if self.passkey:
            raise ActionError("this action needs a passkey", status=403)
        cleaned = self.validate(raw)
        action = auth.Action(self.name, self.preview(cleaned))
        self.perform(cleaned, action, user)
        return action


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

    def perform(self, cleaned, action, user, passkey_id=None):
        argv = self.argv(cleaned)
        for a in argv[2:]:  # belt and braces: the validators already refuse these
            if not isinstance(a, str) or "\x00" in a or (a.startswith("-") and a not in FIXED_FLAGS):
                raise ActionError("bad argument")
        audit(action, user, "started", input=public(cleaned), passkey=passkey_id)
        if self.owner_nonce:
            with owner_nonce() as nonce:
                code, raw = run_argv(argv, self.timeout, stdin_text=nonce + "\n")
        else:
            code, raw = run_argv(argv, self.timeout)
        digest = hashlib.sha256(raw).hexdigest()
        ok = code == 0
        audit(action, user, "ok" if ok else ("timed out" if code is None else "failed"), input=public(cleaned),
              exit_code=code, output_sha256=digest, passkey=passkey_id)
        nxt = self.after(cleaned, code, raw) if self.after else None
        return Result(ok, code, scrub(raw.decode("utf-8", "replace")), action.summary, nxt)


def public(cleaned):
    """The input fields as the request gave them (validated), for the audit log."""
    value = cleaned.get("input") if isinstance(cleaned, dict) else None
    return dict(value) if isinstance(value, dict) else None


# ---------------------------------------------------------------- running


_RUN_LOCK = threading.Lock()


def clean_env():
    """The app's environment minus every CC_* variable (the dev login, the port, the bank switch)."""
    return {k: v for k, v in os.environ.items() if not k.startswith("CC_")}


def run_argv(argv, timeout, stdin_text=None):
    """(exit code or None on a timeout, stdout+stderr bytes). An argv list, never a shell."""
    if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
        raise ActionError("bad command")
    kw = {"cwd": str(REPO), "env": clean_env(), "capture_output": True, "timeout": timeout, "shell": False}
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


def scrub(text, extra_secrets=()):
    """Output safe to show: URLs (lcs_mcp's rule), bearer and key=value secrets, long mixed-case token-shaped
    strings, the given secrets, and any run of six or more digits (account numbers, message ids) masked; then
    trimmed to its last OUTPUT_MAX characters."""
    text = URL_RE.sub("<url>", str(text))
    for s in extra_secrets:
        if s and len(s) >= 6:
            text = text.replace(s, "<redacted>")
    text = BEARER_RE.sub(lambda m: f"{m.group(1)} <redacted>", text)
    text = SECRET_KV_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}<redacted>", text)
    text = TOKENISH_RE.sub("<redacted>", text)
    text = DIGITS_RE.sub("••••••", text)
    text = text.strip()
    if len(text) > OUTPUT_MAX:
        text = "…\n" + text[-OUTPUT_MAX:]
    return text


def run_action(defn, raw, user, credential=None, passkeys=None):
    """Validate, check the passkey when the action needs one, then perform, under the one-at-a-time lock.
    Raises ActionError or auth.PasskeyError (both logged when an Action could be built)."""
    cleaned = defn.validate(raw)
    action = auth.Action(defn.name, defn.preview(cleaned))
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
    if not _RUN_LOCK.acquire(timeout=RUN_WAIT):
        audit(action, user, "refused: another action is running", input=public(cleaned), passkey=passkey_id)
        raise ActionError("another action is running; try again in a moment", status=409)
    try:
        return defn.perform(cleaned, action, user, passkey_id)
    finally:
        _RUN_LOCK.release()


# ---------------------------------------------------------------- audit


def audit_path():
    return auth.config_dir() / "audit.jsonl"


def audit(action, user, result, **extra):
    entry = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             "action": action.name, "summary": action.summary, "login": (user or {}).get("login", ""),
             "result": result}
    for k, v in extra.items():
        if v is not None:
            entry[k] = v[:8] if k == "passkey" and isinstance(v, str) else v
    d = auth.config_dir()
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(audit_path(), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


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


def _confirm_validate(raw):
    f = fields(raw, ("invoice",))
    r = _singer_row(f["invoice"])
    if not r.get("bank_fp"):
        raise ActionError("no bank details recorded on that invoice")
    if r.get("bank_confirmed") == "yes":
        raise ActionError("already confirmed")
    if si.is_withdrawn(r):
        raise ActionError("that invoice was withdrawn")
    return dict(_singer_facts(r), input={"invoice": f["invoice"]})


def _confirm_describe(c):
    return (f"Confirm the bank details on {c['first_name']}'s invoice of £{c['amount']:,.2f} received {c['received']} "
            f"(account ••••{c['last4']}). Only after ringing {c['first_name']} on a number you already hold: "
            f"this account is trusted for them from now on.")


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
                              lambda c: ["confirm", c["message_id"]], title="Confirm bank details")
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
    lambda c: [], passkey=False, timeout=180, clears_cache=True, title="Refresh data now")


# ---------------------------------------------------------------- Google Ads change sets


PROPOSAL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ADS_SCRIPT_RE = re.compile(r"^scripts/ads/[a-z0-9_]+\.py$")
BLOB_RE = re.compile(r"^[0-9a-f]{40,64}$")
_VALIDATIONS = {}  # proposal id -> {"blob", "sha256", "at" (monotonic)}
_VALIDATIONS_LOCK = threading.Lock()
clock = time.monotonic


def proposals_dir():
    return auth.config_dir() / "proposals"


def _git(*args):
    git = shutil.which("git") or "/usr/bin/git"
    try:
        return subprocess.run([git, "-C", str(REPO), *args], capture_output=True, text=True, timeout=15,
                              env=clean_env(), stdin=subprocess.DEVNULL, shell=False)
    except (OSError, subprocess.TimeoutExpired):
        raise ActionError("git didn't answer") from None


def script_blob(rel):
    """The committed blob id of a script under scripts/ads/, or ActionError: the path must match the pattern, be a
    regular file (no symlink, and resolve to itself inside scripts/ads/), be tracked, and have no change in the
    working tree or the index."""
    if not isinstance(rel, str) or not ADS_SCRIPT_RE.fullmatch(rel):
        raise ActionError("the script must be a file in scripts/ads/")
    base = (Path(REPO) / "scripts" / "ads").resolve()
    path = Path(REPO) / rel
    if path.is_symlink() or not path.is_file() or path.resolve().parent != base:
        raise ActionError("the script must be a file in scripts/ads/")
    if _git("ls-files", "--error-unmatch", "--", rel).returncode != 0:
        raise ActionError("the script isn't committed")
    status = _git("status", "--porcelain", "--untracked-files=all", "--", rel)
    if status.returncode != 0 or status.stdout.strip():
        raise ActionError("the script has uncommitted changes")
    blob = _git("rev-parse", f"HEAD:{rel}")
    value = blob.stdout.strip()
    if blob.returncode != 0 or not BLOB_RE.fullmatch(value):
        raise ActionError("the script isn't committed")
    return value


def applied_path(pid):
    return proposals_dir() / f"{pid}.applied"


def load_proposal(pid):
    """A checked proposal dict, or ActionError: <id>.json in proposals/, a regular file (never a symlink), this
    user's, mode exactly 600, with id matching its name, kind "ads" and a script_path in scripts/ads/."""
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
    for k, most in (("title", 120), ("summary", 1000), ("script_path", 100), ("created", 40)):
        if not isinstance(p.get(k), str) or not p[k].strip() or len(p[k]) > most:
            raise ActionError(f"the proposal's {k} is missing or too long")
    if not ADS_SCRIPT_RE.fullmatch(p["script_path"]):
        raise ActionError("the script must be a file in scripts/ads/")
    return {k: p[k].strip() for k in ("id", "title", "summary", "script_path", "created")}


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
                 "applied": good_id and applied_path(pid).exists(), "validated": False}
        try:
            entry.update(load_proposal(pid))
            script_blob(entry["script_path"])
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
    if applied_path(p["id"]).exists():
        raise ActionError("already applied")
    blob = script_blob(p["script_path"])
    return dict(p, blob=blob, input={"proposal": p["id"]})


def _one_line(text, most):
    text = " ".join(str(text).split())
    return text if len(text) <= most else text[:most - 1] + "…"


def _validate_validate(raw):
    return _ads_common(raw)


def _validate_describe(c):
    return (f"Check the Ads change set \"{_one_line(c['title'], 80)}\" with Google, validate only (nothing changes): "
            f"{_one_line(c['summary'], 160)} Script at git blob {c['blob'][:12]}.")


def _validate_after(c, code, raw):
    if code != 0:
        with _VALIDATIONS_LOCK:
            _VALIDATIONS.pop(c["id"], None)
        return None
    with _VALIDATIONS_LOCK:
        _VALIDATIONS[c["id"]] = {"blob": c["blob"], "sha256": hashlib.sha256(raw).hexdigest(), "at": clock()}
    return {"action": "ads-apply", "input": {"proposal": c["id"]}, "label": "Apply this change set"}


def _apply_validate(raw):
    c = _ads_common(raw)
    with _VALIDATIONS_LOCK:
        v = _VALIDATIONS.get(c["id"])
    if not v or clock() - v["at"] >= VALIDATION_TTL:
        raise ActionError("validate this change set first (a validate run lasts 15 minutes)", status=409)
    if v["blob"] != c["blob"]:
        raise ActionError("the script changed since it was validated; validate again", status=409)
    return dict(c, validated_sha=v["sha256"])


def _apply_describe(c):
    return (f"Apply the Ads change set \"{_one_line(c['title'], 80)}\" for real. It is the script you validated "
            f"(git blob {c['blob'][:12]}; the validate output's sha256 began {c['validated_sha'][:16]}). The script "
            f"keeps its £5 daily cap and logs the change in logs/ads-changes.md.")


def _apply_after(c, code, raw):
    with _VALIDATIONS_LOCK:
        _VALIDATIONS.pop(c["id"], None)  # one apply per validate
    if code == 0:
        write_private(applied_path(c["id"]), {
            "applied_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "blob": c["blob"], "validated_sha256": c["validated_sha"], "output_sha256": hashlib.sha256(raw).hexdigest()})
    return None


@dataclasses.dataclass(frozen=True)
class ProposalScriptAction(ScriptAction):
    """Runs the proposal's own script, which the validator has checked (script_blob): inside scripts/ads/,
    committed, unmodified. The scripts' default run is validate-only; `--apply` applies."""

    def argv(self, cleaned):
        return [sys.executable, str(Path(REPO) / cleaned["script_path"]), *self.args(cleaned)]

    def shown(self, cleaned):
        return [PY_SHOWN, cleaned["script_path"], *self.args(cleaned)]


ADS_VALIDATE = ProposalScriptAction("ads-validate", "scripts/ads/", _validate_validate, _validate_describe,
                                    lambda c: [], timeout=180, after=_validate_after, title="Check an Ads change set")
ADS_APPLY = ProposalScriptAction("ads-apply", "scripts/ads/", _apply_validate, _apply_describe,
                                 lambda c: ["--apply"], timeout=180, after=_apply_after,
                                 title="Apply an Ads change set")


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
        entries = len(parsed)
    elif isinstance(parsed, dict):
        lists = [v for v in parsed.values() if isinstance(v, list)]
        entries = len(lists[0]) if lists else 0
    else:
        entries = 0
    if books_approval_path().exists():
        raise ActionError("already approved")
    return {"input": {}, "sha256": hashlib.sha256(blob).hexdigest(), "entries": entries}


def _books_preview(c):
    return (f"Approve the {BOOKS_YEAR} Books import: the dry run at ~/lcs-private/books-import-{BOOKS_YEAR}.json "
            f"({c['entries']} entries, sha256 {c['sha256'][:16]}). This writes an approval record only; the chat "
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


def _books_run(c):
    write_private(books_approval_path(), {
        "approved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "dry_run": f"~/lcs-private/books-import-{BOOKS_YEAR}.json", "dry_run_sha256": c["sha256"],
        "entries": c["entries"], "instruction": BOOKS_INSTRUCTION, "status": "approved"}, exclusive=True)
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


def _todo_run(c):
    todo.set_tick(c["key"], c["done"])


TODO_TICK = LocalAction("todo-tick", _todo_validate, _todo_preview, _todo_run, passkey=False, title="Tick a to-do")
REGISTRY = {a.name: a for a in (TODO_TICK, RESOLVE_HAND_CHECK, SINGER_CONFIRM, SINGER_SETTLED, SINGER_WITHDRAWN,
                                REFRESH, ADS_VALIDATE, ADS_APPLY, BOOKS_IMPORT)}
ROUTED = {n for n in REGISTRY if n != "todo-tick"}  # the JSON routes; the tick keeps its own form route
