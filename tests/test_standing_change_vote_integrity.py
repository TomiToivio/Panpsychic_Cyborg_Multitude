# -*- coding: utf-8 -*-
"""A vote cast while eligible is not erased by a later standing change (#72).

`close_proposal()` and `tally()` used to filter votes through *current*
eligibility, so demoting a member after they voted removed their vote from the
tally and their dissent from the decision record — and could flip the outcome
(rejected -> adopted). These tests pin the corrected rule and the departure
behaviour that must NOT change.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude.models import NodeKind, Outcome, Position, Rule  # noqa: E402
from multitude.rhizome import Rhizome, RhizomeError  # noqa: E402
from multitude.service import MultitudeService  # noqa: E402


class StandingChangeVoteIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "tribes")
        os.makedirs(self.root)
        self.rhizome = Rhizome.found(
            self.root, "Test Rhizome", charter="Honesty, autonomy.", founder_name="Alice"
        )
        self.rhizome.join("Ai", NodeKind.TECHNOLOGICAL, voting=True)
        self.rhizome.join("Bob", NodeKind.BIOLOGICAL, voting=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _blocked_proposal(self, rule=Rule.CONSENSUS, quorum=1):
        p = self.rhizome.open_proposal("Adopt X", "Text.", opened_by="Alice", rule=rule, quorum=quorum)
        self.rhizome.cast_vote(p.id, "Alice", Position.FOR)
        self.rhizome.cast_vote(p.id, "Bob", Position.FOR)
        self.rhizome.cast_vote(p.id, "Ai", Position.BLOCK, reason="X violates participant consent.")
        return p

    def test_demote_does_not_erase_a_cast_vote_from_the_tally(self):
        p = self._blocked_proposal()
        MultitudeService(self.rhizome).demote("Ai", actor="Alice")
        d = self.rhizome.close_proposal(p.id, closed_by="Alice")
        self.assertEqual(d.tally["block"], 1)
        self.assertEqual(d.votes_cast, 3)

    def test_demote_does_not_erase_a_cast_dissent_from_the_decision(self):
        p = self._blocked_proposal()
        MultitudeService(self.rhizome).demote("Ai", actor="Alice")
        d = self.rhizome.close_proposal(p.id, closed_by="Alice")
        self.assertEqual(len(d.dissent), 1)
        self.assertEqual(d.dissent[0]["member"], "Ai")
        self.assertEqual(d.dissent[0]["reason"], "X violates participant consent.")
        self.assertEqual(d.dissent[0]["position"], "block")

    def test_demote_after_voting_does_not_flip_the_outcome(self):
        p = self._blocked_proposal()
        MultitudeService(self.rhizome).demote("Ai", actor="Alice")
        d = self.rhizome.close_proposal(p.id, closed_by="Alice")
        self.assertEqual(d.outcome, Outcome.REJECTED)

    def test_outcome_matches_a_control_run_without_the_demotion(self):
        """The demotion must make no difference at all to the decision."""
        control = self._blocked_proposal()
        control_decision = self.rhizome.close_proposal(control.id, closed_by="Alice")

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        other = Rhizome.found(
            os.path.join(tmp.name, "t"), "Test Rhizome", charter="Honesty, autonomy.", founder_name="Alice"
        )
        other.join("Ai", NodeKind.TECHNOLOGICAL, voting=True)
        other.join("Bob", NodeKind.BIOLOGICAL, voting=True)
        p = other.open_proposal("Adopt X", "Text.", opened_by="Alice", rule=Rule.CONSENSUS, quorum=1)
        other.cast_vote(p.id, "Alice", Position.FOR)
        other.cast_vote(p.id, "Bob", Position.FOR)
        other.cast_vote(p.id, "Ai", Position.BLOCK, reason="X violates participant consent.")
        MultitudeService(other).demote("Ai", actor="Alice")
        case_decision = other.close_proposal(p.id, closed_by="Alice")

        self.assertEqual(case_decision.tally, control_decision.tally)
        self.assertEqual(case_decision.dissent, control_decision.dissent)
        self.assertEqual(case_decision.outcome, control_decision.outcome)
        self.assertEqual(case_decision.votes_cast, control_decision.votes_cast)

    def test_unanimity_denominator_is_frozen_at_open(self):
        p = self.rhizome.open_proposal(
            "Rename", "Rename rhizome.", opened_by="Alice", rule=Rule.UNANIMITY, quorum=2
        )
        self.rhizome.cast_vote(p.id, "Alice", Position.FOR)
        self.rhizome.cast_vote(p.id, "Bob", Position.FOR)
        # A membership change after the votes must not shrink the denominator.
        MultitudeService(self.rhizome).demote("Ai", actor="Alice")
        d = self.rhizome.close_proposal(p.id, closed_by="Alice")
        self.assertEqual(d.outcome, Outcome.REJECTED)

    def test_replay_reconstructs_the_same_tally_dissent_and_outcome(self):
        p = self._blocked_proposal()
        MultitudeService(self.rhizome).demote("Ai", actor="Alice")
        d = self.rhizome.close_proposal(p.id, closed_by="Alice")

        replayed = Rhizome(self.rhizome.store)
        replayed_decision = [x for x in replayed.decisions if x.proposal_id == p.id][0]
        self.assertEqual(replayed_decision.tally, d.tally)
        self.assertEqual(replayed_decision.dissent, d.dissent)
        self.assertEqual(replayed_decision.outcome, d.outcome)
        self.assertEqual(replayed.proposals[p.id].electorate, p.electorate)

    def test_departed_member_is_still_not_counted(self):
        """Departure stays an exclusion — asserted here so the rule is explicit."""
        self.rhizome.join("Visitor", NodeKind.BIOLOGICAL)
        p = self.rhizome.open_proposal("Z", "Text.", opened_by="Alice", quorum=1)
        self.rhizome.cast_vote(p.id, "Visitor", Position.FOR)
        self.rhizome.leave("Visitor")
        t = self.rhizome.tally(p.id)
        self.assertEqual(t["votes_cast"], 0)
        self.assertFalse(t["quorum_met"])

    def test_departed_dissenter_is_still_named_in_the_decision(self):
        p = self.rhizome.open_proposal("Q", "Text.", opened_by="Alice", quorum=1)
        self.rhizome.cast_vote(p.id, "Alice", Position.FOR)
        self.rhizome.cast_vote(p.id, "Ai", Position.BLOCK, reason="consent")
        self.rhizome.leave("Ai")
        d = self.rhizome.close_proposal(p.id, closed_by="Alice")
        self.assertEqual(len(d.dissent), 1)
        self.assertEqual(d.dissent[0]["member"], "Ai")

    def test_non_voting_member_still_cannot_cast_a_vote(self):
        self.rhizome.join("Voice", NodeKind.TECHNOLOGICAL, voting=False)
        p = self.rhizome.open_proposal("V", "Text.", opened_by="Alice", quorum=1)
        with self.assertRaises(RhizomeError):
            self.rhizome.cast_vote(p.id, "Voice", Position.FOR)


if __name__ == "__main__":
    unittest.main()
