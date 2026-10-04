#!/usr/bin/env python3
"""Nightly encrypted backups of ~/lcs-private (the Command Centre's backup job).

    .venv/bin/python scripts/reports/cc_backup.py init [--replace]   # once: make the key, print it ONCE
    .venv/bin/python scripts/reports/cc_backup.py run                # the LaunchAgent (02:30) and "Back up now"
    .venv/bin/python scripts/reports/cc_backup.py verify             # the key on stdin; lists the newest backup

- **init** makes an age X25519 key pair (pyrage). The recipient (the public key, "age1…") goes in the Command
  Centre's config (~/lcs-private/command-centre/config.json, `backup.recipient`); the identity (the private key,
  "AGE-SECRET-KEY-1…") is printed once, for the owner to keep in his password manager, and is never written to
  disk. Refused when a recipient exists already, unless --replace (older backups still need the older key), and
  refused when stdout isn't a terminal, so the key can't land in a pipe, a log or a tool's transcript (Claude's
  Bash tool is denied `cc_backup.py init` in .claude/settings.json as well).
- **run** writes a full backup: a tar.gz of the whole private folder, encrypted to the recipient, as
  lcs-backup-YYYYMMDD-HHMMSS.tar.gz.age (mode 600) in the target folder: the config's `backup.target`, by default
  ~/Library/Mobile Documents/com~apple~CloudDocs/LCS-backups (iCloud Drive). Left out: the backups themselves,
  command-centre/runs/ and command-centre/mirror.git (the app's copies of the public GitHub code, re-creatable),
  and anything that isn't a regular file, folder or symlink (sockets). The tar.gz is streamed through an os.pipe
  into age by a second thread, so no plaintext copy is ever written to disk; the ciphertext goes to a .part file
  that is renamed when complete. Retention afterwards (only files with that exact name, never the newest): every
  backup of the last 14 days, the last of each week for 8 weeks and the last of each month for 7 years (company
  records are kept for 6 years after the period they cover); .part files left by an interrupted run more than a
  day ago are removed. command-centre/backup-state.json records the time, name, size and sha256 for the Health
  page; a failed run adds "error" and "failed_at" to it (the last good backup's fields stay) and posts a macOS
  notification. One run at a time.
- **verify** reads the identity from stdin (hidden when typed), decrypts the newest backup through a pipe (never
  to disk), and prints how many entries it holds and their paths. Nothing is extracted.

Restore: `brew install age`, then `age -d -i key.txt lcs-backup-….tar.gz.age | tar -xz -C ~/restore-check`, with
key.txt holding the identity from the password manager (delete it afterwards).
"""
import argparse
import datetime
import fcntl
import getpass
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import tarfile
import threading
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from command_centre import auth  # noqa: E402  the config (read, locked write) and the private folder

LONDON = ZoneInfo("Europe/London")
DEFAULT_TARGET = "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-backups"
NAME_RE = re.compile(r"^lcs-backup-(\d{8})-(\d{6})\.tar\.gz\.age$")
PART_RE = re.compile(r"^\.lcs-backup-\d{8}-\d{6}\.tar\.gz\.age\.[0-9a-f]{8}\.part$")
KEEP = datetime.timedelta(days=14)  # every backup this recent
KEEP_WEEKS = 8  # the last backup of each of these weeks (the current one included)
KEEP_MONTHS = 84  # the last backup of each of these months: 7 years
RETENTION_WORDS = "kept every night for 14 days, weekly for 8 weeks and monthly for 7 years"
PART_KEEP = datetime.timedelta(days=1)
EXCLUDE = ("command-centre/runs", "command-centre/mirror.git", "command-centre/backups")
LIST_MAX = 200  # paths printed by verify


class BackupError(Exception):
    pass


def pyrage():
    try:
        import pyrage as p
    except ImportError:
        raise BackupError("pyrage is missing: .venv/bin/pip install -r scripts/requirements.txt") from None
    return p


def settings(cfg=None):
    """(recipient or None, target Path) from the config."""
    if cfg is None:
        try:
            cfg = auth.load_config()
        except (OSError, ValueError):
            cfg = {}
    block = cfg.get("backup") if isinstance(cfg.get("backup"), dict) else {}
    target = Path(os.path.expanduser(str(block.get("target") or DEFAULT_TARGET)))
    return (str(block.get("recipient") or "") or None), target


def state_path():
    return auth.config_dir() / "backup-state.json"


def write_private_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------- init


def init(replace=False, out=sys.stdout):
    """Make the key pair; save the recipient; return the identity (printed once by main, stored nowhere)."""
    p = pyrage()
    identity = p.x25519.Identity.generate()
    recipient = str(identity.to_public())
    with auth.config_lock():
        cfg = auth.load_config()
        block = cfg.get("backup") if isinstance(cfg.get("backup"), dict) else {}
        if block.get("recipient") and not replace:
            raise BackupError("a backup key exists already (use --replace to make a new one; older backups "
                              "still need the older key)")
        block = dict(block, recipient=recipient,
                     key_created=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
        block.setdefault("target", DEFAULT_TARGET)
        cfg["backup"] = block
        auth.save_config(cfg)
    return str(identity), recipient


# ---------------------------------------------------------------- run


def excluded(rel, target_rel):
    rel = rel.replace(os.sep, "/")
    for e in EXCLUDE + ((target_rel,) if target_rel else ()):
        if rel == e or rel.startswith(e + "/"):
            return True
    return False


def build_archive(src, fileobj, target=None, stream=False):
    """Write a tar.gz of `src` into `fileobj` (`stream`: a pipe, written strictly forwards). Returns (entries,
    skipped)."""
    src = Path(src)
    target_rel = None
    if target is not None:
        try:
            target_rel = str(Path(target).resolve().relative_to(src.resolve())).replace(os.sep, "/")
        except ValueError:
            target_rel = None
    entries = skipped = 0
    with tarfile.open(fileobj=fileobj, mode="w|gz" if stream else "w:gz", format=tarfile.PAX_FORMAT) as tar:
        for dirpath, dirnames, filenames in os.walk(src, followlinks=False):
            rel_dir = os.path.relpath(dirpath, src)
            rel_dir = "" if rel_dir == "." else rel_dir
            keep = []
            for d in sorted(dirnames):
                rel = os.path.join(rel_dir, d)
                if excluded(rel, target_rel):
                    continue
                if os.path.islink(os.path.join(dirpath, d)):
                    filenames.append(d)  # a symlinked folder is stored as a link, never followed
                    continue
                keep.append(d)
            dirnames[:] = keep
            if rel_dir:
                tar.add(dirpath, arcname=rel_dir, recursive=False)
                entries += 1
            for name in sorted(filenames):
                rel = os.path.join(rel_dir, name)
                path = os.path.join(dirpath, name)
                if excluded(rel, target_rel):
                    continue
                try:
                    mode = os.lstat(path).st_mode
                    if not (stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
                        skipped += 1  # sockets, fifos, devices
                        continue
                    tar.add(path, arcname=rel, recursive=False)
                    entries += 1
                except OSError:
                    skipped += 1  # gone or unreadable since the walk
    return entries, skipped


def backup_name(now):
    return f"lcs-backup-{now.astimezone(LONDON):%Y%m%d-%H%M%S}.tar.gz.age"


def name_time(name):
    m = NAME_RE.fullmatch(name)
    if not m:
        return None
    try:
        return datetime.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(tzinfo=LONDON)
    except ValueError:
        return None


def kept(times, now):
    """The backup times to keep: the newest; every one within KEEP of `now`; the last of each ISO week within
    KEEP_WEEKS weeks (the current week counts as one); the last of each calendar month within KEEP_MONTHS months."""
    times = sorted(times)
    keep = set(times[-1:])
    last_of_week, last_of_month = {}, {}
    for t in times:  # ascending, so each period ends up holding its last backup
        if now - t <= KEEP:
            keep.add(t)
        last_of_week[t.isocalendar()[:2]] = t
        last_of_month[(t.year, t.month)] = t
    this_monday = datetime.date.fromisocalendar(*now.isocalendar()[:2], 1)
    for (year, week), t in last_of_week.items():
        if (this_monday - datetime.date.fromisocalendar(year, week, 1)).days // 7 < KEEP_WEEKS:
            keep.add(t)
    for (year, month), t in last_of_month.items():
        if (now.year - year) * 12 + (now.month - month) < KEEP_MONTHS:
            keep.add(t)
    return keep


def prune(target, now, keep_name):
    """Remove the backups (exact name pattern, regular files) that `kept` doesn't keep, never `keep_name`, and .part
    files (exact name pattern, regular files) last written more than PART_KEEP ago. Returns the count of backups
    removed."""
    removed = 0
    backups = []
    for entry in os.scandir(target):
        if PART_RE.fullmatch(entry.name) and entry.is_file(follow_symlinks=False):
            written = datetime.datetime.fromtimestamp(entry.stat(follow_symlinks=False).st_mtime, LONDON)
            if now - written > PART_KEEP:
                os.unlink(entry.path)
            continue
        when = name_time(entry.name)
        if when is not None and entry.is_file(follow_symlinks=False):
            backups.append((when, entry))
    keep = kept([when for when, _ in backups], now)
    for when, entry in backups:
        if when not in keep and entry.name != keep_name:
            os.unlink(entry.path)
            removed += 1
    return removed


def encrypt_stream(p, rcpt, private, target, out):
    """tar.gz `private` into age-encrypted `out` through an os.pipe: a thread writes the archive into the pipe
    while age reads the other end, so the plaintext is never on disk. Returns (entries, skipped); an error on
    either side is raised here (the caller discards `out`)."""
    rfd, wfd = os.pipe()
    box = {}

    def produce():
        try:
            with os.fdopen(wfd, "wb") as w:
                box["counts"] = build_archive(private, w, target, stream=True)
        except BaseException as e:  # noqa: BLE001  handed to the main thread
            box["error"] = e

    worker = threading.Thread(target=produce, name="cc-backup-tar", daemon=True)
    worker.start()
    try:
        with os.fdopen(rfd, "rb") as r:  # closing it (even on an age error) ends the writer with a broken pipe
            p.encrypt_io(r, out, [rcpt])
    finally:
        worker.join()
    if "error" in box:
        raise box["error"]
    return box["counts"]


def run(now=None, private=None):
    """One backup. Returns a dict for the log line and the state file."""
    now = now or datetime.datetime.now(LONDON)
    private = Path(private or auth.private_dir())
    recipient, target = settings()
    if not recipient:
        raise BackupError("no backup key yet: run cc_backup.py init first")
    p = pyrage()
    try:
        rcpt = p.x25519.Recipient.from_str(recipient)
    except Exception:
        raise BackupError("the backup key in the config isn't an age recipient") from None
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.is_symlink() or not target.is_dir():
        raise BackupError("the backup folder isn't a real folder")
    lock_path = auth.config_dir() / "backup.lock"
    auth.config_dir().mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BackupError("another backup is running") from None
        name = backup_name(now)
        final = target / name
        part = target / f".{name}.{secrets.token_hex(4)}.part"
        fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "wb") as out:
                entries, skipped = encrypt_stream(p, rcpt, private, target, out)
                out.flush()
                os.fsync(out.fileno())
            os.replace(part, final)
        except BaseException:
            part.unlink(missing_ok=True)
            raise
        digest = hashlib.sha256()
        with open(final, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                digest.update(block)
        size = final.stat().st_size
        removed = prune(target, now, name)
        result = {"at": now.astimezone(datetime.timezone.utc).isoformat(timespec="seconds"), "name": name,
                  "size": size, "sha256": digest.hexdigest(), "entries": entries, "skipped": skipped,
                  "removed": removed}
        write_private_json(state_path(), result)
        return result
    finally:
        os.close(lock)


def notify(title, message):
    """A macOS notification (the nightly run has no one watching it). Quietly nothing elsewhere, or with
    LCS_NO_NOTIFY set."""
    if sys.platform != "darwin" or os.environ.get("LCS_NO_NOTIFY"):
        return
    script = f"display notification {json.dumps(message, ensure_ascii=False)} with title {json.dumps(title, ensure_ascii=False)}"
    try:
        subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def record_failure(detail, now=None):
    """Add "error" and "failed_at" to the state file, keeping the last good backup's fields."""
    found = {}
    try:
        found = json.loads(state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    state = found if isinstance(found, dict) else {}
    when = (now or datetime.datetime.now(datetime.timezone.utc)).astimezone(datetime.timezone.utc)
    state.update(error=str(detail)[:200], failed_at=when.isoformat(timespec="seconds"))
    write_private_json(state_path(), state)


# ---------------------------------------------------------------- verify


def newest(target):
    found = []
    for entry in os.scandir(target):
        when = name_time(entry.name)
        if when is not None and entry.is_file(follow_symlinks=False):
            found.append((when, entry.path))
    return max(found)[1] if found else None


def read_identity(stream=None):
    stream = stream or sys.stdin
    if stream.isatty():
        text = getpass.getpass("Backup key (AGE-SECRET-KEY-1…, from the password manager): ")
    else:
        text = stream.readline()
    return text.strip()


def verify(identity_text, target=None):
    """(backup path, [member names]) of the newest backup, decrypted with `identity_text`. Nothing is extracted."""
    p = pyrage()
    try:
        identity = p.x25519.Identity.from_str(identity_text)
    except Exception:
        raise BackupError("that isn't an age identity (AGE-SECRET-KEY-1…)") from None
    if target is None:
        _, target = settings()
    path = newest(target)
    if path is None:
        raise BackupError("no backup found")
    rfd, wfd = os.pipe()
    box = {}

    def produce(enc):
        try:
            with os.fdopen(wfd, "wb") as w:
                p.decrypt_io(enc, w, [identity])
        except BaseException as e:  # noqa: BLE001  a wrong key, or the reader stopped
            box["error"] = e

    names, tar_error = [], None
    with open(path, "rb") as enc:
        worker = threading.Thread(target=produce, args=(enc,), name="cc-backup-verify", daemon=True)
        worker.start()
        try:
            with os.fdopen(rfd, "rb") as r:  # streamed: the plaintext is never on disk
                try:
                    with tarfile.open(fileobj=r, mode="r|gz") as tar:
                        names = [m.name for m in tar]
                except Exception as e:  # noqa: BLE001  a truncated or foreign stream
                    tar_error = e
                while r.read(1 << 16):  # let the writer finish
                    pass
        finally:
            worker.join()
    if "error" in box:
        raise BackupError("this key doesn't open the newest backup")
    if tar_error is not None:
        raise BackupError("the newest backup opens but isn't a readable archive")
    return path, names


# ---------------------------------------------------------------- main


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cc_backup.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init", help="make the backup key (printed once)")
    p_init.add_argument("--replace", action="store_true", help="replace an existing key")
    sub.add_parser("run", help="make one backup now")
    sub.add_parser("verify", help="list the newest backup (the key on stdin)")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "init":
            if not sys.stdout.isatty():
                raise BackupError("init prints the key once, so it runs only in a terminal (not through a pipe, a "
                                  "log or a tool): open Terminal and run it there")
            identity, recipient = init(args.replace)
            print("Backup key made. The recipient (public) is saved in the Command Centre's config:")
            print(f"  {recipient}")
            print()
            print("Store this line in your password manager NOW. It is shown once and kept nowhere else;")
            print("without it no backup can be opened:")
            print()
            print(f"  {identity}")
            print()
            print("Then: bash command_centre/install.sh --backup   (the nightly LaunchAgent, 02:30)")
            del identity
        elif args.cmd == "run":
            try:
                r = run()
            except (BackupError, OSError, ValueError) as e:
                detail = str(e) if isinstance(e, BackupError) else type(e).__name__
                try:
                    record_failure(detail)
                except OSError:
                    pass
                notify("LCS backup failed", f"{detail}. The last good backup is still in iCloud Drive.")
                raise
            print(f"backup written: {r['name']} ({r['size'] / 1e6:,.1f} MB, {r['entries']} entries"
                  f"{', ' + str(r['skipped']) + ' skipped' if r['skipped'] else ''}); "
                  f"removed {r['removed']} not needed under the retention ({RETENTION_WORDS})")
        else:
            path, names = verify(read_identity())
            print(f"{os.path.basename(path)}: opens with this key; {len(names)} entries")
            for n in names[:LIST_MAX]:
                print(f"  {n}")
            if len(names) > LIST_MAX:
                print(f"  … and {len(names) - LIST_MAX} more")
    except (BackupError, OSError, ValueError) as e:
        detail = str(e) if isinstance(e, BackupError) else type(e).__name__
        print(f"cc_backup: {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
