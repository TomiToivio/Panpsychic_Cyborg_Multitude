# -*- coding: utf-8 -*-
"""``pcm-coordination`` — the operator CLI for the Hermes three-node experiment.

Issue #52 asks for commands an agent (or the operator) can actually run:

    pcm-coordination status                 what this node is, and what is missing
    pcm-coordination contact Laskin          contact one named peer
    pcm-coordination contact-all             contact every configured peer
    pcm-coordination report                  the contact matrix from evidence
    pcm-coordination serve                   join the fabric and answer contacts

Configuration is environment-only, so nothing machine-specific lives in the repo:

    PCM_NODE_LABEL=NooPunk
    PCM_AGENT_NAME=agent:hermes-noopunk          (default: derived from the label)
    PCM_PEERS=Laskin=host-a,lh6-725-37563=host-b
    PCM_PEER_DIDS=Laskin=did:key:z...,lh6-725-37563=did:key:z...
    PCM_ZENOH_CONNECT=tcp/host-a:7447            (client/router mode; omit for LAN peer mode)
    PCM_ZENOH_ENABLED=true                       (the transport's existing dormancy guard)

``contact-all`` writes evidence to the node's store (``<node_dir>/coordination/``
by default, i.e. under runtime data). ``report`` merges evidence from the local
store plus any ``--store`` files given, so each machine contributes its own half
and the merged report covers the whole experiment.

The CLI never fills in a "confirmed" cell by hand: every entry comes from a
verified round trip, and a contact that failed is printed as missing.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from multitude.integrations.hermes.contact_store import ContactLedger, ContactStore
from multitude.integrations.hermes.coordination import PeerConfig, load_node_config
from multitude.integrations.hermes.coordination_adapter import (
    CoordinationError,
    CoordinationNode,
)
from multitude.pcm.contact import contact_selector_for_did, default_required_nodes


def _default_node_dir() -> Path:
    """Where this node keeps its identity and contact evidence (runtime data)."""
    import os
    return Path(os.environ.get("PCM_NODE_DIR", "data/coordination"))


def _build_node(args: argparse.Namespace, *, enable_listener: bool = True) -> CoordinationNode:
    """Build this node with the transport the operator selected.

    ADR-001 records HTTP/JSON as the first runtime transport and Zenoh as the
    documented upgrade, so the selection is a configuration choice rather than a
    code change. ``PCM_COORDINATION_TRANSPORT`` picks it:

    - ``http`` (or unset with ``PCM_COORDINATION_LISTEN`` set; outbound-only
      commands also infer HTTP from configured peers): the isolated HTTP/JSON binding;
    - ``zenoh``: the Zenoh fabric (the pre-existing default).

    Both implement the same ``Transport`` ABC, so nothing else in this module
    knows which one is running.
    """
    import os

    config = load_node_config()
    if args.label:
        config.label = args.label

    which = os.environ.get("PCM_COORDINATION_TRANSPORT", "").strip().lower()
    listen = os.environ.get("PCM_COORDINATION_LISTEN", "").strip()
    if not which:
        # The accepted #52 runtime is HTTP. A long-lived server reveals that
        # choice through PCM_COORDINATION_LISTEN; outbound client commands do not
        # need a local listener, so configured peers are enough to select HTTP.
        # Zenoh remains the fallback only when neither HTTP signal is present.
        which = "http" if (listen or (not enable_listener and config.peers)) else "zenoh"

    if which == "http":
        from multitude.integrations.coordination.http_transport import HttpJsonTransport

        listen_host: str | None = None
        listen_port: int | None = None
        if enable_listener:
            host, _, port = listen.partition(":")
            if not host or not port.isdigit():
                raise SystemExit(
                    "PCM_COORDINATION_LISTEN must be <host>:<port> when the transport is "
                    f"http and a listener is required (got {listen!r}); use a local "
                    "bind address and a free port"
                )
            listen_host = host
            listen_port = int(port)

        # The HTTP binding has no discovery: addressing is deployment state, so
        # each peer's URL must be supplied explicitly. Rebuild rather than mutate,
        # so the peer list is never left half-rewritten.
        peers = [
            PeerConfig(
                label=peer.label,
                host=peer.host
                if peer.host.startswith("http")
                else f"http://{peer.host}",
                did=peer.did,
            )
            for peer in config.peers
        ]
        config.peers = peers

        # The protocol calls request(selector) with no URL — it must not know about
        # transports. So hand the binding the address book it needs, keyed by the
        # selector the contact layer will actually use.
        peer_urls = {
            contact_selector_for_did(peer.did): peer.host
            for peer in peers
            if peer.did and peer.host
        }

        transport: Any = HttpJsonTransport(
            {"pcm_id": config.agent_name},
            listen_host=listen_host,
            listen_port=listen_port,
            peer_urls=peer_urls,
        )
    elif which == "zenoh":
        from multitude.integrations.zenoh.fabric import ZenohTransport

        transport = ZenohTransport({"pcm_id": config.agent_name})
    else:
        raise SystemExit(
            f"unknown PCM_COORDINATION_TRANSPORT {which!r}; expected 'http' or 'zenoh'"
        )

    return CoordinationNode(
        transport,
        node_dir=Path(args.node_dir) if args.node_dir else _default_node_dir(),
        config=config,
        evidence_path=args.store,
    )


def cmd_status(args: argparse.Namespace) -> int:
    node = _build_node(args)
    status = node.status()
    status["report"] = node.report()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    missing = node.matrix().missing_pairs()
    if missing:
        print(f"\n{len(missing)} directed contact(s) still missing:", file=sys.stderr)
        for sender, recipient in missing:
            print(f"  {sender} -> {recipient}", file=sys.stderr)
    else:
        print("\nall required directed contacts are confirmed", file=sys.stderr)
    return 0


async def _with_serving(node: CoordinationNode, coro_factory):
    """Start the transport + queryable, run the operation, then stop."""
    await node.transport.start()
    await node.start_serving()
    try:
        return await coro_factory()
    finally:
        await node.transport.stop()


def cmd_contact(args: argparse.Namespace) -> int:
    # Outbound contact is deliberately client-only. The normal live procedure
    # keeps `pcm-coordination serve` running in another process; binding the same
    # listen port here would race that server and fail with "address already in use".
    node = _build_node(args, enable_listener=False)

    async def run():
        await node.transport.start()
        try:
            return await node.contact(args.peer, note=args.note, timeout=args.timeout)
        finally:
            await node.transport.stop()

    try:
        evidence = asyncio.run(run())
    except CoordinationError as exc:
        print(f"contact failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "status": "confirmed",
        "from": evidence.sender_label,
        "to": evidence.recipient_label,
        "request_id": evidence.request_id,
        "ack_id": evidence.ack_id,
        "ack_ts": evidence.ack_ts,
    }, indent=2))
    return 0


def cmd_contact_all(args: argparse.Namespace) -> int:
    # Same rule as `contact`: outgoing matrix work must be able to run while the
    # node's dedicated `serve` process owns the listener.
    node = _build_node(args, enable_listener=False)

    async def run():
        await node.transport.start()
        try:
            return await node.contact_all(note=args.note, timeout=args.timeout)
        finally:
            await node.transport.stop()

    results = asyncio.run(run())
    print(json.dumps(results, indent=2))
    return 0 if all(r["status"] == "confirmed" for r in results.values()) else 1


def cmd_report(args: argparse.Namespace) -> int:
    required = default_required_nodes()
    ledger = ContactLedger(required=required)
    store_paths = list(args.store_files or [])
    default_store = Path(args.store) if args.store else (_default_node_dir() / "coordination"
                                                         / "contacts.json")
    if default_store.exists():
        store_paths.append(str(default_store))
    for path in store_paths:
        if not Path(path).exists():
            print(f"store not found: {path}", file=sys.stderr)
            return 1
        ledger.add_store(ContactStore(path))

    report = ledger.report()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nreport written to {args.output}", file=sys.stderr)
    return 0 if report["complete"] else 1


def cmd_serve(args: argparse.Namespace) -> int:
    node = _build_node(args)

    async def run():
        await node.transport.start()
        await node.start_serving()
        print(f"{node.label} serving contacts as {node.agent_name} ({node.did[:28]}...)")
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            await node.transport.stop()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        return 0
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pcm-coordination",
        description="PCM coordination between Hermes nodes (issue #52).")
    parser.add_argument("--label", help="override PCM_NODE_LABEL for this run")
    parser.add_argument("--node-dir", help="identity + evidence directory (runtime data)")
    parser.add_argument("--store", help="evidence store path for this node")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show this node and the missing contacts")

    contact = sub.add_parser("contact", help="contact one named peer")
    contact.add_argument("peer")
    contact.add_argument("--note", default="")
    contact.add_argument("--timeout", type=float, default=5.0)

    allp = sub.add_parser("contact-all", help="contact every configured peer")
    allp.add_argument("--note", default="")
    allp.add_argument("--timeout", type=float, default=5.0)

    report = sub.add_parser("report", help="print the contact matrix from evidence")
    report.add_argument("--output", help="also write the report JSON here")
    report.add_argument("--store-file", action="append", dest="store_files",
                        help="an additional node's evidence store to merge (repeatable)")

    sub.add_parser("serve", help="join the fabric and answer contacts")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "contact":
        return cmd_contact(args)
    if args.command == "contact-all":
        return cmd_contact_all(args)
    if args.command == "report":
        return cmd_report(args)
    if args.command == "serve":
        return cmd_serve(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
