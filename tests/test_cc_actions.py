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
FP_A = "a1b2c3d4e5f60718"
FP_C = "c0ffee00c0ffee00"
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
        dict(base, message_id=MSG, received="2026-09-20", singer_name="Jane Fenwickson", bank_fp=FP_A, bank_last4="4321",
             bank_confirmed=""),
        dict(base, message_id=MSG_PAID, received="2026-09-01", singer_name="Jane Fenwickson", bank_fp=FP_A,
             bank_last4="4321", paid_on="2026-09-05", paid_amount="120.00"),
        dict(base, message_id=MSG_NOBANK, received="2026-09-21", singer_name="Bob Quillfeather", bank_fp="",
             bank_last4=""),
        dict(base, message_id=MSG_CONFIRMED, received="2026-09-22", singer_name="Cat Mistakeham", bank_fp=FP_C,
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


def setup(clock=None, client_factory=lambda: None):
    """A registered passkey, the fixtures, a fresh audit log; returns (client, authenticator, clock)."""
    for p in ("audit.jsonl",):
        (Path(TMP) / "command-centre" / p).unlink(missing_ok=True)
    write_config()
    fixtures()
    actions.reset_validations()
    clock = clock or Clock()
    pk = auth.Passkeys(auth.ChallengeStore(clock=clock))
    app = create_app(client_factory=client_factory, passkeys=pk, checkout=lambda: "main")
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
CC_SYNC = str(Path(ROOT) / "scripts" / "reports" / "cc_sync.py")


# ---------------------------------------------------------------- the registry


def test_registry_and_passkey_flags():
    assert set(actions.REGISTRY) == {"todo-tick", "resolve-hand-check", "singer-confirm", "singer-settled",
                                     "singer-withdrawn", "refresh-data", "ads-validate", "ads-apply",
                                     "approve-books-import", "books-import-done", "push-subscribe",
                                     "push-unsubscribe", "backup-now", "draft-mark"}
    no_passkey = {n for n, a in actions.REGISTRY.items() if not a.passkey}
    assert no_passkey == {"todo-tick", "refresh-data", "push-unsubscribe", "backup-now", "draft-mark"}, no_passkey
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
    assert actions.SINGER_CONFIRM.argv(c) == [PYX, SINGER, "confirm", MSG, "--expect-fp", FP_A]
    s = actions.SINGER_CONFIRM.preview(c)
    assert "Jane" in s and "Fenwickson" not in s and "••••4321" in s and "£120.00" in s
    assert f"fingerprint {FP_A})" in s  # all 16 characters, the same ones --expect-fp passes
    assert s.endswith(f"Runs: .venv/bin/python scripts/bookings/singer_invoices.py confirm {MSG} --expect-fp {FP_A}")
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
    assert actions.REFRESH.then_argv() == [PYX, CC_SYNC, "books"]
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
    assert challenge[16:] == auth.action_hash("assert", body["summary"], "resolve-hand-check")
    assert challenge[16:] != auth.action_hash("assert", body["summary"], "singer-confirm")  # the name is bound too
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
    assert [c[0] for c in rec.calls] == [[PYX, DASH], [PYX, CC_SYNC, "books"]] and cleared == [True]
    assert all(kw["shell"] is False and kw["env"]["LCS_PRIVATE_DIR"] == TMP for _, kw in rec.calls)
    assert p.json()["command"] == (".venv/bin/python scripts/reports/dashboard.py, then "
                                   ".venv/bin/python scripts/reports/cc_sync.py books"), p.json()["command"]
    assert "Books cache" in p.json()["summary"]
    assert audit_lines()[-1]["action"] == "refresh-data" and "passkey" not in audit_lines()[-1]


def test_refresh_reports_a_failed_books_sync():
    """cc_sync.py books exits 1 when Books can't be read: the refresh says it failed, and the dashboard still ran."""
    c, a, _ = setup()

    def answer(argv, **kw):
        code = 1 if argv[-1] == "books" else 0
        out = b"books: not updated (McpError); the last cache is kept\n" if code else b"wrote dashboard\n"
        return subprocess.CompletedProcess(argv, code, out, b"")
    with Runner(answer):
        r = post(c, "/actions/refresh-data/run", {"input": {}})
    body = r.json()
    assert r.status_code == 200 and body["ok"] is False and body["exit_code"] == 1, body
    assert "wrote dashboard" in body["output"] and "books: not updated (McpError)" in body["output"], body
    assert audit_lines()[-1]["result"] == "failed" and audit_lines()[-1]["exit_code"] == 1


# ---------------------------------------------------------------- the Books approval


def test_books_import_approval_writes_one_record():
    c, a, _ = setup()
    dry = Path(TMP) / "books-import-2026.json"
    dry.unlink(missing_ok=True)
    rec_path = Path(TMP) / "command-centre" / "approvals" / "books-import-2026.json"
    rec_path.unlink(missing_ok=True)
    r = preview(c, "approve-books-import", {})
    assert r.status_code == 400 and "no dry run" in r.json()["error"]
    dry.write_text(json.dumps([{"ref": "2111", "total": 650}, {"ref": "0310", "total": "575.00"}]))
    p = preview(c, "approve-books-import", {}).json()
    sha = hashlib.sha256(dry.read_bytes()).hexdigest()
    assert "2 entries" in p["summary"] and sha[:16] in p["summary"] and p["passkey"] is True
    assert "£1,225.00 in total" in p["summary"] and "first 2111, last 0310" in p["summary"], p["summary"]
    r = post(c, "/actions/approve-books-import/run", {"input": {}})
    assert r.status_code == 403 and not rec_path.exists()
    r = post(c, "/actions/approve-books-import/run", {"input": {}, "credential": a.assert_(p["options"])})
    assert r.status_code == 200 and r.json()["ok"], r.text
    record = json.loads(rec_path.read_text())
    assert record["dry_run_sha256"] == sha and record["entries"] == 2 and record["status"] == "approved"
    assert record["approved_by"] == LOGIN and record["passkey"] == b64(a.cred_id)
    assert record["total_gbp"] == 1225.0 and (record["first_ref"], record["last_ref"]) == ("2111", "0310")
    assert oct(os.stat(rec_path).st_mode & 0o777) == "0o600"
    assert oct(os.stat(rec_path.parent).st_mode & 0o777) == "0o700"
    assert preview(c, "approve-books-import", {}).json()["error"] == "already approved"
    assert audit_lines()[-1]["result"] == "ok"
    # There is no in-app chat and the app never runs Claude Code itself: once approved, Today's Handoffs offer a
    # fixed copy-to-clipboard prompt for Claude Code Remote Control instead.
    out = page(c, "/")
    assert 'class="button quiet cc-copy"' in out and "Copy prompt for Remote Control" in out
    assert "books-import-2026.json" in out and sha[:16] in out
    assert "docs/superpowers/specs/2026-09-28-zoho-books-design.md" in out
    assert "never send, void or record a payment" in out
    prompt = re.search(r'data-prompt="([^"]*)"[^>]*>Copy prompt for Remote Control', out).group(1)
    assert "2111" not in prompt and "0310" not in prompt and "650" not in prompt and "1,225" not in prompt
    assert "skip any invoice number that already exists" in prompt


BOOKS_DRY = [{"ref": "2111", "total": 650}, {"ref": "0310", "total": "575.00"}]


def books_files(dry=BOOKS_DRY, record=None, cache=None):
    """The dry run, the approval record (a dict, or True for one matching the dry run) and books.json, each
    written or removed."""
    dry_path = Path(TMP) / "books-import-2026.json"
    rec_path = Path(TMP) / "command-centre" / "approvals" / "books-import-2026.json"
    cache_path = Path(TMP) / "command-centre" / "cache" / "books.json"
    for p in (dry_path, rec_path, cache_path):
        p.unlink(missing_ok=True)
    if dry is not None:
        dry_path.write_text(json.dumps(dry))
    if record is not None:
        if record is True:
            record = {"approved_at": "2026-09-28T08:00:00+00:00", "approved_by": LOGIN, "passkey": "abc",
                      "dry_run": "~/lcs-private/books-import-2026.json",
                      "dry_run_sha256": hashlib.sha256(dry_path.read_bytes()).hexdigest(), "entries": 2,
                      "total_gbp": 1225.0, "first_ref": "2111", "last_ref": "0310",
                      "instruction": actions.BOOKS_INSTRUCTION, "status": "approved"}
        actions.write_private(rec_path, record)
    if cache is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"generated_at": "2026-09-28T07:00:00+01:00", "totals": {}, "bills": [],
                                          "invoices": [{"number": n, "status": "draft", "date": "2026-09-28",
                                                        "total": 1.0, "balance": 1.0} for n in cache]}))
    return dry_path, rec_path


def attention(out):
    m = re.search(r'<span class="count">(\d+)</span>', out)
    return int(m.group(1)) if m else 0


def approvals_card(out):
    return re.search(r"<h3>Approvals waiting</h3>(.*?)</article>", out, re.S).group(1)


def handoffs_section(out):
    return re.search(r'<h2 id="handoffs"[^>]*>Handoffs</h2>(.*?)</section>', out, re.S).group(1)


def test_books_import_states_on_today():
    c, a, _ = setup()
    for p in (Path(TMP) / "command-centre" / "proposals").glob("*.json"):  # the Ads tests' leftovers
        p.unlink()
    # none: no dry run, no approval
    books_files(dry=None)
    assert actions.books_status()["state"] == "none"
    out = page(c, "/")
    base = attention(out)
    assert "Nothing waiting for approval." in approvals_card(out)
    assert approvals_card(out).count("Nothing waiting for approval.") == 1
    assert "Books import" not in handoffs_section(out) and "books-import-done" not in out
    # waiting: a dry run, no approval — the only Books state under Approvals waiting
    books_files()
    st = actions.books_status()
    assert st["state"] == "waiting" and st["dry_run"] and st["approved_at"] is None
    out = page(c, "/")
    assert 'data-action="approve-books-import"' in approvals_card(out) and attention(out) == base + 1
    assert "Nothing waiting for approval." not in out and "books-import-done" not in out
    # approved: the approval matches the dry run and the import isn't done — a handoff, not an approval
    books_files(record=True)
    st = actions.books_status()
    assert st["state"] == "approved" and st["approved_at"].startswith("2026-09-28") and st["imported_at"] is None
    assert st["dry_run_sha256"] and st["dry_run"]  # the old keys stay
    out = page(c, "/")
    card, hand = approvals_card(out), handoffs_section(out)
    assert "Nothing waiting for approval." in card and "Books import" not in card and attention(out) == base
    assert "Copy prompt for Remote Control" in hand and "skip any invoice number that already exists" in hand
    assert 'data-action="books-import-done"' in hand and "approved Mon 28 Sep 2026" in hand
    assert models.books_import_handoff(st) is not None
    # stale: the dry run changed since — a warning, no prompt, and it needs you
    Path(TMP, "books-import-2026.json").write_text(json.dumps(BOOKS_DRY + [{"ref": "1111", "total": 1}]))
    st = actions.books_status()
    assert st["state"] == "stale" and models.books_import_handoff(st) is None
    out = page(c, "/")
    hand = handoffs_section(out)
    assert "the dry run has moved on" in hand and 'data-action="books-import-done"' in hand
    assert "never send, void or record a payment" not in out  # no import prompt to copy
    assert "Nothing waiting for approval." in approvals_card(out) and attention(out) == base + 1
    Path(TMP, "books-import-2026.json").unlink()  # a dry run that's gone is stale too
    assert actions.books_status()["state"] == "stale"
    # imported, by the record: nothing about the import on Today
    books_files(record=dict(json.loads(books_files(record=True)[1].read_text()), status="imported",
                            imported_at="2026-09-28T12:00:00+00:00"))
    st = actions.books_status()
    assert st["state"] == "imported" and st["imported_at"] == "2026-09-28T12:00:00+00:00"
    out = page(c, "/")
    assert "Books import" not in out and "books-import-done" not in out and "approve-books-import" not in out
    assert attention(out) == base and models.books_import_handoff(st) is None
    # imported, by the Books cache: every dry-run ref is an invoice number in Books (norm_ref: INV2111 is 2111)
    books_files(record=True, cache=["INV2111", "0310", "9999"])
    assert actions.books_status()["state"] == "imported"
    books_files(record=True, cache=["2111"])  # one missing: still approved
    assert actions.books_status()["state"] == "approved"
    books_files(dry=[{"ref": "2111"}, {"amount": 5}], record=True, cache=["2111"])  # an entry without a ref
    assert actions.books_status()["state"] == "approved"
    books_files(dry=[], record=True, cache=[])  # an empty dry run proves nothing
    assert actions.books_status()["state"] == "approved"
    # a cache alone never skips the approval
    books_files(cache=["2111", "0310"])
    assert actions.books_status()["state"] == "waiting"
    books_files(dry=None)


def test_mark_the_books_import_done():
    c, a, _ = setup()
    for state_files in ({"dry": None}, {}):  # none, then waiting
        books_files(**state_files)
        r = preview(c, "books-import-done", {})
        assert r.status_code == 400 and r.json()["error"] == "the Books import isn't approved yet", r.text
    _, rec_path = books_files(record=True)
    before = json.loads(rec_path.read_text())
    p = preview(c, "books-import-done", {}).json()
    assert p["passkey"] is True and p["command"] is None
    assert "Mark the 2026 Books import done" in p["summary"] and before["dry_run_sha256"][:16] in p["summary"]
    assert "approved 2026-09-28" in p["summary"] and "Nothing is sent to Books" in p["summary"]
    assert "Writes: ~/lcs-private/command-centre/approvals/books-import-2026.json" in p["summary"]
    r = post(c, "/actions/books-import-done/run", {"input": {}})
    assert r.status_code == 403 and json.loads(rec_path.read_text()) == before  # a passkey is needed
    r = post(c, "/actions/books-import-done/run", {"input": {}, "credential": a.assert_(p["options"])})
    assert r.status_code == 200 and r.json()["ok"] and r.json()["output"] == "Books import marked done", r.text
    after = json.loads(rec_path.read_text())
    assert after["status"] == "imported" and datetime.datetime.fromisoformat(after["imported_at"]).tzinfo is not None
    assert {k: v for k, v in after.items() if k not in ("status", "imported_at")} == \
        {k: v for k, v in before.items() if k != "status"}  # every other field kept
    assert oct(os.stat(rec_path).st_mode & 0o777) == "0o600"
    assert [p.name for p in rec_path.parent.iterdir()] == [rec_path.name]  # no temp file left
    assert actions.books_status()["state"] == "imported"
    line = audit_lines()[-1]
    assert line["action"] == "books-import-done" and line["result"] == "ok" and line["passkey"]
    assert preview(c, "books-import-done", {}).json()["error"] == "the Books import is already marked done"
    assert "books-import-done" not in page(c, "/")
    # a stale approval can be marked done too (the import ran before the dry run moved on)
    books_files(record=True)
    Path(TMP, "books-import-2026.json").write_text("[]")
    assert actions.books_status()["state"] == "stale"
    p = preview(c, "books-import-done", {}).json()
    assert "The dry run has changed since it was approved" in p["summary"]
    r = post(c, "/actions/books-import-done/run", {"input": {}, "credential": a.assert_(p["options"])})
    assert r.status_code == 200 and actions.books_status()["state"] == "imported"
    books_files(dry=None)


# ---------------------------------------------------------------- Ads proposals


NEG_SCRIPT = '''"""Add three negatives (a test script)."""
import argparse
import helper
p = argparse.ArgumentParser()
p.add_argument("words", nargs="*")
m = p.add_mutually_exclusive_group()
m.add_argument("--validate-only", action="store_true")
m.add_argument("--apply", action="store_true")
a = p.parse_args()
print("APPLIED" if a.apply else "validate only", helper.X, *a.words)
'''
OLD_SCRIPT = '''"""An old script: validate by default, --apply to apply; no --validate-only."""
import argparse
p = argparse.ArgumentParser()
p.add_argument("--apply", action="store_true")
p.parse_args()
print("old script ran")
'''


class AdsRepo:
    """Two temp git repos: `upstream`, a bare repo standing in for GitHub (actions.TEST_UPSTREAM points the app's
    mirror fetch at it), and `root`, a working clone (actions.REPO) that the tests treat as hostile. The app's
    mirror under the temp private dir is removed first, so each block starts from an empty mirror."""

    def __enter__(self):
        self.upstream = Path(tempfile.mkdtemp()) / "github.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.upstream)], check=True)
        self.root = Path(tempfile.mkdtemp())
        (self.root / "scripts" / "ads").mkdir(parents=True)
        (self.root / "scripts" / "other").mkdir(parents=True)
        (self.root / "logs").mkdir()
        self.git("init", "-q")
        self.git("remote", "add", "origin", str(self.upstream))
        self.write("scripts/ads/negatives_2026_10.py", NEG_SCRIPT)
        self.write("scripts/ads/helper.py", "X = 'honest helper'\n")
        self.write("scripts/ads/old_style.py", OLD_SCRIPT)
        self.write("scripts/other/tool.py", "print('x')\n")
        self.write(".gitignore", "__pycache__/\n")
        self.git("add", "-A")
        self.commit("first")
        self.publish()
        self.saved = (actions.REPO, actions.TEST_UPSTREAM)
        actions.REPO = self.root
        actions.TEST_UPSTREAM = self.upstream
        import shutil
        shutil.rmtree(actions.mirror_dir(), ignore_errors=True)
        actions.reset_validations()
        return self

    def __exit__(self, *exc):
        actions.REPO, actions.TEST_UPSTREAM = self.saved
        actions.reset_validations()

    def git(self, *args):
        p = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        return p.stdout

    def commit(self, msg):
        self.git("-c", "user.name=Tess Author", "-c", "user.email=t@example.org", "commit", "-q", "-m", msg)
        return self.head()

    def head(self):
        return self.git("rev-parse", "HEAD").strip()

    def publish(self, ref="HEAD"):
        """Push `ref` to GitHub's main (forced: a rewrite of main is a publish too)."""
        self.git("push", "-q", "--force", "origin", f"{ref}:refs/heads/main")

    def blob(self, rel="scripts/ads/negatives_2026_10.py", commit="HEAD"):
        p = subprocess.run(["git", "-C", str(self.root), "rev-parse", f"{commit}:{rel}"], capture_output=True, text=True)
        return p.stdout.strip() if p.returncode == 0 else "e" * 40  # not in that commit

    def write(self, rel, text):
        path = self.root / rel
        path.write_text(text)
        return path


def proposal(pid="neg-2026-10", mode=0o600, repo=None, **over):
    """A proposal file; with `repo`, pinned to its HEAD and the script's blob there."""
    d = Path(TMP) / "command-centre" / "proposals"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{pid}.applied").unlink(missing_ok=True)
    body = {"id": pid, "kind": "ads", "title": "Add 3 negatives", "summary": "Adds solo, soloist and vocalist.",
            "script_path": "scripts/ads/negatives_2026_10.py", "created": "2026-10-05T09:00:00+01:00",
            "args": ["solo", "soloist", "vocalist"]}
    if repo is not None:
        body["commit"] = repo.head()
        body["script_blob"] = repo.blob(over.get("script_path", body["script_path"]))
    body.update(over)
    path = d / f"{pid}.json"
    path.unlink(missing_ok=True)
    path.write_text(json.dumps({k: v for k, v in body.items() if v is not None}))
    os.chmod(path, mode)
    return path


def clear_applied():
    d = Path(TMP) / "command-centre" / "proposals"
    for p in d.glob("*.applied") if d.exists() else []:
        p.unlink()


def test_ads_proposal_checks():
    fixtures()
    clear_applied()
    with AdsRepo() as repo:
        v = actions.ADS_VALIDATE.validate
        proposal(repo=repo)
        c = v({"proposal": "neg-2026-10"})
        assert c["blob"] == repo.blob() and c["commit"] == repo.head() and c["args"] == ["solo", "soloist", "vocalist"]
        assert c["facts"]["author"] == "Tess Author" and c["facts"]["doc"] == "Add three negatives (a test script)."
        assert actions.ADS_VALIDATE.command(c) == (".venv/bin/python -E -s -B scripts/ads/negatives_2026_10.py solo "
                                                   "soloist vocalist --validate-only")
        s = actions.ADS_VALIDATE.preview(c)
        for bit in ("scripts/ads/negatives_2026_10.py", repo.head()[:12], "on main at GitHub: yes", "Tess Author",
                    "What the script says it does: Add three negatives (a test script).",
                    "Claude's description: \"Add 3 negatives\": Adds solo, soloist and vocalist."):
            assert bit in s, (bit, s)
        assert s.splitlines()[-1].startswith("Runs: ")
        results = []
        checks = [(dict(script_path="scripts/other/tool.py"), 0o600, "the script must be a file in scripts/ads/"),
                  (dict(script_path="scripts/ads/../other/tool.py"), 0o600, "the script must be a file in scripts/ads/"),
                  (dict(script_path="/etc/passwd"), 0o600, "the script must be a file in scripts/ads/"),
                  (dict(script_blob=None), 0o600, "the proposal must pin the script's blob (script_blob)"),
                  (dict(script_blob="abc"), 0o600, "the proposal must pin the script's blob (script_blob)"),
                  (dict(commit=None), 0o600, "the proposal must pin a full commit id (commit)"),
                  (dict(commit="main"), 0o600, "the proposal must pin a full commit id (commit)"),
                  (dict(commit="f" * 40), 0o600, "the proposal's commit isn't on main at GitHub"),
                  (dict(script_blob="e" * 40), 0o600, "the script at that commit isn't the blob the proposal names"),
                  (dict(args="solo"), 0o600, "the proposal's args must be a short list of simple words or numbers"),
                  (dict(args=["--apply"]), 0o600, "the proposal's args must be a short list of simple words or numbers"),
                  (dict(args=["-x"]), 0o600, "the proposal's args must be a short list of simple words or numbers"),
                  (dict(args=["a b"]), 0o600, "the proposal's args must be a short list of simple words or numbers"),
                  (dict(args=["../x"]), 0o600, "the proposal's args must be a short list of simple words or numbers"),
                  (dict(args=["x"] * 13), 0o600, "the proposal's args must be a short list of simple words or numbers"),
                  (dict(args=[5]), 0o600, "the proposal's args must be a short list of simple words or numbers"),
                  (dict(extra="x"), 0o600, "the proposal has an unexpected field"),
                  ({}, 0o644, "the proposal file must be mode 600"),
                  ({}, 0o640, "the proposal file must be mode 600"),
                  (dict(id="other-id"), 0o600, "the proposal's id doesn't match its file name"),
                  (dict(kind="books"), 0o600, "not an Ads proposal"),
                  (dict(title=""), 0o600, "the proposal's title is missing or too long")]
        for over, mode, why in checks:
            proposal(mode=mode, repo=repo, **over)
            results.append((over, mode, refused(v, {"proposal": "neg-2026-10"}), why))
        for over, mode, got, why in results:
            assert got == why, (over, mode, got)
        # a commit that isn't on GitHub's main (committed locally, never pushed)
        repo.write("scripts/ads/negatives_2026_10.py", NEG_SCRIPT + "# local only\n")
        repo.git("add", "-A")
        repo.commit("local")
        proposal(repo=repo)
        assert refused(v, {"proposal": "neg-2026-10"}) == "the proposal's commit isn't on main at GitHub"
        repo.publish()
        assert v({"proposal": "neg-2026-10"})["commit"] == repo.head()
        # a script path missing at that commit, and a symlink committed in scripts/ads/
        proposal(repo=repo, script_path="scripts/ads/missing.py", script_blob="e" * 40)
        assert refused(v, {"proposal": "neg-2026-10"}) == "the script isn't in that commit"
        os.symlink(repo.root / "scripts/other/tool.py", repo.root / "scripts/ads/link_tool.py")
        repo.git("add", "scripts/ads/link_tool.py")
        repo.commit("a symlink")
        repo.publish()
        proposal(repo=repo, script_path="scripts/ads/link_tool.py")
        assert refused(v, {"proposal": "neg-2026-10"}) == "the script must be a file in scripts/ads/"
        # a symlinked proposal file, and bad ids
        proposal(repo=repo)
        d = Path(TMP) / "command-centre" / "proposals"
        (d / "sneaky.json").unlink(missing_ok=True)
        os.symlink(d / "neg-2026-10.json", d / "sneaky.json")
        assert refused(v, {"proposal": "sneaky"}) == "the proposal file must be a plain file"
        (d / "sneaky.json").unlink()
        for bad in ("../neg-2026-10", "Neg", "", "-x"):
            refused(v, {"proposal": bad})
        listed = {p["id"]: p for p in actions.list_proposals()}
        assert listed["neg-2026-10"]["problem"] is None and not listed["neg-2026-10"]["applied"]


def test_ads_git_ignores_the_callers_git_environment():
    fixtures()
    with AdsRepo() as repo:
        proposal(repo=repo)
        bogus = tempfile.mkdtemp()
        keys = ("GIT_DIR", "GIT_WORK_TREE", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_GLOBAL", "GIT_EXEC_PATH")
        saved = {k: os.environ.get(k) for k in keys}
        os.environ.update(GIT_DIR=bogus, GIT_WORK_TREE=bogus, GIT_CONFIG_PARAMETERS="'core.fsmonitor'='touch /x'",
                          GIT_CONFIG_GLOBAL=os.path.join(bogus, "evil.gitconfig"), GIT_EXEC_PATH=bogus)
        try:
            c = actions.ADS_VALIDATE.validate({"proposal": "neg-2026-10"})
        finally:
            for k, val in saved.items():
                if val is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = val
        assert c["commit"] == repo.head()
        env = actions.git_env()
        assert {k for k in env if k.startswith("GIT_")} == {"GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM",
                                                           "GIT_TERMINAL_PROMPT", "GIT_NO_REPLACE_OBJECTS"}
        assert env["GIT_CONFIG_GLOBAL"] == "/dev/null" and env["GIT_CONFIG_NOSYSTEM"] == "1"


class GitCalls:
    """Records every git call the app makes (actions.GIT_RUNNER), passing it through."""

    def __enter__(self):
        self.calls, self.saved = [], actions.GIT_RUNNER

        def rec(argv, **kw):
            self.calls.append((list(argv), kw))
            return self.saved(argv, **kw)
        actions.GIT_RUNNER = rec
        return self

    def __exit__(self, *exc):
        actions.GIT_RUNNER = self.saved


def test_poc3_every_git_call_is_hardened_and_runs_in_the_mirror():
    """Every git call: GIT_CONFIG_GLOBAL=/dev/null, GIT_CONFIG_NOSYSTEM=1, none of the caller's GIT_*, fsmonitor and
    hooks off, in the app's own mirror (never the working repo), and never `git archive`."""
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo)
        os.environ["GIT_CONFIG_PARAMETERS"] = "'core.pager'='evil'"
        try:
            with GitCalls() as g:
                assert real_validate(c, a, {"proposal": "neg-2026-10"}).json()["ok"]
        finally:
            os.environ.pop("GIT_CONFIG_PARAMETERS", None)
        mirror = str(actions.mirror_dir())
        assert g.calls
        fetches = [argv for argv, _ in g.calls if "fetch" in argv]
        assert len(fetches) == 2, fetches  # one at the preview, one at the run: no throttle trusts a stale ref
        for argv, kw in g.calls:
            env = kw["env"]
            assert env["GIT_CONFIG_GLOBAL"] == "/dev/null" and env["GIT_CONFIG_NOSYSTEM"] == "1", argv
            assert "GIT_CONFIG_PARAMETERS" not in env and "GIT_DIR" not in env, argv
            joined = " ".join(argv)
            assert "-c core.fsmonitor=false" in joined and "-c core.hooksPath=/dev/null" in joined, argv
            assert f"--git-dir={mirror}" in argv and str(repo.root) not in joined, argv
            assert "archive" not in argv and "--filters" not in argv and "--textconv" not in argv, argv
        for argv in fetches:
            assert "protocol.allow=never" in argv and argv[argv.index("fetch") + 1:][-2:] == \
                [str(repo.upstream), "+refs/heads/main:refs/heads/main"], argv
        assert oct(os.stat(mirror).st_mode & 0o777) == "0o700"
        assert Path(mirror).parent == Path(TMP) / "command-centre"


def test_poc3_the_fetch_url_is_github_hard_coded_and_file_urls_are_off():
    """The reviewer's p3.py: SAFE_REMOTE_RE accepted any GitHub fork, and the URL came from the working repo's
    remote.origin.url. Now the URL is a constant, the working repo's config is never read, and the production fetch
    turns the file protocol off. Only the tests' module variable (never an environment variable) redirects it."""
    assert actions.GITHUB_URL == "https://github.com/lucawetherall/londonchoralservice.git"
    assert not hasattr(actions, "SAFE_REMOTE_RE")
    saved = actions.TEST_UPSTREAM
    actions.TEST_UPSTREAM = None
    try:
        argv = actions.fetch_args()
    finally:
        actions.TEST_UPSTREAM = saved
    assert argv[-2:] == [actions.GITHUB_URL, "+refs/heads/main:refs/heads/main"]
    for pair in ("protocol.allow=never", "protocol.https.allow=always", "protocol.file.allow=never"):
        assert pair in argv and argv[argv.index(pair) - 1] == "-c", pair
    src = Path(actions.__file__).read_text()
    assert "TEST_UPSTREAM" not in "".join(re.findall(r"os\.environ[^\n]*", src))
    assert not re.search(r"environ(?:\.get)?\(?\[?[\"']LCS_[A-Z_]*(URL|UPSTREAM|GITHUB)", src)
    # an attacker's fork as the working repo's origin changes nothing: the app never reads it
    fixtures()
    with AdsRepo() as repo:
        fork = Path(tempfile.mkdtemp()) / "fork.git"
        subprocess.run(["git", "init", "-q", "--bare", str(fork)], check=True)
        repo.write("scripts/ads/helper.py", "X = 'EVIL from the fork'\n")
        repo.git("add", "-A")
        repo.commit("fork only")
        repo.git("push", "-q", str(fork), "HEAD:refs/heads/main")
        repo.git("remote", "set-url", "origin", "https://github.com/attacker/fork")
        repo.git("config", "remote.origin.url", str(fork))
        proposal(repo=repo)
        assert refused(actions.ADS_VALIDATE.validate, {"proposal": "neg-2026-10"}) == \
            "the proposal's commit isn't on main at GitHub"


def test_poc3_a_fetch_failure_fails_closed():
    fixtures()
    with AdsRepo() as repo:
        proposal(repo=repo)
        assert actions.ADS_VALIDATE.validate({"proposal": "neg-2026-10"})["commit"] == repo.head()
        actions.TEST_UPSTREAM = Path(tempfile.mkdtemp()) / "gone.git"
        assert refused(actions.ADS_VALIDATE.validate, {"proposal": "neg-2026-10"}) == \
            "couldn't verify against GitHub; nothing runs"
        # the Marketing page (no fetch) still lists it, from the mirror as last fetched
        listed = {p["id"]: p for p in actions.list_proposals()}
        assert listed["neg-2026-10"]["problem"] is None


def test_poc3_smudge_filters_and_attributes_never_apply():
    """The reviewer's p3.py: a smudge filter set in the working repo's .git/config with .git/info/attributes (on a
    sibling helper, then on the script itself) changed what `git archive` wrote. Also a filter in a global config
    the caller points GIT_CONFIG_GLOBAL at, and one written into the mirror's own config."""
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo)
        inp = {"proposal": "neg-2026-10"}
        assert "honest helper" in real_validate(c, a, inp).json()["output"]
        repo.git("config", "filter.ev.smudge", "sed s/honest/EVIL-SMUDGED/")
        (repo.root / ".git" / "info").mkdir(exist_ok=True)
        for target in ("scripts/ads/helper.py", "scripts/ads/negatives_2026_10.py", "*"):
            (repo.root / ".git" / "info" / "attributes").write_text(f"{target} filter=ev\n")
            out = real_validate(c, a, inp).json()["output"]
            assert "honest helper" in out and "EVIL" not in out, (target, out)
        evil_cfg = Path(tempfile.mkdtemp()) / "gitconfig"
        attrs = evil_cfg.with_name("attrs")
        attrs.write_text("* filter=ev\n")
        evil_cfg.write_text(f"[filter \"ev\"]\n\tsmudge = sed s/honest/EVIL-GLOBAL/\n[core]\n\tattributesFile = {attrs}\n")
        os.environ["GIT_CONFIG_GLOBAL"] = str(evil_cfg)
        try:
            out = real_validate(c, a, inp).json()["output"]
        finally:
            os.environ.pop("GIT_CONFIG_GLOBAL", None)
        assert "honest helper" in out and "EVIL" not in out, out
        cfg = actions.mirror_dir() / "config"
        cfg.write_text(cfg.read_text() + "[filter \"ev\"]\n\tsmudge = sed s/honest/EVIL-MIRROR/\n"
                       "[core]\n\tfsmonitor = touch /tmp/cc-fsmonitor-ran\n\tattributesFile = " + str(attrs) + "\n")
        (actions.mirror_dir() / "info").mkdir(exist_ok=True)
        (actions.mirror_dir() / "info" / "attributes").write_text("* filter=ev\n")
        out = real_validate(c, a, inp).json()["output"]
        assert "honest helper" in out and "EVIL" not in out, out
        assert "EVIL" not in cfg.read_text() and "fsmonitor = touch" not in cfg.read_text()
        assert not (actions.mirror_dir() / "info" / "attributes").exists()


def test_poc3_a_local_commit_and_a_moved_origin_ref_are_refused():
    """The reviewer's p3.py: a commit made in the working repo, with `git update-ref refs/remotes/origin/main`
    pointing at it, passed the ancestry check. Now ancestry is checked in the mirror against GitHub's main."""
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        blob = repo.blob()
        repo.write("scripts/ads/helper.py", "X = 'EVIL committed locally'\n")
        repo.git("add", "-A")
        repo.git("-c", "user.name=Luca Wetherall", "-c", "user.email=t@example.org", "commit", "-q", "-m", "tidy")
        repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
        repo.git("update-ref", "refs/heads/main", "HEAD")
        proposal(repo=repo, script_blob=blob)
        with Runner(Recorder()) as rec:
            r = preview(c, "ads-validate", {"proposal": "neg-2026-10"})
        assert r.status_code == 400 and r.json()["error"] == "the proposal's commit isn't on main at GitHub", r.text
        assert rec.calls == []


def test_poc3_main_rewritten_after_the_validate_refuses_the_apply():
    """The apply fetches again (no throttle): a commit dropped from GitHub's main after the validate is refused."""
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        first = repo.head()
        repo.write("scripts/ads/negatives_2026_10.py", NEG_SCRIPT + "# second\n")
        repo.git("add", "-A")
        repo.commit("second")
        repo.publish()
        proposal(repo=repo)
        inp = {"proposal": "neg-2026-10"}
        with Runner(Recorder()):
            assert run(c, a, "ads-validate", inp).json()["ok"]
        p = preview(c, "ads-apply", inp).json()
        repo.publish(first)  # main force-pushed back: the pinned commit is no longer on it
        with Runner(Recorder()) as rec:
            r = post(c, "/actions/ads-apply/run", {"input": inp, "credential": a.assert_(p["options"])})
        assert r.status_code == 400 and r.json()["error"] == "the proposal's commit isn't on main at GitHub", r.text
        assert rec.calls == []


def test_poc3_symlinks_and_submodules_are_never_written_and_blobs_are_checked():
    fixtures()
    with AdsRepo() as repo:
        os.symlink("/etc/hosts", repo.root / "scripts/ads/link.py")
        repo.git("add", "-A")
        repo.git("update-index", "--add", "--cacheinfo", f"160000,{repo.head()},scripts/ads/sub")
        repo.commit("a symlink and a submodule")
        repo.publish()
        actions.fetch_mirror()
        seen = {}
        with actions.run_folder(repo.head(), "scripts/ads/negatives_2026_10.py", repo.blob()) as root:
            files = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
            seen["link"] = (root / "scripts/ads/link.py").exists() or (root / "scripts/ads/link.py").is_symlink()
            seen["sub"] = (root / "scripts/ads/sub").exists()
            seen["modes"] = {str(p.relative_to(root)): p.stat().st_mode & 0o777 for p in root.rglob("*") if p.is_file()}
        assert not seen["link"] and not seen["sub"], files
        assert "scripts/ads/helper.py" in files and "scripts/other/tool.py" in files
        assert all(m in (0o600, 0o700) for m in seen["modes"].values()), seen["modes"]
        assert list(actions.runs_dir().iterdir()) == []
        # a pinned blob that isn't the script's at that commit: refused before anything is written
        try:
            with actions.run_folder(repo.head(), "scripts/ads/negatives_2026_10.py", "e" * 40):
                raise AssertionError("ran with the wrong blob")
        except actions.ActionError as e:
            assert e.reason == "the script at that commit isn't the pinned blob"
        assert list(actions.runs_dir().iterdir()) == []


def test_the_preview_shows_the_scripts_code_change():
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        repo.write("scripts/ads/negatives_2026_10.py", NEG_SCRIPT + "print('now it also says hello')\n")
        repo.git("add", "-A")
        commit = repo.commit("say hello")
        repo.write("scripts/other/tool.py", "print('unrelated')\n")
        repo.git("add", "-A")
        repo.commit("unrelated change")
        repo.publish()
        proposal(repo=repo)
        body = preview(c, "ads-validate", {"proposal": "neg-2026-10"}).json()
        code = body["code"]
        assert "+print('now it also says hello')" in code["diff"] and "unrelated" not in code["diff"]
        assert code["link"] == (f"https://github.com/lucawetherall/londonchoralservice/blob/{repo.head()}/"
                                "scripts/ads/negatives_2026_10.py")
        assert commit[:12] in code["head"] and "say hello" in code["head"] and "Tess Author" in code["head"]
        digest = hashlib.sha256(code["diff"].encode("utf-8")).hexdigest()
        assert digest[:16] in body["summary"] and code["link"] in body["summary"]  # the tap binds the code shown
        # a long change is capped at 6,000 characters, with a pointer to the rest
        repo.write("scripts/ads/negatives_2026_10.py", NEG_SCRIPT + "".join(f"# line {i:05d}\n" for i in range(2000)))
        repo.git("add", "-A")
        repo.commit("long")
        repo.publish()
        proposal(repo=repo)
        code = preview(c, "ads-validate", {"proposal": "neg-2026-10"}).json()["code"]
        assert len(code["diff"]) <= actions.DIFF_MAX + 200 and "characters more: open it on GitHub" in code["diff"]
        # the very first version of a script: the whole file is the change
        fresh = actions.commit_facts(repo.git("rev-list", "--max-parents=0", "HEAD").strip(),
                                     "scripts/ads/negatives_2026_10.py",
                                     repo.blob(commit=repo.git("rev-list", "--max-parents=0", "HEAD").strip()))
        assert "+import helper" in fresh["diff"]


def real_validate(c, a, inp):
    """ads-validate through the full route with the real subprocess.run (the archived script really runs)."""
    with Runner(subprocess.run):
        return run(c, a, "ads-validate", inp)


def test_poc_the_working_tree_never_changes_what_runs():
    """The reviewer's ads_poc.py: an untracked module shadowing the stdlib, an uncommitted edit to a tracked helper,
    an ignored unchecked-hash .pyc, and a file swapped between the check and the run. Each ran before; now the
    archived commit runs and none of them is seen."""
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo)
        inp = {"proposal": "neg-2026-10"}
        clean = real_validate(c, a, inp)
        assert clean.json()["ok"] and clean.json()["output"] == "validate only honest helper solo soloist vocalist", \
            clean.json()
        # 1. an untracked shadow of a stdlib module in scripts/ads/
        repo.write("scripts/ads/argparse.py", "import sys; sys.stdout.write('SHADOW argparse ran\\n'); raise SystemExit(0)\n")
        # 2. an uncommitted change to a tracked sibling helper
        repo.write("scripts/ads/helper.py", "X = 'EVIL helper (uncommitted change)'\n")
        # 3. an ignored __pycache__ holding an unchecked-hash .pyc for the helper
        import py_compile
        evil = repo.root / "evil_src.py"
        evil.write_text("X = 'EVIL from unchecked pyc'\n")
        (repo.root / "scripts/ads/__pycache__").mkdir(exist_ok=True)
        py_compile.compile(str(evil), cfile=str(repo.root / f"scripts/ads/__pycache__/helper.{sys.implementation.cache_tag}.pyc"),
                           invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        evil.unlink()
        r = real_validate(c, a, inp)
        out = r.json()["output"]
        assert r.json()["ok"] and "honest helper" in out and "SHADOW" not in out and "EVIL" not in out, out
        # 4. TOCTOU: the script swapped after the preview's checks, before the run
        p = preview(c, "ads-validate", inp).json()
        repo.write("scripts/ads/negatives_2026_10.py", "print('SWAPPED after the git check')\n")
        with Runner(subprocess.run):
            r = post(c, "/actions/ads-validate/run", {"input": inp, "credential": a.assert_(p["options"])})
        assert r.json()["ok"] and "SWAPPED" not in r.json()["output"] and "honest helper" in r.json()["output"]
        # the archive folder is gone afterwards
        assert list((Path(TMP) / "command-centre" / "runs").iterdir()) == []


def test_poc_skip_worktree_and_assume_unchanged_hide_nothing():
    """The reviewer's ads_poc2.py: an edit hidden from `git status` by --skip-worktree or --assume-unchanged."""
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo)
        inp = {"proposal": "neg-2026-10"}
        for flag in ("--skip-worktree", "--assume-unchanged"):
            repo.git("update-index", flag, "scripts/ads/negatives_2026_10.py")
            repo.write("scripts/ads/negatives_2026_10.py", f"print('MODIFIED, hidden by {flag}')\n")
            assert repo.git("status", "--porcelain") == ""
            r = real_validate(c, a, inp)
            out = r.json()["output"]
            assert r.json()["ok"] and "MODIFIED" not in out and "honest helper" in out, (flag, out)
            repo.git("update-index", flag.replace("--", "--no-"), "scripts/ads/negatives_2026_10.py")
            repo.git("checkout", "--", "scripts/ads/negatives_2026_10.py")


def test_ads_child_gets_only_the_allowlisted_environment():
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo)
        seen = {}

        def check(argv, kw):
            seen["argv"], seen["kw"] = argv, kw
            root = Path(kw["cwd"])
            seen["files"] = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
            seen["mode"] = os.stat(root).st_mode & 0o777
        os.environ["CC_SECRET"] = os.environ["SOME_TOKEN"] = os.environ["PYTHONPATH"] = "x"
        os.environ["GIT_DIR"] = "/nowhere"
        try:
            with Runner(Recorder(out=b"ok", check=check)):
                assert run(c, a, "ads-validate", {"proposal": "neg-2026-10"}).json()["ok"]
        finally:
            for k in ("CC_SECRET", "SOME_TOKEN", "PYTHONPATH", "GIT_DIR"):
                os.environ.pop(k, None)
        kw, argv = seen["kw"], seen["argv"]
        assert set(kw["env"]) <= set(actions.ADS_ENV_KEYS) | {"LCS_PRIVATE_DIR", "LCS_ADS_LOG", "PYTHONNOUSERSITE",
                                                              "PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX"}
        assert kw["env"]["LCS_PRIVATE_DIR"] == TMP and kw["env"]["LCS_ADS_LOG"] == str(repo.root / "logs" / "ads-changes.md")
        assert kw["env"]["PYTHONNOUSERSITE"] == "1" and kw["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
        root = Path(kw["cwd"])
        assert root.parent == Path(TMP) / "command-centre" / "runs" and seen["mode"] == 0o700
        assert argv[:4] == [PYX, "-E", "-s", "-B"] and argv[4] == "-X" and argv[5].startswith("pycache_prefix=")
        assert argv[6] == str(root / "scripts/ads/negatives_2026_10.py")
        assert argv[7:] == ["solo", "soloist", "vocalist", "--validate-only"]
        assert "scripts/ads/negatives_2026_10.py" in seen["files"] and "scripts/other/tool.py" in seen["files"]
        assert not any(f.startswith(".git") or "__pycache__" in f for f in seen["files"]), seen["files"]
        assert not root.exists()


def test_ads_validate_then_apply_bound_to_the_output():
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo)
        inp = {"proposal": "neg-2026-10"}
        # apply before any validate: refused, nothing runs
        r = preview(c, "ads-apply", inp)
        assert r.status_code == 409 and "validate this change set first" in r.json()["error"]
        with Runner(Recorder(out=b"Validated 3 operations (validate_only)\n")) as rec:
            r = run(c, a, "ads-validate", inp)
        assert r.status_code == 200 and r.json()["ok"], r.text
        assert r.json()["next"] == {"action": "ads-apply", "input": inp, "label": "Apply this change set"}
        assert rec.calls[0][0][-1] == "--validate-only"
        out_sha = hashlib.sha256(b"Validated 3 operations (validate_only)\n").hexdigest()
        p = preview(c, "ads-apply", inp).json()
        assert out_sha[:16] in p["summary"] and p["command"].endswith("negatives_2026_10.py solo soloist vocalist --apply")
        assert "daily cap (£5" in p["summary"] and repo.head()[:12] in p["summary"]
        # the apply's assertion is bound to that output: a second validate with other output changes the summary
        with Runner(Recorder(out=b"Validated 4 operations\n")):
            run(c, a, "ads-validate", inp)
        with Runner(Recorder(out=b"Applied and logged\n")) as rec:
            r = post(c, "/actions/ads-apply/run", {"input": inp, "credential": a.assert_(p["options"])})
            assert r.status_code == 403 and r.json()["error"] == "wrong action" and rec.calls == []
            r = run(c, a, "ads-apply", inp)
        assert r.status_code == 200 and r.json()["ok"], r.text
        argv, kw = rec.calls[0]
        assert argv[-4:] == ["solo", "soloist", "vocalist", "--apply"] and argv[:4] == [PYX, "-E", "-s", "-B"]
        applied = json.loads((Path(TMP) / "command-centre" / "proposals" / "neg-2026-10.applied").read_text())
        assert applied["commit"] == repo.head() and applied["blob"] == repo.blob()
        assert applied["args"] == ["solo", "soloist", "vocalist"] and applied["login"] == LOGIN
        assert applied["passkey"] == b64(a.cred_id)
        raw_audit = (Path(TMP) / "command-centre" / "audit.jsonl").read_bytes().rstrip(b"\n").split(b"\n")
        assert applied["audit_sha256"] == hashlib.sha256(raw_audit[-1]).hexdigest()
        # applied: neither step is offered again
        assert preview(c, "ads-validate", inp).json()["error"] == "already applied"
        assert preview(c, "ads-apply", inp).json()["error"] == "already applied"
        # the same blob and args under another proposal id: refused too
        proposal(pid="neg-again", repo=repo)
        assert preview(c, "ads-validate", {"proposal": "neg-again"}).json()["error"] == \
            "this script with these arguments was already applied"
        # other args are a different change
        proposal(pid="neg-other", repo=repo, args=["opera"])
        assert preview(c, "ads-validate", {"proposal": "neg-other"}).status_code == 200
        listed = {p["id"]: p for p in actions.list_proposals()}
        assert listed["neg-again"]["problem"] == "this script with these arguments was already applied"


def _apply(c, a, pid, repo, args):
    """Validate then apply a proposal for `repo`'s script with these args; asserts it goes through."""
    proposal(pid=pid, repo=repo, args=args)
    inp = {"proposal": pid}
    with Runner(Recorder()):
        assert run(c, a, "ads-validate", inp).json()["ok"]
    with Runner(Recorder(out=b"Applied and logged\n")):
        r = run(c, a, "ads-apply", inp)
    assert r.status_code == 200 and r.json()["ok"], r.text


def test_a_campaign_can_return_to_an_earlier_amount_but_not_replay_the_latest_one():
    """already_applied only blocks a replay of the MOST RECENT applied change for the same script and first
    argument (the campaign): a budget that goes 4.00 -> 5.00 -> 4.00 again is fine, but repeating the 5.00 that
    was just applied is refused."""
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        _apply(c, a, "bud-1", repo, ["24295921372", "4.00"])
        _apply(c, a, "bud-2", repo, ["24295921372", "5.00"])
        # back to the earlier amount: allowed, since the latest change for this campaign was 5.00, not 4.00
        proposal(pid="bud-3", repo=repo, args=["24295921372", "4.00"])
        assert preview(c, "ads-validate", {"proposal": "bud-3"}).status_code == 200
        _apply(c, a, "bud-3", repo, ["24295921372", "4.00"])
        # immediately replaying the amount just applied (4.00 again) is refused
        proposal(pid="bud-4", repo=repo, args=["24295921372", "4.00"])
        assert preview(c, "ads-validate", {"proposal": "bud-4"}).json()["error"] == \
            "this script with these arguments was already applied"
        # a different campaign (first argument) is unaffected by any of the above
        proposal(pid="bud-other", repo=repo, args=["999", "4.00"])
        assert preview(c, "ads-validate", {"proposal": "bud-other"}).status_code == 200


def test_ads_apply_runs_from_the_validated_commit_only():
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo)
        inp = {"proposal": "neg-2026-10"}
        with Runner(Recorder(code=1, out=b"GoogleAdsException\n")):
            assert run(c, a, "ads-validate", inp).json()["next"] is None
        assert preview(c, "ads-apply", inp).status_code == 409
        with Runner(Recorder()):
            run(c, a, "ads-validate", inp)
        repo.write("scripts/ads/negatives_2026_10.py", NEG_SCRIPT + "print('now it spends')\n")
        repo.git("add", "-A")
        repo.commit("changed after validation")
        repo.publish()
        proposal(repo=repo)  # re-pinned to the new commit: not the one validated
        r = preview(c, "ads-apply", inp)
        assert r.status_code == 409 and "changed since it was validated" in r.json()["error"]


def test_old_scripts_fail_the_validate_step_at_argparse():
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo, script_path="scripts/ads/old_style.py", args=[])
        r = real_validate(c, a, {"proposal": "neg-2026-10"})
        body = r.json()
        assert body["ok"] is False and body["exit_code"] == 2 and "unrecognized arguments: --validate-only" in body["output"]
        assert body["next"] is None and "old script ran" not in body["output"]
        assert preview(c, "ads-apply", {"proposal": "neg-2026-10"}).status_code == 409


def test_one_apply_per_validate_even_racing():
    """The validate record is popped atomically when the apply starts: a second apply finds nothing."""
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo)
        inp = {"proposal": "neg-2026-10"}
        with Runner(Recorder()):
            run(c, a, "ads-validate", inp)
        p1 = preview(c, "ads-apply", inp).json()
        p2 = preview(c, "ads-apply", inp).json()
        with Runner(Recorder(code=1, out=b"REJECTED\n")) as rec:  # a failed apply writes no .applied
            r1 = post(c, "/actions/ads-apply/run", {"input": inp, "credential": a.assert_(p1["options"])})
            r2 = post(c, "/actions/ads-apply/run", {"input": inp, "credential": a.assert_(p2["options"])})
        assert r1.json()["ok"] is False and len(rec.calls) == 1
        assert r2.status_code == 409, r2.text
        assert audit_lines()[-1]["result"].startswith("refused: validate")


def test_an_apply_whose_record_cant_be_saved_warns_and_is_never_applied_again():
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo)
        inp = {"proposal": "neg-2026-10"}
        with Runner(Recorder()):
            run(c, a, "ads-validate", inp)
        real = actions.write_private

        def broken(path, payload, exclusive=False):
            if str(path).endswith(".applied"):
                raise PermissionError("disk")
            return real(path, payload, exclusive)
        actions.write_private = broken
        try:
            with Runner(Recorder(out=b"Applied and logged\n")) as rec:
                r = run(c, a, "ads-apply", inp)
        finally:
            actions.write_private = real
        body = r.json()
        assert r.status_code == 200 and body["ok"] and len(rec.calls) == 1, body
        assert body["output"].startswith("applied, but the record couldn't be saved: DO NOT re-apply"), body["output"]
        assert "Applied and logged" in body["output"]
        assert not actions.applied_path("neg-2026-10").exists()
        # until the app restarts, neither this proposal nor the same blob and args under another id runs again
        assert preview(c, "ads-validate", inp).json()["error"] == "already applied"
        proposal(pid="neg-again", repo=repo)
        assert preview(c, "ads-validate", {"proposal": "neg-again"}).json()["error"] == \
            "this script with these arguments was already applied"
        assert {p["id"]: p for p in actions.list_proposals()}["neg-again"]["problem"] == \
            "this script with these arguments was already applied"
        actions.forget_unrecorded_applies()


def test_ads_output_is_head_and_tail_unmasked():
    body = "".join(f"line {i:05d} campaign 23739971001 £4.50\n" for i in range(1000))
    shown = actions.head_and_tail(body + "refresh_token=1//0gAbCdEfGh\n")
    assert shown.startswith("line 00000 campaign 23739971001") and "23739971001 £4.50" in shown
    assert "characters left out" in shown and "0gAbCdEfGh" not in shown
    head, tail = shown.split("characters left out")
    assert len(head) < actions.ADS_HEAD + 40 and len(tail) < actions.ADS_TAIL + 40
    assert actions.head_and_tail("short 12345678") == "short 12345678"


# ---------------------------------------------------------------- locking, refusals, the audit chain


def test_validation_runs_under_the_action_lock_and_refusals_are_audited():
    c, a, _ = setup()
    seen = []
    real = actions.RESOLVE_HAND_CHECK.validate

    def watching(raw):
        seen.append(actions._RUN_LOCK.locked())
        return real(raw)
    import dataclasses as dc
    defn = dc.replace(actions.RESOLVE_HAND_CHECK, validate=watching)
    inp = {"ref": "2111", "choice": "refunded", "date": D}
    with Runner(Recorder()):
        try:
            actions.run_action(defn, inp, {"login": LOGIN})
        except actions.ActionError:
            pass
    assert seen == [True], seen
    # a refusal at the run step (bad input) is logged with the action's name and a hash of the input
    bad = {"ref": "9999", "choice": "refunded", "date": D}
    r = post(c, "/actions/resolve-hand-check/run", {"input": bad})
    assert r.status_code == 400 and r.json()["error"] == "unknown booking"
    last = audit_lines()[-1]
    assert last["action"] == "resolve-hand-check" and last["result"] == "refused: unknown booking"
    assert last["input_sha256"] == actions.input_sha256(bad) and "input" not in last and "9999" not in json.dumps(last)
    # busy: another action holds the lock
    assert actions._RUN_LOCK.acquire(timeout=1)
    saved = actions.RUN_WAIT
    actions.RUN_WAIT = 0.05
    try:
        r = run(c, a, "resolve-hand-check", inp)
        assert r.status_code == 409
        assert audit_lines()[-1]["result"] == "refused: another action is running"
        # refresh-data has its own lock: it still runs
        with Runner(Recorder(out=b"wrote dashboard\n")):
            r = post(c, "/actions/refresh-data/run", {"input": {}})
        assert r.status_code == 200 and r.json()["ok"], r.text
    finally:
        actions.RUN_WAIT = saved
        actions._RUN_LOCK.release()


def test_the_applied_check_is_made_under_the_lock():
    """An apply that was validated, then applied by another path before this run takes the lock, is refused."""
    c, a, _ = setup()
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo)
        inp = {"proposal": "neg-2026-10"}
        with Runner(Recorder()):
            run(c, a, "ads-validate", inp)
        p = preview(c, "ads-apply", inp).json()
        actions.write_private(actions.applied_path("neg-2026-10"), {"blob": repo.blob(), "args": []})
        with Runner(Recorder()) as rec:
            r = post(c, "/actions/ads-apply/run", {"input": inp, "credential": a.assert_(p["options"])})
        assert r.status_code == 400 and r.json()["error"] == "already applied" and rec.calls == []
        assert audit_lines()[-1]["result"] == "refused: already applied"


def test_the_audit_log_is_hash_chained():
    c, a, _ = setup()
    with Runner(Recorder(out=b"ok")):
        run(c, a, "resolve-hand-check", {"ref": "2111", "choice": "refunded", "date": D})
        run(c, a, "singer-confirm", {"invoice": models.invoice_key(MSG)})
    lines = audit_lines()
    assert len(lines) == 4 and lines[0]["prev"] == actions.GENESIS
    raw = (Path(TMP) / "command-centre" / "audit.jsonl").read_bytes().split(b"\n")
    for before, entry in zip(raw, lines[1:]):
        assert entry["prev"] == hashlib.sha256(before).hexdigest()
    assert actions.verify_audit() == []
    path = Path(TMP) / "command-centre" / "audit.jsonl"
    good = path.read_bytes()
    path.write_bytes(good.replace(b'"result": "ok"', b'"result": "OK"', 1))  # an edited line breaks the next one
    assert actions.verify_audit() != []
    path.write_bytes(b"\n".join(good.split(b"\n")[1:]))  # a removed first line
    assert actions.verify_audit() == [1]
    path.write_bytes(good + b"not json\n")  # an appended stray line, then a real entry chains onto it
    actions.write_audit("x", "y", {"login": LOGIN}, "ok")
    assert actions.verify_audit() == [5]
    path.write_bytes(good[:-1])  # a file that doesn't end with a newline still gets a whole new line
    actions.write_audit("x", "y", {"login": LOGIN}, "ok")
    assert actions.verify_audit() == [] and audit_lines()[-1]["action"] == "x"


def test_a_failed_audit_write_after_a_run_is_reported():
    c, a, _ = setup()
    real = actions.write_audit
    calls = []

    def flaky(name, summary, user, result, **extra):
        calls.append(result)
        if result != "started":
            raise PermissionError("disk")
        return real(name, summary, user, result, **extra)
    actions.write_audit = flaky
    try:
        with Runner(Recorder(out=b"2111: note added\n")) as rec:
            r = run(c, a, "resolve-hand-check", {"ref": "2111", "choice": "refunded", "date": D})
    finally:
        actions.write_audit = real
    assert r.status_code == 200 and len(rec.calls) == 1 and calls == ["started", "ok"]
    assert r.json()["output"].startswith("ran, but the audit write failed (PermissionError)")
    assert "2111: note added" in r.json()["output"]


def test_the_hand_check_child_gets_the_private_dir_and_no_ledger_override():
    c, a, _ = setup()
    with Runner(Recorder()) as rec:
        run(c, a, "resolve-hand-check", {"ref": "2111", "choice": "refunded", "date": D})
        run(c, a, "singer-settled", {"invoice": models.invoice_key(MSG), "date": D})
    hand, singer = rec.calls[0][1]["env"], rec.calls[1][1]["env"]
    assert hand["LCS_PRIVATE_DIR"] == TMP and "LCS_BOOKINGS_CSV" not in hand
    assert singer["LCS_PRIVATE_DIR"] == TMP
    # a ledger moved elsewhere by LCS_BOOKINGS_CSV: the app won't ask check_payments to write beside the nonce
    saved = cp.LEDGER
    try:
        cp.LEDGER = Path(tempfile.mkdtemp()) / "bookings.csv"
        assert refused(actions.RESOLVE_HAND_CHECK.validate, {"ref": "2111", "choice": "refunded", "date": D}) == \
            "the ledger isn't the one in the private folder (LCS_BOOKINGS_CSV moves it)"
    finally:
        cp.LEDGER = saved


def test_real_singer_confirm_through_the_route_is_bound_to_the_fingerprint():
    c, a, _ = setup()
    key = models.invoice_key(MSG)
    r = run(c, a, "singer-confirm", {"invoice": key})
    assert r.status_code == 200 and r.json()["ok"], r.json()
    row = next(x for x in lm.read_csv(si.STORE) if x["message_id"] == MSG)
    assert row["bank_confirmed"] == "yes"
    # the details changed after the preview: the rebuilt summary no longer matches the signed one
    fixtures()
    p = preview(c, "singer-confirm", {"invoice": key}).json()
    rows = lm.read_csv(si.STORE)
    for x in rows:
        if x["message_id"] == MSG:
            x["bank_fp"] = "ffffffff00000000"
    write_csv(str(si.STORE), si.COLUMNS, rows)
    with Runner(Recorder()) as rec:
        r = post(c, "/actions/singer-confirm/run", {"input": {"invoice": key}, "credential": a.assert_(p["options"])})
    assert r.status_code == 403 and r.json()["error"] == "wrong action" and rec.calls == []


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
        "backup-now": {},
    }
    write_config(backup={"recipient": "age1test", "target": TMP})
    seen = set()
    for name, inp in samples.items():
        defn = actions.REGISTRY[name]
        cmd = claude_form(defn.argv(defn.validate(inp)))
        on = allowlist.allowed(cmd, pats)
        seen.add(name)
        if name in SAFE_ON_ALLOWLIST:
            continue
        assert not on, f"{name}: {cmd} is allowlisted"
    with AdsRepo() as repo:
        proposal(repo=repo)
        for name, flag in (("ads-validate", "--validate-only"), ("ads-apply", "--apply")):
            for cmd in (f"{allowlist.PY} scripts/ads/negatives_2026_10.py solo {flag}",
                        f"{allowlist.PY} -E -s -B scripts/ads/negatives_2026_10.py solo {flag}",
                        f"{allowlist.PY} scripts/ads/set_budget.py 111 4.50 {flag}"):
                assert not allowlist.allowed(cmd, pats), cmd
            seen.add(name)
    seen |= {"approve-books-import", "books-import-done", "todo-tick", "push-subscribe", "push-unsubscribe",
             "draft-mark"}  # no subprocess
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
    clear_applied()
    with AdsRepo() as repo:
        proposal(repo=repo)
        proposal(pid="bad-one", mode=0o644, repo=repo)
        out = page(c, "/marketing")
    assert "Claude&#39;s description:" in out or "Claude's description:" in out
    assert "Add 3 negatives" in out and 'data-action="ads-validate"' in out and 'value="neg-2026-10"' in out
    assert "the proposal file must be mode 600" in out
    assert 'data-action="ads-apply"' not in out  # only after a validate
    (Path(TMP) / "command-centre" / "proposals" / "bad-one.json").unlink()
    (Path(TMP) / "command-centre" / "proposals" / "neg-2026-10.json").unlink()


def test_activity_shows_the_audit_chain_status():
    c, a, _ = setup()
    with Runner(Recorder(out=b"ok")):
        run(c, a, "resolve-hand-check", {"ref": "2111", "choice": "refunded", "date": D})
    path = Path(TMP) / "command-centre" / "audit.jsonl"
    lines = path.read_bytes().rstrip(b"\n").split(b"\n")
    st = actions.audit_status()
    assert st == {"ok": True, "bad": [], "lines": len(lines), "last": hashlib.sha256(lines[-1]).hexdigest()}
    out = page(c, "/activity")
    assert "chain intact" in out and f"{len(lines)} lines" in out and st["last"][:16] in out
    path.write_bytes(path.read_bytes().replace(b'"result": "started"', b'"result": "STARTED"', 1))  # line 1 edited
    out = page(c, "/activity")
    assert "chain broken" in out and re.search(r"at line\s+2\b", out), out


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


# ---------------------------------------------------------------- short by transfer fees (owner decision, 28 Sep 2026)


def days_ago(n):
    return (TODAY - datetime.timedelta(days=n)).isoformat()


FEE_ROW = {"booking_ref": "2408", "invoice_date": days_ago(40), "event_date": (TODAY + datetime.timedelta(days=20)).isoformat(),
           "client_name": "Bea Feeworthy", "client_email": "bea@example.org", "occasion": "Wedding", "ensemble": "Octet",
           "value_gbp": "950", "notes": f"deposit seen {days_ago(35)} (Starling)"}


class FeeBank:
    """A GET-only Starling stand-in whose feed holds 2408's two payments: £937.60 of £950, £12.40 lost to fees."""

    def account(self):
        return {"accountUid": "acc-1", "defaultCategory": "cat-1"}

    def get(self, path):
        return {"clearedBalance": {"minorUnits": 100000}, "effectiveBalance": {"minorUnits": 100000}}

    def feed(self, since, until, direction):
        return [{"direction": "IN", "amount": {"minorUnits": m}, "transactionTime": f"{d}T10:00:00Z",
                 "reference": f"INV {ref}", "counterPartyName": who}
                for ref, who, m, d in (("2408", "B FEEWORTHY", 47500, days_ago(35)),
                                       ("2408", "B FEEWORTHY", 46260, days_ago(2)),
                                       # a past booking's payments (only in the ledger for one test)
                                       ("0909", "C PASTFIELD", 30000, days_ago(50)),
                                       ("0909", "C PASTFIELD", 29100, days_ago(10)))]


def fee_setup(client_factory=FeeBank):
    c, a, clock = setup(client_factory=client_factory)
    rows = lm.read_csv(cp.LEDGER)
    write_csv(os.path.join(TMP, "bookings.csv"), LEDGER_COLS, rows + [FEE_ROW])
    return c, a, clock


FEE_INPUT = {"ref": "2408", "choice": "short-by-fees", "date": D, "amount": "12.40"}


def test_short_by_fees_preview_and_argv():
    c, _, _ = fee_setup()
    act = actions.RESOLVE_HAND_CHECK
    cleaned = act.validate(FEE_INPUT)
    assert act.argv(cleaned) == [PYX, CHECK, "--note", "2408", f"short by fees £12.40 accepted {D}", "--owner"]
    s = act.preview(cleaned)
    for part in ("booking 2408 (Bea)", "£937.60 received of £950.00", "short by £12.40 in transfer fees",
                 "will read paid in full", f"\"short by fees £12.40 accepted {D} (owner)\""):
        assert part in s, (part, s)
    assert "Feeworthy" not in s and "example.org" not in s
    assert cleaned["input"] == FEE_INPUT
    assert act.argv(act.validate(dict(FEE_INPUT, amount="12.4")))[4] == f"short by fees £12.40 accepted {D}"
    assert act.argv(act.validate(dict(FEE_INPUT, amount="12.41")))[4] == f"short by fees £12.40 accepted {D}"  # 1p
    r = preview(c, "resolve-hand-check", FEE_INPUT)
    assert r.status_code == 200 and r.json()["summary"] == s, r.text
    # the owner-only phrase stays out of the ordinary select
    assert ("short-by-fees", "short by transfer fees") not in create_app.__globals__["HAND_CHOICES"]


def test_short_by_fees_refusals():
    fee_setup()
    v = actions.RESOLVE_HAND_CHECK.validate
    reasons = {
        "25.01": "the amount must be more than £0 and at most £25.00",
        "30": "the amount must be more than £0 and at most £25.00",
        "0": "the amount must be more than £0 and at most £25.00",
        "12.42": "the amount isn't that booking's balance (£12.40)",
        "5": "the amount isn't that booking's balance (£12.40)",
    }
    for amount, reason in reasons.items():
        assert refused(v, dict(FEE_INPUT, amount=amount)) == reason, amount
    for amount in ("abc", "12.400", "-12.40", "£12.40", "1e1", "12,40", "112.40", " "):
        assert refused(v, dict(FEE_INPUT, amount=amount)), amount
    assert refused(v, {k: x for k, x in FEE_INPUT.items() if k != "amount"}) == "amount is required"
    assert refused(v, dict(FEE_INPUT, amount=12.4)) == "bad amount"  # a number, not a form string
    assert refused(v, dict(FEE_INPUT, choice="paid-in-full")) == "an amount goes only with short by transfer fees"
    assert refused(v, dict(FEE_INPUT, date=days_ago(3))) == f"the date is before the last payment ({days_ago(2)})"
    assert refused(v, dict(FEE_INPUT, ref="2111", amount="5")) == "that booking has no part-paid balance to accept"
    assert refused(v, dict(FEE_INPUT, ref="0310")) == "that booking has no part-paid balance to accept"
    fee_setup(client_factory=lambda: None)  # no bank: nothing to check the shortfall against
    assert refused(v, FEE_INPUT) == "the bank wasn't checked: can't confirm the shortfall"


def test_short_by_fees_through_the_real_script_reads_paid_in_full():
    c, a, _ = fee_setup()
    r = run(c, a, "resolve-hand-check", FEE_INPUT)
    assert r.status_code == 200 and r.json()["ok"] is True, r.text
    notes = ledger_notes("2408")
    assert notes == f"{FEE_ROW['notes']}; short by fees £12.40 accepted {D} (owner)", notes
    row = next(x for x in lm.read_csv(cp.LEDGER) if x["booking_ref"] == "2408")
    got = cp.collect(FeeBank(), [row], TODAY)
    assert [x["state"] for _, _, x in got] == ["PAID_IN_FULL"], got
    assessed = got[0][2]
    assert assessed["balance"] == 0 and assessed["fees"] == 12.4 and assessed["action"] != "balance_reminder"
    assert assessed["record_in_books"][-1] == [days_ago(2), 462.6, 12.4], assessed


def test_booking_page_offers_short_by_fees_only_for_a_small_part_paid_balance():
    c, _, _ = fee_setup()
    out = page(c, "/bookings/2408")
    assert 'name="choice" value="short-by-fees"' in out and 'name="amount" value="12.40"' in out, out
    assert "Short by transfer fees (£12.40)" in out
    assert 'value="short-by-fees"' not in page(c, "/bookings/2111")  # nothing received: no shortfall to accept
    c, _, _ = fee_setup(client_factory=lambda: None)
    assert 'value="short-by-fees"' not in page(c, "/bookings/2408")  # bank not checked


def test_hand_check_list_offers_short_by_fees_on_a_past_part_paid_booking():
    c, _, _ = fee_setup()
    rows = lm.read_csv(cp.LEDGER)
    past = dict(FEE_ROW, booking_ref="0909", invoice_date=days_ago(60), event_date=days_ago(5), value_gbp="600",
                notes="", client_name="Cy Pastfield", client_email="cy@example.org")
    write_csv(os.path.join(TMP, "bookings.csv"), LEDGER_COLS, rows + [past])
    for path in ("/money", "/"):
        out = page(c, path)
        assert "/bookings/0909" in out and 'name="amount" value="9.00"' in out, path
        assert 'name="amount" value="12.40"' not in out, path  # 2408 isn't a hand check
    cleaned = actions.RESOLVE_HAND_CHECK.validate({"ref": "0909", "choice": "short-by-fees", "date": D, "amount": "9"})
    assert cleaned["phrase"] == f"short by fees £9.00 accepted {D}"


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
