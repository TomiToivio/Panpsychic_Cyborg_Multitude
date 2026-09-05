# -*- coding: utf-8 -*-
"""PCM protocol package — Phase 0 of the PCM networking stack.

Per NETWORKING_STACK.md: node identity (did:key), the minimal signed
envelope, the Zenoh key-expression namespace, the semantic event model,
and the generic transport abstraction. The kernel never learns the
transport; the transport never learns about brains.
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
from multitude.pcm.namespace import (
    DOMAINS,
    PCM_KEY_PREFIX,
    validate_key,
)
from multitude.pcm.events import (
    EVENT_TYPES,
    PcmEvent,
    PcmIdentity,
    create_event,
)
from multitude.pcm.transport import (
    Transport,
    InMemoryTransport,
    TransportError,
)

__all__ = [
    "ACTOR_KINDS",
    "DOMAINS",
    "ENVELOPE_TYPES",
    "EVENT_TYPES",
    "PCM_KEY_PREFIX",
    "Envelope",
    "EnvelopeError",
    "InMemoryTransport",
    "PcmEvent",
    "PcmIdentity",
    "Transport",
    "canonical_bytes",
    "create_event",
    "did_from_pubkey",
    "generate_identity",
    "load_identity",
    "pubkey_from_did",
    "validate_key",
    "verify_did_binding",
]