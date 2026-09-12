"""Launcher.

Binds loopback only by default. The app has no authentication of any kind,
so opening it to the network is opt-in: `--lan` is what you want when the
field app has to be reachable from a phone, and it mints a token for the
one destructive endpoint rather than leaving it open to everyone on the
wifi.
"""
from __future__ import annotations

import argparse
import os
import secrets

import uvicorn

LOOPBACK = ("127.0.0.1", "::1", "localhost")


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m setu.web")
    ap.add_argument("--host", default="127.0.0.1",
                    help="interface to bind (default: loopback only)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--lan", action="store_true",
                    help="bind 0.0.0.0 so a phone on the same wifi can "
                         "reach the field app")
    args = ap.parse_args()

    host = "0.0.0.0" if args.lan else args.host
    exposed = host not in LOOPBACK

    # POST /api/reset deletes every entry. On loopback that is a
    # convenience for one person on their own laptop; on a shared network
    # it is a one-request wipe of a live demo. Set the token before the app
    # module is imported, because that is when it reads the environment.
    if exposed and not os.environ.get("SETU_ADMIN_TOKEN"):
        os.environ["SETU_ADMIN_TOKEN"] = secrets.token_urlsafe(16)

    from . import app as _app          # after the environment is settled

    print("\n  SETU server")
    print(f"  database         {_app.DB_PATH}  "
          f"(journal {_app.STORE.journal})")
    print(f"  planner console  http://127.0.0.1:{args.port}/")
    print(f"  field app        http://127.0.0.1:{args.port}/field")
    if exposed:
        print(f"\n  bound to {host} — reachable by anyone on this network,")
        print("  with no login. Do not point this at real project data.")
        print("  On a phone, use this machine's own address in place of")
        print("  127.0.0.1 above.")
        print(f"  admin token      {os.environ['SETU_ADMIN_TOKEN']}")
        print("                   (send as X-SETU-Token to POST /api/reset)")
    print()
    uvicorn.run(_app.app, host=host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
