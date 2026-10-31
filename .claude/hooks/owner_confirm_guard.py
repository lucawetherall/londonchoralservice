#!/usr/bin/env python3
"""PreToolUse guard (matcher Bash): Luca's approval for --owner commands, and an extra "ask" around Zoho Drafts.

Owner approval (owner decisions, 19 Oct 2026: "when i tell you something is okay in claude code like i am now, it
should be okay to override", and 31 Oct 2026: "i run business only through Claude Code app"). The --owner forms
of the money scripts (check_payments.py --fact/--note … --owner, singer_invoices.py confirm/settled/withdrawn …
--owner, events.py migrate --apply/retract/notes-checked … --owner, imap_draft.py discard <Message-ID> --owner)
write only with a one-time nonce on a pipe (lcs_owner.owner_confirmed). Luca approves one by clicking Allow on Claude
Code's own permission prompt for that exact command. For any command holding --owner (in its text, once quotes and
backslashes are dropped, or as a shell word, so `--own''er` counts), this hook:
- denies it from a subagent (the event carries an agent_id): owner actions run only in Luca's own conversation;
- denies it unless it is one plain command (PLAIN_OWNER): `.venv/bin/python scripts/bookings/<check_payments|
  singer_invoices|events|imap_draft>.py` and plain words, single-quoted text or double-quoted text without $,
  backticks or backslashes, so no pipes, ;, &, redirects, globs, variables, env prefixes or newlines, and what Luca
  sees is exactly what runs;
- mints the approval: deletes every outstanding owner-nonce.chat-* file in <private>/owner-approvals (LCS_PRIVATE_DIR,
  else ~/lcs-private; it must be a real folder, not a symlink), so only one is ever outstanding, makes a 64-hex
  secret and creates owner-nonce.chat-<its sha256> (O_EXCL, O_NOFOLLOW, mode 600) holding the command's argv from
  the script path on, the time and the session;
- answers "ask" with updatedInput: the same tool input (description, timeout, run_in_background kept) with the
  command rewritten to `printf '%s\n' <secret> | <command>`. Claude Code shows Luca that command and a plain-English
  reason on its permission prompt (Remote Control relays it to his phone); hook "ask" prompts even in
  bypassPermissions and auto mode, and settings' ask rule Bash(*--owner*) backs it up. The command runs only when he
  clicks Allow, so a scheduled or `claude -p` run (no one to click) never runs it. lcs_owner takes the secret once,
  within 15 minutes, for that argv only.
Any error on an owner command denies it. A typed "yes" in the chat is not the proof: UserPromptSubmit also fires for
scheduled prompts, subagent reports and messages from other sessions, so no hook can tell that Luca typed it; only
his click on the prompt can (spec docs/superpowers/specs/2026-10-19-owner-approval-allow-prompt-design.md).

An approval file outlives a prompt Luca denied or never answered, so two more checks keep it to the command it was
made for: a command naming an outstanding secret is denied, and every other Bash command from the same session
deletes that session's outstanding approvals before it runs (the rewritten command itself passes no hook again).
The mcp_bypass_guard refuses any command that names this hook, so it can't be run by hand to mint an approval.

Zoho Drafts (unchanged). Moving an arbitrary office@ draft to Trash (owner decision, 14 Oct 2026) happens only
through `imap_draft.py discard <Message-ID> --owner` with Luca's approval as above (lcs_owner.owner_confirmed), and
imap_draft.trash_draft refuses any draft but Luca's own original in a process that hasn't passed that check. Two
narrower moves need neither: `attach` retiring Luca's own original once its copy is checked (29 Sep 2026), and
`replace <old> <new>` (owner decision, later on 14 Oct 2026: Claude may retire an old draft once Luca has asked for
a new or changed one), which the script refuses unless the replacement is already in Drafts, both are from office@,
to the same one address and in the same conversation. For commands without --owner this hook is a harmless second
layer on top: it answers "ask" for any command that touches imap_draft except the plain forms the automation uses
(save, attach, sent, replace, check, test, run as `.venv/bin/python scripts/bookings/imap_draft.py <command> …` with
nothing chained after it), and for any command naming its Trash helpers, so an odd command is shown to Luca as well
as failing. It is a check on Bash text, not a sandbox; it never allows anything itself, and it fails closed (an
unreadable event asks, or denies when it mentions --owner). The scheduled tasks never run discard.
"""
import datetime
import hashlib
import json
import os
import re
import secrets
import shlex
import stat
import sys
from pathlib import Path

HELPERS = re.compile(r"trash_draft|forget_saved|retire_original")
PLAIN = re.compile(r"\s*(?:\.venv/bin/python|python3) scripts/bookings/imap_draft\.py (?:save|attach|sent|replace|check|test)\b"
                   r"[^;&|`$<>(){}\n\\]*")
REASON = ("Touches Zoho Drafts beyond the automation's plain save/attach/sent/replace. Moving a draft to Trash runs "
          "only as `imap_draft.py discard <Message-ID> --owner`, which Luca approves (his Allow on Claude Code's prompt); "
          "from here it would refuse anyway.")

# One plain command: the venv's python, one of the four owner scripts, then words that mean the same to bash and to
# shlex: plain characters, '…' without ' or control characters, "…" without ", $, `, \ or control characters.
ARG = r"""(?:[A-Za-z0-9_./:@%+=,£-]+|'[^'\x00-\x1f\x7f]*'|"[^"$`\\\x00-\x1f\x7f]*")"""
PLAIN_OWNER = re.compile(r"[ \t\n]*\.venv/bin/python scripts/bookings/"
                         rf"(?:check_payments|singer_invoices|events|imap_draft)\.py(?: +{ARG})+[ \t\n]*")
CHAT_PREFIX = "owner-nonce.chat-"  # + the secret's sha256 (lcs_owner.CHAT_PREFIX)
MAX_RECORD = 4096  # bytes: lcs_owner refuses a bigger approval file
HEX_RUN = re.compile(r"[0-9a-f]{64,}")
P = "Owner confirm guard: "
NOT_PLAIN = (P + "an --owner action must run as one plain command: .venv/bin/python scripts/bookings/<check_payments|"
             "singer_invoices|events|imap_draft>.py and its arguments, with nothing before or after it (no pipes, ;, "
             "&&, redirects, $, backticks, globs, env prefixes or newlines; quote text with '…'). Nothing was run.")
SUBAGENT = (P + "owner actions run only in Luca's own conversation, never in a subagent. Hand the command back to the "
            "main conversation, which runs it on its own so Luca can approve it.")
# singer_invoices.py confirm without --owner (owner decision, 24 Oct 2026: Luca pays every singer by hand, so he
# confirms bank details by telling Claude in writing, with no Allow click). Only his own conversation runs it.
CHAT_CONFIRM = re.compile(r"singer_invoices\.py\s+confirm\b")
CONFIRM_SUBAGENT = (P + "singer_invoices.py confirm runs only in Luca's own conversation, when he says he has rung the "
                    "singer, never in a subagent or a scheduled run. Nothing was run.")


def decide(command):
    """"ask" with a reason, or None (no opinion: the other hooks and rules decide). For commands without --owner."""
    if not isinstance(command, str):
        return "Owner confirm guard: unreadable command; Luca must approve it."
    if HELPERS.search(command):
        return REASON
    if "imap_draft" in command:
        bare = re.sub(r"'[^']*'", "''", command)  # single-quoted JSON specs are data, not shell
        if "'" in bare.replace("''", "") or not PLAIN.fullmatch(bare):
            return REASON
    return None


def owner_command(text):
    """True when the command asks for an --owner action: --owner in its text, once quotes and backslashes are
    dropped (`--own''er`, `--own\\er`), or as one of its shell words."""
    if "--owner" in text or "--owner" in re.sub(r"[\"'\\]", "", text):
        return True
    try:
        return "--owner" in shlex.split(text, posix=True)
    except ValueError:
        return False


def approvals_folder():
    """<private dir>/owner-approvals, as lcs_owner.owner_approvals_dir() reads it (LCS_PRIVATE_DIR at call time)."""
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private")) / "owner-approvals"


def outstanding(folder):
    """The names of the owner-nonce.chat-* files in the folder ([] when it can't be read)."""
    try:
        return [e.name for e in os.scandir(folder) if e.name.startswith(CHAT_PREFIX)]
    except OSError:
        return []


def summary(argv):
    """The approved action in Luca's words: the script's name and its arguments, without the --owner flag."""
    return " ".join([os.path.basename(argv[0])] + [shlex.quote(a) for a in argv[1:] if a != "--owner"])


class NotSetUp(Exception):
    pass


def mint(argv, session):
    """Write the one approval for argv and return its secret. Raises NotSetUp, ValueError or OSError (the caller
    denies)."""
    folder = approvals_folder()
    try:
        real = stat.S_ISDIR(os.lstat(folder).st_mode)
    except OSError:
        real = False
    if not real:
        raise NotSetUp(f"{folder} is missing or not a real folder")
    created = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    record = json.dumps({"argv": argv, "created": created, "session": session}).encode("utf-8")
    if len(record) > MAX_RECORD:
        raise ValueError("the command is too long to approve")
    for name in outstanding(folder):  # only one chat approval is ever outstanding
        try:
            os.unlink(folder / name)
        except FileNotFoundError:  # another session's command retired it meanwhile
            pass
    secret = secrets.token_hex(32)
    path = folder / (CHAT_PREFIX + hashlib.sha256(secret.encode("ascii")).hexdigest())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(record)
    except BaseException:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return secret


def approve(event, tool_input, command):
    """The owner path: ("deny", reason) or ("ask", reason, updatedInput)."""
    if event.get("agent_id"):
        return "deny", SUBAGENT
    if not PLAIN_OWNER.fullmatch(command):
        return "deny", NOT_PLAIN
    words = shlex.split(command, posix=True)
    argv = words[1:]
    session = event.get("session_id") if isinstance(event.get("session_id"), str) else None
    try:
        secret = mint(argv, session)
    except NotSetUp:
        return "deny", (P + "the private folder isn't set up (its owner-approvals folder is missing or not a real "
                        "folder), so an --owner action can't be approved here. Nothing was run.")
    except ValueError as e:
        return "deny", f"{P}{e}. Nothing was run."
    except OSError as e:
        return "deny", f"{P}couldn't write the one-time approval ({type(e).__name__}). Nothing was run."
    reason = (f"Owner approval: {summary(argv)}. Allow only if you asked Claude for this in this chat; otherwise Deny. "
              "(The long number is a one-time code this check adds.)")
    plain = command.strip(" \t\n")
    rewritten = dict(tool_input, command=f"printf '%s\\n' {secret} | {plain}")
    return "ask", reason, rewritten


def names_a_secret(command, folder, names):
    """True when the command holds the secret of an outstanding approval (any 64-hex stretch whose sha256 names one)."""
    if not names:
        return False
    hashes, checked = {n[len(CHAT_PREFIX):] for n in names}, 0
    for run in HEX_RUN.findall(command):
        for i in range(len(run) - 63):
            if hashlib.sha256(run[i:i + 64].encode("ascii")).hexdigest() in hashes:
                return True
            checked += 1
            if checked > 20000:
                return True  # an unreasonable hex blob beside an outstanding approval: refuse rather than guess
    return False


def retire_session_approvals(folder, names, session):
    """Best effort: delete this session's outstanding approvals (and any unreadable one), so a prompt Luca denied or
    left can't be used by a later command."""
    for name in names:
        path = folder / name
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
            try:
                data = os.read(fd, MAX_RECORD + 1)
            finally:
                os.close(fd)
            mine = json.loads(data.decode("utf-8")).get("session") == session
        except (OSError, ValueError, AttributeError):
            mine = True
        if mine:
            try:
                os.unlink(path)
            except OSError:
                pass


def emit(decision, reason, updated=None):
    out = {"hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason}
    if updated is not None:
        out["updatedInput"] = updated
    print(json.dumps({"hookSpecificOutput": out}))


def main():
    raw = ""
    try:
        raw = sys.stdin.read()
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ValueError("event must be an object")
        tool_input = event.get("tool_input") or {}
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
    except Exception as e:  # fail closed: ask, or deny when it may be an owner action
        if "--owner" in re.sub(r"[\"'\\]", "", raw):
            emit("deny", f"{P}unreadable event ({type(e).__name__}); an --owner action is refused.")
        else:
            emit("ask", f"Owner confirm guard error ({type(e).__name__}); Luca must approve this command.")
        sys.exit(0)
    if (isinstance(command, str) and event.get("agent_id")
            and CHAT_CONFIRM.search(re.sub(r"[\"'\\]", "", command))):
        emit("deny", CONFIRM_SUBAGENT)
        sys.exit(0)
    if isinstance(command, str) and owner_command(command):
        try:
            result = approve(event, tool_input, command)
        except Exception as e:  # fail closed: deny
            result = ("deny", f"{P}error ({type(e).__name__}); an --owner action is refused. Nothing was run.")
        emit(*result)
        sys.exit(0)
    try:
        if isinstance(command, str):
            folder = approvals_folder()
            names = outstanding(folder)
            if names_a_secret(command, folder, names):
                emit("deny", P + "that command holds a one-time approval code. Only the command Luca allowed may use "
                     "it; run the --owner command on its own and he approves it again.")
                sys.exit(0)
            if names:
                session = event.get("session_id") if isinstance(event.get("session_id"), str) else None
                retire_session_approvals(folder, names, session)
        reason = decide(command)
    except Exception as e:  # fail closed: ask
        reason = f"Owner confirm guard error ({type(e).__name__}); Luca must approve this command."
    if reason:
        emit("ask", reason)
    sys.exit(0)


if __name__ == "__main__":
    main()
