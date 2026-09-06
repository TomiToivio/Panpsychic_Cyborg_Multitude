# -*- coding: utf-8 -*-
"""Tests for the ValueFlows domain (issue #11).

Covers: event-sourced VF entities, the commitment/event distinction,
agent resolution (member + assemblage provenance), JSON-LD projection
to the VF namespace, and replay persistence.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude import economy_vf as vf  # noqa: E402
from multitude.models import NodeKind  # noqa: E402
from multitude.rhizome import Rhizome, RhizomeError  # noqa: E402


class VFDomainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rhizome = Rhizome.found(
            os.path.join(self.tmp.name, "tribes"),
            "VF Rhizome",
            charter="the Common is produced, not found",
            founder_name="Alice",
        )
        self.rhizome.join("PCM node", NodeKind.TECHNOLOGICAL)

    def tearDown(self):
        self.tmp.cleanup()

    def _replay(self):
        return Rhizome(self.rhizome.store)

    # ------------------------------------------------------------- creation
    def test_intent_creation_and_replay(self):
        rec = self.rhizome.vf_create_intent(
            title="Need: GPU time for training", created_by="Alice", kind="need",
        )
        self.assertIn(rec.id, self.rhizome.vf_store["intents"])
        replayed = self._replay()
        self.assertIn(rec.id, replayed.vf_store["intents"])

    def test_resource_and_process_and_event_chain(self):
        resource = self.rhizome.vf_create_resource(
            name="Shared research corpus", created_by="Alice", quantity=1, unit="corpus",
        )
        commitment = self.rhizome.vf_create_commitment(
            title="Alice commits to annotate 100 documents",
            committed_by="Alice", owed_by="Alice",
        )
        process = self.rhizome.vf_create_process(
            name="Corpus annotation", created_by="Alice",
            input_resource_ids=[resource.id], commitment_ids=[commitment.id],
        )
        event = self.rhizome.vf_record_economic_event(
            action="work", recorded_by="Alice", provider="Alice",
            title="Annotated 100 documents", commitment_id=commitment.id,
            process_id=process.id, output_resource_ids=[resource.id],
            quantity=100, unit="documents",
        )
        store = self.rhizome.vf_store
        self.assertEqual(len(store["resources"]), 1)
        self.assertEqual(len(store["commitments"]), 1)
        self.assertEqual(len(store["processes"]), 1)
        self.assertEqual(len(store["economic_events"]), 1)
        self.assertEqual(event.action, "work")
        replayed = self._replay()
        self.assertEqual(len(replayed.vf_store["economic_events"]), 1)
        self.assertEqual(len(replayed.vf_store["processes"]), 1)

    def test_agreement_linking_commitments(self):
        c1 = self.rhizome.vf_create_commitment(
            title="Rhizome A offers research", committed_by="Alice", owed_by="Alice",
        )
        c2 = self.rhizome.vf_create_commitment(
            title="Rhizome B offers compute", committed_by="Alice", owed_by="Alice", owed_to="Alice",
        )
        agreement = self.rhizome.vf_create_agreement(
            title="Research-for-compute exchange",
            created_by="Alice", parties=["Alice", "PCM node"],
            commitment_ids=[c1.id, c2.id],
        )
        self.assertEqual(agreement.commitment_ids, [c1.id, c2.id])
        replayed = self._replay()
        self.assertIn(agreement.id, replayed.vf_store["agreements"])

    # ------------------------------------------------- commitment vs event
    def test_commitment_without_event_and_vice_versa(self):
        # a promise may exist with no event ever recorded against it
        self.rhizome.vf_create_commitment(
            title="Promised care work", committed_by="Alice", owed_by="Alice",
        )
        self.assertEqual(len(self.rhizome.vf_store["commitments"]), 1)
        self.assertEqual(len(self.rhizome.vf_store["economic_events"]), 0)
        # an event may occur with no commitment behind it (spontaneous contribution)
        self.rhizome.vf_record_economic_event(
            action="work", recorded_by="Alice", title="Unpromised fix",
        )
        self.assertEqual(len(self.rhizome.vf_store["economic_events"]), 1)
        # neither implies the other: both live in separate stores
        event = list(self.rhizome.vf_store["economic_events"].values())[0]
        self.assertIsNone(event.commitment_id)

    # ------------------------------------------------------- assemblage agent
    def test_assemblage_as_agent(self):
        assemblage = self.rhizome.define_assemblage(
            name="Alice+PCM", defined_by="Alice",
            components=[dict(kind="member", member="Alice",
                             role="human partner"),
                        dict(kind="external", label="the Internet",
                             role="network substrate")],
        )
        ref = vf._vf_agent_ref(self.rhizome, assemblage.name)
        self.assertEqual(ref["pcm_kind"], "assemblage")
        self.assertEqual(len(ref["components"]), 2)  # provenance preserved
        # the assemblage is registered under its id; the name resolves too
        self.assertIn(assemblage.id, self.rhizome.assemblages)
        by_name = vf._vf_agent_ref(self.rhizome, assemblage.name)
        self.assertEqual(by_name["@id"], ref["@id"])

    def test_unknown_agent_refused(self):
        with self.assertRaises(vf.VFError):
            vf._vf_agent_ref(self.rhizome, "Mallory")

    # ------------------------------------------------------- validation
    def test_event_requires_action(self):
        with self.assertRaises(RhizomeError):
            self.rhizome.vf_record_economic_event(action="  ", recorded_by="Alice")

    def test_bad_references_refused(self):
        with self.assertRaises(RhizomeError):
            self.rhizome.vf_record_economic_event(
                action="produce", recorded_by="Alice", commitment_id="vfcommitment-nope",
            )
        with self.assertRaises(RhizomeError):
            self.rhizome.vf_create_resource(name="", created_by="Alice")

    def test_agreement_needs_two_parties(self):
        with self.assertRaises(RhizomeError):
            self.rhizome.vf_create_agreement(
                title="Solo deal", created_by="Alice", parties=["Alice"],
            )

    # ------------------------------------------------------------- JSON-LD
    def test_jsonld_projection_uses_vf_namespace(self):
        intent = self.rhizome.vf_create_intent(
            title="Offer: mentoring", created_by="Alice", kind="offer",
        )
        doc = vf.to_jsonld(self.rhizome, "intent", intent.id)
        self.assertEqual(doc["@type"], "vf:Intent")
        self.assertEqual(doc["@context"]["vf"], vf.VF_NAMESPACE)
        self.assertIn("vf:name", doc)
        self.assertIn("vf:intentType", doc)
        # provenance rides in the pcm namespace, never erased
        self.assertEqual(doc["pcm:internalId"], intent.id)
        agent = doc["vf:creator"]
        self.assertEqual(agent["@id"], "urn:pcm:member:Alice")

    def test_jsonld_assemblage_provider(self):
        assemblage = self.rhizome.define_assemblage(
            name="Alice+PCM", defined_by="Alice",
            components=[dict(kind="member", member="Alice",
                             role="human partner")],
        )
        event = self.rhizome.vf_record_economic_event(
            action="work", recorded_by="Alice", title="Joint research",
        )
        doc = vf.to_jsonld(self.rhizome, "economic_event", event.id)
        self.assertEqual(doc["@type"], "vf:EconomicEvent")
        self.assertIn("vf:recordedIn", doc)

    def test_jsonld_unknown_record_refused(self):
        with self.assertRaises(vf.VFError):
            vf.to_jsonld(self.rhizome, "intent", "vfintent-nope")
        with self.assertRaises(vf.VFError):
            vf.to_jsonld(self.rhizome, "gossip", "x")

    # ------------------------------------------------- domain registration
    def test_domain_registered(self):
        from multitude import domains as registry
        registry.register_builtin_domains()
        registered = registry.registered_domains()
        self.assertIn("valueflows", registered)
        for event_type in vf.VF_EVENT_TYPES:
            self.assertIn(event_type, registered["valueflows"])


if __name__ == "__main__":
    unittest.main()