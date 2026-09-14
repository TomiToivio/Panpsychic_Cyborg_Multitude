import os
import sys
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude.integrations.introspection import JSpaceLabProvider, RetentionMode, parse_sse_blocks  # noqa: E402


class FakeSseResponse:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    def read(self, _size):
        return self.chunks.pop(0) if self.chunks else b""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class JSpaceLabIntegrationTests(unittest.TestCase):
    def test_sse_parser_handles_chunk_boundaries(self):
        chunks = [b'data: {"type":"ask_to', b'ken","text":"hel"}\n\n', b'data: {"type":"ask_done"}\n\n']
        events = list(parse_sse_blocks(chunks))
        self.assertEqual(events[0]["text"], "hel")
        self.assertEqual(events[1]["type"], "ask_done")

    def test_normalizes_provider_specific_fields(self):
        provider = JSpaceLabProvider("http://example.invalid", agent_id="agent:test")
        frame = provider.normalize_event({
            "type": "frame", "step": 3, "veto_layer": 55,
            "engagement_score": 0.7, "veto": True,
            "layers": {"55": [["yes", 0.4]]},
        })
        self.assertEqual(frame.provider, "jspace-lab")
        self.assertEqual(frame.selected_layer, 55)
        self.assertEqual(frame.provider_metrics["engagement_score"], 0.7)
        self.assertIn("provider:veto", frame.flags)

    def test_summary_retention_drops_raw_and_layer_ladder(self):
        provider = JSpaceLabProvider("http://example.invalid", retention=RetentionMode.SUMMARY)
        frame = provider.normalize_event({"type": "frame", "step": 1, "layers": {"1": [["a", 0.9]]}, "engagement_score": 0.2})
        self.assertIsNone(frame.raw)
        self.assertEqual(frame.layer_candidates, {})
        self.assertEqual(frame.provider_metrics["engagement_score"], 0.2)

    def test_none_retention_discards_frame(self):
        provider = JSpaceLabProvider("http://example.invalid", retention=RetentionMode.NONE)
        self.assertIsNone(provider.normalize_event({"type": "frame", "step": 1}))

    def test_full_retention_keeps_raw_trace(self):
        provider = JSpaceLabProvider("http://example.invalid", retention=RetentionMode.FULL)
        frame = provider.normalize_event({"type": "frame", "step": 2, "layers": {"2": [["b", 0.8]]}})
        self.assertEqual(frame.raw["step"], 2)
        self.assertIn("2", frame.layer_candidates)

    def test_partial_frame_is_valid(self):
        frame = JSpaceLabProvider("http://example.invalid").normalize_event({"type": "frame"})
        self.assertIsNone(frame.token_index)
        self.assertEqual(frame.provider_metrics, {})

    def test_ask_mode_uses_sse_without_network(self):
        response = FakeSseResponse([
            b'data: {"type":"ask_token","text":"hel"}\n\n',
            b'data: {"type":"ask_token","text":"lo"}\n\n',
            b'data: {"type":"ask_done"}\n\n',
        ])
        provider = JSpaceLabProvider("http://example.invalid")
        with patch("multitude.integrations.introspection.urllib.request.urlopen", return_value=response):
            observation = provider.ask("test prompt")
        self.assertEqual(observation.status, "ok")
        self.assertEqual(observation.text, "hello")
        self.assertTrue(observation.metadata["ask_done"])
        self.assertIn("prompt_sha256", observation.metadata)
        self.assertNotIn("test prompt", observation.metadata.values())

    def test_unavailable_provider_returns_explicit_state(self):
        provider = JSpaceLabProvider("http://example.invalid")
        with patch("multitude.integrations.introspection.urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            observation = provider.ask("test prompt")
        self.assertEqual(observation.status, "unavailable")
        self.assertIn("offline", observation.error)

    def test_frame_has_no_governance_mutation_surface(self):
        frame = JSpaceLabProvider("http://example.invalid").normalize_event({"type": "frame"})
        self.assertFalse(hasattr(frame, "vote"))
        self.assertFalse(hasattr(frame, "update_member"))
        self.assertFalse(hasattr(frame, "remember"))


if __name__ == "__main__":
    unittest.main()
