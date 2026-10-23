#!/usr/bin/env python3
"""The owner barrier shared by the money scripts (structured-state design, 29 Sep 2026; chat approval, 19 Oct 2026).

An --owner write needs Luca's approval, given in one of two ways, each a one-time nonce that arrives over a pipe on
stdin (owner_confirmed):
- his passkey in the Command Centre: the app writes the nonce's sha256 to <private>/command-centre/owner-nonce,
  then runs the script with the nonce piped in;
- his Allow on Claude Code's own permission prompt for that exact command, in a live chat (owner decision,
  19 Oct 2026: "when i tell you something is okay in claude code like i am now, it should be okay to override"):
  the PreToolUse hook .claude/hooks/owner_confirm_guard.py answers "ask" for any --owner command, writes
  <private>/command-centre/owner-nonce.chat-<the nonce's sha256> holding that command's argv, and rewrites the
  command to pipe the nonce in. Nothing runs until he clicks Allow, and the nonce fits only that argv.
Every file the write touches must also sit directly in the private folder beside the nonce (owner_folder_problem).
check_payments.py imports these under its old names. Nothing here writes anything but the burnt nonce files.
"""

import hashlib
import hmac
import json
import os
import re
import select
import stat
import sys
import time
from pathlib import Path

OWNER_NONCE_TTL = 60  # seconds: the Command Centre writes the file moments before it runs the script
OWNER_CHAT_TTL = 900  # seconds: Luca may answer Claude Code's prompt on his phone (Remote Control) a while later
CHAT_PREFIX = "owner-nonce.chat-"  # + the nonce's sha256: owner_confirm_guard's approval files
HEX64 = re.compile(r"[0-9a-f]{64}")
# the scripts' refusal when owner_confirmed() fails ("; nothing written" or the like follows)
NEEDS_APPROVAL = ("--owner needs Luca's approval: his Allow on Claude Code's prompt for this exact command, run on its "
                  "own in a live chat, or his passkey in the Command Centre")
_PROVEN = False  # set once owner_confirmed() has passed in this process: lcs_events.append then takes by: owner


def owner_proven():
    """True when this process passed owner_confirmed() (the nonce is burnt, so only this run can rely on it)."""
    return _PROVEN


def owner_nonce_path():
    """<private dir>/command-centre/owner-nonce (LCS_PRIVATE_DIR read at call time)."""
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private")) / "command-centre" / "owner-nonce"


def owner_chat_path(line):
    """<private dir>/command-centre/owner-nonce.chat-<sha256 of line>: the approval owner_confirm_guard writes for
    a nonce."""
    return owner_nonce_path().with_name(CHAT_PREFIX + hashlib.sha256(line.encode("ascii")).hexdigest())


def owner_folder_problem(paths, environ=None):
    """None when an --owner write would land only in files directly in the nonce's private folder, else the reason.
    The nonce proves Luca approved; this proves the write goes to the files beside it: LCS_BOOKINGS_CSV must be
    unset (neither the app nor owner_confirm_guard's plain command sets it), and each path (the ledger, the singer
    store, the state log) must name a file in that folder both as written and once resolved, so neither a symlinked
    folder nor a file that is a link elsewhere passes."""
    environ = os.environ if environ is None else environ
    if environ.get("LCS_BOOKINGS_CSV"):
        return "refuses LCS_BOOKINGS_CSV (the ledger must be the one in the private folder)"
    private = owner_nonce_path().parent.parent
    try:
        home, real_home = os.path.abspath(private), private.resolve()
        for p in paths:
            p = Path(p)
            if os.path.abspath(p.parent) != home or p.resolve().parent != real_home:
                return f"needs {p.name} in the same private folder as the nonce"
    except OSError:
        return "couldn't resolve the private folder"
    return None


def _stdin_nonce(stdin_fd):
    """The first line on stdin, read once, when stdin is a pipe (not a terminal, not a redirected file) and that
    line is 64 hex characters; else None."""
    try:
        if not stat.S_ISFIFO(os.fstat(stdin_fd).st_mode):
            return None
        ready, _, _ = select.select([stdin_fd], [], [], 2.0)  # an idle, open pipe never hangs the script
        if not ready:
            return None
        line = os.read(stdin_fd, 200).decode("ascii", "replace").split("\n", 1)[0].strip()
    except (OSError, ValueError):
        return None
    return line if HEX64.fullmatch(line) else None


def _command_centre_nonce(line):
    """(a) The Command Centre's nonce: the one-time nonce file holds the line's sha256, and that file is a regular
    file (never followed through a symlink), this user's, mode 600 with no group or other bits, and under
    OWNER_NONCE_TTL seconds old. The file is deleted on a match. The nonce itself lives only in the app's memory and
    the pipe; the file holds its hash, so redirecting the file into stdin fails twice over."""
    path = owner_nonce_path()
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        return False
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077
                or not -5 <= time.time() - st.st_mtime <= OWNER_NONCE_TTL or st.st_size > 200):
            return False
        want = os.read(fd, 200).decode("ascii", "replace").strip()
    finally:
        os.close(fd)
    if not HEX64.fullmatch(want):
        return False
    if not hmac.compare_digest(hashlib.sha256(line.encode("ascii")).hexdigest(), want):
        return False
    try:
        os.unlink(path)  # single use: burnt before the note is written
    except OSError:
        return False
    return True


def _chat_nonce(line, argv):
    """(b) Luca's Allow on Claude Code's prompt: owner-nonce.chat-<the line's sha256> sits in the command-centre
    folder (a real folder, this user's, not a symlink) and is a regular file (never followed through a symlink),
    this user's, mode 600 with no group or other bits, under OWNER_CHAT_TTL seconds old and at most 4096 bytes,
    whose JSON "argv" is exactly this process's argv: the command Luca allowed, word for word. The file is deleted
    on a match. The hook keeps the nonce only in the command it rewrote; the file is named by its hash."""
    path = owner_chat_path(line)
    try:
        folder = os.lstat(path.parent)
        if not stat.S_ISDIR(folder.st_mode) or folder.st_uid != os.getuid():
            return False
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        return False
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077
                or not -5 <= time.time() - st.st_mtime <= OWNER_CHAT_TTL or st.st_size > 4096):
            return False
        data = os.read(fd, 4097)
    except OSError:
        return False
    finally:
        os.close(fd)
    try:
        recorded = json.loads(data.decode("utf-8"))["argv"] if len(data) <= 4096 else None
    except (ValueError, KeyError, TypeError):
        return False
    if not (isinstance(recorded, list) and all(isinstance(a, str) for a in recorded) and recorded == list(argv)):
        return False
    try:
        os.unlink(path)  # single use: burnt before the note is written
    except OSError:
        return False
    return True


def owner_confirmed(stdin_fd=0, argv=None):
    """True only when Luca approved this --owner write: stdin is a pipe whose first line (64 hex, read once) is
    either (a) the Command Centre's one-time nonce, piped after his passkey (_command_centre_nonce), or (b) the
    one-time nonce owner_confirm_guard piped in once he clicked Allow on Claude Code's prompt for this exact command
    (_chat_nonce; `argv`, sys.argv when None, must be the argv the hook recorded). Either nonce file is deleted on a
    match, so a nonce works once. Claude can't write or pipe either file itself: settings deny its file tools in the
    command-centre folder, and the bypass guard refuses commands and scratch files that name the nonce or the
    approval hook (plan, Task 3.1)."""
    line = _stdin_nonce(stdin_fd)
    if line is None:
        return False
    if not (_command_centre_nonce(line) or _chat_nonce(line, sys.argv if argv is None else argv)):
        return False
    global _PROVEN
    _PROVEN = True
    return True
