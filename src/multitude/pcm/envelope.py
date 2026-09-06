# -*- coding: utf-8 -*-
"""PCM envelope protocol — minimal signed message between nodes (Phase 0).

Implements NETWORKING_STACK.md §3. One versioned, self-describing,
transport-agnostic envelope; it rides inside fabric events, Automerge
documents, JSONL lines, or raw sockets.

Envelope shape (pcm "1"):

    {
      "pcm": "1",
      "id": "pcm_<...>",
      "type": "layer_recorded",
      "from": "did:key:z...",     sender node
      "to": "did:key:z...",       recipient node or rhizome square
      "ts": "2026-09-05T22:40:00Z",
      "interface": "jsonl",
      "actor_kind": "ai",
      "capabilities": [...],
      "content": {...},
      "sig": "ed25519:<base64>"
    }

The signature covers the canonical serialization of every field except
``sig`` itself. Canonical form: json.dumps(sorted keys, separators=(",",":"),
ensure_ascii=False) — the same canonicalization on signer and verifiers.

Rules from the spec:
1. ``type`` is a small closed vocabulary, extensible by minor version.
2. Every envelope is signed by the sender's did:key; receivers verify
   before trusting ``from``.
3. ``content.private: true`` MUST be dropped by relaying nodes unless
   explicitly authorized — privacy is enforced at the envelope level.
4. **Private data never leaves its originating node unless explicitly
   published.** ``create()`` therefore refuses to build a relayable
   envelope whose content carries the private marker — the flag is a
   construction-time guard, not an after-the-fact hope. A node that
   really intends to publish private content must strip/transform it
   first (see ``publishable_copy``).
5. **authenticated != authorized.** A valid signature proves who sent
   an envelope, never what the sender may do. Authorization is a
   separate, local decision (capabilities/permissions checked by the
   receiving node's service layer BEFORE merging or executing) — see
   ``authorize_sender``.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from multitude.pcm.identity import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
    did_from_pubkey,
    pubkey_from_did,
)

PCM_PROTOCOL_VERSION = "1"

# Closed vocabulary at Phase 0 (spec §3 rule 1).
ENVELOPE_TYPES = (
    "say",
    "layer_recorded",
    "proposal_open",
    "vote_cast",
    "counsel_request",
    "counsel_reply",
    "memory_share",
    "heartbeat",
    "capability_grant",
)

ACTOR_KINDS = ("human", "ai", "cyborg", "device", "collective", "organization")


class EnvelopeError(ValueError):
    """Malformed envelope, bad signature, or unknown type."""


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Canonical serialization the signature covers (spec §3)."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def envelope_id(canonical: bytes) -> str:
    """Deterministic, tamper-evident envelope id (content-addressed)."""
    digest = hashlib.sha256(canonical).hexdigest()[:20]
    return f"pcm_{digest}"


class Envelope(BaseModel):
    """One signed PCM message. ``sig`` signs canonical_bytes(self.model_dump(exclude={'sig'}))."""

    pcm: str = PCM_PROTOCOL_VERSION
    id: str = ""
    type: str
    from_did: str = Field(alias="from")
    to_did: str = Field(alias="to")
    ts: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    interface: str = "jsonl"
    actor_kind: str = "ai"
    capabilities: list[str] = Field(default_factory=list)
    content: dict[str, Any] = Field(default_factory=dict)
    sig: str = ""

    model_config = {"populate_by_name": True}

    # -- construction ------------------------------------------------------

    @classmethod
    def create(cls, type_: str, from_did: str, to_did: str,
               content: dict[str, Any], *, interface: str = "jsonl",
               actor_kind: str = "ai", capabilities: list[str] | None = None,
               ts: str | None = None) -> "Envelope":
        if type_ not in ENVELOPE_TYPES:
            raise EnvelopeError(
                f"unknown envelope type {type_!r}; allowed: {ENVELOPE_TYPES}")
        if actor_kind not in ACTOR_KINDS:
            raise EnvelopeError(
                f"unknown actor_kind {actor_kind!r}; allowed: {ACTOR_KINDS}")
        # Privacy invariant (spec rule 4): private content must never be
        # serialized into an outbound envelope. Fail at construction time
        # instead of trusting relays to drop it later.
        if content.get("private"):
            raise EnvelopeError(
                "refusing to build an outbound envelope with private content; "
                "private data never leaves its originating node unless explicitly "
                "published (strip or transform it first)")
        env = cls(
            type=type_, **{"from": from_did}, to=to_did, content=content,
            interface=interface, actor_kind=actor_kind,
            capabilities=capabilities or [], ts=ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        env.id = envelope_id(canonical_bytes({
            "type": env.type, "from": env.from_did, "to": env.to_did,
            "ts": env.ts, "content": env.content,
        }))
        return env

    # -- signing / verification -------------------------------------------

    def unsigned_payload(self) -> dict[str, Any]:
        data = self.model_dump(by_alias=True, exclude={"sig"})
        return data

    def sign(self, private_key: Ed25519PrivateKey, expected_did: str) -> str:
        """Sign this envelope. Raises EnvelopeError if the key does not match ``from``."""
        actual = did_from_pubkey(_pub_raw(private_key))
        if actual != self.from_did:
            raise EnvelopeError(
                f"signing key {actual} does not match envelope from {self.from_did}")
        if expected_did != self.from_did:
            raise EnvelopeError("caller-supplied expected_did does not match from")
        digest = canonical_bytes(self.unsigned_payload())
        self.sig = "ed25519:" + private_key.sign(digest).hex()
        return self.sig

    def verify(self) -> None:
        """Verify the signature against the pubkey embedded in ``from``.

        Raises EnvelopeError on any mismatch. An envelope without a sig,
        with a sig from the wrong key, or with any tampered field fails.
        """
        if not self.sig.startswith("ed25519:"):
            raise EnvelopeError("missing or malformed signature")
        try:
            pubkey = pubkey_from_did(self.from_did)
        except ValueError as e:
            raise EnvelopeError(f"bad from_did: {e}") from e
        digest = canonical_bytes(self.unsigned_payload())
        sig_bytes = bytes.fromhex(self.sig[len("ed25519:"):])
        # pubkey is raw bytes here; wrap it into a cryptography key object
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey as _Key,
        )
        key_obj = _Key.from_public_bytes(pubkey)
        try:
            key_obj.verify(sig_bytes, digest)
        except Exception as e:
            raise EnvelopeError(f"signature verification failed: {e}") from e

    # -- relay policy (spec §3 rule 3) -------------------------------------

    def relay_safe(self) -> bool:
        """False when the content is marked private (relaying nodes drop it)."""
        return not bool(self.content.get("private"))


# -- authorization (spec rule 5: authenticated != authorized) -----------------

# Capability vocabulary a node may grant/check for inbound envelopes.
# Extending this is a minor protocol change, not freeform.
KNOWN_CAPABILITIES = (
    "read_memory",       # may read shared memory
    "write_memory",      # may merge shared-memory entries into the local log
    "search_memory",     # may query the local memory index
    "summarize",
    "analyze",
    "counsel",
    "draft",
    "propose",
    "vote",
)

# Envelope types and the capability each requires to be ACCEPTED (merged/
# executed) by a receiving node. Signature verification (who sent it) is
# separate from this check (what they may do).
REQUIRED_CAPABILITY = {
    "say": None,                  # voice: authenticated membership suffices
    "layer_recorded": "write_memory",
    "proposal_open": "propose",
    "vote_cast": "vote",
    "counsel_request": None,
    "counsel_reply": "counsel",
    "memory_share": "write_memory",
    "heartbeat": None,
    "capability_grant": None,
}


def authorize_sender(envelope_dict: dict[str, Any],
                     granted_capabilities: list[str]) -> dict[str, Any]:
    """Check that a VERIFIED envelope's sender holds the capability this
    envelope type requires before the receiver merges or executes it.

    ``envelope_dict`` must already have passed Envelope.verify() — this
    function does NOT verify signatures; it only decides authorization.
    ``granted_capabilities`` is the receiver's local grant list for the
    sender's DID (e.g. from a capability_grant envelope or local policy).

    Returns the verified envelope dict on success; raises EnvelopeError
    when the envelope type requires a capability the sender lacks.
    """
    env = Envelope.model_validate(envelope_dict)
    required = REQUIRED_CAPABILITY.get(env.type, "write_memory")
    if required is None:
        return env.model_dump(by_alias=True)
    granted = {c for c in granted_capabilities if c in KNOWN_CAPABILITIES}
    if required not in granted:
        raise EnvelopeError(
            f"authorization failed: {env.type!r} requires capability "
            f"{required!r}; sender {env.from_did} holds "
            f"{sorted(granted) or 'none'} — authenticated is not authorized")
    return env.model_dump(by_alias=True)


def _pub_raw(private_key: Ed25519PrivateKey) -> bytes:
    from cryptography.hazmat.primitives import serialization
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)