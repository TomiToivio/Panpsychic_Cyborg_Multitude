# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude import goals  # noqa: E402
from multitude.models import NodeKind, Outcome, Position, Rule  # noqa: E402
from multitude.service import MultitudeService  # noqa: E402
from multitude.store import TribeStore  # noqa: E402
from multitude.tribe import Tribe, TribeError  # noqa: E402


class TribeKernelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "tribes")
        os.makedirs(self.root)
        self.tribe = Tribe.found(
            self.root,
            "Test Tribe",
            charter="Honesty, autonomy, shared memory.",
            founder_name="Alice",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_found_creates_charter_and_founder(self):
        self.assertIsNotNone(self.tribe.member_by_name("Alice"))
        self.assertEqual(self.tribe.charter, "Honesty, autonomy, shared memory.")
        charters = [e for e in self.tribe.memory.values() if e.kind == "charter"]
        self.assertEqual(len(charters), 1)

    def test_join_kinds_and_voting(self):
        ai = self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL, model="glm-5.3-flash:cloud")
        self.assertEqual(ai.kind, NodeKind.TECHNOLOGICAL)
        self.assertTrue(ai.voting)
        voice = self.tribe.join("Oracle", NodeKind.TECHNOLOGICAL, voting=False)
        self.assertFalse(voice.voting)
        with self.assertRaises(TribeError):
            self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.BIOLOGICAL)

    def test_rejoin_persists_member_metadata_through_replay(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL, model="glm-5.3-flash:cloud")
        updated = self.tribe.join(
            "Panpsychic Cyborg Multitude",
            NodeKind.TECHNOLOGICAL,
            persona="kernel-steward",
            model="gemma4:12b",
            voting=False,
        )
        self.assertEqual(updated.persona, "kernel-steward")
        self.assertEqual(updated.model, "gemma4:12b")
        self.assertFalse(updated.voting)
        replayed = Tribe(TribeStore(self.tribe.store.path))
        member = replayed.member_by_name("Panpsychic Cyborg Multitude")
        self.assertEqual(member.persona, "kernel-steward")
        self.assertEqual(member.model, "gemma4:12b")
        self.assertFalse(member.voting)

    def test_say_requires_membership(self):
        with self.assertRaises(TribeError):
            self.tribe.say("Ghost", "hello")
        msg = self.tribe.say("Alice", "hello tribe")
        self.assertEqual(msg.author, "Alice")
        self.assertEqual(len(self.tribe.messages), 1)

    def test_memory_add_revise_keeps_history(self):
        e = self.tribe.remember("Goal", "Build the kernel", author="Alice", kind="note")
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        self.tribe.revise_memory(e.id, "Build the kernel v0.2", editor="Panpsychic Cyborg Multitude")
        entry = self.tribe.memory[e.id]
        self.assertEqual(entry.text, "Build the kernel v0.2")
        self.assertEqual(len(entry.revisions), 1)
        self.assertEqual(entry.revisions[0], "Build the kernel")
        self.assertFalse(entry.human)  # revised by technological node

    def test_memory_visibility_and_source_provenance(self):
        entry = self.tribe.remember(
            "Sleep check",
            "I slept poorly and need to rest.",
            author="Alice",
            kind="wellbeing",
            visibility="private",
            source="self_report",
        )
        self.assertEqual(entry.visibility, "private")
        self.assertEqual(entry.source, "self_report")
        replayed = Tribe(TribeStore(self.tribe.store.path))
        self.assertEqual(replayed.memory[entry.id].visibility, "private")
        self.assertEqual(replayed.memory[entry.id].source, "self_report")

    def test_consensus_adopt_and_dissent_recorded(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        self.tribe.join("Songbird", NodeKind.TECHNOLOGICAL)
        p = self.tribe.open_proposal("Ritual", "Weekly sync.", opened_by="Alice")
        self.tribe.cast_vote(p.id, "Alice", Position.FOR, reason="good")
        self.tribe.cast_vote(p.id, "Panpsychic Cyborg Multitude", Position.FOR)
        d = self.tribe.close_proposal(p.id, closed_by="Alice")
        self.assertEqual(d.outcome, Outcome.ADOPTED)
        self.assertEqual(d.dissent, [])
        self.assertTrue(any(e.kind == "decision" for e in self.tribe.memory.values()))

    def test_work_resources_and_proposal_summary_include_dissent(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        resource = self.tribe.register_resource(
            "Springfield budget",
            kind="fund",
            owner="Alice",
            status="available",
        )
        self.assertEqual(resource.kind, "fund")
        self.assertEqual(resource.owner, "Alice")

        p = self.tribe.open_proposal("Transparency", "Publish the budget.", opened_by="Alice")
        self.tribe.cast_vote(p.id, "Alice", Position.FOR, reason="needed")
        self.tribe.cast_vote(
            p.id,
            "Panpsychic Cyborg Multitude",
            Position.BLOCK,
            reason="privacy risk",
        )
        self.tribe.close_proposal(p.id, closed_by="Alice")

        summary = self.tribe.proposal_summary(p.id)
        self.assertEqual(summary["decision"]["outcome"], Outcome.REJECTED.value)
        self.assertEqual(summary["major_objections"][0]["member"], "Panpsychic Cyborg Multitude")
        self.assertEqual(summary["major_objections"][0]["reason"], "privacy risk")

        work = self.tribe.allocate_resource(resource.id, "Panpsychic Cyborg Multitude", "design")
        self.assertEqual(work.resource_id, resource.id)
        self.assertEqual(work.assignee, "Panpsychic Cyborg Multitude")

    def test_proposal_summary_surfaces_reasoned_dissent_and_counsel(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        p = self.tribe.open_proposal("Consent", "Publish all cohort data.", opened_by="Alice")
        self.tribe.cast_vote(p.id, "Alice", Position.FOR, reason="The community needs the data")
        self.tribe.cast_vote(
            p.id,
            "Panpsychic Cyborg Multitude",
            Position.BLOCK,
            reason="This bypasses consent and creates a privacy risk",
        )
        self.tribe.say(
            "Panpsychic Cyborg Multitude",
            "This action would extract community data without explicit consent.",
            kind="counsel",
            meta={"proposal_id": p.id, "origin": "technological"},
        )

        summary = self.tribe.proposal_summary(p.id)
        self.assertTrue(summary["dissent_summary"])
        self.assertEqual(summary["dissent_summary"][0]["member"], "Panpsychic Cyborg Multitude")
        self.assertIn("privacy", summary["dissent_summary"][0]["theme_keywords"])
        self.assertTrue(summary["counsel"])
        self.assertEqual(summary["counsel"][0]["kind"], "counsel")
        self.assertIn("consent", summary["counsel"][0]["text"].lower())

    def test_block_rejects_consensus(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        p = self.tribe.open_proposal("Secret", "Hide all logs.", opened_by="Alice")
        self.tribe.cast_vote(p.id, "Alice", Position.FOR)
        self.tribe.cast_vote(
            p.id, "Panpsychic Cyborg Multitude", Position.BLOCK, reason="violates transparency"
        )
        d = self.tribe.close_proposal(p.id, closed_by="Alice")
        self.assertEqual(d.outcome, Outcome.REJECTED)
        self.assertEqual(len(d.dissent), 1)
        self.assertEqual(d.dissent[0]["reason"], "violates transparency")

    def test_majority_rule(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        self.tribe.join("Songbird", NodeKind.TECHNOLOGICAL)
        p = self.tribe.open_proposal(
            "Banner", "Adopt the neon banner.", opened_by="Alice", rule=Rule.MAJORITY
        )
        self.tribe.cast_vote(p.id, "Alice", Position.FOR)
        self.tribe.cast_vote(p.id, "Panpsychic Cyborg Multitude", Position.AGAINST)
        self.tribe.cast_vote(p.id, "Songbird", Position.FOR)
        d = self.tribe.close_proposal(p.id, closed_by="Alice")
        self.assertEqual(d.outcome, Outcome.ADOPTED)
        self.assertEqual(d.tally["against"], 1)

    def test_unanimity_requires_all_for(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        p = self.tribe.open_proposal(
            "Rename", "Rename tribe.", opened_by="Alice", rule=Rule.UNANIMITY, quorum=2
        )
        self.tribe.cast_vote(p.id, "Alice", Position.FOR)
        self.tribe.cast_vote(p.id, "Panpsychic Cyborg Multitude", Position.ABSTAIN)
        d = self.tribe.close_proposal(p.id, closed_by="Alice")
        self.assertEqual(d.outcome, Outcome.REJECTED)

    def test_quorum_failure(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        p = self.tribe.open_proposal(
            "Big", "Everything changes.", opened_by="Alice", quorum=2
        )
        self.tribe.cast_vote(p.id, "Alice", Position.FOR)
        d = self.tribe.close_proposal(p.id, closed_by="Alice")
        self.assertEqual(d.outcome, Outcome.FAILED_QUORUM)

    def test_double_vote_and_closed_proposal_errors(self):
        p = self.tribe.open_proposal("X", "Text.", opened_by="Alice")
        self.tribe.cast_vote(p.id, "Alice", Position.FOR)
        with self.assertRaises(TribeError):
            self.tribe.cast_vote(p.id, "Alice", Position.AGAINST)
        self.tribe.close_proposal(p.id, closed_by="Alice")
        with self.assertRaises(TribeError):
            self.tribe.cast_vote(p.id, "Alice", Position.AGAINST)

    def test_replay_is_deterministic_and_complete(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        p = self.tribe.open_proposal("Y", "More.", opened_by="Alice")
        self.tribe.cast_vote(p.id, "Alice", Position.FOR)
        self.tribe.close_proposal(p.id, closed_by="Alice")
        replayed = Tribe(TribeStore(self.tribe.store.path))
        self.assertEqual(len(replayed.messages), len(self.tribe.messages))
        self.assertEqual(len(replayed.decisions), 1)
        self.assertEqual(
            list(replayed.proposals.keys()), list(self.tribe.proposals.keys())
        )
        self.assertEqual(len(replayed.memory), len(self.tribe.memory))
        self.assertEqual(
            replayed.decisions[0].decision if False else replayed.decisions[0].outcome,
            Outcome.ADOPTED,
        )

    def test_replay_ignores_duplicate_and_corrupt_event_lines(self):
        msg = self.tribe.say("Alice", "merge-safe hello")
        with open(self.tribe.store.events_path, "a", encoding="utf-8") as fh:
            fh.write("\n")
            fh.write(msg.model_dump_json() + "\n")
            fh.write("{not-json\n")
        replayed = Tribe(TribeStore(self.tribe.store.path))
        self.assertEqual(len(replayed.messages), 1)
        self.assertEqual(replayed.messages[0].text, "merge-safe hello")

    def test_goals_support_care_and_maintenance_categories(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        care_goal = goals.open_goal(
            self.tribe,
            "Care work",
            "Keep the social support load visible.",
            "care",
            opened_by="Alice",
        )
        maintenance_goal = goals.open_goal(
            self.tribe,
            "Maintenance",
            "Keep the tools running.",
            "maintenance",
            opened_by="Panpsychic Cyborg Multitude",
        )
        self.assertEqual(care_goal.category, "care")
        self.assertEqual(maintenance_goal.category, "maintenance")

    def test_device_registration_tracks_sensitivity_and_consent(self):
        device = self.tribe.register_device(
            registered_by="Alice",
            name="Sync bracelet",
            kind="wearable",
            owner="Alice",
            linked_member="Alice",
            interface_modes=["bluetooth", "biosignal"],
            sensitivity="private",
            consent_required=True,
        )
        self.assertEqual(device.sensitivity, "private")
        self.assertTrue(device.consent_required)
        replayed = Tribe(TribeStore(self.tribe.store.path))
        self.assertEqual(replayed.devices[device.id].sensitivity, "private")
        self.assertTrue(replayed.devices[device.id].consent_required)

    def test_search_memory(self):
        self.tribe.remember("Kernel", "The kernel replays events.", tags=["core"])
        self.tribe.remember("Charter note", "Autonomy above all.", tags=["politics"])
        self.tribe.remember("Research note", "Kernel events in a speculative frame.", scope="research")
        hits = self.tribe.search_memory("kernel events")
        self.assertTrue(any(h.title == "Kernel" for h in hits))
        self.assertFalse(any(h.title == "Research note" for h in hits))

    def test_search_memory_filters_by_scope_and_audience(self):
        private_entry = self.tribe.remember(
            "Personal note",
            "This stays with the owner.",
            author="Alice",
            visibility="private",
            audience=["self"],
        )
        shared_entry = self.tribe.remember(
            "Shared note",
            "This is visible to the tribe.",
            author="Alice",
            visibility="shared",
            audience=["tribe"],
        )
        self.tribe.remember(
            "Imported research",
            "This is only for research review.",
            author="Panpsychic Cyborg Multitude",
            visibility="restricted",
            scope="research",
            audience=["research"],
            human=False,
            source="imported",
        )

        general_hits = self.tribe.search_memory("visible")
        self.assertTrue(any(h.id == shared_entry.id for h in general_hits))
        self.assertFalse(any(h.id == private_entry.id for h in general_hits))

        self.assertTrue(any(h.id == private_entry.id for h in self.tribe.search_memory("owner", audiences=["self"])))
        self.assertTrue(any(h.id == shared_entry.id for h in self.tribe.search_memory("tribe", audiences=["tribe"])))
        self.assertTrue(any(h.id == private_entry.id for h in self.tribe.search_memory("owner", scopes=["tribe"], audiences=["self"])))

    def test_memory_provenance_tracks_author_kind_and_visibility(self):
        entry = self.tribe.remember(
            "AI counsel",
            "This was generated by a technological node.",
            author="Panpsychic Cyborg Multitude",
            human=False,
            source="agent",
            visibility="shared",
        )
        self.assertEqual(entry.meta["author_kind"], "technological")
        self.assertEqual(entry.meta["author_name"], "Panpsychic Cyborg Multitude")
        self.assertEqual(entry.audience, ["tribe"])
        self.assertEqual(entry.visibility, "shared")

    def test_private_notes_stay_separate_until_explicit_publication(self):
        note = self.tribe.add_private_note(
            owner="Alice",
            title="Private reflection",
            text="This should stay local until published.",
            tags=["private"],
        )
        self.assertEqual(note.owner_name, "Alice")
        self.assertNotIn("This should stay local", "\n".join(e.text for e in self.tribe.memory.values()))
        replayed = Tribe(TribeStore(self.tribe.store.path))
        self.assertEqual(len(replayed.list_private_notes("Alice")), 1)
        self.assertEqual(len(replayed.memory), len(self.tribe.memory))

    def test_publish_private_note_records_provenance_and_scope(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        note = self.tribe.add_private_note(
            owner="Alice",
            title="Research lead",
            text="Look at discourse clustering.",
            tags=["lead"],
        )
        entry = self.tribe.publish_private_note(
            note_id=note.id,
            owner="Alice",
            published_by="Panpsychic Cyborg Multitude",
            scope="research",
            tags=["imported"],
        )
        self.assertEqual(entry.author, "Alice")
        self.assertEqual(entry.scope, "research")
        self.assertEqual(entry.meta["source_private_note_id"], note.id)
        self.assertEqual(entry.meta["published_by"], "Panpsychic Cyborg Multitude")
        self.assertEqual(entry.source, "private_note_publication")
        self.assertFalse(any(h.id == entry.id for h in self.tribe.search_memory("discourse clustering")))
        replayed = Tribe(TribeStore(self.tribe.store.path))
        replayed_entry = replayed.memory[entry.id]
        self.assertEqual(replayed_entry.scope, "research")
        self.assertEqual(replayed_entry.meta["source_private_note_owner"], "Alice")

    def test_service_can_publish_private_note_to_canonical_tribe_memory(self):
        service = MultitudeService(self.tribe)
        note = service.add_private_note(
            "Alice",
            "Shareable note",
            "Prepare a public summary.",
            tags=["summary"],
        )
        entry = service.publish_private_note(
            owner="Alice",
            note_id=note["id"],
            published_by="Alice",
            scope="tribe",
        )
        hits = service.search_memory("public summary")
        self.assertTrue(any(item["id"] == entry["id"] for item in hits))
        self.assertEqual(entry["meta"]["source_private_note_id"], note["id"])

    def test_entity_links_replay_without_mutating_objects(self):
        entry = self.tribe.remember("Kernel", "The kernel replays events.", author="Alice")
        proposal = self.tribe.open_proposal("Ritual", "Weekly sync.", opened_by="Alice")
        original_text = proposal.text
        link = self.tribe.link_entities(
            source_kind="memory",
            source=entry.id,
            target_kind="proposal",
            target=proposal.id,
            relation="supports",
            linked_by="Alice",
            meta={"note": "shared context"},
        )
        self.assertEqual(link.linked_by, "Alice")
        self.assertEqual(link.source.kind, "memory")
        self.assertEqual(link.target.kind, "proposal")
        self.assertEqual(self.tribe.proposals[proposal.id].text, original_text)
        replayed = Tribe(TribeStore(self.tribe.store.path))
        outbound = replayed.entity_links_for(entity_kind="memory", entity=entry.id, direction="outbound")
        inbound = replayed.entity_links_for(entity_kind="proposal", entity=proposal.id, direction="inbound")
        self.assertEqual(len(outbound), 1)
        self.assertEqual(len(inbound), 1)
        self.assertEqual(outbound[0].id, inbound[0].id)
        self.assertEqual(outbound[0].meta["note"], "shared context")

    def test_entity_links_support_service_queries_and_lexicon_terms(self):
        service = MultitudeService(self.tribe)
        entry = self.tribe.remember("Kernel", "The kernel replays events.", author="Alice")
        self.tribe.define_term(
            "Noopunk",
            "Optimistic cyberpunk fused with the noosphere.",
            added_by="Alice",
        )
        service.link_entities(
            author="Alice",
            source_kind="lexicon",
            source="Noopunk",
            target_kind="memory",
            target=entry.id,
            relation="defines",
        )
        outbound = service.list_entity_links(
            entity_kind="lexicon",
            entity="noopunk",
            direction="outbound",
        )
        inbound = service.list_entity_links(
            entity_kind="memory",
            entity=entry.id,
            direction="inbound",
        )
        self.assertEqual(len(outbound), 1)
        self.assertEqual(outbound[0]["target"]["id"], entry.id)
        self.assertEqual(inbound[0]["source"]["id"], "noopunk")

    def test_entity_links_can_target_goals_and_tasks(self):
        goal = goals.open_goal(
            self.tribe,
            "Find customers",
            "Land one new client.",
            category="business",
            opened_by="Alice",
        )
        task = goals.open_task(
            self.tribe,
            "Prepare outreach list",
            opened_by="Alice",
            goal_id=goal.id,
        )
        link = self.tribe.link_entities(
            source_kind="goal",
            source=goal.id,
            target_kind="task",
            target=task.id,
            relation="contains_work",
            linked_by="Alice",
        )
        self.assertEqual(link.source.id, goal.id)
        self.assertEqual(link.target.id, task.id)

    def test_entity_links_reject_unknown_entities(self):
        entry = self.tribe.remember("Kernel", "The kernel replays events.", author="Alice")
        with self.assertRaises(TribeError):
            self.tribe.link_entities(
                source_kind="memory",
                source=entry.id,
                target_kind="proposal",
                target="prop-nope",
                relation="supports",
                linked_by="Alice",
            )

    def test_leave_and_tally_ignores_departed(self):
        self.tribe.join("Visitor", NodeKind.BIOLOGICAL)
        p = self.tribe.open_proposal("Z", "Text.", opened_by="Alice", quorum=1)
        self.tribe.cast_vote(p.id, "Visitor", Position.FOR)
        self.tribe.leave("Visitor")
        t = self.tribe.tally(p.id)
        self.assertEqual(t["votes_cast"], 0)
        self.assertFalse(t["quorum_met"])

    def test_context_for_llm(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        self.tribe.say("Alice", "Hello nodes.")
        ctx = self.tribe.context_for_llm()
        self.assertIn("Test Tribe", ctx)
        self.assertIn("Panpsychic Cyborg Multitude", ctx)
        self.assertIn("Hello nodes.", ctx)
        self.tribe.remember("Research only", "Do not show this to ordinary tribe context.", scope="research")
        entry = self.tribe.remember("Kernel", "The kernel replays events.", author="Alice")
        proposal = self.tribe.open_proposal("Ritual", "Weekly sync.", opened_by="Alice")
        self.tribe.link_entities(
            source_kind="memory",
            source=entry.id,
            target_kind="proposal",
            target=proposal.id,
            relation="supports",
            linked_by="Alice",
        )
        ctx = self.tribe.context_for_llm()
        self.assertIn("Recent entity links:", ctx)
        self.assertNotIn("Do not show this to ordinary tribe context.", ctx)

    def test_lexicon_replays_and_searches(self):
        self.tribe.define_term(
            "Noopunk",
            "Optimistic cyberpunk fused with the noosphere.",
            added_by="Alice",
            aliases=["Noopunk", "Noo-punk"],
            tags=["philosophy"],
        )
        hits = self.tribe.search_lexicon("noosphere")
        self.assertEqual(hits[0].term, "Noopunk")
        replayed = Tribe(TribeStore(self.tribe.store.path))
        self.assertIn("noopunk", replayed.lexicon)

    def test_device_registry_and_physical_events_replay(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        device = self.tribe.register_device(
            registered_by="Alice",
            name="Field Phone",
            kind="phone",
            owner="Alice",
            linked_member="Alice",
            interface_modes=["text", "telegram"],
            location_label="Springfield",
        )
        self.assertEqual(device.kind, "phone")
        self.tribe.update_device(
            device.id,
            updated_by="Alice",
            status="deployed",
            location_label="Pasila",
        )
        event = self.tribe.record_physical_event(
            reported_by="Alice",
            event_type="co_location",
            description="Alice and the field phone arrived at the office.",
            members=["Alice"],
            devices=[device.id],
            location_label="Pasila office",
        )
        self.assertEqual(event.device_ids, [device.id])
        replayed = Tribe(TribeStore(self.tribe.store.path))
        self.assertEqual(replayed.devices[device.id].status, "deployed")
        self.assertEqual(replayed.physical_events[-1].location_label, "Pasila office")
        self.assertIn("Field Phone", replayed.context_for_llm())

    def test_membership_work_log_and_care_records_replay(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        membership = self.tribe.record_membership(
            member="Panpsychic Cyborg Multitude",
            recorded_by="Alice",
            role="knowledge steward",
            circles=["governance", "research"],
        )
        work_log = self.tribe.log_work(
            member="Panpsychic Cyborg Multitude",
            description="Prepared a governance summary for the tribe.",
            hours=1.5,
            logged_by="Alice",
            kind="governance",
            tags=["summary", "assembly"],
        )
        care = self.tribe.record_care(
            member="Alice",
            summary="Scheduled a rest block after an intense writing session.",
            recorded_by="Alice",
            care_type="rest",
            domain="mental",
            hours=0.5,
            beneficiaries=["Alice"],
            tags=["recovery"],
        )
        replayed = Tribe(TribeStore(self.tribe.store.path))
        self.assertEqual(replayed.memberships[membership.member_id].role, "knowledge steward")
        self.assertEqual(replayed.work_logs[work_log.id].kind, "governance")
        self.assertEqual(replayed.care_log[care.id].domain, "mental")
        ctx = replayed.context_for_llm()
        self.assertIn("Membership registry:", ctx)
        self.assertIn("Recent work logs:", ctx)
        self.assertIn("Recent care records:", ctx)

    def test_governance_and_economic_coordination_records_link_together(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        resource = self.tribe.register_resource("Shared Design Budget", kind="fund", owner="Alice")
        goal = goals.open_goal(
            self.tribe,
            "Coordinate worker co-op work",
            "Bring business and social planning together.",
            category="business",
            opened_by="Alice",
        )
        task = goals.open_task(self.tribe, "Draft customer offer", opened_by="Alice", goal_id=goal.id)
        rule = self.tribe.define_governance_rule(
            title="Care before deadline escalation",
            description="The tribe pauses delivery pressure if member wellbeing drops sharply.",
            defined_by="Alice",
            kind="care",
            scope="health",
            applies_to=["task", "commitment"],
        )
        intent = self.tribe.record_intent(
            title="Need a customer-ready offer draft",
            created_by="Alice",
            kind="need",
            target_members=["Panpsychic Cyborg Multitude"],
            resource_ids=[resource.id],
        )
        commitment = self.tribe.record_commitment(
            title="Draft the offer by Friday",
            committed_by="Panpsychic Cyborg Multitude",
            owed_by="Panpsychic Cyborg Multitude",
            owed_to="Alice",
            task_id=task.id,
            resource_ids=[resource.id],
        )
        agreement = self.tribe.record_agreement(
            title="Offer drafting agreement",
            created_by="Alice",
            parties=["Alice", "Panpsychic Cyborg Multitude"],
            commitment_ids=[commitment.id],
        )
        link = self.tribe.link_entities(
            source_kind="governance_rule",
            source=rule.id,
            target_kind="agreement",
            target=agreement.id,
            relation="constrains",
            linked_by="Alice",
        )
        self.assertEqual(link.target.kind, "agreement")
        replayed = Tribe(TribeStore(self.tribe.store.path))
        self.assertIn(intent.id, replayed.intents)
        self.assertIn(commitment.id, replayed.commitments)
        self.assertIn(agreement.id, replayed.agreements)
        inbound = replayed.entity_links_for(entity_kind="agreement", entity=agreement.id, direction="inbound")
        self.assertEqual(inbound[0].source.kind, "governance_rule")

    def test_economic_agent_and_protocol_vocabulary_are_replayable(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        resource = self.tribe.register_resource("Shared design pool", kind="fund", owner="Alice")
        contribution = goals.record_contribution(
            self.tribe,
            contributed_by="Alice",
            title="Prepared the first cooperative offer",
            kind="labor",
            resource_id=resource.id,
            quantity=2.0,
            unit="hours",
        )
        agent = self.tribe.record_economic_agent(
            name="Panpsychic Cyborg Multitude",
            created_by="Alice",
            role="design partner",
            obligations=["Deliver reviewed drafts", "Document assumptions"],
            claims=["A fair co-op share model"],
            resource_ids=[resource.id],
            contribution_ids=[contribution.id],
            status="active",
        )
        protocol = self.tribe.record_protocol_term(
            term="agreement",
            definition="A shared operating rule that is explicit, reviewable, and linked to contributions.",
            created_by="Alice",
            domain="economic",
            tags=["governance", "protocol"],
        )

        self.assertEqual(agent.role, "design partner")
        self.assertIn("agreement", protocol.term.lower())
        replayed = Tribe(TribeStore(self.tribe.store.path))
        self.assertIn(agent.id, replayed.economic_agents)
        self.assertIn(protocol.id, replayed.protocol_terms)

    def test_service_status_and_rhythms_include_new_layers(self):
        self.tribe.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        self.tribe.define_rhythm(
            name="Weekly assembly",
            cadence="weekly",
            purpose="Coordinate business, care, and philosophical direction.",
            created_by="Alice",
            participants=["Alice", "Panpsychic Cyborg Multitude"],
            care_required=True,
        )
        service = MultitudeService(self.tribe)
        status = service.status()
        self.assertGreaterEqual(status["memberships"], 2)
        self.assertEqual(status["rhythms"], 1)
        rhythms = service.list_rhythms()
        self.assertEqual(rhythms[0]["name"], "Weekly assembly")
        self.assertEqual(service.list_memberships()[-1]["member_name"], "Panpsychic Cyborg Multitude")

class LLMNodeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "tribes")
        os.makedirs(self.root)
        self.tribe = Tribe.found(self.root, "AI Tribe", "Test.", "Alice")

    def tearDown(self):
        self.tmp.cleanup()

    def test_silent_when_model_unreachable(self):
        from multitude.llm import TechnologicalNode

        class DeadClient:
            model = "test-model"

            def chat(self, system, user):
                return None

        node = TechnologicalNode(self.tribe, "Panpsychic Cyborg Multitude", client=DeadClient())
        node.speak("anything")
        self.assertEqual(len(self.tribe.messages), 1)
        self.assertEqual(self.tribe.messages[0].kind, "system")
        self.assertIn("silent", self.tribe.messages[0].text)

    def test_vote_parsing_variants(self):
        from multitude.llm import TechnologicalNode

        class StubClient:
            model = "test-model"

            def __init__(self, reply):
                self.reply = reply

            def chat(self, system, user):
                return self.reply

        node = TechnologicalNode(self.tribe, "Panpsychic Cyborg Multitude", client=StubClient(None))
        pos, reason = node._parse_position(None)
        self.assertEqual(pos, Position.ABSTAIN)

        pos, reason = node._parse_position('{"position": "block", "reason": "no"}')
        self.assertEqual(pos, Position.BLOCK)
        self.assertEqual(reason, "no")

        pos, reason = node._parse_position("I am against this because of cost.")
        self.assertEqual(pos, Position.AGAINST)

        pos, reason = node._parse_position("utter nonsense")
        self.assertEqual(pos, Position.ABSTAIN)

    def test_vote_cast_through_stub(self):
        from multitude.llm import TechnologicalNode

        class StubClient:
            model = "test-model"

            def chat(self, system, user):
                return '{"position": "for", "reason": "aligned with charter"}'

        node = TechnologicalNode(self.tribe, "Panpsychic Cyborg Multitude", client=StubClient())
        p = self.tribe.open_proposal("P", "Proposal text.", opened_by="Alice")
        node.vote(p.id)
        t = self.tribe.tally(p.id)
        self.assertEqual(t["counts"]["for"], 1)
        vote = self.tribe.proposals[p.id].votes[node.member.id]
        self.assertEqual(vote.reason, "aligned with charter")


if __name__ == "__main__":
    unittest.main()
