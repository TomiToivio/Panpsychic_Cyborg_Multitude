# -*- coding: utf-8 -*-
"""Memory mirror — Phase 3 first slice (NETWORKING_STACK.md §12).

Mirrors a node's personal memory (``IndividualMemoryStore``-shaped JSON)
into a CRDT-friendly, mergeable document and syncs it over the PCM
fabric as signed envelopes. Roadmap line being implemented:

    Phase 3 — two+ nodes end-to-end: signed envelopes over the fabric,
              automerge memory mirror, VC capability grants

Design decisions (spec-aligned):

- **events.jsonl stays authoritative.** The mirror is a *cache/sync
  medium*, exactly as the roadmap's risk mitigation states: conflicts
  surface as new events, never silent overwrites. The mirror carries
  the *last-writer-wins* projection of each memory field; the audit
  trail remains the rhizome log.
- **Automerge is optional, not required.** automerge-py is stale on
  PyPI (0.1.2, 2022 — verified 2026-09-05). The mirror therefore uses
  a plain JSON *merge document* with per-field LWW registers keyed by
  (lamport, did) — the same semantics Automerge gives, small enough
  to implement correctly in stdlib. An Automerge sidecar can replace
  the codec later without changing the wire shape.
- **Sync rides the signed envelope.** Two nodes exchange
  ``memory_share`` envelopes on their direct keys; the receiver merges
  only VERIFIED envelopes (edge verification is the transport's job —
  the mirror trusts the verified dict it receives).
- **Lamport clocks, not wall clocks.** Each field update bumps the
  node's counter; ties break on did:key (total order, deterministic
  on both sides).
- **privacy flag survives merging but not relaying**: fields with
  ``private: true`` are marked in the merge doc and dropped by the
  relay rule (envelope rule 3) when the envelope is forwarded.

Public surface:

    MemoryMirror          — one node's mergeable memory document
    MemorySyncAdapter     — fabric glue: publish/subscribe sync
    merge_memory_docs     — pure function: merge two docs
"""
from __future__ import annotations

import json
from collections.abc import Callable, Collection
from datetime import datetime, timezone
from typing import Any

from multitude.pcm.envelope import Envelope, EnvelopeError, authorize_sender
from multitude.pcm.identity import Ed25519PrivateKey

MIRROR_SCHEMA = "pcm.memory-mirror/1"
DEFAULT_RHIZOME_SQUARE = "pcm/memory/shared/event"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def merge_memory_docs(local: dict[str, Any], remote: dict[str, Any]) -> dict[str, Any]:
    """Merge two memory-mirror documents (pure function).

    Per-field last-writer-wins on (lamport, did) — deterministic on
    both sides. Facts/notes/skills/preferences are field-collections;
    each entry carries its own register (lamport, did, value).
    """
    if local.get("schema") != remote.get("schema"):
        raise ValueError(
            f"schema mismatch: {local.get('schema')!r} vs {remote.get('schema')!r}")

    def merge_field(a: dict, b: dict) -> dict:
        out = dict(a)
        for k, rb in b.items():
            ra = a.get(k)
            if not isinstance(ra, dict) or "lamport" not in ra:
                out[k] = rb
                continue
            if (rb["lamport"], rb.get("did", "")) > (ra["lamport"], ra.get("did", "")):
                out[k] = rb
        return out

    merged = {
        "schema": MIRROR_SCHEMA,
        "did": local.get("did") or remote.get("did"),
        "lamport": max(local.get("lamport", 0), remote.get("lamport", 0)),
        "fields": {},
    }
    for field in ("facts", "notes", "skills", "preferences"):
        merged["fields"][field] = merge_field(
            (local.get("fields") or {}).get(field, {}),
            (remote.get("fields") or {}).get(field, {}),
        )
    return merged


class MemoryMirror:
    """One node's mergeable personal-memory document.

    Wraps the IndividualMemoryStore shape (facts/notes/skills/
    preferences) with per-entry LWW registers and a Lamport clock.
    """

    def __init__(self, did: str) -> None:
        self.did = did
        self.lamport = 0
        # fields: {"facts": {key: register}, "notes": {i: register}, ...}
        self.fields: dict[str, dict[str, dict[str, Any]]] = {
            "facts": {}, "notes": {}, "skills": {}, "preferences": {},
        }

    # -- build from existing store ----------------------------------------

    @classmethod
    def from_memory_dict(cls, did: str, memory: dict[str, Any]) -> "MemoryMirror":
        m = cls(did)
        for field in ("facts", "notes", "skills", "preferences"):
            value = memory.get(field)
            if isinstance(value, dict):
                for k, v in value.items():
                    m.set(field, k, v)
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    m.set(field, str(i), v)
        return m

    # -- mutation -----------------------------------------------------------

    def set(self, field: str, key: str, value: Any,
            *, private: bool = False) -> None:
        if field not in self.fields:
            raise ValueError(f"unknown mirror field {field!r}")
        self.lamport += 1
        self.fields[field][key] = {
            "lamport": self.lamport,
            "did": self.did,
            "ts": _now(),
            "private": private,
            "value": value,
        }

    def to_document(self, *, include_private: bool = True) -> dict[str, Any]:
        """Return the merge document, optionally omitting private registers.

        include_private=False is mandatory at transport boundaries: the
        marker is local metadata, not permission to serialize the value and
        hope that a later relay drops it.
        """
        fields = {
            field: {
                key: register
                for key, register in entries.items()
                if include_private or not register.get("private")
            }
            for field, entries in self.fields.items()
        }
        return {
            "schema": MIRROR_SCHEMA,
            "did": self.did,
            "lamport": self.lamport,
            "fields": json.loads(json.dumps(fields, ensure_ascii=False)),
        }

    def apply_document(self, doc: dict[str, Any]) -> bool:
        """Merge a remote document in. Returns True when state changed."""
        before = json.dumps(self.to_document(), sort_keys=True)
        merged = merge_memory_docs(self.to_document(), doc)
        self.fields = merged["fields"]
        self.lamport = max(self.lamport, merged["lamport"])
        after = json.dumps(json.loads(json.dumps(self.to_document())), sort_keys=True)
        return before != after

    # -- view ---------------------------------------------------------------

    def as_memory_dict(self, include_private: bool = True) -> dict[str, Any]:
        """Project back to the IndividualMemoryStore shape."""
        out: dict[str, Any] = {}
        for field, entries in self.fields.items():
            values = []
            if field in ("facts", "preferences"):
                d = {}
                for k, reg in entries.items():
                    if reg.get("private") and not include_private:
                        continue
                    d[k] = reg["value"]
                out[field] = d
            else:
                for reg in entries.values():
                    if reg.get("private") and not include_private:
                        continue
                    values.append(reg["value"])
                out[field] = values
        return out


class MemorySync:
    """Sync glue between a MemoryMirror and a PCM Transport (ABC).

    Publishes the mirror as a signed ``memory_share`` envelope on the
    rhizome square on ``push()``; applies VERIFIED inbound
    ``memory_share`` envelopes for the same did on ``handle()``.
    """

    def __init__(
        self,
        transport,
        did: str,
        private_key: Ed25519PrivateKey,
        topic: str = DEFAULT_RHIZOME_SQUARE,
        capabilities_for_sender: Callable[[str], Collection[str]] | None = None,
    ) -> None:
        from multitude.pcm.transport import Transport  # noqa: F401  type check
        if not isinstance(transport, Transport):
            raise TypeError("transport must implement pcm.transport.Transport")
        self.transport = transport
        self.did = did
        self.private_key = private_key
        self.topic = topic
        # Signature verification authenticates a sender; the receiver's local
        # grant resolver authorizes it. No resolver means no inbound rights.
        self._capabilities_for_sender = (
            capabilities_for_sender or (lambda _did: ())
        )
        self._remote_lamport = 0

    async def push(self, mirror: MemoryMirror) -> str:
        """Sign and publish the current mirror document."""
        env = Envelope.create(
            "memory_share", self.did, self.did,  # to: rhizome square broadcast
            {"mirror": mirror.to_document(include_private=False)},
            interface="pcm.transport",
        )
        env.sign(self.private_key, self.did)
        await self.transport.publish(self.topic, env.model_dump(by_alias=True))
        return env.id

    async def handle(self, envelope_dict: dict[str, Any],
                     mirror: MemoryMirror) -> bool:
        """Verify an inbound envelope and merge its mirror. Returns True
        when the local mirror changed. Unverified envelopes raise."""
        from multitude.pcm.envelope import Envelope as _E
        env = _E.model_validate(envelope_dict)
        env.verify()
        if env.type != "memory_share":
            raise EnvelopeError(
                f"expected memory_share envelope, got {env.type!r}"
            )
        authorize_sender(
            env.model_dump(by_alias=True),
            list(self._capabilities_for_sender(env.from_did)),
        content = env.content or {}
        remote = content.get("mirror") or {}
        if remote.get("did") != env.from_did:
            raise ValueError("mirror did does not match envelope from_did")
        changed = mirror.apply_document(remote)
        if changed:
            self._remote_lamport = max(self._remote_lamport,
                                       remote.get("lamport", 0))
        return changed

    async def subscribe(self, mirror: MemoryMirror) -> Any:
        """Subscribe the square; verified memory_share envelopes merge."""
        async def _on_event(event: dict[str, Any], topic: str) -> None:
            if event.get("type") != "memory_share":
                return
            try:
                await self.handle(event, mirror)
            except Exception:
                return  # unverified or malformed: dropped
        return await self.transport.subscribe(self.topic, _on_event)


__all__ = [
    "MIRROR_SCHEMA",
    "MemoryMirror",
    "MemorySync",
    "merge_memory_docs",
]