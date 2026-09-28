#!/usr/bin/env python3
"""Security regression tests for the Command Centre, from the phase-1 review (PR #156) and its probe.

Covers: the Host check (DNS rebinding), loopback-only peers and the Unix socket, the bootstrap code that
guards the first passkey, the dev login's limits, pinned dependencies, the challenge-store cap, log rotation,
server-built action summaries and the main-checkout warning. Stdlib runner, fake data in a temp
LCS_PRIVATE_DIR (set by test_cc_auth on import), never the real private files.
"""
import datetime, hashlib, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_cc_auth as T  # noqa: E402  sets LCS_PRIVATE_DIR to a temp dir before the app is imported
from cryptography.hazmat.primitives import hashes  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from command_centre import __main__ as cc_main  # noqa: E402
from command_centre import app as cc_app  # noqa: E402
from command_centre import auth  # noqa: E402
from command_centre.app import create_app  # noqa: E402

ROOT = T.ROOT
H = T.HEADERS
PY = sys.executable


def refused(fn, reason=None):
    try:
        fn()
    except auth.PasskeyError as e:
        assert reason is None or e.reason == reason, e.reason
        return
    raise AssertionError("accepted")


def app_client(client=T.LOCAL, base_url=T.ORIGIN, **kw):
    kw.setdefault("client_factory", lambda: None)
    kw.setdefault("checkout", lambda: "main")
    return TestClient(create_app(**kw), base_url=base_url, client=client)


def _asgi_status(app, scope):
    import anyio
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    anyio.run(app, scope, receive, send)
    return next(m["status"] for m in sent if m["type"] == "http.response.start")


def _scope(headers, client=("127.0.0.1", 5)):
    return {"type": "http", "method": "GET", "path": "/", "raw_path": b"/", "query_string": b"", "client": client,
            "server": ("127.0.0.1", 8765), "scheme": "http", "http_version": "1.1", "root_path": "",
            "headers": headers}


OWNER = [(b"tailscale-user-login", T.LOGIN.encode()), (b"tailscale-user-name", b"Owner")]


# ---------------------------------------------------------------- 1. Host check (DNS rebinding)


def test_wrong_host_is_403():
    T.write_config()
    c = app_client()
    for host in ["evil.example:8765", "evil.example", "127.0.0.1:8765", "localhost:8765", "127.0.0.1",
                 T.RP_ID + ":8443", T.RP_ID + ".evil.example", "x." + T.RP_ID, ""]:
        for path in ["/", "/money", "/passkeys", "/healthz", "/static/app.css"]:
            r = c.get(path, headers={**H, "Host": host})
            assert r.status_code == 403, (host, path, r.status_code)
            assert "no-store" in r.headers["cache-control"]
    r = c.post("/auth/passkey/assert/options", json={"action": "check"},
               headers={**H, "Host": "evil.example", "Origin": T.ORIGIN})
    assert r.status_code == 403


def test_right_host_bare_or_443():
    T.write_config()
    c = app_client()
    for host in [T.RP_ID, T.RP_ID + ":443", T.RP_ID.upper()]:
        assert c.get("/", headers={**H, "Host": host}).status_code == 200, host
        assert c.get("/healthz", headers={"Host": host}).status_code == 200, host


def test_no_config_refuses_even_healthz():
    os.remove(auth.config_path())
    assert app_client().get("/healthz").status_code == 403


def test_dev_login_adds_only_its_own_loopback_host():
    T.write_config()
    os.environ["CC_DEV_LOGIN"] = T.LOGIN
    try:
        c = app_client(base_url="http://127.0.0.1:8799", bind_host="127.0.0.1", port=8799)
        assert c.get("/").status_code == 200
        for host in ["127.0.0.1:8765", "localhost:8799", "127.0.0.1", "evil.example:8799"]:
            assert c.get("/", headers={"Host": host}).status_code == 403, host
        assert c.get("/", headers={"Host": T.RP_ID}).status_code == 200
    finally:
        os.environ.pop("CC_DEV_LOGIN", None)
    c = app_client(base_url="http://127.0.0.1:8799", bind_host="127.0.0.1", port=8799)
    assert c.get("/", headers=H).status_code == 403  # without the dev login, the loopback Host is refused


def test_duplicate_host_or_identity_headers_are_refused():
    T.write_config()
    c = app_client()
    for headers in [
        [("Tailscale-User-Login", T.LOGIN), ("Tailscale-User-Login", "x@example.org"), ("Tailscale-User-Name", "n")],
        [("Tailscale-User-Login", "x@example.org"), ("Tailscale-User-Login", T.LOGIN), ("Tailscale-User-Name", "n")],
        [("Tailscale-User-Login", T.LOGIN), ("Tailscale-User-Name", "n"), ("Tailscale-User-Name", "m")],
    ]:
        assert c.get("/", headers=headers).status_code == 403, headers
    # two Host headers, as a raw ASGI scope (httpx won't send two)
    app = create_app(client_factory=lambda: None, checkout=lambda: "main")
    assert _asgi_status(app, _scope([(b"host", T.RP_ID.encode()), (b"host", b"evil.example")] + OWNER)) == 403
    assert _asgi_status(app, _scope([(b"host", T.RP_ID.encode())] + OWNER)) == 200
    assert _asgi_status(app, _scope(OWNER)) == 403  # no Host at all


# ---------------------------------------------------------------- 3. loopback peers and the Unix socket


def test_non_loopback_peer_is_refused():
    T.write_config()
    for peer in [("testclient", 50000), ("192.168.1.5", 4000), ("100.64.0.7", 4000), ("0.0.0.0", 1),
                 ("127.0.0.2", 1), ("::ffff:127.0.0.1", 1)]:
        assert app_client(client=peer).get("/", headers=H).status_code == 403, peer
        assert app_client(client=peer).get("/healthz").status_code == 403, peer
    for peer in [("127.0.0.1", 1), ("::1", 1)]:
        assert app_client(client=peer).get("/", headers=H).status_code == 200, peer


def test_no_peer_address_is_local_only_on_the_unix_socket():
    T.write_config()
    headers = [(b"host", T.RP_ID.encode())] + OWNER
    tcp = create_app(client_factory=lambda: None, checkout=lambda: "main", bind_host="127.0.0.1", port=8765)
    assert _asgi_status(tcp, _scope(headers, client=None)) == 403
    sock = create_app(client_factory=lambda: None, checkout=lambda: "main", bind_host="127.0.0.1",
                      uds="/tmp/x/cc.sock")
    assert _asgi_status(sock, _scope(headers, client=None)) == 200
    assert _asgi_status(sock, _scope(headers, client=("192.168.1.5", 1))) == 403


def test_uds_dir_is_private_and_serve_options():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "run", "cc.sock")
    assert cc_main.prepare_uds(path) == path
    assert oct(os.stat(os.path.dirname(path)).st_mode & 0o777) == "0o700"
    os.chmod(os.path.dirname(path), 0o755)
    cc_main.prepare_uds(path)  # tightened again
    assert oct(os.stat(os.path.dirname(path)).st_mode & 0o777) == "0o700"
    assert cc_main.parse_args(["--uds", path]).uds == path
    assert cc_main.parse_args([]).uds is None
    assert cc_main.parse_args(["--uds"]).uds == str(auth.config_dir() / "run" / "cc.sock")
    link = os.path.join(d, "link")
    os.symlink(os.path.join(d, "run"), link)
    try:
        cc_main.prepare_uds(os.path.join(link, "cc.sock"))
        raise AssertionError("a symlinked socket directory was accepted")
    except SystemExit:
        pass


# ---------------------------------------------------------------- 2. the bootstrap code for the first passkey


def _first_registration(code, clock=None, now=None):
    pk = auth.Passkeys(auth.ChallengeStore(clock=clock or T.Clock()), wallclock=now)
    c = app_client(passkeys=pk)
    a = T.Authenticator()
    body = {} if code is None else {"bootstrap": code}
    return c, a, pk, T.post(c, "/auth/passkey/register/options", body)


def test_bootstrap_stores_only_a_hash_and_expires_in_30_minutes():
    T.write_config()
    now = datetime.datetime(2026, 9, 28, 12, 0, tzinfo=datetime.timezone.utc)
    code = auth.new_bootstrap(now=now)
    assert code not in open(auth.config_path()).read()
    b = auth.load_config()["bootstrap"]
    assert b["sha256"] == hashlib.sha256(code.encode()).hexdigest()
    assert datetime.datetime.fromisoformat(b["expires"]) == now + datetime.timedelta(minutes=30)
    assert len(code) >= 16


def test_first_registration_needs_the_bootstrap_code():
    T.write_config()
    code = auth.new_bootstrap()
    for bad in [None, "", "wrong-code", code + "x", 5]:
        c, a, pk, r = _first_registration(bad)
        assert r.status_code == 403, (bad, r.text)
    # the probe's forger: no code, straight to register
    c, a, pk, r = _first_registration(None)
    assert r.status_code == 403 and r.json()["error"] == "bootstrap code required", r.text
    assert auth.load_config()["passkeys"] == []
    c, a, pk, r = _first_registration(code)
    assert r.status_code == 200, r.text
    # the finish step needs the same code again
    reg = T.post(c, "/auth/passkey/register", {"credential": a.register(r.json())})
    assert reg.status_code == 403, reg.text
    opts = T.post(c, "/auth/passkey/register/options", {"bootstrap": code}).json()
    reg = T.post(c, "/auth/passkey/register", {"credential": a.register(opts), "bootstrap": code})
    assert reg.status_code == 200, reg.text
    cfg = auth.load_config()
    assert len(cfg["passkeys"]) == 1 and "bootstrap" not in cfg  # used once, then deleted
    # the code is spent: a second device needs an assertion, and the code alone is refused
    r = T.post(c, "/auth/passkey/register/options", {"bootstrap": code})
    assert r.status_code == 403 and r.json()["error"] == "assertion required"


def test_expired_bootstrap_code_is_refused():
    T.write_config()
    issued = datetime.datetime(2026, 9, 28, 12, 0, tzinfo=datetime.timezone.utc)
    code = auth.new_bootstrap(now=issued)
    c, a, pk, r = _first_registration(code, now=lambda: issued + datetime.timedelta(minutes=30, seconds=1))
    assert r.status_code == 403 and r.json()["error"] == "bootstrap code expired", r.text
    # expiry is checked again at the finish step
    clock_now = [issued + datetime.timedelta(minutes=29)]
    c, a, pk, r = _first_registration(code, now=lambda: clock_now[0])
    assert r.status_code == 200
    clock_now[0] = issued + datetime.timedelta(minutes=31)
    reg = T.post(c, "/auth/passkey/register", {"credential": a.register(r.json()), "bootstrap": code})
    assert reg.status_code == 403 and reg.json()["error"] == "bootstrap code expired", reg.text
    assert auth.load_config()["passkeys"] == []


def test_no_bootstrap_code_issued_refuses_the_first_passkey():
    T.write_config()
    c, a, pk, r = _first_registration("anything")
    assert r.status_code == 403 and r.json()["error"] == "no bootstrap code issued", r.text


def test_bootstrap_cli_issues_a_new_code():
    T.write_config()
    env = dict(os.environ)
    run = lambda *args: subprocess.run([PY, "-m", "command_centre.bootstrap", *args], cwd=ROOT, env=env,  # noqa: E731
                                       capture_output=True, text=True, timeout=60)
    r = run("--new-bootstrap")
    assert r.returncode == 0, r.stderr
    code = re.search(r"Bootstrap code: (\S+)", r.stdout).group(1)
    assert auth.load_config()["bootstrap"]["sha256"] == hashlib.sha256(code.encode()).hexdigest()
    assert code not in open(auth.config_path()).read()
    assert run().returncode != 0  # without the option it does nothing
    T.write_config(passkeys=[{"id": "abc", "public_key": "def", "sign_count": 0,
                              "created": "2026-09-28T09:00:00+00:00"}])
    r = run("--new-bootstrap")  # refused once a passkey exists
    assert r.returncode != 0 and "bootstrap" not in auth.load_config()
    os.remove(auth.config_path())
    assert run("--new-bootstrap").returncode != 0  # no config: install.sh first


def test_install_generates_a_bootstrap_code():
    src = open(os.path.join(ROOT, "command_centre", "install.sh")).read()
    assert "command_centre.bootstrap --new-bootstrap" in src


def test_passkey_count_and_last_added_on_today_and_passkeys():
    T.write_config()
    c = app_client()
    assert "No passkeys yet" in c.get("/", headers=H).text
    T.write_config(passkeys=[
        {"id": "a", "public_key": "p", "sign_count": 0, "created": "2026-09-01T09:00:00+00:00"},
        {"id": "b", "public_key": "q", "sign_count": 0, "created": "2026-09-27T21:00:00+00:00"}])
    for path in ["/", "/passkeys"]:
        text = re.sub(r"\s+", " ", c.get(path, headers=H).text)
        assert "2 passkeys, last added Sun 27 Sep 2026" in text, path


# ---------------------------------------------------------------- 4. the dev login


def test_dev_login_refused_on_the_service_port_and_the_socket():
    T.write_config()
    os.environ["CC_DEV_LOGIN"] = T.LOGIN
    mk = lambda **kw: create_app(client_factory=lambda: None, bind_host="127.0.0.1", **kw)  # noqa: E731
    try:
        assert mk(port=8765).state.dev_login is None
        assert mk(port=None).state.dev_login is None
        assert mk(uds="/tmp/cc.sock").state.dev_login is None
        assert mk(port=8799, uds="/tmp/cc.sock").state.dev_login is None
        assert mk(port=8799).state.dev_login == T.LOGIN
    finally:
        os.environ.pop("CC_DEV_LOGIN", None)


def test_launch_agent_blanks_the_dev_login():
    src = open(os.path.join(ROOT, "command_centre", "install.sh")).read()
    env = re.search(r'"EnvironmentVariables": \{([^}]*)\}', src).group(1)
    assert '"CC_DEV_LOGIN": ""' in env


# ---------------------------------------------------------------- 5. dependencies


def test_command_centre_dependencies_are_pinned():
    req = open(os.path.join(ROOT, "scripts", "requirements.txt")).read()
    lines = {re.split(r"[=<>~!\[]", ln)[0].strip().lower(): ln.strip() for ln in req.splitlines()
             if ln.strip() and not ln.startswith("#")}
    for pkg in ["starlette", "uvicorn", "jinja2", "webauthn", "claude-agent-sdk", "mcp"]:
        assert re.fullmatch(rf"{pkg}==\d+(\.\d+)+", lines.get(pkg, ""), re.I), (pkg, lines.get(pkg))
    assert "httpx" not in lines
    dev = open(os.path.join(ROOT, "scripts", "requirements-dev.txt")).read()
    dev_pin = re.search(r"^httpx2==(\S+)", dev, re.M)
    assert dev_pin
    # phase 4: mcp (the Agent SDK's dependency) needs httpx2 at run time, so it is pinned in both, at one version
    assert lines.get("httpx2") == f"httpx2=={dev_pin.group(1)}", lines.get("httpx2")
    install = open(os.path.join(ROOT, "command_centre", "install.sh")).read()
    assert not re.search(r"-r\s+\S*requirements-dev", install)  # test-only packages never reach the service
    assert re.findall(r"-m pip install[^\n]*", install) == ['-m pip install --quiet -r "$REPO/scripts/requirements.txt"']


# ---------------------------------------------------------------- 6. lows


def test_challenge_store_keeps_at_most_100():
    store = auth.ChallengeStore(clock=T.Clock())
    issued = [store.issue("assert", f"s{i}") for i in range(150)]
    assert len(store._issued) == 100
    refused(lambda: store.consume(issued[0], "assert", "s0"), "unknown or used challenge")
    refused(lambda: store.consume(issued[49], "assert", "s49"), "unknown or used challenge")
    store.consume(issued[50], "assert", "s50")
    store.consume(issued[149], "assert", "s149")


def test_logs_over_5_mb_rotate_on_start_keeping_3():
    d = tempfile.mkdtemp()
    big = os.path.join(d, "command-centre.err.log")
    small = os.path.join(d, "command-centre.out.log")
    for i in (1, 2, 3):
        with open(f"{big}.{i}", "w") as f:
            f.write(f"old{i}")
    with open(big, "wb") as f:
        f.write(b"x" * (5 * 1024 * 1024 + 1))
    with open(small, "w") as f:
        f.write("small")
    fd = os.open(big, os.O_WRONLY | os.O_APPEND)  # stands in for launchd's stderr
    try:
        cc_main.rotate_logs(d, fds=(fd,))
        os.write(fd, b"after")
    finally:
        os.close(fd)
    assert os.path.getsize(big + ".1") == 5 * 1024 * 1024 + 1
    assert open(big + ".2").read() == "old1" and open(big + ".3").read() == "old2"
    assert not os.path.exists(big + ".4")
    assert open(big).read() == "after"  # the open descriptor now writes to a fresh file
    assert oct(os.stat(big).st_mode & 0o777) == "0o600"
    assert open(small).read() == "small" and not os.path.exists(small + ".1")
    cc_main.rotate_logs(os.path.join(d, "missing"))  # no logs directory: nothing to do


def test_install_retries_launchctl_bootstrap_once():
    src = open(os.path.join(ROOT, "command_centre", "install.sh")).read()
    assert len(re.findall(r'launchctl bootstrap "\$DOMAIN" "\$PLIST"', src)) == 2
    r = subprocess.run(["bash", "-n", os.path.join(ROOT, "command_centre", "install.sh")], capture_output=True)
    assert r.returncode == 0, r.stderr


def test_assertions_bind_a_server_built_action():
    c, a, pk = T.registered()
    # a plain string (say, from a request) is not an action
    opts = pk.assertion_options(auth.CHECK)
    refused(lambda: pk.require_fresh_assertion(a.assert_(opts), "check passkey"), "server-built action required")
    refused(lambda: pk.assertion_options("check passkey"), "server-built action required")
    # the routes take an action's name and look the summary up; a client-written summary is refused
    for name in ["check passkey", "resolve hand check 0310: paid", "", None, 5, "x" * 501]:
        r = T.post(c, "/auth/passkey/assert/options", {"action": name})
        assert r.status_code == 400 and r.json()["error"] == "unknown action", (name, r.text)
    opts = T.post(c, "/auth/passkey/assert/options", {"action": "check"}).json()
    assert auth.unb64url(opts["challenge"])[16:] == auth.action_hash("assert", auth.CHECK.summary, "check")
    r = T.post(c, "/auth/passkey/assert", {"action": "check", "credential": a.assert_(opts)})
    assert r.status_code == 200, r.text
    try:  # an Action can't be altered once built
        auth.CHECK.summary = "something else"
        raise AssertionError("action changed")
    except (AttributeError, TypeError):
        pass


def test_probe_uv_rp_origin_replay_and_counter():
    c, a, pk = T.registered()

    class NoUV(T.Authenticator):
        def assert_(self, options, origin=T.ORIGIN, rp_id=T.RP_ID):
            self.count += 1
            cdj = self.client_data("webauthn.get", T.unb64(options["challenge"]), origin)
            ad = hashlib.sha256(rp_id.encode()).digest() + bytes([0x01]) + self.count.to_bytes(4, "big")
            sig = self.key.sign(ad + hashlib.sha256(cdj).digest(), ec.ECDSA(hashes.SHA256()))
            return {"id": T.b64(self.cred_id), "rawId": T.b64(self.cred_id), "type": "public-key",
                    "response": {"clientDataJSON": T.b64(cdj), "authenticatorData": T.b64(ad),
                                 "signature": T.b64(sig)}}

    nu = NoUV(a.cred_id)
    nu.key = a.key

    def check(cred_fn):
        o = T.post(c, "/auth/passkey/assert/options", {"action": "check"}).json()
        return T.post(c, "/auth/passkey/assert", {"action": "check", "credential": cred_fn(o)})

    assert check(nu.assert_).status_code == 403
    assert check(lambda o: a.assert_(o, rp_id="evil.ts.net")).status_code == 403
    assert check(lambda o: a.assert_(o, origin="https://evil.ts.net")).status_code == 403
    o = T.post(c, "/auth/passkey/assert/options", {"action": "check"}).json()
    good = a.assert_(o)
    assert T.post(c, "/auth/passkey/assert", {"action": "check", "credential": good}).status_code == 200
    assert T.post(c, "/auth/passkey/assert", {"action": "check", "credential": good}).status_code == 403
    a.count = 0
    assert check(a.assert_).status_code == 403  # the sign counter went backwards


def test_checkout_branch_is_read_from_git():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, ".git"))
    head = os.path.join(d, ".git", "HEAD")
    for content, want in [("ref: refs/heads/main\n", "main"), ("ref: refs/heads/claude/feature\n", "claude/feature"),
                          ("0123456789abcdef0123456789abcdef01234567\n", None)]:
        with open(head, "w") as f:
            f.write(content)
        assert cc_app.checkout_branch(d) == want, content
    wt = tempfile.mkdtemp()
    gitdir = os.path.join(d, "wt-gitdir")
    os.makedirs(gitdir)
    with open(os.path.join(gitdir, "HEAD"), "w") as f:
        f.write("ref: refs/heads/other\n")
    with open(os.path.join(wt, ".git"), "w") as f:
        f.write(f"gitdir: {gitdir}\n")
    assert cc_app.checkout_branch(wt) == "other"
    assert cc_app.checkout_branch(os.path.join(d, "nope")) is None
    assert cc_app.checkout_warning("main") is None
    assert "not on main" in cc_app.checkout_warning("other")
    assert "not on main" in cc_app.checkout_warning(None)


def test_today_health_line_warns_when_not_on_main():
    T.write_config()
    text = app_client(checkout=lambda: "claude/feature").get("/", headers=H).text
    assert "not on main" in text and "claude/feature" in text
    text = app_client(checkout=lambda: "main").get("/", headers=H).text
    assert "not on main" not in text


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
            except Exception as e:
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
