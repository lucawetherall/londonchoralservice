"""python -m command_centre: serve the app on 127.0.0.1 (never any other address).

CC_PORT picks another port for a local check (default 8765, the port `tailscale serve` points at).
CC_DEV_LOGIN, for a local check only, stands in for the Tailscale identity headers; the LaunchAgent never sets it.
"""
import logging
import os

import uvicorn

from .app import create_app

HOST = "127.0.0.1"  # loopback only: `tailscale serve` is the only way in from another device


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    port = int(os.environ.get("CC_PORT", "8765"))
    uvicorn.run(create_app(bind_host=HOST), host=HOST, port=port, proxy_headers=False, server_header=False,
                date_header=False, access_log=False, log_level="info")


if __name__ == "__main__":
    main()
