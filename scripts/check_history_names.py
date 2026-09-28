#!/usr/bin/env python3
"""Refuse commits that carry the real names scrubbed from this public repo's history.

On 28 Sep 2026 the history was rewritten to replace real singers' names that had been
committed in test fixtures and a plan. A branch cut before the rewrite still carries the
old commits, and merging it would bring the names back. This check reads every commit a
pull request adds (message and added lines) and fails if any contains one of those names.

The names themselves are never stored here: only salted SHA-256 fingerprints of the
normalised phrases (lower case, words split on anything but letters). The check hashes
every 1-, 2- and 3-word phrase it reads and compares.

    python3 scripts/check_history_names.py <base sha> <head sha>

Exit 0: clean. Exit 1: a banned name was found (the commit is named, the name is not).
A branch that fails must be rebased onto the current main (`git rebase --onto origin/main
<old main> <branch>`), which drops the old commits.
"""

import hashlib
import re
import subprocess
import sys

SALT = "lcs-private-names-v1:"
BANNED = {
    "f2fb56d340480cabc549ba3d", "83b951ea211bac6eebaf8f02", "e2fefac46d8446a4e98afcc1",
    "03ae1c6e0f2af7fe06208d02", "cd77459061cb5c7511e54152", "6333033eb15b8ad61ee735e2",
    "306bb8044a3594895480f951", "789e0fa18177282362c546ed", "80c6e276b3278d11136ea74e",
    "813c9c9f92ecff743ac89588",
}
WORD = re.compile(r"[^\W\d_]+")


def fingerprint(phrase):
    return hashlib.sha256((SALT + phrase).encode()).hexdigest()[:24]


def phrases(text):
    words = [w.lower() for w in WORD.findall(text)]
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            yield " ".join(words[i:i + n])


def has_banned(text, banned=None):
    banned = BANNED if banned is None else banned
    return any(fingerprint(p) in banned for p in phrases(text))


def git(*args):
    out = subprocess.run(["git", *args], capture_output=True, check=True).stdout
    return out.decode("utf-8", errors="replace")  # old commits hold binary files


def commit_text(sha):
    message = git("log", "-1", "--format=%B", sha)
    added = [ln[1:] for ln in git("show", "--format=", "--unified=0", "--no-color", sha).splitlines()
             if ln.startswith("+") and not ln.startswith("+++")]
    return message + "\n" + "\n".join(added)


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[0])
        return 2
    base, head = argv[1], argv[2]
    commits = git("rev-list", f"{base}..{head}").split()
    bad = [c for c in commits if has_banned(commit_text(c))]
    for c in bad:
        print(f"::error::commit {c[:12]} carries a name scrubbed from this repo's history; "
              "rebase the branch onto the current main (see scripts/check_history_names.py)")
    print(f"{len(commits)} commit(s) checked, {len(bad)} refused")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
