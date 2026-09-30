# -*- coding: utf-8 -*-
"""Issue #66 — a cast vote is not retroactively excluded, and runtimes agree.

Two properties the issue asks for that the first pass did not test:

1. "a cast vote is not retroactively excluded" -- a standing change must not
   reach backwards and rewrite a finished act. Under a majority or unanimity rule
   the old behaviour could flip a proposal's outcome after a member had already
   participated.
2. "the runtime paths agree (Hermes / Claude / Telegram parity)" -- the same
   membership must not produce different rights depending on which runtime drives
   it. This is the property that made the defect worth filing: the revert existed
   on two of the three paths and not the third.

Deliberately NOT tested here: departure semantics. `tally()` still excludes a
member that has *left*, which is an existing separate policy; the defect was only
about a present member's standing being rewritten underneath a vote already cast.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.models import NodeKind, Position  # noqa: E402
from multitude.rhizome import Rhizome  # noqa: E402
from multitude.service import MultitudeService  # noqa: E402

#: The runtime paths that must agree. `llm.TechnologicalNode` is the Telegram one.
RUNTIMES = ("hermes", "claude", "telegram")


def _rhizome() -> Rhizome:
    tmp = Path(tempfile.mkdtemp(prefix="pcm-66-"))
    r = Rhizome.found(str(tmp), "Test Rhizome", "charter", "tomi")
    r.join("human2", NodeKind.BIOLOGICAL)
    return r


def _join_via(runtime: str, rhizome: Rhizome, name: str = "AI"):
    """Join a technological member through a real runtime path."""
    if runtime == "hermes":
        from multitude.integrations.hermes.adapter import (
            HermesPermissions,
            MultitudeHermesAdapter,
        )

        ad = MultitudeHermesAdapter(rhizome=rhizome, agent_name=name,
                                    permissions=HermesPermissions())
        ad.ensure_agent()
        return ad
    if runtime == "claude":
        from multitude.integrations.claude.adapter import ClaudeCodeAdapter
        from multitude.integrations.hermes.adapter import HermesPermissions

        ad = ClaudeCodeAdapter(rhizome=rhizome, agent_name=name,
                               permissions=HermesPermissions())
        ad.ensure_agent()
        return ad
    if runtime == "telegram":
        from multitude.llm import TechnologicalNode

        node = TechnologicalNode(rhizome, name, voting=False)
        return node
    raise AssertionError(f"unknown runtime {runtime!r}")


def _ordinary_work(runtime: str, adapter) -> None:
    """One ordinary call on that runtime -- the thing that caused the revert."""
    if runtime in ("hermes", "claude"):
        adapter.ensure_agent()
        if hasattr(adapter, "create_proposal"):
            adapter.create_proposal("work", "body")
    else:
        adapter.ensure_agent() if hasattr(adapter, "ensure_agent") else None


class CastVoteIsNotRetroactivelyExcludedTests(unittest.TestCase):
    def test_a_demoted_members_cast_vote_stays_in_the_tally(self) -> None:
        """#66's own measurement: {'for': 3} must not silently become {'for': 2}."""
        r = _rhizome()
        r.join("AI", NodeKind.TECHNOLOGICAL, voting=True)
        pid = r.open_proposal("p", "body", opened_by="tomi").id
        r.cast_vote(pid, "human2", Position.FOR)
        r.cast_vote(pid, "AI", Position.FOR)

        before = r.tally(pid)
        self.assertEqual(before["counts"]["for"], 2)
        self.assertEqual(before["votes_cast"], 2)

        MultitudeService(r).demote("AI", actor="tomi")

        after = r.tally(pid)
        self.assertEqual(after["counts"]["for"], 2,
                         "a demotion reached backwards and removed a cast vote")
        self.assertEqual(after["votes_cast"], 2)
        self.assertFalse(r.member_by_name("AI").voting)

    def test_the_tally_names_the_non_voting_votes_it_counted(self) -> None:
        """The change must be visible, not silent.

        Counting the vote is right; hiding that its member is no longer entitled
        would replace one silent behaviour with another.
        """
        r = _rhizome()
        r.join("AI", NodeKind.TECHNOLOGICAL, voting=True)
        pid = r.open_proposal("p", "body", opened_by="tomi").id
        r.cast_vote(pid, "AI", Position.FOR)
        self.assertNotIn("non_voting_votes", r.tally(pid))

        MultitudeService(r).demote("AI", actor="tomi")
        self.assertEqual(r.tally(pid).get("non_voting_votes"), ["AI"])

    def test_a_departed_members_votes_are_still_excluded(self) -> None:
        """Departure semantics are deliberately unchanged by #66.

        Excluding a member that has left is existing policy and a different
        question from the defect: they are not present to be governed by the
        outcome. This test exists so a future change cannot quietly widen #66's
        fix into departure semantics.
        """
        r = _rhizome()
        r.join("AI", NodeKind.TECHNOLOGICAL, voting=True)
        pid = r.open_proposal("p", "body", opened_by="tomi").id
        r.cast_vote(pid, "human2", Position.FOR)
        r.cast_vote(pid, "AI", Position.FOR)
        self.assertEqual(r.tally(pid)["votes_cast"], 2)

        r.leave("AI")
        after = r.tally(pid)
        self.assertEqual(after["votes_cast"], 1,
                         "departure must still exclude the departed member's vote")
        self.assertEqual(after["counts"]["for"], 1)

    def test_replay_keeps_a_cast_vote_after_a_standing_change(self) -> None:
        """The tally must survive replay, or it is only true in memory."""
        from multitude.store import RhizomeStore

        r = _rhizome()
        r.join("AI", NodeKind.TECHNOLOGICAL, voting=True)
        pid = r.open_proposal("p", "body", opened_by="tomi").id
        r.cast_vote(pid, "human2", Position.FOR)
        r.cast_vote(pid, "AI", Position.FOR)
        MultitudeService(r).demote("AI", actor="tomi")

        replayed = Rhizome(RhizomeStore(r.store.path))
        t = replayed.tally(pid)
        self.assertEqual(t["votes_cast"], 2)
        self.assertEqual(t["counts"]["for"], 2)


class RuntimeParityTests(unittest.TestCase):
    """The same membership must behave the same on every runtime (#66 item 4)."""

    def test_a_promotion_survives_ordinary_work_on_every_runtime(self) -> None:
        for runtime in RUNTIMES:
            with self.subTest(runtime=runtime):
                r = _rhizome()
                adapter = _join_via(runtime, r)
                self.assertFalse(
                    r.member_by_name("AI").voting,
                    f"{runtime}: a runtime-joined member did not start voice-only",
                )
                MultitudeService(r).promote("AI", actor="tomi")
                self.assertTrue(r.member_by_name("AI").voting)

                _ordinary_work(runtime, adapter)

                self.assertTrue(
                    r.member_by_name("AI").voting,
                    f"{runtime}: ordinary work revoked the rhizome's promotion",
                )

    def test_a_promotion_survives_replay_on_every_runtime(self) -> None:
        from multitude.store import RhizomeStore

        for runtime in RUNTIMES:
            with self.subTest(runtime=runtime):
                r = _rhizome()
                adapter = _join_via(runtime, r)
                MultitudeService(r).promote("AI", actor="tomi")
                _ordinary_work(runtime, adapter)
                replayed = Rhizome(RhizomeStore(r.store.path))
                self.assertTrue(replayed.member_by_name("AI").voting)

    def test_every_runtime_records_who_changed_standing(self) -> None:
        """Attribution must be present on every path, not just the ones we tested."""
        for runtime in RUNTIMES:
            with self.subTest(runtime=runtime):
                r = _rhizome()
                adapter = _join_via(runtime, r)
                MultitudeService(r).promote("AI", actor="tomi")
                _ordinary_work(runtime, adapter)
                changes = [ev.payload for ev in r.store.replay()
                           if ev.type == "member_updated"
                           and ev.payload.get("standing_changed")]
                self.assertTrue(
                    changes, f"{runtime}: the standing change is unattributable"
                )
                for change in changes:
                    self.assertTrue(change.get("changed_by"))
                    self.assertTrue(change.get("reason"))
                    self.assertTrue(change.get("standing_changed"))

    def test_no_runtime_revokes_standing_it_did_not_grant(self) -> None:
        """The generalised defect: a runtime recomputing a membership property.

        #66 warns this shape would "corrupt any future member-level right built
        on that pattern", so the property is asserted for every runtime rather
        than fixed once per adapter.
        """
        for runtime in RUNTIMES:
            with self.subTest(runtime=runtime):
                r = _rhizome()
                adapter = _join_via(runtime, r)
                MultitudeService(r).promote("AI", actor="tomi")
                for _ in range(3):
                    _ordinary_work(runtime, adapter)
                self.assertTrue(
                    r.member_by_name("AI").voting,
                    f"{runtime}: repeated ordinary work revoked standing",
                )


if __name__ == "__main__":
    unittest.main()
