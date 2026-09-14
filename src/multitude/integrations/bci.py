# -*- coding: utf-8 -*-
"""Optional BCI / biosignal adapter layer (issues #10 and #41).

A thin, OPTIONAL interface between a biological human member and the
wider PCM assemblage. The kernel has no dependency on this module;
adapters produce observations that a human member may explicitly
publish into rhizome memory via ``Rhizome.record_biometric_signal``.

Privacy model (non-negotiable):

* Raw EEG / raw biosignal streams NEVER leave the adapter. Only
  derived context (``BCIObservation``) is ever produced.
* Observations are private by default: nothing is shared, published,
  or recorded in the rhizome unless the human member explicitly
  publishes that observation.
* AI agents cannot enable monitoring or change consent settings;
  the adapter ignores any such request (see ``BCIHub``).
* No medical diagnosis. No claim that any signal measures
  consciousness. Support UNKNOWN / low-confidence rather than
  inventing certainty.

Adversarial-security model (issue #41):

* Passive observations are context only and can never silently become
  commands, regardless of confidence.
* Intentional commands use a separate ``BCICommand`` type and must pass
  a local freshness/replay/provenance gate before downstream handling.
* Passing the BCI gate does NOT authorize an action; ordinary PCM
  capability/policy checks remain mandatory for devices/governance.
* ``BCICommandDispatcher`` is a narrow fail-closed bridge from validated
  BCI intent into the existing ``PhysicalAgency`` authorization chain.
* Real BCI traffic remains behind the Phase 3b confidentiality gate.

Mapping to PCM's six-layer model: observations carry a ``layer``
field restricted to ``biological`` (sleep/wake, heart rate, HRV),
``psychic`` (attention, relaxation/arousal estimates) and
``cybernetic`` (device status, simple user-triggered BCI events).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from multitude.integrations.embodiment import DeviceAction, PhysicalAgency

BCI_LAYERS = frozenset({"biological", "psychic", "cybernetic"})
DEFAULT_SENSITIVITY = "private"


class BCIError(Exception):
    """Invalid BCI observation, adapter misuse, or consent violation."""


class BCISecurityError(BCIError):
    """A BCI event failed the adversarial freshness/replay/authority gate."""


def _parse_utc_timestamp(value: str) -> datetime:
    raw = str(value).strip()
    if not raw:
        raise BCISecurityError("BCI event needs a non-empty timestamp")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise BCISecurityError(f"BCI event timestamp is not valid ISO-8601: {value!r}") from exc
    if parsed.tzinfo is None:
        raise BCISecurityError("BCI event timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class BCIObservation:
    """One derived context reading. This is the ONLY thing an adapter emits."""

    ts: str
    signal_type: str
    value: Any
    unit: str = ""
    confidence: float = 0.0
    source: str = "bci"
    layer: str = "biological"
    sensitivity: str = DEFAULT_SENSITIVITY
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.layer not in BCI_LAYERS:
            raise BCIError(
                f"BCI observation layer must be one of {sorted(BCI_LAYERS)}, got '{self.layer}'"
            )
        if not self.signal_type or not self.signal_type.strip():
            raise BCIError("BCI observation needs a non-empty signal_type")
        if not str(self.ts).strip():
            raise BCIError("BCI observation needs a non-empty timestamp (provenance)")
        conf = float(self.confidence)
        if math.isnan(conf) or not (0.0 <= conf <= 1.0):
            raise BCIError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        if self.sensitivity not in {"private", "limited", "shared"}:
            raise BCIError(
                f"sensitivity must be private, limited, or shared, got '{self.sensitivity}'"
            )

    def to_payload(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "signal_type": self.signal_type.strip().lower(),
            "value": self.value,
            "unit": self.unit,
            "confidence": float(self.confidence),
            "source": self.source,
            "layer": self.layer,
            "sensitivity": self.sensitivity,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class BCICommand:
    """Explicit low-bandwidth human-intent claim from a BCI adapter."""

    ts: str
    command: str
    event_id: str
    source: str
    intentional: bool = True
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.command).strip():
            raise BCISecurityError("BCI command needs a non-empty command")
        if not str(self.event_id).strip():
            raise BCISecurityError("BCI command needs a non-empty event_id")
        if not str(self.source).strip():
            raise BCISecurityError("BCI command needs non-empty source provenance")
        if self.intentional is not True:
            raise BCISecurityError("BCI command must be explicitly marked intentional=True")
        conf = float(self.confidence)
        if math.isnan(conf) or not (0.0 <= conf <= 1.0):
            raise BCISecurityError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        _parse_utc_timestamp(self.ts)


class BCISecurityGate:
    """Local replay/freshness gate for intentional BCI commands."""

    def __init__(self, *, max_age_seconds: float = 10.0, max_future_skew_seconds: float = 2.0) -> None:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be > 0")
        if max_future_skew_seconds < 0:
            raise ValueError("max_future_skew_seconds must be >= 0")
        self.max_age_seconds = float(max_age_seconds)
        self.max_future_skew_seconds = float(max_future_skew_seconds)
        self._seen_event_ids: set[str] = set()

    def validate_command(self, command: BCICommand, *, now: Optional[datetime] = None) -> BCICommand:
        if not isinstance(command, BCICommand):
            raise BCISecurityError("passive BCI observations cannot be validated as intentional commands")
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        current = current.astimezone(timezone.utc)
        event_time = _parse_utc_timestamp(command.ts)
        age = (current - event_time).total_seconds()
        if age > self.max_age_seconds:
            raise BCISecurityError(
                f"stale BCI command rejected: age {age:.3f}s exceeds {self.max_age_seconds:.3f}s"
            )
        if age < -self.max_future_skew_seconds:
            raise BCISecurityError(
                f"future-dated BCI command rejected: skew {-age:.3f}s exceeds "
                f"{self.max_future_skew_seconds:.3f}s"
            )
        if command.event_id in self._seen_event_ids:
            raise BCISecurityError(f"replayed BCI command rejected: event_id={command.event_id!r}")
        provenance = command.metadata.get("provenance")
        if provenance is not None and not isinstance(provenance, dict):
            raise BCISecurityError("BCI command provenance metadata must be a dict when present")
        self._seen_event_ids.add(command.event_id)
        return command

    def reset_replay_cache(self) -> None:
        self._seen_event_ids.clear()


class BCICommandDispatcher:
    """Fail-closed bridge from validated BCI intent to physical agency.

    Commands are first checked for freshness/replay/provenance, then translated
    into an ordinary ``DeviceAction``. Authorization is delegated to
    ``PhysicalAgency.execute`` so BCI input cannot bypass the device capability
    allowlist or PCM policy decision path.
    """

    def __init__(self, *, gate: BCISecurityGate, physical_agency: PhysicalAgency) -> None:
        self._gate = gate
        self._physical_agency = physical_agency

    async def dispatch_device_command(
        self,
        command: BCICommand,
        *,
        requested_by: str,
        target: str,
        action: str,
        parameters: Optional[dict[str, Any]] = None,
        now: Optional[datetime] = None,
    ) -> Any:
        validated = self._gate.validate_command(command, now=now)
        if not str(requested_by).strip():
            raise BCISecurityError("BCI command dispatch requires an explicit biological requester")
        device_action = DeviceAction(
            action=str(action).strip(),
            target=str(target).strip(),
            parameters=dict(parameters or {}),
            requested_by=str(requested_by).strip(),
        )
        result = await self._physical_agency.execute(device_action)
        return {
            "result": result,
            "bci_event_id": validated.event_id,
            "bci_source": validated.source,
            "bci_confidence": validated.confidence,
            "authority": "policy_checked_device_action",
        }


def normalize_observation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise BCIError("observation payload must be a dict")
    ts = str(payload.get("ts", "")).strip()
    if not ts:
        raise BCIError("observation needs a timestamp")
    signal = str(payload.get("signal_type", "")).strip().lower()
    if not signal:
        raise BCIError("observation needs a non-empty signal_type")
    layer = str(payload.get("layer", "biological")).strip().lower()
    if layer not in BCI_LAYERS:
        raise BCIError(f"unknown BCI layer '{layer}'")
    conf = payload.get("confidence", 0.0)
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        raise BCIError(f"confidence must be a number, got {conf!r}")
    if math.isnan(conf) or not (0.0 <= conf <= 1.0):
        raise BCIError(f"confidence must be in [0.0, 1.0], got {conf}")
    sensitivity = str(payload.get("sensitivity", DEFAULT_SENSITIVITY)).strip().lower()
    if sensitivity not in {"private", "limited", "shared"}:
        raise BCIError(f"invalid sensitivity '{sensitivity}'")
    return {
        "ts": ts,
        "signal_type": signal,
        "value": payload.get("value", "UNKNOWN"),
        "unit": str(payload.get("unit", "")).strip(),
        "confidence": conf,
        "source": str(payload.get("source", "bci")).strip() or "bci",
        "layer": layer,
        "sensitivity": sensitivity,
        "metadata": dict(payload.get("metadata") or {}),
    }


class BCIAdapter:
    name: str = "generic-bci"

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = bool(enabled)

    def read_context(self) -> list[BCIObservation]:
        if not self.enabled:
            return []
        return self._read()

    def _read(self) -> list[BCIObservation]:
        raise NotImplementedError

    def _observation(
        self,
        *,
        ts: str,
        signal_type: str,
        value: Any,
        unit: str = "",
        confidence: float = 0.0,
        layer: str = "biological",
        metadata: Optional[dict[str, Any]] = None,
    ) -> BCIObservation:
        return BCIObservation(
            ts=ts,
            signal_type=signal_type,
            value=value,
            unit=unit,
            confidence=confidence,
            source=self.name,
            layer=layer,
            metadata=metadata or {},
        )


class SyntheticBCIAdapter(BCIAdapter):
    name = "synthetic-bci"

    def __init__(self, enabled: bool = False, script: Optional[list[dict[str, Any]]] = None) -> None:
        super().__init__(enabled=enabled)
        self._script = list(script or [])
        self._cursor = 0

    def _read(self) -> list[BCIObservation]:
        if self._cursor >= len(self._script):
            return []
        step = self._script[self._cursor]
        self._cursor += 1
        return [self._observation(**step)]


class BCIHub:
    def __init__(self, rhizome: Any) -> None:
        self._rhizome = rhizome
        self._adapters: dict[str, BCIAdapter] = {}
        self._latest: dict[str, list[BCIObservation]] = {}

    def add_adapter(self, name: str, adapter: BCIAdapter, *, by: str) -> None:
        self._require_human(by, "add a BCI adapter")
        self._adapters[name] = adapter

    def enable(self, name: str, *, by: str) -> None:
        self._require_human(by, "enable BCI monitoring")
        adapter = self._adapters.get(name)
        if adapter is None:
            raise BCIError(f"no BCI adapter '{name}'")
        adapter.enabled = True

    def disable(self, name: str, *, by: str) -> None:
        self._require_human(by, "disable BCI monitoring")
        adapter = self._adapters.get(name)
        if adapter is None:
            raise BCIError(f"no BCI adapter '{name}'")
        adapter.enabled = False

    def read_context(self, name: str, *, by: str) -> list[BCIObservation]:
        self._require_human(by, "read BCI context")
        adapter = self._adapters.get(name)
        if adapter is None:
            raise BCIError(f"no BCI adapter '{name}'")
        observations = adapter.read_context()
        if observations:
            self._latest[name] = observations
        return observations

    def latest(self, name: str) -> list[BCIObservation]:
        return list(self._latest.get(name, []))

    def publish(
        self,
        name: str,
        observation: BCIObservation,
        *,
        by: str,
        sensitivity: Optional[str] = None,
    ) -> dict[str, Any]:
        self._require_human(by, "publish BCI observations")
        if not isinstance(observation, BCIObservation):
            raise BCIError("BCIHub.publish accepts passive BCIObservation objects only")
        if name not in self._adapters:
            raise BCIError(f"no BCI adapter '{name}'")
        payload = normalize_observation_payload(observation.to_payload())
        if sensitivity is not None:
            sensitivity = sensitivity.strip().lower()
            if sensitivity not in {"private", "limited", "shared"}:
                raise BCIError(f"invalid sensitivity '{sensitivity}'")
            payload["sensitivity"] = sensitivity
        sensitive_markers = (
            "attention", "valence", "sleep", "stress", "fatigue", "hrv",
            "heart", "brain", "bci", "neural", "cognitive", "awareness",
            "focus", "mood", "emotion", "alertness", "drowsiness", "eeg",
            "calm", "arousal",
        )
        if (
            payload["sensitivity"] == "shared"
            and any(m in payload["signal_type"] for m in sensitive_markers)
        ):
            raise BCIError(
                "sensitive signals cannot be published as shared; use private or limited"
            )
        rec = self._rhizome.record_biometric_signal(
            member=by,
            signal_type=payload["signal_type"],
            value=payload["value"],
            unit=payload["unit"],
            source=payload["source"],
            sensitivity=payload["sensitivity"],
            consent_required=True,
            meta={
                **payload["metadata"],
                "confidence": payload["confidence"],
                "layer": payload["layer"],
                "bci_adapter": name,
                "authority": "passive_context_only",
            },
        )
        return rec.model_dump()

    def _require_human(self, by: str, action: str) -> Any:
        member = self._rhizome.member_by_name(by)
        if member is None:
            raise BCIError(f"unknown member '{by}'")
        kind = getattr(member, "kind", None)
        kind_value = getattr(kind, "value", kind)
        if kind_value != "biological":
            raise BCIError(
                f"only a biological human member may {action}; "
                f"'{by}' is '{kind_value}' (AI agents cannot change consent settings)"
            )
        return member
