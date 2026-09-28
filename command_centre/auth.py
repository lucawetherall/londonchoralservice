"""Who may use the Command Centre, and how a write is authorised.

Before anything else, IdentityMiddleware refuses (403) a request that
- came from a peer other than 127.0.0.1 or ::1 (on the optional Unix socket there is no peer address, and a
  peer is local by construction: the socket sits in a mode-700 directory), or
- carries a Host other than the configured rp_id (bare or with :443), or more than one Host. This stops DNS
  rebinding: a web page whose name resolves to 127.0.0.1 would send its own Host. With the dev login on (a
  spare port only), 127.0.0.1:<that port> is allowed too.

Then two levels of trust (spec: docs/superpowers/specs/2026-09-28-command-centre-design.md, binding rule 2):

1. **Viewing** needs the owner's Tailscale identity. The app listens on 127.0.0.1 only and is published to
   the tailnet by `tailscale serve`, which adds `Tailscale-User-Login` and `Tailscale-User-Name` to every
   request it proxies from a tailnet device and strips any copies of those headers the device sent, so a
   tailnet client cannot claim another login. IdentityMiddleware refuses (403) any request without both
   headers or with a login not in the config's `allowed_logins`, except `/healthz`. A missing, unreadable
   or empty config refuses everything (fail closed). Because a process on the Mac itself can connect to
   127.0.0.1 and forge the headers, nothing that writes relies on them alone:
2. **Every write** also needs a WebAuthn passkey assertion (Face ID or Touch ID, user verification
   required) over a server-issued challenge that embeds sha256 of the action's summary and expires after
   60 seconds. require_fresh_assertion() checks all of that and burns the challenge on first use, so an
   assertion can't be replayed or reused for another action.

POSTs must also come from the configured origin (Origin header, and Sec-Fetch-Site when the browser sends
it): same-origin plus the assertion binding is the CSRF defence.

The config, ~/lcs-private/command-centre/config.json (LCS_PRIVATE_DIR moves it), mode 600, holds the allowed
logins, the origin and RP ID, and the passkeys' public keys. The only other thing in it is the sha256 and
expiry of the one-time bootstrap code (install.sh, or `python -m command_centre.bootstrap --new-bootstrap`),
which the first passkey registration needs and deletes; with no passkeys and no valid code, nobody can
register. It holds no secrets.
"""

import base64
import contextlib
import dataclasses
import datetime
import fcntl
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from pathlib import Path

from starlette.responses import PlainTextResponse
from webauthn import (generate_authentication_options, generate_registration_options, options_to_json,
                      verify_authentication_response, verify_registration_response)
from webauthn.helpers.structs import (AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor,
                                      ResidentKeyRequirement, UserVerificationRequirement)

CHALLENGE_TTL = 60  # seconds from issue to use
MAX_CHALLENGES = 100  # outstanding challenges kept; the oldest is dropped beyond this
BOOTSTRAP_TTL = datetime.timedelta(minutes=30)
SERVICE_PORT = 8765  # the LaunchAgent's port, which `tailscale serve` points at
LOOPBACK_PEERS = {"127.0.0.1", "::1"}
SINGLE_HEADERS = {"host", "tailscale-user-login", "tailscale-user-name", "origin", "sec-fetch-site"}
REGISTER_SUMMARY = "register a new passkey"
RP_NAME = "LCS Command Centre"
MAX_SUMMARY = 2000  # an Ads preview carries the git facts, the script's docstring and Claude's description
OPEN_PATHS = {"/healthz"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


# ---------------------------------------------------------------- config


def private_dir():
    """Read at call time, so the tests (and a moved private tree) never touch ~/lcs-private."""
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private"))


def config_dir():
    return private_dir() / "command-centre"


def config_path():
    return config_dir() / "config.json"


def load_config():
    """The config as a dict. Raises (OSError, ValueError) when it is missing or unreadable."""
    with open(config_path(), encoding="utf-8") as f:
        cfg = json.load(f)
    if not isinstance(cfg, dict):
        raise ValueError("config is not an object")
    return cfg


def save_config(cfg):
    """Atomic write, mode 600, in a mode-700 directory."""
    d = config_dir()
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    path = config_path()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


_THREAD_LOCK = threading.Lock()


@contextlib.contextmanager
def config_lock():
    """Exclusive lock for a read-modify-write of the config (threads and processes)."""
    d = config_dir()
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    with _THREAD_LOCK:
        fd = os.open(d / "config.json.lock", os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)


def _norm(login):
    return str(login or "").strip().casefold()


def login_allowed(login, cfg):
    allowed = cfg.get("allowed_logins") or []
    if not isinstance(allowed, list):
        return False
    want = _norm(login)
    return bool(want) and any(hmac.compare_digest(want, _norm(a)) for a in allowed if _norm(a))


# ---------------------------------------------------------------- identity middleware


SECURITY_HEADERS = [
    (b"content-security-policy",
     b"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; "
     b"connect-src 'self'; manifest-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; "
     b"form-action 'self'; "
     b"frame-ancestors 'none'"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    (b"x-content-type-options", b"nosniff"),
    (b"cache-control", b"no-store"),
    (b"pragma", b"no-cache"),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"cross-origin-resource-policy", b"same-origin"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
                            b"publickey-credentials-get=(self), publickey-credentials-create=(self)"),
    (b"x-robots-tag", b"noindex, nofollow"),
]
SECURITY_HEADER_NAMES = {k for k, _ in SECURITY_HEADERS}


class SecurityHeadersMiddleware:
    """Adds the security headers to every response, the 403s and 404s included. Outermost middleware."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", [])
                           if k.lower() not in SECURITY_HEADER_NAMES and k.lower() != b"server"]
                message = dict(message, headers=headers + SECURITY_HEADERS)
            await send(message)

        await self.app(scope, receive, send_with_headers)



def _forbidden():
    return PlainTextResponse("Forbidden", status_code=403)


class IdentityMiddleware:
    """Refuses every request from a non-loopback peer or for another Host (see the module docstring), then
    every request, except /healthz, that lacks an allowed Tailscale identity, and every unsafe-method request
    that isn't same-origin. `dev_login` (create_app decides: only on 127.0.0.1, a spare port, with
    CC_DEV_LOGIN set) stands in for the headers during a local visual check, and must itself be an allowed
    login; `dev_port` is that spare port. `uds` is True when serving on the Unix socket."""

    def __init__(self, app, dev_login=None, dev_port=None, uds=False):
        self.app = app
        self.dev_login = dev_login
        self.dev_port = dev_port if dev_login else None
        self.uds = bool(uds)

    def peer_ok(self, scope):
        client = scope.get("client")
        if client is None:
            return self.uds  # a Unix-socket peer has no address; over TCP there always is one
        return not self.uds and str(client[0]) in LOOPBACK_PEERS

    def host_ok(self, host, cfg):
        rp_id = str(cfg.get("rp_id") or "").strip().lower()
        if not rp_id:
            return False
        allowed = {rp_id, rp_id + ":443"}
        if self.dev_port:
            allowed.add(f"127.0.0.1:{self.dev_port}")
        return host.strip().lower() in allowed

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            if scope["type"] == "lifespan":
                return await self.app(scope, receive, send)
            return  # websockets and anything else: refused by not being served
        if not self.peer_ok(scope):
            return await _forbidden()(scope, receive, send)
        headers = {}
        for k, v in scope.get("headers", []):
            name = k.decode("latin-1").lower()
            if name in headers and name in SINGLE_HEADERS:
                return await _forbidden()(scope, receive, send)  # two Hosts, or two identities: refuse
            headers.setdefault(name, v.decode("latin-1"))
        try:
            cfg = load_config()
        except (OSError, ValueError):
            cfg = {}
        if not self.host_ok(headers.get("host", ""), cfg):
            return await _forbidden()(scope, receive, send)
        if scope["path"] in OPEN_PATHS and scope["method"] in SAFE_METHODS:
            return await self.app(scope, receive, send)
        if self.dev_login:
            headers["tailscale-user-login"] = self.dev_login
            headers["tailscale-user-name"] = "Local check"
        login = headers.get("tailscale-user-login", "")
        name = headers.get("tailscale-user-name", "").strip()
        ok = login_allowed(login, cfg) and bool(name)
        if ok and scope["method"] not in SAFE_METHODS:
            ok = same_origin(headers, cfg)
        if not ok:
            return await _forbidden()(scope, receive, send)
        scope.setdefault("state", {})["user"] = {"login": _norm(login), "name": name}
        await self.app(scope, receive, send)


def same_origin(headers, cfg):
    origin = str(cfg.get("origin") or "").rstrip("/")
    sent = headers.get("origin", "").rstrip("/")
    if not origin or not sent or not hmac.compare_digest(sent, origin):
        return False
    return headers.get("sec-fetch-site", "same-origin") == "same-origin"


# ---------------------------------------------------------------- challenges


class PasskeyError(Exception):
    """A refused passkey step. `reason` is a fixed phrase, safe to show and to return as JSON."""

    def __init__(self, reason, status=403):
        super().__init__(reason)
        self.reason = reason
        self.status = status


def action_hash(purpose, summary, name=None):
    """sha256 over the purpose, the action's name (for an action assertion) and the summary: two actions whose
    summaries happened to match still get different challenges."""
    text = f"{purpose}\n{summary}" if name is None else f"{purpose}\n{name}\n{summary}"
    return hashlib.sha256(text.encode("utf-8")).digest()


class ChallengeStore:
    """Server-issued challenges: 16 random bytes followed by sha256(purpose, summary). Each lives
    CHALLENGE_TTL seconds and is removed on its first use, whether that use succeeds or not. At most
    MAX_CHALLENGES are kept (insertion order, so the oldest go first)."""

    def __init__(self, ttl=CHALLENGE_TTL, clock=time.monotonic):
        self.ttl = ttl
        self.clock = clock
        self._issued = {}
        self._lock = threading.Lock()

    def issue(self, purpose, summary, name=None):
        challenge = secrets.token_bytes(16) + action_hash(purpose, summary, name)
        now = self.clock()
        with self._lock:
            self._issued = {c: e for c, e in self._issued.items() if e[1] > now}  # drop the expired
            while len(self._issued) >= MAX_CHALLENGES:  # a flood of requests can't grow memory: drop the oldest
                del self._issued[next(iter(self._issued))]
            self._issued[challenge] = (purpose, now + self.ttl)
        return challenge

    def consume(self, challenge, purpose, summary, name=None):
        with self._lock:
            entry = self._issued.pop(challenge, None)
        if entry is None:
            raise PasskeyError("unknown or used challenge")
        if self.clock() >= entry[1]:
            raise PasskeyError("challenge expired")
        if entry[0] != purpose or not hmac.compare_digest(challenge[16:], action_hash(purpose, summary, name)):
            raise PasskeyError("wrong action")


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def unb64url(text):
    if not isinstance(text, str):
        raise ValueError("not base64url")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _credential(value):
    """A credential as a dict (the browser's PublicKeyCredential JSON), or PasskeyError."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            raise PasskeyError("malformed credential") from None
    if not isinstance(value, dict) or not isinstance(value.get("response"), dict):
        raise PasskeyError("malformed credential")
    return value


def client_challenge(cred):
    """The challenge the authenticator signed, read from clientDataJSON (py_webauthn checks it again)."""
    try:
        client_data = json.loads(unb64url(cred["response"]["clientDataJSON"]))
        return unb64url(client_data["challenge"])
    except (KeyError, TypeError, ValueError):
        raise PasskeyError("malformed credential") from None


def check_summary(summary):
    if not isinstance(summary, str) or not summary.strip() or len(summary) > MAX_SUMMARY:
        raise PasskeyError("an action summary is required", status=400)
    return summary


# ---------------------------------------------------------------- actions


@dataclasses.dataclass(frozen=True)
class Action:
    """Something the owner approves with a passkey. The server builds it: `summary` is written by server code
    from validated input (phase 3's registry: `preview(input)`), never taken from a request, so the text the
    challenge binds is the text the server will act on. Requests name an action; they never supply its
    summary. require_fresh_assertion() and assertion_options() accept nothing else."""

    name: str
    summary: str

    def __post_init__(self):
        check_summary(self.summary)


CHECK = Action("check", "check passkey")
REGISTER = Action("register", REGISTER_SUMMARY)
PHASE1_ACTIONS = {a.name: a for a in (CHECK, REGISTER)}  # the phase-3 registry replaces this lookup


def action_named(name):
    """The server-built Action a request names, or PasskeyError (400)."""
    action = PHASE1_ACTIONS.get(name) if isinstance(name, str) else None
    if action is None:
        raise PasskeyError("unknown action", status=400)
    return action


def _require_action(action):
    if not isinstance(action, Action):
        raise PasskeyError("server-built action required", status=400)
    return action


# ---------------------------------------------------------------- bootstrap code


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _code_hash(code):
    return hashlib.sha256(str(code).encode("utf-8")).hexdigest()


def issue_bootstrap(cfg, now=None):
    """Put a new one-time code's sha256 and expiry (now + 30 minutes) into `cfg`; return the code itself,
    which is shown once and stored nowhere."""
    code = secrets.token_urlsafe(12)
    expires = (now or _utcnow()) + BOOTSTRAP_TTL
    cfg["bootstrap"] = {"sha256": _code_hash(code), "expires": expires.isoformat(timespec="seconds")}
    return code


def new_bootstrap(now=None):
    """Issue a bootstrap code into the saved config (under the lock). Refused once a passkey exists."""
    with config_lock():
        cfg = load_config()
        if cfg.get("passkeys"):
            raise PasskeyError("a passkey is already registered", status=409)
        code = issue_bootstrap(cfg, now)
        save_config(cfg)
    return code


def check_bootstrap(cfg, code, now):
    """The code's sha256 if `code` matches the config's unexpired bootstrap code, else PasskeyError."""
    entry = cfg.get("bootstrap")
    if not isinstance(entry, dict) or not entry.get("sha256"):
        raise PasskeyError("no bootstrap code issued")
    if not isinstance(code, str) or not code.strip():
        raise PasskeyError("bootstrap code required")
    try:
        expires = datetime.datetime.fromisoformat(str(entry.get("expires")))
    except ValueError:
        raise PasskeyError("bootstrap code expired") from None
    if expires.tzinfo is None or now >= expires:
        raise PasskeyError("bootstrap code expired")
    digest = _code_hash(code.strip())
    if not hmac.compare_digest(digest, str(entry["sha256"])):
        raise PasskeyError("wrong bootstrap code")
    return digest


# ---------------------------------------------------------------- passkeys


class Passkeys:
    """Registration and assertion. One instance per app (its ChallengeStore is in memory). `wallclock`
    (UTC-aware datetimes) times the bootstrap code; the tests fake it."""

    def __init__(self, store=None, wallclock=None):
        self.store = store or ChallengeStore()
        self.wallclock = wallclock or _utcnow

    @staticmethod
    def _cfg():
        try:
            cfg = load_config()
        except (OSError, ValueError):
            raise PasskeyError("not configured") from None
        if not cfg.get("rp_id") or not cfg.get("origin"):
            raise PasskeyError("not configured")
        return cfg

    @staticmethod
    def _keys(cfg):
        keys = cfg.get("passkeys") or []
        return keys if isinstance(keys, list) else []

    def assertion_options(self, action):
        """Options for navigator.credentials.get(), bound to the server-built `action`'s summary."""
        action = _require_action(action)
        cfg = self._cfg()
        keys = self._keys(cfg)
        if not keys:
            raise PasskeyError("no passkeys registered", status=409)
        opts = generate_authentication_options(
            rp_id=cfg["rp_id"], challenge=self.store.issue("assert", action.summary, action.name), timeout=CHALLENGE_TTL * 1000,
            allow_credentials=[PublicKeyCredentialDescriptor(id=unb64url(k["id"])) for k in keys],
            user_verification=UserVerificationRequirement.REQUIRED)
        return json.loads(options_to_json(opts))

    def require_fresh_assertion(self, credential, action):
        """The passkey id, if `credential` is a valid assertion, made with a registered passkey and user
        verification, over a challenge issued in the last 60 seconds for exactly this server-built `action`
        (an Action, never a string from the request), and not used before. Otherwise PasskeyError. The
        challenge is burnt before anything else is checked."""
        action = _require_action(action)
        cred = _credential(credential)
        challenge = client_challenge(cred)
        self.store.consume(challenge, "assert", action.summary, action.name)
        cfg = self._cfg()
        key = next((k for k in self._keys(cfg) if k.get("id") == cred.get("id")), None)
        if key is None:
            raise PasskeyError("unknown credential")
        try:
            verified = verify_authentication_response(
                credential=cred, expected_challenge=challenge, expected_rp_id=cfg["rp_id"],
                expected_origin=cfg["origin"], credential_public_key=unb64url(key["public_key"]),
                credential_current_sign_count=int(key.get("sign_count") or 0), require_user_verification=True)
        except Exception:  # py_webauthn raises several types; none of their messages are shown
            raise PasskeyError("verification failed") from None
        with config_lock():
            cfg = load_config()
            for k in self._keys(cfg):
                if k.get("id") == key["id"]:
                    k["sign_count"] = int(verified.new_sign_count)
                    k["last_used"] = _utcnow().isoformat(timespec="seconds")
            save_config(cfg)
        return key["id"]

    @staticmethod
    def _register_summary(login, first, code_hash=None):
        # the first passkey's challenge is bound to the bootstrap code too, so its finish step must show it again
        return f"{login}\nbootstrap:{code_hash}" if first else login

    def registration_options(self, login, display_name, assertion=None, bootstrap=None):
        """Options for navigator.credentials.create(). The first passkey needs the unexpired one-time
        bootstrap code; after that, only a fresh assertion for REGISTER lets another be added."""
        cfg = self._cfg()
        keys = self._keys(cfg)
        if keys:
            if assertion is None:
                raise PasskeyError("assertion required")
            self.require_fresh_assertion(assertion, REGISTER)
            summary = self._register_summary(login, False)
        else:
            summary = self._register_summary(login, True, check_bootstrap(cfg, bootstrap, self.wallclock()))
        opts = generate_registration_options(
            rp_id=cfg["rp_id"], rp_name=RP_NAME, user_name=login, user_display_name=display_name or login,
            user_id=hashlib.sha256(("lcs-cc:" + login).encode()).digest()[:16],
            challenge=self.store.issue("register", summary), timeout=CHALLENGE_TTL * 1000,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED, user_verification=UserVerificationRequirement.REQUIRED),
            exclude_credentials=[PublicKeyCredentialDescriptor(id=unb64url(k["id"])) for k in keys])
        return json.loads(options_to_json(opts))

    def finish_registration(self, credential, login, label="", bootstrap=None):
        """Verify a new passkey against its single-use registration challenge and store its public key. The
        first passkey also needs the bootstrap code again (still unexpired), and deleting the code is part of
        the same locked write that stores the key."""
        cred = _credential(credential)
        challenge = client_challenge(cred)
        cfg = self._cfg()
        first = not self._keys(cfg)
        code_hash = None
        if first:
            try:
                code_hash = check_bootstrap(cfg, bootstrap, self.wallclock())
            except PasskeyError:
                with contextlib.suppress(PasskeyError):  # burn the challenge anyway
                    self.store.consume(challenge, "register", "")
                raise
        try:
            self.store.consume(challenge, "register", self._register_summary(login, first, code_hash))
        except PasskeyError as e:
            if first and e.reason == "wrong action":
                raise PasskeyError("wrong bootstrap code") from None
            raise
        try:
            verified = verify_registration_response(
                credential=cred, expected_challenge=challenge, expected_rp_id=cfg["rp_id"],
                expected_origin=cfg["origin"], require_user_verification=True)
        except Exception:
            raise PasskeyError("verification failed") from None
        entry = {"id": b64url(verified.credential_id), "public_key": b64url(verified.credential_public_key),
                 "sign_count": int(verified.sign_count), "login": login, "label": str(label or "")[:60],
                 "created": _utcnow().isoformat(timespec="seconds")}
        with config_lock():
            cfg = load_config()
            keys = self._keys(cfg)
            if first:
                if keys:
                    raise PasskeyError("already registered")  # another device won the race for the first key
                if check_bootstrap(cfg, bootstrap, self.wallclock()) != code_hash:
                    raise PasskeyError("wrong bootstrap code")
                cfg.pop("bootstrap", None)
            if any(k.get("id") == entry["id"] for k in keys):
                raise PasskeyError("already registered")
            cfg["passkeys"] = keys + [entry]
            save_config(cfg)
        return entry["id"]


def passkey_summary(cfg):
    """{"count", "last_added"} for the pages: how many passkeys, and the newest one's creation time."""
    keys = cfg.get("passkeys") if isinstance(cfg, dict) else None
    keys = keys if isinstance(keys, list) else []
    created = []
    for k in keys:
        try:
            when = datetime.datetime.fromisoformat(str(k.get("created")))
        except (AttributeError, ValueError):
            continue
        if when.tzinfo is not None:
            created.append(when)
    return {"count": len(keys), "last_added": max(created) if created else None}
