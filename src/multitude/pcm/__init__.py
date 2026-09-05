# -*- coding: utf-8 -*-
"""PCM protocol package — Phase 0 of the PCM networking stack.

Per NETWORKING_STACK.md: node identity (did:key) and the minimal signed
envelope. The kernel never learns Matrix; Matrix never learns about brains.
"""
from multitude.pcm.envelope import (
    ENVELOPE_TYPES,
    ACTOR_KINDS,
    Envelope,
    EnvelopeError,
    canonical_bytes,
)
from multitude.pcm.identity import (
    generate_identity,
    load_identity,
    did_from_pubkey,
    pubkey_from_did,
    verify_did_binding,
)

__all__ = [
    "ACTOR_KINDS",
    "ENVELOPE_TYPES",
    "Envelope",
    "EnvelopeError",
    "canonical_bytes",
    "did_from_pubkey",
    "generate_identity",
    "load_identity",
    "pubkey_from_did",
    "verify_did_binding",
]