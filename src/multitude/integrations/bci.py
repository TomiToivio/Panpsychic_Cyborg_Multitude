# -*- coding: utf-8 -*-
"""Optional BCI / biosignal adapter layer (issue #10).

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

Mapping to PCM's six-layer model: observations carry a ``layer``
field restricted to ``biological`` (sleep/wake, heart rate, HRV),
``psychic`` (attention, relaxation/arousal estimates) and
``cybernetic`` (device status, simple user-triggered BCI events).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

# Layers a BCI observation may target (never physical/social/linguistic).
BCI_LAYERS = frozenset({"biological", "psychic", "cybernetic"})

# Signals considered sensitive regardless of name (fail-closed default).
DEFAULT_SENSITIVITY = "private"


class BCIError(Exception):
    """Invalid BCI observation, adapter misuse, or consent violation."""


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
        # discipline: observations are private unless explicitly widened later
        # by a human member at publish time.
        if self.sensitivity not in {"private", "limited", "shared"}:
            raise BCIError(
                f"sensitivity must be private, limited, or shared, got '{self.sensitivity}'"
            )

    def to_payload(self) -> dict[str, Any]:
        """Plain payload (for tests, adapters, and explicit publishing)."""
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


def normalize_observation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate + normalize a raw payload into a publishable observation dict.

    Raises BCIError on malformed input. UNKNOWN values are preserved:
    a device that cannot classify (e.g. sleep state UNKNOWN) is reported
    as UNKNOWN, never guessed.
    """
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
    """Minimal contract for device-specific adapters.

    Subclasses produce observations from their device; ``read_context``
    returns derived context ONLY (never raw signals). ``enabled=False``
    makes the adapter inert: every read returns an empty list.
    """

    name: str = "generic-bci"

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = bool(enabled)

    def read_context(self) -> list[BCIObservation]:
        """Return current derived context. Empty when disabled."""
        if not self.enabled:
            return []
        return self._read()

    def _read(self) -> list[BCIObservation]:  # pragma: no cover - interface
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
    """Reference adapter for tests and demos. No hardware, ever.

    Emits deterministic (or seeded) synthetic observations so the whole
    pipeline is exercisable without a device.
    """

    name = "synthetic-bci"

    def __init__(
        self,
        enabled: bool = False,
        script: Optional[list[dict[str, Any]]] = None,
    ) -> None:
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
    """Per-member BCI integration point. Consent guard, not a recorder.

    - ``enable``/``disable`` are consent acts: ``by`` must name a
      BIOLOGICAL member of the rhizome. Technological (AI) members are
      refused by default: AI agents cannot enable monitoring on a human.
    - Observations stay in the hub. Nothing reaches the rhizome until a
      human calls ``publish`` for that observation.
    """

    def __init__(self, rhizome: Any) -> None:
        self._rhizome = rhizome
        self._adapters: dict[str, BCIAdapter] = {}
        self._latest: dict[str, list[BCIObservation]] = {}

    # ------------------------------------------------------------ consent
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

    # ------------------------------------------------------------- reads
    def read_context(self, name: str, *, by: str) -> list[BCIObservation]:
        """Poll one adapter; results stay private in the hub."""
        self._require_human(by, "read BCI context")
        adapter = self._adapters.get(name)
        if adapter is None:
            raise BCIError(f"no BCI adapter '{name}'")
        observations = adapter.read_context()
        if observations:
            self._latest[name] = observations
        return observations

    def latest(self, name: str) -> list[BCIObservation]:
        """Last read observations for an adapter (private, not shared)."""
        return list(self._latest.get(name, []))

    # ---------------------------------------------------------- publishing
    def publish(
        self,
        name: str,
        observation: BCIObservation,
        *,
        by: str,
        sensitivity: Optional[str] = None,
    ) -> dict[str, Any]:
        """Explicitly publish ONE observation into rhizome memory.

        The publishing member must be the biological human the
        observation belongs to. Sensitivity can only be widened from
        private by this explicit call; the kernel-side consent checks
        still apply (record_biometric_signal re-validates).
        """
        self._require_human(by, "publish BCI observations")
        if name not in self._adapters:
            raise BCIError(f"no BCI adapter '{name}'")
        payload = normalize_observation_payload(observation.to_payload())
        if sensitivity is not None:
            sensitivity = sensitivity.strip().lower()
            if sensitivity not in {"private", "limited", "shared"}:
                raise BCIError(f"invalid sensitivity '{sensitivity}'")
            payload["sensitivity"] = sensitivity
        # The kernel re-checks consent for sensitive signals; a shared
        # sensitivity with a sensitive signal raises there. We surface
        # the same discipline here with a clear message:
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
            },
        )
        return rec.model_dump()

    # ------------------------------------------------------------ internals
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