#!/usr/bin/env python3
"""Tests for command_centre/auth.py: Tailscale identity, the dev login, CSRF and passkeys.

Stdlib runner, Starlette's TestClient. Never touches the real private files: LCS_PRIVATE_DIR is a temp dir.
The passkey tests use a software authenticator (an ES256 key made here), so py_webauthn's real verifiers
check real signatures; only the clock is faked.
"""
import base64, hashlib, json, os, sys, tempfile

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
os.environ.pop("CC_DEV_LOGIN", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import cbor2  # noqa: E402
from cryptography.hazmat.primitives import hashes  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from command_centre import auth  # noqa: E402
from command_centre.app import create_app  # noqa: E402

LOGIN = "owner@example.org"
ORIGIN = "https://mac.example-tailnet.ts.net"
RP_ID = "mac.example-tailnet.ts.net"
HEADERS = {"Tailscale-User-Login": LOGIN, "Tailscale-User-Name": "Owner Example"}


def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def write_config(**over):
    cfg = {"allowed_logins": [LOGIN], "origin": ORIGIN, "rp_id": RP_ID, "passkeys": []}
    cfg.update(over)
    auth.save_config(cfg)
    return cfg


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class Authenticator:
    """A software passkey: ES256, user present and verified."""

    def __init__(self, cred_id=b"cred-one-0123456"):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.cred_id = cred_id
        self.count = 0

    def cose(self):
        n = self.key.public_key().public_numbers()
        return cbor2.dumps({1: 2, 3: -7, -1: 1, -2: n.x.to_bytes(32, "big"), -3: n.y.to_bytes(32, "big")})

    def client_data(self, kind, challenge, origin=ORIGIN):
        return json.dumps({"type": kind, "challenge": b64(challenge), "origin": origin}).encode()

    def register(self, options, origin=ORIGIN):
        challenge = unb64(options["challenge"])
        cdj = self.client_data("webauthn.create", challenge, origin)
        auth_data = (hashlib.sha256(options["rp"]["id"].encode()).digest() + bytes([0x45]) + (0).to_bytes(4, "big")
                     + bytes(16) + len(self.cred_id).to_bytes(2, "big") + self.cred_id + self.cose())
        att = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
        return {"id": b64(self.cred_id), "rawId": b64(self.cred_id), "type": "public-key",
                "response": {"clientDataJSON": b64(cdj), "attestationObject": b64(att)}}

    def assert_(self, options, origin=ORIGIN, rp_id=RP_ID):
        self.count += 1
        challenge = unb64(options["challenge"])
        cdj = self.client_data("webauthn.get", challenge, origin)
        auth_data = hashlib.sha256(rp_id.encode()).digest() + bytes([0x05]) + self.count.to_bytes(4, "big")
        sig = self.key.sign(auth_data + hashlib.sha256(cdj).digest(), ec.ECDSA(hashes.SHA256()))
        return {"id": b64(self.cred_id), "rawId": b64(self.cred_id), "type": "public-key",
                "response": {"clientDataJSON": b64(cdj), "authenticatorData": b64(auth_data),
                             "signature": b64(sig), "userHandle": None}}


def client(**kw):
    return TestClient(create_app(client_factory=lambda: None, **kw), base_url=ORIGIN)


def post(c, path, body, headers=HEADERS, origin=ORIGIN):
    h = dict(headers)
    if origin:
        h["Origin"] = origin
    return c.post(path, json=body, headers=h)


def registered(clock=None):
    """A config with one passkey registered through the real routes; returns (client, authenticator, passkeys)."""
    write_config()
    pk = auth.Passkeys(auth.ChallengeStore(clock=clock or Clock()))
    c = client(passkeys=pk)
    a = Authenticator()
    opts = post(c, "/auth/passkey/register/options", {}).json()
    r = post(c, "/auth/passkey/register", {"credential": a.register(opts)})
    assert r.status_code == 200, r.text
    return c, a, pk


# ---------------------------------------------------------------- identity


def test_no_header_is_403():
    write_config()
    c = client()
    for path in ["/", "/money", "/passkeys", "/static/app.css", "/nope"]:
        r = c.get(path)
        assert r.status_code == 403, (path, r.status_code)
        assert "no-store" in r.headers.get("cache-control", "")
        assert "frame-ancestors 'none'" in r.headers.get("content-security-policy", "")


def test_wrong_login_is_403():
    write_config()
    c = client()
    r = c.get("/", headers={"Tailscale-User-Login": "someone@example.org", "Tailscale-User-Name": "Someone"})
    assert r.status_code == 403


def test_login_without_name_is_403():
    write_config()
    c = client()
    assert c.get("/", headers={"Tailscale-User-Login": LOGIN}).status_code == 403
    assert c.get("/", headers={"Tailscale-User-Login": LOGIN, "Tailscale-User-Name": " "}).status_code == 403


def test_right_login_is_200():
    write_config()
    c = client()
    assert c.get("/", headers=HEADERS).status_code == 200
    assert c.get("/money", headers=HEADERS).status_code == 200
    assert c.get("/static/app.css", headers=HEADERS).status_code == 200
    # the login is compared without case or surrounding space
    assert c.get("/", headers={"Tailscale-User-Login": " Owner@Example.ORG ",
                               "Tailscale-User-Name": "Owner"}).status_code == 200


def test_missing_or_empty_config_fails_closed():
    os.remove(auth.config_path())
    c = client()
    assert c.get("/", headers=HEADERS).status_code == 403
    write_config(allowed_logins=[])
    assert c.get("/", headers=HEADERS).status_code == 403
    with open(auth.config_path(), "w") as f:
        f.write("{not json")
    assert c.get("/", headers=HEADERS).status_code == 403


def test_healthz_is_open_and_says_nothing():
    os.remove(auth.config_path())
    c = client()
    r = c.get("/healthz")
    assert r.status_code == 200 and r.text == "ok", r.text
    assert "no-store" in r.headers["cache-control"]


def test_config_is_private():
    write_config()
    assert oct(os.stat(auth.config_path()).st_mode & 0o777) == "0o600"
    assert oct(os.stat(auth.config_dir()).st_mode & 0o777) == "0o700"


# ---------------------------------------------------------------- dev login


def test_dev_login_is_off_by_default():
    write_config()
    os.environ.pop("CC_DEV_LOGIN", None)
    app = create_app(client_factory=lambda: None, bind_host="127.0.0.1")
    assert app.state.dev_login is None
    assert TestClient(app).get("/").status_code == 403


def test_dev_login_needs_the_loopback_bind():
    write_config()
    os.environ["CC_DEV_LOGIN"] = LOGIN
    try:
        for host in [None, "0.0.0.0", "192.168.1.5", "::"]:
            app = create_app(client_factory=lambda: None, bind_host=host)
            assert app.state.dev_login is None, host
            assert TestClient(app).get("/").status_code == 403, host
        app = create_app(client_factory=lambda: None, bind_host="127.0.0.1")
        assert app.state.dev_login == LOGIN
        assert TestClient(app).get("/").status_code == 200
    finally:
        os.environ.pop("CC_DEV_LOGIN", None)


def test_dev_login_still_needs_an_allowed_login():
    write_config()
    os.environ["CC_DEV_LOGIN"] = "intruder@example.org"
    try:
        app = create_app(client_factory=lambda: None, bind_host="127.0.0.1")
        assert TestClient(app).get("/").status_code == 403
    finally:
        os.environ.pop("CC_DEV_LOGIN", None)


def test_main_binds_loopback_only():
    src = open(os.path.join(ROOT, "command_centre", "__main__.py")).read()
    assert 'HOST = "127.0.0.1"' in src and "0.0.0.0" not in src
    assert "proxy_headers=False" in src


# ---------------------------------------------------------------- CSRF


def test_post_needs_the_configured_origin():
    write_config()
    c = client()
    body = {"action": "check passkey"}
    assert post(c, "/auth/passkey/assert/options", body, origin=None).status_code == 403
    assert post(c, "/auth/passkey/assert/options", body, origin="https://evil.example.org").status_code == 403
    # no passkeys yet, so options are refused for a different reason, but the origin check passed
    r = post(c, "/auth/passkey/assert/options", body)
    assert r.status_code == 409, r.status_code
    assert post(c, "/auth/passkey/assert/options", body, headers={}).status_code == 403


def test_cross_site_fetch_metadata_is_refused():
    write_config()
    c = client()
    h = dict(HEADERS, Origin=ORIGIN)
    h["Sec-Fetch-Site"] = "cross-site"
    assert c.post("/auth/passkey/register/options", json={}, headers=h).status_code == 403


# ---------------------------------------------------------------- challenges


def test_challenge_embeds_the_action_hash():
    store = auth.ChallengeStore(clock=Clock())
    ch = store.issue("assert", "resolve hand check 0310: paid in full 2026-09-28")
    assert len(ch) == 48
    assert ch[16:] == auth.action_hash("assert", "resolve hand check 0310: paid in full 2026-09-28")
    assert ch[16:] != auth.action_hash("assert", "resolve hand check 0310: refunded 2026-09-28")


def test_challenge_is_single_use_and_expires():
    clock = Clock()
    store = auth.ChallengeStore(clock=clock)
    ch = store.issue("assert", "x")
    store.consume(ch, "assert", "x")
    try:
        store.consume(ch, "assert", "x")
        raise AssertionError("replay accepted")
    except auth.PasskeyError as e:
        assert e.reason == "unknown or used challenge"
    ch = store.issue("assert", "x")
    clock.t += 61
    try:
        store.consume(ch, "assert", "x")
        raise AssertionError("expired challenge accepted")
    except auth.PasskeyError as e:
        assert e.reason == "challenge expired"


def test_wrong_summary_burns_the_challenge():
    store = auth.ChallengeStore(clock=Clock())
    ch = store.issue("assert", "summary A")
    for summary in ["summary B", "summary A"]:
        try:
            store.consume(ch, "assert", summary)
            raise AssertionError("accepted")
        except auth.PasskeyError:
            pass


# ---------------------------------------------------------------- passkeys


def test_first_registration_needs_no_assertion_and_stores_public_key_only():
    c, a, pk = registered()
    cfg = auth.load_config()
    assert len(cfg["passkeys"]) == 1
    stored = cfg["passkeys"][0]
    assert stored["id"] == b64(a.cred_id)
    assert unb64(stored["public_key"]) == a.cose()
    assert set(stored) <= {"id", "public_key", "sign_count", "created", "login", "label", "transports"}


def test_registration_challenge_is_single_use():
    write_config()
    pk = auth.Passkeys(auth.ChallengeStore(clock=Clock()))
    c = client(passkeys=pk)
    a = Authenticator()
    opts = post(c, "/auth/passkey/register/options", {}).json()
    cred = a.register(opts)
    assert post(c, "/auth/passkey/register", {"credential": cred}).status_code == 200
    r = post(c, "/auth/passkey/register", {"credential": cred})
    assert r.status_code == 403 and r.json()["error"] == "unknown or used challenge", r.text


def test_registration_challenge_expires():
    write_config()
    clock = Clock()
    pk = auth.Passkeys(auth.ChallengeStore(clock=clock))
    c = client(passkeys=pk)
    opts = post(c, "/auth/passkey/register/options", {}).json()
    clock.t += 61
    r = post(c, "/auth/passkey/register", {"credential": Authenticator().register(opts)})
    assert r.status_code == 403 and r.json()["error"] == "challenge expired"
    assert auth.load_config()["passkeys"] == []


def test_registration_from_another_origin_is_refused():
    write_config()
    pk = auth.Passkeys(auth.ChallengeStore(clock=Clock()))
    c = client(passkeys=pk)
    opts = post(c, "/auth/passkey/register/options", {}).json()
    r = post(c, "/auth/passkey/register", {"credential": Authenticator().register(opts, origin="https://evil.example.org")})
    assert r.status_code == 403 and r.json()["error"] == "verification failed"


def test_second_registration_needs_a_fresh_assertion():
    c, a, pk = registered()
    # without an assertion: refused
    r = post(c, "/auth/passkey/register/options", {})
    assert r.status_code == 403 and r.json()["error"] == "assertion required", r.text
    # an assertion for another action: refused
    opts = post(c, "/auth/passkey/assert/options", {"action": "check passkey"}).json()
    r = post(c, "/auth/passkey/register/options", {"assertion": a.assert_(opts)})
    assert r.status_code == 403 and r.json()["error"] == "wrong action", r.text
    # an assertion for "register a new passkey": allowed, and the new key is stored
    opts = post(c, "/auth/passkey/assert/options", {"action": auth.REGISTER_SUMMARY}).json()
    reg = post(c, "/auth/passkey/register/options", {"assertion": a.assert_(opts)})
    assert reg.status_code == 200, reg.text
    assert [x["id"] for x in reg.json()["excludeCredentials"]] == [b64(a.cred_id)]
    b = Authenticator(b"cred-two-0123456")
    assert post(c, "/auth/passkey/register", {"credential": b.register(reg.json())}).status_code == 200
    assert len(auth.load_config()["passkeys"]) == 2


def test_assertion_accepted_and_sign_count_updated():
    c, a, pk = registered()
    opts = post(c, "/auth/passkey/assert/options", {"action": "check passkey"}).json()
    assert opts["userVerification"] == "required"
    r = post(c, "/auth/passkey/assert", {"action": "check passkey", "credential": a.assert_(opts)})
    assert r.status_code == 200 and r.json() == {"ok": True}, r.text
    assert auth.load_config()["passkeys"][0]["sign_count"] == 1


def test_require_fresh_assertion_binds_the_summary():
    c, a, pk = registered()
    summary = "resolve hand check 0310: paid in full 2026-09-28"
    opts = pk.assertion_options(summary)
    cred = a.assert_(opts)
    try:
        pk.require_fresh_assertion(cred, "resolve hand check 0310: refunded 2026-09-28")
        raise AssertionError("another action's assertion accepted")
    except auth.PasskeyError as e:
        assert e.reason == "wrong action"
    # the challenge was burnt by the failed attempt, so even the right summary is now refused
    try:
        pk.require_fresh_assertion(cred, summary)
        raise AssertionError("burnt challenge accepted")
    except auth.PasskeyError as e:
        assert e.reason == "unknown or used challenge"
    opts = pk.assertion_options(summary)
    assert pk.require_fresh_assertion(a.assert_(opts), summary) == b64(a.cred_id)


def test_require_fresh_assertion_refuses_replay():
    c, a, pk = registered()
    opts = pk.assertion_options("x")
    cred = a.assert_(opts)
    pk.require_fresh_assertion(cred, "x")
    try:
        pk.require_fresh_assertion(cred, "x")
        raise AssertionError("replay accepted")
    except auth.PasskeyError as e:
        assert e.reason == "unknown or used challenge"


def test_require_fresh_assertion_refuses_after_60_seconds():
    clock = Clock()
    c, a, pk = registered(clock)
    opts = pk.assertion_options("x")
    clock.t += 60.5
    try:
        pk.require_fresh_assertion(a.assert_(opts), "x")
        raise AssertionError("stale assertion accepted")
    except auth.PasskeyError as e:
        assert e.reason == "challenge expired"


def test_require_fresh_assertion_refuses_unknown_key_and_bad_signature():
    c, a, pk = registered()
    stranger = Authenticator(b"cred-stranger-01")
    try:
        pk.require_fresh_assertion(stranger.assert_(pk.assertion_options("x")), "x")
        raise AssertionError("unknown credential accepted")
    except auth.PasskeyError as e:
        assert e.reason == "unknown credential"
    forged = a.assert_(pk.assertion_options("x"))
    sig = bytearray(unb64(forged["response"]["signature"]))
    sig[-1] ^= 1
    forged["response"]["signature"] = b64(bytes(sig))
    try:
        pk.require_fresh_assertion(forged, "x")
        raise AssertionError("bad signature accepted")
    except auth.PasskeyError as e:
        assert e.reason == "verification failed"
    other_rp = a.assert_(pk.assertion_options("x"), rp_id="evil.example.org")
    try:
        pk.require_fresh_assertion(other_rp, "x")
        raise AssertionError("another RP's assertion accepted")
    except auth.PasskeyError as e:
        assert e.reason == "verification failed"


def test_require_fresh_assertion_with_mocked_verifier():
    """py_webauthn's verifier patched: the helper still passes it the bound challenge and the stored key."""
    c, a, pk = registered()
    seen = {}

    class Verified:
        new_sign_count = 42

    def fake_verify(**kw):
        seen.update(kw)
        return Verified()

    real = auth.verify_authentication_response
    auth.verify_authentication_response = fake_verify
    try:
        opts = pk.assertion_options("summary")
        pk.require_fresh_assertion(a.assert_(opts), "summary")
    finally:
        auth.verify_authentication_response = real
    assert seen["expected_challenge"] == unb64(opts["challenge"])
    assert seen["expected_challenge"][16:] == auth.action_hash("assert", "summary")
    assert seen["expected_rp_id"] == RP_ID and seen["expected_origin"] == ORIGIN
    assert seen["credential_public_key"] == a.cose() and seen["require_user_verification"] is True
    assert auth.load_config()["passkeys"][0]["sign_count"] == 42


def test_garbage_credentials_are_refused_cleanly():
    c, a, pk = registered()
    for bad in [None, "x", {}, {"response": {}}, {"response": {"clientDataJSON": "!!!"}},
                {"response": {"clientDataJSON": b64(b"{}")}}]:
        try:
            pk.require_fresh_assertion(bad, "x")
            raise AssertionError(f"accepted {bad!r}")
        except auth.PasskeyError:
            pass
    r = post(c, "/auth/passkey/assert", {"action": "x", "credential": "junk"})
    assert r.status_code == 403
    r = c.post("/auth/passkey/assert", content=b"not json", headers=dict(HEADERS, Origin=ORIGIN))
    assert r.status_code == 400


def test_assert_options_need_a_summary():
    c, a, pk = registered()
    for body in [{}, {"action": ""}, {"action": "x" * 501}, {"action": 5}]:
        assert post(c, "/auth/passkey/assert/options", body).status_code == 400, body


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failures += 1
            except Exception as e:  # an unexpected error is a failure too, with its type
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
