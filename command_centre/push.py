"""Web Push for the Command Centre: VAPID keys, subscriptions, payloads, the events watcher and the stale-run check.

- **VAPID keys.** One P-256 key, made once, when the service starts (app.py's lifespan; /device only reads it and
  says "not set up yet" without one). Its private scalar (64 hex characters) lives in the macOS Keychain
  under the service `lcs-command-centre-vapid`, written and read with the `security` CLI from the app's own
  process: added through `security -i` with the command on stdin (so the key never appears in a process list),
  read with `find-generic-password -w`. Claude never reads it (.claude/settings.json denies
  `security find-generic-password`). For the tests and a local visual check only, CC_VAPID_STORE=file keeps it
  in <private>/command-centre/vapid-test.json (mode 600) instead; the live service (port 8765, the socket or the
  watcher) refuses to start with it set.
- **Subscriptions** are in the config's `push_subscriptions`: {id, endpoint, p256dh, auth, added, login,
  passkey}. The endpoint must be https on a known push service (Apple, Google, Mozilla, Microsoft), so the app
  can't be made to POST anywhere else (endpoint_ok): ASCII only; no whitespace anywhere; no backslash, %, ; or @
  in the host part; a host of dotted DNS labels (never an IP literal, an empty label or a trailing dot); no port
  but 443, user info, query or fragment; and urllib3 (what requests sends with) must read the same host as
  urlsplit. It is checked again before every send, and the push session follows no redirect. Adding one is the
  registry action `push-subscribe` (a passkey: a new device receiving business information); removing one is
  `push-unsubscribe`.
- **Events** come from scripts/reports/cc_event.py (the scheduled prompts), one JSON line each in
  <private>/command-centre/events.jsonl: a kind and validated fields, never free text. The watcher reads new lines
  every POLL seconds (from the end of the file the first time, so history is never replayed; a line longer than
  READ_MAX is skipped), and pushes each to every subscription: at most PASS_MAX per pass plus one "And N more",
  and at most HOUR_MAX in any hour.
- **Payloads** are {"title", "body", "url"} and nothing else, built from a fixed template per kind (TEMPLATES).
  The fields are validated again here (cc_event.validate), so a line that didn't come from the CLI still can't
  put anything on the lock screen but a first name, a booking ref, a date and words from fixed lists.
- **Sending** goes over the Mac's normal internet connection to the public push service (Apple's, for the iPhone),
  never through the tailnet, so a phone with the VPN off still gets it. The requests session ignores proxy
  settings from the environment, follows no redirect and refuses any URL endpoint_ok refuses; each push has a
  10-second timeout. A 404 or 410 answer drops that subscription.
- **Stale run.** Between 08:00 and 21:00 London time, if the enquiry assistant's state file hasn't changed for
  more than 3 daytime hours (the hours from 21:00 to 08:00 don't count, so the first run of the morning is never
  late), one push says so; it isn't repeated until the file changes again.
"""

import asyncio
import contextlib
import datetime
import fcntl
import hashlib
import ipaddress
import json
import logging
import os
import re
import secrets
import subprocess
import sys
import urllib.parse
from pathlib import Path
from zoneinfo import ZoneInfo

from . import auth

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "reports"))
import cc_event  # noqa: E402  the same cleaning rules as the CLI

log = logging.getLogger("command_centre.push")
LONDON = ZoneInfo("Europe/London")
KEYCHAIN_SERVICE = "lcs-command-centre-vapid"
KEYCHAIN_ACCOUNT = "vapid-private-key"
SECURITY = "/usr/bin/security"
SECURITY_RUNNER = subprocess.run  # the tests replace this with a fake `security`
WEBPUSH = None  # pywebpush.webpush, loaded on first use; the tests replace it with a fake
POLL = 20  # seconds between the watcher's looks at events.jsonl
PUSH_TIMEOUT = 10
TTL = 12 * 3600  # seconds a push service keeps an undelivered notification
BODY_MAX = 80
TITLE_MAX = 60
DAY_START, DAY_END = 8, 21  # London hours in which the enquiry assistant should be running
STALE_AFTER = datetime.timedelta(hours=3)
READ_MAX = 256 * 1024  # bytes of new events read per look; a longer line is skipped
PASS_MAX = 5  # pushes per watcher pass, then one "And N more"
HOUR_MAX = 20  # pushes in any hour, the summary included
KINDS = {  # kind -> (title, the page a tap opens)
    "enquiry": ("New enquiry", "/enquiries"),
    "deposit": ("Payment arrived", "/money"),
    "bank-change": ("Singer bank details changed", "/singers"),
    "guard-denied": ("A guard refused a call", "/activity"),
    "run-failed": ("A scheduled run failed", "/health"),
    "monday-ready": ("Monday review ready", "/reports"),
    "hand-check": ("Hand check added", "/money"),
    "run-stale": ("Enquiry assistant not seen", "/health"),
}
assert set(KINDS) - {"run-stale"} == set(cc_event.KINDS)
STATE_WORDS = {
    "CHECK_PAYMENT": "check a payment", "CHECK_VALUE": "check the booking value", "NOTED_PAID": "noted as paid",
    "PAST_UNMATCHED": "past, payment not matched", "PAST_PART_PAID": "past, part paid",
    "PAYMENT_ON_CANCELLED": "payment on a cancelled booking", "PAYMENT_AFTER_CLOSE": "payment after closing",
    "ARRANGED": "collect the cash or cheque"}
assert set(STATE_WORDS) == set(cc_event.STATES)
AGENT_WORDS = {"reply-drafter": "Reply drafter", "singer-clerk": "Singer clerk", "daily-pass": "Daily pass",
               "monday": "Monday review"}
assert set(AGENT_WORDS) == set(cc_event.AGENTS)
PUSH_HOSTS = {"web.push.apple.com", "fcm.googleapis.com", "android.googleapis.com",
              "updates.push.services.mozilla.com"}
PUSH_SUFFIXES = (".push.apple.com", ".notify.windows.com")
ENDPOINT_MAX = 1024
HOST_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")
NETLOC_BAD = set("\\%;@[]")
KEY_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")  # a base64url p256dh (87 characters) or auth secret (22)
SUB_ID_RE = re.compile(r"^[0-9a-f]{16}$")


class PushError(Exception):
    pass


# ---------------------------------------------------------------- VAPID keys


def vapid_file():
    return auth.config_dir() / "vapid-test.json"


def file_store():
    """CC_VAPID_STORE=file: the tests' (and a local visual check's) stand-in for the Keychain."""
    return os.environ.get("CC_VAPID_STORE", "").strip() == "file"


def _keychain(args, stdin=None):
    kw = {"capture_output": True, "timeout": 15, "shell": False}
    if stdin is None:
        kw["stdin"] = subprocess.DEVNULL
    else:
        kw["input"] = stdin.encode("ascii")
    return SECURITY_RUNNER([SECURITY, *args], **kw)


def _read_private_hex():
    """The stored private scalar (hex), or None when there isn't one yet."""
    if file_store():
        try:
            with open(vapid_file(), encoding="utf-8") as f:
                value = json.load(f).get("private_hex")
        except FileNotFoundError:
            return None
    else:
        proc = _keychain(["find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT, "-w"])
        if proc.returncode != 0:
            return None  # 44: not found
        value = (proc.stdout or b"").decode("ascii", "replace").strip()
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise PushError("the stored VAPID key is malformed")
    return value


def _store_private_hex(value):
    if file_store():
        path = vapid_file()
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"private_hex": value}, f)
        return
    # the key goes on stdin to `security -i`, never on a command line
    command = f"add-generic-password -s {KEYCHAIN_SERVICE} -a {KEYCHAIN_ACCOUNT} -l {KEYCHAIN_SERVICE} -w {value}\n"
    proc = _keychain(["-i"], stdin=command)
    if proc.returncode != 0 or _read_private_hex() != value:
        raise PushError("couldn't save the VAPID key in the Keychain")


_KEY_CACHE = {}


def private_key(create=True):
    """The VAPID private key (cryptography's EllipticCurvePrivateKey), made and stored the first time. create=False
    (the /device page, a GET) only reads: None when there is no key yet. The service makes it at start-up."""
    from cryptography.hazmat.primitives.asymmetric import ec
    store = "file" if file_store() else "keychain"
    if store in _KEY_CACHE:
        return _KEY_CACHE[store]
    value = _read_private_hex()
    if value is None:
        if not create:
            return None
        key = ec.generate_private_key(ec.SECP256R1())
        value = f"{key.private_numbers().private_value:064x}"
        _store_private_hex(value)
    key = ec.derive_private_key(int(value, 16), ec.SECP256R1())
    _KEY_CACHE[store] = key
    return key


def forget_key():
    _KEY_CACHE.clear()


def public_key_b64(create=True):
    """The applicationServerKey for pushManager.subscribe(): the uncompressed public point, base64url. With
    create=False, None when no key has been made yet."""
    from cryptography.hazmat.primitives import serialization
    key = private_key(create=create)
    if key is None:
        return None
    raw = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return auth.b64url(raw)


def _vapid():
    from py_vapid import Vapid02
    return Vapid02(private_key())


# ---------------------------------------------------------------- subscriptions


def _is_ip(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def endpoint_ok(endpoint):
    """True for an https URL on a known push service, and nothing that two URL parsers could read differently:
    ASCII only, no whitespace or backslash anywhere, no %, ;, @ or brackets in the host part, a host of DNS labels
    (lower case, no IP literal, empty label or trailing dot), no port but 443, no user info, query or fragment, and
    urllib3's host (what requests connects to) equal to urlsplit's."""
    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > ENDPOINT_MAX or not endpoint.isascii():
        return False
    if any(c.isspace() or c == "\\" or ord(c) < 32 or ord(c) == 127 for c in endpoint):
        return False
    if not endpoint.startswith("https://"):
        return False
    try:
        u = urllib.parse.urlsplit(endpoint)
        port = u.port
    except ValueError:
        return False
    netloc = u.netloc
    if u.scheme != "https" or not netloc or any(c in NETLOC_BAD for c in netloc):
        return False
    if u.username is not None or u.password is not None or u.fragment or u.query or "?" in endpoint or "#" in endpoint:
        return False
    host = u.hostname or ""
    if port not in (None, 443) or netloc not in (host, f"{host}:443"):
        return False
    if not HOST_RE.fullmatch(host) or _is_ip(host):
        return False
    try:
        from urllib3.util import parse_url
        if (parse_url(endpoint).host or "") != host:
            return False
    except Exception:
        return False
    return host in PUSH_HOSTS or any(host.endswith(s) and len(host) > len(s) for s in PUSH_SUFFIXES)


def subscription_id(endpoint):
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()[:16]


def validate_subscription(raw):
    """{endpoint, p256dh, auth} from a request, strictly, or ValueError with a fixed phrase."""
    if not isinstance(raw, dict) or set(raw) != {"endpoint", "p256dh", "auth"}:
        raise ValueError("malformed subscription")
    if not all(isinstance(v, str) for v in raw.values()):
        raise ValueError("malformed subscription")
    endpoint, p256dh, secret = raw["endpoint"].strip(), raw["p256dh"].strip(), raw["auth"].strip()
    if not endpoint_ok(endpoint):
        raise ValueError("not a known push service")
    if not KEY_RE.fullmatch(p256dh) or not KEY_RE.fullmatch(secret):
        raise ValueError("malformed subscription keys")
    return {"endpoint": endpoint, "p256dh": p256dh, "auth": secret, "id": subscription_id(endpoint),
            "service": urllib.parse.urlsplit(endpoint).hostname.lower()}


def subscriptions(cfg=None):
    if cfg is None:
        try:
            cfg = auth.load_config()
        except (OSError, ValueError):
            return []
    subs = cfg.get("push_subscriptions")
    return [s for s in subs if isinstance(s, dict) and endpoint_ok(s.get("endpoint"))] if isinstance(subs, list) else []


def add_subscription(sub, login, passkey_id):
    with auth.config_lock():
        cfg = auth.load_config()
        subs = [s for s in subscriptions(cfg) if s.get("id") != sub["id"]]
        subs.append({"id": sub["id"], "endpoint": sub["endpoint"], "p256dh": sub["p256dh"], "auth": sub["auth"],
                     "service": sub["service"], "login": login, "passkey": (passkey_id or "")[:8],
                     "added": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
        cfg["push_subscriptions"] = subs
        auth.save_config(cfg)


def remove_subscription(sub_id):
    """True if a subscription with that id was removed."""
    with auth.config_lock():
        cfg = auth.load_config()
        subs = subscriptions(cfg)
        kept = [s for s in subs if s.get("id") != sub_id]
        if len(kept) == len(subs):
            return False
        cfg["push_subscriptions"] = kept
        auth.save_config(cfg)
    return True


def device_list():
    """What the device page shows: id, push service, when added (no endpoint or keys)."""
    out = []
    for s in subscriptions():
        try:
            added = datetime.datetime.fromisoformat(str(s.get("added")))
        except ValueError:
            added = None
        out.append({"id": s.get("id", ""), "service": s.get("service", ""), "added": added})
    return out


# ---------------------------------------------------------------- payloads


def _date_words(value):
    if value == "tbc":
        return "date tbc"
    d = datetime.date.fromisoformat(value)
    return f"{d.day} {d:%b %Y}"


def _stale_words(value):
    if value == "never":
        return "never seen"
    when = datetime.datetime.fromisoformat(value)
    if when.tzinfo is None:
        raise ValueError("naive time")
    return f"last seen {when.astimezone(LONDON):%a %H:%M}"


TEMPLATES = {  # kind -> the body, from validated fields only
    "enquiry": lambda f: f"{f['first']}: {f['occasion'].replace('-', ' ')}, {_date_words(f['date'])}",
    "deposit": lambda f: f"{f['first']}: {f['ref']} payment arrived",
    "hand-check": lambda f: f"{f['ref']}: {STATE_WORDS[f['state']]}",
    "bank-change": lambda f: f"{f['first']}: ring them before paying",
    "guard-denied": lambda f: f"{AGENT_WORDS[f['agent']]}: the reason is in its summary",
    "run-failed": lambda f: "Open Health for the details.",
    "monday-ready": lambda f: "Changes are waiting for your approval.",
    "run-stale": lambda f: f"Not run for 3 daytime hours ({_stale_words(f['last'])}).",
}
assert set(TEMPLATES) == set(KINDS)


def _fields(kind, fields):
    """The event's fields, validated again at push time (the CLI's rules), or ValueError."""
    if kind == "run-stale":
        if not isinstance(fields, dict) or set(fields) != {"last"} or not isinstance(fields["last"], str):
            raise ValueError("run-stale takes last")
        _stale_words(fields["last"])
        return {"last": fields["last"]}
    return cc_event.validate(kind, fields)


def payload(event):
    """The notification for one event: {"title", "body", "url"} only, from the kind's fixed template, or None for
    an unknown kind or fields that fail validation (free text never passes)."""
    kind = event.get("kind") if isinstance(event, dict) else None
    if kind not in KINDS:
        return None
    try:
        fields = _fields(kind, event.get("fields", {}))
        body = TEMPLATES[kind](fields)
    except (ValueError, KeyError, TypeError):
        return None
    title, url = KINDS[kind]
    return {"title": title[:TITLE_MAX], "body": body[:BODY_MAX], "url": url}


def summary(more):
    return {"title": f"And {more} more", "body": "More notifications than fit at once: open Activity.",
            "url": "/activity"}


# ---------------------------------------------------------------- sending


def _webpush():
    global WEBPUSH
    if WEBPUSH is None:
        from pywebpush import webpush
        WEBPUSH = webpush
    return WEBPUSH


def _session():
    """A requests session that posts to push endpoints only: no proxy from the environment (straight out over the
    Mac's own internet connection), no redirect followed, and any URL endpoint_ok refuses is refused here too."""
    import requests

    class PushSession(requests.Session):
        def request(self, method, url, *args, **kw):
            if not endpoint_ok(url):
                raise PushError("not a known push service")
            kw["allow_redirects"] = False
            return super().request(method, url, *args, **kw)

        def get_redirect_target(self, resp):
            return None  # belt and braces: never a redirect, whatever calls resolve_redirects

    s = PushSession()
    s.trust_env = False
    s.max_redirects = 0
    return s


def claims():
    """The VAPID `sub`: the app's own https origin (no personal address)."""
    try:
        origin = str(auth.load_config().get("origin") or "")
    except (OSError, ValueError):
        origin = ""
    return {"sub": origin if origin.startswith("https://") else "https://localhost"}


def send(message, subs=None):
    """Push `message` (a payload dict) to every subscription. Returns {"sent", "failed", "dropped"}; a 404 or 410
    answer drops that subscription. Failures are logged by type only."""
    subs = subscriptions() if subs is None else subs
    result = {"sent": 0, "failed": 0, "dropped": 0}
    if not subs:
        return result
    body = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    if not any(endpoint_ok(s.get("endpoint")) for s in subs):
        result["failed"] = len(subs)
        return result
    vapid = _vapid()
    push = _webpush()
    session = _session() if push.__module__.startswith("pywebpush") else None
    for s in subs:
        if not endpoint_ok(s.get("endpoint")):
            result["failed"] += 1  # checked again at send time, whatever the config says
            log.warning("push refused: a stored endpoint is not a known push service")
            continue
        info = {"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}}
        kw = {"vapid_private_key": vapid, "vapid_claims": claims(), "ttl": TTL, "timeout": PUSH_TIMEOUT}
        if session is not None:
            kw["requests_session"] = session
        try:
            push(info, body, **kw)
            result["sent"] += 1
        except Exception as e:  # pywebpush.WebPushException and network errors; only the type is logged
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):
                remove_subscription(s.get("id"))
                result["dropped"] += 1
            else:
                result["failed"] += 1
                log.warning("push failed: %s %s", type(e).__name__, status or "")
    return result


# ---------------------------------------------------------------- the watcher


def state_path():
    return auth.config_dir() / "push-state.json"


def events_path():
    return auth.config_dir() / "events.jsonl"


def assistant_state_path():
    return auth.private_dir() / "assistant-state.json"


def load_state():
    try:
        with open(state_path(), encoding="utf-8") as f:
            st = json.load(f)
        return st if isinstance(st, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(st):
    d = auth.config_dir()
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = state_path()
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(st, f)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)  # a failed write (a full disk, a value json can't write) leaves no temp file behind
        raise


def new_events(st):
    """Events appended since the last look (and the state updated in place). The first look, a new file (another
    inode) or a shorter file starts from the end or the start as appropriate; history is never replayed. A line
    longer than READ_MAX is skipped (st["skip"] until its newline), so one bad line can't stall the watcher."""
    path = events_path()
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        st.update(inode=None, offset=0, skip=False)
        return []
    with os.fdopen(fd, "rb") as f:
        info = os.fstat(f.fileno())
        if "offset" not in st:  # the watcher's first start: skip what's already there
            st.update(inode=info.st_ino, offset=info.st_size, skip=False)
            return []
        offset = int(st.get("offset") or 0)
        skip = bool(st.get("skip"))
        if st.get("inode") != info.st_ino or info.st_size < offset:
            offset, skip = 0, False  # a new file since the last look: read it from the start
        f.seek(offset)
        chunk = f.read(READ_MAX)
    if skip:
        nl = chunk.find(b"\n")
        if nl < 0:
            st.update(inode=info.st_ino, offset=offset + len(chunk), skip=True)
            return []
        offset, chunk, skip = offset + nl + 1, chunk[nl + 1:], False
    end = chunk.rfind(b"\n")
    if end < 0:
        if len(chunk) >= READ_MAX:
            st.update(inode=info.st_ino, offset=offset + len(chunk), skip=True)  # too long: skip to its end
            log.warning("push watcher: skipped an event line longer than %d bytes", READ_MAX)
        else:
            st.update(inode=info.st_ino, offset=offset, skip=False)  # a line still being written
        return []
    st.update(inode=info.st_ino, offset=offset + end + 1, skip=False)
    out = []
    for line in chunk[:end].splitlines():
        if len(line) > READ_MAX:
            continue
        try:
            event = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue
        if isinstance(event, dict):
            out.append(event)
    return out


def daytime_between(start, end):
    """How much of [start, end) falls between DAY_START and DAY_END, London time."""
    start, end = start.astimezone(LONDON), end.astimezone(LONDON)
    total = datetime.timedelta(0)
    day = start.date()
    while day <= end.date():
        lo = datetime.datetime.combine(day, datetime.time(DAY_START), LONDON)
        hi = datetime.datetime.combine(day, datetime.time(DAY_END), LONDON)
        a, b = max(lo, start), min(hi, end)
        if b > a:
            total += b - a
        day += datetime.timedelta(days=1)
    return total


def stale_run(now, st):
    """The run-stale event to push now, or None. Pushed once per state-file version (its mtime, or "missing")."""
    now = now.astimezone(LONDON)
    if not DAY_START <= now.hour < DAY_END:
        return None
    try:
        changed = datetime.datetime.fromtimestamp(assistant_state_path().stat().st_mtime, LONDON)
        mark = changed.isoformat()
    except FileNotFoundError:
        changed, mark = None, "missing"
    if changed is not None and daytime_between(changed, now) <= STALE_AFTER:
        return None
    if st.get("stale_for") == mark:
        return None
    st["stale_for"] = mark
    return {"kind": "run-stale", "fields": {"last": "never" if changed is None else changed.isoformat()}}


def capped(messages, st, now_ts):
    """The messages to send now: at most PASS_MAX, then one "And N more" in place of the rest, and never more than
    HOUR_MAX in the hour before now_ts (st["sent"] keeps those times; updated in place)."""
    recent = [t for t in st.get("sent") or [] if isinstance(t, (int, float)) and 0 <= now_ts - t < 3600]
    budget = max(0, HOUR_MAX - len(recent))
    if len(messages) <= min(PASS_MAX, budget):
        out = list(messages)
    elif budget == 0:
        out = []
    else:
        direct = messages[:min(PASS_MAX, budget - 1)]
        out = direct + [summary(len(messages) - len(direct))]
    if len(out) < len(messages):
        log.warning("push watcher: %d of %d notifications held back by the caps", len(messages) - len(out),
                    len(messages))
    st["sent"] = recent + [now_ts] * len(out)
    return out


def look(now=None):
    """One pass of the watcher: new events, then the stale-run check, capped. Returns the payloads it pushed."""
    now = now or datetime.datetime.now(LONDON)
    lock_path = auth.config_dir() / "push.lock"
    auth.config_dir().mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        st = load_state()
        events = new_events(st)
        stale = stale_run(now, st)
        if stale:
            events.append(stale)
        messages = [m for m in (payload(e) for e in events) if m is not None]
        messages = capped(messages, st, now.timestamp())
        save_state(st)
    finally:
        os.close(fd)
    for message in messages:
        send(message)
    return messages


async def watch(stop_event=None, poll=POLL):
    """The service's background loop (started in the app's lifespan). A failing pass is logged by type only."""
    from starlette.concurrency import run_in_threadpool
    while not (stop_event and stop_event.is_set()):
        try:
            await run_in_threadpool(look)
        except Exception as e:
            log.warning("push watcher: %s", type(e).__name__)
        with contextlib.suppress(asyncio.TimeoutError):
            if stop_event:
                await asyncio.wait_for(stop_event.wait(), timeout=poll)
            else:
                await asyncio.sleep(poll)
