#!/usr/bin/env python3
"""Tests for the Command Centre's phase-3 actions (command_centre/actions.py and the /actions and /activity routes).

Stdlib runner, Starlette's TestClient, a software passkey (an ES256 key made here, so py_webauthn checks real
signatures), fake fixtures in a temp LCS_PRIVATE_DIR (fake names, example.org emails) and a recording stand-in
for subprocess.run. One test runs the real check_payments.py --note … --owner against a temp ledger through the
whole route. The Ads tests use a temp git repo for scripts/ads/. Never touches the real private files, the bank,
Google Ads or ~/.claude.
"""
import ast, base64, csv, datetime, hashlib, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

TMP = tempfile.mkdtemp()
HOME = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
os.environ["CC_SCHEDULED_TASKS_DIR"] = os.path.join(HOME, ".claude", "scheduled-tasks")
os.environ.pop("CC_DEV_LOGIN", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import cbor2  # noqa: E402
from cryptography.hazmat.primitives import hashes  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from command_centre import actions, auth, data, models, sources  # noqa: E402
from command_centre.app import create_app  # noqa: E402
import test_prompt_allowlist as allowlist  # noqa: E402

lm, cp, si = data.lm, data.cp, data.si
LOGIN = "owner@example.org"
RP_ID = "mac.example-tailnet.ts.net"
ORIGIN = f"https://{RP_ID}"
HEADERS = {"Tailscale-User-Login": LOGIN, "Tailscale-User-Name": "Owner"}
LOCAL = ("127.0.0.1", 50000)
TODAY = lm.today()
D = TODAY.isoformat()
MSG = "1789828736363141700"
MSG_PAID = "1789828736363141701"
MSG_NOBANK = "1789828736363141702"
MSG_CONFIRMED = "1789828736363141703"
LEDGER_COLS = ["booking_ref", "invoice_date", "event_date", "client_name", "client_email", "occasion", "ensemble",
               "value_gbp", "enquiry_date", "source", "gclid", "consent", "uploaded_at", "notes"]
sources.HOME = Path(HOME)


# ---------------------------------------------------------------- helpers


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
        challenge = unb64(options["challenge"])
        cdj = json.dumps({"type": "webauthn.create", "challenge": b64(challenge), "origin": ORIGIN}).encode()
        auth_data = (hashlib.sha256(options["rp"]["id"].encode()).digest() + bytes([0x45]) + (0).to_bytes(4, "big")
                     + bytes(16) + len(self.cred_id).to_bytes(2, "big") + self.cred_id + self.cose())
        att = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
        return {"id": b64(self.cred_id), "rawId": b64(self.cred_id), "type": "public-key",
                "response": {"clientDataJSON": b64(cdj), "attestationObject": b64(att)}}

    def assert_(self, options):
        self.count += 1
        challenge = unb64(options["challenge"])
        cdj = json.dumps({"type": "webauthn.get", "challenge": b64(challenge), "origin": ORIGIN}).encode()
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
    os.chmod(path, 0o600)


def fixtures():
    write_csv(os.path.join(TMP, "bookings.csv"), LEDGER_COLS, [
        {"booking_ref": "2111", "invoice_date": "2026-08-22", "event_date": "2026-11-21", "client_name": "Ann Smithfield",
         "client_email": "ann@example.org", "occasion": "Wedding", "ensemble": "Quartet", "value_gbp": "650",
         "notes": "PENDING: invoiced"},
        {"booking_ref": "0310", "invoice_date": "2026-09-01", "event_date": "2026-10-03", "client_name": "Tom Pastmore",
         "client_email": "tom@example.org", "occasion": "Funeral", "ensemble": "Quartet", "value_gbp": "575",
         "notes": "cancelled 2026-09-10"}])
    base = {"singer_email": "jane@example.org", "invoice_ref": "INV-7", "amount_gbp": "120.00", "payee": "",
            "bank_changed": "", "paid_verified": "", "notes": "", "withdrawn": ""}
    write_csv(str(si.STORE), si.COLUMNS, [
        dict(base, message_id=MSG, received="2026-09-20", singer_name="Jane Fenwickson", bank_fp="fp-a", bank_last4="4321",
             bank_confirmed=""),
        dict(base, message_id=MSG_PAID, received="2026-09-01", singer_name="Jane Fenwickson", bank_fp="fp-a",
             bank_last4="4321", paid_on="2026-09-05", paid_amount="120.00"),
        dict(base, message_id=MSG_NOBANK, received="2026-09-21", singer_name="Bob Quillfeather", bank_fp="",
             bank_last4=""),
        dict(base, message_id=MSG_CONFIRMED, received="2026-09-22", singer_name="Cat Mistakeham", bank_fp="fp-c",
             bank_last4="9876", bank_confirmed="yes")])


def write_config(**over):
    cfg = {"allowed_logins": [LOGIN], "origin": ORIGIN, "rp_id": RP_ID, "passkeys": []}
    cfg.update(over)
    auth.save_config(cfg)


class Recorder:
    """Stands in for subprocess.run: records every call; answers with (code, stdout)."""

    def __init__(self, code=0, out=b"done\n", err=b"", raise_=None, check=None):
        self.calls, self.code, self.out, self.err, self.raise_, self.check = [], code, out, err, raise_, check

    def __call__(self, argv, **kw):
        self.calls.append((argv, kw))
        if self.check:
            self.check(argv, kw)
        if self.raise_:
            raise self.raise_
        return subprocess.CompletedProcess(argv, self.code, self.out, self.err)


class Runner:
    """actions.RUNNER swapped for the duration of a with-block."""

    def __init__(self, fake):
        self.fake = fake

    def __enter__(self):
        self.saved = actions.RUNNER
        actions.RUNNER = self.fake
        return self.fake

    def __exit__(self, *exc):
        actions.RUNNER = self.saved


def setup(clock=None):
    """A registered passkey, the fixtures, a fresh audit log; returns (client, authenticator, clock)."""
    for p in ("audit.jsonl",):
        (Path(TMP) / "command-centre" / p).unlink(missing_ok=True)
    write_config()
    fixtures()
    actions.reset_validations()
    clock = clock or Clock()
    pk = auth.Passkeys(auth.ChallengeStore(clock=clock))
    app = create_app(client_factory=lambda: None, passkeys=pk, checkout=lambda: "main")
    c = TestClient(app, base_url=ORIGIN, client=LOCAL, follow_redirects=False)
    a = Authenticator()
    code = auth.new_bootstrap()
    opts = post(c, "/auth/passkey/register/options", {"bootstrap": code}).json()
    r = post(c, "/auth/passkey/register", {"credential": a.register(opts), "bootstrap": code})
    assert r.status_code == 200, r.text
    return c, a, clock


def post(c, path, body, origin=ORIGIN):
    h = dict(HEADERS)
    if origin:
        h["Origin"] = origin
    return c.post(path, json=body, headers=h)


def preview(c, name, inp):
    return post(c, f"/actions/{name}/preview", {"input": inp})


def run(c, a, name, inp, opts_input=None, opts_name=None):
    """Preview (for opts_name/opts_input, default the same), sign its challenge, then run name/inp."""
    p = preview(c, opts_name or name, inp if opts_input is None else opts_input)
    assert p.status_code == 200, p.text
    return post(c, f"/actions/{name}/run", {"input": inp, "credential": a.assert_(p.json()["options"])})


def audit_lines():
    path = Path(TMP) / "command-centre" / "audit.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def refused(fn, *args):
    try:
        fn(*args)
    except actions.ActionError as e:
        return e.reason
    raise AssertionError(f"not refused: {args}")


def ledger_notes(ref):
    return next(r for r in lm.read_csv(cp.LEDGER) if r["booking_ref"] == ref)["notes"]


PYX = sys.executable
CHECK = str(Path(ROOT) / "scripts" / "bookings" / "check_payments.py")
SINGER = str(Path(ROOT) / "scripts" / "bookings" / "singer_invoices.py")
DASH = str(Path(ROOT) / "scripts" / "reports" / "dashboard.py")


# ---------------------------------------------------------------- the registry


def test_registry_and_passkey_flags():
    assert set(actions.REGISTRY) == {"todo-tick", "resolve-hand-check", "singer-confirm", "singer-settled",
                                     "singer-withdrawn", "refresh-data", "ads-validate", "ads-apply",
                                     "approve-books-import"}
    no_passkey = {n for n, a in actions.REGISTRY.items() if not a.passkey}
    assert no_passkey == {"todo-tick", "refresh-data"}, no_passkey
    assert "todo-tick" not in actions.ROUTED


def test_hand_check_argv_and_summary():
    fixtures()
    a = actions.RESOLVE_HAND_CHECK
    c = a.validate({"ref": "2111", "choice": "paid-in-full", "date": D})
    assert a.argv(c) == [PYX, CHECK, "--note", "2111", f"paid in full {D}", "--owner"]
    s = a.preview(c)
    assert s.endswith(f"Runs: .venv/bin/python scripts/bookings/check_payments.py --note 2111 'paid in full {D}' --owner")
    assert "Ann" in s and "Smithfield" not in s and f"\"paid in full {D} (owner)\"" in s
    assert a.owner_nonce and a.passkey
    for choice, phrase in [("deposit-kept", f"deposit kept {D}"), ("refunded", f"refunded {D}"),
                           ("reinstated", f"reinstated {D}"), ("cancelled", f"cancelled {D}"),
                           ("payment-checked", f"payment checked {D}"),
                           ("arranged-cash", f"balance payable in cash on the day (arranged {D})"),
                           ("arranged-cheque", f"balance payable by cheque on the day (arranged {D})")]:
        assert a.argv(a.validate({"ref": "0310", "choice": choice, "date": D}))[4] == phrase


def test_hand_check_refuses_bad_input():
    fixtures()
    v = actions.RESOLVE_HAND_CHECK.validate
    ok = {"ref": "2111", "choice": "refunded", "date": D}
    future = (TODAY + datetime.timedelta(days=1)).isoformat()
    old = (TODAY - datetime.timedelta(days=800)).isoformat()
    for bad in [None, [], "x", {}, dict(ok, ref="9999"), dict(ok, ref="--apply"), dict(ok, ref="-2111"),
                dict(ok, ref="2111 --apply"), dict(ok, ref="21;11"), dict(ok, choice="paid"), dict(ok, choice=""),
                dict(ok, date=future), dict(ok, date=old), dict(ok, date="2026-02-30"), dict(ok, date="28/09/2026"),
                dict(ok, extra="x"), dict(ok, ref=2111), {"ref": "2111", "choice": "refunded"}]:
        refused(v, bad)
    assert v(ok)["phrase"] == f"refunded {D}"


def test_each_hand_phrase_means_what_it_says_to_check_payments():
    row = {"booking_ref": "X", "value_gbp": "650", "invoice_date": "2026-08-22", "event_date": "2026-11-21",
           "client_name": "Ann Smithfield"}
    day = datetime.date.fromisoformat(D)

    def notes(choice, before="PENDING: invoiced"):
        phrase = actions.HAND_CHOICES[choice][1].format(d=D)
        return f"{before}; {phrase} (owner)"
    assert cp.closed_on({"notes": notes("paid-in-full")}) == day
    for choice in ("deposit-kept", "refunded", "payment-checked"):
        assert cp.cancel_settled_on({"notes": "cancelled 2026-09-01; " + notes(choice, "x")}, day) == day, choice
    assert cp.is_cancelled({"notes": notes("cancelled")})
    assert not cp.is_cancelled({"notes": notes("reinstated", "cancelled 2026-09-01")})
    for choice in ("arranged-cash", "arranged-cheque"):
        state = cp.assess(dict(row, notes=notes(choice)), [], day)["state"]
        assert state == "ARRANGED", (choice, state)


def test_singer_actions_argv_and_refusals():
    fixtures()
    key, paid, nobank, confirmed = (models.invoice_key(m) for m in (MSG, MSG_PAID, MSG_NOBANK, MSG_CONFIRMED))
    assert re.fullmatch(r"[a-z]{12}", key)
    c = actions.SINGER_CONFIRM.validate({"invoice": key})
    assert actions.SINGER_CONFIRM.argv(c) == [PYX, SINGER, "confirm", MSG]
    s = actions.SINGER_CONFIRM.preview(c)
    assert "Jane" in s and "Fenwickson" not in s and "••••4321" in s and "£120.00" in s
    assert s.endswith(f"Runs: .venv/bin/python scripts/bookings/singer_invoices.py confirm {MSG}")
    c = actions.SINGER_SETTLED.validate({"invoice": key, "date": D})
    assert actions.SINGER_SETTLED.argv(c) == [PYX, SINGER, "settled", MSG, D]
    c = actions.SINGER_WITHDRAWN.validate({"invoice": key, "reason": "not-ours"})
    assert actions.SINGER_WITHDRAWN.argv(c) == [PYX, SINGER, "withdrawn", MSG, "not-ours"]
    future = (TODAY + datetime.timedelta(days=1)).isoformat()
    for defn, bad, why in [
            (actions.SINGER_CONFIRM, {"invoice": "abc"}, "unknown invoice"),
            (actions.SINGER_CONFIRM, {"invoice": MSG}, "unknown invoice"),  # the raw id is never accepted
            (actions.SINGER_CONFIRM, {"invoice": "a" * 12}, "unknown invoice"),
            (actions.SINGER_CONFIRM, {"invoice": nobank}, "no bank details recorded on that invoice"),
            (actions.SINGER_CONFIRM, {"invoice": confirmed}, "already confirmed"),
            (actions.SINGER_CONFIRM, {"invoice": key, "x": "y"}, "unexpected field"),
            (actions.SINGER_SETTLED, {"invoice": paid, "date": D}, "already paid"),
            (actions.SINGER_SETTLED, {"invoice": key, "date": future}, "the date is after today"),
            (actions.SINGER_SETTLED, {"invoice": key}, "date is required"),
            (actions.SINGER_WITHDRAWN, {"invoice": key, "reason": "Not Ours"}, None),
            (actions.SINGER_WITHDRAWN, {"invoice": key, "reason": "--apply"}, None),
            (actions.SINGER_WITHDRAWN, {"invoice": paid, "reason": "not-ours"}, "already paid")]:
        reason = refused(defn.validate, bad)
        assert why is None or reason == why, (defn.name, bad, reason)


def test_refresh_and_books_argv():
    c = actions.REFRESH.validate({})
    assert actions.REFRESH.argv(c) == [PYX, DASH] and not actions.REFRESH.passkey
    refused(actions.REFRESH.validate, {"x": "y"})
    assert actions.BOOKS_IMPORT.command({}) is None


def test_no_shell_anywhere_in_the_app():
    for path in Path(ROOT, "command_centre").glob("*.py"):
        tree = ast.parse(path.read_text(), str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "shell":
                assert isinstance(node.value, ast.Constant) and node.value.value is False, path
            if isinstance(node, ast.Attribute) and node.attr in ("system", "popen", "spawnl", "spawnv", "execv",
                                                                 "execl", "getoutput", "getstatusoutput"):
                raise AssertionError(f"{path}: {node.attr}")
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "Popen":
                raise AssertionError(f"{path}: Popen")


# ---------------------------------------------------------------- routes: passkey, binding, audit


def test_run_needs_a_passkey_and_nothing_runs_without_one():
    c, a, _ = setup()
    inp = {"ref": "2111", "choice": "paid-in-full", "date": D}
    with Runner(Recorder()) as rec:
        r = post(c, "/actions/resolve-hand-check/run", {"input": inp})
        assert r.status_code == 403 and r.json()["error"] == "this action needs a passkey", r.text
        r = post(c, "/actions/resolve-hand-check/run", {"input": inp, "credential": {"id": "x"}})
        assert r.status_code == 403
        assert rec.calls == []
    assert ledger_notes("2111") == "PENDING: invoiced"
    assert [e["result"] for e in audit_lines()] == ["refused: no passkey", "refused: malformed credential"]


def test_preview_shows_summary_and_command_and_binds_the_challenge():
    c, a, _ = setup()
    r = preview(c, "resolve-hand-check", {"ref": "2111", "choice": "paid-in-full", "date": D})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["passkey"] is True and body["title"] == "Resolve a hand check"
    assert body["command"] == f".venv/bin/python scripts/bookings/check_payments.py --note 2111 'paid in full {D}' --owner"
    challenge = unb64(body["options"]["challenge"])
    assert challenge[16:] == auth.action_hash("assert", body["summary"])
    assert body["options"]["userVerification"] == "required"
    assert audit_lines() == []  # a preview runs nothing and logs nothing


def test_a_valid_assertion_runs_the_exact_argv_once_and_is_audited():
    c, a, _ = setup()
    inp = {"ref": "2111", "choice": "refunded", "date": D}
    os.environ["CC_SECRET_SHOULD_NOT_PASS"] = "x"
    try:
        with Runner(Recorder(out=b"2111: note added\n")) as rec:
            r = run(c, a, "resolve-hand-check", inp)
    finally:
        os.environ.pop("CC_SECRET_SHOULD_NOT_PASS")
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True and r.json()["exit_code"] == 0 and r.json()["output"] == "2111: note added"
    assert len(rec.calls) == 1
    argv, kw = rec.calls[0]
    assert argv == [PYX, CHECK, "--note", "2111", f"refunded {D}", "--owner"]
    assert kw["shell"] is False and kw["cwd"] == str(actions.REPO) and kw["timeout"] == 30
    assert not any(k.startswith("CC_") for k in kw["env"])
    assert len(kw["input"]) == 65 and kw["input"].endswith(b"\n")  # the nonce, over a pipe
    lines = audit_lines()
    assert [e["result"] for e in lines] == ["started", "ok"]
    done = lines[-1]
    assert done["action"] == "resolve-hand-check" and done["login"] == LOGIN and done["exit_code"] == 0
    assert done["input"] == inp and done["passkey"] == b64(a.cred_id)[:8]
    assert done["output_sha256"] == hashlib.sha256(b"2111: note added\n").hexdigest()
    assert done["summary"].endswith("--owner")
    assert oct(os.stat(Path(TMP) / "command-centre" / "audit.jsonl").st_mode & 0o777) == "0o600"


def test_stale_replayed_and_mismatched_assertions_are_refused():
    c, a, clock = setup()
    inp = {"ref": "2111", "choice": "refunded", "date": D}
    with Runner(Recorder()) as rec:
        # stale: more than 60 seconds after the preview
        p = preview(c, "resolve-hand-check", inp).json()
        clock.t += 61
        r = post(c, "/actions/resolve-hand-check/run", {"input": inp, "credential": a.assert_(p["options"])})
        assert r.status_code == 403 and r.json()["error"] == "challenge expired", r.text
        # replayed: the same assertion twice
        p = preview(c, "resolve-hand-check", inp).json()
        cred = a.assert_(p["options"])
        assert post(c, "/actions/resolve-hand-check/run", {"input": inp, "credential": cred}).status_code == 200
        r = post(c, "/actions/resolve-hand-check/run", {"input": inp, "credential": cred})
        assert r.status_code == 403 and r.json()["error"] == "unknown or used challenge", r.text
        # mismatched: approved for one input, run with another (another date, another choice, another ref)
        for other in (dict(inp, choice="paid-in-full"), dict(inp, ref="0310"),
                      dict(inp, date=(TODAY - datetime.timedelta(days=1)).isoformat())):
            r = run(c, a, "resolve-hand-check", other, opts_input=inp)
            assert r.status_code == 403 and r.json()["error"] == "wrong action", (other, r.text)
        # another action's assertion
        key = models.invoice_key(MSG)
        p = preview(c, "singer-confirm", {"invoice": key}).json()
        r = post(c, "/actions/resolve-hand-check/run", {"input": inp, "credential": a.assert_(p["options"])})
        assert r.status_code == 403 and r.json()["error"] == "wrong action", r.text
        assert len(rec.calls) == 1  # only the one good run
    results = [e["result"] for e in audit_lines()]
    assert results.count("ok") == 1 and results.count("refused: wrong action") == 4, results


def test_the_summary_is_rebuilt_at_run_time():
    """If the data a summary depends on changes between preview and run, the signed summary no longer matches."""
    c, a, _ = setup()
    key = models.invoice_key(MSG)
    p = preview(c, "singer-settled", {"invoice": key, "date": D}).json()
    rows = lm.read_csv(si.STORE)
    for r in rows:
        if r["message_id"] == MSG:
            r["amount_gbp"] = "999.00"
    write_csv(str(si.STORE), si.COLUMNS, rows)
    with Runner(Recorder()) as rec:
        r = post(c, "/actions/singer-settled/run", {"input": {"invoice": key, "date": D},
                                                    "credential": a.assert_(p["options"])})
    assert r.status_code == 403 and r.json()["error"] == "wrong action" and rec.calls == []


def test_output_is_scrubbed_and_trimmed():
    out = (b"fetched https://secret-mcp.example.net/zoho/abc123token ok\n"
           b"account 12345678 sort 601234, message 1789828736363141700\n"
           b"refresh_token=1//0gAbCdEfGh developer_token: AbCdEf123456 Authorization: Bearer abcdefghijklmnop\n"
           b"ya29.A0ARrdaM-Xy1234567890abcdefGHIJKLMNOPqrstuv\n"
           b"Applied 3 negatives to campaign on 2026-09-28 for \xc2\xa35.00\n")
    shown = actions.scrub(out.decode())
    for secret in ("secret-mcp", "abc123token", "12345678", "601234", "1789828736363141700", "0gAbCdEfGh",
                   "AbCdEf123456", "abcdefghijklmnop", "ya29.A0ARrdaM"):
        assert secret not in shown, (secret, shown)
    assert "<url>" in shown and "••••••" in shown and "Applied 3 negatives to campaign on 2026-09-28 for £5.00" in shown
    long = actions.scrub("x " * 10000)
    assert len(long) <= actions.OUTPUT_MAX + 2 and long.startswith("…")


def test_route_output_is_scrubbed():
    c, a, _ = setup()
    with Runner(Recorder(code=1, out=b"", err=b"no booking 2111 at https://x.example.org/y acct 87654321\n")):
        r = run(c, a, "resolve-hand-check", {"ref": "2111", "choice": "refunded", "date": D})
    body = r.json()
    assert body["ok"] is False and body["exit_code"] == 1
    assert "87654321" not in body["output"] and "x.example.org" not in body["output"]
    assert audit_lines()[-1]["result"] == "failed"


def test_a_timeout_is_reported_and_logged():
    c, a, _ = setup()
    boom = subprocess.TimeoutExpired(["x"], 30, output=b"partial", stderr=b"")
    with Runner(Recorder(raise_=boom)):
        r = run(c, a, "resolve-hand-check", {"ref": "2111", "choice": "refunded", "date": D})
    assert r.status_code == 200 and r.json()["exit_code"] is None and "no answer after 30 seconds" in r.json()["output"]
    assert audit_lines()[-1]["result"] == "timed out"
    assert not (Path(TMP) / "command-centre" / "owner-nonce").exists()


def test_the_owner_nonce_is_hashed_on_disk_and_gone_afterwards():
    c, a, _ = setup()
    seen = {}

    def check(argv, kw):
        path = Path(TMP) / "command-centre" / "owner-nonce"
        st = os.lstat(path)
        seen["mode"] = st.st_mode & 0o777
        seen["file"] = path.read_text()
        seen["stdin"] = kw["input"].decode().strip()
    with Runner(Recorder(check=check)):
        assert run(c, a, "resolve-hand-check", {"ref": "2111", "choice": "refunded", "date": D}).status_code == 200
    assert seen["mode"] == 0o600
    assert re.fullmatch(r"[0-9a-f]{64}", seen["stdin"])
    assert seen["file"] == hashlib.sha256(seen["stdin"].encode()).hexdigest() != seen["stdin"]
    assert not (Path(TMP) / "command-centre" / "owner-nonce").exists()
    # only the hand check gets a nonce: the singer actions read /dev/null
    with Runner(Recorder()) as rec:
        run(c, a, "singer-confirm", {"invoice": models.invoice_key(MSG)})
    assert rec.calls[0][1]["stdin"] == subprocess.DEVNULL and "input" not in rec.calls[0][1]


def test_real_check_payments_owner_note_through_the_full_route():
    c, a, _ = setup()
    r = run(c, a, "resolve-hand-check", {"ref": "2111", "choice": "paid-in-full", "date": D})
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True, r.json()
    assert r.json()["output"] == "2111: note added"
    assert ledger_notes("2111") == f"PENDING: invoiced; paid in full {D} (owner)"
    assert not (Path(TMP) / "command-centre" / "owner-nonce").exists()
    assert [e["result"] for e in audit_lines()] == ["started", "ok"]
    # and the same script refuses the same note without the app's nonce (as an allowlisted Claude call would)
    env = dict(os.environ)
    p = subprocess.run([PYX, CHECK, "--note", "2111", f"refunded {D}", "--owner"], env=env, capture_output=True,
                       text=True, stdin=subprocess.DEVNULL, timeout=30)
    assert p.returncode != 0 and ledger_notes("2111") == f"PENDING: invoiced; paid in full {D} (owner)"


def test_route_refusals():
    c, a, _ = setup()
    assert post(c, "/actions/rm-rf/preview", {"input": {}}).status_code == 404
    assert post(c, "/actions/todo-tick/preview", {"input": {}}).status_code == 404
    assert c.get("/actions/refresh-data/run", headers=HEADERS).status_code == 405
    r = c.post("/actions/refresh-data/run", content=b"input=", headers=dict(HEADERS, Origin=ORIGIN,
                                                                             **{"Content-Type": "application/x-www-form-urlencoded"}))
    assert r.status_code == 400
    assert post(c, "/actions/refresh-data/run", {"input": {}}, origin="https://evil.example").status_code == 403
    assert post(c, "/actions/refresh-data/run", {"input": {}, "summary": "anything"}).status_code == 400
    assert c.post("/actions/refresh-data/run", json={"input": {}}, headers={"Origin": ORIGIN}).status_code == 403
    r = preview(c, "resolve-hand-check", {"ref": "9999", "choice": "refunded", "date": D})
    assert r.status_code == 400 and r.json() == {"error": "unknown booking"}


def test_preview_without_a_registered_passkey_is_refused():
    write_config()
    fixtures()
    app = create_app(client_factory=lambda: None, checkout=lambda: "main")
    c = TestClient(app, base_url=ORIGIN, client=LOCAL)
    r = preview(c, "singer-confirm", {"invoice": models.invoice_key(MSG)})
    assert r.status_code == 409 and r.json()["error"] == "no passkeys registered"


def test_refresh_needs_no_passkey_and_clears_the_caches():
    c, a, _ = setup()
    cleared = []
    saved = data.Data.clear_caches
    data.Data.clear_caches = lambda self: cleared.append(True)
    try:
        with Runner(Recorder(out=b"wrote dashboard\n")) as rec:
            p = preview(c, "refresh-data", {})
            assert p.status_code == 200 and p.json()["passkey"] is False and "options" not in p.json()
            r = post(c, "/actions/refresh-data/run", {"input": {}})
    finally:
        data.Data.clear_caches = saved
    assert r.status_code == 200 and r.json()["ok"], r.text
    assert rec.calls[0][0] == [PYX, DASH] and cleared == [True]
    assert audit_lines()[-1]["action"] == "refresh-data" and "passkey" not in audit_lines()[-1]


# ---------------------------------------------------------------- the Books approval


def test_books_import_approval_writes_one_record():
    c, a, _ = setup()
    dry = Path(TMP) / "books-import-2026.json"
    dry.unlink(missing_ok=True)
    rec_path = Path(TMP) / "command-centre" / "approvals" / "books-import-2026.json"
    rec_path.unlink(missing_ok=True)
    r = preview(c, "approve-books-import", {})
    assert r.status_code == 400 and "no dry run" in r.json()["error"]
    dry.write_text(json.dumps([{"ref": "2111"}, {"ref": "0310"}]))
    p = preview(c, "approve-books-import", {}).json()
    sha = hashlib.sha256(dry.read_bytes()).hexdigest()
    assert "2 entries" in p["summary"] and sha[:16] in p["summary"] and p["passkey"] is True
    r = post(c, "/actions/approve-books-import/run", {"input": {}})
    assert r.status_code == 403 and not rec_path.exists()
    r = post(c, "/actions/approve-books-import/run", {"input": {}, "credential": a.assert_(p["options"])})
    assert r.status_code == 200 and r.json()["ok"], r.text
    record = json.loads(rec_path.read_text())
    assert record["dry_run_sha256"] == sha and record["entries"] == 2 and record["status"] == "approved"
    assert oct(os.stat(rec_path).st_mode & 0o777) == "0o600"
    assert oct(os.stat(rec_path.parent).st_mode & 0o777) == "0o700"
    assert preview(c, "approve-books-import", {}).json()["error"] == "already approved"
    assert audit_lines()[-1]["result"] == "ok"


# ---------------------------------------------------------------- Ads proposals


class AdsRepo:
    """A temp git repo with scripts/ads/, and actions.REPO pointed at it for the block."""

    def __enter__(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "scripts" / "ads").mkdir(parents=True)
        (self.root / "scripts" / "other").mkdir(parents=True)
        self.git("init", "-q")
        self.write("scripts/ads/negatives_2026_10.py", "print('validate only')\n")
        self.write("scripts/other/tool.py", "print('x')\n")
        self.git("add", "-A")
        self.commit("first")
        self.saved = actions.REPO
        actions.REPO = self.root
        actions.reset_validations()
        return self

    def __exit__(self, *exc):
        actions.REPO = self.saved
        actions.reset_validations()

    def git(self, *args):
        p = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        return p.stdout

    def commit(self, msg):
        self.git("-c", "user.name=t", "-c", "user.email=t@example.org", "commit", "-q", "-m", msg)

    def write(self, rel, text):
        path = self.root / rel
        path.write_text(text)
        return path


def proposal(pid="neg-2026-10", mode=0o600, **over):
    d = Path(TMP) / "command-centre" / "proposals"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{pid}.applied").unlink(missing_ok=True)
    body = {"id": pid, "kind": "ads", "title": "Add 3 negatives", "summary": "Adds solo, soloist and vocalist.",
            "script_path": "scripts/ads/negatives_2026_10.py", "created": "2026-10-05T09:00:00+01:00"}
    body.update(over)
    path = d / f"{pid}.json"
    path.unlink(missing_ok=True)
    path.write_text(json.dumps(body))
    os.chmod(path, mode)
    return path


def test_ads_proposal_checks():
    fixtures()
    with AdsRepo() as repo:
        v = actions.ADS_VALIDATE.validate
        proposal()
        c = v({"proposal": "neg-2026-10"})
        blob = repo.git("rev-parse", "HEAD:scripts/ads/negatives_2026_10.py").strip()
        assert c["blob"] == blob
        assert actions.ADS_VALIDATE.argv(c) == [PYX, str(repo.root / "scripts/ads/negatives_2026_10.py")]
        assert actions.ADS_VALIDATE.command(c) == ".venv/bin/python scripts/ads/negatives_2026_10.py"
        results = []
        checks = [(dict(script_path="scripts/other/tool.py"), 0o600, "the script must be a file in scripts/ads/"),
                  (dict(script_path="scripts/ads/../other/tool.py"), 0o600, "the script must be a file in scripts/ads/"),
                  (dict(script_path="/etc/passwd"), 0o600, "the script must be a file in scripts/ads/"),
                  (dict(script_path="scripts/ads/missing.py"), 0o600, "the script must be a file in scripts/ads/"),
                  ({}, 0o644, "the proposal file must be mode 600"),
                  ({}, 0o640, "the proposal file must be mode 600"),
                  (dict(id="other-id"), 0o600, "the proposal's id doesn't match its file name"),
                  (dict(kind="books"), 0o600, "not an Ads proposal"),
                  (dict(title=""), 0o600, "the proposal's title is missing or too long")]
        for over, mode, why in checks:
            proposal(mode=mode, **over)
            results.append((over, mode, refused(v, {"proposal": "neg-2026-10"}), why))
        for over, mode, got, why in results:
            assert got == why, (over, mode, got)
        # untracked, then modified, then a symlink
        repo.write("scripts/ads/new_one.py", "print(1)\n")
        proposal(script_path="scripts/ads/new_one.py")
        assert refused(v, {"proposal": "neg-2026-10"}) == "the script isn't committed"
        repo.write("scripts/ads/negatives_2026_10.py", "print('changed')\n")
        proposal()
        assert refused(v, {"proposal": "neg-2026-10"}) == "the script has uncommitted changes"
        repo.git("checkout", "--", "scripts/ads/negatives_2026_10.py")
        os.symlink(repo.root / "scripts/other/tool.py", repo.root / "scripts/ads/link_tool.py")
        repo.git("add", "scripts/ads/link_tool.py")
        repo.commit("a symlink")
        proposal(script_path="scripts/ads/link_tool.py")
        assert refused(v, {"proposal": "neg-2026-10"}) == "the script must be a file in scripts/ads/"
        # a symlinked proposal file, and bad ids
        proposal()
        d = Path(TMP) / "command-centre" / "proposals"
        (d / "sneaky.json").unlink(missing_ok=True)
        os.symlink(d / "neg-2026-10.json", d / "sneaky.json")
        assert refused(v, {"proposal": "sneaky"}) == "the proposal file must be a plain file"
        (d / "sneaky.json").unlink()
        for bad in ("../neg-2026-10", "Neg", "", "-x"):
            refused(v, {"proposal": bad})
        listed = {p["id"]: p for p in actions.list_proposals()}
        assert listed["neg-2026-10"]["problem"] is None and not listed["neg-2026-10"]["applied"]


def test_ads_validate_then_apply_bound_to_the_output():
    c, a, _ = setup()
    with AdsRepo() as repo:
        proposal()
        inp = {"proposal": "neg-2026-10"}
        # apply before any validate: refused, nothing runs
        r = preview(c, "ads-apply", inp)
        assert r.status_code == 409 and "validate this change set first" in r.json()["error"]
        with Runner(Recorder(out=b"Validated 3 operations (validate_only)\n")) as rec:
            r = run(c, a, "ads-validate", inp)
        assert r.status_code == 200 and r.json()["ok"], r.text
        assert r.json()["next"] == {"action": "ads-apply", "input": inp, "label": "Apply this change set"}
        assert rec.calls[0][0] == [PYX, str(repo.root / "scripts/ads/negatives_2026_10.py")]
        out_sha = hashlib.sha256(b"Validated 3 operations (validate_only)\n").hexdigest()
        p = preview(c, "ads-apply", inp).json()
        assert out_sha[:16] in p["summary"] and p["command"].endswith("negatives_2026_10.py --apply")
        assert "£5 daily cap" in p["summary"]
        # the apply's assertion is bound to that output: a second validate with other output changes the summary
        with Runner(Recorder(out=b"Validated 4 operations\n")):
            run(c, a, "ads-validate", inp)
        with Runner(Recorder(out=b"Applied and logged\n")) as rec:
            r = post(c, "/actions/ads-apply/run", {"input": inp, "credential": a.assert_(p["options"])})
            assert r.status_code == 403 and r.json()["error"] == "wrong action" and rec.calls == []
            r = run(c, a, "ads-apply", inp)
        assert r.status_code == 200 and r.json()["ok"], r.text
        assert rec.calls[0][0] == [PYX, str(repo.root / "scripts/ads/negatives_2026_10.py"), "--apply"]
        assert (Path(TMP) / "command-centre" / "proposals" / "neg-2026-10.applied").exists()
        # applied: neither step is offered again
        assert preview(c, "ads-validate", inp).json()["error"] == "already applied"
        assert preview(c, "ads-apply", inp).json()["error"] == "already applied"


def test_ads_apply_refused_after_the_script_changes_or_a_failed_validate():
    c, a, _ = setup()
    with AdsRepo() as repo:
        proposal()
        inp = {"proposal": "neg-2026-10"}
        with Runner(Recorder(code=1, out=b"GoogleAdsException\n")):
            assert run(c, a, "ads-validate", inp).json()["next"] is None
        assert preview(c, "ads-apply", inp).status_code == 409
        with Runner(Recorder()):
            run(c, a, "ads-validate", inp)
        repo.write("scripts/ads/negatives_2026_10.py", "print('now it spends')\n")
        repo.git("add", "-A")
        repo.commit("changed after validation")
        r = preview(c, "ads-apply", inp)
        assert r.status_code == 409 and "changed since it was validated" in r.json()["error"]


# ---------------------------------------------------------------- owner-only protection vs the allowlist


def claude_form(argv):
    """An action's argv as Claude would type it: .venv/bin/python scripts/… args (shell-quoted)."""
    import shlex
    rel = os.path.relpath(argv[1], str(actions.REPO))
    return shlex.join([allowlist.PY, rel, *argv[2:]]).replace("'", '"')


SAFE_ON_ALLOWLIST = {
    "refresh-data": "read-only; dashboard.py is allowlisted for the scheduled prompts",
    "singer-withdrawn": "the enquiry assistant already withdraws a mis-sent invoice (Appendix E)",
    "resolve-hand-check": "matched by --note *; check_payments.py refuses --owner without the app's nonce",
}


def test_the_apps_own_commands_are_not_allowlisted_unless_safe():
    fixtures()
    pats = allowlist.allow_patterns()
    key = models.invoice_key(MSG)
    samples = {
        "resolve-hand-check": {"ref": "2111", "choice": "paid-in-full", "date": D},
        "singer-confirm": {"invoice": key},
        "singer-settled": {"invoice": key, "date": D},
        "singer-withdrawn": {"invoice": key, "reason": "not-ours"},
        "refresh-data": {},
    }
    seen = set()
    for name, inp in samples.items():
        defn = actions.REGISTRY[name]
        cmd = claude_form(defn.argv(defn.validate(inp)))
        on = allowlist.allowed(cmd, pats)
        seen.add(name)
        if name in SAFE_ON_ALLOWLIST:
            continue
        assert not on, f"{name}: {cmd} is allowlisted"
    with AdsRepo():
        proposal()
        for name, flag in (("ads-validate", []), ("ads-apply", ["--apply"])):
            cmd = f"{allowlist.PY} scripts/ads/negatives_2026_10.py" + (" --apply" if flag else "")
            assert not allowlist.allowed(cmd, pats), cmd
            seen.add(name)
    seen |= {"approve-books-import", "todo-tick"}  # no subprocess
    assert seen == set(actions.REGISTRY)
    # the guarded one really is matched, and its refusal is tested in test_check_payments.py
    cmd = claude_form(actions.RESOLVE_HAND_CHECK.argv(actions.RESOLVE_HAND_CHECK.validate(samples["resolve-hand-check"])))
    assert allowlist.allowed(cmd, pats) and cmd.endswith("--owner")
    head = re.sub(r"--note \S+ ", "--note X ", cmd.split('"')[0])
    assert any(g.startswith(head) for g in allowlist.SCRIPT_GUARDED), head


# ---------------------------------------------------------------- pages


def page(c, path):
    r = c.get(path, headers=HEADERS)
    assert r.status_code == 200, (path, r.status_code, r.text[:300])
    return r.text


def test_pages_carry_the_action_forms_without_ids_or_inline_code():
    c, a, _ = setup()
    (Path(TMP) / "books-import-2026.json").write_text("[]")
    (Path(TMP) / "command-centre" / "approvals" / "books-import-2026.json").unlink(missing_ok=True)
    key = models.invoice_key(MSG)
    out = page(c, "/singers")
    assert 'data-action="singer-confirm"' in out and f'value="{key}"' in out
    assert 'data-action="singer-withdrawn"' in out and 'data-action="singer-settled"' in out
    booking = page(c, "/bookings/2111")
    assert 'data-action="resolve-hand-check"' in booking and 'name="ref" value="2111"' in booking
    today = page(c, "/")
    assert 'data-action="approve-books-import"' in today
    assert 'data-action="refresh-data"' in page(c, "/health")
    for path in ("/", "/money", "/singers", "/bookings/2111", "/health", "/marketing", "/activity"):
        out = page(c, path)
        for bad in (MSG, MSG_PAID, "Fenwickson", "Smithfield", "example.org", "https:"):
            assert bad not in out, (path, bad)
        assert not re.search(r"\sstyle\s*=|\son[a-z]+\s*=", out, re.I), path
        for tag in re.findall(r"<script\b[^>]*>", out, re.I):
            assert re.search(r'src="/static/[a-z.]+\.js"', tag), tag
        assert '<dialog id="cc-dialog"' in out and 'src="/static/actions.js"' in out
    js = c.get("/static/actions.js", headers=HEADERS).text
    assert "fetch(" not in js and "innerHTML" not in js and not re.search(r"https?:", js)
    assert "/preview" in js and "/run" in js
    (Path(TMP) / "books-import-2026.json").unlink()


def test_marketing_lists_proposals():
    c, a, _ = setup()
    with AdsRepo():
        proposal()
        proposal(pid="bad-one", mode=0o644)
        out = page(c, "/marketing")
    assert "Add 3 negatives" in out and 'data-action="ads-validate"' in out and 'value="neg-2026-10"' in out
    assert "the proposal file must be mode 600" in out
    assert 'data-action="ads-apply"' not in out  # only after a validate
    (Path(TMP) / "command-centre" / "proposals" / "bad-one.json").unlink()
    (Path(TMP) / "command-centre" / "proposals" / "neg-2026-10.json").unlink()


def test_activity_page_filters_and_masks():
    c, a, _ = setup()
    with Runner(Recorder(out=b"ok")):
        run(c, a, "resolve-hand-check", {"ref": "2111", "choice": "refunded", "date": D})
        run(c, a, "singer-confirm", {"invoice": models.invoice_key(MSG)})
    post(c, "/actions/singer-confirm/run", {"input": {"invoice": models.invoice_key(MSG)}})  # refused
    with open(Path(TMP) / "command-centre" / "audit.jsonl", "a") as f:
        f.write("not json\n")
    out = page(c, "/activity")
    assert "resolve-hand-check" in out and "singer-confirm" in out
    assert MSG not in out and "••••••" in out  # the message id in the singer summary is masked
    assert "owner@" not in out and "by owner" in out
    only = page(c, "/activity?action=resolve-hand-check")
    assert "Resolve the hand check" in only and "Confirm the bank details" not in only
    ref = page(c, "/activity?result=refused")
    assert "refused: no passkey" in ref and "Resolve the hand check" not in ref
    q = page(c, "/activity?q=%3Cscript%3Ealert(1)")
    assert "<script>alert" not in q and 'value="&lt;script&gt;alert(1)"' in q and "Nothing matches" in q
    assert "Confirm the bank details" in page(c, "/activity?q=bank+details")
    assert page(c, "/activity?action=%3Cx%3E&result=nope").count("activity-item") >= 3


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"PASS {name}")
        except Exception as ex:  # an error is a failure too
            failures += 1
            import traceback
            traceback.print_exc()
            print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
