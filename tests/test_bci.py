# -*- coding: utf-8 -*-
"""Tests for the optional BCI integration (issues #10 and #41).

Hardware is never required: the synthetic adapter feeds the pipeline.
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude.integrations.bci import (  # noqa: E402
    BCIAdapter,
    BCICommand,
    BCIError,
    BCIObservation,
    BCISecurityError,
    BCISecurityGate,
    BCIHub,
    SyntheticBCIAdapter,
    normalize_observation_payload,
)
from multitude.models import NodeKind  # noqa: E402
from multitude.rhizome import Rhizome  # noqa: E402


def obs(**overrides):
    base: dict = dict(
        ts="2026-09-06T12:00:00Z",
        signal_type="attention",
        value=0.72,
        unit="",
        confidence=0.63,
        layer="psychic",
        metadata={},
    )
    base.update(overrides)
    return BCIObservation(**base)


def command(now: datetime, **overrides):
    base: dict = dict(
        ts=now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        command="select",
        event_id="evt-1",
        source="synthetic-bci",
        intentional=True,
        confidence=0.9,
        metadata={"provenance": {"adapter": "synthetic-bci", "classifier": "test-v1"}},
    )
    base.update(overrides)
    return BCICommand(**base)


class ObservationTests(unittest.TestCase):
    def test_observation_rejects_invalid_layer(self):
        with self.assertRaises(BCIError):
            obs(layer="social")

    def test_observation_rejects_bad_confidence(self):
        with self.assertRaises(BCIError):
            obs(confidence=1.5)
        with self.assertRaises(BCIError):
            obs(confidence=float("nan"))

    def test_observation_rejects_empty_signal(self):
        with self.assertRaises(BCIError):
            obs(signal_type="  ")

    def test_to_payload_normalizes_signal_case(self):
        payload = obs(signal_type="Attention").to_payload()
        self.assertEqual(payload["signal_type"], "attention")

    def test_normalize_rejects_malformed(self):
        with self.assertRaises(BCIError):
            normalize_observation_payload({"ts": "", "signal_type": "attention"})
        with self.assertRaises(BCIError):
            normalize_observation_payload(payload="not a dict")  # type: ignore[arg-type]
        with self.assertRaises(BCIError):
            normalize_observation_payload(
                {"ts": "t", "signal_type": "attention", "confidence": "high"}
            )
        with self.assertRaises(BCIError):
            normalize_observation_payload(
                {"ts": "t", "signal_type": "attention", "layer": "physical"}
            )

    def test_normalize_preserves_unknown_values(self):
        payload = normalize_observation_payload(
            {"ts": "t", "signal_type": "sleep_state", "value": "UNKNOWN",
             "confidence": 0.1, "layer": "biological"}
        )
        self.assertEqual(payload["value"], "UNKNOWN")


class SyntheticAdapterTests(unittest.TestCase):
    def test_disabled_adapter_reads_nothing(self):
        adapter = SyntheticBCIAdapter(enabled=False, script=[dict(
            ts="t", signal_type="attention", value=0.7, confidence=0.5, layer="psychic",
        )])
        self.assertEqual(adapter.read_context(), [])

    def test_enabled_adapter_streams_script(self):
        adapter = SyntheticBCIAdapter(enabled=True, script=[dict(
            ts="t1", signal_type="heart_rate", value=62, unit="bpm",
            confidence=0.9, layer="biological",
        ), dict(
            ts="t2", signal_type="attention", value=0.55, confidence=0.4,
            layer="psychic",
        )])
        first = adapter.read_context()
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].signal_type, "heart_rate")
        second = adapter.read_context()
        self.assertEqual(second[0].signal_type, "attention")
        self.assertEqual(adapter.read_context(), [])


class BCISecurityGateTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 14, 10, 0, 0, tzinfo=timezone.utc)
        self.gate = BCISecurityGate(max_age_seconds=10, max_future_skew_seconds=2)

    def test_valid_intentional_command_passes(self):
        cmd = command(self.now)
        self.assertIs(self.gate.validate_command(cmd, now=self.now), cmd)

    def test_replayed_command_is_rejected(self):
        cmd = command(self.now)
        self.gate.validate_command(cmd, now=self.now)
        with self.assertRaises(BCISecurityError):
            self.gate.validate_command(cmd, now=self.now)

    def test_stale_command_is_rejected(self):
        stale = command(self.now - timedelta(seconds=11), event_id="stale-1")
        with self.assertRaises(BCISecurityError):
            self.gate.validate_command(stale, now=self.now)

    def test_future_dated_command_is_rejected(self):
        future = command(self.now + timedelta(seconds=3), event_id="future-1")
        with self.assertRaises(BCISecurityError):
            self.gate.validate_command(future, now=self.now)

    def test_passive_observation_cannot_escalate_to_command(self):
        passive = obs(confidence=0.99)
        with self.assertRaises(BCISecurityError):
            self.gate.validate_command(passive, now=self.now)  # type: ignore[arg-type]

    def test_command_requires_explicit_intent_and_provenance_source(self):
        with self.assertRaises(BCISecurityError):
            command(self.now, intentional=False, event_id="no-intent")
        with self.assertRaises(BCISecurityError):
            command(self.now, source="", event_id="no-source")

    def test_bad_provenance_shape_fails_closed(self):
        cmd = command(self.now, event_id="bad-prov", metadata={"provenance": "forged"})
        with self.assertRaises(BCISecurityError):
            self.gate.validate_command(cmd, now=self.now)


class HubConsentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rhizome = Rhizome.found(
            os.path.join(self.tmp.name, "tribes"),
            "BCI Test",
            charter="consent-first",
            founder_name="Alice",
        )
        self.rhizome.join("PCM node", NodeKind.TECHNOLOGICAL)
        self.hub = BCIHub(self.rhizome)
        self.adapter = SyntheticBCIAdapter(enabled=False, script=[dict(
            ts="t", signal_type="attention", value=0.72, confidence=0.63,
            layer="psychic",
        )])

    def tearDown(self):
        self.tmp.cleanup()

    def test_ai_agent_cannot_add_enable_or_read(self):
        with self.assertRaises(BCIError):
            self.hub.add_adapter("muse", self.adapter, by="PCM node")
        self.hub.add_adapter("muse", self.adapter, by="Alice")
        with self.assertRaises(BCIError):
            self.hub.enable("muse", by="PCM node")
        with self.assertRaises(BCIError):
            self.hub.disable("muse", by="PCM node")
        with self.assertRaises(BCIError):
            self.hub.read_context("muse", by="PCM node")
        with self.assertRaises(BCIError):
            self.hub.publish("muse", obs(), by="PCM node")
        self.assertFalse(self.adapter.enabled)

    def test_unknown_member_refused(self):
        with self.assertRaises(BCIError):
            self.hub.enable("muse", by="Mallory")

    def test_disabled_reads_nothing_then_enable_by_human(self):
        self.hub.add_adapter("muse", self.adapter, by="Alice")
        self.assertEqual(self.hub.read_context("muse", by="Alice"), [])
        self.hub.enable("muse", by="Alice")
        got = self.hub.read_context("muse", by="Alice")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].signal_type, "attention")
        self.assertEqual(self.hub.latest("muse"), got)

    def test_publish_is_explicit_and_private_by_default(self):
        self.hub.add_adapter("muse", self.adapter, by="Alice")
        self.hub.enable("muse", by="Alice")
        observation = self.hub.read_context("muse", by="Alice")[0]
        self.assertEqual(len(self.rhizome.biometric_signals), 0)
        rec = self.hub.publish("muse", observation, by="Alice")
        self.assertEqual(len(self.rhizome.biometric_signals), 1)
        self.assertEqual(rec["signal_type"], "attention")
        self.assertEqual(rec["sensitivity"], "private")
        self.assertEqual(rec["meta"]["confidence"], 0.63)
        self.assertEqual(rec["meta"]["layer"], "psychic")
        self.assertEqual(rec["meta"]["bci_adapter"], "muse")
        self.assertEqual(rec["meta"]["authority"], "passive_context_only")

    def test_publish_sensitive_as_shared_refused(self):
        self.hub.add_adapter("muse", self.adapter, by="Alice")
        with self.assertRaises(BCIError):
            self.hub.publish("muse", obs(sensitivity="private"),
                             by="Alice", sensitivity="shared")
        rec = self.hub.publish("muse", obs(), by="Alice", sensitivity="limited")
        self.assertEqual(rec["sensitivity"], "limited")

    def test_publish_rejects_intentional_command_object(self):
        self.hub.add_adapter("muse", self.adapter, by="Alice")
        cmd = command(datetime.now(timezone.utc))
        with self.assertRaises(BCIError):
            self.hub.publish("muse", cmd, by="Alice")  # type: ignore[arg-type]

    def test_publish_heart_rate_biological_layer(self):
        hr = SyntheticBCIAdapter(enabled=True, script=[dict(
            ts="t", signal_type="heart_rate", value=61, unit="bpm",
            confidence=0.95, layer="biological",
        )])
        self.hub.add_adapter("hr", hr, by="Alice")
        reading = self.hub.read_context("hr", by="Alice")[0]
        rec = self.hub.publish("hr", reading, by="Alice", sensitivity="limited")
        self.assertEqual(rec["signal_type"], "heart_rate")
        self.assertEqual(rec["value"], 61)
        self.assertEqual(rec["meta"]["layer"], "biological")


class AdapterContractTests(unittest.TestCase):
    def test_base_adapter_is_abstract(self):
        adapter = BCIAdapter(enabled=True)
        with self.assertRaises(NotImplementedError):
            adapter.read_context()


if __name__ == "__main__":
    unittest.main()
