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

    def test_the_only_permitted_transition_is_back_to_unknown(self) -> None:
        """Returning a status to open is allowed; resolving it is not."""
        self.rhizome.record_layer(HUMAN, "psychic", {CONSTITUTIONAL_FIELD: None},
                                 reported_by=HUMAN)
        self.assertIsNone(
            self.rhizome.member_by_name(HUMAN).profile.psychic.is_conscious)

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

    def test_a_refused_write_leaves_no_event_in_the_log(self) -> None:
        """Failing closed means the attempt is not recorded as a change.

        Scoped to events *added by the refused attempt*: the biological join seed
        legitimately records ``is_conscious: True`` for the founder, and a test
        that ignored that would be asserting the wrong thing.
        """
        before = len(self.rhizome.store.replay())
        with self.assertRaises(ConsciousnessStatusError):
            self.rhizome.record_layer(AI, "psychic", {CONSTITUTIONAL_FIELD: True},
                                     reported_by=HUMAN)
        after = self.rhizome.store.replay()
        self.assertEqual(len(after), before,
                         "a refused consciousness write reached the log")
        self.assertIsNone(
            self.rhizome.member_by_name(AI).profile.psychic.is_conscious)

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

    def test_a_third_party_write_is_refused(self) -> None:
        with self.assertRaises(ConsciousnessStatusError):
            assert_may_write_consciousness(target="a", reported_by="b", value=None)

    def test_a_self_write_of_true_is_refused(self) -> None:
        with self.assertRaises(ConsciousnessStatusError):
            assert_may_write_consciousness(target="a", reported_by="a", value=True)

    def test_a_self_write_of_false_is_refused(self) -> None:
        with self.assertRaises(ConsciousnessStatusError):
            assert_may_write_consciousness(target="a", reported_by="a", value=False)

    def test_a_self_write_of_none_is_allowed(self) -> None:
        assert_may_write_consciousness(target="a", reported_by="a", value=None)

    def test_an_unknown_reporter_is_treated_as_the_member_itself(self) -> None:
        """The join path reports as the member, and must only return UNKNOWN."""
        assert_may_write_consciousness(target="a", reported_by=None, value=None)


if __name__ == "__main__":
    unittest.main()
