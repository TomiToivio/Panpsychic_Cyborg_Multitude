"""Optional Aion J-Space adapter and self-model calibration structures.

Aion J-Space is treated as an external measurement instrument. Its layer
readouts are not beliefs, identity, phenomenology, or consciousness scores.
Nothing in this module mutates PCM memory, identity, permissions, or governance.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from . import IntrospectionFrame, IntrospectionObservation, RetentionMode


@dataclass(frozen=True)
class SelfModelCalibration:
    """Provenance-first comparison of distinct self-knowledge channels."""

    agent_id: str
    question: str
    narrative_claim: str
    external_truth: Any = None
    external_status: str = "unavailable"
    introspection: IntrospectionObservation | None = None
    intervention_result: Any = None
    status: str = "requires_followup"
    measured_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: dict[str, Any] = field(default_factory=dict)

    def as_event_payload(self) -> dict[str, Any]:
        """Return a serializable event candidate; this method performs no write."""
        return {
            "agent_id": self.agent_id,
            "question": self.question,
            "prompt_sha256": hashlib.sha256(self.question.encode()).hexdigest(),
            "narrative_claim": self.narrative_claim,
            "external_truth": self.external_truth,
            "external_status": self.external_status,
            "introspection_provider": self.introspection.provider if self.introspection else None,
            "introspection_status": self.introspection.status if self.introspection else "not_run",
            "intervention_result": self.intervention_result,
            "status": self.status,
            "measured_at": self.measured_at,
            "provenance": dict(self.provenance),
        }


def calibration_status(*, narrative_matches_truth: bool | None,
                       introspection_available: bool,
                       instrument_disagrees: bool = False) -> str:
    """Classify a discrepancy without allowing an instrument to overwrite selfhood."""
    if narrative_matches_truth is True and not instrument_disagrees:
        return "claim_supported"
    if narrative_matches_truth is False:
        return "claim_contradicted"
    if not introspection_available:
        return "instrument_inconclusive"
    if instrument_disagrees:
        return "measurement_disagreement"
    return "requires_followup"


class AionJSpaceProvider:
    """Read-only adapter for the deployment-style Aion ``POST /probe`` API."""

    def __init__(self, endpoint: str, *, timeout: float = 120.0,
                 retention: RetentionMode | str = RetentionMode.SUMMARY,
                 agent_id: str | None = None, model: str | None = None,
                 topk: int = 10) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.retention = RetentionMode(retention)
        self.agent_id = agent_id
        self.model = model
        self.topk = int(topk)

    def normalize_response(self, payload: dict[str, Any], *, prompt: str = "") -> IntrospectionObservation:
        if payload.get("error"):
            return IntrospectionObservation(
                provider="aion-jspace", status="error", error=str(payload["error"]),
                metadata={"prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()},
            )

        signature = dict(payload.get("signature") or {})
        frames: list[IntrospectionFrame] = []
        for raw_layer, candidates in (payload.get("layers") or {}).items():
            try:
                layer = int(str(raw_layer).removeprefix("L"))
            except ValueError:
                layer = None
            frame = IntrospectionFrame(
                provider="aion-jspace",
                selected_layer=layer,
                layer_candidates={str(raw_layer): candidates},
                provider_metrics={},
                model=self.model,
                agent_id=self.agent_id,
                raw={"layer": raw_layer, "candidates": candidates},
            ).retained(self.retention)
            if frame is not None:
                frames.append(frame)

        model_output = payload.get("model_output") or []
        text = str(model_output[0][0]) if model_output and isinstance(model_output[0], (list, tuple)) else ""
        metadata = {
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "source": "external-instrument",
            "epistemic_status": "measurement",
            "provider_metrics": {"signature": signature},
            "model_output": model_output if self.retention == RetentionMode.FULL else [],
        }
        return IntrospectionObservation(
            provider="aion-jspace", text=text, frames=tuple(frames), metadata=metadata,
        )

    def probe(self, prompt: str, *, system: str | None = None,
              context: dict | None = None) -> IntrospectionObservation:
        context = dict(context or {})
        body: dict[str, Any] = {"prompt": prompt, "topk": int(context.get("topk", self.topk))}
        if system:
            body["system"] = system
        req = urllib.request.Request(
            self.endpoint + "/probe",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            return IntrospectionObservation(
                provider="aion-jspace", status="unavailable", error=str(exc),
                metadata={"prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()},
            )
        return self.normalize_response(payload, prompt=prompt)

    def ask(self, prompt: str, *, context: dict | None = None) -> IntrospectionObservation:
        context = dict(context or {})
        return self.probe(prompt, system=context.pop("system", None), context=context)

    def stream(self, prompt: str, *, context: dict | None = None):
        raise NotImplementedError(
            "Aion's deployment /probe API is request/response. Use JSpaceLabProvider for live SSE streaming."
        )
