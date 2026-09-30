# -*- coding: utf-8 -*-
"""Issue #65 — the ``is_conscious`` guard is constitutional and enforced.

``README.md`` states the standing rule twice:

    A node's `is_conscious` field stays `UNKNOWN` for every member, composite or
    not — no test, no benchmark, no self-report may flip it.

Before this guard that was prose. Any member could write any other member's
``psychic`` layer through the ordinary public API, including setting the field to
``True`` **or** ``False`` — so a machine could assert away a human's recorded
awareness, or grant or deny its own. The guard is deliberately symmetric: setting
the field to ``False`` is the same error as setting it to ``True``, because
removing a possible subject is not more permitted than asserting one.

The fourth case in the issue matters most: ``False`` is not merely "not UNKNOWN",
it is the direction that *removes* a possible subject, which is exactly what the
precautionary rule exists to prevent.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.layers import (  # noqa: E402
    CONSTITUTIONAL_FIELD,
    ConsciousnessStatusError,
    assert_may_write_consciousness,
)
from multitude.models import NodeKind  # noqa: E402
from multitude.rhizome import Rhizome  # noqa: E402

HUMAN = "Tomi"
AI = "Hermes"


class ConsciousnessGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self.tmp = Path(tempfile.mkdtemp(prefix="pcm-65-"))
        self.rhizome = Rhizome.found(str(self.tmp), "T", "c", HUMAN)
        self.rhizome.join(AI, NodeKind.TECHNOLOGICAL)

    def test_a_peer_cannot_declare_another_member_conscious(self) -> None:
        with self.assertRaises(ConsciousnessStatusError):
            self.rhizome.record_layer(AI, "psychic", {CONSTITUTIONAL_FIELD: True},
                                     reported_by=HUMAN)

    def test_a_peer_cannot_declare_another_member_not_conscious(self) -> None:
        """The direction that REMOVES a possible subject is equally forbidden."""
        with self.assertRaises(ConsciousnessStatusError):
            self.rhizome.record_layer(HUMAN, "psychic", {CONSTITUTIONAL_FIELD: False},
                                     reported_by=AI)

    def test_a_member_cannot_declare_itself_conscious(self) -> None:
        with self.assertRaises(ConsciousnessStatusError):
            self.rhizome.record_layer(AI, "psychic", {CONSTITUTIONAL_FIELD: True},
                                     reported_by=AI)

    def test_a_member_cannot_declare_itself_not_conscious(self) -> None:
        with self.assertRaises(ConsciousnessStatusError):
            self.rhizome.record_layer(AI, "psychic", {CONSTITUTIONAL_FIELD: False},
                                     reported_by=AI)

    def test_a_member_cannot_open_or_close_its_own_field_either(self) -> None:
        """Not even the member may change it, in either direction (#65 item 1).

        The issue is explicit: the field is set at join time by the seeding path
        and *never* rewritten by record_layer afterwards -- "not by a peer, not
        by the node itself". So a member returning its own True to UNKNOWN is
        refused exactly like a third party forcing it to False.
        """
        with self.assertRaises(ConsciousnessStatusError):
            self.rhizome.record_layer(HUMAN, "psychic", {CONSTITUTIONAL_FIELD: None},
                                     reported_by=HUMAN)
        self.assertTrue(
            self.rhizome.member_by_name(HUMAN).profile.psychic.is_conscious)

    def test_re_asserting_the_current_value_is_permitted(self) -> None:
        """Not a rewrite -- this is what keeps the guard surgical.

        The runtime adapters write a member's own psychic layer with the value
        the member already holds, and the join path seeds the documented default.
        If re-assertion were refused, the guard would break every runtime join
        and would have to special-case a caller list; permitting it means the
        rule is purely "this value does not change".
        """
        current = self.rhizome.member_by_name(AI).profile.psychic.is_conscious
        self.rhizome.record_layer(AI, "psychic", {CONSTITUTIONAL_FIELD: current},
                                 reported_by=AI)
        self.assertIsNone(
            self.rhizome.member_by_name(AI).profile.psychic.is_conscious)

    def test_the_guard_does_not_block_other_psychic_data(self) -> None:
        """Only the constitutional field is guarded, not the whole layer."""
        self.rhizome.record_layer(AI, "psychic", {"state": "attentive"},
                                 reported_by=HUMAN)
        self.assertEqual(
            self.rhizome.member_by_name(AI).profile.psychic.state, "attentive")

    def test_the_guard_does_not_block_other_layers(self) -> None:
        self.rhizome.record_layer(AI, "cybernetic", {"interface_mode": "text"},
                                 reported_by=HUMAN)
        self.assertEqual(
            self.rhizome.member_by_name(AI).profile.cybernetic.interface_mode, "text")

    def test_a_blocked_write_leaves_the_member_unchanged(self) -> None:
        """A refused write must not have partially applied."""
        before_ai = self.rhizome.member_by_name(AI).profile.psychic.is_conscious
        before_human = self.rhizome.member_by_name(HUMAN).profile.psychic.is_conscious
        for target, reporter, value in ((AI, HUMAN, True), (HUMAN, AI, False)):
            with self.assertRaises(ConsciousnessStatusError):
                self.rhizome.record_layer(target, "psychic",
                                         {CONSTITUTIONAL_FIELD: value},
                                         reported_by=reporter)
        self.assertEqual(
            self.rhizome.member_by_name(AI).profile.psychic.is_conscious, before_ai)
        self.assertEqual(
            self.rhizome.member_by_name(HUMAN).profile.psychic.is_conscious,
            before_human)

    def test_a_refused_write_is_traced_without_changing_state(self) -> None:
        """#65 item 4: the attempt must leave an auditable trace.

        The issue asks that a refused write "leave an auditable trace -- the
        attempt itself is evidence" (its right-to-contest tie-in), while the
        refusal must still change nothing. Both hold at once because the trace
        event records the ATTEMPT and is deliberately absent from the reducer:
        the log gains the attempt, the member state does not move.
        """
        before_state = self.rhizome.member_by_name(AI).profile.psychic.is_conscious
        before_events = len(self.rhizome.store.replay())

        with self.assertRaises(ConsciousnessStatusError):
            self.rhizome.record_layer(AI, "psychic", {CONSTITUTIONAL_FIELD: True},
                                     reported_by=HUMAN)

        after = self.rhizome.store.replay()
        self.assertEqual(len(after), before_events + 1,
                         "the refusal left no trace at all")
        trace = after[-1]
        self.assertEqual(trace.type, "layer_write_refused")
        self.assertEqual(trace.payload["member_name"], AI)
        self.assertEqual(trace.payload["requested_by"], HUMAN)
        self.assertEqual(trace.payload["attempted_value"], True)
        # ...and the state is untouched, which is the other half of the promise.
        self.assertEqual(
            self.rhizome.member_by_name(AI).profile.psychic.is_conscious,
            before_state)

    def test_the_trace_survives_replay(self) -> None:
        """The audit trail must be replayable, or it is not an audit trail."""
        from multitude.store import RhizomeStore

        with self.assertRaises(ConsciousnessStatusError):
            self.rhizome.record_layer(AI, "psychic", {CONSTITUTIONAL_FIELD: True},
                                     reported_by=HUMAN)
        replayed = Rhizome(RhizomeStore(self.rhizome.store.path))
        refused = [ev for ev in replayed.store.replay()
                   if ev.type == "layer_write_refused"]
        self.assertEqual(len(refused), 1)
        self.assertEqual(refused[0].payload["attempted_value"], True)
        # and the replay did not resurrect the refused value
        self.assertIsNone(replayed.member_by_name(AI).profile.psychic.is_conscious)

    def test_the_biological_seed_still_starts_awake(self) -> None:
        """The guard must not break the documented 'the ape starts awake' seed.

        That seed is applied by the join path, not by a third-party write, so it
        is out of the guard's scope. If this ever fails, the guard has started
        blocking the project's own documented default.
        """
        self.assertTrue(
            self.rhizome.member_by_name(HUMAN).profile.psychic.is_conscious)

    def test_a_technological_member_still_joins_unknown(self) -> None:
        self.assertIsNone(
            self.rhizome.member_by_name(AI).profile.psychic.is_conscious)


class GuardPrimitiveTests(unittest.TestCase):
    """The predicate itself, tested directly."""

    def test_a_third_party_change_is_refused(self) -> None:
        with self.assertRaises(ConsciousnessStatusError):
            assert_may_write_consciousness(target="a", reported_by="b",
                                          value=True, current=None)

    def test_a_self_change_to_true_is_refused(self) -> None:
        with self.assertRaises(ConsciousnessStatusError):
            assert_may_write_consciousness(target="a", reported_by="a",
                                          value=True, current=None)

    def test_a_self_change_to_false_is_refused(self) -> None:
        """The direction that removes a possible subject is equally forbidden."""
        with self.assertRaises(ConsciousnessStatusError):
            assert_may_write_consciousness(target="a", reported_by="a",
                                          value=False, current=True)

    def test_a_self_change_from_true_to_unknown_is_refused(self) -> None:
        with self.assertRaises(ConsciousnessStatusError):
            assert_may_write_consciousness(target="a", reported_by="a",
                                          value=None, current=True)

    def test_re_asserting_the_same_value_is_permitted(self) -> None:
        for value in (None, True, False):
            assert_may_write_consciousness(target="a", reported_by="a",
                                          value=value, current=value)


if __name__ == "__main__":
    unittest.main()
