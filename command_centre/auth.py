"""Who may use the Command Centre, and how a write is authorised.

Two levels of trust (spec: docs/superpowers/specs/2026-09-28-command-centre-design.md, binding rule 2):

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
logins, the origin and RP ID, and the passkeys' public keys. It holds no secrets.
"""

import base64
import contextlib
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
REGISTER_SUMMARY = "register a new passkey"
RP_NAME = "LCS Command Centre"
MAX_SUMMARY = 500
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
     b"connect-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; "
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
    """Refuses every request, except /healthz, that lacks an allowed Tailscale identity, and every
    unsafe-method request that isn't same-origin. `dev_login` (create_app decides; off unless bound to
    127.0.0.1 with CC_DEV_LOGIN set) stands in for the headers during a local visual check, and must
    itself be an allowed login."""

    def __init__(self, app, dev_login=None):
        self.app = app
        self.dev_login = dev_login

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            if scope["type"] == "lifespan":
                return await self.app(scope, receive, send)
            return  # websockets and anything else: refused by not being served
        if scope["path"] in OPEN_PATHS and scope["method"] in SAFE_METHODS:
            return await self.app(scope, receive, send)
        headers = {}
        for k, v in scope.get("headers", []):
            headers.setdefault(k.decode("latin-1").lower(), v.decode("latin-1"))
        if self.dev_login:
            headers["tailscale-user-login"] = self.dev_login
            headers["tailscale-user-name"] = "Local check"
        try:
            cfg = load_config()
        except (OSError, ValueError):
            cfg = {}
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


def action_hash(purpose, summary):
    return hashlib.sha256(f"{purpose}\n{summary}".encode("utf-8")).digest()


class ChallengeStore:
    """Server-issued challenges: 16 random bytes followed by sha256(purpose, summary). Each lives
    CHALLENGE_TTL seconds and is removed on its first use, whether that use succeeds or not."""

    def __init__(self, ttl=CHALLENGE_TTL, clock=time.monotonic):
        self.ttl = ttl
        self.clock = clock
        self._issued = {}
        self._lock = threading.Lock()

    def issue(self, purpose, summary):
        challenge = secrets.token_bytes(16) + action_hash(purpose, summary)
        now = self.clock()
        with self._lock:
            self._issued = {c: e for c, e in self._issued.items() if e[1] > now}  # drop the expired
            self._issued[challenge] = (purpose, now + self.ttl)
        return challenge

    def consume(self, challenge, purpose, summary):
        with self._lock:
            entry = self._issued.pop(challenge, None)
        if entry is None:
            raise PasskeyError("unknown or used challenge")
        if self.clock() >= entry[1]:
            raise PasskeyError("challenge expired")
        if entry[0] != purpose or not hmac.compare_digest(challenge[16:], action_hash(purpose, summary)):
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


# ---------------------------------------------------------------- passkeys


class Passkeys:
    """Registration and assertion. One instance per app (its ChallengeStore is in memory)."""

    def __init__(self, store=None):
        self.store = store or ChallengeStore()

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

    def assertion_options(self, summary):
        """Options for navigator.credentials.get(), bound to `summary`."""
        check_summary(summary)
        cfg = self._cfg()
        keys = self._keys(cfg)
        if not keys:
            raise PasskeyError("no passkeys registered", status=409)
        opts = generate_authentication_options(
            rp_id=cfg["rp_id"], challenge=self.store.issue("assert", summary), timeout=CHALLENGE_TTL * 1000,
            allow_credentials=[PublicKeyCredentialDescriptor(id=unb64url(k["id"])) for k in keys],
            user_verification=UserVerificationRequirement.REQUIRED)
        return json.loads(options_to_json(opts))

    def require_fresh_assertion(self, credential, action_summary):
        """The passkey id, if `credential` is a valid assertion, made with a registered passkey and user
        verification, over a challenge issued in the last 60 seconds for exactly `action_summary`, and not
        used before. Otherwise PasskeyError. The challenge is burnt before anything else is checked."""
        check_summary(action_summary)
        cred = _credential(credential)
        self.store.consume(client_challenge(cred), "assert", action_summary)
        challenge = client_challenge(cred)
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
                    k["last_used"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
            save_config(cfg)
        return key["id"]

    def registration_options(self, login, display_name, assertion=None):
        """Options for navigator.credentials.create(). With no passkeys registered, anyone the identity
        check let in may register the first; after that, only with a fresh assertion for REGISTER_SUMMARY."""
        cfg = self._cfg()
        keys = self._keys(cfg)
        if keys:
            if assertion is None:
                raise PasskeyError("assertion required")
            self.require_fresh_assertion(assertion, REGISTER_SUMMARY)
        opts = generate_registration_options(
            rp_id=cfg["rp_id"], rp_name=RP_NAME, user_name=login, user_display_name=display_name or login,
            user_id=hashlib.sha256(("lcs-cc:" + login).encode()).digest()[:16],
            challenge=self.store.issue("register", login), timeout=CHALLENGE_TTL * 1000,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED, user_verification=UserVerificationRequirement.REQUIRED),
            exclude_credentials=[PublicKeyCredentialDescriptor(id=unb64url(k["id"])) for k in keys])
        return json.loads(options_to_json(opts))

    def finish_registration(self, credential, login, label=""):
        """Verify a new passkey against its single-use registration challenge and store its public key."""
        cred = _credential(credential)
        challenge = client_challenge(cred)
        self.store.consume(challenge, "register", login)
        cfg = self._cfg()
        try:
            verified = verify_registration_response(
                credential=cred, expected_challenge=challenge, expected_rp_id=cfg["rp_id"],
                expected_origin=cfg["origin"], require_user_verification=True)
        except Exception:
            raise PasskeyError("verification failed") from None
        entry = {"id": b64url(verified.credential_id), "public_key": b64url(verified.credential_public_key),
                 "sign_count": int(verified.sign_count), "login": login, "label": str(label or "")[:60],
                 "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
        with config_lock():
            cfg = load_config()
            keys = self._keys(cfg)
            if any(k.get("id") == entry["id"] for k in keys):
                raise PasskeyError("already registered")
            cfg["passkeys"] = keys + [entry]
            save_config(cfg)
        return entry["id"]
