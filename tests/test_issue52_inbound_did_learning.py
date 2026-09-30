# -*- coding: utf-8 -*-
"""Issue #52 — a contact you receive teaches you how to contact back.

The three-node matrix stood at 2/6 while every node waited for lh6 to publish a
did:key. The value was not missing: it arrives inside every contact request, in
the signed envelope's ``from`` field, already verified by
``accept_inbound_contact`` before the callback runs. The Hermes adapter kept
``from``, ``request_id``, ``kind`` and ``ts`` -- and dropped the did:key.

That made a node contactable by a peer it could not contact back, which is the
deadlock. These tests pin the fix and, more importantly, its two guards:

1. the did:key from a verified inbound envelope is retained and adopted, so one
   inbound contact opens the return direction;
2. **only configured peers are learned** -- a stranger cannot insert itself into
   the peer set by contacting us;
3. **a conflicting did for an already-known label is not adopted silently** --
   two live identities for one node is the ambiguity the runbook warns about.

Point 2 is the one that matters for safety: this is identity material learned
from network input, so the fix must not be able to widen a node's reach.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from multitude.integrations.hermes.coordination import PeerConfig, load_node_config
from multitude.integrations.hermes.coordination_adapter import CoordinationNode
from multitude.pcm.transport import InMemoryTransport


def _node(tmp: Path, label: str, agent: str, peers=None, dirname: str = "") -> CoordinationNode:
    cfg = load_node_config({"PCM_NODE_LABEL": label, "PCM_AGENT_NAME": agent})
    cfg.peers = list(peers or [])
    bus = InMemoryTransport()
    return CoordinationNode(bus, node_dir=tmp / (dirname or label), config=cfg)


class InboundDidLearningTests(unittest.TestCase):
    """The fix: an inbound verified did:key is retained and adopted."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def test_inbound_record_keeps_the_senders_did(self) -> None:
        """The regression: this field used to be discarded."""
        bus_holder = {}

        async def scenario():
            bus = InMemoryTransport()
            await bus.start()
            bus_holder["bus"] = bus

            cfg_a = load_node_config({"PCM_NODE_LABEL": "Laskin",
                                      "PCM_AGENT_NAME": "agent:hermes-laskin"})
            cfg_a.peers = []

            cfg_c = load_node_config({"PCM_NODE_LABEL": "lh6-725-37563",
                                      "PCM_AGENT_NAME": "agent:hermes-lh6-725-37563"})

            a = CoordinationNode(bus, node_dir=self.tmp / "a", config=cfg_a)
            await a.start_serving()

            cfg_c.peers = [PeerConfig(label="Laskin", host="bus", did=a.did)]
            c = CoordinationNode(bus, node_dir=self.tmp / "c", config=cfg_c)
            await c.contact("Laskin", timeout=5.0)

            await bus.stop()
            return a

        a = asyncio.run(scenario())
        self.assertTrue(a.inbound, "the contact should have been recorded")
        rec = a.inbound[0]
        self.assertIn("from_did", rec, "the sender's did:key must be retained")
        self.assertTrue(rec["from_did"].startswith("did:key:"))

    def test_return_direction_opens_from_one_inbound_contact(self) -> None:
        """End to end: C contacts A; A can then contact C with nothing published."""
        async def scenario():
            bus = InMemoryTransport()
            await bus.start()

            cfg_a = load_node_config({"PCM_NODE_LABEL": "Laskin",
                                      "PCM_AGENT_NAME": "agent:hermes-laskin"})
            cfg_a.peers = [PeerConfig(label="lh6-725-37563", host="bus", did="")]

            a = CoordinationNode(bus, node_dir=self.tmp / "a2", config=cfg_a)
            await a.start_serving()

            cfg_c = load_node_config({"PCM_NODE_LABEL": "lh6-725-37563",
                                      "PCM_AGENT_NAME": "agent:hermes-lh6-725-37563"})
            cfg_c.peers = [PeerConfig(label="Laskin", host="bus", did=a.did)]
            c = CoordinationNode(bus, node_dir=self.tmp / "c2", config=cfg_c)
            await c.start_serving()

            # before any inbound contact, A genuinely cannot reach C
            with self.assertRaises(Exception):
                await a.contact("lh6-725-37563", timeout=5.0)

            fwd = await c.contact("Laskin", timeout=5.0)
            self.assertTrue(fwd.verified)

            back = await a.contact("lh6-725-37563", timeout=5.0)
            self.assertTrue(back.verified)
            self.assertEqual(back.sender_label, "Laskin")
            self.assertEqual(back.recipient_label, "lh6-725-37563")

            await bus.stop()
            return back

        back = asyncio.run(scenario())
        self.assertTrue(back.verified)


class LearningGuardTests(unittest.TestCase):
    """The guards: learning from network input must not widen reach."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def test_a_stranger_does_not_become_an_addressable_peer(self) -> None:
        """An unknown sender is recorded, but never added to the peer set."""
        async def scenario():
            bus = InMemoryTransport()
            await bus.start()

            cfg_a = load_node_config({"PCM_NODE_LABEL": "Laskin",
                                      "PCM_AGENT_NAME": "agent:hermes-laskin"})
            cfg_a.peers = [PeerConfig(label="NooPunk", host="bus", did="")]

            a = CoordinationNode(bus, node_dir=self.tmp / "g1", config=cfg_a)
            await a.start_serving()

            stranger_cfg = load_node_config({"PCM_NODE_LABEL": "intruder",
                                             "PCM_AGENT_NAME": "agent:hermes-intruder"})
            stranger_cfg.peers = [PeerConfig(label="Laskin", host="bus", did=a.did)]
            s = CoordinationNode(bus, node_dir=self.tmp / "s1", config=stranger_cfg)
            await s.contact("Laskin", timeout=5.0)

            await bus.stop()
            return a

        a = asyncio.run(scenario())
        # recorded for inspection
        self.assertTrue(a.inbound)
        # but not addressable, and not learned under any peer label
        self.assertEqual(a._learned_dids, {})
        self.assertNotIn("intruder", a.config.peer_labels())
        self.assertNotIn("agent:hermes-intruder", a._learned_dids)

    def test_a_conflicting_did_is_not_adopted_silently(self) -> None:
        """Same label, different did -> record the conflict, keep the first."""
        async def scenario():
            bus = InMemoryTransport()
            await bus.start()

            cfg_a = load_node_config({"PCM_NODE_LABEL": "Laskin",
                                      "PCM_AGENT_NAME": "agent:hermes-laskin"})
            cfg_a.peers = [PeerConfig(label="lh6-725-37563", host="bus", did="")]

            a = CoordinationNode(bus, node_dir=self.tmp / "g2", config=cfg_a)
            await a.start_serving()

            # first contact from the real lh6 identity
            cfg_c = load_node_config({"PCM_NODE_LABEL": "lh6-725-37563",
                                      "PCM_AGENT_NAME": "agent:hermes-lh6-725-37563"})
            cfg_c.peers = [PeerConfig(label="Laskin", host="bus", did=a.did)]
            c = CoordinationNode(bus, node_dir=self.tmp / "c3", config=cfg_c)
            await c.contact("Laskin", timeout=5.0)
            adopted = a._learned_dids.get("lh6-725-37563")
            self.assertTrue(adopted)

            # a DIFFERENT identity claiming the same label
            cfg_impostor = load_node_config({"PCM_NODE_LABEL": "lh6-725-37563",
                                             "PCM_AGENT_NAME": "agent:hermes-lh6-725-37563"})
            cfg_impostor.peers = [PeerConfig(label="Laskin", host="bus", did=a.did)]
            imp = CoordinationNode(bus, node_dir=self.tmp / "i3", config=cfg_impostor)
            self.assertNotEqual(imp.did, adopted)
            await imp.contact("Laskin", timeout=5.0)

            await bus.stop()
            return a, adopted

        a, adopted = asyncio.run(scenario())
        # the adopted did is unchanged, and the second one is recorded as a conflict
        self.assertEqual(a._learned_dids.get("lh6-725-37563"), adopted)
        self.assertIn("lh6-725-37563", a._did_conflicts)
        self.assertTrue(a._did_conflicts["lh6-725-37563"])

    def test_a_configured_did_is_never_overwritten(self) -> None:
        """Explicit configuration wins; learning only fills blanks."""
        async def scenario():
            bus = InMemoryTransport()
            await bus.start()

            cfg_c = load_node_config({"PCM_NODE_LABEL": "lh6-725-37563",
                                      "PCM_AGENT_NAME": "agent:hermes-lh6-725-37563"})
            c = CoordinationNode(bus, node_dir=self.tmp / "c4", config=cfg_c)

            cfg_a = load_node_config({"PCM_NODE_LABEL": "Laskin",
                                      "PCM_AGENT_NAME": "agent:hermes-laskin"})
            cfg_a.peers = [PeerConfig(label="lh6-725-37563", host="bus",
                                      did="did:key:z6MkConfiguredPlaceholderValue11111")]
            a = CoordinationNode(bus, node_dir=self.tmp / "a4", config=cfg_a)
            await a.start_serving()

            cfg_c.peers = [PeerConfig(label="Laskin", host="bus", did=a.did)]
            c.config = cfg_c
            await c.contact("Laskin", timeout=5.0)

            await bus.stop()
            return a

        a = asyncio.run(scenario())
        configured = a.config.peer("lh6-725-37563").did
        self.assertEqual(configured, "did:key:z6MkConfiguredPlaceholderValue11111")


class StatusSurfaceTests(unittest.TestCase):
    def test_status_reports_learned_dids_and_conflicts(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        cfg = load_node_config({"PCM_NODE_LABEL": "Laskin",
                                "PCM_AGENT_NAME": "agent:hermes-laskin"})
        cfg.peers = [PeerConfig(label="NooPunk", host="h", did="did:key:z6MkX")]
        node = CoordinationNode(InMemoryTransport(), node_dir=tmp / "st", config=cfg)
        st = node.status()
        self.assertIn("learned_dids", st)
        self.assertIn("did_conflicts", st)
        peer = next(p for p in st["peers"] if p["label"] == "NooPunk")
        self.assertTrue(peer["did_known"])
        self.assertEqual(peer["did_source"], "configured")

    def test_a_peer_with_no_did_reports_not_known(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        cfg = load_node_config({"PCM_NODE_LABEL": "Laskin",
                                "PCM_AGENT_NAME": "agent:hermes-laskin"})
        cfg.peers = [PeerConfig(label="lh6-725-37563", host="h", did="")]
        node = CoordinationNode(InMemoryTransport(), node_dir=tmp / "st2", config=cfg)
        peer = next(p for p in node.status()["peers"] if p["label"] == "lh6-725-37563")
        self.assertFalse(peer["did_known"])
        self.assertEqual(peer["did_source"], "")


if __name__ == "__main__":
    unittest.main()
