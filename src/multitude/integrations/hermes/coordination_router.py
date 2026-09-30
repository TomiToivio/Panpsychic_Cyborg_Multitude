# -*- coding: utf-8 -*-
"""``pcm-coordination-router`` — a Zenoh rendezvous point for PCM coordination.

Routers exist for one reason here: issue #52 asks the experiment to work when the
three nodes are **not** on the same LAN, and Zenoh's own answer to that is a
router. Peer mode (multicast scouting) is the default for a shared LAN; this
binary is for when the machines are on different networks or behind NAT.

A router is **plumbing, never an authority** (docs/NETWORKING_STACK.md §3). It
forwards messages and does not authorize anything: the signed PCM envelopes are
what make a contact trustworthy, and every check in ``pcm.contact`` runs on the
endpoints regardless of how the bytes travelled.

Bind address:

    pcm-coordination-router --listen tcp/<address>:7447

``<address>`` must be reachable by the other nodes. A tailnet address works well
because each machine keeps a stable one; loopback is fine for a local test. Only
the listen address is deployment-specific, and it is passed on the command line,
never committed.

Run it as an ordinary foreground process (cron/systemd/whatever supervises the
process on the rendezvous host). It holds no keys and stores no research data.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time

DEFAULT_PORT = 7447


def build_config(listen: list[str]):
    """Zenoh config for a plain forwarding router."""
    import zenoh

    cfg = zenoh.Config()
    cfg.insert_json5("mode", json.dumps("router"))
    cfg.insert_json5("listen/endpoints", json.dumps(listen))
    return cfg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pcm-coordination-router",
        description="Zenoh rendezvous router for PCM coordination (issue #52).")
    parser.add_argument(
        "--listen", action="append", default=None,
        help="listen endpoint, e.g. tcp/100.64.0.1:7447 (repeatable). "
             f"Default: tcp/0.0.0.0:{DEFAULT_PORT}")
    parser.add_argument("--quiet", action="store_true", help="do not print the banner")
    args = parser.parse_args(argv)

    try:
        import zenoh
    except ImportError:
        print(
            "eclipse-zenoh is not installed; install it with:\n"
            "  pip install -e '.[zenoh]'   (or: pip install eclipse-zenoh)",
            file=sys.stderr,
        )
        return 1

    listen = args.listen or [f"tcp/0.0.0.0:{DEFAULT_PORT}"]
    router = zenoh.open(build_config(listen))
    if not args.quiet:
        print("PCM coordination router listening on: " + ", ".join(listen))
        print("routers forward; they do not authorize. Signed PCM envelopes decide trust.")

    stop = False

    def _handle(_signum, _frame):
        nonlocal stop
        stop = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle)
        except (ValueError, OSError):  # not the main thread / unsupported
            pass
    try:
        while not stop:
            time.sleep(0.5)
    finally:
        router.close()
        if not args.quiet:
            print("router stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
