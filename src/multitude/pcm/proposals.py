# -*- coding: utf-8 -*-
"""PCM proposal envelopes — Phase 1 component (NETWORKING_STACK.md §7).

Phase 1 wires the Phase 0 primitives into the rhizome kernel's proposal
flow:

  - ``signed_proposal_envelope`` — a ``proposal_open`` envelope carrying
    the proposal title/text, signed by the technological node.
  - ``signed_vote_envelope``     — a ``vote_cast`` envelope carrying the
    proposal id and position, signed by the voter node.
  - ``accept_proposal_envelope`` — verifies an inbound proposal envelope
    and opens it as a real proposal attributed to the sender's DID.

Proposals still go through MultitudeService.create_proposal — the kernel
gains signatures, not a new write path. The signature covers the
canonical form of the envelope; receivers verify before trusting `from`.
"""
from __future__ import annotations

from typing import Any

from multitude.pcm.envelope import Envelope, EnvelopeError
from multitude.pcm.identity import (
    Ed25519PrivateKey,
    generate_identity,
    load_identity,
    private_key_from_identity,
    pubkey_from_did,
    verify_did_binding,
)

PROTOCOL_BANNER = "PCM 1"


def _identity_for(rhizome_dir: str) -> dict:
    return generate_identity(rhizome_dir)


def _key_for(rhizome_dir: str) -> Ed25519PrivateKey:
    return private_key_from_identity(_identity_for(rhizome_dir))


def signed_proposal_envelope(rhizome_dir: str, title: str, text: str, *,
                             interface: str = "jsonl") -> dict[str, Any]:
    """Build a signed proposal_open envelope attributed to this node."""
    identity = _identity_for(rhizome_dir)
    env = Envelope.create(
        "proposal_open", identity["did"], identity["did"],
        {"title": title, "text": text},
        interface=interface,
    )
    env.sign(_key_for(rhizome_dir), identity["did"])
    return env.model_dump(by_alias=True)


def signed_vote_envelope(rhizome_dir: str, proposal_id: str, position: str, *,
                         reason: str = "", interface: str = "jsonl") -> dict[str, Any]:
    """Build a signed vote_cast envelope. position: for|against|abstain."""
    if position not in ("for", "against", "abstain"):
        raise EnvelopeError(f"bad vote position {position!r}")
    identity = _identity_for(rhizome_dir)
    env = Envelope.create(
        "vote_cast", identity["did"], identity["did"],
        {"proposal_id": proposal_id, "position": position, "reason": reason},
        interface=interface,
    )
    env.sign(_key_for(rhizome_dir), identity["did"])
    return env.model_dump(by_alias=True)


def proposal_from_envelope(envelope_dict: dict[str, Any]) -> dict[str, Any]:
    """Verify an inbound proposal envelope and return its proposal fields.

    Returns {"did": ..., "title": ..., "text": ...} after signature
    verification; raises EnvelopeError on tampering, wrong type, or a
    signing key that does not match the claimed DID.
    """
    env = Envelope.model_validate(envelope_dict)
    if env.type != "proposal_open":
        raise EnvelopeError(f"not a proposal_open envelope: {env.type!r}")
    # verify() checks the signature against the pubkey embedded in from_did;
    # a forged from_did or tampered content fails here.
    env.verify()
    verify_did_binding({
        "did": env.from_did,
        "public_key_hex": pubkey_from_did(env.from_did).hex(),
    })
    return {
        "did": env.from_did,
        "title": str(env.content.get("title", "")),
        "text": str(env.content.get("text", "")),
    }