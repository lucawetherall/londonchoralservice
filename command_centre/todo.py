"""The owner's to-do list: the numbered sections of MANUAL-ACTIONS-REQUIRED.md, with ticks kept locally in
~/lcs-private/command-centre/todo.json (mode 600): {"<N>-<slug>": {"done": true|false, "at": "<iso>"}}.

parse() reads each "## N. Title" heading and the first paragraph under it, as plain text. The file is the
owner's; the app never writes it. Ticking goes through actions.REGISTRY["todo-tick"].
"""

import datetime
import json
import os
import re
import secrets
from pathlib import Path

from . import auth

REPO = Path(__file__).resolve().parent.parent
MANUAL_ACTIONS = REPO / "MANUAL-ACTIONS-REQUIRED.md"
HEADING = re.compile(r"^##\s+(\d{1,3})\.\s+(.+?)\s*$")
KEY_RE = re.compile(r"^\d{1,3}-[a-z0-9-]{1,60}$")
SUMMARY_MAX = 400


def plain(text):
    """Markdown inline marks stripped: links keep their text, emphasis and code marks go."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<(https?://[^>]+)>", "", text)
    text = re.sub(r"(\*\*|__|`)", "", text)
    text = re.sub(r"(?<!\w)[*_](\S[^*_]*?)[*_](?!\w)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", plain(title).lower()).strip("-")[:60] or "item"


def parse(text):
    """[{number, title, key, summary}] in file order."""
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if not m:
            continue
        para, j = [], i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        while j < len(lines) and lines[j].strip() and not lines[j].lstrip().startswith("#"):
            para.append(lines[j].strip())
            j += 1
        summary = plain(" ".join(para))
        if len(summary) > SUMMARY_MAX:
            summary = summary[:SUMMARY_MAX].rsplit(" ", 1)[0] + " …"
        number, title = int(m.group(1)), plain(m.group(2))
        out.append({"number": number, "title": title, "key": f"{number}-{slug(m.group(2))}", "summary": summary})
    return out


def read_items():
    with open(MANUAL_ACTIONS, encoding="utf-8") as f:
        return parse(f.read())


def store_path():
    return auth.config_dir() / "todo.json"


def load_ticks():
    try:
        with open(store_path(), encoding="utf-8") as f:
            ticks = json.load(f)
    except FileNotFoundError:
        return {}
    return ticks if isinstance(ticks, dict) else {}


def todo_items(items, ticks):
    """The items with their tick state, open ones first (file order), then the done ones."""
    out = []
    for it in items:
        t = ticks.get(it["key"]) if isinstance(ticks.get(it["key"]), dict) else {}
        out.append(dict(it, done=bool(t.get("done")), at=str(t.get("at") or "")[:25]))
    return [i for i in out if not i["done"]] + [i for i in out if i["done"]]


def write_private_json(path, obj):
    """Atomic write, mode 600, in a mode-700 directory."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def set_tick(key, done, when=None):
    """Record one tick, under the config lock (one writer at a time)."""
    when = when or datetime.datetime.now(datetime.timezone.utc)
    with auth.config_lock():
        ticks = load_ticks()
        ticks[key] = {"done": bool(done), "at": when.isoformat(timespec="seconds")}
        write_private_json(store_path(), ticks)
