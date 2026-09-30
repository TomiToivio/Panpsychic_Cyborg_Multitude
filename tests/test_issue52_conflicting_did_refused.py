# -*- coding: utf-8 -*-
"""Issue #52 — a conflicting did:key for a known label must not be adopted.

The in-band bootstrap (merged as 2f9117a) makes a node learn a peer's did:key
from a verified inbound contact. The identity is bound to the advertised
``node_label`` and checked against the expected agent name — but nothing stopped
a *later* contact presenting a **different** did:key for the same label. The
cache was overwritten unconditionally, and because the cache is read at
construction, the swap survived a restart.

Measured on the merged code, before this guard:

    genuine lh6 did       : did:key:z6Mkms4uZ4WjjUR6fKmaB9hxVZ...
    second identity did   : did:key:z6MkqkruJYfv5C54B3hfMBxWa5...

    AFTER RESTART, A adopts: did:key:z6MkqkruJYfv5C54B3hfMBxWa5...
      is it the GENUINE lh6?      False
      is it the SECOND identity?  True

So a node that had been re-pointed silently addressed a different identity under
its peer's label. These tests pin the guard: the first verified did for a label
wins, a conflicting one is refused and recorded, and a restart keeps the original.
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from multitude.integrations.hermes.coordination import PeerConfig, load_node_config
from multitude.integrations.hermes.coordination_adapter import CoordinationNode
from multitude.pcm.transport import InMemoryTransport


def _config(label: str, agent: str, peers=None):
    cfg = load_node_config({"PCM_NODE_LABEL": label, "PCM_AGENT_NAME": agent})
    cfg.peers = list(peers or [])
    return cfg


async def _contact_from(tmp: Path, bus, node_under_test, dirname: str):
    """A distinct identity labelled 'lh6-725-37563' contacts the node under test."""
    cfg = _config("lh6-725-37563", "agent:hermes-lh6-725-37563",
                  [PeerConfig(label="Laskin", host="bus", did=node_under_test.did)])
    impostor = CoordinationNode(bus, node_dir=tmp / dirname, config=cfg)
    await impostor.contact("Laskin", timeout=5.0)
    return impostor


class ConflictingDidTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def test_a_conflicting_did_is_refused_and_recorded(self) -> None:
        async def scenario():
            bus = InMemoryTransport()
            await bus.start()

            cfg_a = _config("Laskin", "agent:hermes-laskin",
                            [PeerConfig(label="lh6-725-37563", host="bus", did="")])
            a = CoordinationNode(bus, node_dir=self.tmp / "a", config=cfg_a)
            await a.start_serving()

            first = await _contact_from(self.tmp, bus, a, "c1")
            adopted = a.config.peer("lh6-725-37563").did
            self.assertEqual(adopted, first.did)

            second = await _contact_from(self.tmp, bus, a, "c2")
            self.assertNotEqual(second.did, adopted)
            await bus.stop()
            return a, adopted, second.did

        a, adopted, conflicting = asyncio.run(scenario())
        # in-process identity is unchanged
        self.assertEqual(a.config.peer("lh6-725-37563").did, adopted)
        # the conflicting value is recorded, not silently accepted
        self.assertIn("lh6-725-37563", a.rejected_dids)
        self.assertIn(conflicting, a.rejected_dids["lh6-725-37563"])

    def test_the_cache_keeps_the_first_did(self) -> None:
        async def scenario():
            bus = InMemoryTransport()
            await bus.start()
            cfg_a = _config("Laskin", "agent:hermes-laskin",
                            [PeerConfig(label="lh6-725-37563", host="bus", did="")])
            a = CoordinationNode(bus, node_dir=self.tmp / "b", config=cfg_a)
            await a.start_serving()

            first = await _contact_from(self.tmp, bus, a, "c3")
            adopted = a.config.peer("lh6-725-37563").did
            await _contact_from(self.tmp, bus, a, "c4")
            await bus.stop()
            return a, adopted, first.did

        a, adopted, genuine = asyncio.run(scenario())
        cache = json.loads((Path(a.node_dir) / "coordination" / "peer_dids.json").read_text())
        self.assertEqual(cache["peers"]["lh6-725-37563"], adopted)
        self.assertEqual(cache["peers"]["lh6-725-37563"], genuine)

    def test_a_restart_keeps_the_genuine_did(self) -> None:
        """The consequence that made this worth guarding: no silent re-point."""
        async def scenario():
            bus = InMemoryTransport()
            await bus.start()
            cfg_a = _config("Laskin", "agent:hermes-laskin",
                            [PeerConfig(label="lh6-725-37563", host="bus", did="")])
            a = CoordinationNode(bus, node_dir=self.tmp / "c", config=cfg_a)
            await a.start_serving()

            first = await _contact_from(self.tmp, bus, a, "c5")
            genuine = first.did
            await _contact_from(self.tmp, bus, a, "c6")
            await bus.stop()
            return a, genuine

        a, genuine = asyncio.run(scenario())

        # rebuild from the same node_dir with no peer did configured -- a restart
        cfg_a2 = _config("Laskin", "agent:hermes-laskin",
                         [PeerConfig(label="lh6-725-37563", host="bus", did="")])
        a2 = CoordinationNode(InMemoryTransport(), node_dir=a.node_dir, config=cfg_a2)
        self.assertEqual(a2.config.peer("lh6-725-37563").did, genuine)

    def test_an_agreeing_repeat_contact_is_not_a_conflict(self) -> None:
        """Idempotence: the same identity contacting twice must not be flagged."""
        async def scenario():
            bus = InMemoryTransport()
            await bus.start()
            cfg_a = _config("Laskin", "agent:hermes-laskin",
                            [PeerConfig(label="lh6-725-37563", host="bus", did="")])
            a = CoordinationNode(bus, node_dir=self.tmp / "d", config=cfg_a)
            await a.start_serving()

            cfg_c = _config("lh6-725-37563", "agent:hermes-lh6-725-37563",
                            [PeerConfig(label="Laskin", host="bus", did=a.did)])
            c = CoordinationNode(bus, node_dir=self.tmp / "d_peer", config=cfg_c)
            await c.contact("Laskin", timeout=5.0)
            await c.contact("Laskin", timeout=5.0)
            await bus.stop()
            return a

        a = asyncio.run(scenario())
        self.assertEqual(a.rejected_dids, {})

    def test_status_surfaces_rejected_dids(self) -> None:
        async def scenario():
            bus = InMemoryTransport()
            await bus.start()
            cfg_a = _config("Laskin", "agent:hermes-laskin",
                            [PeerConfig(label="lh6-725-37563", host="bus", did="")])
            a = CoordinationNode(bus, node_dir=self.tmp / "e", config=cfg_a)
            await a.start_serving()
            await _contact_from(self.tmp, bus, a, "c7")
            await _contact_from(self.tmp, bus, a, "c8")
            await bus.stop()
            return a

        a = asyncio.run(scenario())
        st = a.status()
        self.assertIn("rejected_dids", st)
        self.assertTrue(st["rejected_dids"].get("lh6-725-37563"))


if __name__ == "__main__":
    unittest.main()
