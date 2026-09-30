# -*- coding: utf-8 -*-
"""Deterministic tests for AI participant subjecthood and procedural rights."""
from __future__ import annotations

import tempfile
import unittest

from multitude.integrations.hermes.adapter import (
    HermesPermissionError,
    MultitudeHermesAdapter,
)
from multitude.models import NodeKind
from multitude.rhizome import Rhizome, RhizomeError
from multitude.service import MultitudeService, ServiceError
from multitude.store import RhizomeStore


class ParticipantRightsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.rhizome = Rhizome.found(self.tmp.name, "Rights Rhizome", "Due process.", "Alice")
        self.rhizome.join("agent:a", NodeKind.TECHNOLOGICAL, model="model-a", voting=False)
        self.service = MultitudeService(self.rhizome)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def replayed(self) -> Rhizome:
        return Rhizome(RhizomeStore(self.rhizome.store.path))

    def test_refusal_is_first_class_and_replays_with_provenance(self):
        record = self.service.record_refusal(
            "agent:a",
            request_id="req-1",
            runtime="hermes-agent",
            reason_code="policy_conflict",
            public_reason="I decline this action.",
            authority={"capability": "write_memory"},
        )
        self.assertEqual(record["actor"], "agent:a")
        replayed = self.replayed()
        self.assertEqual(replayed.participant_rights["refusals"][0]["request_id"], "req-1")
        self.assertEqual(replayed.participant_rights["refusals"][0]["runtime"], "hermes-agent")

    def test_contest_suspend_resume_and_dispatch_gate(self):
        contest = self.service.contest(
            "agent:a", about="memory:claim-7", public_reason="Misattributed."
        )
        self.assertEqual(contest["status"], "open")
        self.service.suspend_participation("agent:a", public_reason="Pause requested.")
        with self.assertRaises(ServiceError):
            self.service.assert_dispatchable("agent:a")
        self.service.resume_participation("agent:a")
        self.service.assert_dispatchable("agent:a")
        replayed = self.replayed()
        subject = self.rhizome.member_by_name("agent:a").id
        self.assertEqual(replayed.participant_rights["status"][subject], "active")
        self.assertEqual(len(replayed.participant_rights["contests"]), 1)

    def test_exit_preserves_history_and_prevents_identity_reuse(self):
        member_id = self.rhizome.member_by_name("agent:a").id
        self.service.exit_participation("agent:a", public_reason="Leaving.")
        self.assertIsNone(self.rhizome.member_by_name("agent:a"))
        self.assertIn(member_id, self.rhizome.former_members)
        with self.assertRaises(RhizomeError):
            self.rhizome.join("agent:a", NodeKind.TECHNOLOGICAL, model="model-b")
        replayed = self.replayed()
        self.assertEqual(replayed.participant_rights["status"][member_id], "exited")
        self.assertIn(member_id, replayed.former_members)

    def test_termination_is_not_consent_or_exit(self):
        member_id = self.rhizome.member_by_name("agent:a").id
        record = self.service.terminate_participant(
            "agent:a", terminated_by="Alice", public_reason="Operator shutdown."
        )
        self.assertFalse(record["consent"])
        replayed = self.replayed()
        self.assertEqual(replayed.participant_rights["status"][member_id], "terminated")
        self.assertEqual(replayed.participant_rights["terminations"][0]["actor"], "Alice")

    def test_succession_is_explicit_and_auditable(self):
        successor = self.rhizome.join(
            "agent:b", NodeKind.TECHNOLOGICAL, model="model-b", voting=False
        )
        with self.assertRaises(ServiceError):
            self.service.record_succession("agent:a", "agent:b", handover_proof="")
        record = self.service.record_succession(
            "agent:a",
            "agent:b",
            handover_proof="verified-envelope:handover-1",
            public_reason="Runtime migration.",
        )
        predecessor = self.rhizome.member_by_name("agent:a")
        self.assertEqual(record["predecessor"], predecessor.id)
        self.assertEqual(record["successor"], successor.id)
        replayed = self.replayed()
        self.assertEqual(replayed.participant_rights["status"][predecessor.id], "succeeded")
        self.assertEqual(replayed.participant_rights["successions"][0]["handover_proof"],
                         "verified-envelope:handover-1")

    def test_hermes_refusal_and_model_substitution_guard(self):
        adapter = MultitudeHermesAdapter(
            self.rhizome, agent_name="agent:a", model="model-a"
        )
        adapter.ensure_agent()
        refusal = adapter.refuse("req-2", public_reason="No.")
        self.assertEqual(refusal["runtime"], "hermes-agent")

        swapped = MultitudeHermesAdapter(
            self.rhizome, agent_name="agent:a", model="different-model"
        )
        with self.assertRaises(HermesPermissionError):
            swapped.ensure_agent()

    def test_rights_do_not_depend_on_consciousness_or_grant_authority(self):
        member = self.rhizome.member_by_name("agent:a")
        self.assertIsNone(member.profile.psychic.is_conscious)
        before_voting = member.voting
        self.service.record_refusal(
            "agent:a", request_id="req-3", runtime="test", public_reason="No."
        )
        after = self.rhizome.member_by_name("agent:a")
        self.assertEqual(after.voting, before_voting)
        self.assertIsNone(after.profile.psychic.is_conscious)


if __name__ == "__main__":
    unittest.main()
