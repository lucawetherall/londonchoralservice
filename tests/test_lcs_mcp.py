#!/usr/bin/env python3
"""Tests for scripts/bookings/lcs_mcp.py. Stdlib only, no network: the "server" is a local Python script
speaking MCP over stdio. .venv/bin/python tests/test_lcs_mcp.py"""
import json, os, signal, subprocess, sys, tempfile, time, urllib.parse
from pathlib import Path

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import lcs_mcp
import invoice_text

SECRET = "https://mcp.example.invalid/zoho/abc123SECRETTOKEN456"
REPO = "/work/lcs"

FAKE_SERVER = r'''
import json, sys, time
mode, secret = sys.argv[1], sys.argv[2]
sys.stderr.write("connecting to " + secret + "\n"); sys.stderr.flush()
def send(m):
    sys.stdout.write(json.dumps(m) + "\n"); sys.stdout.flush()
state = "new"
for line in sys.stdin:
    msg = json.loads(line)
    if msg.get("method") == "initialize":
        assert state == "new"
        state = "init"
        if mode == "hang":
            time.sleep(60)
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"protocolVersion": msg["params"]["protocolVersion"],
              "capabilities": {"tools": {}}, "serverInfo": {"name": "fake"}}})
    elif msg.get("method") == "notifications/initialized":
        assert state == "init"
        state = "ready"
    elif msg.get("method") == "tools/list":
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": [{"name": "ZohoMail_getOriginalMessage"}]}})
    elif msg.get("method") == "tools/call":
        if state != "ready":
            send({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32002, "message": "not initialised"}})
            continue
        if mode == "exit":
            sys.exit(3)
        if mode == "huge":
            send({"jsonrpc": "2.0", "id": msg["id"], "result": {"content": [{"type": "text", "text": "x" * 5000}]}})
            continue
        if mode == "badbytes":
            sys.stdout.buffer.write(b'{"jsonrpc": "2.0", "id": %d, "result": {"content": [{"type": "text", "text": "caf\xe9"}]}}\n' % msg["id"])
            sys.stdout.flush()
            continue
        if mode == "rpc-error":
            send({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32000, "message": "upstream " + secret + " failed"}})
            continue
        if mode == "noisy":
            sys.stdout.write("mcp-remote: proxy ready\n")
            send({"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info", "data": "hi"}})
            send({"jsonrpc": "2.0", "id": "srv-1", "method": "ping"})
            reply = json.loads(sys.stdin.readline())
            assert reply == {"jsonrpc": "2.0", "id": "srv-1", "result": {}}, reply
            send({"jsonrpc": "2.0", "id": 999, "result": {"content": [{"type": "text", "text": "stale"}]}})
        payload = {"status": {"code": 200}, "data": {"messageId": "1", "content": "Subject: hi\n\n" + json.dumps(msg["params"])}}
        is_error = mode == "tool-error"
        text = ("bad key for " + secret) if is_error else json.dumps(payload)
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"content": [{"type": "text", "text": text}], "isError": is_error}})
'''


def config(mode, repo=REPO, entry=None):
    server = Path(TMP) / "fake_server.py"
    server.write_text(FAKE_SERVER)
    entry = entry or {"command": sys.executable, "args": [str(server), mode, SECRET]}
    path = Path(TMP) / f"claude-{mode}.json"
    path.write_text(json.dumps({"projects": {repo: {"mcpServers": {"zoho-mail": entry}}}}))
    return path


class Spy:
    """Records the processes started, so a test can check they were killed."""
    def __init__(self):
        self.procs, self.kw = [], []

    def __call__(self, *a, **kw):
        p = subprocess.Popen(*a, **kw)
        self.procs.append(p)
        self.kw.append(kw)
        return p


def call(mode, **kw):
    saved = lcs_mcp.REPO
    lcs_mcp.REPO = Path(REPO)
    try:
        return lcs_mcp.zoho_original_message("1788039834223141600", config_path=config(mode), **kw)
    finally:
        lcs_mcp.REPO = saved


def fails(fn):
    try:
        fn()
    except lcs_mcp.McpError as e:
        return str(e)
    raise AssertionError("no McpError")


def test_call_returns_text_and_the_process_is_killed():
    spy = Spy()
    text = call("ok", popen=spy)
    raw = invoice_text.raw_message_text(text)
    params = json.loads(raw.split("\n\n", 1)[1])
    assert params == {"name": "ZohoMail_getOriginalMessage", "arguments": {"path_variables": {
        "accountId": "6133510000000008002", "messageId": "1788039834223141600"}}}, params
    assert len(spy.procs) == 1 and spy.procs[0].poll() is not None


def test_noise_notifications_and_server_pings_are_handled():
    assert "ZohoMail_getOriginalMessage" in call("noisy")


def test_only_allowed_tools_and_no_process_for_a_refused_one():
    spy = Spy()
    for server, tool in (("zoho-mail", "ZohoMail_sendEmail"), ("zoho-mail", "ZohoMail_deleteZohoMailCopy"),
                         ("zoho-books", "ZohoMail_getOriginalMessage")):
        msg = fails(lambda: lcs_mcp.call_tool(server, tool, {}, config_path=config("ok"), popen=spy))
        assert msg == f"{server}: tool {tool} is not allowed", msg
    assert spy.procs == []
    assert lcs_mcp.ALLOWED == {("zoho-mail", "ZohoMail_getOriginalMessage")}


def test_timeout_kills_the_process():
    spy = Spy()
    msg = fails(lambda: call("hang", timeout=1, popen=spy))
    assert msg == "zoho-mail: timed out after 1s", msg
    assert spy.procs[0].poll() is not None


def test_errors_never_carry_the_secret_url():
    for mode in ("rpc-error", "tool-error", "exit"):
        msg = fails(lambda: call(mode))
        assert "SECRETTOKEN" not in msg and "mcp.example" not in msg and "fake_server" not in msg, (mode, msg)
        assert msg.startswith("zoho-mail: "), msg
    assert fails(lambda: call("exit")) == "zoho-mail: the MCP server exited before answering"


def test_missing_or_unsupported_server():
    missing = Path(TMP) / "none.json"
    missing.write_text(json.dumps({"projects": {}}))
    assert fails(lambda: lcs_mcp.server_config("zoho-mail", missing, REPO)) == "zoho-mail: no such MCP server configured"
    assert fails(lambda: lcs_mcp.server_config("zoho-mail", Path(TMP) / "absent.json", REPO)) == \
        "zoho-mail: could not read the MCP settings"
    http = config("http", entry={"type": "http", "url": SECRET})
    msg = fails(lambda: lcs_mcp.server_config("zoho-mail", http, REPO))
    assert msg == "zoho-mail: not a stdio MCP server", msg
    bad = config("badcmd", entry={"command": "/nonexistent/" + SECRET.rsplit("/", 1)[1], "args": [SECRET]})
    saved = lcs_mcp.REPO
    lcs_mcp.REPO = Path(REPO)
    try:
        msg = fails(lambda: lcs_mcp.zoho_original_message("1788039834223141600", config_path=bad))
    finally:
        lcs_mcp.REPO = saved
    assert msg == "zoho-mail: could not start the MCP server", msg


def test_a_worktree_falls_back_to_the_main_checkout():
    path = config("ok")
    cmd, args, env = lcs_mcp.server_config("zoho-mail", path, REPO + "/.claude/worktrees/agent-x")
    assert cmd == sys.executable and args[-1] == SECRET and env == {}
    user = Path(TMP) / "user.json"
    user.write_text(json.dumps({"projects": {}, "mcpServers": {"zoho-mail": {"command": "npx", "args": ["x"]}}}))
    assert lcs_mcp.server_config("zoho-mail", user, "/elsewhere")[0] == "npx"


def test_message_id_must_be_numeric():
    spy = Spy()
    assert fails(lambda: lcs_mcp.zoho_original_message("1; rm -rf", config_path=config("ok"), popen=spy)).startswith(
        "zoho-mail: not a message id")
    assert spy.procs == []


def test_list_tools():
    saved = lcs_mcp.REPO
    lcs_mcp.REPO = Path(REPO)
    try:
        assert [t["name"] for t in lcs_mcp.list_tools("zoho-mail", config_path=config("ok"))] == ["ZohoMail_getOriginalMessage"]
    finally:
        lcs_mcp.REPO = saved


def test_raw_message_text_accepts_inline_json_and_mime():
    inline = json.dumps({"status": {"code": 200}, "data": {"messageId": "1", "content": "From: a\n\nbody"}})
    assert invoice_text.raw_message_text(inline) == "From: a\n\nbody"
    assert invoice_text.raw_message_text("From: a\n\nbody") == "From: a\n\nbody"
    saved = Path(TMP) / "saved.json"
    saved.write_text(inline)
    assert invoice_text.raw_message(saved) == "From: a\n\nbody"


def test_invoice_text_fetch_option():
    import contextlib, io
    saved = (invoice_text.fetch_message, sys.argv)
    calls = []
    invoice_text.fetch_message = lambda mid: calls.append(mid) or "From: a\nSubject: x\n\nno attachment here"
    try:
        sys.argv = ["invoice_text.py", "--fetch", "1788039834223141600"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            invoice_text.main()
    finally:
        invoice_text.fetch_message, sys.argv = saved
    assert calls == ["1788039834223141600"]
    assert buf.getvalue().strip() == "== message 1788039834223141600: no Invoice*.pdf attachment", buf.getvalue()


# --- review of PR 152: process groups, reply limits, scrubbing ---------------------------------------

WRAPPER = r"""
import subprocess, sys
# like npx: run the real server as a child with inherited stdio, and wait for it
sys.exit(subprocess.call([sys.executable, sys.argv[1], *sys.argv[2:]]))
"""

GRANDCHILD = r"""
import json, os, sys, time
if sys.argv[2] == "escape":
    os.setsid()  # leaves the process group: only the pipe handling can save the caller now
open(sys.argv[1], "w").write(str(os.getpid()))
for line in sys.stdin:
    if json.loads(line).get("method") == "initialize":
        time.sleep(60)  # a hung upstream
time.sleep(60)  # an open upstream connection keeps it alive after stdin closes
"""


def orphan_call(how):
    wrapper, child = Path(TMP) / "wrapper.py", Path(TMP) / "grandchild.py"
    wrapper.write_text(WRAPPER)
    child.write_text(GRANDCHILD)
    pidf = Path(TMP) / f"gc-{how}.pid"
    pidf.unlink(missing_ok=True)
    cfg = config("orphan-" + how, entry={"command": sys.executable, "args": [str(wrapper), str(child), str(pidf), how]})
    saved = lcs_mcp.REPO
    lcs_mcp.REPO = Path(REPO)
    t = time.monotonic()
    try:
        msg = fails(lambda: lcs_mcp.zoho_original_message("1788039834223141600", config_path=cfg, timeout=2))
    finally:
        lcs_mcp.REPO = saved
    return msg, time.monotonic() - t, int(pidf.read_text())


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_timeout_kills_the_whole_process_group():
    msg, took, pid = orphan_call("stay")
    assert msg == "zoho-mail: timed out after 2s" and took < 5, (msg, took)
    for _ in range(40):  # a killed orphan is reaped by launchd/init
        if not alive(pid):
            break
        time.sleep(0.05)
    try:
        assert not alive(pid), f"grandchild {pid} still running"
    finally:
        if alive(pid):
            os.kill(pid, signal.SIGKILL)


def test_a_grandchild_holding_stdout_never_blocks_the_call():
    msg, took, pid = orphan_call("escape")
    try:
        assert msg == "zoho-mail: timed out after 2s" and took < 5, (msg, took)
    finally:
        if alive(pid):
            os.kill(pid, signal.SIGKILL)


def test_the_server_starts_in_its_own_session():
    spy = Spy()
    call("ok", popen=spy)
    kw = {k: spy.kw[0].get(k) for k in ("start_new_session", "encoding", "errors")}  # never the env: it holds secrets
    assert kw == {"start_new_session": True, "encoding": "utf-8", "errors": "replace"}, kw


def test_a_reply_over_the_cap_is_refused():
    saved = lcs_mcp.MAX_REPLY
    lcs_mcp.MAX_REPLY = 1000
    try:
        assert fails(lambda: call("huge")) == "zoho-mail: the MCP server's reply was too large"
    finally:
        lcs_mcp.MAX_REPLY = saved
    assert lcs_mcp.MAX_REPLY == 60 << 20
    assert "x" * 5000 in call("huge")


def test_undecodable_bytes_are_replaced():
    assert call("badbytes") == "caf�"


TOKEN = SECRET.rsplit("/", 1)[1]


def test_scrub_catches_every_shape_of_the_url():
    secrets = [sys.executable, "--flag", SECRET]
    for leak in (f"POST /zoho/{TOKEN} returned 401", "reaching mcp.example.invalid/zoho/" + TOKEN,
                 "bad url " + urllib.parse.quote(SECRET, safe=""), f"key {TOKEN} revoked",
                 "host mcp.example.invalid refused", "GET /zoho/" + TOKEN):
        got = lcs_mcp._scrub(leak, secrets)
        assert TOKEN not in got and "mcp.example.invalid" not in got and "%2F" not in got, (leak, got)
    q = "https://h.example.invalid/api?key=QUERYVALUE123&x=1"
    assert "QUERYVALUE123" not in lcs_mcp._scrub("sent key QUERYVALUE123", [q])
    assert lcs_mcp._scrub("port 87654321 closed", [87654321]) == "port <redacted> closed"
    assert lcs_mcp._scrub("fine", [None, "", 5]) == "fine"


def test_list_tools_only_for_allowed_servers():
    spy = Spy()
    msg = fails(lambda: lcs_mcp.list_tools("zoho-books", config_path=config("ok"), popen=spy))
    assert msg == "zoho-books: not an allowed server", msg
    assert spy.procs == []


def test_message_id_must_be_ascii_digits():
    spy = Spy()
    for bad in ("１２３４５６７８", "١٢٣٤٥٦٧٨", "12345678\n", "", "1" * 26):
        msg = fails(lambda: lcs_mcp.zoho_original_message(bad, config_path=config("ok"), popen=spy))
        assert msg.startswith("zoho-mail: not a message id"), (bad, msg)
    assert spy.procs == []


def test_invoice_text_fetch_failure_is_one_line():
    import contextlib, io
    saved = (invoice_text.fetch_message, sys.argv)

    def boom(mid):
        raise lcs_mcp.McpError("zoho-mail: timed out after 90s")
    invoice_text.fetch_message = boom
    try:
        sys.argv = ["invoice_text.py", "--fetch", "1788039834223141600"]
        with contextlib.redirect_stdout(io.StringIO()):
            invoice_text.main()
        raise AssertionError("no SystemExit")
    except SystemExit as e:
        assert e.code == "could not fetch message 1788039834223141600: zoho-mail: timed out after 90s", e.code
    finally:
        invoice_text.fetch_message, sys.argv = saved


def books_config():
    server = Path(TMP) / "fake_server.py"
    server.write_text(FAKE_SERVER)
    entry = {"command": sys.executable, "args": [str(server), "ok", SECRET]}
    path = Path(TMP) / "claude-books.json"
    path.write_text(json.dumps({"projects": {REPO: {"mcpServers": {"zoho-books": entry, "zoho-books-invoices": entry}}}}))
    return path


def test_books_read_list_is_the_guard_hooks():
    import importlib.util
    spec = importlib.util.spec_from_file_location("g", os.path.join(ROOT, ".claude", "hooks", "zoho_books_guard.py"))
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    assert lcs_mcp.BOOKS_READ == frozenset(guard.READ_ALLOW) and lcs_mcp.BOOKS_READ
    assert not lcs_mcp.BOOKS_READ & set(guard.WRITE_TOOLS)
    assert {"ZohoBooks_list_invoices", "ZohoBooks_list_bills"} <= lcs_mcp.BOOKS_READ


def test_books_read_tools_run_on_the_books_servers_only():
    saved = lcs_mcp.REPO
    lcs_mcp.REPO = Path(REPO)
    try:
        for server, tool in (("zoho-books-invoices", "ZohoBooks_list_invoices"), ("zoho-books", "ZohoBooks_list_bills")):
            spy = Spy()
            text = lcs_mcp.call_tool(server, tool, {"query_params": {"organization_id": "941014440"}},
                                     config_path=books_config(), popen=spy)
            sent = json.loads(json.loads(text)["data"]["content"].split("\n\n", 1)[1])
            assert sent == {"name": tool, "arguments": {"query_params": {"organization_id": "941014440"}}}, sent
            assert len(spy.procs) == 1 and spy.procs[0].poll() is not None
    finally:
        lcs_mcp.REPO = saved


def test_books_writes_and_unlisted_tools_are_refused_before_a_process():
    spy = Spy()
    for server, tool in (("zoho-books", "ZohoBooks_create_bill"), ("zoho-books-invoices", "ZohoBooks_create_invoice"),
                         ("zoho-books-invoices", "ZohoBooks_update_invoice"), ("zoho-books", "ZohoBooks_delete_bill"),
                         ("zoho-books", "ZohoBooks_list_bank_accounts"), ("zoho-books", "ZohoBooks_get_contact_bank_account"),
                         ("zoho-mail", "ZohoBooks_list_invoices"), ("zoho-books-x", "ZohoBooks_list_invoices"),
                         ("zoho-books", "ZohoMail_getOriginalMessage")):
        msg = fails(lambda: lcs_mcp.call_tool(server, tool, {}, config_path=books_config(), popen=spy))
        assert msg == f"{server}: tool {tool} is not allowed", msg
    assert spy.procs == []


def test_an_unloadable_guard_allows_no_books_tool():
    bad = Path(TMP) / "broken_guard.py"
    bad.write_text("raise RuntimeError('broken')\n")
    assert lcs_mcp.books_read_allow(bad) == frozenset()
    assert lcs_mcp.books_read_allow(Path(TMP) / "missing.py") == frozenset()
    odd = Path(TMP) / "odd_guard.py"
    odd.write_text("READ_ALLOW = {'ZohoBooks_list_invoices', 'ZohoBooks_create_bill'}\nWRITE_TOOLS = {'ZohoBooks_create_bill': 1}\n")
    assert lcs_mcp.books_read_allow(odd) == frozenset({"ZohoBooks_list_invoices"})


def test_a_bare_command_is_found_in_the_node_folders():
    """launchd gives the Command Centre a bare PATH: a bare `npx` is looked for in the usual Node folders."""
    seen = []

    def which(cmd, path=None):
        seen.append((cmd, path))
        return f"{path}/{cmd}" if path == "/fake/node/bin" else None
    assert lcs_mcp.resolve_command("zoho-books", "/abs/npx", "/usr/bin", dirs=["/x"], which=which) == ("/abs/npx", None)
    assert seen == []  # a path is used as it is
    assert lcs_mcp.resolve_command("zoho-books", "npx", "/fake/node/bin", dirs=["/x"], which=which) == ("npx", None)
    seen.clear()
    found = lcs_mcp.resolve_command("zoho-books", "npx", "/usr/bin:/bin", dirs=["/opt/none", "/fake/node/bin"],
                                    which=which)
    assert found == ("/fake/node/bin/npx", "/fake/node/bin"), found
    assert seen == [("npx", "/usr/bin:/bin"), ("npx", "/opt/none"), ("npx", "/fake/node/bin")], seen
    try:
        lcs_mcp.resolve_command("zoho-books", "npx", "/usr/bin", dirs=["/opt/none"], which=lambda c, path=None: None)
    except lcs_mcp.CommandNotFound as e:
        assert isinstance(e, lcs_mcp.McpError) and str(e).startswith("zoho-books: ") and "npx" not in str(e), e
    else:
        raise AssertionError("no CommandNotFound")


def test_fallback_folders_are_homebrew_then_nvm_newest_first():
    home = Path(tempfile.mkdtemp())
    for v in ("v18.19.0", "v20.11.1", "v9.0.0"):
        (home / ".nvm" / "versions" / "node" / v / "bin").mkdir(parents=True)
    dirs = lcs_mcp.fallback_dirs(home)
    assert dirs[:2] == ["/opt/homebrew/bin", "/usr/local/bin"], dirs
    assert [Path(d).parent.name for d in dirs[2:]] == ["v20.11.1", "v18.19.0", "v9.0.0"], dirs
    assert lcs_mcp.fallback_dirs(Path(tempfile.mkdtemp())) == ["/opt/homebrew/bin", "/usr/local/bin"]


def test_the_session_starts_the_resolved_command_with_its_folder_on_path():
    """No real server: a fake Node folder holds an executable `npx`, and a popen stand-in records what would run."""
    node = Path(tempfile.mkdtemp())
    fake = node / "lcs-fake-npx"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o700)
    cfg = config("bare", entry={"command": "lcs-fake-npx", "args": [SECRET]})
    calls = []

    def popen(argv, **kw):
        calls.append((argv, kw))
        raise OSError("not starting anything in a test")
    saved = (lcs_mcp.REPO, lcs_mcp.NODE_DIRS, os.environ.get("PATH"))
    lcs_mcp.REPO, lcs_mcp.NODE_DIRS = Path(REPO), (str(node),)
    os.environ["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"  # launchd's
    try:
        msg = fails(lambda: lcs_mcp.zoho_original_message("1788039834223141600", config_path=cfg, popen=popen))
        assert msg == "zoho-mail: could not start the MCP server", msg
        argv, kw = calls[0]
        assert argv == [str(fake), SECRET], argv
        assert kw["env"]["PATH"].split(os.pathsep)[0] == str(node), kw["env"]["PATH"]
        calls.clear()
        lcs_mcp.NODE_DIRS = ()
        missing = config("bare-missing", entry={"command": "lcs-no-such-npx", "args": [SECRET]})
        saved_home = os.environ.get("HOME")
        os.environ["HOME"] = tempfile.mkdtemp()  # no nvm folders either
        try:
            msg = fails(lambda: lcs_mcp.zoho_original_message("1788039834223141600", config_path=missing,
                                                             popen=popen))
        finally:
            os.environ["HOME"] = saved_home
        assert calls == [] and msg.startswith("zoho-mail: the MCP server's command isn't on PATH"), msg
        assert "SECRETTOKEN" not in msg and "lcs-no-such-npx" not in msg, msg
    finally:
        lcs_mcp.REPO, lcs_mcp.NODE_DIRS = saved[0], saved[1]
        os.environ["PATH"] = saved[2]


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
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
