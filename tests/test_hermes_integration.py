# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude import goals  # noqa: E402
from multitude.integrations.hermes import (  # noqa: E402
    HermesAgent,
    HermesAgentUnavailable,
    HermesPermissionError,
    MultitudeHermesAdapter,
)
from multitude.models import NodeKind, Position  # noqa: E402
from multitude.store import RhizomeStore  # noqa: E402
from multitude.rhizome import Rhizome  # noqa: E402


class HermesIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "tribes")
        os.makedirs(self.root)
        self.rhizome = Rhizome.found(self.root, "Hermes Rhizome", "Keep memory honest.", "Alice")
        goals.open_goal(
            self.rhizome, "Find customers", "Land one new client.",
            category="business", opened_by="Alice",
        )
        self.rhizome.remember("Launch note", "Call the first customer.", author="Alice")
        self.adapter = MultitudeHermesAdapter(self.rhizome, agent_name="Panpsychic Cyborg Multitude", model="glm-5.3-flash:cloud")
        self.agent = HermesAgent(self.adapter)

    def tearDown(self):
        self.tmp.cleanup()

    def test_technological_agent_is_normal_member_with_six_layers(self):
        member = self.adapter.get_agent()
        self.assertEqual(member.kind, NodeKind.TECHNOLOGICAL)
        self.assertEqual(member.profile.social.tribe_role, "knowledge_steward")
        self.assertEqual(member.profile.cybernetic.interface_mode, "text")
        self.assertIsNone(member.profile.psychic.is_conscious)
        self.assertEqual(member.profile.biological.species, "not_applicable")

    def test_status_and_memory_are_readable(self):
        status = self.adapter.get_status()
        self.assertEqual(status["tribe"], "Hermes Rhizome")
        hits = self.adapter.search_memory("customer")
        self.assertTrue(any(h.title == "Launch note" for h in hits))

    def test_individual_memory_is_separate_from_collective_memory(self):
        self.agent.memory.remember("favorite_hobby", "science fiction")
        stored = json.loads(self.agent.memory.path.read_text(encoding="utf-8"))
        self.assertEqual(stored["facts"]["favorite_hobby"], "science fiction")
        self.assertFalse(any("favorite_hobby" in e.text for e in self.rhizome.memory.values()))
        self.assertFalse(any(ev.type == "memory_added" and "favorite_hobby" in json.dumps(ev.payload) for ev in self.rhizome.store.replay()))

    def test_draft_does_not_mutate_state(self):
        before_events = len(self.rhizome.store.replay())
        draft = self.agent.draft_proposal("test collective memory tomorrow")
        after_events = len(self.rhizome.store.replay())
        self.assertIn("AI-authored by Panpsychic Cyborg Multitude", draft["text"])
        self.assertEqual(before_events, after_events)

    def test_create_proposal_adds_normal_event_with_technological_authorship(self):
        p = self.agent.create_proposal("test collective memory tomorrow")
        self.assertEqual(p.opened_by, "Panpsychic Cyborg Multitude")
        replayed = Rhizome(RhizomeStore(self.rhizome.store.path))
        event = [ev for ev in replayed.store.replay() if ev.type == "proposal_opened"][-1]
        self.assertEqual(event.actor, "Panpsychic Cyborg Multitude")
        self.assertEqual(replayed.member_by_name("Panpsychic Cyborg Multitude").kind, NodeKind.TECHNOLOGICAL)

    def test_ensure_agent_persists_runtime_metadata_and_non_voting_state(self):
        self.rhizome.join(
            "Panpsychic Cyborg Multitude",
            NodeKind.TECHNOLOGICAL,
            voting=True,
            model="glm-5.3-flash:cloud",
        )
        adapter = MultitudeHermesAdapter(
            self.rhizome,
            agent_name="Panpsychic Cyborg Multitude",
            model="glm-5.3-flash:cloud",
        )
        member = adapter.ensure_agent()
        self.assertFalse(member.voting)
        self.assertEqual(member.meta["runtime"], "hermes-agent")
        self.assertIn("knowledge_steward", member.meta["roles"])
        replayed = Rhizome(RhizomeStore(self.rhizome.store.path))
        replayed_member = replayed.member_by_name("Panpsychic Cyborg Multitude")
        self.assertFalse(replayed_member.voting)
        self.assertEqual(replayed_member.meta["runtime"], "hermes-agent")
        self.assertIn("knowledge_steward", replayed_member.meta["roles"])

    def test_default_agent_name_matches_repo_identity(self):
        default_adapter = MultitudeHermesAdapter(self.rhizome, model="glm-5.3-flash:cloud")
        member = default_adapter.ensure_agent()
        self.assertEqual(member.name, "Panpsychic Cyborg Multitude")

    def test_suggest_prefix_does_not_force_adopt_title(self):
        draft = self.agent.draft_proposal("suggest that we create a memory review ritual")
        self.assertEqual(draft["title"], "create a memory review ritual")

    def test_unauthorized_voting_is_rejected(self):
        p = self.rhizome.open_proposal("Test", "Proposal.", opened_by="Alice")
        with self.assertRaises(HermesPermissionError):
            self.adapter.cast_vote(p.id, Position.FOR)

    def test_unauthorized_governance_change_is_rejected(self):
        with self.assertRaises(HermesPermissionError):
            self.adapter.modify_governance()

    def test_question_routing_is_grounded_in_state(self):
        self.assertIn("Panpsychic Cyborg Multitude", self.agent.ask("Who are the members of the rhizome?"))
        self.assertIn("Find customers", self.agent.ask("What are our current goals?"))
        self.assertIn("Launch note", self.agent.ask("What happened in the rhizome during the last week?"))

    def test_unresolved_decisions_preserve_structure(self):
        p = self.rhizome.open_proposal("Ritual", "Meet every week.", opened_by="Alice")
        out = self.agent.ask("What unresolved decisions do we have?")
        self.assertIn(p.id, out)
        self.assertIn("rule=", out)

    def test_live_counsel_failure_is_clean(self):
        class DeadClient:
            model = "dead-model"

            def chat(self, _system, _user):
                return None

        agent = HermesAgent(self.adapter, client=DeadClient())
        with self.assertRaises(HermesAgentUnavailable):
            agent.counsel("What should we do next?")
        self.assertEqual(self.rhizome.messages[-1].kind, "system")
        self.assertIn("silent", self.rhizome.messages[-1].text)


if __name__ == "__main__":
    unittest.main()
