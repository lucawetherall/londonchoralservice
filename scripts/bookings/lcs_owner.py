#!/usr/bin/env python3
"""The owner barrier shared by the money scripts (structured-state design, 29 Sep 2026).

An --owner write happens only when the Command Centre ran the script after the owner's passkey approval: its
one-time nonce arrives over a pipe on stdin (owner_confirmed), and every file the write touches sits directly in
the private folder beside that nonce (owner_folder_problem). check_payments.py imports these under its old names.
Nothing here writes anything but the burnt nonce file.
"""

import hashlib
import hmac
import os
import re
import select
import stat
import time
from pathlib import Path

OWNER_NONCE_TTL = 60  # seconds: the Command Centre writes the file moments before it runs the script
_PROVEN = False  # set once owner_confirmed() has passed in this process: lcs_events.append then takes by: owner


def owner_proven():
    """True when this process passed owner_confirmed() (the nonce is burnt, so only this run can rely on it)."""
    return _PROVEN


def owner_nonce_path():
    """<private dir>/command-centre/owner-nonce (LCS_PRIVATE_DIR read at call time)."""
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private")) / "command-centre" / "owner-nonce"


def owner_folder_problem(paths, environ=None):
    """None when an --owner write would land only in files directly in the nonce's private folder, else the reason.
    The nonce proves the app asked; this proves the write goes to the files the app read: LCS_BOOKINGS_CSV must be
    unset (the app never sets it for its subprocesses), and each path (the ledger, the singer store, the state log)
    must name a file in that folder both as written and once resolved, so neither a symlinked folder nor a file
    that is a link elsewhere passes."""
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


def owner_confirmed(stdin_fd=0):
    """True only when the Command Centre ran this --owner write after the owner's passkey approval: stdin is a pipe
    (not a terminal, not a redirected file) whose first line hashes (sha256) to the contents of the one-time nonce
    file, and that file is a regular file (never followed through a symlink), this user's, mode 600 with no group
    or other bits, and under OWNER_NONCE_TTL seconds old. The file is deleted on a match, so a nonce works once.
    The nonce itself lives only in the app's memory and the pipe; the file holds its hash, so redirecting the
    file into stdin fails twice over. No allowlisted command can pipe or write that file (plan, Task 3.1)."""
    try:
        if not stat.S_ISFIFO(os.fstat(stdin_fd).st_mode):
            return False
        path = owner_nonce_path()
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
    if not re.fullmatch(r"[0-9a-f]{64}", want):
        return False
    ready, _, _ = select.select([stdin_fd], [], [], 2.0)  # an idle, open pipe never hangs the script
    if not ready:
        return False
    line = os.read(stdin_fd, 200).decode("ascii", "replace").split("\n", 1)[0].strip()
    if not re.fullmatch(r"[0-9a-f]{64}", line):
        return False
    if not hmac.compare_digest(hashlib.sha256(line.encode("ascii")).hexdigest(), want):
        return False
    try:
        os.unlink(path)  # single use: burnt before the note is written
    except OSError:
        return False
    global _PROVEN
    _PROVEN = True
    return True
