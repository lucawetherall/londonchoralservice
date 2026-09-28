# LCS Command Centre Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One private web app, reached only over the owner's tailnet, that shows everything about the business and (from phase 3) lets him act on it with a passkey. It replaces the static `scripts/reports/dashboard.py` page once phase 2 ships.

**Architecture:** `command_centre/` is a Starlette app served by uvicorn on `127.0.0.1:8765` only (or, optionally, a Unix socket in a mode-700 directory), and published to the tailnet by `tailscale serve`. Every request must come from a loopback peer with `Host` equal to the Mac's tailnet name (DNS rebinding); every request except `/healthz` must also carry the Tailscale identity headers for an allowed login; every write (from phase 3) also needs a WebAuthn assertion made in the last 60 seconds over a challenge bound to that action's summary. The data layer imports the existing read functions (`dashboard.py`, `check_payments`, `money_report`, `singer_invoices`, `pipeline`, `economics`, `weekly_review`) and never shells out to read. Pages are Jinja2 templates (autoescape on) with htmx served from `static/`, and nothing is loaded from any other origin.

**Tech Stack:**
- Python 3 in the repo's `.venv`: `starlette`, `jinja2`, `uvicorn`, `webauthn` (py_webauthn), pinned to exact versions with their dependencies in `scripts/requirements.txt`. Test-only: `httpx2` (Starlette's TestClient) in `scripts/requirements-dev.txt`, which `install.sh` never installs. Later, also pinned: `pywebpush` (phase 5), `claude-agent-sdk` (phase 4).
- htmx 2.0.11, vendored as `command_centre/static/htmx.min.js` (from the npm package `htmx.org@2.0.11`, tarball integrity `sha512-Thx/WtpeOQqSrqBCw/A1cwGJGg4UrVa3+sW0GmrM3p4gJgO89ecH4qtbnyzDDWFvBTqjnIMCgELTNt636dtamA==`; file SHA-256 `d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717`).
- Tests are stdlib-only scripts in the repo's style, with Starlette's `TestClient`: `.venv/bin/python tests/test_cc_auth.py`.

**Spec:** [docs/superpowers/specs/2026-09-28-command-centre-design.md](../specs/2026-09-28-command-centre-design.md). Its binding rules apply to every phase.

---

## Read this before starting

- **No public internet.** `python -m command_centre` binds to `127.0.0.1`, never `0.0.0.0`, and the host is not configurable. `tailscale serve` is the only way in from another device.
- **Host and peer first.** Before the identity check, the app refuses a peer other than 127.0.0.1 or ::1 (a Unix-socket peer counts as local) and a `Host` other than the config's `rp_id`, bare or with `:443` (and `127.0.0.1:<port>` only while the dev login is on). A second `Host` or identity header is refused too.
- **The first passkey needs a bootstrap code.** `install.sh` issues it (sha256 and a 30-minute expiry in the config, the code printed once); the first registration needs it at both steps and deletes it. `python -m command_centre.bootstrap --new-bootstrap` issues another while no passkey exists.
- **Trust in the identity headers.** `tailscale serve` sets `Tailscale-User-Login` and `Tailscale-User-Name` on requests it proxies from a tailnet device, and strips any copies the client sent, so a tailnet client can't claim someone else's login. A process running on the Mac itself can reach `127.0.0.1:8765` and forge them: that is why every write also needs a passkey (phase 3), and why nothing else on the Mac should listen for or proxy to this port.
- **Fail closed.** No config, an unreadable config, or an empty `allowed_logins` means every route except `/healthz` answers 403.
- **Private data stays in `~/lcs-private`.** The config, logs, cache, audit log and events live under `~/lcs-private/command-centre/` (directories 700, files 600). The repo holds code only. `LCS_PRIVATE_DIR` moves the whole private tree (the tests use a temp dir).
- **Never run the service from a session.** The owner runs `command_centre/install.sh` and `tailscale serve`. Sessions start the app only on a spare port (`CC_PORT=8799`) against a temp `LCS_PRIVATE_DIR` holding fake data, with `CC_NO_BANK=1` (no Keychain read, no Starling call) and `CC_DEV_LOGIN` (honoured only when bound to 127.0.0.1 on a port other than 8765, never on the Unix socket, and only for a login in the temp config; the LaunchAgent sets it to ""), for a visual check, and stop it afterwards.
- **`command_centre/` is never published.** It is in `scripts/stage_site.py`'s `PRIVATE` list, so GitHub Pages never serves its templates or code.
- **No secrets in output.** A failing data source shows `couldn't load (<TypeName>)`, never the exception message. Client and singer first names only; bank accounts as `••••last4` only.

## File structure (all phases)

| File | Responsibility | Phase |
|---|---|---|
| `command_centre/__init__.py`, `__main__.py` | `python -m command_centre [--uds [PATH]]`: uvicorn on `127.0.0.1:${CC_PORT:-8765}` or a Unix socket; rotates logs over 5 MB on start (3 kept) | 1 |
| `command_centre/bootstrap.py` | `--new-bootstrap`: a new one-time code for the first passkey | 1 |
| `command_centre/app.py` | Routes, security headers, templates, `create_app()` | 1 |
| `command_centre/auth.py` | Config, Tailscale identity middleware, passkeys, `require_fresh_assertion` | 1 |
| `command_centre/data.py` | Read models per page, each source wrapped, the 10-minute bank cache | 1, grows in 2 |
| `command_centre/templates/`, `static/` | Jinja2 pages, `app.css`, `htmx.min.js`, `passkey.js` | 1 |
| `command_centre/install.sh` | LaunchAgent, config, the `tailscale serve` command to run | 1 |
| `command_centre/actions.py` | The action registry: validated input, preview, fixed argv, audit log | 3 |
| `command_centre/jobs.py` | Refresh jobs and caches, backups | 2, 5 |
| `command_centre/chat.py` | Claude Agent SDK session, streaming, approval cards | 4 |
| `command_centre/push.py` | Web Push, events watcher | 5 |
| `tests/test_cc_*.py` | One test file per module | all |

---

## Phase 1: secure skeleton, Today and Money (this PR)

### Task 1.1: Dependencies and the deploy allowlist

**Files:** Modify `scripts/requirements.txt`, `scripts/stage_site.py`, `build.sh`, `scripts/generate_sitemap.py`; create `command_centre/static/htmx.min.js`.

- [x] **Step 1:** `.venv/bin/pip install starlette jinja2 uvicorn webauthn httpx2` and add the five to `scripts/requirements.txt`.
- [x] **Step 2:** Vendor htmx: `npm pack htmx.org@2.0.11`, check the tarball's SHA-512 against `npm view htmx.org@2.0.11 dist.integrity`, copy `package/dist/htmx.min.js` to `command_centre/static/`. The page turns off htmx's inline indicator styles and `eval` (`htmx-config` meta), so the CSP needs no `unsafe-inline` or `unsafe-eval`.
- [x] **Step 3:** Add `'command_centre/**'` to `PRIVATE` in `scripts/stage_site.py`, and skip `command_centre/` in `build.sh`'s three `find`s and `scripts/generate_sitemap.py`'s walk (otherwise its templates land in `sitemap.xml` and break `generate_llms_full.py`). `./build.sh` then leaves the pages unchanged.

### Task 1.2: Auth, test-first (`tests/test_cc_auth.py`, `command_centre/auth.py`)

Config, `~/lcs-private/command-centre/config.json` (mode 600):

```json
{
  "allowed_logins": ["owner@example.com"],
  "origin": "https://<mac>.<tailnet>.ts.net",
  "rp_id": "<mac>.<tailnet>.ts.net",
  "passkeys": [{"id": "<b64url>", "public_key": "<b64url>", "sign_count": 0, "created": "<iso>", "label": ""}]
}
```

- [x] **Step 1: Tests first.**
  - No `Tailscale-User-Login`, a wrong login, or a login without `Tailscale-User-Name`: 403 on `/`, `/money`, `/static/app.css`, `/auth/passkey/assert/options`. The right login and a name: 200.
  - No config, or an empty `allowed_logins`: 403 (fail closed).
  - `/healthz` answers 200 without headers, with a body of `ok` and nothing else.
  - `CC_DEV_LOGIN` injects the login only when the app was created with `bind_host="127.0.0.1"` and the variable is set; it is off by default and off for any other bind host, and the injected login must still be in `allowed_logins`.
  - A POST whose `Origin` isn't the configured origin gets 403 (CSRF).
  - `require_fresh_assertion(credential, summary)`:
    - accepts a signed assertion over a challenge issued for that summary, within 60 seconds;
    - refuses a different summary (the challenge embeds `sha256(summary)`), an expired challenge, a second use of the same challenge (replay), an unknown challenge and an unknown credential id;
    - updates the stored sign count.
  - Registration: allowed with no passkeys; with passkeys, only after a fresh assertion for "register a new passkey"; the registration challenge is single-use and expires after 60 seconds; only the public key is stored.
  - py_webauthn's `verify_*_response` is patched in the tests; the structures (`RegistrationCredential`, `AuthenticationCredential` JSON, `clientDataJSON`) are real.
- [x] **Step 2: Implement** `auth.py`:
  - `config_dir()`, `load_config()`, `save_config()` (atomic, mode 600, under an `flock`).
  - `IdentityMiddleware` (pure ASGI): `/healthz` passes; everything else needs both headers and an allowed login, else a 403 with the security headers; POSTs also need `Origin` equal to the configured origin.
  - `ChallengeStore`: challenge = 16 random bytes ‖ `sha256(purpose ‖ summary)`, expiry 60 seconds, single use, in memory.
  - `require_fresh_assertion(credential_json, action_summary)` and the four passkey routes: `POST /auth/passkey/register/options`, `POST /auth/passkey/register`, `POST /auth/passkey/assert/options`, `POST /auth/passkey/assert`. User verification is required (Face ID or Touch ID).

### Task 1.3: Pages, test-first (`tests/test_cc_pages.py`, `command_centre/data.py`, `app.py`, templates)

- [x] **Step 1: Tests first**, with fixture CSVs (fake names, `example.org` emails) in a temp `LCS_PRIVATE_DIR`:
  - Today shows, in order: bank-detail warnings (singer invoices with `ring_first`), hand checks (`money_report.needs_hand_check`), unpaid singer invoices, then upcoming events split into this week and later.
  - Money shows the Starling balance (fake client), the Monday money lines, hand checks and singer invoices; without a Keychain token it says "bank not checked".
  - A source that raises shows `couldn't load (<TypeName>)` while the rest of the page renders, and the exception's message never appears.
  - Every page has the freshness stamp, the nav with the phase-2 pages marked "soon", and `lang="en-GB"`.
  - A `<script>` in a client name is escaped.
  - No `http:`/`https:` URL, protocol-relative `//` URL, inline `<script>` or `style=` in any page.
  - Headers: `Content-Security-Policy` (self only, `frame-ancestors 'none'`), `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and `Cache-Control: no-store` on every page (also on 403s and `/healthz`).
  - Surnames, emails and full account numbers never appear.
- [x] **Step 2: Implement** `data.py` on top of `dashboard.py`'s functions (`payments`, `upcoming`, `money_lines`, `hand_check`, `singers`, `bank_balance`, `section`), with the Starling reads cached for 10 minutes and each source's last good value kept, then `app.py` and the templates. The layout is mobile-first, has light and dark themes from `prefers-color-scheme`, and uses no inline styles or scripts.

### Task 1.4: Service

- [x] **Step 1:** `command_centre/__main__.py`: `uvicorn.run(create_app(bind_host="127.0.0.1"), host="127.0.0.1", port=CC_PORT or 8765, proxy_headers=False, server_header=False)`.
- [x] **Step 2:** `command_centre/install.sh`, idempotent:
  - makes `~/lcs-private/command-centre/{logs,cache}` (mode 700);
  - asks for the owner's Tailscale login (`read -p`) and the tailnet name, and writes `config.json` (mode 600) only if it doesn't exist;
  - writes `~/Library/LaunchAgents/com.lcs.command-centre.plist` (`<repo>/.venv/bin/python -m command_centre`, working directory the repo, `RunAtLoad`, `KeepAlive`, logs in `~/lcs-private/command-centre/logs/`);
  - reloads it with `launchctl bootout`/`bootstrap`, then checks `/healthz`;
  - prints the `tailscale serve --bg --https=443 http://127.0.0.1:8765` command for the owner to run.
- [x] **Step 3:** `bash -n command_centre/install.sh`. Never run it from a session.

### Task 1.5: Visual check and PR

- [x] **Step 1:** Start the app on `127.0.0.1:8799` with `CC_DEV_LOGIN` and a temp `LCS_PRIVATE_DIR` of fake data; check Today and Money at 390px and 1280px wide; stop it.
- [x] **Step 2:** Run every `tests/test_*.py`; commit `feat(command-centre): phase 1, secure skeleton with Tailscale identity, passkeys, Today and Money`; open a PR. Don't merge: the owner reviews it and runs the install.

### Task 1.6: Security review fixes (PR #156)

- [x] Host check against DNS rebinding; loopback peers only; duplicate `Host`/identity headers refused; `/healthz` also needs the right `Host`.
- [x] Bootstrap code for the first passkey (`install.sh`, `python -m command_centre.bootstrap --new-bootstrap`); "N passkeys, last added <date>" on Today and Passkeys.
- [x] Optional Unix socket (`--uds`), dev login refused on 8765 and the socket, `CC_DEV_LOGIN=""` in the LaunchAgent.
- [x] Pinned dependencies; test-only packages in `scripts/requirements-dev.txt`.
- [x] Challenge store capped at 100; logs rotated on start; `launchctl bootstrap` retried once; `require_fresh_assertion` takes a server-built `auth.Action` (phase 3's registry builds these from `preview(input)`); a warning on Today's health line when the main checkout isn't on `main`.
- Tests: `tests/test_cc_security.py`.

### Owner steps after merge

1. `cd ~/Documents/GitHub/londonchoralservice && git checkout main && git pull` (the LaunchAgent runs this checkout, so keep it on `main`; Today warns if it isn't).
2. `bash command_centre/install.sh`. It installs the pinned `scripts/requirements.txt`, asks for the Tailscale login (for example `luca@example.com`) and the Mac's tailnet name, loads the LaunchAgent, and prints a one-time bootstrap code (valid 30 minutes).
3. Run the printed `tailscale serve --bg --https=443 http://127.0.0.1:8765`. (The printed Unix-socket alternative, `tailscale serve --bg --https=443 unix:~/lcs-private/command-centre/run/cc.sock` with the LaunchAgent on `--uds`, is untested: try it only if you want it, and check the page loads.)
4. Open `https://<mac>.<tailnet>.ts.net/passkeys` on the iPhone, enter the bootstrap code and register a passkey. If the page answers `Forbidden`, `tailscale serve` isn't passing the tailnet name as `Host`: say so before changing anything. If the code expired: `.venv/bin/python -m command_centre.bootstrap --new-bootstrap`.
5. Then register the laptop (it needs a Face ID or Touch ID check with the iPhone's passkey, no code). Today's health line shows "2 passkeys, last added …".

---

## Phase 2: data pages (expand before building)

**Goal:** Bookings, Enquiries, Singers, Marketing, Calendar, Search, Reports, Runs and health, To-do; the static dashboard retires.

- **Task 2.1 `jobs.py` and the cache.** A refresh job (every 30 minutes, 07:00 to 22:00, in-process scheduler) writes `cache/{ads,ga4,gsc,books,drafts,calendar}.json` from `weekly_review`'s and `economics`' functions and a Books read client that mirrors `lcs_mcp`'s allowlisted read tools. Each cache entry stores `as_of` and the last error type. Tests: a failing refresher keeps the last good file and records the type.
- **Task 2.2 Bookings.** List with filters (upcoming, past, state) from the ledger and `check_payments.collect`; a timeline per booking (enquiry, quote, follow-ups, invoice, payments, singers, singer bills, review request, notes) and links to the Zoho thread and Books invoice. Tests: fixtures cover every state in `dashboard.STATES`.
- **Task 2.3 Enquiries.** Board by status (`pipeline.STATUS_ORDER`), follow-ups due, conversion (`pipeline.summary_dict`), source mix, timeline.
- **Task 2.4 Singers.** Directory from `singer-invoices.csv`: payee status (`singer_invoices.payee_status`), `••••last4`, invoices, total paid, last booking, warnings.
- **Task 2.5 Marketing.** Ads by campaign, cost per enquiry and booking (`economics.cost_table`), budget proposals, flagged search terms, the Search Console shortlist, GA4 leads, trends as inline SVG from `static/`-free markup.
- **Task 2.6 Calendar.** Month and week views: Google Calendar (cached, read-only), bookings, deposit and balance due dates (`check_payments.deposit_due_date`), follow-up dates.
- **Task 2.7 Search, Reports, Runs and health, To-do.** Search across bookings, clients, singers, enquiries, invoice numbers and refs; the archived Monday reports; the health checks (Starling selftest, ADC, MCPs, Tailscale status, disk, fingerprint-key backup age, last backup); `MANUAL-ACTIONS-REQUIRED.md` parsed, with ticks in a local file.
- **Task 2.8** Retire `dashboard.py` from the scheduled prompts (Appendices A and E) once the owner has used the app for a week.

## Phase 3: actions (expand before building)

**Goal:** the action registry, every write behind a passkey, append-only audit log.

- **Task 3.1 `actions.py`.** Each action: a name, a validator for its input, `preview(input) -> str` (the exact summary the passkey challenge binds), `argv(input) -> list[str]` (fixed script path, no shell). Runs with `subprocess.run(argv, shell=False, cwd=REPO, timeout=...)`; stderr trimmed and scrubbed with `lcs_mcp`'s rules; `audit.jsonl` appended (mode 600) before and after. Tests: exact argv per action, bad input refused, no `shell=True` anywhere (AST check).
- **Task 3.2 Routes.** `POST /actions/<name>/preview` returns the summary and assertion options; `POST /actions/<name>` needs `require_fresh_assertion(credential, action)`, where `action` is an `auth.Action` the registry built from the validated input (never text from the request), and the same-origin check. Tests: refused without, with a stale, a replayed, or another action's assertion.
- **Task 3.3 The actions.** Hand-check resolutions (`check_payments.py --note <ref> "<phrase> <date>" --owner`: add the `--owner` flag to `check_payments.py` first, test-first); singer confirm, settle and withdraw (`singer_invoices.py`); Ads approve (validate-only run, show output, second tap to apply; the scripts' £5 cap stays); run a scheduled task now (headless `claude -p` with the task prompt); refresh now; back up now; local records (draft sent or discarded, to-do ticks).
- **Task 3.4 Activity log page.** Every action and run from `audit.jsonl`, filterable.

## Phase 4: chat (expand before building)

**Goal:** Claude Code in the app under the repo's own guards.

- **Task 4.1 `chat.py`.** `claude-agent-sdk` with `cwd=REPO` and the repo's `.claude/settings.json` and hooks; a permission callback that turns any tool call outside the allowlist into an approve/deny card; approving needs a passkey bound to the card's summary.
- **Task 4.2 Streaming.** Server-sent events to `static/chat.js`; a stop button; a conversation list stored under `~/lcs-private/command-centre/chats/`.
- **Task 4.3 Quick prompts** and the queue for approved instructions (Books import, page fixes) from phase 3.
- Tests: a crashed chat leaves the other pages working; a denied card never runs the tool.

## Phase 5: PWA, push, drafts inbox, quote calculator, exports, backups (expand before building)

- **Task 5.1 PWA.** Manifest, service worker (no caching of data pages), icons.
- **Task 5.2 Push.** VAPID keys in the Keychain; `events.jsonl` watcher; `scripts/bookings/cc_event.py` (allowlisted) for the scheduled prompts; payload has a title and a first name only (tested).
- **Task 5.3 Drafts inbox.** From run summaries and a Zoho drafts read; "open in Zoho"; local sent/discarded marks.
- **Task 5.4 Quote calculator.** Prices parsed as `assistant_io.py prices` does; copyable wording in Luca's style.
- **Task 5.5 Backups.** Nightly `tar` + `age` of `~/lcs-private`, 14 kept, to iCloud Drive `LCS-backups/`; the health page warns after 36 hours; a documented restore.
- **Task 5.6 Security review** by a separate agent, adversarially, before go-live of the actions.

---

## Self-review (done while writing)

- **Spec coverage:** binding rule 1 (Task 1.2, Task 1.4), rule 2 (Task 1.2's machinery, Phase 3's use of it), rules 3 and 4 (Phase 3), rule 5 (Read this before starting, Task 1.4), rule 6 (Phase 4). Pages 1 and 4 in phase 1, pages 2, 3, 5, 6, 8, 10 to 13 and 15 in phases 2 and 3, 7 and 9 in phase 5, 14 in phase 4.
- **Consistency:** hand checks use `money_report.needs_hand_check` and `hand_check_label` through `dashboard.hand_check`, so the app, the dashboard and the Monday report agree.
- **Open assumptions:** the Money page in phase 1 shows the balance and the Monday lines; the 30-day in/out, Books receivables and monthly income against costs arrive with the phase 2 cache.
