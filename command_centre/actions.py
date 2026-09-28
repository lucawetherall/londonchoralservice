"""The action registry. Every write the app makes is an action here: a name, a validator for its input, a
preview that builds the summary on the server (auth.Action), and a run. Each run is logged, append-only, in
~/lcs-private/command-centre/audit.jsonl (mode 600).

Phase 2 registers one action, `todo-tick`, a local record in the app's own folder. It is the spec's one
exception to the passkey rule (see the actions table in docs/superpowers/specs/2026-09-28-command-centre-design.md):
it writes nothing but todo.json, so the Tailscale identity, the Host check and the same-origin POST check
(IdentityMiddleware) are enough. Phase 3 adds the passkey actions (argv lists, no shell) to the same registry;
they will need auth.Passkeys.require_fresh_assertion over the Action that build() returns.
"""

import dataclasses
import datetime
import json
import os
from typing import Callable

from . import auth, todo


class ActionError(Exception):
    """Refused input. `reason` is a fixed phrase, safe to show."""

    def __init__(self, reason, status=400):
        super().__init__(reason)
        self.reason = reason
        self.status = status


@dataclasses.dataclass(frozen=True)
class LocalAction:
    name: str
    validate: Callable  # raw input (a dict of strings) -> cleaned input, or ActionError
    preview: Callable   # cleaned input -> the summary, written by the server
    run: Callable       # cleaned input -> None
    passkey: bool = True

    def build(self, raw):
        """The server-built auth.Action for this input (what a passkey, when needed, would bind)."""
        return auth.Action(self.name, self.preview(self.validate(raw)))

    def execute(self, raw, user):
        """Validate, run and log. Refuses an action that needs a passkey: phase 3's route does those."""
        if self.passkey:
            raise ActionError("this action needs a passkey", status=403)
        cleaned = self.validate(raw)
        action = auth.Action(self.name, self.preview(cleaned))
        try:
            self.run(cleaned)
        except Exception as e:
            audit(action, user, f"failed: {type(e).__name__}")
            raise
        audit(action, user, "ok")
        return action


def audit_path():
    return auth.config_dir() / "audit.jsonl"


def audit(action, user, result):
    entry = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             "action": action.name, "summary": action.summary, "login": (user or {}).get("login", ""),
             "result": result}
    d = auth.config_dir()
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(audit_path(), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- todo-tick


def _todo_validate(raw):
    if not isinstance(raw, dict):
        raise ActionError("malformed request")
    key, done = raw.get("key"), raw.get("done")
    if not isinstance(key, str) or not todo.KEY_RE.fullmatch(key):
        raise ActionError("unknown to-do item")
    if done not in ("yes", "no"):
        raise ActionError("done must be yes or no")
    item = next((i for i in todo.read_items() if i["key"] == key), None)
    if item is None:
        raise ActionError("unknown to-do item")
    return {"key": key, "done": done == "yes", "item": item}


def _todo_preview(c):
    verb = "tick" if c["done"] else "untick"
    return f"{verb} to-do {c['item']['number']}: {c['item']['title']}"[:auth.MAX_SUMMARY]


def _todo_run(c):
    todo.set_tick(c["key"], c["done"])


TODO_TICK = LocalAction("todo-tick", _todo_validate, _todo_preview, _todo_run, passkey=False)
REGISTRY = {a.name: a for a in (TODO_TICK,)}
