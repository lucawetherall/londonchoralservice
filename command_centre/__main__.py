"""python -m command_centre [--uds [PATH]]: serve the app on 127.0.0.1 (never any other address), or on a Unix
socket.

- TCP (the LaunchAgent's default): 127.0.0.1:${CC_PORT:-8765}. CC_PORT picks another port for a local check.
- `--uds [PATH]`: a Unix socket instead, by default ~/lcs-private/command-centre/run/cc.sock, in a directory
  this makes mode 700 (so only this user can connect); `tailscale serve ... unix:<PATH>` can point at it.
- CC_DEV_LOGIN, for a local check only, stands in for the Tailscale identity headers. create_app refuses it on
  port 8765 and on the socket; the LaunchAgent sets it to "".

The service (port 8765 or the socket) also runs the push watcher (command_centre/push.py).

On start, logs over 5 MB in ~/lcs-private/command-centre/logs are rotated (3 kept): launchd can't rotate them.
"""
import argparse
import logging
import os
import stat
import sys
from pathlib import Path

import uvicorn

from . import auth
from .app import checkout_branch, checkout_warning, create_app

HOST = "127.0.0.1"  # loopback only: `tailscale serve` is the only way in from another device
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_KEEP = 3
log = logging.getLogger("command_centre")


def default_uds():
    return str(auth.config_dir() / "run" / "cc.sock")


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="python -m command_centre", description=__doc__.split("\n")[0])
    p.add_argument("--uds", nargs="?", const=default_uds(), default=None, metavar="PATH",
                   help="serve on this Unix socket instead of TCP (default path: %(const)s)")
    return p.parse_args(argv)


def prepare_uds(path):
    """Make the socket's directory mode 700 and owned by this user; refuse a symlinked or foreign one."""
    parent = Path(path).parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    st = os.lstat(parent)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
        sys.exit(f"Refusing the socket directory {parent}: it must be a real directory owned by this user.")
    os.chmod(parent, 0o700)
    return str(path)


def rotate_logs(log_dir, max_bytes=LOG_MAX_BYTES, keep=LOG_KEEP, fds=(1, 2)):
    """Rotate each *.log in `log_dir` over `max_bytes`: x.log -> x.log.1 -> ... -> x.log.<keep>, the oldest
    dropped. launchd opened stdout/stderr on those files before we started, so any of `fds` that pointed at a
    rotated file is reopened on a fresh one (mode 600)."""
    d = Path(log_dir)
    if not d.is_dir():
        return
    for path in sorted(d.glob("*.log")):
        try:
            st = path.stat()
        except OSError:
            continue
        if st.st_size <= max_bytes:
            continue
        watching = []
        for fd in fds:
            try:
                fst = os.fstat(fd)
            except OSError:
                continue
            if (fst.st_dev, fst.st_ino) == (st.st_dev, st.st_ino):
                watching.append(fd)
        for i in range(keep - 1, 0, -1):
            older = path.with_name(f"{path.name}.{i}")
            if older.exists():
                os.replace(older, path.with_name(f"{path.name}.{i + 1}"))
        os.replace(path, path.with_name(f"{path.name}.1"))
        new = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            for fd in watching:
                os.dup2(new, fd)
        finally:
            os.close(new)


def main(argv=None):
    rotate_logs(auth.config_dir() / "logs")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    warning = checkout_warning(checkout_branch())
    if warning:
        log.warning("%s", warning)
    common = dict(proxy_headers=False, server_header=False, date_header=False, access_log=False, log_level="info")
    if args.uds:
        path = prepare_uds(args.uds)
        uvicorn.run(create_app(bind_host=HOST, uds=path, watch=True), uds=path, **common)
    else:
        port = int(os.environ.get("CC_PORT", str(auth.SERVICE_PORT)))
        # the push watcher runs in the service only, never on a spare port for a local check
        uvicorn.run(create_app(bind_host=HOST, port=port, watch=port == auth.SERVICE_PORT), host=HOST, port=port,
                    **common)


if __name__ == "__main__":
    main()
