#!/usr/bin/env python3
"""Tests for the Command Centre's encrypted backups (phase 5): scripts/reports/cc_backup.py, the backup-now action
and the Health page's backup line.

Stdlib runner, a temp LCS_PRIVATE_DIR as the private folder, a temp target folder and a test-only age key made
here. Never touches ~/lcs-private, iCloud Drive or a real key.
"""
import datetime, io, json, os, socket, subprocess, sys, tarfile, tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

TMP = tempfile.mkdtemp()
TARGET = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
os.environ.pop("CC_DEV_LOGIN", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
import pyrage  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

import cc_backup  # noqa: E402
from command_centre import actions, auth, sources  # noqa: E402
from command_centre.app import create_app  # noqa: E402

LONDON = ZoneInfo("Europe/London")
LOGIN = "owner@example.org"
HOST = "mac.example-tailnet.ts.net"
ORIGIN = f"https://{HOST}"
HEADERS = {"Tailscale-User-Login": LOGIN, "Tailscale-User-Name": "Owner"}
SCRIPT = os.path.join(ROOT, "scripts", "reports", "cc_backup.py")


def write(rel, text="x"):
    p = Path(TMP) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def fresh(recipient=None):
    for base in (TMP, TARGET):
        for dirpath, dirnames, filenames in os.walk(base, topdown=False):
            for f in filenames:
                os.remove(os.path.join(dirpath, f))
            for d in dirnames:
                p = os.path.join(dirpath, d)
                (os.remove if os.path.islink(p) else os.rmdir)(p)
    cfg = {"allowed_logins": [LOGIN], "origin": ORIGIN, "rp_id": HOST, "passkeys": [],
           "backup": {"target": TARGET}}
    if recipient:
        cfg["backup"]["recipient"] = recipient
    auth.save_config(cfg)
    write("bookings.csv", "booking_ref\n2111\n")
    write("fingerprint.key", "k")
    write("reports/2026-09-21.txt", "report")
    write("command-centre/audit.jsonl", "{}\n")
    write("command-centre/runs/r1/scripts/x.py", "run folder")
    write("command-centre/cache/calendar.json", "[]")
    write("command-centre/mirror.git/HEAD", "ref")
    write("command-centre/backups/old.age", "no")


def make_key():
    ident = pyrage.x25519.Identity.generate()
    return ident, str(ident.to_public())


def listing(path, ident):
    with open(path, "rb") as f:
        plain = pyrage.decrypt(f.read(), [ident])
    with tarfile.open(fileobj=io.BytesIO(plain), mode="r:gz") as tar:
        return {m.name: (tar.extractfile(m).read() if m.isfile() else None) for m in tar.getmembers()}


def test_round_trip_with_excludes_and_mode():
    ident, rcpt = make_key()
    fresh(rcpt)
    sock_path = os.path.join(TMP, "command-centre", "s.sock")
    s = socket.socket(socket.AF_UNIX)
    s.bind(sock_path)
    try:
        now = datetime.datetime(2026, 9, 28, 2, 30, tzinfo=LONDON)
        r = cc_backup.run(now=now)
    finally:
        s.close()
    assert r["name"] == "lcs-backup-20260928-023000.tar.gz.age"
    path = Path(TARGET) / r["name"]
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert not list(Path(TARGET).glob(".*part"))
    raw = path.read_bytes()
    assert b"booking_ref" not in raw and raw.startswith(b"age-encryption.org/v1")
    names = listing(path, ident)
    assert names["bookings.csv"] == b"booking_ref\n2111\n" and "fingerprint.key" in names
    assert "reports/2026-09-21.txt" in names and "command-centre/audit.jsonl" in names
    for gone in ("command-centre/runs", "command-centre/cache", "command-centre/mirror.git", "command-centre/backups",
                 "command-centre/s.sock"):
        assert not any(n == gone or n.startswith(gone + "/") for n in names), gone
    assert r["skipped"] == 1  # the socket
    state = json.loads((Path(TMP) / "command-centre" / "backup-state.json").read_text())
    assert state["name"] == r["name"] and state["size"] == len(raw) and len(state["sha256"]) == 64
    # another key can't open it
    other, _ = make_key()
    try:
        listing(path, other)
    except Exception:
        pass
    else:
        raise AssertionError("opened with the wrong key")


def test_a_target_inside_the_private_folder_is_left_out():
    ident, rcpt = make_key()
    fresh(rcpt)
    inside = Path(TMP) / "my-backups"
    cfg = auth.load_config()
    cfg["backup"]["target"] = str(inside)
    auth.save_config(cfg)
    cc_backup.run(now=datetime.datetime(2026, 9, 28, 2, 30, tzinfo=LONDON))
    second = cc_backup.run(now=datetime.datetime(2026, 9, 29, 2, 30, tzinfo=LONDON))
    names = listing(inside / second["name"], ident)
    assert not any(n.startswith("my-backups") for n in names), names


def test_retention_keeps_14_days_and_only_touches_its_own_files():
    ident, rcpt = make_key()
    fresh(rcpt)
    old = Path(TARGET) / "lcs-backup-20260901-023000.tar.gz.age"
    edge = Path(TARGET) / "lcs-backup-20260914-030000.tar.gz.age"
    other = Path(TARGET) / "notes.txt"
    lookalike = Path(TARGET) / "lcs-backup-20200101-000000.tar.gz.age.keep"
    for p in (old, edge, other, lookalike):
        p.write_text("x")
    os.symlink(other, Path(TARGET) / "lcs-backup-20200102-000000.tar.gz.age")
    r = cc_backup.run(now=datetime.datetime(2026, 9, 28, 2, 30, tzinfo=LONDON))
    assert r["removed"] == 1
    assert not old.exists() and edge.exists() and other.exists() and lookalike.exists()
    assert (Path(TARGET) / "lcs-backup-20200102-000000.tar.gz.age").is_symlink()
    assert (Path(TARGET) / r["name"]).exists()


def test_stale_part_files_are_pruned_after_a_day():
    ident, rcpt = make_key()
    fresh(rcpt)
    now = datetime.datetime(2026, 9, 28, 2, 30, tzinfo=LONDON)
    old = Path(TARGET) / ".lcs-backup-20260926-023000.tar.gz.age.0123abcd.part"
    new = Path(TARGET) / ".lcs-backup-20260928-011500.tar.gz.age.89abcdef.part"
    other = Path(TARGET) / ".something.part"
    for f, hours in ((old, 49), (new, 2), (other, 100)):
        f.write_text("x")
        t = (now - datetime.timedelta(hours=hours)).timestamp()
        os.utime(f, (t, t))
    cc_backup.run(now=now)
    assert not old.exists() and new.exists() and other.exists()


class NoTempFiles:
    """Stands in for the tempfile module: any temp file is a failure (the plaintext must never be on disk)."""

    def __getattr__(self, name):
        raise AssertionError(f"tempfile.{name} used")


def test_the_plaintext_never_touches_disk_and_a_failure_leaves_nothing():
    ident, rcpt = make_key()
    fresh(rcpt)
    saved_tempfile = getattr(cc_backup, "tempfile", None)
    cc_backup.tempfile = NoTempFiles()
    real_open = os.open
    opened = []

    def watching_open(path, flags, *a, **kw):
        opened.append(str(path))
        return real_open(path, flags, *a, **kw)

    os.open = watching_open
    try:
        r = cc_backup.run(now=datetime.datetime(2026, 9, 28, 2, 30, tzinfo=LONDON))
        written = [p for p in opened if p.startswith(os.path.realpath(TARGET)) or p.startswith(TARGET)]
        assert all(p.endswith(".part") for p in written), written  # only the ciphertext's .part is written
        path, names = cc_backup.verify(str(ident), Path(TARGET))
        assert "bookings.csv" in names and os.path.basename(path) == r["name"]
    finally:
        os.open = real_open
        if saved_tempfile is not None:
            cc_backup.tempfile = saved_tempfile
        else:
            del cc_backup.tempfile
    # the archive side fails part-way: nothing is left in the target, the error comes through
    real_build = cc_backup.build_archive

    def failing_build(src, fileobj, target=None, stream=False):
        fileobj.write(b"\x1f\x8b" + b"partial" * 1000)
        raise OSError("disk went away")

    cc_backup.build_archive = failing_build
    before = sorted(os.listdir(TARGET))
    try:
        cc_backup.run(now=datetime.datetime(2026, 9, 28, 3, 30, tzinfo=LONDON))
    except OSError as e:
        assert "disk went away" in str(e)
    else:
        raise AssertionError("a failed archive was kept")
    finally:
        cc_backup.build_archive = real_build
    assert sorted(os.listdir(TARGET)) == before
    # the age side fails: the writer thread isn't left blocked, and nothing is kept
    real_pyrage = cc_backup.pyrage

    class FailingAge:
        x25519 = pyrage.x25519

        @staticmethod
        def encrypt_io(reader, writer, recipients):
            reader.read(10)
            raise RuntimeError("age failed")

    cc_backup.pyrage = lambda: FailingAge
    try:
        cc_backup.run(now=datetime.datetime(2026, 9, 28, 4, 30, tzinfo=LONDON))
    except RuntimeError as e:
        assert "age failed" in str(e)
    else:
        raise AssertionError("a failed encryption was kept")
    finally:
        cc_backup.pyrage = real_pyrage
    assert sorted(os.listdir(TARGET)) == before


def test_run_needs_a_key():
    fresh()
    try:
        cc_backup.run()
    except cc_backup.BackupError as e:
        assert "init" in str(e)
    else:
        raise AssertionError("ran without a key")


def all_files(*bases):
    for base in bases:
        for dirpath, _, filenames in os.walk(base):
            for f in filenames:
                yield os.path.join(dirpath, f)


def run_tty(args, env):
    """Run the script with stdout and stderr on a pseudo-terminal (as in Terminal). Returns (code, output)."""
    import pty, select
    master, slave = pty.openpty()
    proc = subprocess.Popen([sys.executable, SCRIPT, *args], stdin=subprocess.DEVNULL, stdout=slave, stderr=slave,
                            env=env)
    os.close(slave)
    out = b""
    while True:
        ready, _, _ = select.select([master], [], [], 30)
        if not ready:
            proc.kill()
            raise AssertionError("no output from the script")
        try:
            chunk = os.read(master, 4096)
        except OSError:  # EIO: the child closed the terminal
            break
        if not chunk:
            break
        out += chunk
    os.close(master)
    return proc.wait(timeout=30), out.decode().replace("\r\n", "\n")


def test_init_refuses_without_a_terminal():
    fresh()
    env = dict(os.environ, HOME=tempfile.mkdtemp())
    for how in ({"capture_output": True}, {"stdout": subprocess.PIPE, "stderr": subprocess.DEVNULL}):
        r = subprocess.run([sys.executable, SCRIPT, "init"], text=True, env=env, **how)
        assert r.returncode == 1 and "AGE-SECRET" not in (r.stdout or ""), r.stdout
        assert "backup" not in auth.load_config() or not auth.load_config()["backup"].get("recipient")
    r = subprocess.run([sys.executable, SCRIPT, "init"], capture_output=True, text=True, env=env)
    assert "terminal" in r.stderr


def test_claude_is_denied_cc_backup_init():
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import test_prompt_allowlist as tpa
    deny, pats = tpa.deny_patterns()
    assert "Bash(*cc_backup.py init*)" in deny
    for cmd in (".venv/bin/python scripts/reports/cc_backup.py init", "python3 scripts/reports/cc_backup.py init",
                ".venv/bin/python scripts/reports/cc_backup.py init --replace",
                "cd /x && .venv/bin/python scripts/reports/cc_backup.py init | cat"):
        assert any(p.fullmatch(cmd) for _, p in pats), cmd
    for cmd in (".venv/bin/python scripts/reports/cc_backup.py run", ".venv/bin/python scripts/reports/cc_backup.py verify"):
        assert not any(p.fullmatch(cmd) for _, p in pats), cmd


def test_init_prints_the_identity_once_and_never_stores_it():
    fresh()
    env = dict(os.environ, HOME=tempfile.mkdtemp())
    code, output = run_tty(["init"], env)
    assert code == 0, output
    secret = [line.strip() for line in output.splitlines() if line.strip().startswith("AGE-SECRET-KEY-1")]
    assert len(secret) == 1 and output.count("AGE-SECRET-KEY-1") == 1
    cfg = auth.load_config()
    rcpt = cfg["backup"]["recipient"]
    assert rcpt.startswith("age1") and rcpt in output
    ident = pyrage.x25519.Identity.from_str(secret[0])
    assert str(ident.to_public()) == rcpt
    for path in all_files(TMP, TARGET, env["HOME"]):
        try:
            with open(path, "rb") as f:
                assert b"AGE-SECRET-KEY" not in f.read(), path
        except (PermissionError, IsADirectoryError, OSError):
            continue
    # a second init is refused, --replace makes a new one
    code2, out2 = run_tty(["init"], env)
    assert code2 == 1 and "exists already" in out2 and "AGE-SECRET" not in out2
    # verify: the key from stdin opens the newest backup and lists it; a wrong key doesn't
    r3 = subprocess.run([sys.executable, SCRIPT, "run"], capture_output=True, text=True, env=env)
    assert r3.returncode == 0 and r3.stdout.startswith("backup written: lcs-backup-"), r3.stderr
    r4 = subprocess.run([sys.executable, SCRIPT, "verify"], input=secret[0] + "\n", capture_output=True, text=True, env=env)
    assert r4.returncode == 0 and "opens with this key" in r4.stdout and "bookings.csv" in r4.stdout, r4.stderr
    wrong = str(pyrage.x25519.Identity.generate())
    r5 = subprocess.run([sys.executable, SCRIPT, "verify"], input=wrong + "\n", capture_output=True, text=True, env=env)
    assert r5.returncode == 1 and "doesn't open" in r5.stderr
    r6 = subprocess.run([sys.executable, SCRIPT, "verify", secret[0]], capture_output=True, text=True, env=env)
    assert r6.returncode == 2  # never on the command line
    code7, _ = run_tty(["init", "--replace"], env)
    assert code7 == 0 and auth.load_config()["backup"]["recipient"] != rcpt


def test_health_shows_the_backup_age_and_warns_after_36_hours():
    ident, rcpt = make_key()
    fresh(rcpt)
    now = datetime.datetime(2026, 9, 28, 12, 0, tzinfo=LONDON)
    assert sources.backup_check(now)["ok"] is False  # none yet
    cc_backup.run(now=datetime.datetime(2026, 9, 28, 2, 30, tzinfo=LONDON))
    c = sources.backup_check(now)
    assert c["ok"] is True and "9 hours ago" in c["detail"]
    late = sources.backup_check(now + datetime.timedelta(hours=28))
    assert late["ok"] is False and "over 36 hours" in late["detail"]
    assert sources.fingerprint_check(now)["ok"] is True
    fresh()
    assert "init" in sources.backup_check(now)["detail"]
    fresh(rcpt)
    cc_backup.run(now=datetime.datetime(2026, 9, 26, 2, 30, tzinfo=LONDON))
    app = create_app(client_factory=lambda: None, checkout=lambda: "main", now=lambda: now)
    client = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000))
    page = client.get("/health", headers=HEADERS).text
    assert "over 36 hours" in page and 'data-action="backup-now"' in page


def test_backup_now_is_registered_without_a_passkey_and_needs_same_origin():
    ident, rcpt = make_key()
    fresh(rcpt)
    defn = actions.REGISTRY["backup-now"]
    assert defn.passkey is False and defn.lock == "backup" and actions._LOCKS["backup"] is not actions._LOCKS["action"]
    assert defn.args(defn.validate({})) == ["run"] and defn.script == "scripts/reports/cc_backup.py"
    app = create_app(client_factory=lambda: None, checkout=lambda: "main")
    client = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000))
    calls = []
    saved = actions.RUNNER
    actions.RUNNER = lambda argv, **kw: calls.append(argv) or subprocess.CompletedProcess(argv, 0, b"backup written: x\n", b"")
    try:
        r = client.post("/actions/backup-now/run", json={"input": {}}, headers=HEADERS)
        assert r.status_code == 403 and calls == []  # no Origin: refused (CSRF)
        r = client.post("/actions/backup-now/run", json={"input": {}}, headers=dict(HEADERS, Origin=ORIGIN))
        assert r.status_code == 200 and r.json()["ok"], r.text
        assert calls == [[sys.executable, os.path.join(str(actions.REPO), "scripts", "reports", "cc_backup.py"), "run"]]
    finally:
        actions.RUNNER = saved
    fresh()
    r = client.post("/actions/backup-now/preview", json={"input": {}}, headers=dict(HEADERS, Origin=ORIGIN))
    assert r.status_code == 400 and "init" in r.json()["error"]


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
