"""Optional read-only model instrumentation and self-knowledge evaluation for PCM."""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Iterator, Protocol


class RetentionMode(str, Enum):
    NONE = "none"
    SUMMARY = "summary"
    FULL = "full"


@dataclass(frozen=True)
class IntrospectionFrame:
    provider: str
    token_index: int | None = None
    emitted_token: str | None = None
    selected_layer: int | None = None
    layer_candidates: dict[str, Any] = field(default_factory=dict)
    provider_metrics: dict[str, Any] = field(default_factory=dict)
    flags: tuple[str, ...] = ()
    model: str | None = None
    agent_id: str | None = None
    raw: dict[str, Any] | None = None

    def retained(self, mode: RetentionMode) -> "IntrospectionFrame | None":
        if mode == RetentionMode.NONE:
            return None
        if mode == RetentionMode.FULL:
            return self
        return IntrospectionFrame(
            provider=self.provider,
            token_index=self.token_index,
            emitted_token=self.emitted_token,
            selected_layer=self.selected_layer,
            provider_metrics=dict(self.provider_metrics),
            flags=self.flags,
            model=self.model,
            agent_id=self.agent_id,
        )


@dataclass(frozen=True)
class IntrospectionObservation:
    provider: str
    text: str = ""
    frames: tuple[IntrospectionFrame, ...] = ()
    status: str = "ok"
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LiveIntrospectionProvider(Protocol):
    def ask(self, prompt: str, *, context: dict | None = None) -> IntrospectionObservation: ...
    def stream(self, prompt: str, *, context: dict | None = None) -> Iterable[IntrospectionFrame]: ...


class JSpaceLabError(RuntimeError):
    pass


def parse_sse_blocks(chunks: Iterable[bytes | str]) -> Iterator[dict[str, Any]]:
    buf = ""
    for chunk in chunks:
        buf += chunk.decode(errors="replace") if isinstance(chunk, bytes) else chunk
        while "\n\n" in buf:
            block, buf = buf.split("\n\n", 1)
            lines = [line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")]
            if lines:
                yield json.loads("\n".join(lines))


class JSpaceLabProvider:
    """Thin read-only HTTP/SSE adapter. It grants no PCM authority."""

    def __init__(self, endpoint: str, *, timeout: float = 30.0,
                 retention: RetentionMode | str = RetentionMode.SUMMARY,
                 agent_id: str | None = None, model: str | None = None) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.retention = RetentionMode(retention)
        self.agent_id = agent_id
        self.model = model

    def normalize_event(self, event: dict[str, Any]) -> IntrospectionFrame | None:
        metrics = {k: event[k] for k in (
            "engagement_score", "concept_mass", "deflection_top", "engagement_onset_layer"
        ) if k in event}
        flags = ("provider:veto",) if event.get("veto") or event.get("is_veto") else ()
        frame = IntrospectionFrame(
            provider="jspace-lab",
            token_index=event.get("token_index", event.get("step")),
            emitted_token=event.get("emitted_token", event.get("text") if event.get("type") == "token" else None),
            selected_layer=event.get("selected_layer", event.get("veto_layer")),
            layer_candidates=event.get("layers", event.get("layer_candidates", {})) or {},
            provider_metrics=metrics,
            flags=flags,
            model=event.get("model", self.model),
            agent_id=self.agent_id,
            raw=dict(event),
        )
        return frame.retained(self.retention)

    def stream_events(self, chunks: Iterable[bytes | str]) -> Iterator[IntrospectionFrame]:
        for event in parse_sse_blocks(chunks):
            if event.get("type") in {"token", "lens", "frame"}:
                frame = self.normalize_event(event)
                if frame is not None:
                    yield frame

    def ask(self, prompt: str, *, context: dict | None = None) -> IntrospectionObservation:
        context = dict(context or {})
        payload = {"prompt": prompt, **{k: v for k, v in context.items() if k in {"lens_run", "lens_step", "identity", "max_new"}}}
        req = urllib.request.Request(
            self.endpoint + "/api/ask",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        )
        text: list[str] = []
        frames: list[IntrospectionFrame] = []
        meta = {"prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}
        try:
            response = urllib.request.urlopen(req, timeout=self.timeout)
            with response:
                def chunks():
                    while True:
                        part = response.read(4096)
                        if not part:
                            break
                        yield part
                for event in parse_sse_blocks(chunks()):
                    kind = event.get("type")
                    if kind == "ask_token":
                        text.append(str(event.get("text", "")))
                    elif kind in {"token", "lens", "frame"}:
                        frame = self.normalize_event(event)
                        if frame is not None:
                            frames.append(frame)
                    elif kind == "error":
                        return IntrospectionObservation("jspace-lab", "".join(text), tuple(frames), "error", str(event.get("error", "provider error")), meta)
                    elif kind == "ask_done":
                        meta["ask_done"] = True
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            return IntrospectionObservation("jspace-lab", status="unavailable", error=str(exc), metadata=meta)
        return IntrospectionObservation("jspace-lab", "".join(text), tuple(frames), metadata=meta)

    def stream(self, prompt: str, *, context: dict | None = None) -> Iterable[IntrospectionFrame]:
        raise JSpaceLabError("Use stream_events() with the upstream live SSE stream; ASK mode is implemented by ask().")


from .benchmark import (  # noqa: E402
    CalibrationResult,
    CallableRespondent,
    GroundTruthObservation,
    GroundTruthProvider,
    HermesRespondent,
    MappingGroundTruthProvider,
    PCMRuntimeGroundTruthProvider,
    PCM_QUESTION_BANK,
    SelfKnowledgeBenchmark,
    SelfKnowledgeProbe,
    SelfKnowledgeRespondent,
    grade_claim,
)

__all__ = [
    "IntrospectionFrame",
    "IntrospectionObservation",
    "RetentionMode",
    "LiveIntrospectionProvider",
    "JSpaceLabProvider",
    "JSpaceLabError",
    "parse_sse_blocks",
    "CalibrationResult",
    "CallableRespondent",
    "GroundTruthObservation",
    "GroundTruthProvider",
    "HermesRespondent",
    "MappingGroundTruthProvider",
    "PCMRuntimeGroundTruthProvider",
    "PCM_QUESTION_BANK",
    "SelfKnowledgeBenchmark",
    "SelfKnowledgeProbe",
    "SelfKnowledgeRespondent",
    "grade_claim",
]
