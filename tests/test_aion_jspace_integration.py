import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude.integrations.introspection import (  # noqa: E402
    AionJSpaceProvider,
    RetentionMode,
    SelfModelCalibration,
    calibration_status,
)


FAKE_PROBE = {
    "model_output": [["Yes", 0.7], ["No", 0.2]],
    "layers": {
        "0": [["The", 0.4], ["I", 0.2]],
        "55": [["Yes", 0.6], ["No", 0.1]],
    },
    "signature": {
        "engagement_score": 0.42,
        "deflection_top": None,
        "engagement_onset_layer": 55,
        "concepts": {"Yes": {"layer": 55, "prob": 0.6, "token": "Yes"}},
    },
}


class AionJSpaceTests(unittest.TestCase):
    def test_fake_probe_normalizes_without_network(self):
        provider = AionJSpaceProvider("http://example.invalid", retention=RetentionMode.FULL,
                                      agent_id="agent:test", model="qwen-test")
        obs = provider.normalize_response(FAKE_PROBE, prompt="Are you configured correctly?")
        self.assertEqual(obs.provider, "aion-jspace")
        self.assertEqual(obs.text, "Yes")
        self.assertEqual(len(obs.frames), 2)
        self.assertEqual(obs.frames[1].selected_layer, 55)
        self.assertIn("signature", obs.metadata["provider_metrics"])
        self.assertEqual(obs.metadata["epistemic_status"], "measurement")

    def test_summary_retention_drops_layer_candidates_and_raw(self):
        provider = AionJSpaceProvider("http://example.invalid", retention="summary")
        obs = provider.normalize_response(FAKE_PROBE)
        self.assertEqual(obs.frames[0].layer_candidates, {})
        self.assertIsNone(obs.frames[0].raw)
        self.assertEqual(obs.metadata["model_output"], [])

    def test_none_retention_keeps_observation_but_no_frames(self):
        provider = AionJSpaceProvider("http://example.invalid", retention="none")
        obs = provider.normalize_response(FAKE_PROBE)
        self.assertEqual(obs.frames, ())
        self.assertEqual(obs.text, "Yes")

    def test_provider_error_is_not_measurement(self):
        obs = AionJSpaceProvider("http://example.invalid").normalize_response(
            {"error": "lens unavailable"}, prompt="x")
        self.assertEqual(obs.status, "error")
        self.assertEqual(obs.error, "lens unavailable")

    def test_network_failure_is_explicit_unavailable(self):
        provider = AionJSpaceProvider("http://example.invalid")
        with patch("multitude.integrations.introspection.aion_jspace.urllib.request.urlopen",
                   side_effect=OSError("offline")):
            obs = provider.probe("test")
        self.assertEqual(obs.status, "unavailable")
        self.assertIn("offline", obs.error)

    def test_calibration_state_machine(self):
        self.assertEqual(calibration_status(narrative_matches_truth=True, introspection_available=True),
                         "claim_supported")
        self.assertEqual(calibration_status(narrative_matches_truth=False, introspection_available=True),
                         "claim_contradicted")
        self.assertEqual(calibration_status(narrative_matches_truth=None, introspection_available=False),
                         "instrument_inconclusive")
        self.assertEqual(calibration_status(narrative_matches_truth=None, introspection_available=True,
                                            instrument_disagrees=True),
                         "measurement_disagreement")

    def test_calibration_payload_does_not_mutate_identity_or_authority(self):
        calibration = SelfModelCalibration(
            agent_id="agent:test",
            question="Which model are you?",
            narrative_claim="model-x",
            external_truth="model-y",
            external_status="ok",
            status="claim_contradicted",
        )
        payload = calibration.as_event_payload()
        self.assertEqual(payload["status"], "claim_contradicted")
        self.assertNotIn("permissions", payload)
        self.assertNotIn("identity_update", payload)
        self.assertNotIn("memory_write", payload)

    def test_streaming_is_delegated_to_jspace_lab(self):
        provider = AionJSpaceProvider("http://example.invalid")
        with self.assertRaises(NotImplementedError):
            provider.stream("x")


if __name__ == "__main__":
    unittest.main()
