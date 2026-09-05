# -*- coding: utf-8 -*-
"""PCM semantic event model — what the data on the fabric *means*.

Zenoh carries bytes; PCM defines meaning. This module is the event
ontology of the migration spec §5: a small closed vocabulary of typed,
versioned, serializable events. It deliberately does NOT reuse Matrix
event semantics — there are no rooms, no users, no federation here.

An event is the semantic body; the signed PCM envelope (envelope.py) is
how it travels between nodes. Mapping: an event dict is carried inside
``envelope.content`` (``content.event``); the envelope stamps author
(Ed25519 did:key), timestamp, and signature around it.

Event shape (version 1)::

    {
      "version": 1,
      "type": "pcm.message",
      "author": "agent:alice",
      "timestamp": "2026-09-06T12:00:00Z",
      "subject": "pcm/agent/alice/message",
      "payload": {...},
      "references": [],
      "metadata": {}
    }

Vocabulary (16 types; extending is a minor version, not freeform):
    pcm.message, pcm.action, pcm.observation, pcm.memory,
    pcm.agent.request, pcm.agent.response, pcm.task, pcm.task.result,
    pcm.presence, pcm.identity, pcm.capability, pcm.device.state,
    pcm.device.command, pcm.sensor.reading, pcm.knowledge, pcm.resource
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator

EVENT_TYPES = (
    "pcm.message",
    "pcm.action",
    "pcm.observation",
    "pcm.memory",
    "pcm.agent.request",
    "pcm.agent.response",
    "pcm.task",
    "pcm.task.result",
    "pcm.presence",
    "pcm.identity",
    "pcm.capability",
    "pcm.device.state",
    "pcm.device.command",
    "pcm.sensor.reading",
    "pcm.knowledge",
    "pcm.resource",
)

PCM_EVENT_VERSION = 1


class EventError(ValueError):
    """Malformed PCM event."""


class PcmEvent(BaseModel):
    """One typed semantic event on the PCM fabric."""

    version: int = PCM_EVENT_VERSION
    type: str
    author: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    subject: str
    payload: dict[str, Any] = Field(default_factory=dict)
    references: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _type_in_vocabulary(cls, v: str) -> str:
        if v not in EVENT_TYPES:
            raise EventError(f"unknown event type {v!r}; allowed: {EVENT_TYPES}")
        return v

    @field_validator("author")
    @classmethod
    def _author_shape(cls, v: str) -> str:
        # "<kind>:<name>" where kind is a PCM identity kind
        if ":" not in v:
            raise EventError(f"author must be '<kind>:<name>': {v!r}")
        kind, name = v.split(":", 1)
        if kind not in IDENTITY_KINDS:
            raise EventError(f"unknown author kind {kind!r}; allowed: {IDENTITY_KINDS}")
        if not name:
            raise EventError("author name must be non-empty")
        return v

    # -- serialization -------------------------------------------------------

    def to_json(self) -> str:
        """JSON string (compact, non-ASCII preserved)."""
        return json.dumps(self.model_dump(), ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> "PcmEvent":
        try:
            return cls.model_validate(json.loads(text))
        except json.JSONDecodeError as e:
            raise EventError(f"invalid JSON: {e}") from e

    def to_envelope_content(self) -> dict[str, Any]:
        """The dict to place inside an envelope's ``content`` for transport."""
        return {"event": self.model_dump()}


def validate_payload(type_: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Minimal per-type payload validation. Returns payload or raises EventError.

    KISS: only the invariants that keep the fabric unambiguous are
    checked here; deeper validation belongs to the policy/authorization
    layer (policy.py) and to the device/agent that executes.
    """
    if type_ == "pcm.device.command":
        if "action" not in payload or "target" not in payload:
            raise EventError("pcm.device.command requires 'action' and 'target'")
        if not isinstance(payload.get("parameters", {}), dict):
            raise EventError("pcm.device.command 'parameters' must be an object")
    elif type_ == "pcm.agent.request":
        if "action" not in payload or "target" not in payload:
            raise EventError("pcm.agent.request requires 'action' and 'target'")
    elif type_ == "pcm.sensor.reading":
        if "value" not in payload:
            raise EventError("pcm.sensor.reading requires 'value'")
    elif type_ == "pcm.resource":
        for field in ("hash", "mime", "location"):
            if field not in payload:
                raise EventError(f"pcm.resource requires {field!r}")
    elif type_ == "pcm.capability":
        if "capabilities" not in payload or not isinstance(payload["capabilities"], list):
            raise EventError("pcm.capability requires a 'capabilities' list")
    return payload


def create_event(type_: str, author: str, subject: str,
                 payload: dict[str, Any] | None = None, *,
                 references: list[dict[str, Any]] | None = None,
                 metadata: dict[str, Any] | None = None,
                 timestamp: str | None = None) -> PcmEvent:
    """Build a validated event in one call. Always raises EventError
    (never pydantic's ValidationError) on malformed input."""
    try:
        event = PcmEvent(
            type=type_, author=author, subject=subject,
            payload=payload or {}, references=references or [],
            metadata=metadata or {},
            timestamp=timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
    except Exception as e:
        raise EventError(str(e)) from e
    validate_payload(event.type, event.payload)
    return event


# -- identity model (spec §6) -----------------------------------------------

IDENTITY_KINDS = (
    "human",
    "agent",
    "service",
    "device",
    "sensor",
    "gateway",
    "robot",
    "drone",
)


class PcmIdentity(BaseModel):
    """A stable PCM semantic identity, independent of the transport.

    The Zenoh session has no identity of its own beyond reachability;
    PCM identity is ``<kind>:<name>`` plus (optionally) a did:key that
    binds the semantic identity to a signing key.
    """

    kind: str
    name: str
    did: str = ""          # did:key:z... when cryptographically bound
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("kind")
    @classmethod
    def _kind_valid(cls, v: str) -> str:
        if v not in IDENTITY_KINDS:
            raise EventError(f"unknown identity kind {v!r}; allowed: {IDENTITY_KINDS}")
        return v

    @property
    def pcm_id(self) -> str:
        return f"{self.kind}:{self.name}"

    @classmethod
    def parse(cls, pcm_id: str) -> "PcmIdentity":
        if ":" not in pcm_id:
            raise EventError(f"pcm id must be '<kind>:<name>': {pcm_id!r}")
        kind, name = pcm_id.split(":", 1)
        return cls(kind=kind, name=name)

    @classmethod
    def check(cls, **kwargs: Any) -> "PcmIdentity":
        """Public constructor: always raises EventError, never pydantic's
        ValidationError, on malformed input."""
        try:
            return cls(**kwargs)
        except Exception as e:
            raise EventError(str(e)) from e


__all__ = [
    "EVENT_TYPES",
    "PCM_EVENT_VERSION",
    "EventError",
    "PcmEvent",
    "PcmIdentity",
    "IDENTITY_KINDS",
    "validate_payload",
    "create_event",
]