# Zoho MCP sign-in: why it asked again, and the pin that stops it

*9 October 2026*

## What went wrong

The three Zoho servers (`zoho-mail`, `zoho-books`, `zoho-books-invoices`) run as `npx mcp-remote <secret Zoho URL> --transport http-only`, set in `~/.claude.json` under this project. mcp-remote keeps each server's OAuth sign-in in `~/.mcp-auth/mcp-remote-v1/<md5 of the URL>_tokens.json` and refreshes the hourly access token on its own. That part works: the Books tokens refresh without help.

On every start mcp-remote also works out which scopes to ask for. With nothing configured, it takes them from the Zoho server's metadata (`scopes_supported`) and compares that string, exactly, with the one saved at sign-in. If they differ it logs "The scopes this client asks for have changed since it signed in; signing in again", deletes the tokens file and opens the browser for a fresh approval. Zoho lists the scopes in no fixed order, and the list also changes whenever the tool selection on the Zoho MCP server changes. So from time to time the strings stop matching and the sign-in is thrown away.

That happened to `zoho-mail` at 16:15 on 5 October 2026. Every scheduled run after it hung at "Waiting for authorization…" until the connect timeout, and the enquiry assistant missed every run from 5 to 9 October. Luca approved it again at 16:43 on 9 October.

Ruled out: package upgrades (the token store is `mcp-remote-v1` and doesn't change between releases) and orphaned proxies (all the running proxies belonged to open sessions).

## The fix

mcp-remote takes the scope from `--static-oauth-client-metadata '{"scope": "…"}'` before anything the server says. The script below pins each Zoho server to the scope string its current sign-in was made with, which is the string the comparison checks, so it never sees a change and no new approval is needed. It also pins the package to `mcp-remote@0.14.3`, so the scheduled runs don't pick up a new release unannounced.

Claude can't run it: `mcp_bypass_guard.py` keeps Claude out of the MCP config, on purpose. Luca runs it in a terminal. It prints no URLs or tokens, backs up `~/.claude.json` first (as `~/.claude.json.bak-zoho-<time>`, mode 600) and checks 15 seconds later that no open Claude session has written over the change. Running it again is harmless: it re-pins to whatever the current sign-in holds.

```bash
python3 - <<'PY'
import json, os, sys, glob, hashlib, shutil, time, pathlib
H = pathlib.Path.home()
CFG = pathlib.Path(os.path.realpath(H / '.claude.json'))
AUTH = H / '.mcp-auth' / 'mcp-remote-v1'
PIN, FLAG = 'mcp-remote@0.14.3', '--static-oauth-client-metadata'
unpin = sys.argv[1:] == ['unpin']
proxy = lambda a: a.split('@')[0] == 'mcp-remote'

def zoho_servers(data):
    blocks = [data] + list((data.get('projects') or {}).values())
    for b in blocks:
        for name, e in (b.get('mcpServers') or {}).items():
            if name.startswith('zoho') and any(proxy(str(a)) for a in e.get('args') or []):
                yield name, e

data = json.loads(CFG.read_text())
report = []
for name, e in zoho_servers(data):
    args = [str(a) for a in e['args']]
    url = next(a for a in args if a.startswith('https://'))
    h = hashlib.md5(url.encode()).hexdigest()
    if FLAG in args:
        i = args.index(FLAG)
        del args[i:i + 2]
    args = [PIN if proxy(a) else a for a in args]
    if unpin:
        report.append(f'{name}: unpinned')
    else:
        hits = glob.glob(str(AUTH / f'{h[:6]}*_tokens.json'))
        if len(hits) != 1:
            sys.exit(f'{name}: no single saved sign-in for {h[:6]} ({len(hits)} found). Nothing changed.')
        t = json.loads(pathlib.Path(hits[0]).read_text())
        scope = t.get('requested_scope') or t.get('scope')
        if not scope:
            sys.exit(f'{name}: the saved sign-in holds no scope. Nothing changed.')
        args += [FLAG, json.dumps({'scope': scope})]
        report.append(f"{name}: pinned to its saved scope ({len(scope.split())} permissions, "
                      f"{'requested' if t.get('requested_scope') else 'granted'} list, {h[:6]})")
    e['args'] = args
if not report:
    sys.exit('No Zoho servers found. Nothing changed.')
bak = CFG.with_name(CFG.name + '.bak-zoho-' + time.strftime('%Y%m%d-%H%M%S'))
shutil.copy2(CFG, bak)
os.chmod(bak, 0o600)
tmp = CFG.with_name(CFG.name + '.tmp-zoho')
tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
os.chmod(tmp, os.stat(CFG).st_mode & 0o777)
os.replace(tmp, CFG)
print('\n'.join(report))
print('backup:', bak.name)
print('checking in 15 seconds that it stuck...')
time.sleep(15)
ok = all((FLAG in e['args']) != unpin and PIN in e['args']
         for _, e in zoho_servers(json.loads(CFG.read_text())))
print('it stuck: yes' if ok else 'it stuck: NO - an open Claude session wrote over it; close the other sessions and run this again')
PY
```

New sessions, including every scheduled run, start with the pin. Sessions already open keep their old unpinned proxies until they close, so restart the Claude app when convenient.

## Adding or removing Zoho tools later

The pin fixes the scopes to the ones granted today. If you change the tool selection on the Zoho MCP server and a new tool needs a scope that isn't in that list, calls to it fail with a permission error. Nothing opens a browser. To take the new scopes:

1. Run the script with `unpin` added to its first line (`python3 - unpin <<'PY'`).
2. Start a Claude session and approve the Zoho page once.
3. Run the script again as it stands, to pin the new list.

## If it ever asks again

Look in the newest file under `~/Library/Caches/claude-cli-nodejs/*/mcp-logs-zoho-mail/` for the line before "Please authorize this client". The enquiry assistant's step 1b already raises a push alert when mail hasn't been checked for four hours.
