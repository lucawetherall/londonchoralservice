# LCS Command Centre Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One private web app, reached only over the owner's tailnet, that shows everything about the business and (from phase 3) lets him act on it with a passkey. It replaces the static `scripts/reports/dashboard.py` page once phase 2 ships.

**Architecture:** `command_centre/` is a Starlette app served by uvicorn on `127.0.0.1:8765` only (or, optionally, a Unix socket in a mode-700 directory), and published to the tailnet by `tailscale serve`. Every request must come from a loopback peer with `Host` equal to the Mac's tailnet name (DNS rebinding); every request except `/healthz` must also carry the Tailscale identity headers for an allowed login; every write (from phase 3) also needs a WebAuthn assertion made in the last 60 seconds over a challenge bound to that action's summary. The data layer imports the existing read functions (`dashboard.py`, `check_payments`, `money_report`, `singer_invoices`, `pipeline`, `economics`, `weekly_review`) and never shells out to read. Pages are Jinja2 templates (autoescape on) with htmx served from `static/`, and nothing is loaded from any other origin.

**Tech Stack:**
- Python 3 in the repo's `.venv`: `starlette`, `jinja2`, `uvicorn`, `webauthn` (py_webauthn), pinned to exact versions with their dependencies in `scripts/requirements.txt`. Test-only: `httpx2` (Starlette's TestClient) in `scripts/requirements-dev.txt`, which `install.sh` never installs. Later, also pinned: `pywebpush` (phase 5). No `claude-agent-sdk`: Claude work is done through Claude Code Remote Control from the owner's phone, not an in-app chat (owner decision, 2026-09-28; PR #161 closed unmerged).
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
| `command_centre/models.py`, `sources.py`, `todo.py` | Pure page builders; cache, report and health readers; the to-do parser and tick store | 2 |
| `command_centre/actions.py` | The action registry: validated input, preview, fixed argv, audit log | 2 (the to-do tick), 3 |
| `command_centre/jobs.py` | Refresh jobs and caches, backups | 5 |
| `command_centre/static/handoffs.js` | Copy-to-clipboard handoff prompts for Claude Code Remote Control (no server-side execution) | 4 |
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

## Phase 2: read-only data pages, the to-do tick and exports (this PR)

**Goal:** Bookings, Enquiries, Singers, Marketing, Calendar, Search, Reports, Runs and health, To-do and Exports, all read-only apart from the to-do tick (a local record). Every page has the freshness stamp, every source is a `data.Panel` (a failing one shows `couldn't load (<TypeName>)` and the rest render), every value goes through Jinja's autoescape, and there is still no GET route with a side effect.

**Scope change from the first outline:** the refresh job (`jobs.py`, cache writers for Ads, GA4, Search Console, Books, drafts and the calendar) moves to phase 3, with "Refresh now". Phase 2 only *reads* caches that already exist (`ads-summary.json` and `gclid-campaigns.json`, which the Monday review writes) or that the later job will write (`command-centre/cache/calendar.json`). CSV exports move here from phase 5. Links to the Zoho thread and the Books invoice wait for the Books read client: phase 2 shows the thread id as text, and no page carries an external URL.

**Files:**
- `command_centre/models.py`: pure builders, no I/O (booking list and timeline, enquiry board and timeline, next follow-up date, singer directory, calendar, search, CSV rows, SVG chart geometry).
- `command_centre/sources.py`: the file readers (caches, reports, scheduled-task metadata, health checks), each reading at call time from `auth.private_dir()`.
- `command_centre/todo.py`: `MANUAL-ACTIONS-REQUIRED.md` parser and the tick store.
- `command_centre/actions.py`: the registry's first entry. `LocalAction(name, validate, preview, run, passkey=False)`; phase 3 adds the passkey actions to the same registry.
- `command_centre/data.py`: one `Data.<page>_page()` per page, wrapping the builders in panels.
- `command_centre/app.py`, `templates/*.html`, `static/app.css`: routes, pages, the bottom tab bar.
- `tests/test_cc_pages2.py`, with fake fixtures in a temp `LCS_PRIVATE_DIR`. `tests/test_cc_pages.py` loses its "soon" nav assertions.

### Task 2.1: Navigation

- [x] Every page is linked from the header nav (wide screens) and from `/more`. Below 720px the header nav hides and a fixed bottom tab bar shows Today, Bookings, Enquiries, Money and More; `/more` lists every page. The current page has `aria-current="page"` in both.

### Task 2.2: Bookings (`/bookings`, `/bookings/<ref>`)

- [x] **List:** every ledger row. Filters by query string: `when` = `upcoming` (default: event today or later, or no event date), `past` or `all`; `state` = one of `data.STATES` (unknown values are ignored). Each row: event date, ref, client first name, occasion, ensemble, value, payment state. The state comes from the phase-1 bank cache (`check_payments.collect` through `dashboard.payments`); a row it doesn't cover is `CANCELLED` (`cp.is_cancelled`), `CLOSED` (`cp.closed_on`) or its notes-only `cp.assess(row, [], today)` state, as `dashboard.upcoming` does.
- [x] **Timeline** (`ref` must match `^[A-Za-z0-9-]{1,20}$`, else 404), oldest first, undated items last:
  - enquiry rows with this `booking_ref` (`pipeline`): first seen (source), each `quoted YYYY-MM-DD` note with the package and amount, follow-ups sent, the thread id;
  - the invoice (ledger `invoice_date`, value);
  - the deposit due date (the assessment's `deposit_due`, from `cp.deposit_due_date`);
  - payments from the assessment (first confident payment, total received, each unconfirmed or flagged payment with its date);
  - ledger notes, split on `;`, dated when a clause holds a `YYYY-MM-DD`; review marks (`cp.REVIEW_NOTE`) are tagged "review"; emails and the client's other name words are masked (first names only);
  - singer invoices whose `event_date` field (when the store has one) equals the booking's event date; the store has no such field yet, so this shows "none linked" until it does;
  - "review request due" when `pipeline.reviews_due` lists the ref;
  - the event itself.

### Task 2.3: Enquiries (`/enquiries`, `/enquiries/<id>`)

- [x] Board: one column per `pipeline.STATUS_ORDER` status (id, occasion, event date, source, quote). Follow-ups due: `pipeline.followups_due(rows, today)`. Conversion: `dashboard.window` (so `pipeline.summary_dict`) for the season and the last 30 days. Sources: `summary_dict(...)["by_source"]`.
- [x] Timeline (`id` must match `pipeline.ID_RE`): first seen, quotes, follow-ups (count and last contact), the next follow-up date, the event, the status, the booking ref (linked), the campaign from `gclid-campaigns.json` when the click id is cached there (no Google call).
- [x] `models.next_followup(row, today)`: the date the next follow-up (or mark-lost) falls due, found by asking `pipeline.followups_due([row], day)` itself about the candidate day (last contact plus `FIRST_AFTER`/`SECOND_AFTER`/`LOST_AFTER`, or the event date if sooner), so the rules live in one place.

### Task 2.4: Singers (`/singers`)

- [x] Grouped by `singer_invoices.normalise_name`: first name, invoices (withdrawn ones listed apart), total paid (`paid_amount`, else `amount_gbp`, of rows with `paid_on`), unpaid total, last invoice date, payee status (`payee_status` of the newest row), bank `••••last4` of the newest row and its check (`is_trusted`: paid to verifiably or confirmed by phone; else not yet verified), warnings (`ring_first`, plus note clauses outside `KEEP_NOTES`), each invoice's bill number (`bill_number`, never a long digit run). Any run of six or more digits in shown text is masked.

### Task 2.5: Marketing (`/marketing`)

- [x] From `ads-summary.json`: "data as of" its `generated`; the last four weeks via `dashboard.ads` (spend, clicks, enquiries, cost per enquiry); the season per campaign (`season.campaigns`, `unattributed`, `total`: spend, clicks, enquiries, bookings, booked, cost per enquiry and per booking); an inline SVG bar chart of weekly spend with clicks as a line, drawn server-side (`models.bar_chart`), classes only, no `style=`, no library.
- [x] From `gclid-campaigns.json`: click ids traced per campaign (misses, keyed `gclid@date/days`, are left out).
- [x] Budget proposals, search terms, the Search Console shortlist and GA4 leads say "arrives with the refresh job (phase 3)".

### Task 2.6: Calendar (`/calendar?view=month|week&date=YYYY-MM-DD`)

- [x] Items: booking events (not cancelled), deposit due dates (open bookings still awaiting a deposit), balance due dates (three days before the event, check_payments' `BALANCE_DUE` rule, while a balance is outstanding), follow-up dates (`next_followup`), unbooked enquiries' event dates, and diary entries.
- [x] Month view: a Monday-first grid from 720px, an agenda list below it. Week view: seven days. Previous/next/today links; a bad `date` or `view` falls back to today/month.
- [x] **Calendar cache** (written by the phase-3 sync job; read-only here): `~/lcs-private/command-centre/cache/calendar.json`, mode 600:

  ```json
  [{"start": "2026-10-03T14:00:00+01:00", "end": "2026-10-03T16:00:00+01:00", "summary": "Wedding, St Mary's", "calendar": "LCS"},
   {"start": "2026-10-05", "end": "2026-10-06", "summary": "Day off", "calendar": "Personal"}]
  ```

  `start`/`end` are ISO dates (all-day, `end` exclusive) or ISO datetimes with an offset; `summary` and `calendar` are strings (trimmed to 120 and 40 characters). Invalid entries are skipped. No file: "diary not synced yet". The file's mtime is the "synced at" stamp.

### Task 2.7: Search (`/search?q=`)

- [x] Server-side, case-insensitive substring, `q` trimmed to 80 characters, at least 2. Across bookings (ref, the client's name, shown as the first name only), enquiries (id, occasion), singers (name, shown as the first name), singer invoice refs and bill numbers, ledger invoice numbers (the ref, with or without `INV`). Output escaped; the query is echoed escaped.

### Task 2.8: Reports (`/reports`, `/reports/<name>`)

- [x] `~/lcs-private/reports/*.txt` whose names match `^\d{4}-\d{2}-\d{2}\.txt$`, newest first. One report in a `<pre>`. A name that doesn't match, a symlink, anything that resolves outside the folder, or a file over 2 MB is a 404.

### Task 2.9: Runs and health (`/health`)

- [x] Scheduled tasks: the names and descriptions from the frontmatter of `~/.claude/scheduled-tasks/*/SKILL.md` (`CC_SCHEDULED_TASKS_DIR` overrides; read-only). That metadata has no run history, so the last-run proxies are the mtimes of `assistant-state.json` (with its `last_checked`), `ads-summary.json`, the newest report, `dashboard.html`, the ledger, the singer store and `enquiries.csv`; stale ones are flagged (assistant over 3 hours in the daytime, Monday review over 8 days).
- [x] Checks: Starling (`client.account()` only, cached 10 minutes, "not checked" without a token; the token is never read into the page), Google ADC (the file exists; never opened), the Zoho Mail and Books MCP servers (the server names exist under this repo's project in `~/.claude.json` or in `.mcp.json`; values are never kept or shown), `fingerprint.key` present and its backup age (a placeholder until phase 5's backups), free disk space, and the serving checkout's git branch. No "Run now" (phase 3).

### Task 2.10: To-do (`/todo`, `POST /todo/tick`)

- [x] `MANUAL-ACTIONS-REQUIRED.md`'s `## N. Title` sections, each with its first paragraph as plain text (markdown marks stripped). Ticks in `~/lcs-private/command-centre/todo.json` (mode 600, atomic, under a lock): `{"<N>-<slug>": {"done": true, "at": "<iso>"}}`.
- [x] The tick is the registry's first action, `todo-tick` (`actions.LocalAction`, `passkey=False`): the form posts only `key` and `done`; the key must be a section the parser finds now; the summary is built by the server ("tick to-do 21: Back up …"); the run writes `todo.json` and appends to `audit.jsonl` (mode 600). It passes the identity middleware's Host and same-origin (`Origin`, `Sec-Fetch-Site`) checks like any POST, and answers 303 to `/todo`. No passkey: it is low risk and touches private data only (the spec's actions table says so). `GET /todo/tick` is 405.

### Task 2.11: Exports (`/exports`, `/exports/<name>.csv`)

- [x] `bookings.csv` (ref, dates, first name, occasion, ensemble, value, state, received, balance), `singer-invoices.csv` (received, first name, bill number, amount, payee status, `••••last4`, flags, paid on and amount, withdrawn) and `pipeline.csv` (every `enquiries.csv` column except notes and gclid, plus the cached campaign). `Content-Disposition: attachment`, `Cache-Control: no-store`, cells starting `= + - @` prefixed with `'`. Any other name is a 404.

### Task 2.12: Tests, visual check, PR

- [x] `tests/test_cc_pages2.py`: each page renders with fixtures; filters; timelines; search escapes its input; report traversal refused; the CSVs carry no full bank number; the to-do tick needs the right Origin and Host (and GET is 405); a failing source is isolated on every page; the calendar without and with its cache; health prints no secret and never opens the ADC file.
- [x] Visual check on `127.0.0.1:8796` with fake data and the dev login, at 390px and 1280px, light and dark; screenshots in the scratchpad only; stop the server.
- [x] Every `tests/test_*.py`; commit; PR; don't merge.
- **Task 2.13 (after merge)** Retire `dashboard.py` from the scheduled prompts (Appendices A and E) once the owner has used the app for a week.

## Phase 3: passkey-gated actions and the activity log (this PR)

**Goal:** the action registry, every write behind a passkey (the to-do tick and "refresh data now" excepted), fixed argv lists with no shell, an append-only audit log, and an Activity page. These are the app's first writes to the ledger, the singer store and Google Ads, so each step below is test-first and the owner-only operations are closed to anything Claude can run unprompted.

**Scope changes from the outline:**
- **Run a scheduled task now** moves to phase 4. There is no reliable local trigger for a scheduled task (the task metadata has no run command, and a headless `claude -p` started from the app would sit outside the scheduler's own bookkeeping). Phase 4 has no chat to ask, so the app just explains: use Run now on the task in the Claude app (Routines).
- **Back up now** moves to phase 5 with the backup job itself.
- **Task 3.0, the 30-minute refresh job** (`jobs.py` writing `cache/{ads,ga4,gsc,books,drafts,calendar}.json`), moves to phase 5 with the other background jobs. Phase 3's "Refresh data now" re-runs `scripts/reports/dashboard.py` and clears the app's in-memory caches (the 10-minute bank cache and the Starling health check).
- **Approve the 2026 Books import** writes an approval record only. The app never calls Books.

**Files:**
- `command_centre/actions.py`: the registry (`LocalAction`, `ScriptAction`), validation, previews, argv lists, the runner, output scrubbing, the owner nonce, the audit log, the ads proposal checks.
- `command_centre/app.py`: `POST /actions/<name>/preview`, `POST /actions/<name>/run`, `GET /activity`.
- `command_centre/data.py`, `models.py`: invoice keys on singer rows, proposals and the Books approval on Today and Marketing, the activity reader.
- `command_centre/templates/*.html`, `static/actions.js`, `static/passkey.js`, `static/app.css`: action buttons, the preview dialog, the Activity page.
- `scripts/bookings/check_payments.py`: `--owner` (test-first).
- `tests/test_cc_actions.py` (new), `tests/test_check_payments.py`, `tests/test_prompt_allowlist.py`.

### Task 3.1: Owner-only protection, test-first

The allowlist entry `Bash(.venv/bin/python scripts/bookings/check_payments.py --note *)` also matches `--note X "paid in full …" --owner`, and `--reminded *` matches `--reminded X --note Y "…" --owner`. A glob can't exclude a flag, so the refusal lives in the script.

**Design: a one-time owner nonce, hashed on disk, delivered over a pipe.**

- Before the app runs `check_payments.py --note <ref> "<phrase> <date>" --owner`, it makes 32 random bytes (the nonce, hex), writes `sha256(nonce)` to `~/lcs-private/command-centre/owner-nonce` (`O_CREAT|O_EXCL|O_NOFOLLOW`, mode 600, directory 700) and passes the nonce itself on the child's stdin (a pipe). It deletes the file afterwards, whatever happened. Actions run one at a time (a lock), so there is only ever one nonce.
- `check_payments.py --owner` writes nothing unless all of these hold:
  - stdin is a pipe (`S_ISFIFO`), not a terminal and not a redirected file;
  - the nonce file is a regular file (opened with `O_NOFOLLOW`, so not a symlink), owned by this user, mode 600 with no group or other bits, and written in the last 60 seconds;
  - `sha256(first line of stdin)` equals the file's contents (constant-time compare).
  On a match it deletes the file (single use) before writing, and appends ` (owner)` to the note. Without `--owner` nothing changes: the owner-only phrases are still refused.
- **Why this design.** The barrier is the nonce file, not the pipe. A pipe on its own proves nothing (an allowlisted `*` pattern may match a piped command, and we don't rely on how compound commands are matched). What an allowlisted command can't do is produce the file: sha256 of a fresh nonce, mode 600, under 60 seconds old, in `~/lcs-private/command-centre/`. No allowlisted command writes there, and `.claude/settings.json` denies Claude's Write and Edit tools that folder (`Write(~/lcs-private/command-centre/**)`, `Edit(~/lcs-private/command-centre/**)`). Redirecting the nonce file itself (`< owner-nonce`) gives a regular file, not a pipe, and holds only the hash, whose hash doesn't match. With `--owner` the script also refuses `LCS_BOOKINGS_CSV` and a ledger outside the nonce's private folder, and the app sets `LCS_PRIVATE_DIR` explicitly, so the note lands in the ledger the app read. The nonce exists only in the app's memory and the pipe, for under a second. An environment token (`CC_OWNER_TOKEN`) was the alternative, but the script would still need a stored secret to compare it with, and an env prefix on the command line is easier to forge than a pipe plus a file. **Residual risk (accepted, as in the threat model):** a command the owner approves at a prompt, or any process running as the owner, can write its own nonce file and pipe the matching nonce. Such a process could edit the ledger directly anyway.
- **Singer confirm and settle, Ads apply:** no allowlist entry matches `singer_invoices.py confirm|settled` or any `scripts/ads/*.py --apply`, and no allowlisted command reaches them (argparse subcommands; no allowlisted script calls them). `tests/test_prompt_allowlist.py`'s NEVER list grows to cover them, and the `--owner` forms that the allowlist can't exclude are listed as SCRIPT_GUARDED, each tested to be refused by the script without the nonce.
- **The app's own argv lists** (`tests/test_cc_actions.py`): each registered action's argv, written as Claude would type it, must not be allowlisted, unless the action is on an explicit list with its reason: `refresh-data` (read-only; `dashboard.py` is allowlisted for the scheduled prompts), `singer-withdrawn` (the enquiry assistant may already withdraw a mis-sent invoice) and `resolve-hand-check` (allowlisted by `--note *`, refused by the script without the nonce).

- [x] **Step 1: Tests first** (`tests/test_check_payments.py`): `--owner` with no nonce file, a nonce file but stdin from `/dev/null` or a redirected file (even the nonce file itself), the wrong nonce, an old file (over 60 seconds), a group-readable file or a symlink are all refused and leave the ledger unchanged; the right nonce over a pipe writes `"<text> (owner)"` once and deletes the file; a second use is refused. Without `--owner`, the owner-only phrases are still refused.
- [x] **Step 2: Implement** `owner_confirmed()` in `check_payments.py`, and `--owner` in `main()`.
- [x] **Step 3:** Extend `tests/test_prompt_allowlist.py`: NEVER gains `singer_invoices.py confirm` and `settled` forms and three `scripts/ads/*.py --apply` forms; SCRIPT_GUARDED lists `--note X "paid in full 2026-09-28" --owner` and `--reminded X --note X "refunded 2026-09-28" --owner`.

### Task 3.2: The registry (`command_centre/actions.py`), test-first

- Each action: `name`, `validate(raw) -> cleaned` (strict: a dict of strings, unknown keys refused, every field checked against a pattern or a fixed choice and against the current private data), `preview(cleaned) -> str` (plain English, then `Runs: <argv as shown>`; this is the `auth.Action` summary the passkey challenge binds, so the challenge covers the exact command), `argv(cleaned) -> list[str]` (`sys.executable`, a fixed absolute script path under the repo, validated arguments), `passkey` (True for all but `todo-tick` and `refresh-data`), `timeout`.
- **Runner:** `subprocess.run(argv, shell=False, cwd=REPO, env=os.environ minus every CC_* variable with LCS_PRIVATE_DIR set explicitly (and LCS_BOOKINGS_CSV removed for the hand check), capture_output=True, timeout=…)`, stdin `/dev/null` except for the owner nonce. One action at a time: the lock is taken before validation, so every check is made under it; `refresh-data` has its own lock. No retries. Ads scripts run differently (Task 3.5).
- **Output:** stdout and stderr joined, scrubbed (lcs_mcp's approach: URLs become `<url>`; plus `token=…`-style values and long token-shaped strings become `<redacted>`, and any run of six or more digits becomes `••••••`), and trimmed to the last 6,000 characters. The audit keeps only the sha256 of the raw output.
- **Audit:** `audit.jsonl` (mode 600, append-only, written under an flock) gets a `started` line before a script runs and a result line after: `at`, `login`, `action`, `summary`, `input` (the cleaned fields), `result` (`ok`, `failed`, `refused: <reason>`), `exit_code`, `output_sha256`, `passkey` (the first 8 characters of the credential id), and `prev`, the sha256 of the line before (a hash chain; `verify_audit()` names any line that breaks it). A refused passkey is logged too, and so is a refusal before a summary exists (bad input, busy), with the action name and `input_sha256`. If the result line can't be written after a run, the output starts "ran, but the audit write failed".
- **Routes:** `POST /actions/<name>/preview` (JSON `{input}`) validates and returns `{summary, argv, passkey, options}`, where `options` are assertion options bound to `auth.Action(name, summary)`. `POST /actions/<name>/run` (JSON `{input, credential}`) validates again, rebuilds the summary from the data as it is now, calls `require_fresh_assertion(credential, action)`, then runs. Both pass the identity middleware's Host and same-origin checks. `todo-tick` keeps its form route; a registry action with no passkey (refresh) needs no credential.
- [x] **Step 1: Tests first** (`tests/test_cc_actions.py`): valid and invalid input for every action; the exact argv; no `shell=True` and no `os.system`/`os.popen` anywhere in `command_centre/` (AST check); a passkey is required, and a stale (over 60 seconds), replayed, other action's or other input's assertion is refused and nothing runs; audit lines written; output scrubbed; a timeout reported.
- [x] **Step 2: Implement.**

### Task 3.3: The actions

| Action | Input | argv | Passkey |
|---|---|---|---|
| `resolve-hand-check` | `ref` (in the ledger), `choice` (paid-in-full, deposit-kept, refunded, reinstated, cancelled, payment-checked, arranged-cash, arranged-cheque), `date` (ISO, not after today, not over two years back) | `check_payments.py --note <ref> "<phrase> <date>" --owner`, nonce on stdin. Phrases: `paid in full D`, `deposit kept D`, `refunded D`, `reinstated D`, `cancelled D`, `payment checked D`, `balance payable in cash on the day (arranged D)`, `balance payable by cheque on the day (arranged D)`, each tested against `check_payments` for what it means | yes |
| `singer-confirm` | `invoice` (a 12-letter key derived from the message id, so no long digit run reaches a page; must name one stored invoice with bank details not yet confirmed) | `singer_invoices.py confirm <message id> --expect-fp <bank_fp, all 16 characters>` (the summary shows the same 16; the script refuses anything but an exact match) | yes |
| `singer-settled` | `invoice` (open), `date` (ISO, not after today) | `singer_invoices.py settled <message id> <date>` | yes |
| `singer-withdrawn` | `invoice` (unpaid, not withdrawn), `reason` (`^[a-z][a-z-]{0,19}$`) | `singer_invoices.py withdrawn <message id> <reason>` | yes |
| `refresh-data` | none | `scripts/reports/dashboard.py`, then the app clears its bank and Starling caches | no (same-origin only) |
| `ads-validate` | `proposal` (an id in `proposals/`) | `python -E -s -B <run folder>/scripts/ads/<name>.py <args> --validate-only`, from its commit on GitHub's main, via the app's mirror (Task 3.5) | yes |
| `ads-apply` | `proposal` | the same, `--apply`, from the same commit | yes, a second tap |
| `approve-books-import` | none | no script: writes `approvals/books-import-2026.json` | yes |
| `todo-tick` | as phase 2 | local record | no |

- **Ads proposals:** `~/lcs-private/command-centre/proposals/<id>.json`, `{id, kind: "ads", title, summary, script_path, created, commit, script_blob, args?}`, written by the Monday review in future. Refused unless: the file is a regular file (no symlink), owned by this user, mode exactly 600, has no other field, its `id` matches the file name (`^[a-z0-9][a-z0-9-]{0,63}$`), `kind` is `ads`, `script_path` matches `^scripts/ads/[a-z0-9_]+\.py$`, `commit` and `script_blob` are full ids, and `args` (optional) is at most 12 simple tokens (`^[A-Za-z0-9][A-Za-z0-9._]{0,63}$`: never a flag, a path or a space). The commit, blob and running are Task 3.5. `ads-validate` records `{commit, blob, args, sha256 of the raw output}` (exit 0 only, kept 15 minutes, in memory); `ads-apply` is refused without that record or when any of the four changed, takes the record atomically when it starts (one apply per validate), and its summary names the commit, the blob and the validate output's hash, so the second passkey tap is bound to the output the owner saw. After a successful apply the app writes `proposals/<id>.applied` (mode 600: commit, blob, args, hashes, login, passkey); that proposal, and any other with the same blob and args, is no longer offered. The scripts keep their own £5 cap and write `logs/ads-changes.md` themselves.
- **Books import approval:** refused unless `~/lcs-private/books-import-2026.json` (the dry run, MANUAL-ACTIONS §20) exists; the summary names its sha256, entry count, total and first and last refs; the record `{approved_at, approved_by, passkey, dry_run_sha256, entries, total_gbp, first_ref, last_ref, instruction}` is written once (mode 600, directory 700). Phase 4's handoff prompt points a Claude Code Remote Control session at it, and that session must check the dry run's hash still matches.
- **Where:** hand checks on Today, Money and each booking's timeline; singer confirm, settle and withdraw on Singers and on the singer rows of Today and Money; ads proposals on Marketing, counted on Today with the Books approval; Refresh data now on Health.
- [x] Tests: every action's valid and invalid input and exact argv; the ads path checks (outside `scripts/ads/`, a symlink, untracked, modified, wrong mode, id mismatch: each refused); apply without a validate, after the blob changed, or twice: refused; one real run of `check_payments.py --note … --owner` through the full route against a temp ledger.

### Task 3.5: Adversarial review fixes (PR #158)

The reviewer showed that an Ads validate could run code that wasn't the committed script: an untracked module shadowing the stdlib in `scripts/ads/`, an uncommitted edit to a tracked helper, an ignored unchecked-hash `.pyc`, an edit hidden by `--skip-worktree` or `--assume-unchanged`, and a file swapped between the check and the run. Each proof of concept is now a regression test in `tests/test_cc_actions.py`.

- [x] **Immutable copy, from GitHub.** The app keeps a bare mirror at `~/lcs-private/command-centre/mirror.git` (mode 700, fixed config) and fetches `main` into it from the hard-coded `GITHUB_URL` at the preview and again at the run (https only, `protocol.file.allow=never`; a failure refuses: "couldn't verify against GitHub"). The commit must be an ancestor of that `main` (`git merge-base --is-ancestor`, in the mirror). The run folder is written from `git ls-tree -r <commit> -- scripts/` plus `git cat-file --batch` (no archive or checkout, so no filters), each file checked against its blob id, regular files only, into a fresh mode-700 folder under `~/lcs-private/command-centre/runs/`; the script runs with `python -E -s -B -X pycache_prefix=<empty folder>`, cwd that folder, and only HOME, PATH, LANG, TZ, GOOGLE_ADS_CONFIGURATION_FILE_PATH, LCS_PRIVATE_DIR, LCS_ADS_LOG (plus PYTHONNOUSERSITE=1, PYTHONDONTWRITEBYTECODE=1 and PYTHONPYCACHEPREFIX at that empty folder). The folder is removed afterwards. Every git call: `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, no caller `GIT_*`, `-c core.fsmonitor=false -c core.hooksPath=/dev/null`. Tests redirect the fetch with the module variable `actions.TEST_UPSTREAM`, never an environment variable.
- [x] **The change log.** `scripts/ads/ads_log.py` resolves `logs/ads-changes.md` from `LCS_ADS_LOG` (the app sets the repo's log) or relative to itself, and refuses to apply when the log has no table.
- [x] **Proposal-aware scripts only.** Validate passes `--validate-only`; old scripts fail at argparse, the natural allowlist. `scripts/ads/set_budget.py` is the first: a campaign id or exact name and a daily amount, refused above £5 before Google is called, validate-only by default, `--apply` logs (`tests/test_set_budget.py`, a fake client).
- [x] **The preview shows git's facts and the code**: the script's last change on main as a diff (6,000 characters at most, its sha256 in the signed summary) and a GitHub link to the file at that commit; path, commit, on main at GitHub, who last changed the script and when, and its docstring; Claude's title and summary labelled "Claude's description" (also on Marketing). The action hash now covers the action's name as well as its summary.
- [x] **Ads output** is shown unmasked (secrets still redacted): the first and last 3,000 characters.
- [x] **Owner nonce:** `check_payments.py --owner` refuses `LCS_BOOKINGS_CSV` and a ledger outside the nonce's private folder; deny rules for Claude's Write and Edit tools on `~/lcs-private/command-centre/**`.
- [x] **Locking:** the action lock before validation; `.applied` re-checked inside it; the validate record popped atomically; refresh on its own lock.
- [x] **Audit:** refusals at the run step logged with the action name and an input hash; a hash-chained log; "ran, but the audit write failed" when the result line can't be written.
- [x] **Singer confirm** bound to the fingerprint (`--expect-fp`, tested in `tests/test_singer_invoices.py`); `confirm` stays off the allowlist.
- [x] **Books:** the preview shows the total and the first and last refs; the record carries the login and passkey.

### Task 3.4: UI

- [x] `static/actions.js` (no inline code): a button in a `form.cc-action` posts the form's fields to `/actions/<name>/preview`, shows a `<dialog>` with the plain-English summary and the argv, then **Approve with Face ID or Touch ID** (`navigator.credentials.get` with the returned options, through `passkey.js`'s helpers, which it now exposes as `window.LCSPasskey`), then the result: exit code and the scrubbed output. A result may offer a next step (validate, then apply).
- [x] `GET /activity`: `audit.jsonl`, newest first, the last 1,000 lines, filterable by action, result and text; any six-digit run masked; a malformed line skipped.

### Task 3.5: Visual check and PR

- [x] Fake data on `127.0.0.1:8795` with the dev login: the dialogs up to the passkey step (a dev browser has no passkey), at 390px and 1280px; the assertion is covered by the unit tests with a software authenticator. Stop the server.
- [x] Every `tests/test_*.py`; commit; PR; don't merge.

## Phase 4: Handoffs (done)

**Goal:** no in-app chat and no server-side execution of Claude tool calls. Claude work is done through Claude Code Remote Control from the owner's phone; the app's job is only to put a correct, useful prompt on the clipboard.

- **Task 4.1 Books import handoff.** When `~/lcs-private/command-centre/approvals/books-import-2026.json` exists and its `dry_run_sha256` still matches the current dry-run list, Today and Marketing show a "Copy prompt for Remote Control" button. It copies a fixed, server-written instruction naming the two files, the approval hash and the guard doc (`docs/superpowers/specs/2026-09-28-zoho-books-design.md`), asking Claude Code to check the hash, create each invoice as a draft under the guard, and report. It never includes any record's own text (client names, amounts, refs).
- **Task 4.2 Run a scheduled task now.** Not an app action: Runs and health explains "Use Run now on the task in the Claude app (Routines)". No button, nothing to copy.
- **Task 4.3 Quick prompts.** Fixed copy-to-clipboard buttons naming the relevant scripts and files: "What's owed this week?", "Summarise today's business", "Why is `<ref>` on the hand check?" (with a ref picker filled from the current hand-check list), "Draft a reply to `<thread>`" (from Bookings/Enquiries thread ids). Each prompt is built entirely server-side from fixed templates plus the chosen ref/thread id; no free text from the page reaches the prompt.
- **Task 4.4 UI.** `static/handoffs.js` (no inline code, CSP self-only): `navigator.clipboard.writeText`, with a fallback that selects a `<textarea>`/`<pre>` holding the text for a manual copy when the Clipboard API is unavailable or refuses (not a secure context, permission denied). Copying needs no passkey and is not a registered action: nothing runs, nothing is sent to the server beyond the page load that rendered the fixed text.
- Tests: each quick prompt's exact text for known fixtures; the Books import button appears only when the approval file exists and its hash matches, and disappears (or shows why) when the dry run has moved on; the ref picker only offers refs currently on the hand check; no handoff route accepts free text from the client into the copied prompt; `handoffs.js` contains no `eval`, inline handler or non-`self` fetch.

## Phase 5: installable app, push notifications, encrypted nightly backups (this PR)

**Goal:** the app installs on the iPhone's Home Screen and shows Today and Money offline; the owner gets a push notification for the events that need him; `~/lcs-private` is backed up every night, encrypted, with 14 days kept.

**Access (owner decision):** Tailscale only, and the phone does not keep the VPN on. The owner opens the app with an iPhone Shortcut that connects Tailscale and then opens the ts.net URL. Web Push reaches the phone through Apple's push service with the VPN off; the Mac sends it over its normal internet connection, never through the tailnet. With the VPN off the Home Screen app shows the cached Today and Money pages, marked "Couldn't reach the Mac (showing the copy from <time>)", after at most a 4-second wait (copies over 7 days old are refused; a 401/403, "Clear offline copies" or turning notifications off deletes them).

**Scope changes from the outline:**
- The drafts inbox (5.3), the quote calculator (5.4) and the 30-minute refresh job (5.0) move to a later PR; this one is the PWA, push and backups.
- The service worker caches the last Today and Money pages for offline viewing (the outline said no data pages): the owner wants them with the VPN off. Nothing else is cached, and no write.
- The backup recipient (a public key, not a secret) lives in the config rather than the Keychain, so the nightly run from launchd needs no Keychain prompt. The identity (the private key) is printed once by `init` and never stored.

**Files:**
- `command_centre/push.py`: VAPID keys (Keychain), subscriptions (config), the payload builder, the `events.jsonl` watcher and the stale-run check.
- `command_centre/pwa.py`: the manifest and the icons (pure-Python PNG: Pillow isn't in the venv); `static/sw.js`, `pwa.js`, `push.js`, `icons/*.png`.
- `command_centre/app.py`: `GET /manifest.webmanifest`, `GET /sw.js`, `GET /device`; the watcher in the app's lifespan (the service only). `auth.py`: `worker-src 'self'` in the CSP.
- `command_centre/actions.py`: `push-subscribe` (passkey), `push-unsubscribe` and `backup-now` (no passkey, same-origin), each on its own lock.
- `command_centre/sources.py`, `data.py`, `templates/health.html`: the backup age.
- `scripts/reports/cc_event.py` (allowlisted), `scripts/reports/cc_backup.py` (not allowlisted).
- `command_centre/install.sh`: `--backup` installs the `com.lcs.backup` LaunchAgent (02:30 nightly); the owner steps for Tailscale, the Shortcut and notifications in its output.
- Handover Appendices A and E: one `cc_event.py` line where each event happens. `.claude/settings.json`: the allowlist entry.
- Tests: `tests/test_cc_pwa.py`, `tests/test_cc_push.py`, `tests/test_cc_backup.py`; `tests/test_prompt_allowlist.py` keeps passing.

### Task 5.1: PWA

- [x] `GET /manifest.webmanifest` (`application/manifest+json`): name "LCS Command Centre", short name "LCS", `display: standalone`, start URL and scope `/`, theme `#8B3A3A`, background `#F7F3EE`, icons 180, 192, 512 and a maskable 512, PNG files in `static/icons/` drawn by `pwa.py` (a drift test redraws them). No external asset.
- [x] `GET /sw.js` (`application/javascript`, `Service-Worker-Allowed: /`, `no-store`), scope `/`. It caches the app shell (CSS, JS, icons) and the last copy of `/` and `/money` (exact paths, no query, a 200 HTML answer only). Those two pages are fetched with a 4-second timeout; when the network fails or is slow (Tailscale off) the saved copy is served with a banner "Couldn't reach the Mac (showing the copy from <time>)"; a copy over 7 days old is deleted instead, a 401 or 403 deletes both, and a same-origin `{type: "clear-offline"}` message deletes them. Any method but GET returns before the worker touches it, so it never sees, caches or replays a POST; `/actions/`, `/auth/`, exports and every other page are never cached. On push it shows the title and body (truncated); a tap opens the payload's path when it is a same-origin path, else `/`.
- [x] `base.html`: the manifest link, `theme-color`, the Apple touch icon, `pwa.js` (registers the worker) and an install hint in iOS Safari when the app isn't installed yet.
- [x] CSP: `worker-src 'self'` and `manifest-src 'self'`; the rest unchanged.

### Task 5.2: Push

- [x] `pywebpush==2.5.0` pinned with its dependencies. **VAPID keys:** a P-256 key made once with `cryptography`, its private scalar (hex) stored with the `security` CLI under the Keychain service `lcs-command-centre-vapid` (added through `security -i` on stdin, so the key never appears in a process list; read with `find-generic-password -w` from the app's own process, never by Claude). For tests and the local visual check only, `CC_VAPID_STORE=file` switches to `<private>/command-centre/vapid-test.json` (mode 600).
- [x] **Subscribe** is `push-subscribe` in the registry: input `endpoint`, `p256dh`, `auth`. The endpoint must be `https://` on a known push service (Apple, Google, Mozilla, Microsoft) with no port, user info or fragment, so the app can't be made to POST anywhere else. The summary names the push service and a hash of the device key; the owner approves it with a passkey (a new device receiving business information). Stored in the config's `push_subscriptions` (id = the first 16 hex characters of sha256(endpoint), when, login, passkey id). **Unsubscribe** is `push-unsubscribe` (input `id`), no passkey: it only narrows who is told. Both pass the Host and same-origin checks and are audited.
- [x] **Events:** `scripts/reports/cc_event.py <kind> --<field> <value> …` appends `{"at", "kind", "fields"}` to `~/lcs-private/command-centre/events.jsonl` (mode 600, directory 700, under an flock). Kinds and fields: `enquiry --first --occasion --date`, `deposit --first --ref`, `hand-check --ref --state`, `bank-change --first`, `guard-denied --agent`, `run-failed`, `monday-ready`; no free text. A first name is `^[A-Z][a-z'’-]{1,20}$`, a ref `^[A-Z0-9-]{3,20}$`, the rest fixed lists or an ISO date. The app re-validates and builds each notification from a fixed template (security review fixes).
- [x] **Payload:** `{"title", "body", "url"}` only. The title and the page come from the kind (a fixed table); the body is the event's text, scrubbed again, with every known client and singer surname removed (ledger, pipeline, singer store), at most 80 characters.
- [x] **Sending:** pywebpush over the Mac's normal internet connection (a `requests` session with no proxy from the environment and a 10-second timeout; the push services are public hosts, never tailnet addresses).
- [x] **Watcher** (the service only, never on a dev port): every 20 seconds it reads new lines from `events.jsonl` (from the end of the file on its first start, so history isn't replayed; the offset lives in `push-state.json`), pushes each to every subscription (a 404 or 410 drops that subscription) and runs the stale-run check.
- [x] **Stale run:** between 08:00 and 21:00 London time, if `assistant-state.json` hasn't changed for more than 3 daytime hours (21:00 to 08:00 doesn't count, so the first run of the morning isn't late), push "Enquiry assistant not seen" once per stale file.
- [x] **This device** (`/device`, from More and the footer): the install steps (Shortcut included), this device's notification state, **Enable notifications** (asks permission and subscribes; a second tap approves it with Face ID or Touch ID), **Turn off on this device**, and the subscribed devices with a remove button each.

### Task 5.3: Backups

- [x] `pyrage==1.4.0` (the age format; no CLI needed to make or check a backup). `scripts/reports/cc_backup.py`:
  - `init`: makes an age X25519 identity, saves the recipient (public key) in the config's `backup.recipient`, and prints the identity once for the password manager. It never writes the identity anywhere. Refused if a recipient exists, unless `--replace`.
  - `run` (the LaunchAgent and "Back up now"): a tar.gz of `~/lcs-private` without the backups themselves, `command-centre/runs/`, `command-centre/cache/` and `command-centre/mirror.git`, nor sockets or other special files, built in an unlinked temp file, encrypted to the recipient, written as `lcs-backup-YYYYMMDD-HHMMSS.tar.gz.age` (mode 600) through a `.part` file and a rename. Then backups older than 14 days go (only files with that exact name pattern, regular files, never the newest). `command-centre/backup-state.json` records the time, name, size and sha256. One run at a time (flock).
  - `verify`: reads the identity from stdin (hidden when typed), decrypts the newest backup in memory and prints its listing. Nothing is extracted.
  - Target: the config's `backup.target`, default `~/Library/Mobile Documents/com~apple~CloudDocs/LCS-backups`.
- [x] Health shows the last backup's age and warns after 36 hours (or when there is none, or no recipient); the fingerprint key row points at it.
- [x] `backup-now` in the registry: `cc_backup.py run`, no passkey, same-origin (CSRF) required, its own lock, a 15-minute timeout.
- [x] `install.sh --backup` writes and loads `com.lcs.backup` (02:30 daily), refused until `init` has set a recipient.
- **Restore:** `brew install age`, then `age -d -i key.txt lcs-backup-….tar.gz.age | tar -xz -C ~/restore-check` (key.txt holds the identity, typed from the password manager and deleted afterwards). `cc_backup.py verify` checks a backup without extracting it.

### Task 5.4: Wiring

- [x] `.claude/settings.json` allows `Bash(.venv/bin/python scripts/reports/cc_event.py *)`.
- [x] Appendix E: a new enquiry recorded (3a), a receipt drafted (5a), a bank-change warning (4), a Books guard denial (3.iii and 4a), a hand check (5a); Appendix A: the Monday review ready. One `cc_event.py` line each; Appendix E's command list names each kind it uses. `tests/test_prompt_allowlist.py` passes.

### Task 5.5: Tests, visual check, PR

- [x] `tests/test_cc_pwa.py`: manifest and worker served with their headers; the CSP; the worker's GET-only early return, its cache list and its 4-second timeout (a static check of `sw.js`); the icons valid and in step with `pwa.py`; the base template's links.
- [x] `tests/test_cc_push.py`: subscribe needs a passkey (refused without one, with a stale one or another action's); the endpoint allowlist; unsubscribe; the payload has only title, body and url and no surname, email or long number; events → pushes (a fake pywebpush); a 410 drops the subscription; no replay of history; the stale-run window; `cc_event.py` kinds, length and file mode; the VAPID file store and the Keychain calls (a fake `security`).
- [x] `tests/test_cc_backup.py`: excludes, retention, an encryption round trip with a test key, `verify` from stdin, the identity never on disk, Health's age and warning, `backup-now` with no passkey.
- [x] Visual check on `127.0.0.1:8792` with fake data (the manifest link, the install hint, Health's backup line); stop the server.
- [x] Every `tests/test_*.py`; commit; PR; don't merge.
- **Task 5.6 (next):** a security review by a separate agent, adversarially, before relying on push.

### Owner steps after merge (phase 5)

1. `git pull` in the main checkout, then `bash command_centre/install.sh` (it installs the new pinned packages and restarts the app).
2. **Tailscale admin console → DNS:** turn on MagicDNS and HTTPS certificates. The Home Screen app and Web Push need the real ts.net certificate.
3. **Install:** on the iPhone, with Tailscale connected, open `https://<mac>.<tailnet>.ts.net/` in Safari, Share → Add to Home Screen.
4. **Shortcut "LCS":** in the Shortcuts app, a new shortcut with two actions: Tailscale → Connect, then Open URL `https://<mac>.<tailnet>.ts.net/`. Add it to the Home Screen: it is the main way to open the app. Optional second shortcut: Tailscale → Disconnect.
5. **Notifications:** open the installed app, More → This device, tap **Enable notifications**, allow them, then **Approve this device** with Face ID. macOS may ask once whether python may use the `lcs-command-centre-vapid` Keychain item: Always Allow. Notifications arrive with the VPN off, through Apple's push service; tapping one opens the app (connect Tailscale first, or use the Shortcut, to see live data).
6. **Offline:** with the VPN off, the Home Screen app shows the last Today and Money pages it saw, marked "Couldn't reach the Mac (showing the copy from <time>)". Actions need the VPN.
7. **Backups:** `.venv/bin/python scripts/reports/cc_backup.py init`; store the printed `AGE-SECRET-KEY-…` line in the password manager (shown once, kept nowhere else). Then `bash command_centre/install.sh --backup` for the 02:30 LaunchAgent. Tap **Back up now** on Health once, and check it with `.venv/bin/python scripts/reports/cc_backup.py verify` (paste the key). If the run says "Operation not permitted", macOS is blocking iCloud Drive for background processes: give `.venv/bin/python` Full Disk Access, or set `backup.target` in the config to another folder.

---

## Phase 6: final wiring (this PR)

**Goal:** the data the scheduled runs already cache reaches the pages (Books, margins, the diary), and the three features deferred from phase 5 land: the drafts inbox, the quote calculator and the 30-minute background refresh. Nothing new writes outside `~/lcs-private/command-centre/`, and nothing new needs a passkey: the only new write is a local draft mark.

**Files:**
- `command_centre/models.py`: pure builders for the Books panel, the Books/Starling flags, a booking's Books and singer lines, the margin columns and the season total.
- `command_centre/data.py`: the new panels (`books`, `books_flags`, `margins`, `season_margin`, `drafts`), each failing on its own.
- `command_centre/drafts.py`: reads `cache/drafts.json` and the local marks (`drafts-marks.json`).
- `command_centre/quote.py`: the calculator over `assistant_io.PriceParser`'s rows.
- `command_centre/jobs.py`: the background refresh job.
- `command_centre/actions.py`: `draft-mark` (a LocalAction, no passkey, same-origin, audited).
- `command_centre/app.py`, `templates/`: Money's Books panel and season total, Today's Books flags, the Bookings margin columns, the timeline's Books status, singers and margin, `GET /drafts`, `GET /quote`.
- `scripts/reports/cc_sync.py`: `drafts-put '<json>'`. `scripts/bookings/assistant_io.py`: `PriceParser` also keeps structured rows (its text output is unchanged).
- `.claude/agents/lcs-reply-drafter.md`, `lcs-daily-pass.md`, `lcs-singer-clerk.md`: one `cc_sync.py drafts-put` line per saved draft (already allowlisted by `cc_sync.py *`).
- `tests/test_cc_final.py`.

### Task 6.1: Books on the pages (R17)

- [x] **Money:** a Books panel from `cache/books.json` (`books_cache.books_cache()`): receivables (count and £), overdue, drafts not yet sent (invoice numbers), unpaid bills (count and £), and "Books as of <generated_at>". No cache yet says "Books not synced yet: the daily pass runs `cc_sync.py books`".
- [x] **Timeline:** the booking's Books invoice, matched by invoice number = booking ref: its status, total and balance, dated by the invoice date. None: "Not in Books".
- [x] **Today:** the Appendix A step 6g rules, as flags in "Needs you" (and in the attention count): a Books draft more than 2 days old ("Books draft not sent (>2 days)"); Books paid but Starling hasn't matched the full fee (the state isn't PAID_IN_FULL and there is no "paid in full" note); Starling matched (DEPOSIT_SEEN, PAID_IN_FULL or a "paid in full" note) but Books unpaid or overdue with nothing paid, or part-paid when Starling says paid in full. The two Starling comparisons are skipped when the bank wasn't checked, as 6g skips them.

### Task 6.2: Margins (R18)

- [x] Bookings list and timeline: fee, singer costs, margin and margin % from `singer_invoices.margins()` over the same ledger and store the pages read.
- [x] Money: the season total (bookings from `season_start`, cancelled ones left out): fee, singer costs, margin, margin %.
- [x] Timeline: the singers linked to the booking (the store's `booking_ref`), first names only, with each invoice's amount and paid state.

### Task 6.3: Calendar

- [x] `cc_sync.py calendar-put` writes `<private>/command-centre/cache/calendar.json`, a JSON list of `{start, end, summary, calendar}`; `sources.calendar_cache()` reads that path and `models.diary_items()` that shape. A round-trip test pins it.

### Task 6.4: Drafts inbox

- [x] `cc_sync.py drafts-put '<json>'`: one object or a list of at most 50, each exactly `{thread_id, kind, first_name, subject, created}`: a thread id of 1 to 40 letters and digits, a kind from a fixed list, a first name as `cc_event.py` takes it, a subject of at most 80 characters with no control characters, a created date YYYY-MM-DD. Anything else refuses the whole input and writes nothing. Merged into `cache/drafts.json` (same thread and kind replaces), newest 500 kept, under an flock, atomically at mode 600.
- [x] The reply drafter, the daily pass and the singer clerk run it once per saved draft.
- [x] `GET /drafts`: the open drafts (newest first) and the marked ones, with "Open Zoho Mail drafts" (`https://mail.zoho.com/zm/#mail/folder/drafts`: the owner's account is on Zoho's .com data centre, per the handover's Appendix C and the MCP hosts on zohomcp.com).
- [x] `draft-mark` (sent or discarded): a local record in `<private>/command-centre/drafts-marks.json`, no passkey, same-origin, audited. A draft is named by a 12-letter hash of its thread, kind and date, so no thread id reaches a form.

### Task 6.5: Quote calculator

- [x] `GET /quote` (a GET form: nothing is written). The packages, the organist add-on and the soloist-with-organist combination come only from `pricing.html` and `christmas-pricing.html`, parsed by `assistant_io.PriceParser`. Pick the price list, a package (its number of singers shown), an organist and whether the venue is outside Greater London (travel "confirmed with the quote", no figure), and for Christmas Eve or Christmas Day the page's premium sentence (no figure added).
- [x] The output: the total and copyable wording in the house style: UK English, "No VAT is added." and no other VAT wording, no roster size.
- [x] Tests: the parsed figures equal the pages' (Small Choir £1,150, organist £250, Small Choir + organist £1,400, soloist + organist £450).

### Task 6.6: Background refresh

- [x] `command_centre/jobs.py`: in the service's lifespan (never on a dev port, and off when `CC_NO_REFRESH_JOB` is set), every 30 minutes from 07:00 to 22:00 London time: `dashboard.py` then `cc_sync.py books` as subprocesses (argv, no shell, the actions' clean environment, a timeout each), then the bank cache is cleared. Its own lock, and it takes the manual refresh's lock without waiting, so the two never overlap (a slot that finds either busy is skipped). A failure goes to the audit log as `refresh-job` with its type name only.

### Task 6.7: Roadmap, tests, visual check, PR

- [x] R17 and R18 marked done; anything newly deferred added.
- [x] `tests/test_cc_final.py`; every `tests/test_*.py` with temp env vars.
- [x] Visual check on `127.0.0.1:8791` with fake data at 390px and 1280px, light and dark; stop the server.
- [x] Commit, PR, don't merge.

---

## Self-review (done while writing)

- **Spec coverage:** binding rule 1 (Task 1.2, Task 1.4), rule 2 (Task 1.2's machinery, Phase 3's use of it), rules 3 and 4 (Phase 3), rule 5 (Read this before starting, Task 1.4), rule 6 (Phase 4). Pages 1 and 4 in phase 1, pages 2, 3, 5, 6, 8, 10 to 13 and 15 in phases 2 and 3, 7 and 9 in phase 5, 14 in phase 4.
- **Consistency:** hand checks use `money_report.needs_hand_check` and `hand_check_label` through `dashboard.hand_check`, so the app, the dashboard and the Monday report agree.
- **Open assumptions:** the Money page in phase 1 shows the balance and the Monday lines; the 30-day in/out, Books receivables and monthly income against costs arrive with the phase 2 cache.
