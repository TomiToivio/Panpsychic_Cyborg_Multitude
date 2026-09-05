# -*- coding: utf-8 -*-
"""PCM node bootstrap — Phase 0 activation (NETWORKING_STACK.md §4.2).

Ties the identity, envelope and bridge modules into one call surface for
the Hermes node. Called from agent.py's command dispatch:

  - ``ensure_node_identity(tribe_dir)``  — idempotent; generates the
    node's did:key on first use, loads it afterwards.
  - ``node_status(tribe_dir)``           — identity + protocol info for
    the ``status`` command.
  - ``signed_say_envelope(...)``         — builds and signs a ``say``
    envelope for outbound delivery.

The private key never enters the event log; only public identity
material (DID, capabilities, signature) rides in payloads.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from multitude.pcm.envelope import Envelope, EnvelopeError, canonical_bytes
from multitude.pcm.identity import (
    generate_identity,
    load_identity,
    private_key_from_identity,
    verify_did_binding,
)

PROTOCOL_BANNER = "PCM 1"


def ensure_node_identity(tribe_dir: str) -> dict:
    """Generate-or-load the node identity inside the tribe directory."""
    return generate_identity(tribe_dir)


def node_status(tribe_dir: str) -> dict[str, Any]:
    """Identity + protocol status for the node's status command."""
    identity = ensure_node_identity(tribe_dir)
    return {
        "protocol": PROTOCOL_BANNER,
        "did": identity["did"],
        "algorithm": identity.get("algorithm", "ed25519"),
        "identity_created_at": identity.get("created_at", ""),
        "did_binding_ok": verify_did_binding(identity),
    }


def signed_say_envelope(tribe_dir: str, text: str, *, interface: str = "jsonl",
                        actor_kind: str = "ai",
                        capabilities: list[str] | None = None) -> dict[str, Any]:
    """Build a signed say envelope attributed to this node."""
    identity = ensure_node_identity(tribe_dir)
    env = Envelope.create(
        "say", identity["did"], identity["did"],
        {"text": text, "interface": interface},
        interface=interface, actor_kind=actor_kind,
        capabilities=capabilities or [],
    )
    env.sign(private_key_from_identity(identity), identity["did"])
    return env.model_dump(by_alias=True)


def verify_envelope_dict(envelope_dict: dict[str, Any]) -> bool:
    """Verify a wire-form envelope dict (id + signature integrity)."""
    env = Envelope.model_validate(envelope_dict)
    env.verify()
    return True