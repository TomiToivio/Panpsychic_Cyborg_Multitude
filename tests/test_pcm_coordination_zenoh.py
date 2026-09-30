# -*- coding: utf-8 -*-
"""Issue #52 — the coordination protocol over REAL Zenoh, two live sessions.

``tests/test_pcm_coordination.py`` proves the protocol semantics in-process. This
file proves the protocol actually rides Zenoh: two independent Zenoh sessions
(multicast-scouted peers on the host) with distinct PCM identities exchange a
signed contact and a correlated acknowledgement, over the same canonical
envelopes and selectors a three-machine deployment uses.

What this does and does not establish, stated honestly because issue #52 is
explicit that "mere discovery" is not proof:

- it establishes that the wire path works: request reaches the peer's queryable,
  the signed ack comes back, correlation holds, and the contact matrix fills;
- it does NOT establish the three-machine matrix. Two sessions on one host are
  not three hosts. The real experiment is the runbook in
  ``docs/HERMES_COORDINATION.md``; this test is the closest thing CI can do
  without the live machines, which is exactly what the issue asks for when it
  says CI coverage must not need the three live machines.

Requires the optional extra (``pip install eclipse-zenoh``); skipped otherwise,
like the existing Zenoh tests.
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.integrations.hermes.contact_store import ContactLedger  # noqa: E402
from multitude.integrations.hermes.coordination import (  # noqa: E402
    NodeConfig,
    PeerConfig,
    agent_name_for,
)
from multitude.integrations.hermes.coordination_adapter import CoordinationNode  # noqa: E402
from multitude.integrations.zenoh.fabric import ZenohTransport  # noqa: E402
from multitude.pcm.identity import generate_identity, private_key_from_identity  # noqa: E402

pytestmark = pytest.mark.zenoh


def _zenoh_available() -> bool:
    return importlib.util.find_spec("zenoh") is not None


def _node(tmp: Path, label: str, peers: list[str]):
    directory = tmp / label
    directory.mkdir(parents=True, exist_ok=True)
    identity = generate_identity(str(directory))
    transport = ZenohTransport({"pcm_id": agent_name_for(label)})
    node = CoordinationNode(
        transport,
        node_dir=directory,
        config=NodeConfig(
            label=label,
            agent_name=agent_name_for(label),
            peers=[PeerConfig(label=p, host="localhost") for p in peers],
        ),
    )
    return node, private_key_from_identity(identity)


@pytest.mark.skipif(not _zenoh_available(), reason="eclipse-zenoh not installed")
def test_contact_over_real_zenoh_sessions() -> None:
    """Two live Zenoh sessions complete a signed, correlated contact."""

    async def scenario() -> None:
        os.environ.setdefault("PCM_ZENOH_ENABLED", "true")
        tmp = Path(tempfile.mkdtemp(prefix="pcm-coord-zenoh-"))

        a, _ = _node(tmp, "NooPunk", ["Laskin"])
        b, _ = _node(tmp, "Laskin", ["NooPunk"])
        await a.transport.start()
        await b.transport.start()
        await a.start_serving()
        await b.start_serving()
        await asyncio.sleep(0.8)  # scouting + queryable declaration settle

        # each node learns the other's public did (in deployment: PCM_PEER_DIDS)
        a.config.peers = [PeerConfig(label="Laskin", host="localhost", did=b.did)]
        b.config.peers = [PeerConfig(label="NooPunk", host="localhost", did=a.did)]

        forward = await a.contact("Laskin", note="hello over zenoh", timeout=5.0)
        backward = await b.contact("NooPunk", note="and back", timeout=5.0)

        assert (forward.sender_label, forward.recipient_label) == ("NooPunk", "Laskin")
        assert (backward.sender_label, backward.recipient_label) == ("Laskin", "NooPunk")
        assert forward.verified and backward.verified
        # B really received and answered A's request over the fabric
        assert any(item["request_id"] == forward.request_id for item in b.inbound)

        # the two proven contacts alone are not the six-entry matrix
        ledger = ContactLedger(required=["Laskin", "lh6-725-37563", "NooPunk"])
        ledger.add_store(a.store)
        ledger.add_store(b.store)
        report = ledger.report()
        assert report["confirmed_count"] == 2
        assert report["complete"] is False
        assert {"from": "NooPunk", "to": "Laskin"} not in report["missing"]

        await a.transport.stop()
        await b.transport.stop()

    asyncio.run(scenario())


@pytest.mark.skipif(not _zenoh_available(), reason="eclipse-zenoh not installed")
def test_a_peer_that_is_present_but_silent_is_not_a_contact() -> None:
    """The issue's core warning, over real Zenoh: visible is not contacted."""

    async def scenario() -> None:
        os.environ.setdefault("PCM_ZENOH_ENABLED", "true")
        tmp = Path(tempfile.mkdtemp(prefix="pcm-coord-zenoh-silent-"))

        a, _ = _node(tmp, "NooPunk", ["Laskin"])
        b, _ = _node(tmp, "Laskin", ["NooPunk"])
        await a.transport.start()
        await b.transport.start()
        # B joins the fabric with a liveliness token but declares NO queryable:
        # it is discoverable, and cannot be contacted.
        await asyncio.sleep(0.8)
        a.config.peers = [PeerConfig(label="Laskin", host="localhost", did=b.did)]

        from multitude.integrations.hermes.coordination_adapter import CoordinationError
        with pytest.raises(CoordinationError):
            await a.contact("Laskin", timeout=2.0)

        await a.transport.stop()
        await b.transport.stop()

    asyncio.run(scenario())


@pytest.mark.skipif(not _zenoh_available(), reason="eclipse-zenoh not installed")
def test_contact_through_a_router_rendezvous() -> None:
    """The WAN/NAT topology: two client sessions meet through one router.

    This is the configuration issue #52 asks for when peers are not on one LAN,
    and it closes the networking stack's own open risk that "router topologies
    are untested in CI" (docs/NETWORKING_STACK.md §13.6).

    The router binds to loopback here so the test needs nothing external; in a
    real cross-host deployment it binds to an address both machines can reach
    (e.g. a tailnet address), which is exactly what the runbook documents.
    """

    async def scenario() -> None:
        import json as _json

        import zenoh
        from zenoh import Config

        os.environ.setdefault("PCM_ZENOH_ENABLED", "true")
        tmp = Path(tempfile.mkdtemp(prefix="pcm-coord-router-"))
        endpoint = "tcp/127.0.0.1:17457"

        cfg = Config()
        cfg.insert_json5("mode", _json.dumps("router"))
        cfg.insert_json5("listen/endpoints", _json.dumps([endpoint]))
        router = zenoh.open(cfg)
        try:
            a, _ = _node(tmp, "NooPunk", ["Laskin"])
            b, _ = _node(tmp, "Laskin", ["NooPunk"])
            # both sessions are clients of the router, not LAN peers
            a.transport._connect = [endpoint]
            b.transport._connect = [endpoint]
            await a.transport.start()
            await b.transport.start()
            await a.start_serving()
            await b.start_serving()
            await asyncio.sleep(1.0)

            a.config.peers = [PeerConfig(label="Laskin", host="127.0.0.1", did=b.did)]
            b.config.peers = [PeerConfig(label="NooPunk", host="127.0.0.1", did=a.did)]

            forward = await a.contact("Laskin", note="routed", timeout=6.0)
            backward = await b.contact("NooPunk", note="routed back", timeout=6.0)

            assert (forward.sender_label, forward.recipient_label) == ("NooPunk", "Laskin")
            assert (backward.sender_label, backward.recipient_label) == ("Laskin", "NooPunk")
            assert forward.request_id in [i["request_id"] for i in b.inbound]

            await a.transport.stop()
            await b.transport.stop()
        finally:
            router.close()

    asyncio.run(scenario())
