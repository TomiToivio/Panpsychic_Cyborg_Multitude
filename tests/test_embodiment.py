# -*- coding: utf-8 -*-
"""Tests for the optional embodiment module (issue #12).

Hardware is never required: the simulated light stands in for devices.
"""
import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude.integrations.embodiment import (  # noqa: E402
    DeviceAction,
    EmbodimentError,
    PhysicalAgency,
    PhysicalDevice,
    SimulatedLight,
    embodiment_enabled,
)


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def always_allow(author, action, target, parameters):
    return True


class FlagTests(unittest.TestCase):
    def test_flag_defaults_off(self):
        os.environ.pop("PCM_EMBODIMENT_ENABLED", None)
        self.assertFalse(embodiment_enabled())

    def test_flag_truthy_values(self):
        for value in ("1", "true", "yes", "True", "YES"):
            os.environ["PCM_EMBODIMENT_ENABLED"] = value
            self.assertTrue(embodiment_enabled())
        for value in ("0", "false", "", "no"):
            os.environ["PCM_EMBODIMENT_ENABLED"] = value
            self.assertFalse(embodiment_enabled())
        os.environ.pop("PCM_EMBODIMENT_ENABLED", None)


class DisabledTests(unittest.TestCase):
    def test_registration_refused_while_disabled(self):
        agency = PhysicalAgency(enabled=False)
        with self.assertRaises(EmbodimentError):
            agency.register(SimulatedLight())

    def test_execution_refused_while_disabled(self):
        agency = PhysicalAgency(enabled=False)
        action = DeviceAction(action="power.set", target="sim-light-01",
                              parameters={"value": "off"}, requested_by="Alice")
        with self.assertRaises(EmbodimentError):
            run(agency.execute(action))

    def test_read_state_refused_while_disabled(self):
        agency = PhysicalAgency(enabled=False)
        with self.assertRaises(EmbodimentError):
            run(agency.read_state("sim-light-01"))


class SimulatedDeviceTests(unittest.TestCase):
    def setUp(self):
        self.agency = PhysicalAgency(enabled=True, policy_decide=always_allow)
        self.light = SimulatedLight(initial_state="on")
        self.agency.register(self.light)

    def test_describe_and_capabilities(self):
        desc = run(self.light.describe())
        self.assertTrue(desc["simulated"])
        self.assertEqual(desc["kind"], "actuator.light")
        self.assertIn("power.set", run(self.light.capabilities()))

    def test_read_state(self):
        state = run(self.agency.read_state("sim-light-01"))
        self.assertEqual(state["power"], "on")
        self.assertEqual(state["source"], "simulated")

    def test_safe_action_executes_and_verifies(self):
        action = DeviceAction(action="power.set", target="sim-light-01",
                              parameters={"value": "off"}, requested_by="Alice")
        result = run(self.agency.execute(action))
        self.assertTrue(result.ok)
        self.assertEqual(result.state_after["power"], "off")  # verified read-back
        self.assertEqual(result.requested_by, "Alice")
        # journal carries provenance
        self.assertEqual(len(self.agency.journal), 1)
        self.assertEqual(self.agency.journal[0].action, "power.set")

    def test_unknown_capability_refused(self):
        action = DeviceAction(action="brightness.set", target="sim-light-01",
                              parameters={"value": 50}, requested_by="Alice")
        with self.assertRaises(EmbodimentError):
            run(self.agency.execute(action))

    def test_malformed_parameter_refused(self):
        action = DeviceAction(action="power.set", target="sim-light-01",
                              parameters={"value": "blink"}, requested_by="Alice")
        with self.assertRaises(EmbodimentError):
            run(self.agency.execute(action))

    def test_unregistered_device_refused(self):
        action = DeviceAction(action="power.set", target="no-such-light",
                              parameters={"value": "off"}, requested_by="Alice")
        with self.assertRaises(EmbodimentError):
            run(self.agency.execute(action))


class PolicyTests(unittest.TestCase):
    def test_policy_deny_blocks_action(self):
        def deny_all(author, action, target, parameters):
            return False

        agency = PhysicalAgency(enabled=True, policy_decide=deny_all)
        agency.register(SimulatedLight())
        action = DeviceAction(action="power.set", target="sim-light-01",
                              parameters={"value": "off"}, requested_by="Alice")
        with self.assertRaises(EmbodimentError):
            run(agency.execute(action))
        # state untouched, journal empty — fail-closed
        self.assertEqual(run(agency.read_state("sim-light-01"))["power"], "on")
        self.assertEqual(agency.journal, [])

    def test_pcm_policy_semantics_plug_in(self):
        # a policy table in pcm.policy style: allow Alice only
        def policy(author, action, target, parameters):
            return author == "Alice" and action == "power.set"

        agency = PhysicalAgency(enabled=True, policy_decide=policy)
        agency.register(SimulatedLight())
        ok_action = DeviceAction(action="power.set", target="sim-light-01",
                                 parameters={"value": "off"}, requested_by="Alice")
        result = run(agency.execute(ok_action))
        self.assertTrue(result.ok)
        denied = DeviceAction(action="power.set", target="sim-light-01",
                              parameters={"value": "on"}, requested_by="Mallory")
        with self.assertRaises(EmbodimentError):
            run(agency.execute(denied))


class ArchitectureTests(unittest.TestCase):
    def test_physical_device_is_abstract(self):
        with self.assertRaises(TypeError):
            PhysicalDevice()  # type: ignore[abstract]

    def test_no_real_dependencies(self):
        # the module imports without HA/MQTT/zenoh — only stdlib + PCM
        import multitude.integrations.embodiment as mod
        self.assertTrue(hasattr(mod, "PhysicalDevice"))
        self.assertTrue(hasattr(mod, "SimulatedLight"))
        self.assertTrue(hasattr(mod, "PhysicalAgency"))


if __name__ == "__main__":
    unittest.main()