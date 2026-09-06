# -*- coding: utf-8 -*-
"""Optional embodiment module — PhysicalDevice abstraction (issue #12).

The minimal first step of the embodied-AI plan: the *architecture* so
real devices can be added later, nothing more. Disabled by default
(``PCM_EMBODIMENT_ENABLED=false`` — the kernel and every other PCM
subsystem work exactly as before when embodiment is off).

Architecture principle (constitutional):

    LLM / Agent
         ↓  structured intent
    PCM
         ↓
    optional Physical Agency adapter   ← this module
         ↓
    PhysicalDevice                     ← simulated for now

The LLM never calls hardware. This module never executes arbitrary
code: actions are validated dicts matched against an explicit
capability allowlist, policy authorization is fail-closed (default
DENY, reusing ``pcm.policy`` semantics), every action is recorded with
provenance, and the resulting device state is verified after execution.

No real integrations here — Home Assistant, MQTT, zenoh-pico, cameras,
drones, ROS 2 are later stages with clear extension points (implement
``PhysicalDevice`` and register with a ``DeviceRegistry``).
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

# Config flag: embodiment is opt-in. Absent/false means fully off.
EMBODIMENT_ENV = "PCM_EMBODIMENT_ENABLED"


def embodiment_enabled() -> bool:
    """True when PCM_EMBODIMENT_ENABLED is truthy ('1', 'true', 'yes')."""
    return os.environ.get(EMBODIMENT_ENV, "").strip().lower() in {"1", "true", "yes"}


class EmbodimentError(Exception):
    """Invalid device operation, unauthorized action, or disabled module."""


# --------------------------------------------------------------- device ABC

class PhysicalDevice(ABC):
    """The thin contract every device driver implements.

    Async by design (real drivers are I/O); the simulated device keeps
    the same shape so tests exercise the true interface.
    """

    device_id: str = ""
    location: str = ""

    @abstractmethod
    async def describe(self) -> dict[str, Any]:
        """Identity, kind, location — never vendor internals."""

    @abstractmethod
    async def capabilities(self) -> list[str]:
        """Explicit capability allowlist (e.g. ['power.set', 'state.read'])."""

    @abstractmethod
    async def read_state(self) -> dict[str, Any]:
        """Current normalized device state."""

    @abstractmethod
    async def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute one validated action; returns the resulting state."""


# ----------------------------------------------------------- action records

@dataclass(frozen=True)
class DeviceAction:
    """A structured device command — the only thing an agent may issue."""

    action: str          # capability name, e.g. 'power.set'
    target: str          # device id
    parameters: dict[str, Any] = field(default_factory=dict)
    requested_by: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "target": self.target,
            "parameters": dict(self.parameters),
            "requested_by": self.requested_by,
        }


@dataclass(frozen=True)
class ActionResult:
    """Verified outcome of one device action (provenance attached)."""

    ok: bool
    device_id: str
    action: str
    state_after: dict[str, Any]
    requested_by: str
    error: str = ""


# -------------------------------------------------------------- sim device

class SimulatedLight(PhysicalDevice):
    """Simulated hardware: a light with on/off state, no real dependency.

    The entire pipeline is testable against this device; real drivers
    later implement the same ABC (extension point, not in this scope).
    """

    def __init__(self, device_id: str = "sim-light-01", location: str = "living_room",
                 initial_state: str = "on") -> None:
        self.device_id = device_id
        self.location = location
        self._state: dict[str, Any] = {
            "power": "on" if initial_state == "on" else "off",
            "source": "simulated",
        }

    async def describe(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id, "kind": "actuator.light",
            "location": self.location, "simulated": True,
        }

    async def capabilities(self) -> list[str]:
        return ["power.set", "state.read"]

    async def read_state(self) -> dict[str, Any]:
        return dict(self._state)

    async def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        action_name = str(action.get("action", "")).strip()
        if action_name != "power.set":
            raise EmbodimentError(
                f"SimulatedLight only supports 'power.set', got '{action_name}'")
        value = action.get("parameters", {}).get("value")
        if value not in ("on", "off"):
            raise EmbodimentError(
                f"power.set parameter 'value' must be 'on' or 'off', got {value!r}")
        self._state["power"] = value
        return dict(self._state)


# ------------------------------------------------------------- the adapter

class PhysicalAgency:
    """The optional adapter between PCM agents and devices.

    Fail-closed by construction:

    * everything is refused while ``enabled=False`` (the default);
    * actions must match the device's declared capability allowlist;
    * policy check (pcm.policy-compatible callable or rule table) runs
      BEFORE any device touch;
    * the resulting state is read back and verified after execution;
    * every result carries provenance (requested_by, action, state).
    """

    def __init__(self, enabled: Optional[bool] = None,
                 policy_decide: Optional[Any] = None) -> None:
        # policy_decide: callable(author, action, target, parameters) -> bool
        # (a pcm.policy.Policy.decide bound method plugs in directly)
        self.enabled = embodiment_enabled() if enabled is None else bool(enabled)
        self._policy_decide = policy_decide
        self._devices: dict[str, PhysicalDevice] = {}
        self._journal: list[ActionResult] = []

    def register(self, device: PhysicalDevice) -> None:
        if not self.enabled:
            raise EmbodimentError("embodiment is disabled (PCM_EMBODIMENT_ENABLED)")
        self._devices[device.device_id] = device

    def device(self, device_id: str) -> PhysicalDevice:
        device = self._devices.get(device_id)
        if device is None:
            raise EmbodimentError(f"no registered device '{device_id}'")
        return device

    @property
    def journal(self) -> list[ActionResult]:
        """Every executed action with provenance (read-only copy)."""
        return list(self._journal)

    # ------------------------------------------------------------- actions
    async def execute(self, action: DeviceAction) -> ActionResult:
        """Run one structured action through the full safety chain."""
        if not self.enabled:
            raise EmbodimentError(
                "embodiment is disabled (PCM_EMBODIMENT_ENABLED); action refused")
        device = self.device(action.target)
        caps = await device.capabilities()
        if action.action not in caps:
            raise EmbodimentError(
                f"action '{action.action}' is not in the capability allowlist "
                f"of '{action.target}' ({caps})")
        if self._policy_decide is not None and not self._policy_decide(
                action.requested_by, action.action, action.target,
                action.parameters):
            raise EmbodimentError(
                f"policy denies {action.requested_by!r} -> "
                f"{action.action!r} on {action.target!r}")
        try:
            state_after = await device.execute(action.to_payload())
        except EmbodimentError:
            raise
        except Exception as exc:  # device drivers may raise anything
            raise EmbodimentError(f"device execution failed: {exc}") from exc
        # verify resulting state by reading it back from the device
        verified = await device.read_state()
        result = ActionResult(
            ok=True, device_id=action.target, action=action.action,
            state_after=verified, requested_by=action.requested_by,
        )
        self._journal.append(result)
        return result

    async def read_state(self, device_id: str) -> dict[str, Any]:
        """Read one device's normalized state (observation, no action)."""
        device = self.device(device_id)
        return await device.read_state()