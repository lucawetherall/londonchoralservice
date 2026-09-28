"""python -m command_centre.bootstrap --new-bootstrap: issue a new one-time code for the first passkey.

The first passkey registration needs this code (install.sh prints one). Use this when that code expired
(30 minutes) or was lost before any passkey was registered. It stores only the code's sha256 and expiry in
~/lcs-private/command-centre/config.json and prints the code once. Once a passkey exists it refuses: another
device is added with a passkey you already have.
"""
import argparse
import sys

from . import auth


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m command_centre.bootstrap", description=__doc__.split("\n")[0])
    p.add_argument("--new-bootstrap", action="store_true", help="issue a new code (valid 30 minutes)")
    args = p.parse_args(argv)
    if not args.new_bootstrap:
        p.print_help(sys.stderr)
        return 2
    try:
        code = auth.new_bootstrap()
    except (OSError, ValueError):
        print(f"No readable config at {auth.config_path()}: run command_centre/install.sh first.", file=sys.stderr)
        return 1
    except auth.PasskeyError as e:
        print(f"Not issued: {e.reason}. Add another device with a passkey you already have.", file=sys.stderr)
        return 1
    print(f"Bootstrap code: {code}")
    print("It works once, for the first passkey only, and expires in 30 minutes. It is not stored anywhere.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
