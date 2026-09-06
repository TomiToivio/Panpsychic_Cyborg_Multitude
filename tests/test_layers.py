# -*- coding: utf-8 -*-
"""Tests for the six-layer agent tracking (physical .. cybernetic)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude.layers import (  # noqa: E402
    LayerError,
    normalize_changes,
    normalize_layer_name,
)
from multitude.models import Layer, NodeKind  # noqa: E402
from multitude.store import RhizomeStore  # noqa: E402
from multitude.rhizome import Rhizome, RhizomeError  # noqa: E402


class LayerTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "tribes")
        os.makedirs(self.root)
        self.rhizome = Rhizome.found(
            self.root,
            "Layer Rhizome",
            charter="Track the whole agent.",
            founder_name="Alice",
        )

    def tearDown(self):
        self.tmp.cleanup()


class TestNormalizedVocabulary(LayerTestBase):
    def test_normalize_layer_name(self):
        self.assertEqual(normalize_layer_name("Physical"), Layer.PHYSICAL)
        with self.assertRaises(LayerError):
            normalize_layer_name("emotionally")

    def test_alias_mapping(self):
        out = normalize_changes(Layer.BIOLOGICAL, {"sleep": "tired", "mood": "curious"})
        self.assertEqual(out["sleep_state"], "tired")
        self.assertEqual(out["mood"], "curious")
        with self.assertRaises(LayerError):
            normalize_changes(Layer.BIOLOGICAL, {"not_a_field": 1})

    def test_data_becomes_notes(self):
        out = normalize_changes(Layer.SOCIAL, {"data": "works with Castells lens"})
        self.assertEqual(out["notes"], "works with Castells lens")

    def test_list_fields(self):
        out = normalize_changes(
            Layer.LINGUISTIC,
            {"languages": ["fi", "en"], "special_vocabularies": "populism theory"},
        )
        self.assertEqual(out["languages"], ["fi", "en"])
        self.assertEqual(out["vocabularies"], ["populism theory"])

    def test_gps_pair_validation(self):
        out = normalize_changes(Layer.PHYSICAL, {"lat": 60.17, "lon": 24.94})
        self.assertEqual(out["gps"], {"lat": 60.17, "lon": 24.94})
        with self.assertRaises(LayerError):
            normalize_changes(Layer.PHYSICAL, {"lat": 60.17})  # no lon
        with self.assertRaises(LayerError):
            normalize_changes(Layer.PHYSICAL, {"lat": 91.0, "lon": 0.0})
        with self.assertRaises(LayerError):
            normalize_changes(Layer.PHYSICAL, {"lat": "north", "lon": 0.0})

    def test_empty_record_rejected(self):
        with self.assertRaises(LayerError):
            normalize_changes(Layer.PSYCHIC, {})


class TestJoinSeeds(LayerTestBase):
    def test_biological_join_seeds_psychic_conscious(self):
        self.rhizome.join("Mari", NodeKind.BIOLOGICAL)
        m = self.rhizome.member_by_name("Mari")
        self.assertTrue(m.profile.psychic.is_conscious)
        self.assertIn("ape", m.profile.psychic.notes)

    def test_technological_join_seeds_distributed_physical(self):
        self.rhizome.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL, model="glm-5.3-flash:cloud")
        m = self.rhizome.member_by_name("Panpsychic Cyborg Multitude")
        self.assertIn("distributed", m.profile.physical.notes)
        self.assertIsNone(m.profile.psychic.is_conscious)  # unknown, not asserted
        self.assertEqual(m.profile.cybernetic.interface_mode, "text")

    def test_founder_gets_seeds_and_replay_keeps_them(self):
        tom = self.rhizome.member_by_name("Alice")
        self.assertTrue(tom.profile.biological.is_biological)
        self.assertTrue(tom.profile.psychic.is_conscious)
        # fresh Rhizome instance replays the same log
        again = Rhizome(RhizomeStore(self.rhizome.store.path))
        tom2 = again.member_by_name("Alice")
        self.assertTrue(tom2.profile.psychic.is_conscious)


class TestRecordAndReplay(LayerTestBase):
    def test_record_layer_updates_state_and_log(self):
        self.rhizome.record_layer("Alice", "physical", {"location": "Springfield"})
        m = self.rhizome.member_by_name("Alice")
        self.assertEqual(m.profile.physical.location_label, "Springfield")
        events = [
            e for e in self.rhizome.store.replay() if e.type == "layer_recorded"
        ]
        self.assertTrue(any(e.payload["layer"] == "physical" for e in events))

    def test_self_report_default_and_observer_report(self):
        self.rhizome.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        self.rhizome.record_layer("Panpsychic Cyborg Multitude", "cybernetic", {"interface_mode": "text"})
        self.rhizome.record_layer(
            "Alice", "Panpsychic Cyborg Multitude",  # wrong order on purpose: member, then layer handled below
        ) if False else None
        self.rhizome.record_layer("Panpsychic Cyborg Multitude", "psychic", {"state": "attentive"},
                                reported_by="Alice")
        history = self.rhizome.layer_history("Panpsychic Cyborg Multitude", "psychic")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["reported_by"], "Alice")

    def test_history_is_append_only(self):
        self.rhizome.record_layer("Alice", "biological", {"mood": "focused"})
        self.rhizome.record_layer("Alice", "biological", {"mood": "restless"})
        history = self.rhizome.layer_history("Alice", "biological")
        self.assertEqual(len(history), 2)
        m = self.rhizome.member_by_name("Alice")
        # newest reading wins in replayed profile
        self.assertEqual(m.profile.biological.mood, "restless")
        # replay from scratch preserves it
        again = Rhizome(RhizomeStore(self.rhizome.store.path))
        self.assertEqual(
            again.member_by_name("Alice").profile.biological.mood, "restless"
        )

    def test_unknown_member_raises(self):
        with self.assertRaises(RhizomeError):
            self.rhizome.record_layer("Ghost", "physical", {"location_label": "nowhere"})

    def test_invalid_gps_rejected_end_to_end(self):
        with self.assertRaises(LayerError):
            self.rhizome.record_layer("Alice", "physical", {"lat": 200, "lon": 0})

    def test_private_flag_stored(self):
        self.rhizome.record_layer("Alice", "psychic", {"state": "low"}, visible=False)
        history = self.rhizome.layer_history("Alice", "psychic")
        self.assertFalse(history[-1]["visible"])


class TestFormatting(LayerTestBase):
    def test_format_shows_filled_layers_only(self):
        self.rhizome.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        text = self.rhizome.member_by_name("Panpsychic Cyborg Multitude")
        from multitude.layers import format_member_layers

        rendered = format_member_layers(text)
        self.assertIn("physical:", rendered)
        self.assertIn("distributed", rendered)
        self.assertNotIn("linguistic:", rendered)

    def test_context_includes_layer_summaries(self):
        self.rhizome.join("Panpsychic Cyborg Multitude", NodeKind.TECHNOLOGICAL)
        ctx = self.rhizome.context_for_llm()
        self.assertIn("Member layer summaries:", ctx)
        self.assertIn("distributed", ctx)


if __name__ == "__main__":
    unittest.main()
