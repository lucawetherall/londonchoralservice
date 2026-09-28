# LCS Command Centre: design

**Date:** 2026-09-28

**Status:** Approved by the owner. Access is over Tailscale; the Mac is always on. All features are in, and the owner sees full detail, because the app is private to him.

**Related:**
- [Business automation programme](2026-09-28-business-automation-design.md)
- [Zoho Books design](2026-09-28-zoho-books-design.md)
- `scripts/reports/dashboard.py`: the static page this app replaces.

---

## Goal

One private web app, on any of the owner's devices, that shows everything about the business and lets him act on it: approve proposals, resolve checks, confirm singer bank details, and talk to Claude Code. It is not tied to Claude: the chat is one module that can be swapped out.

## Binding rules

These are the programme's rules, plus:

1. **No public internet.** The server binds to 127.0.0.1 only and is exposed only via `tailscale serve` (the tailnet, over HTTPS). Every request must carry Tailscale identity headers (`Tailscale-User-Login`) matching the owner's login from config. Anything else gets a 403, including requests from the Mac itself when the header is missing, except the health check.
2. **Two levels of trust.**
   - Viewing needs the owner's Tailscale identity.
   - Every action (anything that writes) also needs a fresh WebAuthn passkey assertion (Face ID or Touch ID), made within the last 60 seconds and bound to that specific action's summary.
3. **Actions reuse the guarded paths.** Each action calls an existing script or guarded tool with fixed arguments, never a new path. It shows exactly what will happen first, and it is logged, append-only, in `~/lcs-private/command-centre/audit.jsonl`.
4. **Money never moves from the app.** It never sends email, never makes a payment or payee, and never deletes. The owner still presses Send in Zoho or Books, and pays in Starling.
5. **Private data stays on the Mac.** It lives in `~/lcs-private` only (mode 600 files, 700 directories). The repo holds code only, never data, and nothing is published. The app stores no credentials of its own: it uses the Keychain, the existing MCP config and ADC.
6. **Claude Code chat keeps the repo's guards.** It runs with the repo's `.claude/settings.json`, hooks and allowlist. Tool calls outside the allowlist become approve/deny cards, and approving one needs a passkey.


## Threat model

- **Who it defends against:**
  - other devices on the tailnet or the local network: the app listens on loopback only and refuses any other peer address;
  - web pages in the owner's browsers: the Host must be the Mac's tailnet name (DNS rebinding), POSTs must be same-origin, and every write needs a passkey;
  - a stolen or forged Tailscale identity: writes still need a passkey;
  - someone who reaches the page before the owner registers: the first passkey needs a one-time bootstrap code that `install.sh` prints (sha256 stored, 30 minutes, deleted on use).
- **Accepted risk: other processes on the Mac.** This is a single-user Mac. Any process running as the owner can connect to 127.0.0.1:8765 and send any headers, so it can read the pages as the owner. It can't make a write, because that needs a passkey assertion from the owner's Face ID or Touch ID. Such a process could already read `~/lcs-private` directly, so the app adds no new exposure. The optional Unix socket (`python -m command_centre --uds`, in a mode-700 directory) narrows this to processes of the same user, which are the same set; it is offered in `install.sh` as an alternative to verify, not the default.
- **Claude sessions in this repo (the adversarial review of phase 3).** A Claude session can write anywhere in the working tree, write proposal files, and run the allowlisted commands without a prompt. None of that may turn into a write the owner didn't approve:
  - *Ads scripts run from the app's own mirror of GitHub's main.* A proposal pins a commit, the script's blob at that commit and its arguments (simple tokens only). The app keeps a bare mirror, `~/lcs-private/command-centre/mirror.git` (mode 700; its config rewritten to a fixed one and any alternates, grafts or attributes removed each time), and fetches `main` into it from a hard-coded URL, `https://github.com/lucawetherall/londonchoralservice.git`, at the preview and again at the run, with only https allowed (`protocol.file.allow=never`). A failed fetch refuses ("couldn't verify against GitHub"). The commit must be an ancestor of that freshly fetched `main`. The working repo is never read: not its refs (a local commit with `git update-ref refs/remotes/origin/main` changes nothing), not its config (no smudge filter or attributes apply), not its remote URL. The run folder is written from `git ls-tree -r <commit> -- scripts/` and `git cat-file --batch` in the mirror, with no checkout or archive and so no filters; each file's bytes are checked against its blob id; only regular files are written (no symlinks, no submodules), exclusively and never through a symlink, into a fresh mode-700 folder. The script runs with `python -E -s -B`, no bytecode from anywhere else and an allowlisted environment (HOME, PATH, LANG, TZ, the Ads config path, LCS_PRIVATE_DIR, LCS_ADS_LOG). Every git call runs with `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_NO_REPLACE_OBJECTS=1`, none of the caller's `GIT_*`, and `-c core.fsmonitor=false -c core.hooksPath=/dev/null`. The reviewers' proofs of concept (untracked shadows, uncommitted or hidden edits, `__pycache__`, a swapped file, smudge filters, a moved origin ref, a fork's URL, a committed symlink) are regression tests. `ads_log.py` refuses a log that isn't a repo's own `logs/ads-changes.md` or is reached through a symlink.
  - *Proposal-aware scripts only.* Validate passes `--validate-only`, which old scripts refuse at argparse, so only scripts written for the app (the first is `scripts/ads/set_budget.py`) can reach apply. Apply runs from the same commit, blob and arguments as the validate run and is bound to its output hash; the validate record is taken atomically, once. A blob and arguments once applied are refused under any proposal id.
  - *The owner sees git's facts, not only Claude's words.* The preview is written by the server from git: path, commit, who last changed the script and when, whether the commit is on main at GitHub, and the script's own docstring, plus the script's last change on main as a diff (`git diff <commit>^ <commit> -- <path>` from the mirror, up to 6,000 characters, its sha256 in the signed summary) and a link to the file at that commit on GitHub. Claude may merge its own pull requests, so the owner reads the code, not a description of it. Claude's title and summary appear labelled "Claude's description".
  - *The owner nonce.* The barrier for `check_payments.py --owner` is the nonce file (sha256 of the nonce, mode 600, under 60 seconds old, in `~/lcs-private/command-centre/`): no allowlisted command writes there and `.claude/settings.json` denies Claude's Write and Edit tools that folder. A pipe on its own is not the barrier. With `--owner`, the script also refuses `LCS_BOOKINGS_CSV` and any ledger outside the nonce's private folder; the app sets `LCS_PRIVATE_DIR` explicitly for its subprocesses.
  - *Singer confirm is bound to the bank details.* The summary shows the whole 16-character bank fingerprint and the app passes it as `--expect-fp`, which must match exactly; `singer_invoices.py confirm` refuses on a mismatch, so a rescan between approval and run confirms nothing. `confirm` stays off the allowlist.
  - *Checks under one lock, and a tamper-evident log.* The action lock is taken before validation, so the `.applied` check and the validate record are read under it. Refusals at the run step are logged with the action name and a hash of the input. Each audit line carries the sha256 of the line before it; Activity shows whether the chain is whole, its line count and the last line's hash, and each `.applied` record stores that hash as it stood after the apply. If the `.applied` record can't be written after a successful apply, the result says "applied, but the record couldn't be saved: DO NOT re-apply" and an in-memory marker refuses the change set until the app restarts. `.claude/settings.json` denies `git update-ref`, `git remote set-url`, `git config` and edits under `.git/`.
  - **Residual risk (accepted):** code on GitHub's `main` is trusted. Getting a script there takes a merged pull request, and Claude may merge its own; the owner's passkey tap, after reading the diff and git facts in the preview, is the last check. The preview shows the script's own last change only: a change to a sibling module in `scripts/` that the script imports is not in that diff, so the link to the commit is there to read further.
  - **Residual risk (accepted): the interpreter and its site-packages.** The app runs Ads scripts with its own Python (the repo's `.venv`), and that venv's site-packages, including any `.pth` file (which Python executes at start-up even with `-E -s`), the installed `google-ads` library, the `git` binary, the mirror and the private folder are all trusted. They belong to the same macOS user as the app, and a process running as that user could alter any of them. The mirror and the run folder stop the working tree and its git state from changing what runs; they do not stop that user. A process running as the owner outside Claude's tools (a command the owner approves at a prompt) can still write a nonce file or edit the ledger directly, as before.
- **Out of the model:** a compromised macOS account, or root. Those own the Keychain and the private files anyway.

## Architecture

```
iPhone / iPad / laptop ──Tailscale (WireGuard, HTTPS via tailscale serve)──▶ Mac
   PWA (installable, push)                                   127.0.0.1:8765  command_centre (Python)
                                                              ├─ data layer ──▶ scripts/bookings/*, scripts/reports/* (import, no shell)
                                                              ├─ cache ──────▶ ~/lcs-private/command-centre/cache/*.json (written by scheduled runs + refresh jobs)
                                                              ├─ actions ────▶ fixed script invocations (subprocess, argv lists, allowlisted)
                                                              ├─ chat ───────▶ Claude Agent SDK (repo cwd, repo settings/hooks)
                                                              ├─ push ───────▶ Web Push (VAPID keys in Keychain)
                                                              └─ audit log, backups, health
```

- **Stack:**
  - Python 3 in the repo `.venv`.
  - Starlette or FastAPI plus uvicorn.
  - Jinja2 templates with htmx for partial updates, no JS build step. A small vanilla JS file handles the passkey, the chat stream and push.
  - `webauthn` (py_webauthn) and `pywebpush`.
  - `claude-agent-sdk`.
  - Tests use the stdlib runner, as elsewhere in the repo, with Starlette's TestClient.
- **Code:**
  - `command_centre/` in the repo: `app.py` (routes), `auth.py` (Tailscale identity and passkeys), `data.py` (read models), `actions.py` (the action registry), `chat.py`, `push.py`, `jobs.py` (refresh and backup), `templates/`, `static/`.
  - Each module has one job, with its own tests in `tests/test_cc_*.py`.
- **Service:**
  - A LaunchAgent `com.lcs.command-centre.plist`, started at login and restarted on crash, with logs to `~/lcs-private/command-centre/logs/`.
  - A one-time `tailscale serve --bg --https=443 http://127.0.0.1:8765` makes it reachable at `https://<mac>.<tailnet>.ts.net`.
  - Both steps are scripted in `command_centre/install.sh`. The owner runs it once; it is idempotent and needs no secrets.
- **Config:** `~/lcs-private/command-centre/config.json`. It holds the allowed Tailscale login(s), the passkey credentials (public keys only), the push subscriptions and the backup target.

## Pages

All pages are mobile-first, with dark and light modes and the LCS brand colours. Every page has a freshness stamp.

1. **Today (home)**
   - What needs the owner, in priority order:
     - bank-detail warnings;
     - hand checks;
     - approvals waiting;
     - drafts to review and send;
     - Books drafts not sent;
     - follow-ups the assistant drafted;
     - failed runs.
   - Also: today's and this week's events, with diary entries and money deadlines.
2. **Bookings:** a list and filters (upcoming, past, state).
   - Each booking has a timeline: enquiry, quote, follow-ups, invoice (ledger and Books), payments (Starling), singers booked, singer bills, review request, and notes.
   - Links open the Zoho thread and the Books invoice.
3. **Enquiries (pipeline):** a board by status, follow-ups due, conversion rate, source mix, and a timeline per enquiry.
4. **Money:**
   - the Starling balance and the last 30 days in and out;
   - client money due and overdue;
   - hand checks, each with its resolve actions;
   - singer invoices unpaid, with payee and bank status;
   - Books receivables and bills;
   - monthly income against costs.
5. **Singers:** a directory of name, payee status, bank check (••••last4 only), invoices, total paid, last booking and warnings.
6. **Marketing:**
   - Ads spend by campaign;
   - cost per enquiry and per booking;
   - budget proposals;
   - search terms flagged;
   - the Search Console shortlist;
   - GA4 leads;
   - trends.
7. **Drafts:** the drafts the assistant saved in Zoho, taken from its run summaries and a Zoho drafts read.
   - Each has a preview and an "open in Zoho" link.
   - The owner can mark a draft sent or discarded; this is a local record only, and the app never sends.
8. **Calendar:** month and week views combining Google Calendar (read-only), bookings, deposit and balance due dates, and follow-up dates.
9. **Quote calculator:** packages, organist and travel taken from `pricing.html` and `christmas-pricing.html` (parsed the same way as `assistant_io.py prices`), with copyable wording in Luca's style.
10. **Reports:** every Monday review archived (the scheduled task writes its report to `~/lcs-private/reports/YYYY-MM-DD.txt`), plus trend charts drawn as inline SVG with no external library.
11. **Runs and health:**
    - scheduled-task runs (last run, result, failures, and a **Run now** button that triggers the task);
    - Starling selftest, Google ADC, the Zoho Mail and Books MCPs, Tailscale status and disk;
    - the fingerprint-key backup age;
    - the last backup.
12. **To-do:** the owner-only items from `MANUAL-ACTIONS-REQUIRED.md` (parsed), with ticks stored locally.
13. **Search:** one box across bookings, clients, singers, enquiries, invoice numbers and refs.
14. **Chat:** Claude Code.
    - Quick prompts: "what's owed this week", "draft a reply to …", "summarise today", "why is <ref> on the hand check".
    - Streamed replies and a conversation list.
    - Approve/deny cards (passkey).
    - A "stop" button.
15. **Activity log:** every action and every run, filterable.

## Actions (the registry)

Each action has:
- a name;
- the input it takes, validated;
- a preview showing exactly what will run;
- the command (argv) that runs it.

It needs a passkey (except the local records below) and is logged.

| Action | Runs |
|---|---|
| Resolve hand check: paid in full / deposit kept / refunded / reinstated / cancelled / arranged | `check_payments.py --note <ref> "<fixed phrase> <date>"`. The owner-only phrases are allowed here, because the owner is the one acting. This path passes `--owner` and records the owner as the author. |
| Confirm singer bank details | `singer_invoices.py confirm <id> --expect-fp <the whole 16-character fingerprint>` (refused if the details changed) |
| Settle or withdraw a singer invoice | `singer_invoices.py settled <id> <date>` / `withdrawn <id> <reason>` |
| Approve an Ads change set | Run a proposal-aware `scripts/ads/*.py` from its commit on GitHub's main (the app's own mirror) with `--validate-only`, show the output (its first and last 3,000 characters, unmasked), then `--apply` from the same commit after a second tap; the script writes `logs/ads-changes.md` (`LCS_ADS_LOG`). It never goes above £5/day (the script refuses). |
| Approve the 2026 Books import / a proposed page fix | Queue it for Claude Code (chat) with the approved instruction. The chat runs it under its guards. |
| Mark a draft sent or discarded; tick a to-do | Local record only. **Exception: no passkey.** These write only the app's own files in `~/lcs-private/command-centre/` (never the ledger, the singer store, email, Books or the bank), so the owner's Tailscale identity, the Host check and the same-origin check are enough. They are still registered actions, with a server-built summary and an `audit.jsonl` entry. |
| Run a scheduled task now | Triggers the task (headless `claude -p` with the task prompt in the repo folder, the same as the scheduled run) |
| Refresh data now | Refresh jobs, read-only |
| Back up now | The backup job |

Not in the app: sending email, payments, payees, deletes, and Books sends or voids.

## Push notifications

- The app is an installable PWA with a manifest and a service worker. On iOS 16.4+, Web Push works once it's added to the Home Screen. VAPID keys live in the Keychain.
- **Triggers:**
  - a new enquiry;
  - a deposit or balance arrived;
  - singer bank details changed or differ;
  - a guard denied a call;
  - a scheduled run failed or wasn't seen for more than 3 hours in the daytime;
  - the Monday review is ready;
  - a hand check was added.
- **Sources:** hooks and scripts append events to `~/lcs-private/command-centre/events.jsonl`, and the app watches the file and pushes. The scheduled prompts also add one line each: "append an event" via a tiny `cc_event.py` CLI, which is allowlisted.
- **Content:** a short title and a first name only. Full detail opens in the app.

## Data freshness

- **Live on each page load** (fast, local):
  - the ledger, the singer store and enquiries.csv;
  - the check_payments collect, cached for 10 minutes;
  - the audit log and events.
- **Cached** (written by the scheduled runs and by a refresh job every 30 minutes, 07:00–22:00):
  - the Ads summary, and the GA4 and Search Console summaries (via weekly_review's functions);
  - Books receivables and bills (via `lcs_mcp` reads, allowlisted read tools only, through a Books read client mirroring `lcs_mcp`'s safety);
  - Zoho drafts and the calendar.
- Every panel shows "as of <time>". When a source fails, its panel shows the last good data and the error type; it never breaks the page.

## Backups

- A nightly encrypted archive of `~/lcs-private`, keeping 14 days, in `tar` + `age` format.
- The recipient key is in the Keychain; the identity key is printed once for the owner to store in his password manager.
- The target is iCloud Drive `LCS-backups/` by default (config).
- A restore procedure is documented.
- The health page warns if the last backup is more than 36 hours old.

## Error handling

- Every data source is wrapped: on failure the panel shows its stale data and the reason, and the page still renders.
- An action failure shows the command's stderr, trimmed and with secrets scrubbed (`lcs_mcp` scrub rules), and is logged. There are no automatic retries for actions.
- If the chat crashes, it doesn't affect the rest of the app.

## Testing

- Unit tests for each module:
  - auth: header check, passkey verify/replay/expiry, per-action binding;
  - the action registry: exact argv, input validation, no shell;
  - data read models, using fixtures under temp `LCS_PRIVATE_DIR`;
  - the push payload contains no data beyond first names.
- Route tests with TestClient:
  - 403 without the Tailscale header or with the wrong login;
  - actions refused without a fresh assertion;
  - CSRF (same-origin plus assertion binding).
- A security review by a separate agent before go-live, run adversarially like the guard reviews.
- A visual check in the browser at phone width, with screenshots.

## Build order (phases)

1. **Skeleton:** the app, auth (Tailscale identity and passkey), LaunchAgent, install script, and Today and Money read-only.
2. **Data pages:** Bookings, Enquiries, Singers, Marketing, Calendar, Search, Reports, Runs and health, To-do, CSV exports.
3. **Actions:** the registry with passkey; hand checks, singer confirm/settle/withdraw, Ads approve, run now, refresh, backup.
4. **Chat:** the Agent SDK, streaming, approval cards, quick prompts.
5. **PWA and push, drafts inbox, quote calculator, backups.**

Each phase is reviewed and merged before the next. The static `dashboard.py` stays as a fallback until phase 2 ships.

## Out of scope

- Public access.
- Multiple users.
- Sending email or moving money from the app.
- Editing site pages from the app (the chat can propose; the owner approves in chat).
