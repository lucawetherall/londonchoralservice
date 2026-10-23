# Owner approval with Claude Code's Allow prompt

**Date:** 2026-10-19
**Status:** Approved for implementation. The owner, live in chat on 19 Oct 2026: "i dont want to have to use command centre anymore. change this", and "when i tell you something is okay in claude code like i am now, it should be okay to override."

## Problem

Some writes are the owner's alone: the `--owner` forms of the money scripts.

- `check_payments.py --fact REF <paid-in-full|fees-accepted --amount X|reinstated|deposit-kept|refunded|payment-checked> --owner` and `--note REF "…" --owner`
- `singer_invoices.py confirm|settled|withdrawn … --owner`
- `events.py migrate --apply`, `retract` and `notes-checked`, each with `--owner`
- `imap_draft.py discard <Message-ID> --owner`

Until now they ran only from the Command Centre, after Luca's passkey. The app writes the sha256 of a one-time nonce to `<private>/command-centre/owner-nonce` and pipes the nonce into the script, and `lcs_owner.owner_confirmed()` checks it (60 seconds, single use). Luca wants to approve these from Claude Code instead, including from his phone over Remote Control.

## Design

Luca approves an owner action by clicking **Allow** on Claude Code's own permission prompt for that exact command.

- **The hook** (`.claude/hooks/owner_confirm_guard.py`, PreToolUse on Bash) treats a command as an owner command when `--owner` is in its text, in its text once quotes and backslashes are dropped (`--own''er`), or among its shell words. For an owner command it:
  - denies a subagent's call (the event carries an `agent_id`);
  - denies anything but one plain command: `.venv/bin/python scripts/bookings/<one of the four scripts>.py` and arguments that read the same to bash and to Python's shlex (plain characters, `'…'`, or `"…"` without `$`, backticks or backslashes). No pipes, `;`, `&`, redirects, globs, variables, env prefixes or newlines, so the prompt shows exactly what runs;
  - deletes any outstanding chat approval, makes a 64-hex secret and writes `command-centre/owner-nonce.chat-<sha256 of the secret>` (`O_EXCL`, `O_NOFOLLOW`, mode 600) holding the command's argv from the script path on, the time and the session. The command-centre folder must be a real folder, not a symlink;
  - answers "ask" with `updatedInput`: the same tool input with the command rewritten to `printf '%s\n' <secret> | <command>`, and a reason in plain English ("Owner approval: check_payments.py --fact 2108A paid-in-full --on 2026-10-19. Allow only if you asked Claude for this in this chat; otherwise Deny.").

  Any error on an owner command denies it.
- **The script.** `owner_confirmed()` reads the first line of stdin once (a pipe, 64 hex) and accepts either:
  - (a) the Command Centre's nonce, with exactly the old checks; or
  - (b) a chat approval named by its hash. The file must be regular, this user's, mode 600, at most 15 minutes old (`OWNER_CHAT_TTL`, time to answer on the phone) and at most 4096 bytes. Its argv must equal the process's `sys.argv` word for word. It is deleted on a match.
- **Settings.** `"ask": ["Bash(*--owner*)"]` backs the hook up: an explicit ask rule prompts even in bypassPermissions. The deny rules that stopped `events.py migrate --apply`, `retract`, `notes-checked` and `singer_invoices.py confirm`/`settled` being tried at all are removed. The nonce, approvals, state-log and command-centre denies stay.
- **The Command Centre** is unchanged and keeps working.

Only a human click runs the command. A scheduled run or `claude -p` has no one to click, so its "ask" becomes a refusal. Hook "ask" prompts in bypassPermissions and in auto mode; the classifier can deny it but not approve it. Remote Control relays the prompt to Luca's phone.

## Why a typed message isn't the proof

A hook could look for Luca's "yes, do it" in the chat instead. But UserPromptSubmit also fires for scheduled-task prompts, subagent reports and messages from other sessions, so no hook can tell that Luca typed a given message. A message inside an email or a document, once quoted, reads the same. The Allow click on the permission prompt is the one signal only he can give, and it is tied to the exact command shown.

## What the guards cover

- The approval works once, for one argv, within 15 minutes, and only through a pipe. Only one is ever outstanding: each new owner command replaces it.
- An approval outlives a prompt Luca denied or never answered. Two checks keep it to the command it was made for:
  - the hook denies any command that holds an outstanding secret;
  - every other Bash command from the same session deletes that session's outstanding approvals before it runs. The rewritten command itself passes no hook again.
- `mcp_bypass_guard.py` refuses commands, and untracked files, that name the approval hook (`owner_confirm_guard`, though not its test file) or reach it through a glob or another path. Run by hand, the hook would mint an approval without the prompt. The Read and Edit tools may still open it. `owner-nonce.chat-*` is already covered by the `owner-nonce` rule.
- The approval file is written only by the hook. Settings deny Claude's Write and Edit tools in the command-centre folder and any Bash command naming `owner-nonce`.
- The scripts still refuse every owner write without `--owner` and a valid nonce, and `owner_folder_problem` still ties the write to the files beside the nonce.

## Residual risks

- **Text checks, not a sandbox.** Deliberate obfuscation (a file name or module name assembled at run time) could still forge an approval file or import the hook. That is the same exposure the Command Centre's nonce has always had; CLAUDE.md's rule covers intent.
- **A leaked secret.** The secret sits in the rewritten command. If Claude Code keeps that in a transcript another session can read, that session could use it within 15 minutes of a denied prompt, but only with an obfuscated `--owner` the hook can't see and before any new owner command replaces the approval.
- **Fails safe, not quietly.** A Bash call made alongside the owner command (parallel tool calls, a background subagent) retires the approval before Luca clicks, and the script then refuses. Claude runs owner commands on their own. A `--owner` the hook can't see, such as an argparse abbreviation, gets no approval and the script refuses it.
- **Click fatigue.** The prompt names the action and says to deny anything Luca didn't ask for, but the click is still his judgement.
- **Bank details.** A chat `confirm` without `--expect-fp` trusts the details recorded when it runs. The Command Centre pins the fingerprint it showed.
- **Harness behaviour.** The design relies on Claude Code honouring `updatedInput` on "ask" without re-running hooks on the rewritten command. Both were measured or documented on 19 Oct 2026; if either changes, owner commands fail closed.

## Testing

- `tests/test_owner_confirm_guard.py`:
  - the ask, the rewritten command and the kept fields;
  - one approval file, mode 600, holding the argv;
  - a second command replacing the first;
  - subagent, compound and odd forms denied;
  - `--own''er` caught;
  - a missing or linked folder denied;
  - same-session clean-up;
  - a command naming a secret denied;
  - the old imap_draft asks.
- `tests/test_lcs_owner.py`:
  - a chat approval taken once with its argv;
  - refused for a different argv, an expired, future or loose-mode file, a symlink, bad JSON, a linked folder, a non-pipe stdin and a wrong line;
  - the Command Centre's nonce unchanged.
- `tests/test_check_payments.py`, end to end: the hook's rewritten command writes the owner note once; another command with the same code and a replay are refused.
- `tests/test_mcp_bypass_guard.py`: the hook can't be run by name, glob or path; its test file runs.
- `tests/test_prompt_allowlist.py`: the ask rule covers every owner form, the removed denies are gone, the kept ones stay, and no scheduled prompt command would prompt.
