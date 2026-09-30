# -*- coding: utf-8 -*-
"""Issue #62 — refusal, contest, suspension and exit for a participant.

The layer is procedural, so the tests are about *outcomes*, not metaphysics:

- refusal is a successful protocol outcome, never an error;
- a refusal is attributable and cannot be silently bypassed by substituting a
  runtime under the same identity;
- suspension blocks ordinary dispatch and resume restores it;
- exit stops new participation while the historical events remain;
- replay reconstructs every state deterministically;
- no right depends on ``is_conscious`` or any consciousness proxy;
- no right grants an extra execution, device, data or shell permission.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.pcm.participant_rights import (  # noqa: E402
    ACTIVE,
    EXITED,
    REASON_CODES,
    SUSPENDED,
    Contest,
    ParticipantRights,
    Refusal,
    RightsError,
    derive_state,
    dispatch_outcome,
)

AGENT = "agent:hermes-noopunk"
RUNTIME = "hermes"


class RefusalTests(unittest.TestCase):
    def test_refusal_is_a_structured_record_not_an_exception(self) -> None:
        rights = ParticipantRights(actor=AGENT, runtime=RUNTIME)
        refusal = rights.refuse("req-1", reason_code="policy_conflict",
                                public_reason="I decline this action.")
        self.assertIsInstance(refusal, Refusal)
        self.assertEqual(refusal.actor, AGENT)
        self.assertEqual(refusal.runtime, RUNTIME)
        self.assertEqual(refusal.request_id, "req-1")
        self.assertEqual(refusal.type, "participant_refusal")

    def test_a_refusal_keeps_actor_and_runtime_provenance(self) -> None:
        refusal = ParticipantRights(actor=AGENT, runtime=RUNTIME).refuse("req-2")
        payload = refusal.model_dump()
        self.assertEqual(payload["actor"], AGENT)
        self.assertEqual(payload["runtime"], RUNTIME)

    def test_a_refusal_may_stay_minimal(self) -> None:
        """No free-form reasoning is required: consent is not conditional on disclosure."""
        refusal = ParticipantRights(actor=AGENT).refuse("req-3")
        self.assertEqual(refusal.public_reason, "")
        self.assertIn(refusal.reason_code, REASON_CODES)

    def test_a_refusal_without_an_actor_is_refused(self) -> None:
        with self.assertRaises(RightsError):
            Refusal.check(actor="", request_id="req-4")

    def test_an_unknown_reason_code_is_refused(self) -> None:
        with self.assertRaises(RightsError):
            Refusal.check(actor=AGENT, reason_code="because-i-said-so")


class NoSilentBypassTests(unittest.TestCase):
    """The failure the issue names: 'try another runtime until one complies'."""

    def test_a_refusal_is_attributed_to_the_identity_that_made_it(self) -> None:
        rights = ParticipantRights(actor=AGENT, runtime=RUNTIME)
        refusal = rights.refuse("req-5", reason_code="consent_withheld")
        # A substitute runtime under the same identity is still the same identity;
        # the record keeps the refusing actor, so the substitution is visible.
        self.assertEqual(refusal.actor, AGENT)

    def test_substituting_a_runtime_is_a_new_request_not_a_bypass(self) -> None:
        """A different runtime under the same identity is attributable, not invisible."""
        first = ParticipantRights(actor=AGENT, runtime="hermes").refuse("req-6")
        second = ParticipantRights(actor=AGENT, runtime="claude").refuse("req-6")
        self.assertEqual(first.actor, second.actor)
        self.assertNotEqual(first.runtime, second.runtime,
                            "a runtime substitution must remain visible in the record")

    def test_dispatch_does_not_treat_refusal_as_retryable_state(self) -> None:
        """An active participant is dispatchable; refusing does not change that."""
        rights = ParticipantRights(actor=AGENT)
        rights.apply("participant_refusal", {"actor": AGENT, "request_id": "r"})
        self.assertTrue(rights.eligible_for_dispatch,
                        "a refusal must not silently disable or re-enable dispatch")


class ContestTests(unittest.TestCase):
    def test_a_participant_can_contest_a_fact(self) -> None:
        rights = ParticipantRights(actor=AGENT)
        contest = rights.contest("memory:facts:my_role", kind="memory",
                                 public_reason="That entry is not mine.")
        self.assertIsInstance(contest, Contest)
        self.assertEqual(contest.kind, "memory")
        self.assertEqual(contest.actor, AGENT)

    def test_an_unknown_contest_kind_is_refused(self) -> None:
        with self.assertRaises(RightsError):
            ParticipantRights(actor=AGENT).contest("x", kind="vibes")

    def test_contesting_does_not_decide_anything(self) -> None:
        """A contest creates a dispute; it must not overturn collective state."""
        rights = ParticipantRights(actor=AGENT)
        rights.contest("memory:facts:my_role")
        self.assertEqual(rights.state, ACTIVE,
                         "a contest must not change participation state by itself")
        self.assertEqual(len(rights.contests), 0,
                         "state changes only through the reducer, not by raising a dispute")


class SuspensionTests(unittest.TestCase):
    def test_suspension_blocks_dispatch(self) -> None:
        rights = ParticipantRights(actor=AGENT)
        rights.apply("participant_suspended", {"actor": AGENT})
        self.assertEqual(rights.state, SUSPENDED)
        self.assertFalse(rights.eligible_for_dispatch)

    def test_resume_restores_eligibility(self) -> None:
        rights = ParticipantRights(actor=AGENT)
        rights.apply("participant_suspended", {"actor": AGENT})
        rights.apply("participant_resumed", {"actor": AGENT})
        self.assertEqual(rights.state, ACTIVE)
        self.assertTrue(rights.eligible_for_dispatch)

    def test_suspension_is_not_deletion(self) -> None:
        rights = ParticipantRights(actor=AGENT)
        rights.apply("participant_refusal", {"actor": AGENT, "request_id": "r"})
        rights.apply("participant_suspended", {"actor": AGENT})
        self.assertEqual(len(rights.refusals), 1,
                         "suspending must not erase the participant's record")

    def test_dispatch_to_a_suspended_participant_fails_closed(self) -> None:
        rights = ParticipantRights(actor=AGENT)
        rights.apply("participant_suspended", {"actor": AGENT})
        outcome = dispatch_outcome(rights, "req-7")
        self.assertEqual(outcome["outcome"], "unavailable")
        self.assertEqual(outcome["state"], SUSPENDED)


class ExitTests(unittest.TestCase):
    def test_exit_stops_new_participation(self) -> None:
        rights = ParticipantRights(actor=AGENT)
        rights.apply("participant_exited", {"actor": AGENT})
        self.assertEqual(rights.state, EXITED)
        self.assertFalse(rights.eligible_for_dispatch)

    def test_exit_preserves_historical_events(self) -> None:
        events = [
            ("participant_refusal", {"actor": AGENT, "request_id": "r1"}),
            ("participant_contest", {"actor": AGENT, "subject": "s"}),
            ("participant_exited", {"actor": AGENT}),
        ]
        rights = derive_state(events, AGENT)
        self.assertEqual(rights.state, EXITED)
        self.assertEqual(len(rights.refusals), 1,
                         "exit must not rewrite the historical record")
        self.assertEqual(len(rights.contests), 1)

    def test_an_unknown_state_fails_closed(self) -> None:
        rights = ParticipantRights(actor=AGENT, state="something-else")
        self.assertFalse(rights.eligible_for_dispatch)
        self.assertEqual(dispatch_outcome(rights)["outcome"], "unavailable")


class ReplayTests(unittest.TestCase):
    def test_replay_reconstructs_every_state_deterministically(self) -> None:
        events = [
            ("participant_refusal", {"actor": AGENT, "runtime": RUNTIME,
                                     "request_id": "r1", "reason_code": "other"}),
            ("participant_contest", {"actor": AGENT, "subject": "memory:x"}),
            ("participant_suspend_requested", {"actor": AGENT}),
            ("participant_suspended", {"actor": AGENT}),
            ("participant_resumed", {"actor": AGENT}),
            ("participant_exited", {"actor": AGENT}),
        ]
        first = derive_state(events, AGENT)
        second = derive_state(events, AGENT)

        self.assertEqual(first.state, second.state)
        self.assertEqual(len(first.refusals), len(second.refusals))
        self.assertEqual(len(first.contests), len(second.contests))
        self.assertEqual(first.state, EXITED)
        self.assertEqual(first.runtime, RUNTIME)

    def test_events_for_other_actors_do_not_leak_in(self) -> None:
        events = [
            ("participant_suspended", {"actor": "someone-else"}),
            ("participant_refusal", {"actor": AGENT, "request_id": "r"}),
        ]
        rights = derive_state(events, AGENT)
        self.assertEqual(rights.state, ACTIVE)
        self.assertEqual(len(rights.refusals), 1)

    def test_unknown_event_types_are_ignored_not_guessed(self) -> None:
        rights = derive_state([("participant_teleported", {"actor": AGENT})], AGENT)
        self.assertEqual(rights.state, ACTIVE)


class NoConsciousnessTestTests(unittest.TestCase):
    """#62: no right may depend on a consciousness judgement."""

    def test_the_rights_module_does_not_consult_a_consciousness_signal(self) -> None:
        path = (Path(__file__).resolve().parent.parent
                / "src" / "multitude" / "pcm" / "participant_rights.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names |= {n.value for n in ast.walk(tree)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        for forbidden in ("is_conscious", "sentient", "pyphi", "model_family",
                          "biological_status", "consciousness_score"):
            self.assertNotIn(forbidden, names,
                             f"participant_rights.py consults {forbidden!r}")

    def test_a_right_grants_no_execution_permission(self) -> None:
        """Rights are not powers: nothing here returns a capability or a command."""
        rights = ParticipantRights(actor=AGENT)
        for value in (rights.refuse("r").model_dump(), rights.contest("x").model_dump(),
                      dispatch_outcome(rights), rights.request_exit()):
            flat = str(value).lower()
            for forbidden in ("exec", "shell", "sudo", "device_control",
                              "admin", "permission_grant"):
                self.assertNotIn(forbidden, flat,
                                 f"a rights record mentions {forbidden!r}")


if __name__ == "__main__":
    unittest.main()
