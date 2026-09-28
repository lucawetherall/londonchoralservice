#!/usr/bin/env python3
"""Tests for the Command Centre's push notifications (phase 5): command_centre/push.py, the push-subscribe and
push-unsubscribe actions, the /device page and scripts/reports/cc_event.py.

Stdlib runner, Starlette's TestClient, a software passkey, a fake pywebpush and a fake `security` CLI, fake
fixtures in a temp LCS_PRIVATE_DIR (fake names, example.org emails). Never touches the Keychain, a push service or
the real private files.
"""
import base64, csv, datetime, hashlib, json, os, subprocess, sys, tempfile, types
from pathlib import Path
from zoneinfo import ZoneInfo

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
os.environ["CC_VAPID_STORE"] = "file"
os.environ.pop("CC_DEV_LOGIN", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import cbor2  # noqa: E402
from cryptography.hazmat.primitives import hashes  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from command_centre import actions, auth, data, push  # noqa: E402
from command_centre.app import create_app  # noqa: E402
import cc_event  # noqa: E402  (push.py put scripts/reports on the path)

LONDON = ZoneInfo("Europe/London")
LOGIN = "owner@example.org"
RP_ID = "mac.example-tailnet.ts.net"
ORIGIN = f"https://{RP_ID}"
HEADERS = {"Tailscale-User-Login": LOGIN, "Tailscale-User-Name": "Owner"}
APPLE = "https://web.push.apple.com/QGuQyavXutnMH3u9bXfFoSSpAq7uT0qNJhMY"
P256DH = "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM"
AUTH = "tBHItJI5svbpez7KI4CCXg"
LEDGER_COLS = ["booking_ref", "invoice_date", "event_date", "client_name", "client_email", "occasion", "ensemble",
               "value_gbp", "enquiry_date", "source", "gclid", "consent", "uploaded_at", "notes"]


def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


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

    def register(self, options):
        cdj = json.dumps({"type": "webauthn.create", "challenge": options["challenge"], "origin": ORIGIN}).encode()
        auth_data = (hashlib.sha256(RP_ID.encode()).digest() + bytes([0x45]) + (0).to_bytes(4, "big") + bytes(16)
                     + len(self.cred_id).to_bytes(2, "big") + self.cred_id + self.cose())
        att = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
        return {"id": b64(self.cred_id), "rawId": b64(self.cred_id), "type": "public-key",
                "response": {"clientDataJSON": b64(cdj), "attestationObject": b64(att)}}

    def assert_(self, options):
        self.count += 1
        cdj = json.dumps({"type": "webauthn.get", "challenge": options["challenge"], "origin": ORIGIN}).encode()
        auth_data = hashlib.sha256(RP_ID.encode()).digest() + bytes([0x05]) + self.count.to_bytes(4, "big")
        sig = self.key.sign(auth_data + hashlib.sha256(cdj).digest(), ec.ECDSA(hashes.SHA256()))
        return {"id": b64(self.cred_id), "rawId": b64(self.cred_id), "type": "public-key",
                "response": {"clientDataJSON": b64(cdj), "authenticatorData": b64(auth_data),
                             "signature": b64(sig), "userHandle": None}}


def write_csv(path, cols, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def fixtures():
    cc = Path(TMP) / "command-centre"
    for name in ("events.jsonl", "push-state.json", "audit.jsonl"):
        (cc / name).unlink(missing_ok=True)
    (Path(TMP) / "assistant-state.json").unlink(missing_ok=True)
    auth.save_config({"allowed_logins": [LOGIN], "origin": ORIGIN, "rp_id": RP_ID, "passkeys": []})
    write_csv(os.path.join(TMP, "bookings.csv"), LEDGER_COLS, [
        {"booking_ref": "2111", "event_date": "2026-11-21", "client_name": "Ann Smithfield",
         "client_email": "ann@example.org", "occasion": "wedding", "value_gbp": "650"}])
    write_csv(str(data.si.STORE), data.si.COLUMNS, [
        {"message_id": "1789828736363141700", "received": "2026-09-20", "singer_name": "Jane Fenwick-Hale",
         "singer_email": "jane@example.org", "amount_gbp": "120.00"}])


def setup():
    fixtures()
    clock = Clock()
    pk = auth.Passkeys(auth.ChallengeStore(clock=clock))
    app = create_app(client_factory=lambda: None, passkeys=pk, checkout=lambda: "main")
    c = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000), follow_redirects=False)
    a = Authenticator()
    code = auth.new_bootstrap()
    opts = post(c, "/auth/passkey/register/options", {"bootstrap": code}).json()
    assert post(c, "/auth/passkey/register", {"credential": a.register(opts), "bootstrap": code}).status_code == 200
    return c, a, clock


def post(c, path, body, origin=ORIGIN):
    h = dict(HEADERS)
    if origin:
        h["Origin"] = origin
    return c.post(path, json=body, headers=h)


def sub_input(endpoint=APPLE):
    return {"endpoint": endpoint, "p256dh": P256DH, "auth": AUTH}


def subs():
    return auth.load_config().get("push_subscriptions", [])


class FakeWebPush:
    __module__ = "fake_pywebpush"

    def __init__(self, status=None):
        self.calls, self.status = [], status

    def __call__(self, info, body, **kw):
        self.calls.append((info, json.loads(body), kw))
        if self.status:
            raise FakeError(self.status)


class FakeError(Exception):
    def __init__(self, status):
        super().__init__("push failed")
        self.response = types.SimpleNamespace(status_code=status)


def with_fake(fake):
    saved = push.WEBPUSH
    push.WEBPUSH = fake
    return saved


# ---------------------------------------------------------------- subscribing


def test_subscribe_needs_a_fresh_passkey_bound_to_this_device():
    c, a, clock = setup()
    p = post(c, "/actions/push-subscribe/preview", {"input": sub_input()})
    assert p.status_code == 200, p.text
    body = p.json()
    assert body["passkey"] is True and "web.push.apple.com" in body["summary"]
    assert APPLE not in body["summary"] and AUTH not in body["summary"]  # the secret keys never reach a page
    # no credential: refused, nothing stored
    r = post(c, "/actions/push-subscribe/run", {"input": sub_input()})
    assert r.status_code == 403 and subs() == []
    # stale
    clock.t += 61
    r = post(c, "/actions/push-subscribe/run", {"input": sub_input(), "credential": a.assert_(body["options"])})
    assert r.status_code == 403 and r.json()["error"] == "challenge expired" and subs() == []
    # approved for another device
    other = sub_input("https://web.push.apple.com/another-device-endpoint-0001")
    p2 = post(c, "/actions/push-subscribe/preview", {"input": other}).json()
    r = post(c, "/actions/push-subscribe/run", {"input": sub_input(), "credential": a.assert_(p2["options"])})
    assert r.status_code == 403 and r.json()["error"] == "wrong action" and subs() == []
    # another action's assertion
    p3 = post(c, "/auth/passkey/assert/options", {"action": "check"}).json()
    r = post(c, "/actions/push-subscribe/run", {"input": sub_input(), "credential": a.assert_(p3)})
    assert r.status_code == 403 and subs() == []
    # the right one
    p = post(c, "/actions/push-subscribe/preview", {"input": sub_input()}).json()
    r = post(c, "/actions/push-subscribe/run", {"input": sub_input(), "credential": a.assert_(p["options"])})
    assert r.status_code == 200 and r.json()["ok"], r.text
    [s] = subs()
    assert s["endpoint"] == APPLE and s["id"] == push.subscription_id(APPLE) and s["login"] == LOGIN
    audit = [json.loads(line) for line in (Path(TMP) / "command-centre" / "audit.jsonl").read_text().splitlines()]
    assert audit[-1]["result"] == "ok" and audit[-1]["input"] == {"service": "web.push.apple.com", "id": s["id"]}
    assert APPLE not in json.dumps(audit) and AUTH not in json.dumps(audit)
    # a POST from another origin is refused before anything
    assert post(c, "/actions/push-subscribe/preview", {"input": sub_input()}, origin="https://evil.example").status_code == 403


def test_only_known_push_services_are_accepted():
    c, a, _ = setup()
    for bad in ("http://web.push.apple.com/x", "https://evil.example/push", "https://web.push.apple.com:8443/x",
                "https://user@web.push.apple.com/x", "https://web.push.apple.com/x?y=1",
                "https://web.push.apple.com/x#y", "https://push.apple.com.evil.example/x", "https://127.0.0.1/x",
                "https://fcm.googleapis.com.evil.example/x", "https://a b.push.apple.com/x",
                "https://127.0.0.1\\.push.apple.com/x"):
        r = post(c, "/actions/push-subscribe/preview", {"input": sub_input(bad)})
        assert r.status_code == 400, (bad, r.text)
    for good in (APPLE, "https://fcm.googleapis.com/fcm/send/abc", "https://updates.push.services.mozilla.com/wpush/v2/x",
                 "https://api.push.apple.com/x", "https://wns2-db5p.notify.windows.com/w/?token=x".split("?")[0],
                 "https://web.push.apple.com:443/x"):
        assert push.endpoint_ok(good), good
    for bad_keys in ({"p256dh": "short"}, {"auth": "has space in it here"}, {"extra": "x"}):
        r = post(c, "/actions/push-subscribe/preview", {"input": dict(sub_input(), **bad_keys)})
        assert r.status_code == 400, bad_keys


PROBES = (
    # a backslash: urllib3 (what requests sends with) reads the host as the part before it, urlsplit the whole
    "https://127.0.0.1\\.push.apple.com/x", "https://169.254.169.254\\.push.apple.com/x",
    "https://evil.com\\.push.apple.com/x", "https://evil.com\\@web.push.apple.com/x",
    # user info, in every spelling
    "https://user@web.push.apple.com/x", "https://user:pw@web.push.apple.com/x", "https://@web.push.apple.com/x",
    "https://evil.com%40web.push.apple.com/x", "https://evil.com@web.push.apple.com/x",
    # percent-encoding and separators in the host
    "https://web%2Epush.apple.com/x", "https://evil.com%2F.push.apple.com/x", "https://evil.com%5C.push.apple.com/x",
    "https://evil.com;.push.apple.com/x", "https://web.push.apple.com;x/x",
    # IDN and non-ASCII (a fullwidth dot, a Cyrillic letter)
    "https://evil。push.apple.com/x", "https://wеb.push.apple.com/x", "https://ex\u00e4mple.push.apple.com/x",
    # empty labels and trailing dots
    "https://evil..push.apple.com/x", "https://web..push.apple.com/x", "https://..push.apple.com/x",
    "https://web.push.apple.com./x", "https://.push.apple.com/x",
    # IP literals
    "https://[::1]/x", "https://[::ffff:127.0.0.1].push.apple.com/x", "https://127.0.0.1/x", "https://2130706433/x",
    "https://0x7f000001/x",
    # ports other than 443, whitespace, other schemes
    "https://web.push.apple.com:80/x", "https://web.push.apple.com:0443/x", "https://web.push.apple.com:/x",
    "https://web.push.apple.com :443/x", "https://web.push.apple.com/x y", "https://web.push.apple.com\t/x",
    "HTTPS://web.push.apple.com/x", "https:web.push.apple.com/x", "https:///web.push.apple.com/x",
    "https://WEB.PUSH.APPLE.COM/x",
)


def test_endpoint_probes_are_all_refused():
    for bad in PROBES:
        assert not push.endpoint_ok(bad), bad
    assert push.endpoint_ok("https://web.push.apple.com:443/QGuQ-_x")


class RedirectAdapter:
    """A requests transport that answers every request with a 307 to the metadata address."""

    def __init__(self):
        self.sent = []

    def send(self, request, **kw):
        import requests
        self.sent.append((request.url, kw))
        r = requests.Response()
        r.status_code, r.url, r.request = 307, request.url, request
        r.headers["Location"] = "http://169.254.169.254/latest/meta-data/"
        r._content = b""
        return r

    def close(self):
        pass


def test_the_push_session_never_follows_a_redirect_or_posts_elsewhere():
    s = push._session()
    assert s.max_redirects == 0 and s.trust_env is False
    fake = RedirectAdapter()
    s.mount("https://", fake)
    s.mount("http://", fake)
    r = s.post(APPLE, data=b"x", timeout=1)
    assert r.status_code == 307 and len(fake.sent) == 1 and fake.sent[0][0] == APPLE  # not followed
    r = s.request("POST", APPLE, data=b"x", allow_redirects=True, timeout=1)
    assert r.status_code == 307 and len(fake.sent) == 2  # a caller can't turn following back on
    for bad in ("https://evil.example/x", "https://127.0.0.1\\.push.apple.com/x"):
        try:
            s.post(bad, data=b"x", timeout=1)
        except push.PushError:
            pass
        else:
            raise AssertionError(bad)
    assert len(fake.sent) == 2


def test_a_stored_subscription_with_a_bad_endpoint_is_never_sent_to():
    fixtures()
    cfg = auth.load_config()
    cfg["push_subscriptions"] = [{"id": "0" * 16, "endpoint": "https://evil.com\\.push.apple.com/x",
                                  "p256dh": P256DH, "auth": AUTH}]
    auth.save_config(cfg)
    fake = FakeWebPush()
    saved = with_fake(fake)
    try:
        assert push.send({"title": "t", "body": "b", "url": "/"}) == {"sent": 0, "failed": 0, "dropped": 0}
        assert push.send({"title": "t", "body": "b", "url": "/"}, subs=cfg["push_subscriptions"])["failed"] == 1
        assert fake.calls == []
    finally:
        push.WEBPUSH = saved


def test_unsubscribe_needs_no_passkey_and_removes_the_device():
    c, a, _ = setup()
    p = post(c, "/actions/push-subscribe/preview", {"input": sub_input()}).json()
    post(c, "/actions/push-subscribe/run", {"input": sub_input(), "credential": a.assert_(p["options"])})
    sid = push.subscription_id(APPLE)
    assert actions.REGISTRY["push-unsubscribe"].passkey is False
    assert post(c, "/actions/push-unsubscribe/run", {"input": {"id": "0" * 16}}).status_code == 400
    r = post(c, "/actions/push-unsubscribe/run", {"input": {"id": sid}})
    assert r.status_code == 200, r.text
    assert subs() == []
    # same-origin still required
    assert post(c, "/actions/push-unsubscribe/run", {"input": {"id": sid}}, origin=None).status_code == 403


def test_device_page_never_makes_the_key():
    c, a, _ = setup()
    push.forget_key()
    push.vapid_file().unlink(missing_ok=True)
    page = c.get("/device", headers=HEADERS).text
    assert not push.vapid_file().exists()  # a GET writes nothing
    assert 'data-key=""' in page and "Not set up yet" in page
    assert push.public_key_b64(create=False) is None and not push.vapid_file().exists()
    push.private_key()  # what the service does when it starts
    page = c.get("/device", headers=HEADERS).text
    assert f'data-key="{push.public_key_b64(create=False)}"' in page and "Not set up yet" not in page


def test_the_service_makes_the_key_at_start_up():
    fake = FakeSecurity()
    saved = push.SECURITY_RUNNER, push.watch, os.environ.pop("CC_VAPID_STORE")

    async def no_watch(stop=None, poll=None):
        return None

    push.SECURITY_RUNNER, push.watch = fake, no_watch
    os.environ["CC_NO_REFRESH_JOB"] = "1"
    push.forget_key()
    try:
        fixtures()
        app = create_app(client_factory=lambda: None, checkout=lambda: "main", watch=True)
        assert fake.stored is None and fake.calls == []  # nothing before start-up
        with TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000)):
            pass
        assert fake.stored and len(fake.stored) == 64
        assert sum(1 for argv, _ in fake.calls if argv[1] == "-i") == 1
    finally:
        push.SECURITY_RUNNER, push.watch = saved[0], saved[1]
        os.environ["CC_VAPID_STORE"] = saved[2]
        os.environ.pop("CC_NO_REFRESH_JOB", None)
        push.forget_key()


def test_save_state_leaves_no_temp_file_when_it_fails():
    fixtures()
    d = auth.config_dir()
    try:
        push.save_state({"bad": object()})  # json can't write it
    except TypeError:
        pass
    else:
        raise AssertionError("save_state accepted an unwritable value")
    assert not [p.name for p in d.iterdir() if p.name.endswith(".tmp")]
    push.save_state({"ok": 1})
    assert push.load_state() == {"ok": 1} and not [p for p in d.iterdir() if p.name.endswith(".tmp")]


def test_device_page_shows_the_key_and_devices_without_secrets():
    c, a, _ = setup()
    push.private_key()  # made at the service's start-up
    p = post(c, "/actions/push-subscribe/preview", {"input": sub_input()}).json()
    post(c, "/actions/push-subscribe/run", {"input": sub_input(), "credential": a.assert_(p["options"])})
    page = c.get("/device", headers=HEADERS).text
    key = push.public_key_b64()
    assert f'data-key="{key}"' in page and push.subscription_id(APPLE) in page
    assert APPLE not in page and AUTH not in page and P256DH not in page
    assert "Enable notifications" in page and "/static/push.js" in page
    assert len(unb64(key)) == 65 and unb64(key)[0] == 4


# ---------------------------------------------------------------- payloads and sending


def test_payload_is_a_fixed_template_with_validated_fields_only():
    fixtures()
    m = push.payload({"kind": "enquiry", "at": "x", "extra": "should not pass",
                      "fields": {"first": "Ann", "occasion": "wedding", "date": "2026-11-21"}})
    assert m == {"title": "New enquiry", "body": "Ann: wedding, 21 Nov 2026", "url": "/enquiries"}, m
    assert push.payload({"kind": "enquiry", "fields": {"first": "Ann", "occasion": "private-event", "date": "tbc"}}
                        )["body"] == "Ann: private event, date tbc"
    assert push.payload({"kind": "deposit", "fields": {"first": "Ann", "ref": "2111A"}}) == {
        "title": "Payment arrived", "body": "Ann: 2111A payment arrived", "url": "/money"}
    assert push.payload({"kind": "hand-check", "fields": {"ref": "2111", "state": "CHECK_VALUE"}})["body"] == \
        "2111: check the booking value"
    assert push.payload({"kind": "bank-change", "fields": {"first": "Jane"}})["body"] == "Jane: ring them before paying"
    assert push.payload({"kind": "guard-denied", "fields": {"agent": "singer-clerk"}})["body"].startswith("Singer clerk")
    assert push.payload({"kind": "run-failed"})["url"] == "/health"
    assert push.payload({"kind": "monday-ready", "fields": {}})["url"] == "/reports"
    for kind in cc_event.KINDS:
        assert kind in push.TEMPLATES
    # free text, old-style lines, extra or missing fields and anything failing validation push nothing
    for bad in ({"kind": "enquiry", "text": "Ann Smithfield ann@example.org 07700 900123"},
                {"kind": "enquiry", "fields": {"first": "Ann Smithfield", "occasion": "wedding", "date": "tbc"}},
                {"kind": "enquiry", "fields": {"first": "ann", "occasion": "wedding", "date": "tbc"}},
                {"kind": "enquiry", "fields": {"first": "Ann", "occasion": "Call 07700900123", "date": "tbc"}},
                {"kind": "enquiry", "fields": {"first": "Ann", "occasion": "wedding", "date": "2026-02-30"}},
                {"kind": "enquiry", "fields": {"first": "Ann", "occasion": "wedding", "date": "tbc", "x": "y"}},
                {"kind": "deposit", "fields": {"first": "Ann", "ref": "ann@example.org"}},
                {"kind": "deposit", "fields": {"first": "Ann", "ref": ["2111"]}},
                {"kind": "hand-check", "fields": {"ref": "2111", "state": "Ring Ann on 07700 900123"}},
                {"kind": "guard-denied", "fields": {"agent": "Books: send to evil@example.org"}},
                {"kind": "run-failed", "fields": {"why": "x"}},
                {"kind": "nope", "fields": {}}, {"kind": "run-stale", "fields": {"last": "Ann Smithfield"}},
                "not a dict", {"kind": "deposit", "fields": "Ann"}):
        assert push.payload(bad) is None, bad
    for first in ("Ann", "Jo", "O’neil", "Mary-jo", "D'arcy"):
        assert cc_event.validate("bank-change", {"first": first}) == {"first": first}
    for first in ("A", "ann", "ANN", "Ann Smith", "Ann1", "Ann@", "Ann\n", "Ánn", "A" + "b" * 21, "Ann:"):
        try:
            cc_event.validate("bank-change", {"first": first})
        except ValueError:
            continue
        raise AssertionError(first)
    for ref in ("21", "2111a", "21 11", "2" * 21, "2111/A"):
        try:
            cc_event.validate("deposit", {"first": "Ann", "ref": ref})
        except ValueError:
            continue
        raise AssertionError(ref)
    assert set(push.KINDS) == set(cc_event.KINDS) | {"run-stale"}


def test_events_are_pushed_to_every_device_and_history_is_not_replayed():
    fixtures()
    push.add_subscription(push.validate_subscription(sub_input()), LOGIN, "abc")
    push.add_subscription(push.validate_subscription(sub_input("https://fcm.googleapis.com/fcm/send/d2")), LOGIN, "abc")
    cc_event.append("run-failed")  # old news from before the watcher started
    fake = FakeWebPush()
    saved = with_fake(fake)
    try:
        now = datetime.datetime(2026, 9, 28, 23, 0, tzinfo=LONDON)  # night: no stale-run check
        assert push.look(now) == [] and fake.calls == []  # the first look starts at the end of the file
        cc_event.append("deposit", {"first": "Ann", "ref": "2111"})
        cc_event.append("bank-change", {"first": "Jane"})
        pushed = push.look(now)
        assert [p["title"] for p in pushed] == ["Payment arrived", "Singer bank details changed"]
        assert len(fake.calls) == 4
        info, body, kw = fake.calls[0]
        assert info == {"endpoint": APPLE, "keys": {"p256dh": P256DH, "auth": AUTH}}
        assert body == {"title": "Payment arrived", "body": "Ann: 2111 payment arrived", "url": "/money"}
        assert kw["vapid_claims"] == {"sub": ORIGIN} and kw["timeout"] == push.PUSH_TIMEOUT
        assert push.look(now) == []  # nothing new
        # a torn line is left for the next look; a garbage line is skipped
        with open(push.events_path(), "a") as f:
            f.write("not json\n")
        assert push.look(now) == []
    finally:
        push.WEBPUSH = saved


def test_a_gone_device_is_dropped():
    fixtures()
    push.add_subscription(push.validate_subscription(sub_input()), LOGIN, "abc")
    saved = with_fake(FakeWebPush(status=410))
    try:
        assert push.send({"title": "t", "body": "b", "url": "/"}) == {"sent": 0, "failed": 0, "dropped": 1}
        assert subs() == []
    finally:
        push.WEBPUSH = saved
    push.add_subscription(push.validate_subscription(sub_input()), LOGIN, "abc")
    saved = with_fake(FakeWebPush(status=500))
    try:
        assert push.send({"title": "t", "body": "b", "url": "/"})["failed"] == 1 and len(subs()) == 1
    finally:
        push.WEBPUSH = saved


# ---------------------------------------------------------------- stale runs


def set_state_mtime(when):
    path = Path(TMP) / "assistant-state.json"
    path.write_text("{}")
    os.utime(path, (when.timestamp(), when.timestamp()))


def test_stale_run_counts_daytime_hours_and_pushes_once():
    fixtures()
    at = lambda d, h, m=0: datetime.datetime(2026, 9, d, h, m, tzinfo=LONDON)  # noqa: E731
    st = {}
    set_state_mtime(at(27, 20))  # the last run of yesterday
    assert push.stale_run(at(28, 7), st) is None  # before 08:00: not checked
    assert push.stale_run(at(28, 8, 5), st) is None  # 1h (20-21) + 5 min: the first run isn't late
    assert push.stale_run(at(28, 10), st) is None  # exactly 3 daytime hours
    e = push.stale_run(at(28, 10, 30), st)
    assert e and e["kind"] == "run-stale" and push.payload(e)["url"] == "/health"
    assert push.stale_run(at(28, 12), st) is None  # once per stale file
    assert push.stale_run(at(28, 21, 30), st) is None  # after 21:00: not checked
    set_state_mtime(at(28, 12))  # it ran again: a later gap is reported again
    assert push.stale_run(at(28, 14), st) is None
    assert push.stale_run(at(28, 15, 30), st)
    (Path(TMP) / "assistant-state.json").unlink()
    st = {}
    never = push.stale_run(at(28, 12), st)
    assert never["fields"] == {"last": "never"} and push.payload(never)["body"].endswith("(never seen).")
    assert push.payload(e)["body"] == "Not run for 3 daytime hours (last seen Sun 20:00)."
    assert push.stale_run(at(28, 13), st) is None
    assert push.daytime_between(at(27, 20), at(28, 9)) == datetime.timedelta(hours=2)


# ---------------------------------------------------------------- cc_event.py


def test_cc_event_cli_takes_a_kind_and_validated_fields_only():
    fixtures()
    script = os.path.join(ROOT, "scripts", "reports", "cc_event.py")
    env = dict(os.environ)

    def run(*args):
        return subprocess.run([sys.executable, script, *args], capture_output=True, text=True, env=env)

    assert run("nope").returncode == 2
    assert run("enquiry").returncode == 2  # missing fields
    assert run("enquiry", "Ann: wedding").returncode == 2  # free text is not an argument
    assert run("run-failed", "the reason").returncode == 2
    assert run("deposit", "--first", "Ann", "--ref", "2111", "--text", "x").returncode == 2
    r = run("enquiry", "--first", "Ann Smithfield", "--occasion", "wedding", "--date", "tbc")
    assert r.returncode == 1 and "first name" in r.stderr and "Smithfield" not in r.stderr
    assert run("enquiry", "--first", "Ann", "--occasion", "a party at 10 Downing St", "--date", "tbc").returncode == 1
    assert run("hand-check", "--ref", "2111", "--state", "call Ann").returncode == 1
    assert run("guard-denied", "--agent", "Books: reason").returncode == 1
    path = Path(TMP) / "command-centre" / "events.jsonl"
    assert not path.exists()  # nothing refused was written
    r = run("enquiry", "--first", "Ann", "--occasion", "private event", "--date", "2026-11-21")
    assert r.returncode == 0 and r.stdout.strip() == "event recorded: enquiry", r.stderr
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert oct(path.parent.stat().st_mode & 0o777) == "0o700"
    event = json.loads(path.read_text().splitlines()[-1])
    assert set(event) == {"at", "kind", "fields"} and event["kind"] == "enquiry"
    assert event["fields"] == {"first": "Ann", "occasion": "private-event", "date": "2026-11-21"}
    for args in (("deposit", "--first", "Ann", "--ref", "2111A"), ("hand-check", "--ref", "2111", "--state", "NOTED_PAID"),
                 ("bank-change", "--first", "Jane"), ("guard-denied", "--agent", "monday"), ("run-failed",),
                 ("monday-ready",)):
        assert run(*args).returncode == 0, args
    assert {json.loads(line)["kind"] for line in path.read_text().splitlines()} == set(cc_event.KINDS)


def test_every_cc_event_line_in_the_prompts_uses_the_fixed_syntax():
    import re, shlex
    samples = {"first name": "Ann", "ref": "2111", "invoice ref": "2111A", "state": "CHECK_VALUE",
               "occasion": "wedding", "wedding|funeral|christmas|corporate|private-event|other": "private-event",
               "YYYY-MM-DD or tbc": "tbc"}
    texts = [p.read_text() for p in sorted((Path(ROOT) / ".claude" / "agents").glob("*.md"))]
    texts.append((Path(ROOT) / "docs" / "HANDOVER-2026-09-27-ads-analytics.md").read_text())
    lines = [m.group(1) for t in texts for m in re.finditer(r"cc_event\.py ([^`\n]*)", t)]
    kinds = set()
    for line in lines:
        line = re.sub(r"\s+\(.*$", "", line).strip()
        filled = re.sub(r"<([^<>]*)>", lambda m: samples[m.group(1)], line)
        args = cc_event.parser().parse_args(shlex.split(filled))
        cc_event.validate(args.kind, {n: getattr(args, n) for n in cc_event.KINDS[args.kind]})
        assert "'" not in line, line  # no free-text argument left
        kinds.add(args.kind)
    assert kinds >= {"enquiry", "deposit", "hand-check", "bank-change", "guard-denied", "monday-ready"}, kinds


# ---------------------------------------------------------------- VAPID keys


def test_vapid_file_store_is_mode_600_and_stable():
    fixtures()
    push.forget_key()
    push.vapid_file().unlink(missing_ok=True)
    first = push.public_key_b64()
    assert oct(push.vapid_file().stat().st_mode & 0o777) == "0o600"
    push.forget_key()
    assert push.public_key_b64() == first


class FakeSecurity:
    def __init__(self):
        self.calls, self.stored = [], None

    def __call__(self, argv, **kw):
        self.calls.append((argv, kw))
        if argv[1] == "find-generic-password":
            if self.stored is None:
                return subprocess.CompletedProcess(argv, 44, b"", b"not found")
            return subprocess.CompletedProcess(argv, 0, (self.stored + "\n").encode(), b"")
        if argv[1] == "-i":
            cmd = kw["input"].decode()
            assert cmd.startswith(f"add-generic-password -s {push.KEYCHAIN_SERVICE} -a {push.KEYCHAIN_ACCOUNT} ")
            self.stored = cmd.split(" -w ")[1].strip()
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        raise AssertionError(argv)


def test_keychain_store_keeps_the_key_off_the_command_line():
    fake = FakeSecurity()
    saved_runner, saved_env = push.SECURITY_RUNNER, os.environ.pop("CC_VAPID_STORE")
    push.SECURITY_RUNNER = fake
    push.forget_key()
    try:
        key = push.public_key_b64()
        assert fake.stored and len(fake.stored) == 64
        for argv, kw in fake.calls:
            assert argv[0] == "/usr/bin/security" and kw["shell"] is False
            assert fake.stored not in " ".join(argv)  # never in a process list
        push.forget_key()
        assert push.public_key_b64() == key  # read back, not made again
        assert sum(1 for a, _ in fake.calls if a[1] == "-i") == 1
    finally:
        push.SECURITY_RUNNER = saved_runner
        os.environ["CC_VAPID_STORE"] = saved_env
        push.forget_key()


# ---------------------------------------------------------------- caps and robustness


def test_pushes_are_capped_per_pass_and_per_hour():
    fixtures()
    push.add_subscription(push.validate_subscription(sub_input()), LOGIN, "abc")
    fake = FakeWebPush()
    saved = with_fake(fake)
    try:
        now = datetime.datetime(2026, 9, 28, 23, 0, tzinfo=LONDON)
        push.look(now)  # the first look starts at the end
        for _ in range(8):
            cc_event.append("bank-change", {"first": "Jane"})
        pushed = push.look(now)
        assert len(pushed) == push.PASS_MAX + 1 == 6, pushed
        assert pushed[-1]["title"] == "And 3 more" and pushed[-1]["url"] == "/activity"
        assert len(fake.calls) == 6
        # 6 of the hour's 20 used; 3 more passes of 8 events: 6 + 6 + 6 would be 24, so the third pass is cut
        for _ in range(2):
            for _ in range(8):
                cc_event.append("bank-change", {"first": "Jane"})
            assert len(push.look(now)) == 6
        for _ in range(8):
            cc_event.append("bank-change", {"first": "Jane"})
        third = push.look(now)
        assert len(third) == 2 and third[-1]["title"] == "And 7 more", third
        assert len(fake.calls) == push.HOUR_MAX == 20
        cc_event.append("bank-change", {"first": "Jane"})
        assert push.look(now) == [] and len(fake.calls) == 20  # the hour is used up
        later = now + datetime.timedelta(minutes=61)
        cc_event.append("bank-change", {"first": "Jane"})
        assert len(push.look(later)) == 1 and len(fake.calls) == 21
    finally:
        push.WEBPUSH = saved


def test_a_line_longer_than_the_read_size_is_skipped_not_stuck():
    fixtures()
    push.add_subscription(push.validate_subscription(sub_input()), LOGIN, "abc")
    fake = FakeWebPush()
    saved = with_fake(fake)
    try:
        now = datetime.datetime(2026, 9, 28, 23, 0, tzinfo=LONDON)
        push.look(now)
        with open(push.events_path(), "ab") as f:
            f.write(b"x" * (push.READ_MAX * 2 + 17) + b"\n")
        cc_event.append("bank-change", {"first": "Jane"})
        got = []
        for _ in range(5):
            got += push.look(now)
        assert [p["body"] for p in got] == ["Jane: ring them before paying"], got
        # a long line still being written (no newline yet) is skipped too, and the next event gets through
        with open(push.events_path(), "ab") as f:
            f.write(b"y" * (push.READ_MAX + 5))
        assert push.look(now) == []
        with open(push.events_path(), "ab") as f:
            f.write(b"yyy\n")
        cc_event.append("run-failed")
        got = []
        for _ in range(3):
            got += push.look(now)
        assert [p["title"] for p in got] == ["A scheduled run failed"], got
    finally:
        push.WEBPUSH = saved


def test_the_vapid_file_store_is_refused_in_the_live_service():
    from command_centre.app import LOOPBACK
    assert os.environ["CC_VAPID_STORE"] == "file"
    for kw in ({"watch": True}, {"bind_host": LOOPBACK, "port": auth.SERVICE_PORT},
               {"bind_host": LOOPBACK, "uds": "/tmp/x.sock"}):
        try:
            create_app(client_factory=lambda: None, checkout=lambda: "main", **kw)
        except SystemExit as e:
            assert "CC_VAPID_STORE" in str(e)
        else:
            raise AssertionError(kw)
    create_app(client_factory=lambda: None, checkout=lambda: "main", bind_host=LOOPBACK, port=8766)  # a local check


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"PASS {name}")
        except Exception as ex:
            failures += 1
            import traceback
            traceback.print_exc()
            print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
