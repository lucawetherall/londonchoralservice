#!/usr/bin/env python3
"""Tests for scripts/bookings/lcs_mcp.py. Stdlib only, no network: the "server" is a local Python script
speaking MCP over stdio. .venv/bin/python tests/test_lcs_mcp.py"""
import json, os, subprocess, sys, tempfile
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
        self.procs = []

    def __call__(self, *a, **kw):
        p = subprocess.Popen(*a, **kw)
        self.procs.append(p)
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
